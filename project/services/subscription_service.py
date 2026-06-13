import aiosqlite
import logging
from config import DB_PATH

logger = logging.getLogger(__name__)

CONTENT_TYPES = {
    "hadith": "📿 حديث اليوم",
    "wisdom": "💎 حكمة يومية",
    "daily_dua": "🤲 دعاء يومي",
    "taqibat": "📖 تعقيبات الصلاة",
}


async def subscribe(user_id: int, content_type: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO subscriptions(user_id, content_type, active)
            VALUES(?, ?, 1)
            ON CONFLICT(user_id, content_type) DO UPDATE SET active=1
            """,
            (user_id, content_type),
        )
        await db.commit()
    logger.info("User %d subscribed to %s", user_id, content_type)
    return True


async def unsubscribe(user_id: int, content_type: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE subscriptions SET active=0 WHERE user_id=? AND content_type=?",
            (user_id, content_type),
        )
        await db.commit()
    logger.info("User %d unsubscribed from %s", user_id, content_type)
    return True


async def is_subscribed(user_id: int, content_type: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT active FROM subscriptions WHERE user_id=? AND content_type=?",
            (user_id, content_type),
        )
        row = await cur.fetchone()
        return bool(row and row[0] == 1)


async def get_user_subscriptions(user_id: int) -> list[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT content_type FROM subscriptions WHERE user_id=? AND active=1",
            (user_id,),
        )
        rows = await cur.fetchall()
        return [r[0] for r in rows]


async def get_subscribers(content_type: str) -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT user_id FROM subscriptions WHERE content_type=? AND active=1",
            (content_type,),
        )
        rows = await cur.fetchall()
        return [r[0] for r in rows]
