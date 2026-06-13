import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
ADMIN_IDS: list[int] = [
    int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()
]
CHANNEL_ID: str = os.getenv("CHANNEL_ID", "")

# Absolute path of the directory containing this file (project/)
_PROJECT_DIR: str = os.path.dirname(os.path.abspath(__file__))
# Absolute path of the repository root (one level above project/)
_REPO_ROOT: str = os.path.dirname(_PROJECT_DIR)

DB_PATH: str   = os.path.join(_PROJECT_DIR, "storage", "bot.db")
DATA_PATH: str = os.path.join(_REPO_ROOT,   "data", "normalized")
LOGS_PATH: str = os.path.join(_PROJECT_DIR, "logs")

DEFAULT_CITY: str = "الكوت"
LATITUDE: float = 32.5017
LONGITUDE: float = 45.8122
UTC_OFFSET: int = 3
DEFAULT_TIMEZONE: str = "Asia/Baghdad"

LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
