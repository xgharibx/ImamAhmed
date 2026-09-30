"""Exercise the actual debug WebView and capture unmodified Android screenshots."""
import argparse
import json
import re
import subprocess
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def run(adb_path, output):
    def adb(*args):
        return subprocess.check_output([str(adb_path), *args])

    output.mkdir(parents=True, exist_ok=True)
    adb("shell", "wm", "size", "1080x1920")
    adb("shell", "am", "force-stop", "com.ahmedelfashny.official.debug")
    adb("shell", "am", "start", "-n", "com.ahmedelfashny.official.debug/com.ahmedelfashny.official.MainActivity")
    for _ in range(30):
        try:
            pid = adb("shell", "pidof", "com.ahmedelfashny.official.debug").decode().strip()
            sockets = adb("shell", "cat", "/proc/net/unix").decode()
            if f"webview_devtools_remote_{pid}" in sockets: break
        except subprocess.CalledProcessError:
            pass
        time.sleep(.5)
    else:
        raise RuntimeError("Debug WebView did not become available")
    adb("forward", "tcp:9222", f"localabstract:webview_devtools_remote_{pid}")

    def capture(name):
        (output / name).write_bytes(adb("exec-out", "screencap", "-p"))

    with sync_playwright() as playwright:
        browser = playwright.chromium.connect_over_cdp("http://127.0.0.1:9222")
        page = browser.contexts[0].pages[0]
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))

        def ready():
            page.locator(".mobile-bottom-nav").wait_for(timeout=30000)
            page.wait_for_function("!document.querySelector('#preloader') || document.querySelector('#preloader').classList.contains('hidden')")
            page.wait_for_timeout(800)
            assert page.locator(".mobile-bottom-nav").count() == 1
            assert page.evaluate("!!window.__sheikhAppRuntime && !!window.SheikhNative")
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")

        def frame_content(locator):
            locator.evaluate("element => { const y=element.getBoundingClientRect().top+scrollY-120; window.scrollTo({top: y, behavior:'instant'}); }")
            page.wait_for_timeout(500)

        ready()
        capture("01-home.png")
        page.locator(".mobile-bottom-nav a").nth(2).click()
        ready()
        frame_content(page.locator("a[href*=k-20261002]").first.locator("xpath=ancestor::div[contains(@class, 'card')][1]"))
        capture("02-written-sermons.png")
        page.locator("a[href*=k-20261002]").first.click()
        ready()
        assert "وَلَقَدْ" in page.locator("#khutba-content").inner_text()
        frame_content(page.locator("#khutba-content"))
        capture("03-sermon-reading.png")
        page.locator(".mobile-bottom-nav a").nth(1).click()
        ready()
        page.locator(".video-card").first.wait_for(timeout=30000)
        frame_content(page.locator(".video-card").first)
        capture("04-videos.png")
        page.locator(".video-thumbnail").first.click()
        page.locator("#video-modal.active").wait_for()
        iframe = page.locator("#modal-iframe")
        assert "youtube-nocookie.com/embed/" in iframe.get_attribute("src")
        assert iframe.get_attribute("allowfullscreen") is not None
        page.wait_for_timeout(8000)
        adb("shell", "input", "keyevent", "KEYCODE_BACK")
        page.wait_for_function("!document.querySelector('#video-modal').classList.contains('active')")
        page.locator(".mobile-bottom-nav a").nth(3).click()
        ready()
        capture("06-library.png")
        page.locator(".mobile-bottom-nav button").click()
        page.wait_for_function("document.querySelector('#mobile-nav-sheet').open")
        capture("07-sections.png")
        adb("shell", "input", "keyevent", "KEYCODE_BACK")
        page.wait_for_function("!document.querySelector('#mobile-nav-sheet').open")
        assert page.evaluate("!document.body.classList.contains('mobile-nav-open')")
        assert page.locator(".mobile-bottom-nav button").get_attribute("aria-expanded") == "false"
        page.evaluate("navigator.share({title: document.title, url: location.href})")
        page.wait_for_timeout(800)
        focus = adb("shell", "dumpsys", "window").decode()
        assert "ChooserActivity" in focus
        capture("08-native-share.png")
        adb("shell", "input", "keyevent", "KEYCODE_BACK")
        assert not errors, errors
        report = {"url": page.url, "errors": errors, "checks": ["live content", "single unchanged navigation", "no horizontal overflow", "written sermon", "video embed", "video modal back", "more menu back", "native sharing"]}
        (output / "smoke-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("adb", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "play-store/screenshots")
    args = parser.parse_args()
    run(args.adb, args.output)
