#!/usr/bin/env python3
"""
Advanced Sunnah.com Hadith Scraper with Selenium
Extracts all hadiths from major collections with JavaScript rendering
"""

import json
import time
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
import os
from pathlib import Path

# Headers to mimic browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

# Hadith collections
COLLECTIONS = {
    'bukhari': 'https://sunnah.com/bukhari',
    'muslim': 'https://sunnah.com/muslim',
    'nasai': 'https://sunnah.com/nasai',
    'abudawud': 'https://sunnah.com/abudawud',
    'tirmidhi': 'https://sunnah.com/tirmidhi',
    'ibnmajah': 'https://sunnah.com/ibnmajah',
    'malik': 'https://sunnah.com/malik',
    'ahmad': 'https://sunnah.com/ahmad',
    'darimi': 'https://sunnah.com/darimi',
    'adab': 'https://sunnah.com/adab',
    'shamail': 'https://sunnah.com/shamail',
    'mishkat': 'https://sunnah.com/mishkat',
    'bulugh': 'https://sunnah.com/bulugh',
    'hisn': 'https://sunnah.com/hisn',
    'riyadussaliheen': 'https://sunnah.com/riyadussaliheen'
}

class AdvancedSunnahScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.data = {}
    
    def get_page(self, url, retries=3):
        """Fetch a page with retry logic"""
        for attempt in range(retries):
            try:
                response = self.session.get(url, timeout=15)
                response.raise_for_status()
                return response.text
            except requests.RequestException as e:
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
        return None
    
    def get_collection_data(self, collection_code, base_url):
        """Scrape all data from a collection using REST endpoints"""
        print(f"Fetching {collection_code} data...")
        
        chapters = []
        hadiths_count = 0
        
        # Try to fetch from common API endpoints
        api_urls = [
            f'{base_url}/index.json',
            f'https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/editions/ara-{collection_code}.json',
            f'https://api.sunnah.com/{collection_code}/chapters',
        ]
        
        for api_url in api_urls:
            try:
                response = self.session.get(api_url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    print(f"✓ Got data from {api_url}")
                    return data
            except:
                continue
        
        # Fallback: HTML scraping with improved selectors
        html = self.get_page(base_url)
        if not html:
            print(f"✗ Failed to fetch {base_url}")
            return {}
        
        soup = BeautifulSoup(html, 'html.parser')
        data = {
            'code': collection_code,
            'chapters': []
        }
        
        # Find all chapter links
        chapter_links = soup.find_all('a')
        seen_chapters = set()
        
        for link in chapter_links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            
            if f'/{collection_code}/' in href and href not in seen_chapters:
                seen_chapters.add(href)
                chapter_id = href.split('/')[-1]
                if chapter_id.isdigit() or chapter_id in ['introduction', 'letter', 'about']:
                    # Keep Arabic-only title to avoid English spillover
                    def only_arabic(t):
                        # keep Arabic chars, spaces and Arabic digits
                        return ''.join(ch for ch in t if ('\u0600' <= ch <= '\u06FF') or ch.isspace()) or t
                    ar_title = only_arabic(text)
                    data['chapters'].append({
                        'id': chapter_id,
                        'name': ar_title.strip() or f'الفصل {chapter_id}',
                        'url': href if href.startswith('http') else urljoin(base_url, href)
                    })
        
        return data
    
    def get_chapter_hadiths(self, chapter_url, collection_code):
        """Get hadiths from a specific chapter"""
        html = self.get_page(chapter_url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        hadiths = []
        
        # Precise extraction: each hadith is within .actualHadithContainer
        containers = soup.select('.actualHadithContainer')
        for i, cont in enumerate(containers):
            ar = cont.select_one('.arabic_hadith_full') or cont.select_one('.arabic_text_details') or cont.select_one('.arabic')
            if not ar:
                continue
            text = ar.get_text(' ', strip=True)
            if not text:
                continue
            # Ensure mostly Arabic and remove excessive whitespace
            arab_chars = sum(1 for ch in text if '\u0600' <= ch <= '\u06FF')
            if arab_chars < 10:
                continue
            clean = re.sub(r'\s+', ' ', text).strip()
            hadiths.append({
                'text': clean[:2000],
                'source': collection_code,
                'chapter_url': chapter_url
            })
        
        # Reasonable cap to keep JSON small but useful
        return hadiths[:200]
    
    def scrape_all(self):
        """Scrape all collections"""
        for code, url in COLLECTIONS.items():
            print(f"\n{'='*60}")
            print(f"Processing {code}")
            print(f"{'='*60}")
            
            try:
                collection_data = self.get_collection_data(code, url)
                
                self.data[code] = {
                    'name': code,
                    'chapters': [],
                    'total_hadiths': 0
                }
                
                if 'chapters' in collection_data:
                    chapters = collection_data['chapters'][:50]  # Limit to 50 chapters
                    
                    for i, chapter in enumerate(chapters):
                        print(f"Chapter {i+1}/{len(chapters)}")
                        
                        chapter_url = chapter.get('url') or f"{url}/{chapter.get('id', '')}"
                        hadiths = self.get_chapter_hadiths(chapter_url, code)
                        
                        if hadiths:
                            self.data[code]['chapters'].append({
                                'name': chapter.get('name', f"Chapter {chapter.get('id')}"),
                                'id': chapter.get('id', ''),
                                'hadiths': hadiths,
                                'count': len(hadiths)
                            })
                            
                            self.data[code]['total_hadiths'] += len(hadiths)
                        
                        time.sleep(0.5)  # Be respectful
                
                # Save intermediate results
                self.save_data(code)
                
            except Exception as e:
                print(f"✗ Error processing {code}: {e}")
                continue
    
    def save_data(self, collection_code=None):
        """Save scraped data to JSON files"""
        output_dir = Path('m:\\Sheikh Ahmed\\data')
        output_dir.mkdir(exist_ok=True)
        
        if collection_code and collection_code in self.data:
            filename = output_dir / f'{collection_code}.json'
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.data[collection_code], f, ensure_ascii=False, indent=2)
            print(f"✓ Saved: {filename}")
        
        # Save all together
        if self.data:
            filename = output_dir / 'all_hadiths.json'
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            print(f"✓ Saved: {filename}")
    
    def print_summary(self):
        """Print scraping summary"""
        print(f"\n{'='*60}")
        print("SCRAPING SUMMARY")
        print(f"{'='*60}")
        
        total_hadiths = 0
        for code, data in self.data.items():
            count = data.get('total_hadiths', 0)
            chapters = len(data.get('chapters', []))
            total_hadiths += count
            print(f"{code}: {chapters} chapters, {count} hadiths")
        
        print(f"\nTotal hadiths scraped: {total_hadiths}")

if __name__ == '__main__':
    print("Starting advanced Sunnah.com scraper...")
    scraper = AdvancedSunnahScraper()
    
    try:
        scraper.scrape_all()
        scraper.save_data()
        scraper.print_summary()
        print("\n✓ Scraping completed!")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
