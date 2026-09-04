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
        f"{tg_e('CART')} <b>{t('shop_categories_title')}</b>\n\n"
        f"{t('shop_categories_subtitle')}"
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
        text = t("shop_no_products")
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t("btn_back"), callback_data="menu:shop")]])
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
    
    lang = getattr(t, "lang", "en")
    if lang == "ar":
        cat_name = products[0].get("name_ar") or products[0].get("category_name", "المنتجات")
    elif lang == "ru":
        cat_name = products[0].get("name_ru") or products[0].get("category_name", "Товары")
    else:
        cat_name = products[0].get("category_name", "Products")

    text = (
        f"{tg_e('EPIC_NEW')} <b>{cat_name}</b>\n\n"
        f"{tg_e('WALLET_NEW')} <b>{t('shop_price_range', range=price_range)}</b>\n"
        f"<i>{t('shop_choose_variant')}</i>"
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

    text = (
        f"{tg_e('VIP_BADGE_NEW')} <b>{prod['name']}</b>\n"
        f"{tg_e('WALLET_NEW')} <b>{t('shop_price_label')}: ${price_val} USDT</b>\n"
        f"{tg_e('SHIELD_BETTER')} <b>{t('shop_warranty_label')}: {t('shop_warranty_days', days=warranty_val)}</b>\n"
        f"{tg_e('FAST_CLOCK_24H')} <b>{t('shop_stock_label')}: {t('shop_stock_units', stock=stock)}</b>\n"
        f"{tg_e('TAG_AT')} <b>{t('shop_sold_label')}: {t('shop_sold_units', sold=sold_val)}</b>\n\n"
        f"<b>{t('shop_description_label')}:</b>\n"
        f"{prod['description']}"
    )

    kb = get_product_quantity_keyboard(prod_id, stock, category_id=cat_id, t=t)
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
    await process_purchase(callback.message, callback.from_user.id, prod_id, qty, is_callback=True, query=callback, t=t)

@router.callback_query(F.data.startswith("buy_custom:"))
async def prompt_custom_qty(callback: CallbackQuery, t, state: FSMContext):
    prod_id = int(callback.data.split(":")[1])
    await state.set_state(ShopStates.waiting_custom_qty)
    await state.update_data(prod_id=prod_id)
    text = (
        f"{tg_e('CART')} <b>{t('shop_custom_prompt_title')}</b>\n\n"
        f"{t('shop_custom_prompt_body')}\n\n"
        f"<code>/cancel</code>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t("btn_back"), callback_data=f"shop_prod:{prod_id}")]])
    if callback.message.photo:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
    else:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.message(ShopStates.waiting_custom_qty)
async def process_custom_qty_input(message: Message, t, state: FSMContext):
    if message.text and message.text.startswith("/"):
        await state.clear()
        return

    if not message.text.strip().isdigit():
        await message.answer(t("shop_invalid_number"))
        return

    qty = int(message.text.strip())
    if qty <= 0:
        await message.answer(t("shop_min_qty"))
        return

    data = await state.get_data()
    prod_id = data["prod_id"]
    await state.clear()
    await process_purchase(message, message.from_user.id, prod_id, qty, is_callback=False, t=t)

async def process_purchase(message_or_callback, user_id: int, prod_id: int, qty: int, is_callback: bool = False, query: CallbackQuery = None, t=None):
    success, total_or_err, items = await buy_product_batch(user_id, prod_id, qty)
    if not success:
        if is_callback and query:
            await query.answer(total_or_err, show_alert=True)
            user = await get_user(user_id)
            bal = user.get("balance", 0.0) if user else 0.0
            
            deposit_btn_txt = t("btn_deposit_usdt") if t else "Deposit USDT"
            back_btn_txt = t("btn_back") if t else "Back"
            kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=deposit_btn_txt, style="success", icon_custom_emoji_id=EMOJI_IDS["PLUS_GREEN"], callback_data="wallet:deposit")],
                    [InlineKeyboardButton(text=back_btn_txt, callback_data=f"shop_prod:{prod_id}")]
                ]
            )
            title = t("insufficient_balance_title") if t else "Insufficient Balance"
            prompt = t("insufficient_balance_prompt") if t else "Please top up your wallet below:"
            
            try:
                needed = total_or_err.split()[4]
            except Exception:
                needed = total_or_err
                
            msg_text = t("insufficient_balance_msg", needed=needed, balance=f"{bal:.2f}") if t else f"You need {needed}. Balance: {bal:.2f} USDT"
            await query.message.answer(
                f"{tg_e('CROSS_RED')} <b>{title}</b>\n\n"
                f"{msg_text}\n\n"
                f"{prompt}",
                reply_markup=kb,
                parse_mode="HTML"
            )
        else:
            await message_or_callback.answer(f"{tg_e('CROSS_RED')} {total_or_err}", parse_mode="HTML")
        return

    user = await get_user(user_id)
    new_bal = user.get("balance", 0.0)
    delivered_formatted = "\n".join([f"<code>{itm}</code>" for itm in items])

    title = t("purchase_success_title") if t else "Purchase Successful!"
    units_lbl = t("purchase_units_bought") if t else "Units Bought"
    paid_lbl = t("purchase_total_paid") if t else "Total Paid"
    rem_lbl = t("purchase_remaining_balance") if t else "Remaining Balance"
    deliv_lbl = t("purchase_delivered_items") if t else "Delivered Accounts / Credentials:"
    saved_lbl = t("purchase_saved_to_orders") if t else "Saved to your orders list."

    text = (
        f"{tg_e('CHECKMARK_GREEN')} <b>{title}</b>\n\n"
        f"<b>{units_lbl}:</b> {qty}\n"
        f"<b>{paid_lbl}:</b> {total_or_err} USDT\n"
        f"<b>{rem_lbl}:</b> {new_bal:.2f} USDT\n\n"
        f"<b>{deliv_lbl}</b>\n"
        f"{delivered_formatted}\n\n"
        f"<i>{saved_lbl}</i>"
    )

    btn_orders = t("btn_view_orders") if t else "View My Orders"
    btn_shop = t("btn_back_to_shop") if t else "Back to Shop"
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=btn_orders, callback_data="profile:orders")],
            [InlineKeyboardButton(text=btn_shop, callback_data="menu:shop")]
        ]
    )

    if is_callback and query:
        if query.message.photo:
            await query.message.delete()
            await query.message.answer(text, reply_markup=kb, parse_mode="HTML")
        else:
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

