import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
ADMIN_IDS: list[int] = [
    int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()
]
CHANNEL_ID: str = os.getenv("CHANNEL_ID", "")

# تحديد مجلد المشروع الحالي الذي يحتوي على ملف الإعدادات
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH: str = os.path.join(CURRENT_DIR, "storage", "bot.db")
DATA_PATH: str = os.path.join(CURRENT_DIR, "data", "normalized")
LOGS_PATH: str = os.path.join(CURRENT_DIR, "logs")

DEFAULT_CITY: str = "الكوت"
LATITUDE: float = 32.5017
LONGITUDE: float = 45.8122
UTC_OFFSET: int = 3
DEFAULT_TIMEZONE: str = "Asia/Baghdad"

LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
