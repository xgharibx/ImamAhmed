# قالب تصميم الخطب المكتوبة | Khutbah Website Design Standard

## Overview

جميع الخطب المكتوبة يجب أن تتبع نفس تصميم موقع الويب لضمان الاتساق البصري والاحترافية عبر جميع الصفحات.

**Reference Khutbahs (Template Examples):**
- ✅ k-20260313-bg9jywwtmjay.html (الْعُرُوجُ الرُّوحِيُّ فِي شَهْرِ الْفُتُوحَاتِ)
- ✅ k-20260327-bg9jywwtmjay.html (مَصَايِدُ الْهَوَاتِفِ وَذِئَابُ الْخَفَاءِ)

---

## Visual Design Elements

### 1. Page Structure
- **Header:** Sticky navigation bar with logo, menu items, and hamburger menu
- **Page Header:** Title section with breadcrumb navigation and wave SVG divider
- **Main Content:** Centered container with khutbah-content div (loaded dynamically from JSON)
- **Actions Bar:** Back button to khutab-written.html listing
- **Footer:** Copyright information with footer pattern
- **Back-to-Top Button:** Floating button for navigation

### 2. Color & Typography
- **Font Family:** Amiri (Arabic text), Cairo (headers), Tajawal (body), Aref Ruqaa (decorative)
- **Theme Colors:** Using CSS custom properties (--bg-primary, etc.)
- **Text Direction:** RTL (right-to-left) for Arabic content

### 3. Animations & Effects
- **AOS Library:** Fade-up animations on scroll (`data-aos="fade-up"`)
- **Preloader:** Islamic pattern with Bismillah text
- **Wave Divider:** SVG wave animation between sections
- **Responsive:** Mobile-first design with hamburger menu

---

## File Naming Convention

**Pattern:** `k-[YYYYMMDD]-[ID].html`

Examples:
- `k-20260313-bg9jywwtmjay.html` (13 March 2026)
- `k-20260327-bg9jywwtmjay.html` (27 March 2026)

Where:
- `YYYYMMDD` = Gregorian date of khutbah delivery
- `ID` = Unique 5-10 character identifier

---

## HTML Structure (Standard Template)

### Must Include
```html
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <!-- Charset & Viewport -->
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  
  <!-- Fonts & Icons -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Amiri:ital,wght@0,400;0,700;1,400;1,700&family=Cairo:wght@300;400;500;600;700;800;900&family=Tajawal:wght@300;400;500;700;800;900&family=Aref+Ruqaa:wght@400;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
  
  <!-- Animations -->
  <link href="https://unpkg.com/aos@2.3.1/dist/aos.css" rel="stylesheet">
  
  <!-- Stylesheets -->
  <link rel="stylesheet" href="../style.css">
  <link rel="stylesheet" href="../animations.css">
  <link rel="stylesheet" href="../khutab.css?v=20260327-1">
  
  <!-- Meta Tags & OpenGraph -->
  <link rel="canonical" href="https://ahmedelfashny.com/khutab/k-[YYYYMMDD]-[ID].html?v=[YYYYMMDD]-1">
  <meta property="og:type" content="article">
  <meta property="og:locale" content="ar_AR">
  <meta property="og:site_name" content="Sheikh Ahmed Ismail Al-Fashni">
  <meta property="og:title" content="[Title]">
  <meta property="og:description" content="[Title] — [Author] • [Date]">
  <meta property="og:image" content="https://ahmedelfashny.com/assets/og/sheikh-ahmed-share.jpg?v=[YYYYMMDD]-1">
  <meta property="og:url" content="https://ahmedelfashny.com/khutab/k-[YYYYMMDD]-[ID].html?v=[YYYYMMDD]-1">
  <meta property="og:updated_time" content="[YYYY-MM-DD]T00:00:00+00:00">
  
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="[Title]">
  <meta name="twitter:description" content="[Title]">
  <meta name="twitter:image" content="https://ahmedelfashny.com/assets/og/sheikh-ahmed-share.jpg?v=[YYYYMMDD]-1">
</head>

<body data-khutba-id="local-[YYYY-MM-DD]-[slug]">
  <script>window.KHUTBA_ID = 'local-[YYYY-MM-DD]-[slug]';</script>
  
  <!-- Preloader -->
  <div id="preloader">
    <div class="loader">
      <div class="islamic-pattern-loader"></div>
      <div class="bismillah-loader">بِسْمِ اللَّهِ الرَّحْمَنِ الرَّحِيمِ</div>
    </div>
  </div>
  
  <!-- Navigation Header -->
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
  
  <!-- Page Title Section -->
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
        <h1 class="page-title" id="khutba-title"><span class="title-icon"><i class="fas fa-file-lines"></i></span>[Title]</h1>
        <p class="page-subtitle" id="khutba-meta">[Islamic Date] - [Gregorian Date]</p>
      </div>
    </div>
    <div class="page-header-wave">
      <svg viewBox="0 0 1440 120" preserveAspectRatio="none">
        <path d="M0,64 C480,150 960,-20 1440,64 L1440,120 L0,120 Z" fill="var(--bg-primary)"/>
      </svg>
    </div>
  </section>
  
  <!-- Main Content -->
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
  
  <!-- Navigation & Back to Top -->
  <a href="#" class="back-to-top" id="backToTop"><i class="fas fa-arrow-up"></i></a>
  
  <!-- Scripts (REQUIRED ORDER) -->
  <script src="https://unpkg.com/aos@2.3.1/dist/aos.js" defer></script>
  <script src="../main.js" defer></script>
  <script src="../pdf-export.js?v=20260309-1" defer></script>
  <script src="../khutba-view.js?v=20260327-1" defer></script>
</body>
```

---

## Data Entry (khutab_written.json)

Every khutbah must have a corresponding entry in `data/khutab_written.json`:

```json
{
  "id": "local-2026-03-27-masayid-hawatif",
  "title": "مَصَايِدُ الْهَوَاتِفِ الكامل العنوان",
  "author": "أحمد إسماعيل الفشني",
  "date": {
    "display": "٨ شَوَّال ١٤٤٧ هـ - ٢٧ مَارِس ٢٠٢٦ م",
    "iso": "2026-03-27"
  },
  "content_text": "[full khutbah text - plain ASCII]",
  "content_html": "[formatted with HTML tags]",
  "excerpt": "[first 50-100 words for preview]"
}
```

---

## Version Numbers

**Current Stable Versions:**
- khutab.css: `v=20260327-1`
- khutba-view.js: `v=20260327-1`
- pdf-export.js: `v=20260309-1` (stable)
- main.js: no version (always latest)

**When to Update:**
- Update khutab.css version when CSS styling changes
- Update khutba-view.js version when rendering logic/data loading changes
- Add `?v=[YYYYMMDD]-1` to canonical URL and og:image for cache busting

---

## Import Checklist for New Khutbahs

- [ ] HTML file created with correct naming: `k-[YYYYMMDD]-[ID].html`
- [ ] Data entry added to `khutab_written.json` with matching ID
- [ ] Title and subtitle in HTML match JSON data
- [ ] Date formatted correctly in both displays (Arabic + Gregorian)
- [ ] Breadcrumb and navigation links correct
- [ ] Version numbers updated in CSS/JS links
- [ ] OpenGraph meta tags complete and accurate
- [ ] Canonical URL includes version parameter
- [ ] File pushed to GitHub
- [ ] Khutab added to listing on `khutab-written.html`

---

## Notes

- This design uses **dynamic content loading** via JavaScript from the JSON data file
- The `khutba-view.js` script reads the `data-khutba-id` and loads content from JSON
- This allows centralized content management and reduces HTML file size
- All styling is controlled via external CSS files for maintainability
- Responsive design automatically adjusts for mobile/tablet/desktop

---

**Standard Established:** 27 March 2026
**Applies To:** All khutbahs from this date forward
