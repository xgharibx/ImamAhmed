"""Check the optimized signed APK on a disposable emulator without WebView debugging."""
import argparse
import json
from pathlib import Path
import subprocess
import time
from xml.etree import ElementTree as ET

PACKAGE = 'com.ahmedelfashny.official'
ROOT = Path(__file__).resolve().parents[2]


def run(adb_path, output):
    def adb(*args):
        return subprocess.check_output([str(adb_path), '-s', 'emulator-5554', *args])

    def airplane(enabled):
        adb('shell', 'cmd', 'connectivity', 'airplane-mode', 'enable' if enabled else 'disable')
        adb('shell', 'svc', 'wifi', 'disable' if enabled else 'enable')
        adb('shell', 'svc', 'data', 'disable' if enabled else 'enable')

    output.mkdir(parents=True, exist_ok=True)
    destinations = ['index.html', 'articles.html', 'khutab-written.html', 'videos.html',
                    'books/mathabat-alarwah-rihlat-alishq-ila-rihab-alnur-almuhammadi.html']
    report = {'mode': 'signed-release-first-launch-airplane', 'pages': []}
    adb('shell', 'am', 'force-stop', PACKAGE)
    assert adb('shell', 'pm', 'clear', PACKAGE).strip() == b'Success'
    airplane(True)
    try:
        for index, destination in enumerate(destinations):
            adb('shell', 'am', 'start', '-a', 'android.intent.action.VIEW', '-d',
                'https://ahmedelfashny.com/' + destination, '-n',
                PACKAGE + '/com.ahmedelfashny.official.MainActivity')
            for _ in range(10):
                adb('shell', 'uiautomator', 'dump', '/sdcard/release-qa.xml')
                raw = adb('shell', 'cat', '/sdcard/release-qa.xml')
                nodes = list(ET.fromstring(raw).iter('node'))
                content = ' '.join(node.get('text', '') + ' ' + node.get('content-desc', '') for node in nodes)
                if len(content) > 180 and any(node.get('class') == 'android.webkit.WebView' for node in nodes):
                    break
                time.sleep(.5)
            else:
                raise AssertionError('No visible offline reading content: ' + destination)
            assert not any(node.get('class') == 'android.widget.ProgressBar' for node in nodes)
            assert 'net::ERR_' not in content
            assert 'Web page not available' not in content
            pid = adb('shell', 'pidof', PACKAGE).decode().strip()
            assert 'webview_devtools_remote_' + pid not in adb('shell', 'cat', '/proc/net/unix').decode()
            (output / f'{index:02d}-release.png').write_bytes(adb('exec-out', 'screencap', '-p'))
            (output / f'{index:02d}-release.xml').write_bytes(raw)
            report['pages'].append({'path': destination, 'visibleCharacters': len(content)})
        report['status'] = 'passed'
        (output / 'release-offline-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(report, ensure_ascii=False))
    finally:
        airplane(False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('adb', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.adb, args.output)
