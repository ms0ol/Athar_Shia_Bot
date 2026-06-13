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
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sent_content (
                content_id  TEXT NOT NULL,
                category    TEXT NOT NULL,
                sent_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (content_id, category)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bot_state (
                key     TEXT PRIMARY KEY,
                value   TEXT
            )
        """)
        await db.commit()
    logger.info("Database initialized successfully")


async def get_state(key: str) -> str | None:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT value FROM bot_state WHERE key = ?", (key,))
        row = await cur.fetchone()
        return row[0] if row else None


async def set_state(key: str, value: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO bot_state(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        await db.commit()
