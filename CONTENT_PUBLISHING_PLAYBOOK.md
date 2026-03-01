# Content Publishing Playbook

This file records the stable workflow used in this repo so future updates stay consistent.

## 1) Written Khutab
- Source of truth: `data/khutab_written.json`.
- Viewer rendering: `khutba-view.js` + styles in `khutab.css`.
- Access gate (latest N khutab) is controlled in `khutab-written.js` and `khutba-view.js`.
- PDF export entrypoint: `SheikhPdfExporter.exportKhutbaItem` in `pdf-export.js`.
- Current PDF behavior:
  - no forced first/second khutba page split,
  - intro page skipped by default for khutba,
  - `عناصر الخطبة` rendered on a dedicated centered page.

## 2) Fatawa
- Source of truth: `data/fatawa.json` (`count` must match `items.length`).
- Frontend: `fatawa.js` + `fatawa.css`.
- Keep IDs sequential and append new entries at the end.

## 3) Articles from DOCX
- Canonical template: `templates/article-publishing/ramadan-article-template.html`.
- Preferred script: `scripts/publish_docx_article.ps1`.
- If PowerShell encoding breaks, fallback: extract DOCX XML + token replacement with same template.
- Outputs:
  - article page in `books/<slug>.html`,
  - extracted text in `Articals/processed/<slug>.txt`,
  - add newest article card at top of internal grid in `articles.html`.

## 4) Videos
- Source of truth: `data/videos.json`.
- Dynamic listing: `videos-dynamic.js` and filters in `videos.html`.
- Keep ordering newest-first when adding new items.
- Avoid duplicates by checking existing `id` before insert.
- Category rules in `videos-dynamic.js` must remain aligned with filter buttons in `videos.html`.

## 5) Data Health (important)
- Validate all `data/*.json` before commit.
- Save JSON as UTF-8 without BOM and with valid trailing newline.
- Never leave literal `\\n` characters after closing `]`/`}`.

## 6) Finalization
- Run diagnostics (`get_errors`) on changed files.
- Verify git diff/status includes only intended files.
- Commit and push to `main`.
