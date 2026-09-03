from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from config.settings import MINI_APP_URL
from config.emojis import EMOJI_IDS

def get_mini_app_btn(text: str) -> InlineKeyboardButton:
    if MINI_APP_URL and MINI_APP_URL.startswith("https://") and not MINI_APP_URL.startswith("https://t.me/"):
        return InlineKeyboardButton(
            text=text,
            style="primary",
            icon_custom_emoji_id=EMOJI_IDS["TELEGRAM"],
            web_app=WebAppInfo(url=MINI_APP_URL)
        )
    return InlineKeyboardButton(
        text=text,
        style="primary",
        icon_custom_emoji_id=EMOJI_IDS["TELEGRAM"],
        callback_data="menu:mini_app_notice"
    )

def get_main_menu_keyboard(t) -> InlineKeyboardMarkup:
    """
    Every button has a dedicated, vibrant style:
    - Primary (Cyan / Blue)
    - Success (Green)
    - Danger (Red)
    No empty/uncolored buttons!
    Includes separated, direct 3-language selector row at the bottom.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("btn_shop"),
                    style="success",
                    icon_custom_emoji_id=EMOJI_IDS.get("CART"),
                    callback_data="menu:shop"
                )
            ],
            [
                get_mini_app_btn(t("btn_mini_app"))
            ],
            # Financial & Account Management Row (Harmonized Green)
            [
                InlineKeyboardButton(
                    text=t("btn_wallet"),
                    style="success",
                    icon_custom_emoji_id="5278535688915012421", # wallet
                    callback_data="menu:wallet"
                ),
                InlineKeyboardButton(
                    text=t("btn_profile"),
                    style="success",
                    icon_custom_emoji_id="5350396951407895212", # settings apple
                    callback_data="menu:profile"
                )
            ],
            # Store Services & Community Row (Harmonized Blue)
            [
                InlineKeyboardButton(
                    text=t("btn_verification"),
                    style="primary",
                    icon_custom_emoji_id="5278394972901492572", # better shield
                    callback_data="menu:verification"
                ),
                InlineKeyboardButton(
                    text=t("btn_methods"),
                    style="primary",
                    icon_custom_emoji_id="5345905193005371012", # purple flash
                    callback_data="menu:methods"
                )
            ],
            # Growth & Assistance Row (Blue & Red Alert)
            [
                InlineKeyboardButton(
                    text=t("btn_referral"),
                    style="primary",
                    icon_custom_emoji_id="5431684550424011313", # vip badge
                    callback_data="menu:referral"
                ),
                InlineKeyboardButton(
                    text=t("btn_support"),
                    style="danger",
                    icon_custom_emoji_id="5188540541922480562", # question icon
                    callback_data="menu:support"
                )
            ],
            # Language Selection - Each language given its own spacious row
            [
                InlineKeyboardButton(
                    text="English",
                    style="primary",
                    icon_custom_emoji_id="5278449725144582811", # united states flag
                    callback_data="set_lang:en"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Русский",
                    style="success",
                    icon_custom_emoji_id=EMOJI_IDS.get("CHECKMARK_GREEN_BTN", "6296367896398399651"),
                    callback_data="set_lang:ru"
                )
            ],
            [
                InlineKeyboardButton(
                    text="العربية",
                    style="danger",
                    icon_custom_emoji_id="5859296708504063489", # meta verified red
                    callback_data="set_lang:ar"
                )
            ]

        ]



    )

def get_profile_keyboard(t) -> InlineKeyboardMarkup:
    """Profile screen: full color on every button."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("btn_stats"), style="primary", icon_custom_emoji_id=EMOJI_IDS["STATS"], callback_data="profile:stats")],
            [InlineKeyboardButton(text=t("btn_notifications"), style="success", icon_custom_emoji_id=EMOJI_IDS["MAIL"], callback_data="profile:notifications")],
            [InlineKeyboardButton(text=t("btn_orders"), style="primary", icon_custom_emoji_id=EMOJI_IDS["CART"], callback_data="profile:orders")],
            [InlineKeyboardButton(text=t("btn_shop_mode"), style="success", icon_custom_emoji_id=EMOJI_IDS["CALENDAR"], callback_data="profile:toggle_mode")],
            [InlineKeyboardButton(text=t("btn_language"), style="primary", icon_custom_emoji_id=EMOJI_IDS["META_VERIFIED_MULTI"], callback_data="menu:language")],
            [InlineKeyboardButton(text="Reseller API", style="success", icon_custom_emoji_id=EMOJI_IDS["LOCK_NEW"], callback_data="menu:api")],
            [InlineKeyboardButton(text="<", style="danger", callback_data="back_to_main")]
        ]
    )

def get_stats_keyboard(t) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("btn_refresh"), style="success", icon_custom_emoji_id=EMOJI_IDS["CHECKMARK_GREEN_BTN"], callback_data="profile:stats_refresh")],
            [InlineKeyboardButton(text="<", style="danger", callback_data="menu:profile")]
        ]
    )

def get_notifications_keyboard(t, user: dict) -> InlineKeyboardMarkup:
    stock_on = user.get("stock_alerts", 1) == 1
    news_on = user.get("news_offers", 1) == 1
    ref_on = user.get("ref_bonuses", 1) == 1

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("notif_stock", status="ON" if stock_on else "OFF"),
                    style="success" if stock_on else "danger",
                    icon_custom_emoji_id=EMOJI_IDS["CHECKMARK_GREEN_BTN"] if stock_on else EMOJI_IDS["RED_BUTTON"],
                    callback_data="notif_toggle:stock_alerts"
                )
            ],
            [
                InlineKeyboardButton(
                    text=t("notif_news", status="ON" if news_on else "OFF"),
                    style="success" if news_on else "danger",
                    icon_custom_emoji_id=EMOJI_IDS["CHECKMARK_GREEN_BTN"] if news_on else EMOJI_IDS["RED_BUTTON"],
                    callback_data="notif_toggle:news_offers"
                )
            ],
            [
                InlineKeyboardButton(
                    text=t("notif_ref", status="ON" if ref_on else "OFF"),
                    style="success" if ref_on else "danger",
                    icon_custom_emoji_id=EMOJI_IDS["CHECKMARK_GREEN_BTN"] if ref_on else EMOJI_IDS["RED_BUTTON"],
                    callback_data="notif_toggle:ref_bonuses"
                )
            ],
            [InlineKeyboardButton(text="<", style="primary", callback_data="menu:profile")]
        ]
    )

def get_verification_keyboard(t) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("btn_open_mini_app"),
                    style="success",
                    icon_custom_emoji_id=EMOJI_IDS["CART"],
                    callback_data="menu:mini_app_notice"
                )
            ],
            [InlineKeyboardButton(text="<", style="danger", callback_data="back_to_main")]
        ]
    )

def get_wallet_keyboard(t) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Deposit",
                    style="success",
                    icon_custom_emoji_id=EMOJI_IDS["PLUS_GREEN"],
                    callback_data="wallet:deposit"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Top-up history",
                    style="primary",
                    icon_custom_emoji_id=EMOJI_IDS["CART"],
                    callback_data="wallet:history"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Refresh",
                    style="success",
                    icon_custom_emoji_id=EMOJI_IDS["CHECKMARK_GREEN_BTN"],
                    callback_data="wallet:refresh"
                )
            ],
            [InlineKeyboardButton(text="<", style="danger", callback_data="back_to_main")]
        ]
    )

def get_topup_history_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Refresh",
                    style="success",
                    icon_custom_emoji_id=EMOJI_IDS["CHECKMARK_GREEN_BTN"],
                    callback_data="wallet:history"
                )
            ],
            [InlineKeyboardButton(text="<", style="danger", callback_data="menu:wallet")]
        ]
    )

def get_support_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Submit Support Ticket",
                    style="danger",
                    icon_custom_emoji_id=EMOJI_IDS["MAIL"],
                    callback_data="support:new_ticket"
                )
            ],
            [InlineKeyboardButton(text="<", style="primary", callback_data="back_to_main")]
        ]
    )

def get_reseller_api_keyboard(has_key: bool) -> InlineKeyboardMarkup:
    """Matches user screenshot media_1788447712306.png."""
    btn_key_text = "Generate API key" if not has_key else "Re-generate API key"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=btn_key_text,
                    style="success",
                    icon_custom_emoji_id=EMOJI_IDS["LOCK_NEW"],
                    callback_data="api:generate_key"
                )
            ],
            [
                InlineKeyboardButton(
                    text="API documentation ↗",
                    style="primary",
                    icon_custom_emoji_id=EMOJI_IDS["LINK"],
                    url="https://ventetelegrambotrailway-production.up.railway.app/api/swagger/"
                )
            ],
            [InlineKeyboardButton(text="🔙 Back", style="danger", callback_data="back_to_main")]
        ]
    )


def get_product_quantity_keyboard(product_id: int, stock_count: int, category_id: int = 1) -> InlineKeyboardMarkup:
    row1 = []
    for qty in [1, 2, 3]:
        if qty <= stock_count:
            row1.append(InlineKeyboardButton(text=str(qty), style="success", callback_data=f"buy_qty:{product_id}:{qty}"))
    
    kb = []
    if row1:
        kb.append(row1)
        kb.append([InlineKeyboardButton(text="Custom", style="primary", callback_data=f"buy_custom:{product_id}")])
    else:
        kb.append([InlineKeyboardButton(text="Out of stock", style="danger", callback_data="out_of_stock")])
    kb.append([InlineKeyboardButton(text="⬅ Back", style="danger", callback_data=f"shop_cat:{category_id}")])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def get_referral_keyboard(t) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("btn_refresh_status"),
                    style="success",
                    icon_custom_emoji_id=EMOJI_IDS["CHECKMARK_GREEN_BTN"],
                    callback_data="referral:refresh"
                )
            ],
            [InlineKeyboardButton(text="<", style="danger", callback_data="back_to_main")]
        ]
    )

def get_methods_keyboard(t) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("btn_open_mini_app"),
                    style="success",
                    icon_custom_emoji_id=EMOJI_IDS["CART"],
                    callback_data="menu:mini_app_notice"
                )
            ],
            [InlineKeyboardButton(text="<", style="danger", callback_data="back_to_main")]
        ]
    )

def get_orders_keyboard(t, orders: list) -> InlineKeyboardMarkup:
    keyboard = []
    for o in orders[:8]:
        title = f"• {o['product_name']} · {o['price']} USDT"
        keyboard.append([InlineKeyboardButton(text=title, style="primary", callback_data=f"order_view:{o['id']}")])
    keyboard.append([InlineKeyboardButton(text="<", style="danger", callback_data="menu:profile")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="English (UK/US)", style="primary", icon_custom_emoji_id=EMOJI_IDS["META_VERIFIED_BLUE"], callback_data="set_lang:en")],
            [InlineKeyboardButton(text="Русский (RU)", style="success", icon_custom_emoji_id=EMOJI_IDS["CHECKMARK_GREEN_BTN"], callback_data="set_lang:ru")],
            [InlineKeyboardButton(text="العربية (AR)", style="danger", icon_custom_emoji_id=EMOJI_IDS["META_VERIFIED_RED"], callback_data="set_lang:ar")],
            [InlineKeyboardButton(text="<", style="primary", callback_data="back_to_main")]
        ]
    )

def get_shop_categories_keyboard(categories: list, t) -> InlineKeyboardMarkup:
    keyboard = []
    styles = ["primary", "success", "danger"]
    for i, cat in enumerate(categories):
        name = cat.get("name_en")
        s = styles[i % len(styles)]
        keyboard.append([InlineKeyboardButton(
            text=name,
            style=s,
            icon_custom_emoji_id=EMOJI_IDS["CART"],
            callback_data=f"shop_cat:{cat['id']}"
        )])
    keyboard.append([InlineKeyboardButton(text="<", style="danger", callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_products_keyboard(products: list, t) -> InlineKeyboardMarkup:
    keyboard = []
    for p in products:
        stock = p.get("stock_count", 0)
        price_str = f"${p['price']:.2f}"
        if stock > 0:
            btn_text = f"{p['name']} | {price_str} | 📦 {stock}"
            btn_style = "success"
        else:
            btn_text = f"{p['name']} | {price_str} | Out of stock"
            btn_style = "danger"

        keyboard.append([InlineKeyboardButton(
            text=btn_text,
            style=btn_style,
            icon_custom_emoji_id=EMOJI_IDS.get(p.get("icon_brand", "FLAME_RED"), EMOJI_IDS["FLAME_RED"]),
            callback_data=f"shop_prod:{p['id']}"
        )])
    keyboard.append([InlineKeyboardButton(text="⬅ Back", style="danger", callback_data="menu:shop")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="English", style="primary", icon_custom_emoji_id=EMOJI_IDS["META_VERIFIED_BLUE"], callback_data="set_lang:en"),
                InlineKeyboardButton(text="Русский", style="success", icon_custom_emoji_id=EMOJI_IDS["CHECKMARK_GREEN_BTN"], callback_data="set_lang:ru"),
                InlineKeyboardButton(text="العربية", style="danger", icon_custom_emoji_id=EMOJI_IDS["META_VERIFIED_RED"], callback_data="set_lang:ar"),
            ],
            [InlineKeyboardButton(text="<", style="danger", callback_data="back_to_main")]
        ]
    )

