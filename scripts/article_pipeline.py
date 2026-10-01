#!/usr/bin/env python3
"""Publish a DOCX article, matching listing card, and Arabic-shaped static PDF."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from xml.etree import ElementTree as ET

import content_pipeline as shared

ROOT = shared.ROOT
TEMPLATE = ROOT / "templates" / "article-publishing" / "ramadan-article-template.html"
PipelineError = shared.PipelineError


class ArticleListingParser(HTMLParser):
    """Locate the active grid without reserializing or altering existing markup."""
    def __init__(self, source: str):
        super().__init__(convert_charrefs=True)
        self.source = source
        self.line_offsets = [0]
        for line in source.splitlines(keepends=True):
            self.line_offsets.append(self.line_offsets[-1] + len(line))
        self.stack: list[str] = []
        self.grid_depth = 0
        self.insertions: list[int] = []
        self.cards: list[dict] = []
        self.card: dict | None = None
        self.title_depth = 0
        self.feed(source)
        self.close()

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        classes = (values.get("class") or "").split()
        if "newspaper-articles-grid" in classes:
            if self.grid_depth:
                raise PipelineError("Nested article listing grid")
            line, column = self.getpos()
            self.insertions.append(self.line_offsets[line - 1] + column + len(self.get_starttag_text()))
            self.grid_depth = len(self.stack) + 1
        if self.grid_depth and tag == "article" and "newspaper-article-card" in classes:
            self.card = {"id": values.get("data-article-id", ""), "title": "", "hrefs": [],
                         "content_sha256": values.get("data-content-sha256", "")}
            self.cards.append(self.card)
        if self.card and "newspaper-title" in classes:
            self.title_depth = len(self.stack) + 1
        if self.card and tag == "a":
            self.card["hrefs"].append(values.get("href", ""))
        if tag not in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag not in self.stack:
            return
        index = len(self.stack) - 1 - self.stack[::-1].index(tag)
        if self.title_depth and index < self.title_depth:
            self.title_depth = 0
        if tag == "article":
            self.card = None
        if self.grid_depth and index < self.grid_depth:
            self.grid_depth = 0
        del self.stack[index:]

    def handle_data(self, text):
        if self.card and self.title_depth:
            self.card["title"] += text


def prepare_article_docx(path: Path) -> dict:
    paragraphs = shared.extract_docx_paragraphs(path, min_paragraphs=3, min_characters=80, content_label="المقال")
    labels = {"عنوانالمقال", "مقالتحتعنوان", "مقالبعنوان", "عنوان"}
    title = ""
    title_index = -1
    for index, line in enumerate(paragraphs):
        normalized = shared.normalize_arabic(line).strip(" :：")
        if normalized in labels or normalized.startswith(("بسمالله", "بقلم", "لفضيله")):
            continue
        title = re.sub(r"^(?:عنوان المقال|مقال تحت عنوان|مقال بعنوان)\s*[:：]?\s*", "", line).strip(' «»"')
        title_index = index
        break
    if not 5 <= len(title) <= 300:
        raise PipelineError("عنوان المقال يجب أن يكون بين 5 و300 حرف")
    body = [line for index, line in enumerate(paragraphs) if index != title_index]
    excerpt_lines = [line for line in body if len(line) >= 40 and not shared.normalize_arabic(line).startswith(("بقلم", "بسمالله"))]
    excerpt = shared.compact_excerpt(excerpt_lines[0] if excerpt_lines else " ".join(body))
    if len(excerpt) < 20:
        raise PipelineError("متن المقال لا يكفي لبطاقة النشر")
    digest = hashlib.sha256(json.dumps(paragraphs, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()
    return {"title": title, "excerpt": excerpt, "paragraphs": paragraphs, "body_paragraphs": body,
            "content_sha256": digest}


def render_page(article: dict) -> str:
    body = []
    for line in article["body_paragraphs"]:
        heading = len(line) <= 95 and (line.endswith(":") or (line.startswith("(") and line.endswith(")")))
        tag, css = ("h2", "section-title") if heading else ("p", "text-content")
        body.append(f'            <{tag} class="{css}">{html.escape(line)}</{tag}>')
    values = {"PAGE_TITLE": html.escape(article["title"], quote=True),
              "META_DESCRIPTION": html.escape(article["excerpt"], quote=True),
              "AUTHOR": html.escape(shared.DEFAULT_AUTHOR), "BACK_TEXT": "عودة إلى المقالات",
              "CANONICAL_URL": f'{shared.SITE_URL}/{article["file"]}', "ARTICLE_ID": article["id"],
              "CONTENT_SHA256": article["content_sha256"], "PDF_FILENAME": Path(article["pdf"]).name,
              "BODY_HTML": "\n".join(body)}
    def replace(match):
        key = match.group(1)
        if key not in values:
            raise PipelineError(f"Unknown article template token: {key}")
        return values[key]
    return re.sub(r"\{\{([A-Z0-9_]+)\}\}", replace, TEMPLATE.read_text(encoding="utf-8")).rstrip() + "\n"


def render_card(article: dict) -> str:
    return f'''
                <article class="newspaper-article-card" data-aos="fade-up" data-article-id="{article['id']}" data-content-sha256="{article['content_sha256']}">
                    <div class="newspaper-badge"><i class="fas fa-scroll"></i> مقالات عامة</div>
                    <div class="newspaper-content">
                        <h3 class="newspaper-title">{html.escape(article['title'])}</h3>
                        <p class="newspaper-excerpt">{html.escape(article['excerpt'])}</p>
                        <div class="newspaper-meta"><span><i class="fas fa-book"></i> مقالات عامة</span></div>
                        <div class="pdf-action-group">
                            <a href="{article['file']}" class="btn btn-outline btn-sm pdf-action-btn"><i class="fas fa-external-link-alt"></i> اقرأ المزيد</a>
                            <a href="{article['pdf']}" class="js-download-pdf btn btn-outline btn-sm pdf-action-btn" download><i class="fas fa-download"></i> تحميل PDF</a>
                        </div>
                    </div>
                </article>
'''


def validate_pdf(path: Path) -> int:
    from pypdf import PdfReader
    if not path.is_file() or not path.read_bytes().startswith(b"%PDF-"):
        raise PipelineError("ملف PDF غير صالح")
    try:
        reader = PdfReader(path)
        if not reader.pages or not any((page.extract_text() or "").strip() for page in reader.pages):
            raise PipelineError("ملف PDF فارغ أو بلا نص قابل للقراءة")
        for page in reader.pages:
            contents = page.get_contents()
            if contents is None or not contents.get_data().strip():
                raise PipelineError("صفحة PDF فارغة")
        return len(reader.pages)
    except PipelineError:
        raise
    except Exception as error:
        raise PipelineError("تعذر التحقق من ملف PDF") from error


def render_pdf(page_path: Path, pdf_path: Path) -> None:
    from playwright.sync_api import sync_playwright
    try:
        with sync_playwright() as playwright:
            channel = os.environ.get("ARTICLE_CHROMIUM_CHANNEL")
            browser = playwright.chromium.launch(**({"channel": channel} if channel else {}))
            try:
                page = browser.new_page(viewport={"width": 900, "height": 1000})
                page.goto(page_path.resolve().as_uri(), wait_until="networkidle", timeout=60000)
                page.emulate_media(media="print")
                if not page.evaluate("async () => { await document.fonts.ready; return (await document.fonts.load('18px Amiri')).length > 0; }"):
                    raise PipelineError("تعذر تحميل خط Amiri العربي؛ لم يتم نشر PDF")
                page.pdf(path=str(pdf_path), format="A4", print_background=True,
                         margin={"top": "12mm", "bottom": "12mm", "left": "10mm", "right": "10mm"})
            finally:
                browser.close()
        validate_pdf(pdf_path)
    except PipelineError:
        raise
    except Exception as error:
        raise PipelineError(f"تعذر إنشاء PDF العربي: {error}") from error


def publish_article(docx: Path, *, root: Path = ROOT, date_iso: str = "") -> dict:
    prepared = prepare_article_docx(Path(docx))
    article_id = "article-" + hashlib.sha256(shared.normalize_arabic(prepared["title"]).encode("utf-8")).hexdigest()[:16]
    article = {**prepared, "kind": "article", "id": article_id,
               "date": shared.validate_iso_date(date_iso or dt.datetime.now(dt.timezone.utc).date().isoformat()),
               "file": f"books/{article_id}.html", "pdf": f"books/{article_id}.pdf"}
    listing_path = root / "articles.html"
    original = listing_path.read_bytes()
    listing = original.decode("utf-8")
    parser = ArticleListingParser(listing)
    if len(parser.insertions) != 1:
        raise PipelineError("يجب وجود شبكة مقالات فعالة واحدة")
    if any(shared.normalize_arabic(card["title"]) == shared.normalize_arabic(article["title"])
           or card["id"] == article_id or card["content_sha256"] == article["content_sha256"] for card in parser.cards):
        raise PipelineError("المقال موجود بالفعل؛ لم يتم تكراره")
    page_path, pdf_path = root / article["file"], root / article["pdf"]
    if page_path.exists() or pdf_path.exists():
        raise PipelineError("ملفات المقال موجودة بالفعل؛ لن يتم استبدالها")
    page_html = render_page(article)
    offset = parser.insertions[0]
    updated = listing[:offset] + render_card(article) + listing[offset:]
    page_path.parent.mkdir(parents=True, exist_ok=True)
    stage = None
    staged_pdf = None
    created = []
    listing_stage = None
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".html", prefix=".article-stage-", dir=page_path.parent,
                                         encoding="utf-8", newline="\n", delete=False) as handle:
            handle.write(page_html)
            stage = Path(handle.name)
        staged_pdf = stage.with_suffix(".pdf")
        render_pdf(stage, staged_pdf)
        if listing_path.read_bytes() != original:
            raise PipelineError("قائمة المقالات تغيرت أثناء النشر؛ أعد المحاولة")
        with tempfile.NamedTemporaryFile("w", dir=root, encoding="utf-8", newline="\n", delete=False) as handle:
            handle.write(updated)
            listing_stage = Path(handle.name)
        stage.replace(page_path)
        created.append(page_path)
        staged_pdf.replace(pdf_path)
        created.append(pdf_path)
        listing_stage.replace(listing_path)
    except Exception:
        for path in created:
            path.unlink(missing_ok=True)
        raise
    finally:
        for path in (stage, staged_pdf, listing_stage):
            if path:
                path.unlink(missing_ok=True)
    return {key: value for key, value in article.items() if key not in {"paragraphs", "body_paragraphs"}} | {
        "page_sha256": hashlib.sha256(page_path.read_bytes()).hexdigest(),
        "pdf_sha256": hashlib.sha256(pdf_path.read_bytes()).hexdigest()}


def validate_target(item: dict) -> None:
    if item.get("kind") != "article" or not re.fullmatch(r"article-[a-z0-9-]+", item.get("id", "")):
        raise PipelineError("نتيجة النشر ليست مقالا صالحا")
    for key, suffix in (("file", ".html"), ("pdf", ".pdf")):
        if item.get(key) != f'books/{item["id"]}{suffix}':
            raise PipelineError("مسار المقال غير صالح")
    for key in ("page_sha256", "pdf_sha256"):
        if not re.fullmatch(r"[0-9a-f]{64}", item.get(key, "")):
            raise PipelineError("بصمة ملف المقال مفقودة")


def validate_article_result(item: dict, *, root: Path = ROOT) -> dict:
    validate_target(item)
    parser = ArticleListingParser((root / "articles.html").read_text(encoding="utf-8"))
    cards = [card for card in parser.cards if card["id"] == item["id"]]
    if len(parser.insertions) != 1 or len(cards) != 1 or any(item[key] not in cards[0]["hrefs"] for key in ("file", "pdf")):
        raise PipelineError("بطاقة المقال أو روابطها مفقودة أو مكررة")
    if shared.normalize_arabic(cards[0]["title"]) != shared.normalize_arabic(item["title"]):
        raise PipelineError("عنوان البطاقة لا يطابق المقال")
    for key, digest in (("file", "page_sha256"), ("pdf", "pdf_sha256")):
        if hashlib.sha256((root / item[key]).read_bytes()).hexdigest() != item[digest]:
            raise PipelineError("ملف المقال لا يطابق نتيجة النشر")
    locations = [node.text for node in ET.parse(root / "sitemap.xml").getroot().iter() if node.tag.rsplit("}", 1)[-1] == "loc"]
    if f'{shared.SITE_URL}/{item["file"]}' not in locations:
        raise PipelineError("المقال غير موجود في sitemap.xml")
    return {"id": item["id"], "file": item["file"], "pdf": item["pdf"]}


def publish_issue(event_path: Path, *, root: Path = ROOT) -> dict:
    issue = (shared.read_json(Path(event_path)).get("issue") or {})
    if issue.get("author_association") not in {"OWNER", "MEMBER", "COLLABORATOR"}:
        raise PipelineError("هذا الحساب غير مصرح له بنشر المقالات")
    if not str(issue.get("title", "")).startswith("[نشر مقال]"):
        raise PipelineError("نوع طلب النشر ليس مقالا")
    sections = shared.parse_issue_sections(str(issue.get("body") or ""))
    attachment = shared.download_docx(shared.extract_attachment_url(sections.get("ملف Word", "")))
    try:
        created = str(issue.get("created_at") or "")[:10]
        return publish_article(attachment, root=root, date_iso=created)
    finally:
        attachment.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    commands = parser.add_subparsers(dest="command", required=True)
    publish = commands.add_parser("publish")
    publish.add_argument("--docx", type=Path, required=True)
    publish.add_argument("--date", default="")
    issue = commands.add_parser("publish-issue")
    issue.add_argument("--event", type=Path, required=True)
    validate = commands.add_parser("validate-result")
    validate.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "publish":
            result = publish_article(args.docx, root=args.root, date_iso=args.date)
        elif args.command == "publish-issue":
            result = publish_issue(args.event, root=args.root)
        else:
            result = validate_article_result(shared.read_json(args.result), root=args.root)
    except (PipelineError, OSError, ValueError, ET.ParseError) as error:
        print(f"ARTICLE PIPELINE ERROR: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
