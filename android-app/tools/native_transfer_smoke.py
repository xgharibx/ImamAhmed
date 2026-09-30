"""Regression checks against the real emulator bridge and Android save picker."""
import argparse
import base64
import json
import re
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from playwright.sync_api import sync_playwright

PACKAGE = "com.ahmedelfashny.official.debug"


def run(adb_path):
    def adb(*args):
        result = subprocess.run([str(adb_path), *args], stdout=subprocess.PIPE, check=False)
        if result.returncode and args[:2] != ("shell", "pidof"):
            result.check_returncode()
        return result.stdout

    def connect(playwright):
        for _ in range(30):
            pid = adb("shell", "pidof", PACKAGE).decode().strip()
            if pid and f"webview_devtools_remote_{pid}" in adb("shell", "cat", "/proc/net/unix").decode():
                adb("forward", "tcp:9222", f"localabstract:webview_devtools_remote_{pid}")
                browser = playwright.chromium.connect_over_cdp("http://127.0.0.1:9222")
                page = browser.contexts[0].pages[0]
                page.wait_for_function("!!window.SheikhNative && !!window.__sheikhAppRuntime")
                return page
            time.sleep(.5)
        raise RuntimeError("No debug WebView")

    with sync_playwright() as playwright:
        focus = adb("shell", "dumpsys", "window").decode()
        if "documentsui" in focus or "ChooserActivity" in focus:
            adb("shell", "input", "keyevent", "KEYCODE_BACK")
        adb("shell", "am", "force-stop", PACKAGE)
        adb("shell", "am", "start", "-n", PACKAGE + "/com.ahmedelfashny.official.MainActivity")
        page = connect(playwright)
        page.evaluate("""() => {
            const normal = SheikhNative.onmessage;
            window.testReplies = {};
            SheikhNative.onmessage = e => {
                const reply = JSON.parse(e.data); testReplies[reply.id] = reply;
                normal(e);
            };
            window.nativeTestRequest = msg => SheikhNative.postMessage(JSON.stringify(msg));
        }""")

        def request(message):
            page.evaluate("msg => nativeTestRequest(msg)", message)
            page.wait_for_function("id => !!testReplies[id]", arg=message["id"])
            return page.evaluate("id => testReplies[id]", message["id"])

        payload = b"%PDF-1.4\n% bridge process restoration test\n%%EOF\n"
        test_name = f"android-picker-restore-{int(time.time())}.pdf"
        assert request({"id": 1001, "type": "start", "name": test_name, "size": len(payload)})["ok"]
        assert not request({"id": 1002, "type": "start", "name": "second.pdf", "size": 10})["ok"]
        assert request({"id": 1003, "type": "chunk", "data": base64.b64encode(payload).decode()})["ok"]
        page.evaluate("SheikhNative.postMessage(new Uint8Array([1,2,3]).buffer)")
        assert request({"id": 1004, "type": "finish"})["ok"]
        time.sleep(1)
        assert "documentsui" in adb("shell", "dumpsys", "window").decode()
        old_pid = adb("shell", "pidof", PACKAGE).decode().strip()
        adb("shell", "am", "kill", PACKAGE)
        if adb("shell", "pidof", PACKAGE).decode().strip():
            adb("shell", "run-as", PACKAGE, "kill", "-9", old_pid)
        for _ in range(20):
            if not adb("shell", "pidof", PACKAGE).decode().strip(): break
            time.sleep(.2)
        else: raise AssertionError("Background app did not die")

        adb("shell", "uiautomator", "dump", "/sdcard/native-transfer-ui.xml")
        tree = ET.fromstring(adb("exec-out", "cat", "/sdcard/native-transfer-ui.xml"))
        save = next(node for node in tree.iter("node") if node.get("text", "").lower() == "save" and node.get("enabled") == "true")
        x1, y1, x2, y2 = map(int, re.findall(r"\d+", save.get("bounds")))
        adb("shell", "input", "tap", str((x1+x2)//2), str((y1+y2)//2))
        time.sleep(2)
        assert adb("exec-out", "cat", "/sdcard/Download/" + test_name) == payload
        new_pid = adb("shell", "pidof", PACKAGE).decode().strip()
        assert new_pid and new_pid != old_pid
        page = connect(playwright)
        png_data = page.evaluate("""async () => {
            const canvas = document.createElement('canvas'); canvas.width=4; canvas.height=4;
            canvas.getContext('2d').fillRect(0,0,4,4);
            const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/png'));
            const file = new File([blob], 'card.png', {type:'image/png'});
            if (!navigator.canShare({files:[file]})) throw Error('PNG sharing not supported');
            await navigator.share({files:[file]});
            return btoa(String.fromCharCode(...new Uint8Array(await blob.arrayBuffer())));
        }""")
        time.sleep(.8)
        assert "ChooserActivity" in adb("shell", "dumpsys", "window").decode()
        shared = adb("exec-out", "run-as", PACKAGE, "ls", "-1", "cache/shared").decode().splitlines()
        assert any(name.endswith("-card.png") and adb("exec-out", "run-as", PACKAGE, "cat", "cache/shared/" + name) == base64.b64decode(png_data) for name in shared)
        adb("shell", "input", "keyevent", "KEYCODE_BACK")
        print(json.dumps({"checks": ["competing download preserves first transfer", "binary message does not crash", "save picker survives app process death", "saved bytes unchanged", "native PNG sharing"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("adb", type=Path)
    run(parser.parse_args().adb)
