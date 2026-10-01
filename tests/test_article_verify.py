import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from content_pipeline import PipelineError


class ArticleVerifyTests(unittest.TestCase):
    def api(self):
        self.assertIsNotNone(importlib.util.find_spec("verify_article_publish"), "article live verifier is missing")
        import verify_article_publish
        return verify_article_publish

    def fixture(self):
        page = b'<html><article data-article-id="article-safe"></article></html>'
        pdf = b'%PDF-1.4\nfixture'
        listing = b'<div class="newspaper-articles-grid"><article class="newspaper-article-card" data-article-id="article-safe"><a href="books/article-safe.html">Read</a><a href="books/article-safe.pdf">PDF</a></article></div>'
        item = {"kind": "article", "id": "article-safe", "title": "Article", "file": "books/article-safe.html",
                "pdf": "books/article-safe.pdf", "page_sha256": hashlib.sha256(page).hexdigest(),
                "pdf_sha256": hashlib.sha256(pdf).hexdigest()}
        return item, [listing, page, pdf]

    def test_exact_card_page_and_pdf_are_required(self):
        api = self.api()
        item, blobs = self.fixture()
        with patch.object(api.urllib.request, "urlopen", side_effect=[io.BytesIO(blob) for blob in blobs]):
            api.wait_for_publication("https://example.com", item, 0)

    def test_stale_page_is_not_confirmed(self):
        api = self.api()
        item, blobs = self.fixture()
        blobs[1] = b'<html>old</html>'
        with patch.object(api.urllib.request, "urlopen", side_effect=[io.BytesIO(blob) for blob in blobs]):
            with self.assertRaises(PipelineError):
                api.wait_for_publication("https://example.com", item, 0)

    def test_stale_pdf_is_not_confirmed(self):
        api = self.api()
        item, blobs = self.fixture()
        blobs[2] = b'%PDF-1.4\nold'
        with patch.object(api.urllib.request, "urlopen", side_effect=[io.BytesIO(blob) for blob in blobs]):
            with self.assertRaises(PipelineError):
                api.wait_for_publication("https://example.com", item, 0)

    def test_card_in_legacy_grid_is_not_confirmed(self):
        api = self.api()
        item, blobs = self.fixture()
        blobs[0] = blobs[0].replace(b'newspaper-articles-grid', b'article-grid')
        with patch.object(api.urllib.request, "urlopen", side_effect=[io.BytesIO(blob) for blob in blobs]):
            with self.assertRaises(PipelineError):
                api.wait_for_publication("https://example.com", item, 0)

    def test_result_paths_cannot_escape_site_root(self):
        api = self.api()
        item, _ = self.fixture()
        item['file'] = '../outside.html'
        with self.assertRaises(PipelineError):
            api.validate_target(item)


if __name__ == "__main__":
    unittest.main()
