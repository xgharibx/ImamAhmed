# الحديث الشريف | Hadith Section

## Overview

The hadith section uses pre-scraped JSON data files in `data/` with a client-side browser at `hadith.html`. Data was sourced from the Sunnah.com API via `scraper_v2.py`.

---

## Hadith Collections

| Collection | File | Count |
|-----------|------|-------|
| صحيح البخاري | `data/bukhari.json` | 7,000+ |
| صحيح مسلم | `data/muslim.json` | 5,000+ |
| سنن أبي داود | `data/abudawud.json` | 4,800+ |
| جامع الترمذي | `data/tirmidhi.json` | 3,900+ |
| سنن النسائي | `data/nasai.json` | 5,800+ |
| سنن ابن ماجه | `data/ibnmajah.json` | 4,300+ |
| موطأ مالك | `data/malik.json` | 1,900+ |

---

## Re-Scraping Data (if needed)

Use the Python scraper to refresh hadith data:

```powershell
python scraper_v2.py
```

**Source API:** `https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/`

The scraper fetches Arabic text for all collections and saves to `data/*.json`.

---

## Architecture

| Component | File | Role |
|-----------|------|------|
| Data files | `data/bukhari.json`, `muslim.json`, etc. | Pre-scraped hadith collections |
| Frontend | `hadith.html` + `hadith.css` | Browse/search hadiths |
| Renderer | `hadith.js` | Collection/chapter/hadith navigation |
| Scraper | `scraper_v2.py` | Data refresh from Sunnah.com API |

## User Flow
1. Select hadith collection (book)
2. Browse chapters/sections
3. Read individual hadiths with grades and metadata
4. Navigate back to previous level

## Adding New Collections
Edit the `books` array in `hadith.js`:

```javascript
const books = [
    { id: 'collection-id', name: 'Collection Name',
      icon: 'fa-icon', edition: 'ara-collection-id' },
];
```

Then scrape the data using `scraper_v2.py` with the new collection identifier.
