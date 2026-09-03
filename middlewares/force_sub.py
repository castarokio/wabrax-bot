import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware, Bot
from aiogram.types import TelegramObject, User, Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.queries import get_active_channels, get_admin_role
from config.emojis import tg_e

logger = logging.getLogger(__name__)

class ForceSubMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user: User = data.get("event_from_user")
        bot: Bot = data.get("bot")

        if not user:
            return await handler(event, data)

        # Allow /start command with args (e.g. check_sub), and callback check_sub
        if isinstance(event, CallbackQuery):
            if event.data in ("check_sub_status", "change_lang:en", "change_lang:ru", "change_lang:ar"):
                return await handler(event, data)
        elif isinstance(event, Message) and event.text:
            if event.text.startswith("/start") or event.text.startswith("/admin") or event.text.startswith("/id"):
                return await handler(event, data)

        # Exempt Admins
        role = await get_admin_role(user.id)
        if role in ("SUPER_ADMIN", "MINI_ADMIN"):
            return await handler(event, data)

        channels = await get_active_channels()
        if not channels:
            return await handler(event, data)

        unjoined = []
        for ch in channels:
            ch_id = ch["channel_id"]
            try:
                member = await bot.get_chat_member(chat_id=ch_id, user_id=user.id)
                if member.status in ("left", "kicked"):
                    unjoined.append(ch)
            except Exception as e:
                logger.warning(f"Could not check membership for channel {ch_id}: {e}")
                # If bot cannot check or was removed as admin, don't permanently lock user out

        if unjoined:
            t = data.get("t", lambda k, **kw: k)
            builder = InlineKeyboardBuilder()
            for ch in unjoined:
                builder.button(text=f"{tg_e('TELEGRAM')} {ch['title']}", url=ch["invite_link"])
            builder.button(text=t("btn_check_sub"), callback_data="check_sub_status")
            builder.adjust(1)

            text = (
                f"{tg_e('LOCK')} <b>{t('forcesub_title')}</b>\n\n"
                f"{t('forcesub_desc')}\n"
            )

            if isinstance(event, CallbackQuery):
                await event.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
                await event.answer()
            elif isinstance(event, Message):
                await event.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")
            return

        return await handler(event, data)
