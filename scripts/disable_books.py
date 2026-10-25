#!/usr/bin/env python3
"""Replace public book pages with a temporary unavailable state."""
from __future__ import annotations

import argparse
import re
import urllib.parse
from pathlib import Path

import content_pipeline as shared


ROOT = Path(__file__).resolve().parents[1]


def disable_books(root: Path = ROOT) -> dict[str, int]:
    index_path = root / "books.html"
    index = index_path.read_text(encoding="utf-8-sig")
    index, subtitle_count = re.subn(
        r'(<p class="page-subtitle"[^>]*>).*?(</p>)', r"\1قريبا\2", index, count=1, flags=re.DOTALL
    )
    if subtitle_count != 1:
        raise shared.PipelineError("تعذر إظهار حالة قريباً في صفحة المؤلفات")
    index, description_count = re.subn(
        r'<meta name="description" content="[^"]*">',
        '<meta name="description" content="المؤلفات - قريبا">',
        index,
        count=1,
    )
    index, keyword_count = re.subn(r'\s*<meta name="keywords" content="[^"]*">', "", index, count=1)
    if description_count != 1 or keyword_count > 1:
        raise shared.PipelineError("تعذر تحديث بيانات صفحة المؤلفات")
    index, title_count = re.subn(
        r'<title>.*?</title>', '<title>المؤلفات | قريبا - الشيخ أحمد إسماعيل الفشني</title>', index, count=1, flags=re.DOTALL
    )
    if title_count != 1:
        raise shared.PipelineError("تعذر تحديث عنوان صفحة المؤلفات")
    if not re.search(r'<link\s+[^>]*rel="canonical"', index, flags=re.IGNORECASE):
        index = index.replace(
            "</title>",
            '</title>\n    <link rel="canonical" href="https://ahmedelfashny.com/books.html">',
            1,
        )
    if '<meta name="robots"' not in index:
        index = index.replace(
            '<meta name="description" content="المؤلفات - قريبا">',
            '<meta name="description" content="المؤلفات - قريبا">\n    <meta name="robots" content="noindex, nofollow, noarchive">',
            1,
        )

    start_marker = "    <!-- Books Grid -->"
    end_marker = "    <!-- Footer -->"
    marker_count = index.count(start_marker)
    if marker_count == 1 and index.count(end_marker) == 1:
        start = index.index(start_marker)
        end = index.index(end_marker, start)
        index = index[:start] + '    <section class="books-section" hidden aria-hidden="true"></section>\n\n' + index[end:]
    elif marker_count != 0 or 'class="books-section" hidden' not in index:
        raise shared.PipelineError("تعذر تحديد شبكة المؤلفات بأمان")
    index_path.write_text(index, encoding="utf-8", newline="\n")

    template = (root / "templates" / "books-disabled.html").read_text(encoding="utf-8")
    disabled = 0
    for page in sorted((root / "books").glob("*.html")):
        if page.name.startswith("article-"):
            continue
        relative = page.relative_to(root).as_posix()
        canonical = f"{shared.SITE_URL}/{urllib.parse.quote(relative, safe='/')}"
        page.write_text(template.replace("{{CANONICAL_URL}}", canonical), encoding="utf-8", newline="\n")
        disabled += 1

    return {"book_pages_disabled": disabled, "article_pages_preserved": len(list((root / "books").glob("article-*.html")))}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    result = disable_books(parser.parse_args().root)
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
