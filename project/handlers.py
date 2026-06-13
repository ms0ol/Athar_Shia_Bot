import logging
import aiosqlite
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart, Command
from config import DB_PATH

logger = logging.getLogger(__name__)
router = Router()

MAIN_MENU = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="📿 القائمة الرئيسية")]],
    resize_keyboard=True,
)


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


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await save_user(message.from_user)
    logger.info("User %s started the bot", message.from_user.id)
    await message.answer(
        f"السلام عليكم ورحمة الله وبركاته 🌿\n\n"
        f"أهلاً وسهلاً بك يا {message.from_user.first_name}\n\n"
        f"هذا البوت الإسلامي الشيعي يقدم لك:\n"
        f"• الأحاديث والحكم اليومية\n"
        f"• مواقيت الصلاة\n"
        f"• الأدعية والمناجاة\n"
        f"• المناسبات الدينية\n\n"
        f"اضغط على الزر أدناه للبدء 👇",
        reply_markup=MAIN_MENU,
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "📖 <b>الأوامر المتاحة:</b>\n\n"
        "/start — بدء البوت\n"
        "/help  — عرض المساعدة\n"
        "/menu  — القائمة الرئيسية",
        parse_mode="HTML",
    )


@router.message(Command("menu"))
@router.message(F.text == "📿 القائمة الرئيسية")
async def cmd_menu(message: Message) -> None:
    await message.answer(
        "📿 <b>القائمة الرئيسية</b>\n\n"
        "اختر ما تريد من القائمة.",
        parse_mode="HTML",
        reply_markup=MAIN_MENU,
    )
