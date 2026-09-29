import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "content_pipeline.py"
SPEC = importlib.util.spec_from_file_location("content_pipeline", MODULE_PATH)
pipeline = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(pipeline)


class ContentPipelineTests(unittest.TestCase):
    def make_docx(self, paragraphs):
        namespace = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        body = "".join(
            f'<w:p><w:r><w:t>{text}</w:t></w:r></w:p>' for text in paragraphs
        )
        xml = f'<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="{namespace}"><w:body>{body}</w:body></w:document>'
        handle = tempfile.NamedTemporaryFile(suffix=".docx", delete=False)
        handle.close()
        path = Path(handle.name)
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("word/document.xml", xml)
        self.addCleanup(path.unlink, missing_ok=True)
        return path

    def test_extract_docx_and_required_sections(self):
        paragraphs = [
            "خُطْبَةُ الجُمُعَةِ بتاريخ ١ صفر ١٤٤٨ هـ",
            "عنوان الخطبة",
            "بقلم فضيلة الشيخ أحمد إسماعيل الفشني",
            "عناصر الخطبة:",
            "١. الخطبة الأولى: العنوان الأول",
            "٢. عنصر تفصيلي مهم",
            "٣. الخطبة الثانية: العنوان الثاني",
            "الخطبة الأولى",
            "نص طويل " * 55,
            "الخطبة الثانية",
            "نص ختامي " * 55,
        ]
        extracted = pipeline.extract_docx_paragraphs(self.make_docx(paragraphs))
        pipeline.validate_new_khutba_content(extracted)
        self.assertEqual(extracted[1], "عنوان الخطبة")
        self.assertGreater(len("\n".join(extracted)), 500)

    def test_rejects_incomplete_khutba(self):
        with self.assertRaises(pipeline.PipelineError):
            pipeline.validate_new_khutba_content(["عناصر الخطبة", "الخطبة الأولى"])

    def test_issue_form_parser_preserves_arabic(self):
        body = """### عنوان الخطبة
الرحمة المهداة

### التاريخ الميلادي
2026-07-24

### ملف Word
[sermon.docx](https://user-attachments.githubusercontent.com/files/1/sermon.docx)
"""
        sections = pipeline.parse_issue_sections(body)
        self.assertEqual(sections["عنوان الخطبة"], "الرحمة المهداة")
        self.assertEqual(sections["التاريخ الميلادي"], "2026-07-24")
        self.assertTrue(pipeline.extract_attachment_url(sections["ملف Word"]).endswith("sermon.docx"))

    def test_only_github_attachment_links_are_accepted(self):
        self.assertEqual(pipeline.extract_attachment_url("https://github.com/user-attachments/assets/abc-123"),
                         "https://github.com/user-attachments/assets/abc-123")
        with self.assertRaises(pipeline.PipelineError):
            pipeline.extract_attachment_url("https://github.com/other/repository")

    def test_github_attachment_cdn_redirect_is_allowed(self):
        self.assertTrue(pipeline.allowed_attachment_redirect("github-production-user-asset-6210df.s3.amazonaws.com"))
        self.assertFalse(pipeline.allowed_attachment_redirect("untrusted.s3.amazonaws.com"))

    def test_video_classification(self):
        self.assertEqual(pipeline.classify_video("خطبة الجمعة القادمة"), "khutbah")
        self.assertEqual(pipeline.classify_video("تلاوة سورة الملك"), "quran")
        self.assertEqual(pipeline.classify_video("كلمة قصيرة", "1:20"), "shorts")
        self.assertEqual(pipeline.classify_video("درس جديد", "14:20"), "lessons")

    def test_shell_escapes_metadata_and_keeps_id(self):
        item = {
            "id": "local-2026-07-24-safe-id",
            "title": 'عنوان <آمن> "مهم"',
            "author": pipeline.DEFAULT_AUTHOR,
            "date": {"display": "١٠ صفر ١٤٤٨ هـ", "iso": "2026-07-24"},
            "content_text": "x",
            "content_html": "",
            "excerpt": "ملخص",
        }
        rendered = pipeline.render_khutba_shell(item, "k-test.html")
        self.assertIn("عنوان &lt;آمن&gt; &quot;مهم&quot;", rendered)
        self.assertIn('data-khutba-id="local-2026-07-24-safe-id"', rendered)
        self.assertNotIn("{{TITLE}}", rendered)

    def test_shell_name_matches_browser_card_slug(self):
        self.assertEqual(pipeline.make_shell_name("2026-07-17", "local-2026-07-17-abc123"),
                         "k-20260717-bg9jywwtmjay.html")

    def test_automatic_metadata_and_two_khutba_outline(self):
        paragraphs = [
            "بِسْمِ اللَّهِ الرَّحْمَنِ الرَّحِيمِ",
            "خُطْبَةُ الْجُمُعَةِ الْقَادِمَةِ",
            "لِفَضِيلَةِ الشَّيْخِ أَحْمَدَ الْفَشَنِيِّ",
            "« وَلَقَدْ كَرَّمْنَا بَنِي آدَمَ »",
            "الْمُوَافِقُ: الْعِشْرُونَ مِنْ رَبِيعٍ الْآخِرِ 1448هـ - الثَّانِي مِنْ أُكْتُوبَرَ 2026م",
            "عَنَاصِرُ الْخُطْبَةِ",
            "أَوَّلًا: كَرَامَةُ الْإِنْسَانِ فِي الْقُرْآنِ.",
            "ثَانِيًا: حُقُوقُ الْإِنْسَانِ فِي السُّنَّةِ.",
            "ثَالِثًا: إِكْرَامُ الضَّيْفِ وَالْجَارِ.",
            "الْخُطْبَةُ الْأُولَى",
            "الحمد لله رب العالمين. " * 30,
            "الْخُطْبَةُ الثَّانِيَةُ",
            "ثَالِثًا: إِكْرَامُ الضَّيْفِ وَالْجَارِ.",
            "الحمد لله وكفى. " * 30,
        ]
        result = pipeline.prepare_khutba_docx(self.make_docx(paragraphs))
        self.assertEqual(result["title"], "وَلَقَدْ كَرَّمْنَا بَنِي آدَمَ")
        self.assertEqual(result["date_iso"], "2026-10-02")
        self.assertIn("الْعِشْرُونَ", result["date_display"])
        self.assertIn("١. الخطبة الأولى: وَلَقَدْ كَرَّمْنَا بَنِي آدَمَ", result["content_text"])
        self.assertIn("٤. الخطبة الثانية: إِكْرَامُ الضَّيْفِ وَالْجَارِ", result["content_text"])
        self.assertLess(result["content_text"].index("الخطبة الثانية:"), result["content_text"].index("الْخُطْبَةُ الْأُولَى\n"))
        self.assertNotIn("**", result["content_text"])

    def test_numeric_date_and_explicit_outline_groups(self):
        paragraphs = [
            "خطبة الجمعة ٢٢ رَبِيعٍ الأَوَّلِ ١٤٤٨ هـ - ٤ سِبْتَمْبَر ٢٠٢٦ م",
            "تحت عنوان \"الإِبْدَاعُ وَالاِبْتِكَارُ فِي العَهْدِ النَّبَوِيِّ\"",
            "لفضيلة الشيخ أحمد إسماعيل الفشني",
            "عناصر الخطبة",
            "الخطبة الأولى:",
            "* بناء الإنسان بالعلم والإبداع.",
            "الخطبة الثانية:",
            "4. بداية العام الدراسي برعاية المواهب.",
            "الموضوع",
            "الحمد لله رب العالمين. " * 30,
            "الخطبة الثانية",
            "الحمد لله وكفى. " * 30,
        ]
        result = pipeline.prepare_khutba_docx(self.make_docx(paragraphs))
        self.assertEqual(result["date_iso"], "2026-09-04")
        self.assertEqual(result["title"], "الإِبْدَاعُ وَالاِبْتِكَارُ فِي العَهْدِ النَّبَوِيِّ")
        self.assertIn("الخطبة الأولى: الإِبْدَاعُ", result["content_text"])
        self.assertIn("الخطبة الثانية: بداية العام الدراسي", result["content_text"])
        self.assertIn("الْخُطْبَةُ الْأُولَى\n", result["content_text"])
        self.assertEqual(result["content_text"].count("الخطبة الأولى:"), 1)
        self.assertNotIn("2. الخطبة الأولى:", result["content_text"])

    def test_accented_title_inside_quoted_preface(self):
        paragraphs = ['خُطْبَةٌ مِنْبَرِيَّةٌ تَحْتَ عُنْوَان" نَبِيُّ الرَّحْمَةِ صَلَّى اللَّهُ عَلَيْهِ وَسَلَّمَ"',
                      "١٥ رَبِيعٍ الأَوَّلِ ١٤٤٨ هـ - ٢٨ أَغُسْطُسَ ٢٠٢٦ م", "عناصر الخطبة:"]
        self.assertEqual(pipeline.extract_khutba_title(paragraphs, Path("fallback.docx")),
                         "نَبِيُّ الرَّحْمَةِ صَلَّى اللَّهُ عَلَيْهِ وَسَلَّمَ")

    def test_publishing_updates_index_and_matching_detail_page(self):
        paragraphs = [
            "خُطْبَةُ الْجُمُعَةِ بتاريخ ١ صفر ١٤٤٨ هـ - ١٧ يوليو ٢٠٢٦ م",
            "عنوان خطبة اختبارية",
            "بقلم فضيلة الشيخ أحمد إسماعيل الفشني",
            "عناصر الخطبة:",
            "١- فضل العلم والعمل.",
            "٢- أثر الصدق في المجتمع (الخطبة الثانية).",
            "الموضوع",
            "الحمد لله رب العالمين. " * 30,
            "الخطبة الثانية",
            "الحمد لله وكفى. " * 30,
        ]
        source = self.make_docx(paragraphs)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            data_path = root / "khutab_written.json"
            index_path = root / "khutab_written_index.json"
            data_path.write_text("[]\n", encoding="utf-8")
            with patch.object(pipeline, "ROOT", root), patch.object(pipeline, "KHUTAB_JSON", data_path), patch.object(pipeline, "KHUTAB_INDEX_JSON", index_path), patch.object(pipeline, "KHUTAB_DIR", root):
                args = pipeline.argparse.Namespace(docx=str(source), title="", date="", date_display="", excerpt="", author=pipeline.DEFAULT_AUTHOR, id="")
                result = pipeline.publish_khutba(args)
                items = json.loads(data_path.read_text(encoding="utf-8"))
                index = json.loads(index_path.read_text(encoding="utf-8"))
                self.assertEqual(index[0]["id"], items[0]["id"])
                self.assertEqual(index[0]["has_content"], True)
                self.assertNotIn("content_text", index[0])
                self.assertEqual(result["file"], "khutab/" + pipeline.make_shell_name("2026-07-17", items[0]["id"]))
                self.assertIn(f'data-khutba-id="{items[0]["id"]}"', (root / Path(result["file"]).name).read_text(encoding="utf-8"))
                (root / "sitemap.xml").write_text(f"<urlset><url><loc>https://ahmedelfashny.com/{result['file']}</loc></url></urlset>", encoding="utf-8")
                self.assertEqual(pipeline.validate_khutba_result(result)["id"], result["id"])
                second_args = pipeline.argparse.Namespace(docx=str(source), title="عنوان خطبة ثانية مختلفة", date="", date_display="", excerpt="", author=pipeline.DEFAULT_AUTHOR, id="")
                second = pipeline.publish_khutba(second_args)
                self.assertNotEqual(second["file"], result["file"])
                second_index = json.loads(index_path.read_text(encoding="utf-8"))
                self.assertEqual(next(row for row in second_index if row["id"] == second["id"])["file"], second["file"])
                (root / "sitemap.xml").write_text(f"<urlset><url><loc>https://ahmedelfashny.com/{second['file']}</loc></url></urlset>", encoding="utf-8")
                self.assertEqual(pipeline.validate_khutba_result(second)["id"], second["id"])
                index[0]["has_content"] = False
                index_path.write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
                with self.assertRaisesRegex(pipeline.PipelineError, "البطاقة"):
                    pipeline.validate_khutba_result(result)

    def test_rejects_missing_gregorian_date_without_writing(self):
        paragraphs = ["عنوان خطبة بلا تاريخ", "عناصر الخطبة:", "١- الأول", "الخطبة الأولى", "نص " * 100, "الخطبة الثانية", "نص " * 100, "الخاتمة"]
        with self.assertRaisesRegex(pipeline.PipelineError, "تاريخ"):
            pipeline.prepare_khutba_docx(self.make_docx(paragraphs))

    def test_issue_needs_only_word_attachment(self):
        source = self.make_docx([
            "خطبة الجمعة بتاريخ ١ صفر ١٤٤٨ هـ - ١٧ يوليو ٢٠٢٦ م",
            "عنوان خطبة اختبارية",
            "بقلم فضيلة الشيخ أحمد إسماعيل الفشني",
            "عناصر الخطبة:",
            "١- فضل العلم والعمل.",
            "٢- أثر الصدق في المجتمع (الخطبة الثانية).",
            "الموضوع",
            "الحمد لله رب العالمين. " * 30,
            "الخطبة الثانية",
            "الحمد لله وكفى. " * 30,
        ])
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            data_path = root / "khutab_written.json"
            data_path.write_text("[]\n", encoding="utf-8")
            event = root / "event.json"
            event.write_text(json.dumps({"issue": {"title": "[نشر خطبة] ملف Word",
                    "body": "### ملف Word\n[sermon.docx](https://github.com/user-attachments/assets/abc-123)"}},
                    ensure_ascii=False), encoding="utf-8")
            with patch.object(pipeline, "KHUTAB_JSON", data_path), patch.object(pipeline, "KHUTAB_INDEX_JSON", root / "index.json"), patch.object(pipeline, "KHUTAB_DIR", root), patch.object(pipeline, "download_docx", return_value=source):
                result = pipeline.publish_issue(pipeline.argparse.Namespace(event=str(event)))
            self.assertEqual(result["kind"], "khutba")
            self.assertEqual(result["title"], "عنوان خطبة اختبارية")
            self.assertEqual(len(json.loads(data_path.read_text(encoding="utf-8"))), 1)


if __name__ == "__main__":
    unittest.main()
