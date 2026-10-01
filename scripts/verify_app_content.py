"""Verify the deployed offline manifest and the bytes it promises to clients."""
import argparse
import concurrent.futures
import hashlib
import json
import sys
import time
from urllib.parse import quote, urljoin
from urllib.request import Request, urlopen

from generate_app_content import ROOT, MAX_FILE, build_manifest


def verify_live(base_url, manifest, wait_seconds=0, all_resources=False):
    def read(path, maximum):
        url = urljoin(base_url.rstrip('/') + '/', quote(path, safe='/')) + '?verify=' + str(time.time_ns())
        request = Request(url, headers={'Cache-Control': 'no-cache', 'User-Agent': 'AppContentCheck/1.0'})
        with urlopen(request, timeout=30) as response:
            data = response.read(maximum + 1)
        if len(data) > maximum:
            raise ValueError('Oversized resource: ' + path)
        return data

    def check_resource(entry):
        data = read(entry['path'], MAX_FILE)
        if len(data) != entry['size'] or hashlib.sha256(data).hexdigest() != entry['sha256']:
            raise ValueError('Resource checksum mismatch: ' + entry['path'])

    deadline = time.monotonic() + wait_seconds
    while True:
        try:
            if json.loads(read('data/app-content-manifest.json', 5 * 1024 * 1024)) != manifest:
                raise ValueError('Live manifest is not the expected complete revision')
            entries = {e['path']: e for e in manifest['resources'] if all_resources or not e['key'].startswith(('https://i.ytimg.com/', 'https://img.youtube.com/'))}
            with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
                list(pool.map(check_resource, entries.values()))
            return dict(status='verified-live', revision=manifest['revision'], resources=len(manifest['resources']), checkedResources=len(entries))
        except (ValueError, OSError) as error:
            if time.monotonic() >= deadline:
                raise ValueError('Live app content not confirmed: ' + str(error)) from error
            time.sleep(min(10, max(0, deadline - time.monotonic())))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', required=True)
    parser.add_argument('--wait-seconds', type=int, default=0)
    parser.add_argument('--all-resources', action='store_true')
    args = parser.parse_args()
    try:
        print(json.dumps(verify_live(args.base_url, build_manifest(ROOT), args.wait_seconds, args.all_resources)))
    except (ValueError, OSError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
