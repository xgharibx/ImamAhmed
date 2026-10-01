#!/usr/bin/env python3
"""Single, deterministic publishing engine for Sheikh Ahmed's content.

The same commands are used locally and by GitHub Actions.  This keeps phone
submissions on exactly the same parsing, rendering, and validation path as
developer submissions.
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import html
import json
import re
import subprocess
import sys
import tempfile
import unicodedata
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Any
from html.parser import HTMLParser
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape as xml_escape


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
KHUTAB_JSON = DATA_DIR / "khutab_written.json"
KHUTAB_INDEX_JSON = DATA_DIR / "khutab_written_index.json"
VIDEOS_JSON = DATA_DIR / "videos.json"
KHUTAB_DIR = ROOT / "khutab"
SHELL_TEMPLATE = ROOT / "templates" / "khutba-publishing" / "shell.html"
CHANNELS_CONFIG = ROOT / "content-pipeline" / "channels.json"
SITE_URL = "https://ahmedelfashny.com"
DEFAULT_AUTHOR = "فضيلة الشيخ احمد اسماعيل الفشني"
MAX_DOCX_BYTES = 25 * 1024 * 1024
MAX_XML_BYTES = 20 * 1024 * 1024

VALID_VIDEO_CATEGORIES = {
    "lessons",
    "khutbah",
    "quran",
    "shorts",
    "tafseer",
    "tv",
    "ali-wusul",
    "fi-nur-allah",
    "qisas-ibra",
}

CATEGORY_LABELS = {
    "تحديد تلقائي": "auto",
    "دروس ومحاضرات": "lessons",
    "خطب الجمعة": "khutbah",
    "تلاوات قرآنية": "quran",
    "مقاطع قصيرة": "shorts",
    "تفسير": "tafseer",
    "لقاءات تلفزيونية": "tv",
    "برنامج على وصول": "ali-wusul",
    "برنامج في نور الله": "fi-nur-allah",
    "برنامج في قصصهم عبرة": "qisas-ibra",
}

ISSUE_HEADINGS = {
    "title": "عنوان الخطبة",
    "date_iso": "التاريخ الميلادي",
    "date_display": "التاريخ المعروض",
    "excerpt": "ملخص بطاقة الخطبة",
    "docx": "ملف Word",
    "video_url": "رابط YouTube",
    "video_category": "قسم الفيديو",
}


class PipelineError(RuntimeError):
    pass


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
    ) as handle:
        handle.write(text)
        temp_path = Path(handle.name)
    temp_path.replace(path)


def normalize_arabic(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "")
    value = re.sub(r"[\u064b-\u065f\u0670\u06d6-\u06ed]", "", value)
    return value.translate(str.maketrans("أإآٱىةـ", "اااايه ")).replace(" ", "")


def validate_iso_date(value: str) -> str:
    try:
        parsed = dt.date.fromisoformat(value)
    except ValueError as exc:
        raise PipelineError("التاريخ يجب أن يكون بصيغة YYYY-MM-DD") from exc
    if not 2000 <= parsed.year <= 2100:
        raise PipelineError("التاريخ خارج النطاق المقبول")
    return parsed.isoformat()


def extract_docx_paragraphs(path: Path, *, min_paragraphs: int = 8,
                            min_characters: int = 500, content_label: str = "الخطبة") -> list[str]:
    if not path.is_file():
        raise PipelineError(f"ملف Word غير موجود: {path}")
    if path.suffix.lower() != ".docx":
        raise PipelineError("يُسمح بملفات DOCX فقط")
    if path.stat().st_size > MAX_DOCX_BYTES:
        raise PipelineError("حجم ملف Word أكبر من 25 MB")

    try:
        with zipfile.ZipFile(path) as archive:
            info = archive.getinfo("word/document.xml")
            if info.file_size > MAX_XML_BYTES:
                raise PipelineError("النص الداخلي للملف أكبر من الحد الآمن")
            xml_bytes = archive.read(info)
    except (zipfile.BadZipFile, KeyError) as exc:
        raise PipelineError("ملف Word غير صالح أو تالف") from exc

    try:
        document = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise PipelineError("تعذر قراءة بنية ملف Word") from exc

    ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    paragraphs: list[str] = []
    for paragraph in document.iter(f"{ns}p"):
        pieces: list[str] = []
        for node in paragraph.iter():
            if node.tag == f"{ns}t" and node.text:
                pieces.append(node.text)
            elif node.tag == f"{ns}tab":
                pieces.append("\t")
            elif node.tag in {f"{ns}br", f"{ns}cr"}:
                pieces.append("\n")
        for line in "".join(pieces).splitlines() or [""]:
            line = re.sub(r"[ \t]+", " ", line).strip()
            if line:
                paragraphs.append(line)

    content_length = sum(len(p) for p in paragraphs)
    if len(paragraphs) < min_paragraphs or content_length < min_characters:
        raise PipelineError(f"محتوى {content_label} قصير جداً؛ راجع ملف Word قبل النشر")
    return paragraphs


def validate_new_khutba_content(paragraphs: list[str]) -> None:
    normalized = "\n".join(normalize_arabic(p) for p in paragraphs)
    required = {
        "عناصر الخطبة": "عناصرالخطبه",
        "الخطبة الأولى": "الخطبهالاولي",
        "الخطبة الثانية": "الخطبهالثانيه",
    }
    missing = [label for label, marker in required.items() if marker not in normalized]
    if missing:
        raise PipelineError("ملف Word يفتقد أقساماً أساسية: " + "، ".join(missing))


def compact_excerpt(value: str, limit: int = 320) -> str:
    cleaned = re.sub(r"\s+", " ", value or "").strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip(" ،؛:.-") + "…"


ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
EASTERN_DIGITS = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")
GREGORIAN_MONTHS = {
    "يناير": 1, "فبراير": 2, "مارس": 3, "ابريل": 4, "مايو": 5,
    "يونيو": 6, "يونيه": 6, "يوليو": 7, "اغسطس": 8, "سبتمبر": 9,
    "اكتوبر": 10, "نوفمبر": 11, "ديسمبر": 12,
}
DAY_UNITS = {
    "اول": 1, "غره": 1, "حادي": 1, "واحد": 1, "ثاني": 2,
    "ثالث": 3, "رابع": 4, "خامس": 5, "سادس": 6, "سابع": 7,
    "ثامن": 8, "تاسع": 9,
}
DAY_TENS = {"عاشر": 10, "عشر": 10, "عشرين": 20, "عشرون": 20,
            "ثلاثين": 30, "ثلاثون": 30}


def plain_arabic(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "").translate(ARABIC_DIGITS)
    value = re.sub(r"[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed\u200b-\u200f\ufeff]", "", value)
    value = value.translate(str.maketrans("أإآٱىةـ", "اااايه "))
    return re.sub(r"\s+", " ", value).strip()


def clean_docx_line(value: str) -> str:
    value = re.sub(r"[\u200b-\u200f\ufeff]", "", value).strip()
    return re.sub(r"^\*\*|\*\*$", "", value).strip()


def parse_written_day(prefix: str) -> int | None:
    words = re.findall(r"[\u0621-\u064a]+", plain_arabic(prefix))[-5:]
    values: list[int] = []
    for word in words:
        candidate = word
        if candidate.startswith("و") and len(candidate) > 3:
            candidate = candidate[1:]
        candidate = candidate.removeprefix("ال")
        value = DAY_UNITS.get(candidate, DAY_TENS.get(candidate))
        if value:
            values.append(value)
    if not values:
        return None
    if values[-1] >= 10:
        return values[-1] + (values[-2] if len(values) >= 2 and values[-2] < 10 else 0)
    return values[-1]


def extract_khutba_date(paragraphs: list[str]) -> tuple[str, str]:
    for raw_line in paragraphs[:12]:
        line = clean_docx_line(raw_line)
        plain = plain_arabic(line)
        year = re.search(r"\b(20\d{2})\s*م?\b", plain)
        if not year:
            continue
        before_year = plain[:year.start()]
        month_matches = [match for name in GREGORIAN_MONTHS
                         for match in re.finditer(rf"\b{name}\b", before_year)]
        if not month_matches:
            continue
        month_match = max(month_matches, key=lambda match: match.start())
        month = GREGORIAN_MONTHS[month_match.group()]
        day_prefix = before_year[:month_match.start()].split("-")[-1].split("–")[-1]
        digits = re.search(r"(\d{1,2})\s*(?:من\s*)?$", day_prefix)
        day = int(digits.group(1)) if digits else parse_written_day(day_prefix)
        if day is None:
            continue
        try:
            date_iso = dt.date(int(year.group(1)), month, day).isoformat()
        except ValueError as exc:
            raise PipelineError("التاريخ الميلادي في ملف Word غير صالح") from exc
        display = line
        # Keep the author's original Hijri wording while removing surrounding heading text.
        display = re.split(r"(?:بِ?تَ?ارِيخ|بتاريخ|الْمُوَافِقُ|الموافق)\s*[:：]?", display, maxsplit=1)[-1].strip()
        display = re.sub(r"^.*?خُ?طْ?بَ?ةُ?\s+(?:الْ?جُ?مُ?عَ?ةِ?|عِيدِ?)\s*[:：]?", "", display, count=1).strip()
        display = re.split(r"\s+لِ?فَ?ضِيلَةِ?\s+", display, maxsplit=1)[0].strip(" :،")
        year_raw = re.search(r"[20٠-٩]{4}\s*م", display)
        if year_raw:
            display = display[:year_raw.end()].strip()
        return date_iso, display.translate(EASTERN_DIGITS)
    raise PipelineError("لم أجد تاريخاً ميلادياً واضحاً في مقدمة ملف Word؛ أضف اليوم والشهر والسنة ثم أعد الرفع")


def extract_khutba_title(paragraphs: list[str], path: Path) -> str:
    for raw_line in paragraphs[:12]:
        line = clean_docx_line(raw_line)
        plain = plain_arabic(line)
        if plain.startswith("عناصر الخطبه"):
            break
        if "تحت عنوان" in plain or plain.startswith("العنوان:") or plain.startswith("عنوان الخطبه:"):
            quoted = re.search(r'["«]\s*(.+?)\s*["»]', line)
            line = quoted.group(1) if quoted else re.split(
                r"(?:تحت\s+عنوان|العنوان|عُنْوَانُ\s+الْخُطْبَةِ)\s*[:：]?\s*", line, maxsplit=1
            )[-1]
        elif any(marker in plain for marker in ("خطبه الجمعه", "خطبه عيد", "الموافق", "144", "202", "فضيله الشيخ", "بقلم", "بسم الله", "الخطبه الثانيه")):
            continue
        title = line.strip(" \"'«»🔸:،.")
        if len(title) >= 5:
            return title
    title = path.stem.replace("^.", "..").strip(" \"'«»🔸")
    if len(title) >= 5:
        return title
    raise PipelineError("تعذر تحديد عنوان الخطبة من ملف Word")


def khutba_section(line: str) -> str:
    normalized = plain_arabic(line).strip(" :،.\"'«»")
    if re.fullmatch(r"(?:عناصر )?الخطبه الاولي", normalized):
        return "first"
    if re.fullmatch(r"(?:عناصر )?الخطبه الثانيه", normalized):
        return "second"
    if normalized == "الموضوع":
        return "topic"
    return ""


def outline_match_score(outline: str, body_line: str) -> float:
    def words(value: str) -> set[str]:
        normalized = plain_arabic(value)
        return {word for word in re.findall(r"[\u0621-\u064a]{3,}", normalized)
                if word not in {"الخطبه", "الثانيه", "الاولى", "العنصر", "الله", "على", "في", "من", "الى", "عن"}}
    outline_words = words(outline)
    body_words = words(body_line)
    return len(outline_words & body_words) / max(1, min(len(outline_words), len(body_words)))


def prepare_khutba_docx(path: Path, *, title: str = "", date_iso: str = "", date_display: str = "") -> dict[str, str]:
    paragraphs = [clean_docx_line(line) for line in extract_docx_paragraphs(path)]
    title = title or extract_khutba_title(paragraphs, path)
    if not date_iso or not date_display:
        detected_iso, detected_display = extract_khutba_date(paragraphs)
        date_iso = date_iso or detected_iso
        date_display = date_display or detected_display
    date_iso = validate_iso_date(date_iso)
    outline_start = next((i for i, line in enumerate(paragraphs[:20])
                          if plain_arabic(line).startswith("عناصر الخطبه")), -1)
    if outline_start < 0:
        raise PipelineError("ملف Word يفتقد عناصر الخطبة")
    body_start = -1
    for i in range(outline_start + 1, len(paragraphs) - 1):
        section = khutba_section(paragraphs[i])
        if (section == "topic" or
            (section == "first" and i > outline_start + 3 and len(paragraphs[i + 1]) > 40) or
            (i > outline_start + 3 and plain_arabic(paragraphs[i]).startswith("الحمد لله"))):
            body_start = i
            break
    if body_start < 0:
        raise PipelineError("تعذر تحديد بداية متن الخطبة في ملف Word")

    raw_outline = paragraphs[outline_start + 1:body_start]
    entries: list[str] = []
    second_at: int | None = None
    first_title = title
    second_title = ""
    for raw in raw_outline:
        line = re.sub(r"^\s*(?:[0-9٠-٩]+\s*[.\-):،]?\s*|[*•]\s*)", "", raw).strip()
        normalized = plain_arabic(line)
        if normalized.startswith("عناصر الخطبه الثانيه"):
            second_at = len(entries)
            continue
        if normalized.startswith("عناصر الخطبه الاولي"):
            continue
        group = re.match(r"^(?:و\s*)?الخطبه\s+(الاولي|الثانيه)\s*[:：]?\s*(.*)$", normalized)
        if group:
            raw_title = re.split(r"[:：]", line, maxsplit=1)
            group_title = raw_title[1].strip(" \"'«»") if len(raw_title) > 1 else ""
            if group.group(1) == "الثانيه":
                second_at = len(entries)
                second_title = group_title
            elif group_title:
                first_title = group_title
            continue
        if "(الخطبه الثانيه)" in normalized or normalized.endswith("الخطبه الثانيه"):
            second_at = len(entries)
            line = re.sub(r"\s*\(\s*الخطبة الثانية\s*\)\.?$", "", line).strip()
        if line:
            entries.append(line)
    if len(entries) < 2:
        raise PipelineError("عناصر الخطبة غير كافية لإنشاء صفحة وملف PDF")

    body = paragraphs[body_start:]
    second_body_at = next((i for i, line in enumerate(body[1:], 1)
                           if plain_arabic(line).startswith("الخطبه الثانيه")), -1)
    if second_body_at >= 0 and second_at is None:
        second_lines = body[second_body_at + 1:second_body_at + 15]
        for i, entry in enumerate(entries):
            if i and any(outline_match_score(entry, candidate) >= 0.62 for candidate in second_lines):
                second_at = i
                break
    if second_body_at >= 0 and (second_at is None or second_at >= len(entries)):
        raise PipelineError("تعذر فصل عناصر الخطبة الأولى عن الثانية؛ ضع (الخطبة الثانية) بجوار أول عنصر في الخطبة الثانية")
    if second_body_at < 0 and second_at is not None:
        raise PipelineError("الخطبة الثانية مذكورة في العناصر دون متن واضح")
    for header in paragraphs[:outline_start]:
        if plain_arabic(header).startswith(("والخطبه الثانيه", "و الخطبه الثانيه", "الخطبه الثانيه")) and ":" in header:
            second_title = header.split(":", 1)[1].strip(" \"'«»")
            break
    if second_at is not None and not second_title:
        second_title = entries[second_at]
    if second_title and ":" in second_title:
        label, remainder = second_title.split(":", 1)
        if plain_arabic(label).strip() in {"اولا", "ثانيا", "ثالثا", "رابعا", "خامسا", "سادسا", "سابعا", "ثامنا", "تاسعا", "عاشرا"}:
            second_title = remainder.strip()
    if second_title:
        second_title = second_title.rstrip(". ")

    outline = ["عَنَاصِرُ الْخُطْبَةِ", f"١. الخطبة الأولى: {first_title}"]
    for i, entry in enumerate(entries):
        if i == second_at:
            outline.append(f"{len(outline)}. الخطبة الثانية: {second_title}".translate(EASTERN_DIGITS))
        outline.append(f"{len(outline)}. {entry}".translate(EASTERN_DIGITS))

    normalized_body: list[str] = []
    for i, line in enumerate(body):
        section = khutba_section(line)
        if i == 0 and section == "topic":
            normalized_body.append("الْخُطْبَةُ الْأُولَى")
            continue
        prefix = plain_arabic(line)
        if prefix.startswith("الخطبه الاولي") or prefix.startswith("الخطبه الثانيه"):
            heading = "الْخُطْبَةُ الْأُولَى" if prefix.startswith("الخطبه الاولي") else "الْخُطْبَةُ الثَّانِيَةُ"
            if section in {"first", "second"}:
                normalized_body.append(heading)
                continue
            parts = re.split(r"[:：]", line, maxsplit=1)
            if len(parts) > 1 and len(parts[1].strip()) > 80:
                normalized_body.extend((heading, parts[1].strip()))
                continue
        normalized_body.append(line)
    if not any(khutba_section(line) == "first" for line in normalized_body):
        normalized_body.insert(0, "الْخُطْبَةُ الْأُولَى")

    intro = [f"خُطْبَةُ الْجُمُعَةِ بتاريخ {date_display}", title]
    if second_title and plain_arabic(second_title) != plain_arabic(title):
        intro.append(f"وَالْخُطْبَةُ الثَّانِيَةُ: {second_title}")
    intro.append(f"بقلم {DEFAULT_AUTHOR}")
    summary = "تتناول الخطبة " + "، و".join(entries[:2])
    if second_at is not None:
        summary += "، ثم في الخطبة الثانية " + entries[second_at]
    summary = compact_excerpt(summary.rstrip(". ") + ".")
    content_text = "\n".join([*intro, "", *outline, "", *normalized_body])
    validate_new_khutba_content(content_text.splitlines())
    return {"title": title, "date_iso": date_iso, "date_display": date_display,
            "excerpt": summary, "content_text": content_text}


def make_khutba_id(date_iso: str, title: str) -> str:
    digest = hashlib.sha256(f"{date_iso}\n{title}".encode("utf-8")).hexdigest()[:12]
    return f"local-{date_iso}-{digest}"


def make_shell_name(date_iso: str, khutba_id: str) -> str:
    compact = base64.urlsafe_b64encode(khutba_id.encode("utf-8")).decode("ascii").rstrip("=").lower()[:12]
    return f"k-{date_iso.replace('-', '')}-{compact}.html"


def existing_primary_shells() -> dict[str, str]:
    result: dict[str, str] = {}
    for path in sorted(KHUTAB_DIR.glob("k-*.html")):
        raw = path.read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("cp1256", errors="replace")
        match = re.search(r'data-khutba-id="([^"]+)"', text)
        if match:
            result[match.group(1)] = path.name
    return result


def render_khutba_shell(item: dict[str, Any], filename: str, canonical_name: str | None = None) -> str:
    template = SHELL_TEMPLATE.read_text(encoding="utf-8")
    title = str(item["title"]).strip()
    author = str(item.get("author") or DEFAULT_AUTHOR).strip()
    display_date = str(item["date"]["display"]).strip()
    date_iso = validate_iso_date(str(item["date"]["iso"]))
    description = f"{title} — بقلم {author} • {display_date}"
    canonical_file = canonical_name or filename
    version = date_iso.replace("-", "") + "-1"
    replacements = {
        "{{TITLE}}": html.escape(title, quote=True),
        "{{DESCRIPTION}}": html.escape(description, quote=True),
        "{{CANONICAL_URL}}": html.escape(f"{SITE_URL}/khutab/{urllib.parse.quote(canonical_file)}", quote=True),
        "{{OG_IMAGE}}": f"{SITE_URL}/assets/og/sheikh-ahmed-share.jpg?v={version}",
        "{{UPDATED_TIME}}": f"{date_iso}T00:00:00+00:00",
        "{{KHUTBA_ID}}": html.escape(str(item["id"]), quote=True),
        "{{KHUTBA_ID_JS}}": str(item["id"]).replace("\\", "\\\\").replace("'", "\\'"),
        "{{DATE_DISPLAY}}": html.escape(display_date, quote=True),
    }
    rendered = template
    for token, replacement in replacements.items():
        rendered = rendered.replace(token, replacement)
    leftovers = re.findall(r"\{\{[A-Z0-9_]+\}\}", rendered)
    if leftovers:
        raise PipelineError(f"رموز قالب غير مستبدلة: {leftovers}")
    return rendered.rstrip() + "\n"


def publish_khutba(args: argparse.Namespace) -> dict[str, str]:
    prepared = prepare_khutba_docx(Path(args.docx).resolve(), title=args.title or "",
                                   date_iso=args.date or "", date_display=args.date_display or "")
    date_iso = prepared["date_iso"]
    title = re.sub(r"\s+", " ", prepared["title"]).strip()
    date_display = re.sub(r"\s+", " ", prepared["date_display"]).strip()
    excerpt = compact_excerpt(args.excerpt or prepared["excerpt"])
    if not 5 <= len(title) <= 300:
        raise PipelineError("عنوان الخطبة يجب أن يكون بين 5 و300 حرف")
    if len(date_display) < 6:
        raise PipelineError("التاريخ المعروض غير مكتمل")
    if not 20 <= len(excerpt) <= 320:
        raise PipelineError("ملخص البطاقة يجب أن يكون بين 20 و320 حرف")

    khutba_id = args.id or make_khutba_id(date_iso, title)
    if not re.fullmatch(r"[a-z0-9-]{12,100}", khutba_id):
        raise PipelineError("معرّف الخطبة غير صالح")

    items = read_json(KHUTAB_JSON)
    if any(item.get("id") == khutba_id for item in items):
        raise PipelineError(f"الخطبة موجودة بالفعل بالمعرّف {khutba_id}")
    if any(
        (item.get("date") or {}).get("iso") == date_iso
        and normalize_arabic(str(item.get("title", ""))) == normalize_arabic(title)
        for item in items
    ):
        raise PipelineError("توجد خطبة بنفس العنوان والتاريخ بالفعل")

    entry = {
        "id": khutba_id,
        "title": title,
        "author": args.author,
        "date": {"display": date_display, "iso": date_iso},
        "content_text": prepared["content_text"],
        "content_html": "",
        "excerpt": excerpt,
    }
    filename = make_shell_name(date_iso, khutba_id)
    if (KHUTAB_DIR / filename).exists():
        stem = filename.removesuffix(".html")
        digest = hashlib.sha256(khutba_id.encode("utf-8")).hexdigest()[:8]
        filename = f"{stem}-{digest}.html"
        if (KHUTAB_DIR / filename).exists():
            raise PipelineError(f"صفحة الخطبة موجودة بالفعل: {filename}")
    entry["file"] = f"khutab/{filename}"
    items.append(entry)
    items.sort(key=lambda item: (item.get("date") or {}).get("iso", ""), reverse=True)
    shell = render_khutba_shell(entry, filename)
    index = []
    for item in items:
        row = {"id": item["id"], "title": item["title"], "author": item["author"],
               "date": item["date"], "excerpt": item["excerpt"],
               "has_content": bool(item.get("content_text") or item.get("content_html"))}
        if item.get("file"):
            row["file"] = item["file"]
        index.append(row)
    write_json(KHUTAB_JSON, items)
    write_json(KHUTAB_INDEX_JSON, index)
    (KHUTAB_DIR / filename).write_text(shell, encoding="utf-8", newline="\n")
    return {"id": khutba_id, "title": title, "file": f"khutab/{filename}"}


def validate_khutba_result(result: dict[str, str]) -> dict[str, str]:
    item_id = result.get("id", "")
    matches = [item for item in read_json(KHUTAB_JSON) if item.get("id") == item_id]
    if len(matches) != 1:
        raise PipelineError("سجل الخطبة الجديدة مفقود أو مكرر")
    item = matches[0]
    index_matches = [entry for entry in read_json(KHUTAB_INDEX_JSON) if entry.get("id") == item_id]
    if len(index_matches) != 1 or not index_matches[0].get("has_content"):
        raise PipelineError("البطاقة الجديدة مفقودة أو بلا محتوى")
    card = index_matches[0]
    if any(card.get(key) != item.get(key) for key in ("title", "author", "date", "excerpt")):
        raise PipelineError("البطاقة لا تطابق بيانات صفحة الخطبة")
    date_iso = validate_iso_date(item["date"]["iso"])
    expected_file = item.get("file") or f"khutab/{make_shell_name(date_iso, item_id)}"
    if result.get("file") != expected_file or card.get("file") != expected_file:
        raise PipelineError("رابط البطاقة لا يطابق اسم صفحة الخطبة")
    expected_name = Path(expected_file).name
    shell_path = KHUTAB_DIR / expected_name
    if not shell_path.is_file():
        raise PipelineError("صفحة الخطبة غير موجودة")
    shell = shell_path.read_text(encoding="utf-8")
    if f'data-khutba-id="{item_id}"' not in shell or item["title"] not in html.unescape(shell):
        raise PipelineError("صفحة الخطبة لا تطابق سجل المحتوى")
    content = item.get("content_text", "")
    if not content or item.get("content_html") != "":
        raise PipelineError("متن الخطبة غير صالح")
    validate_new_khutba_content(content.splitlines())
    if "الخطبة الأولى:" not in content or "الخطبة الثانية:" not in content:
        raise PipelineError("عناصر الخطبتين غير مجمعة في المتن")
    sitemap = ROOT / "sitemap.xml"
    if not sitemap.is_file() or f"{SITE_URL}/{result['file']}" not in sitemap.read_text(encoding="utf-8"):
        raise PipelineError("رابط الخطبة غير موجود في sitemap.xml")
    return {"id": item_id, "file": result["file"]}


def validate_khutba_result_file(args: argparse.Namespace) -> dict[str, str]:
    return validate_khutba_result(read_json(Path(args.result)))


def seconds_to_duration(value: Any) -> str:
    try:
        total = int(float(value))
    except (TypeError, ValueError):
        return ""
    if total < 0:
        return ""
    hours, remainder = divmod(total, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes}:{seconds:02d}"


def classify_video(title: str, duration: str = "", feed: str = "", default: str = "") -> str:
    if default in VALID_VIDEO_CATEGORIES:
        return default
    text = normalize_arabic(title).lower()
    if "عليوصول" in text:
        return "ali-wusul"
    if "فينورالله" in text or "فينورالقران" in text:
        return "fi-nur-allah"
    if "فيقصصهمعبره" in text or "قصصهمعبره" in text or "قصهوعبره" in text:
        return "qisas-ibra"
    if feed == "shorts":
        return "shorts"
    words = " ".join(normalize_arabic(word) for word in re.findall(r"[\w\u064b-\u065f]+", title.replace("_", " "))).lower()

    def contains(*phrases):
        return any(re.search(r"(?<!\w)و?" + re.escape(phrase) + r"(?!\w)", words) for phrase in phrases)

    parts = duration.split(":") if duration else []
    try:
        seconds = sum(int(part) * (60 ** index) for index, part in enumerate(reversed(parts)))
    except ValueError:
        seconds = 0
    talk_category = "shorts" if 0 < seconds <= 180 else "lessons"
    if any(word in text for word in ("خطبه", "خطبالجمعه", "منبرالجمعه", "الخطبالمنبريه")) or ("الجمعه" in text and "بعنوان" in text):
        return "khutbah"
    if "تفسير" in text:
        return "tafseer"
    if contains("قران الصباح", "صباح القران"):
        return "quran"
    if any(word in text for word in ("التلفزيون", "القناه", "لقاءتلفزيوني", "برنامج", "النيلالثقافيه", "منارهالازهر", "الاذاعه", "اذيعت")) or contains("قناه", "حلقه", "اذاعه"):
        return "tv"
    # Talks about prayer or Quran are not recitations merely because those words occur.
    if contains("خاطره", "خواطر", "سلسله", "درس", "موعظه", "احكام", "فقه", "الفقه", "وقفه مع", "الاسئله", "ما حكم", "منهج", "معني", "كلمه"):
        return talk_category
    if contains("سوره", "سورتي", "سور", "تلاوه", "تلاوات", "المصحف", "ما تيسر", "قران الصلاه"):
        return "quran"
    if contains("كيف", "دعاء", "ابتهال"):
        return talk_category
    if contains("تراويح", "التراويح", "تهجد", "التهجد", "صلاه", "صلاتي", "فجر", "الفجر", "فجريه", "العشاء"):
        return "quran"
    return talk_category


def run_yt_dlp(url: str, flat: bool = False, playlist_end: int = 0) -> dict[str, Any]:
    command = [sys.executable, "-m", "yt_dlp", "--ignore-errors", "--no-warnings"]
    if flat:
        command += ["--flat-playlist", "--dump-single-json"]
        if playlist_end:
            command += ["--playlist-end", str(playlist_end)]
    else:
        command += ["--skip-download", "--dump-single-json", "--no-playlist"]
    command.append(url)
    try:
        completed = subprocess.run(command, check=True, capture_output=True, text=True, encoding="utf-8", timeout=180)
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as exc:
        detail = getattr(exc, "stderr", "") or str(exc)
        raise PipelineError("تعذر جلب بيانات YouTube: " + detail.strip()[-500:]) from exc
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise PipelineError("استجابة YouTube غير صالحة") from exc


def ensure_youtube_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url.strip())
    host = (parsed.hostname or "").lower()
    if host not in {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be", "music.youtube.com"}:
        raise PipelineError("يجب استخدام رابط YouTube صالح")
    return url.strip()


def video_record(metadata: dict[str, Any], *, category: str = "auto", source: dict[str, Any] | None = None, feed: str = "") -> dict[str, str]:
    source = source or {}
    video_id = str(metadata.get("id") or "").strip()
    title = str(metadata.get("title") or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{6,20}", video_id) or not title:
        raise PipelineError("بيانات الفيديو تفتقد المعرّف أو العنوان")
    duration = str(metadata.get("duration_string") or "").strip() or seconds_to_duration(metadata.get("duration"))
    upload_date = str(metadata.get("upload_date") or "").strip()
    if re.fullmatch(r"\d{8}", upload_date):
        upload_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:]}"
    elif not re.fullmatch(r"\d{4}-\d{2}-\d{2}", upload_date):
        upload_date = ""
    selected = category if category in VALID_VIDEO_CATEGORIES else classify_video(
        title, duration, feed, str(source.get("defaultCategory") or "")
    )
    thumbnail = str(metadata.get("thumbnail") or f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg")
    return {
        "id": video_id,
        "title": title,
        "category": selected,
        "thumbnail": thumbnail,
        "duration": duration,
        "date": upload_date,
        "sourceChannel": str(source.get("sourceChannel") or "main"),
        "channelHandle": str(source.get("channelHandle") or "@ahmedelfashny"),
        "channelName": str(source.get("channelName") or "الشيخ أحمد إسماعيل الفشني"),
    }


def add_video(args: argparse.Namespace) -> dict[str, str]:
    url = ensure_youtube_url(args.url)
    metadata = run_yt_dlp(url)
    record = video_record(metadata, category=args.category)
    videos = read_json(VIDEOS_JSON)
    if any(item.get("id") == record["id"] for item in videos):
        return {"id": record["id"], "title": record["title"], "status": "already-present"}
    videos.insert(0, record)
    write_json(VIDEOS_JSON, videos)
    return {"id": record["id"], "title": record["title"], "status": "added"}


def sync_youtube(args: argparse.Namespace) -> dict[str, Any]:
    sources = read_json(CHANNELS_CONFIG)
    videos = read_json(VIDEOS_JSON)
    existing = {str(item.get("id")) for item in videos}
    additions: list[dict[str, str]] = []
    seen = set(existing)
    for source in sources:
        for feed in source.get("feeds", ["videos"]):
            playlist_url = str(source["url"]).rstrip("/") + f"/{feed}"
            print(f"Reading {source['channelHandle']}/{feed}", file=sys.stderr)
            try:
                payload = run_yt_dlp(playlist_url, flat=True, playlist_end=args.limit)
            except PipelineError as exc:
                if "does not have a" in str(exc) and "tab" in str(exc):
                    print(f"Skipping absent optional tab: {feed}", file=sys.stderr)
                    continue
                raise
            for item in payload.get("entries") or []:
                if not item or str(item.get("id")) in seen:
                    continue
                # Flat channel listings omit exact upload dates. Resolve new items before publication.
                if not item.get("upload_date"):
                    print(f"Checking new video {item.get('id')}", file=sys.stderr)
                    metadata = run_yt_dlp("https://www.youtube.com/watch?v=" + str(item["id"]))
                    if metadata.get("live_status") in {"is_upcoming", "is_live"}:
                        continue
                    item = {**item, **metadata}
                record = video_record(item, source=source, feed=feed)
                seen.add(record["id"])
                additions.append(record)
    if additions:
        write_json(VIDEOS_JSON, sorted(additions + videos, key=lambda item: item.get("date", ""), reverse=True))
    return {"added": len(additions), "ids": [item["id"] for item in additions]}


def parse_issue_sections(body: str) -> dict[str, str]:
    matches = list(re.finditer(r"^###\s+(.+?)\s*$", body or "", flags=re.MULTILINE))
    result: dict[str, str] = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        value = body[start:end].strip()
        if value and value != "_No response_":
            result[match.group(1).strip()] = value
    return result


def extract_attachment_url(value: str) -> str:
    urls = re.findall(r"https://[^\s)>]+", value or "")
    for url in urls:
        clean = url.rstrip(".,؛")
        parsed = urllib.parse.urlparse(clean)
        host = (parsed.hostname or "").lower()
        path = parsed.path
        if (host == "github.com" and
            (path.startswith(("/user-attachments/assets/", "/user-attachments/files/")) or
             re.fullmatch(r"/[^/]+/[^/]+/assets/[^/]+/[^/]+", path))):
            return clean
        if host == "user-attachments.githubusercontent.com":
            return clean
    raise PipelineError("لم يتم العثور على مرفق Word صالح في الطلب")


def allowed_attachment_redirect(host: str) -> bool:
    return host in {"github.com", "user-attachments.githubusercontent.com", "objects.githubusercontent.com"} or bool(
        re.fullmatch(r"github-production-user-asset-[a-z0-9]+\.s3\.amazonaws\.com", host)
    )


def download_docx(url: str) -> Path:
    request = urllib.request.Request(url, headers={"User-Agent": "Sheikh-Ahmed-content-pipeline"})
    try:
        response = urllib.request.urlopen(request, timeout=45)
        final_host = (urllib.parse.urlparse(response.geturl()).hostname or "").lower()
        if not allowed_attachment_redirect(final_host):
            raise PipelineError("تم رفض إعادة توجيه المرفق إلى نطاق غير موثوق")
        length = int(response.headers.get("Content-Length") or 0)
        if length > MAX_DOCX_BYTES:
            raise PipelineError("حجم ملف Word أكبر من 25 MB")
        data = response.read(MAX_DOCX_BYTES + 1)
    except (OSError, ValueError) as exc:
        raise PipelineError("تعذر تنزيل ملف Word المرفق") from exc
    if len(data) > MAX_DOCX_BYTES or not data.startswith(b"PK"):
        raise PipelineError("المرفق ليس ملف DOCX صالحاً")
    handle = tempfile.NamedTemporaryFile(suffix=".docx", delete=False)
    handle.write(data)
    handle.close()
    return Path(handle.name)


def publish_issue(args: argparse.Namespace) -> dict[str, Any]:
    event = json.loads(Path(args.event).read_text(encoding="utf-8"))
    issue = event.get("issue") or {}
    labels = {str(item.get("name")) for item in issue.get("labels") or []}
    issue_title = str(issue.get("title") or "")
    sections = parse_issue_sections(str(issue.get("body") or ""))
    if "خُطبة مكتوبة" in labels or issue_title.startswith("[نشر خطبة]"):
        required = ["docx"]
        values: dict[str, str] = {}
        for key in required:
            heading = ISSUE_HEADINGS[key]
            if heading not in sections:
                raise PipelineError(f"الحقل المطلوب غير موجود: {heading}")
            values[key] = sections[heading]
        attachment = download_docx(extract_attachment_url(values["docx"]))
        try:
            namespace = argparse.Namespace(
                docx=str(attachment),
                title=sections.get(ISSUE_HEADINGS["title"], ""),
                date=sections.get(ISSUE_HEADINGS["date_iso"], ""),
                date_display=sections.get(ISSUE_HEADINGS["date_display"], ""),
                excerpt=sections.get(ISSUE_HEADINGS["excerpt"], ""),
                author=DEFAULT_AUTHOR,
                id="",
            )
            return {"kind": "khutba", **publish_khutba(namespace)}
        finally:
            attachment.unlink(missing_ok=True)
    if "فيديو" in labels or issue_title.startswith("[نشر فيديو]"):
        url = sections.get(ISSUE_HEADINGS["video_url"], "")
        label = sections.get(ISSUE_HEADINGS["video_category"], "تحديد تلقائي")
        category = CATEGORY_LABELS.get(label, label if label in VALID_VIDEO_CATEGORIES else "auto")
        return {"kind": "video", **add_video(argparse.Namespace(url=url, category=category))}
    raise PipelineError("نوع طلب النشر غير معروف")


def rebuild_shells(args: argparse.Namespace) -> dict[str, int]:
    items = read_json(KHUTAB_JSON)
    by_id = {str(item["id"]): item for item in items}
    primary = existing_primary_shells()
    missing = [item_id for item_id in by_id if item_id not in primary]
    if missing:
        raise PipelineError("خطب بلا صفحات أساسية: " + ", ".join(missing))
    changed = 0
    paths = list(KHUTAB_DIR.glob("*.html")) if args.include_aliases else list(KHUTAB_DIR.glob("k-*.html"))
    for path in paths:
        raw = path.read_bytes()
        try:
            old = raw.decode("utf-8")
        except UnicodeDecodeError:
            old = raw.decode("cp1256", errors="replace")
        match = re.search(r'data-khutba-id="([^"]+)"', old)
        if not match:
            continue
        item_id = match.group(1)
        if item_id not in by_id:
            legacy_date = re.search(r"local-(\d{4}-\d{2}-\d{2})-", item_id)
            candidates = [
                candidate_id
                for candidate_id, candidate in by_id.items()
                if legacy_date and (candidate.get("date") or {}).get("iso") == legacy_date.group(1)
            ]
            if len(candidates) != 1:
                continue
            item_id = candidates[0]
        rendered = render_khutba_shell(by_id[item_id], path.name, primary[item_id])
        if raw != rendered.encode("utf-8"):
            path.write_text(rendered, encoding="utf-8", newline="\n")
            changed += 1
    return {"changed": changed, "checked": len(paths)}


def migrate_legacy_data(_: argparse.Namespace) -> dict[str, int]:
    """Apply lossless schema normalization required by the quality gate."""
    videos = read_json(VIDEOS_JSON)
    converted_dates = 0
    for item in videos:
        value = str(item.get("date") or "").strip()
        match = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", value)
        if match:
            day, month, year = match.groups()
            try:
                item["date"] = dt.date(int(year), int(month), int(day)).isoformat()
            except ValueError as exc:
                raise PipelineError(f"تاريخ فيديو غير صالح: {value}") from exc
            converted_dates += 1

    khutab = read_json(KHUTAB_JSON)
    added_fields = 0
    for item in khutab:
        if "content_html" not in item:
            item["content_html"] = ""
            added_fields += 1

    if converted_dates:
        write_json(VIDEOS_JSON, videos)
    if added_fields:
        write_json(KHUTAB_JSON, khutab)
    return {"video_dates_converted": converted_dates, "khutba_fields_added": added_fields}


def public_html_paths() -> list[Path]:
    paths = list(ROOT.glob("*.html")) + list((ROOT / "books").glob("*.html")) + list(KHUTAB_DIR.glob("*.html"))
    return sorted(path for path in paths if path.is_file())


def repair_seo_metadata(_: argparse.Namespace) -> dict[str, int]:
    canonicals_added = 0
    descriptions_added = 0
    for path in public_html_paths():
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(ROOT).as_posix()
        encoded_path = urllib.parse.quote(relative, safe="/")
        if not re.search(r'<link\s+[^>]*rel=["\']canonical["\']', text, flags=re.IGNORECASE):
            canonical = f'  <link rel="canonical" href="{SITE_URL}/{encoded_path}">'
            text, count = re.subn(r"(</title>)", r"\1\n" + canonical, text, count=1, flags=re.IGNORECASE)
            if not count:
                raise PipelineError(f"صفحة بلا title لإضافة canonical: {relative}")
            canonicals_added += 1
        if not re.search(r'<meta\s+[^>]*name=["\']description["\']', text, flags=re.IGNORECASE):
            title_match = re.search(r"<title>(.*?)</title>", text, flags=re.IGNORECASE | re.DOTALL)
            title = html.unescape(re.sub(r"\s+", " ", title_match.group(1)).strip()) if title_match else "محتوى إسلامي"
            short_title = title.split("|")[0].strip()
            description = html.escape(
                f"{short_title} — بقلم فضيلة الشيخ أحمد إسماعيل الفشني.", quote=True
            )
            meta = f'  <meta name="description" content="{description}">'
            text, count = re.subn(
                r"(<meta\s+[^>]*name=[\"\']viewport[\"\'][^>]*>)",
                r"\1\n" + meta,
                text,
                count=1,
                flags=re.IGNORECASE,
            )
            if not count:
                text, count = re.subn(r"(<meta\s+[^>]*charset[^>]*>)", r"\1\n" + meta, text, count=1, flags=re.IGNORECASE)
            if not count:
                raise PipelineError(f"تعذر إضافة الوصف إلى: {relative}")
            descriptions_added += 1
        path.write_text(text, encoding="utf-8", newline="\n")
    return {"canonicals_added": canonicals_added, "descriptions_added": descriptions_added}


def generate_sitemap(_: argparse.Namespace) -> dict[str, int]:
    paths: list[Path] = []
    for path in public_html_paths():
        relative = path.relative_to(ROOT).as_posix()
        if relative.startswith("khutab/") and not path.name.startswith("k-"):
            continue
        if path.name == "khutba-view.html":
            continue
        paths.append(path)
    urls = []
    for path in paths:
        relative = path.relative_to(ROOT).as_posix()
        location = SITE_URL + ("/" if relative == "index.html" else "/" + urllib.parse.quote(relative, safe="/"))
        urls.append(f"  <url><loc>{xml_escape(location)}</loc></url>")
    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(urls) + "\n</urlset>\n"
    (ROOT / "sitemap.xml").write_text(sitemap, encoding="utf-8", newline="\n")
    robots = "User-agent: *\nAllow: /\nDisallow: /admin/\n\nSitemap: https://ahmedelfashny.com/sitemap.xml\n"
    (ROOT / "robots.txt").write_text(robots, encoding="utf-8", newline="\n")
    return {"urls": len(urls)}


class SiteAuditParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.description = False
        self.canonical = False
        self.ids: list[str] = []
        self.references: list[tuple[str, str]] = []
        self.unsafe_blank_targets = 0
        self.insecure_assets = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): value or "" for key, value in attrs}
        if tag == "meta" and values.get("name", "").lower() == "description" and values.get("content", "").strip():
            self.description = True
        if tag == "link" and "canonical" in values.get("rel", "").lower() and values.get("href"):
            self.canonical = True
        if values.get("id"):
            self.ids.append(values["id"])
        if values.get("target", "").lower() == "_blank" and "noopener" not in values.get("rel", "").lower():
            self.unsafe_blank_targets += 1
        for attribute in ("href", "src"):
            value = values.get(attribute, "").strip()
            if value:
                self.references.append((attribute, value))
                if value.lower().startswith("http://"):
                    self.insecure_assets += 1


def audit_public_site(_: argparse.Namespace) -> dict[str, int]:
    errors: list[str] = []
    pages = public_html_paths() + [ROOT / "admin" / "index.html"]
    for path in pages:
        relative = path.relative_to(ROOT)
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            errors.append(f"صفحة ليست UTF-8: {relative}")
            continue
        parser = SiteAuditParser()
        try:
            parser.feed(text)
        except Exception as exc:
            errors.append(f"تعذر تحليل HTML في {relative}: {exc}")
            continue
        if not parser.description:
            errors.append(f"صفحة بلا description: {relative}")
        if relative.parts[0] != "admin" and not parser.canonical:
            errors.append(f"صفحة بلا canonical: {relative}")
        duplicate_ids = sorted({value for value in parser.ids if parser.ids.count(value) > 1})
        if duplicate_ids:
            errors.append(f"معرّفات HTML مكررة في {relative}: {duplicate_ids}")
        if parser.unsafe_blank_targets:
            errors.append(f"روابط target=_blank بلا noopener في {relative}")
        if parser.insecure_assets:
            errors.append(f"روابط HTTP غير آمنة في {relative}")
        for _, reference in parser.references:
            if reference.startswith(("#", "http://", "https://", "mailto:", "tel:", "javascript:", "data:", "//")):
                continue
            local_path = urllib.parse.unquote(urllib.parse.urlsplit(reference).path)
            if local_path and not (path.parent / local_path).resolve().exists():
                errors.append(f"مرجع محلي مفقود في {relative}: {reference}")

    for required in (ROOT / "robots.txt", ROOT / "sitemap.xml"):
        if not required.is_file():
            errors.append(f"ملف اكتشاف مفقود: {required.name}")
    if (ROOT / "sitemap.xml").is_file():
        try:
            ET.parse(ROOT / "sitemap.xml")
        except ET.ParseError as exc:
            errors.append(f"sitemap.xml غير صالح: {exc}")

    if errors:
        for error in errors:
            print("ERROR:", error, file=sys.stderr)
        raise PipelineError(f"فشل تدقيق الموقع: {len(errors)} مشكلة")
    return {"pages": len(pages), "missing_local_references": 0, "metadata_errors": 0}


def validate_repository(_: argparse.Namespace) -> dict[str, int]:
    errors: list[str] = []
    warnings: list[str] = []

    for path in sorted(DATA_DIR.glob("*.json")):
        try:
            read_json(path)
        except Exception as exc:  # validation must aggregate failures
            errors.append(f"JSON غير صالح {path.relative_to(ROOT)}: {exc}")

    try:
        videos = read_json(VIDEOS_JSON)
        seen: set[str] = set()
        for index, item in enumerate(videos):
            prefix = f"videos[{index}]"
            video_id = str(item.get("id") or "")
            if not re.fullmatch(r"[A-Za-z0-9_-]{6,20}", video_id):
                errors.append(f"{prefix}: id غير صالح")
            if video_id in seen:
                errors.append(f"{prefix}: id مكرر {video_id}")
            seen.add(video_id)
            if not str(item.get("title") or "").strip():
                errors.append(f"{prefix}: عنوان فارغ")
            if item.get("category") not in VALID_VIDEO_CATEGORIES:
                errors.append(f"{prefix}: قسم غير معروف {item.get('category')!r}")
            date_value = str(item.get("date") or "")
            if date_value and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_value):
                errors.append(f"{prefix}: تاريخ غير صالح {date_value!r}")
            duration = str(item.get("duration") or "")
            if duration and not re.fullmatch(r"(?:\d{1,3}:)?\d{1,2}:\d{2}", duration):
                errors.append(f"{prefix}: مدة غير صالحة {duration!r}")
    except Exception:
        videos = []

    try:
        khutab = read_json(KHUTAB_JSON)
        seen_ids: set[str] = set()
        dates: list[str] = []
        for index, item in enumerate(khutab):
            prefix = f"khutab[{index}]"
            required = {"id", "title", "author", "date", "content_text", "content_html", "excerpt"}
            missing = required - set(item)
            if missing:
                errors.append(f"{prefix}: حقول ناقصة {sorted(missing)}")
            item_id = str(item.get("id") or "")
            if item_id in seen_ids:
                errors.append(f"{prefix}: id مكرر {item_id}")
            seen_ids.add(item_id)
            date_value = str((item.get("date") or {}).get("iso") or "")
            try:
                validate_iso_date(date_value)
            except PipelineError:
                errors.append(f"{prefix}: تاريخ غير صالح {date_value!r}")
            dates.append(date_value)
            if not str(item.get("content_text") or "").strip():
                errors.append(f"{prefix}: محتوى فارغ")
        if dates != sorted(dates, reverse=True):
            errors.append("الخطب ليست مرتبة من الأحدث إلى الأقدم")

        primary_map: dict[str, list[Path]] = {}
        for path in KHUTAB_DIR.glob("k-*.html"):
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                errors.append(f"صفحة ليست UTF-8: {path.relative_to(ROOT)}")
                continue
            match = re.search(r'data-khutba-id="([^"]+)"', text)
            if not match:
                errors.append(f"صفحة بلا data-khutba-id: {path.relative_to(ROOT)}")
                continue
            primary_map.setdefault(match.group(1), []).append(path)
            if "????" in text:
                errors.append(f"صفحة تحتوي canonical تالف: {path.relative_to(ROOT)}")
        for item_id in seen_ids:
            count = len(primary_map.get(item_id, []))
            if count != 1:
                errors.append(f"المعرّف {item_id} له {count} صفحة أساسية بدلاً من واحدة")
        for item_id in primary_map.keys() - seen_ids:
            errors.append(f"صفحة أساسية بلا سجل JSON: {item_id}")
    except Exception:
        khutab = []

    for path in sorted(KHUTAB_DIR.glob("*.html")):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            warnings.append(f"صفحة قديمة ليست UTF-8: {path.relative_to(ROOT)}")
            continue
        if "????" in text:
            warnings.append(f"صفحة قديمة تحتوي نصاً تالفاً: {path.relative_to(ROOT)}")

    if warnings:
        for warning in warnings:
            print("WARNING:", warning, file=sys.stderr)
    if errors:
        for error in errors:
            print("ERROR:", error, file=sys.stderr)
        raise PipelineError(f"فشل التحقق: {len(errors)} مشكلة")
    return {"videos": len(videos), "khutab": len(khutab), "warnings": len(warnings)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sheikh Ahmed content publishing pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    publish = sub.add_parser("publish-khutba", help="Publish one DOCX khutba")
    publish.add_argument("--docx", required=True)
    publish.add_argument("--title", default="")
    publish.add_argument("--date", default="", help="YYYY-MM-DD")
    publish.add_argument("--date-display", default="")
    publish.add_argument("--excerpt", default="")
    publish.add_argument("--author", default=DEFAULT_AUTHOR)
    publish.add_argument("--id", default="")
    publish.set_defaults(func=publish_khutba)

    video = sub.add_parser("add-video", help="Add one YouTube video")
    video.add_argument("--url", required=True)
    video.add_argument("--category", default="auto", choices=["auto", *sorted(VALID_VIDEO_CATEGORIES)])
    video.set_defaults(func=add_video)

    sync = sub.add_parser("sync-youtube", help="Import new videos from configured channels")
    sync.add_argument("--limit", type=int, default=60)
    sync.set_defaults(func=sync_youtube)

    issue = sub.add_parser("publish-issue", help="Publish a trusted GitHub issue form")
    issue.add_argument("--event", required=True)
    issue.set_defaults(func=publish_issue)

    published = sub.add_parser("validate-khutba-result", help="Validate one newly published khutba")
    published.add_argument("--result", required=True)
    published.set_defaults(func=validate_khutba_result_file)

    rebuild = sub.add_parser("rebuild-shells", help="Regenerate khutba HTML shells from JSON")
    rebuild.add_argument("--include-aliases", action="store_true")
    rebuild.set_defaults(func=rebuild_shells)

    migrate = sub.add_parser("migrate-legacy-data", help="Normalize legacy data without changing content")
    migrate.set_defaults(func=migrate_legacy_data)

    seo = sub.add_parser("repair-seo", help="Add missing canonical URLs and descriptions")
    seo.set_defaults(func=repair_seo_metadata)

    sitemap = sub.add_parser("generate-sitemap", help="Generate sitemap.xml and robots.txt")
    sitemap.set_defaults(func=generate_sitemap)

    site_audit = sub.add_parser("audit-site", help="Audit public HTML, metadata, links, robots, and sitemap")
    site_audit.set_defaults(func=audit_public_site)

    validate = sub.add_parser("validate", help="Validate all managed content")
    validate.set_defaults(func=validate_repository)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        result = args.func(args)
    except PipelineError as exc:
        print(f"PIPELINE ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
