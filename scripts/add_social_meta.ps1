param(
    [string]$RootPath = "m:\Sheikh Ahmed",
    [string]$BaseUrl = "https://xgharibx.github.io/ImamAhmed",
    [string]$DefaultImage = "https://xgharibx.github.io/ImamAhmed/sheikh-photo.png",
    [string]$SiteName = "Sheikh Ahmed Ismail Al-Fashni"
)

$ErrorActionPreference = 'Stop'

function Get-MetaDescription {
    param([string]$html)

    $descMatch = [regex]::Match($html, '<meta\s+name="description"\s+content="([^"]*)"\s*/?>', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
    if ($descMatch.Success) {
        return $descMatch.Groups[1].Value.Trim()
    }
    return "Official website of Sheikh Ahmed Ismail Al-Fashni"
}

function Get-TitleText {
    param([string]$html)

    $titleMatch = [regex]::Match($html, '<title>(.*?)</title>', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase -bor [System.Text.RegularExpressions.RegexOptions]::Singleline)
    if ($titleMatch.Success) {
        return ($titleMatch.Groups[1].Value -replace '\s+', ' ').Trim()
    }
    return $SiteName
}

$files = Get-ChildItem -Path $RootPath -Filter '*.html' -File -Recurse
$updated = 0
$skipped = 0

foreach ($file in $files) {
    $content = Get-Content -Path $file.FullName -Raw -Encoding UTF8

    if ($content -match 'property="og:title"') {
        $skipped++
        continue
    }

    $title = Get-TitleText -html $content
    $description = Get-MetaDescription -html $content

    $relativePath = $file.FullName.Substring($RootPath.Length).TrimStart('\\') -replace '\\', '/'
    $fullUrl = "$BaseUrl/$relativePath"

    $metaBlock = @"
    <meta property="og:type" content="website">
    <meta property="og:locale" content="ar_AR">
    <meta property="og:site_name" content="$SiteName">
    <meta property="og:title" content="$title">
    <meta property="og:description" content="$description">
    <meta property="og:image" content="$DefaultImage">
    <meta property="og:url" content="$fullUrl">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="$title">
    <meta name="twitter:description" content="$description">
    <meta name="twitter:image" content="$DefaultImage">
"@

    $newContent = [regex]::Replace(
        $content,
        '</head>',
        "$metaBlock`r`n</head>",
        [System.Text.RegularExpressions.RegexOptions]::IgnoreCase
    )

    if ($newContent -ne $content) {
        Set-Content -Path $file.FullName -Value $newContent -Encoding UTF8
        $updated++
    }
}

Write-Output "Updated files: $updated"
Write-Output "Skipped files (already had OG tags): $skipped"
