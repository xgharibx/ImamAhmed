import argparse
import json
import re
import time
from dataclasses import asdict, dataclass
from datetime import date
from typing import Iterable, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


BASE_CATEGORY_URL = (
    "https://ahmedelfashny.com/category/"
    "%d8%a7%d9%84%d8%ae%d8%b7%d8%a8-%d8%a7%d9%84%d9%85%d9%86%d8%a8%d8%b1%d9%8a%d8%a9/"
    "%d8%ae%d8%b7%d8%a8-%d9%85%d9%83%d8%aa%d9%88%d8%a8%d8%a9/"
)

AR_MONTHS = {
    "يناير": 1,
    "فبراير": 2,
    "مارس": 3,
    "أبريل": 4,
    "ابريل": 4,
    "مايو": 5,
    "يونيو": 6,
    "يوليو": 7,
    "أغسطس": 8,
    "اغسطس": 8,
    "سبتمبر": 9,
    "أكتوبر": 10,
    "اكتوبر": 10,
    "نوفمبر": 11,
    "ديسمبر": 12,
}

AR_DATE_RE = re.compile(
    r"(?P<month>" + "|".join(map(re.escape, AR_MONTHS.keys())) + r")\s+"
    r"(?P<day>\d{1,2})\s*,\s*(?P<year>\d{4})"
)

AUTHOR_HINT_RE = re.compile(
    r"(?:للشيخ|فضيلة\s+الشيخ\s*/?|الشيخ\s*/|بقلم)\s+([\w\u0600-\u06FF\s]{3,60})",
    flags=re.UNICODE,
)


@dataclass
class KhutbaDate:
    display: str = ""
    iso: str = ""


@dataclass
class Attachment:
    url: str
    text: str = ""


@dataclass
class KhutbaItem:
    id: str
    title: str
    author: str
    date: KhutbaDate
    source_url: str
    pdf_url: str
    content_html: str
    excerpt: str
    attachments: list[Attachment]


def _slug_from_url(url: str) -> str:
    path = urlparse(url).path.strip("/")
    if not path:
        return ""
    return path.split("/")[-1]


def _make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0 Safari/537.36"
            ),
            "Accept-Language": "ar,en-US;q=0.9,en;q=0.8",
        }
    )
    return s


def fetch_html(session: requests.Session, url: str, timeout: int = 30) -> str:
    last_err: Optional[Exception] = None
    for _ in range(3):
        try:
            r = session.get(url, timeout=timeout)
            r.raise_for_status()
            r.encoding = r.apparent_encoding or r.encoding
            return r.text
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(1.2)
    raise RuntimeError(f"Failed to fetch {url}: {last_err}")


def parse_category_post_links(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")

    links: list[str] = []
    seen = set()

    # Prefer typical WP markup
    for a in soup.select("article .entry-title a, article h2 a, article h3 a"):
        href = (a.get("href") or "").strip()
        if not href:
            continue
        abs_url = urljoin(base_url, href)
        if "/category/" in abs_url or "/tag/" in abs_url or "/page/" in abs_url:
            continue
        if urlparse(abs_url).netloc != urlparse(base_url).netloc:
            continue
        if abs_url in seen:
            continue
        seen.add(abs_url)
        links.append(abs_url)

    # Fallback: any link that looks like a post URL
    if not links:
        for a in soup.select("a[href]"):
            href = (a.get("href") or "").strip()
            if not href:
                continue
            abs_url = urljoin(base_url, href)
            if "/category/" in abs_url or "/tag/" in abs_url or "/page/" in abs_url:
                continue
            if urlparse(abs_url).netloc != urlparse(base_url).netloc:
                continue
            slug = _slug_from_url(abs_url)
            if not slug or slug.isdigit():
                continue
            if abs_url in seen:
                continue
            seen.add(abs_url)
            links.append(abs_url)

    return links


def parse_post_date(soup: BeautifulSoup) -> KhutbaDate:
    # Try <time datetime="...">
    time_el = soup.select_one("time[datetime]")
    if time_el and time_el.get("datetime"):
        dt = time_el.get("datetime").strip()
        # Keep date part only
        iso = dt[:10] if len(dt) >= 10 else ""
        display = (time_el.get_text(" ", strip=True) or "").strip()
        return KhutbaDate(display=display, iso=iso)

    # Try entry-date text
    date_text = ""
    for sel in [".entry-date", ".posted-on", ".post-date", ".meta-date"]:
        el = soup.select_one(sel)
        if el:
            date_text = el.get_text(" ", strip=True)
            if date_text:
                break

    if not date_text:
        # Fallback: search full page text for Arabic month format
        page_text = soup.get_text(" ", strip=True)
        m = AR_DATE_RE.search(page_text)
        if m:
            date_text = m.group(0)

    iso = ""
    m = AR_DATE_RE.search(date_text)
    if m:
        month = AR_MONTHS.get(m.group("month"), 0)
        day = int(m.group("day"))
        year = int(m.group("year"))
        try:
            iso = date(year, month, day).isoformat()
        except Exception:  # noqa: BLE001
            iso = ""

    return KhutbaDate(display=date_text.strip(), iso=iso)


def parse_post_author(soup: BeautifulSoup, title: str, content_text: str) -> str:
    def cleanup(name: str) -> str:
        name = re.sub(r"\s+", " ", (name or "")).strip(" -–—/\\\n\t")
        if not name:
            return ""

        # Cut off common trailing phrases that appear in titles
        name = re.split(r"\s+(?:تحت|تَحْتَ|بعنوان|بِعُنْوَانِ)\s+", name, maxsplit=1)[0]
        name = re.split(r"[:،\(\)\[\]—–-]", name, maxsplit=1)[0]
        name = re.sub(r"\s+", " ", name).strip()

        # If we still have an unusually long string, keep first few words
        parts = name.split()
        if len(parts) > 6:
            name = " ".join(parts[:6])
        return name

    for sel in [
        ".author a",
        "a[rel='author']",
        ".byline a",
        ".byline",
        ".post-author",
    ]:
        el = soup.select_one(sel)
        if el:
            text = el.get_text(" ", strip=True)
            text = re.sub(r"\s+", " ", text).strip()
            if text and len(text) <= 80:
                return cleanup(text)

    hint_source = f"{title} {content_text}"
    m = AUTHOR_HINT_RE.search(hint_source)
    if m:
        return cleanup(m.group(1))

    return ""


def clean_content_html(container: BeautifulSoup) -> str:
    # Remove obvious junk
    for sel in [
        "script",
        "style",
        "noscript",
        "iframe",
        "#comments",
        ".comments-area",
        ".sharedaddy",
        ".jp-relatedposts",
        ".post-tags",
        ".tagcloud",
        ".addtoany_share_save_container",
        ".a2a_kit",
        ".elementor-post__text",
        ".elementor-posts-container",
        ".elementor-posts",
    ]:
        for el in container.select(sel):
            el.decompose()

    # Strip inline event handlers
    for el in container.find_all(True):
        attrs = dict(el.attrs)
        for k in list(attrs.keys()):
            if k.lower().startswith("on"):
                del el.attrs[k]
        if el.name == "a":
            el.attrs["rel"] = "noopener noreferrer"
            el.attrs["target"] = "_blank"

    html = container.decode_contents().strip()
    html = re.sub(r"\s+\n", "\n", html)
    return html


def parse_post(html: str, url: str) -> KhutbaItem:
    soup = BeautifulSoup(html, "lxml")

    title_el = soup.select_one("h1.entry-title") or soup.find("h1")
    title = title_el.get_text(" ", strip=True) if title_el else _slug_from_url(url)

    # The site uses Elementor templates; the real post content is usually in a
    # theme-post-content widget. Fall back progressively.
    content_el = (
        soup.select_one("div.elementor-location-single .elementor-widget-theme-post-content")
        or soup.select_one("div.elementor-widget-theme-post-content")
        or soup.select_one("div.elementor-location-single")
        or soup.select_one("div.entry-content")
        or soup.select_one("div.post-content")
        or soup.select_one("article")
        or soup.body
    )

    content_text = content_el.get_text(" ", strip=True) if content_el else ""
    author = parse_post_author(soup, title=title, content_text=content_text)
    dt = parse_post_date(soup)

    attachments: list[Attachment] = []
    if content_el:
        for a in content_el.select("a[href]"):
            href = (a.get("href") or "").strip()
            if not href:
                continue
            abs_url = urljoin(url, href)
            if "/storage/" in abs_url or abs_url.lower().endswith((".pdf", ".doc", ".docx")):
                attachments.append(Attachment(url=abs_url, text=a.get_text(" ", strip=True)))

    pdf_url = ""
    for att in attachments:
        if att.url.lower().endswith(".pdf") or ".pdf" in att.url.lower():
            pdf_url = att.url
            break

    content_html = clean_content_html(content_el) if content_el else ""

    excerpt = re.sub(r"\s+", " ", content_text).strip()
    excerpt = excerpt[:320]

    slug = _slug_from_url(url)
    item_id = slug or re.sub(r"\W+", "-", title).strip("-")

    return KhutbaItem(
        id=item_id,
        title=title,
        author=author,
        date=dt,
        source_url=url,
        pdf_url=pdf_url,
        content_html=content_html,
        excerpt=excerpt,
        attachments=attachments,
    )


def iter_category_pages(base_url: str, max_pages: int) -> Iterable[str]:
    if max_pages <= 0:
        # unknown length; keep going until a page yields no new links
        # (bounded by a safety max)
        hard_cap = 200
        for i in range(1, hard_cap + 1):
            if i == 1:
                yield base_url
            else:
                yield urljoin(base_url, f"page/{i}/")
    else:
        for i in range(1, max_pages + 1):
            if i == 1:
                yield base_url
            else:
                yield urljoin(base_url, f"page/{i}/")


def main() -> int:
    ap = argparse.ArgumentParser(description="Scrape written khutab posts into local JSON.")
    ap.add_argument("--base-url", default=BASE_CATEGORY_URL, help="Category URL for written khutab")
    ap.add_argument("--out", default="data/khutab_written.json", help="Output JSON path")
    ap.add_argument("--max-pages", type=int, default=0, help="Max category pages (0 = auto)")
    ap.add_argument("--limit", type=int, default=0, help="Max posts to fetch (0 = no limit)")
    ap.add_argument("--delay", type=float, default=0.7, help="Delay seconds between requests")
    args = ap.parse_args()

    session = _make_session()

    all_post_urls: list[str] = []
    seen_posts = set()

    print(f"[1/3] Crawling category pages from: {args.base_url}")
    for page_url in iter_category_pages(args.base_url, args.max_pages):
        html = fetch_html(session, page_url)
        links = parse_category_post_links(html, base_url=args.base_url)
        new = 0
        for u in links:
            if u not in seen_posts:
                seen_posts.add(u)
                all_post_urls.append(u)
                new += 1
                if args.limit and len(all_post_urls) >= args.limit:
                    break
        print(f"  - {page_url} -> +{new} (total {len(all_post_urls)})")

        if args.limit and len(all_post_urls) >= args.limit:
            break

        # Auto-stop if page yields no new posts (only when max_pages=0)
        if args.max_pages <= 0 and new == 0:
            break

        time.sleep(args.delay)

    print(f"[2/3] Fetching {len(all_post_urls)} post pages...")
    items: list[KhutbaItem] = []
    for idx, post_url in enumerate(all_post_urls, start=1):
        try:
            html = fetch_html(session, post_url)
            item = parse_post(html, post_url)
            items.append(item)
            print(f"  - ({idx}/{len(all_post_urls)}) {item.title[:60]}")
        except Exception as e:  # noqa: BLE001
            print(f"  ! Failed: {post_url} ({e})")
        time.sleep(args.delay)

    # Sort newest first if possible
    def sort_key(it: KhutbaItem) -> str:
        return it.date.iso or ""

    items.sort(key=sort_key, reverse=True)

    payload = [
        {
            **{k: v for k, v in asdict(item).items() if k not in {"attachments", "date"}},
            "date": asdict(item.date),
            "attachments": [asdict(a) for a in item.attachments],
        }
        for item in items
    ]

    print(f"[3/3] Writing: {args.out}")
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
