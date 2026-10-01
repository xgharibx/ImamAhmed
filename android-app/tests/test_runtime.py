"""Browser regression tests for the Android-only runtime (no UI changes)."""
import json
import unittest
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


class RuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        self.page = self.browser.new_page()
        self.page.route("https://ahmedelfashny.com/**", lambda route: route.fulfill(
            status=200, content_type="text/html", body="<html><body><nav>original</nav></body></html>"))
        self.page.goto("https://ahmedelfashny.com/")
        self.page.evaluate("""() => {
            window.calls = []; window.messages = [];
            window.fetch = async (...args) => { calls.push(args); return new Response('{}'); };
            window.SheikhNative = { postMessage(raw) {
                const message = JSON.parse(raw); messages.push(message);
                queueMicrotask(() => this.onmessage({data: JSON.stringify({id: message.id, ok: true})}));
            }};
        }""")
        runtime = ROOT / "app/src/main/assets/app-runtime.js"
        self.page.evaluate(runtime.read_text(encoding="utf-8") if runtime.exists() else "void 0")

    def tearDown(self):
        self.page.close()

    def test_first_party_content_revalidates_without_changing_other_fetches(self):
        result = self.page.evaluate("""async () => {
            await fetch('/data/videos.json'); await fetch('https://example.com/data/videos.json');
            return calls.map(call => call[1]?.cache || null);
        }""")
        self.assertEqual(result, ["no-cache", None])

    def test_post_requests_are_unchanged(self):
        self.page.evaluate("fetch('/data/upload.json', {method: 'POST', body: 'hello'})")
        self.assertIsNone(self.page.evaluate("calls[0][1].cache || null"))

    def test_runtime_keeps_the_existing_dom(self):
        self.assertEqual(self.page.locator("body").inner_html(), "<nav>original</nav>")

    def test_app_preloader_is_hidden_before_site_scripts_run(self):
        self.page.evaluate("document.body.insertAdjacentHTML('afterbegin', '<div id=preloader>Loading</div>')")
        self.assertEqual(self.page.locator('#preloader').evaluate('element => getComputedStyle(element).display'), 'none')

    def test_blob_pdf_download_preserves_bytes_even_when_url_is_revoked(self):
        self.page.evaluate("""() => {
            const url = URL.createObjectURL(new Blob(['%PDF-1.7\\nexact original bytes'], {type: 'application/pdf'}));
            const link = document.createElement('a'); link.href = url; link.download = 'خطبة.pdf';
            link.click(); URL.revokeObjectURL(url);
        }""")
        self.page.wait_for_function("messages.some(message => message.type === 'finish')", timeout=3000)
        messages = self.page.evaluate("messages")
        self.assertEqual(messages[0]["name"], "خطبة.pdf")
        import base64
        self.assertEqual(b"".join(base64.b64decode(m["data"]) for m in messages if m["type"] == "chunk"),
                         b"%PDF-1.7\nexact original bytes")

    def test_link_sharing_uses_native_chooser(self):
        self.page.evaluate("navigator.share({title: 'Title', url: location.href})")
        self.page.wait_for_function("messages.some(message => message.type === 'share')", timeout=3000)
        self.assertEqual(self.page.evaluate("messages[0].url"), "https://ahmedelfashny.com/")

    def test_filesaver_detached_anchor_dispatch_is_handled(self):
        self.page.evaluate("""() => {
            const link = document.createElement('a');
            link.href = URL.createObjectURL(new Blob(['%PDF-1.7\\nFileSaver'], {type: 'application/pdf'}));
            link.download = 'khutba.pdf'; link.dispatchEvent(new MouseEvent('click'));
        }""")
        self.page.wait_for_timeout(100)
        self.assertTrue(self.page.evaluate("messages.some(message => message.type === 'finish')"))

    def test_existing_png_file_sharing_transfers_the_original_image(self):
        self.page.evaluate("""async () => {
            const file = new File([new Uint8Array([137,80,78,71,13,10,26,10,1,2])], 'quote.png', {type: 'image/png'});
            window.canShareImage = navigator.canShare({files: [file]});
            await navigator.share({files: [file], title: 'Quote'}).catch(error => { window.shareError=error.message; });
        }""")
        self.assertTrue(self.page.evaluate("canShareImage"))
        self.assertEqual(self.page.evaluate("messages[0].operation"), "share")
        self.assertEqual(self.page.evaluate("messages[0].mime"), "image/png")
        self.assertTrue(self.page.evaluate("messages.some(message => message.type === 'finish')"))


if __name__ == "__main__":
    unittest.main()
