import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
ADMIN_IDS: list[int] = [
    int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()
]

DB_PATH: str = os.path.join(os.path.dirname(__file__), "storage", "bot.db")
DATA_PATH: str = os.path.join(os.path.dirname(__file__), "..", "data", "normalized")
LOGS_PATH: str = os.path.join(os.path.dirname(__file__), "logs")

DEFAULT_CITY: str = "Al Kut"
DEFAULT_COUNTRY: str = "Iraq"
DEFAULT_TIMEZONE: str = "Asia/Baghdad"

LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
