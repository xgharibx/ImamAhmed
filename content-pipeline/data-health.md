# صحة البيانات | Data Health Rules

## Overview

All JSON data files must pass these validation rules before committing to maintain site stability.

---

## Validation Checklist

### For All JSON Files

- [ ] Valid JSON syntax (no trailing commas, unclosed brackets)
- [ ] UTF-8 encoding **without BOM**
- [ ] Valid trailing newline at end of file
- [ ] No literal `\n` characters after closing `]` or `}`
- [ ] No duplicate entries (check by `id` field)

### For `data/fatawa.json`

- [ ] `count` field matches `items.length`
- [ ] IDs are sequential (1, 2, 3, ...)
- [ ] No empty `question` or `answer` fields

### For `data/videos.json`

- [ ] No duplicate video IDs
- [ ] All entries have `id`, `title`, `date`, `duration`, `category`
- [ ] Duration format: `MM:SS` or `H:MM:SS` (never `0:MM:SS`)
- [ ] Categories match filter buttons in `videos.html`
- [ ] Ordered newest first

### For `data/khutab_written.json`

- [ ] Each entry has `id`, `title`, `author`, `date`, `content_text`, `content_html`, `excerpt`
- [ ] `date.iso` format: `YYYY-MM-DD`
- [ ] IDs match corresponding HTML shell page's `data-khutba-id`

### For `data/adhkar.json`

- [ ] Categories present with valid entries
- [ ] Arabic text properly encoded

### For Hadith Files (`data/bukhari.json`, etc.)

- [ ] Valid JSON structure
- [ ] Chapter/hadith numbering intact

---

## Quick Validation Commands

```powershell
# Validate JSON syntax
Get-Content "data/fatawa.json" -Raw | ConvertFrom-Json | Out-Null
Get-Content "data/videos.json" -Raw | ConvertFrom-Json | Out-Null
Get-Content "data/khutab_written.json" -Raw | ConvertFrom-Json | Out-Null

# Check fatawa count
$f = Get-Content "data/fatawa.json" -Raw | ConvertFrom-Json
Write-Host "Count field: $($f.count), Actual items: $($f.items.Count)"

# Check for duplicate video IDs
$v = Get-Content "data/videos.json" -Raw | ConvertFrom-Json
$dupes = $v | Group-Object id | Where-Object { $_.Count -gt 1 }
if ($dupes) { Write-Host "DUPLICATES FOUND:" ; $dupes | Format-Table } else { Write-Host "No duplicates" }
```

---

## Encoding Notes

- Always save as **UTF-8 without BOM**
- Arabic text must preserve diacritics (tashkeel) where intended
- Never use Windows-1256 or ISO-8859-6 encoding
- When editing JSON in PowerShell, use: `[System.IO.File]::WriteAllText($path, $content, [System.Text.UTF8Encoding]::new($false))`
