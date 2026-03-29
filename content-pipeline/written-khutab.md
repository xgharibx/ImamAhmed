# خطب مكتوبة | Written Khutab Pipeline

## Overview

Written khutab are published as JSON entries rendered dynamically by `khutba-view.js`. Each khutba also gets a lightweight HTML shell page in `khutab/` for direct linking and social sharing.

---

## Step-by-Step: Publishing a New Written Khutba

### 1. Prepare the Content
- Extract the full khutba text from the source (DOCX, PDF, or raw text)
- Identify: **title** (with tashkeel), **Islamic date**, **Gregorian date**, **author**
- Split into `content_text` (plain text) and `content_html` (formatted HTML)
- Write a short `excerpt` (first 50-100 words)

### 2. Add JSON Entry
Append to `data/khutab_written.json`:

```json
{
  "id": "local-YYYY-MM-DD-slug",
  "title": "عُنْوَانُ الْخُطْبَةِ",
  "author": "أحمد إسماعيل الفشني",
  "date": {
    "display": "١٥ رَبِيع الأَوَّل ١٤٤٧ هـ - ١٥ سبتمبر ٢٠٢٥ م",
    "iso": "2025-09-15"
  },
  "content_text": "Plain text of the khutba...",
  "content_html": "<h2>الخطبة الأولى</h2><p>Content with HTML formatting...</p>",
  "excerpt": "First 50-100 words preview..."
}
```

**ID format:** `local-YYYY-MM-DD-slug` where slug is a short Arabic-to-latin transliteration.

### 3. Create HTML Shell Page
Create `khutab/k-YYYYMMDD-ID.html` using this template:

```html
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="description" content="[TITLE] — [DATE] — by Sheikh Ahmed Ismail Al-Fashni">
  <title>[TITLE] | خطبة مكتوبة | الشيخ أحمد إسماعيل الفشني</title>

  <!-- Fonts & Icons -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Amiri:ital,wght@0,400;0,700;1,400;1,700&family=Cairo:wght@300;400;500;600;700;800;900&family=Tajawal:wght@300;400;500;700;800;900&family=Aref+Ruqaa:wght@400;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
  <link href="https://unpkg.com/aos@2.3.1/dist/aos.css" rel="stylesheet">

  <!-- Stylesheets -->
  <link rel="stylesheet" href="../style.css">
  <link rel="stylesheet" href="../animations.css">
  <link rel="stylesheet" href="../khutab.css">

  <!-- OpenGraph -->
  <link rel="canonical" href="https://ahmedelfashny.com/khutab/k-YYYYMMDD-ID.html">
  <meta property="og:type" content="article">
  <meta property="og:locale" content="ar_AR">
  <meta property="og:site_name" content="Sheikh Ahmed Ismail Al-Fashni">
  <meta property="og:title" content="[TITLE]">
  <meta property="og:description" content="[TITLE] — بقلم أحمد إسماعيل الفشني • [DATE]">
  <meta property="og:image" content="https://ahmedelfashny.com/assets/og/sheikh-ahmed-share.jpg">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta property="og:url" content="https://ahmedelfashny.com/khutab/k-YYYYMMDD-ID.html">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="[TITLE]">
  <meta name="twitter:description" content="[TITLE]">
  <meta name="twitter:image" content="https://ahmedelfashny.com/assets/og/sheikh-ahmed-share.jpg">
</head>

<body data-khutba-id="local-YYYY-MM-DD-slug">
  <script>window.KHUTBA_ID = 'local-YYYY-MM-DD-slug';</script>

  <!-- Preloader -->
  <div id="preloader">
    <div class="loader">
      <div class="islamic-pattern-loader"></div>
      <div class="bismillah-loader">بِسْمِ اللَّهِ الرَّحْمَنِ الرَّحِيمِ</div>
    </div>
  </div>

  <!-- Header -->
  <header id="header" class="scrolled">
    <nav class="navbar">
      <div class="nav-container">
        <a href="../index.html" class="logo">
          <div class="logo-icon"><span class="moon-icon">☾</span></div>
          <div class="logo-text">
            <span class="logo-title">الشيخ أحمد الفشني</span>
            <span class="logo-subtitle">الْبَاحِثُ الْأَزْهَرِيُّ وَخَادِمُ الْوَحْيَيْنِ</span>
          </div>
        </a>
        <ul class="nav-menu">
          <li class="nav-item"><a href="../khutab-written.html" class="nav-link"><i class="fas fa-file-lines"></i> خطب مكتوبة</a></li>
          <li class="nav-item"><a href="../articles.html" class="nav-link"><i class="fas fa-book-open"></i> المقالات</a></li>
          <li class="nav-item"><a href="../contact.html" class="nav-link"><i class="fas fa-envelope"></i> تواصل</a></li>
        </ul>
        <div class="hamburger"><span class="bar"></span><span class="bar"></span><span class="bar"></span></div>
      </div>
    </nav>
  </header>

  <!-- Page Header -->
  <section class="page-header">
    <div class="page-header-bg"></div>
    <div class="container">
      <div class="page-header-content" data-aos="fade-up">
        <div class="breadcrumb">
          <a href="../index.html">الرئيسية</a>
          <i class="fas fa-chevron-left"></i>
          <a href="../khutab-written.html">خطب مكتوبة</a>
          <i class="fas fa-chevron-left"></i>
          <span>عرض خطبة</span>
        </div>
        <h1 class="page-title" id="khutba-title"><span class="title-icon"><i class="fas fa-file-lines"></i></span>[TITLE]</h1>
        <p class="page-subtitle" id="khutba-meta">[ISLAMIC_DATE] - [GREGORIAN_DATE]</p>
      </div>
    </div>
    <div class="page-header-wave">
      <svg viewBox="0 0 1440 120" preserveAspectRatio="none">
        <path d="M0,64 C480,150 960,-20 1440,64 L1440,120 L0,120 Z" fill="var(--bg-primary)"/>
      </svg>
    </div>
  </section>

  <!-- Content -->
  <section class="khutab-section">
    <div class="container">
      <div class="khutba-actions" data-aos="fade-up">
        <a class="btn btn-outline" href="../khutab-written.html"><i class="fas fa-arrow-right"></i> الرجوع للقائمة</a>
      </div>
      <div class="khutba-content" id="khutba-content" data-aos="fade-up"></div>
    </div>
  </section>

  <!-- Footer -->
  <footer id="footer" class="footer">
    <div class="footer-pattern"></div>
    <div class="container">
      <div class="footer-bottom"><p>&copy; <span id="currentYear"></span> الشيخ أحمد الفشني. جميع الحقوق محفوظة.</p></div>
    </div>
  </footer>

  <a href="#" class="back-to-top" id="backToTop"><i class="fas fa-arrow-up"></i></a>

  <!-- Scripts -->
  <script src="https://unpkg.com/aos@2.3.1/dist/aos.js" defer></script>
  <script src="../main.js" defer></script>
  <script src="../pdf-export.js" defer></script>
  <script src="../khutba-view.js" defer></script>
</body>
</html>
```

### 4. Checklist Before Commit

- [ ] JSON entry ID matches `data-khutba-id` in HTML
- [ ] HTML filename follows pattern: `k-YYYYMMDD-ID.html`
- [ ] Title and dates match between JSON and HTML page header
- [ ] `content_html` has proper `<h2>`, `<p>`, `<strong>` formatting
- [ ] Excerpt is concise (50-100 words)
- [ ] OG/Twitter meta tags have correct title and URL

---

## Architecture

| Component | File | Role |
|-----------|------|------|
| Data source | `data/khutab_written.json` | All khutab entries (source of truth) |
| Listing page | `khutab-written.html` + `khutab-written.js` | Browse/search/filter khutab |
| Detail viewer | `khutba-view.html` + `khutba-view.js` | Generic viewer page |
| Shell pages | `khutab/k-*.html` | Direct-link pages (load from JSON) |
| Styling | `khutab.css` | All khutab visual styles |
| PDF export | `pdf-export.js` → `SheikhPdfExporter.exportKhutbaItem` | In-browser PDF generation |

## HTML Formatting Guide for `content_html`

- `<h2>` — Section headings (الخطبة الأولى، الخطبة الثانية، عناصر الخطبة)
- `<h3>` — Sub-headings within sections
- `<p>` — Body paragraphs
- `<strong>` — Key phrases, Quranic references
- `<em>` — Emphasis
- `<br>` — Line breaks within paragraphs
- Quranic verses: wrap in `<strong>` with proper tashkeel
- Hadith references: wrap in `<em>`

## File Naming

**Pattern:** `k-[YYYYMMDD]-[ID].html`
- `YYYYMMDD` = Gregorian date of delivery
- `ID` = Unique 5-12 character identifier (lowercase)

## PDF Export

Users can download khutab as PDF via the built-in export button. The PDF is generated client-side by `pdf-export.js`:
- Entry point: `SheikhPdfExporter.exportKhutbaItem(item)`
- Intro page skipped by default for khutab
- عناصر الخطبة rendered on dedicated centered page
