import argparse
import copy
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import video_catalog as pipeline
import refresh_video_catalog as refresh


class ScheduledVideoSyncTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.catalog = self.root / "videos.json"
        self.status = self.root / "status.json"
        self.old = {
            "id": "aaaaaaaaaaa", "title": "Reviewed video", "date": "2026-09-10",
            "publishedAt": "2026-09-10T12:00:00Z", "duration": "10:00",
            "category": "tv", "categoryVerified": True, "sourceChannel": "main",
            "channelHandle": "@main", "channelName": "Main",
        }
        pipeline.write_json(self.catalog, [self.old])
        self.sources = [
            {"sourceChannel": "main", "url": "https://www.youtube.com/@main",
             "channelHandle": "@main", "channelName": "Main", "feeds": ["videos", "shorts"]},
            {"sourceChannel": "tarteel", "url": "https://www.youtube.com/@tarteel",
             "channelHandle": "@tarteel", "channelName": "Recitations", "feeds": ["videos"],
             "defaultCategory": "quran"},
        ]
        self.metadata = {
            "bbbbbbbbbbb": {"id": "bbbbbbbbbbb", "title": "New lesson", "upload_date": "2026-09-30",
                            "publishedAt": "2026-09-30T13:00:00-07:00", "duration": 600,
                            "channel_id": "main-channel", "live_status": "not_live"},
            "ccccccccccc": {"id": "ccccccccccc", "title": "New recitation", "upload_date": "2026-09-29",
                            "publishedAt": "2026-09-29T10:00:00Z", "duration": 400,
                            "channel_id": "tarteel-channel", "live_status": "not_live"},
        }
        self.fetched = []
        self.args = argparse.Namespace(cache=str(self.root / "cache"), limit=0, workers=2,
                                       refresh_feeds=True, apply=True, new_only=True, report=str(self.status))

    def feed(self, url, **kwargs):
        ids = ["aaaaaaaaaaa", "bbbbbbbbbbb"] if "@main" in url else ["ccccccccccc"]
        if url.endswith("shorts"):
            ids = ["bbbbbbbbbbb"]
        return {"channel_id": "main-channel" if "@main" in url else "tarteel-channel",
                "entries": [{"id": value, "title": value} for value in ids]}

    def fetch(self, video_id, context):
        self.fetched.append(video_id)
        return copy.deepcopy(self.metadata[video_id])

    def run_sync(self, overrides=None, feed=None):
        original_read = pipeline.read_json

        def read(path):
            if path == pipeline.CHANNELS_CONFIG:
                return self.sources
            if path.name == "video-category-overrides.json":
                return overrides or {}
            return original_read(path)

        with patch.object(pipeline, "VIDEOS_JSON", self.catalog), \
                patch.object(pipeline, "read_json", side_effect=read), \
                patch.object(pipeline, "run_yt_dlp", side_effect=feed or self.feed), \
                patch.object(refresh, "fetch_metadata", side_effect=self.fetch):
            return refresh.refresh(self.args)

    def test_incremental_sync_preserves_reviewed_records(self):
        self.run_sync()
        records = pipeline.read_json(self.catalog)
        self.assertEqual(next(row for row in records if row["id"] == self.old["id"]), self.old)
        self.assertEqual(set(self.fetched), set(self.metadata))

    def test_sources_shorts_and_reviewed_overrides_are_respected(self):
        self.run_sync({"bbbbbbbbbbb": {"category": "fi-nur-allah", "reason": "Reviewed series"}})
        records = {row["id"]: row for row in pipeline.read_json(self.catalog)}
        self.assertEqual(records["bbbbbbbbbbb"]["category"], "fi-nur-allah")
        self.assertEqual(records["ccccccccccc"]["category"], "quran")
        self.assertEqual(records["ccccccccccc"]["sourceChannel"], "tarteel")
        self.assertEqual(len(records), 3)

    def test_failed_new_metadata_leaves_published_files_unchanged(self):
        self.metadata["bbbbbbbbbbb"] = {"id": "bbbbbbbbbbb", "unavailable": "Missing date"}
        before = self.catalog.read_bytes()
        with self.assertRaises(pipeline.PipelineError):
            self.run_sync()
        self.assertEqual(self.catalog.read_bytes(), before)
        self.assertFalse(self.status.exists())

    def test_wrong_channel_metadata_is_never_published(self):
        self.metadata["bbbbbbbbbbb"]["channel_id"] = "unrelated-channel"
        before = self.catalog.read_bytes()
        with self.assertRaises(pipeline.PipelineError):
            self.run_sync()
        self.assertEqual(self.catalog.read_bytes(), before)

    def test_wrong_channel_live_metadata_is_not_silently_deferred(self):
        self.metadata["bbbbbbbbbbb"].update({"channel_id": "unrelated-channel", "live_status": "is_live"})
        before = self.catalog.read_bytes()
        with self.assertRaises(pipeline.PipelineError):
            self.run_sync()
        self.assertEqual(self.catalog.read_bytes(), before)
        self.assertFalse(self.status.exists())

    def test_live_videos_are_skipped_until_completed(self):
        self.metadata["bbbbbbbbbbb"]["live_status"] = "is_live"
        self.run_sync()
        self.assertNotIn("bbbbbbbbbbb", {row["id"] for row in pipeline.read_json(self.catalog)})
        self.assertEqual(pipeline.read_json(self.status)["live_skipped"], ["bbbbbbbbbbb"])

    def test_previously_confirmed_pending_video_retries_without_blocking_valid_uploads(self):
        completed = copy.deepcopy(self.metadata['bbbbbbbbbbb'])
        self.metadata['bbbbbbbbbbb']['live_status'] = 'is_live'
        self.run_sync()
        self.metadata['bbbbbbbbbbb'] = {'id': 'bbbbbbbbbbb', 'unavailable': 'Sign in to confirm you are not a bot'}
        self.run_sync()
        status = pipeline.read_json(self.status)
        self.assertEqual(status['errors'], [])
        self.assertEqual([item['id'] for item in status['deferred_pending']], ['bbbbbbbbbbb'])
        self.assertNotIn('bbbbbbbbbbb', status['live_skipped'])
        self.assertNotIn('bbbbbbbbbbb', {row['id'] for row in pipeline.read_json(self.catalog)})
        self.run_sync()
        self.assertEqual([item['id'] for item in pipeline.read_json(self.status)['deferred_pending']], ['bbbbbbbbbbb'])
        self.metadata['bbbbbbbbbbb'] = completed
        self.run_sync()
        self.assertIn('bbbbbbbbbbb', {row['id'] for row in pipeline.read_json(self.catalog)})
        self.assertEqual(pipeline.read_json(self.status)['deferred_pending'], [])

    def test_stale_pending_proof_does_not_suppress_a_metadata_error(self):
        pipeline.write_json(self.status, {'status': 'success', 'catalog_sha256': 'stale', 'live_skipped': ['bbbbbbbbbbb']})
        self.metadata['bbbbbbbbbbb'] = {'id': 'bbbbbbbbbbb', 'unavailable': 'Unavailable'}
        before = self.catalog.read_bytes()
        with self.assertRaises(pipeline.PipelineError):
            self.run_sync()
        self.assertEqual(before, self.catalog.read_bytes())

    def test_channel_pending_marker_defers_metadata_requests(self):
        def feed(url, **kwargs):
            payload = self.feed(url, **kwargs)
            for item in payload["entries"]:
                if item["id"] == "bbbbbbbbbbb":
                    item["live_status"] = "is_upcoming"
            return payload
        self.run_sync(feed=feed)
        self.assertNotIn("bbbbbbbbbbb", self.fetched)
        self.assertEqual(pipeline.read_json(self.status)["live_skipped"], ["bbbbbbbbbbb"])

    def test_invalid_dates_are_not_published(self):
        self.metadata["bbbbbbbbbbb"]["upload_date"] = "2026-02-31"
        before = self.catalog.read_bytes()
        with self.assertRaises(pipeline.PipelineError):
            self.run_sync()
        self.assertEqual(self.catalog.read_bytes(), before)

    def test_empty_channel_response_cannot_be_reported_as_success(self):
        with self.assertRaises(pipeline.PipelineError):
            self.run_sync(feed=lambda *args, **kwargs: {"entries": []})
        self.assertFalse(self.status.exists())

    def test_existing_reviewed_override_is_applied_without_refetching(self):
        self.run_sync({"aaaaaaaaaaa": {"category": "lessons", "reason": "Reviewed correction"}})
        existing = next(row for row in pipeline.read_json(self.catalog) if row["id"] == "aaaaaaaaaaa")
        self.assertEqual(existing, {**self.old, "category": "lessons"})
        self.assertNotIn("aaaaaaaaaaa", self.fetched)

    def test_invalid_entries_cannot_be_reported_as_successful_feed(self):
        with self.assertRaises(pipeline.PipelineError):
            self.run_sync(feed=lambda *args, **kwargs: {"channel_id": "main-channel", "entries": [None, {"id": "bad"}]})
        self.assertFalse(self.status.exists())

    def test_status_identifies_both_sources_and_the_exact_published_catalog(self):
        self.run_sync()
        status = pipeline.read_json(self.status)
        self.assertEqual(status["catalog_sha256"], hashlib.sha256(self.catalog.read_bytes()).hexdigest())
        self.assertEqual(status["total"], 3)
        self.assertEqual({row["channel"] for row in status["feeds"]}, {"main", "tarteel"})
        self.assertEqual(status["status"], "success")
        pipeline.dt.datetime.fromisoformat(status["checked_at"])
        before = self.catalog.read_bytes()
        self.fetched.clear()
        self.run_sync()
        self.assertEqual(self.catalog.read_bytes(), before)
        self.assertEqual(self.fetched, [])

    def test_order_uses_the_exact_timestamp_across_timezones(self):
        self.metadata["bbbbbbbbbbb"]["publishedAt"] = "2026-09-29T23:30:00-07:00"
        self.metadata["bbbbbbbbbbb"]["upload_date"] = "2026-09-29"
        self.metadata["ccccccccccc"]["publishedAt"] = "2026-09-30T01:00:00Z"
        self.metadata["ccccccccccc"]["upload_date"] = "2026-09-30"
        self.run_sync()
        self.assertEqual(pipeline.read_json(self.catalog)[0]["id"], "bbbbbbbbbbb")

    def test_publication_date_takes_priority_over_private_upload_date(self):
        payload = {"videoDetails": {"videoId": "bbbbbbbbbbb", "title": "Video", "lengthSeconds": "120"},
                   "microformat": {"playerMicroformatRenderer": {
                       "uploadDate": "2026-09-20T10:00:00Z", "publishDate": "2026-09-30T12:00:00Z"}}}
        with patch.object(refresh.urllib.request, "urlopen", return_value=io.BytesIO(json.dumps(payload).encode())):
            metadata = refresh.fetch_metadata("bbbbbbbbbbb", {})
        self.assertEqual(metadata["upload_date"], "2026-09-30")
        self.assertEqual(metadata["publishedAt"], "2026-09-30T12:00:00Z")

    def test_upcoming_without_publication_date_does_not_block_completed_videos(self):
        payload = {"videoDetails": {"videoId": "bbbbbbbbbbb", "title": "Upcoming", "isUpcoming": True}}
        with patch.object(refresh.urllib.request, "urlopen", return_value=io.BytesIO(json.dumps(payload).encode())):
            self.metadata["bbbbbbbbbbb"] = refresh.fetch_metadata("bbbbbbbbbbb", {})
        self.run_sync()
        self.assertEqual({row["id"] for row in pipeline.read_json(self.catalog)}, {"aaaaaaaaaaa", "ccccccccccc"})
        self.assertEqual(pipeline.read_json(self.status)["live_skipped"], ["bbbbbbbbbbb"])

    def test_bot_checked_player_with_public_live_watch_page_defers_only_live_video(self):
        blocked = {"playabilityStatus": {"status": "LOGIN_REQUIRED", "reason": "Sign in to confirm you’re not a bot"}}
        watch_player = {"videoDetails": {"videoId": "bbbbbbbbbbb", "title": "Live recitation", "isLive": True,
                                          "channelId": "main-channel", "lengthSeconds": "0"},
                        "microformat": {"playerMicroformatRenderer": {"externalChannelId": "main-channel",
                            "liveBroadcastDetails": {"isLiveNow": True}}}}
        watch_html = ('<html><script>var ytInitialPlayerResponse = ' + json.dumps(watch_player) + ';</script></html>').encode()
        with patch.object(refresh.urllib.request, "urlopen", side_effect=[
                io.BytesIO(json.dumps(blocked).encode()), io.BytesIO(watch_html)]):
            self.metadata["bbbbbbbbbbb"] = refresh.fetch_metadata("bbbbbbbbbbb", {})
        try:
            self.run_sync()
        except pipeline.PipelineError as error:
            self.fail(f"Confirmed public live metadata should be deferred, not abort sync: {error}")
        records = pipeline.read_json(self.catalog)
        self.assertEqual({row["id"] for row in records}, {"aaaaaaaaaaa", "ccccccccccc"})
        self.assertEqual(next(row for row in records if row["id"] == "aaaaaaaaaaa"), self.old)
        status = pipeline.read_json(self.status)
        self.assertEqual(status["live_skipped"], ["bbbbbbbbbbb"])
        self.assertEqual(status["errors"], [])
        pipeline.validate_catalog(records)

    def test_bot_checked_player_with_completed_public_watch_page_still_fails_closed(self):
        reason = "Sign in to confirm you’re not a bot"
        blocked = {"playabilityStatus": {"status": "LOGIN_REQUIRED", "reason": reason}}
        completed = {"videoDetails": {"videoId": "bbbbbbbbbbb", "title": "Completed stream", "isLiveContent": True,
                                       "channelId": "main-channel", "lengthSeconds": "600"},
                     "microformat": {"playerMicroformatRenderer": {"externalChannelId": "main-channel",
                         "publishDate": "2026-09-30T12:00:00Z",
                         "liveBroadcastDetails": {"isLiveNow": False, "endTimestamp": "2026-09-30T12:00:00Z"}}}}
        watch_html = ('<script>var ytInitialPlayerResponse = ' + json.dumps(completed) + ';</script>').encode()
        with patch.object(refresh.urllib.request, "urlopen", side_effect=[
                io.BytesIO(json.dumps(blocked).encode()), io.BytesIO(watch_html)]):
            self.metadata["bbbbbbbbbbb"] = refresh.fetch_metadata("bbbbbbbbbbb", {})
        before = self.catalog.read_bytes()
        with self.assertRaises(pipeline.PipelineError):
            self.run_sync()
        self.assertEqual(self.catalog.read_bytes(), before)
        self.assertEqual(self.metadata["bbbbbbbbbbb"].get("unavailable"), reason)
        self.assertFalse(self.status.exists())

    def test_incomplete_channel_continuation_is_fatal(self):
        import subprocess
        from yt_dlp import YoutubeDL, parse_options
        from yt_dlp.extractor.youtube import YoutubeTabIE
        from yt_dlp.utils import ExtractorError
        original_run = subprocess.run

        def run(command, **kwargs):
            # Leave yt-dlp's own runtime probes outside the mocked CLI boundary.
            with patch.object(subprocess, "run", original_run):
                options = parse_options(command[3:]).ydl_opts
                options.update({"extractor_retries": 0, "quiet": True})
                with YoutubeDL(options, auto_init=False) as downloader:
                    extractor = YoutubeTabIE(downloader)
                    with patch.object(extractor, "_call_api", return_value={}):
                        try:
                            extractor._extract_response("channel", {"continuation": "page-2"},
                                                        check_get_keys="continuationContents")
                        except ExtractorError as error:
                            raise subprocess.CalledProcessError(1, command, output='{"entries": [{"id": "aaaaaaaaaaa"}]}',
                                                                stderr=str(error)) from error
            return subprocess.CompletedProcess(command, 0, '{"channel_id": "main-channel", "entries": [{"id": "aaaaaaaaaaa"}]}')

        with patch.object(pipeline.subprocess, "run", side_effect=run):
            with self.assertRaisesRegex(pipeline.PipelineError, "Incomplete data received"):
                pipeline.run_yt_dlp("https://www.youtube.com/@main/videos", flat=True)


if __name__ == "__main__":
    unittest.main()
