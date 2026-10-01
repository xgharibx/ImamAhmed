import hashlib
import importlib.util
import json
import tempfile
import subprocess
import unittest
from unittest.mock import patch
import io
from email.message import Message
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
import urllib.request
import urllib.response
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/generate_app_content.py'


class AppContentTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SCRIPT.exists(), 'Offline resource generator has not been implemented')
        spec = importlib.util.spec_from_file_location('app_content', SCRIPT)
        self.app = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.app)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.write('index.html', '<link rel="stylesheet" href="style.css"><img src="assets/logo.png">')
        self.write('style.css', 'body { color: green; }')
        self.write('assets/logo.png', b'fixture-image')
        self.write('data/videos.json', '[]')
        self.write('books/article.html', '<p>Reading content</p>')
        self.write('khutab/sermon.html', '<script src="../main.js"></script>')
        self.write('main.js', 'window.ready = true;')

    def write(self, path, data):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data.encode() if isinstance(data, str) else data)

    def test_untrusted_cdn_redirect_is_rejected_before_contact(self):
        contacts = []
        class Receiver(BaseHTTPRequestHandler):
            def do_GET(self):
                contacts.append(self.path)
                self.send_response(200)
                self.send_header('Content-Type', 'text/css')
                self.end_headers()
                self.wfile.write(b'body{}')
            def log_message(self, *args):
                pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Receiver)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        destination = f'http://127.0.0.1:{server.server_port}/must-not-contact'
        class RedirectedHttps(urllib.request.HTTPSHandler):
            def https_open(self, request):
                headers = Message()
                headers['Location'] = destination
                response = urllib.response.addinfourl(io.BytesIO(b''), headers, request.full_url, 302)
                response.msg = 'Found'
                return response
        original_builder = urllib.request.build_opener
        def builder(*handlers):
            return original_builder(RedirectedHttps(), *handlers)
        original_open = builder().open
        with patch.object(self.app, 'urlopen', original_open, create=True), patch.object(self.app, 'build_opener', builder, create=True):
            with self.assertRaises(ValueError):
                self.app.fetch_mirror(self.root, 'https://fonts.googleapis.com/css2?family=Amiri')
        self.assertEqual(contacts, [], 'Untrusted recipient received a request before validation')

    def test_cdn_mirror_text_keeps_its_published_line_endings(self):
        raw = b'body { color: green; }\r\n'
        self.write('assets/app-content/external.css', raw)
        self.assertEqual(self.app.content_bytes(self.root / 'assets/app-content/external.css'), raw)

    def test_git_publishes_owned_text_in_manifest_line_endings(self):
        self.write('style.css', b'body { color: green; }\r\n')
        self.write('.gitattributes', (SCRIPT.parent.parent / '.gitattributes').read_bytes())
        for args in [('init', '-q'), ('config', 'core.autocrlf', 'false'), ('add', '.')]:
            subprocess.run(['git', '-C', str(self.root), *args], check=True, capture_output=True)
        published = subprocess.check_output(['git', '-C', str(self.root), 'show', ':style.css'])
        self.assertEqual(self.app.content_bytes(self.root / 'style.css'), published)

    def test_revision_changes_only_when_public_content_changes(self):
        original = self.app.build_manifest(self.root)
        self.write('data/video-sync-status.json', '{"checkedAt":"now"}')
        self.write('docs/private.html', 'secret')
        self.assertEqual(original, self.app.build_manifest(self.root))
        self.write('books/article.html', '<p>New reading content</p>')
        changed = self.app.build_manifest(self.root)
        self.assertNotEqual(original['revision'], changed['revision'])
        self.assertEqual(changed, self.app.build_manifest(self.root))

    def test_new_article_sermon_and_video_catalog_enter_next_snapshot(self):
        first = self.app.build_manifest(self.root)
        self.write('books/new.html', '<p>New article</p>')
        self.write('khutab/new.html', '<p>New sermon</p>')
        self.write('data/videos.json', '[{"id":"a4upwTATNWQ","title":"New video"}]')
        next_manifest = self.app.build_manifest(self.root)
        keys = {e['key'] for e in next_manifest['resources']}
        self.assertIn('/books/new.html', keys)
        self.assertIn('/khutab/new.html', keys)
        self.assertNotEqual(first['revision'], next_manifest['revision'])
        self.assertEqual(next_manifest, self.app.build_manifest(self.root))

    def test_seed_contains_unvisited_reading_and_matches_hashes(self):
        out = self.root / 'android-app/build/seed'
        manifest = self.app.prepare_seed(self.root, out)
        entries = {e['key']: e for e in manifest['resources']}
        self.assertIn('/books/article.html', entries)
        self.assertIn('/khutab/sermon.html', entries)
        self.assertIn('/assets/logo.png', entries)
        for entry in entries.values():
            content = (out / 'objects' / entry['sha256']).read_bytes()
            self.assertEqual(len(content), entry['size'])
            self.assertEqual(hashlib.sha256(content).hexdigest(), entry['sha256'])
        self.assertEqual(json.loads((out / 'manifest.json').read_text()), manifest)

    def test_sources_build_files_admin_and_pdf_are_excluded(self):
        for path in ['admin/index.html', 'templates/test.html', 'android-app/private.js',
                     'khutab/source.docx', 'books/read.pdf', 'data/app-content-manifest.json']:
            self.write(path, 'private')
        paths = [e['path'] for e in self.app.build_manifest(self.root)['resources']]
        self.assertFalse(any('private' in p or p.endswith(('.docx', '.pdf')) or p.startswith('admin/') for p in paths))

    def test_missing_required_linked_resource_fails(self):
        self.write('index.html', '<script src="missing.js"></script>')
        with self.assertRaisesRegex(ValueError, 'missing.js'):
            self.app.build_manifest(self.root)

    def test_legacy_invalid_metadata_bytes_do_not_hide_script_dependencies(self):
        self.write('khutab/legacy.html', b'<title>old \x93title</title><script src="../main.js"></script>')
        entries = {e['key']: e for e in self.app.build_manifest(self.root)['resources']}
        self.assertIn('/khutab/legacy.html', entries)
        self.assertIn('/main.js', entries)

    def test_private_and_traversal_keys_are_rejected(self):
        for key in ['/../keystore.properties', '/data/%2e%2e/private', '/admin/index.html',
                    'http://evil.test/a.js', 'https://user:pass@fonts.gstatic.com/x', '/downloads/app.apk']:
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.app.normalize_key(key)

    def test_owned_query_is_removed_but_font_query_is_preserved(self):
        self.assertEqual('/books/article.html', self.app.normalize_key('https://www.ahmedelfashny.com/books/article.html?v=2'))
        self.assertEqual('/index.html', self.app.normalize_key('/'))
        font = 'https://fonts.googleapis.com/css2?family=Amiri&display=swap'
        self.assertEqual(font, self.app.normalize_key(font))

    def test_external_stylesheet_and_font_have_owned_download_mirrors(self):
        css = 'https://fonts.googleapis.com/css2?family=Amiri&display=swap'
        font = 'https://fonts.gstatic.com/s/amiri/v1/font.woff2'
        self.write('index.html', f'<link rel="stylesheet" href="{css.replace("&", "&amp;")}">')
        css_path = 'assets/app-content/css.css'
        font_path = 'assets/app-content/font.woff2'
        self.write(css_path, f'@font-face {{src:url({font});}}')
        self.write(font_path, b'font-fixture')
        self.write('assets/app-content/mappings.json', json.dumps({css: css_path, font: font_path}))
        entries = {e['key']: e for e in self.app.build_manifest(self.root)['resources']}
        self.assertEqual(css_path, entries[css]['path'])
        self.assertEqual(font_path, entries[font]['path'])


if __name__ == '__main__':
    unittest.main()
