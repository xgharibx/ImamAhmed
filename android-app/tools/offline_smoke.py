"""Fresh-install Android offline reading checks via its debug WebView."""
import argparse
import json
import subprocess
import time
from pathlib import Path

from playwright.sync_api import sync_playwright


PACKAGE = 'com.ahmedelfashny.official.debug'
SITE = 'https://ahmedelfashny.com/'
ROOT = Path(__file__).resolve().parents[2]


def run(adb_path, output):
    def adb(*args):
        return subprocess.check_output([str(adb_path), *args])

    def connect(playwright):
        for _ in range(60):
            try:
                pid = adb('shell', 'pidof', PACKAGE).decode().strip()
                sockets = adb('shell', 'cat', '/proc/net/unix').decode()
                if f'webview_devtools_remote_{pid}' in sockets:
                    adb('forward', 'tcp:9222', f'localabstract:webview_devtools_remote_{pid}')
                    browser = playwright.chromium.connect_over_cdp('http://127.0.0.1:9222')
                    return browser, browser.contexts[0].pages[0]
            except (subprocess.CalledProcessError, IndexError):
                pass
            time.sleep(.5)
        raise RuntimeError('Debug WebView unavailable')

    def airplane(enabled):
        adb('shell', 'cmd', 'connectivity', 'airplane-mode', 'enable' if enabled else 'disable')
        adb('shell', 'svc', 'wifi', 'disable' if enabled else 'enable')
        adb('shell', 'svc', 'data', 'disable' if enabled else 'enable')

    output.mkdir(parents=True, exist_ok=True)
    adb('shell', 'am', 'force-stop', PACKAGE)
    adb('shell', 'pm', 'clear', PACKAGE)
    airplane(True)
    report = dict(mode='fresh-install-airplane', pages=[], errors=[], networkFailures=[])
    try:
        adb('shell', 'am', 'start', '-n', PACKAGE + '/com.ahmedelfashny.official.MainActivity')
        with sync_playwright() as playwright:
            browser, page = connect(playwright)
            page.on('pageerror', lambda error: report['errors'].append(str(error)))
            page.on('requestfailed', lambda req: report['networkFailures'].append(req.url))

            def ready():
                page.locator('.mobile-bottom-nav').wait_for(timeout=15000)
                page.wait_for_function('document.body.innerText.length > 100')
                page.wait_for_function('!!window.__sheikhAppRuntime')
                assert page.locator('meta[name="app-content-revision"]').count() == 1
                assert page.evaluate("!document.querySelector('#preloader') || getComputedStyle(document.querySelector('#preloader')).display==='none'")
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')

            ready()
            assert page.evaluate('!navigator.onLine'), 'Emulator was not actually offline'
            manifest = json.loads((ROOT / 'data/app-content-manifest.json').read_text('utf-8'))
            page.goto(SITE + 'khutab-written.html', wait_until='domcontentloaded')
            ready()
            page.locator("a[href^='khutab/']").first.wait_for()
            sermon_url = page.locator("a[href^='khutab/']").first.get_attribute('href')
            article = 'books/mathabat-alarwah-rihlat-alishq-ila-rihab-alnur-almuhammadi.html'
            destinations = ['index.html', 'articles.html', article, 'khutab-written.html', sermon_url,
                            'videos.html', 'khutab-video.html', 'tilawa.html', 'books.html',
                            'quran.html', 'hadith.html', 'adhkar.html', 'fatawa.html', 'khawater.html', 'about.html']
            for index, destination in enumerate(destinations):
                start = time.monotonic()
                page.goto(SITE + destination.lstrip('/'), wait_until='domcontentloaded')
                ready()
                if destination.endswith('videos.html') or destination in ('khutab-video.html', 'tilawa.html'):
                    page.locator('.video-card').first.wait_for(timeout=10000)
                    page.locator('.video-card img').first.wait_for()
                    page.wait_for_function('document.querySelector(".video-card img").naturalWidth > 0')
                if destination.startswith('khutab/'):
                    page.wait_for_function('document.querySelector("#khutba-content")?.innerText.length > 1000')
                page.evaluate('document.fonts.ready')
                loaded_fonts = page.evaluate('Array.from(document.fonts).filter(f=>f.status==="loaded").map(f=>f.family)')
                assert any('Amiri' in f or 'Cairo' in f for f in loaded_fonts), loaded_fonts
                (output / f'{index:02}-{Path(destination).stem}.png').write_bytes(adb('exec-out', 'screencap', '-p'))
                report['pages'].append(dict(path=destination, title=page.title(), milliseconds=round((time.monotonic()-start)*1000),
                                            characters=len(page.locator('body').inner_text()), fonts=sorted(set(loaded_fonts)),
                                            revision=page.locator('meta[name="app-content-revision"]').get_attribute('content')))
                print('PASS offline', destination, flush=True)
            # Exercise the actual navigation UI and Android back handler offline.
            page.locator('.mobile-bottom-nav a').first.click()
            ready()
            page.locator('.mobile-bottom-nav button').click()
            page.wait_for_function('document.querySelector("#mobile-nav-sheet").open')
            adb('shell', 'input', 'keyevent', 'KEYCODE_BACK')
            page.wait_for_function('!document.querySelector("#mobile-nav-sheet").open')
            assert not report['errors'], report['errors']
            assert all(p['revision'] == manifest['revision'] for p in report['pages'])
            # App restart must still read the same seed without network or HTTP cache.
            browser.close()
            adb('shell', 'am', 'force-stop', PACKAGE)
            adb('shell', 'am', 'start', '-n', PACKAGE + '/com.ahmedelfashny.official.MainActivity')
            browser, page = connect(playwright)
            ready()
            assert page.evaluate('!navigator.onLine')
            browser.close()
        report['status'] = 'passed'
    except Exception as error:
        report['status'] = 'failed'
        report['failure'] = str(error)
        (output / 'failure.png').write_bytes(adb('exec-out', 'screencap', '-p'))
        raise
    finally:
        (output / 'offline-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        airplane(False)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adb', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.adb, args.output), ensure_ascii=True))
