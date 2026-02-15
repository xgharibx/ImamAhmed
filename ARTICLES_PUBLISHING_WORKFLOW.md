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

## 3) تفعيل وسوم المشاركة (thumbnail) على الصفحات القديمة والجديدة
لتطبيق وسوم المشاركة على كل صفحات HTML التي لا تحتويها بعد:

```powershell
powershell -ExecutionPolicy Bypass -File "scripts/add_social_meta.ps1"
```

### ماذا يضيف السكربت؟
- `og:title`, `og:description`, `og:image`, `og:url`
- `twitter:title`, `twitter:description`, `twitter:image`
- صورة افتراضية للمشاركة: `sheikh-photo.png`

## 4) النشر
```powershell
git add .
git commit -m "Publish article and update social sharing metadata"
git push --force origin main
```

## ملاحظات
- إذا لم تظهر thumbnail مباشرة بعد النشر، افعل تحديث قوي للمتصفح (`Ctrl+F5`) وانتظر تحديث كاش المنصات الاجتماعية.
- يمكن لاحقًا تخصيص صورة مشاركة مختلفة لكل صفحة بدل الصورة الافتراضية.
