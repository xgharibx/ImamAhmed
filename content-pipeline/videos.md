# فيديوهات | Videos Pipeline

## Overview

Videos are sourced from YouTube and cataloged in `data/videos.json`. The frontend at `videos.html` provides category filtering, search, and dynamic rendering via `videos-dynamic.js`.

---

## Automatic Updates

`.github/workflows/video-sync.yml` runs on **Monday and Thursday at 06:17 Africa/Cairo**, including local daylight-saving changes. It runs on GitHub, not on a phone or PC. GitHub may delay scheduled jobs under load.

Both official channels in `channels.json` are checked: `@ahmedelfashny` and `@AhmedIsmailElfashny`. Each run scans all public videos, Shorts, and streams, imports missing completed videos, and retains existing records. There is no 15-video RSS limit or recent-upload cutoff that can lose older missed uploads.

The workflow:

1. Resolves each new video's actual public publication date, title, and duration, and checks its owning channel.
2. Applies the existing category rules and reviewed `video-category-overrides.json` corrections. The recitation channel always uses `quran`; recognized program series retain their own categories.
3. Skips live/upcoming broadcasts until they finish. Fails rather than publishing missing/invalid metadata or an empty channel response.
4. Runs the Python and JavaScript catalog tests, commits `data/videos.json` and `data/video-sync-status.json` to `main`, and requests a GitHub Pages build.
5. Verifies the exact live catalog and sync-status bytes after deployment. A pushed commit alone is not reported as verified publication.

The website's video library, Friday-sermon section, and recitation section revalidate the shared JSON on page load. The signed Android app loads these same live pages and catalog, so no APK update is needed. An already-open page is refreshed on its next load; no visible auto-reload or UI change is introduced.

`data/video-sync-status.json` records the last successful check, channel-tab counts, additions, skipped broadcasts, and catalog checksum. Updating this real health record also keeps the scheduled workflow active during periods without new uploads. Errors are shown in GitHub Actions and retain an audit report for 30 days; the last published catalog remains available.

To run immediately, open **Actions > Update both YouTube channels > Run workflow**. No new API key, YouTube password, or local scheduler is required. The written-khutba uploader shares the publication lock to avoid competing bot deployments.

For a local import:

```powershell
python scripts/refresh_video_catalog.py --new-only --refresh-feeds --apply --report data/video-sync-status.json
python -m unittest discover -s tests -p 'test_*.py' -v
node tests/video_catalog.cjs
```

After committing and publishing, verify:

```powershell
python scripts/verify_video_sync.py --base-url https://ahmedelfashny.com --wait-seconds 600
```

For ambiguous titles, add an ID-based category correction with a reason in `video-category-overrides.json`. Reviewed overrides are applied to existing entries too; other existing records are not automatically reclassified. Title-based classification cannot guarantee every future ambiguous video is understood without an editorial correction.

The small `yt_dlp_plugins/extractor/channel_live_status.py` adapter preserves YouTube's public LIVE badge in newer channel cards. This defers unfinished broadcasts before requesting publication metadata; completed videos still require exact metadata. It does not download video media or bypass sign-in checks.

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
  "category": "lessons"
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

For comprehensive metadata audits of both configured channels, use:

```powershell
python scripts/refresh_video_catalog.py --refresh-feeds
```

Without `--apply`, this writes an audit report/cache only. Unlike the scheduled new-only mode, a full audit resolves metadata for existing entries too. Flat channel listings alone do not supply exact publication dates; do not publish approximate relative dates or dates extracted from titles.

---

## Video Categories

| JSON category | Used For |
|-------------------|----------|
| `lessons` | Lessons, lectures, and reflections |
| `khutbah` | Friday and occasion sermons |
| `quran` | Recitations and Quran prayers |
| `shorts` | Main-channel short-form clips |
| `tafseer` | Quran interpretation |
| `tv` | Broadcast interviews and appearances |
| `ali-wusul` | Ali Wusul program |
| `fi-nur-allah` | Fi Nur Allah / Fi Nur Al-Quran program |
| `qisas-ibra` | Qisas / Qissa Wa Ibra program |

**Rules:** JSON category identifiers must match the filter `data-filter` values and the renderers, not their displayed Arabic labels. Automated imports set `categoryVerified` so each section respects the assigned category. `date` is the source's public publication day, not necessarily the event date mentioned in the title; `publishedAt` preserves the source's timestamp for exact chronological ordering across time zones.

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
- Read the current total and successful sync date from `data/video-sync-status.json`.
- **Categories:** 9 canonical identifiers.
- **Ordering:** Newest public timestamp first.

## Pending Streams

Live and upcoming streams are retried after completion, not published with guessed dates. If YouTube blocks metadata for a previously audited pending ID, the next successful status records it in `deferred_pending` and keeps importing other verified videos. The prior status must match the current catalog hash; the ID must still appear in an official channel feed and must not already be published. It remains visibly unresolved in the audit until complete metadata can be verified. Unknown metadata errors and incorrect channels still fail the run without changing the catalog.
