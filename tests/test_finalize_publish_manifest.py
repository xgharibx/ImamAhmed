import importlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import generate_app_content as generator


class FinalizePublishManifestTests(unittest.TestCase):
    def api(self):
        try:
            return importlib.import_module('finalize_publish_manifest')
        except ModuleNotFoundError:
            self.fail('Final-tree manifest validation is missing')

    def fixture(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        self.git(root, 'init', '-q')
        self.git(root, 'config', 'user.name', 'Test')
        self.git(root, 'config', 'user.email', 'test@example.com')
        (root / 'index.html').write_text('<link rel="stylesheet" href="style.css">')
        (root / 'style.css').write_text('body { color: green; }')
        generator.write_json(root / 'data/app-content-manifest.json', generator.build_manifest(root))
        self.git(root, 'add', '.')
        self.git(root, 'commit', '-qm', 'Publication')
        return root

    def git(self, root, *args):
        return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.STDOUT).decode().strip()

    def test_final_tree_is_rebuilt_after_rebase_without_changing_source_files(self):
        api = self.api()
        root = self.fixture()
        source = 'body { color: teal; }'
        (root / 'style.css').write_text(source)
        self.git(root, 'add', 'style.css')
        self.git(root, 'commit', '--amend', '--no-edit', '-q')
        api.finalize(root)
        self.assertEqual(generator.build_manifest(root), generator.json.loads((root / 'data/app-content-manifest.json').read_text()))
        self.assertEqual((root / 'style.css').read_text(), source)
        self.assertEqual(self.git(root, 'status', '--porcelain'), '')

    def test_unchanged_manifest_does_not_create_or_amend_a_commit(self):
        api = self.api()
        root = self.fixture()
        before = self.git(root, 'rev-parse', 'HEAD')
        api.finalize(root)
        self.assertEqual(self.git(root, 'rev-parse', 'HEAD'), before)

    def test_unrelated_staging_is_rejected_before_any_amend(self):
        api = self.api()
        root = self.fixture()
        (root / 'unrelated.txt').write_text('do not amend this')
        self.git(root, 'add', 'unrelated.txt')
        before = self.git(root, 'rev-parse', 'HEAD')
        with self.assertRaises(ValueError):
            api.finalize(root)
        self.assertEqual(self.git(root, 'rev-parse', 'HEAD'), before)

    def test_all_publishers_finalize_between_rebase_and_push(self):
        root = Path(__file__).resolve().parents[1]
        for name in ('content-publish.yml', 'article-publish.yml', 'video-sync.yml', 'app-content.yml'):
            with self.subTest(name=name):
                source = (root / '.github/workflows' / name).read_text('utf-8')
                rebase = source.index('git pull --rebase origin main')
                push = source.index('git push origin HEAD:main')
                self.assertIn('python scripts/finalize_publish_manifest.py', source[rebase:push])

    def test_publication_queue_preserves_multiple_waiting_uploads(self):
        root = Path(__file__).resolve().parents[1]
        for name in ('content-publish.yml', 'article-publish.yml', 'video-sync.yml', 'app-content.yml'):
            with self.subTest(name=name):
                source = (root / '.github/workflows' / name).read_text('utf-8')
                self.assertIn('  queue: max', source)


if __name__ == '__main__':
    unittest.main()
