from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config.emojis import EMOJI_IDS

def get_admin_main_keyboard(is_super_admin: bool) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text="Products & Inventory",
                style="primary",
                icon_custom_emoji_id=EMOJI_IDS["CART"],
                callback_data="admin:products"
            ),
            InlineKeyboardButton(
                text="Global Analytics",
                style="success",
                icon_custom_emoji_id=EMOJI_IDS["STATS"],
                callback_data="admin:analytics"
            )
        ],
        [
            InlineKeyboardButton(
                text="Broadcast Announcement",
                style="primary",
                icon_custom_emoji_id=EMOJI_IDS["MAIL"],
                callback_data="admin:broadcast"
            )
        ]
    ]

    if is_super_admin:
        buttons.extend([
            [
                InlineKeyboardButton(
                    text="Force-Join Channels",
                    style="danger",
                    icon_custom_emoji_id=EMOJI_IDS["LOCK"],
                    callback_data="admin:channels"
                ),
                InlineKeyboardButton(
                    text="Manage Admins",
                    style="primary",
                    icon_custom_emoji_id=EMOJI_IDS["ADMIN_BADGE"],
                    callback_data="admin:mini_admins"
                )
            ],
            [
                InlineKeyboardButton(
                    text="User Manager & Balance",
                    style="success",
                    icon_custom_emoji_id=EMOJI_IDS["USDT"],
                    callback_data="admin:users"
                )
            ]
        ])

    buttons.append([
        InlineKeyboardButton(
            text="Back to Store",
            style="primary",
            icon_custom_emoji_id=EMOJI_IDS["DIAMOND"],
            callback_data="back_to_main"
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_channels_keyboard(channels: list) -> InlineKeyboardMarkup:
    rows = []
    for ch in channels:
        rows.append([
            InlineKeyboardButton(
                text=ch["title"],
                style="primary",
                icon_custom_emoji_id=EMOJI_IDS["TELEGRAM"],
                url=ch["invite_link"]
            ),
            InlineKeyboardButton(
                text="Delete",
                style="danger",
                icon_custom_emoji_id=EMOJI_IDS["CROSS_RED"],
                callback_data=f"admin:del_channel:{ch['channel_id']}"
            )
        ])
    rows.append([
        InlineKeyboardButton(
            text="Add New Channel",
            style="success",
            icon_custom_emoji_id=EMOJI_IDS["PLUS_GREEN"],
            callback_data="admin:add_channel"
        )
    ])
    rows.append([InlineKeyboardButton(text="<", callback_data="admin:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def get_admin_products_keyboard(products: list) -> InlineKeyboardMarkup:
    rows = []
    for p in products[:12]:
        stock = p.get("stock_count", 0)
        status_text = f"{p['name']} ({stock} left)"
        rows.append([
            InlineKeyboardButton(
                text=status_text,
                style="primary" if stock > 0 else "danger",
                icon_custom_emoji_id=EMOJI_IDS.get(p.get("icon_brand", "CART"), EMOJI_IDS["CART"]),
                callback_data=f"admin:prod_view:{p['id']}"
            )
        ])
    rows.append([
        InlineKeyboardButton(
            text="Create New Product",
            style="success",
            icon_custom_emoji_id=EMOJI_IDS["PLUS_GREEN"],
            callback_data="admin:new_prod"
        ),
        InlineKeyboardButton(
            text="Quick Restock Stock",
            style="success",
            icon_custom_emoji_id=EMOJI_IDS["SAVE_FILE"],
            callback_data="admin:add_stock"
        )
    ])
    rows.append([InlineKeyboardButton(text="<", callback_data="admin:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def get_admin_product_detail_keyboard(prod_id: int, is_active: bool) -> InlineKeyboardMarkup:
    toggle_text = "Status: Active (Click to Pause)" if is_active else "Status: Paused (Click to Activate)"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Edit Price",
                    style="primary",
                    icon_custom_emoji_id=EMOJI_IDS.get("USDT"),
                    callback_data=f"admin:edit_price:{prod_id}"
                ),
                InlineKeyboardButton(
                    text="Edit Description",
                    style="primary",
                    icon_custom_emoji_id=EMOJI_IDS.get("DIAMOND"),
                    callback_data=f"admin:edit_desc:{prod_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Edit Picture",
                    style="primary",
                    icon_custom_emoji_id=EMOJI_IDS.get("PURPLE_FLASH"),
                    callback_data=f"admin:edit_pic:{prod_id}"
                ),
                InlineKeyboardButton(
                    text="Edit Name",
                    style="primary",
                    icon_custom_emoji_id=EMOJI_IDS.get("TAG_AT"),
                    callback_data=f"admin:edit_name:{prod_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Add Stock Items",
                    style="success",
                    icon_custom_emoji_id=EMOJI_IDS.get("PLUS_GREEN"),
                    callback_data=f"admin:stock_for:{prod_id}"
                ),
                InlineKeyboardButton(
                    text="Clear Stock",
                    style="danger",
                    icon_custom_emoji_id=EMOJI_IDS.get("GARBAGE"),
                    callback_data=f"admin:clear_stock:{prod_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text=toggle_text,
                    style="success" if is_active else "danger",
                    callback_data=f"admin:toggle_prod:{prod_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Delete Product",
                    style="danger",
                    icon_custom_emoji_id=EMOJI_IDS.get("CROSS_RED"),
                    callback_data=f"admin:del_prod:{prod_id}"
                )
            ],
            [InlineKeyboardButton(text="Back to Products", callback_data="admin:products")]
        ]
    )

def get_admin_users_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Browse All Registered Users",
                    style="primary",
                    icon_custom_emoji_id=EMOJI_IDS.get("ADD_PERSON"),
                    callback_data="admin:users_page:1"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Search User (ID or @username)",
                    style="primary",
                    icon_custom_emoji_id=EMOJI_IDS.get("QUESTION_ICON"),
                    callback_data="admin:user_lookup"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Direct Balance Adjustment",
                    style="success",
                    icon_custom_emoji_id=EMOJI_IDS.get("USDT"),
                    callback_data="admin:balance_adjust"
                )
            ],
            [InlineKeyboardButton(text="Admin Dashboard", callback_data="admin:main")]
        ]
    )

def get_admin_users_list_keyboard(users: list, page: int, total_count: int, per_page: int = 8) -> InlineKeyboardMarkup:
    rows = []
    for u in users:
        ban_mark = " [BANNED]" if u.get("is_banned") == 1 else ""
        uname = f"@{u['username']}" if u.get("username") else f"ID: {u['user_id']}"
        bal = f"${float(u.get('balance', 0)):.2f}"
        rows.append([
            InlineKeyboardButton(
                text=f"{uname} · {bal}{ban_mark}",
                style="danger" if u.get("is_banned") == 1 else "primary",
                callback_data=f"admin:user_view:{u['user_id']}"
            )
        ])

    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton(text="Prev", callback_data=f"admin:users_page:{page - 1}"))
    max_pages = max(1, (total_count + per_page - 1) // per_page)
    nav_row.append(InlineKeyboardButton(text=f"Page {page}/{max_pages}", callback_data=f"admin:users_page:{page}"))
    if page < max_pages:
        nav_row.append(InlineKeyboardButton(text="Next", callback_data=f"admin:users_page:{page + 1}"))

    rows.append(nav_row)
    rows.append([InlineKeyboardButton(text="Back to User Manager", callback_data="admin:users")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def get_admin_user_card_keyboard(target_uid: int, is_banned: bool) -> InlineKeyboardMarkup:
    ban_btn_text = "Unban User" if is_banned else "Ban User"
    ban_btn_style = "success" if is_banned else "danger"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Add Funds (+)",
                    style="success",
                    icon_custom_emoji_id=EMOJI_IDS.get("PLUS_GREEN"),
                    callback_data=f"admin:add_funds:{target_uid}"
                ),
                InlineKeyboardButton(
                    text="Remove Funds (-)",
                    style="danger",
                    icon_custom_emoji_id=EMOJI_IDS.get("CROSS_RED"),
                    callback_data=f"admin:rem_funds:{target_uid}"
                )
            ],
            [
                InlineKeyboardButton(
                    text=ban_btn_text,
                    style=ban_btn_style,
                    callback_data=f"admin:toggle_ban:{target_uid}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="View Order History",
                    style="primary",
                    icon_custom_emoji_id=EMOJI_IDS.get("CART"),
                    callback_data=f"admin:user_orders:{target_uid}"
                )
            ],
            [InlineKeyboardButton(text="Back to Users", callback_data="admin:users_page:1")]
        ]
    )



def get_admin_admins_keyboard(admins: list) -> InlineKeyboardMarkup:
    rows = []
    for a in admins:
        role_tag = "Super Admin" if a["role"] == "SUPER_ADMIN" else "Mini Admin"
        rows.append([
            InlineKeyboardButton(
                text=f"{a['user_id']} ({role_tag})",
                style="primary",
                icon_custom_emoji_id=EMOJI_IDS["ADMIN_BADGE"],
                callback_data=f"admin:view_admin:{a['user_id']}"
            )
        ])
    rows.append([
        InlineKeyboardButton(
            text="Add Mini-Admin",
            style="success",
            icon_custom_emoji_id=EMOJI_IDS["PLUS_GREEN"],
            callback_data="admin:add_mini_admin_prompt"
        )
    ])
    rows.append([InlineKeyboardButton(text="<", callback_data="admin:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
