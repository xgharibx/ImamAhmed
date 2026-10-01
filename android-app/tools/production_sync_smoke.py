"""Verify the downloaded production snapshot survives a disconnected restart."""
import argparse
import json
import subprocess
import time
from pathlib import Path

from playwright.sync_api import sync_playwright


def run(adb_path, output, revision):
    package = 'com.ahmedelfashny.official.debug'
    def adb(*args):
        return subprocess.check_output([str(adb_path), '-s', 'emulator-5554', *args])

    output.mkdir(parents=True, exist_ok=True)
    journal = adb('shell', 'run-as', package, 'ls', 'files/offline-content').decode()
    assert revision + '.json' in journal, 'Expected production snapshot was not downloaded'
    log = adb('logcat', '-d', '-s', 'ContentSync:V').decode()
    assert 'Activated ' + revision in log, 'No production worker activation evidence'
    (output / 'production-worker.log').write_text(log, encoding='utf-8')
    try:
        adb('shell', 'cmd', 'connectivity', 'airplane-mode', 'enable')
        adb('shell', 'svc', 'wifi', 'disable')
        adb('shell', 'svc', 'data', 'disable')
        adb('shell', 'am', 'force-stop', package)
        adb('shell', 'am', 'start', '-n', package + '/com.ahmedelfashny.official.MainActivity')
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            try:
                pid = adb('shell', 'pidof', package).decode().strip()
                if pid and 'webview_devtools_remote_' + pid in adb('shell', 'cat', '/proc/net/unix').decode():
                    break
            except subprocess.CalledProcessError:
                pass
            time.sleep(.5)
        else:
            raise RuntimeError('Restarted debug WebView unavailable')
        adb('forward', 'tcp:9222', 'localabstract:webview_devtools_remote_' + pid)
        with sync_playwright() as playwright:
            browser = playwright.chromium.connect_over_cdp('http://127.0.0.1:9222')
            page = browser.contexts[0].pages[0]
            page.wait_for_load_state('load')
            page.locator('.mobile-bottom-nav').wait_for()
            failures = []
            page.on('requestfailed', lambda request: failures.append(dict(url=request.url, error=request.failure)))
            page.goto('https://ahmedelfashny.com/books/mathabat-alarwah-rihlat-alishq-ila-rihab-alnur-almuhammadi.html', wait_until='domcontentloaded')
            page.locator('.mobile-bottom-nav').wait_for()
            page.wait_for_function('document.body.innerText.length > 1000')
            page.wait_for_load_state('load')
            assert not page.evaluate('navigator.onLine')
            assert page.locator('meta[name="app-content-revision"]').get_attribute('content') == revision
            assert not failures, failures
            (output / 'production-update-offline.png').write_bytes(adb('exec-out', 'screencap', '-p'))
            browser.close()
        result = dict(status='passed', revision=revision, checks=['real HTTPS worker activated published snapshot', 'downloaded revision survived process restart', 'changed article read in airplane mode', 'no failed page resource requests'])
        (output / 'production-sync-report.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        return result
    finally:
        adb('shell', 'cmd', 'connectivity', 'airplane-mode', 'disable')
        adb('shell', 'svc', 'wifi', 'enable')
        adb('shell', 'svc', 'data', 'enable')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adb', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--revision', required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.adb, args.output, args.revision)))
