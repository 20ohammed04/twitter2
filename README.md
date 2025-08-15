# twitter2

واجهة محلية لإدارة ونشر تغريدات على X (Twitter) باستخدام Playwright، مع دعم النشر اليدوي محلياً أو عبر GitHub Actions بحدود نشر آمنة.

## المحتويات
- `manage_tweets.py` — واجهة سطر أوامر لإدارة `tweets.json` (عرض/إضافة/تعديل/حذف/تعطيل/تفعيل/وضع تفاعلي).
- `manage_tweets_gui.py` — واجهة رسومية (Tkinter) لإدارة التغريدات محلياً.
- `post_tweets.py` — نشر تلقائي باستخدام Playwright، مع إعادة محاولات، وسجلات، وحدود آمنة.
- `login_helper.py` — توليد `storage_state.json` بعد تسجيل الدخول اليدوي.
- `tweets.json` — مصدر التغريدات.
- `post_history.json` — تتبُّع النشر لآخر 24 ساعة (حد 20).
- `runner_state.json` — توقيت التشغيل القادم في نمط CI الأحادي.
- `debug_outputs/` — ملفات تصحيح عند الفشل.
- `runner.log` — سجل دوّار.

## المتطلبات
- Python 3.10+
- Playwright وChromium

ثبّت المتطلبات:
```powershell
pip install -r requirements.txt
python -m playwright install
```

## إعداد الجلسة (مرة واحدة)
أنشئ جلسة دخول صالحة لتفادي التحققات أثناء النشر:
```powershell
python login_helper.py
# ستُفتح نافذة متصفح؛ سجّل الدخول يدويًا ثم اضغط Enter لحفظ storage_state.json
```

## إدارة التغريدات
- سطر أوامر (CLI):
```powershell
python manage_tweets.py --list
python manage_tweets.py --add --text "نص" --hashtags "#a,#b"
python manage_tweets.py --edit --id t1 --text "نص جديد" --hashtags "#tag"
python manage_tweets.py --delete --id t2
python manage_tweets.py --interactive
```
- واجهة رسومية:
```powershell
python manage_tweets_gui.py
```

## النشر محليًا
- تشغيل نشر تغريدة واحدة لكل استدعاء:
```powershell
python post_tweets.py
```
- للنشر المتواصل حتى بلوغ السقف اليومي (بفواصل 30–180 دقيقة):
```powershell
$env:LOCAL_CONTINUOUS=1
python post_tweets.py
```

ملاحظات:
- يتم احترام السقف 20 تغريدة خلال 24 ساعة عبر `post_history.json`.
- في حال عدم وجود جديد، قد يعاد استخدام نص قديم مع خلط فقرات/كلمات مع الحفاظ على النص داخل الأقواس كوحدة.
- سجلات التشغيل في الطرفية و`runner.log`. عند الفشل تُحفظ لقطات وHTML في `debug_outputs/`.

## التشغيل عبر GitHub Actions
- ملف العمل: `.github/workflows/poster.yml` يشغّل نشرًا واحدًا في كل تشغيل ويحدد موعد التشغيل التالي عشوائيًا (30–180 دقيقة) عبر `runner_state.json`.
- أضف السر `STORAGE_STATE_B64` بدل رفع `storage_state.json`:
```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("storage_state.json")) | Set-Clipboard
# GitHub → Settings → Secrets → Actions → New repository secret
# الاسم: STORAGE_STATE_B64 (ألصق القيمة)
```
- ماذا يحدث في الـ Workflow؟
  - تثبيت بايثون والحزم وChromium لـ Playwright.
  - فك ترميز `STORAGE_STATE_B64` إلى `storage_state.json` وقت التشغيل.
  - تشغيل `post_tweets.py` مرة واحدة (Headless في CI).
  - تحديث `post_history.json` و`runner_state.json` ودفعهما فقط إلى الفرع.

## القيود والسياسات
- الحد الأقصى: 20 تغريدة خلال 24 ساعة (ي enforced برمجيًا).
- الفاصل بين المنشورات: 30–180 دقيقة (محلي المتواصل وCI).
- احترم شروط X (Twitter) لاستخدام الأتمتة.

## استكشاف الأخطاء وإصلاحها
- مشاكل الجلسة/الدخول: شغّل `login_helper.py` لتجديد `storage_state.json` ثم حدّث السر `STORAGE_STATE_B64`.
- تعذر النشر أو تغيّر واجهة X: افحص `debug_outputs/*.jpg` و`*.html` والسجل `runner.log`.
- فشل دفع التغييرات من Actions: تأكد من `permissions: contents: write` و`persist-credentials: true` وعدم وجود قواعد تمنع push.

## مثال بنية tweets.json
```json
[
  {
    "id": "t1",
    "text": "مثال تغريدة…",
    "hashtags": ["#python", "#automation"],
    "enabled": true
  }
]
```

مهم: لا تشارك `storage_state.json` علنًا. استخدم السر `STORAGE_STATE_B64` فقط داخل CI.
ح `debug_outputs/`، و`runner.log` (راجع `.gitignore`).

## أنماط التشغيل

- CI (افتراضي): تغريدة واحدة لكل تشغيل، واحترام 20/24h، وتشغيل headless، وقراءة الجلسة من `STORAGE_STATE_B64`.
- محلي متواصل: عيّن `LOCAL_CONTINUOUS=1` قبل التشغيل لنشر عدة تغريدات متتالية بفواصل 30–180 دقيقة حتى الوصول للسقف.
## التسجيل (Logs) والاحتفاظ

- تتم طباعة السجلات إلى الطرفية، ويتم أيضاً تدويرها إلى `runner.log` (بحد 500KB و3 نسخ احتياطية) باستخدام `RotatingFileHandler`.

## إعادة المحاولة (Retry/Backoff)

- تمت إضافة آلية إعادة محاولة مع Backoff أسي بسيط عند فشل النشر المؤقت (`post_with_retries`).

## استكشاف الأخطاء وإصلاحها (Troubleshooting)

- مشاكل تسجيل الدخول/جلسة غير صالحة: أعد تشغيل `login_helper.py` محلياً لتجديد `storage_state.json`، ثم حدّث السر `STORAGE_STATE_B64` بنفس الخطوات أعلاه.
- فشل الدفع (push) من Actions: تحقق من أن ملف العمل يحتوي `permissions: contents: write` وأن `actions/checkout` يستخدم `persist-credentials: true`، وتأكّد من عدم وجود قواعد حماية تمنع دفع البوت.
- أخطاء Playwright أو تغيّر واجهة تويتر: راجع ملفات `debug_outputs/*.html` و`*.jpg` لمعرفة السبب.

## ضمان الالتزام بالقيود

- الحد الأقصى 20 تغريدة لكل 24 ساعة مفروض عبر `post_history.json` والتحقُّق قبل كل نشر.
- الفواصل العشوائية بين 30 و180 دقيقة مفروضة في CI (للتشغيل القادم) وفي المحلي المتواصل (انتظار بين كل تغريدة).

