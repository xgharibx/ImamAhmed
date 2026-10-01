import hashlib
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


class LiveVideoSyncTests(unittest.TestCase):
    def fixture(self):
        catalog = b'[{"id":"abcdefghijk","title":"Video","date":"2026-09-30","category":"lessons","sourceChannel":"main"}]\n'
        status = json.dumps({"status": "success", "checked_at": "2026-10-01T01:00:00Z",
                             "total": 1, "catalog_sha256": hashlib.sha256(catalog).hexdigest()}).encode()
        return catalog, status

    def test_accepts_only_the_exact_deployed_catalog_and_sync(self):
        import verify_video_sync as verify
        catalog, status = self.fixture()
        with patch.object(verify.urllib.request, "urlopen", side_effect=[io.BytesIO(catalog), io.BytesIO(status)]):
            result = verify.wait_for_catalog("https://example.com", catalog, status, 0)
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["status"], "verified-live")

    def test_stale_catalog_is_not_reported_as_published(self):
        import verify_video_sync as verify
        catalog, status = self.fixture()
        with patch.object(verify.urllib.request, "urlopen", side_effect=[io.BytesIO(b"[]"), io.BytesIO(status)]):
            with self.assertRaises(verify.PipelineError):
                verify.wait_for_catalog("https://example.com", catalog, status, 0)

    def test_stale_sync_status_is_not_reported_as_published(self):
        import verify_video_sync as verify
        catalog, status = self.fixture()
        with patch.object(verify.urllib.request, "urlopen", side_effect=[io.BytesIO(catalog), io.BytesIO(b"{}")]):
            with self.assertRaises(verify.PipelineError):
                verify.wait_for_catalog("https://example.com", catalog, status, 0)

    def test_status_cannot_claim_a_different_catalog(self):
        import verify_video_sync as verify
        catalog, status = self.fixture()
        bad_status = json.loads(status)
        bad_status["catalog_sha256"] = "wrong"
        with self.assertRaises(verify.PipelineError):
            verify.wait_for_catalog("https://example.com", catalog, json.dumps(bad_status).encode(), 0)


if __name__ == "__main__":
    unittest.main()
