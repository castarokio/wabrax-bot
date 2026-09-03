from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.queries import (
    get_all_categories, get_products_by_category, get_product, buy_product_batch, get_user
)
from keyboards.inline_user import (
    get_shop_categories_keyboard, get_products_keyboard, get_product_quantity_keyboard
)
from config.emojis import tg_e, EMOJI_IDS

router = Router(name="shop")

class ShopStates(StatesGroup):
    waiting_custom_qty = State()

import os
from aiogram.types import FSInputFile, InputMediaPhoto

@router.callback_query(F.data == "menu:shop")
async def show_categories(callback: CallbackQuery, t, state: FSMContext):
    await state.clear()
    categories = await get_all_categories()
    text = (
        f"{tg_e('CART')} <b>Product Categories</b>\n\n"
        f"Select a category to browse available digital subscriptions and licenses:"
    )
    kb = get_shop_categories_keyboard(categories, t)
    if callback.message.photo:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
    else:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("shop_cat:"))
async def show_products_in_category(callback: CallbackQuery, t, state: FSMContext):
    await state.clear()
    cat_id = int(callback.data.split(":")[1])
    products = await get_products_by_category(cat_id)
    if not products:
        text = "No products found in this category currently."
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅ Back", callback_data="menu:shop")]])
        if callback.message.photo:
            await callback.message.delete()
            await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
        else:
            await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await callback.answer()
        return

    # Calculate price range
    prices = [p["price"] for p in products]
    min_p, max_p = min(prices), max(prices)
    price_range = f"${min_p:.2f} — ${max_p:.2f}" if min_p != max_p else f"${min_p:.2f}"
    cat_name = products[0].get("category_name", "Products")

    # Exact layout matching Screenshot 2
    text = (
        f"📁 <b>{cat_name}</b>\n\n"
        f"💰 <b>Prix : {price_range}</b>\n"
        f"👇 <i>Choisissez votre variante :</i>"
    )
    kb = get_products_keyboard(products, t)

    # Check banner image
    img_path = products[0].get("image_url") or "static/banners/claude_api.jpg"
    if os.path.exists(img_path):
        if callback.message.photo:
            await callback.message.edit_media(
                media=InputMediaPhoto(media=FSInputFile(img_path), caption=text, parse_mode="HTML"),
                reply_markup=kb
            )
        else:
            await callback.message.delete()
            await callback.message.answer_photo(photo=FSInputFile(img_path), caption=text, reply_markup=kb, parse_mode="HTML")
    else:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("shop_prod:"))
async def show_product_detail(callback: CallbackQuery, t, state: FSMContext):
    await state.clear()
    prod_id = int(callback.data.split(":")[1])
    prod = await get_product(prod_id)
    if not prod:
        await callback.answer("Product not found", show_alert=True)
        return

    stock = prod.get("stock_count", 0)
    price_val = f"{prod['price']:.2f}"
    warranty_val = prod.get("warranty_days", 30)
    sold_val = prod.get("sold_count", 0)
    cat_id = prod.get("category_id", 1)

    # Exact layout matching Screenshot 1
    text = (
        f"✨ <b>{prod['name']}</b>\n"
        f"💵 <b>Price: ${price_val}</b>\n"
        f"🛡️ <b>Warranty: {warranty_val} days</b>\n"
        f"📦 <b>Stock: {stock} accounts</b>\n"
        f"📊 <b>Sold: {sold_val} accounts</b>\n\n"
        f"” <b>Description:</b>\n"
        f"{prod['description']}"
    )

    kb = get_product_quantity_keyboard(prod_id, stock, category_id=cat_id)
    img_path = prod.get("image_url") or "static/banners/gemini_18m.jpg"
    if os.path.exists(img_path):
        if callback.message.photo:
            await callback.message.edit_media(
                media=InputMediaPhoto(media=FSInputFile(img_path), caption=text, parse_mode="HTML"),
                reply_markup=kb
            )
        else:
            await callback.message.delete()
            await callback.message.answer_photo(photo=FSInputFile(img_path), caption=text, reply_markup=kb, parse_mode="HTML")
    else:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("buy_qty:"))
async def execute_quantity_purchase(callback: CallbackQuery, t, state: FSMContext):
    await state.clear()
    parts = callback.data.split(":")
    prod_id = int(parts[1])
    qty = int(parts[2])
    await process_purchase(callback.message, callback.from_user.id, prod_id, qty, is_callback=True, query=callback)

@router.callback_query(F.data.startswith("buy_custom:"))
async def prompt_custom_qty(callback: CallbackQuery, state: FSMContext):
    prod_id = int(callback.data.split(":")[1])
    await state.set_state(ShopStates.waiting_custom_qty)
    await state.update_data(prod_id=prod_id)
    text = (
        f"{tg_e('CART')} <b>Custom Purchase Quantity</b>\n\n"
        f"Type how many accounts you want to buy (e.g. <code>5</code>):\n\n"
        f"/cancel — stop"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Back", callback_data=f"shop_prod:{prod_id}")]])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@router.message(ShopStates.waiting_custom_qty)
async def process_custom_qty_input(message: Message, state: FSMContext):
    if message.text and message.text.startswith("/"):
        await state.clear()
        return

    if not message.text.strip().isdigit():
        await message.answer("Please type a valid positive number.")
        return

    qty = int(message.text.strip())
    if qty <= 0:
        await message.answer("Quantity must be at least 1.")
        return

    data = await state.get_data()
    prod_id = data["prod_id"]
    await state.clear()
    await process_purchase(message, message.from_user.id, prod_id, qty, is_callback=False)

async def process_purchase(message_or_callback, user_id: int, prod_id: int, qty: int, is_callback: bool = False, query: CallbackQuery = None):
    success, total_or_err, items = await buy_product_batch(user_id, prod_id, qty)
    if not success:
        if is_callback and query:
            await query.answer(total_or_err, show_alert=True)
            # If insufficient funds, offer deposit button
            user = await get_user(user_id)
            bal = user.get("balance", 0.0) if user else 0.0
            kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="Deposit USDT", style="success", icon_custom_emoji_id=EMOJI_IDS["PLUS_GREEN"], callback_data="wallet:deposit")],
                    [InlineKeyboardButton(text="🔙 Back", callback_data=f"shop_prod:{prod_id}")]
                ]
            )
            await query.message.answer(
                f"{tg_e('CROSS_RED')} <b>Insufficient Balance</b>\n\n"
                f"You need <b>{total_or_err.split()[4]} USDT</b>.\n"
                f"Your balance: <b>{bal} USDT</b>\n\n"
                f"Please top up your wallet below:",
                reply_markup=kb,
                parse_mode="HTML"
            )
        else:
            await message_or_callback.answer(f"{tg_e('CROSS_RED')} {total_or_err}", parse_mode="HTML")
        return

    user = await get_user(user_id)
    new_bal = user.get("balance", 0.0)
    delivered_formatted = "\n".join([f"<code>{itm}</code>" for itm in items])

    text = (
        f"{tg_e('CHECKMARK_GREEN')} <b>Purchase Successful!</b>\n\n"
        f"<b>Units Bought:</b> {qty}\n"
        f"<b>Total Paid:</b> {total_or_err} USDT\n"
        f"<b>Remaining Balance:</b> {new_bal} USDT\n\n"
        f"<b>Delivered Accounts / Credentials:</b>\n"
        f"{delivered_formatted}\n\n"
        f"<i>Saved to your orders list. You can view them anytime in 'My profile' > 'My orders'.</i>"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛒 View My Orders", callback_data="profile:orders")],
            [InlineKeyboardButton(text="🏪 Back to Shop", callback_data="menu:shop")]
        ]
    )

    if is_callback and query:
        await query.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await query.answer()
    else:
        await message_or_callback.answer(text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data == "out_of_stock")
async def cb_out_of_stock(callback: CallbackQuery):
    await callback.answer("This product is currently out of stock. Check back soon!", show_alert=True)

@router.message(F.text.startswith("/search"))
async def cmd_search_products(message: Message, t, state: FSMContext):
    await state.clear()
    query_parts = message.text.split(maxsplit=1)
    if len(query_parts) < 2 or not query_parts[1].strip():
        await message.answer(
            f"{tg_e('SEARCH')} <b>Search Catalog</b>\n\n"
            f"Usage: <code>/search &lt;product name&gt;</code>\n"
            f"Example: <code>/search gpt</code> or <code>/search claude</code>",
            parse_mode="HTML"
        )
        return

    q = query_parts[1].strip()
    from database.queries import search_products
    results = await search_products(q)
    if not results:
        await message.answer(
            f"{tg_e('SEARCH')} No matching products found for '<b>{q}</b>'.\n\n"
            f"Try browsing our full catalog with /start.",
            parse_mode="HTML"
        )
        return

    buttons = []
    for p in results[:8]:
        brand_icon = EMOJI_IDS.get(p.get("icon_brand", "CART"), EMOJI_IDS["CART"])
        buttons.append([
            InlineKeyboardButton(
                text=f"{p['name']} · ${p['price']} ({p.get('stock_count', 0)} left)",
                style="primary",
                icon_custom_emoji_id=brand_icon,
                callback_data=f"shop_prod:{p['id']}"
            )
        ])
    buttons.append([InlineKeyboardButton(text="🏪 Browse All Categories", style="success", callback_data="menu:shop")])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer(
        f"{tg_e('SEARCH')} <b>Found {len(results)} products matching '{q}':</b>",
        reply_markup=kb,
        parse_mode="HTML"
    )

