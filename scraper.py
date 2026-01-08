#!/usr/bin/env python3
"""
Comprehensive Sunnah.com Hadith Scraper
Extracts all hadiths from major collections and saves to JSON
"""

import json
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import os
from pathlib import Path

# Headers to mimic browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

# Hadith collections to scrape
COLLECTIONS = {
    'bukhari': {
        'name': 'صحيح البخاري',
        'url': 'https://sunnah.com/bukhari',
        'code': 'bukhari'
    },
    'muslim': {
        'name': 'صحيح مسلم',
        'url': 'https://sunnah.com/muslim',
        'code': 'muslim'
    },
    'nasai': {
        'name': 'سنن النسائي',
        'url': 'https://sunnah.com/nasai',
        'code': 'nasai'
    },
    'abudawud': {
        'name': 'سنن أبي داود',
        'url': 'https://sunnah.com/abudawud',
        'code': 'abudawud'
    },
    'tirmidhi': {
        'name': 'جامع الترمذي',
        'url': 'https://sunnah.com/tirmidhi',
        'code': 'tirmidhi'
    },
    'ibnmajah': {
        'name': 'سنن ابن ماجه',
        'url': 'https://sunnah.com/ibnmajah',
        'code': 'ibnmajah'
    },
    'malik': {
        'name': 'موطأ مالك',
        'url': 'https://sunnah.com/malik',
        'code': 'malik'
    },
    'ahmad': {
        'name': 'مسند أحمد',
        'url': 'https://sunnah.com/ahmad',
        'code': 'ahmad'
    }
}

class SunnahScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.data = {}
    
    def get_page(self, url, retries=3):
        """Fetch a page with retry logic"""
        for attempt in range(retries):
            try:
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                return response.text
            except requests.RequestException as e:
                print(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    return None
    
    def get_collection_chapters(self, collection_code):
        """Get all chapters/books for a collection"""
        url = f'https://sunnah.com/{collection_code}'
        print(f"Fetching chapters for {collection_code}...")
        
        html = self.get_page(url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        chapters = []
        
        # Find book/chapter links
        book_links = soup.find_all('a', href=True)
        
        for link in book_links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            
            # Check if it's a chapter/book link
            if f'/{collection_code}/' in href and text and len(text) > 2:
                chapters.append({
                    'url': href if href.startswith('http') else urljoin('https://sunnah.com', href),
                    'name': text,
                    'id': href.split('/')[-1] if '/' in href else ''
                })
        
        return chapters[:100]  # Limit to 100 chapters per collection
    
    def get_hadiths_from_chapter(self, url):
        """Extract all hadiths from a chapter page"""
        print(f"Scraping hadiths from {url}...")
        
        html = self.get_page(url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        hadiths = []
        
        # Find hadith containers
        hadith_divs = soup.find_all('div', {'class': 'hadith'})
        
        for hadith_div in hadith_divs:
            try:
                # Extract hadith text
                hadith_text_elem = hadith_div.find('div', {'class': 'text'})
                hadith_text = hadith_text_elem.get_text(strip=True) if hadith_text_elem else ''
                
                # Extract hadith number
                number_elem = hadith_div.find('span', {'class': 'hadith_number'})
                hadith_number = number_elem.get_text(strip=True) if number_elem else ''
                
                # Extract narrator
                narrator_elem = hadith_div.find('div', {'class': 'narrator'})
                narrator = narrator_elem.get_text(strip=True) if narrator_elem else ''
                
                # Extract grade/status
                grade_elem = hadith_div.find('div', {'class': 'grade'})
                grade = grade_elem.get_text(strip=True) if grade_elem else ''
                
                if hadith_text:
                    hadiths.append({
                        'number': hadith_number,
                        'text': hadith_text,
                        'narrator': narrator,
                        'grade': grade,
                        'url': url
                    })
            except Exception as e:
                print(f"Error parsing hadith: {e}")
                continue
        
        return hadiths
    
    def scrape_all(self):
        """Scrape all collections"""
        for code, collection_info in COLLECTIONS.items():
            print(f"\n{'='*60}")
            print(f"Scraping {collection_info['name']} ({code})")
            print(f"{'='*60}")
            
            self.data[code] = {
                'name': collection_info['name'],
                'chapters': [],
                'total_hadiths': 0
            }
            
            # Get chapters
            chapters = self.get_collection_chapters(code)
            print(f"Found {len(chapters)} chapters")
            
            # Scrape each chapter
            for i, chapter in enumerate(chapters):
                print(f"Chapter {i+1}/{len(chapters)}: {chapter['name']}")
                
                hadiths = self.get_hadiths_from_chapter(chapter['url'])
                
                self.data[code]['chapters'].append({
                    'name': chapter['name'],
                    'id': chapter['id'],
                    'hadiths': hadiths,
                    'count': len(hadiths)
                })
                
                self.data[code]['total_hadiths'] += len(hadiths)
                
                # Be respectful with requests
                time.sleep(1)
            
            # Save intermediate results
            self.save_data(code)
    
    def save_data(self, collection_code=None):
        """Save scraped data to JSON files"""
        output_dir = Path('m:\\Sheikh Ahmed\\data')
        output_dir.mkdir(exist_ok=True)
        
        if collection_code:
            filename = output_dir / f'{collection_code}.json'
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.data[collection_code], f, ensure_ascii=False, indent=2)
            print(f"Saved: {filename}")
        else:
            filename = output_dir / 'all_hadiths.json'
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            print(f"Saved: {filename}")
    
    def print_summary(self):
        """Print scraping summary"""
        print(f"\n{'='*60}")
        print("SCRAPING SUMMARY")
        print(f"{'='*60}")
        
        total_hadiths = 0
        for code, data in self.data.items():
            count = data['total_hadiths']
            total_hadiths += count
            print(f"{data['name']}: {count} hadiths")
        
        print(f"\nTotal hadiths scraped: {total_hadiths}")

if __name__ == '__main__':
    scraper = SunnahScraper()
    
    try:
        scraper.scrape_all()
        scraper.save_data()
        scraper.print_summary()
        print("\n✓ Scraping completed successfully!")
    except Exception as e:
        print(f"\n✗ Error during scraping: {e}")
        import traceback
        traceback.print_exc()
