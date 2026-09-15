import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import video_catalog as pipeline
import refresh_video_catalog as refresh


class VideoCatalogTests(unittest.TestCase):
    def test_published_catalog_integrity(self):
        videos = pipeline.read_json(pipeline.VIDEOS_JSON)
        self.assertEqual(len(videos), len({video["id"] for video in videos}))
        missing = set()
        for video in videos:
            self.assertIn(video["category"], pipeline.VALID_VIDEO_CATEGORIES)
            if video["id"] in {"KW-L6uOsJAs", "vao6ATA9FXs"}:
                self.assertEqual(video["sourceChannel"], "legacy")
            else:
                self.assertIn(video["sourceChannel"], {"main", "tarteel"})
            if video.get("date"):
                self.assertEqual(pipeline.dt.date.fromisoformat(video["date"]).isoformat(), video["date"])
            else:
                missing.add(video["id"])
            if video.get("publishedAt"):
                pipeline.dt.datetime.fromisoformat(video["publishedAt"])
        self.assertLessEqual(missing, {"KW-L6uOsJAs", "vao6ATA9FXs"})

    def test_category_precedence(self):
        self.assertEqual(pipeline.classify_video("برنامج في نور القرآن الكريم تفسير سورة الملك"), "fi-nur-allah")
        self.assertEqual(pipeline.classify_video("تفسير سورة الملك"), "tafseer")
        self.assertEqual(pipeline.classify_video("تلاوة سورة الجمعة"), "quran")
        self.assertEqual(pipeline.classify_video("مقطع من خطبة الجمعة", feed="shorts"), "shorts")
        self.assertEqual(pipeline.classify_video("سورة الملك", default="quran", feed="shorts"), "quran")
        self.assertEqual(pipeline.classify_video("صلاة العشاء والتراويح ليلة ١٣ رمضان"), "quran")
        self.assertEqual(pipeline.classify_video("خاطرة التراويح سلسلة المبشرون بالجنة"), "lessons")
        self.assertEqual(pipeline.classify_video("سلسلة الدعاء في القرآن"), "lessons")
        self.assertEqual(pipeline.classify_video('بَرْنَامَجُ قِصَّةٌ وَعِبْرَةٌ الحلقة 6'), "qisas-ibra")
        self.assertEqual(pipeline.classify_video("اوصل اهلي ازاي؟", "2:10"), "shorts")
        self.assertEqual(pipeline.classify_video("سورة النجم شاهد كيف قرأها"), "quran")
        self.assertEqual(pipeline.classify_video("مداخلتي على قناة نايل لايف"), "tv")
        self.assertEqual(pipeline.classify_video("حلقة جديدة أذيعت فجر اليوم السلام النفسي"), "tv")
        self.assertEqual(pipeline.classify_video("نعمة الستر من روائع الخطب المنبرية"), "khutbah")
        self.assertEqual(pipeline.classify_video("قرآن الصباح"), "quran")
        self.assertEqual(pipeline.classify_video("دعاء يوم الجمعة #صلاة_الجمعة", "1:20"), "shorts")

    def test_public_metadata_does_not_require_playback(self):
        payload = {
            "videoDetails": {"videoId": "abcdefghijk", "title": "تلاوة", "lengthSeconds": "120", "channelId": "official"},
            "microformat": {"playerMicroformatRenderer": {"uploadDate": "2026-07-05T10:15:19-07:00"}},
            "playabilityStatus": {"status": "UNPLAYABLE", "reason": "The page needs to be reloaded."},
        }
        with patch.object(refresh.urllib.request, "urlopen", return_value=io.BytesIO(json.dumps(payload).encode())):
            metadata = refresh.fetch_metadata("abcdefghijk", {})
        self.assertEqual(metadata["upload_date"], "2026-07-05")
        self.assertEqual(metadata["duration"], 120)
        self.assertNotIn("unavailable", metadata)

    def test_wrong_video_metadata_is_not_accepted(self):
        payload = {"videoDetails": {"videoId": "differentid", "title": "other"}}
        with patch.object(refresh.urllib.request, "urlopen", return_value=io.BytesIO(json.dumps(payload).encode())):
            self.assertIn("unavailable", refresh.fetch_metadata("abcdefghijk", {}))


if __name__ == "__main__":
    unittest.main()
