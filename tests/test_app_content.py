import hashlib
import importlib.util
import json
import tempfile
import unittest
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

    def test_revision_changes_only_when_public_content_changes(self):
        original = self.app.build_manifest(self.root)
        self.write('data/video-sync-status.json', '{"checkedAt":"now"}')
        self.write('docs/private.html', 'secret')
        self.assertEqual(original, self.app.build_manifest(self.root))
        self.write('books/article.html', '<p>New reading content</p>')
        changed = self.app.build_manifest(self.root)
        self.assertNotEqual(original['revision'], changed['revision'])
        self.assertEqual(changed, self.app.build_manifest(self.root))

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
