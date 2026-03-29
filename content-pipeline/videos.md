# فيديوهات | Videos Pipeline

## Overview

Videos are sourced from YouTube and cataloged in `data/videos.json`. The frontend at `videos.html` provides category filtering, search, and dynamic rendering via `videos-dynamic.js`.

---

## Step-by-Step: Adding New Videos

### 1. Get Video Metadata
From YouTube, collect:
- **Video ID** (from URL: `youtube.com/watch?v=XXXXXXXXXXX`)
- **Title** (Arabic)
- **Upload date** (YYYY-MM-DD)
- **Duration** (MM:SS or H:MM:SS)
- **Category** (see category list below)

### 2. Add to JSON
Add a new entry to `data/videos.json` array (newest first):

```json
{
  "id": "VIDEO_ID",
  "title": "عنوان الفيديو",
  "date": "2026-04-01",
  "duration": "15:30",
  "category": "دروس ومحاضرات"
}
```

### 3. Verify No Duplicates
Before adding, check that the video ID doesn't already exist:

```powershell
Select-String -Path "data/videos.json" -Pattern "VIDEO_ID"
```

### 4. Commit

```powershell
git add data/videos.json
git commit -m "Add video: [title]"
git push origin main
```

---

## Bulk Scraping (Full Channel Audit)

For comprehensive channel audits, use `yt-dlp`:

```powershell
# Scrape all videos
yt-dlp --flat-playlist --print "%(id)s|%(title)s|%(upload_date)s|%(duration)s" "https://www.youtube.com/@ahmedelfashny/videos"

# Scrape shorts
yt-dlp --flat-playlist --print "%(id)s|%(title)s|%(upload_date)s|%(duration)s" "https://www.youtube.com/@ahmedelfashny/shorts"

# Scrape streams
yt-dlp --flat-playlist --print "%(id)s|%(title)s|%(upload_date)s|%(duration)s" "https://www.youtube.com/@ahmedelfashny/streams"
```

Then compare against existing `data/videos.json` to find missing entries.

---

## Video Categories

| Category (Arabic) | Used For |
|-------------------|----------|
| دروس ومحاضرات | Lessons and lectures |
| خطب الجمعة | Friday sermons |
| خطب المناسبات | Special occasion sermons |
| خواطر قرآنية | Quranic reflections |
| فتاوى وأحكام | Fatwas and rulings |
| تلاوات وابتهالات | Recitations and prayers |
| صلوات وتراويح | Prayers and Taraweeh |
| محاضرات وندوات | Talks and seminars |
| مسابقات وتكريمات | Competitions and awards |
| منوعات إسلامية | Islamic miscellaneous |
| Shorts | Short-form content |
| IG Reels | Instagram reels |

**Rules:** Category names in `videos.json` must match the filter button labels in `videos.html` and the logic in `videos-dynamic.js`.

---

## Data Format

```json
[
  {
    "id": "YouTube_video_id",
    "title": "عنوان الفيديو بالعربية",
    "date": "YYYY-MM-DD",
    "duration": "MM:SS",
    "category": "category_name"
  }
]
```

## Duration Format
- Under 1 hour: `MM:SS` (e.g., `15:30`)
- Over 1 hour: `H:MM:SS` (e.g., `1:23:45`)
- Never use `0:MM:SS` format

## Architecture

| Component | File | Role |
|-----------|------|------|
| Data source | `data/videos.json` | Full video catalog (source of truth) |
| Listing | `videos.html` + `videos.css` | Browse/filter/search videos |
| Renderer | `videos-dynamic.js` | Category filtering, lazy loading |
| Khutab video | `khutab-video.html` + `khutab-video.js` | Friday sermon video filter |
| Tilawa | `tilawa.html` + `tilawa-dynamic.js` | Recitation video filter |

## Current Stats
- **Total videos:** ~1388
- **Categories:** 12+
- **Ordering:** Newest first
