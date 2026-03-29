# فتاوى | Fatawa Pipeline

## Overview

Fatawa (Q&A rulings) are stored in `data/fatawa.json` and rendered dynamically by `fatawa.js`. The frontend at `fatawa.html` provides search, filtering, and social sharing.

---

## Step-by-Step: Adding New Fatawa

### 1. Prepare the Content
- Extract question and answer text from the source (DOCX, text, or dictation)
- Clean up the answer text — remove trailing numbering artifacts
- Ensure proper Arabic formatting with tashkeel where appropriate

### 2. Add to JSON
Append new entries to `data/fatawa.json` → `items` array:

```json
{
  "question": "ما حكم [الموضوع]؟",
  "answer": "الجواب: [النص الكامل للفتوى مع الأدلة والتفصيل].",
  "id": 78
}
```

**Rules:**
- `id` must be **sequential** — use the next number after the last entry
- `count` field at the top of the JSON **must match** `items.length`
- Keep answers clear and complete with Islamic references
- Append new entries at the **end** of the `items` array

### 3. Update the Count
Update the `count` field at the top of `fatawa.json`:

```json
{
  "title": "أحكام فقهية للشيخ أحمد إسماعيل الفشني",
  "generatedFrom": "QA/**/*.docx",
  "count": 78,  ← must match total items
  "items": [...]
}
```

### 4. Commit

```powershell
git add data/fatawa.json
git commit -m "Add fatwa #78: [topic summary]"
git push origin main
```

---

## Data Format

```json
{
  "title": "أحكام فقهية للشيخ أحمد إسماعيل الفشني",
  "generatedFrom": "QA/**/*.docx",
  "count": 77,
  "items": [
    {
      "question": "السؤال بالعربية",
      "answer": "الإجابة الكاملة مع الأدلة الشرعية.",
      "id": 1
    }
  ]
}
```

## Architecture

| Component | File | Role |
|-----------|------|------|
| Data source | `data/fatawa.json` | All fatawa entries (source of truth) |
| Frontend | `fatawa.html` + `fatawa.css` | Browse/search fatawa |
| Renderer | `fatawa.js` | Search, filter, render, share |
| Search utils | `search-utils.js` | Arabic text normalization |

## Features
- **Arabic search** with diacritics normalization (hamza, taa marbuta, etc.)
- **Share cards** — canvas-based image generation for social sharing
- **Expand/collapse** — answers toggle on click
- **Counter display** — total fatawa count shown
- **Responsive** — mobile-friendly card layout

## Content Guidelines
- Questions should be concise and clearly state the topic
- Answers should include:
  - The ruling (حكم)
  - Supporting evidence (Quran/Hadith/scholarly opinions)
  - Practical application when relevant
- Avoid trailing numbering from DOCX extraction (cleaned by `sanitizeAnswerText`)
