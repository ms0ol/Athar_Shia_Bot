import json
import logging
import os
import random
import aiosqlite
from typing import Optional
from config import DATA_PATH, DB_PATH

logger = logging.getLogger(__name__)

_cache: dict[str, list] = {}


def _load(filename: str) -> list:
    if filename in _cache:
        return _cache[filename]
    path = os.path.join(DATA_PATH, filename)
    if not os.path.exists(path):
        logger.warning("File not found: %s", path)
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    _cache[filename] = data
    logger.info("Loaded %d items from %s", len(data), filename)
    return data


def reload_all() -> None:
    _cache.clear()
    logger.info("Content cache cleared")


async def _mark_sent(content_id: str, category: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO sent_content(content_id, category) VALUES(?,?)",
            (content_id, category),
        )
        await db.commit()


async def _is_sent(content_id: str, category: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT 1 FROM sent_content WHERE content_id=? AND category=?",
            (content_id, category),
        )
        return await cur.fetchone() is not None


async def _reset_sent(category: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM sent_content WHERE category=?", (category,))
        await db.commit()
    logger.info("Reset sent tracking for category: %s", category)


async def _pick(items: list, category: str) -> Optional[dict]:
    if not items:
        return None

    unsent = []
    for item in items:
        if not await _is_sent(item["id"], category):
            unsent.append(item)

    if not unsent:
        await _reset_sent(category)
        unsent = items[:]

    featured = [i for i in unsent if i.get("is_featured")]
    pool = featured if featured else unsent
    pool.sort(key=lambda x: x.get("send_score", 0), reverse=True)
    top = pool[: max(1, len(pool) // 5)]
    chosen = random.choice(top)
    await _mark_sent(chosen["id"], category)
    return chosen


def _format_item(item: dict) -> str:
    category = item.get("category", "")
    text = item.get("text", "")
    author = item.get("author", "")
    source = item.get("source", "")
    title = item.get("title", "")

    if category == "hadith":
        header = "📿 <b>حديث اليوم</b>\n\n"
        footer = f"\n\n<i>— {author}</i>" if author else ""
        if source:
            footer += f"\n<i>المصدر: {source}</i>"
        return header + text + footer

    elif category == "wisdom":
        header = "💎 <b>حكمة الإمام علي عليه السلام</b>\n\n"
        footer = f"\n\n<i>— {author}</i>" if author else ""
        if source:
            footer += f"\n<i>المصدر: {source}</i>"
        return header + text + footer

    elif category == "dua":
        header = f"🤲 <b>{title or 'دعاء اليوم'}</b>\n\n"
        footer = f"\n\n<i>المصدر: {source}</i>" if source else ""
        return header + text + footer

    elif category == "munajat":
        header = f"🌙 <b>{title or 'مناجاة'}</b>\n\n"
        footer = f"\n\n<i>المصدر: {source}</i>" if source else ""
        return header + text + footer

    elif category == "ziyarat":
        header = f"🕌 <b>{title or 'زيارة'}</b>\n\n"
        footer = f"\n\n<i>المصدر: {source}</i>" if source else ""
        return header + text + footer

    elif category == "taqibat":
        prayer_names = {"fajr": "الفجر", "dhuhr": "الظهر", "maghrib": "المغرب", "isha": "العشاء"}
        prayer_ar = prayer_names.get(item.get("prayer", ""), "")
        header = f"📖 <b>تعقيب صلاة {prayer_ar}</b>\n\n"
        footer = f"\n\n<i>المصدر: {source}</i>" if source else ""
        return header + text + footer

    return text


def split_message(text: str, limit: int = 4000) -> list[str]:
    if len(text) <= limit:
        return [text]
    parts = []
    while text:
        if len(text) <= limit:
            parts.append(text)
            break
        split_at = text.rfind("\n", 0, limit)
        if split_at == -1:
            split_at = limit
        parts.append(text[:split_at])
        text = text[split_at:].lstrip()
    return parts


async def get_random_hadith() -> Optional[dict]:
    items = _load("daily_content/hadith.json")
    return await _pick(items, "hadith")


async def get_random_wisdom() -> Optional[dict]:
    items = _load("daily_content/wisdom.json")
    return await _pick(items, "wisdom")


async def get_daily_dua() -> Optional[dict]:
    items = _load("daily_content/daily_dua.json")
    return await _pick(items, "dua")


async def get_munajat() -> Optional[dict]:
    items = _load("daily_content/munajat.json")
    return await _pick(items, "munajat")


async def get_ziyarah() -> Optional[dict]:
    items = _load("daily_content/ziyarat.json")
    return await _pick(items, "ziyarat")


async def get_taqibat(prayer: str) -> Optional[dict]:
    filename = f"prayer_content/{prayer}.json"
    items = _load(filename)
    return await _pick(items, f"taqibat_{prayer}")


def format_content(item: dict) -> str:
    return _format_item(item)
