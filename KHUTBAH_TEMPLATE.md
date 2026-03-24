# قالب تصميم الخطب المكتوبة | Khutbah HTML Template

## Design Standard for Website View

جميع الخطب المكتوبة يجب أن تتبع نفس تصميم موقع الويب لضمان الاتساق والاحترافية.

---

## Base HTML Structure

### Head Section (Required Meta Tags)
```html
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="description" content="[khutbah title] — [date] — by Sheikh Ahmed Ismail Al-Fashni">
  <title>[Khutbah Title] | خطبة مكتوبة | الشيخ أحمد إسماعيل الفشني</title>
  
  <!-- Fonts & Icons -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Amiri:ital,wght@0,400;0,700;1,400;1,700&family=Cairo:wght@300;400;500;600;700;800;900&family=Tajawal:wght@300;400;500;700;800;900&family=Aref+Ruqaa:wght@400;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
  
  <!-- AOS Animation -->
  <link href="https://unpkg.com/aos@2.3.1/dist/aos.css" rel="stylesheet">
  
  <!-- Stylesheets -->
  <link rel="stylesheet" href="../style.css">
  <link rel="stylesheet" href="../animations.css">
  <link rel="stylesheet" href="../khutab.css?v=[DATE]-1">
  
  <!-- Canonical & OpenGraph -->
  <link rel="canonical" href="https://ahmedelfashny.com/khutab/k-[YYYYMMDD]-[ID].html?v=[YYYYMMDD]-1">
  
  <meta property="og:type" content="article">
  <meta property="og:locale" content="ar_AR">
  <meta property="og:site_name" content="Sheikh Ahmed Ismail Al-Fashni">
  <meta property="og:title" content="[Khutbah Title]">
  <meta property="og:description" content="[Khutbah Title] — بقلم أحمد إسماعيل الفشني • [Islamic Date] - [Gregorian Date]">
  <meta property="og:image" content="https://ahmedelfashny.com/assets/og/sheikh-ahmed-share.jpg?v=[YYYYMMDD]-1">
  <meta property="og:image:url" content="https://ahmedelfashny.com/assets/og/sheikh-ahmed-share.jpg?v=[YYYYMMDD]-1">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta property="og:image:type" content="image/jpeg">
  <meta property="og:image:secure_url" content="https://ahmedelfashny.com/assets/og/sheikh-ahmed-share.jpg?v=[YYYYMMDD]-1">
  <meta property="og:url" content="https://ahmedelfashny.com/khutab/k-[YYYYMMDD]-[ID].html?v=[YYYYMMDD]-1">
  <meta property="og:updated_time" content="[YYYY]-[MM]-[DD]T00:00:00+00:00">
  
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="[Khutbah Title]">
  <meta name="twitter:description" content="[Khutbah Title] — بقلم أحمد إسماعيل الفشني • [Islamic Date] - [Gregorian Date]">
  <meta name="twitter:image" content="https://ahmedelfashny.com/assets/og/sheikh-ahmed-share.jpg?v=[YYYYMMDD]-1">
</head>
```

### Body Section Structure
```html
<body data-khutba-id="local-[YYYY-MM-DD]-[slug]">
  <script>window.KHUTBA_ID = 'local-[YYYY-MM-DD]-[slug]';</script>
  
  <!-- Preloader -->
  <div id="preloader">
    <div class="loader">
      <div class="islamic-pattern-loader"></div>
      <div class="bismillah-loader">بِسْمِ اللَّهِ الرَّحْمَنِ الرَّحِيمِ</div>
    </div>
  </div>
  
  <!-- Header/Navigation -->
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
        <div class="hamburger">
          <span class="bar"></span>
          <span class="bar"></span>
          <span class="bar"></span>
        </div>
      </div>
    </nav>
  </header>
  
  <!-- Page Header with Title -->
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
        <h1 class="page-title" id="khutba-title">
          <span class="title-icon"><i class="fas fa-file-lines"></i></span>
          [Khutbah Title]
        </h1>
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
        <a class="btn btn-outline" href="../khutab-written.html">
          <i class="fas fa-arrow-right"></i> الرجوع للقائمة
        </a>
      </div>
      <div class="khutba-content" id="khutba-content" data-aos="fade-up"></div>
    </div>
  </section>
  
  <!-- Footer -->
  <footer id="footer" class="footer">
    <div class="footer-pattern"></div>
    <div class="container">
      <div class="footer-bottom">
        <p>&copy; <span id="currentYear"></span> الشيخ أحمد الفشني. جميع الحقوق محفوظة.</p>
      </div>
    </div>
  </footer>
  
  <!-- Back to Top Button -->
  <a href="#" class="back-to-top" id="backToTop"><i class="fas fa-arrow-up"></i></a>
  
  <!-- Scripts -->
  <script src="https://unpkg.com/aos@2.3.1/dist/aos.js" defer></script>
  <script src="../main.js" defer></script>
  <script src="../pdf-export.js?v=20260309-1" defer></script>
  <script src="../khutba-view.js?v=20260327-1" defer></script>
</body>
```

---

## File Naming Convention

**Pattern:** `k-[YYYYMMDD]-[ID].html`

**Example:** `k-20260327-bg9jywwtmjay.html`

Where:
- `YYYYMMDD` = Date of khutbah delivery in Gregorian calendar
- `ID` = Unique identifier (5-10 character random string or slug)

---

## Version Management

### CSS & JS Versioning
- Update `khutab.css?v=[YYYYMMDD]-1` to match current date when major style updates occur
- Keep `main.js` reference without version for core functionality
- Update `khutba-view.js?v=[YYYYMMDD]-1` to latest when rendering logic changes
- PDF export script version `pdf-export.js?v=20260309-1` remains stable

### Cache Busting
- Canonical URL includes `?v=[YYYYMMDD]-1` parameter
- All OpenGraph image URLs include version parameter
- This ensures fresh content loads across all platforms/social media

---

## Required Data File Entry

Add entry to `data/khutab_written.json`:

```json
{
  "id": "local-[YYYY-MM-DD]-[slug]",
  "title": "[Khutbah Full Title]",
  "author": "أحمد إسماعيل الفشني",
  "date": {
    "display": "[Islamic Date] - [Gregorian Date]",
    "iso": "[YYYY-MM-DD]"
  },
  "content_text": "[Full text content]",
  "content_html": "[HTML formatted content]",
  "excerpt": "[First ~100 words]"
}
```

---

## Example References

✅ **Reference Khutbahs (Follow This Design):**
- k-20260313-bg9jywwtmjay.html (الْعُرُوجُ الرُّوحِيُّ)
- k-20260327-bg9jywwtmjay.html (مَصَايِدُ الْهَوَاتِفِ)

All future khutbahs should use this identical structure and follow these standards.

---

## Notes for Future Development

1. **Responsive Design:** All pages use Bootstrap-like container classes and responsive breakpoints
2. **Animations:** AOS.js provides scroll animations with `data-aos="fade-up"` attributes
3. **Navigation:** Header remains "sticky" (class="scrolled") for better UX
4. **Content Loading:** `khutba-view.js` dynamically loads content from JSON based on `data-khutba-id`
5. **Accessibility:** Breadcrumbs and semantic HTML improve navigation and indexing
6. **Social Sharing:** Full OpenGraph + Twitter meta tags ensure proper social media preview

---

**Last Updated:** 27 March 2026
**Template Version:** v1.0
