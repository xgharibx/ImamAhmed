import unittest

from yt_dlp import YoutubeDL
from yt_dlp_plugins.extractor.channel_live_status import YoutubeTabLiveStatusIE


class ChannelLiveStatusTests(unittest.TestCase):
    def setUp(self):
        downloader = YoutubeDL({"quiet": True, "no_warnings": True}, auto_init=False)
        self.addCleanup(downloader.close)
        self.extractor = YoutubeTabLiveStatusIE(downloader)

    def test_lockup_live_badge_is_preserved(self):
        model = {"contentId": "abcdefghijk", "contentType": "LOCKUP_CONTENT_TYPE_VIDEO",
                 "contentImage": {"thumbnailViewModel": {"overlays": [{
                     "thumbnailBottomOverlayViewModel": {"badges": [{"thumbnailBadgeViewModel": {
                         "badgeStyle": "THUMBNAIL_OVERLAY_BADGE_STYLE_LIVE", "text": "LIVE"}}]}}]}}}
        record = self.extractor._extract_lockup_view_model(model)
        self.assertEqual(record["live_status"], "is_live")

    def test_completed_lockup_keeps_normal_duration(self):
        model = {"contentId": "abcdefghijk", "contentType": "LOCKUP_CONTENT_TYPE_VIDEO",
                 "contentImage": {"thumbnailViewModel": {"overlays": [{
                     "thumbnailBottomOverlayViewModel": {"badges": [{"thumbnailBadgeViewModel": {
                         "badgeStyle": "THUMBNAIL_OVERLAY_BADGE_STYLE_DEFAULT", "text": "12:34"}}]}}]}}}
        record = self.extractor._extract_lockup_view_model(model)
        self.assertEqual(record["duration"], 754)
        self.assertNotEqual(record.get("live_status"), "is_live")
