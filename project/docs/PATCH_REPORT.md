# PATCH_REPORT.md — Wave 1 Critical Fixes

**تاريخ التطبيق:** يونيو 2026
**عدد الملفات المعدلة:** 5
**عدد الـ patches:** 8
**حالة البوت بعد التعديل:** ✅ يعمل بدون أخطاء

---

## ملخص التغييرات

| الـ Patch | المعرف | الملف | الأسطر المتأثرة | الخطورة |
|-----------|--------|-------|----------------|--------|
| WAL mode | M-07 | `database.py` | +2 أسطر في `init_db()` | Medium |
| Atomic claim | H-02 | `database.py` | +15 سطر (دالة جديدة) | High |
| Safe JSON load (events) | C-02 | `event_service.py` | +18 سطر (دالة مساعدة) | Critical |
| Safe JSON load (content) | M-04 | `content_service.py` | +12 سطر تعديل في `_load()` | High |
| Rate limit — subscribers | C-03 | `scheduler.py` | +1 سطر في `_send_to_subscribers()` | Critical |
| Rate limit — broadcast | C-03 | `scheduler.py` | +1 سطر في `_send_broadcast()` | Critical |
| No double send (events) | C-01 | `scheduler.py` | تعديل منطق `check_daily_event()` | Critical |
| Atomic adhan/taqibat | H-02 | `scheduler.py` | تعديل `send_adhan()` + `send_taqibat()` | High |
| Taqibat schedule fix | M-06 | `scheduler.py` | تعديل `_schedule_prayer_jobs_for_day()` | Medium |
| Rate limit — admin broadcast | C-03 | `admin.py` | +2 سطر في `cmd_broadcast()` | Critical |

---

## تفاصيل كل Patch

---

### [M-07] SQLite WAL Mode — `database.py`

**الأسطر:** 14–15 (جديدة في `init_db()`)

**ما تغيّر:**
```python
# قبل:
async with aiosqlite.connect(DB_PATH) as db:
    await db.execute("CREATE TABLE IF NOT EXISTS users ...")

# بعد:
async with aiosqlite.connect(DB_PATH) as db:
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA synchronous=NORMAL")
    await db.execute("CREATE TABLE IF NOT EXISTS users ...")
```

**التأثير:** يُتيح WAL قراءة متزامنة مع الكتابة، يمنع "database is locked".
**Side effects:** يُنشئ ملفات `bot.db-wal` و `bot.db-shm` جانبية — هذا طبيعي وصحيح.

---

### [H-02] Atomic State Claim — `database.py`

**الأسطر:** 67–79 (دالة جديدة `try_claim_state`)

**ما تغيّر:** إضافة دالة جديدة تستخدم `INSERT OR IGNORE` كعملية ذرية:
```python
async def try_claim_state(key: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT OR IGNORE INTO bot_state(key, value) VALUES(?, ?)",
            (key, "claimed"),
        )
        await db.commit()
        return cur.rowcount == 1
```

**التأثير:** يحل race condition في الأذان والتعقيبات — الـ check+set صارا عملية واحدة في DB بدل عمليتين منفصلتين.
**Side effects:** لا يوجد. الدالة القديمة `get_state/set_state` لا تزال موجودة وتُستخدم في باقي الكود.

---

### [C-02] Safe JSON Load — `event_service.py`

**الأسطر:** 26–52 (دالة مساعدة جديدة `_safe_load` + تعديل `_load_events` و`_load_weekly_duas`)

**ما تغيّر:**
```python
# قبل (ينهار عند غياب الملف):
def _load_events() -> list:
    path = os.path.join(DATA_PATH, "event_content/events.json")
    with open(path, encoding="utf-8") as f:   # FileNotFoundError!
        return json.load(f)

# بعد (آمن بالكامل):
def _safe_load(path: str) -> list:
    if not os.path.exists(path):
        logger.warning("File not found: %s", path)
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            logger.error("Expected list in %s ...", path)
            return []
        return data
    except json.JSONDecodeError as e:
        logger.error("JSON parse error in %s: %s", path, e)
        return []
    except OSError as e:
        logger.error("Cannot read %s: %s", path, e)
        return []

def _load_events() -> list:
    return _safe_load(os.path.join(DATA_PATH, "event_content/events.json"))
```

**التأثير:** `/event` والمجدول لن ينهاروا بعد الآن عند غياب أو تلف الملف.
**Side effects:** لا يوجد. نفس public API (`_load_events` → `list`).

---

### [M-04] Safe JSON Load — `content_service.py`

**الأسطر:** 24–42 (تعديل في `_load()`)

**ما تغيّر:** أُضيفت ثلاث طبقات حماية في دالة `_load()`:
1. `try/except json.JSONDecodeError` — JSON مكسور
2. `try/except OSError` — خطأ قراءة الملف
3. فلترة العناصر الناقصة `id` أو `text`

```python
# جديد: تصفية العناصر غير الصالحة
valid = [item for item in data if isinstance(item, dict) and "id" in item and "text" in item]
```

**التأثير:** لن يحدث `KeyError` في `_pick()` أو `_format_item()` بسبب بيانات ناقصة.
**Side effects:** عناصر JSON الناقصة `id` أو `text` ستُتجاهل مع تحذير في الـ logs. Cache يحفظ القائمة المُصفّاة.

---

### [C-03] Rate Limiting — `scheduler.py`

**التغييرات:**

**`_send_to_subscribers()` — السطر 44:**
```python
        await asyncio.sleep(0.05)  # C-03: ~20 msg/s rate limit
```

**`_send_broadcast()` — السطر 71:**
```python
        await asyncio.sleep(0.05)  # C-03: ~20 msg/s rate limit
```

**`import asyncio`** أُضيف في أعلى الملف (السطر 1).

**التأثير:** الإرسال الجماعي مقيّد بـ ~20 رسالة/ثانية. مع 100 مستخدم = 5 ثوان بدل خطر حظر فوري.
**Side effects:** broadcasts ستأخذ وقتاً أطول مع قواعد مستخدمين كبيرة — هذا مقصود وصحيح.

---

### [C-01] No Double Send — `scheduler.py`

**الأسطر:** 203–215 (تعديل منطق `check_daily_event()`)

**ما تغيّر:**
```python
# قبل (إرسال مزدوج):
if CHANNEL_ID:
    await _send_to_channel(_bot, full_text)       # إرسال أول
    if event.get("pin_message"):
        msg = await _bot.send_message(...)         # إرسال ثانٍ!
        await _bot.pin_chat_message(...)

# بعد (إرسال واحد):
if CHANNEL_ID:
    if event.get("pin_message"):
        msg = await _bot.send_message(...)         # إرسال مرة واحدة
        await _bot.pin_chat_message(...)           # ثم تثبيت نفس الرسالة
    else:
        await _send_to_channel(_bot, full_text)    # أو إرسال عادي
```

**التأثير:** المناسبات ذات `pin_message=true` تُرسَل مرة واحدة وتُثبَّت. لا رسالتان.
**Side effects:** لا يوجد. المناسبات العادية (`pin_message=false`) تسلك نفس المسار السابق.

---

### [H-02] Atomic Adhan/Taqibat Guard — `scheduler.py`

**الأسطر:** تعديل `send_adhan()` (113–116) و`send_taqibat()` (137–140)

**ما تغيّر:**
```python
# قبل (TOCTOU — عمليتان منفصلتان):
if await get_state(state_key):   # فحص
    return
# ... معالجة (await هنا يتيح للـ coroutine الثاني التسلل) ...
await set_state(state_key, "sent")  # تسجيل

# بعد (ذري — عملية واحدة):
if not await try_claim_state(state_key):  # فحص + تسجيل معاً
    return
```

**التأثير:** مستحيل إرسال نفس الأذان مرتين حتى لو جاءتا في نفس اللحظة.
**Side effects:** قيمة الـ state الآن `"claimed"` بدل `"sent"` — لا تأثير وظيفي لأنها تُستخدم فقط كـ boolean existence check.

---

### [M-06] Taqibat Scheduling Fix — `scheduler.py`

**الأسطر:** 255–270 (تعديل في `_schedule_prayer_jobs_for_day()`)

**ما تغيّر:**
```python
# قبل (continue يتخطى الأذان أيضاً عند مرور وقت التعقيب):
if taqibat_dt <= now:
    continue  # ← كانت تتخطى كل اللوب!

# بعد (الأذان والتعقيب مستقلان):
# M-06: schedule taqibat independently
if taqibat_dt > now:
    # جدوِل التعقيب
    ...
# الأذان يستمر بشكل مستقل
```

**التأثير:** إذا كان وقت الأذان لم يمضِ لكن وقت التعقيب مضى، يُجدوَل الأذان فقط بدون تخطيه.
**Side effects:** لا يوجد. سلوك التعقيب لم يتغير — فقط لم يعد يُوقف جدولة الأذان معه.

---

### [C-03] Rate Limiting — `admin.py`

**الأسطر:** 161–166 (تعديل `cmd_broadcast()`)

**ما تغيّر:**
```python
# قبل:
await message.bot.send_message(uid, text, parse_mode="HTML")

# بعد:
for part in content_service.split_message(text):
    await message.bot.send_message(uid, part, parse_mode="HTML")
await asyncio.sleep(0.05)  # C-03: ~20 msg/s rate limit
```

ملاحظة: أُضيف `split_message` هنا أيضاً لإصلاح M-05 (broadcast الطويل) ضمن نفس الـ patch.
**Side effects:** لا يوجد.

---

## نتائج ما بعد التطبيق

```
2026-06-13 18:02:03 | INFO | __main__  | Starting Shia Religious Bot — Phase 11 (complete)
2026-06-13 18:02:03 | INFO | database  | Initializing database at .../bot.db
2026-06-13 18:02:03 | INFO | database  | Database initialized successfully
2026-06-13 18:02:03 | INFO | scheduler | Prayer jobs scheduled for 2026-06-13
2026-06-13 18:02:03 | INFO | scheduler | Scheduler started — 7 jobs active
2026-06-13 18:02:03 | INFO | __main__  | Bot is running. Ctrl+C to stop.
```

✅ لا أخطاء — البوت يقلع نظيفاً.

---

## Side Effects المحتملة (إجمالي)

| الـ Patch | Side Effect | درجة الخطر |
|-----------|------------|-----------|
| WAL mode | ملفات `bot.db-wal` و`bot.db-shm` إضافية | لا شيء |
| Rate limiting | broadcasts أبطأ مع كثرة المستخدمين | مقبول/مطلوب |
| `try_claim_state` | قيمة الـ state `"claimed"` بدل `"sent"` | لا تأثير |
| Safe JSON | عناصر ناقصة الحقول تُتجاهل بصمت | مطلوب |
| Taqibat fix | لا تغيير في السلوك الفعلي | لا شيء |

---

## الـ Patches المتبقية (Wave 2)

هذه لم تُطبَّق بعد — مُرجأة للـ Wave التالي:

| المعرف | الوصف |
|--------|-------|
| C-04 | N+1 DB queries في `_pick()` |
| H-01 | Cache في `event_service` |
| H-03 | `split_message` يكسر HTML tags |
| H-04 | `CHANNEL_ID` نوع `str` بدل `int` |
| H-05 | `DATA_PATH` مسار هش |
| H-06 | `shutdown(wait=False)` |
| L-03 | `import aiosqlite` داخل دالة |
| L-04 | Validate `content_type` في subscriptions |
| L-05 | توحيد تنسيق الوقت 12h/24h |
| L-06 | 🗓 مكررة في رسائل المناسبات |
