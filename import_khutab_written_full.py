import argparse
import json
import os
import re
import time
import shutil
import unicodedata
from dataclasses import asdict
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse

import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import requests
from bs4 import BeautifulSoup

from requests.utils import requote_uri

from scrape_khutab_written import (
    BASE_CATEGORY_URL,
    KhutbaItem,
    _make_session,
    fetch_html,
    parse_category_post_links,
    parse_post,
)


PAGE_1 = BASE_CATEGORY_URL
PAGE_2 = urljoin(BASE_CATEGORY_URL, "page/2/")

INVISIBLE_MARKS_RE = re.compile(r"[\u200e\u200f\u202a-\u202e\u2066-\u2069\ufeff]")
KHUTBA_TITLE_RE = re.compile(r"(?:^|\b)(?:خطبة|خ\s*ُ?ط\s*ْ?ب\s*َ?ة)\b", re.UNICODE)
TESSERACT_CANDIDATES = [
    Path(r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"),
    Path(r"C:\\Program Files (x86)\\Tesseract-OCR\\tesseract.exe"),
]
TESSERACT_READY = False
LOCAL_TESSDATA = Path(__file__).parent / "tessdata"


def clean_arabic_text(text: str) -> str:
    """Clean extracted Arabic text for display.

    This function is intentionally conservative: it removes invisible direction
    marks and normalizes whitespace, but preserves Arabic diacritics (tashkeel)
    for fidelity.
    """

    if not text:
        return ""

    # Remove directional/invisible marks first
    text = INVISIBLE_MARKS_RE.sub("", text)

    # Normalize Unicode composition without dropping marks
    text = unicodedata.normalize("NFC", text)

    # Split and clean per-line to avoid runaway spaces
    lines: list[str] = []
    for raw_line in text.splitlines():
        # Keep diacritics; only normalize whitespace
        normalized = re.sub(r"[ \t]+", " ", raw_line)
        normalized = normalized.strip()
        if normalized:
            lines.append(normalized)

    cleaned = "\n".join(lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def normalize_arabic_for_search(text: str) -> str:
    """Normalize Arabic for search/indexing (drops diacritics + tatweel)."""

    if not text:
        return ""

    text = INVISIBLE_MARKS_RE.sub("", text)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("ـ", "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def safe_filename(name: str) -> str:
    name = name.strip().replace(" ", "-")
    name = re.sub(r"[^0-9A-Za-z\u0600-\u06FF._-]+", "-", name)
    name = re.sub(r"-+", "-", name).strip("-._")
    return name or "khutba"


def download_file(session: requests.Session, url: str, dest: Path, timeout: int = 60) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with session.get(url, timeout=timeout, stream=True) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 64):
                if chunk:
                    f.write(chunk)


def download_pdf_with_fallback(
    session: requests.Session, pdf_url: str, dest: Path, timeout: int = 60
) -> str:
    """Downloads a PDF, trying the original URL first.

    The source site sometimes includes invisible Unicode direction marks in the
    stored filename. Removing them can cause 404s, so we try multiple variants.
    Returns the URL variant that succeeded.
    """

    candidates: list[str] = []

    raw = (pdf_url or "").strip()
    if raw:
        candidates.append(raw)
        candidates.append(requote_uri(raw))

    # Variant: strip invisible marks from the URL string.
    if raw:
        stripped = INVISIBLE_MARKS_RE.sub("", raw)
        candidates.append(stripped)
        candidates.append(requote_uri(stripped))

    # Variant: decode percent-encoding, strip invisible marks, then re-quote.
    # This catches cases like %E2%80%8E (LRM) inside filenames.
    if raw:
        try:
            from urllib.parse import unquote

            decoded = unquote(raw)
            decoded_stripped = INVISIBLE_MARKS_RE.sub("", decoded)
            candidates.append(decoded)
            candidates.append(requote_uri(decoded))
            candidates.append(decoded_stripped)
            candidates.append(requote_uri(decoded_stripped))
        except Exception:
            pass

    # Deduplicate while keeping order.
    seen: set[str] = set()
    ordered: list[str] = []
    for c in candidates:
        c = (c or "").strip()
        if c and c not in seen:
            seen.add(c)
            ordered.append(c)

    last_error: Optional[Exception] = None
    for candidate in ordered:
        try:
            download_file(session, candidate, dest, timeout=timeout)
            return candidate
        except Exception as e:
            last_error = e
            continue

    if last_error:
        raise last_error
    raise RuntimeError("No PDF URL candidates")


def sanitize_url(url: str) -> str:
    url = (url or "").strip()
    url = INVISIBLE_MARKS_RE.sub("", url)
    # requests will quote unsafe characters, but we also avoid breaking already-quoted urls
    url = requote_uri(url)
    return url


def extract_pdf_text(pdf_path: Path) -> str:
    """Extract text preferring embedded text, with OCR fallback for scanned PDFs."""

    def normalize_block_text(raw_text: str) -> str:
        raw_text = INVISIBLE_MARKS_RE.sub("", raw_text or "")
        lines = [re.sub(r"\s+", " ", ln).strip() for ln in raw_text.splitlines()]
        lines = [ln for ln in lines if ln]
        return " ".join(lines).strip()

    def extract_words() -> str:
        doc = fitz.open(pdf_path)
        page_lines: list[tuple[float, str]] = []
        for page in doc:
            words = page.get_text("words")  # (x0, y0, x1, y1, word, block_no, line_no, word_no)
            if not words:
                continue
            # group by (block, line)
            lines_map: dict[tuple[int, int], list[tuple[float, float, str]]] = {}
            for x0, y0, x1, y1, w, bno, lno, wno in words:
                if not w or not str(w).strip():
                    continue
                key = (int(bno), int(lno))
                lines_map.setdefault(key, []).append((x0, x1, str(w)))

            # order lines by their vertical position; approximate via min y0 per line from words
            # Re-fetch y via bbox averaging per line: using first word y0 from the words list
            # Since get_text("words") doesn't include line y in grouping, we sort keys by min x0's y is not available here
            # We'll reconstruct line text and then order by the smallest x0 encountered; combine with page.y0 via page number to keep flow
            # Simpler: accumulate lines per page maintaining input order of words by y0; but 'words' already roughly sorted top-to-bottom
            # So we instead build an ordered list using the first word appearance per (bno,lno) as encountered
            seen_line_keys: set[tuple[int, int]] = set()
            ordered_keys: list[tuple[int, int]] = []
            for x0, y0, x1, y1, w, bno, lno, wno in words:
                key = (int(bno), int(lno))
                if key not in seen_line_keys:
                    seen_line_keys.add(key)
                    ordered_keys.append(key)

            arabic_ranges = [
                (0x0600, 0x06FF),
                (0x0750, 0x077F),
                (0x08A0, 0x08FF),
                (0xFB50, 0xFDFF),
                (0xFE70, 0xFEFF),
            ]

            def is_arabic_char(ch: str) -> bool:
                cp = ord(ch)
                for a, b in arabic_ranges:
                    if a <= cp <= b:
                        return True
                return False

            def is_single_arabic_token(tok: str) -> bool:
                tok = tok.strip()
                return len(tok) == 1 and all(is_arabic_char(c) for c in tok)

            for key in ordered_keys:
                entries = lines_map.get(key, [])
                # RTL: sort by x0 descending so words on the right appear first
                entries.sort(key=lambda t: -t[0])
                built: list[str] = []
                buffer = ""
                prev_single = False
                for x0, x1, tok in entries:
                    tok = tok.strip()
                    if not tok:
                        continue
                    current_single = is_single_arabic_token(tok)
                    if prev_single and current_single:
                        buffer += tok
                    else:
                        if buffer:
                            built.append(buffer)
                        buffer = tok
                    prev_single = current_single
                if buffer:
                    built.append(buffer)

                text_line = " ".join(part for part in built if part)
                text_line = normalize_block_text(text_line)
                if text_line:
                    # Keep page-relative order
                    page_lines.append((page.number + (len(page_lines) * 1e-6), text_line))

        doc.close()
        # Sort primarily by the captured order (already stable per page); the first element keeps insertion order by page.number
        page_lines.sort(key=lambda t: t[0])
        text = "\n".join(line for _, line in page_lines)
        return re.sub(r"\n{3,}", "\n\n", text).strip()

    def extract_blocks() -> str:
        doc = fitz.open(pdf_path)
        collected: list[str] = []
        for page in doc:
            blocks = page.get_text(
                "blocks",
                flags=fitz.TEXT_PRESERVE_LIGATURES | fitz.TEXT_PRESERVE_WHITESPACE,
            )
            blocks = sorted(blocks, key=lambda b: (round(b[1], 2), -round(b[0], 2)))
            for block in blocks:
                if len(block) < 5:
                    continue
                text_part = normalize_block_text(block[4] or "")
                if text_part:
                    collected.append(text_part)
        doc.close()
        text = "\n\n".join(collected)
        return re.sub(r"\n{3,}", "\n\n", text).strip()

    def ensure_tesseract():
        global TESSERACT_READY
        if TESSERACT_READY:
            return

        candidate = shutil.which("tesseract")
        for p in TESSERACT_CANDIDATES:
            if p.exists():
                candidate = candidate or str(p)
                break

        if not candidate:
            raise RuntimeError("Tesseract is not installed or not on PATH")

        pytesseract.pytesseract.tesseract_cmd = candidate

        data_dirs: list[Path] = []
        env_dir = os.environ.get("TESSDATA_PREFIX", "").strip()
        if env_dir:
            data_dirs.append(Path(env_dir))

        exe_dir = Path(candidate).resolve().parent
        data_dirs.append(exe_dir / "tessdata")
        data_dirs.append(LOCAL_TESSDATA)

        for data_dir in data_dirs:
            trained = data_dir / "ara.traineddata"
            if trained.exists():
                os.environ["TESSDATA_PREFIX"] = str(data_dir)
                TESSERACT_READY = True
                return

        raise RuntimeError("Tesseract Arabic data (ara.traineddata) not found. Place it under tessdata/")

    def ocr_pdf() -> str:
        ensure_tesseract()
        parts: list[str] = []
        doc = fitz.open(pdf_path)
        for page in doc:
            mat = fitz.Matrix(4, 4)  # higher DPI for better Arabic OCR
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            text = pytesseract.image_to_string(img, lang="ara", config="--psm 4 --oem 3")
            text = INVISIBLE_MARKS_RE.sub("", text)
            text = re.sub(r"\n{3,}", "\n\n", text)
            text = re.sub(r"[ \t]{2,}", " ", text)
            if text.strip():
                parts.append(text.strip())
        doc.close()
        text = "\n\n".join(parts)
        return re.sub(r"\n{3,}", "\n\n", text).strip()

    # 1) Try embedded text first (words-based, then blocks)
    try:
        embedded_words = extract_words()
        if embedded_words:
            return clean_arabic_text(embedded_words)
        embedded_blocks = extract_blocks()
        if embedded_blocks:
            return clean_arabic_text(embedded_blocks)
    except Exception as e:
        print(f"  ! PDF text extraction fallback to OCR: {e}")

    # 2) Fallback to OCR for scanned/image PDFs
    try:
        return clean_arabic_text(ocr_pdf())
    except Exception as e:
        print(f"  ! PDF OCR error: {e}")
        return ""


def text_to_html(text: str) -> str:
    """Convert plain text khutba content to structured HTML.

    Produces headings and lists when obvious patterns exist (e.g. "عناصر الخطبة",
    numbered points, bullet points, "الخطبة الأولى/الثانية").
    """

    if not (text or "").strip():
        return ""

    lines = [ln.rstrip() for ln in text.splitlines()]
    out: list[str] = []

    paragraph_lines: list[str] = []
    list_mode: str | None = None  # "ol" | "ul"
    list_items: list[str] = []

    arabic_digit_re = r"0-9\u0660-\u0669"
    re_numbered = re.compile(rf"^(?P<n>[{arabic_digit_re}]+)\s*[\.|\)|\-|–|—]\s*(?P<body>.+)$")
    re_bullet = re.compile(r"^(?:\*|•|\u2022|-)\s+(?P<body>.+)$")
    re_heading = re.compile(
        r"^(?P<h>عناصر\s+الخطبة|الخطبة\s+(?:الأولى|الاولى)|الخطبة\s+الثانية|الدعاء|الموضوع)\s*[:：]?\s*(?P<rest>.*)$"
    )

    in_outline_section = False

    def flush_paragraph() -> None:
        nonlocal paragraph_lines
        if not paragraph_lines:
            return
        cleaned_lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in paragraph_lines if ln.strip()]
        if not cleaned_lines:
            paragraph_lines = []
            return
        if len(cleaned_lines) == 1:
            out.append(f'<p class="khutba-paragraph">{escape_html(cleaned_lines[0])}</p>')
        else:
            content = "<br>\n".join(escape_html(ln) for ln in cleaned_lines)
            out.append(f'<p class="khutba-paragraph">{content}</p>')
        paragraph_lines = []

    def flush_list() -> None:
        nonlocal list_mode, list_items
        if not list_mode or not list_items:
            list_mode = None
            list_items = []
            return
        tag = "ol" if list_mode == "ol" else "ul"
        css = "khutba-list khutba-list-ordered" if tag == "ol" else "khutba-list khutba-list-bullets"
        items_html = "\n".join(f"<li>{it}</li>" for it in list_items)
        out.append(f'<{tag} class="{css}">\n{items_html}\n</{tag}>')
        list_mode = None
        list_items = []

    for raw in lines:
        s = (raw or "").strip()
        s_norm = normalize_arabic_for_search(s)

        # Paragraph/list boundary
        if not s:
            flush_paragraph()
            flush_list()
            in_outline_section = False
            continue

        # Section headings
        m_head = re_heading.match(s_norm)
        if m_head:
            flush_paragraph()
            flush_list()
            heading_norm = (m_head.group("h") or "").strip()

            # Preserve original text (with tashkeel) after the first ':' if present
            rest = ""
            for sep in (":", "："):
                if sep in s:
                    rest = s.split(sep, 1)[1].strip()
                    break

            # Canonicalize common headings for consistent display
            if "عناصر" in heading_norm:
                out.append('<h2 class="khutba-heading">عناصر الخطبة</h2>')
                in_outline_section = True
            elif "الخطبة" in heading_norm and "الثانية" in heading_norm:
                out.append('<h2 class="khutba-heading">الخطبة الثانية</h2>')
                in_outline_section = False
            elif "الخطبة" in heading_norm:
                out.append('<h2 class="khutba-heading">الخطبة الأولى</h2>')
                in_outline_section = False
            elif "الدعاء" in heading_norm:
                out.append('<h2 class="khutba-heading">الدعاء</h2>')
                in_outline_section = False
            else:
                out.append('<h2 class="khutba-heading">الموضوع</h2>')
                in_outline_section = False

            if rest:
                paragraph_lines = [rest]
                flush_paragraph()
            continue

        # Numbered lists
        m_num = re_numbered.match(s)
        if m_num:
            flush_paragraph()
            n_raw = m_num.group("n").strip()
            body = m_num.group("body").strip()

            # داخل "عناصر الخطبة" نعرضها كقائمة مرتبة، وخارجها نجعلها عنوانًا فرعيًا.
            if in_outline_section:
                if list_mode not in ("ol", None):
                    flush_list()
                list_mode = "ol"
                list_items.append(escape_html(body))
            else:
                flush_list()
                out.append(
                    f'<h3 class="khutba-subheading">{escape_html(n_raw)}. {escape_html(body)}</h3>'
                )
            continue

        # Bullet lists
        m_bul = re_bullet.match(s)
        if m_bul:
            flush_paragraph()
            if list_mode not in ("ul", None):
                flush_list()
            list_mode = "ul"
            list_items.append(escape_html(m_bul.group("body").strip()))
            continue

        # Default: accumulate paragraph lines
        # If we're currently in a list and encounter normal text, close the list.
        if list_mode:
            flush_list()
        paragraph_lines.append(s)

    flush_paragraph()
    flush_list()

    return "\n".join(out)


def escape_html(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#039;")
    )


def guess_pdf_url(item: KhutbaItem) -> str:
    # Keep the original URL as-is; some valid filenames include invisible marks.
    if getattr(item, "pdf_url", ""):
        return (item.pdf_url or "").strip()
    for att in item.attachments:
        u = (att.url or "").strip()
        if u.lower().endswith(".pdf") or ".pdf" in u.lower():
            return u
    return ""


def normalize_author(author: str) -> str:
    author = (author or "").strip()
    author = re.sub(r"\s+", " ", author)
    # Normalize common variations for display
    author = author.replace("أَحْمَدَ", "أحمد").replace("إِسْمَاعِيلَ", "إسماعيل")
    author = author.replace("الْفَشَنِيِّ", "الفشني")
    return author


def main() -> int:
    ap = argparse.ArgumentParser(description="Import all written khutab: download PDFs, extract text, write local JSON.")
    ap.add_argument("--out", default="data/khutab_written.json", help="Output JSON")
    ap.add_argument("--pdf-dir", default="khutab_pdfs", help="Local folder to store PDFs")
    ap.add_argument(
        "--missing-report",
        default="data/khutab_written_missing_pdfs.json",
        help="Write a report of posts whose PDF links fail (e.g., 404)",
    )
    ap.add_argument(
        "--include-missing",
        action="store_true",
        help="Include items even if the PDF link is missing (content will be empty)",
    )
    ap.add_argument("--delay", type=float, default=0.5, help="Delay between requests")
    ap.add_argument("--force", action="store_true", help="Re-download PDFs even if present")
    args = ap.parse_args()

    session = _make_session()

    pages = [PAGE_1, PAGE_2]
    post_urls: list[str] = []
    seen = set()

    print("[1/4] Collecting post URLs from 2 pages...")
    for p in pages:
        html = fetch_html(session, p)
        for u in parse_category_post_links(html, base_url=p):
            if u not in seen:
                seen.add(u)
                post_urls.append(u)
        print(f"  - {p} -> total {len(post_urls)}")
        time.sleep(args.delay)

    print(f"[2/4] Fetching posts and extracting PDF links ({len(post_urls)})...")
    items: list[dict] = []
    missing: list[dict] = []

    imported = 0
    skipped_not_khutba = 0
    skipped_no_pdf = 0
    failed_pdf = 0

    pdf_dir = Path(args.pdf_dir)

    for idx, post_url in enumerate(post_urls, start=1):
        try:
            html = fetch_html(session, post_url)
            parsed: KhutbaItem = parse_post(html, post_url)

            pdf_url = guess_pdf_url(parsed)

            # Filter to khutba items only (avoid unrelated site posts)
            title_text = (parsed.title or "").strip()
            if not KHUTBA_TITLE_RE.search(title_text):
                skipped_not_khutba += 1
                print(f"  - ({idx}/{len(post_urls)}) SKIP (not khutba): {title_text[:55]}")
                continue
            if not pdf_url:
                # We only import written khutab PDFs for this section
                skipped_no_pdf += 1
                print(f"  - ({idx}/{len(post_urls)}) SKIP (no pdf): {title_text[:55]}")
                continue

            slug = parsed.id or safe_filename(urlparse(post_url).path.split("/")[-1])
            filename = safe_filename(slug) + ".pdf"
            local_pdf_path = pdf_dir / filename
            local_pdf_rel = f"{pdf_dir.as_posix()}/{filename}"

            content_text = ""
            # Never store external links/content. We only render extracted PDF text (or show the embedded local PDF).
            content_html = ""

            if pdf_url:
                if args.force or not local_pdf_path.exists():
                    try:
                        download_pdf_with_fallback(session, pdf_url, local_pdf_path)
                    except Exception as e:
                        failed_pdf += 1
                        status_code = None
                        if isinstance(e, requests.HTTPError) and getattr(e, "response", None) is not None:
                            status_code = e.response.status_code
                        missing.append(
                            {
                                "post_url": post_url,
                                "title": parsed.title,
                                "pdf_url": pdf_url,
                                "status_code": status_code,
                                "error": str(e),
                            }
                        )
                        print(f"  ! ({idx}/{len(post_urls)}) MISSING PDF: {title_text[:55]} ({status_code})")
                        if args.include_missing:
                            # Keep the record but with no local PDF/content.
                            items.append(
                                {
                                    "id": parsed.id,
                                    "title": parsed.title,
                                    "author": normalize_author(parsed.author),
                                    "date": asdict(parsed.date),
                                    "pdf_local": "",
                                    "content_text": "",
                                    "content_html": "",
                                    "excerpt": parsed.excerpt,
                                    "missing_pdf": True,
                                }
                            )
                            imported += 1
                        continue
                content_text = extract_pdf_text(local_pdf_path)

                # Prefer extracted PDF text, fallback to parsed HTML if PDF extraction fails
                if content_text.strip():
                    content_html = text_to_html(content_text)

            item = {
                "id": parsed.id,
                "title": parsed.title,
                "author": normalize_author(parsed.author),
                "date": asdict(parsed.date),
                "pdf_local": local_pdf_rel if pdf_url else "",
                "content_text": content_text,
                "content_html": content_html,
                "excerpt": parsed.excerpt,
            }

            items.append(item)
            imported += 1
            print(f"  - ({idx}/{len(post_urls)}) OK: {parsed.title[:55]}")
        except Exception as e:
            print(f"  ! ({idx}/{len(post_urls)}) FAIL: {post_url} ({e})")

        time.sleep(args.delay)

    # Sort newest first when possible
    items.sort(key=lambda x: (x.get("date", {}).get("iso") or ""), reverse=True)

    print(f"[3/4] Writing JSON: {args.out}")
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    if args.missing_report:
        print(f"[3b/4] Writing missing-PDF report: {args.missing_report}")
        miss_path = Path(args.missing_report)
        miss_path.parent.mkdir(parents=True, exist_ok=True)
        with open(miss_path, "w", encoding="utf-8") as f:
            json.dump(missing, f, ensure_ascii=False, indent=2)

    # Simple extraction report
    extracted = sum(1 for x in items if (x.get("content_text") or "").strip())
    pdfs = sum(1 for x in items if (x.get("pdf_local") or "").strip())
    print(f"[4/4] Done. PDFs: {pdfs}, extracted text: {extracted}.")

    print(
        "Summary: "
        f"collected={len(post_urls)}, imported={imported}, "
        f"skipped_not_khutba={skipped_not_khutba}, skipped_no_pdf={skipped_no_pdf}, "
        f"missing_pdf={failed_pdf}."
    )

    if pdfs and extracted == 0:
        print("Note: PDFs may be image-based; OCR would be required for text.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
