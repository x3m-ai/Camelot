$rootReadme = "C:\Users\ninoc\OfficeAddinApps\Camelot\README.md"
$morganaReadme = "C:\Users\ninoc\OfficeAddinApps\Camelot\morgana\README.md"
$morganaDir = "C:\Users\ninoc\OfficeAddinApps\Camelot\morgana"

# 1. ROOT LINK OK
$ROOT_LINK_OK = "NO"
if (Test-Path $rootReadme) {
    if (Test-Path $morganaReadme) {
        $rootContent = Get-Content -Path $rootReadme -Raw
        # Search for links containing morgana/README.md or morgana\README.md
        if ($rootContent -match '\[([^\]]+)\]\(([^)]*morgana[/\\]README\.md[^)]*)\)') {
            $ROOT_LINK_OK = "YES"
        }
    }
}

# 2. Extract relative links from morgana\README.md
$relative_links_count = 0
$broken_links_count = 0
$broken_links_list = New-Object System.Collections.Generic.List[string]

if (Test-Path $morganaReadme) {
    $content = Get-Content -Path $morganaReadme -Raw
    # Retrieve all markdown link destinations: [text](dest)
    $matches = [regex]::Matches($content, '\[([^\]]+)\]\(([^)]+)\)')
    foreach ($m in $matches) {
        $dest = $m.Groups[2].Value
        # Skip http, https, mailto, and fragment-only links
        if ($dest -notmatch '^(https?://|mailto:|#)') {
            $relative_links_count++
            # Strip fragment
            $cleanDest = ($dest -split '#')[0].Trim()
            # If path has spaces encoded as %20, decode them
            $cleanDest = [Uri]::UnescapeDataString($cleanDest)
            
            # Resolve relative to morgana directory
            $resolvedPath = Join-Path $morganaDir $cleanDest
            
            if (-not (Test-Path $resolvedPath)) {
                $broken_links_count++
                $broken_links_list.Add("BROKEN_LINK: $dest (Resolved: $resolvedPath)")
            }
        }
    }
}

# 3. Heading validation (hierarchy and duplicates)
$headings_count = 0
$hierarchy_issues = 0
$duplicate_anchors = 0
$headings_list = New-Object System.Collections.Generic.List[PSCustomObject]
$slugs = @{}

if (Test-Path $morganaReadme) {
    $lines = Get-Content -Path $morganaReadme
    $prevLevel = 0
    foreach ($line in $lines) {
        if ($line -match '^(\s*)(#+)\s+(.*)$') {
            $level = $matches[2].Length
            $title = $matches[3].Trim()
            $headings_count++
            
            # Hierarchy issues (can't skip depth by > 1, e.g. level 1 to level 3)
            # A leap of more than 1 from prevLevel is a hierarchy issue, unless prevLevel is 0 or decreasing (going up)
            if ($prevLevel -gt 0 -and $level -gt ($prevLevel + 1)) {
                $hierarchy_issues++
                Write-Host "Hierarchy issue: leaped from L$prevLevel to L$level at '$title'"
            }
            $prevLevel = $level
            
            # GitHub slug generation
            # 1. Convert to lowercase
            # 2. Replace spaces/underscores with hyphens
            # 3. Strip everything else except alphanumeric, hyphen, underscore
            # 4. Handle duplicates by appending -1, -2, etc. and tracking original
            $slug = $title.ToLower()
            $slug = $slug -replace '[^\w\s-]', ''  # remove non-word/space/hyphen (punctuation etc)
            $slug = $slug -replace '[\s_]+', '-'   # replace spaces and underscores with hyphens
            $slug = $slug -replace '-+', '-'       # trim multiple hyphens
            $slug = $slug.Trim('-')
            
            # Check unique slug
            if ($slugs.ContainsKey($slug)) {
                $duplicate_anchors++
                # GitHub style: duplicate slug becomes slug-1, slug-2, etc.
                $count = $slugs[$slug]
                $count++
                $slugs[$slug] = $count
                $uniqueSlug = "$slug-$count"
                $slugs[$uniqueSlug] = 1
                Write-Host "Duplicate anchor found for: '$title' -> original slug: '$slug', auto-resolved as: '$uniqueSlug'"
            } else {
                $slugs[$slug] = 1
            }
        }
    }
}

# 4. SUSPICIOUS MATCHES SEARCH
# Let's search inside the entire C:\Users\ninoc\OfficeAddinApps\Camelot folder
$suspicious_count = 0

# Patterns:
# - TODO
# - FIXME
# - C:\Users
# - OfficeAddinApps
# - literal default/bootstrap password (we'll check config/scripts/READMEs for terms like bootstrap_password, default_password, default password, password_default etc.)
# - API-key mrg_ followed by 32+ hex characters: mrg_[0-9a-fA-F]{32,}
# - GitHub-token-like: ghp_[0-9a-zA-Z]{36}
# - AWS Access Key: AKIA[0-9A-Z]{16}
# - phrase 'Refresh Canary Scripts'
# - instruction to clone/index Atomic Red Team natively (e.g. "Atomic Red Team", "invoke-atomicredteam", "clon" / "native" etc. Let's do a direct phrase check)

$all_files = Get-ChildItem -Path "C:\Users\ninoc\OfficeAddinApps\Camelot" -Recurse -File
foreach ($file in $all_files) {
    $filePath = $file.FullName
    # Skip binary files or current script
    if ($filePath -match '\.(png|jpg|exe|zip|tar|gz|xlsx|docx|pdf|ico|dll)$') { continue }
    
    $fileContent = Get-Content -Path $filePath -Raw
    if ($null -eq $fileContent) { continue }
    
    # Run Regex matches
    # TODO
    $matchesTodo = [regex]::Matches($fileContent, '(?i)\b(TODO|FIXME)\b')
    if ($matchesTodo.Count -gt 0) {
        $suspicious_count += $matchesTodo.Count
        Write-Host "File $filePath matched TODO/FIXME count: $($matchesTodo.Count)"
    }
    
    # C:\Users
    $matchesUsers = [regex]::Matches($fileContent, '(?i)C:\\Users')
    # Filter out current standard references or the specific scan target itself if it's stored in code, but count them if requested.
    # The prompt says "Search and report any matches for TODO, FIXME, C:\Users, OfficeAddinApps"
    if ($matchesUsers.Count -gt 0) {
        $suspicious_count += $matchesUsers.Count
        Write-Host "File $filePath matched C:\Users count: $($matchesUsers.Count)"
    }
    
    # OfficeAddinApps
    $matchesOAA = [regex]::Matches($fileContent, '(?i)OfficeAddinApps')
    if ($matchesOAA.Count -gt 0) {
        $suspicious_count += $matchesOAA.Count
        Write-Host "File $filePath matched OfficeAddinApps count: $($matchesOAA.Count)"
    }
    
    # mrg_ followed by 32+ hex
    $matchesMrg = [regex]::Matches($fileContent, 'mrg_[0-9a-fA-F]{32,}')
    if ($matchesMrg.Count -gt 0) {
        $suspicious_count += $matchesMrg.Count
        Write-Host "File $filePath matched mrg_ API key count: $($matchesMrg.Count)"
    }
    
    # ghp_
    $matchesGhp = [regex]::Matches($fileContent, 'ghp_[0-9a-zA-Z]{36,40}')
    if ($matchesGhp.Count -gt 0) {
        $suspicious_count += $matchesGhp.Count
        Write-Host "File $filePath matched GitHub token count: $($matchesGhp.Count)"
    }
    
    # AWS AKIA
    $matchesAws = [regex]::Matches($fileContent, 'AKIA[0-9A-Z]{16}')
    if ($matchesAws.Count -gt 0) {
        $suspicious_count += $matchesAws.Count
        Write-Host "File $filePath matched AWS Key count: $($matchesAws.Count)"
    }
    
    # Refresh Canary Scripts
    $matchesCanary = [regex]::Matches($fileContent, '(?i)Refresh Canary Scripts')
    if ($matchesCanary.Count -gt 0) {
        $suspicious_count += $matchesCanary.Count
        Write-Host "File $filePath matched 'Refresh Canary Scripts' count: $($matchesCanary.Count)"
    }
    
    # clone/index Atomic Red Team natively
    # Let's search for atomicredteam or atomic red team clone natively instructions.
    # We will look for "Atomic Red Team" or specific instructions. Let's do a case-insensitive match on "Atomic Red Team". Or "clone.*Atomic Red Team". Let's run matches on both.
    $matchesAtomic = [regex]::Matches($fileContent, '(?i)clone.*Atomic Red Team|index.*Atomic Red Team')
    if ($matchesAtomic.Count -gt 0) {
        $suspicious_count += $matchesAtomic.Count
        Write-Host "File $filePath matched Atomic Red Team Native instruction count: $($matchesAtomic.Count)"
    }
    
    # Let's look for default passwords in code or readme
    # e.g. "password" or typical bootstrap values
    # Let's search for specific common password keys like "bootstrap_password_value", or we can do manual check if we find any.
    $matchesPws = [regex]::Matches($fileContent, '(?i)(bootstrap_password|default_password|bootstrap password)\b')
    if ($matchesPws.Count -gt 0) {
        $suspicious_count += $matchesPws.Count
        Write-Host "File $filePath matched password keyword count: $($matchesPws.Count)"
    }
}

Write-Host "`n--- DETAIL SUMMARY ---"
$broken_links_list | ForEach-Object { Write-Host $_ }

Write-Host "`n--- FINAL COMPACT SUMMARY ---"
Write-Host "RELATIVE_LINKS: $relative_links_count"
Write-Host "BROKEN_LINKS: $broken_links_count"
Write-Host "HEADINGS: $headings_count"
Write-Host "HIERARCHY_ISSUES: $hierarchy_issues"
Write-Host "DUPLICATE_ANCHORS: $duplicate_anchors"
Write-Host "SUSPICIOUS_MATCHES: $suspicious_count"
Write-Host "ROOT_LINK_OK: $ROOT_LINK_OK"
