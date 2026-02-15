param(
    [string]$RootPath = "m:\Sheikh Ahmed",
    [string]$BaseUrl = "",
    [string]$OutputDir = "assets\og"
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing

function Get-BaseUrl {
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
    return "Sheikh Ahmed Ismail Al-Fashni"
}

function Get-OgImageName {
    param([string]$relativePath)

    $name = $relativePath.ToLowerInvariant()
    if ($name -eq 'index.html') { return 'index.png' }

    $name = $name -replace '\.html$', ''
    $name = $name -replace '[^a-z0-9\-/]+', '-'
    $name = $name -replace '/+', '-'
    $name = $name -replace '-+', '-'
    $name = $name.Trim('-')

    if ([string]::IsNullOrWhiteSpace($name)) { return 'page.png' }
    return "$name.png"
}

function Draw-WrappedText {
    param(
        [System.Drawing.Graphics]$Graphics,
        [string]$Text,
        [System.Drawing.Font]$Font,
        [System.Drawing.Brush]$Brush,
        [float]$X,
        [float]$Y,
        [float]$MaxWidth,
        [float]$LineHeight,
        [int]$MaxLines,
        [System.Drawing.StringFormat]$Format
    )

    $words = $Text -split '\s+'
    $line = ''
    $lines = New-Object System.Collections.Generic.List[string]

    foreach ($word in $words) {
        $candidate = if ([string]::IsNullOrWhiteSpace($line)) { $word } else { "$line $word" }
        $size = $Graphics.MeasureString($candidate, $Font, [int]$MaxWidth, $Format)

        if ($size.Width -le $MaxWidth -or [string]::IsNullOrWhiteSpace($line)) {
            $line = $candidate
        } else {
            $lines.Add($line)
            $line = $word
            if ($lines.Count -ge $MaxLines) { break }
        }
    }

    if ($lines.Count -lt $MaxLines -and -not [string]::IsNullOrWhiteSpace($line)) {
        $lines.Add($line)
    }

    if ($lines.Count -gt $MaxLines) {
        $lines = $lines.GetRange(0, $MaxLines)
    }

    if ($lines.Count -eq $MaxLines) {
        $last = $lines[$MaxLines - 1]
        if ($last.Length -gt 3) { $lines[$MaxLines - 1] = "$last..." }
    }

    for ($i = 0; $i -lt $lines.Count; $i++) {
        $Graphics.DrawString($lines[$i], $Font, $Brush, [System.Drawing.PointF]::new($X, $Y + ($i * $LineHeight)), $Format)
    }
}

$resolvedBaseUrl = Get-BaseUrl -root $RootPath -fallback $BaseUrl
$outputPath = Join-Path $RootPath $OutputDir
if (-not (Test-Path $outputPath)) {
    New-Item -ItemType Directory -Path $outputPath | Out-Null
}

$backgroundPath = Join-Path $RootPath 'sheikh-photo.png'
$hasBackground = Test-Path $backgroundPath

$files = Get-ChildItem -Path $RootPath -Filter '*.html' -File -Recurse
$generated = 0

foreach ($file in $files) {
    $html = Get-Content -Path $file.FullName -Raw -Encoding UTF8
    $title = Get-TitleText -html $html
    $relativePath = $file.FullName.Substring($RootPath.Length).TrimStart('\\') -replace '\\', '/'
    $fullUrl = "$resolvedBaseUrl/$relativePath"

    $imageName = Get-OgImageName -relativePath $relativePath
    $targetImage = Join-Path $outputPath $imageName

    $width = 1200
    $height = 630
    $bitmap = New-Object System.Drawing.Bitmap($width, $height)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
    $graphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit

    if ($hasBackground) {
        $bg = [System.Drawing.Image]::FromFile($backgroundPath)
        $scale = [Math]::Max($width / $bg.Width, $height / $bg.Height)
        $drawW = [int]($bg.Width * $scale)
        $drawH = [int]($bg.Height * $scale)
        $drawX = [int](($width - $drawW) / 2)
        $drawY = [int](($height - $drawH) / 2)
        $graphics.DrawImage($bg, $drawX, $drawY, $drawW, $drawH)
        $bg.Dispose()
    } else {
        $brush = New-Object System.Drawing.Drawing2D.LinearGradientBrush(
            ([System.Drawing.Rectangle]::new(0, 0, $width, $height)),
            ([System.Drawing.Color]::FromArgb(255, 26, 95, 74)),
            ([System.Drawing.Color]::FromArgb(255, 44, 62, 80)),
            45
        )
        $graphics.FillRectangle($brush, 0, 0, $width, $height)
        $brush.Dispose()
    }

    $overlay = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(150, 0, 0, 0))
    $graphics.FillRectangle($overlay, 0, 0, $width, $height)
    $overlay.Dispose()

    $panelBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(185, 255, 255, 255))
    $graphics.FillRectangle($panelBrush, 60, 70, 1080, 490)
    $panelBrush.Dispose()

    $accentBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(255, 26, 95, 74))
    $graphics.FillRectangle($accentBrush, 60, 70, 1080, 16)
    $accentBrush.Dispose()

    $titleFont = New-Object System.Drawing.Font('Tahoma', 42, [System.Drawing.FontStyle]::Bold)
    $metaFont = New-Object System.Drawing.Font('Tahoma', 20, [System.Drawing.FontStyle]::Regular)
    $urlFont = New-Object System.Drawing.Font('Consolas', 16, [System.Drawing.FontStyle]::Regular)

    $titleBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(255, 20, 40, 35))
    $subBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(255, 26, 95, 74))
    $urlBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(255, 60, 60, 60))

    $rtl = New-Object System.Drawing.StringFormat
    $rtl.Alignment = [System.Drawing.StringAlignment]::Far
    $rtl.FormatFlags = [System.Drawing.StringFormatFlags]::DirectionRightToLeft

    $ltr = New-Object System.Drawing.StringFormat
    $ltr.Alignment = [System.Drawing.StringAlignment]::Near

    Draw-WrappedText -Graphics $graphics -Text $title -Font $titleFont -Brush $titleBrush -X 100 -Y 120 -MaxWidth 1000 -LineHeight 62 -MaxLines 4 -Format $rtl

    $graphics.DrawString('Official Website | Sheikh Ahmed Ismail Al-Fashni', $metaFont, $subBrush, [System.Drawing.PointF]::new(1040, 410), $rtl)
    $graphics.DrawString($fullUrl, $urlFont, $urlBrush, [System.Drawing.PointF]::new(90, 500), $ltr)

    $titleFont.Dispose()
    $metaFont.Dispose()
    $urlFont.Dispose()
    $titleBrush.Dispose()
    $subBrush.Dispose()
    $urlBrush.Dispose()
    $rtl.Dispose()
    $ltr.Dispose()

    $bitmap.Save($targetImage, [System.Drawing.Imaging.ImageFormat]::Png)
    $graphics.Dispose()
    $bitmap.Dispose()

    $generated++
}

Write-Output "Base URL: $resolvedBaseUrl"
Write-Output "Generated thumbnails: $generated"
Write-Output "Output directory: $outputPath"
