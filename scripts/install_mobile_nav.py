"""Attach the floating navigation to existing pages without changing their design."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def attach_navigation(text, prefix):
    if "mobile-nav.js" not in text:
        includes = f'<link rel="stylesheet" href="{prefix}mobile-nav.css">\n<script src="{prefix}mobile-nav.js" defer></script>\n'
        text = text.replace("</head>", includes + "</head>", 1)
    text = text.replace('content="width=device-width, initial-scale=1.0"',
                        'content="width=device-width, initial-scale=1.0, viewport-fit=cover"')
    return text


def install():
    paths = list(ROOT.glob("*.html")) + list((ROOT / "books").glob("*.html")) + list((ROOT / "khutab").glob("*.html"))
    paths += [ROOT / "templates/khutba-publishing/shell.html", ROOT / "templates/article-publishing/ramadan-article-template.html"]
    updated = 0
    for path in paths:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        original = text
        prefix = "" if path.parent == ROOT else "../"
        text = attach_navigation(text, prefix)
        if text != original:
            path.write_text(text, encoding="utf-8", newline="\n")
            updated += 1
    return updated


if __name__ == "__main__":
    print(f"Updated navigation includes on {install()} pages")
