import json
import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User
from config.settings import LOCALES_DIR, DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES
from database.queries import get_or_create_user

logger = logging.getLogger(__name__)

class Localization:
    def __init__(self):
        self.translations = {}
        self.load_translations()

    def load_translations(self):
        for lang in SUPPORTED_LANGUAGES:
            path = LOCALES_DIR / f"{lang}.json"
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    self.translations[lang] = json.load(f)
            else:
                self.translations[lang] = {}

    def get(self, key: str, lang: str = DEFAULT_LANGUAGE, **kwargs) -> str:
        lang = lang if lang in self.translations else DEFAULT_LANGUAGE
        text = self.translations.get(lang, {}).get(key) or self.translations.get(DEFAULT_LANGUAGE, {}).get(key, key)
        if kwargs:
            try:
                return text.format(**kwargs)
            except Exception:
                return text
        return text

i18n = Localization()

import time

_USER_CACHE: Dict[int, tuple] = {} # user_id: (u_data, user_lang, expire_timestamp)

def invalidate_user_cache(user_id: int):
    _USER_CACHE.pop(user_id, None)

def set_user_cached_lang(user_id: int, lang: str):
    if user_id in _USER_CACHE:
        u_data, _, exp = _USER_CACHE[user_id]
        if isinstance(u_data, dict):
            u_data["language"] = lang
        _USER_CACHE[user_id] = (u_data, lang, exp)

class I18nMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user: User = data.get("event_from_user")
        user_lang = DEFAULT_LANGUAGE

        if user:
            now = time.monotonic()
            cached = _USER_CACHE.get(user.id)
            if cached and now < cached[2]:
                u_data, user_lang = cached[0], cached[1]
            else:
                u_data = await get_or_create_user(user.id, user.username or "", user.first_name or "")
                user_lang = u_data.get("language") or DEFAULT_LANGUAGE
                _USER_CACHE[user.id] = (u_data, user_lang, now + 120.0)
            data["user_data"] = u_data

        data["lang"] = user_lang
        def t_func(key: str, **kw):
            return i18n.get(key, lang=user_lang, **kw)
        t_func.lang = user_lang
        data["t"] = t_func
        
        return await handler(event, data)


