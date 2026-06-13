import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
ADMIN_IDS: list[int] = [
    int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()
]
CHANNEL_ID: str = os.getenv("CHANNEL_ID", "")

DB_PATH: str = os.path.join(os.path.dirname(__file__), "storage", "bot.db")
DATA_PATH: str = os.path.join(os.path.dirname(__file__), "..", "data", "normalized")
LOGS_PATH: str = os.path.join(os.path.dirname(__file__), "logs")

DEFAULT_CITY: str = "الكوت"
LATITUDE: float = 32.5017
LONGITUDE: float = 45.8122
UTC_OFFSET: int = 3
DEFAULT_TIMEZONE: str = "Asia/Baghdad"

LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
