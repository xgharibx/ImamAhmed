#!/usr/bin/env python3
"""
Quran scraper from api.alquran.cloud - pulls only surahs and ayat with diacritics (tashkeel)
"""
import json, urllib.request, ssl
from pathlib import Path

ssl._create_default_https_context = ssl._create_unverified_context

API_URL = 'https://api.alquran.cloud/v1/surah/{}/ar.alafasy'
OUT = Path('m:/Sheikh Ahmed/data/quran.json')

def fetch_surah(num):
    """Fetch a single surah with ayat"""
    url = API_URL.format(num)
    with urllib.request.urlopen(url, timeout=20) as resp:
        data = json.loads(resp.read())
    return data

def main():
    """Fetch all 114 surahs and save to JSON"""
    surahs = []
    
    for i in range(1, 115):
        try:
            print(f"Fetching surah {i}...")
            result = fetch_surah(i)
            
            if result.get('code') == 200 and result.get('status') == 'OK':
                data = result.get('data', {})
                surah = {
                    'id': data.get('number', i),
                    'name': data.get('name', f'سورة {i}'),
                    'englishName': data.get('englishName', ''),
                    'ayahs': [a.get('text', '') for a in data.get('ayahs', [])]
                }
                surahs.append(surah)
        except Exception as e:
            print(f"Error fetching surah {i}: {e}")
    
    # Save to JSON
    output = {'surahs': surahs}
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"\nSaved {len(surahs)} surahs to {OUT}")

if __name__ == '__main__':
    main()
