# تقرير مشروع بوت تليجرام ديني شيعي

## ملخص تقني

| البيان | القيمة |
|--------|--------|
| الاسم | Shia Religious Bot |
| التقنية | Python 3.11 + Aiogram v3 + APScheduler 3.10.4 + SQLite |
| إطار الصلاة | الجعفرية — الكوت، العراق |
| تاريخ التقرير | يونيو 2026 |
| الحالة | جميع المراحل الـ 11 منتهية — البوت يعمل |
| المهام المجدولة النشطة | 8 مهام |

---

## هيكل الملفات

| الملف | الأسطر | الوظيفة | المراحل |
|-------|--------|---------|--------|
| `app.py` | 82 | نقطة الدخول + إدارة دورة الحياة | 0 |
| `config.py` | 23 | إعدادات المشروع + متغيرات البيئة | 0 |
| `database.py` | 60 | SQLite + إدارة الحالة | 0 |
| `handlers.py` | 264 | الأوامر + Inline Keyboard | 1–5 |
| `admin.py` | 180 | لوحة تحكم الأدمن | 10 |
| `scheduler.py` | 307 | APScheduler + جدولة المهام | 5–9 |
| `services/content_service.py` | 175 | محرك المحتوى + Cache | 2 |
| `services/prayer_service.py` | 163 | حساب مواقيت الصلاة الجعفرية | 4 |
| `services/subscription_service.py` | 69 | إدارة الاشتراكات | 3 |
| `services/event_service.py` | 113 | المناسبات الهجرية | 9 |
| `services/__init__.py` | 1 | placeholder | — |
| `requirements.txt` | 9 | الاعتماديات | 0 |

---

## ملفات البيانات (JSON)

| الملف | الحالة | النوع |
|-------|--------|-------|
| `data/normalized/daily_content/hadith.json` | **غير موجود** | أحاديث يومية |
| `data/normalized/daily_content/wisdom.json` | **غير موجود** | حِكَم الإمام علي |
| `data/normalized/daily_content/daily_dua.json` | **غير موجود** | أدعية يومية |
| `data/normalized/daily_content/munajat.json` | **غير موجود** | مناجاة |
| `data/normalized/daily_content/ziyarat.json` | **غير موجود** | زيارات |
| `data/normalized/prayer_content/fajr.json` | **غير موجود** | تعقيبات الفجر |
| `data/normalized/prayer_content/dhuhr.json` | **غير موجود** | تعقيبات الظهر |
| `data/normalized/prayer_content/maghrib.json` | **غير موجود** | تعقيبات المغرب |
| `data/normalized/prayer_content/isha.json` | **غير موجود** | تعقيبات العشاء |
| `data/normalized/event_content/events.json` | **غير موجود** | المناسبات الهجرية |
| `data/normalized/event_content/weekly_duas.json` | **غير موجود** | أدعية الأيام |

> ⚠️ مجلد `data/normalized` موجود لكن جميع ملفات JSON غائبة — هذا أكبر نقص في المشروع.

---

## قاعدة البيانات (SQLite)

**المسار:** `project/storage/bot.db`

### الجداول

| الجدول | الأعمدة الرئيسية | الوظيفة |
|--------|-----------------|---------|
| `users` | `id` (PK)، `username`، `first_name`، `joined_at` | حفظ المستخدمين |
| `subscriptions` | `user_id + content_type` (PK)، `active`، `created_at` | الاشتراكات |
| `sent_content` | `content_id + category` (PK)، `sent_at` | منع التكرار |
| `bot_state` | `key` (PK)، `value` | الحالة والإعدادات |

---

## المراحل والمهام المنجزة

### المرحلة 0 — Setup (البنية التحتية)
- ✅ إنشاء هيكل المشروع
- ✅ `requirements.txt` (9 حزم)
- ✅ `config.py` + `.env` + Replit Secrets
- ✅ تهيئة SQLite تلقائياً عند الإطلاق
- ✅ Logging مع RotatingFileHandler (5MB × 3)
- ✅ التحقق من `BOT_TOKEN` عند البدء

### المرحلة 1 — Core Bot
- ✅ القائمة الرئيسية بأزرار Inline
- ✅ الأوامر: `/start`, `/help`, `/menu`, `/prayer`, `/event`
- ✅ حفظ/تحديث بيانات المستخدم تلقائياً عند `/start`

### المرحلة 2 — Content Engine
- ✅ قراءة JSON مع Cache في الذاكرة
- ✅ منع التكرار عبر جدول `sent_content`
- ✅ نظام `is_featured` و`send_score`
- ✅ `split_message()` للرسائل الطويلة (حد 4000 حرف)
- ✅ أنواع المحتوى: حديث، حكمة، دعاء، مناجاة، زيارة، تعقيب

### المرحلة 3 — Subscriptions
- ✅ جدول `subscriptions` في قاعدة البيانات
- ✅ `subscribe()` / `unsubscribe()`
- ✅ أزرار Inline تفاعلية (✅/❌)
- ✅ 4 أنواع اشتراك: حديث، حكمة، دعاء، تعقيب

### المرحلة 4 — Prayer System
- ✅ حساب مواقيت الصلاة الجعفرية يدوياً (Julian Date)
- ✅ الزوايا: فجر -16°، مغرب -4°، عشاء -14°
- ✅ العصر: ظل الشاخص 1×
- ✅ الموقع: الكوت، العراق (32.5017°N، 45.8122°E، UTC+3)
- ✅ حساب الصلاة القادمة والعد التنازلي
- ✅ أمر `/prayer` مع معلومات كاملة

### المرحلة 5 — Pinned Prayer Message
- ✅ تحديث تلقائي كل دقيقة عبر Scheduler
- ✅ تثبيت الرسالة في القناة
- ✅ تعديل الرسالة المثبتة إن وُجدت، إرسال جديدة إن لم توجد
- ✅ حفظ `message_id` في `bot_state`

### المرحلة 6 — Adhan Notification
- ✅ أذان تلقائي عند وقت كل صلاة
- ✅ حماية من التكرار بمفتاح `adhan_{prayer}_{date}`
- ✅ الإرسال للقناة أو للمستخدمين (حسب `CHANNEL_ID`)

### المرحلة 7 — Prayer Taqibat
- ✅ تعقيب الفجر بعد +3 دقائق
- ✅ تعقيب الظهر والمغرب بعد +2 دقيقة
- ✅ حماية من التكرار بمفتاح `taqibat_{prayer}_{date}`
- ✅ يقرأ المحتوى من JSON (يعود فارغاً إن لم توجد ملفات)

### المرحلة 8 — Daily Scheduler

| الوقت | المهمة | الجمهور |
|-------|--------|---------|
| 07:00 | فحص المناسبات اليومية | القناة أو الجميع |
| 08:00 | حديث اليوم | مشتركو الحديث |
| 13:00 | حكمة يومية | مشتركو الحكمة |
| 18:00 | دعاء يومي | مشتركو الدعاء |
| 20:00 | مناجاة | مشتركو التعقيب |

### المرحلة 9 — Events System
- ✅ `event_service.py` كامل
- ✅ التقويم الهجري بواسطة `hijri-converter`
- ✅ `/event` يعرض المناسبة الحالية + القادمة (7 أيام)
- ✅ فحص يومي تلقائي عند 07:00

### المرحلة 10 — Admin Panel
- ✅ فلتر `IsAdmin` يحمي جميع الأوامر
- ✅ `/stats` — إحصائيات مفصّلة
- ✅ `/broadcast` — إرسال جماعي
- ✅ `/reload_json` — إعادة تحميل Cache
- ✅ `/test_hadith`, `/test_wisdom`, `/test_dua` — اختبار المحتوى
- ✅ `/test_prayer`, `/test_adhan`, `/test_taqibat` — اختبار الصلوات
- ✅ `/test_pinned`, `/test_event` — اختبار المثبتة والمناسبات
- ✅ `/jobs` — عرض المهام المجدولة

### المرحلة 11 — Optimization
- ✅ Logging منظم مع RotatingFileHandler
- ✅ منع التكرار في الأذان والتعقيبات
- ✅ Cache للـ JSON مع `reload_all()`
- ✅ `misfire_grace_time=120` في APScheduler
- ✅ معالجة أخطاء شاملة في الـ Scheduler

---

## المهام المجدولة

| معرف المهمة | الوقت | النوع | الحالة |
|------------|-------|-------|--------|
| `pinned_prayer` | كل دقيقة | تحديث الرسالة المثبتة | نشطة إذا `CHANNEL_ID` مضبوط |
| `daily_event` | 07:00 | فحص المناسبات | نشطة |
| `daily_hadith` | 08:00 | حديث يومي | نشطة |
| `daily_wisdom` | 13:00 | حكمة يومية | نشطة |
| `daily_dua` | 18:00 | دعاء يومي | نشطة |
| `daily_munajat` | 20:00 | مناجاة | نشطة |
| `reschedule_prayers` | 00:01 | جدولة صلوات اليوم التالي | نشطة |
| `adhan_{prayer}_{date}` | وقت الصلاة | أذان (DateTrigger، ينتهي بعد التنفيذ) | ديناميكي |
| `taqibat_{prayer}_{date}` | بعد الأذان بدقائق | تعقيب (DateTrigger) | ديناميكي |

---

## النواقص الرئيسية

### 1. ملفات JSON (الأولوية القصوى)
جميع ملفات البيانات العشرة غائبة. البوت يعمل لكن لن يرسل أي محتوى ديني.

### 2. بيانات بيئة اختيارية
- `CHANNEL_ID` غير مضبوط → لا تحديث للمثبتة، لا أذان في القناة
- `ADMIN_IDS` غير مضبوط → لا يمكن استخدام أوامر الأدمن

### 3. دالة `get_today_dua()` في `event_service.py`
موجودة في الكود لكنها غير مُستدعاة من أي مكان في المشروع.

### 4. لا Rate Limiting
`/broadcast` والمجدول لا يتحكمان في سرعة الإرسال، مما قد يُشغّل Flood Control لدى تيليجرام.

### 5. عدم وجود WAL Mode في SQLite
قد يُسبب "database is locked" عند الاستخدام المتزامن المكثف.
