param(
    [Parameter(Mandatory = $true)]
    [string]$DocxPath,

    [Parameter(Mandatory = $true)]
    [string]$Slug,

    [string]$RootPath = "m:\Sheikh Ahmed",
    [string]$Author = "&#1576;&#1602;&#1604;&#1605;: &#1601;&#1590;&#1610;&#1604;&#1577; &#1575;&#1604;&#1588;&#1610;&#1582; &#1571;&#1581;&#1605;&#1583; &#1573;&#1587;&#1605;&#1575;&#1593;&#1610;&#1604; &#1575;&#1604;&#1601;&#1588;&#1606;&#1610;",
    [string]$BaseUrl = "",
    [string]$TemplatePath = "templates/article-publishing/ramadan-article-template.html"
)

$ErrorActionPreference = 'Stop'

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

function Escape-Html([string]$s) {
    if ($null -eq $s) { return '' }
    return $s.Replace('&', '&amp;').Replace('<', '&lt;').Replace('>', '&gt;').Replace('"', '&quot;')
}

function Test-IsSectionTitle([string]$line) {
    $text = ($line | Out-String).Trim()
    if ([string]::IsNullOrWhiteSpace($text)) { return $false }

    if ($text.StartsWith('(') -and ($text.EndsWith(')') -or $text.EndsWith('):') -or $text.EndsWith(') :'))) {
        return $true
    }

    if ($text.Length -le 95 -and ($text.EndsWith(':') -or $text.EndsWith('؟') -or $text.EndsWith('!'))) {
        return $true
    }

    return $false
}

function Get-ArticleTitle {
    param([string[]]$Paragraphs)

    if ($null -eq $Paragraphs -or $Paragraphs.Count -eq 0) {
        return 'مقال'
    }

    $ignored = @(
        'مقال تحت عنوان',
        'مقال بعنوان',
        'عنوان المقال',
        'عنوان'
    )

    foreach ($line in $Paragraphs) {
        $candidate = ($line | Out-String).Trim()
        if ([string]::IsNullOrWhiteSpace($candidate)) { continue }
        if ($ignored -contains $candidate) { continue }
        return $candidate
    }

    return ($Paragraphs[0] | Out-String).Trim()
}

if (-not (Test-Path $DocxPath)) {
    throw "DOCX not found: $DocxPath"
}

$templateFullPath = $TemplatePath
if (-not [System.IO.Path]::IsPathRooted($TemplatePath)) {
    $templateFullPath = Join-Path $RootPath $TemplatePath
}
if (-not (Test-Path $templateFullPath)) {
    throw "Template file not found: $templateFullPath"
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

$title = Get-ArticleTitle -Paragraphs $paragraphs
$bodyStartIndex = 0
if ($paragraphs.Count -gt 0 -and (($paragraphs[0] | Out-String).Trim() -eq $title)) {
    $bodyStartIndex = 1
}

$bodyParagraphs = $paragraphs | Select-Object -Skip $bodyStartIndex
if ($bodyParagraphs.Count -lt 1) {
    throw "Body content empty; stopping."
}

$lastLine = ($bodyParagraphs[$bodyParagraphs.Count - 1] | Out-String).Trim()
$lastWordCount = (($lastLine -split '\s+' | Where-Object { $_ -ne '' }).Count)
if ($lastWordCount -le 6 -and $lastLine.Length -le 55) {
    $bodyParagraphs = $bodyParagraphs | Select-Object -SkipLast 1
}

$resolvedBaseUrl = Resolve-BaseUrl -root $RootPath -fallback $BaseUrl
$pageUrl = "$resolvedBaseUrl/books/$Slug.html"
$ogImageUrl = "$resolvedBaseUrl/assets/og/sheikh-ahmed-share.jpg"

$processedDir = Join-Path $RootPath 'Articals\\processed'
if (-not (Test-Path $processedDir)) { New-Item -ItemType Directory -Path $processedDir | Out-Null }

$txtPath = Join-Path $processedDir "$Slug.txt"
[System.IO.File]::WriteAllLines($txtPath, $paragraphs, [System.Text.Encoding]::UTF8)

$bodyHtml = New-Object System.Collections.Generic.List[string]
foreach ($line in $bodyParagraphs) {
    $escaped = Escape-Html $line
    if (Test-IsSectionTitle $line) {
        $bodyHtml.Add('            <h2 class="section-title">' + $escaped + '</h2>')
    } else {
        $bodyHtml.Add('            <p class="text-content">' + $escaped + '</p>')
    }
}

$desc = "&#1605;&#1602;&#1575;&#1604; &#1576;&#1602;&#1604;&#1605; &#1601;&#1590;&#1610;&#1604;&#1577; &#1575;&#1604;&#1588;&#1610;&#1582; &#1571;&#1581;&#1605;&#1583; &#1573;&#1587;&#1605;&#1575;&#1593;&#1610;&#1604; &#1575;&#1604;&#1601;&#1588;&#1606;&#1610;."
$backText = "&#1593;&#1608;&#1583;&#1577; &#1573;&#1604;&#1609; &#1575;&#1604;&#1605;&#1602;&#1575;&#1604;&#1575;&#1578;"

$template = [System.IO.File]::ReadAllText($templateFullPath, [System.Text.Encoding]::UTF8)
$tokens = @{
    '{{PAGE_TITLE}}' = (Escape-Html $title)
    '{{META_DESCRIPTION}}' = $desc
    '{{OG_TITLE}}' = (Escape-Html $title)
    '{{OG_DESCRIPTION}}' = $desc
    '{{OG_IMAGE}}' = (Escape-Html $ogImageUrl)
    '{{OG_URL}}' = (Escape-Html $pageUrl)
    '{{TWITTER_TITLE}}' = (Escape-Html $title)
    '{{TWITTER_DESCRIPTION}}' = $desc
    '{{TWITTER_IMAGE}}' = (Escape-Html $ogImageUrl)
    '{{AUTHOR}}' = $Author
    '{{BACK_TEXT}}' = $backText
    '{{BODY_HTML}}' = ($bodyHtml -join "`r`n")
    '{{AUTHOR_TAIL}}' = ''
}

$html = $template
foreach ($token in $tokens.Keys) {
    $html = $html.Replace($token, $tokens[$token])
}

$htmlPath = Join-Path $RootPath "books\\$Slug.html"
[System.IO.File]::WriteAllText($htmlPath, $html, [System.Text.Encoding]::UTF8)

$wordCount = (($bodyParagraphs -join ' ') -split '\s+' | Where-Object { $_ -ne '' }).Count
Write-Output "Generated HTML: $htmlPath"
Write-Output "Saved extracted TXT: $txtPath"
Write-Output "Approx words (body): $wordCount"
Write-Output "Template used: $templateFullPath"
