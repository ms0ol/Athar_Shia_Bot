#!/usr/bin/env python3
"""
Improvement script for normalized Islamic content files.
Tasks:
  1. Split wisdom.json → short.json / deep.json / featured.json (best 1000)
  2. Separate daily_dua.json → daily_dua.json (duas) + ziyarat.json (ziyarat)
  3. Add metadata to all files: content_length, recommended_time, is_featured, send_score
  4. Generate QUALITY_REPORT.md
"""

import json
import os
import re
import unicodedata
from datetime import datetime
from collections import Counter

# ─── Paths ────────────────────────────────────────────────────────────────────
DAILY = "data/normalized/daily_content"
PRAYER = "data/normalized/prayer_content"
EVENT  = "data/normalized/event_content"

# ─── Helpers ──────────────────────────────────────────────────────────────────

def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  ✅ Saved {path}  ({len(data) if isinstance(data, list) else '?'} items)")

def strip_diacritics(text):
    """Remove Arabic diacritics for duplicate detection."""
    return re.sub(r'[\u064b-\u065f\u0670]', '', text)

def normalize_spaces(text):
    return re.sub(r'\s+', ' ', text).strip()

# ─── Scoring ──────────────────────────────────────────────────────────────────

MORNING_KEYWORDS = ['صباح', 'فجر', 'الصبح', 'طلوع', 'النهار', 'يوم']
EVENING_KEYWORDS = ['مساء', 'ليل', 'العشاء', 'المغرب', 'الليل', 'عشية']
NIGHT_KEYWORDS   = ['ليلة', 'منتصف الليل', 'التهجد', 'سحر', 'قيام']

def infer_recommended_time(item):
    """Infer best time to send this content."""
    category = item.get('category', '')
    prayer   = item.get('prayer', '')
    title    = (item.get('title', '') + ' ' + item.get('name', '')).lower()
    text_snip = item.get('text', '')[:200].lower()
    combined = title + ' ' + text_snip

    if category == 'taqibat' or prayer:
        mapping = {'fajr': 'after_fajr', 'dhuhr': 'after_dhuhr',
                   'maghrib': 'after_maghrib', 'isha': 'after_isha'}
        return mapping.get(prayer, 'after_prayer')

    if category == 'munajat':
        return 'night'

    if 'عاشوراء' in combined or 'أربعين' in combined:
        return 'any'

    if any(k in combined for k in MORNING_KEYWORDS):
        return 'morning'
    if any(k in combined for k in EVENING_KEYWORDS):
        return 'evening'
    if any(k in combined for k in NIGHT_KEYWORDS):
        return 'night'

    return 'any'

def wisdom_send_score(text):
    """
    Score a wisdom for daily sending suitability (0.0–10.0).
    Criteria:
      - Length sweet spot 40–180 chars → high score
      - Too short (<20) or too long (>400) → penalise
      - Starts with meaningful Arabic letter → bonus
      - Contains diacritics (authentic) → bonus
      - Pure punctuation/numbers → penalise
    """
    length = len(text)

    # Length score (0–5)
    if 40 <= length <= 180:
        length_score = 5.0
    elif 20 <= length < 40:
        length_score = 3.5
    elif 180 < length <= 300:
        length_score = 3.0
    elif length > 300:
        length_score = 1.5
    else:  # <20
        length_score = 0.5

    # Diacritics bonus (0–2): authentic text usually has tashkeel
    diacritics_count = len(re.findall(r'[\u064b-\u065f\u0670]', text))
    diacritics_score = min(2.0, diacritics_count * 0.15)

    # Starts with Arabic letter (0–1)
    start_score = 1.0 if text and '\u0600' <= text[0] <= '\u06ff' else 0.0

    # Arabic word density (0–2): ratio of Arabic chars to total
    arabic_chars = len(re.findall(r'[\u0600-\u06ff]', text))
    arabic_ratio = arabic_chars / max(length, 1)
    arabic_score = arabic_ratio * 2.0

    total = length_score + diacritics_score + start_score + arabic_score
    return round(min(10.0, total), 2)

def hadith_send_score(item):
    text = item['text'] if isinstance(item, dict) else item
    length = len(text)
    if 60 <= length <= 300:
        length_score = 5.0
    elif 30 <= length < 60:
        length_score = 3.0
    elif 300 < length <= 500:
        length_score = 3.0
    else:
        length_score = 1.0

    arabic_chars = len(re.findall(r'[\u0600-\u06ff]', text))
    arabic_score = min(2.0, (arabic_chars / max(len(text), 1)) * 2.0)

    source_bonus = 1.0 if 'بحار الأنوار' in text else 0.5

    return round(min(10.0, length_score + arabic_score + source_bonus), 2)

def dua_send_score(item):
    text = item.get('text', '')
    title = item.get('title', item.get('name', ''))
    length = len(text)

    base = 5.0
    if length > 5000:
        base = 3.0
    elif length > 2000:
        base = 4.0

    known_duas = [
        'دعاء كميل', 'دعاء العهد', 'دعاء الندبة', 'حديث الكساء',
        'دعاء أبي حمزة', 'دعاء الجوشن', 'دعاء التوسل',
        'الزيارة الجامعة', 'زيارة عاشوراء', 'زيارة الأربعين',
        'زيارة آل ياسين', 'زيارة وارث',
    ]
    featured_bonus = 1.5 if any(k in title for k in known_duas) else 0.0
    return round(min(10.0, base + featured_bonus), 2)

def munajat_send_score(item):
    text = item['text'] if isinstance(item, dict) else item
    length = len(text)
    if 500 <= length <= 3000:
        return 7.5
    elif length < 500:
        return 5.0
    return 6.0

def taqibat_send_score(item):
    priority = item.get('priority', 5) if isinstance(item, dict) else 5
    return round(min(10.0, 10.0 - priority * 0.5), 2)

# ─── Featured wisdom selection ────────────────────────────────────────────────

def select_featured_wisdom(items, n=1000):
    """
    Select top N wisdoms for daily sending.
    Strategy: score each, remove near-duplicates, pick top N.
    """
    # Score all
    for item in items:
        item['_score'] = wisdom_send_score(item['text'])

    # Sort by score desc
    items_sorted = sorted(items, key=lambda x: x['_score'], reverse=True)

    # Deduplicate by normalised text prefix (first 30 stripped chars)
    seen = set()
    featured = []
    for item in items_sorted:
        key = strip_diacritics(item['text'])[:30].strip()
        if key not in seen:
            seen.add(key)
            featured.append(item)
        if len(featured) >= n:
            break

    # Remove temporary score key
    for item in featured:
        item.pop('_score', None)
    for item in items_sorted:
        item.pop('_score', None)

    return featured

# ─── Metadata enrichment ──────────────────────────────────────────────────────

def enrich(item, score_fn=None, featured_ids=None):
    """Add/update metadata fields to item in-place."""
    text = item.get('text', '')
    item['content_length']   = len(text)
    item['recommended_time'] = infer_recommended_time(item)
    item['is_featured']      = (featured_ids is not None and item.get('id') in featured_ids)
    item['send_score']       = score_fn(item) if score_fn else 5.0
    return item

# ═══════════════════════════════════════════════════════════════════════════════
# TASK 1 — Split wisdom.json
# ═══════════════════════════════════════════════════════════════════════════════

print("\n📚 Processing wisdom.json …")
wisdom_all = load(f"{DAILY}/wisdom.json")

# Select featured first (before enrichment so we can record IDs)
featured_wisdom = select_featured_wisdom([dict(x) for x in wisdom_all], n=1000)
featured_ids = {x['id'] for x in featured_wisdom}

SHORT_THRESHOLD = 80   # chars — compact, pithy maxims
DEEP_THRESHOLD  = 80   # chars and above → deep

short_items    = []
deep_items     = []

for item in wisdom_all:
    enriched = enrich(
        dict(item),
        score_fn=lambda i: wisdom_send_score(i['text']),
        featured_ids=featured_ids
    )
    if len(item['text']) < SHORT_THRESHOLD:
        short_items.append(enriched)
    else:
        deep_items.append(enriched)

# Enrich featured separately
for item in featured_wisdom:
    enrich(item, score_fn=lambda i: wisdom_send_score(i['text']), featured_ids=featured_ids)
    item['is_featured'] = True  # ensure flag is set

save(f"{DAILY}/wisdom_short.json",    short_items)
save(f"{DAILY}/wisdom_deep.json",     deep_items)
save(f"{DAILY}/wisdom_featured.json", featured_wisdom)

# Keep original wisdom.json but enrich it too
enriched_all_wisdom = short_items + deep_items
enriched_all_wisdom.sort(key=lambda x: int(x['id'].replace('W', '') or 0))
save(f"{DAILY}/wisdom.json", enriched_all_wisdom)

print(f"  → short: {len(short_items)}, deep: {len(deep_items)}, featured: {len(featured_wisdom)}")

# ═══════════════════════════════════════════════════════════════════════════════
# TASK 2 — Separate daily_dua.json → daily_dua.json + ziyarat.json
# ═══════════════════════════════════════════════════════════════════════════════

print("\n🕌 Processing daily_dua.json …")
dua_all = load(f"{DAILY}/daily_dua.json")

duas    = []
ziyarat = []

for item in dua_all:
    enriched = enrich(
        dict(item),
        score_fn=dua_send_score,
        featured_ids=None
    )
    # Mark known featured duas
    known_featured_duas = [
        'دعاء كميل', 'دعاء العهد', 'دعاء الندبة', 'حديث الكساء',
        'دعاء أبي حمزة', 'دعاء الجوشن'
    ]
    enriched['is_featured'] = any(k in enriched.get('title', '') for k in known_featured_duas)

    if item.get('category') == 'zyarat':
        enriched['category'] = 'ziyarat'   # normalize spelling
        ziyarat.append(enriched)
    else:
        duas.append(enriched)

save(f"{DAILY}/daily_dua.json", duas)
save(f"{DAILY}/ziyarat.json",   ziyarat)
print(f"  → duas: {len(duas)}, ziyarat: {len(ziyarat)}")

# ═══════════════════════════════════════════════════════════════════════════════
# TASK 3 — Enrich remaining files with metadata
# ═══════════════════════════════════════════════════════════════════════════════

print("\n📿 Enriching hadith.json …")
hadith_all = load(f"{DAILY}/hadith.json")
# Featured hadiths: score >= 7.0
enriched_hadith = []
for item in hadith_all:
    score = hadith_send_score(item['text'])
    enriched = enrich(dict(item), score_fn=hadith_send_score, featured_ids=None)
    enriched['is_featured'] = score >= 7.5
    enriched_hadith.append(enriched)
save(f"{DAILY}/hadith.json", enriched_hadith)

print("📿 Enriching munajat.json …")
munajat_all = load(f"{DAILY}/munajat.json")
enriched_munajat = []
for item in munajat_all:
    enriched = enrich(dict(item), score_fn=munajat_send_score, featured_ids=None)
    enriched['is_featured'] = True   # all 15 munajat are featured
    enriched_munajat.append(enriched)
save(f"{DAILY}/munajat.json", enriched_munajat)

print("🕋 Enriching prayer_content files …")
for prayer in ['fajr', 'dhuhr', 'maghrib', 'isha']:
    path = f"{PRAYER}/{prayer}.json"
    items = load(path)
    enriched = []
    for item in items:
        e = enrich(dict(item), score_fn=taqibat_send_score, featured_ids=None)
        e['is_featured'] = e.get('priority', 10) <= 3
        enriched.append(e)
    save(path, enriched)

print("📅 Enriching weekly_duas.json …")
weekly = load(f"{EVENT}/weekly_duas.json")
enriched_weekly = []
for item in weekly:
    e = enrich(dict(item), score_fn=dua_send_score, featured_ids=None)
    e['is_featured'] = True   # all 7 are featured (weekly schedule)
    enriched_weekly.append(e)
save(f"{EVENT}/weekly_duas.json", enriched_weekly)

print("📅 Enriching events.json …")
events = load(f"{EVENT}/events.json")
enriched_events = []
for item in events:
    e = dict(item)
    e['content_length']   = len(e.get('title', '') + ' ' + e.get('description', ''))
    e['recommended_time'] = 'event_day'
    e['is_featured']      = e.get('priority', 5) <= 3
    e['send_score']       = round(10.0 - e.get('priority', 5) * 0.5, 2)
    enriched_events.append(e)
save(f"{EVENT}/events.json", enriched_events)


# ═══════════════════════════════════════════════════════════════════════════════
# TASK 4 — QUALITY_REPORT.md
# ═══════════════════════════════════════════════════════════════════════════════

print("\n📊 Generating QUALITY_REPORT.md …")

def detect_duplicates(items, key='text', prefix_len=40):
    """Return list of (item1, item2) near-duplicate pairs."""
    seen = {}
    dupes = []
    for item in items:
        norm = strip_diacritics(item.get(key, ''))[:prefix_len].strip()
        if norm in seen:
            dupes.append((seen[norm], item))
        else:
            seen[norm] = item
    return dupes

def quality_stats(items, label, text_key='text', short_thresh=20, long_thresh=1000):
    texts = [item.get(text_key, '') for item in items]
    lengths = [len(t) for t in texts]
    n = len(lengths)
    if n == 0:
        return f"### {label}\nNo items.\n"

    too_short = [items[i] for i, l in enumerate(lengths) if l < short_thresh]
    too_long  = [items[i] for i, l in enumerate(lengths) if l > long_thresh]
    dupes     = detect_duplicates(items, key=text_key)

    avg = sum(lengths) / n
    sorted_l = sorted(lengths)
    median = sorted_l[n // 2]

    report = f"""### {label}

| المقياس | القيمة |
|---------|--------|
| المجموع | {n:,} |
| متوسط الطول | {avg:.0f} حرف |
| وسيط الطول | {median} حرف |
| أقصر نص | {sorted_l[0]} حرف |
| أطول نص | {sorted_l[-1]} حرف |
| نصوص قصيرة جداً (<{short_thresh} حرف) | {len(too_short)} |
| نصوص طويلة جداً (>{long_thresh} حرف) | {len(too_long)} |
| تكرارات محتملة | {len(dupes)} |

"""
    if too_short:
        report += f"**أمثلة على النصوص القصيرة جداً:**\n"
        for item in too_short[:5]:
            t = item.get(text_key, '')
            report += f'- `{t[:80]}`\n'
        report += "\n"

    if too_long:
        report += f"**أمثلة على النصوص الطويلة جداً (>1000 حرف):**\n"
        for item in too_long[:3]:
            t = item.get('title', item.get('id', '?'))
            report += f'- {t} ({len(item.get(text_key,""))} حرف)\n'
        report += "\n"

    if dupes:
        report += f"**أمثلة على التكرارات المحتملة ({len(dupes)} زوج):**\n"
        for a, b in dupes[:5]:
            report += f'- `{a.get("id","?")}` ↔ `{b.get("id","?")}` — "{a.get(text_key,"")[:60]}…"\n'
        report += "\n"

    return report

# Reload enriched files
w_short    = load(f"{DAILY}/wisdom_short.json")
w_deep     = load(f"{DAILY}/wisdom_deep.json")
w_feat     = load(f"{DAILY}/wisdom_featured.json")
w_all      = load(f"{DAILY}/wisdom.json")
h_all      = load(f"{DAILY}/hadith.json")
d_all      = load(f"{DAILY}/daily_dua.json")
z_all      = load(f"{DAILY}/ziyarat.json")
m_all      = load(f"{DAILY}/munajat.json")
fajr_t     = load(f"{PRAYER}/fajr.json")
dhuhr_t    = load(f"{PRAYER}/dhuhr.json")
maghrib_t  = load(f"{PRAYER}/maghrib.json")
isha_t     = load(f"{PRAYER}/isha.json")
weekly_d   = load(f"{EVENT}/weekly_duas.json")
events_d   = load(f"{EVENT}/events.json")

# Daily content quality
w_scores   = [x.get('send_score', 0) for x in w_feat]
h_scores   = [x.get('send_score', 0) for x in h_all]
d_scores   = [x.get('send_score', 0) for x in d_all + z_all]
avg_w = sum(w_scores)/len(w_scores) if w_scores else 0
avg_h = sum(h_scores)/len(h_scores) if h_scores else 0
avg_d = sum(d_scores)/len(d_scores) if d_scores else 0

featured_hadith_count = sum(1 for x in h_all if x.get('is_featured'))
featured_wisdom_count = len(w_feat)

# Score distribution for wisdom featured
score_buckets = Counter()
for s in w_scores:
    if s >= 8:
        score_buckets['≥ 8.0 (ممتاز)'] += 1
    elif s >= 6:
        score_buckets['6–8 (جيد)'] += 1
    elif s >= 4:
        score_buckets['4–6 (مقبول)'] += 1
    else:
        score_buckets['< 4 (ضعيف)'] += 1

score_dist_str = "\n".join(f"| {k} | {v} |" for k, v in score_buckets.most_common())

now = datetime.now().strftime("%Y-%m-%d %H:%M")

report_lines = f"""# QUALITY REPORT — تقرير جودة المحتوى

**تاريخ التوليد:** {now}

---

## 📊 ملخص تنفيذي

| الملف | العناصر | متوسط send_score | المميزة |
|-------|---------|-----------------|---------|
| `wisdom_featured.json` | {len(w_feat):,} | {avg_w:.2f} | {featured_wisdom_count:,} |
| `wisdom_short.json` | {len(w_short):,} | — | — |
| `wisdom_deep.json` | {len(w_deep):,} | — | — |
| `hadith.json` | {len(h_all):,} | {avg_h:.2f} | {featured_hadith_count} |
| `daily_dua.json` | {len(d_all)} | — | {sum(1 for x in d_all if x.get('is_featured'))} |
| `ziyarat.json` | {len(z_all)} | — | {sum(1 for x in z_all if x.get('is_featured'))} |
| `munajat.json` | {len(m_all)} | — | {len(m_all)} |
| `fajr.json` | {len(fajr_t)} | — | {sum(1 for x in fajr_t if x.get('is_featured'))} |
| `dhuhr.json` | {len(dhuhr_t)} | — | {sum(1 for x in dhuhr_t if x.get('is_featured'))} |
| `maghrib.json` | {len(maghrib_t)} | — | {sum(1 for x in maghrib_t if x.get('is_featured'))} |
| `isha.json` | {len(isha_t)} | — | {sum(1 for x in isha_t if x.get('is_featured'))} |
| `weekly_duas.json` | {len(weekly_d)} | — | {len(weekly_d)} |
| `events.json` | {len(events_d)} | — | {sum(1 for x in events_d if x.get('is_featured'))} |

---

## 🌟 جودة wisdom_featured.json (أفضل 1000 حكمة)

### توزيع درجات send_score

| الفئة | العدد |
|-------|-------|
{score_dist_str}

### منهجية الاختيار
- الطول المثالي: **40–180 حرف** → أعلى نقاط
- التشكيل (الحركات): مؤشر على أصالة النص → نقاط إضافية
- إزالة التكرارات: بمقارنة أول 30 حرف (بعد حذف التشكيل)
- الفئة `short.json` (<80 حرف): **{len(w_short):,}** حكمة
- الفئة `deep.json` (≥80 حرف): **{len(w_deep):,}** حكمة

---

## 🔍 تفاصيل الجودة لكل ملف

{quality_stats(w_all, "wisdom.json (الكل)", short_thresh=10, long_thresh=400)}
{quality_stats(w_feat, "wisdom_featured.json", short_thresh=30, long_thresh=300)}
{quality_stats(h_all, "hadith.json", short_thresh=40, long_thresh=500)}
{quality_stats(d_all, "daily_dua.json", text_key='text', short_thresh=200, long_thresh=15000)}
{quality_stats(z_all, "ziyarat.json", text_key='text', short_thresh=200, long_thresh=15000)}
{quality_stats(m_all, "munajat.json", text_key='text', short_thresh=200, long_thresh=10000)}

---

## ⚠️ المشاكل المكتشفة

### wisdom.json
| المشكلة | التفصيل |
|---------|---------|
| نصوص قصيرة جداً (<10 حرف) | {sum(1 for x in w_all if len(x.get('text',''))<10)} عنصر |
| نصوص طويلة جداً (>400 حرف) | {sum(1 for x in w_all if len(x.get('text',''))>400)} عنصر |
| نصوص فارغة | {sum(1 for x in w_all if not x.get('text','').strip())} عنصر |

### hadith.json
| المشكلة | التفصيل |
|---------|---------|
| نصوص قصيرة جداً (<40 حرف) | {sum(1 for x in h_all if len(x.get('text',''))<40)} عنصر |
| نصوص طويلة جداً (>500 حرف) | {sum(1 for x in h_all if len(x.get('text',''))>500)} عنصر |
| مصدر مجهول (null) | {sum(1 for x in h_all if not x.get('source') or x.get('source')=='null')} عنصر |

### daily_dua.json + ziyarat.json
| المشكلة | التفصيل |
|---------|---------|
| أدعية طويلة جداً (>8000 حرف) | {sum(1 for x in d_all+z_all if len(x.get('text',''))>8000)} عنصر |
| أدعية بلا عنوان | {sum(1 for x in d_all+z_all if not x.get('title','').strip())} عنصر |

---

## 📅 جودة المحتوى اليومي

### التوزيع الزمني الموصى به

| الوقت | الملف | العناصر |
|-------|-------|---------|
| صباح (`morning`) | hadith + wisdom | متجدد يومياً من {len(h_all):,}+ عنصر |
| بعد الفجر | `fajr.json` | {len(fajr_t)} تعقيب |
| بعد الظهر | `dhuhr.json` | {len(dhuhr_t)} تعقيب |
| بعد المغرب | `maghrib.json` | {len(maghrib_t)} تعقيب |
| بعد العشاء | `isha.json` | {len(isha_t)} تعقيب |
| ليلي (`night`) | munajat | {len(m_all)} مناجاة |
| أسبوعي | `weekly_duas.json` | {len(weekly_d)} أدعية |
| مناسبات | `events.json` | {len(events_d)} مناسبة |

### سعة المحتوى المميّز للإرسال اليومي

| النوع | العناصر المميزة | يكفي لـ |
|-------|----------------|---------|
| حِكَم (featured) | {len(w_feat):,} | {len(w_feat)//365} سنة+ |
| أحاديث (featured) | {featured_hadith_count} | {featured_hadith_count//365} سنة+ |
| أدعية | {len(d_all)} | تدوير شهري |
| زيارات | {len(z_all)} | تدوير أسبوعي |
| مناجيات | {len(m_all)} | تدوير أسبوعين |

---

## 🗂️ هيكل الملفات بعد التحسين

```
data/normalized/
├── daily_content/
│   ├── wisdom.json            ({len(w_all):,} حكمة — مُثرى بالـ metadata)
│   ├── wisdom_short.json      ({len(w_short):,} حكمة — طول < 80 حرف)
│   ├── wisdom_deep.json       ({len(w_deep):,} حكمة — طول ≥ 80 حرف)
│   ├── wisdom_featured.json   ({len(w_feat):,} حكمة — أفضل 1000 للإرسال اليومي ★)
│   ├── hadith.json            ({len(h_all):,} حديث — مُثرى)
│   ├── daily_dua.json         ({len(d_all)} دعاء — مُثرى)
│   ├── ziyarat.json           ({len(z_all)} زيارة — مُفصولة ★ جديد)
│   └── munajat.json           ({len(m_all)} مناجاة — مُثرى)
├── prayer_content/
│   ├── fajr.json              ({len(fajr_t)} تعقيب)
│   ├── dhuhr.json             ({len(dhuhr_t)} تعقيب)
│   ├── maghrib.json           ({len(maghrib_t)} تعقيب)
│   └── isha.json              ({len(isha_t)} تعقيب)
└── event_content/
    ├── weekly_duas.json       ({len(weekly_d)} دعاء أسبوعي)
    └── events.json            ({len(events_d)} مناسبة)
```

---

## ✅ الحقول المضافة لكل عنصر

| الحقل | النوع | الوصف |
|-------|-------|-------|
| `content_length` | `int` | عدد الأحرف في النص |
| `recommended_time` | `str` | الوقت الموصى به للإرسال |
| `is_featured` | `bool` | هل العنصر مرشّح للإرسال اليومي؟ |
| `send_score` | `float` | درجة الجودة للإرسال (0.0–10.0) |

### قيم `recommended_time` المستخدمة
| القيمة | المعنى |
|--------|--------|
| `any` | مناسب في أي وقت |
| `morning` | صباح |
| `evening` | مساء |
| `night` | ليلي |
| `after_fajr` | بعد صلاة الفجر |
| `after_dhuhr` | بعد صلاة الظهر |
| `after_maghrib` | بعد صلاة المغرب |
| `after_isha` | بعد صلاة العشاء |
| `after_prayer` | بعد الصلاة (عام) |
| `event_day` | يوم المناسبة |

---

*تم التوليد تلقائياً بواسطة `improve_normalized.py`*
"""

with open("QUALITY_REPORT.md", "w", encoding="utf-8") as f:
    f.write(report_lines)
print("  ✅ Saved QUALITY_REPORT.md")

print("\n🎉 All improvements complete!")
