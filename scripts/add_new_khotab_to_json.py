import json
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(r"m:/Sheikh Ahmed")
JSON_PATH = ROOT / "data" / "khutab_written.json"
SOURCE_DIR = ROOT / "NewKhotab folder"

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def extract_docx_paragraphs(docx_path: Path) -> list[str]:
    with zipfile.ZipFile(docx_path) as zf:
        xml_bytes = zf.read("word/document.xml")
    root = ET.fromstring(xml_bytes)

    paragraphs: list[str] = []
    for p in root.findall('.//w:body/w:p', NS):
        runs = [t.text or "" for t in p.findall('.//w:t', NS)]
        line = "".join(runs).strip()
        if line:
            line = re.sub(r"\s+", " ", line)
            paragraphs.append(line)
    return paragraphs


def to_html_paragraphs(paragraphs: list[str]) -> str:
    def esc(s: str) -> str:
        return (
            s.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    return "\n".join(f'<p class="khutba-paragraph">{esc(p)}</p>' for p in paragraphs)


entries = [
    {
        "file": "خُطْبَةُ الْجُمُعَةِ  ٢٣ يَنَايِر ٢٠٢٦ م --.docx",
        "id": "local-2026-01-23-mihan-islam",
        "title": "الْمِهَنُ فِي الْإِسْلَامِ طَرِيقُ الْعُمْرَانِ وَالْإِيمَانِ مَعًا",
        "date_display": "٤ شَعْبَان ١٤٤٧ هـ - ٢٣ يَنَايِر ٢٠٢٦ م",
        "date_iso": "2026-01-23",
    },
    {
        "file": "(خُطْبَةُ الْجُمُعَةِ ) بتاريخ ١١ شعبان ١٤٤٧ هـ - ٣٠ يناير ٢٠٢٦م    تحت عنوان  بُطُولَاتٌ لَا تُنْسَى.. وَوَفَاءٌ لِحَقِّ الْوَطَنِ   .docx",
        "id": "local-2026-01-30-botolat-watan",
        "title": "بُطُولَاتٌ لَا تُنْسَى.. وَوَفَاءٌ لِحَقِّ الْوَطَنِ",
        "date_display": "١١ شَعْبَان ١٤٤٧ هـ - ٣٠ يَنَايِر ٢٠٢٦ م",
        "date_iso": "2026-01-30",
    },
    {
        "file": "��خطبة الحمعه (الدَّعْوَةُ إِلَى اللَّهِ تَعَالَى بِالْحِكْمَةِ وَالْمَوْعِظَةِ الْحَسَنَةِ)� 7 2 2026.docx",
        "id": "local-2026-02-06-dawah-bilhikmah",
        "title": "الدَّعْوَةُ إِلَى اللَّهِ تَعَالَى بِالْحِكْمَةِ وَالْمَوْعِظَةِ الْحَسَنَةِ",
        "date_display": "١٨ شَعْبَان ١٤٤٧ هـ - ٦ فِبْرَايِر ٢٠٢٦ م",
        "date_iso": "2026-02-06",
    },
    {
        "file": "خُطْبَةُ الْجُمُعَةِ الْقَادِمَةِ 13 2 2026م.docx",
        "id": "local-2026-02-13-ramadan-prep",
        "title": "اسْتِقْبَالُ شَهْرِ رَمَضَانَ بَيْنَ الطَّاعَةِ الرَّبَّانِيَّةِ وَالْعَادَاتِ الِاسْتِهْلَاكِيَّةِ",
        "date_display": "٢٥ شَعْبَان ١٤٤٧ هـ - ١٣ فِبْرَايِر ٢٠٢٦ م",
        "date_iso": "2026-02-13",
    },
]

with JSON_PATH.open("r", encoding="utf-8") as f:
    data = json.load(f)

if not isinstance(data, list):
    raise RuntimeError("Expected khutab_written.json to be a JSON array")

existing_ids = {item.get("id") for item in data if isinstance(item, dict)}

for meta in entries:
    docx = SOURCE_DIR / meta["file"]
    if not docx.exists():
        raise FileNotFoundError(f"Missing DOCX: {docx}")

    paragraphs = extract_docx_paragraphs(docx)
    content_text = "\n".join(paragraphs).strip()
    content_html = to_html_paragraphs(paragraphs)

    excerpt = meta["title"]
    if content_text:
        excerpt = re.sub(r"\s+", " ", content_text)[:170]

    new_item = {
        "id": meta["id"],
        "title": meta["title"],
        "author": "أحمد إسماعيل الفشني",
        "date": {
            "display": meta["date_display"],
            "iso": meta["date_iso"],
        },
        "content_text": content_text,
        "content_html": content_html,
        "excerpt": excerpt,
    }

    if meta["id"] in existing_ids:
        for idx, item in enumerate(data):
            if isinstance(item, dict) and item.get("id") == meta["id"]:
                data[idx] = new_item
                break
    else:
        data.append(new_item)

# Keep deterministic order newest first by ISO date where available

def iso(item: dict) -> str:
    d = item.get("date") if isinstance(item, dict) else None
    if isinstance(d, dict):
        return d.get("iso") or ""
    return ""


data.sort(key=lambda item: iso(item), reverse=True)

with JSON_PATH.open("w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
    f.write("\n")

print("Updated khutab_written.json with 4 new khutab entries.")
