import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT = ROOT / 'data' / 'youtube_raw.json'
DEFAULT_OUTPUT = ROOT / 'data' / 'videos.json'

def get_category(title, duration):
    title_lower = title.lower()
    
    # 1. Shorts
    if duration and duration <= 60:
        return "shorts"
    if "#shorts" in title_lower or "short" in title_lower:
        return "shorts"
        
    # 2. Khutbah
    if any(k in title for k in ["خطبة", "الجمعة", "جمعة"]):
        return "khutbah"
        
    # 3. Quran
    if any(k in title for k in ["تلاوة", "سورة", "قرآن", "القرآن"]):
        return "quran"
        
    # 4. Tafseer
    if "تفسير" in title:
        return "tafseer"

    # 5. Lessons (Default for long content)
    # Includes "درس", "شرح", "محاضرة", "مجلس", "خاطرة", "كلمة"
    return "lessons"

def format_duration(seconds):
    if not seconds:
        return "00:00"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"

def main():
    ap = argparse.ArgumentParser(description='Convert yt-dlp raw JSONL export into data/videos.json')
    ap.add_argument('--input', default=str(DEFAULT_INPUT), help='Path to raw youtube JSONL file')
    ap.add_argument('--output', default=str(DEFAULT_OUTPUT), help='Path to output videos.json file')
    args = ap.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        raise SystemExit(f"Missing input file: {input_path}. Generate it first (e.g., via yt-dlp) then re-run.")

    videos = []
    
    print("Reading raw file...")
    # PowerShell redirection often creates UTF-16 Little Endian files
    encoding = 'utf-16' 
    
    try:
        with open(input_path, 'r', encoding=encoding) as f:
            # Check first char to be sure
            f.read(1)
            f.seek(0)
    except UnicodeError:
        encoding = 'utf-8'

    with open(input_path, 'r', encoding=encoding) as f:
        for line in f:
            if not line.strip(): continue
            try:
                raw = json.loads(line)
                
                vid_id = raw.get('id')
                title = raw.get('title', 'Unknown Title')
                duration = raw.get('duration', 0)
                
                category = get_category(title, duration)
                duration_str = format_duration(duration)
                
                # Thumbnails: Prefer 'medium' or 'high', verify list exists
                thumb = f"https://i.ytimg.com/vi/{vid_id}/mqdefault.jpg"
                
                videos.append({
                    "id": vid_id,
                    "title": title,
                    "category": category,
                    "thumbnail": thumb,
                    "duration": duration_str,
                    "date": raw.get('upload_date', '') # Might not be in flat-playlist, usually is
                })
                
            except json.JSONDecodeError:
                continue

    print(f"Processed {len(videos)} videos.")
    
    # Sort by date usually? Or just keep order (latest first usually from yt-dlp)
    # yt-dlp returns latest first by default on /videos
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(videos, f, ensure_ascii=False, indent=2)
        
    print(f"Saved to {output_path}")

if __name__ == "__main__":
    main()
