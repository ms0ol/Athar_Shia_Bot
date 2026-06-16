import asyncio
import logging
from datetime import date, datetime, timedelta

import pytz
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

from config import CHANNEL_ID, DEFAULT_TIMEZONE, DB_PATH
from database import get_state, set_state, try_claim_state
from services import content_service, subscription_service, event_service
from services.prayer_service import (
    PRAYER_NAMES_AR,
    PRAYER_ICONS,
    get_prayer_times,
    format_pinned_prayer,
)

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone=DEFAULT_TIMEZONE)
_bot: Bot | None = None


# ─── helpers ───────────────────────────────────────────────────────────────────

async def _send_to_subscribers(bot: Bot, content_type: str, text: str) -> None:
    subscribers = await subscription_service.get_subscribers(content_type)
    sent, failed = 0, 0
    for uid in subscribers:
        try:
            parts = content_service.split_message(text)
            for part in parts:
                await bot.send_message(uid, part, parse_mode="HTML")
            sent += 1
        except Exception as e:
            logger.debug("Failed to send to %d: %s", uid, e)
            failed += 1
        await asyncio.sleep(0.05)  # C-03: ~20 msg/s rate limit
    logger.info("Sent '%s' → %d ok / %d failed", content_type, sent, failed)


async def _send_to_channel(bot: Bot, text: str) -> None:
    if not CHANNEL_ID:
        return
    try:
        parts = content_service.split_message(text)
        for part in parts:
            await bot.send_message(CHANNEL_ID, part, parse_mode="HTML")
    except Exception as e:
        logger.error("Channel send error: %s", e)


async def _send_broadcast(bot: Bot, text: str) -> None:
    import aiosqlite
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT id FROM users")
        users = [r[0] for r in await cur.fetchall()]
    for uid in users:
        try:
            parts = content_service.split_message(text)
            for part in parts:
                await bot.send_message(uid, part, parse_mode="HTML")
        except Exception:
            pass
        await asyncio.sleep(0.05)  # C-03: ~20 msg/s rate limit


# ─── Phase 5: pinned prayer message ────────────────────────────────────────────

async def update_pinned_prayer(bot: Bot | None = None) -> None:
    if bot is None:
        bot = _bot
    if bot is None or not CHANNEL_ID:
        return
    try:
        times = get_prayer_times()
        text = format_pinned_prayer(times)
        msg_id = await get_state("pinned_prayer_msg_id")

        if msg_id:
            try:
                await bot.edit_message_text(
                    chat_id=CHANNEL_ID,
                    message_id=int(msg_id),
                    text=text,
                    parse_mode="HTML",
                )
                return
            except Exception as e:
                logger.warning("Cannot edit pinned msg: %s — will resend", e)

        sent = await bot.send_message(CHANNEL_ID, text, parse_mode="HTML")
        await bot.pin_chat_message(CHANNEL_ID, sent.message_id, disable_notification=True)
        await set_state("pinned_prayer_msg_id", str(sent.message_id))
        logger.info("New pinned prayer message id=%d", sent.message_id)
    except Exception as e:
        logger.error("update_pinned_prayer: %s", e)


# ─── Phase 6: adhan notification ───────────────────────────────────────────────

async def send_adhan(prayer: str) -> None:
    if _bot is None:
        return
    today = datetime.now(pytz.timezone(DEFAULT_TIMEZONE)).strftime("%Y-%m-%d")
    state_key = f"adhan_{prayer}_{today}"
    # H-02: atomic INSERT OR IGNORE — only first caller proceeds
    if not await try_claim_state(state_key):
        logger.debug("Adhan %s already sent today, skipping", prayer)
        return

    icon = PRAYER_ICONS.get(prayer, "🔔")
    name = PRAYER_NAMES_AR.get(prayer, prayer)
    text = f"🔔 <b>حان الآن أذان {name}</b> {icon}\n\nاللهم صلِّ على محمد وآل محمد"

    if CHANNEL_ID:
        await _send_to_channel(_bot, text)
    else:
        await _send_broadcast(_bot, text)

    logger.info("Adhan sent: %s", prayer)


# ─── Phase 7: prayer taqibat ───────────────────────────────────────────────────

async def send_taqibat(prayer: str) -> None:
    if _bot is None:
        return
    today = datetime.now(pytz.timezone(DEFAULT_TIMEZONE)).strftime("%Y-%m-%d")
    state_key = f"taqibat_{prayer}_{today}"
    # H-02: atomic INSERT OR IGNORE — only first caller proceeds
    if not await try_claim_state(state_key):
        logger.debug("Taqibat %s already sent today", prayer)
        return

    item = await content_service.get_taqibat(prayer)
    if not item:
        logger.warning("No taqibat found for %s", prayer)
        return

    text = content_service.format_content(item)

    if CHANNEL_ID:
        await _send_to_channel(_bot, text)
    else:
        await _send_to_subscribers(_bot, "taqibat", text)

    logger.info("Taqibat sent: %s", prayer)


# ─── Phase 8: daily content ────────────────────────────────────────────────────

async def _daily_send(content_type: str, getter, sub_type: str) -> None:
    if _bot is None:
        return
    item = await getter()
    if not item:
        logger.warning("No item for daily %s", content_type)
        return
    text = content_service.format_content(item)
    await _send_to_subscribers(_bot, sub_type, text)
    logger.info("Daily %s sent", content_type)


async def send_daily_hadith() -> None:
    await _daily_send("hadith", content_service.get_random_hadith, "hadith")


async def send_daily_wisdom() -> None:
    await _daily_send("wisdom", content_service.get_random_wisdom, "wisdom")


async def send_daily_dua() -> None:
    await _daily_send("dua", content_service.get_daily_dua, "daily_dua")


async def send_daily_munajat() -> None:
    await _daily_send("munajat", content_service.get_munajat, "taqibat")



# ─── Phase 9: event check ──────────────────────────────────────────────────────

async def check_daily_event() -> None:
    if _bot is None:
        return

    from datetime import date, timedelta
    import os
    from config import CHANNEL_ID

    today = date.today()
    state_key = f"event_checked_{today.isoformat()}"
    if await get_state(state_key):
        return

    # 💡 نسحب الإزاحة مباشرة بدون المرور بملف الإعدادات لتجنب المشاكل
    offset = int(os.getenv("HIJRI_OFFSET", "-1"))
    shia_today = today + timedelta(days=offset)

    event = event_service.get_current_event(shia_today)

    if event:
        text = event_service.format_event(event, show_pin=True)
        hijri = event_service.format_hijri_today(today)
        full_text = f"🗓 <b>{hijri}</b>\n\n{text}"

        if CHANNEL_ID:
            if event.get("pin_message"):
                try:
                    msg = await _bot.send_message(CHANNEL_ID, full_text, parse_mode="HTML")
                    await _bot.pin_chat_message(CHANNEL_ID, msg.message_id, disable_notification=False)
                except Exception as e:
                    logger.error("Pin event error: %s", e)
                    await _send_to_channel(_bot, full_text)
            else:
                await _send_to_channel(_bot, full_text)
        else:
            await _send_broadcast(_bot, full_text)

        logger.info("Event announced: %s", event.get("title"))

    await set_state(state_key, "done")


# ─── prayer jobs: schedule daily ───────────────────────────────────────────────

TAQIBAT_DELAYS = {"fajr": 3, "dhuhr": 2, "maghrib": 2}
ADHAN_PRAYERS = ["fajr", "dhuhr", "asr", "maghrib", "isha"]


def _schedule_prayer_jobs_for_day(d: date | None = None) -> None:
    if d is None:
        d = datetime.now(pytz.timezone(DEFAULT_TIMEZONE)).date()

    times = get_prayer_times(d)
    tz = pytz.timezone(DEFAULT_TIMEZONE)
    now = datetime.now(tz)

    for prayer in ADHAN_PRAYERS:
        if prayer not in times:
            continue
        prayer_dt = times[prayer]
        if prayer_dt <= now:
            continue

        job_id = f"adhan_{prayer}_{d.isoformat()}"
        if not scheduler.get_job(job_id):
            scheduler.add_job(
                send_adhan,
                trigger=DateTrigger(run_date=prayer_dt, timezone=tz),
                args=[prayer],
                id=job_id,
                replace_existing=True,
                misfire_grace_time=120,
            )
            logger.debug("Scheduled adhan: %s @ %s", prayer, prayer_dt.strftime("%H:%M"))

        # M-06: schedule taqibat independently — don't skip if only taqibat time passed
        delay = TAQIBAT_DELAYS.get(prayer)
        if delay:
            taqibat_dt = prayer_dt + timedelta(minutes=delay)
            if taqibat_dt > now:
                tid = f"taqibat_{prayer}_{d.isoformat()}"
                if not scheduler.get_job(tid):
                    scheduler.add_job(
                        send_taqibat,
                        trigger=DateTrigger(run_date=taqibat_dt, timezone=tz),
                        args=[prayer],
                        id=tid,
                        replace_existing=True,
                        misfire_grace_time=120,
                    )
                    logger.debug("Scheduled taqibat: %s @ %s", prayer, taqibat_dt.strftime("%H:%M"))

    logger.info("Prayer jobs scheduled for %s", d.isoformat())


async def _reschedule_next_day() -> None:
    tz = pytz.timezone(DEFAULT_TIMEZONE)
    tomorrow = (datetime.now(tz) + timedelta(days=1)).date()
    _schedule_prayer_jobs_for_day(tomorrow)


# ─── start / stop ──────────────────────────────────────────────────────────────

def start_scheduler(bot: Bot) -> None:
    global _bot
    _bot = bot

    if CHANNEL_ID:
        scheduler.add_job(
            update_pinned_prayer,
            trigger="interval",
            minutes=1,
            id="pinned_prayer",
            replace_existing=True,
        )

    scheduler.add_job(send_daily_hadith,  CronTrigger(hour=8,  minute=0, timezone=DEFAULT_TIMEZONE), id="daily_hadith",  replace_existing=True)
    scheduler.add_job(send_daily_wisdom,  CronTrigger(hour=13, minute=0, timezone=DEFAULT_TIMEZONE), id="daily_wisdom",  replace_existing=True)
    scheduler.add_job(send_daily_dua,     CronTrigger(hour=18, minute=0, timezone=DEFAULT_TIMEZONE), id="daily_dua",     replace_existing=True)
    scheduler.add_job(send_daily_munajat, CronTrigger(hour=20, minute=0, timezone=DEFAULT_TIMEZONE), id="daily_munajat", replace_existing=True)
    scheduler.add_job(check_daily_event,  CronTrigger(hour=7,  minute=0, timezone=DEFAULT_TIMEZONE), id="daily_event",   replace_existing=True)
    scheduler.add_job(_reschedule_next_day, CronTrigger(hour=0, minute=1, timezone=DEFAULT_TIMEZONE), id="reschedule_prayers", replace_existing=True)

    _schedule_prayer_jobs_for_day()

    scheduler.start()
    logger.info("Scheduler started — %d jobs active", len(scheduler.get_jobs()))


def stop_scheduler() -> None:
    scheduler.shutdown(wait=False)
    logger.info("Scheduler stopped")
