# 📂 Content Pipeline — دليل نشر المحتوى

This folder contains the complete publishing technique and design reference for every content type on the Sheikh Ahmed website. When you receive new content (a khutba, article, fatwa, video, etc.), consult the relevant guide below — it contains the exact steps, templates, data format, and design standards.

## Content Type Guides

| Guide | Content Type | Source Format |
|-------|-------------|---------------|
| [written-khutab.md](written-khutab.md) | خطب مكتوبة (Written Sermons) | DOCX / text |
| [articles.md](articles.md) | مقالات (Articles/Books) | DOCX |
| [fatawa.md](fatawa.md) | فتاوى (Fatwas/Q&A) | DOCX / text |
| [videos.md](videos.md) | فيديوهات (Videos) | YouTube |
| [hadith.md](hadith.md) | الحديث الشريف (Hadith) | API / JSON |
| [data-health.md](data-health.md) | صحة البيانات (Data Validation) | JSON |

## Quick Reference

- **Domain:** `ahmedelfashny.com` (from `CNAME`)
- **Hosting:** GitHub Pages, branch `main`
- **Fonts:** Amiri, Cairo, Tajawal, Aref Ruqaa (Google Fonts)
- **Icons:** Font Awesome 6.5.1
- **Animations:** AOS 2.3.1
- **Direction:** RTL (Arabic)

## Folder Structure Overview

```
Root/
├── index.html                    # Homepage
├── style.css                     # Global styles + CSS variables
├── animations.css                # Preloader + animations
├── main.js                       # Core JS (nav, scroll, counters)
├── data/                         # All JSON data sources
│   ├── khutab_written.json       # Written khutab entries
│   ├── fatawa.json               # Fatwa Q&A entries
│   ├── videos.json               # YouTube video catalog
│   ├── adhkar.json               # Daily adhkar
│   └── quran.json                # Quran page data
├── khutab/                       # Individual khutba HTML pages
├── books/                        # Article/book HTML pages
├── assets/og/                    # Social sharing thumbnails
├── scripts/                      # Publishing helper scripts
│   ├── publish_docx_article.ps1  # DOCX → article page
│   ├── generate_page_thumbnails.ps1
│   ├── add_social_meta.ps1
│   └── compute_slugs.py
└── templates/
    └── article-publishing/       # Article HTML template
```
