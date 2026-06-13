import logging
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import CHANNEL_ID
from database import get_state, set_state
from services.prayer_service import get_prayer_times, format_pinned_prayer

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="Asia/Baghdad")
_bot: Bot | None = None


def init_scheduler(bot: Bot) -> None:
    global _bot
    _bot = bot


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
                logger.debug("Pinned prayer message updated (id=%s)", msg_id)
                return
            except Exception as e:
                logger.warning("Could not edit pinned message: %s — sending new one", e)

        sent = await bot.send_message(CHANNEL_ID, text, parse_mode="HTML")
        await bot.pin_chat_message(CHANNEL_ID, sent.message_id, disable_notification=True)
        await set_state("pinned_prayer_msg_id", str(sent.message_id))
        logger.info("New pinned prayer message sent (id=%d)", sent.message_id)

    except Exception as e:
        logger.error("update_pinned_prayer error: %s", e)


def start_scheduler(bot: Bot) -> None:
    init_scheduler(bot)

    if CHANNEL_ID:
        scheduler.add_job(
            update_pinned_prayer,
            trigger="interval",
            minutes=1,
            id="pinned_prayer",
            replace_existing=True,
        )
        logger.info("Pinned prayer job scheduled (every 1 minute)")
    else:
        logger.info("CHANNEL_ID not set — pinned prayer message disabled")

    scheduler.start()
    logger.info("Scheduler started")


def stop_scheduler() -> None:
    scheduler.shutdown(wait=False)
    logger.info("Scheduler stopped")
