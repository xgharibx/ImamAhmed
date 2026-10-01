"""Retain the public LIVE badge omitted by yt-dlp's channel lockup adapter."""
from yt_dlp.extractor.youtube import YoutubeTabIE
from yt_dlp.utils.traversal import traverse_obj


class YoutubeTabLiveStatusIE(YoutubeTabIE, plugin_name="channel_live_status"):
    def _extract_lockup_view_model(self, view_model):
        record = super()._extract_lockup_view_model(view_model)
        styles = traverse_obj(view_model, (
            "contentImage", "thumbnailViewModel", "overlays", ...,
            (("thumbnailBottomOverlayViewModel", "badges"), ("thumbnailOverlayBadgeViewModel", "thumbnailBadges")),
            ..., "thumbnailBadgeViewModel", "badgeStyle", {str}))
        if record and "THUMBNAIL_OVERLAY_BADGE_STYLE_LIVE" in styles:
            record["live_status"] = "is_live"
        return record
