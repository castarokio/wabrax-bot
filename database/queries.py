import aiosqlite
import logging
from datetime import datetime
from database.db import get_db

logger = logging.getLogger(__name__)


async def get_or_create_user(user_id: int, username: str = "", first_name: str = "", referrer_id: int = None):
    async with get_db() as db:
        cur = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        if not row:
            ref = None
            if referrer_id and referrer_id != user_id:
                # verify referrer exists
                ref_cur = await db.execute("SELECT user_id FROM users WHERE user_id = ?", (referrer_id,))
                if await ref_cur.fetchone():
                    ref = referrer_id
                    # increment referral count bonus if valid
                    await db.execute("UPDATE users SET tokens = tokens + 1 WHERE user_id = ?", (ref,))
            
            await db.execute("""
                INSERT INTO users (user_id, username, first_name, referrer_id)
                VALUES (?, ?, ?, ?)
            """, (user_id, username or "", first_name or "", ref))
            await db.commit()
            cur = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = await cur.fetchone()
        return dict(row)

async def get_user(user_id: int):
    async with get_db() as db:
        cur = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        return dict(row) if row else None

async def update_user_language(user_id: int, lang: str):
    async with get_db() as db:
        await db.execute("UPDATE users SET language = ? WHERE user_id = ?", (lang, user_id))
        await db.commit()

async def toggle_user_notification(user_id: int, notif_key: str):
    allowed = {"stock_alerts", "news_offers", "ref_bonuses"}
    if notif_key not in allowed:
        return None
    async with get_db() as db:
        await db.execute(f"UPDATE users SET {notif_key} = CASE WHEN {notif_key} = 1 THEN 0 ELSE 1 END WHERE user_id = ?", (user_id,))
        await db.commit()
        cur = await db.execute(f"SELECT {notif_key} FROM users WHERE user_id = ?", (user_id,))
        val = await cur.fetchone()
        return val[0] if val else 0

async def get_user_stats(user_id: int):
    async with get_db() as db:
        # Orders count & items bought
        cur = await db.execute("SELECT COUNT(*), COALESCE(SUM(price), 0) FROM orders WHERE user_id = ?", (user_id,))
        orders_count, total_spent = await cur.fetchone()
        
        cur = await db.execute("SELECT created_at FROM orders WHERE user_id = ? ORDER BY created_at DESC LIMIT 1", (user_id,))
        last_row = await cur.fetchone()
        last_order = last_row[0] if last_row else "—"

        # Referrals count
        cur = await db.execute("SELECT COUNT(*) FROM users WHERE referrer_id = ?", (user_id,))
        referrals = (await cur.fetchone())[0]

        return {
            "orders": orders_count,
            "items": orders_count,
            "spent": round(total_spent, 2),
            "last_order": last_order,
            "topups": 0,
            "withdrawn": 0.0,
            "pending": 0,
            "referrals": referrals,
            "invites": referrals
        }

async def get_admin_role(user_id: int):
    async with get_db() as db:
        cur = await db.execute("SELECT role FROM admins WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        return row["role"] if row else None

async def get_active_channels():
    async with get_db() as db:
        cur = await db.execute("SELECT * FROM channels WHERE is_active = 1")
        rows = await cur.fetchall()
        return [dict(r) for r in rows]

async def add_channel(channel_id: str, title: str, invite_link: str):
    async with get_db() as db:
        await db.execute("""
            INSERT INTO channels (channel_id, title, invite_link, is_active)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(channel_id) DO UPDATE SET title=excluded.title, invite_link=excluded.invite_link, is_active=1
        """, (channel_id, title, invite_link))
        await db.commit()

async def remove_channel(channel_id: str):
    async with get_db() as db:
        await db.execute("DELETE FROM channels WHERE channel_id = ?", (channel_id,))
        await db.commit()

async def get_in_stock_summary():
    async with get_db() as db:
        query = """
            SELECT p.*, c.name_en as category_name, COUNT(s.id) as stock_count
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            LEFT JOIN stock_items s ON p.id = s.product_id AND s.is_sold = 0
            WHERE p.is_active = 1
            GROUP BY p.id
            ORDER BY p.id ASC
        """
        cur = await db.execute(query)
        rows = await cur.fetchall()
        return [dict(r) for r in rows]

async def get_all_categories():
    async with get_db() as db:
        cur = await db.execute("SELECT * FROM categories ORDER BY order_priority ASC")
        rows = await cur.fetchall()
        return [dict(r) for r in rows]

async def get_products_by_category(category_id: int):
    async with get_db() as db:
        query = """
            SELECT p.*, c.name_en as category_name, COUNT(s.id) as stock_count
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            LEFT JOIN stock_items s ON p.id = s.product_id AND s.is_sold = 0
            WHERE p.category_id = ? AND p.is_active = 1
            GROUP BY p.id
            ORDER BY p.id ASC
        """
        cur = await db.execute(query, (category_id,))
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def get_product(product_id: int):
    async with get_db() as db:
        cur = await db.execute("""
            SELECT p.*, COUNT(s.id) as stock_count
            FROM products p
            LEFT JOIN stock_items s ON p.id = s.product_id AND s.is_sold = 0
            WHERE p.id = ?
            GROUP BY p.id
        """, (product_id,))
        row = await cur.fetchone()
        return dict(row) if row else None

async def buy_product_atomic(user_id: int, product_id: int):
    """
    Deducts balance, assigns an unsold stock item, creates an order.
    Returns (True, order_id, delivered_content) or (False, error_msg, None)
    """
    async with get_db() as db:
        # Check user balance
        u_cur = await db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        u_row = await u_cur.fetchone()
        if not u_row:
            return False, "User not found", None
        balance = u_row["balance"]

        # Check product
        p_cur = await db.execute("SELECT name, price FROM products WHERE id = ? AND is_active = 1", (product_id,))
        p_row = await p_cur.fetchone()
        if not p_row:
            return False, "Product not available", None
        
        price = p_row["price"]
        prod_name = p_row["name"]

        if balance < price:
            return False, f"Insufficient balance. Product costs {price} USDT, you have {balance} USDT.", None

        # Fetch one unsold stock item
        s_cur = await db.execute("SELECT id, content FROM stock_items WHERE product_id = ? AND is_sold = 0 LIMIT 1", (product_id,))
        stock_row = await s_cur.fetchone()
        if not stock_row:
            return False, "Item is out of stock.", None

        stock_id = stock_row["id"]
        content = stock_row["content"]

        # Deduct balance
        await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (price, user_id))
        
        # Mark stock item sold
        await db.execute("""
            UPDATE stock_items 
            SET is_sold = 1, sold_to_user_id = ?, sold_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        """, (user_id, stock_id))

        # Insert order
        order_cur = await db.execute("""
            INSERT INTO orders (user_id, product_id, product_name, price, content_delivered)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, product_id, prod_name, price, content))
        
        order_id = order_cur.lastrowid
        await db.commit()
        return True, order_id, content

async def get_user_orders(user_id: int):
    async with get_db() as db:
        cur = await db.execute("SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
        rows = await cur.fetchall()
        return [dict(r) for r in rows]

async def update_balance(user_id: int, delta: float):
    async with get_db() as db:
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (delta, user_id))
        await db.commit()

async def get_all_admins():
    async with get_db() as db:
        cur = await db.execute("SELECT * FROM admins ORDER BY role ASC")
        rows = await cur.fetchall()
        return [dict(r) for r in rows]

async def add_admin_user(user_id: int, role: str, added_by: int):
    async with get_db() as db:
        await db.execute("""
            INSERT INTO admins (user_id, role, added_by)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET role = excluded.role
        """, (user_id, role, added_by))
        await db.commit()

async def remove_admin_user(user_id: int):
    async with get_db() as db:
        await db.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
        await db.commit()

async def get_store_metrics():
    async with get_db() as db:
        u_count = (await (await db.execute("SELECT COUNT(*) FROM users")).fetchone())[0]
        o_count = (await (await db.execute("SELECT COUNT(*) FROM orders")).fetchone())[0]
        total_rev = (await (await db.execute("SELECT COALESCE(SUM(price), 0) FROM orders")).fetchone())[0]
        stock_count = (await (await db.execute("SELECT COUNT(*) FROM stock_items WHERE is_sold = 0")).fetchone())[0]
        return {
            "users": u_count,
            "orders": o_count,
            "revenue": round(total_rev, 2),
            "available_stock": stock_count
        }

async def buy_product_batch(user_id: int, product_id: int, quantity: int = 1):
    if quantity <= 0:
        return False, "Invalid quantity", None
    async with get_db() as db:
        u_cur = await db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        u_row = await u_cur.fetchone()
        if not u_row:
            return False, "User not found", None
        balance = u_row["balance"]

        p_cur = await db.execute("SELECT id, name, price FROM products WHERE id = ? AND is_active = 1", (product_id,))
        p_row = await p_cur.fetchone()
        if not p_row:
            return False, "Product not available", None

        p_dict = dict(p_row)
        price = p_dict["price"]
        total_cost = round(price * quantity, 2)
        prod_name = p_dict["name"]

        if balance < total_cost:
            deficit = round(total_cost - balance, 2)
            return False, f"Insufficient balance. Total is ${total_cost:.2f} USDT (Need +${deficit:.2f} USDT).", None

        delivered_items = []

        # ==================== 1. REAL ROBIXE COURSERA INTEGRATION ====================
        if "coursera" in prod_name.lower():
            from services.robixe import robixe_client
            robixe_token = await robixe_client.get_token()
            if robixe_token:
                for _ in range(quantity):
                    link_res = await robixe_client.create_activation_link()
                    full_url = link_res.get("full_url")
                    if full_url:
                        delivered_items.append(f"Coursera Premium Activation Link:\n{full_url}")
                    else:
                        logger.warning(f"Robixe returned without full_url: {link_res}")

        # ==================== 2. REAL VENTEBOT RESELLER INTEGRATION ====================
        if not delivered_items:
            from services.ventebot import ventebot_client
            ventebot_key = await ventebot_client.get_api_key()
            if ventebot_key:
                vb_pid = p_dict.get("ventebot_product_id") or p_dict["id"]
                try:
                    vb_res = await ventebot_client.create_order(
                        product_id=vb_pid,
                        quantity=quantity,
                        customer_reference=f"user_{user_id}"
                    )
                    if vb_res.get("success") and vb_res.get("items"):
                        delivered_items = [str(itm) for itm in vb_res["items"]]
                    else:
                        logger.info(f"VenteBot upstream response: {vb_res.get('message', vb_res)}")
                except Exception as ex:
                    logger.warning(f"VenteBot upstream call exception: {ex}")

        # ==================== 3. LOCAL STOCK FALLBACK ====================
        if not delivered_items:
            s_cur = await db.execute(
                "SELECT id, content FROM stock_items WHERE product_id = ? AND is_sold = 0 LIMIT ?",
                (product_id, quantity)
            )
            stock_rows = await s_cur.fetchall()
            if len(stock_rows) < quantity:
                return False, "This product is currently out of stock. Please check back shortly.", None

            for s_row in stock_rows:
                s_id = s_row["id"]
                content = s_row["content"]
                delivered_items.append(content)
                await db.execute(
                    "UPDATE stock_items SET is_sold = 1, sold_to_user_id = ?, sold_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (user_id, s_id)
                )


        # Deduct balance
        await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (total_cost, user_id))

        # Record into orders
        for item in delivered_items:
            await db.execute(
                "INSERT INTO orders (user_id, product_id, product_name, price, content_delivered) VALUES (?, ?, ?, ?, ?)",
                (user_id, product_id, prod_name, price, item)
            )

        # Update sold_count
        await db.execute("UPDATE products SET sold_count = COALESCE(sold_count, 0) + ? WHERE id = ?", (quantity, product_id))
        await db.commit()
        return True, total_cost, delivered_items


# Support tickets
async def create_support_ticket(user_id: int, username: str, message: str):
    async with get_db() as db:
        cur = await db.execute("""
            INSERT INTO support_tickets (user_id, username, message)
            VALUES (?, ?, ?)
        """, (user_id, username or "", message))
        ticket_id = cur.lastrowid
        await db.commit()
        return ticket_id

async def answer_support_ticket(ticket_id: int, reply: str):
    async with get_db() as db:
        await db.execute("""
            UPDATE support_tickets SET admin_reply = ?, status = 'answered' WHERE id = ?
        """, (reply, ticket_id))
        await db.commit()

# Topups
async def create_topup_invoice(user_id: int, amount: float):
    async with get_db() as db:
        cur = await db.execute("""
            INSERT INTO topups (user_id, amount, currency, status)
            VALUES (?, ?, 'USDT', 'pending')
        """, (user_id, amount))
        topup_id = cur.lastrowid
        await db.commit()
        return topup_id

async def get_user_topups(user_id: int):
    async with get_db() as db:
        cur = await db.execute("SELECT * FROM topups WHERE user_id = ? ORDER BY created_at DESC LIMIT 10", (user_id,))
        rows = await cur.fetchall()
        return [dict(r) for r in rows]

async def get_user_by_api_key(api_key: str):
    if not api_key:
        return None
    async with get_db() as db:
        cur = await db.execute("SELECT * FROM users WHERE api_key = ?", (api_key,))
        row = await cur.fetchone()
        return dict(row) if row else None

async def generate_user_api_key(user_id: int) -> str:
    import secrets
    new_key = f"vk_live_{secrets.token_hex(16)}"
    async with get_db() as db:
        await db.execute("UPDATE users SET api_key = ? WHERE user_id = ?", (new_key, user_id))
        await db.commit()
    return new_key

async def validate_coupon(code: str):
    if not code:
        return None
    async with get_db() as db:
        cur = await db.execute("SELECT * FROM coupons WHERE UPPER(code) = UPPER(?) AND is_active = 1", (code.strip(),))
        row = await cur.fetchone()
        if not row:
            return None
        c = dict(row)
        if c["used_count"] >= c["max_uses"]:
            return None
        return c

async def apply_coupon_use(coupon_id: int):
    async with get_db() as db:
        await db.execute("UPDATE coupons SET used_count = used_count + 1 WHERE id = ?", (coupon_id,))
        await db.commit()

async def search_products(query_str: str):
    if not query_str:
        return await get_in_stock_summary()
    pattern = f"%{query_str.strip()}%"
    async with get_db() as db:
        query = """
            SELECT p.*, COUNT(s.id) as stock_count
            FROM products p
            LEFT JOIN stock_items s ON p.id = s.product_id AND s.is_sold = 0
            WHERE p.is_active = 1 AND (p.name LIKE ? OR p.description LIKE ?)
            GROUP BY p.id
            HAVING stock_count > 0
            ORDER BY p.id ASC
        """
        cur = await db.execute(query, (pattern, pattern))
        rows = await cur.fetchall()
        return [dict(r) for r in rows]

async def get_user_stats(user_id: int) -> dict:
    async with get_db() as db:
        u_cur = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        u = await u_cur.fetchone()
        
        o_cur = await db.execute("SELECT COUNT(*) as count, COALESCE(SUM(price), 0) as spent FROM orders WHERE user_id = ?", (user_id,))
        o_stat = await o_cur.fetchone()

        r_cur = await db.execute("SELECT COUNT(*) as refs FROM users WHERE referrer_id = ?", (user_id,))
        r_stat = await r_cur.fetchone()

        return {
            "user_id": user_id,
            "balance": u["balance"] if u else 0.0,
            "total_orders": o_stat["count"] if o_stat else 0,
            "total_spent": o_stat["spent"] if o_stat else 0.0,
            "referrals_count": r_stat["refs"] if r_stat else 0,
            "member_since": u["joined_at"][:10] if u and u["joined_at"] else "2026-09-01"
        }

async def get_system_setting(key: str, default: str = "") -> str:
    async with get_db() as db:
        cur = await db.execute("SELECT value FROM system_settings WHERE key = ?", (key,))
        row = await cur.fetchone()
        if row and row["value"]:
            return row["value"]
        return default

async def set_system_setting(key: str, value: str):
    async with get_db() as db:
        await db.execute("""
            INSERT INTO system_settings (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
        """, (key, value))
        await db.commit()

async def update_product_field(product_id: int, field: str, value):
    """Safely update a product attribute (name, price, description, banner_image, icon_brand, is_active)."""
    allowed_fields = {"name", "price", "description", "banner_image", "icon_brand", "is_active", "item_type"}
    if field not in allowed_fields:
        raise ValueError(f"Field '{field}' is not allowed for update.")
    async with get_db() as db:
        await db.execute(f"UPDATE products SET {field} = ? WHERE id = ?", (value, product_id))
        await db.commit()

async def clear_product_stock(product_id: int) -> int:
    """Clear all unsold stock items for a product."""
    async with get_db() as db:
        cur = await db.execute("DELETE FROM stock_items WHERE product_id = ? AND is_sold = 0", (product_id,))
        count = cur.rowcount
        await db.commit()
        return count

async def get_all_users_paginated(page: int = 1, per_page: int = 8) -> tuple[list[dict], int]:
    """Get paginated users and total user count."""
    offset = max(0, (page - 1) * per_page)
    async with get_db() as db:
        count_cur = await db.execute("SELECT COUNT(*) FROM users")
        total = (await count_cur.fetchone())[0]

        cur = await db.execute("""
            SELECT u.*, 
                   COUNT(o.id) as order_count,
                   COALESCE(SUM(o.price), 0) as total_spent
            FROM users u
            LEFT JOIN orders o ON u.user_id = o.user_id
            GROUP BY u.user_id
            ORDER BY u.joined_at DESC
            LIMIT ? OFFSET ?
        """, (per_page, offset))
        rows = await cur.fetchall()
        return [dict(r) for r in rows], total

async def search_users(query: str) -> list[dict]:
    """Search users by username (with or without @) or numeric telegram ID."""
    clean_q = query.strip().lstrip("@")
    async with get_db() as db:
        if clean_q.isdigit():
            cur = await db.execute("""
                SELECT u.*, COUNT(o.id) as order_count, COALESCE(SUM(o.price), 0) as total_spent
                FROM users u
                LEFT JOIN orders o ON u.user_id = o.user_id
                WHERE u.user_id = ? OR u.username LIKE ?
                GROUP BY u.user_id
                LIMIT 10
            """, (int(clean_q), f"%{clean_q}%"))
        else:
            cur = await db.execute("""
                SELECT u.*, COUNT(o.id) as order_count, COALESCE(SUM(o.price), 0) as total_spent
                FROM users u
                LEFT JOIN orders o ON u.user_id = o.user_id
                WHERE u.username LIKE ? OR u.first_name LIKE ?
                GROUP BY u.user_id
                LIMIT 10
            """, (f"%{clean_q}%", f"%{clean_q}%"))
        rows = await cur.fetchall()
        return [dict(r) for r in rows]

async def toggle_user_ban(user_id: int, ban_status: int = None) -> int:
    """Ban or unban a user. Returns new is_banned status (0 or 1)."""
    async with get_db() as db:
        if ban_status is not None:
            new_status = 1 if ban_status else 0
        else:
            cur = await db.execute("SELECT is_banned FROM users WHERE user_id = ?", (user_id,))
            row = await cur.fetchone()
            curr = row["is_banned"] if row else 0
            new_status = 0 if curr == 1 else 1

        await db.execute("UPDATE users SET is_banned = ? WHERE user_id = ?", (new_status, user_id))
        await db.commit()
        return new_status

async def get_user_purchases_detailed(user_id: int, limit: int = 10) -> list[dict]:
    """Get detailed recent orders for a user."""
    async with get_db() as db:
        cur = await db.execute("""
            SELECT id, product_name, price, content_delivered, created_at
            FROM orders
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (user_id, limit))
        rows = await cur.fetchall()
        return [dict(r) for r in rows]





