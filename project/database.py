import aiosqlite
import logging
from config import DB_PATH

logger = logging.getLogger(__name__)


async def init_db() -> None:
    logger.info("Initializing database at %s", DB_PATH)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY,
                username    TEXT,
                first_name  TEXT,
                joined_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                user_id         INTEGER NOT NULL,
                content_type    TEXT NOT NULL,
                active          INTEGER DEFAULT 1,
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, content_type)
            )
        """)
        await db.commit()
    logger.info("Database initialized successfully")


async def get_db() -> aiosqlite.Connection:
    return await aiosqlite.connect(DB_PATH)
