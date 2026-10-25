import json
import importlib.util
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "content_pipeline.py"
SPEC = importlib.util.spec_from_file_location("content_pipeline", MODULE_PATH)
content_pipeline = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(content_pipeline)


class ShareImageSelectionTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.pool = self.root / "assets" / "share-pics"
        self.pool.mkdir(parents=True)
        for name in ("portrait-a.jpg", "portrait-b.jpg", "portrait-c.jpg"):
            (self.pool / name).write_bytes(b"image")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_assigns_a_shuffled_balanced_rotation_without_repeating_until_cycle(self):
        selected = [
            content_pipeline.select_share_image(f"published-item-{index}", root=self.root)
            for index in range(3)
        ]

        expected = {
            f"{content_pipeline.SITE_URL}/assets/share-pics/{name}"
            for name in ("portrait-a.jpg", "portrait-b.jpg", "portrait-c.jpg")
        }
        self.assertEqual(set(selected), expected)

        for index in range(3, 8):
            content_pipeline.select_share_image(f"published-item-{index}", root=self.root)
        state = json.loads((self.root / "data" / "share-image-usage.json").read_text(encoding="utf-8"))
        self.assertEqual(sorted(state["usage"].values()), [2, 3, 3])

    def test_new_images_join_the_rotation_before_previously_used_images_repeat(self):
        state_path = self.root / "data" / "share-image-usage.json"
        state_path.parent.mkdir(parents=True)
        state_path.write_text(json.dumps({"schema": 1, "usage": {
            "portrait-a.jpg": 4, "portrait-b.jpg": 4, "portrait-c.jpg": 4,
        }}), encoding="utf-8")
        (self.pool / "portrait-d.jpg").write_bytes(b"image")

        selected = content_pipeline.select_share_image("next-published-item", root=self.root)

        self.assertEqual(selected, f"{content_pipeline.SITE_URL}/assets/share-pics/portrait-d.jpg")

    def test_updates_all_social_preview_tags_and_removes_inaccurate_dimensions(self):
        markup = '''<meta property="og:image" content="old.jpg">
<meta property="og:image:url" content="old.jpg">
<meta property="og:image:secure_url" content="old.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:image" content="old.jpg">'''

        updated = content_pipeline.update_share_image_metadata(markup, "https://example.com/new.jpg")

        self.assertEqual(updated.count('content="https://example.com/new.jpg"'), 4)
        self.assertNotIn("og:image:width", updated)
        self.assertNotIn("og:image:height", updated)


if __name__ == "__main__":
    unittest.main()
