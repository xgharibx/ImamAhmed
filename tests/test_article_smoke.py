import hashlib
import importlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from xml.etree import ElementTree as ET
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import content_pipeline as shared


class ArticleSmokeTests(unittest.TestCase):
    def smoke(self):
        try:
            return importlib.import_module("smoke_article_publish")
        except ModuleNotFoundError as error:
            if error.name != "smoke_article_publish":
                raise
            self.fail("Temporary-root article smoke implementation is missing")

    def test_checkout_and_nested_paths_are_rejected(self):
        smoke = self.smoke()
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "checkout"
            source.mkdir()
            for candidate in (source, source / "fake-temp", source.parent):
                with self.subTest(candidate=candidate), self.assertRaises(shared.PipelineError):
                    smoke.require_isolated(source, candidate)
            smoke.require_isolated(source, Path(directory) / "outside")

    def test_artifacts_cannot_write_into_checkout_or_overwrite_evidence(self):
        smoke = self.smoke()
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "checkout"
            source.mkdir()
            with self.assertRaises(shared.PipelineError):
                smoke.validate_output(source, source / "artifacts")
            output = Path(directory) / "artifacts"
            output.mkdir()
            (output / "report.json").write_text("previous evidence", encoding="utf-8")
            with self.assertRaises(shared.PipelineError):
                smoke.validate_output(source, output)
            self.assertEqual((output / "report.json").read_text(), "previous evidence")

    def test_copy_follows_site_resources_without_secrets_or_android(self):
        smoke = self.smoke()
        with tempfile.TemporaryDirectory() as directory:
            source, target = Path(directory) / "checkout", Path(directory) / "temporary"
            source.mkdir()
            target.mkdir()
            listing = '<html><link rel="stylesheet" href="style.css"><script src="main.js"></script><div class="newspaper-articles-grid"></div></html>'
            (source / "articles.html").write_text(listing)
            (source / "style.css").write_text('body { background: url("assets/mark.svg"); }')
            (source / "main.js").write_text("window.example = true;")
            (source / "assets").mkdir()
            (source / "assets/mark.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
            (source / ".env").write_text("SECRET=do-not-copy")
            (source / "android").mkdir()
            (source / "android/secret.html").write_text("not public")
            (source / "unrelated.html").write_text("not needed")
            smoke.copy_site_resources(source, target)
            self.assertEqual((target / "articles.html").read_text(), listing)
            self.assertTrue((target / "assets/mark.svg").is_file())
            self.assertFalse((target / ".env").exists())
            self.assertFalse((target / "android").exists())
            self.assertFalse((target / "unrelated.html").exists())
            self.assertEqual((source / ".env").read_text(), "SECRET=do-not-copy")

    def test_mirror_mapping_cannot_read_outside_checkout(self):
        smoke = self.smoke()
        with tempfile.TemporaryDirectory() as directory:
            source, target = Path(directory) / "checkout", Path(directory) / "temporary"
            source.mkdir()
            target.mkdir()
            (source / "articles.html").write_text('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Amiri">')
            (source / "assets/app-content").mkdir(parents=True)
            (source / "assets/app-content/mappings.json").write_text('{"https://fonts.googleapis.com/css2?family=Amiri":"../secret.css"}')
            (Path(directory) / "secret.css").write_text("private")
            with self.assertRaises(shared.PipelineError):
                smoke.copy_site_resources(source, target)
            self.assertFalse((target / "secret.css").exists())

    def test_failed_real_publication_reports_failure_without_changing_source(self):
        smoke = self.smoke()
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "checkout"
            source.mkdir()
            listing = "<html><body>No active grid</body></html>"
            (source / "articles.html").write_text(listing)
            output = Path(directory) / "artifacts"
            with self.assertRaises(shared.PipelineError):
                smoke.run_smoke(output, source=source)
            report = json.loads((output / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "failed")
            self.assertEqual(report["phase"], "publish-article-and-real-pdf")
            self.assertFalse((output / "article.pdf").exists())
            self.assertEqual((source / "articles.html").read_text(), listing)
            self.assertFalse((source / "books").exists())

    def test_fixture_is_real_docx_and_preserves_arabic_closing_lines(self):
        smoke = self.smoke()
        with tempfile.TemporaryDirectory() as directory:
            docx = Path(directory) / "fixture.docx"
            smoke.write_fixture(docx)
            with zipfile.ZipFile(docx) as archive:
                for name in ("[Content_Types].xml", "_rels/.rels", "word/document.xml"):
                    ET.fromstring(archive.read(name))
            paragraphs = shared.extract_docx_paragraphs(docx, min_paragraphs=3, min_characters=80)
            self.assertEqual(paragraphs[0], "اختبار النشر الآمن للمقال")
            self.assertEqual(paragraphs[-2:], ["والله المستعان", "آمين"])

    def test_pdf_closing_check_handles_observed_rtl_word_order_but_not_missing_text(self):
        smoke = self.smoke()
        self.assertTrue(callable(getattr(smoke, "validate_pdf_closing_lines", None)), "RTL closing-line validation is missing")
        smoke.validate_pdf_closing_lines("المستعان  والله\nآمين\n")
        smoke.validate_pdf_closing_lines("والله المستعان\nآمين\n")
        with self.assertRaises(shared.PipelineError):
            smoke.validate_pdf_closing_lines("المستعان والله\n")
        with self.assertRaises(shared.PipelineError):
            smoke.validate_pdf_closing_lines("المستعان\nآمين\n")

    def test_sitemap_writes_only_temporary_site_and_restores_shared_root(self):
        smoke = self.smoke()
        original_root, original_khutab = shared.ROOT, shared.KHUTAB_DIR
        original_sitemap = (original_root / "sitemap.xml").read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "books").mkdir()
            (root / "books/article-fixture.html").write_text("<html>temporary</html>")
            smoke.generate_sitemap(root)
            locations = [node.text for node in ET.parse(root / "sitemap.xml").getroot().iter() if node.tag.endswith("loc")]
            self.assertIn("https://ahmedelfashny.com/books/article-fixture.html", locations)
        self.assertEqual((shared.ROOT, shared.KHUTAB_DIR), (original_root, original_khutab))
        self.assertEqual((original_root / "sitemap.xml").read_bytes(), original_sitemap)

    def test_manifest_must_contain_exact_article_and_listing(self):
        smoke = self.smoke()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "books").mkdir()
            data = b"<html>temporary article</html>\n"
            (root / "books/article-fixture.html").write_bytes(data)
            (root / "articles.html").write_bytes(b"listing")
            manifest = {"resources": [
                {"key": "/books/article-fixture.html", "path": "books/article-fixture.html", "sha256": hashlib.sha256(data).hexdigest()},
                {"key": "/articles.html", "path": "articles.html", "sha256": hashlib.sha256(b"listing").hexdigest()},
            ]}
            item = {"file": "books/article-fixture.html"}
            smoke.validate_manifest_article(root, manifest, item)
            manifest["resources"][0]["sha256"] = "0" * 64
            with self.assertRaises(shared.PipelineError):
                smoke.validate_manifest_article(root, manifest, item)
            manifest["resources"] = manifest["resources"][1:]
            with self.assertRaises(shared.PipelineError):
                smoke.validate_manifest_article(root, manifest, item)


if __name__ == "__main__":
    unittest.main()
