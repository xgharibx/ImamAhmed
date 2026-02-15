param(
    [string]$RootPath = "m:\Sheikh Ahmed",
    [string]$BaseUrl = "",
    [string]$SiteName = "Sheikh Ahmed Ismail Al-Fashni"
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

function Ensure-LibrarySuffix {
    param([string]$title)

    $suffix = [string]::Concat(
        [char]0x0645, [char]0x0643, [char]0x062A, [char]0x0628, [char]0x0629,
        [char]0x0020,
        [char]0x0627, [char]0x0644, [char]0x0634, [char]0x064A, [char]0x062E,
        [char]0x0020,
        [char]0x0623, [char]0x062D, [char]0x0645, [char]0x062F
    )

    if ([string]::IsNullOrWhiteSpace($title)) {
        return $suffix
    }

    $baseTitle = ($title -split '\|')[0].Trim()
    return "$baseTitle | $suffix"
}

function Get-OgImageName {
    param([string]$relativePath)

    $name = $relativePath.ToLowerInvariant()
    if ($name -eq 'index.html') {
        return 'index.png'
    }

    $name = $name -replace '\.html$', ''
    $name = $name -replace '[^a-z0-9\-/]+', '-'
    $name = $name -replace '/+', '-'
    $name = $name -replace '-+', '-'
    $name = $name.Trim('-')

    if ([string]::IsNullOrWhiteSpace($name)) {
        return 'page.png'
    }

    return "$name.png"
}

$resolvedBaseUrl = Get-BaseUrl -root $RootPath -fallback $BaseUrl
$files = Get-ChildItem -Path $RootPath -Filter '*.html' -File -Recurse
$updated = 0

foreach ($file in $files) {
    $content = Get-Content -Path $file.FullName -Raw -Encoding UTF8

    $relativePath = $file.FullName.Substring($RootPath.Length).TrimStart('\\') -replace '\\', '/'
    $fullUrl = "$resolvedBaseUrl/$relativePath"
    $imageName = Get-OgImageName -relativePath $relativePath
    $imageUrl = "$resolvedBaseUrl/assets/og/$imageName"

    $resolvedTitle = Ensure-LibrarySuffix (Get-TitleText -html $content)
    $title = HtmlEscape $resolvedTitle
    $description = HtmlEscape (Get-MetaDescription -html $content)

    $cleaned = $content
    $cleaned = [regex]::Replace($cleaned, '<meta\s+property="og:[^"]+"\s+content="[^"]*"\s*/?>\r?\n?', '', 'IgnoreCase')
    $cleaned = [regex]::Replace($cleaned, '<meta\s+name="twitter:[^"]+"\s+content="[^"]*"\s*/?>\r?\n?', '', 'IgnoreCase')
    $cleaned = [regex]::Replace($cleaned, '<meta\s+property="twitter:[^"]+"\s+content="[^"]*"\s*/?>\r?\n?', '', 'IgnoreCase')

    $metaBlock = @"
    <meta property="og:type" content="website">
    <meta property="og:locale" content="ar_AR">
    <meta property="og:site_name" content="$SiteName">
    <meta property="og:title" content="$title">
    <meta property="og:description" content="$description">
    <meta property="og:image" content="$imageUrl">
    <meta property="og:image:width" content="1200">
    <meta property="og:image:height" content="630">
    <meta property="og:url" content="$fullUrl">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="$title">
    <meta name="twitter:description" content="$description">
    <meta name="twitter:image" content="$imageUrl">
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
