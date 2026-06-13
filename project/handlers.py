import logging
import aiosqlite
from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.filters import CommandStart, Command

from config import DB_PATH
from services import content_service, subscription_service, prayer_service

logger = logging.getLogger(__name__)
router = Router()

MAIN_KB = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="📿 القائمة الرئيسية")]],
    resize_keyboard=True,
)


def main_menu_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📿 حديث اليوم",    callback_data="content:hadith"),
            InlineKeyboardButton(text="💎 حكمة يومية",    callback_data="content:wisdom"),
        ],
        [
            InlineKeyboardButton(text="🤲 دعاء اليوم",    callback_data="content:dua"),
            InlineKeyboardButton(text="🌙 مناجاة",        callback_data="content:munajat"),
        ],
        [
            InlineKeyboardButton(text="🕌 مواقيت الصلاة", callback_data="content:prayer"),
            InlineKeyboardButton(text="📖 زيارة",         callback_data="content:ziyarah"),
        ],
        [
            InlineKeyboardButton(text="🔔 اشتراكاتي",     callback_data="subs:show"),
        ],
    ])


def subscriptions_inline(user_subs: list[str]) -> InlineKeyboardMarkup:
    def btn(label: str, key: str) -> InlineKeyboardButton:
        active = key in user_subs
        status = "✅" if active else "❌"
        action = "unsub" if active else "sub"
        return InlineKeyboardButton(text=f"{status} {label}", callback_data=f"subs:{action}:{key}")

    return InlineKeyboardMarkup(inline_keyboard=[
        [btn("📿 حديث اليوم",       "hadith")],
        [btn("💎 حكمة يومية",       "wisdom")],
        [btn("🤲 دعاء يومي",        "daily_dua")],
        [btn("📖 تعقيبات الصلاة",   "taqibat")],
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="menu:main")],
    ])


async def save_user(user) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO users (id, username, first_name)
            VALUES (?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                username   = excluded.username,
                first_name = excluded.first_name
            """,
            (user.id, user.username, user.first_name),
        )
        await db.commit()


async def send_long(message: Message, text: str) -> None:
    parts = content_service.split_message(text)
    for part in parts:
        await message.answer(part, parse_mode="HTML")


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await save_user(message.from_user)
    logger.info("User %s started the bot", message.from_user.id)
    await message.answer(
        f"السلام عليكم ورحمة الله وبركاته 🌿\n\n"
        f"أهلاً وسهلاً بك يا <b>{message.from_user.first_name}</b>\n\n"
        f"اضغط على الزر أدناه للقائمة الرئيسية 👇",
        reply_markup=MAIN_KB,
        parse_mode="HTML",
    )
    await message.answer("📿 <b>القائمة الرئيسية</b>", reply_markup=main_menu_inline(), parse_mode="HTML")


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "📖 <b>الأوامر المتاحة:</b>\n\n"
        "/start  — بدء البوت\n"
        "/help   — المساعدة\n"
        "/menu   — القائمة الرئيسية\n"
        "/prayer — مواقيت الصلاة",
        parse_mode="HTML",
    )


@router.message(Command("menu"))
@router.message(F.text == "📿 القائمة الرئيسية")
async def cmd_menu(message: Message) -> None:
    await message.answer("📿 <b>القائمة الرئيسية</b>", reply_markup=main_menu_inline(), parse_mode="HTML")


@router.message(Command("prayer"))
async def cmd_prayer(message: Message) -> None:
    times = prayer_service.get_prayer_times()
    next_p = prayer_service.get_next_prayer(times)
    text = prayer_service.format_prayer_times(times)
    if next_p:
        name_ar = prayer_service.PRAYER_NAMES_AR.get(next_p[0], next_p[0])
        cd = prayer_service.countdown(next_p[1])
        text += f"\n\n⏳ <b>الصلاة القادمة:</b> {name_ar}\n🕐 بعد: {cd}"
    await message.answer(text, parse_mode="HTML")


@router.callback_query(F.data == "menu:main")
async def cb_main_menu(cb: CallbackQuery) -> None:
    await cb.message.edit_text("📿 <b>القائمة الرئيسية</b>", reply_markup=main_menu_inline(), parse_mode="HTML")


@router.callback_query(F.data == "content:hadith")
async def cb_hadith(cb: CallbackQuery) -> None:
    await cb.answer()
    item = await content_service.get_random_hadith()
    if item:
        await send_long(cb.message, content_service.format_content(item))
    else:
        await cb.message.answer("⚠️ لا يوجد محتوى متاح حالياً.")


@router.callback_query(F.data == "content:wisdom")
async def cb_wisdom(cb: CallbackQuery) -> None:
    await cb.answer()
    item = await content_service.get_random_wisdom()
    if item:
        await send_long(cb.message, content_service.format_content(item))
    else:
        await cb.message.answer("⚠️ لا يوجد محتوى متاح حالياً.")


@router.callback_query(F.data == "content:dua")
async def cb_dua(cb: CallbackQuery) -> None:
    await cb.answer()
    item = await content_service.get_daily_dua()
    if item:
        await send_long(cb.message, content_service.format_content(item))
    else:
        await cb.message.answer("⚠️ لا يوجد محتوى متاح حالياً.")


@router.callback_query(F.data == "content:munajat")
async def cb_munajat(cb: CallbackQuery) -> None:
    await cb.answer()
    item = await content_service.get_munajat()
    if item:
        await send_long(cb.message, content_service.format_content(item))
    else:
        await cb.message.answer("⚠️ لا يوجد محتوى متاح حالياً.")


@router.callback_query(F.data == "content:ziyarah")
async def cb_ziyarah(cb: CallbackQuery) -> None:
    await cb.answer()
    item = await content_service.get_ziyarah()
    if item:
        await send_long(cb.message, content_service.format_content(item))
    else:
        await cb.message.answer("⚠️ لا يوجد محتوى متاح حالياً.")


@router.callback_query(F.data == "content:prayer")
async def cb_prayer(cb: CallbackQuery) -> None:
    await cb.answer()
    times = prayer_service.get_prayer_times()
    next_p = prayer_service.get_next_prayer(times)
    text = prayer_service.format_prayer_times(times)
    if next_p:
        name_ar = prayer_service.PRAYER_NAMES_AR.get(next_p[0], next_p[0])
        cd = prayer_service.countdown(next_p[1])
        text += f"\n\n⏳ <b>الصلاة القادمة:</b> {name_ar}\n🕐 بعد: {cd}"
    await cb.message.answer(text, parse_mode="HTML")


@router.callback_query(F.data == "subs:show")
async def cb_subs_show(cb: CallbackQuery) -> None:
    await cb.answer()
    user_subs = await subscription_service.get_user_subscriptions(cb.from_user.id)
    await cb.message.edit_text(
        "🔔 <b>اشتراكاتي</b>\n\nاضغط لتفعيل أو إيقاف أي اشتراك:",
        reply_markup=subscriptions_inline(user_subs),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("subs:sub:"))
async def cb_subscribe(cb: CallbackQuery) -> None:
    content_type = cb.data.split(":")[2]
    await subscription_service.subscribe(cb.from_user.id, content_type)
    user_subs = await subscription_service.get_user_subscriptions(cb.from_user.id)
    await cb.message.edit_reply_markup(reply_markup=subscriptions_inline(user_subs))
    await cb.answer("✅ تم الاشتراك بنجاح!")


@router.callback_query(F.data.startswith("subs:unsub:"))
async def cb_unsubscribe(cb: CallbackQuery) -> None:
    content_type = cb.data.split(":")[2]
    await subscription_service.unsubscribe(cb.from_user.id, content_type)
    user_subs = await subscription_service.get_user_subscriptions(cb.from_user.id)
    await cb.message.edit_reply_markup(reply_markup=subscriptions_inline(user_subs))
    await cb.answer("❌ تم إلغاء الاشتراك.")
