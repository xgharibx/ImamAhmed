param(
    [string]$RootPath = "m:\Sheikh Ahmed",
    [string]$BaseUrl = "",
    [string]$SiteName = "Sheikh Ahmed Ismail Al-Fashni",
    [string]$DefaultImagePath = "assets/og/sheikh-ahmed-share.jpg"
)

$ErrorActionPreference = 'Stop'

function Get-BaseUrl {
    param([string]$root, [string]$fallback)

    if (-not [string]::IsNullOrWhiteSpace($fallback)) {
        return $fallback.TrimEnd('/')
    }

    $cnamePath = Join-Path $root 'CNAME'
    if (Test-Path $cnamePath) {
        $domain = (Get-Content -Path $cnamePath -Raw -Encoding UTF8).Trim()
        if ($domain) {
            return "https://$domain"
        }
    }

    return "https://xgharibx.github.io/ImamAhmed"
}

function HtmlEscape {
    param([string]$text)

    if ($null -eq $text) { return '' }
    return $text.Replace('&', '&amp;').Replace('"', '&quot;').Replace('<', '&lt;').Replace('>', '&gt;')
}

function Get-MetaDescription {
    param([string]$html)

    $descMatch = [regex]::Match(
        $html,
        '<meta\s+name="description"\s+content="([^"]*)"\s*/?>',
        [System.Text.RegularExpressions.RegexOptions]::IgnoreCase
    )
    if ($descMatch.Success) {
        return $descMatch.Groups[1].Value.Trim()
    }
    return "Official website of Sheikh Ahmed Ismail Al-Fashni"
}

function Get-TitleText {
    param([string]$html)

    $titleMatch = [regex]::Match(
        $html,
        '<title>(.*?)</title>',
        [System.Text.RegularExpressions.RegexOptions]::IgnoreCase -bor [System.Text.RegularExpressions.RegexOptions]::Singleline
    )
    if ($titleMatch.Success) {
        return ($titleMatch.Groups[1].Value -replace '\s+', ' ').Trim()
    }
    return $SiteName
}

function Normalize-ShareTitle {
    param([string]$title)

    if ([string]::IsNullOrWhiteSpace($title)) {
        return 'Sheikh Ahmed Ismail Al-Fashni'
    }

    return ($title -split '\|')[0].Trim()
}

$resolvedBaseUrl = Get-BaseUrl -root $RootPath -fallback $BaseUrl
$cleanDefaultImagePath = $DefaultImagePath.TrimStart('/').Replace('\\', '/')
$sharedImageUrl = "$resolvedBaseUrl/$cleanDefaultImagePath"
$files = Get-ChildItem -Path $RootPath -Filter '*.html' -File -Recurse
$updated = 0

foreach ($file in $files) {
    $content = Get-Content -Path $file.FullName -Raw -Encoding UTF8

    $relativePath = $file.FullName.Substring($RootPath.Length).TrimStart('\\') -replace '\\', '/'
    $fullUrl = "$resolvedBaseUrl/$relativePath"

    $resolvedTitle = Normalize-ShareTitle (Get-TitleText -html $content)
    $title = HtmlEscape $resolvedTitle
    $description = HtmlEscape (Get-MetaDescription -html $content)

    $cleaned = $content
    $cleaned = [regex]::Replace($cleaned, '<meta\s+property="og:[^"]+"\s+content="[^"]*"\s*/?>\r?\n?', '', 'IgnoreCase')
    $cleaned = [regex]::Replace($cleaned, '<meta\s+name="twitter:[^"]+"\s+content="[^"]*"\s*/?>\r?\n?', '', 'IgnoreCase')
    $cleaned = [regex]::Replace($cleaned, '<meta\s+property="twitter:[^"]+"\s+content="[^"]*"\s*/?>\r?\n?', '', 'IgnoreCase')

    $metaBlock = @"
    <meta property="og:type" content="article">
    <meta property="og:locale" content="ar_AR">
    <meta property="og:site_name" content="$SiteName">
    <meta property="og:title" content="$title">
    <meta property="og:description" content="$description">
    <meta property="og:image" content="$sharedImageUrl">
    <meta property="og:image:url" content="$sharedImageUrl">
    <meta property="og:image:width" content="1200">
    <meta property="og:image:height" content="630">
    <meta property="og:image:type" content="image/jpeg">
    <meta property="og:image:secure_url" content="$sharedImageUrl">
    <meta property="og:url" content="$fullUrl">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="$title">
    <meta name="twitter:description" content="$description">
    <meta name="twitter:image" content="$sharedImageUrl">
"@

    $newContent = [regex]::Replace(
        $cleaned,
        '</head>',
        "$metaBlock`r`n</head>",
        [System.Text.RegularExpressions.RegexOptions]::IgnoreCase
    )

    if ($newContent -ne $content) {
        Set-Content -Path $file.FullName -Value $newContent -Encoding UTF8
        $updated++
    }
}

Write-Output "Base URL: $resolvedBaseUrl"
Write-Output "Updated files: $updated"
