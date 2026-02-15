# Article Publishing Workflow (DOCX -> Website)

## الهدف
هذه الطريقة تضمن نشر المقال كاملًا من ملف DOCX بنفس تصميم الموقع، مع حفظ نسخة نصية، وإضافة وسوم المشاركة (thumbnail) تلقائيًا.

## 1) نشر مقال جديد من DOCX
شغّل الأمر التالي من PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File "scripts/publish_docx_article.ps1" `
  -DocxPath "Articals\اسم-الملف.docx" `
  -Slug "article-slug"
```

### الناتج
- صفحة HTML داخل `books/article-slug.html`
- نسخة نصية كاملة داخل `Articals/processed/article-slug.txt`
- المحتوى يُنشَر كاملًا من DOCX (بدون اختصار)
- وسوم مشاركة مضافة داخل الصفحة الجديدة (`og:*` و `twitter:*`)

## 2) إضافة بطاقة المقال في صفحة المقالات
أضف بطاقة في `articles.html` بنفس النمط الحالي مع رابط الصفحة الجديدة.

## 3) توليد صورة thumbnail مستقلة لكل رابط
لتوليد صور مشاركة لكل صفحات الموقع (الحالية والجديدة):

```powershell
powershell -ExecutionPolicy Bypass -File "scripts/generate_page_thumbnails.ps1"
```

### الناتج
- صور PNG بالمقاس القياسي للمشاركة `1200x630`
- مكان الحفظ: `assets/og/*.png`
- اسم صورة فريد لكل صفحة (مثال: `books-ramadan-basirat-altakhtit-anwar-altalluq.png`)

## 4) تحديث وسوم المشاركة (OG/Twitter) على كل الصفحات
بعد توليد الصور، حدّث جميع صفحات HTML لتستخدم الصورة الخاصة بكل صفحة + الدومين من `CNAME`:

```powershell
powershell -ExecutionPolicy Bypass -File "scripts/add_social_meta.ps1"
```

### ماذا يضيف السكربت؟
- `og:title`, `og:description`, `og:image`, `og:url`
- `twitter:title`, `twitter:description`, `twitter:image`
- `og:image:width=1200` و `og:image:height=630`
- يعتمد تلقائيًا على الدومين من ملف `CNAME` (مثل `https://ahmedelfashny.com`)

## 5) النشر
```powershell
git add .
git commit -m "Publish article and update per-page social thumbnails"
git push --force origin main
```

## ملاحظات
- إذا لم تظهر thumbnail مباشرة بعد النشر، افعل تحديث قوي للمتصفح (`Ctrl+F5`) وانتظر تحديث كاش المنصات الاجتماعية.
- واتساب/فيسبوك/تويتر قد يحتفظوا بكاش للرابط؛ أحيانًا يلزم إعادة مشاركة الرابط بعد دقائق ليظهر التصميم الجديد.
