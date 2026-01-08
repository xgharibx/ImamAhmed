import json
import re
import os

RAW_DIR = "data/raw_azkar"
OUTPUT_FILE = "data/adhkar.json"

SECTIONS = {
    "morning": "أذكار الصباح",
    "evening": "أذكار المساء",
    "post_prayer": "أذكار بعد الصلاة",
    "adhan": "أذكار الأذان",
    "home": "أذكار المنزل"
}

def parse_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split by the end marker
    items = content.split('')
    parsed_items = []
    
    for item in items:
        item = item.strip()
        if not item:
            continue
            
        # Extract Count info:    01 01 1
        # Regex for count: \s+(\d+)\s+(\d+)\s+(\d+)
        # Or just look for the numbers at the end if  is missing
        
        count = 1
        benefit = ""
        text = item
        
        # Check for Z match (Count marker)
        z_match = re.search(r'\s+(\d+)\s+(\d+)\s+(\d+)', item)
        if not z_match:
             # Try without Z, sometimes it's just numbers at the end
             z_match = re.search(r'(\d+)\s+(\d+)\s+(\d+)\s*$', item)
        
        if z_match:
            try:
                count = int(z_match.group(1))
                # Remove the count part from text
                text = item[:z_match.start()].strip()
            except:
                pass
        
        # Check for E match (Benefit marker)
        e_match = re.search(r'', text)
        if e_match:
            benefit_part = text[e_match.end():].strip()
            text_part = text[:e_match.start()].strip()
            
            benefit = benefit_part
            text = text_part
            
        # Clean text
        text = text.replace('Your\'s Today', '').strip()
        
        if text:
            parsed_items.append({
                "text": text,
                "benefit": benefit,
                "count": count,
                "count_description": str(count) if count > 1 else ""
            })
            
    return parsed_items

data = {"sections": []}

for filename in os.listdir(RAW_DIR):
    if filename.endswith(".txt"):
        key = filename.replace(".txt", "")
        if key in SECTIONS:
            parsed = parse_file(os.path.join(RAW_DIR, filename))
            data["sections"].append({
                "id": key,
                "title": SECTIONS[key],
                "content": parsed
            })

with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("Adhkar JSON generated.")
