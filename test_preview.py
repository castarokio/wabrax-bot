import asyncio, sys
sys.stdout.reconfigure(encoding='utf-8')
from aiogram import Bot
from config.settings import BOT_TOKEN
from keyboards.inline_user import get_main_menu_keyboard, get_wallet_keyboard, get_product_quantity_keyboard
from handlers.start import build_welcome_text
from middlewares.i18n import i18n
from database.queries import get_product
from database.db import get_db
from config.emojis import tg_e

async def main():
    bot = Bot(token=BOT_TOKEN)
    t = lambda k, **kw: i18n.get(k, 'en', **kw)
    
    # 1. Main Menu
    menu_text = await build_welcome_text(7127148321, t)
    menu_kb = get_main_menu_keyboard(t)
    m1 = await bot.send_message(chat_id=7127148321, text=menu_text, reply_markup=menu_kb, parse_mode='HTML')
    print('Delivered updated Main Menu! msg_id:', m1.message_id)

    # 2. Product Detail
    async with get_db() as db:
        cur = await db.execute("SELECT id FROM products WHERE name LIKE ?", ("%Claude%",))
        row = await cur.fetchone()
        prod = await get_product(row['id'])

    brand_icon = tg_e(prod.get('icon_brand', 'CLAUDE'))
    prod_text = (
        f"{brand_icon} <b>{prod['name']}</b>\n"
        f"{tg_e('USDT')} <b>Price:</b> ${prod['price']:.2f}\n"
        f"{tg_e('ADMIN_BADGE')} <b>Warranty:</b> {prod.get('warranty_days', 30)} days\n"
        f"{tg_e('SAVE_FILE')} <b>Stock:</b> {prod.get('stock_count', 0)} accounts\n"
        f"{tg_e('STATS')} <b>Sold:</b> {prod.get('sold_count', 0)} accounts\n\n"
        f"<b>” Description:</b>\n"
        f"{prod['description']}"
    )
    prod_kb = get_product_quantity_keyboard(prod['id'], prod['stock_count'])
    m2 = await bot.send_message(chat_id=7127148321, text=prod_text, reply_markup=prod_kb, parse_mode='HTML')
    print('Delivered Claude Product Detail! msg_id:', m2.message_id)

    await bot.session.close()

if __name__ == '__main__':
    asyncio.run(main())
