# مقالات | Articles Pipeline

## Overview

Articles are published as standalone HTML pages in `books/` from DOCX source files. The process uses a PowerShell script for extraction, with a standard template for consistent design.

---

## Step-by-Step: Publishing a New Article from DOCX

### 1. Run the Publishing Script

```powershell
powershell -ExecutionPolicy Bypass -File "scripts/publish_docx_article.ps1" `
  -DocxPath "Articals\اسم-الملف.docx" `
  -Slug "article-slug"
```

**Output:**
- `books/article-slug.html` — Full article page with site design
- `Articals/processed/article-slug.txt` — Plain text backup

### 2. Add Article Card to Listing Page

In `articles.html`, add a new card **at the top** of the articles grid:

```html
<div class="article-card" data-aos="fade-up">
  <div class="article-card-content">
    <h3 class="article-title">
      <a href="books/article-slug.html">عنوان المقال</a>
    </h3>
    <p class="article-excerpt">مقتطف من المقال في سطرين أو ثلاثة...</p>
    <a href="books/article-slug.html" class="article-read-more">
      <span>اقرأ المقال</span>
      <i class="fas fa-arrow-left"></i>
    </a>
  </div>
</div>
```

### 3. Generate Social Thumbnails

```powershell
powershell -ExecutionPolicy Bypass -File "scripts/generate_page_thumbnails.ps1"
```

Generates `1200x630` PNG thumbnails in `assets/og/` for all pages.

### 4. Update Social Meta Tags

```powershell
powershell -ExecutionPolicy Bypass -File "scripts/add_social_meta.ps1"
```

Adds `og:*` and `twitter:*` meta tags using the domain from `CNAME`.

### 5. Commit & Push

```powershell
git add .
git commit -m "Publish article: [article title]"
git push origin main
```

---

## Manual Fallback (if PowerShell script fails)

If the script has encoding issues with Arabic DOCX files:

1. Extract DOCX XML content manually (unzip .docx → word/document.xml)
2. Copy the template: `templates/article-publishing/ramadan-article-template.html`
3. Replace placeholder tokens with actual content
4. Save as `books/article-slug.html`
5. Extract plain text to `Articals/processed/article-slug.txt`

---

## Article HTML Design Standard

Each article page in `books/` must follow the site design. Key elements:

```html
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <!-- Standard font/icon/animation links (same as khutab) -->
  <!-- Page-specific stylesheets: style.css, animations.css -->
  <!-- OG/Twitter meta tags with article-specific title, description, image -->
</head>
<body>
  <!-- Preloader (same as all pages) -->
  <!-- Header with navigation (same as all pages) -->
  <!-- Page header with breadcrumb: الرئيسية > المقالات > [Article Title] -->
  <!-- Article content in a container -->
  <!-- Footer (same as all pages) -->
  <!-- Scripts: AOS, main.js -->
</body>
</html>
```

## Architecture

| Component | File | Role |
|-----------|------|------|
| Template | `templates/article-publishing/ramadan-article-template.html` | HTML boilerplate |
| Script | `scripts/publish_docx_article.ps1` | DOCX→HTML converter |
| Thumbnails | `scripts/generate_page_thumbnails.ps1` | OG image generator |
| Meta tags | `scripts/add_social_meta.ps1` | Social meta injector |
| Output | `books/<slug>.html` | Published article page |
| Text backup | `Articals/processed/<slug>.txt` | Plain text archive |
| Listing | `articles.html` + `articles.css` | Browse articles |

## Notes
- New articles go at the **top** of the grid (newest first)
- Social thumbnails may take time to propagate on WhatsApp/Facebook/Twitter
- Use `Ctrl+F5` for hard refresh after publishing
- DOCX source files are kept in `Articals/` for reference
