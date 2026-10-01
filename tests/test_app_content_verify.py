import functools
import http.server
import importlib.util
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import generate_app_content as app


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class AppContentVerifyTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('verify_app_content'), 'Live offline content verifier is missing')
        import verify_app_content
        self.verify = verify_app_content.verify_live
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'data').mkdir()
        (self.root / 'index.html').write_text('<p>Reading</p>', encoding='utf-8')
        self.manifest = app.build_manifest(self.root)
        app.write_json(self.root / 'data/app-content-manifest.json', self.manifest)
        self.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=self.tmp.name))
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.base = 'http://127.0.0.1:' + str(self.server.server_port)

    def test_matching_revision_and_resource_bytes_are_confirmed(self):
        self.assertEqual('verified-live', self.verify(self.base, self.manifest)['status'])

    def test_stale_manifest_is_not_confirmed(self):
        (self.root / 'index.html').write_text('Updated page', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'manifest'):
            self.verify(self.base, app.build_manifest(self.root))

    def test_manifest_with_stale_page_is_not_confirmed(self):
        (self.root / 'index.html').write_text('Wrong content', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'checksum'):
            self.verify(self.base, self.manifest)


if __name__ == '__main__':
    unittest.main()
