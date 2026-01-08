#!/usr/bin/env python3
# Simple Quran scraper from surahquran.com -> data/quran.json
import json, time, ssl
from urllib.request import urlopen
from bs4 import BeautifulSoup
from pathlib import Path

ssl._create_default_https_context = ssl._create_unverified_context

BASE = 'https://surahquran.com'
OUT = Path('m:/Sheikh Ahmed/data/quran.json')

SURAH_COUNT = 114

def fetch(url):
    with urlopen(url, timeout=20) as resp:
        return resp.read()

def parse_surah(n):
    html = fetch(f'{BASE}/{n}.html')
    soup = BeautifulSoup(html, 'html.parser')
    title = soup.find('title').get_text(strip=True) if soup.find('title') else f'Surah {n}'
    # Try to find aya containers
    ayahs = []
    # Common spans/divs possibly containing ayat
    for el in soup.select('.ayah, .aya, .ayas, span, p, div'):
        t = el.get_text(' ', strip=True)
        if not t: continue
        # Heuristic: arabic letters present and not boilerplate
        if any('\u0600' <= ch <= '\u06FF' for ch in t) and len(t.split()) >= 2:
            # Skip menus and headers
            if 'سورة' in t and len(t.split()) < 6:
                continue
            if 'تفسير' in t or 'بحث' in t or 'إعلانات' in t:
                continue
            ayahs.append(t)
        if len(ayahs) >= 300:
            break
    # Remove obvious duplicates and keep order
    seen = set()
    clean = []
    for a in ayahs:
        if a in seen: continue
        seen.add(a)
        clean.append(a)
    return {
        'id': n,
        'name': title,
        'ayahs': clean
    }

def main():
    data = {'surahs': []}
    for n in range(1, SURAH_COUNT+1):
        try:
            print('Parsing surah', n)
            s = parse_surah(n)
            data['surahs'].append(s)
            time.sleep(0.5)
        except Exception as e:
            print('Failed surah', n, e)
            data['surahs'].append({'id': n, 'name': f'Surah {n}', 'ayahs': []})
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Saved', OUT)

if __name__ == '__main__':
    main()
