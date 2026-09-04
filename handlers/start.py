from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command, CommandObject
from database.queries import get_or_create_user, get_user, get_in_stock_summary

from keyboards.inline_user import get_main_menu_keyboard
from config.settings import BOT_USERNAME, STORE_NAME
from config.emojis import tg_e

router = Router(name="start")

async def build_welcome_text(user_id: int, t) -> str:
    user = await get_user(user_id)
    balance = user.get("balance", 0.0) if user else 0.0
    lang = user.get("language", "en") if user else "en"
    username = f"@{user['username']}" if (user and user.get("username")) else f"ID: {user_id}"

    if lang == "ar":
        return (
            f"{tg_e('CROWN')} <b>{STORE_NAME.upper()}</b> {tg_e('VIP_BADGE_NEW')}\n"
            f"<i>المنصة الرقمية للبرمجيات والاشتراكات المعتمدة</i>\n\n"
            f"{tg_e('TAG_AT')} <b>الحساب:</b> {username} · {tg_e('WALLET_NEW')} <b>المحفظة:</b> <code>{balance:.2f} USDT</code>\n\n"
            f"<blockquote>{tg_e('FAST_CLOCK_24H')} <b>تسليم آلي فوري:</b> تسليم التراخيص والحسابات تلقائياً في ثوانٍ.\n"
            f"{tg_e('SHIELD_BETTER')} <b>ضمان ذهبي:</b> تغطية استبدال كاملة طوال مدة الاشتراك مع دعم فني متواصل.\n"
            f"{tg_e('LOCK_NEW')} <b>دفع تلقائي آمن:</b> شحن فوري وبدون عمولات عبر Binance Pay والعملات الرقمية.</blockquote>\n\n"
            f"{tg_e('EPIC_NEW')} <b>أقسام المنصة:</b>\n"
            f"{tg_e('DOT_BLUE')} {tg_e('CHATGPT')} <b>حلول ونماذج الذكاء الاصطناعي:</b> ChatGPT, Claude, Midjourney\n"
            f"{tg_e('DOT_GREEN')} {tg_e('GOOGLE_ONE')} <b>أنظمة التشغيل والبرمجيات:</b> Windows 11, Office 365, GitHub\n"
            f"{tg_e('DOT_PURPLE')} {tg_e('PICSART')} <b>حزم التصميم وصناعة المحتوى:</b> Canva Pro, CapCut Pro\n"
            f"{tg_e('DOT_PINK')} {tg_e('EXPRESS_VPN')} <b>خدمات الحماية والخصوصية:</b> ExpressVPN, NordVPN\n"
            f"{tg_e('DOT_YELLOW')} {tg_e('NETFLIX')} <b>المنصات التعليمية والترفيهية:</b> Coursera Plus, Netflix 4K\n\n"
            f"<i>حدد خياراً من الأسفل للمتابعة:</i>"
        )
    elif lang == "ru":
        return (
            f"{tg_e('CROWN')} <b>{STORE_NAME.upper()}</b> {tg_e('VIP_BADGE_NEW')}\n"
            f"<i>Официальный маркетплейс цифровых лицензий и софта</i>\n\n"
            f"{tg_e('TAG_AT')} <b>Профиль:</b> {username} · {tg_e('WALLET_NEW')} <b>Баланс:</b> <code>{balance:.2f} USDT</code>\n\n"
            f"<blockquote>{tg_e('FAST_CLOCK_24H')} <b>Мгновенная выдача:</b> Автоматическая отправка ключей и доступов 24/7.\n"
            f"{tg_e('SHIELD_BETTER')} <b>Гарантия качества:</b> Полное гарантийное обслуживание на весь срок лицензии.\n"
            f"{tg_e('LOCK_NEW')} <b>Авто-оплата:</b> Моментальное пополнение через Binance Pay и криптовалюту.</blockquote>\n\n"
            f"{tg_e('EPIC_NEW')} <b>Категории:</b>\n"
            f"{tg_e('DOT_BLUE')} {tg_e('CHATGPT')} <b>Искусственный интеллект:</b> ChatGPT, Claude, Midjourney\n"
            f"{tg_e('DOT_GREEN')} {tg_e('GOOGLE_ONE')} <b>Операционные системы и софт:</b> Windows 11, Office 365, GitHub\n"
            f"{tg_e('DOT_PURPLE')} {tg_e('PICSART')} <b>Дизайн и видеомонтаж:</b> Canva Pro, CapCut Pro, Adobe\n"
            f"{tg_e('DOT_PINK')} {tg_e('EXPRESS_VPN')} <b>Безопасность и приватность:</b> ExpressVPN, NordVPN\n"
            f"{tg_e('DOT_YELLOW')} {tg_e('NETFLIX')} <b>Обучение и кинотеатры:</b> Coursera Plus, Netflix 4K\n\n"
            f"<i>Выберите действие ниже для продолжения:</i>"
        )
    else:
        return (
            f"{tg_e('CROWN')} <b>{STORE_NAME.upper()}</b> {tg_e('VIP_BADGE_NEW')}\n"
            f"<i>Official Digital Goods & Software Licensing</i>\n\n"
            f"{tg_e('TAG_AT')} <b>Account:</b> {username} · {tg_e('WALLET_NEW')} <b>Wallet:</b> <code>${balance:.2f} USDT</code>\n\n"
            f"<blockquote>{tg_e('FAST_CLOCK_24H')} <b>Instant 24/7 Delivery:</b> Automated digital key and credential dispatch.\n"
            f"{tg_e('SHIELD_BETTER')} <b>Buyer Protection:</b> Full replacement warranty on all active licenses.\n"
            f"{tg_e('LOCK_NEW')} <b>Automated Billing:</b> Direct zero-fee checkout via Binance Pay & crypto.</blockquote>\n\n"
            f"{tg_e('EPIC_NEW')} <b>Available Departments:</b>\n"
            f"{tg_e('DOT_BLUE')} {tg_e('CHATGPT')} <b>Artificial Intelligence:</b> ChatGPT Plus, Claude API, Midjourney\n"
            f"{tg_e('DOT_GREEN')} {tg_e('GOOGLE_ONE')} <b>Cloud & Software:</b> Windows 11, Office 365, GitHub, JetBrains\n"
            f"{tg_e('DOT_PURPLE')} {tg_e('PICSART')} <b>Design & Creativity:</b> Canva Pro, CapCut Pro, Adobe Suite\n"
            f"{tg_e('DOT_PINK')} {tg_e('EXPRESS_VPN')} <b>Security & Privacy:</b> ExpressVPN, NordVPN, Private Proxies\n"
            f"{tg_e('DOT_YELLOW')} {tg_e('NETFLIX')} <b>Streaming & Education:</b> Netflix 4K, Coursera Plus, Spotify\n\n"
            f"<i>Select an option below to proceed:</i>"
        )







from aiogram.fsm.context import FSMContext

@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext, t):
    await state.clear()
    text = await build_welcome_text(message.from_user.id, t)
    await message.answer(f"{tg_e('CHECKMARK_GREEN')} Action cancelled.\n\n" + text, reply_markup=get_main_menu_keyboard(t), parse_mode="HTML")

@router.message(CommandStart())
async def cmd_start(message: Message, t, state: FSMContext, command: CommandObject = None):

    await state.clear()
    referrer_id = None
    if command and command.args:
        args = command.args.strip()
        if args.startswith("ref_"):
            try:
                referrer_id = int(args.replace("ref_", ""))
            except ValueError:
                pass

    await get_or_create_user(
        user_id=message.from_user.id,
        username=message.from_user.username or "",
        first_name=message.from_user.first_name or "",
        referrer_id=referrer_id
    )

    text = await build_welcome_text(message.from_user.id, t)
    await message.answer(text, reply_markup=get_main_menu_keyboard(t), parse_mode="HTML")

@router.message(Command("id"))
async def cmd_id(message: Message):
    await message.answer(f"Your Telegram ID: <code>{message.from_user.id}</code>", parse_mode="HTML")

@router.callback_query(F.data == "back_to_main")
async def cb_back_to_main(callback: CallbackQuery, t, state: FSMContext):
    await state.clear()
    text = await build_welcome_text(callback.from_user.id, t)
    kb = get_main_menu_keyboard(t)
    if callback.message.photo:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
    else:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "check_sub_status")
async def cb_check_sub(callback: CallbackQuery, t):
    text = await build_welcome_text(callback.from_user.id, t)
    await callback.message.edit_text(text, reply_markup=get_main_menu_keyboard(t), parse_mode="HTML")
    await callback.answer(t("forcesub_success"), show_alert=False)

@router.callback_query(F.data == "menu:mini_app_notice")
async def cb_mini_app_notice(callback: CallbackQuery):
    await callback.answer("🚀 Mini App is launching soon! Please use 'Shop in the bot' to browse and purchase digital products.", show_alert=True)

