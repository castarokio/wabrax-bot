import os
import json
import logging
from aiohttp import web
from database.queries import (
    get_in_stock_summary, get_user, get_user_orders,
    buy_product_batch, create_topup_invoice, get_product,
    get_user_by_api_key, get_user_topups
)
from database.db import get_db
from services.ventebot import ventebot_client
from services.robixe import robixe_client

logger = logging.getLogger(__name__)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "webapp")
EMOJI_CACHE_DIR = os.path.join(STATIC_DIR, "emojis")
os.makedirs(EMOJI_CACHE_DIR, exist_ok=True)

# Helper to authenticate reseller API keys
async def authenticate_reseller(request) -> tuple:
    api_key = request.headers.get("X-Reseller-Key") or request.headers.get("X-API-Key")
    if not api_key:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            api_key = auth_header.replace("Bearer ", "").strip()

    if not api_key:
        return None, web.json_response(
            {"success": False, "code": "INVALID_API_KEY", "message": "Missing reseller API key header"},
            status=401
        )

    user = await get_user_by_api_key(api_key)
    if not user:
        return None, web.json_response(
            {"success": False, "code": "INVALID_API_KEY", "message": "Invalid or revoked reseller API key"},
            status=401
        )

    if user.get("is_banned") == 1:
        return None, web.json_response(
            {"success": False, "code": "FORBIDDEN", "message": "Reseller account suspended"},
            status=403
        )

    return user, None

_BOT_INSTANCE = None

def set_bot_instance(bot):
    global _BOT_INSTANCE
    _BOT_INSTANCE = bot

# ==================== WEBAPP STATIC & EMOJI ====================
async def handle_index(request):
    return web.FileResponse(os.path.join(STATIC_DIR, "index.html"))

async def handle_emoji(request):
    """Dynamic custom emoji proxy delivering WebP graphics to the Mini App."""
    emoji_id = request.match_info.get("emoji_id", "")
    local_path = os.path.join(EMOJI_CACHE_DIR, f"{emoji_id}.webp")
    if os.path.exists(local_path):
        return web.FileResponse(local_path, headers={"Cache-Control": "public, max-age=604800"})

    # Fallback to Telegram Bot API
    bot = _BOT_INSTANCE or request.app.get("bot")
    if bot:
        try:
            stickers = await bot.get_custom_emoji_stickers(custom_emoji_ids=[emoji_id])
            if stickers:
                st = stickers[0]
                fid = st.thumbnail.file_id if st.thumbnail else st.file_id
                f = await bot.get_file(fid)
                import aiohttp
                url = f"https://api.telegram.org/file/bot{bot.token}/{f.file_path}"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            content = await resp.read()
                            with open(local_path, "wb") as out:
                                out.write(content)
                            return web.Response(body=content, content_type="image/webp", headers={"Cache-Control": "public, max-age=604800"})
        except Exception as e:
            logger.debug(f"Emoji fetch failed for {emoji_id}: {e}")

    return web.Response(status=404)


# ==================== MINI APP INTERNAL API ====================
async def api_get_products(request):
    products = await get_in_stock_summary()
    return web.json_response({"ok": True, "products": products})

async def api_get_user(request):
    uid_str = request.query.get("user_id")
    if not uid_str or not uid_str.isdigit():
        return web.json_response({"ok": False, "error": "Invalid user_id"}, status=400)
    user = await get_user(int(uid_str))
    if not user:
        return web.json_response({"ok": True, "user": {"user_id": int(uid_str), "balance": 0.0}})
    return web.json_response({"ok": True, "user": user})

async def api_get_orders(request):
    uid_str = request.query.get("user_id")
    if not uid_str or not uid_str.isdigit():
        return web.json_response({"ok": False, "error": "Invalid user_id"}, status=400)
    orders = await get_user_orders(int(uid_str))
    return web.json_response({"ok": True, "orders": orders})

async def api_post_buy(request):
    try:
        data = await request.json()
        user_id = int(data.get("user_id"))
        product_id = int(data.get("product_id"))
        quantity = int(data.get("quantity", 1))
        coupon_code = data.get("coupon_code", "").strip()
    except Exception:
        return web.json_response({"ok": False, "error": "Invalid request payload"}, status=400)

    try:
        from database.queries import validate_coupon, apply_coupon_use
        discount_pct = 0
        coupon_obj = None
        if coupon_code:
            coupon_obj = await validate_coupon(coupon_code)
            if coupon_obj:
                discount_pct = coupon_obj["discount_percent"]

        success, total_or_err, items = await buy_product_batch(user_id, product_id, quantity, discount_percent=discount_pct)
        if not success:

            return web.json_response({"ok": False, "error": total_or_err}, status=200)

        if coupon_obj:
            await apply_coupon_use(coupon_obj["id"])

        return web.json_response({
            "ok": True,
            "total_cost": total_or_err,
            "discount_applied": discount_pct,
            "items": items
        })
    except Exception as e:
        logger.error(f"api_post_buy unexpected exception: {e}", exc_info=True)
        return web.json_response({"ok": False, "error": f"Error processing purchase: {str(e)}"}, status=200)


async def api_get_search(request):
    q = request.query.get("q", "").strip()
    from database.queries import search_products
    prods = await search_products(q)
    return web.json_response({"ok": True, "products": prods})

async def api_validate_coupon(request):
    try:
        data = await request.json()
        code = data.get("code", "")
    except Exception:
        return web.json_response({"ok": False, "error": "Invalid payload"}, status=400)

    from database.queries import validate_coupon
    c = await validate_coupon(code)
    if not c:
        return web.json_response({"ok": False, "error": "Invalid or expired coupon code"}, status=404)
    return web.json_response({"ok": True, "discount_percent": c["discount_percent"], "code": c["code"]})

async def api_get_user_stats(request):
    uid_str = request.query.get("user_id")
    if not uid_str or not uid_str.isdigit():
        return web.json_response({"ok": False, "error": "Invalid user_id"}, status=400)
    from database.queries import get_user_stats
    stats = await get_user_stats(int(uid_str))
    return web.json_response({"ok": True, "stats": stats})

async def api_post_support(request):
    try:
        data = await request.json()
        uid = int(data.get("user_id"))
        username = data.get("username", "")
        message = data.get("message", "").strip()
    except Exception:
        return web.json_response({"ok": False, "error": "Invalid payload"}, status=400)

    if not message:
        return web.json_response({"ok": False, "error": "Message cannot be empty"}, status=400)

    from database.queries import create_support_ticket
    ticket_id = await create_support_ticket(uid, username, message)

    # Notify admins if bot available
    bot = request.app.get("bot") or _BOT_INSTANCE
    if bot:
        from config.settings import SUPER_ADMIN_IDS
        for a_id in SUPER_ADMIN_IDS:
            try:
                await bot.send_message(
                    chat_id=a_id,
                    text=f"📨 <b>New Mini App Support Ticket #{ticket_id}</b>\nFrom: <code>{uid}</code> (@{username})\n\n<blockquote>{message}</blockquote>",
                    parse_mode="HTML"
                )
            except Exception:
                pass

    return web.json_response({"ok": True, "ticket_id": ticket_id})

async def api_post_topup(request):
    try:
        data = await request.json()
        user_id = int(data.get("user_id"))
        amount = float(data.get("amount", 20.0))
        network = data.get("network", "USDT (TON)")
    except Exception:
        return web.json_response({"ok": False, "error": "Invalid payload"}, status=400)

    invoice_id = await create_topup_invoice(user_id, amount)

    if network == "Binance Pay":
        from services.binance_pay import binance_pay_service
        res = await binance_pay_service.create_order(
            order_id=f"ORD_{invoice_id}",
            amount=amount,
            currency="USDT",
            description=f"Store Wallet Deposit #{invoice_id}"
        )
        if res.get("type") == "api" and res.get("checkout_url"):
            return web.json_response({
                "ok": True,
                "invoice_id": invoice_id,
                "amount": amount,
                "network": network,
                "is_binance": True,
                "checkout_url": res["checkout_url"],
                "address": f"Binance Checkout Link Available"
            })
        else:
            pay_id = res.get("pay_id", "Not configured")
            return web.json_response({
                "ok": True,
                "invoice_id": invoice_id,
                "amount": amount,
                "network": network,
                "is_binance": True,
                "address": f"Pay ID: {pay_id} (Ref: ORD-{invoice_id})"
            })

    addresses = {
        "USDT (TON)": os.getenv("DEPOSIT_ADDRESS_TON", "UQBYFi938472910294729482749284729482948274"),
        "USDT (TRC-20)": os.getenv("DEPOSIT_ADDRESS_TRC20", "TXs9284719284729482749284729482948"),
        "USDT (BEP-20)": os.getenv("DEPOSIT_ADDRESS_BEP20", "0x71C2849284729482749284729482948274928472"),
        "Telegram Stars": "telegram_stars_instant"
    }
    addr = addresses.get(network, addresses["USDT (TON)"])


    return web.json_response({
        "ok": True,
        "invoice_id": invoice_id,
        "amount": amount,
        "network": network,
        "address": addr
    })



# ==================== VENTEBOT RESELLER OAS 3.0 API ====================
async def reseller_get_me(request):
    user, err_resp = await authenticate_reseller(request)
    if err_resp:
        return err_resp

    return web.json_response({
        "success": True,
        "user_telegram_id": user["user_id"],
        "username": user["username"] or "",
        "first_name": user["first_name"] or "Reseller",
        "wallet_balance": float(user["balance"]),
        "key_name": "Partner Bot",
        "key_prefix": (user.get("api_key") or "vk_")[0:7]
    })

async def reseller_get_products(request):
    user, err_resp = await authenticate_reseller(request)
    if err_resp:
        return err_resp

    products = await get_in_stock_summary()
    formatted = []
    for p in products:
        formatted.append({
            "id": p["id"],
            "name": p["name"],
            "description": p.get("description", ""),
            "price": float(p["price"]),
            "stock_count": p.get("stock_count", 0),
            "warranty_days": p.get("warranty_days", 30),
            "is_active": True
        })
    return web.json_response(formatted)

async def reseller_post_quote(request):
    user, err_resp = await authenticate_reseller(request)
    if err_resp:
        return err_resp

    try:
        data = await request.json()
        pid = int(data["product_id"])
        qty = int(data.get("quantity", 1))
    except Exception:
        return web.json_response({"success": False, "message": "Invalid request body"}, status=422)

    prod = await get_product(pid)
    if not prod:
        return web.json_response({"success": False, "message": "Product not found"}, status=404)

    total = round(prod["price"] * qty, 2)
    return web.json_response({
        "success": True,
        "product_id": pid,
        "unit_price": prod["price"],
        "quantity": qty,
        "total": total
    })

async def reseller_post_orders(request):
    user, err_resp = await authenticate_reseller(request)
    if err_resp:
        return err_resp

    try:
        data = await request.json()
        pid = int(data["product_id"])
        qty = int(data.get("quantity", 1))
        cust_ref = data.get("customer_reference", "")
        idempotency_key = data.get("idempotency_key", "")
    except Exception:
        return web.json_response({"success": False, "message": "Invalid order payload"}, status=422)

    prod = await get_product(pid)
    if not prod:
        return web.json_response({"success": False, "message": "Product not found"}, status=404)

    # Execute purchase from user wallet
    success, total_or_err, items = await buy_product_batch(user["user_id"], pid, qty)
    if not success:
        if "Insufficient balance" in total_or_err:
            return web.json_response({"success": False, "code": "INSUFFICIENT_FUNDS", "message": total_or_err}, status=402)
        return web.json_response({"success": False, "message": total_or_err}, status=400)

    u_after = await get_user(user["user_id"])
    item_objs = [{"id": i + 1, "account_data": itm} for i, itm in enumerate(items)]

    return web.json_response({
        "success": True,
        "status": "ok",
        "idempotent": False,
        "balance_after": u_after["balance"],
        "unit_price": prod["price"],
        "standard_unit_price": prod["price"],
        "pricing_type": "standard",
        "total": total_or_err,
        "order": {
            "id": os.urandom(4).hex(),
            "status": "COMPLETED",
            "product_id": pid,
            "product_name": prod["name"],
            "quantity": qty,
            "amount_usd": total_or_err,
            "delivery_type": "instant_stock",
            "customer_reference": cust_ref,
            "idempotency_key": idempotency_key,
            "created_at": "2026-09-03 16:00:00",
            "items": item_objs
        }
    })

async def reseller_get_wallet_transactions(request):
    user, err_resp = await authenticate_reseller(request)
    if err_resp:
        return err_resp

    topups = await get_user_topups(user["user_id"])
    orders = await get_user_orders(user["user_id"])
    txs = []
    for t in topups:
        txs.append({
            "id": t["id"],
            "type": "deposit",
            "amount": t["amount"],
            "created_at": str(t["created_at"])
        })
    for o in orders:
        txs.append({
            "id": o["id"],
            "type": "purchase",
            "amount": -o["price"],
            "description": o["product_name"],
            "created_at": str(o["created_at"])
        })
    return web.json_response(txs)

def create_webapp_app(bot=None):
    app = web.Application()
    app["bot"] = bot

    # WebApp Static Files & Emoji Caching
    app.router.add_get("/", handle_index)
    app.router.add_get("/api/emoji/{emoji_id}", handle_emoji)
    app.router.add_static("/static", STATIC_DIR)

    # Mini App Internal Endpoints
    app.router.add_get("/api/products", api_get_products)
    app.router.add_get("/api/search", api_get_search)
    app.router.add_get("/api/user", api_get_user)
    app.router.add_get("/api/user/stats", api_get_user_stats)
    app.router.add_get("/api/orders", api_get_orders)
    app.router.add_post("/api/buy", api_post_buy)
    app.router.add_post("/api/coupon/validate", api_validate_coupon)
    app.router.add_post("/api/support", api_post_support)
    app.router.add_post("/api/topup", api_post_topup)

    # VenteBot Reseller OAS 3.0 Compatible Endpoints
    app.router.add_get("/api/reseller/me", reseller_get_me)
    app.router.add_get("/api/reseller/products", reseller_get_products)
    app.router.add_post("/api/reseller/quote", reseller_post_quote)
    app.router.add_post("/api/reseller/orders", reseller_post_orders)
    app.router.add_get("/api/reseller/wallet/transactions", reseller_get_wallet_transactions)

    return app

if __name__ == "__main__":
    app = create_webapp_app()
    web.run_app(app, host="127.0.0.1", port=8080)
