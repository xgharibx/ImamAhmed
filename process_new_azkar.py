import json
import os
import re

# Configuration
DATA_DIR = r"m:\Sheikh Ahmed\data"
RAW_DIR = os.path.join(DATA_DIR, "raw_azkar_new")
JSON_FILE = os.path.join(DATA_DIR, "adhkar.json")

# Map filenames to logic IDs and Arabic Titles
SECTION_MAP = {
    "sleep.txt": {"id": "sleep", "title": "أذكار النوم"},
    "waking.txt": {"id": "waking", "title": "أذكار الاستيقاظ"},
    "mosque.txt": {"id": "mosque", "title": "أذكار المسجد"},
    "wudu.txt": {"id": "wudu", "title": "أذكار الوضوء"},
    "toilet.txt": {"id": "toilet", "title": "أذكار الخلاء"},
    "food.txt": {"id": "food", "title": "أذكار الطعام"},
    "hajj.txt": {"id": "hajj", "title": "أذكار الحج والعمرة"},
    "virtue.txt": {"id": "virtue", "title": "فضل الذكر"},
    "misc.txt": {"id": "misc", "title": "أذكار متفرقة"},
    "prayer.txt": {"id": "salaah", "title": "أذكار الصلاة"}
}

def clean_text(text):
    # Remove extra whitespace
    text = text.strip()
    return text

def parse_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split by the marker  count count_desc id 
    # Regex to capture content and the marker data
    # Marker pattern: \s*(\d+|who knows)\s*(\d+|who knows)\s*(\d+)\s*
    # Note: Regex might need to be flexible for spaces
    
    # We will split by the ending marker "" and then process each chunk
    chunks = content.split('')
    
    parsed_items = []
    
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
            
        # Find the start of the marker ""
        marker_split = chunk.split('')
        
        if len(marker_split) < 2:
            # Maybe just text? skip or warn
            print(f"Warning: Could not find marker start in chunk: {chunk[:20]}...")
            continue
            
        text_part = "".join(marker_split[:-1]).strip()
        marker_part = marker_split[-1].strip()
        
        # Parse marker: expecting "count description id"
        # In my generated files: "01 01 1"
        # Regex to extract numbers
        nums = re.findall(r'\d+', marker_part)
        count = 1
        if len(nums) >= 1:
            try:
                count = int(nums[0])
            except:
                pass
        
        # Clean text
        # Remove [Header] lines if present at start?
        # My generator added [Header] lines. I should keep them or format them.
        # The user wants proper text.
        
        cleaned_text = clean_text(text_part)
        
        parsed_items.append({
            "text": cleaned_text,
            "benefit": "",
            "count": count,
            "count_description": ""
        })
        
    return parsed_items

def main():
    # Load existing JSON
    with open(JSON_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    existing_ids = {s['id'] for s in data.get('sections', [])}
    
    # Process new files
    for filename, info in SECTION_MAP.items():
        filepath = os.path.join(RAW_DIR, filename)
        if not os.path.exists(filepath):
            print(f"File not found: {filename}")
            continue
            
        section_id = info['id']
        section_title = info['title']
        
        if section_id in existing_ids:
            print(f"Skipping {section_id} (already exists)")
            continue
            
        print(f"Processing {filename} -> {section_id}")
        items = parse_file(filepath)
        
        if items:
            new_section = {
                "id": section_id,
                "title": section_title,
                "content": items
            }
            data['sections'].append(new_section)
        
    # Standardise text similar to fix_adhkar_v2.py
    # Remove excessive newlines in 'text', replace with spaces if inside sentence?
    # Or keep newlines if they are poetic?
    # For now, just save.
    
    with open(JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
    print("Done updating adhkar.json")

if __name__ == "__main__":
    main()
