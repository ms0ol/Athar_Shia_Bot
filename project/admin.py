import asyncio
import logging
from datetime import date
import aiosqlite
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.filters.base import Filter

from config import ADMIN_IDS, DB_PATH
from services import content_service, prayer_service, event_service

logger = logging.getLogger(__name__)
router = Router()


class IsAdmin(Filter):
    async def __call__(self, message: Message) -> bool:
        return message.from_user.id in ADMIN_IDS


router.message.filter(IsAdmin())


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        (user_count,) = (await (await db.execute("SELECT COUNT(*) FROM users")).fetchone())
        (sub_count,) = (await (await db.execute("SELECT COUNT(*) FROM subscriptions WHERE active=1")).fetchone())
        (sent_count,) = (await (await db.execute("SELECT COUNT(*) FROM sent_content")).fetchone())
        cur = await db.execute("SELECT content_type, COUNT(*) FROM subscriptions WHERE active=1 GROUP BY content_type")
        sub_breakdown = await cur.fetchall()

    breakdown = "\n".join(f"  • {ct}: {n}" for ct, n in sub_breakdown)
    await message.answer(
        f"📊 <b>إحصائيات البوت:</b>\n\n"
        f"👤 المستخدمون: {user_count}\n"
        f"🔔 الاشتراكات النشطة: {sub_count}\n"
        f"📤 المحتوى المُرسل: {sent_count}\n\n"
        f"<b>توزيع الاشتراكات:</b>\n{breakdown}",
        parse_mode="HTML",
    )


@router.message(Command("test_hadith"))
async def cmd_test_hadith(message: Message) -> None:
    item = await content_service.get_random_hadith()
    if item:
        for part in content_service.split_message(content_service.format_content(item)):
            await message.answer(part, parse_mode="HTML")
    else:
        await message.answer("⚠️ لا يوجد حديث.")


@router.message(Command("test_wisdom"))
async def cmd_test_wisdom(message: Message) -> None:
    item = await content_service.get_random_wisdom()
    if item:
        for part in content_service.split_message(content_service.format_content(item)):
            await message.answer(part, parse_mode="HTML")
    else:
        await message.answer("⚠️ لا توجد حكمة.")


@router.message(Command("test_dua"))
async def cmd_test_dua(message: Message) -> None:
    item = await content_service.get_daily_dua()
    if item:
        for part in content_service.split_message(content_service.format_content(item)):
            await message.answer(part, parse_mode="HTML")
    else:
        await message.answer("⚠️ لا يوجد دعاء.")


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


@router.message(Command("test_adhan"))
async def cmd_test_adhan(message: Message) -> None:
    from services.prayer_service import PRAYER_NAMES_AR, PRAYER_ICONS
    times = prayer_service.get_prayer_times()
    next_p = prayer_service.get_next_prayer(times)
    if next_p:
        prayer = next_p[0]
        icon = PRAYER_ICONS.get(prayer, "🔔")
        name = PRAYER_NAMES_AR.get(prayer, prayer)
        await message.answer(
            f"🔔 <b>حان الآن أذان {name}</b> {icon}\n\nاللهم صلِّ على محمد وآل محمد",
            parse_mode="HTML",
        )
    else:
        await message.answer("⚠️ لا تتوفر معلومات الأذان.")


@router.message(Command("test_taqibat"))
async def cmd_test_taqibat(message: Message) -> None:
    args = message.text.split()
    prayer = args[1] if len(args) > 1 else "fajr"
    item = await content_service.get_taqibat(prayer)
    if item:
        for part in content_service.split_message(content_service.format_content(item)):
            await message.answer(part, parse_mode="HTML")
    else:
        await message.answer(f"⚠️ لا توجد تعقيبات لـ {prayer}.")


@router.message(Command("test_pinned"))
async def cmd_test_pinned(message: Message) -> None:
    from scheduler import update_pinned_prayer
    await update_pinned_prayer(message.bot)
    await message.answer("✅ تم تحديث الرسالة المثبتة.")


@router.message(Command("test_event"))
async def cmd_test_event(message: Message) -> None:
    today = date.today()
    hijri = event_service.format_hijri_today(today)
    event = event_service.get_current_event(today)
    upcoming = event_service.get_upcoming_events(7, today)
    parts = [f"🗓 <b>{hijri}</b>\n"]
    if event:
        parts.append(event_service.format_event(event, show_pin=True))
    else:
        parts.append("لا توجد مناسبة اليوم.")
    parts.append("\n" + event_service.format_upcoming(upcoming))
    await message.answer("\n".join(parts), parse_mode="HTML")


@router.message(Command("reload_json"))
async def cmd_reload_json(message: Message) -> None:
    content_service.reload_all()
    await message.answer("✅ تم إعادة تحميل ملفات JSON.")


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message) -> None:
    text = message.text.replace("/broadcast", "", 1).strip()
    if not text:
        await message.answer("⚠️ استخدام: /broadcast [النص]")
        return

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT id FROM users")
        users = [r[0] for r in await cur.fetchall()]

    sent, failed = 0, 0
    for uid in users:
        try:
            for part in content_service.split_message(text):
                await message.bot.send_message(uid, part, parse_mode="HTML")
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)  # C-03: ~20 msg/s rate limit

    await message.answer(
        f"📢 <b>إرسال جماعي:</b>\n✅ نجح: {sent}\n❌ فشل: {failed}",
        parse_mode="HTML",
    )


@router.message(Command("jobs"))
async def cmd_jobs(message: Message) -> None:
    from scheduler import scheduler
    jobs = scheduler.get_jobs()
    if not jobs:
        await message.answer("لا توجد مهام مجدولة.")
        return
    lines = [f"⚙️ <b>المهام المجدولة ({len(jobs)}):</b>\n"]
    for j in jobs:
        next_run = j.next_run_time.strftime("%H:%M") if j.next_run_time else "—"
        lines.append(f"• <code>{j.id}</code> → {next_run}")
    await message.answer("\n".join(lines), parse_mode="HTML")
