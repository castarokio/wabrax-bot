import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "8840887093:AAG83nK1Jb8SaHSpWcv3d47Cu4GKrOVteZM")
SUPER_ADMIN_IDS = [int(x.strip()) for x in os.getenv("SUPER_ADMIN_IDS", "7127148321").split(",") if x.strip()]
BOT_USERNAME = os.getenv("BOT_USERNAME", "wabraxstorebot")
STORE_NAME = os.getenv("STORE_NAME", "Wabrax Store")
MINI_APP_URL = os.getenv("MINI_APP_URL", "https://t.me/wabraxstorebot/app")
SUPPORT_URL = os.getenv("SUPPORT_URL", "https://t.me/supportelegram")
ESCROW_RULES_URL = os.getenv("ESCROW_RULES_URL", "https://t.me/rules")
METHODS_URL = os.getenv("METHODS_URL", "https://t.me/wabraxstore")
VERIFICATION_URL = os.getenv("VERIFICATION_URL", "https://t.me/wabraxverify")
CRYPTOBOT_TOKEN = os.getenv("CRYPTOBOT_TOKEN", "")


DB_PATH = BASE_DIR / "database" / "store.db"
LOCALES_DIR = BASE_DIR / "config" / "locales"
DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES = ["en", "ru", "ar"]
