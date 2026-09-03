from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database.queries import (
    get_user, get_user_stats, toggle_user_notification, get_user_orders
)
from keyboards.inline_user import (
    get_profile_keyboard, get_stats_keyboard, get_notifications_keyboard, get_orders_keyboard
)
from config.emojis import tg_e

router = Router(name="profile")

@router.callback_query(F.data == "menu:profile")
async def show_profile(callback: CallbackQuery, t):
    user = await get_user(callback.from_user.id)
    balance = user.get("balance", 0.0) if user else 0.0
    joined = str(user.get("joined_at", "2026-05-20")).split()[0] if user else "2026-05-20"
    mode_desc = t("profile_shopping")

    text = (
        f"{tg_e('VIP_YELLOW')} <b>{t('profile_title')}</b>\n\n"
        f"<b>ID:</b> <code>{callback.from_user.id}</code>\n"
        f"<b>Balance:</b> {balance} USDT\n"
        f"<b>Joined:</b> {joined}\n"
        f"<b>Shopping in:</b> {mode_desc.split(':')[-1].strip()}"
    )

    await callback.message.edit_text(text, reply_markup=get_profile_keyboard(t), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.in_(["profile:stats", "profile:stats_refresh"]))
async def show_stats(callback: CallbackQuery, t):
    stats = await get_user_stats(callback.from_user.id)
    text = (
        f"{tg_e('CREDIT_CARD')} <b>{t('stats_title')}</b>\n\n"
        f"<b>Orders:</b> {stats['orders']}\n"
        f"<b>Items bought:</b> {stats['items']}\n"
        f"<b>Total spent:</b> {stats['spent']} USDT\n"
        f"<b>Last order:</b> {stats['last_order']}\n\n"
        f"<b>Top-ups:</b> {stats['topups']}\n"
        f"<b>Withdrawn:</b> {stats['withdrawn']} USDT\n"
        f"<b>Pending withdrawals:</b> {stats['pending']}\n\n"
        f"<b>Referrals:</b> {stats['referrals']}\n"
        f"<b>Invites sent:</b> {stats['invites']}"
    )
    await callback.message.edit_text(text, reply_markup=get_stats_keyboard(t), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "profile:notifications")
async def show_notifications(callback: CallbackQuery, t):
    user = await get_user(callback.from_user.id)
    text = (
        f"{tg_e('MAIL')} <b>{t('notif_title')}</b>\n\n"
        f"<blockquote>{t('notif_quote')}</blockquote>"
    )
    await callback.message.edit_text(text, reply_markup=get_notifications_keyboard(t, user), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("notif_toggle:"))
async def cb_toggle_notif(callback: CallbackQuery, t):
    notif_key = callback.data.split(":")[1]
    await toggle_user_notification(callback.from_user.id, notif_key)
    user = await get_user(callback.from_user.id)
    await callback.message.edit_reply_markup(reply_markup=get_notifications_keyboard(t, user))
    await callback.answer()

@router.callback_query(F.data == "profile:orders")
async def show_orders(callback: CallbackQuery, t):
    orders = await get_user_orders(callback.from_user.id)
    if not orders:
        text = (
            f"{tg_e('CART')} <b>{t('orders_title')}</b>\n\n"
            f"<i>{t('orders_empty')}</i>"
        )
    else:
        text = f"{tg_e('CART')} <b>{t('orders_title')}</b>\n\n"
        for o in orders[:5]:
            date_str = str(o["created_at"]).replace("T", " ")[:16]
            text += f"• <code>{o['product_name']}</code> · {o['price']} USDT · {date_str}\n"

    await callback.message.edit_text(text, reply_markup=get_orders_keyboard(t, orders), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("order_view:"))
async def show_order_detail(callback: CallbackQuery, t):
    order_id = int(callback.data.split(":")[1])
    orders = await get_user_orders(callback.from_user.id)
    match = next((o for o in orders if o["id"] == order_id), None)
    if not match:
        await callback.answer("Order not found", show_alert=True)
        return

    text = (
        f"{tg_e('CHECKMARK_GREEN')} <b>Order #{match['id']}</b>\n\n"
        f"<b>Product:</b> {match['product_name']}\n"
        f"<b>Price:</b> {match['price']} USDT\n"
        f"<b>Date:</b> {match['created_at']}\n\n"
        f"<b>Delivered Content:</b>\n"
        f"<code>{match['content_delivered']}</code>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="<", callback_data="profile:orders")]])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "profile:toggle_mode")
async def toggle_shopping_mode(callback: CallbackQuery, t):
    await callback.answer("Shopping mode is active: in the bot", show_alert=True)
