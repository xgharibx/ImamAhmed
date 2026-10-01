#!/usr/bin/env python3
"""Run the real article/PDF/offline pipeline in a disposable site, never Git."""
from __future__ import annotations

import argparse
import functools
import hashlib
import html
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import shutil
import sys
import tempfile
import threading
import unicodedata
from urllib.parse import quote, urljoin
import zipfile

import article_pipeline as article
import content_pipeline as shared
import generate_app_content as offline
import verify_article_publish as verify

ROOT = Path(__file__).resolve().parents[1]
PipelineError = shared.PipelineError
FIXTURE_LINES = (
    "اختبار النشر الآمن للمقال",
    "الرحمة والعمل الصالح:",
    "الرحمة خلق كريم يجمع الناس على الخير والإحسان. نحفظ حق الجار ونصل الرحم ونرعى الضعيف، ونطلب العلم النافع ونخلص في العمل.",
    "إن حسن الخلق حياة للقلب ونور للبيوت، وهو سبيل إلى بناء مجتمع متعاون يحفظ كرامة الإنسان ويعين المحتاج ويصون الأمانة.",
    "التعاون على الخير:",
    "نتواصى بالحق والصبر، ونجمع بين العلم والعمل. كل كلمة طيبة وكل مساعدة صادقة باب من أبواب الخير وخطوة إلى مجتمع رحيم.",
    "والله المستعان",
    "آمين",
)


def require_isolated(source: Path, destination: Path) -> None:
    source, destination = source.resolve(), destination.resolve()
    if destination.is_relative_to(source) or source.is_relative_to(destination):
        raise PipelineError("Smoke paths must be outside and separate from the checkout")


def validate_output(source: Path, output: Path) -> None:
    require_isolated(source, output)
    if any((output / name).exists() for name in ("report.json", "article.pdf")):
        raise PipelineError("Smoke artifacts already exist; choose a fresh output directory")


def copy_site_resources(source: Path, root: Path) -> None:
    require_isolated(source, root)
    source, root = source.resolve(), root.resolve()
    mapped = offline.mappings(source)
    copied_mirrors = {}
    queue = [("/articles.html", "articles.html")]
    seen = set()
    while queue:
        key, relative = queue.pop()
        if key in seen:
            continue
        seen.add(key)
        path = source / relative
        target = root / relative
        if not path.resolve().is_relative_to(source) or not target.resolve().is_relative_to(root):
            raise PipelineError("Site resource escapes the isolated roots")
        if key.startswith("https://") and not relative.startswith(offline.MIRRORS):
            raise PipelineError("CDN resources must use public generated mirrors")
        if not path.is_file():
            raise PipelineError("Required smoke resource is missing: " + relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        if key.startswith("https://"):
            copied_mirrors[key] = relative
        base = key if key.startswith("https://") else urljoin(offline.SITE, quote(relative))
        for url in offline.references(path, offline.content_bytes(path), base):
            child = offline.normalize_key(url)
            if child.startswith("/"):
                queue.append((child, child.lstrip("/")))
            elif child in mapped:
                queue.append((child, mapped[child]))
            # Missing CDN mirrors are prepared only in the disposable root.
    offline.write_json(root / offline.MAPPING_FILE, copied_mirrors)


def write_fixture(path: Path) -> None:
    paragraphs = "".join('<w:p><w:pPr><w:bidi/></w:pPr><w:r><w:t xml:space="preserve">'
                         + html.escape(line) + '</w:t></w:r></w:p>' for line in FIXTURE_LINES)
    document = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                '<w:body>' + paragraphs + '<w:sectPr/></w:body></w:document>')
    types = ('<?xml version="1.0" encoding="UTF-8"?>'
             '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
             '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
             '<Default Extension="xml" ContentType="application/xml"/>'
             '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
             '</Types>')
    relationships = ('<?xml version="1.0" encoding="UTF-8"?>'
                     '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                     '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
                     '</Relationships>')
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in (("[Content_Types].xml", types), ("_rels/.rels", relationships), ("word/document.xml", document)):
            archive.writestr(name, data.encode("utf-8"))


def generate_sitemap(root: Path) -> None:
    require_isolated(ROOT, root)
    previous = shared.ROOT, shared.KHUTAB_DIR
    try:
        shared.ROOT, shared.KHUTAB_DIR = root, root / "khutab"
        shared.generate_sitemap(None)
    finally:
        shared.ROOT, shared.KHUTAB_DIR = previous


def validate_manifest_article(root: Path, manifest: dict, item: dict) -> None:
    for relative in ("articles.html", item["file"]):
        matches = [entry for entry in manifest["resources"] if entry["key"] == "/" + relative]
        digest = hashlib.sha256(offline.content_bytes(root / relative)).hexdigest()
        if len(matches) != 1 or matches[0]["path"] != relative or matches[0]["sha256"] != digest:
            raise PipelineError("Offline manifest does not contain the exact article/listing")


def validate_pdf_closing_lines(text: str) -> None:
    def compact(value):
        return "".join(c for c in unicodedata.normalize("NFKC", value)
                       if not c.isspace() and c != "ـ" and unicodedata.category(c) != "Cf")
    text = compact(text)
    for line in FIXTURE_LINES[-2:]:
        # PDF extraction can reverse RTL word order or character order.
        alternatives = (line, " ".join(reversed(line.split())), line[::-1])
        if not any(compact(candidate) in text for candidate in alternatives):
            raise PipelineError("PDF closing lines are missing")


def source_content_hashes(source: Path) -> dict:
    names = ("articles.html", "sitemap.xml", "robots.txt", "data/app-content-manifest.json")
    return {name: hashlib.sha256((source / name).read_bytes()).hexdigest() if (source / name).is_file() else None
            for name in names}


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def run_smoke(output: Path, *, source: Path = ROOT) -> dict:
    source, output = source.resolve(), output.resolve()
    validate_output(source, output)
    before = source_content_hashes(source)
    output.mkdir(parents=True, exist_ok=True)
    report = {"status": "failed", "phase": "temporary-root", "checks": {}}
    try:
        with tempfile.TemporaryDirectory(prefix="article-publish-smoke-") as temporary:
            root = Path(temporary).resolve()
            require_isolated(source, root)
            require_isolated(output, root)
            report["checks"]["isolated_temporary_root"] = True
            report["phase"] = "copy-resources"
            copy_site_resources(source, root)
            fixture = root / "fixture.docx"
            write_fixture(fixture)
            report["phase"] = "publish-article-and-real-pdf"
            item = article.publish_article(fixture, root=root, date_iso="2026-10-01")
            shutil.copyfile(root / item["pdf"], output / "article.pdf")
            report.update({"article_id": item["id"], "page_sha256": item["page_sha256"], "pdf_sha256": item["pdf_sha256"]})
            page_html = (root / item["file"]).read_text(encoding="utf-8")
            if not all(html.escape(line) in page_html for line in FIXTURE_LINES):
                raise PipelineError("Fixture text or closing lines were lost from the page")
            from pypdf import PdfReader
            text = "".join(page.extract_text() or "" for page in PdfReader(root / item["pdf"]).pages)
            validate_pdf_closing_lines(text)
            report["checks"]["fixture_text_and_pdf_closing_lines"] = True
            report["phase"] = "sitemap-and-publication-validation"
            generate_sitemap(root)
            article.validate_article_result(item, root=root)
            report["checks"]["listing_page_pdf_sitemap"] = True
            report["phase"] = "offline-manifest"
            offline.prepare_assets(root)
            manifest = offline.build_manifest(root)
            offline.write_json(root / "data/app-content-manifest.json", manifest)
            validate_manifest_article(root, manifest, item)
            if shared.read_json(root / "data/app-content-manifest.json") != offline.build_manifest(root):
                raise PipelineError("Written offline manifest is stale")
            report["checks"]["offline_article_and_listing_hashes"] = True
            report.update({"offline_revision": manifest["revision"], "offline_resources": len(manifest["resources"])})
            report["phase"] = "http-and-chromium-verification"
            handler = functools.partial(QuietHandler, directory=str(root))
            server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                base = "http://127.0.0.1:" + str(server.server_address[1])
                verify.wait_for_publication(base, item, 0)
                report["pdf_pages"] = verify.verify_browser(base, item)
                report["checks"]["http_and_real_browser_download"] = True
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
        report["checks"]["temporary_root_removed"] = not root.exists()
        if not report["checks"]["temporary_root_removed"]:
            raise PipelineError("Temporary site was not removed")
        if source_content_hashes(source) != before:
            raise PipelineError("Source content changed during the smoke run")
        report["checks"]["source_content_unchanged"] = True
        report.update({"status": "passed", "phase": "complete"})
        return report
    except Exception as error:
        report["error"] = str(error)
        raise
    finally:
        offline.write_json(output / "report.json", report)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="Fresh artifact directory outside the checkout")
    args = parser.parse_args()
    try:
        report = run_smoke(args.output)
    except Exception as error:
        print(f"ARTICLE SMOKE ERROR: {error}", file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
