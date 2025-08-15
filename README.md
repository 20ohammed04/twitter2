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
