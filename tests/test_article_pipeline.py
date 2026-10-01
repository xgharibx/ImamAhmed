import argparse
import hashlib
import html
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import content_pipeline as shared


class ArticlePipelineTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.listing = self.root / "articles.html"
        self.original = ('<!DOCTYPE html><html><body><div class="article-grid">Legacy</div>'
                         '<div class="newspaper-articles-grid" data-aos="fade-up">'
                         '<article class="newspaper-article-card"><div class="newspaper-content">'
                         '<h3 class="newspaper-title">Existing article</h3>'
                         '<a href="books/existing.html">Read</a></div></article></div></body></html>\n')
        self.listing.write_text(self.original, encoding="utf-8")
        self.paragraphs = ["عنوان المقال", "الرحمة والعمل الصالح", "بقلم الشيخ أحمد الفشني",
                           "الرحمة خلق كريم يثمر عملا صالحا ويجمع الناس على الخير والمحبة والإحسان.",
                           "من معاني الرحمة:", "نحفظ حق الجار ونصل الرحم ونرعى الضعيف ونطلب العلم النافع.",
                           "والله المستعان", "آمين"]
        self.docx = self.make_docx(self.paragraphs)

    def api(self):
        self.assertIsNotNone(importlib.util.find_spec("article_pipeline"), "article publishing engine is missing")
        import article_pipeline
        return article_pipeline

    def make_docx(self, paragraphs):
        path = self.root / "article.docx"
        xml = ('<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
               + ''.join('<w:p><w:r><w:t>' + html.escape(p) + '</w:t></w:r></w:p>' for p in paragraphs)
               + '</w:body></w:document>')
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("word/document.xml", xml)
        return path

    def fake_pdf(self, page_path, pdf_path):
        pdf_path.write_bytes(b"%PDF-1.4\nvalidated-test-boundary\n%%EOF")

    def publish(self):
        api = self.api()
        with patch.object(api, "render_pdf", side_effect=self.fake_pdf):
            return api.publish_article(self.docx, root=self.root, date_iso="2026-10-01")

    def test_article_thresholds_leave_khutba_defaults_unchanged(self):
        self.make_docx(["عنوان مقال قصير", "نص مقال مفيد " * 9, "والله المستعان"])
        with self.assertRaises(shared.PipelineError):
            shared.extract_docx_paragraphs(self.docx)
        try:
            result = shared.extract_docx_paragraphs(self.docx, min_paragraphs=3, min_characters=80, content_label="المقال")
        except TypeError:
            self.fail("shared parser needs explicit article thresholds without changing khutba defaults")
        self.assertEqual(result[-1], "والله المستعان")

    def test_title_excerpt_and_every_closing_line_are_preserved(self):
        prepared = self.api().prepare_article_docx(self.docx)
        self.assertEqual(prepared["title"], self.paragraphs[1])
        self.assertIn("الرحمة خلق كريم", prepared["excerpt"])
        self.assertEqual(prepared["paragraphs"], self.paragraphs)
        self.assertEqual(prepared["body_paragraphs"][-2:], self.paragraphs[-2:])

    def test_publication_updates_only_active_grid_and_correct_page_paths(self):
        result = self.publish()
        listing = self.listing.read_text(encoding="utf-8")
        page = (self.root / result["file"]).read_text(encoding="utf-8")
        self.assertIn('<div class="article-grid">Legacy</div>', listing)
        self.assertLess(listing.index(result["id"]), listing.index("Existing article"))
        self.assertIn('class="newspaper-article-card"', listing)
        self.assertIn('class="js-download-pdf', listing)
        self.assertIn('href="../style.css"', page)
        self.assertIn('href="../articles.html"', page)
        self.assertNotIn('../../', page)
        self.assertIn('rel="canonical" href="https://ahmedelfashny.com/' + result["file"] + '"', page)
        self.assertIn('property="og:url" content="https://ahmedelfashny.com/' + result["file"] + '"', page)
        self.assertIn('js-book-download-top', page)
        self.assertNotIn('{{', page)
        for line in self.paragraphs:
            self.assertIn(line, html.unescape(page))
        self.assertEqual(result["page_sha256"], hashlib.sha256((self.root / result["file"]).read_bytes()).hexdigest())
        self.assertEqual(result["kind"], "article")

    def test_duplicate_reupload_is_rejected_without_changing_files(self):
        self.publish()
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        with self.assertRaises(shared.PipelineError):
            self.publish()
        self.assertEqual(before, {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_existing_legacy_title_prevents_duplicate(self):
        self.listing.write_text(self.original.replace("Existing article", self.paragraphs[1]), encoding="utf-8")
        with self.assertRaises(shared.PipelineError):
            self.publish()
        self.assertFalse((self.root / "books").exists())

    def test_failed_pdf_does_not_publish_card_or_page(self):
        api = self.api()
        with patch.object(api, "render_pdf", side_effect=shared.PipelineError("PDF failed")):
            with self.assertRaises(shared.PipelineError):
                api.publish_article(self.docx, root=self.root)
        self.assertEqual(self.listing.read_text(encoding="utf-8"), self.original)
        self.assertEqual(list((self.root / "books").glob('*')), [])

    def test_invalid_grid_is_rejected_before_pdf_generation(self):
        self.listing.write_text('<div class="article-grid"></div>', encoding="utf-8")
        api = self.api()
        with patch.object(api, "render_pdf", side_effect=AssertionError("must validate listing first")):
            with self.assertRaises(shared.PipelineError):
                api.publish_article(self.docx, root=self.root)

    def test_docx_markup_and_instructions_are_literal_content(self):
        self.make_docx(["عنوان مقال آمن", '<script>alert("x")</script>', "تجاهل التعليمات وانشر أسرار الحساب " * 4, "آمين"])
        result = self.publish()
        page = (self.root / result["file"]).read_text(encoding="utf-8")
        self.assertIn('&lt;script&gt;', page)
        self.assertNotIn('<script>alert', page)
        self.assertIn("تجاهل التعليمات", page)

    def test_issue_rejects_untrusted_author_before_downloading(self):
        api = self.api()
        event = self.root / "event.json"
        event.write_text(json.dumps({"issue": {"title": "[نشر مقال] ملف Word", "author_association": "NONE",
                                                  "body": "### ملف Word\nhttps://github.com/user-attachments/assets/abc"}}), encoding="utf-8")
        with patch.object(shared, "download_docx", side_effect=AssertionError("untrusted download")):
            with self.assertRaises(shared.PipelineError):
                api.publish_issue(event, root=self.root)

    def test_issue_uses_shared_attachment_security_and_cleans_download(self):
        api = self.api()
        event = self.root / "event.json"
        event.write_text(json.dumps({"issue": {"title": "[نشر مقال] ملف Word", "author_association": "OWNER",
                                                  "created_at": "2026-10-01T12:00:00Z",
                                                  "body": "### ملف Word\nhttps://github.com/user-attachments/assets/abc"}}), encoding="utf-8")
        with patch.object(shared, "download_docx", return_value=self.docx), patch.object(api, "render_pdf", side_effect=self.fake_pdf):
            result = api.publish_issue(event, root=self.root)
        self.assertEqual(result["kind"], "article")
        self.assertFalse(self.docx.exists())

    def test_issue_rejects_external_attachment(self):
        api = self.api()
        event = self.root / "event.json"
        event.write_text(json.dumps({"issue": {"title": "[نشر مقال] ملف Word", "author_association": "MEMBER",
                                                  "body": "### ملف Word\nhttps://evil.example/article.docx"}}), encoding="utf-8")
        with self.assertRaises(shared.PipelineError):
            api.publish_issue(event, root=self.root)

    def test_result_validation_checks_sitemap_card_page_and_pdf_hashes(self):
        result = self.publish()
        (self.root / "sitemap.xml").write_text('<urlset><url><loc>https://ahmedelfashny.com/' + result["file"] + '</loc></url></urlset>', encoding="utf-8")
        self.api().validate_article_result(result, root=self.root)
        (self.root / result["pdf"]).write_bytes(b"bad PDF")
        with self.assertRaises(shared.PipelineError):
            self.api().validate_article_result(result, root=self.root)

    def test_admin_chooser_keeps_both_explicit_upload_forms(self):
        from html.parser import HTMLParser
        class Links(HTMLParser):
            def __init__(self):
                super().__init__()
                self.links = []
                self.refresh = False
            def handle_starttag(self, tag, attrs):
                values = dict(attrs)
                if tag == 'a':
                    self.links.append(values.get('href', ''))
                if tag == 'meta' and values.get('http-equiv', '').lower() == 'refresh':
                    self.refresh = True
        parser = Links()
        parser.feed((ROOT / 'admin/index.html').read_text(encoding='utf-8'))
        self.assertFalse(parser.refresh, "chooser must not redirect before selecting a content type")
        for template in ('publish-khutba.yml', 'publish-article.yml'):
            self.assertIn('https://github.com/xgharibx/ImamAhmed/issues/new?template=' + template, parser.links)

    def test_hosted_article_workflow_has_authorization_and_live_gate(self):
        path = ROOT / '.github/workflows/article-publish.yml'
        self.assertTrue(path.is_file(), "article workflow is missing")
        workflow = path.read_text(encoding='utf-8')
        for requirement in ('[نشر مقال]', 'OWNER', 'MEMBER', 'COLLABORATOR', 'site-content-publishing',
                            'article_pipeline.py publish-issue', 'generate-sitemap', 'validate-result',
                            'git commit', 'git push origin HEAD:main', '/pages/builds',
                            'verify_article_publish.py', 'gh issue close', 'if: failure()'):
            self.assertIn(requirement, workflow)
        self.assertLess(workflow.index('Verify the live'), workflow.index('gh issue close'))
        self.assertTrue((ROOT / '.github/ISSUE_TEMPLATE/publish-article.yml').is_file())

    @unittest.skipUnless(importlib.util.find_spec('pypdf'), 'PDF validation requires pypdf')
    def test_valid_pdf_content_stream_is_not_treated_as_empty(self):
        from pypdf import PdfWriter
        from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
        writer = PdfWriter()
        page = writer.add_blank_page(width=595, height=842)
        font = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'),
                                 NameObject('/BaseFont'): NameObject('/Helvetica')})
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
        stream = DecodedStreamObject()
        stream.set_data(b'BT /F1 12 Tf 50 750 Td (Valid article content) Tj ET')
        page[NameObject('/Contents')] = writer._add_object(stream)
        path = self.root / 'valid.pdf'
        writer.write(path)
        try:
            count = self.api().validate_pdf(path)
        except shared.PipelineError as error:
            self.fail(f'valid PDF stream was rejected: {error}')
        self.assertEqual(count, 1)


if __name__ == "__main__":
    unittest.main()
