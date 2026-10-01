#!/usr/bin/env python3
"""Confirm the article's active card, exact page, and downloadable static PDF."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from article_pipeline import ArticleListingParser, PipelineError, validate_pdf, validate_target
from content_pipeline import read_json


def wait_for_publication(base_url: str, item: dict, seconds: int) -> None:
    validate_target(item)
    root = base_url.rstrip("/") + "/"
    deadline = time.monotonic() + seconds
    last_error = "البطاقة أو الصفحة أو PDF لم يظهر بعد"
    while True:
        try:
            nonce = str(time.time_ns())
            blobs = []
            for path in ("articles.html", item["file"], item["pdf"]):
                request = urllib.request.Request(urllib.parse.urljoin(root, path) + "?verify=" + nonce,
                                                 headers={"Cache-Control": "no-cache", "User-Agent": "ArticlePublishCheck/1.0"})
                with urllib.request.urlopen(request, timeout=30) as response:
                    blobs.append(response.read())
            listing = ArticleListingParser(blobs[0].decode("utf-8"))
            cards = [card for card in listing.cards if card["id"] == item["id"]]
            if (len(listing.insertions) == 1 and len(cards) == 1
                    and all(item[key] in cards[0]["hrefs"] for key in ("file", "pdf"))
                    and hashlib.sha256(blobs[1]).hexdigest() == item["page_sha256"]
                    and hashlib.sha256(blobs[2]).hexdigest() == item["pdf_sha256"]):
                return
        except (urllib.error.URLError, TimeoutError, ValueError) as error:
            last_error = str(error)
        if time.monotonic() >= deadline:
            raise PipelineError(f"لم يتم تأكيد نشر المقال: {last_error}")
        time.sleep(min(10, max(0, deadline - time.monotonic())))


def inspect_browser(page, base_url: str, item: dict) -> int:
    validate_target(item)
    root = base_url.rstrip("/") + "/"
    page.goto(urllib.parse.urljoin(root, "articles.html") + "?verify=" + str(time.time_ns()),
              wait_until="domcontentloaded", timeout=60000)
    card = page.locator(f'.newspaper-articles-grid .newspaper-article-card[data-article-id="{item["id"]}"]')
    card.wait_for(state="visible", timeout=45000)
    if card.count() != 1 or card.locator(".js-download-pdf").count() != 1:
        raise PipelineError("بطاقة المقال مفقودة أو تعرض أزرار PDF مكررة")
    if card.locator(".newspaper-title").inner_text().strip() != item["title"]:
        raise PipelineError("عنوان بطاقة المقال غير صحيح")
    card.locator(f'a[href="{item["file"]}"]').click()
    body = page.locator(f'.article-body[data-article-id="{item["id"]}"]')
    body.wait_for(state="visible", timeout=45000)
    if page.locator("h1.book-title").inner_text().strip() != item["title"] or not body.inner_text().strip():
        raise PipelineError("صفحة المقال لا تعرض العنوان أو المتن")
    if page.locator(".js-book-download-top").count() != 1:
        raise PipelineError("زر PDF في صفحة المقال مفقود أو مكرر")
    with page.expect_download(timeout=60000) as event:
        page.locator(".js-book-download-top").click()
    downloaded = event.value.path()
    if not downloaded or hashlib.sha256(Path(downloaded).read_bytes()).hexdigest() != item["pdf_sha256"]:
        raise PipelineError("ملف PDF الذي تم تنزيله لا يطابق المقال")
    return validate_pdf(Path(downloaded))


def verify_browser(base_url: str, item: dict) -> int:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            context = browser.new_context(accept_downloads=True, viewport={"width": 390, "height": 844}, locale="ar-EG")
            return inspect_browser(context.new_page(), base_url, item)
        finally:
            browser.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--wait-seconds", type=int, default=0)
    args = parser.parse_args()
    try:
        item = read_json(args.result)
        wait_for_publication(args.base_url, item, args.wait_seconds)
        pages = verify_browser(args.base_url, item)
    except Exception as error:
        print(f"ARTICLE VERIFY ERROR: {error}", file=sys.stderr)
        return 1
    print(json.dumps({"id": item["id"], "url": urllib.parse.urljoin(args.base_url.rstrip("/") + "/", item["file"]),
                      "pdf_pages": pages}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
