import math
import logging
from datetime import date, datetime, timedelta
import pytz
from config import LATITUDE, LONGITUDE, UTC_OFFSET, DEFAULT_TIMEZONE, DEFAULT_CITY

logger = logging.getLogger(__name__)

PRAYER_NAMES_AR = {
    "fajr": "الفجر",
    "sunrise": "الشروق",
    "dhuhr": "الظهر",
    "asr": "العصر",
    "maghrib": "المغرب",
    "isha": "العشاء",
}

PRAYER_ICONS = {
    "fajr": "🌅",
    "sunrise": "☀️",
    "dhuhr": "🌤",
    "asr": "🌇",
    "maghrib": "🌆",
    "isha": "🌙",
}


def _julian_date(d: date) -> float:
    year, month, day = d.year, d.month, d.day
    if month <= 2:
        year -= 1
        month += 12
    A = year // 100
    B = 2 - A + A // 4
    return int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day + B - 1524.5


def _sun_params(jd: float) -> tuple[float, float]:
    D = jd - 2451545.0
    g = math.radians(357.529 + 0.98560028 * D)
    q = 280.459 + 0.98564736 * D
    L = math.radians(q + 1.915 * math.sin(g) + 0.020 * math.sin(2 * g))
    e = math.radians(23.439 - 0.00000036 * D)
    RA = math.degrees(math.atan2(math.cos(e) * math.sin(L), math.cos(L))) / 15
    dec = math.degrees(math.asin(math.sin(e) * math.sin(L)))
    eq_t = q / 15 - RA
    return dec, eq_t


def _hour_angle(altitude_deg: float, dec: float, lat: float) -> float:
    lat_r = math.radians(lat)
    dec_r = math.radians(dec)
    cos_h = (math.sin(math.radians(altitude_deg)) - math.sin(lat_r) * math.sin(dec_r)) / (
        math.cos(lat_r) * math.cos(dec_r)
    )
    cos_h = max(-1.0, min(1.0, cos_h))
    return math.degrees(math.acos(cos_h)) / 15


def _asr_angle(shadow_factor: float, dec: float, lat: float) -> float:
    lat_r = math.radians(lat)
    dec_r = math.radians(dec)
    angle = math.degrees(math.atan(1.0 / (shadow_factor + math.tan(abs(lat_r - dec_r)))))
    return _hour_angle(angle, dec, lat)
<<<<<<< HEAD

=======
>>>>>>> 1414ff53755537c838f7cbb135f5707f6c117bba


def _decimal_to_time(hours: float, d: date) -> datetime:
    tz = pytz.timezone(DEFAULT_TIMEZONE)
    hours = hours % 24
    total_seconds = round(hours * 3600)
    h = (total_seconds // 3600) % 24
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    naive = datetime(d.year, d.month, d.day, h, m, s)
    return tz.localize(naive)


def get_prayer_times(d: date | None = None) -> dict[str, datetime]:
    if d is None:
        d = datetime.now(pytz.timezone(DEFAULT_TIMEZONE)).date()

    jd = _julian_date(d)
    dec, eq_t = _sun_params(jd)

    solar_noon = 12.0 - LONGITUDE / 15.0 - eq_t + UTC_OFFSET

    fajr_h = solar_noon - _hour_angle(-16.0, dec, LATITUDE)
    sunrise_h = solar_noon - _hour_angle(-0.833, dec, LATITUDE)
    dhuhr_h = solar_noon + (1.0 / 12.0)
    asr_h = solar_noon + _asr_angle(1.0, dec, LATITUDE)
    maghrib_h = solar_noon + _hour_angle(-4.0, dec, LATITUDE)
    isha_h = solar_noon + _hour_angle(-14.0, dec, LATITUDE)

    return {
        "fajr": _decimal_to_time(fajr_h, d),
        "sunrise": _decimal_to_time(sunrise_h, d),
        "dhuhr": _decimal_to_time(dhuhr_h, d),
        "asr": _decimal_to_time(asr_h, d),
        "maghrib": _decimal_to_time(maghrib_h, d),
        "isha": _decimal_to_time(isha_h, d),
    }


def get_next_prayer(times: dict[str, datetime] | None = None) -> tuple[str, datetime] | None:
    tz = pytz.timezone(DEFAULT_TIMEZONE)
    now = datetime.now(tz)
    if times is None:
        times = get_prayer_times()

    ordered = ["fajr", "sunrise", "dhuhr", "asr", "maghrib", "isha"]
    for name in ordered:
        if name in times and times[name] > now:
            return name, times[name]

    tomorrow = (now + timedelta(days=1)).date()
    tomorrow_times = get_prayer_times(tomorrow)
    return "fajr", tomorrow_times["fajr"]


def countdown(target: datetime) -> str:
    tz = pytz.timezone(DEFAULT_TIMEZONE)
    now = datetime.now(tz)
    diff = target - now
    if diff.total_seconds() <= 0:
        return "00:00:00"
    total_seconds = int(diff.total_seconds())
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def format_prayer_times(times: dict[str, datetime]) -> str:
    # إزاحات تصحيحية (بالدقائق) لتطابق التوقيت المحلي
    offsets = {
        "fajr": -15,      # أضف دقيقتين للفجر
        "sunrise": -2,
        "dhuhr": -5,     # أضف دقيقة للظهر
        "asr": 1,
        "maghrib": 2,   # أضف 3 دقائق للمغرب
        "isha": 2       # أضف دقيقتين للعشاء
    }

    lines = [f"🕌 <b>مواقيت الصلاة — {DEFAULT_CITY}</b>\\n"]
    for key in ["fajr", "sunrise", "dhuhr", "asr", "maghrib", "isha"]:
        if key not in times:
            continue

        # تطبيق الإزاحة
        adjusted_time = times[key] + timedelta(minutes=offsets.get(key, 0))

        icon = PRAYER_ICONS.get(key, "🕐")
        name = PRAYER_NAMES_AR.get(key, key)
        time_str = adjusted_time.strftime("%I:%M %p")
        lines.append(f"{icon} <b>{name}</b>: {time_str}")

    return "\n".join(lines)


def format_pinned_prayer(times: dict[str, datetime]) -> str:
    next_prayer = get_next_prayer(times)
    lines = ["🕌 <b>مواقيت الصلاة</b>"]
    lines.append(f"📍 <b>{DEFAULT_CITY}</b>\n")

    for key in ["fajr", "sunrise", "dhuhr", "asr", "maghrib", "isha"]:
        if key not in times:
            continue
        icon = PRAYER_ICONS.get(key, "🕐")
        name = PRAYER_NAMES_AR.get(key, key)
        time_str = times[key].strftime("%H:%M")
        if next_prayer and next_prayer[0] == key:
            cd = countdown(next_prayer[1])
            lines.append(f"▶️ <b>{icon} {name}: {time_str}</b>  ⏳ {cd}")
        else:
            lines.append(f"   {icon} {name}: {time_str}")

    return "\n".join(lines)
