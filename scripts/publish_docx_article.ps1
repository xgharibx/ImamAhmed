param(
    [Parameter(Mandatory = $true)]
    [string]$DocxPath,

    [Parameter(Mandatory = $true)]
    [string]$Slug,

    [string]$RootPath = "m:\Sheikh Ahmed",
    [string]$Author = "بقلم: فضيلة الشيخ أحمد إسماعيل الفشني",
    [string]$BaseUrl = ""
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path $DocxPath)) {
    throw "DOCX not found: $DocxPath"
}

Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::OpenRead($DocxPath)
$entry = $zip.Entries | Where-Object { $_.FullName -eq 'word/document.xml' }
$reader = New-Object System.IO.StreamReader($entry.Open(), [System.Text.Encoding]::UTF8)
$xmlText = $reader.ReadToEnd()
$reader.Close()
$zip.Dispose()

[xml]$xml = $xmlText
$ns = New-Object System.Xml.XmlNamespaceManager($xml.NameTable)
$ns.AddNamespace('w', 'http://schemas.openxmlformats.org/wordprocessingml/2006/main')

$paragraphs = foreach ($p in $xml.SelectNodes('//w:p', $ns)) {
    $text = ($p.SelectNodes('.//w:t', $ns) | ForEach-Object { $_.InnerText }) -join ''
    if (-not [string]::IsNullOrWhiteSpace($text)) { $text.Trim() }
}

if ($paragraphs.Count -lt 3) {
    throw "Extracted content is too short; stopping."
}

function Resolve-BaseUrl {
    param([string]$root, [string]$fallback)

    if (-not [string]::IsNullOrWhiteSpace($fallback)) {
        return $fallback.TrimEnd('/')
    }

    $cnamePath = Join-Path $root 'CNAME'
    if (Test-Path $cnamePath) {
        $domain = (Get-Content -Path $cnamePath -Raw -Encoding UTF8).Trim()
        if ($domain) { return "https://$domain" }
    }

    return "https://xgharibx.github.io/ImamAhmed"
}

$title = $paragraphs[0]
$bodyParagraphs = $paragraphs | Select-Object -Skip 1
$resolvedBaseUrl = Resolve-BaseUrl -root $RootPath -fallback $BaseUrl
$pageUrl = "$resolvedBaseUrl/books/$Slug.html"
$ogImageUrl = "$resolvedBaseUrl/assets/og/sheikh-ahmed-share.png"

$processedDir = Join-Path $RootPath 'Articals\\processed'
if (-not (Test-Path $processedDir)) { New-Item -ItemType Directory -Path $processedDir | Out-Null }

$txtPath = Join-Path $processedDir "$Slug.txt"
[System.IO.File]::WriteAllLines($txtPath, $paragraphs, [System.Text.Encoding]::UTF8)

function Escape-Html([string]$s) {
    return $s.Replace('&', '&amp;').Replace('<', '&lt;').Replace('>', '&gt;').Replace('"', '&quot;')
}

$bodyHtml = New-Object System.Collections.Generic.List[string]
foreach ($line in $bodyParagraphs) {
    $escaped = Escape-Html $line
    if ($escaped -match '^(أَوَّلًا|أولًا|ثَانِيًا|ثالثًا|ثَالِثًا|رَابِعًا|خامسًا|سادسًا|النَّصِيحَةُ|الجَانِبُ|مَشَاهِدُ|جَدْوَلُ).*[\:؟]?$') {
        $bodyHtml.Add("            <h2 class=\"section-title\">$escaped</h2>")
    } else {
        $bodyHtml.Add("            <p class=\"text-content\">$escaped</p>")
    }
}

$htmlPath = Join-Path $RootPath "books\\$Slug.html"

$html = @"
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="مقال بقلم فضيلة الشيخ أحمد إسماعيل الفشني.">
    <title>$title | مكتبة الشيخ أحمد</title>
    <meta property="og:type" content="article">
    <meta property="og:locale" content="ar_AR">
    <meta property="og:site_name" content="الشيخ أحمد إسماعيل الفشني">
    <meta property="og:title" content="$title | مكتبة الشيخ أحمد">
    <meta property="og:description" content="مقال بقلم فضيلة الشيخ أحمد إسماعيل الفشني.">
    <meta property="og:image" content="$ogImageUrl">
    <meta property="og:url" content="$pageUrl">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="$title | مكتبة الشيخ أحمد">
    <meta name="twitter:description" content="مقال بقلم فضيلة الشيخ أحمد إسماعيل الفشني.">
    <meta name="twitter:image" content="$ogImageUrl">
    <link rel="stylesheet" href="../style.css">
    <link href="https://fonts.googleapis.com/css2?family=Amiri:ital,wght@0,400;0,700;1,400&family=Aref+Ruqaa:wght@400;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        :root { --primary-color: #1a5f4a; --heading-font: 'Aref Ruqaa', serif; --body-font: 'Amiri', serif; }
        body { font-family: var(--body-font); background-color: #f5f5f5; color: #333; line-height: 1.9; margin: 0; padding: 0; }
        .book-header { background: linear-gradient(135deg, #1a5f4a, #2c3e50); color: white; padding: 4rem 2rem; text-align: center; }
        .book-title { font-family: var(--heading-font); font-size: 2.4rem; margin-bottom: .75rem; }
        .book-author { font-size: 1.2rem; opacity: 0.92; }
        .container { max-width: 900px; margin: -2rem auto 3rem; padding: 0 1.25rem; }
        .content-card { background: white; border-radius: 15px; padding: 2.25rem; box-shadow: 0 10px 30px rgba(0,0,0,0.08); }
        .text-content { font-size: 1.32rem; text-align: justify; margin-bottom: 1.25rem; }
        .section-title { font-family: var(--heading-font); font-size: 1.9rem; color: #1a5f4a; margin: 1.75rem 0 1rem; }
        .nav-button { display:inline-block; margin-top:1.5rem; padding:10px 24px; background:var(--primary-color); color:white; text-decoration:none; border-radius:25px; }
        @media (max-width: 768px) {
            .book-title { font-size: 1.8rem; }
            .content-card { padding: 1.4rem; }
            .text-content { font-size: 1.15rem; }
            .section-title { font-size: 1.6rem; }
        }
    </style>
</head>
<body>
    <header class="book-header">
        <h1 class="book-title">$title</h1>
        <div class="book-author">$Author</div>
        <a href="../articles.html" class="nav-button"><i class="fas fa-arrow-right"></i> عودة إلى المقالات</a>
    </header>

    <div class="container">
        <article class="content-card">
$(($bodyHtml -join "`r`n"))
            <p class="text-content">بِقَلَمِ فَضِيلَةِ الشَّيْخِ / أَحْمَدَ إِسْمَاعِيلَ الْفَشَنِيِّ</p>
        </article>
    </div>

    <script src="../pdf-export.js"></script>
</body>
</html>
"@

[System.IO.File]::WriteAllText($htmlPath, $html, [System.Text.Encoding]::UTF8)

$wordCount = (($bodyParagraphs -join ' ') -split '\s+' | Where-Object { $_ -ne '' }).Count
Write-Output "Generated HTML: $htmlPath"
Write-Output "Saved extracted TXT: $txtPath"
Write-Output "Approx words (body): $wordCount"
