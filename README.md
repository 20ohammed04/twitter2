# twitter2

واجهة محلية لإدارة ونشر تغريدات باستخدام Playwright.

المحتويات
- `manage_tweets.py` - CLI لإدارة `tweets.json` (عرض، إضافة، تعديل، حذف).
- `manage_tweets_gui.py` - واجهة رسومية (Tkinter) لإدارة التغريدات محلياً.
- `post_tweets.py` - سكربت نشر التغريدات تلقائياً باستخدام Playwright.
- `login_helper.py` - أداة لحفظ حالة الجلسة (سجل الدخول يدوياً ثم حفظ `storage_state.json`).
- `tweets.json` - قائمة التغريدات.
- `storage_state.json` - حالة الجلسة (كوكيز) لتمكين Playwright من الوصول للحساب.

السلوك العام
- لا ينشر البرنامج تلقائياً عند التثبيت. عليك تسجيل الجلسة ثم اختبار النشر يدوياً أولاً.

الشروع السريع (موصى به)
1. تثبيت الحزم المطلوبة:

```powershell
pip install -r requirements.txt
```

2. تثبيت متصفحات Playwright (مرة واحدة):

```powershell
python -m playwright install
```

3. تسجيل الجلسة وتخزينها:

```powershell
python login_helper.py
# ستفتح نافذة متصفح؛ سجّل الدخول يدوياً ثم اضغط Enter في الطرفية لحفظ storage_state.json
```

4. اختبار القراءة من `tweets.json` (سريع، لا نشر):

```powershell
python manage_tweets.py --list
```

5. اختبار نشر مرئي (مبسط، لا يعمل headless):
- لتحقّق أولي، افتح `post_tweets.py` وعدّل:
   - `browser = await p.chromium.launch(headless=True)` -> `headless=False`
   - قلّل التغريدات: `tweets = load_tweets()[:1]` لنشر تغريدة واحدة للاختبار.

ثم شغّل:

```powershell
python post_tweets.py
```

راقب نافذة المتصفح وتأكد أن النص يوضع ويضغط زر النشر. إذا نجح، أعد `headless=True` للتشغيل الخلفي.

فحص التركيب السريع (آمن)
لتأكد من عدم وجود أخطاء بايثون تركيبية في سكربت النشر:

```powershell
python -m py_compile post_tweets.py
```

تحسينات موصى بها
- أضيف خيار `--dry-run` لطباعة النصوص دون النشر.
- سجِّل إلى ملف log مع طوابع زمنية لكل محاولة نشر.
- أضف خيار `--count N` للاختبار السريع على N تغريدات.
- شغّل الاختبارات على حساب تجريبي لتقليل المخاطر.

ملاحظات الأمان
- لا تنشر `storage_state.json` علناً — يحتوي على بيانات الجلسة.
- اتبع شروط استخدام Twitter/X بشأن النشر الآلي.

هل تريد الآن أن أطبق أيًا من التحسينات التالية تلقائياً؟
- إضافة `--dry-run` و`--count` إلى `post_tweets.py` مع اختبارات سريعة.
- إضافة سجل (log) لإجراءات النشر.
- تشغيل تجربة نشر مرئي واحد الآن (أقوم بتعديل مؤقت ثم أعيده).

---

## التشغيل عبر GitHub Actions (موصى به للإطلاق)

يوفر المستودع ملف عمل `GitHub Actions` جاهز: `/.github/workflows/poster.yml` يقوم بتشغيل نشر واحد في كل تشغيل، ويُجدول التشغيل التالي عشوائياً (30–180 دقيقة) عبر ملف الحالة `runner_state.json`. كما يحفظ `post_history.json` لضمان عدم تجاوز 20 تغريدة خلال 24 ساعة.

### 1) إنشاء السر STORAGE_STATE_B64

لا تقم أبداً برفع `storage_state.json` إلى المستودع. بدلاً من ذلك أنشئ سرًّا مشفَّراً Base64:

PowerShell (ويندوز):

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("storage_state.json")) | Set-Clipboard
# ثم أنشئ سراً جديداً في: GitHub → Settings → Secrets → Actions → New repository secret
# الاسم: STORAGE_STATE_B64 ، والصق القيمة من الحافظة
```

macOS/Linux:

```bash
base64 -w0 storage_state.json | pbcopy   # macOS
# أو
base64 -w0 storage_state.json | xclip -selection clipboard  # Linux
# ثم أنشئ السر باسم STORAGE_STATE_B64 كما في الأعلى
```

### 2) ما الذي يفعله ملف العمل؟

- يفحص المستودع (`actions/checkout@v4` مع `persist-credentials: true`).
- يثبت بايثون والحزم وكروم Playwright (`python -m playwright install --with-deps chromium`).
- يشغّل `post_tweets.py` بنمط CI (تغريدة واحدة كحد أقصى لكل تشغيل، headless).
- يُحدّث ويدفع فقط `post_history.json` و`runner_state.json` إلى الفرع (بدون `storage_state.json`).

### 3) التفعيل اليدوي والتحقق من السجلات

- من تبويب Actions اختر “Scheduled Twitter Poster” ثم “Run workflow”.
- النتائج المتوقعة:
  - نجاح النشر: رسالة مثل `Posting single tweet (CI mode): ...` ثم لا أخطاء.
  - لم يحن الوقت: `Not time yet. Next post at ts=...` وسينتهي التشغيل سريعاً.
  - فشل: سترى استثناءات وقد تُحفَظ ملفات تصحيح في `debug_outputs/`.

### 4) الملفات المتتبعة والسرية

- يتم تتبُّع: `post_history.json`, `runner_state.json` (لتتبع الحالة بين التشغيلات).
- يتم تجاهل: `storage_state.json`، وملفات التصحيح `debug_outputs/`، و`runner.log` (راجع `.gitignore`).

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

