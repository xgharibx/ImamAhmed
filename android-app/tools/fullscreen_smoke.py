"""Check real YouTube playback, Android fullscreen, rotation and Back."""
import argparse
import json
import subprocess
import time
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright


def run(adb_path, output):
    def adb(*args):
        return subprocess.check_output([str(adb_path), '-s', 'emulator-5554', *args])

    output.mkdir(parents=True, exist_ok=True)
    rotation = adb('shell', 'settings', 'get', 'system', 'user_rotation').decode().strip()
    automatic = adb('shell', 'settings', 'get', 'system', 'accelerometer_rotation').decode().strip()
    adb('shell', 'cmd', 'connectivity', 'airplane-mode', 'disable')
    adb('shell', 'svc', 'wifi', 'enable')
    pid = adb('shell', 'pidof', 'com.ahmedelfashny.official.debug').decode().strip()
    if not pid:
        adb('shell', 'am', 'start', '-n', 'com.ahmedelfashny.official.debug/com.ahmedelfashny.official.MainActivity')
        time.sleep(1)
        pid = adb('shell', 'pidof', 'com.ahmedelfashny.official.debug').decode().strip()
    adb('forward', 'tcp:9222', 'localabstract:webview_devtools_remote_' + pid)
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.connect_over_cdp('http://127.0.0.1:9222')
            page = browser.contexts[0].pages[0]
            page.locator('.mobile-bottom-nav').wait_for()
            if page.url != 'https://ahmedelfashny.com/videos.html' or not page.locator('#video-modal.active').count():
                page.goto('https://ahmedelfashny.com/videos.html', wait_until='domcontentloaded')
                page.locator('.video-thumbnail').first.click()
            iframe = page.locator('#modal-iframe')
            source = iframe.get_attribute('src')
            deadline = time.monotonic() + 90
            while time.monotonic() < deadline:
                player = next((frame for frame in page.frames if 'youtube-nocookie.com/embed/' in frame.url), None)
                if player and player.locator('video').count():
                    break
                time.sleep(.5)
            else:
                raise RuntimeError('YouTube player unavailable')
            play_button = player.get_by_role('button', name='Play video', exact=True)
            if player.locator('video').first.evaluate('v => v.paused') and play_button.is_visible():
                play_button.click()
            deadline = time.monotonic() + 90
            while time.monotonic() < deadline:
                if player.locator('video').first.evaluate('v => v.readyState >= 2 && v.currentTime > 0'):
                    break
                time.sleep(.5)
            else:
                raise RuntimeError('YouTube video did not start')
            player.locator('video').first.click(force=True)
            fullscreen = player.locator('button.fullscreen-icon, button.ytp-fullscreen-button').first
            fullscreen.wait_for(state='visible', timeout=15000)
            fullscreen.click()
            deadline = time.monotonic() + 15
            while not player.evaluate('!!document.fullscreenElement'):
                if time.monotonic() >= deadline:
                    raise RuntimeError('Native fullscreen did not open')
                time.sleep(.2)
            (output / 'fullscreen-portrait.png').write_bytes(adb('exec-out', 'screencap', '-p'))
            adb('shell', 'settings', 'put', 'system', 'accelerometer_rotation', '0')
            adb('shell', 'settings', 'put', 'system', 'user_rotation', '1')
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                screenshot = output / 'fullscreen-landscape.png'
                screenshot.write_bytes(adb('exec-out', 'screencap', '-p'))
                with Image.open(screenshot) as picture:
                    if picture.width > picture.height:
                        break
                time.sleep(.5)
            else:
                raise RuntimeError('Fullscreen did not rotate to landscape')
            assert player.evaluate('!!document.fullscreenElement')
            adb('shell', 'input', 'keyevent', 'KEYCODE_BACK')
            deadline = time.monotonic() + 15
            while player.evaluate('!!document.fullscreenElement'):
                if time.monotonic() >= deadline:
                    raise RuntimeError('Back did not leave fullscreen')
                time.sleep(.2)
            page.locator('#video-modal.active').wait_for()
            adb('shell', 'input', 'keyevent', 'KEYCODE_BACK')
            page.wait_for_function('!document.querySelector("#video-modal").classList.contains("active")')
            assert page.locator('.mobile-bottom-nav').is_visible()
            result = dict(status='passed', source=source, checks=['actual YouTube video advanced', 'native fullscreen entered', 'landscape rotation retained playback fullscreen', 'Back left fullscreen', 'second Back closed modal', 'original navigation restored'])
            (output / 'fullscreen-report.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
            browser.close()
            return result
    finally:
        adb('shell', 'settings', 'put', 'system', 'user_rotation', rotation)
        adb('shell', 'settings', 'put', 'system', 'accelerometer_rotation', automatic)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adb', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.adb, args.output)))
