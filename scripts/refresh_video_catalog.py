"""Audit both official channels and backfill exact YouTube metadata without downloading media."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import time
import urllib.error
import urllib.request

import video_catalog as pipeline


def fetch_metadata(video_id, context):
    request = urllib.request.Request(
        "https://www.youtube.com/youtubei/v1/player?prettyPrint=false",
        data=json.dumps({"context": context, "videoId": video_id}).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=25) as response:
                payload = json.load(response)
            details = payload.get("videoDetails") or {}
            micro = (payload.get("microformat") or {}).get("playerMicroformatRenderer") or {}
            if details.get("videoId") != video_id or not details.get("title"):
                status = payload.get("playabilityStatus") or {}
                return {"unavailable": status.get("reason", "Public metadata unavailable"), "id": video_id}
            live = micro.get("liveBroadcastDetails") or {}
            if details.get("isLive") or details.get("isUpcoming") or live.get("isLiveNow"):
                return {"id": video_id, "live_status": "is_live"}
            published = str(micro.get("publishDate") or micro.get("uploadDate") or "")
            if not published:
                return {"unavailable": "YouTube did not expose a publication date", "id": video_id}
            date = dt.date.fromisoformat(published[:10]).isoformat()
            return {
                "id": video_id, "title": details["title"], "upload_date": date,
                "duration": int(details.get("lengthSeconds") or 0),
                "channel_id": details.get("channelId", ""),
                "publishedAt": published,
                "live_status": "not_live",
            }
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            if attempt == 2:
                raise
            time.sleep(2 ** (attempt + 1))


def refresh(args):
    from yt_dlp.extractor.youtube._base import INNERTUBE_CLIENTS

    cache = Path(args.cache)
    cache.mkdir(parents=True, exist_ok=True)
    original_bytes = pipeline.VIDEOS_JSON.read_bytes()
    original = json.loads(original_bytes)
    pipeline.validate_catalog(original)
    new_only = getattr(args, "new_only", False)
    sources = pipeline.read_json(pipeline.CHANNELS_CONFIG)
    overrides = pipeline.read_json(pipeline.ROOT / "content-pipeline" / "video-category-overrides.json")
    for entry in overrides.values():
        if entry.get("category") not in pipeline.VALID_VIDEO_CATEGORIES or not entry.get("reason"):
            raise pipeline.PipelineError("Invalid reviewed category override")
    listed = {}
    channel_ids = {}
    feeds_report = []
    for source in sources:
        for feed in source.get("feeds", ["videos"]):
            feed_cache = cache / f"feed-{source['sourceChannel']}-{feed}-{args.limit}.json"
            print(f"Reading {source['channelHandle']}/{feed}", flush=True)
            try:
                payload = pipeline.read_json(feed_cache) if feed_cache.exists() and not args.refresh_feeds else pipeline.run_yt_dlp(
                    source["url"].rstrip("/") + "/" + feed, flat=True, playlist_end=args.limit)
            except pipeline.PipelineError as error:
                if "does not have a" in str(error) and "tab" in str(error):
                    feeds_report.append({"channel": source["sourceChannel"], "feed": feed, "absent": True})
                    continue
                raise
            if not isinstance(payload, dict) or not payload.get("channel_id") or not payload.get("entries"):
                raise pipeline.PipelineError(f"Incomplete channel listing: {source['channelHandle']}/{feed}")
            channel_id = payload["channel_id"]
            if source.get("channelId") and source["channelId"] != channel_id:
                raise pipeline.PipelineError("The channel listing does not match the configured channel")
            source = {**source, "channelId": channel_id}
            channel_ids[channel_id] = source
            pipeline.write_json(feed_cache, payload)
            count = 0
            for item in payload.get("entries") or []:
                if not item or not re.fullmatch(r"[A-Za-z0-9_-]{11}", str(item.get("id", ""))):
                    continue
                count += 1
                if item["id"] not in listed or feed == "shorts":
                    listed[item["id"]] = (source, feed, item)
            if not count:
                raise pipeline.PipelineError(f"No valid video entries: {source['channelHandle']}/{feed}")
            feeds_report.append({"channel": source["sourceChannel"], "feed": feed, "count": count})

    records = {item["id"]: item for item in original}
    ids = sorted(set(listed) - set(records) if new_only else set(records) | set(listed))
    context = INNERTUBE_CLIENTS["web"]["INNERTUBE_CONTEXT"]

    def resolve(video_id):
        if video_id in listed and listed[video_id][2].get("live_status") in {"is_live", "is_upcoming", "post_live"}:
            return {"id": video_id, "live_status": "is_live"}
        path = cache / f"{video_id}.json"
        if path.exists():
            cached = pipeline.read_json(path)
            if not cached.get("unavailable") and cached.get("live_status") != "is_live":
                return cached
        result = fetch_metadata(video_id, context)
        pipeline.write_json(path, result)
        return result

    report = {"feeds": feeds_report, "added": [], "dates_corrected": [], "categories_corrected": [], "unavailable": [], "live_skipped": [], "errors": []}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(resolve, video_id): video_id for video_id in ids}
        for done, future in enumerate(as_completed(futures), 1):
            video_id = futures[future]
            try:
                metadata = future.result()
            except Exception as error:
                report["errors"].append({"id": video_id, "error": str(error)})
                continue
            if metadata.get("unavailable"):
                report["unavailable"].append(metadata)
                if video_id not in records:
                    report["errors"].append({"id": video_id, "error": metadata["unavailable"]})
                continue
            if metadata.get("live_status") == "is_live":
                report["live_skipped"].append(video_id)
                continue
            old = records.get(video_id)
            source, feed, item = listed.get(video_id, (channel_ids.get(metadata.get("channel_id"), {}), "", {}))
            if not source and old:
                source = {key: old.get(key, "") for key in ("sourceChannel", "channelHandle", "channelName")}
            try:
                if source.get("channelId") and metadata.get("channel_id") != source["channelId"]:
                    raise pipeline.PipelineError("Video belongs to a different channel")
                record = pipeline.video_record({**item, **metadata}, source=source, feed=feed)
                if not record["date"] or int(metadata.get("duration") or 0) <= 0:
                    raise pipeline.PipelineError("Missing publication date or duration")
                dt.date.fromisoformat(record["date"])
                pipeline.video_timestamp({**record, "publishedAt": metadata["publishedAt"]})
            except (pipeline.PipelineError, ValueError, KeyError, TypeError) as error:
                report["errors"].append({"id": video_id, "error": str(error)})
                continue
            if video_id in overrides:
                record["category"] = overrides[video_id]["category"]
            record["publishedAt"] = metadata["publishedAt"]
            record["categoryVerified"] = True
            if old:
                record = {**old, **record}
                if old.get("date") != record["date"]:
                    report["dates_corrected"].append(video_id)
                if old.get("category") != record["category"]:
                    report["categories_corrected"].append({"id": video_id, "title": record["title"], "from": old.get("category"), "to": record["category"]})
            else:
                report["added"].append(video_id)
            records[video_id] = record
            if done % 100 == 0 or done == len(ids):
                print(f"Verified {done}/{len(ids)} videos", flush=True)

    for video_id, override in overrides.items():
        record = records.get(video_id)
        if record and record["category"] != override["category"]:
            report["categories_corrected"].append({"id": video_id, "title": record["title"],
                                                   "from": record["category"], "to": override["category"]})
            records[video_id] = {**record, "category": override["category"], "categoryVerified": True}
    result = sorted(records.values(), key=lambda item: (pipeline.video_timestamp(item), item["id"]), reverse=True)
    report["total"] = len(result)
    report["missing_dates"] = [item["id"] for item in result if not item.get("date")]
    report["source_sha256"] = hashlib.sha256(original_bytes).hexdigest()
    pipeline.write_json(cache / "report.json", report)
    if report["errors"]:
        raise pipeline.PipelineError(f"{len(report['errors'])} metadata errors; catalog unchanged. See {cache / 'report.json'}.")
    pipeline.validate_catalog(result)
    if args.apply:
        if pipeline.VIDEOS_JSON.read_bytes() != original_bytes:
            raise pipeline.PipelineError("The catalog changed during the audit; refusing to overwrite another edit.")
        if result != original:
            pipeline.write_json(pipeline.VIDEOS_JSON, result)
        if getattr(args, "report", None):
            status = {**report, "status": "success", "checked_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                      "mode": "new-only" if new_only else "audit",
                      "catalog_sha256": hashlib.sha256(pipeline.VIDEOS_JSON.read_bytes()).hexdigest()}
            pipeline.write_json(Path(args.report), status)
    return {key: len(value) if isinstance(value, list) else value for key, value in report.items() if key != "source_sha256"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=0, help="Items per channel tab; zero scans all public entries")
    parser.add_argument("--workers", type=int, choices=range(1, 5), default=4)
    parser.add_argument("--cache", default=str(pipeline.ROOT / "tmp" / ("youtube-audit-" + dt.date.today().isoformat())))
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--refresh-feeds", action="store_true", help="Refresh channel listings while reusing verified metadata")
    parser.add_argument("--new-only", action="store_true", help="Import missing videos without changing reviewed catalog entries")
    parser.add_argument("--report", help="Publish a successful sync status alongside the catalog when applying")
    print(json.dumps(refresh(parser.parse_args()), ensure_ascii=False, indent=2))
