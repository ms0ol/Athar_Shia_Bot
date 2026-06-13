import json
import logging
import os
from datetime import date, timedelta
from hijri_converter import Gregorian
from config import DATA_PATH

logger = logging.getLogger(__name__)

WEEKDAYS_AR = {
    "saturday": "السبت",
    "sunday": "الأحد",
    "monday": "الاثنين",
    "tuesday": "الثلاثاء",
    "wednesday": "الأربعاء",
    "thursday": "الخميس",
    "friday": "الجمعة",
}

WEEKDAYS_EN = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def _load_events() -> list:
    path = os.path.join(DATA_PATH, "event_content/events.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _load_weekly_duas() -> list:
    path = os.path.join(DATA_PATH, "event_content/weekly_duas.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _to_hijri(d: date) -> tuple[int, int]:
    h = Gregorian(d.year, d.month, d.day).to_hijri()
    return h.month, h.day


def _hijri_key(d: date) -> str:
    month, day = _to_hijri(d)
    return f"{month:02d}-{day:02d}"


def get_current_event(d: date | None = None) -> dict | None:
    if d is None:
        d = date.today()
    key = _hijri_key(d)
    events = _load_events()
    matches = [e for e in events if e.get("hijri_date") == key]
    if not matches:
        return None
    return max(matches, key=lambda x: x.get("send_score", 0))


def get_upcoming_events(days: int = 7, d: date | None = None) -> list[dict]:
    if d is None:
        d = date.today()
    events = _load_events()
    upcoming = []
    for i in range(1, days + 1):
        check = d + timedelta(days=i)
        key = _hijri_key(check)
        for e in events:
            if e.get("hijri_date") == key:
                upcoming.append({**e, "_days_until": i})
    return upcoming[:5]


def get_today_dua(d: date | None = None) -> dict | None:
    if d is None:
        d = date.today()
    weekday_name = WEEKDAYS_EN[d.weekday()]
    duas = _load_weekly_duas()
    for dua in duas:
        if dua.get("weekday") == weekday_name:
            return dua
    return None


def format_event(event: dict, show_pin: bool = False) -> str:
    title = event.get("title", "")
    desc = event.get("description", "")
    pin = "\n📌 <i>هذا اليوم يُعدّ من أبرز المناسبات</i>" if show_pin and event.get("pin_message") else ""
    return f"🗓 <b>{title}</b>\n\n{desc}{pin}"


def format_upcoming(events: list) -> str:
    if not events:
        return "لا توجد مناسبات خلال الأيام السبعة القادمة."
    lines = ["📅 <b>المناسبات القادمة:</b>\n"]
    for e in events:
        days = e["_days_until"]
        title = e["title"]
        unit = "يوم" if days == 1 else "أيام"
        lines.append(f"• <b>{title}</b> — بعد {days} {unit}")
    return "\n".join(lines)


def format_hijri_today(d: date | None = None) -> str:
    if d is None:
        d = date.today()
    h = Gregorian(d.year, d.month, d.day).to_hijri()
    weekday = WEEKDAYS_EN[d.weekday()]
    weekday_ar = WEEKDAYS_AR.get(weekday, "")
    hijri_months = [
        "", "محرم", "صفر", "ربيع الأول", "ربيع الثاني",
        "جمادى الأولى", "جمادى الثانية", "رجب", "شعبان",
        "رمضان", "شوال", "ذو القعدة", "ذو الحجة",
    ]
    month_ar = hijri_months[h.month] if 1 <= h.month <= 12 else ""
    return f"{weekday_ar} | {h.day} {month_ar} {h.year} هـ"
