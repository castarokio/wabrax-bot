import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.queries import (
    get_admin_role, get_store_metrics, get_active_channels, add_channel, remove_channel,
    get_in_stock_summary, get_all_admins, add_admin_user, remove_admin_user, update_balance,
    get_product, get_user, get_user_stats, update_product_field, clear_product_stock,
    get_all_users_paginated, search_users, toggle_user_ban, get_user_purchases_detailed,
    set_system_setting, get_system_setting
)
from keyboards.inline_admin import (
    get_admin_main_keyboard, get_admin_channels_keyboard, get_admin_products_keyboard,
    get_admin_product_detail_keyboard, get_admin_users_keyboard, get_admin_admins_keyboard,
    get_admin_users_list_keyboard, get_admin_user_card_keyboard
)
from config.emojis import tg_e, EMOJI_IDS
from database.db import get_db
from services.binance_pay import binance_pay_service

logger = logging.getLogger(__name__)

router = Router(name="admin")

class AdminStates(StatesGroup):
    waiting_channel_info = State()
    waiting_mini_admin_id = State()
    waiting_stock_info = State()
    waiting_new_product_info = State()
    waiting_stock_for_prod = State()
    waiting_user_lookup = State()
    waiting_balance_adjust = State()
    waiting_broadcast_text = State()
    waiting_edit_price = State()
    waiting_edit_desc = State()
    waiting_edit_pic = State()
    waiting_edit_name = State()
    waiting_add_funds = State()
    waiting_rem_funds = State()
    waiting_binance_keys = State()
    waiting_binance_pay_id = State()


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    role = await get_admin_role(message.from_user.id)
    if not role:
        return

    is_super = (role == "SUPER_ADMIN")
    metrics = await get_store_metrics()

    text = (
        f"{tg_e('ADMIN_BADGE')} <b>Store Management Dashboard</b>\n"
        f"<b>Authorization Level:</b> {role}\n\n"
        f"{tg_e('ADD_PERSON')} <b>Registered Buyers:</b> {metrics['users']}\n"
        f"{tg_e('CART')} <b>Total Orders:</b> {metrics['orders']}\n"
        f"{tg_e('USDT')} <b>Total Revenue:</b> {metrics['revenue']} USDT\n"
        f"{tg_e('VIP_YELLOW')} <b>Available Stock Items:</b> {metrics['available_stock']}\n\n"
        f"<i>Select an administrative department:</i>"
    )
    await message.answer(text, reply_markup=get_admin_main_keyboard(is_super), parse_mode="HTML")

@router.callback_query(F.data == "admin:main")
async def cb_admin_main(callback: CallbackQuery):
    role = await get_admin_role(callback.from_user.id)
    if not role:
        await callback.answer("Unauthorized", show_alert=True)
        return
    is_super = (role == "SUPER_ADMIN")
    metrics = await get_store_metrics()
    text = (
        f"{tg_e('ADMIN_BADGE')} <b>Store Management Dashboard</b>\n"
        f"<b>Authorization Level:</b> {role}\n\n"
        f"{tg_e('ADD_PERSON')} <b>Registered Buyers:</b> {metrics['users']}\n"
        f"{tg_e('CART')} <b>Total Orders:</b> {metrics['orders']}\n"
        f"{tg_e('USDT')} <b>Total Revenue:</b> {metrics['revenue']} USDT\n"
        f"{tg_e('VIP_YELLOW')} <b>Available Stock Items:</b> {metrics['available_stock']}\n"
    )
    await callback.message.edit_text(text, reply_markup=get_admin_main_keyboard(is_super), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "admin:analytics")
async def cb_admin_analytics(callback: CallbackQuery):
    metrics = await get_store_metrics()
    async with get_db() as db:
        recent_orders = await (await db.execute("SELECT product_name, price, created_at FROM orders ORDER BY created_at DESC LIMIT 5")).fetchall()

    orders_log = ""
    for o in recent_orders:
        orders_log += f"\n• <code>{o['product_name']}</code> · {o['price']} USDT"

    text = (
        f"{tg_e('STATS')} <b>Store Financial & Inventory Analytics</b>\n\n"
        f"• Total Buyers Registered: <b>{metrics['users']}</b>\n"
        f"• Total Completed Orders: <b>{metrics['orders']}</b>\n"
        f"• Gross Volume Processed: <b>{metrics['revenue']} USDT</b>\n"
        f"• Active Digital Stock Units: <b>{metrics['available_stock']}</b>\n\n"
        f"<b>Recent Purchases:</b>{orders_log if orders_log else ' None yet'}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="<", callback_data="admin:main")]])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

# ==================== CHANNELS MANAGEMENT ====================
@router.callback_query(F.data == "admin:channels")
async def cb_admin_channels(callback: CallbackQuery):
    role = await get_admin_role(callback.from_user.id)
    if role != "SUPER_ADMIN":
        await callback.answer("Super Admin privileges required", show_alert=True)
        return

    channels = await get_active_channels()
    text = (
        f"{tg_e('LOCK')} <b>Mandatory Channels (Force-Subscribe)</b>\n\n"
        f"Users must subscribe to all listed channels before accessing store functions.\n\n"
        f"<b>Currently Configured:</b> {len(channels)} channel(s)"
    )
    await callback.message.edit_text(text, reply_markup=get_admin_channels_keyboard(channels), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("admin:del_channel:"))
async def cb_del_channel(callback: CallbackQuery):
    ch_id = callback.data.replace("admin:del_channel:", "")
    await remove_channel(ch_id)
    channels = await get_active_channels()
    await callback.message.edit_reply_markup(reply_markup=get_admin_channels_keyboard(channels))
    await callback.answer("Channel removed from mandatory list.", show_alert=True)

@router.callback_query(F.data == "admin:add_channel")
async def cb_add_channel_prompt(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_channel_info)
    text = (
        f"{tg_e('PLUS_GREEN')} <b>Add Mandatory Channel</b>\n\n"
        f"Send the channel parameters in this exact format:\n"
        f"<code>channel_id | Title | Invite Link</code>\n\n"
        f"<b>Example:</b>\n"
        f"<code>@mychannel | Official Announcements | https://t.me/mychannel</code>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="<", callback_data="admin:channels")]])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@router.message(AdminStates.waiting_channel_info)
async def process_add_channel(message: Message, state: FSMContext):
    parts = [p.strip() for p in message.text.split("|")]
    if len(parts) < 3:
        await message.answer("Invalid format. Send: <code>channel_id | Title | Link</code>", parse_mode="HTML")
        return
    ch_id, title, link = parts[0], parts[1], parts[2]
    await add_channel(ch_id, title, link)
    await state.clear()
    channels = await get_active_channels()
    await message.answer(
        f"{tg_e('CHECKMARK_GREEN')} Channel <b>{title}</b> ({ch_id}) has been successfully linked!",
        reply_markup=get_admin_channels_keyboard(channels),
        parse_mode="HTML"
    )

# ==================== PRODUCTS & STOCK ====================
@router.callback_query(F.data == "admin:products")
async def cb_admin_products(callback: CallbackQuery):
    items = await get_in_stock_summary()
    text = (
        f"{tg_e('CART')} <b>Product & Inventory Management</b>\n\n"
        f"Tap any product to inspect details, restock keys/credentials, or toggle availability:"
    )
    await callback.message.edit_text(text, reply_markup=get_admin_products_keyboard(items), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("admin:prod_view:"))
async def cb_admin_prod_view(callback: CallbackQuery):
    prod_id = int(callback.data.split(":")[2])
    prod = await get_product(prod_id)
    if not prod:
        await callback.answer("Product not found", show_alert=True)
        return

    stock = prod.get("stock_count", 0)
    status_label = "Active" if prod.get("is_active") == 1 else "Inactive"

    text = (
        f"{tg_e('VIP_BADGE_NEW')} <b>Product #{prod['id']}: {prod['name']}</b>\n\n"
        f"• Description: {prod['description']}\n"
        f"• Price: <b>{prod['price']} USDT</b>\n"
        f"• In-Stock Units: <b>{stock}</b>\n"
        f"• Store Status: <b>{status_label}</b>\n"
        f"• Type: <code>{prod['item_type']}</code>"
    )

    await callback.message.edit_text(
        text,
        reply_markup=get_admin_product_detail_keyboard(prod_id, prod.get("is_active") == 1),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("admin:toggle_prod:"))
async def cb_toggle_product(callback: CallbackQuery):
    prod_id = int(callback.data.split(":")[2])
    async with get_db() as db:
        await db.execute("UPDATE products SET is_active = CASE WHEN is_active = 1 THEN 0 ELSE 1 END WHERE id = ?", (prod_id,))
        await db.commit()
    prod = await get_product(prod_id)
    await callback.answer(f"Status updated to {'Active' if prod['is_active'] == 1 else 'Inactive'}", show_alert=True)
    await cb_admin_prod_view(callback)

@router.callback_query(F.data.startswith("admin:del_prod:"))
async def cb_del_product(callback: CallbackQuery):
    prod_id = int(callback.data.split(":")[2])
    async with get_db() as db:
        await db.execute("DELETE FROM products WHERE id = ?", (prod_id,))
        await db.execute("DELETE FROM stock_items WHERE product_id = ? AND is_sold = 0", (prod_id,))
        await db.commit()
    await callback.answer("Product and stock deleted from catalog.", show_alert=True)
    items = await get_in_stock_summary()
    await callback.message.edit_text(f"{tg_e('CART')} <b>Product & Inventory Management</b>", reply_markup=get_admin_products_keyboard(items), parse_mode="HTML")

@router.callback_query(F.data.startswith("admin:stock_for:"))
async def cb_stock_for_prod(callback: CallbackQuery, state: FSMContext):
    prod_id = int(callback.data.split(":")[2])
    await state.set_state(AdminStates.waiting_stock_for_prod)
    await state.update_data(prod_id=prod_id)
    text = (
        f"{tg_e('PLUS_GREEN')} <b>Restock Product #{prod_id}</b>\n\n"
        f"Paste the digital delivery items (license keys, account logins, or links).\n"
        f"Send one item per line or separated by commas.\n\n"
        f"Each line will be automatically saved as 1 instant delivery unit."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="<", callback_data=f"admin:prod_view:{prod_id}")]])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@router.message(AdminStates.waiting_stock_for_prod)
async def process_stock_for_prod(message: Message, state: FSMContext):
    data = await state.get_data()
    prod_id = data["prod_id"]
    raw = message.text
    # Support multiple lines or commas
    items = []
    for line in raw.split("\n"):
        for sub in line.split(","):
            s = sub.strip()
            if s:
                items.append(s)

    if not items:
        await message.answer("No valid items detected. Please paste keys/accounts.")
        return

    async with get_db() as db:
        for itm in items:
            await db.execute("INSERT INTO stock_items (product_id, content) VALUES (?, ?)", (prod_id, itm))
        await db.commit()

    await state.clear()
    prod = await get_product(prod_id)
    await message.answer(
        f"{tg_e('CHECKMARK_GREEN')} Added <b>{len(items)}</b> stock items to <b>{prod['name']}</b>!\n"
        f"New Total Stock: <b>{prod['stock_count']}</b> available for automated instant delivery.",
        reply_markup=get_admin_product_detail_keyboard(prod_id, prod['is_active'] == 1),
        parse_mode="HTML"
    )

# ==================== PRODUCT CMS / EDIT SUITE ====================
@router.callback_query(F.data.startswith("admin:edit_price:"))
async def cb_edit_price(callback: CallbackQuery, state: FSMContext):
    prod_id = int(callback.data.split(":")[2])
    prod = await get_product(prod_id)
    await state.set_state(AdminStates.waiting_edit_price)
    await state.update_data(prod_id=prod_id)
    text = (
        f"{tg_e('USDT')} <b>Edit Price for {prod['name']}</b>\n\n"
        f"Current Price: <b>${prod['price']:.2f} USDT</b>\n"
        f"Send the new price in USDT (e.g. <code>12.50</code>):"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅ Cancel", callback_data=f"admin:prod_view:{prod_id}")]])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@router.message(AdminStates.waiting_edit_price)
async def process_edit_price(message: Message, state: FSMContext):
    data = await state.get_data()
    prod_id = data["prod_id"]
    try:
        new_price = float(message.text.strip().replace("$", ""))
        if new_price < 0:
            raise ValueError("Price cannot be negative")
        await update_product_field(prod_id, "price", new_price)
        await state.clear()
        prod = await get_product(prod_id)
        await message.answer(
            f"{tg_e('CHECKMARK_GREEN')} Updated price for <b>{prod['name']}</b> to <b>${new_price:.2f} USDT</b>!",
            reply_markup=get_admin_product_detail_keyboard(prod_id, prod['is_active'] == 1),
            parse_mode="HTML"
        )
    except Exception as e:
        await message.answer(f"Invalid price format. Please enter a valid number (e.g. <code>12.50</code>): {e}", parse_mode="HTML")

@router.callback_query(F.data.startswith("admin:edit_desc:"))
async def cb_edit_desc(callback: CallbackQuery, state: FSMContext):
    prod_id = int(callback.data.split(":")[2])
    prod = await get_product(prod_id)
    await state.set_state(AdminStates.waiting_edit_desc)
    await state.update_data(prod_id=prod_id)
    text = (
        f"{tg_e('DIAMOND')} <b>Edit Description for {prod['name']}</b>\n\n"
        f"Current Description:\n<i>{prod['description']}</i>\n\n"
        f"Send the new description text (HTML formatting allowed):"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅ Cancel", callback_data=f"admin:prod_view:{prod_id}")]])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@router.message(AdminStates.waiting_edit_desc)
async def process_edit_desc(message: Message, state: FSMContext):
    data = await state.get_data()
    prod_id = data["prod_id"]
    new_desc = message.text or message.caption or ""
    if not new_desc.strip():
        await message.answer("Description cannot be empty.")
        return
    await update_product_field(prod_id, "description", new_desc)
    await state.clear()
    prod = await get_product(prod_id)
    await message.answer(
        f"{tg_e('CHECKMARK_GREEN')} Description updated successfully for <b>{prod['name']}</b>!",
        reply_markup=get_admin_product_detail_keyboard(prod_id, prod['is_active'] == 1),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("admin:edit_name:"))
async def cb_edit_name(callback: CallbackQuery, state: FSMContext):
    prod_id = int(callback.data.split(":")[2])
    prod = await get_product(prod_id)
    await state.set_state(AdminStates.waiting_edit_name)
    await state.update_data(prod_id=prod_id)
    text = (
        f"{tg_e('TAG_AT')} <b>Edit Name for #{prod_id}</b>\n\n"
        f"Current Name: <b>{prod['name']}</b>\n"
        f"Send the new title/name:"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅ Cancel", callback_data=f"admin:prod_view:{prod_id}")]])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@router.message(AdminStates.waiting_edit_name)
async def process_edit_name(message: Message, state: FSMContext):
    data = await state.get_data()
    prod_id = data["prod_id"]
    new_name = message.text.strip()
    if not new_name:
        await message.answer("Product title cannot be empty.")
        return
    await update_product_field(prod_id, "name", new_name)
    await state.clear()
    prod = await get_product(prod_id)
    await message.answer(
        f"{tg_e('CHECKMARK_GREEN')} Product renamed to <b>{prod['name']}</b>!",
        reply_markup=get_admin_product_detail_keyboard(prod_id, prod['is_active'] == 1),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("admin:edit_pic:"))
async def cb_edit_pic(callback: CallbackQuery, state: FSMContext):
    prod_id = int(callback.data.split(":")[2])
    prod = await get_product(prod_id)
    await state.set_state(AdminStates.waiting_edit_pic)
    await state.update_data(prod_id=prod_id)
    text = (
        f"{tg_e('PURPLE_FLASH')} <b>Edit Picture / Banner for {prod['name']}</b>\n\n"
        f"Current Banner: <code>{prod.get('banner_image') or 'Default studio art'}</code>\n\n"
        f"📸 <b>Send a photo directly</b> to upload it as the banner, or paste an <b>image URL</b>:"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅ Cancel", callback_data=f"admin:prod_view:{prod_id}")]])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@router.message(AdminStates.waiting_edit_pic)
async def process_edit_pic(message: Message, state: FSMContext, bot: Bot):
    import os
    data = await state.get_data()
    prod_id = data["prod_id"]

    saved_path = None
    if message.photo:
        highest_res = message.photo[-1]
        os.makedirs("static/banners", exist_ok=True)
        dest = f"static/banners/{prod_id}.jpg"
        await bot.download(highest_res, destination=dest)
        saved_path = dest
    elif message.text and (message.text.startswith("http://") or message.text.startswith("https://") or message.text.startswith("static/")):
        saved_path = message.text.strip()

    if not saved_path:
        await message.answer("Please send a photo or a valid image URL.")
        return

    await update_product_field(prod_id, "banner_image", saved_path)
    await state.clear()
    prod = await get_product(prod_id)
    await message.answer(
        f"{tg_e('CHECKMARK_GREEN')} Banner updated for <b>{prod['name']}</b>!\nPath: <code>{saved_path}</code>",
        reply_markup=get_admin_product_detail_keyboard(prod_id, prod['is_active'] == 1),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("admin:clear_stock:"))
async def cb_clear_stock(callback: CallbackQuery):
    prod_id = int(callback.data.split(":")[2])
    count = await clear_product_stock(prod_id)
    await callback.answer(f"Cleared {count} unsold items from stock.", show_alert=True)
    await cb_admin_prod_view(callback)


@router.callback_query(F.data == "admin:add_stock")
async def cb_add_stock_generic(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_stock_info)
    text = (
        f"{tg_e('SAVE_FILE')} <b>Quick Stock Ingestion</b>\n\n"
        f"Send in format:\n"
        f"<code>product_id | item1, item2, item3...</code>\n\n"
        f"<b>Example:</b>\n"
        f"<code>1 | KEY-AAA-111, KEY-BBB-222, https://invite.link/333</code>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="<", callback_data="admin:products")]])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@router.message(AdminStates.waiting_stock_info)
async def process_stock_generic(message: Message, state: FSMContext):
    try:
        pid_str, contents_str = message.text.split("|", 1)
        prod_id = int(pid_str.strip())
        contents = [c.strip() for c in contents_str.split(",") if c.strip()]
        async with get_db() as db:
            for item in contents:
                await db.execute("INSERT INTO stock_items (product_id, content) VALUES (?, ?)", (prod_id, item))
            await db.commit()
        await state.clear()
        prod = await get_product(prod_id)
        await message.answer(
            f"{tg_e('CHECKMARK_GREEN')} Successfully ingested <b>{len(contents)}</b> items into <b>{prod['name']}</b>!",
            reply_markup=get_admin_product_detail_keyboard(prod_id, prod['is_active'] == 1),
            parse_mode="HTML"
        )
    except Exception as e:
        await message.answer(f"Error parsing stock: {e}")

@router.callback_query(F.data == "admin:new_prod")
async def cb_new_prod_prompt(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_new_product_info)
    text = (
        f"{tg_e('PLUS_GREEN')} <b>Create New Product</b>\n\n"
        f"Send product details in this format:\n"
        f"<code>Name | Price (USDT) | Description | Category ID | Brand Emoji</code>\n\n"
        f"<b>Example:</b>\n"
        f"<code>ExpressVPN 1 Year | 15.0 | High speed secure VPN account | 2 | EXPRESS_VPN</code>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="<", callback_data="admin:products")]])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@router.message(AdminStates.waiting_new_product_info)
async def process_new_product(message: Message, state: FSMContext):
    parts = [p.strip() for p in message.text.split("|")]
    if len(parts) < 3:
        await message.answer("Invalid format. Use: <code>Name | Price | Description | Category ID | Brand</code>", parse_mode="HTML")
        return
    name = parts[0]
    price = float(parts[1])
    desc = parts[2]
    cat_id = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 1
    brand = parts[4].upper() if len(parts) > 4 else "DIAMOND"

    async with get_db() as db:
        cur = await db.execute("""
            INSERT INTO products (category_id, name, description, price, icon_brand, item_type)
            VALUES (?, ?, ?, ?, ?, 'stock')
        """, (cat_id, name, desc, price, brand))
        prod_id = cur.lastrowid
        await db.commit()

    await state.clear()
    await message.answer(
        f"{tg_e('CHECKMARK_GREEN')} Product <b>{name}</b> (#{prod_id}) created successfully!\n"
        f"Price: {price} USDT\n"
        f"You can now add stock items to it.",
        reply_markup=get_admin_product_detail_keyboard(prod_id, True),
        parse_mode="HTML"
    )

# ==================== USER MANAGEMENT ====================
@router.callback_query(F.data == "admin:users")
async def cb_admin_users(callback: CallbackQuery):
    text = (
        f"{tg_e('ADD_PERSON')} <b>User Management & Profile Controller</b>\n\n"
        f"• Browse all registered buyer profiles.\n"
        f"• Lookup by Telegram ID or @username.\n"
        f"• Credit / deduct balances, view order history, or ban/unban."
    )
    await callback.message.edit_text(text, reply_markup=get_admin_users_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("admin:users_page:"))
async def cb_admin_users_page(callback: CallbackQuery):
    page = int(callback.data.split(":")[2])
    users, total_count = await get_all_users_paginated(page=page, per_page=8)
    text = (
        f"{tg_e('ADD_PERSON')} <b>Registered User Directory</b> ({total_count} Total)\n\n"
        f"Tap any profile to view full details, adjust wallet funds, or manage ban status:"
    )
    await callback.message.edit_text(text, reply_markup=get_admin_users_list_keyboard(users, page, total_count, per_page=8), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("admin:user_view:"))
async def cb_admin_user_view(callback: CallbackQuery):
    uid = int(callback.data.split(":")[2])
    user = await get_user(uid)
    if not user:
        await callback.answer("User profile not found in database.", show_alert=True)
        return
    stats = await get_user_stats(uid)
    is_banned = (user.get("is_banned") == 1)
    status_tag = "🚫 <b>BANNED</b>" if is_banned else "✅ <b>Active Buyer</b>"

    text = (
        f"{tg_e('VIP_YELLOW')} <b>User Profile:</b> <code>{uid}</code>\n\n"
        f"• Username: @{user['username'] if user['username'] else 'None'}\n"
        f"• First Name: <b>{user['first_name']}</b>\n"
        f"• Wallet Balance: <b>${user['balance']:.2f} USDT</b>\n"
        f"• Account Status: {status_tag}\n"
        f"• Total Orders: <b>{stats['total_orders']}</b> (Spent: ${stats['total_spent']:.2f} USDT)\n"
        f"• Referral Affiliates: <b>{stats['referrals_count']}</b>\n"
        f"• Registered On: <code>{user.get('joined_at', 'N/A')}</code>"
    )
    await callback.message.edit_text(text, reply_markup=get_admin_user_card_keyboard(uid, is_banned), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("admin:toggle_ban:"))
async def cb_toggle_ban(callback: CallbackQuery):
    uid = int(callback.data.split(":")[2])
    new_status = await toggle_user_ban(uid)
    action_str = "Banned" if new_status == 1 else "Unbanned"
    await callback.answer(f"User {uid} has been {action_str}!", show_alert=True)
    await cb_admin_user_view(callback)

@router.callback_query(F.data.startswith("admin:add_funds:"))
async def cb_add_funds(callback: CallbackQuery, state: FSMContext):
    uid = int(callback.data.split(":")[2])
    user = await get_user(uid)
    await state.set_state(AdminStates.waiting_add_funds)
    await state.update_data(target_uid=uid)
    text = (
        f"{tg_e('PLUS_GREEN')} <b>Add Funds to User:</b> <code>{uid}</code> (@{user.get('username') or 'None'})\n\n"
        f"Current Balance: <b>${user['balance']:.2f} USDT</b>\n"
        f"Send the amount in USDT to credit (e.g. <code>25.0</code>):"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅ Cancel", callback_data=f"admin:user_view:{uid}")]])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@router.message(AdminStates.waiting_add_funds)
async def process_add_funds(message: Message, state: FSMContext):
    data = await state.get_data()
    uid = data["target_uid"]
    try:
        amt = float(message.text.strip().replace("$", ""))
        if amt <= 0:
            raise ValueError("Amount must be greater than 0")
        await update_balance(uid, amt)
        u = await get_user(uid)
        await state.clear()
        await message.answer(
            f"{tg_e('CHECKMARK_GREEN')} Added <b>+${amt:.2f} USDT</b> to user <code>{uid}</code>!\n"
            f"New Balance: <b>${u['balance']:.2f} USDT</b>",
            reply_markup=get_admin_user_card_keyboard(uid, u.get("is_banned") == 1),
            parse_mode="HTML"
        )
    except Exception as e:
        await message.answer(f"Invalid amount. Please enter a valid positive number (e.g. <code>10.0</code>): {e}", parse_mode="HTML")

@router.callback_query(F.data.startswith("admin:rem_funds:"))
async def cb_rem_funds(callback: CallbackQuery, state: FSMContext):
    uid = int(callback.data.split(":")[2])
    user = await get_user(uid)
    await state.set_state(AdminStates.waiting_rem_funds)
    await state.update_data(target_uid=uid)
    text = (
        f"{tg_e('CROSS_RED')} <b>Deduct Funds from User:</b> <code>{uid}</code> (@{user.get('username') or 'None'})\n\n"
        f"Current Balance: <b>${user['balance']:.2f} USDT</b>\n"
        f"Send the amount in USDT to remove (e.g. <code>15.0</code>):"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅ Cancel", callback_data=f"admin:user_view:{uid}")]])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@router.message(AdminStates.waiting_rem_funds)
async def process_rem_funds(message: Message, state: FSMContext):
    data = await state.get_data()
    uid = data["target_uid"]
    try:
        amt = float(message.text.strip().replace("$", ""))
        if amt <= 0:
            raise ValueError("Amount must be greater than 0")
        await update_balance(uid, -amt)
        u = await get_user(uid)
        await state.clear()
        await message.answer(
            f"{tg_e('CHECKMARK_GREEN')} Deducted <b>-${amt:.2f} USDT</b> from user <code>{uid}</code>!\n"
            f"New Balance: <b>${u['balance']:.2f} USDT</b>",
            reply_markup=get_admin_user_card_keyboard(uid, u.get("is_banned") == 1),
            parse_mode="HTML"
        )
    except Exception as e:
        await message.answer(f"Invalid amount. Please enter a valid positive number to deduct: {e}", parse_mode="HTML")

@router.callback_query(F.data.startswith("admin:user_orders:"))
async def cb_user_orders(callback: CallbackQuery):
    uid = int(callback.data.split(":")[2])
    orders = await get_user_purchases_detailed(uid, limit=8)
    if not orders:
        await callback.answer("This user has not made any purchases yet.", show_alert=True)
        return

    text = f"{tg_e('CART')} <b>Purchase History for User <code>{uid}</code></b>:\n\n"
    for o in orders:
        text += (
            f"• <b>{o['product_name']}</b> · ${o['price']:.2f} USDT\n"
            f"  Delivered: <code>{o['content_delivered'][:40]}...</code>\n"
            f"  Date: <i>{o['created_at']}</i>\n\n"
        )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅ Back to User Profile", callback_data=f"admin:user_view:{uid}")]])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "admin:user_lookup")
async def cb_user_lookup_prompt(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_user_lookup)
    text = f"{tg_e('ADD_PERSON')} Send the Telegram User ID or @username you want to inspect:"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅ Back to Users", callback_data="admin:users")]])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@router.message(AdminStates.waiting_user_lookup)
async def process_user_lookup(message: Message, state: FSMContext):
    query = message.text.strip()
    users = await search_users(query)
    if not users:
        await message.answer(f"No registered users found matching <code>{query}</code>.", parse_mode="HTML")
        return

    await state.clear()
    if len(users) == 1:
        u = users[0]
        uid = u["user_id"]
        stats = await get_user_stats(uid)
        is_banned = (u.get("is_banned") == 1)
        status_tag = "🚫 <b>BANNED</b>" if is_banned else "✅ <b>Active Buyer</b>"
        text = (
            f"{tg_e('VIP_YELLOW')} <b>User Profile:</b> <code>{uid}</code>\n\n"
            f"• Username: @{u['username'] if u['username'] else 'None'}\n"
            f"• First Name: <b>{u['first_name']}</b>\n"
            f"• Wallet Balance: <b>${u['balance']:.2f} USDT</b>\n"
            f"• Account Status: {status_tag}\n"
            f"• Total Orders: <b>{stats['total_orders']}</b> (Spent: ${stats['total_spent']:.2f} USDT)\n"
            f"• Referrals: <b>{stats['referrals_count']}</b>\n"
            f"• Registered: <code>{u.get('joined_at', 'N/A')}</code>"
        )
        await message.answer(text, reply_markup=get_admin_user_card_keyboard(uid, is_banned), parse_mode="HTML")
    else:
        # Multiple users found
        rows = []
        for u in users:
            uname = f"@{u['username']}" if u.get("username") else f"ID: {u['user_id']}"
            rows.append([
                InlineKeyboardButton(
                    text=f"{uname} (${float(u['balance']):.2f})",
                    style="primary",
                    callback_data=f"admin:user_view:{u['user_id']}"
                )
            ])
        rows.append([InlineKeyboardButton(text="⬅ Back to Users", callback_data="admin:users")])
        await message.answer(f"Found <b>{len(users)}</b> matching users. Select one:", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")


@router.callback_query(F.data == "admin:balance_adjust")
async def cb_balance_adjust_prompt(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_balance_adjust)
    text = (
        f"{tg_e('USDT')} <b>Adjust User Balance</b>\n\n"
        f"Send in format:\n"
        f"<code>user_id | amount</code>\n\n"
        f"<b>Example:</b>\n"
        f"<code>7127148321 | 25.0</code> (or -10 to deduct)"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="<", callback_data="admin:users")]])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@router.message(AdminStates.waiting_balance_adjust)
async def process_balance_adjust(message: Message, state: FSMContext):
    if message.text and message.text.startswith("/"):
        await state.clear()
        return
    data = await state.get_data()
    target_uid = data.get("target_uid")
    if target_uid:
        try:
            amt = float(message.text.strip())
            await update_balance(target_uid, amt)
            u = await get_user(target_uid)
            await state.clear()
            await message.answer(
                f"{tg_e('CHECKMARK_GREEN')} Credited <b>{amt} USDT</b> to user <code>{target_uid}</code>!\n"
                f"New Balance: <b>{u['balance']} USDT</b>",
                parse_mode="HTML"
            )
            return
        except Exception as e:
            await message.answer(f"Error: {e}")
            return

    try:
        parts = message.text.split("|")
        uid = int(parts[0].strip())
        amt = float(parts[1].strip())
        await update_balance(uid, amt)
        u = await get_user(uid)
        await state.clear()
        await message.answer(
            f"{tg_e('CHECKMARK_GREEN')} Credited <b>{amt} USDT</b> to user <code>{uid}</code>!\n"
            f"New Balance: <b>{u['balance']} USDT</b>",
            parse_mode="HTML"
        )
    except Exception as e:
        await message.answer(f"Invalid format. Use: <code>user_id | amount</code>. Error: {e}", parse_mode="HTML")

# ==================== ADMINS MANAGEMENT ====================
@router.callback_query(F.data == "admin:mini_admins")
async def cb_manage_mini_admins(callback: CallbackQuery):
    role = await get_admin_role(callback.from_user.id)
    if role != "SUPER_ADMIN":
        await callback.answer("Super Admin access only", show_alert=True)
        return
    admins = await get_all_admins()
    text = (
        f"{tg_e('ADMIN_BADGE')} <b>System Administrators Directory:</b>\n\n"
        f"Tap any admin below to view details or revoke privileges:"
    )
    await callback.message.edit_text(text, reply_markup=get_admin_admins_keyboard(admins), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "admin:add_mini_admin_prompt")
async def cb_add_mini_admin_prompt(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_mini_admin_id)
    text = (
        f"{tg_e('PLUS_GREEN')} <b>Promote Mini Admin</b>\n\n"
        f"Send the Telegram User ID of the person you want to promote to Mini-Admin:\n"
        f"<i>Mini-Admins can manage stock, view orders, and inspect catalog, but cannot delete channels or modify super admin rights.</i>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="<", callback_data="admin:mini_admins")]])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@router.message(AdminStates.waiting_mini_admin_id)
async def process_add_mini_admin(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("Please send a valid numeric Telegram ID.")
        return
    uid = int(message.text.strip())
    await add_admin_user(uid, "MINI_ADMIN", message.from_user.id)
    await state.clear()
    admins = await get_all_admins()
    await message.answer(
        f"{tg_e('CHECKMARK_GREEN')} User <code>{uid}</code> is now designated as a <b>Mini-Admin</b>!",
        reply_markup=get_admin_admins_keyboard(admins),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("admin:view_admin:"))
async def cb_view_admin(callback: CallbackQuery):
    uid = int(callback.data.split(":")[2])
    role = await get_admin_role(uid)
    text = (
        f"{tg_e('ADMIN_BADGE')} <b>Administrator Profile</b>\n\n"
        f"• ID: <code>{uid}</code>\n"
        f"• Role: <b>{role}</b>"
    )
    kb_buttons = []
    if role == "MINI_ADMIN":
        kb_buttons.append([
            InlineKeyboardButton(
                text="Revoke Mini Admin",
                style="danger",
                icon_custom_emoji_id=EMOJI_IDS["CROSS_RED"],
                callback_data=f"admin:revoke_admin:{uid}"
            )
        ])
    kb_buttons.append([InlineKeyboardButton(text="< Admins List", callback_data="admin:mini_admins")])
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_buttons), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("admin:revoke_admin:"))
async def cb_revoke_admin(callback: CallbackQuery):
    uid = int(callback.data.split(":")[2])
    await remove_admin_user(uid)
    await callback.answer(f"Admin rights for {uid} revoked.", show_alert=True)
    admins = await get_all_admins()
    await callback.message.edit_reply_markup(reply_markup=get_admin_admins_keyboard(admins))

# ==================== BROADCAST TOOL ====================
@router.callback_query(F.data == "admin:broadcast")
async def cb_admin_broadcast(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_broadcast_text)
    text = (
        f"{tg_e('MAIL')} <b>Store Broadcast Announcement</b>\n\n"
        f"Send the announcement message you wish to dispatch to all store customers.\n"
        f"HTML formatting and custom tags like <code>&lt;tg-emoji emoji-id=\"...\"&gt;</code> are supported."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="<", callback_data="admin:main")]])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@router.message(AdminStates.waiting_broadcast_text)
async def process_broadcast(message: Message, state: FSMContext, bot: Bot):
    text = message.text
    async with get_db() as db:
        users = await (await db.execute("SELECT user_id FROM users")).fetchall()

    success = 0
    fail = 0
    for u in users:
        uid = u["user_id"]
        try:
            await bot.send_message(chat_id=uid, text=text, parse_mode="HTML")
            success += 1
        except Exception:
            fail += 1

    await state.clear()
    await message.answer(
        f"{tg_e('CHECKMARK_GREEN')} <b>Broadcast Dispatched</b>\n\n"
        f"• Successfully Delivered: <b>{success}</b>\n"
        f"• Failed / Blocked: <b>{fail}</b>",
        reply_markup=get_admin_main_keyboard(True),
        parse_mode="HTML"
    )

# ==================== UPSTREAM WHOLESALE APIS (VENTEBOT & ROBIXE) ====================
@router.message(Command("apis"))
async def cmd_manage_apis(message: Message):
    role = await get_admin_role(message.from_user.id)
    if not role:
        return

    from services.ventebot import ventebot_client
    from services.robixe import robixe_client

    vb_key = await ventebot_client.get_api_key()
    rb_tok = await robixe_client.get_token()

    vb_status = f"<code>{vb_key[:8]}...{vb_key[-4:]}</code> (Configured)" if vb_key else "❌ Not configured"
    rb_status = f"<code>{rb_tok[:8]}...{rb_tok[-4:]}</code> (Configured)" if rb_tok else "❌ Not configured"

    text = (
        f"{tg_e('LIGHTNING')} <b>Wholesale API Integrations</b>\n\n"
        f"<b>1. VenteBot Reseller API 1.2.0:</b>\n"
        f"• Base URL: <code>https://ventetelegrambotrailway-production.up.railway.app</code>\n"
        f"• Status: {vb_status}\n"
        f"• Test Connection: /test_ventebot\n"
        f"• Update Key: <code>/set_ventebot_key &lt;API_KEY&gt;</code>\n\n"
        f"<b>2. Robixe Coursera Wholesale Platform:</b>\n"
        f"• Base URL: <code>https://seller.robixe.com</code>\n"
        f"• Status: {rb_status}\n"
        f"• Test Connection: /test_robixe\n"
        f"• Login with URL: <code>/login_robixe &lt;telegram_url&gt;</code>\n"
        f"• Or Set Token: <code>/set_robixe_token &lt;TOKEN&gt;</code>\n\n"
        f"<i>When configured, store purchases dynamically dispatch orders to these live wholesale providers in real-time.</i>"
    )
    await message.answer(text, parse_mode="HTML")

@router.message(F.text.startswith("/set_ventebot_key"))
async def cmd_set_ventebot_key(message: Message):
    role = await get_admin_role(message.from_user.id)
    if not role:
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await message.answer("Usage: <code>/set_ventebot_key &lt;your_ventebot_api_key&gt;</code>", parse_mode="HTML")
        return
    key = parts[1].strip()
    from services.ventebot import ventebot_client
    await ventebot_client.set_api_key(key)
    res = await ventebot_client.get_me()
    if res.get("success"):
        await message.answer(
            f"{tg_e('CHECKMARK_GREEN')} <b>VenteBot API Key Connected!</b>\n\n"
            f"• Partner Account: <b>{res.get('first_name')} (@{res.get('username')})</b>\n"
            f"• Wallet Balance: <b>${res.get('wallet_balance', 0.0):.2f} USDT</b>\n"
            f"• Key Name: <code>{res.get('key_name', 'Default')}</code>",
            parse_mode="HTML"
        )
    else:
        await message.answer(
            f"{tg_e('RED_BUTTON')} Key saved, but test request returned: <code>{res.get('message', res)}</code>\n"
            f"Verify that your key is valid and not suspended on VenteBot.",
            parse_mode="HTML"
        )

@router.message(Command("test_ventebot"))
async def cmd_test_ventebot(message: Message):
    role = await get_admin_role(message.from_user.id)
    if not role:
        return
    from services.ventebot import ventebot_client
    key = await ventebot_client.get_api_key()
    if not key:
        await message.answer("❌ VenteBot API key is not set. Use <code>/set_ventebot_key &lt;key&gt;</code>", parse_mode="HTML")
        return
    res = await ventebot_client.get_me()
    if res.get("success"):
        await message.answer(
            f"{tg_e('CHECKMARK_GREEN')} <b>VenteBot API Connection LIVE:</b>\n\n"
            f"• Partner Account: <b>{res.get('first_name')} (@{res.get('username')})</b>\n"
            f"• Wallet Balance: <b>${res.get('wallet_balance', 0.0):.2f} USDT</b>\n"
            f"• Reseller ID: <code>{res.get('user_telegram_id')}</code>",
            parse_mode="HTML"
        )
    else:
        await message.answer(f"{tg_e('RED_BUTTON')} Connection failed: {res}", parse_mode="HTML")

@router.message(F.text.startswith("/login_robixe"))
async def cmd_login_robixe(message: Message):
    role = await get_admin_role(message.from_user.id)
    if not role:
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await message.answer(
            "Usage: <code>/login_robixe &lt;telegram_url_from_robixe_bot&gt;</code>\n"
            "Example: <code>/login_robixe https://seller.robixe.com/auth?token=...</code>",
            parse_mode="HTML"
        )
        return
    tg_url = parts[1].strip()
    from services.robixe import robixe_client
    token = await robixe_client.login_with_telegram_url(tg_url)
    if token:
        await message.answer(
            f"{tg_e('CHECKMARK_GREEN')} <b>Robixe Wholesale Authenticated!</b>\n\n"
            f"Bearer token generated and saved: <code>{token[:10]}...{token[-5:]}</code>\n"
            f"Coursera 12-Month links will now be generated dynamically on checkout!",
            parse_mode="HTML"
        )
    else:
        await message.answer(f"{tg_e('RED_BUTTON')} Login failed. Make sure the Telegram URL is fresh and not expired.", parse_mode="HTML")

@router.message(F.text.startswith("/set_robixe_token"))
async def cmd_set_robixe_token(message: Message):
    role = await get_admin_role(message.from_user.id)
    if not role:
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await message.answer("Usage: <code>/set_robixe_token &lt;token&gt;</code>", parse_mode="HTML")
        return
    token = parts[1].strip()
    from services.robixe import robixe_client
    await robixe_client.set_token(token)
    await message.answer(f"{tg_e('CHECKMARK_GREEN')} Robixe token updated successfully!", parse_mode="HTML")

@router.message(Command("test_robixe"))
async def cmd_test_robixe(message: Message):
    role = await get_admin_role(message.from_user.id)
    if not role:
        return
    from services.robixe import robixe_client
    token = await robixe_client.get_token()
    if not token:
        await message.answer("❌ Robixe token is not set. Use <code>/login_robixe &lt;url&gt;</code> or <code>/set_robixe_token &lt;token&gt;</code>", parse_mode="HTML")
        return
    res = await robixe_client.create_activation_link()
    if res.get("full_url"):
        await message.answer(
            f"{tg_e('CHECKMARK_GREEN')} <b>Robixe API is LIVE and Operational!</b>\n\n"
            f"Generated test Coursera activation URL:\n"
            f"<code>{res['full_url']}</code>",
            parse_mode="HTML"
        )
    else:
        await message.answer(f"{tg_e('RED_BUTTON')} Robixe test returned: <code>{res}</code>", parse_mode="HTML")

@router.message(Command("sync_ventebot"))
async def cmd_sync_ventebot(message: Message):
    role = await get_admin_role(message.from_user.id)
    if not role:
        return
    from services.ventebot import ventebot_client
    wait_msg = await message.answer(f"{tg_e('LIGHTNING')} Connecting to VenteBot and synchronizing wholesale catalog...")
    res = await ventebot_client.sync_catalog_to_database()
    if res.get("success"):
        await wait_msg.edit_text(
            f"{tg_e('CHECKMARK_GREEN')} <b>Catalog Synchronized Successfully!</b>\n\n"
            f"• <b>{res['count']} products</b> imported live from VenteBot into your store database.\n"
            f"• Prices, stock counts, and warranties are now live and synced.",
            parse_mode="HTML"
        )
    else:
        await wait_msg.edit_text(
            f"{tg_e('RED_BUTTON')} <b>Catalog Sync Failed:</b>\n"
            f"<code>{res.get('message', res)}</code>\n\n"
            f"Make sure you have connected your VenteBot API Key first:\n"
            f"<code>/set_ventebot_key &lt;API_KEY&gt;</code>",
            parse_mode="HTML"
        )

# ==================== BINANCE PAY INTEGRATION COMMANDS ====================
@router.message(Command("binance"))
async def cmd_binance_status(message: Message):
    role = await get_admin_role(message.from_user.id)
    if not role:
        return

    key, secret, pay_id = await binance_pay_service.get_credentials()
    key_disp = f"<code>{key[:8]}...{key[-4:]}</code>" if key else "❌ Not configured"
    sec_disp = f"<code>***configured***</code>" if secret else "❌ Not configured"
    pay_disp = f"<code>{pay_id}</code>" if pay_id else "❌ Not configured"

    text = (
        f"{tg_e('VIP_YELLOW')} <b>Binance Pay Gateway Configuration</b>\n\n"
        f"<b>1. Merchant OpenAPI (Auto-Checkout):</b>\n"
        f"• API Key: {key_disp}\n"
        f"• Secret Key: {sec_disp}\n"
        f"• Configure: <code>/set_binance_keys &lt;API_KEY&gt; &lt;SECRET_KEY&gt;</code>\n\n"
        f"<b>2. Direct Binance Pay ID / QR Transfer:</b>\n"
        f"• Pay ID: {pay_disp}\n"
        f"• Configure: <code>/set_binance_pay_id &lt;PAY_ID&gt;</code>\n\n"
        f"• Test Gateway: <code>/test_binance</code>\n\n"
        f"<i>Supports both automated Merchant checkout links and direct Binance Pay ID transfers.</i>"
    )
    await message.answer(text, parse_mode="HTML")

@router.message(F.text.startswith("/set_binance_keys"))
async def cmd_set_binance_keys(message: Message):
    role = await get_admin_role(message.from_user.id)
    if not role:
        return

    parts = message.text.split()
    if len(parts) < 3:
        await message.answer(
            "<b>Usage:</b>\n<code>/set_binance_keys &lt;API_KEY&gt; &lt;API_SECRET&gt;</code>",
            parse_mode="HTML"
        )
        return

    api_key = parts[1].strip()
    api_secret = parts[2].strip()
    await binance_pay_service.set_credentials(api_key=api_key, api_secret=api_secret)

    await message.answer(
        f"{tg_e('CHECKMARK_GREEN')} <b>Binance Pay API Credentials Saved!</b>\n\n"
        f"• API Key: <code>{api_key[:8]}...{api_key[-4:]}</code>\n"
        f"• Secret: <code>{'*'*12}</code>\n"
        f"• Test with: <code>/test_binance</code>",
        parse_mode="HTML"
    )

@router.message(F.text.startswith("/set_binance_pay_id"))
async def cmd_set_binance_pay_id(message: Message):
    role = await get_admin_role(message.from_user.id)
    if not role:
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await message.answer("<b>Usage:</b>\n<code>/set_binance_pay_id &lt;PAY_ID&gt;</code>", parse_mode="HTML")
        return

    pay_id = parts[1].strip()
    await binance_pay_service.set_credentials(pay_id=pay_id)
    await message.answer(
        f"{tg_e('CHECKMARK_GREEN')} <b>Binance Pay ID Updated!</b>\n"
        f"Pay ID set to: <code>{pay_id}</code>\n"
        f"Customers choosing Binance Pay can now transfer directly to this Pay ID.",
        parse_mode="HTML"
    )

@router.message(Command("test_binance"))
async def cmd_test_binance(message: Message):
    role = await get_admin_role(message.from_user.id)
    if not role:
        return

    res = await binance_pay_service.create_order(
        order_id=f"TEST_{int(message.date.timestamp())}",
        amount=1.00,
        currency="USDT",
        description="Admin Test Topup"
    )

    if res.get("type") == "api" and res.get("checkout_url"):
        await message.answer(
            f"{tg_e('CHECKMARK_GREEN')} <b>Binance Pay Merchant API Active!</b>\n\n"
            f"• Test Checkout URL: <a href='{res['checkout_url']}'>Open Checkout</a>\n"
            f"• Prepay ID: <code>{res.get('prepay_id')}</code>",
            parse_mode="HTML"
        )
    else:
        await message.answer(
            f"{tg_e('VIP_YELLOW')} <b>Binance Pay Direct Mode Active:</b>\n\n"
            f"• Pay ID: <code>{res.get('pay_id')}</code>\n"
            f"• Instructions:\n{res.get('instructions')}\n\n"
            f"<i>To enable automated checkout URLs, set your API keys with /set_binance_keys</i>",
            parse_mode="HTML"
        )



