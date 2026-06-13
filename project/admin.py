import logging
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.filters.base import Filter
from config import ADMIN_IDS

logger = logging.getLogger(__name__)
router = Router()


class IsAdmin(Filter):
    async def __call__(self, message: Message) -> bool:
        return message.from_user.id in ADMIN_IDS


router.message.filter(IsAdmin())


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    import aiosqlite
    from config import DB_PATH

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        (user_count,) = await cursor.fetchone()

    await message.answer(f"📊 <b>إحصائيات البوت:</b>\n\nعدد المستخدمين: {user_count}", parse_mode="HTML")
