from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config.settings import BOT_USERNAME, SUPER_ADMIN_IDS
from config.emojis import tg_e, EMOJI_IDS
from database.queries import (
    get_user, update_user_language, get_user_stats,
    create_support_ticket, answer_support_ticket,
    create_topup_invoice, get_user_topups, update_balance
)
from keyboards.inline_user import (
    get_verification_keyboard, get_referral_keyboard,
    get_methods_keyboard, get_wallet_keyboard,
    get_topup_history_keyboard, get_support_keyboard,
    get_language_keyboard, get_main_menu_keyboard
)
from database.db import get_db
from services.binance_pay import binance_pay_service

router = Router(name="info_menus")

class UserMenuStates(StatesGroup):
    waiting_topup_amount = State()
    waiting_deposit_receipt = State()
    waiting_support_message = State()
    admin_replying_ticket = State()


# ==================== WALLET (Screenshots 2, 3, 4) ====================
@router.callback_query(F.data.in_(["menu:wallet", "wallet:refresh"]))
async def show_wallet(callback: CallbackQuery, t, state: FSMContext):
    await state.clear()
    user = await get_user(callback.from_user.id)
    balance = user.get("balance", 0.0) if user else 0.0
    topups = await get_user_topups(callback.from_user.id)

    topups_text = "No top-ups yet."
    if topups:
        topups_text = "\n".join([f"• +{tu['amount']} USDT · {tu['status'].upper()}" for tu in topups[:3]])

    text = (
        f"{tg_e('CART_PINK')} <b>Wallet</b>\n\n"
        f"<b>Balance:</b> {balance} USDT\n\n"
        f"<blockquote>This is your shop balance - it pays for products in the shop.</blockquote>\n\n"
        f"<b>Recent top-ups</b>\n"
        f"<i>{topups_text}</i>"
    )
    await callback.message.edit_text(text, reply_markup=get_wallet_keyboard(t), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "wallet:history")
async def show_topup_history(callback: CallbackQuery, t, state: FSMContext):
    await state.clear()
    topups = await get_user_topups(callback.from_user.id)
    
    if not topups:
        history_body = "<i>No top-ups yet.</i>"
    else:
        history_body = "\n".join([f"• <b>+{tu['amount']} USDT</b> · {tu['status'].upper()} · {str(tu['created_at'])[:16]}" for tu in topups])

    text = (
        f"{tg_e('CART_PINK')} <b>Top-up history</b>\n\n"
        f"{history_body}\n\n"
        f"<blockquote>Completed top-ups and invoices still waiting for payment. Invoices that were never paid are not listed.</blockquote>"
    )
    await callback.message.edit_text(text, reply_markup=get_topup_history_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "wallet:deposit")
async def prompt_topup_amount(callback: CallbackQuery, state: FSMContext):
    await state.set_state(UserMenuStates.waiting_topup_amount)
    user = await get_user(callback.from_user.id)
    balance = user.get("balance", 0.0) if user else 0.0

    text = (
        f"{tg_e('CART_PINK')} <b>Top up balance</b>\n\n"
        f"<blockquote>How much do you want to add? Type a number in USDT (e.g. 20). Minimum 1.</blockquote>\n\n"
        f"<b>Current balance:</b> {balance} USDT\n\n"
        f"<code>/cancel</code> — stop"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="<", callback_data="menu:wallet")]])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@router.message(UserMenuStates.waiting_topup_amount)
async def process_topup_amount(message: Message, state: FSMContext):
    if message.text and message.text.startswith("/"):
        await state.clear()
        return

    try:
        amount = float(message.text.strip().replace("$", ""))
        if amount < 1.0:
            await message.answer("Minimum deposit is 1 USDT. Please enter an amount:")
            return
    except ValueError:
        await message.answer("Please type a valid numeric amount (e.g. <code>20</code>):", parse_mode="HTML")
        return

    invoice_id = await create_topup_invoice(message.from_user.id, amount)
    await state.clear()

    text = (
        f"{tg_e('USDT')} <b>Deposit Invoice #{invoice_id}</b>\n\n"
        f"Amount: <b>${amount:.2f} USDT</b>\n\n"
        f"<i>Select your preferred payment gateway:</i>"
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🟡 Binance Pay",
                    style="primary",
                    icon_custom_emoji_id=EMOJI_IDS.get("VIP_YELLOW"),
                    callback_data=f"topup:binance:{invoice_id}:{amount}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="💎 Crypto (USDT TON / TRC20)",
                    style="success",
                    icon_custom_emoji_id=EMOJI_IDS.get("USDT"),
                    callback_data=f"topup:crypto:{invoice_id}:{amount}"
                )
            ],
            [InlineKeyboardButton(text="⬅ Cancel", callback_data="menu:wallet")]
        ]
    )
    await message.answer(text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data.startswith("topup:binance:"))
async def cb_topup_binance(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    invoice_id = int(parts[2])
    amount = float(parts[3])

    res = await binance_pay_service.create_order(
        order_id=f"ORD_{invoice_id}",
        amount=amount,
        currency="USDT",
        description=f"Store Wallet Deposit #{invoice_id}"
    )

    await state.set_state(UserMenuStates.waiting_deposit_receipt)
    await state.update_data(invoice_id=invoice_id, amount=amount, method="Binance Pay")

    if res.get("type") == "api" and res.get("checkout_url"):
        text = (
            f"🟡 <b>Binance Pay Automated Checkout</b>\n\n"
            f"• Invoice ID: <code>#{invoice_id}</code>\n"
            f"• Amount Due: <b>${amount:.2f} USDT</b>\n\n"
            f"1. Tap <b>Open Binance Checkout</b> below.\n"
            f"2. Pay in Binance app.\n"
            f"3. Tap <b>🔄 Check Payment Status</b> below for <b>100% instant automated credit</b>!"
        )
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🟡 Open Binance Checkout ↗", url=res["checkout_url"])],
                [
                    InlineKeyboardButton(
                        text="🔄 Check Payment Status (Instant Auto-Credit)",
                        style="success",
                        icon_custom_emoji_id=EMOJI_IDS.get("CHECKMARK_GREEN_BTN"),
                        callback_data=f"topup:check_auto:{invoice_id}:{amount}"
                    )
                ],
                [InlineKeyboardButton(text="⬅ Cancel", callback_data="menu:wallet")]
            ]
        )
    else:
        pay_id = res.get("pay_id", "Not set")
        text = (
            f"🟡 <b>Binance Pay Direct Transfer</b>\n\n"
            f"• Binance Pay ID: <code>{pay_id}</code>\n"
            f"• Amount Due: <b>${amount:.2f} USDT</b>\n"
            f"• Payment Note / Reference: <code>ORD-{invoice_id}</code>\n\n"
            f"<b>Instructions:</b>\n"
            f"1. Open Binance App ➔ Pay ➔ Send.\n"
            f"2. Enter Pay ID: <code>{pay_id}</code>.\n"
            f"3. Send exactly <b>${amount:.2f} USDT</b>.\n"
            f"4. 📸 Send your payment screenshot here, or tap <b>Check Status</b> below."
        )
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔄 Check Payment Status",
                        style="success",
                        icon_custom_emoji_id=EMOJI_IDS.get("CHECKMARK_GREEN_BTN"),
                        callback_data=f"topup:check_auto:{invoice_id}:{amount}"
                    )
                ],
                [InlineKeyboardButton(text="⬅ Cancel", callback_data="menu:wallet")]
            ]
        )

    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("topup:check_auto:"))
async def cb_check_auto_payment(callback: CallbackQuery, bot: Bot):
    parts = callback.data.split(":")
    invoice_id = int(parts[2])
    amount = float(parts[3])
    user_id = callback.from_user.id

    # Check if invoice already completed
    async with get_db() as db:
        cur = await db.execute("SELECT status FROM topup_invoices WHERE id = ?", (invoice_id,))
        inv_row = await cur.fetchone()
        if inv_row and inv_row["status"] == "completed":
            await callback.answer("This invoice is already paid and credited!", show_alert=True)
            return

    # 1. Query Binance Pay OpenAPI
    res = await binance_pay_service.query_order(f"ORD_{invoice_id}")
    if res.get("success") and res.get("status") == "PAID":
        # 100% automated credit!
        await update_balance(user_id, amount)
        async with get_db() as db:
            await db.execute("UPDATE topup_invoices SET status = 'completed' WHERE id = ?", (invoice_id,))
            await db.commit()

        u = await get_user(user_id)
        text = (
            f"{tg_e('CHECKMARK_GREEN')} <b>Payment Verified Automatically!</b>\n\n"
            f"• Invoice: <code>#{invoice_id}</code>\n"
            f"• Amount Credited: <b>+${amount:.2f} USDT</b>\n"
            f"• Current Balance: <b>${u['balance']:.2f} USDT</b>\n\n"
            f"Your funds are available immediately for purchases! 🚀"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🛒 Start Shopping", style="success", callback_data="menu:shop")]])
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await callback.answer("Payment verified and balance added!", show_alert=True)
        return

    # If Binance Pay returned pending or keys not configured
    msg = res.get("message") or "Payment has not been detected yet on Binance."
    await callback.answer(f"Status: Pending\n{msg}\nIf you just sent the payment, please allow a few moments and tap again.", show_alert=True)


@router.callback_query(F.data.startswith("topup:crypto:"))
async def cb_topup_crypto(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    invoice_id = int(parts[2])
    amount = float(parts[3])

    import os
    deposit_addr = os.getenv("DEPOSIT_ADDRESS_TON", "UQBYFi938472910294729482749284729482948274")

    await state.set_state(UserMenuStates.waiting_deposit_receipt)
    await state.update_data(invoice_id=invoice_id, amount=amount, method="Crypto (USDT)")

    text = (
        f"{tg_e('USDT')} <b>Deposit Invoice #{invoice_id}</b>\n\n"
        f"<blockquote>Send exactly <b>{amount:.2f} USDT</b> (TON / TRC-20) to the deposit address below:</blockquote>\n\n"
        f"<code>{deposit_addr}</code>\n\n"
        f"📸 <i>After sending, please send your transaction screenshot or TxID here for verification.</i>"
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Check Status", style="success", icon_custom_emoji_id=EMOJI_IDS.get("CHECKMARK_GREEN_BTN"), callback_data="wallet:history")],
            [InlineKeyboardButton(text="⬅ Wallet", callback_data="menu:wallet")]
        ]
    )
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@router.message(UserMenuStates.waiting_deposit_receipt)
async def process_deposit_receipt(message: Message, state: FSMContext, bot: Bot):
    if message.text and message.text.startswith("/"):
        await state.clear()
        return

    data = await state.get_data()
    invoice_id = data.get("invoice_id")
    amount = data.get("amount")
    method = data.get("method", "Deposit")
    user_id = message.from_user.id
    username = message.from_user.username or "NoUser"

    await state.clear()

    await message.answer(
        f"{tg_e('CHECKMARK_GREEN')} <b>Receipt Received!</b>\n\n"
        f"Your deposit verification for <b>${amount:.2f} USDT</b> via {method} is being reviewed by admin.\n"
        f"Your balance will be credited as soon as it is confirmed.",
        parse_mode="HTML"
    )

    # Forward receipt to Super Admins with Approve/Reject buttons
    approval_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"✅ Approve (+${amount:.2f} USDT)",
                    style="success",
                    callback_data=f"admdep:appr:{invoice_id}:{user_id}:{amount}"
                ),
                InlineKeyboardButton(
                    text="❌ Reject",
                    style="danger",
                    callback_data=f"admdep:rej:{invoice_id}:{user_id}"
                )
            ]
        ]
    )

    alert_text = (
        f"🟡 <b>New {method} Deposit Pending Verification!</b>\n\n"
        f"• Invoice: <code>#{invoice_id}</code>\n"
        f"• User: <code>{user_id}</code> (@{username})\n"
        f"• Amount: <b>${amount:.2f} USDT</b>\n"
        f"• Proof below:"
    )

    for admin_id in SUPER_ADMIN_IDS:
        try:
            if message.photo:
                await bot.send_photo(admin_id, photo=message.photo[-1].file_id, caption=alert_text, reply_markup=approval_kb, parse_mode="HTML")
            else:
                await bot.send_message(admin_id, text=f"{alert_text}\n\n<code>{message.text}</code>", reply_markup=approval_kb, parse_mode="HTML")
        except Exception as e:
            logger.warning(f"Failed to notify admin {admin_id} for deposit #{invoice_id}: {e}")

@router.callback_query(F.data.startswith("admdep:appr:"))
async def cb_admin_approve_deposit(callback: CallbackQuery, bot: Bot):
    parts = callback.data.split(":")
    invoice_id = int(parts[2])
    user_id = int(parts[3])
    amount = float(parts[4])

    await update_balance(user_id, amount)
    async with get_db() as db:
        await db.execute("UPDATE topup_invoices SET status = 'completed' WHERE id = ?", (invoice_id,))
        await db.commit()

    u = await get_user(user_id)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        f"{tg_e('CHECKMARK_GREEN')} Approved deposit <b>#{invoice_id}</b>! Credited <b>+${amount:.2f} USDT</b> to user <code>{user_id}</code>.\n"
        f"New Balance: <b>${u['balance']:.2f} USDT</b>",
        parse_mode="HTML"
    )
    await callback.answer("Deposit approved & credited!")

    # Notify User
    try:
        await bot.send_message(
            user_id,
            f"{tg_e('CHECKMARK_GREEN')} <b>Deposit Confirmed!</b>\n\n"
            f"Your deposit of <b>+${amount:.2f} USDT</b> has been verified and added to your wallet!\n"
            f"Current Balance: <b>${u['balance']:.2f} USDT</b>\n\n"
            f"Thank you for shopping with us! 🚀",
            parse_mode="HTML"
        )
    except Exception:
        pass

@router.callback_query(F.data.startswith("admdep:rej:"))
async def cb_admin_reject_deposit(callback: CallbackQuery, bot: Bot):
    parts = callback.data.split(":")
    invoice_id = int(parts[2])
    user_id = int(parts[3])

    async with get_db() as db:
        await db.execute("UPDATE topup_invoices SET status = 'rejected' WHERE id = ?", (invoice_id,))
        await db.commit()

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(f"❌ Rejected deposit invoice #{invoice_id}.", parse_mode="HTML")
    await callback.answer("Deposit rejected.")

    try:
        await bot.send_message(
            user_id,
            f"{tg_e('CROSS_RED')} <b>Deposit Verification Failed</b>\n\n"
            f"Your deposit receipt for invoice #{invoice_id} could not be verified.\n"
            f"If you believe this is an error, please contact our support team.",
            parse_mode="HTML"
        )
    except Exception:
        pass


# ==================== SUPPORT TICKETS ====================
@router.callback_query(F.data == "menu:support")
async def show_support(callback: CallbackQuery, t, state: FSMContext):
    await state.clear()
    text = (
        f"{tg_e('MAIL')} <b>{t('support_desk_title')}</b>\n\n"
        f"<blockquote>{t('support_desk_quote')}</blockquote>"
    )
    await callback.message.edit_text(text, reply_markup=get_support_keyboard(t), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "support:new_ticket")
async def prompt_support_ticket(callback: CallbackQuery, t, state: FSMContext):
    await state.set_state(UserMenuStates.waiting_support_message)
    text = (
        f"{tg_e('MAIL')} <b>{t('support_prompt_title')}</b>\n\n"
        f"<blockquote>{t('support_prompt_body')}</blockquote>\n\n"
        f"<code>/cancel</code>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="<", callback_data="menu:support")]])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@router.message(UserMenuStates.waiting_support_message)
async def process_support_ticket(message: Message, t, state: FSMContext, bot: Bot):
    if message.text and message.text.startswith("/"):
        await state.clear()
        return

    ticket_text = message.text.strip()
    ticket_id = await create_support_ticket(
        user_id=message.from_user.id,
        username=message.from_user.username or "",
        message=ticket_text
    )
    await state.clear()

    await message.answer(
        f"{tg_e('CHECKMARK_GREEN')} <b>{t('support_ticket_created', ticket_id=ticket_id)}</b>",
        parse_mode="HTML"
    )


    # Notify Admins with quick Reply button
    admin_alert = (
        f"{tg_e('MAIL')} <b>New Support Ticket #{ticket_id}</b>\n"
        f"• From User: <code>{message.from_user.id}</code> (@{message.from_user.username or 'NoUser'})\n\n"
        f"<b>Message:</b>\n"
        f"{ticket_text}"
    )
    reply_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Reply to Ticket",
                    style="primary",
                    icon_custom_emoji_id=EMOJI_IDS["MAIL"],
                    callback_data=f"support_admin:reply:{ticket_id}:{message.from_user.id}"
                )
            ]
        ]
    )
    for admin_id in SUPER_ADMIN_IDS:
        try:
            await bot.send_message(chat_id=admin_id, text=admin_alert, reply_markup=reply_kb, parse_mode="HTML")
        except Exception:
            pass

@router.callback_query(F.data.startswith("support_admin:reply:"))
async def cb_admin_reply_ticket(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    ticket_id = int(parts[2])
    user_id = int(parts[3])
    await state.set_state(UserMenuStates.admin_replying_ticket)
    await state.update_data(ticket_id=ticket_id, target_user_id=user_id)
    await callback.message.answer(f"Type your reply to customer for Ticket #{ticket_id}:\n\n/cancel — stop")
    await callback.answer()

@router.message(UserMenuStates.admin_replying_ticket)
async def process_admin_reply_to_ticket(message: Message, state: FSMContext, bot: Bot):
    if message.text and message.text.startswith("/"):
        await state.clear()
        return

    data = await state.get_data()
    ticket_id = data["ticket_id"]
    target_uid = data["target_user_id"]
    reply_text = message.text.strip()

    await answer_support_ticket(ticket_id, reply_text)
    await state.clear()

    # Deliver to customer
    try:
        customer_msg = (
            f"{tg_e('MAIL')} <b>Support Response to Ticket #{ticket_id}</b>\n\n"
            f"<blockquote>{reply_text}</blockquote>\n\n"
            f"<i>If you need further help, you can submit another ticket anytime.</i>"
        )
        await bot.send_message(chat_id=target_uid, text=customer_msg, parse_mode="HTML")
        await message.answer(f"{tg_e('CHECKMARK_GREEN')} Reply sent to customer <code>{target_uid}</code>!", parse_mode="HTML")
    except Exception as e:
        await message.answer(f"Failed to deliver to customer: {e}")

# ==================== VERIFICATION & METHODS ====================
@router.callback_query(F.data == "menu:verification")
async def show_verification(callback: CallbackQuery, t, state: FSMContext):
    await state.clear()
    text = (
        f"{tg_e('CHECKMARK_GREEN')} <b>{t('verif_title')}</b>\n\n"
        f"<blockquote>{t('verif_quote_1')}</blockquote>\n\n"
        f"<b>{t('verif_steps_title')}</b>\n"
        f"{t('verif_step_1')}\n"
        f"{t('verif_step_2')}\n"
        f"{t('verif_step_3')}\n\n"
        f"<blockquote>{t('verif_quote_2')}</blockquote>"
    )
    await callback.message.edit_text(text, reply_markup=get_verification_keyboard(t), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "menu:methods")
async def show_methods(callback: CallbackQuery, t, state: FSMContext):
    await state.clear()
    text = (
        f"{tg_e('CART_PINK')} <b>{t('methods_title')}</b>\n\n"
        f"<blockquote>{t('methods_quote_1')}</blockquote>\n\n"
        f"{t('methods_p1')}\n"
        f"{t('methods_p2')}\n"
        f"{t('methods_p3')}\n\n"
        f"<blockquote>{t('methods_quote_2')}</blockquote>"
    )
    await callback.message.edit_text(text, reply_markup=get_methods_keyboard(t), parse_mode="HTML")
    await callback.answer()

# ==================== RESELLER API (Screenshot media_1788447712306.png) ====================
@router.callback_query(F.data == "menu:api")
async def show_reseller_api(callback: CallbackQuery, state: FSMContext = None):
    if state:
        await state.clear()
    from database.queries import get_user, generate_user_api_key
    from keyboards.inline_user import get_reseller_api_keyboard
    user = await get_user(callback.from_user.id)
    balance = user.get("balance", 0.0) if user else 0.0
    api_key = user.get("api_key")

    if api_key:
        key_display = f"<b>Active API Key:</b>\n<code>{api_key}</code>"
    else:
        key_display = "No active key yet."

    text = (
        f"🔌 <b>Reseller API</b>\n\n"
        f"Connect your own bot to VenteBot and resell products using your wallet balance.\n\n"
        f"Your reseller bot must send the header <code>X-Reseller-Key</code> on each request.\n\n"
        f"{tg_e('USDT')} <b>Balance:</b> ${balance:.2f}\n"
        f"Your wallet must have enough balance before your API bot can buy products.\n\n"
        f"{key_display}\n\n"
        f"<b>Documentation:</b> https://ventetelegrambotrailway-production.up.railway.app/api/swagger/"
    )

    await callback.message.edit_text(
        text,
        reply_markup=get_reseller_api_keyboard(bool(api_key)),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "api:generate_key")
async def cb_generate_api_key(callback: CallbackQuery):
    from database.queries import generate_user_api_key
    new_key = await generate_user_api_key(callback.from_user.id)
    await callback.answer("New API Key generated successfully!", show_alert=True)
    await show_reseller_api(callback, None)


# ==================== REFERRAL & LANGUAGE ====================
@router.callback_query(F.data.in_(["menu:referral", "referral:refresh"]))
async def show_referral(callback: CallbackQuery, t, state: FSMContext):
    await state.clear()
    user = await get_user(callback.from_user.id)
    stats = await get_user_stats(callback.from_user.id)
    tokens = user.get("tokens", 0) if user else 0
    ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{callback.from_user.id}"

    text = (
        f"{tg_e('ADD_PERSON')} <b>{t('ref_title')}</b>\n\n"
        f"<blockquote>{t('ref_quote_1')}</blockquote>\n\n"
        f"<b>{t('ref_steps_title')}</b>\n"
        f"{t('ref_step_1')}\n"
        f"{t('ref_step_2')}\n"
        f"{t('ref_step_3')}\n\n"
        f"<b>{t('ref_your_referrals', referrals=stats['referrals'])}</b>\n"
        f"<b>{t('ref_your_tokens', tokens=tokens)}</b>\n\n"
        f"<b>{t('ref_your_link_title')}</b>\n"
        f"<code>{ref_link}</code>\n\n"
        f"<blockquote>{t('ref_quote_2')}</blockquote>"
    )
    await callback.message.edit_text(text, reply_markup=get_referral_keyboard(t), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "menu:language")
async def show_language(callback: CallbackQuery, t, state: FSMContext):
    await state.clear()
    text = t("lang_choose")
    await callback.message.edit_text(text, reply_markup=get_language_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.message(F.text.startswith("/promo") | F.text.startswith("/coupon"))
async def cmd_redeem_promo(message: Message, t, state: FSMContext):
    await state.clear()
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await message.answer(
            f"{tg_e('STAR')} <b>Redeem Promo Code</b>\n\n"
            f"Usage: <code>/promo &lt;code&gt;</code>\n"
            f"Example: <code>/promo WELCOME10</code> or <code>/promo VENTE20</code>",
            parse_mode="HTML"
        )
        return

    code = parts[1].strip()
    from database.queries import validate_coupon, apply_coupon_use, update_balance, get_user
    coupon = await validate_coupon(code)
    if not coupon:
        await message.answer(
            f"{tg_e('CROSS_RED')} <b>Invalid or Expired Code</b>\n\n"
            f"The promo code <code>{code}</code> could not be applied or has reached its usage limit.",
            parse_mode="HTML"
        )
        return

    # Calculate promo reward (e.g. $1.50 or $3.00 deposit credit based on discount %)
    bonus_amount = round(coupon["discount_percent"] * 0.15, 2)
    user = await get_user(message.from_user.id)
    cur_bal = user.get("balance", 0.0) if user else 0.0
    await update_balance(message.from_user.id, bonus_amount)
    await apply_coupon_use(coupon["id"])
    new_bal = cur_bal + bonus_amount

    await message.answer(
        f"{tg_e('EPIC_NEW')} <b>Promo Code Redeemed!</b>\n\n"
        f"Code: <code>{coupon['code']}</code>\n"
        f"Discount / Bonus: <b>{coupon['discount_percent']}% (+${bonus_amount:.2f} USDT)</b>\n"
        f"New Balance: <b>${new_bal:.2f} USDT</b>\n\n"
        f"<i>Funds are ready to spend in the store or Mini App!</i>",
        parse_mode="HTML"
    )



@router.callback_query(F.data.startswith("set_lang:"))
async def set_language(callback: CallbackQuery, t, state: FSMContext):
    await state.clear()
    new_lang = callback.data.split(":")[1]
    await update_user_language(callback.from_user.id, new_lang)
    
    from middlewares.i18n import i18n, set_user_cached_lang
    set_user_cached_lang(callback.from_user.id, new_lang)
    
    new_t = lambda k, **kw: i18n.get(k, lang=new_lang, **kw)
    new_t.lang = new_lang

    from handlers.start import build_welcome_text
    text = await build_welcome_text(callback.from_user.id, new_t)
    kb = get_main_menu_keyboard(new_t)
    if callback.message.photo:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
    else:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer("Language updated / Язык обновлен / تم تغيير اللغة")

