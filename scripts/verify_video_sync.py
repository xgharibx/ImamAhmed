"""Verify that the exact checked video catalog and sync status reached the live site."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from video_catalog import PipelineError, ROOT, VIDEOS_JSON, validate_catalog


def wait_for_catalog(base_url: str, catalog: bytes, status: bytes, seconds: int) -> dict:
    records = json.loads(catalog)
    validate_catalog(records)
    summary = json.loads(status)
    digest = hashlib.sha256(catalog).hexdigest()
    if summary.get("status") != "success" or summary.get("catalog_sha256") != digest or summary.get("total") != len(records):
        raise PipelineError("The sync status does not match the validated catalog")
    root = base_url.rstrip("/") + "/"
    deadline = time.monotonic() + seconds
    last_error = "Deployment has not reached the site"
    while True:
        try:
            nonce = str(time.time_ns())
            fetched = []
            for path in ("data/videos.json", "data/video-sync-status.json"):
                url = urllib.parse.urljoin(root, path) + "?verify=" + nonce
                request = urllib.request.Request(url, headers={"Cache-Control": "no-cache", "User-Agent": "VideoSyncCheck/1.0"})
                with urllib.request.urlopen(request, timeout=30) as response:
                    fetched.append(response.read())
            if fetched == [catalog, status]:
                return {"status": "verified-live", "total": len(records), "catalog_sha256": digest,
                        "checked_at": summary["checked_at"], "url": urllib.parse.urljoin(root, "videos.html")}
        except (urllib.error.URLError, TimeoutError, ValueError) as error:
            last_error = str(error)
        if time.monotonic() >= deadline:
            raise PipelineError(f"Live video publication was not confirmed: {last_error}")
        time.sleep(min(10, max(0, deadline - time.monotonic())))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--catalog", type=Path, default=VIDEOS_JSON)
    parser.add_argument("--status", type=Path, default=ROOT / "data" / "video-sync-status.json")
    parser.add_argument("--wait-seconds", type=int, default=0)
    args = parser.parse_args()
    try:
        result = wait_for_catalog(args.base_url, args.catalog.read_bytes(), args.status.read_bytes(), args.wait_seconds)
    except (PipelineError, OSError, ValueError, KeyError) as error:
        print(f"VIDEO SYNC VERIFY ERROR: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
