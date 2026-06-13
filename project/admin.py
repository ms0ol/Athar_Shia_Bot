import logging
import aiosqlite
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.filters.base import Filter

from config import ADMIN_IDS, DB_PATH
from services import content_service, prayer_service

logger = logging.getLogger(__name__)
router = Router()


class IsAdmin(Filter):
    async def __call__(self, message: Message) -> bool:
        return message.from_user.id in ADMIN_IDS


router.message.filter(IsAdmin())


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) FROM users")
        (user_count,) = await cur.fetchone()
        cur = await db.execute("SELECT COUNT(*) FROM subscriptions WHERE active=1")
        (sub_count,) = await cur.fetchone()
        cur = await db.execute("SELECT COUNT(*) FROM sent_content")
        (sent_count,) = await cur.fetchone()

    await message.answer(
        f"📊 <b>إحصائيات البوت:</b>\n\n"
        f"👤 المستخدمون: {user_count}\n"
        f"🔔 الاشتراكات النشطة: {sub_count}\n"
        f"📤 المحتوى المُرسل: {sent_count}",
        parse_mode="HTML",
    )


@router.message(Command("test_hadith"))
async def cmd_test_hadith(message: Message) -> None:
    item = await content_service.get_random_hadith()
    if item:
        text = content_service.format_content(item)
        for part in content_service.split_message(text):
            await message.answer(part, parse_mode="HTML")
    else:
        await message.answer("⚠️ لا يوجد حديث متاح.")


@router.message(Command("test_wisdom"))
async def cmd_test_wisdom(message: Message) -> None:
    item = await content_service.get_random_wisdom()
    if item:
        text = content_service.format_content(item)
        for part in content_service.split_message(text):
            await message.answer(part, parse_mode="HTML")
    else:
        await message.answer("⚠️ لا يوجد حكمة متاحة.")


@router.message(Command("test_prayer"))
async def cmd_test_prayer(message: Message) -> None:
    times = prayer_service.get_prayer_times()
    next_p = prayer_service.get_next_prayer(times)
    text = prayer_service.format_prayer_times(times)
    if next_p:
        name_ar = prayer_service.PRAYER_NAMES_AR.get(next_p[0], next_p[0])
        cd = prayer_service.countdown(next_p[1])
        text += f"\n\n⏳ <b>الصلاة القادمة:</b> {name_ar}\n🕐 بعد: {cd}"
    await message.answer(text, parse_mode="HTML")


@router.message(Command("test_pinned"))
async def cmd_test_pinned(message: Message) -> None:
    from scheduler import update_pinned_prayer
    await update_pinned_prayer(message.bot)
    await message.answer("✅ تم تحديث الرسالة المثبتة.")


@router.message(Command("reload_json"))
async def cmd_reload_json(message: Message) -> None:
    content_service.reload_all()
    await message.answer("✅ تم إعادة تحميل ملفات JSON.")


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message) -> None:
    text = message.text.replace("/broadcast", "").strip()
    if not text:
        await message.answer("⚠️ استخدام: /broadcast [النص]")
        return

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT id FROM users")
        users = [r[0] for r in await cur.fetchall()]

    sent, failed = 0, 0
    for uid in users:
        try:
            await message.bot.send_message(uid, text, parse_mode="HTML")
            sent += 1
        except Exception:
            failed += 1

    await message.answer(f"📢 <b>إرسال جماعي:</b>\n✅ نجح: {sent}\n❌ فشل: {failed}", parse_mode="HTML")
