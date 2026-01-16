"""Quick static scan for broken local href/src references.

- Scans *.html files (workspace root + subfolders)
- Extracts href/src links
- Ignores external links (http/https), anchors, mailto/tel, javascript:
- Reports missing files on disk

Usage:
  python scripts/scan_site_links.py
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]

HREF_SRC_RE = re.compile(r"\b(?:href|src)\s*=\s*([\"'])(.*?)\1", re.IGNORECASE)

IGNORE_PREFIXES = (
    "http://",
    "https://",
    "mailto:",
    "tel:",
    "javascript:",
    "data:",
)


def should_check(url: str) -> bool:
    u = (url or "").strip()
    if not u:
        return False
    if u.startswith(IGNORE_PREFIXES):
        return False
    if u.startswith("#"):
        return False
    return True


def normalize_path(url: str) -> str:
    u = (url or "").strip()
    u = u.split("#", 1)[0]
    u = u.split("?", 1)[0]
    u = unquote(u)
    return u


def main() -> int:
    html_files = sorted(ROOT.rglob("*.html"))
    missing: list[tuple[str, str]] = []

    for html_path in html_files:
        try:
            text = html_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        for _, raw_url in HREF_SRC_RE.findall(text):
            if not should_check(raw_url):
                continue

            rel = normalize_path(raw_url)
            # Skip empty after normalization
            if not rel:
                continue

            # Treat URLs as relative to the HTML file.
            target = (html_path.parent / rel).resolve()
            # Ensure we don't allow escaping outside ROOT via ../
            try:
                target.relative_to(ROOT)
            except ValueError:
                continue

            if not target.exists():
                missing.append((str(html_path.relative_to(ROOT)).replace("\\", "/"), rel))

    if not missing:
        print("OK: No missing local href/src targets found.")
        return 0

    print(f"Found {len(missing)} missing local references:\n")
    for page, rel in missing:
        print(f"- {page} -> {rel}")

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
