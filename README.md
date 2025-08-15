Twitter Auto Poster (Playwright + GitHub Actions)

الوصف
برنامج يقوم بنشر تغريداتك بشكل دوري على تويتر باستخدام Playwright و GitHub Actions مجانًا، حتى لو كان جهازك مغلق.

المميزات
- مجاني بالكامل
- يعمل 24/7 عبر GitHub Actions
- إعادة ترتيب فقرات التغريدات والهاشتاقات عشوائيًا لتقليل النمطية
- إضافة تغريدات جديدة بسهولة عبر تعديل ملف tweets.json

الإعداد
1. ثبّت Python وPlaywright على جهازك:
   pip install -r requirements.txt
   playwright install

2. شغل login_helper.py وسجل الدخول لحسابك في تويتر، ثم اضغط Enter لحفظ الجلسة.

3. حول ملف storage_state.json إلى base64:
   base64 storage_state.json > storage_state.b64

4. أنشئ مستودع جديد في GitHub، أضف الملفات إليه.

5. في إعدادات المستودع، أضف Secret جديد باسم:
   - Key: PLAYWRIGHT_STORAGE_BASE64
   - Value: محتوى ملف storage_state.b64

6. شغل الـ workflow يدويًا من صفحة Actions لاختبار النشر.

ملاحظات
- يفضل تجربة الحساب على حساب تجريبي أولًا
- تابع الـ Logs في GitHub Actions لمعرفة أي مشاكل
- في حال تغيّر واجهة تويتر أو تم تسجيل الخروج، أعد خطوة login_helper.py
