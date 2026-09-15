# Video Catalog Refresh

Install Python 3.11+ and `yt-dlp`, then run from the repository root:

```powershell
python -m pip install yt-dlp
python scripts/refresh_video_catalog.py --refresh-feeds --apply
python -m unittest discover -s tests -p test_video_catalog.py
node tests/video_catalog.cjs
```

The two official channels and their video, Shorts, and live-stream tabs are
configured in `content-pipeline/channels.json`. No media is downloaded.
Upload dates come from public YouTube metadata, not dates mentioned in titles.
Reviewed exceptions are in `content-pipeline/video-category-overrides.json`.
Named series and channel-specific recitations retain their own categories.

The audit cache and report live under `tmp/youtube-audit-YYYY-MM-DD`.
Use `--cache PATH` to resume a run; `--refresh-feeds` refreshes channel listings
while reusing successful metadata responses. Network failures or concurrent
catalog edits prevent the final write. Review the report and diff before
committing the catalog. Publish through the existing repository deployment.
The Android app reads the live website, so content changes require no app release.

On September 15, 2026, public metadata was unavailable for `KW-L6uOsJAs`,
`vao6ATA9FXs`, `rX0R-maMhmc`, and `spnvDfpGAhk`. Their existing records are
preserved; the first two have no verifiable date and are not assigned one.
The generic livestream `qPNYpYqRzJ4` has no descriptive title or description;
it remains in the general lessons category pending editorial identification.
