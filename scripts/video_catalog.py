"""Shared video metadata, categorization, and channel listing helpers."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unicodedata
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VIDEOS_JSON = ROOT / "data" / "videos.json"
CHANNELS_CONFIG = ROOT / "content-pipeline" / "channels.json"

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
