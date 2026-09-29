#!/usr/bin/env python3
"""Check a published khutba card, detail page, and real browser PDF download."""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from content_pipeline import KHUTAB_JSON, PipelineError, make_shell_name, read_json


def target_item(args: argparse.Namespace) -> dict[str, str]:
    if args.result:
        result = read_json(Path(args.result))
        if result.get("kind") != "khutba":
            raise PipelineError("نتيجة النشر ليست خطبة مكتوبة")
        return result
    if not args.id:
        raise PipelineError("حدد --result أو --id")
    for item in read_json(KHUTAB_JSON):
        if item.get("id") == args.id:
            date_iso = item["date"]["iso"]
            return {"id": args.id, "title": item["title"],
                    "file": item.get("file") or "khutab/" + make_shell_name(date_iso, args.id)}
    raise PipelineError(f"معرّف الخطبة غير موجود: {args.id}")


def get_json(url: str) -> object:
    request = urllib.request.Request(url, headers={"Cache-Control": "no-cache", "User-Agent": "KhutbaPublishCheck/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def wait_for_library(base_url: str, item: dict[str, str], seconds: int) -> None:
    deadline = time.monotonic() + seconds
    archive_url = urllib.parse.urljoin(base_url.rstrip("/") + "/", "data/khutab_written_index.json")
    detail_url = urllib.parse.urljoin(base_url.rstrip("/") + "/", item["file"])
    last_error = ""
    while True:
        try:
            nonce = str(time.time_ns())
            index = get_json(archive_url + "?verify=" + nonce)
            matching = [row for row in index if row.get("id") == item["id"]]
            if matching and matching[0].get("has_content"):
                request = urllib.request.Request(detail_url + "?verify=" + nonce,
                                                 headers={"Cache-Control": "no-cache"})
                with urllib.request.urlopen(request, timeout=30) as response:
                    page = response.read().decode("utf-8")
                if f'data-khutba-id="{item["id"]}"' in page:
                    return
            last_error = "البطاقة أو الصفحة لم تظهر بعد"
        except (urllib.error.URLError, TimeoutError, ValueError, KeyError) as exc:
            last_error = str(exc)
        if time.monotonic() >= deadline:
            raise PipelineError(f"لم تظهر الخطبة على الموقع بعد {seconds} ثانية: {last_error}")
        time.sleep(10)


def verify_browser(base_url: str, item: dict[str, str]) -> int:
    from playwright.sync_api import sync_playwright
    from pypdf import PdfReader

    root = base_url.rstrip("/") + "/"
    list_url = urllib.parse.urljoin(root, "khutab-written.html")
    expected_href = item["file"]
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True, viewport={"width": 390, "height": 844}, locale="ar-EG")
        page = context.new_page()
        page.goto(list_url, wait_until="domcontentloaded", timeout=60000)
        page.locator(".khutab-item-card").first.wait_for(state="visible", timeout=45000)
        card_link = page.locator(f'a[href^="{expected_href}"]')
        for _ in range(100):
            if card_link.count():
                break
            more = page.locator("#khutab-load-more")
            if not more.is_visible():
                break
            more.click()
        card_link.first.wait_for(state="visible", timeout=45000)
        card = card_link.first.locator("xpath=ancestor::*[contains(@class, 'khutab-item-card')]")
        if card.locator(".khutba-download-btn").count() != 1:
            raise PipelineError("بطاقة الخطبة لا تعرض زر PDF")
        card_link.first.click()
        page.locator("#khutba-content .khutba-body").wait_for(state="visible", timeout=45000)
        if item["title"] not in page.locator("#khutba-title").inner_text():
            raise PipelineError("عنوان صفحة الخطبة لا يطابق ملف Word")
        group_titles = page.locator(".khutba-elements-group-title").all_inner_texts()
        if not any("الخطبة الأولى" in title for title in group_titles):
            raise PipelineError("عناصر الخطبة الأولى لا تظهر في الصفحة")
        if not any("الخطبة الثانية" in title for title in group_titles):
            raise PipelineError("عناصر الخطبة الثانية لا تظهر في الصفحة")
        with page.expect_download(timeout=180000) as event:
            page.locator("#khutba-download-pdf").click()
        download = event.value
        pdf_path = download.path()
        if pdf_path is None:
            raise PipelineError("لم يكتمل تنزيل ملف PDF")
        pdf = PdfReader(str(pdf_path))
        if len(pdf.pages) < 3:
            raise PipelineError("ملف PDF لا يحتوي الغلاف والعناصر والمتن")
        for number, pdf_page in enumerate(pdf.pages, 1):
            contents = pdf_page.get_contents()
            xobjects = (pdf_page.get("/Resources") or {}).get("/XObject")
            if contents is None or not contents.get_data().strip() or not xobjects:
                raise PipelineError(f"صفحة PDF فارغة: {number}")
        page_count = len(pdf.pages)
        context.close()
        browser.close()
    return page_count


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--result")
    parser.add_argument("--id")
    parser.add_argument("--wait-seconds", type=int, default=0)
    args = parser.parse_args()
    try:
        item = target_item(args)
        wait_for_library(args.base_url, item, args.wait_seconds)
        pages = verify_browser(args.base_url, item)
    except Exception as exc:
        print(f"PUBLISH VERIFY ERROR: {exc}", file=sys.stderr)
        return 1
    live_url = urllib.parse.urljoin(args.base_url.rstrip("/") + "/", item["file"])
    print(json.dumps({"url": live_url, "id": item["id"], "pdf_pages": pages}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
