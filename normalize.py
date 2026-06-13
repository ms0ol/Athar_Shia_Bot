#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
normalize.py — Data Architecture Script for Shia Telegram Bot
Reads all raw JSON files, normalizes them, and writes structured output.
"""

import os
import json
import re
import shutil
from datetime import datetime

# ─────────────────────────────────────────────
# DIRECTORY STRUCTURE
# ─────────────────────────────────────────────
DIRS = [
    "data/raw/hadith",
    "data/raw/duas",
    "data/raw/taqibat",
    "data/raw/munajat",
    "data/raw/events",
    "data/raw/tafsir",
    "data/normalized/daily_content",
    "data/normalized/prayer_content",
    "data/normalized/event_content",
    "data/normalized/bot_content",
    "data/runtime",
]

for d in DIRS:
    os.makedirs(d, exist_ok=True)

print("✅ Directory structure created.")

# ─────────────────────────────────────────────
# REPORT COUNTERS
# ─────────────────────────────────────────────
report = {
    "processed_files": [],
    "failed_files": [],
    "hadith_count": 0,
    "wisdom_count": 0,
    "dua_count": 0,
    "munajat_count": 0,
    "taqibat_count": 0,
    "weekly_duas_count": 0,
    "zyarat_count": 0,
    "events_count": 0,
    "issues": [],
}


# ─────────────────────────────────────────────
# HELPER: safe load JSON
# ─────────────────────────────────────────────
def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        report["failed_files"].append({"file": path, "error": str(e)})
        report["issues"].append(f"فشل تحليل: {path} — {e}")
        return None


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ─────────────────────────────────────────────
# STEP 1: COPY RAW FILES
# ─────────────────────────────────────────────
raw_map = {
    "Mohammed(PBUH).json":          "data/raw/hadith/Mohammed(PBUH).json",
    "Fatima-Zahra(as).json":        "data/raw/hadith/Fatima-Zahra(as).json",
    "Imam_AL-Baqer(as).json":       "data/raw/hadith/Imam_AL-Baqer(as).json",
    "Imam_AL-Mahdi(as).json":       "data/raw/hadith/Imam_AL-Mahdi(as).json",
    "Imam_Ali(as).json":            "data/raw/hadith/Imam_Ali(as).json",
    "duaas.json":                   "data/raw/duas/duaas.json",
    "zyarat.json":                  "data/raw/duas/zyarat.json",
    "munajat.json":                 "data/raw/munajat/munajat.json",
    "تعقيبات-الصلاة.json":         "data/raw/taqibat/تعقيبات-الصلاة.json",
    "تعقيبات-الصلاة-العامة.json":  "data/raw/taqibat/تعقيبات-الصلاة-العامة.json",
    "ادعية-ايام-الاسبوع.json":     "data/raw/events/ادعية-ايام-الاسبوع.json",
}

for src, dst in raw_map.items():
    if os.path.exists(src):
        shutil.copy2(src, dst)
        report["processed_files"].append(src)
        print(f"  📂 Copied: {src} → {dst}")
    else:
        report["issues"].append(f"ملف غير موجود: {src}")
        print(f"  ⚠️  Not found: {src}")

print("✅ Raw files copied.")


# ─────────────────────────────────────────────
# HELPER: extract source from text
# ─────────────────────────────────────────────
def extract_source(text):
    m = re.search(r'المصدر\s*[:\:]\s*(.+?)(?:\s*$)', text.strip(), re.MULTILINE)
    if m:
        src = m.group(1).strip()
        if src in ("_", "-", ""):
            return None
        return src
    return None


def clean_text(text):
    """Remove 'المصدر: ...' suffix from text body if present."""
    return re.sub(r'\s*المصدر\s*[:\:]\s*.+?$', '', text.strip(), flags=re.MULTILINE).strip()


# ─────────────────────────────────────────────
# STEP 2: NORMALIZED — hadith.json
# ─────────────────────────────────────────────
print("\n📖 Building hadith.json ...")

hadith_files = [
    ("data/raw/hadith/Mohammed(PBUH).json",    "النبي محمد ﷺ"),
    ("data/raw/hadith/Fatima-Zahra(as).json",  "السيدة فاطمة الزهراء عليها السلام"),
    ("data/raw/hadith/Imam_AL-Baqer(as).json", "الإمام محمد الباقر عليه السلام"),
    ("data/raw/hadith/Imam_AL-Mahdi(as).json", "الإمام المهدي عجل الله فرجه"),
]

hadith_list = []
h_counter = 1

for filepath, author in hadith_files:
    data = load_json(filepath)
    if data is None:
        continue
    # All these files are dict {"1": "text", "2": "text", ...}
    for key in sorted(data.keys(), key=lambda x: int(x) if x.isdigit() else 0):
        raw_text = data[key]
        source = extract_source(raw_text)
        text = clean_text(raw_text)
        hadith_list.append({
            "id": f"H{h_counter:06d}",
            "category": "hadith",
            "text": text,
            "author": author,
            "source": source,
            "chapter": None,
            "tags": [],
            "priority": 1,
            "sent": False,
        })
        h_counter += 1

report["hadith_count"] = len(hadith_list)
save_json("data/normalized/daily_content/hadith.json", hadith_list)
print(f"  ✅ hadith.json — {len(hadith_list)} حديث")


# ─────────────────────────────────────────────
# STEP 3: NORMALIZED — wisdom.json (Imam Ali)
# ─────────────────────────────────────────────
print("\n📖 Building wisdom.json ...")

ali_data = load_json("data/raw/hadith/Imam_Ali(as).json")
wisdom_list = []

if ali_data:
    for key in sorted(ali_data.keys(), key=lambda x: int(x) if x.isdigit() else 0):
        text = ali_data[key].strip()
        wisdom_list.append({
            "id": f"W{len(wisdom_list)+1:06d}",
            "category": "wisdom",
            "text": text,
            "author": "الإمام علي بن أبي طالب عليه السلام",
            "source": "غرر الحكم",
            "tags": [],
            "sent": False,
        })

report["wisdom_count"] = len(wisdom_list)
save_json("data/normalized/daily_content/wisdom.json", wisdom_list)
print(f"  ✅ wisdom.json — {len(wisdom_list)} حكمة")


# ─────────────────────────────────────────────
# STEP 4: NORMALIZED — daily_dua.json
# ─────────────────────────────────────────────
print("\n📖 Building daily_dua.json ...")

dua_list = []
d_counter = 1

# From duaas.json
duaas_data = load_json("data/raw/duas/duaas.json")
if duaas_data and "duaas" in duaas_data:
    for item in duaas_data["duaas"]:
        dua_list.append({
            "id": f"D{d_counter:06d}",
            "category": "dua",
            "title": item.get("name", ""),
            "text": item.get("text", ""),
            "source": item.get("source", None),
            "tags": [],
            "recommended_time": None,
            "sent": False,
        })
        d_counter += 1

# From zyarat.json
zyarat_data = load_json("data/raw/duas/zyarat.json")
if zyarat_data and "zyarat" in zyarat_data:
    for item in zyarat_data["zyarat"]:
        dua_list.append({
            "id": f"D{d_counter:06d}",
            "category": "zyarat",
            "title": item.get("name", ""),
            "text": item.get("text", ""),
            "source": item.get("source", None),
            "tags": [],
            "recommended_time": None,
            "sent": False,
        })
        d_counter += 1
        report["zyarat_count"] += 1

report["dua_count"] = d_counter - 1
save_json("data/normalized/daily_content/daily_dua.json", dua_list)
print(f"  ✅ daily_dua.json — {len(dua_list)} دعاء وزيارة")


# ─────────────────────────────────────────────
# STEP 5: NORMALIZED — munajat.json
# ─────────────────────────────────────────────
print("\n📖 Building munajat.json ...")

munajat_list = []

# munajat.json has a syntax error — try to load, fallback to manual parse
raw_munajat = load_json("data/raw/munajat/munajat.json")
if raw_munajat is None:
    # Manual fix: read text, fix commas between objects
    report["issues"].append("munajat.json تحتوي على خطأ JSON — تم إصلاح الهيكل تلقائياً")
    try:
        with open("munajat.json", "r", encoding="utf-8") as f:
            raw_text = f.read()
        # Fix: add missing commas between } and {
        fixed = re.sub(r'\}\s*\n+\s*\{', '},\n{', raw_text)
        raw_munajat = json.loads(fixed)
        print("  🔧 munajat.json — تم إصلاح الهيكل")
    except Exception as e:
        report["issues"].append(f"فشل إصلاح munajat.json: {e}")
        raw_munajat = None

if raw_munajat and "munajat" in raw_munajat:
    for item in raw_munajat["munajat"]:
        name = item.get("name", "")
        text = item.get("text", "")
        source = item.get("source", "مفاتيح الجنان")
        # Skip placeholder entries
        if name in ("munajat_name", "", None) or text in ("munajat_text", "", None):
            continue
        munajat_list.append({
            "id": f"MN{len(munajat_list)+1:03d}",
            "category": "munajat",
            "title": name,
            "text": text,
            "source": source,
        })

report["munajat_count"] = len(munajat_list)
save_json("data/normalized/daily_content/munajat.json", munajat_list)
print(f"  ✅ munajat.json — {len(munajat_list)} مناجاة")


# ─────────────────────────────────────────────
# STEP 6: NORMALIZED — weekly_duas.json
# ─────────────────────────────────────────────
print("\n📖 Building weekly_duas.json ...")

day_map = {
    "دعاء_يوم_السبت":     "saturday",
    "دعاء_يوم_الأحد":     "sunday",
    "دعاء_يوم_الاثنين":   "monday",
    "دعاء_يوم_الثلاثاء":  "tuesday",
    "دعاء_يوم_الأربعاء":  "wednesday",
    "دعاء_يوم_الخميس":    "thursday",
    "دعاء_يوم_الجمعة":    "friday",
}

day_title_map = {
    "saturday":  "دعاء يوم السبت",
    "sunday":    "دعاء يوم الأحد",
    "monday":    "دعاء يوم الاثنين",
    "tuesday":   "دعاء يوم الثلاثاء",
    "wednesday": "دعاء يوم الأربعاء",
    "thursday":  "دعاء يوم الخميس",
    "friday":    "دعاء يوم الجمعة",
}

weekly_list = []
weekly_data = load_json("data/raw/events/ادعية-ايام-الاسبوع.json")
if weekly_data and "أدعية_أيام_الأسبوع" in weekly_data:
    days = weekly_data["أدعية_أيام_الأسبوع"]
    wd_counter = 1
    for ar_key, en_day in day_map.items():
        if ar_key in days:
            entry = days[ar_key]
            text = entry.get("النص", "")
            weekly_list.append({
                "id": f"WD{wd_counter:03d}",
                "weekday": en_day,
                "title": day_title_map[en_day],
                "text": text,
                "source": "مفاتيح الجنان",
            })
            wd_counter += 1

report["weekly_duas_count"] = len(weekly_list)
save_json("data/normalized/event_content/weekly_duas.json", weekly_list)
print(f"  ✅ weekly_duas.json — {len(weekly_list)} دعاء أسبوعي")


# ─────────────────────────────────────────────
# STEP 7: NORMALIZED — prayer taqibat
# ─────────────────────────────────────────────
print("\n📖 Building prayer taqibat files ...")

taqibat_data = load_json("data/raw/taqibat/تعقيبات-الصلاة.json")
general_data = load_json("data/raw/taqibat/تعقيبات-الصلاة-العامة.json")

prayer_map = {
    "صلاة_الصبح":   ("fajr",    "الفجر"),
    "صلاة_الظهر":   ("dhuhr",   "الظهر"),
    "صلاة_العصر":   ("dhuhr",   "العصر"),   # merged into dhuhr
    "صلاة_المغرب":  ("maghrib", "المغرب"),
    "صلاة_العشاء":  ("isha",    "العشاء"),
}

prayer_buckets = {"fajr": [], "dhuhr": [], "maghrib": [], "isha": []}
t_counters = {"fajr": 1, "dhuhr": 1, "maghrib": 1, "isha": 1}
prefix_map = {"fajr": "F", "dhuhr": "D", "maghrib": "M", "isha": "I"}

def collect_texts_from_section(section):
    """Recursively collect all text/dhikr/dua strings from a section dict or list."""
    texts = []
    if isinstance(section, str):
        if len(section) > 10:
            texts.append(section)
    elif isinstance(section, list):
        for item in section:
            texts.extend(collect_texts_from_section(item))
    elif isinstance(section, dict):
        for k, v in section.items():
            if k in ("الذكر", "النص", "التعقيب_الأول", "دعاء_عام",
                     "التعقيب_بعد_تسبيح_الزهراء", "التعقيب_الأول",
                     "الدعاء_الأول", "الدعاء_الثاني", "القنوت"):
                if isinstance(v, str) and len(v) > 10:
                    texts.append(v)
            elif k in ("أذكار_مكررة", "أذكار_مأثورة_خاصة", "الأدعية_المتصلة",
                       "التعقيب_بعد_النافلة", "أذكار_مكررة"):
                texts.extend(collect_texts_from_section(v))
            elif isinstance(v, (dict, list)):
                texts.extend(collect_texts_from_section(v))
    return texts

def get_source_from_section(section):
    if isinstance(section, dict):
        return section.get("المصدر", None)
    return None

# Process per-prayer taqibat
if taqibat_data and "تعقيبات_الصلوات" in taqibat_data:
    prayers = taqibat_data["تعقيبات_الصلوات"]
    for ar_prayer, (en_prayer, ar_name) in prayer_map.items():
        if ar_prayer not in prayers:
            continue
        section = prayers[ar_prayer]
        # Collect all texts
        for k, v in section.items():
            texts = collect_texts_from_section(v) if not isinstance(v, str) else [v]
            # also handle string values directly
            if isinstance(v, str) and len(v) > 10:
                texts = [v]
            source = get_source_from_section(v) if isinstance(v, dict) else None
            for text in texts:
                if not text or len(text) < 10:
                    continue
                bucket = prayer_buckets[en_prayer]
                ctr = t_counters[en_prayer]
                pfx = prefix_map[en_prayer]
                bucket.append({
                    "id": f"{pfx}{ctr:03d}",
                    "category": "taqibat",
                    "prayer": en_prayer,
                    "title": f"تعقيب {ar_name}",
                    "text": text,
                    "source": source or "مفاتيح الجنان",
                    "delay_minutes": 3,
                    "priority": ctr,
                })
                t_counters[en_prayer] += 1

# Add general taqibat to all prayers
if general_data and "التعقيبات_العامة_للصلوات" in general_data:
    general_section = general_data["التعقيبات_العامة_للصلوات"]
    general_texts = []
    for section_key, section_val in general_section.items():
        src = None
        if isinstance(section_val, list):
            for item in section_val:
                if isinstance(item, dict):
                    t = item.get("الذكر") or item.get("الفعل") or item.get("القراءة")
                    s = item.get("المصدر", None)
                    if t and len(t) > 10:
                        general_texts.append((t, s or "مصباح المتهجد"))
        elif isinstance(section_val, dict):
            t = section_val.get("الذكر") or section_val.get("الفعل") or section_val.get("القراءة")
            s = section_val.get("المصدر", None)
            if t and len(t) > 10:
                general_texts.append((t, s or section_key))
        elif isinstance(section_val, str) and len(section_val) > 10:
            general_texts.append((section_val, section_key))

    for en_prayer in prayer_buckets:
        pfx = prefix_map[en_prayer]
        for text, src in general_texts:
            ctr = t_counters[en_prayer]
            prayer_buckets[en_prayer].append({
                "id": f"{pfx}{ctr:03d}",
                "category": "taqibat",
                "prayer": en_prayer,
                "title": "تعقيب عام",
                "text": text,
                "source": src,
                "delay_minutes": 5,
                "priority": ctr,
            })
            t_counters[en_prayer] += 1

total_taqibat = 0
for en_prayer, items in prayer_buckets.items():
    save_json(f"data/normalized/prayer_content/{en_prayer}.json", items)
    total_taqibat += len(items)
    print(f"  ✅ {en_prayer}.json — {len(items)} تعقيب")

report["taqibat_count"] = total_taqibat


# ─────────────────────────────────────────────
# STEP 8: NORMALIZED — events.json
# ─────────────────────────────────────────────
print("\n📖 Building events.json ...")

events = [
    {"id": "EV001", "hijri_date": "01-01", "title": "رأس السنة الهجرية", "description": "مستهل محرم الحرام - بداية السنة الهجرية", "priority": 8, "pin_message": False},
    {"id": "EV002", "hijri_date": "10-01", "title": "يوم عاشوراء", "description": "ذكرى استشهاد الإمام الحسين عليه السلام في كربلاء", "priority": 10, "pin_message": True},
    {"id": "EV003", "hijri_date": "20-02", "title": "زيارة الأربعين", "description": "الذكرى الأربعينية لاستشهاد الإمام الحسين عليه السلام", "priority": 10, "pin_message": True},
    {"id": "EV004", "hijri_date": "28-02", "title": "وفاة الرسول الأكرم ﷺ", "description": "ذكرى وفاة النبي محمد صلى الله عليه وآله", "priority": 10, "pin_message": True},
    {"id": "EV005", "hijri_date": "30-02", "title": "شهادة الإمام الحسن العسكري", "description": "ذكرى استشهاد الإمام الحادي عشر عليه السلام", "priority": 9, "pin_message": True},
    {"id": "EV006", "hijri_date": "17-03", "title": "المولد النبوي الشريف", "description": "ذكرى ولادة النبي محمد صلى الله عليه وآله", "priority": 10, "pin_message": True},
    {"id": "EV007", "hijri_date": "13-01", "title": "ذكرى ولادة الإمام علي", "description": "ذكرى ولادة أمير المؤمنين علي بن أبي طالب عليه السلام", "priority": 9, "pin_message": True},
    {"id": "EV008", "hijri_date": "21-01", "title": "شهادة الإمام علي عليه السلام", "description": "ذكرى استشهاد أمير المؤمنين في ليلة الحادي والعشرين من رمضان", "priority": 10, "pin_message": True},
    {"id": "EV009", "hijri_date": "03-05", "title": "ذكرى ولادة السيدة فاطمة الزهراء", "description": "ذكرى ولادة سيدة نساء العالمين فاطمة الزهراء عليها السلام", "priority": 10, "pin_message": True},
    {"id": "EV010", "hijri_date": "13-07", "title": "ذكرى ولادة الإمام علي الهادي", "description": "ذكرى ولادة الإمام العاشر عليه السلام", "priority": 8, "pin_message": False},
    {"id": "EV011", "hijri_date": "15-08", "title": "ذكرى ولادة الإمام المهدي", "description": "ذكرى ولادة الإمام الثاني عشر صاحب الزمان عجل الله فرجه", "priority": 10, "pin_message": True},
    {"id": "EV012", "hijri_date": "18-12", "title": "عيد الغدير الأغر", "description": "ذكرى تنصيب الإمام علي خليفةً للمسلمين في غدير خم", "priority": 10, "pin_message": True},
    {"id": "EV013", "hijri_date": "25-12", "title": "ذكرى مولد الإمام الكاظم", "description": "ذكرى ولادة الإمام موسى الكاظم عليه السلام", "priority": 8, "pin_message": False},
    {"id": "EV014", "hijri_date": "01-09", "title": "بداية شهر رمضان المبارك", "description": "أول أيام شهر رمضان المبارك", "priority": 9, "pin_message": True},
    {"id": "EV015", "hijri_date": "19-09", "title": "ليلة القدر الأولى (19 رمضان)", "description": "إحياء ليلة التاسع عشر من رمضان", "priority": 9, "pin_message": True},
    {"id": "EV016", "hijri_date": "21-09", "title": "ليلة القدر الثانية (21 رمضان)", "description": "إحياء ليلة الحادي والعشرين من رمضان", "priority": 10, "pin_message": True},
    {"id": "EV017", "hijri_date": "23-09", "title": "ليلة القدر الثالثة (23 رمضان)", "description": "إحياء ليلة الثالث والعشرين من رمضان", "priority": 10, "pin_message": True},
    {"id": "EV018", "hijri_date": "01-10", "title": "عيد الفطر المبارك", "description": "أول أيام عيد الفطر المبارك", "priority": 10, "pin_message": True},
    {"id": "EV019", "hijri_date": "10-12", "title": "عيد الأضحى المبارك", "description": "يوم عيد الأضحى", "priority": 10, "pin_message": True},
]

report["events_count"] = len(events)
save_json("data/normalized/event_content/events.json", events)
print(f"  ✅ events.json — {len(events)} مناسبة")


# ─────────────────────────────────────────────
# STEP 9: bot_content index
# ─────────────────────────────────────────────
bot_index = {
    "version": "1.0",
    "generated_at": datetime.now().isoformat(),
    "files": {
        "hadith":       "normalized/daily_content/hadith.json",
        "wisdom":       "normalized/daily_content/wisdom.json",
        "daily_dua":    "normalized/daily_content/daily_dua.json",
        "munajat":      "normalized/daily_content/munajat.json",
        "weekly_duas":  "normalized/event_content/weekly_duas.json",
        "events":       "normalized/event_content/events.json",
        "fajr":         "normalized/prayer_content/fajr.json",
        "dhuhr":        "normalized/prayer_content/dhuhr.json",
        "maghrib":      "normalized/prayer_content/maghrib.json",
        "isha":         "normalized/prayer_content/isha.json",
    },
    "counts": {
        "hadith":      report["hadith_count"],
        "wisdom":      report["wisdom_count"],
        "duas":        report["dua_count"],
        "munajat":     report["munajat_count"],
        "weekly_duas": report["weekly_duas_count"],
        "taqibat":     report["taqibat_count"],
        "events":      report["events_count"],
    }
}
save_json("data/normalized/bot_content/index.json", bot_index)
print("\n  ✅ bot_content/index.json")


# ─────────────────────────────────────────────
# STEP 10: NORMALIZATION REPORT
# ─────────────────────────────────────────────
report_md = f"""# NORMALIZATION REPORT
**تاريخ التنفيذ:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 📊 إحصاءات المحتوى

| النوع | العدد |
|-------|-------|
| الأحاديث (`hadith.json`) | **{report['hadith_count']}** |
| حكم الإمام علي (`wisdom.json`) | **{report['wisdom_count']}** |
| الأدعية والزيارات (`daily_dua.json`) | **{report['dua_count']}** |
| منها الزيارات | **{report['zyarat_count']}** |
| المناجيات (`munajat.json`) | **{report['munajat_count']}** |
| أدعية الأسبوع (`weekly_duas.json`) | **{report['weekly_duas_count']}** |
| تعقيبات الصلاة (مجموع) | **{report['taqibat_count']}** |
| المناسبات (`events.json`) | **{report['events_count']}** |

---

## 📁 الملفات المعالجة ({len(report['processed_files'])})

{chr(10).join(f'- ✅ `{f}`' for f in report['processed_files'])}

---

## ❌ الملفات التي تعذر تحليلها ({len(report['failed_files'])})

{chr(10).join(f"- ⚠️ `{f['file']}` — {f['error']}" for f in report['failed_files']) or '- لا يوجد'}

---

## ⚠️ ملاحظات وتحذيرات

{chr(10).join(f'- {i}' for i in report['issues']) or '- لا توجد مشاكل'}

---

## 🗂️ هيكل المجلدات الناتج

```
data/
├── raw/
│   ├── hadith/
│   │   ├── Mohammed(PBUH).json          ({report['hadith_count']} حديث قبل الدمج)
│   │   ├── Fatima-Zahra(as).json
│   │   ├── Imam_AL-Baqer(as).json
│   │   ├── Imam_AL-Mahdi(as).json
│   │   └── Imam_Ali(as).json            ({report['wisdom_count']} حكمة)
│   ├── duas/
│   │   ├── duaas.json
│   │   └── zyarat.json
│   ├── taqibat/
│   │   ├── تعقيبات-الصلاة.json
│   │   └── تعقيبات-الصلاة-العامة.json
│   ├── munajat/
│   │   └── munajat.json
│   ├── events/
│   │   └── ادعية-ايام-الاسبوع.json
│   └── tafsir/                          (فارغ - جاهز للتوسع)
│
├── normalized/
│   ├── daily_content/
│   │   ├── hadith.json                  ({report['hadith_count']} حديث موحّد)
│   │   ├── wisdom.json                  ({report['wisdom_count']} حكمة)
│   │   ├── daily_dua.json               ({report['dua_count']} دعاء وزيارة)
│   │   └── munajat.json                 ({report['munajat_count']} مناجاة)
│   ├── prayer_content/
│   │   ├── fajr.json
│   │   ├── dhuhr.json                   (يشمل العصر)
│   │   ├── maghrib.json
│   │   └── isha.json
│   ├── event_content/
│   │   ├── weekly_duas.json             ({report['weekly_duas_count']} أيام)
│   │   └── events.json                  ({report['events_count']} مناسبة)
│   └── bot_content/
│       └── index.json                   (فهرس لجميع الملفات)
│
└── runtime/                             (فارغ - للبوت)
```

---

## 🔖 Schema الموحّدة

### Hadith
```json
{{
  "id": "H000001",
  "category": "hadith",
  "text": "نص الحديث",
  "author": "النبي محمد ﷺ",
  "source": "بحار الأنوار",
  "chapter": null,
  "tags": [],
  "priority": 1,
  "sent": false
}}
```

### Wisdom
```json
{{
  "id": "W000001",
  "category": "wisdom",
  "text": "النص",
  "author": "الإمام علي بن أبي طالب عليه السلام",
  "source": "غرر الحكم",
  "tags": [],
  "sent": false
}}
```

### Dua
```json
{{
  "id": "D000001",
  "category": "dua",
  "title": "دعاء كميل",
  "text": "النص الكامل",
  "source": "مفاتيح الجنان",
  "tags": [],
  "recommended_time": null,
  "sent": false
}}
```

### Taqibat
```json
{{
  "id": "F001",
  "category": "taqibat",
  "prayer": "fajr",
  "title": "تعقيب الفجر",
  "text": "النص",
  "source": "المصدر",
  "delay_minutes": 3,
  "priority": 1
}}
```

---
*تم الإنشاء تلقائياً بواسطة normalize.py*
"""

with open("NORMALIZATION_REPORT.md", "w", encoding="utf-8") as f:
    f.write(report_md)

print("\n" + "="*60)
print("✅ NORMALIZATION COMPLETE")
print("="*60)
print(f"  📖 الأحاديث:        {report['hadith_count']}")
print(f"  💎 حكم الإمام علي: {report['wisdom_count']}")
print(f"  🤲 الأدعية:         {report['dua_count']}")
print(f"  🌙 المناجيات:       {report['munajat_count']}")
print(f"  📅 أدعية الأسبوع:   {report['weekly_duas_count']}")
print(f"  🕌 التعقيبات:       {report['taqibat_count']}")
print(f"  📆 المناسبات:       {report['events_count']}")
print(f"  ⚠️  تحذيرات:        {len(report['issues'])}")
print("="*60)
print("📄 NORMALIZATION_REPORT.md — تم إنشاء التقرير")
