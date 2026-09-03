import asyncio
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
sys.stdout.reconfigure(encoding='utf-8')

from database.db import init_db
from database.queries import (
    get_or_create_user, get_admin_role, get_in_stock_summary, get_all_categories
)
from middlewares.i18n import i18n
from config.settings import SUPER_ADMIN_IDS
from aiogram import Bot

async def test_all():
    print("Testing Database Init...")
    await init_db()
    print("DB initialized successfully.")

    print("Testing Super Admin role...")
    for admin_id in SUPER_ADMIN_IDS:
        role = await get_admin_role(admin_id)
        assert role == "SUPER_ADMIN", f"Expected SUPER_ADMIN for {admin_id}, got {role}"
        print(f"Verified {admin_id} is {role}")

    print("Testing In Stock Catalog...")
    stock = await get_in_stock_summary()
    print(f"Catalog contains {len(stock)} items in stock.")
    for item in stock[:3]:
        print(f"  - {item['name']} | {item['price']} USDT | {item['stock_count']} items")

    print("Testing i18n Languages...")
    for lang in ["en", "ru", "ar"]:
        title = i18n.get("welcome_title", lang=lang, bot_name="Veriyferbot")
        print(f"[{lang}] Welcome title: {title}")

    print("Testing Bot Token connection with Telegram API...")
    from config.settings import BOT_TOKEN
    bot = Bot(token=BOT_TOKEN)
    try:
        me = await bot.get_me()
        print(f"Bot connected! Username: @{me.username} (ID: {me.id}, Name: {me.first_name})")
    finally:
        await bot.session.close()

    print("ALL TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(test_all())
