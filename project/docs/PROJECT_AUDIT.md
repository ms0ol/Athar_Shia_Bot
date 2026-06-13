# PROJECT_AUDIT.md — تقرير الفحص الأمني والتقني الشامل

**تاريخ الفحص:** يونيو 2026
**نطاق الفحص:** جميع ملفات Python (8 ملفات، ~1450 سطر)
**المنهجية:** مراجعة يدوية كاملة للكود سطراً بسطر

---

## ملخص تنفيذي

| المستوى | العدد |
|---------|-------|
| 🔴 خطر حرج (Critical) | 4 |
| 🟠 خطر عالي (High) | 6 |
| 🟡 تحذير (Medium) | 8 |
| 🔵 ملاحظة (Low/Info) | 7 |
| **الإجمالي** | **25** |

---

## 🔴 المستوى الحرج (Critical)

---

### C-01 — إرسال مزدوج للمناسبات في القناة

**الملف:** `scheduler.py` — السطور 197–208

**الكود المشكل:**
```python
if CHANNEL_ID:
    await _send_to_channel(_bot, full_text)          # ← إرسال أول
    if event.get("pin_message"):
        try:
            ...
            msg = await _bot.send_message(CHANNEL_ID, full_text, ...)  # ← إرسال ثانٍ!
            await _bot.pin_chat_message(...)
```

**المشكلة:** عند وجود مناسبة بها `pin_message=true`، يُرسَل النص مرتين للقناة — مرة عبر `_send_to_channel()` ومرة أخرى مباشرة. ثم يُثبَّت الإرسال الثاني بينما الأول يبقى بلا تثبيت.

**الإصلاح:**
```python
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
```

---

### C-02 — `event_service.py` يرمي استثناءً غير محمي عند غياب ملفات JSON

**الملف:** `event_service.py` — السطران 24–26 و 30–32

**الكود المشكل:**
```python
def _load_events() -> list:
    path = os.path.join(DATA_PATH, "event_content/events.json")
    with open(path, encoding="utf-8") as f:   # ← FileNotFoundError هنا!
        return json.load(f)
```

**المشكلة:** بخلاف `content_service.py` الذي يتحقق من وجود الملف ويُعيد قائمة فارغة، دالة `_load_events()` تفتح الملف مباشرة. إذا لم يوجد الملف، سيُرمى `FileNotFoundError` يصعد عبر:
- `/event` في handlers
- `check_daily_event()` في scheduler
- Callback `content:event`

هذا يُوقف استجابة البوت للمستخدم كاملاً ويطبع traceback في الـ logs.

**الإصلاح:**
```python
def _load_events() -> list:
    path = os.path.join(DATA_PATH, "event_content/events.json")
    if not os.path.exists(path):
        logger.warning("events.json not found at %s", path)
        return []
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.error("Failed to load events.json: %s", e)
        return []
```

---

### C-03 — لا يوجد Rate Limiting في الإرسال الجماعي

**الملفات:** `scheduler.py` (السطور 29–39، 57–65) + `admin.py` (السطور 154–165)

**الكود المشكل:**
```python
for uid in users:
    try:
        await bot.send_message(uid, part, ...)  # ← بلا delay بين المستخدمين
    except Exception:
        pass
```

**المشكلة:** تيليجرام يسمح بـ 30 رسالة/ثانية لمستخدمين مختلفين. البوت يرسل بالحد الأقصى لسرعة الإنترنت. مع أكثر من 30 مستخدم، ستُفعَّل `FloodWaitError` وقد يُحظر البوت لفترة تصل إلى 24 ساعة.

**الإصلاح:**
```python
import asyncio

for uid in users:
    try:
        await bot.send_message(uid, part, parse_mode="HTML")
        sent += 1
    except Exception as e:
        logger.debug("Failed to send to %d: %s", uid, e)
        failed += 1
    await asyncio.sleep(0.05)  # ← 20 رسالة/ثانية (آمن)
```

---

### C-04 — N+1 استعلام قاعدة بيانات في `_pick()`

**الملف:** `content_service.py` — السطور 58–77

**الكود المشكل:**
```python
async def _pick(items: list, category: str) -> Optional[dict]:
    for item in items:
        if not await _is_sent(item["id"], category):  # ← اتصال DB جديد لكل عنصر!
            unsent.append(item)
```

**المشكلة:** إذا كان الملف يحتوي 200 عنصر، يُفتح 200 اتصال SQLite منفصل في تسلسل. هذا بطيء جداً (~2-5 ثانية) ويُضغط على قاعدة البيانات.

**الإصلاح:** جلب كل IDs المُرسلة بـ استعلام واحد:
```python
async def _pick(items: list, category: str) -> Optional[dict]:
    if not items:
        return None
    
    # استعلام واحد بدلاً من N استعلامات
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT content_id FROM sent_content WHERE category=?", (category,)
        )
        sent_ids = {row[0] for row in await cur.fetchall()}
    
    unsent = [item for item in items if item["id"] not in sent_ids]
    if not unsent:
        await _reset_sent(category)
        unsent = items[:]
    
    featured = [i for i in unsent if i.get("is_featured")]
    pool = featured if featured else unsent
    pool.sort(key=lambda x: x.get("send_score", 0), reverse=True)
    top = pool[:max(1, len(pool) // 5)]
    chosen = random.choice(top)
    await _mark_sent(chosen["id"], category)
    return chosen
```

---

## 🟠 المستوى العالي (High)

---

### H-01 — `event_service` لا يُخزّن البيانات في Cache

**الملف:** `event_service.py` — السطران 23–32

**المشكلة:** كل استدعاء لـ `get_current_event()`، `get_upcoming_events()`، أو `get_today_dua()` يقرأ الملف من القرص من جديد. مع الإرسال المجدول وطلبات المستخدمين المتزامنة، هذا يعني I/O غير ضروري.

**الإصلاح:** إضافة cache مشابه لـ `content_service.py`:
```python
_events_cache: list | None = None
_weekly_duas_cache: list | None = None

def _load_events() -> list:
    global _events_cache
    if _events_cache is not None:
        return _events_cache
    # ... load from file ...
    _events_cache = data
    return data

def reload_events() -> None:
    global _events_cache, _weekly_duas_cache
    _events_cache = None
    _weekly_duas_cache = None
```

---

### H-02 — Race Condition في TOCTOU للأذان والتعقيبات

**الملف:** `scheduler.py` — السطور 107–120

**الكود المشكل:**
```python
if await get_state(state_key):      # ← فحص
    return
# ... معالجة ...
await set_state(state_key, "sent") # ← تسجيل
```

**المشكلة:** في asyncio، عند وجود `await` بين الفحص والتسجيل، يمكن لكوروتين ثانٍ أن يبدأ قبل انتهاء الأول. إذا جُدوِل نفس الأذان مرتين (بسبب إعادة التشغيل أو خطأ)، كلاهما سيجتاز الفحص ويُرسلان.

**الإصلاح:** استخدام `INSERT OR IGNORE` في قاعدة البيانات كضمان ذري:
```python
async def try_claim_state(key: str) -> bool:
    """يُعيد True فقط إذا كان أول من يسجّل هذا المفتاح."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT OR IGNORE INTO bot_state(key,value) VALUES(?,?)", (key, "sent")
        )
        await db.commit()
        return cur.rowcount == 1  # 1 = تم الإدراج (أول مرة)
```

---

### H-03 — `split_message` قد يكسر وسوم HTML

**الملف:** `content_service.py` — السطور 126–138

**المشكلة:** إذا كانت الرسالة تحتوي `<b>نص طويل جداً...</b>` والقطع يقع داخل الوسم، يصبح HTML مكسوراً. تيليجرام قد يرفض الرسالة أو يُظهرها بشكل خاطئ.

```python
# مثال على المشكلة:
text = "<b>نص" + "أ" * 4000 + "</b>"
# نتيجة split_message():
# جزء 1: "<b>نصأأأ..." ← وسم <b> مفتوح بلا إغلاق
# جزء 2: "...أأأ</b>" ← وسم إغلاق بلا فتح
```

**الإصلاح:** البحث عن نقطة قطع آمنة قبل `<` أو بعد `>`:
```python
def split_message(text: str, limit: int = 4000) -> list[str]:
    if len(text) <= limit:
        return [text]
    parts = []
    while len(text) > limit:
        split_at = text.rfind("\n", 0, limit)
        if split_at == -1:
            # ابحث عن نقطة قبل وسم HTML
            tag_pos = text.rfind("<", 0, limit)
            split_at = tag_pos if tag_pos > limit // 2 else limit
        parts.append(text[:split_at])
        text = text[split_at:].lstrip()
    parts.append(text)
    return parts
```

---

### H-04 — `CHANNEL_ID` نوعه `str` وقد يُسبب مشاكل API

**الملف:** `config.py` — السطر 10

**الكود المشكل:**
```python
CHANNEL_ID: str = os.getenv("CHANNEL_ID", "")
```

**المشكلة:** تيليجرام يقبل الـ channel ID كـ integer (مثل `-1001234567890`) أو username (مثل `@channel`). تمريره كـ string رقمي يعمل في أغلب الأحيان، لكن بعض عمليات API كـ `pin_chat_message` قد تفشل أو تُعيد أخطاء غير متوقعة.

**الإصلاح:**
```python
_channel_raw = os.getenv("CHANNEL_ID", "")
if _channel_raw.lstrip("-").isdigit():
    CHANNEL_ID = int(_channel_raw)
else:
    CHANNEL_ID = _channel_raw  # username مثل @channel
```

---

### H-05 — `DATA_PATH` يعتمد على مسار نسبي هش

**الملف:** `config.py` — السطر 13

**الكود المشكل:**
```python
DATA_PATH: str = os.path.join(os.path.dirname(__file__), "..", "data", "normalized")
```

**المشكلة:** `__file__` قد يكون مساراً نسبياً في بعض بيئات التشغيل. إذا شُغّل البوت من مجلد مختلف، `..` قد يُشير إلى مكان خاطئ.

**الإصلاح:** استخدام `os.path.abspath`:
```python
_BASE = os.path.abspath(os.path.dirname(__file__))
DATA_PATH: str = os.path.join(_BASE, "..", "data", "normalized")
```

---

### H-06 — `stop_scheduler()` يوقف المجدول بدون انتظار

**الملف:** `app.py` السطر 75 + `scheduler.py` السطر 305

**الكود المشكل:**
```python
def stop_scheduler() -> None:
    scheduler.shutdown(wait=False)  # ← المهام الجارية تُقطع فجأة
```

**المشكلة:** إذا كان البوت يُرسل رسالة جماعية لمئات المستخدمين عند إيقاف التشغيل، تُقطع العملية في منتصفها. بعض المستخدمين يستقبلون الرسالة، آخرون لا.

**الإصلاح:**
```python
def stop_scheduler() -> None:
    scheduler.shutdown(wait=True)   # انتظر انتهاء المهام الجارية
    logger.info("Scheduler stopped cleanly")
```

---

## 🟡 المستوى المتوسط (Medium)

---

### M-01 — `get_today_dua()` موجودة لكنها غير مستخدمة (Dead Code)

**الملف:** `event_service.py` — السطور 70–78

دالة `get_today_dua()` تُحمّل `weekly_duas.json` وتُعيد دعاء اليوم حسب يوم الأسبوع، لكنها **لا تُستدعى من أي مكان** في المشروع — لا من `scheduler.py` ولا من `handlers.py`.

**التوصية:** إما إضافة مهمة مجدولة لدعاء اليوم، أو حذف الدالة والملف المرتبط بها.

---

### M-02 — `check_daily_event()` تُنفَّذ مرتين عند الإطلاق

**الملف:** `app.py` — السطر 69

**الكود:**
```python
start_scheduler(bot)        # ← يضيف cron job لـ 07:00
...
await check_daily_event()   # ← ينفذها فوراً أيضاً
```

**المشكلة:** إذا أُعيد تشغيل البوت بعد 07:00 وقبل منتصف الليل، سيتحقق من المناسبات فوراً عند الإطلاق (السطر 69) وهذا صحيح. لكن الـ cron job لن يُنفَّذ حتى 07:00 التالية فلا إشكال. 

الإشكال الفعلي: إذا أُعيد التشغيل قبل 07:00 وانتهى `check_daily_event()` بنجاح وسجّل `event_checked_{date}`، ثم جاء الـ cron job في 07:00 ووجد المفتاح موجوداً فتجاوز — **هذا سلوك صحيح في الواقع**. لكن إذا أُعيد التشغيل بعد 07:00 ووُجد المفتاح، فإن الدعوة الفورية في السطر 69 لن تُرسل لأن المفتاح محفوظ.

**التوصية:** توثيق هذا السلوك بتعليق واضح في الكود.

---

### M-03 — `cmd_jobs` في `admin.py` قد تتجاوز حد رسالة تيليجرام

**الملف:** `admin.py` — السطور 168–179

**المشكلة:** مع تراكم مهام `adhan_*` و`taqibat_*` (5 صلوات × 2 = 10 مهام يومياً)، وخاصة إذا لم تُنفَّذ بعض المهام وتراكمت، قد تتجاوز الرسالة حد تيليجرام (4096 حرف).

**الإصلاح:** استخدام `split_message` أو تقليل التفاصيل:
```python
text = "\n".join(lines)
for part in content_service.split_message(text):
    await message.answer(part, parse_mode="HTML")
```

---

### M-04 — JSON لا يُتحقق من صحته عند التحميل

**الملف:** `content_service.py` — السطور 14–25

**المشكلة:** إذا كان ملف JSON مكسوراً (syntax error)، `json.load()` يرمي `json.JSONDecodeError`. الكود يلتقط أخطاء الملف غير الموجود، لكن لا يلتقط أخطاء التحليل.

**أيضاً:** إذا كان العنصر لا يحتوي حقل `id`، ستنكسر دالة `_pick()` بـ `KeyError`.

**الإصلاح:**
```python
try:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
except json.JSONDecodeError as e:
    logger.error("JSON parse error in %s: %s", path, e)
    return []

# تصفية العناصر الناقصة الحقول الأساسية
data = [item for item in data if isinstance(item, dict) and "id" in item and "text" in item]
```

---

### M-05 — `broadcast` في `admin.py` لا يُقسّم الرسائل الطويلة

**الملف:** `admin.py` — السطور 155–158

**الكود المشكل:**
```python
await message.bot.send_message(uid, text, parse_mode="HTML")  # ← بلا split!
```

**المشكلة:** إذا أرسل الأدمن broadcast طويل، سيفشل الإرسال لجميع المستخدمين بصمت لأن الرسالة تتجاوز 4096 حرف.

**الإصلاح:**
```python
for part in content_service.split_message(text):
    await message.bot.send_message(uid, part, parse_mode="HTML")
```

---

### M-06 — `_schedule_prayer_jobs_for_day` لا تُجدول صلاة العشاء لليوم التالي صحيحاً

**الملف:** `scheduler.py` — السطر 253

**الكود المشكل:**
```python
taqibat_dt = prayer_dt + timedelta(minutes=delay)
if taqibat_dt <= now:
    continue  # ← تتجاوز الأذان أيضاً إذا كان التعقيب مضى!
```

**المشكلة:** إذا كان وقت الأذان لم يمضِ، لكن وقت التعقيب مضى (الأذان قبل دقيقتين من الآن والتعقيب بعد دقيقة من الآن)، سيُجدول الأذان بشكل صحيح لكن `continue` يتخطى تسجيل التعقيب. الأذان سيُرسَل لكن التعقيب لن يُجدوَل أبداً.

**الإصلاح:**
```python
delay = TAQIBAT_DELAYS.get(prayer)
if delay:
    taqibat_dt = prayer_dt + timedelta(minutes=delay)
    if taqibat_dt > now:  # ← فقط إذا لم يمضِ وقت التعقيب
        tid = f"taqibat_{prayer}_{d.isoformat()}"
        if not scheduler.get_job(tid):
            scheduler.add_job(...)
```

---

### M-07 — لا يوجد WAL Mode في SQLite

**الملف:** `database.py` — `init_db()`

**المشكلة:** SQLite بوضعه الافتراضي يستخدم journal mode يمنع القراءة أثناء الكتابة. مع عمليات async متزامنة (مستخدم يشترك بينما الـ scheduler يُرسِل)، قد تظهر أخطاء `database is locked`.

**الإصلاح:** تفعيل WAL mode:
```python
async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA synchronous=NORMAL")
        # ... باقي الجداول
```

---

### M-08 — `format_pinned_prayer` تستدعي `get_next_prayer()` ثم `get_prayer_times()` مجدداً

**الملف:** `prayer_service.py` — السطور 145–162

**الكود:**
```python
def format_pinned_prayer(times: dict[str, datetime]) -> str:
    next_prayer = get_next_prayer(times)  # ← يمرر times
```

```python
def get_next_prayer(times=None):
    if times is None:
        times = get_prayer_times()  # ← لن يُعيد حساب لأن times مُمرَّر
```

هذا سليم تقنياً. لكن في `update_pinned_prayer` في `scheduler.py`:
```python
times = get_prayer_times()
text = format_pinned_prayer(times)
```

لا مشكلة هنا. **✅ هذا في الواقع صحيح** — تم التثبّت.

---

## 🔵 المستوى المنخفض / ملاحظات (Low/Info)

---

### L-01 — Scheduler هو متغير module-level مشترك

**الملف:** `scheduler.py` — السطر 22

```python
scheduler = AsyncIOScheduler(timezone=DEFAULT_TIMEZONE)
```

إذا استُورد `scheduler.py` في سياقين مختلفين (نادر في Python لكنه ممكن في الاختبارات)، يُشاركان نفس الـ scheduler instance. يُفضَّل استخدام Singleton pattern أو تمرير الـ scheduler كـ dependency.

---

### L-02 — `_bot` متغير global في `scheduler.py`

```python
_bot: Bot | None = None

def start_scheduler(bot: Bot) -> None:
    global _bot
    _bot = bot
```

النمط يعمل لكنه صعب الاختبار. يُفضَّل تمرير `bot` مباشرة للدوال أو استخدام class-based scheduler.

---

### L-03 — `aiosqlite` يُستورد داخل الدالة في مكانين

**الملف:** `scheduler.py` — السطور 55 و 202

```python
async def _send_broadcast(bot: Bot, text: str) -> None:
    import aiosqlite  # ← import داخل دالة!
```

يعمل، لكن يُعدّ ممارسة سيئة. يجب نقله لأعلى الملف.

---

### L-04 — `admin.py` لا يتحقق من صحة `content_type` في الاشتراكات

**الملف:** `handlers.py` — السطور 249–254

```python
content_type = cb.data.split(":")[2]
await subscription_service.subscribe(cb.from_user.id, content_type)
```

إذا عدّل مستخدم الـ callback_data يدوياً (عبر Telegram Bot API أو client معدّل)، يمكنه إدخال أي قيمة كـ `content_type`. يُفضَّل التحقق:
```python
VALID_TYPES = {"hadith", "wisdom", "daily_dua", "taqibat"}
if content_type not in VALID_TYPES:
    await cb.answer("⚠️ نوع اشتراك غير صالح", show_alert=True)
    return
```

---

### L-05 — `time_str` في `format_prayer_times` يستخدم 12-hour format

**الملف:** `prayer_service.py` — السطر 141

```python
time_str = times[key].strftime("%I:%M %p")
```

النتيجة مثل `03:45 AM`. لمستخدمين عراقيين، التنسيق 24-ساعة (`%H:%M`) أوضح وأكثر شيوعاً. الرسالة المثبتة بالفعل تستخدم `%H:%M` (السطر 155) — **تناقض في نفس الملف**.

**الإصلاح:** توحيد التنسيق إلى `%H:%M`.

---

### L-06 — `check_daily_event()` تستدعي `event_service.format_hijri_today()` لكن لا تُرسل التاريخ في الرسالة بشكل متسق

**الملف:** `scheduler.py` — السطر 193–195

```python
hijri = event_service.format_hijri_today(today)
full_text = f"🗓 <b>{hijri}</b>\n\n{text}"
```

لكن `format_event()` أيضاً يُضيف `🗓` في بداية الرسالة (السطر 85 من `event_service.py`). النتيجة:
```
🗓 الثلاثاء | 17 ذو الحجة 1447 هـ

🗓 عيد الأضحى المبارك  ← 🗓 مكررة!
```

**الإصلاح:** حذف `🗓` من `format_event()` أو من `full_text` في `check_daily_event()`.

---

### L-07 — Logging لـ APScheduler و aiogram مكبوت بالكامل

**الملف:** `app.py` — السطور 39–41

```python
logging.getLogger("aiogram").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.WARNING)
```

عند التطوير، هذا يُخفي معلومات مفيدة مثل تفاصيل الـ jobs وأخطاء الشبكة. يُفضَّل جعله قابلاً للتحكم عبر `LOG_LEVEL`:
```python
if config.LOG_LEVEL == "DEBUG":
    logging.getLogger("apscheduler").setLevel(logging.DEBUG)
```

---

## جدول الأولويات والإصلاح

| # | المعرف | الوصف المختصر | الملف | الجهد |
|---|--------|--------------|-------|-------|
| 1 | C-01 | إرسال مزدوج للمناسبة في القناة | `scheduler.py` | 5 دقائق |
| 2 | C-02 | FileNotFoundError غير محمي في event_service | `event_service.py` | 10 دقائق |
| 3 | C-03 | لا rate limiting في الإرسال الجماعي | `scheduler.py`, `admin.py` | 10 دقائق |
| 4 | C-04 | N+1 استعلامات DB في `_pick()` | `content_service.py` | 20 دقيقة |
| 5 | H-01 | لا cache في `event_service` | `event_service.py` | 15 دقيقة |
| 6 | H-02 | TOCTOU race في الأذان | `scheduler.py`, `database.py` | 20 دقيقة |
| 7 | H-03 | split_message يكسر HTML tags | `content_service.py` | 15 دقيقة |
| 8 | H-04 | CHANNEL_ID نوع string بدل int | `config.py` | 5 دقائق |
| 9 | H-05 | DATA_PATH مسار هش | `config.py` | 2 دقيقة |
| 10 | H-06 | scheduler.shutdown بلا انتظار | `scheduler.py` | 2 دقيقة |
| 11 | M-01 | get_today_dua() dead code | `event_service.py` | — |
| 12 | M-03 | cmd_jobs قد يتجاوز 4096 حرف | `admin.py` | 5 دقائق |
| 13 | M-04 | لا تحقق من JSON schema | `content_service.py` | 10 دقائق |
| 14 | M-05 | broadcast لا يُقسّم الرسائل | `admin.py` | 2 دقيقة |
| 15 | M-06 | تعقيب مفقود بسبب continue خاطئ | `scheduler.py` | 5 دقائق |
| 16 | M-07 | لا WAL mode في SQLite | `database.py` | 2 دقيقة |
| 17 | L-03 | import داخل دالة | `scheduler.py` | 1 دقيقة |
| 18 | L-04 | لا validation لـ content_type | `handlers.py` | 5 دقائق |
| 19 | L-05 | تناقض تنسيق الوقت 12h/24h | `prayer_service.py` | 1 دقيقة |
| 20 | L-06 | 🗓 مكررة في رسائل المناسبات | `scheduler.py` | 1 دقيقة |

---

## خلاصة

المشروع مبني بشكل جيد بشكل عام — الهيكل نظيف، الفصل بين الطبقات واضح، والـ logging موجود. لكن يوجد **4 مشاكل حرجة** يجب معالجتها قبل الإطلاق الفعلي:

1. **الإرسال المزدوج للمناسبات** — خطأ منطقي واضح يُحرج البوت.
2. **FileNotFoundError في event_service** — يُسقط البوت عند أي طلب متعلق بالمناسبات.
3. **غياب Rate Limiting** — يُعرّض البوت للحظر الفوري مع نمو قاعدة المستخدمين.
4. **N+1 queries في `_pick()`** — يجعل البوت بطيئاً مع نمو البيانات.

---

*نهاية تقرير الفحص — PROJECT_AUDIT.md*
