"""Build the public Android snapshot without changing website resource URLs."""
import argparse
import concurrent.futures
import hashlib
import json
import mimetypes
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote, unquote, urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
SITE = 'https://ahmedelfashny.com/'
MIRRORS = 'assets/app-content/'
MAPPING_FILE = MIRRORS + 'mappings.json'
MAX_FILE = 32 * 1024 * 1024
MAX_TOTAL = 384 * 1024 * 1024
SUFFIXES = {'.html', '.css', '.js', '.json', '.png', '.jpg', '.jpeg', '.webp',
            '.svg', '.gif', '.ico', '.woff', '.woff2', '.ttf', '.eot'}
MIMES = {'.js': 'application/javascript', '.json': 'application/json',
         '.woff': 'font/woff', '.woff2': 'font/woff2', '.ttf': 'font/ttf',
         '.eot': 'application/vnd.ms-fontobject'}
CDN_PREFIXES = ('https://fonts.googleapis.com/css', 'https://fonts.gstatic.com/s/',
                'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/',
                'https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/',
                'https://cdnjs.cloudflare.com/ajax/libs/html2canvas/',
                'https://cdnjs.cloudflare.com/ajax/libs/jspdf/',
                'https://unpkg.com/aos@2.3.1/dist/', 'https://i.ytimg.com/vi/',
                'https://img.youtube.com/vi/')
URL_PATTERN = re.compile(r'url\(\s*[\"\']?([^\"\')]+)[\"\']?\s*\)', re.I)
EXTERNAL_PATTERN = re.compile(r'https://[^\s\"\'<>`]+')


def normalize_key(value):
    parts = urlsplit(value)
    if parts.username or parts.password or parts.port not in (None, 443):
        raise ValueError('Unsafe URL authority')
    owned = not parts.netloc or parts.hostname in ('ahmedelfashny.com', 'www.ahmedelfashny.com')
    decoded = unquote(parts.path)
    if any(c in decoded for c in ('\\', '\x00', '\r', '\n')) or any(p in ('.', '..') for p in decoded.split('/')):
        raise ValueError('Unsafe resource path')
    if owned:
        if parts.scheme not in ('', 'https'):
            raise ValueError('HTTPS required')
        path = decoded or '/'
        if not path.startswith('/'):
            path = '/' + path
        if path == '/':
            path = '/index.html'
        relative = path.lstrip('/')
        public = '/' not in relative or relative.startswith(('books/', 'khutab/', 'data/', 'assets/'))
        if not public or Path(relative).suffix.lower() not in SUFFIXES:
            raise ValueError('Not an approved public resource: ' + path)
        if relative in ('data/app-content-manifest.json', 'data/video-sync-status.json'):
            raise ValueError('Control metadata is not snapshot content')
        return path
    if parts.scheme != 'https' or not any(value.startswith(prefix) for prefix in CDN_PREFIXES):
        raise ValueError('Unapproved external resource: ' + value)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, ''))


class Resources(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.urls = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ('script', 'img', 'source') and attrs.get('src'):
            self.urls.append(attrs['src'])
        if tag == 'link' and any(x in attrs.get('rel', '').split() for x in ('stylesheet', 'icon', 'apple-touch-icon')) and attrs.get('href'):
            self.urls.append(attrs['href'])
        if attrs.get('style'):
            self.urls.extend(URL_PATTERN.findall(attrs['style']))


def public_files(root):
    files = list(root.glob('*.html')) + list(root.glob('*.css')) + list(root.glob('*.js'))
    for directory, suffix in [('books', '*.html'), ('khutab', '*.html'), ('data', '*.json')]:
        files.extend((root / directory).glob(suffix))
    return sorted(p for p in files if p.name not in ('app-content-manifest.json', 'video-sync-status.json'))


def references(path, data, base):
    if path.suffix == '.html':
        parser = Resources()
        parser.feed(data.decode('utf-8', errors='replace'))
        urls = parser.urls
    elif path.suffix == '.css':
        urls = URL_PATTERN.findall(data.decode('utf-8'))
    elif path.suffix == '.js':
        urls = [u for u in EXTERNAL_PATTERN.findall(data.decode('utf-8'))
                if any(u.startswith(p) for p in CDN_PREFIXES) and '${' not in u]
    else:
        urls = []
    return [urljoin(base, u) for u in urls if not u.startswith(('data:', '#', 'blob:'))]


def content_bytes(path):
    data = path.read_bytes()
    if path.suffix in ('.html', '.css', '.js', '.json', '.svg'):
        data = data.replace(b'\r\n', b'\n')
    if not data or len(data) > MAX_FILE:
        raise ValueError('Empty or oversized resource: ' + str(path))
    return data


def mappings(root):
    path = root / MAPPING_FILE
    return json.loads(path.read_text('utf-8')) if path.exists() else {}


def resource_map(root):
    mapped = mappings(root)
    queue = [(normalize_key('/' + p.relative_to(root).as_posix()), p.relative_to(root).as_posix()) for p in public_files(root)]
    # Catalog images are generated dynamically, not present as HTML img tags.
    catalog = root / 'data/videos.json'
    if catalog.exists():
        for video in json.loads(catalog.read_text('utf-8')):
            if isinstance(video, dict) and re.fullmatch(r'[A-Za-z0-9_-]{11}', video.get('id', '')):
                for url in (video.get('thumbnail'), f'https://i.ytimg.com/vi/{video["id"]}/hqdefault.jpg'):
                    if url and url in mapped:
                        queue.append((normalize_key(url), mapped[url]))
    result = {}
    while queue:
        key, relative = queue.pop()
        if key in result:
            continue
        target = root / relative
        if not target.resolve().is_relative_to(root.resolve()) or not target.is_file():
            raise ValueError('Missing required resource: ' + relative)
        if key.startswith('https://') and not relative.startswith(MIRRORS):
            raise ValueError('External mirrors must be public generated assets')
        data = content_bytes(target)
        result[key] = (relative, data)
        base = key if key.startswith('https://') else urljoin(SITE, quote(key.lstrip('/')))
        for url in references(target, data, base):
            child = normalize_key(url)
            relative_child = child.lstrip('/') if child.startswith('/') else mapped.get(child)
            if relative_child is None:
                raise ValueError('Missing required CDN mirror: ' + child)
            queue.append((child, relative_child))
    if len(result) > 10000 or sum(len(d) for _, d in result.values()) > MAX_TOTAL:
        raise ValueError('Snapshot exceeds resource/storage bounds')
    return result


def build_manifest(root):
    entries = []
    for key, (path, data) in sorted(resource_map(root).items()):
        suffix = Path(path).suffix
        mime = MIMES.get(suffix) or mimetypes.guess_type(path)[0]
        if not mime:
            raise ValueError('Unknown resource MIME: ' + path)
        entries.append(dict(key=key, path=path, sha256=hashlib.sha256(data).hexdigest(), size=len(data), mime=mime))
    canonical = ''.join('\x00'.join(str(e[k]) for k in ('key', 'path', 'sha256', 'size', 'mime')) + '\n' for e in entries)
    return dict(schema=1, revision=hashlib.sha256(canonical.encode('utf-8')).hexdigest(), resources=entries)


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')


def prepare_seed(root, output):
    manifest = build_manifest(root)
    objects = output / 'objects'
    objects.mkdir(parents=True, exist_ok=True)
    for entry in manifest['resources']:
        destination = objects / entry['sha256']
        data = content_bytes(root / entry['path'])
        if hashlib.sha256(data).hexdigest() != entry['sha256']:
            raise ValueError('Resource changed during seed generation')
        destination.write_bytes(data)
    write_json(output / 'manifest.json', manifest)
    keep = {e['sha256'] for e in manifest['resources']}
    for path in objects.iterdir():
        if path.name not in keep and path.is_file():
            path.unlink()
    return manifest


def fetch_mirror(root, url):
    normalize_key(url)
    # This user agent requests WOFF2 and Arabic unicode ranges used by WebView.
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36'})
    with urlopen(req, timeout=30) as response:
        normalize_key(response.url)
        data = response.read(MAX_FILE + 1)
        mime = response.headers.get_content_type()
    if not data or len(data) > MAX_FILE:
        raise ValueError('Empty/oversized CDN response')
    suffix = { 'text/css': '.css', 'application/javascript': '.js', 'text/javascript': '.js',
               'image/jpeg': '.jpg', 'image/png': '.png', 'font/woff2': '.woff2',
               'application/font-woff': '.woff', 'font/ttf': '.ttf' }.get(mime)
    if not suffix:
        suffix = Path(urlsplit(url).path).suffix
    if suffix not in SUFFIXES or mime == 'text/html':
        raise ValueError('Invalid CDN resource type: ' + url)
    relative = MIRRORS + hashlib.sha256(url.encode()).hexdigest() + suffix
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return url, relative, references(target, data, url)


def prepare_assets(root):
    mapped = mappings(root)
    pending = set()
    for path in public_files(root):
        for url in references(path, content_bytes(path), urljoin(SITE, path.relative_to(root).as_posix())):
            if urlsplit(url).hostname not in ('ahmedelfashny.com', 'www.ahmedelfashny.com'):
                pending.add(normalize_key(url))
    # Revisit mirrored CSS dependencies to repair partial previous preparation.
    for url, relative in mapped.items():
        if (root / relative).is_file():
            pending.update(references(root / relative, content_bytes(root / relative), url))
    catalog = root / 'data/videos.json'
    if catalog.exists():
        for item in json.loads(catalog.read_text('utf-8')):
            if isinstance(item, dict) and re.fullmatch(r'[A-Za-z0-9_-]{11}', item.get('id', '')):
                pending.add(f'https://i.ytimg.com/vi/{item["id"]}/hqdefault.jpg')
                if item.get('thumbnail'):
                    pending.add(normalize_key(item['thumbnail']))
    unavailable = []
    while pending:
        urls = sorted(u for u in pending if u not in mapped or not (root / mapped[u]).is_file())
        pending = set()
        if not urls:
            break
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
            futures = {pool.submit(fetch_mirror, root, u): u for u in urls}
            for future in concurrent.futures.as_completed(futures):
                url = futures[future]
                try:
                    key, relative, children = future.result()
                    mapped[key] = relative
                    pending.update(normalize_key(c) for c in children)
                except Exception as error:
                    if url.startswith(('https://i.ytimg.com/vi/', 'https://img.youtube.com/vi/')):
                        unavailable.append(url)
                    else:
                        write_json(root / MAPPING_FILE, dict(sorted(mapped.items())))
                        raise ValueError(f'Required CDN dependency failed: {url}: {error}') from error
        write_json(root / MAPPING_FILE, dict(sorted(mapped.items())))
    return dict(mirrors=len(mapped), unavailableThumbnails=unavailable)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--prepare-assets', action='store_true')
    parser.add_argument('--seed', type=Path)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.prepare_assets:
        print(json.dumps(prepare_assets(args.root)))
    manifest = prepare_seed(args.root, args.seed) if args.seed else build_manifest(args.root)
    published = args.root / 'data/app-content-manifest.json'
    if args.check:
        if not published.exists() or json.loads(published.read_text('utf-8')) != manifest:
            raise ValueError('Published app manifest does not match public content')
    else:
        write_json(published, manifest)
    print(json.dumps(dict(revision=manifest['revision'], resources=len(manifest['resources']),
                          bytes=sum(e['size'] for e in manifest['resources']))))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
