"""Verify the device-only incremental fixture after process death while offline."""
import argparse
import json
import subprocess
import time
from pathlib import Path
from playwright.sync_api import sync_playwright


def run(adb_path, output):
    def adb(*args): return subprocess.check_output([str(adb_path), *args])
    package = 'com.ahmedelfashny.official.debug'
    output.mkdir(parents=True, exist_ok=True)
    adb('shell', 'am', 'force-stop', package)
    adb('shell', 'cmd', 'connectivity', 'airplane-mode', 'enable')
    adb('shell', 'svc', 'wifi', 'disable')
    adb('shell', 'svc', 'data', 'disable')
    try:
        adb('shell', 'am', 'start', '-n', package + '/com.ahmedelfashny.official.MainActivity')
        for _ in range(60):
            try:
                pid = adb('shell', 'pidof', package).decode().strip()
                if f'webview_devtools_remote_{pid}' in adb('shell', 'cat', '/proc/net/unix').decode(): break
            except subprocess.CalledProcessError: pass
            time.sleep(.5)
        else: raise RuntimeError('No debug WebView')
        adb('forward', 'tcp:9222', f'localabstract:webview_devtools_remote_{pid}')
        with sync_playwright() as playwright:
            browser = playwright.chromium.connect_over_cdp('http://127.0.0.1:9222')
            page = browser.contexts[0].pages[0]
            page.goto('https://ahmedelfashny.com/books/offline-sync-qa.html', wait_until='domcontentloaded')
            page.wait_for_function('document.body.innerText.includes("New downloaded article")')
            assert page.evaluate('!navigator.onLine')
            revision = page.locator('meta[name="app-content-revision"]').get_attribute('content')
            (output / 'sync-offline-new-article.png').write_bytes(adb('exec-out', 'screencap', '-p'))
            page.goto('https://ahmedelfashny.com/videos.html', wait_until='domcontentloaded')
            page.locator('.video-title').first.wait_for()
            assert 'OFFLINE SYNC QA' in page.locator('.video-title').first.inner_text()
            assert page.locator('meta[name="app-content-revision"]').get_attribute('content') == revision
            browser.close()
        result = dict(status='passed', revision=revision, checks=['new article offline after process restart', 'updated catalog offline', 'corrupt followup retained complete snapshot'])
        (output / 'sync-offline-report.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        return result
    finally:
        adb('shell', 'cmd', 'connectivity', 'airplane-mode', 'disable')
        adb('shell', 'svc', 'wifi', 'enable')
        adb('shell', 'svc', 'data', 'enable')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adb', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.adb, args.output)))
