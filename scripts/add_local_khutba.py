import argparse
import json
from pathlib import Path
from datetime import datetime
import sys
from urllib.parse import quote

# Ensure project root on sys.path for local imports
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from import_khutab_written_full import text_to_html, clean_arabic_text, safe_filename
from scripts.generate_khutba_pdf import generate_pdf


def main():
    ap = argparse.ArgumentParser(description="Add a local khutba from a text file, generate PDF, and update JSON.")
    ap.add_argument("text_file", help="Path to Arabic UTF-8 text file (khutba body)")
    ap.add_argument("--title", required=True, help="Khutba title")
    ap.add_argument("--date-iso", required=True, help="ISO date YYYY-MM-DD")
    ap.add_argument("--date-display", required=True, help="Display date (Arabic)")
    ap.add_argument("--author", default="أحمد إسماعيل الفشني")
    ap.add_argument("--out-json", default="data/khutab_written.json")
    ap.add_argument("--pdf-dir", default="khutab_pdfs")
    ap.add_argument("--id", default=None, help="Optional stable ID; defaults to local-<date>-<slug>")
    args = ap.parse_args()

    text_path = Path(args.text_file)
    out_json = Path(args.out_json)
    pdf_dir = Path(args.pdf_dir)
    pdf_dir.mkdir(parents=True, exist_ok=True)

    body_raw = text_path.read_text(encoding="utf-8")
    # Keep tashkeel for display + PDF; only remove invisible marks/normalize whitespace.
    body_clean = clean_arabic_text(body_raw)
    body_html = text_to_html(body_clean)

    # Build id and pdf filename
    base_slug = safe_filename(args.title) or "khutba"
    item_id = args.id or f"local-{args.date_iso}-{base_slug[:40]}"

    # Make the PDF filename ASCII-safe (works better with browsers + file://)
    # Use percent-encoding then reuse safe_filename() to keep the existing naming style.
    quoted_id = quote(item_id, safe="")
    pdf_name = f"{safe_filename(quoted_id)}.pdf"
    pdf_path = pdf_dir / pdf_name

    # Derive subtitle from date
    subtitle = f"بتاريخ: {args.date_display}"

    # Generate PDF
    generate_pdf(body_clean, pdf_path, title=args.title, subtitle=subtitle)

    # Load existing JSON
    items = []
    if out_json.exists():
        items = json.loads(out_json.read_text(encoding="utf-8"))
        if not isinstance(items, list):
            items = items.get("items", [])

    # Build new item
    item = {
        "id": item_id,
        "title": args.title,
        "author": args.author,
        "date": {"display": args.date_display, "iso": args.date_iso},
        "pdf_local": f"{pdf_dir.as_posix()}/{pdf_name}",
        "content_text": body_clean,
        "content_html": body_html,
        "excerpt": args.title,
    }

    # Replace if exists, else prepend
    idx = next((i for i, x in enumerate(items) if x.get("id") == item_id), None)
    if idx is not None:
        items[idx] = item
    else:
        items.insert(0, item)

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Updated {out_json} with item id={item_id}")


if __name__ == "__main__":
    main()
