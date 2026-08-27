$morganaDir = "C:\Users\ninoc\OfficeAddinApps\Camelot\morgana"
$readmePath = Join-Path $morganaDir "README.md"
$content = Get-Content -Path $readmePath -Raw

# Match links: [text](link)
$matches = [regex]::Matches($content, '\[([^\]]+)\]\(([^)]+)\)')
$relativeLinks = New-Object System.Collections.Generic.List[PSCustomObject]

foreach ($m in $matches) {
    $text = $m.Groups[1].Value
    $link = $m.Groups[2].Value
    # Skip web links and element fragments
    if ($link -notmatch '^(https?://|mailto:|#)') {
        # Check if the link contains a fragment we need to strip
        $rawLink = $link
        $fragment = ""
        if ($link -match '#') {
            $parts = $link -split '#'
            $rawLink = $parts[0]
            $fragment = $parts[1]
        }
        
        $resolvedPath = Join-Path $morganaDir $rawLink
        $exists = Test-Path $resolvedPath
        
        $relativeLinks.Add([PSCustomObject]@{
            Text = $text
            OriginalLink = $link
            CleanLinkPath = $rawLink
            ResolvedPath = $resolvedPath
            Exists = $exists
        })
    }
}

$relativeLinks | Format-Table -AutoSize
