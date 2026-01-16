import argparse
from pathlib import Path
import fitz  # PyMuPDF


def choose_font() -> str | None:
    # Prefer Traditional Arabic on Windows if available
    candidates = [
        r"C:\\Windows\\Fonts\\trado.ttf",  # Traditional Arabic
        r"C:\\Windows\\Fonts\\arabtype.ttf",  # Arabic Typesetting
        r"C:\\Windows\\Fonts\\arial.ttf",
    ]
    for c in candidates:
        if Path(c).exists():
            return c
    return None


def generate_pdf(text: str, out_path: Path, title: str = "خطبة", subtitle: str = "", signature_image: Path | None = None):
    out_path.parent.mkdir(parents=True, exist_ok=True)

    doc = fitz.open()
    page = doc.new_page()  # default: A4
    width, height = page.rect.width, page.rect.height

    margin = 36  # pts (~0.5in)
    box = fitz.Rect(margin, margin + 60, width - margin, height - margin - 80)

    fontfile = choose_font()

    # Header
    header_rect = fitz.Rect(margin, margin, width - margin, margin + 50)
    page.insert_textbox(
        header_rect,
        f"{title}\n{subtitle}" if subtitle else title,
        fontsize=18,
        fontfile=fontfile,
        align=fitz.TEXT_ALIGN_CENTER,
        color=(0, 0, 0),
    )

    # Body
    page.insert_textbox(
        box,
        text,
        fontsize=13,
        fontfile=fontfile,
        align=fitz.TEXT_ALIGN_RIGHT,
        color=(0, 0, 0),
    )

    # Footer signature
    footer_y = height - margin - 60
    sig_rect = fitz.Rect(margin, footer_y, width - margin, footer_y + 50)
    if signature_image and signature_image.exists():
        try:
            img_rect = fitz.Rect(width/2 - 80, footer_y, width/2 + 80, footer_y + 40)
            page.insert_image(img_rect, filename=str(signature_image))
        except Exception:
            page.insert_textbox(
                sig_rect,
                "توقيع: الشيخ أحمد إسماعيل الفشني",
                fontsize=12,
                fontfile=fontfile,
                align=fitz.TEXT_ALIGN_CENTER,
            )
    else:
        page.insert_textbox(
            sig_rect,
            "توقيع: الشيخ أحمد إسماعيل الفشني",
            fontsize=12,
            fontfile=fontfile,
            align=fitz.TEXT_ALIGN_CENTER,
        )

    doc.save(out_path)
    doc.close()


def main():
    ap = argparse.ArgumentParser(description="Generate a styled PDF for a khutba text (Arabic RTL)")
    ap.add_argument("text_file", help="Path to UTF-8 text file")
    ap.add_argument("output_pdf", help="Output PDF path")
    ap.add_argument("--title", default="خطبة الجمعة")
    ap.add_argument("--subtitle", default="")
    ap.add_argument("--signature", default="assets/signature.png")
    args = ap.parse_args()

    src = Path(args.text_file)
    out = Path(args.output_pdf)
    sig = Path(args.signature)

    text = src.read_text(encoding="utf-8")
    generate_pdf(text, out, title=args.title, subtitle=args.subtitle, signature_image=sig if sig.exists() else None)
    print(f"Wrote PDF: {out}")


if __name__ == "__main__":
    main()
