import aiosqlite
import logging
from datetime import datetime
from config.settings import DB_PATH, SUPER_ADMIN_IDS

from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

@asynccontextmanager
async def get_db():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON;")
        await db.execute("PRAGMA journal_mode = WAL;")
        await db.execute("PRAGMA synchronous = NORMAL;")
        await db.execute("PRAGMA busy_timeout = 5000;")
        await db.execute("PRAGMA temp_store = MEMORY;")
        await db.execute("PRAGMA mmap_size = 268435456;")
        yield db


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON;")
        await db.execute("PRAGMA journal_mode = WAL;")
        await db.execute("PRAGMA synchronous = NORMAL;")

        
        # Users
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                language TEXT DEFAULT 'en',
                balance REAL DEFAULT 0.0,
                escrow_balance REAL DEFAULT 0.0,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                shopping_mode TEXT DEFAULT 'in_bot',
                stock_alerts INTEGER DEFAULT 1,
                news_offers INTEGER DEFAULT 1,
                ref_bonuses INTEGER DEFAULT 1,
                referrer_id INTEGER,
                tokens INTEGER DEFAULT 0,
                is_banned INTEGER DEFAULT 0
            )
        """)

        # Admins (Super Admin & Mini Admin)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY,
                role TEXT NOT NULL,  -- 'SUPER_ADMIN' or 'MINI_ADMIN'
                added_by INTEGER,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Mandatory Channels for Force-Subscribe
        await db.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                invite_link TEXT NOT NULL,
                is_active INTEGER DEFAULT 1
            )
        """)

        # Categories
        await db.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name_en TEXT NOT NULL,
                name_ru TEXT NOT NULL,
                name_ar TEXT NOT NULL,
                emoji TEXT DEFAULT '📦',
                order_priority INTEGER DEFAULT 0
            )
        """)

        # Products
        await db.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER,
                name TEXT NOT NULL,
                description TEXT,
                price REAL NOT NULL,
                warranty_days INTEGER DEFAULT 30,
                sold_count INTEGER DEFAULT 0,
                icon_brand TEXT DEFAULT 'DIAMOND',
                item_type TEXT DEFAULT 'stock',
                is_active INTEGER DEFAULT 1,
                FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
            )
        """)

        # Stock items for instant delivery
        await db.execute("""
            CREATE TABLE IF NOT EXISTS stock_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                is_sold INTEGER DEFAULT 0,
                sold_to_user_id INTEGER,
                sold_at TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
            )
        """)

        # Orders
        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                product_id INTEGER,
                product_name TEXT NOT NULL,
                price REAL NOT NULL,
                content_delivered TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        # Support Tickets
        await db.execute("""
            CREATE TABLE IF NOT EXISTS support_tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                message TEXT NOT NULL,
                admin_reply TEXT,
                status TEXT DEFAULT 'open', -- 'open' or 'answered'
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        # Topups & Invoices
        await db.execute("""
            CREATE TABLE IF NOT EXISTS topups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                currency TEXT DEFAULT 'USDT',
                status TEXT DEFAULT 'pending', -- 'pending' or 'completed'
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        # System Settings (Upstream API Keys & Config)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS system_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.commit()

        # Migration check for new columns
        try:
            await db.execute("ALTER TABLE products ADD COLUMN warranty_days INTEGER DEFAULT 30")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE products ADD COLUMN sold_count INTEGER DEFAULT 0")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE users ADD COLUMN api_key TEXT UNIQUE")
        except Exception:
            pass

        await db.commit()

        # Seed Super Admins
        for admin_id in SUPER_ADMIN_IDS:
            await db.execute("""
                INSERT INTO admins (user_id, role, added_by)
                VALUES (?, 'SUPER_ADMIN', 0)
                ON CONFLICT(user_id) DO UPDATE SET role='SUPER_ADMIN'
            """, (admin_id,))
        
        await db.commit()
        await seed_initial_products(db)

async def seed_initial_products(db):
    cursor = await db.execute("SELECT COUNT(*) FROM products")
    count = (await cursor.fetchone())[0]
    if count == 0:
        await db.execute("""
            INSERT INTO categories (id, name_en, name_ru, name_ar, emoji, order_priority)
            VALUES 
            (1, 'AI Tools & Models', 'ИИ сервисы и модели', 'أدوات ونماذج الذكاء الاصطناعي', '🤖', 1),
            (2, 'Developer & Design', 'Разработка и Дизайн', 'أدوات المطورين والتصميم', '🎨', 2),
            (3, 'Business & Marketing', 'Бизнес и Маркетинг', 'الأعمال والتسويق', '💼', 3)
        """)

        claude_desc = (
            "🔑 100$ API Claude - 30 days\n"
            "• Works with all apps: 9router, claude code, codex, cursor, etc.\n"
            "• Full warranty (BHF).\n"
            "Activation & API Key: https://api.mwapi.dev/\n"
            "• Detailed guide:\n"
            "https://docs.google.com/document/d/1yxSEreqNY9VaqCa5Whzv2Q_Z7-0RDKdKk0csM5l7aIw/edit?usp=sharing"
        )

        sample_products = [
            (1, "Claude 100$ Api 30 D warranty", claude_desc, 1.80, 30, 161, "CLAUDE", "stock"),
            (1, "Gemini Pro 18-month link", "Google Gemini Pro 18 Months activation link\n• Full warranty\n• Instant activation on personal account", 1.7, 30, 48, "GOOGLE_ONE", "stock"),
            (1, "ChatGPT Business - 2 Months", "ChatGPT Business subscription for 2 months\n• Personal or dedicated invite\n• High speed GPT-4o access", 35.0, 30, 29, "CHATGPT", "stock"),
            (3, "PostHog Scale — 1 Year (2x Limits)", "PostHog Scale 1 Year plan with double limits\n• Immediate enterprise activation", 29.0, 365, 14, "FLAME_RED", "stock"),
            (2, "Figma 24 Months Acc", "Figma full license account for 24 months\n• Full warranty (BHF)", 20.0, 730, 85, "PICSART", "stock"),
            (3, "Customer.io Essentials — 1 Year", "Customer.io Essentials 1 Year account\n• Full API & marketing access", 25.0, 365, 19, "FLAME_RED", "stock"),
            (2, "Factory Pro — 1 Year", "Factory Pro 1 Year plan license\n• Cloud IDE and autonomous coding", 39.0, 365, 33, "FLAME_RED", "stock"),
            (1, "Fin AI Agent + Fin Advanced — 1 Year", "Fin AI Agent 1 Year activation\n• Enterprise customer automation", 39.0, 365, 12, "FLAME_RED", "stock"),
            (2, "Framer Pro — 1 Year", "Framer Pro 1 Year account access\n• Custom domains and unlimited hosting", 29.0, 365, 52, "FLAME_RED", "stock"),
            (3, "Granola Business — 1 Year (10 Seats)", "Granola Business 10 seats 1 Year plan\n• AI meeting transcription", 19.0, 365, 41, "FLAME_RED", "stock"),
            (1, "Gumloop Pro — 1 Year (20k Credits/mo)", "Gumloop Pro 1 Year with 20k credits monthly\n• AI workflow automation", 19.0, 365, 27, "FLAME_RED", "stock"),
        ]

        for cat_id, name, desc, price, w_days, s_count, brand, itype in sample_products:
            cur = await db.execute("""
                INSERT INTO products (category_id, name, description, price, warranty_days, sold_count, icon_brand, item_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (cat_id, name, desc, price, w_days, s_count, brand, itype))
            prod_id = cur.lastrowid
            # Add initial stock items for each
            for i in range(1, 5):
                await db.execute("""
                    INSERT INTO stock_items (product_id, content)
                    VALUES (?, ?)
                """, (prod_id, f"ACCESS_KEY_{name.split()[0].upper()}_{i}: https://portal.service.com/claim?token=KEY_{i*928374}"))
        
        await db.commit()
        logger.info("Database initialized with sample store catalog and initial stock.")

