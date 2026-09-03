import asyncio
import logging
import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import MenuButtonWebApp, WebAppInfo
from aiohttp import web

from config.settings import BOT_TOKEN, MINI_APP_URL
from database.db import init_db
from middlewares.i18n import I18nMiddleware
from middlewares.force_sub import ForceSubMiddleware

from handlers import start, profile, info_menus, shop
from handlers.admin import main as admin_main
from webapp_server import create_webapp_app, set_bot_instance

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("tg_store_bot")

import socket
from aiogram.client.session.aiohttp import AiohttpSession

async def main():
    logger.info("Initializing Store Database...")
    await init_db()

    session = AiohttpSession()
    session._connector_init["family"] = socket.AF_INET

    bot = Bot(
        token=BOT_TOKEN,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    set_bot_instance(bot)
    # Start WebApp HTTP Server on port 8080 with bot reference
    app = create_webapp_app(bot=bot)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 8080)
    await site.start()
    logger.info("Mini App Backend running on http://127.0.0.1:8080")

    # Configure Telegram Menu Button for WebApp
    if MINI_APP_URL and MINI_APP_URL.startswith("https://"):
        try:
            await asyncio.wait_for(
                bot.set_chat_menu_button(
                    menu_button=MenuButtonWebApp(
                        text="Shop App",
                        web_app=WebAppInfo(url=MINI_APP_URL)
                    )
                ),
                timeout=5.0
            )
            logger.info(f"Configured Telegram Chat Menu Button to {MINI_APP_URL}")
        except Exception as e:
            logger.warning(f"Failed to set chat menu button: {e}")

    # Middlewares
    dp.update.middleware(I18nMiddleware())
    dp.update.middleware(ForceSubMiddleware())

    # Routers
    dp.include_router(admin_main.router)
    dp.include_router(start.router)
    dp.include_router(profile.router)
    dp.include_router(info_menus.router)
    dp.include_router(shop.router)

    logger.info("Starting Telegram Bot Polling (IPv4 Native)...")
    try:
        await asyncio.wait_for(bot.delete_webhook(drop_pending_updates=True), timeout=5.0)
    except Exception as e:
        logger.warning(f"delete_webhook warning: {e}")

    while True:
        try:
            await dp.start_polling(bot)
        except Exception as e:
            logger.error(f"Polling connection interrupted: {e}. Reconnecting in 3 seconds...")
            await asyncio.sleep(3)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")

