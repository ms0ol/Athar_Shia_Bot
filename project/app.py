import asyncio
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

import config
from database import init_db
from scheduler import start_scheduler, stop_scheduler, update_pinned_prayer
import handlers
import admin


def setup_logging() -> None:
    os.makedirs(config.LOGS_PATH, exist_ok=True)
    fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    log_handlers = [
        logging.StreamHandler(sys.stdout),
        RotatingFileHandler(
            os.path.join(config.LOGS_PATH, "bot.log"),
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        ),
    ]

    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL, logging.INFO),
        format=fmt,
        datefmt=datefmt,
        handlers=log_handlers,
    )
    logging.getLogger("aiogram").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)


async def main() -> None:
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting Shia Religious Bot — Phase 5")

    if not config.BOT_TOKEN:
        logger.critical("BOT_TOKEN is not set.")
        sys.exit(1)

    await init_db()

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    dp.include_router(handlers.router)
    dp.include_router(admin.router)

    start_scheduler(bot)

    if config.CHANNEL_ID:
        logger.info("Channel configured: %s — syncing pinned message on startup", config.CHANNEL_ID)
        await update_pinned_prayer(bot)

    logger.info("Bot is running. Press Ctrl+C to stop.")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        stop_scheduler()
        await bot.session.close()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
