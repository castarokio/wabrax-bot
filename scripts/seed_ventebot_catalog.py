import os
import sqlite3

def seed():
    db_path = "database/store.db"
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Clear old demo categories and products to perfectly align with VenteBot catalog
    c.execute("DELETE FROM categories")
    c.execute("DELETE FROM products")
    c.execute("DELETE FROM stock_items")

    # Categories
    categories = [
        (1, "Claude API", "Claude API", "Claude API", "📁", 1, "static/banners/claude_api.jpg"),
        (2, "Google Gemini", "Google Gemini", "Google Gemini", "✨", 2, "static/banners/gemini_18m.jpg"),
        (3, "ChatGPT & OpenAI", "ChatGPT & OpenAI", "ChatGPT & OpenAI", "🤖", 3, "static/banners/claude_api.jpg"),
        (4, "Coursera Wholesale", "Coursera Wholesale", "Coursera Wholesale", "🎓", 4, "static/banners/gemini_18m.jpg"),
        (5, "Streaming & VPN", "Streaming & VPN", "Streaming & VPN", "🎬", 5, "static/banners/gemini_18m.jpg")
    ]

    c.executemany("""
        INSERT INTO categories (id, name_en, name_ru, name_ar, emoji, order_priority, image_url)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, categories)

    # 1. Claude API Products (Screenshot 2 exact matches!)
    claude_desc_base = """🔑 100$ API Claude - 30 days
• Works with all apps: 9router, claude code, codex, cursor, librechat, etc.
• Full warranty (BHF).
• Instant API Key delivery with activation endpoint: https://api.mwapi.dev/
• High concurrency, 0 logging, 100% genuine Anthropic tokens."""

    products = [
        # Cat 1: Claude API
        (1, 1, "Claude 100$ Api 30 D warranty", claude_desc_base, 1.80, 30, 1420, "CLAUDE", "stock", 1, "static/banners/claude_api.jpg", 1),
        (2, 1, "API 10M Token Claude 1Day Warranty", "🔑 Claude API 10M Tokens.\n• 1 Day full replacement warranty.\n• Ultra fast inference endpoint.", 1.25, 1, 850, "CLAUDE", "stock", 1, "static/banners/claude_api.jpg", 1),
        (3, 1, "API Claude 50M Token (2Day)", "🔑 Claude API 50M Tokens.\n• 2 Days full replacement warranty.\n• Unlimited parallel threads.", 3.00, 2, 430, "CLAUDE", "stock", 1, "static/banners/claude_api.jpg", 0), # Out of stock
        (4, 1, "API 100M Token Claude 3Day", "🔑 Claude API 100M Tokens.\n• 3 Days full replacement warranty.\n• High-throughput commercial rate limits.", 4.50, 3, 620, "CLAUDE", "stock", 1, "static/banners/claude_api.jpg", 1),
        (5, 1, "500$ API CLAudio - 30 days", "🔑 500$ Tier Enterprise Claude API.\n• 30 Days warranty.\n• Dedicated proxy bypass.", 5.50, 30, 290, "CLAUDE", "stock", 1, "static/banners/claude_api.jpg", 0), # Out of stock

        # Cat 2: Google Gemini (Screenshot 1 exact match!)
        (6, 2, "Gemini 18 months", """✨ GEMINI AI PRO 18M [NW]
🤴 Gemini AI Pro 18 Months
✦ ⛔ Card-free activation
✦ ⏩ 5TB Google One cloud storage
✦ 🚀 No VPN required.
I tested it by myself so No replacement
🫶 12Hrs hold warranty.hour
In case of any replacement, please DM Support with order ID and Link,
without this replacements wont be entertained.""", 0.90, 0, 42463, "GOOGLE_ONE", "stock", 1, "static/banners/gemini_18m.jpg", 307),

        # Cat 3: ChatGPT & OpenAI
        (7, 3, "ChatGPT Business - 2 Months", """🤖 CHATGPT BUSINESS 2 MONTHS FULL ADMIN
✦ Complete admin workspace access
✦ GPT-4o & GPT-o1 unlimited reasoning
✦ Card-free automated activation link
✦ 60 Days warranty & priority replacement.""", 35.00, 60, 120, "CHATGPT", "stock", 1, "static/banners/claude_api.jpg", 5),
        (8, 3, "ChatGPT Plus 1 Month Private", "🤖 ChatGPT Plus Private Account.\n✦ Dedicated email + password\n✦ 30 Days full warranty.\n✦ Instant automated delivery.", 4.50, 30, 890, "CHATGPT", "stock", 1, "static/banners/claude_api.jpg", 45),

        # Cat 4: Coursera Wholesale
        (9, 4, "Coursera Premium 12 Months", """🎓 Coursera Plus 12-Month Wholesale Subscription
✦ Access to 7,000+ courses, certificates & degrees
✦ Automated 'Send & Forget' smart activation link
✦ Direct wholesale fulfillment via Robixe
✦ 100% full 365-day replacement guarantee.""", 2.50, 365, 1540, "VIP_BADGE_NEW", "stock", 1, "static/banners/gemini_18m.jpg", 84),

        # Cat 5: Streaming & VPN
        (10, 5, "Netflix 4K UHD 1 Month", "🎬 Netflix Premium Ultra HD (4 Screens).\n✦ Private profile + PIN\n✦ 30 Days warranty.", 3.00, 30, 410, "NETFLIX", "stock", 1, "static/banners/claude_api.jpg", 20),
        (11, 5, "Spotify Premium 3 Months", "🎵 Spotify Premium 3 Months Individual.\n✦ Works on your personal account or fresh account\n✦ 90 Days warranty.", 2.20, 90, 380, "FLAME_RED", "stock", 1, "static/banners/claude_api.jpg", 15),
        (12, 5, "ExpressVPN 1 Year", "🛡️ ExpressVPN 1-Year Premium License.\n✦ Ultra-fast servers in 105 countries\n✦ 365 Days warranty.", 4.00, 365, 520, "EXPRESS_VPN", "stock", 1, "static/banners/claude_api.jpg", 18)
    ]

    for p in products:
        (pid, cid, name, desc, price, warr, sold, icon, itype, active, img, stock_cnt) = p
        c.execute("""
            INSERT INTO products (id, category_id, name, description, price, warranty_days, sold_count, icon_brand, item_type, is_active, image_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (pid, cid, name, desc, price, warr, sold, icon, itype, active, img))

        # Seed stock items for each product
        for i in range(stock_cnt):
            if "coursera" in name.lower():
                content = f"https://client.robixe.com/act_{pid}_{i+1000}"
            elif "gemini" in name.lower():
                content = f"gemini_pro_{i+100}@gmail.com:GooglePass99! | Activation Link: https://one.google.com/promo/claim_{pid}_{i+1000}"
            elif "claude" in name.lower():
                content = f"sk-ant-api03-{os.urandom(16).hex()}-AA | Endpoint: https://api.mwapi.dev/"
            elif "chatgpt" in name.lower():
                content = f"chatgpt_user_{i+100}@openai-corp.com:SecureGpt#2026"
            else:
                content = f"license_key_{pid}_{os.urandom(8).hex()}"

            c.execute("""
                INSERT INTO stock_items (product_id, content, is_sold)
                VALUES (?, ?, 0)
            """, (pid, content))

    conn.commit()
    print("VenteBot catalog and stock seeded successfully!")
    conn.close()

if __name__ == "__main__":
    seed()
