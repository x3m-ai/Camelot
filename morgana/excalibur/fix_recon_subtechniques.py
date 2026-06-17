"""
fix_recon_subtechniques.py
Rewrites all placeholder sub-technique scripts in excalibur-reconnaissance-emulation-pack.json
with real, meaningful adversary emulation PowerShell scripts.
Run from the excalibur/ directory.
"""
import json
import sys

FILENAME = "excalibur-reconnaissance-emulation-pack.json"

# ---------------------------------------------------------------------------
# Script definitions: tcode -> (description, required_tags, command, cleanup, detection_rule)
# ---------------------------------------------------------------------------
SCRIPTS = {

# ── T1596.004 fix only missing fields (command already present) ──────────────
"T1596.004": {
    "fix_only": True,
    "cleanup_command": "Write-Host '[INFO] T1596.004 cleanup: no artefacts created - network connections only'",
    "detection_rule": "CDN IP range detection + CDN-specific HTTP header analysis from non-browser process (T1596.004 pattern)",
},

# ── T1596.005 ─────────────────────────────────────────────────────────────────
"T1596.005": {
    "description": (
        "Simulates querying open scan databases (Shodan/Censys/GreyNoise-style) from a foothold machine (T1596.005). "
        "Queries ipinfo.io, Shodan InternetDB API, and GreyNoise community API to retrieve known open ports, "
        "vulnerabilities, and threat classifications for the target domain's IPs. "
        "Generates MDE outbound telemetry to these known threat-intel infrastructure endpoints."
    ),
    "required_tags": ["excalibur_recon_target_domain"],
    "command": r"""Write-Host '[START] T1596.005 - Scan Databases (Shodan/Censys/GreyNoise open scan DB recon)'
$domain = '#{excalibur_recon_target_domain}'
$ua = 'MorganaTest-T1596.005-ScanDB/1.0'

# Resolve domain to IPs first
Write-Host '[INFO] Resolving target IPs for scan database lookup...'
$targetIPs = @()
try {
    $ips = [System.Net.Dns]::GetHostAddresses($domain) | Select-Object -ExpandProperty IPAddressToString
    $targetIPs = $ips | Where-Object { $_ -notmatch ':' }  # IPv4 only
    Write-Host ('[INFO] ' + $domain + ' -> ' + ($targetIPs -join ', '))
} catch {
    Write-Host ('[INFO] DNS resolution: ' + $_.Exception.Message.Split([char]10)[0])
    $targetIPs = @('8.8.8.8')  # fallback for telemetry generation
}

foreach ($ip in $targetIPs | Select-Object -First 3) {
    Write-Host ('[INFO] Querying scan databases for: ' + $ip)

    # Shodan InternetDB (free, no API key required)
    Write-Host '[INFO] Step 1/3: Shodan InternetDB query...'
    try {
        $shodanResp = Invoke-WebRequest -Uri ('https://internetdb.shodan.io/' + $ip) `
            -Headers @{'User-Agent'=$ua; 'Accept'='application/json'} `
            -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
        $shodanData = $shodanResp.Content | ConvertFrom-Json
        Write-Host ('[INFO] Shodan InternetDB - ' + $ip + ':')
        if ($shodanData.ports) { Write-Host ('    Open ports: ' + ($shodanData.ports -join ', ')) }
        if ($shodanData.vulns) { Write-Host ('    CVEs: ' + ($shodanData.vulns -join ', ')) }
        if ($shodanData.tags)  { Write-Host ('    Tags: ' + ($shodanData.tags -join ', ')) }
        if ($shodanData.hostnames) { Write-Host ('    Hostnames: ' + ($shodanData.hostnames -join ', ')) }
    } catch {
        Write-Host ('[INFO] Shodan InternetDB: ' + $_.Exception.Message.Split([char]10)[0])
    }

    # GreyNoise Community API (free)
    Write-Host '[INFO] Step 2/3: GreyNoise community threat classification...'
    try {
        $gnResp = Invoke-WebRequest -Uri ('https://api.greynoise.io/v3/community/' + $ip) `
            -Headers @{'User-Agent'=$ua; 'Accept'='application/json'; 'key'='MorganaSimKey-NotReal'} `
            -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
        $gnData = $gnResp.Content | ConvertFrom-Json
        Write-Host ('[INFO] GreyNoise: ' + $ip + ' classified as: ' + $gnData.classification + ' | noise=' + $gnData.noise + ' | riot=' + $gnData.riot)
    } catch {
        Write-Host ('[INFO] GreyNoise: ' + $_.Exception.Message.Split([char]10)[0])
    }

    # ipinfo.io full detail
    Write-Host '[INFO] Step 3/3: ipinfo.io detailed IP intelligence...'
    try {
        $ipinfoResp = Invoke-WebRequest -Uri ('https://ipinfo.io/' + $ip + '/json') `
            -Headers @{'User-Agent'=$ua} `
            -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
        $ipData = $ipinfoResp.Content | ConvertFrom-Json
        Write-Host ('[INFO] ipinfo: ' + $ip + ' | org=' + $ipData.org + ' | asn=' + $ipData.asn + ' | country=' + $ipData.country + ' | city=' + $ipData.city)
    } catch {
        Write-Host ('[INFO] ipinfo: ' + $_.Exception.Message.Split([char]10)[0])
    }
}
Write-Host '[SUCCESS] T1596.005 emulation completed'""",
    "cleanup_command": "Write-Host '[INFO] T1596.005 cleanup: no artefacts created - HTTP queries only'",
    "detection_rule": "Outbound queries to Shodan InternetDB + GreyNoise + ipinfo.io from non-browser process (T1596.005 pattern)",
},

# ── T1593.001 ─────────────────────────────────────────────────────────────────
"T1593.001": {
    "description": (
        "Simulates social media OSINT reconnaissance from a foothold machine (T1593.001). "
        "Constructs and queries LinkedIn, Twitter/X, and Facebook OSINT URLs for the target organization. "
        "Searches for employee profiles, executive names, and technology stack mentions. "
        "Also queries Hunter.io-style API pattern for email format discovery. "
        "Generates MDE outbound telemetry to social media and OSINT infrastructure."
    ),
    "required_tags": ["excalibur_recon_target_domain"],
    "command": r"""Write-Host '[START] T1593.001 - Social Media OSINT (LinkedIn/Twitter/Facebook employee recon)'
$domain = '#{excalibur_recon_target_domain}'
$orgName = $domain -replace '\.[^.]+$','' -replace '\.',''
$ua = 'MorganaTest-T1593.001-SocialMediaRecon/1.0'

# LinkedIn company and employee search (URL pattern - generates outbound telemetry)
Write-Host '[INFO] Step 1/4: LinkedIn company and employee enumeration...'
$linkedInUrls = @(
    'https://www.linkedin.com/company/' + $orgName,
    'https://www.linkedin.com/search/results/people/?keywords=' + $domain + '&origin=GLOBAL_SEARCH_HEADER',
    'https://www.linkedin.com/search/results/people/?facetCurrentCompany=' + $orgName + '&facetTitle=CEO',
    'https://www.linkedin.com/search/results/people/?facetCurrentCompany=' + $orgName + '&facetTitle=CISO'
)
foreach ($url in $linkedInUrls) {
    try {
        $req = [System.Net.WebRequest]::Create($url)
        $req.Timeout = 3000
        $req.Method = 'HEAD'
        $req.Headers.Add('User-Agent', $ua)
        $resp = $req.GetResponse()
        Write-Host ('[INFO] LinkedIn reachable: ' + $url.Substring(0,[Math]::Min(80,$url.Length)) + ' (' + [int]$resp.StatusCode + ')')
        $resp.Close()
    } catch [System.Net.WebException] {
        $sc = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { 0 }
        Write-Host ('[INFO] LinkedIn: ' + $url.Substring(0,[Math]::Min(80,$url.Length)) + ' -> HTTP ' + $sc)
    } catch { Write-Host ('[INFO] LinkedIn: ' + $url.Substring(0,60) + ' -> ' + $_.Exception.Message.Split([char]10)[0]) }
}

# Twitter/X search pattern
Write-Host '[INFO] Step 2/4: Twitter/X organization search...'
$twitterUrls = @(
    'https://twitter.com/search?q=' + [System.Uri]::EscapeDataString($domain),
    'https://x.com/search?q=' + [System.Uri]::EscapeDataString('from:' + $orgName + ' filter:links')
)
foreach ($url in $twitterUrls) {
    try {
        $req = [System.Net.WebRequest]::Create($url); $req.Timeout = 3000; $req.Method = 'HEAD'
        $req.Headers.Add('User-Agent', $ua)
        $resp = $req.GetResponse(); Write-Host ('[INFO] Twitter/X: ' + $url.Substring(0,60) + ' -> ' + [int]$resp.StatusCode); $resp.Close()
    } catch [System.Net.WebException] { Write-Host ('[INFO] Twitter/X: HTTP ' + $(if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { 'ERR' })) } catch {}
}

# Hunter.io email format discovery (OSINT for email enumeration pattern)
Write-Host '[INFO] Step 3/4: Hunter.io email format discovery...'
try {
    $hunterResp = Invoke-WebRequest -Uri ('https://api.hunter.io/v2/domain-search?domain=' + $domain + '&api_key=MorganaSimKey') `
        -Headers @{'User-Agent'=$ua} -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
    $hunterData = $hunterResp.Content | ConvertFrom-Json
    if ($hunterData.data) {
        Write-Host ('[INFO] Hunter.io: email pattern=' + $hunterData.data.pattern + ' | emails found=' + @($hunterData.data.emails).Count)
    }
} catch { Write-Host ('[INFO] Hunter.io: ' + $_.Exception.Message.Split([char]10)[0] + ' (outbound to Hunter.io logged by MDE)') }

# Facebook/Instagram org presence check
Write-Host '[INFO] Step 4/4: Facebook/Instagram organization presence...'
try {
    $fbUrl = 'https://www.facebook.com/' + $orgName
    $req = [System.Net.WebRequest]::Create($fbUrl); $req.Timeout = 3000; $req.Method = 'HEAD'
    $req.Headers.Add('User-Agent', $ua)
    $resp = $req.GetResponse(); Write-Host ('[INFO] Facebook: ' + $fbUrl + ' -> ' + [int]$resp.StatusCode); $resp.Close()
} catch [System.Net.WebException] { Write-Host ('[INFO] Facebook: HTTP ' + $(if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { 'ERR' })) } catch {}
Write-Host '[SUCCESS] T1593.001 emulation completed'""",
    "cleanup_command": "Write-Host '[INFO] T1593.001 cleanup: no artefacts created - HTTP queries only'",
    "detection_rule": "Outbound queries to LinkedIn/Twitter/Hunter.io/Facebook from non-browser process (T1593.001 social media OSINT pattern)",
},

# ── T1593.002 ─────────────────────────────────────────────────────────────────
"T1593.002": {
    "description": (
        "Simulates search engine OSINT (Google dorking) from a foothold machine (T1593.002). "
        "Constructs Google/Bing dork queries targeting the victim domain: filetype:pdf/xls/doc, "
        "site:pastebin.com, inurl:admin, intitle:login, site:github.com password. "
        "Queries Bing Search API pattern and DuckDuckGo for dork results. "
        "Generates MDE outbound telemetry characteristic of search engine reconnaissance."
    ),
    "required_tags": ["excalibur_recon_target_domain"],
    "command": r"""Write-Host '[START] T1593.002 - Search Engine OSINT (Google dorking + Bing recon)'
$domain = '#{excalibur_recon_target_domain}'
$ua = 'MorganaTest-T1593.002-SearchEngineRecon/1.0'

# Google dork query patterns adversaries use
$dorks = @(
    'site:' + $domain + ' filetype:pdf',
    'site:' + $domain + ' filetype:xls OR filetype:xlsx',
    'site:' + $domain + ' filetype:doc OR filetype:docx',
    'site:' + $domain + ' inurl:admin OR inurl:login OR inurl:portal',
    'site:' + $domain + ' intitle:"index of"',
    'site:pastebin.com ' + $domain,
    'site:github.com ' + $domain + ' password OR secret OR apikey',
    'site:' + $domain + ' ext:config OR ext:env OR ext:bak',
    '"@' + $domain + '" filetype:pdf',
    'site:' + $domain + ' "powered by" OR "built with"'
)

Write-Host '[INFO] Executing Google dork queries via Bing Search...'
foreach ($dork in $dorks) {
    $encodedDork = [System.Uri]::EscapeDataString($dork)
    $bingUrl = 'https://www.bing.com/search?q=' + $encodedDork + '&count=10'
    try {
        $req = [System.Net.WebRequest]::Create($bingUrl)
        $req.Timeout = 3000
        $req.Method = 'GET'
        $req.Headers.Add('User-Agent', $ua)
        $resp = $req.GetResponse()
        $stream = $resp.GetResponseStream()
        $reader = New-Object System.IO.StreamReader($stream)
        $content = $reader.ReadToEnd()
        $resultCount = ([regex]::Matches($content, '<li class="b_algo"')).Count
        Write-Host ('[INFO] Dork [' + $dork.Substring(0,[Math]::Min(60,$dork.Length)) + '] -> ~' + $resultCount + ' results')
        $resp.Close()
    } catch [System.Net.WebException] {
        $sc = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { 0 }
        Write-Host ('[INFO] Bing dork: ' + $dork.Substring(0,[Math]::Min(50,$dork.Length)) + ' -> HTTP ' + $sc)
    } catch { Write-Host ('[INFO] Bing dork: ' + $dork.Substring(0,40) + ' -> ' + $_.Exception.Message.Split([char]10)[0]) }
}

# DuckDuckGo instant answers API
Write-Host '[INFO] DuckDuckGo instant answer query...'
try {
    $ddgResp = Invoke-WebRequest -Uri ('https://api.duckduckgo.com/?q=' + [System.Uri]::EscapeDataString($domain) + '&format=json&no_redirect=1') `
        -Headers @{'User-Agent'=$ua} -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
    $ddgData = $ddgResp.Content | ConvertFrom-Json
    if ($ddgData.AbstractText) { Write-Host ('[INFO] DDG: ' + $ddgData.AbstractText.Substring(0,[Math]::Min(200,$ddgData.AbstractText.Length))) }
    if ($ddgData.RelatedTopics) { Write-Host ('[INFO] DDG related topics: ' + @($ddgData.RelatedTopics).Count) }
} catch { Write-Host ('[INFO] DuckDuckGo: ' + $_.Exception.Message.Split([char]10)[0]) }

Write-Host '[SUCCESS] T1593.002 emulation completed'""",
    "cleanup_command": "Write-Host '[INFO] T1593.002 cleanup: no artefacts created - HTTP queries only'",
    "detection_rule": "Bing/DuckDuckGo dorking queries (site:, filetype:, inurl:, pastebin, github password) from non-browser process (T1593.002 pattern)",
},

# ── T1593.003 ─────────────────────────────────────────────────────────────────
"T1593.003": {
    "description": (
        "Simulates code repository OSINT from a foothold machine (T1593.003). "
        "Queries GitHub search API and GitLab for repositories, gists, and code containing the target "
        "domain, email addresses, API keys, passwords, and internal hostnames. "
        "Also checks npm registry and PyPI for packages potentially leaking internal code. "
        "Generates MDE outbound telemetry to GitHub/GitLab API endpoints characteristic of credential exposure recon."
    ),
    "required_tags": ["excalibur_recon_target_domain"],
    "command": r"""Write-Host '[START] T1593.003 - Code Repositories (GitHub/GitLab credential exposure recon)'
$domain = '#{excalibur_recon_target_domain}'
$ua = 'MorganaTest-T1593.003-CodeRepoRecon/1.0'

# GitHub code search - adversaries look for leaked creds/config
$searchTerms = @(
    $domain,
    ($domain -replace '\.[^.]+$','') + ' password',
    ($domain -replace '\.[^.]+$','') + ' api_key',
    ($domain -replace '\.[^.]+$','') + ' secret',
    ($domain -replace '\.[^.]+$','') + ' smtp',
    ($domain -replace '\.[^.]+$','') + ' connection_string',
    'smtp.office365.com ' + ($domain -replace '\.[^.]+$','')
)

Write-Host '[INFO] Querying GitHub search API for credential exposure...'
foreach ($term in $searchTerms) {
    try {
        $encoded = [System.Uri]::EscapeDataString($term)
        $ghUrl = 'https://api.github.com/search/code?q=' + $encoded + '&per_page=3'
        $resp = Invoke-WebRequest -Uri $ghUrl `
            -Headers @{'User-Agent'=$ua; 'Accept'='application/vnd.github.v3+json'} `
            -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
        $ghData = $resp.Content | ConvertFrom-Json
        Write-Host ('[INFO] GitHub code search [' + $term.Substring(0,[Math]::Min(50,$term.Length)) + ']: ' + $ghData.total_count + ' results')
        if ($ghData.items) {
            $ghData.items | Select-Object -First 2 | ForEach-Object {
                Write-Host ('    Repo: ' + $_.repository.full_name + ' | File: ' + $_.name)
            }
        }
    } catch { Write-Host ('[INFO] GitHub: ' + $term.Substring(0,40) + ' -> ' + $_.Exception.Message.Split([char]10)[0]) }
}

# GitHub repository search for org
Write-Host '[INFO] Querying GitHub for organization repositories...'
$orgName = $domain -replace '\.[^.]+$',''
try {
    $orgResp = Invoke-WebRequest -Uri ('https://api.github.com/search/repositories?q=org:' + $orgName + '&per_page=5') `
        -Headers @{'User-Agent'=$ua; 'Accept'='application/vnd.github.v3+json'} `
        -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
    $orgData = $orgResp.Content | ConvertFrom-Json
    Write-Host ('[INFO] GitHub org repos: ' + $orgData.total_count + ' public repositories')
    if ($orgData.items) {
        $orgData.items | Select-Object -First 3 | ForEach-Object {
            Write-Host ('    ' + $_.full_name + ' | stars=' + $_.stargazers_count + ' | lang=' + $_.language)
        }
    }
} catch { Write-Host ('[INFO] GitHub org: ' + $_.Exception.Message.Split([char]10)[0]) }

# GitLab search
Write-Host '[INFO] Querying GitLab for project exposure...'
try {
    $glResp = Invoke-WebRequest -Uri ('https://gitlab.com/api/v4/projects?search=' + $orgName + '&per_page=5') `
        -Headers @{'User-Agent'=$ua; 'Accept'='application/json'} `
        -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
    $glData = $glResp.Content | ConvertFrom-Json
    Write-Host ('[INFO] GitLab: ' + @($glData).Count + ' projects found')
    $glData | Select-Object -First 3 | ForEach-Object { Write-Host ('    ' + $_.path_with_namespace + ' | visibility=' + $_.visibility) }
} catch { Write-Host ('[INFO] GitLab: ' + $_.Exception.Message.Split([char]10)[0]) }

# npm registry check for internal package names
Write-Host '[INFO] Checking npm registry for potential internal package exposure...'
try {
    $npmResp = Invoke-WebRequest -Uri ('https://registry.npmjs.org/-/v1/search?text=' + $orgName + '&size=5') `
        -Headers @{'User-Agent'=$ua} -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
    $npmData = $npmResp.Content | ConvertFrom-Json
    Write-Host ('[INFO] npm: ' + $npmData.total + ' packages matching org name')
    if ($npmData.objects) { $npmData.objects | Select-Object -First 3 | ForEach-Object { Write-Host ('    npm: ' + $_.package.name + ' v' + $_.package.version) } }
} catch { Write-Host ('[INFO] npm: ' + $_.Exception.Message.Split([char]10)[0]) }

Write-Host '[SUCCESS] T1593.003 emulation completed'""",
    "cleanup_command": "Write-Host '[INFO] T1593.003 cleanup: no artefacts created - HTTP queries only'",
    "detection_rule": "GitHub API code search + GitLab + npm registry queries from non-browser process (T1593.003 credential exposure recon pattern)",
},

# ── T1597.001 ─────────────────────────────────────────────────────────────────
"T1597.001": {
    "description": (
        "Simulates querying commercial threat intelligence platforms from a foothold machine (T1597.001). "
        "Queries VirusTotal, AbuseIPDB, AlienVault OTX, and URLVoid for the target domain's threat reputation, "
        "malware associations, and prior compromise indicators. Adversaries use these to understand if the "
        "target is monitored, what security vendors are covering it, and to identify any prior incidents. "
        "Generates MDE outbound telemetry to threat intel APIs."
    ),
    "required_tags": ["excalibur_recon_target_domain"],
    "command": r"""Write-Host '[START] T1597.001 - Threat Intelligence Platform Recon (VirusTotal/OTX/AbuseIPDB)'
$domain = '#{excalibur_recon_target_domain}'
$ua = 'MorganaTest-T1597.001-ThreatIntelRecon/1.0'

# VirusTotal domain report (simulated API call pattern)
Write-Host '[INFO] Step 1/4: VirusTotal domain reputation lookup...'
try {
    $vtResp = Invoke-WebRequest -Uri ('https://www.virustotal.com/api/v3/domains/' + $domain) `
        -Headers @{'User-Agent'=$ua; 'x-apikey'='MorganaSimKey-NotReal'; 'Accept'='application/json'} `
        -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
    $vtData = $vtResp.Content | ConvertFrom-Json
    if ($vtData.data.attributes) {
        $stats = $vtData.data.attributes.last_analysis_stats
        Write-Host ('[INFO] VT: malicious=' + $stats.malicious + ' suspicious=' + $stats.suspicious + ' harmless=' + $stats.harmless)
    }
} catch { Write-Host ('[INFO] VirusTotal: ' + $_.Exception.Message.Split([char]10)[0] + ' (outbound to VT logged by MDE)') }

# AlienVault OTX domain pulse check
Write-Host '[INFO] Step 2/4: AlienVault OTX threat pulse check...'
try {
    $otxResp = Invoke-WebRequest -Uri ('https://otx.alienvault.com/api/v1/indicators/domain/' + $domain + '/general') `
        -Headers @{'User-Agent'=$ua; 'X-OTX-API-KEY'='MorganaSimKey-NotReal'} `
        -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
    $otxData = $otxResp.Content | ConvertFrom-Json
    Write-Host ('[INFO] OTX: pulse_count=' + $otxData.pulse_info.count + ' | reputation=' + $otxData.reputation)
} catch { Write-Host ('[INFO] OTX: ' + $_.Exception.Message.Split([char]10)[0]) }

# Resolve domain IPs and check AbuseIPDB
Write-Host '[INFO] Step 3/4: AbuseIPDB IP reputation check...'
try {
    $ips = [System.Net.Dns]::GetHostAddresses($domain) | Where-Object { $_.AddressFamily -eq 'InterNetwork' } | Select-Object -ExpandProperty IPAddressToString
    foreach ($ip in $ips | Select-Object -First 2) {
        try {
            $abuseResp = Invoke-WebRequest -Uri ('https://api.abuseipdb.com/api/v2/check?ipAddress=' + $ip + '&maxAgeInDays=90') `
                -Headers @{'User-Agent'=$ua; 'Key'='MorganaSimKey-NotReal'; 'Accept'='application/json'} `
                -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
            $abuseData = $abuseResp.Content | ConvertFrom-Json
            Write-Host ('[INFO] AbuseIPDB: ' + $ip + ' | score=' + $abuseData.data.abuseConfidenceScore + '% | reports=' + $abuseData.data.totalReports)
        } catch { Write-Host ('[INFO] AbuseIPDB ' + $ip + ': ' + $_.Exception.Message.Split([char]10)[0]) }
    }
} catch { Write-Host ('[INFO] IP resolution: ' + $_.Exception.Message.Split([char]10)[0]) }

# URLVoid domain reputation
Write-Host '[INFO] Step 4/4: URLVoid multi-engine domain reputation...'
try {
    $uvResp = Invoke-WebRequest -Uri ('https://www.urlvoid.com/scan/' + $domain + '/') `
        -Headers @{'User-Agent'=$ua} -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
    $detected = ([regex]::Matches($uvResp.Content, 'label-danger')).Count
    $clean = ([regex]::Matches($uvResp.Content, 'label-success')).Count
    Write-Host ('[INFO] URLVoid: ' + $domain + ' | engines flagging=' + $detected + ' | clean=' + $clean)
} catch { Write-Host ('[INFO] URLVoid: ' + $_.Exception.Message.Split([char]10)[0]) }

Write-Host '[SUCCESS] T1597.001 emulation completed'""",
    "cleanup_command": "Write-Host '[INFO] T1597.001 cleanup: no artefacts created - HTTP queries only'",
    "detection_rule": "Outbound queries to VirusTotal/OTX/AbuseIPDB/URLVoid threat intel APIs from non-browser process (T1597.001 pattern)",
},

# ── T1597.002 ─────────────────────────────────────────────────────────────────
"T1597.002": {
    "description": (
        "Simulates adversary purchasing or querying sold/leaked technical data from a foothold machine (T1597.002). "
        "Queries data broker APIs (Dehashed, Snusbase pattern), dark web aggregator APIs, and leaked credential "
        "databases for the target domain. Also searches Pastebin and similar paste sites for exposed internal data. "
        "Generates MDE outbound telemetry to breach data aggregator endpoints."
    ),
    "required_tags": ["excalibur_recon_email_domain"],
    "command": r"""Write-Host '[START] T1597.002 - Purchase Technical Data (breach database + paste site recon)'
$emailDomain = '#{excalibur_recon_email_domain}'
$ua = 'MorganaTest-T1597.002-PurchasedDataRecon/1.0'

# DeHashed API pattern (aggregates breach data)
Write-Host '[INFO] Step 1/4: DeHashed breach data aggregator query...'
try {
    $dhHeaders = @{
        'User-Agent' = $ua
        'Accept' = 'application/json'
        'Authorization' = 'Basic ' + [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes('admin@' + $emailDomain + ':MorganaSimKey'))
    }
    $dhResp = Invoke-WebRequest -Uri ('https://api.dehashed.com/search?query=' + [System.Uri]::EscapeDataString('domain:' + $emailDomain) + '&size=5') `
        -Headers $dhHeaders -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
    $dhData = $dhResp.Content | ConvertFrom-Json
    Write-Host ('[INFO] DeHashed: ' + $dhData.total + ' breached entries for domain ' + $emailDomain)
    if ($dhData.entries) {
        $dhData.entries | Select-Object -First 3 | ForEach-Object {
            Write-Host ('    Entry: email=' + $_.email + ' | source=' + $_.database_name + ' | hashed_password=' + $(if ($_.hashed_password) { 'YES' } else { 'NO' }))
        }
    }
} catch { Write-Host ('[INFO] DeHashed: ' + $_.Exception.Message.Split([char]10)[0] + ' (outbound to DeHashed logged by MDE)') }

# Snusbase-style query (sold breach database)
Write-Host '[INFO] Step 2/4: Snusbase breach database query pattern...'
try {
    $snResp = Invoke-WebRequest -Uri 'https://api.snusbase.com/data/search' `
        -Method POST `
        -Headers @{'User-Agent'=$ua; 'Auth'='MorganaSimKey'; 'Content-Type'='application/json'} `
        -Body ('{"terms":["' + $emailDomain + '"],"types":["email"],"wildcard":false}') `
        -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
    $snData = $snResp.Content | ConvertFrom-Json
    Write-Host ('[INFO] Snusbase: ' + $snData.size + ' results for ' + $emailDomain)
} catch { Write-Host ('[INFO] Snusbase: ' + $_.Exception.Message.Split([char]10)[0]) }

# Pastebin search for domain data
Write-Host '[INFO] Step 3/4: Paste site search for leaked data...'
$pasteSites = @(
    'https://psbdmp.ws/api/search/' + $emailDomain,
    'https://pastebin.com/search?q=' + $emailDomain
)
foreach ($url in $pasteSites) {
    try {
        $req = [System.Net.WebRequest]::Create($url); $req.Timeout = 3000; $req.Method = 'GET'
        $req.Headers.Add('User-Agent', $ua)
        $resp = $req.GetResponse()
        $content = (New-Object System.IO.StreamReader($resp.GetResponseStream())).ReadToEnd()
        Write-Host ('[INFO] Paste search: ' + $url.Substring(0,60) + ' -> ' + $content.Length + ' bytes')
        $resp.Close()
    } catch { Write-Host ('[INFO] Paste: ' + $url.Substring(0,50) + ' -> ' + $_.Exception.Message.Split([char]10)[0]) }
}

# Intelligence X / leaked database search pattern
Write-Host '[INFO] Step 4/4: IntelligenceX leaked data search...'
try {
    $ixResp = Invoke-WebRequest -Uri 'https://2.intelx.io/intelligent/search' `
        -Method POST `
        -Headers @{'User-Agent'=$ua; 'x-key'='MorganaSimKey'; 'Content-Type'='application/json'} `
        -Body ('{"term":"' + $emailDomain + '","buckets":[],"lookuplevel":0,"maxresults":5,"timeout":5,"datefrom":"","dateto":"","sort":4,"media":0,"terminate":[]}') `
        -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
    Write-Host ('[INFO] IntelX: search initiated for ' + $emailDomain)
} catch { Write-Host ('[INFO] IntelligenceX: ' + $_.Exception.Message.Split([char]10)[0]) }

Write-Host '[SUCCESS] T1597.002 emulation completed'""",
    "cleanup_command": "Write-Host '[INFO] T1597.002 cleanup: no artefacts created - HTTP queries only'",
    "detection_rule": "Outbound queries to DeHashed/Snusbase/IntelligenceX breach data APIs from non-browser process (T1597.002 pattern)",
},

# ── T1598.001 ─────────────────────────────────────────────────────────────────
"T1598.001": {
    "description": (
        "Simulates spearphishing reconnaissance via messaging services from a foothold machine (T1598.001). "
        "Enumerates collaboration/messaging services (Teams, Slack, Zoom, Webex) installed and configured on "
        "the host: process list, config files, registry keys, cached tokens. Identifies which services are in "
        "use and maps targets for future spearphishing via service messaging. Also enumerates Teams tenant "
        "ID and user list endpoints. Read-only."
    ),
    "required_tags": [],
    "command": r"""Write-Host '[START] T1598.001 - Spearphishing via Service (messaging platform enumeration)'

# Enumerate installed messaging/collaboration clients
Write-Host '[INFO] Step 1/4: Installed messaging clients...'
$messagingApps = @(
    @{Name='Microsoft Teams'; Process='Teams'; ConfigPath=($env:APPDATA + '\Microsoft\Teams'); RegKey='HKCU:\SOFTWARE\Microsoft\Office\Teams'},
    @{Name='Slack'; Process='slack'; ConfigPath=($env:APPDATA + '\Slack'); RegKey='HKCU:\SOFTWARE\Slack Technologies\Slack'},
    @{Name='Zoom'; Process='Zoom'; ConfigPath=($env:APPDATA + '\Zoom'); RegKey='HKCU:\SOFTWARE\Zoom'},
    @{Name='Webex'; Process='CiscoWebExStart'; ConfigPath=($env:LOCALAPPDATA + '\WebEx'); RegKey='HKCU:\SOFTWARE\Cisco Systems\Cisco Webex Meetings'},
    @{Name='Discord'; Process='Discord'; ConfigPath=($env:APPDATA + '\discord'); RegKey='HKCU:\SOFTWARE\discord'},
    @{Name='Skype'; Process='Skype'; ConfigPath=($env:APPDATA + '\Skype'); RegKey='HKCU:\SOFTWARE\Skype'}
)
foreach ($app in $messagingApps) {
    $installed = Test-Path $app.ConfigPath
    $running = @(Get-Process -Name $app.Process -ErrorAction SilentlyContinue).Count -gt 0
    $regExists = Test-Path $app.RegKey -ErrorAction SilentlyContinue
    Write-Host ('[INFO] ' + $app.Name + ': installed=' + $installed + ' running=' + $running + ' registry=' + $regExists)
    if ($installed) {
        $configSize = (Get-ChildItem $app.ConfigPath -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
        Write-Host ('    Config size: ' + [math]::Round($configSize/1MB, 1) + ' MB in ' + $app.ConfigPath)
    }
}

# Teams-specific: enumerate tenant ID and signed-in accounts
Write-Host '[INFO] Step 2/4: Microsoft Teams tenant and account enumeration...'
$teamsAcctPath = Join-Path $env:APPDATA 'Microsoft\Teams\Accounts'
if (Test-Path $teamsAcctPath) {
    Get-ChildItem $teamsAcctPath -Filter '*.json' -ErrorAction SilentlyContinue | Select-Object -First 3 | ForEach-Object {
        try {
            $acctData = Get-Content $_.FullName -Raw | ConvertFrom-Json
            Write-Host ('    Teams account: ' + $acctData.preferredUsername + ' | tenant: ' + $acctData.tenantId + ' | env: ' + $acctData.environment)
        } catch { Write-Host ('    Teams config file: ' + $_.Name) }
    }
} else { Write-Host '    Teams accounts directory not found' }

# Slack workspace enumeration
Write-Host '[INFO] Step 3/4: Slack workspace configuration...'
$slackConfigPath = Join-Path $env:APPDATA 'Slack\storage'
if (Test-Path $slackConfigPath) {
    $slackFiles = Get-ChildItem $slackConfigPath -ErrorAction SilentlyContinue | Where-Object { $_.Name -match 'slack-workspaces|team' }
    Write-Host ('    Slack config files: ' + @($slackFiles).Count)
    $slackFiles | Select-Object -First 2 | ForEach-Object { Write-Host ('    ' + $_.Name + ' (' + $_.Length + ' bytes)') }
} else { Write-Host '    Slack config not found' }

# Enumerate running communication processes and network connections
Write-Host '[INFO] Step 4/4: Active messaging service network connections...'
try {
    $commProcesses = @('Teams','slack','zoom','webex','discord','skype')
    foreach ($proc in $commProcesses) {
        $ps = Get-Process -Name $proc -ErrorAction SilentlyContinue
        if ($ps) {
            Write-Host ('[INFO] Active: ' + $proc + ' | PID=' + ($ps | Select-Object -First 1).Id + ' | version=' + ($ps | Select-Object -First 1).FileVersion)
        }
    }
} catch {}
Write-Host '[SUCCESS] T1598.001 emulation completed'""",
    "cleanup_command": "Write-Host '[INFO] T1598.001 cleanup: no artefacts created - read-only enumeration'",
    "detection_rule": "Messaging client config file access + Teams account JSON read + Slack workspace enum from non-browser process (T1598.001 pattern)",
},

# ── T1598.002 ─────────────────────────────────────────────────────────────────
"T1598.002": {
    "description": (
        "Simulates spearphishing attachment reconnaissance from a foothold machine (T1598.002). "
        "Enumerates recent email attachments received by the user (Outlook attachment cache, "
        "Downloads folder for macro-enabled documents, recent Office file MRU list). "
        "Identifies file types commonly used in phishing (xlsm, docm, xlsb, ppam, hta, iso, img, lnk). "
        "Maps the organization's document handling patterns to craft convincing attachments. Read-only."
    ),
    "required_tags": [],
    "command": r"""Write-Host '[START] T1598.002 - Spearphishing Attachment Recon (attachment surface mapping)'

# Enumerate Downloads folder for received files
Write-Host '[INFO] Step 1/4: Downloads folder - recently received files...'
$downloadsPath = Join-Path $env:USERPROFILE 'Downloads'
if (Test-Path $downloadsPath) {
    $recentFiles = Get-ChildItem $downloadsPath -Recurse -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -gt (Get-Date).AddDays(-30) -and -not $_.PSIsContainer } |
        Sort-Object LastWriteTime -Descending | Select-Object -First 20
    Write-Host ('[INFO] Files downloaded last 30 days: ' + @($recentFiles).Count)
    $phishingExt = @('.xlsm','.docm','.xlsb','.ppam','.hta','.iso','.img','.lnk','.vbs','.js','.jse','.wsf','.wsh','.ps1','.bat','.cmd')
    $suspicious = $recentFiles | Where-Object { $phishingExt -contains $_.Extension.ToLower() }
    Write-Host ('[INFO] Phishing-relevant file types found: ' + @($suspicious).Count)
    $suspicious | Select-Object -First 5 | ForEach-Object { Write-Host ('    [SUSPICIOUS] ' + $_.Name + ' (' + $_.Extension + ') - ' + $_.LastWriteTime) }
    $recentFiles | Select-Object -First 10 | ForEach-Object { Write-Host ('    ' + $_.Name + ' (' + [math]::Round($_.Length/1KB,1) + ' KB) - ' + $_.LastWriteTime) }
}

# Outlook attachment cache enumeration
Write-Host '[INFO] Step 2/4: Outlook attachment temporary cache...'
$outlookCachePath = Join-Path $env:LOCALAPPDATA 'Microsoft\Windows\INetCache\Content.Outlook'
if (Test-Path $outlookCachePath) {
    $cachedAttachments = Get-ChildItem $outlookCachePath -Recurse -ErrorAction SilentlyContinue |
        Where-Object { -not $_.PSIsContainer } | Sort-Object LastWriteTime -Descending | Select-Object -First 15
    Write-Host ('[INFO] Outlook cached attachments: ' + @($cachedAttachments).Count)
    $cachedAttachments | Select-Object -First 8 | ForEach-Object { Write-Host ('    ' + $_.Name + ' (' + $_.Extension + ')') }
}

# Office MRU (Most Recently Used) documents
Write-Host '[INFO] Step 3/4: Office MRU - recently opened documents...'
$officeApps = @('Word','Excel','PowerPoint')
foreach ($app in $officeApps) {
    $mruPath = "HKCU:\SOFTWARE\Microsoft\Office\16.0\$app\File MRU"
    if (Test-Path $mruPath -ErrorAction SilentlyContinue) {
        $mruItems = Get-ItemProperty $mruPath -ErrorAction SilentlyContinue
        $files = $mruItems.PSObject.Properties | Where-Object { $_.Name -match '^Item \d+' } | Select-Object -First 5
        Write-Host ('[INFO] ' + $app + ' MRU: ' + @($files).Count + ' recent files')
        $files | ForEach-Object { Write-Host ('    ' + ($_.Value -split '\]')[-1].Trim()) }
    }
}

# Email client - identify which client is in use
Write-Host '[INFO] Step 4/4: Email client identification...'
$emailClients = @(
    @{Name='Outlook'; Path=($env:LOCALAPPDATA + '\Microsoft\Outlook'); Process='OUTLOOK'},
    @{Name='Thunderbird'; Path=($env:APPDATA + '\Thunderbird'); Process='thunderbird'},
    @{Name='Windows Mail (UWP)'; Path=($env:LOCALAPPDATA + '\Comms\Unistore\data'); Process='HxOutlook'}
)
foreach ($client in $emailClients) {
    $exists = Test-Path $client.Path
    $running = @(Get-Process -Name $client.Process -ErrorAction SilentlyContinue).Count -gt 0
    if ($exists -or $running) {
        Write-Host ('[INFO] Email client found: ' + $client.Name + ' | running=' + $running + ' | data path exists=' + $exists)
    }
}
Write-Host '[SUCCESS] T1598.002 emulation completed'""",
    "cleanup_command": "Write-Host '[INFO] T1598.002 cleanup: no artefacts created - read-only enumeration'",
    "detection_rule": "Downloads folder + Outlook cache + Office MRU access enumerating received documents and attachment patterns (T1598.002 pattern)",
},

# ── T1598.003 ─────────────────────────────────────────────────────────────────
"T1598.003": {
    "description": (
        "Simulates spearphishing link reconnaissance from a foothold machine (T1598.003). "
        "Enumerates browser history (Edge/Chrome SQLite Login Data + History DB) to identify "
        "frequently visited internal and external URLs. Maps the organization's web application "
        "landscape and authentication pages (SSO, ADFS, Azure AD login, VPN portals) to craft "
        "convincing phishing links. Also checks URL filtering/proxy categories. Read-only."
    ),
    "required_tags": [],
    "command": r"""Write-Host '[START] T1598.003 - Spearphishing Link Recon (browser history + URL surface mapping)'

# Enumerate browser history databases
Write-Host '[INFO] Step 1/4: Browser history database enumeration...'
$browserHistoryPaths = @(
    @{Browser='Chrome'; Path=Join-Path $env:LOCALAPPDATA 'Google\Chrome\User Data\Default\History'},
    @{Browser='Edge'; Path=Join-Path $env:LOCALAPPDATA 'Microsoft\Edge\User Data\Default\History'},
    @{Browser='Chrome Profile 1'; Path=Join-Path $env:LOCALAPPDATA 'Google\Chrome\User Data\Profile 1\History'},
    @{Browser='Edge Work Profile'; Path=Join-Path $env:LOCALAPPDATA 'Microsoft\Edge\User Data\Profile 1\History'},
    @{Browser='Brave'; Path=Join-Path $env:LOCALAPPDATA 'BraveSoftware\Brave-Browser\User Data\Default\History'}
)
foreach ($bh in $browserHistoryPaths) {
    $exists = Test-Path $bh.Path
    if ($exists) {
        $size = (Get-Item $bh.Path).Length
        Write-Host ('[INFO] FOUND: ' + $bh.Browser + ' history DB at ' + $bh.Path + ' (' + [math]::Round($size/1KB,1) + ' KB)')
    }
}

# Read Edge/Chrome history via file copy (non-locking read)
Write-Host '[INFO] Step 2/4: Reading browser history URLs (copy-read method)...'
$edgeHistory = Join-Path $env:LOCALAPPDATA 'Microsoft\Edge\User Data\Default\History'
if (Test-Path $edgeHistory) {
    try {
        $tempHistory = Join-Path $env:TEMP ('MorganaHistorySnap_' + (Get-Date -Format 'HHmmss') + '.db')
        Copy-Item $edgeHistory $tempHistory -Force -ErrorAction Stop
        # Use .NET SQLite-style read (byte-level pattern matching for URL strings)
        $bytes = [System.IO.File]::ReadAllBytes($tempHistory)
        $text = [System.Text.Encoding]::UTF8.GetString($bytes)
        $urls = [regex]::Matches($text, 'https?://[a-zA-Z0-9\-._~:/?#\[\]@!$&''()*+,;=%]{10,150}') |
            Select-Object -ExpandProperty Value | Sort-Object -Unique | Select-Object -First 20
        Write-Host ('[INFO] Edge history URLs found: ' + @($urls).Count)
        $urls | ForEach-Object { Write-Host ('    ' + $_.Substring(0,[Math]::Min(100,$_.Length))) }
        Remove-Item $tempHistory -Force -ErrorAction SilentlyContinue
    } catch { Write-Host ('[INFO] Edge history read: ' + $_.Exception.Message.Split([char]10)[0]) }
}

# Identify SSO/authentication URLs visited (high-value phishing targets)
Write-Host '[INFO] Step 3/4: Authentication/SSO URL identification...'
$authPatterns = @(
    @{Pattern='login.microsoftonline.com'; Label='Azure AD / M365 Login'},
    @{Pattern='adfs'; Label='ADFS Federated Login'},
    @{Pattern='okta.com'; Label='Okta SSO'},
    @{Pattern='ping'; Label='PingIdentity SSO'},
    @{Pattern='sso'; Label='Generic SSO Portal'},
    @{Pattern='vpn'; Label='VPN Portal'},
    @{Pattern='webmail'; Label='Webmail'},
    @{Pattern='owa'; Label='Outlook Web Access'}
)
# Check browser bookmarks for auth URLs
$edgeBookmarks = Join-Path $env:LOCALAPPDATA 'Microsoft\Edge\User Data\Default\Bookmarks'
if (Test-Path $edgeBookmarks) {
    try {
        $bookmarkContent = Get-Content $edgeBookmarks -Raw
        Write-Host '[INFO] Edge bookmarks:'
        foreach ($ap in $authPatterns) {
            if ($bookmarkContent -match $ap.Pattern) {
                Write-Host ('    FOUND in bookmarks: ' + $ap.Label + ' (' + $ap.Pattern + ')')
            }
        }
    } catch {}
}

# Check IE/Edge typed URLs from registry
Write-Host '[INFO] Step 4/4: Registry typed URLs (HKCU Internet Explorer)...'
try {
    $typedUrls = Get-ItemProperty 'HKCU:\SOFTWARE\Microsoft\Internet Explorer\TypedURLs' -ErrorAction SilentlyContinue
    if ($typedUrls) {
        $urls = $typedUrls.PSObject.Properties | Where-Object { $_.Name -match '^url' } | Select-Object -First 10
        Write-Host ('[INFO] IE/Edge typed URLs: ' + @($urls).Count)
        $urls | ForEach-Object { Write-Host ('    ' + $_.Value) }
    }
} catch {}
Write-Host '[SUCCESS] T1598.003 emulation completed'""",
    "cleanup_command": "Remove-Item (Join-Path $env:TEMP 'MorganaHistorySnap_*.db') -ErrorAction SilentlyContinue; Write-Host '[INFO] T1598.003 cleanup: temp history snapshot removed'",
    "detection_rule": "Browser History SQLite DB access + bookmark file read + IE typed URLs registry access (T1598.003 spearphishing link recon pattern)",
},

# ── T1598.004 ─────────────────────────────────────────────────────────────────
"T1598.004": {
    "description": (
        "Simulates spearphishing voice (vishing) reconnaissance from a foothold machine (T1598.004). "
        "Enumerates VoIP/telephony configuration on the host: Teams phone system config, Skype for Business "
        "settings, direct inward dial numbers from AD user objects, Cisco Webex telephony config, "
        "and PBX/softphone registry keys. Maps phone numbers and extensions to AD accounts for "
        "targeted vishing campaigns. Read-only."
    ),
    "required_tags": [],
    "command": r"""Write-Host '[START] T1598.004 - Spearphishing Voice Recon (VoIP/telephony surface mapping)'

# Teams phone system configuration
Write-Host '[INFO] Step 1/5: Microsoft Teams Phone System configuration...'
$teamsConfigPaths = @(
    (Join-Path $env:APPDATA 'Microsoft\Teams\desktop-config.json'),
    (Join-Path $env:APPDATA 'Microsoft\Teams\settings.json')
)
foreach ($tp in $teamsConfigPaths) {
    if (Test-Path $tp) {
        try {
            $config = Get-Content $tp -Raw | ConvertFrom-Json -ErrorAction SilentlyContinue
            Write-Host ('[INFO] Teams config: ' + $tp)
            if ($config.currentWebLanguage) { Write-Host ('    Language: ' + $config.currentWebLanguage) }
            if ($config.geoLocale) { Write-Host ('    Geo locale: ' + $config.geoLocale) }
        } catch { Write-Host ('    Config file exists: ' + (Get-Item $tp).Length + ' bytes') }
    }
}

# AD user phone attributes (if domain-joined)
Write-Host '[INFO] Step 2/5: Active Directory user phone number enumeration...'
try {
    $adSearcher = New-Object System.DirectoryServices.DirectorySearcher
    $adSearcher.Filter = '(&(objectClass=user)(telephoneNumber=*))'
    $adSearcher.PropertiesToLoad.AddRange(@('cn','telephoneNumber','mobile','ipPhone','mail','department')) | Out-Null
    $adSearcher.SizeLimit = 20
    $results = $adSearcher.FindAll()
    Write-Host ('[INFO] AD users with phone numbers: ' + $results.Count)
    $results | Select-Object -First 10 | ForEach-Object {
        $p = $_.Properties
        Write-Host ('    ' + $p['cn'][0] + ' | tel=' + $p['telephoneNumber'][0] + $(if ($p['mobile'].Count -gt 0) { ' | mobile=' + $p['mobile'][0] } else { '' }) + $(if ($p['department'].Count -gt 0) { ' | dept=' + $p['department'][0] } else { '' }))
    }
} catch { Write-Host ('[INFO] AD phone enum: ' + $_.Exception.Message.Split([char]10)[0] + ' (workgroup or AD not reachable)') }

# Skype for Business / Lync configuration
Write-Host '[INFO] Step 3/5: Skype for Business / Lync telephony config...'
$sfbPaths = @(
    'HKCU:\SOFTWARE\Microsoft\Office\16.0\Lync',
    'HKCU:\SOFTWARE\Microsoft\Communicator'
)
foreach ($regPath in $sfbPaths) {
    if (Test-Path $regPath -ErrorAction SilentlyContinue) {
        try {
            $sfbConfig = Get-ItemProperty $regPath -ErrorAction SilentlyContinue
            Write-Host ('[INFO] SfB/Lync registry: ' + $regPath)
            if ($sfbConfig.ServerAddress) { Write-Host ('    Server: ' + $sfbConfig.ServerAddress) }
            if ($sfbConfig.SignInName) { Write-Host ('    Sign-in: ' + $sfbConfig.SignInName) }
        } catch {}
    }
}

# Cisco Webex telephony config
Write-Host '[INFO] Step 4/5: Cisco Webex phone configuration...'
$webexConfigPath = Join-Path $env:LOCALAPPDATA 'CiscoSpark'
if (Test-Path $webexConfigPath) {
    $webexFiles = Get-ChildItem $webexConfigPath -Filter '*.json' -ErrorAction SilentlyContinue | Select-Object -First 3
    Write-Host ('[INFO] Webex config files: ' + @($webexFiles).Count)
    $webexFiles | ForEach-Object { Write-Host ('    ' + $_.Name) }
}

# Softphone registry keys (generic PBX clients)
Write-Host '[INFO] Step 5/5: Softphone / PBX client registry scan...'
$softphoneKeys = @(
    @{Key='HKCU:\SOFTWARE\3CX'; Label='3CX Phone'},
    @{Key='HKCU:\SOFTWARE\Zoiper'; Label='Zoiper VoIP'},
    @{Key='HKCU:\SOFTWARE\X-Lite'; Label='X-Lite SIP'},
    @{Key='HKCU:\SOFTWARE\Polycom'; Label='Polycom'},
    @{Key='HKCU:\SOFTWARE\AVAYA'; Label='Avaya one-X'}
)
foreach ($sp in $softphoneKeys) {
    if (Test-Path $sp.Key -ErrorAction SilentlyContinue) {
        Write-Host ('[INFO] Softphone FOUND: ' + $sp.Label + ' at ' + $sp.Key)
        $props = Get-ItemProperty $sp.Key -ErrorAction SilentlyContinue
        if ($props) { $props.PSObject.Properties | Where-Object { $_.Name -notmatch '^PS' } | Select-Object -First 3 | ForEach-Object { Write-Host ('    ' + $_.Name + ' = ' + $_.Value) } }
    }
}
Write-Host '[SUCCESS] T1598.004 emulation completed'""",
    "cleanup_command": "Write-Host '[INFO] T1598.004 cleanup: no artefacts created - read-only enumeration'",
    "detection_rule": "Teams config JSON + AD LDAP telephoneNumber attribute + SfB registry + softphone registry access (T1598.004 vishing recon pattern)",
},

# ── T1591.001 ─────────────────────────────────────────────────────────────────
"T1591.001": {
    "description": (
        "Simulates identifying victim organization locations from a foothold machine (T1591.001). "
        "Queries IP geolocation APIs to identify physical locations associated with the organization's IPs, "
        "enumerates AD Sites and Services for physical office locations, reads LDAP location attributes "
        "from user and computer objects, and checks DNS SRV records for regional site indicators. "
        "Maps physical infrastructure for operational planning. Read-only."
    ),
    "required_tags": ["excalibur_recon_target_domain"],
    "command": r"""Write-Host '[START] T1591.001 - Identify Locations (physical office + IP geolocation mapping)'
$domain = '#{excalibur_recon_target_domain}'
$ua = 'MorganaTest-T1591.001-LocationRecon/1.0'

# AD Sites and Services (physical location indicators)
Write-Host '[INFO] Step 1/4: AD Sites and Services enumeration...'
try {
    $forest = [System.DirectoryServices.ActiveDirectory.Forest]::GetCurrentForest()
    $sites = $forest.Sites
    Write-Host ('[INFO] AD Sites found: ' + $sites.Count)
    $sites | Select-Object -First 10 | ForEach-Object {
        $links = @($_.SiteLinks).Count
        $subnets = @($_.Subnets).Count
        Write-Host ('    Site: ' + $_.Name + ' | subnets=' + $subnets + ' | links=' + $links)
        $_.Subnets | Select-Object -First 3 | ForEach-Object { Write-Host ('        Subnet: ' + $_.Name + ' | location=' + $_.Location) }
    }
} catch { Write-Host ('[INFO] AD Sites: ' + $_.Exception.Message.Split([char]10)[0] + ' (not domain-joined or no access)') }

# LDAP location attributes from user objects
Write-Host '[INFO] Step 2/4: LDAP user location attributes...'
try {
    $locSearcher = New-Object System.DirectoryServices.DirectorySearcher
    $locSearcher.Filter = '(&(objectClass=user)(physicalDeliveryOfficeName=*))'
    $locSearcher.PropertiesToLoad.AddRange(@('cn','physicalDeliveryOfficeName','l','st','co','streetAddress')) | Out-Null
    $locSearcher.SizeLimit = 20
    $results = $locSearcher.FindAll()
    $officeLocations = $results | ForEach-Object {
        $p = $_.Properties
        if ($p['physicalDeliveryOfficeName'].Count -gt 0) { $p['physicalDeliveryOfficeName'][0] }
    } | Sort-Object -Unique
    Write-Host ('[INFO] Unique office locations in AD: ' + @($officeLocations).Count)
    $officeLocations | Select-Object -First 10 | ForEach-Object { Write-Host ('    Office: ' + $_) }
} catch { Write-Host ('[INFO] LDAP location: ' + $_.Exception.Message.Split([char]10)[0]) }

# IP geolocation for target domain IPs
Write-Host '[INFO] Step 3/4: IP geolocation for target organization...'
try {
    $ips = [System.Net.Dns]::GetHostAddresses($domain) | Where-Object { $_.AddressFamily -eq 'InterNetwork' } | Select-Object -ExpandProperty IPAddressToString
    foreach ($ip in $ips | Select-Object -First 3) {
        $geoResp = Invoke-WebRequest -Uri ('https://ipinfo.io/' + $ip + '/json') -Headers @{'User-Agent'=$ua} -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
        $geo = $geoResp.Content | ConvertFrom-Json
        Write-Host ('[INFO] IP ' + $ip + ' -> ' + $geo.city + ', ' + $geo.region + ', ' + $geo.country + ' | org=' + $geo.org + ' | loc=' + $geo.loc)
    }
} catch { Write-Host ('[INFO] Geolocation: ' + $_.Exception.Message.Split([char]10)[0]) }

# DNS SRV records for site/regional indicators
Write-Host '[INFO] Step 4/4: DNS SRV records (regional site indicators)...'
$srvRecords = @('_ldap._tcp','_kerberos._tcp','_gc._tcp','_ldap._tcp.dc._msdcs','_kerberos._tcp.dc._msdcs')
foreach ($srv in $srvRecords) {
    try {
        $fqdn = $srv + '.' + $env:USERDNSDOMAIN
        $r = Resolve-DnsName -Name $fqdn -Type SRV -ErrorAction SilentlyContinue -DnsOnly
        if ($r) { Write-Host ('[INFO] SRV ' + $srv + ': ' + @($r).Count + ' targets -> ' + ($r | Select-Object -ExpandProperty NameTarget | Select-Object -First 3) -join ', ') }
    } catch {}
}
Write-Host '[SUCCESS] T1591.001 emulation completed'""",
    "cleanup_command": "Write-Host '[INFO] T1591.001 cleanup: no artefacts created - read-only LDAP and HTTP queries'",
    "detection_rule": "AD Sites enumeration + LDAP physicalDeliveryOfficeName query + IP geolocation API + DNS SRV (T1591.001 location recon pattern)",
},

# ── T1591.002 ─────────────────────────────────────────────────────────────────
"T1591.002": {
    "description": (
        "Simulates identifying business relationships from a foothold machine (T1591.002). "
        "Enumerates AD forest trusts, cross-domain relationships, email routing MX records for "
        "partner domains, Outlook auto-discovered connectors, and web certificates SANs that reveal "
        "partner/subsidiary domains. Also queries SPF records for authorized mail senders (reveals "
        "cloud email providers and third-party services). Maps supply chain and partner relationships. Read-only."
    ),
    "required_tags": ["excalibur_recon_target_domain"],
    "command": r"""Write-Host '[START] T1591.002 - Identify Business Relationships (trust + partner + supply chain recon)'
$domain = '#{excalibur_recon_target_domain}'
$ua = 'MorganaTest-T1591.002-BusinessRelRecon/1.0'

# AD forest trust enumeration
Write-Host '[INFO] Step 1/5: Active Directory trust relationships...'
try {
    $forest = [System.DirectoryServices.ActiveDirectory.Forest]::GetCurrentForest()
    $trusts = $forest.GetAllTrustRelationships()
    Write-Host ('[INFO] Forest trusts: ' + @($trusts).Count)
    $trusts | ForEach-Object {
        Write-Host ('    ' + $_.SourceName + ' <--> ' + $_.TargetName + ' [' + $_.TrustDirection + '] [' + $_.TrustType + ']')
    }
    $domains = $forest.Domains
    Write-Host ('[INFO] Domains in forest: ' + @($domains).Count)
    $domains | ForEach-Object { Write-Host ('    ' + $_.Name) }
} catch { Write-Host ('[INFO] Trust enum: ' + $_.Exception.Message.Split([char]10)[0]) }

# SPF record analysis (reveals third-party email senders / cloud services)
Write-Host '[INFO] Step 2/5: SPF record analysis (authorized senders = business partners)...'
try {
    $spf = Resolve-DnsName -Name $domain -Type TXT -ErrorAction SilentlyContinue | Where-Object { $_.Strings -match 'v=spf1' }
    if ($spf) {
        $spfText = ($spf.Strings -join ' ')
        Write-Host ('[INFO] SPF record: ' + $spfText)
        # Parse includes (third-party email providers)
        $includes = [regex]::Matches($spfText, 'include:([^\s]+)') | ForEach-Object { $_.Groups[1].Value }
        Write-Host ('[INFO] Third-party email senders (' + @($includes).Count + '):')
        $includes | ForEach-Object { Write-Host ('    include: ' + $_ + $(
            switch -Wildcard ($_) {
                '*sendgrid*' { ' [SendGrid]' }; '*mailchimp*' { ' [Mailchimp]' }; '*salesforce*' { ' [Salesforce]' }
                '*zendesk*' { ' [Zendesk]' }; '*hubspot*' { ' [HubSpot]' }; '*protection.outlook*' { ' [Office 365]' }
                '*google*' { ' [Google Workspace]' }; '*amazonses*' { ' [AWS SES]' }; default { '' }
            }
        ))}
    }
} catch { Write-Host ('[INFO] SPF: ' + $_.Exception.Message.Split([char]10)[0]) }

# Certificate SANs (subsidiary/partner domain discovery)
Write-Host '[INFO] Step 3/5: TLS certificate SANs (subsidiary/partner domains)...'
try {
    $tcp = New-Object System.Net.Sockets.TcpClient($domain, 443)
    $ssl = New-Object System.Net.Security.SslStream($tcp.GetStream(), $false, {$true})
    $ssl.AuthenticateAsClient($domain)
    $cert2 = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($ssl.RemoteCertificate)
    $sanExt = $cert2.Extensions | Where-Object { $_.Oid.Value -eq '2.5.29.17' }
    if ($sanExt) {
        $sans = $sanExt.Format($true) -split "`n" | Where-Object { $_ -match 'DNS Name=' } | ForEach-Object { ($_ -split '=')[-1].Trim() }
        Write-Host ('[INFO] Certificate SANs (' + @($sans).Count + ' domains):')
        $sans | Where-Object { $_ -notmatch '^\*\.' } | Select-Object -First 15 | ForEach-Object { Write-Host ('    ' + $_) }
    }
    $ssl.Close(); $tcp.Close()
} catch { Write-Host ('[INFO] Cert SANs: ' + $_.Exception.Message.Split([char]10)[0]) }

# MX record partners (shared email routing)
Write-Host '[INFO] Step 4/5: MX record analysis (email routing partners)...'
try {
    $mx = Resolve-DnsName -Name $domain -Type MX -ErrorAction SilentlyContinue
    if ($mx) {
        Write-Host ('[INFO] MX records (' + @($mx).Count + '):')
        $mx | Sort-Object Preference | ForEach-Object {
            Write-Host ('    Priority ' + $_.Preference + ': ' + $_.NameExchange + $(
                switch -Wildcard ($_.NameExchange) {
                    '*protection.outlook*' { ' [Microsoft 365]' }; '*google*' { ' [Google]' }
                    '*mimecast*' { ' [Mimecast]' }; '*proofpoint*' { ' [Proofpoint]' }
                    '*barracuda*' { ' [Barracuda]' }; default { '' }
                }
            ))
        }
    }
} catch { Write-Host ('[INFO] MX records: ' + $_.Exception.Message.Split([char]10)[0]) }

# DMARC policy (security posture + reporting partner)
Write-Host '[INFO] Step 5/5: DMARC policy and reporting partner...'
try {
    $dmarc = Resolve-DnsName -Name ('_dmarc.' + $domain) -Type TXT -ErrorAction SilentlyContinue
    if ($dmarc) {
        $dmarcText = ($dmarc.Strings -join ' ')
        Write-Host ('[INFO] DMARC: ' + $dmarcText)
        $rua = [regex]::Match($dmarcText, 'rua=([^;]+)').Groups[1].Value
        if ($rua) { Write-Host ('[INFO] DMARC aggregate reports sent to: ' + $rua) }
    }
} catch {}
Write-Host '[SUCCESS] T1591.002 emulation completed'""",
    "cleanup_command": "Write-Host '[INFO] T1591.002 cleanup: no artefacts created - read-only DNS and LDAP queries'",
    "detection_rule": "AD trust enumeration + SPF/DMARC/MX DNS queries + TLS cert SAN extraction (T1591.002 business relationship recon pattern)",
},

# ── T1591.003 ─────────────────────────────────────────────────────────────────
"T1591.003": {
    "description": (
        "Simulates identifying business tempo from a foothold machine (T1591.003). "
        "Enumerates working hours and activity patterns from AD user lastLogon timestamps, "
        "event log logon patterns, scheduled task timing, and email server activity indicators. "
        "Maps when the organization is most/least active to identify optimal attack windows. Read-only."
    ),
    "required_tags": [],
    "command": r"""Write-Host '[START] T1591.003 - Identify Business Tempo (working hours + activity pattern analysis)'

# AD lastLogon analysis for working hours
Write-Host '[INFO] Step 1/4: AD user lastLogon temporal analysis...'
try {
    $searcher = New-Object System.DirectoryServices.DirectorySearcher
    $searcher.Filter = '(&(objectClass=user)(lastLogon>=1)(!(userAccountControl:1.2.840.113556.1.4.803:=2)))'
    $searcher.PropertiesToLoad.AddRange(@('cn','lastLogon','lastLogonTimestamp')) | Out-Null
    $searcher.SizeLimit = 100
    $results = $searcher.FindAll()
    Write-Host ('[INFO] AD users with logon data: ' + $results.Count)
    $hours = @{}
    $results | ForEach-Object {
        $p = $_.Properties
        if ($p['lastLogon'].Count -gt 0 -and $p['lastLogon'][0] -gt 0) {
            try {
                $logonTime = [DateTime]::FromFileTime($p['lastLogon'][0])
                $hour = $logonTime.Hour
                $hours[$hour] = ($hours[$hour] + 1)
            } catch {}
        }
    }
    if ($hours.Count -gt 0) {
        Write-Host '[INFO] Logon activity by hour (UTC):'
        0..23 | ForEach-Object {
            $count = if ($hours[$_]) { $hours[$_] } else { 0 }
            $bar = '#' * [Math]::Min($count, 40)
            Write-Host ('    ' + $_'.ToString('00')' + ':00 | ' + $bar + ' (' + $count + ')')
        }
    }
} catch { Write-Host ('[INFO] AD lastLogon: ' + $_.Exception.Message.Split([char]10)[0]) }

# Local event log logon pattern
Write-Host '[INFO] Step 2/4: Local logon event pattern (last 7 days)...'
try {
    $logonEvents = Get-WinEvent -FilterHashtable @{LogName='Security'; Id=4624; StartTime=(Get-Date).AddDays(-7)} -MaxEvents 200 -ErrorAction Stop
    $hourlyLogons = $logonEvents | Group-Object { $_.TimeCreated.Hour } | Sort-Object Name
    Write-Host ('[INFO] Logon events last 7 days: ' + @($logonEvents).Count)
    $hourlyLogons | ForEach-Object {
        $bar = '#' * [Math]::Min($_.Count, 30)
        Write-Host ('    ' + $_.Name.PadLeft(2,'0') + ':00 | ' + $bar + ' (' + $_.Count + ')')
    }
} catch { Write-Host ('[INFO] Event log: ' + $_.Exception.Message.Split([char]10)[0]) }

# Scheduled task timing
Write-Host '[INFO] Step 3/4: Scheduled task timing (business process indicators)...'
try {
    $tasks = Get-ScheduledTask -ErrorAction SilentlyContinue | Where-Object { $_.State -eq 'Ready' -and $_.TaskPath -notmatch 'Microsoft' }
    Write-Host ('[INFO] Non-Microsoft scheduled tasks: ' + @($tasks).Count)
    $tasks | Select-Object -First 10 | ForEach-Object {
        $trigger = ($_.Triggers | Select-Object -First 1)
        Write-Host ('    ' + $_.TaskName + ' | trigger=' + $(if ($trigger) { $trigger.CimClass.CimClassName } else { 'none' }))
    }
} catch {}

# System uptime patterns
Write-Host '[INFO] Step 4/4: System uptime (continuous operation indicator)...'
try {
    $lastBoot = (Get-WmiObject Win32_OperatingSystem).ConvertToDateTime((Get-WmiObject Win32_OperatingSystem).LastBootUpTime)
    $uptime = (Get-Date) - $lastBoot
    Write-Host ('[INFO] Last boot: ' + $lastBoot.ToString('yyyy-MM-dd HH:mm:ss') + ' | Uptime: ' + [math]::Round($uptime.TotalHours, 1) + 'h')
    Write-Host ('[INFO] Day of week last booted: ' + $lastBoot.DayOfWeek)
} catch {}
Write-Host '[SUCCESS] T1591.003 emulation completed'""",
    "cleanup_command": "Write-Host '[INFO] T1591.003 cleanup: no artefacts created - read-only LDAP and event log queries'",
    "detection_rule": "AD lastLogon bulk read + Security event log 4624 query + scheduled task enumeration (T1591.003 business tempo recon pattern)",
},

# ── T1591.004 ─────────────────────────────────────────────────────────────────
"T1591.004": {
    "description": (
        "Simulates identifying roles within the victim organization from a foothold machine (T1591.004). "
        "Enumerates AD user attributes (title, department, manager, directReports) to map the "
        "organizational hierarchy. Identifies C-suite, IT admins, finance, and security personnel. "
        "Also enumerates privileged group membership and service accounts. Read-only."
    ),
    "required_tags": [],
    "command": r"""Write-Host '[START] T1591.004 - Identify Roles (organizational hierarchy and key personnel mapping)'

# LDAP role enumeration: title and department
Write-Host '[INFO] Step 1/4: LDAP user title and department enumeration...'
try {
    $searcher = New-Object System.DirectoryServices.DirectorySearcher
    $searcher.Filter = '(&(objectClass=user)(title=*)(!(userAccountControl:1.2.840.113556.1.4.803:=2)))'
    $searcher.PropertiesToLoad.AddRange(@('cn','title','department','mail','manager')) | Out-Null
    $searcher.SizeLimit = 50
    $results = $searcher.FindAll()
    Write-Host ('[INFO] Users with job titles: ' + $results.Count)
    # Group by high-value roles
    $highValueTitles = @('CEO','CTO','CFO','CISO','CIO','Director','VP','Vice President','Head of','Manager','Administrator','Engineer','Analyst')
    $results | Select-Object -First 20 | ForEach-Object {
        $p = $_.Properties
        $title = if ($p['title'].Count -gt 0) { $p['title'][0] } else { '' }
        $dept = if ($p['department'].Count -gt 0) { $p['department'][0] } else { '' }
        $isHighValue = $highValueTitles | Where-Object { $title -match $_ }
        $prefix = if ($isHighValue) { '[HVT] ' } else { '      ' }
        Write-Host ($prefix + $p['cn'][0] + ' | ' + $title + ' | ' + $dept)
    }
} catch { Write-Host ('[INFO] LDAP roles: ' + $_.Exception.Message.Split([char]10)[0]) }

# Department mapping
Write-Host '[INFO] Step 2/4: Department structure mapping...'
try {
    $deptSearcher = New-Object System.DirectoryServices.DirectorySearcher
    $deptSearcher.Filter = '(&(objectClass=user)(department=*))'
    $deptSearcher.PropertiesToLoad.AddRange(@('department')) | Out-Null
    $deptSearcher.SizeLimit = 200
    $deptResults = $deptSearcher.FindAll()
    $departments = $deptResults | ForEach-Object { $_.Properties['department'][0] } | Group-Object | Sort-Object Count -Descending
    Write-Host ('[INFO] Departments found: ' + @($departments).Count)
    $departments | Select-Object -First 15 | ForEach-Object { Write-Host ('    ' + $_.Name + ': ' + $_.Count + ' users') }
} catch { Write-Host ('[INFO] Departments: ' + $_.Exception.Message.Split([char]10)[0]) }

# Privileged group membership mapping
Write-Host '[INFO] Step 3/4: Privileged group membership (admin roles)...'
$adminGroups = @('Domain Admins','Enterprise Admins','Schema Admins','Group Policy Creator Owners','Administrators','Account Operators','Server Operators','Backup Operators','Print Operators')
foreach ($grp in $adminGroups) {
    try {
        $grpSearcher = New-Object System.DirectoryServices.DirectorySearcher
        $grpSearcher.Filter = '(&(objectClass=group)(cn=' + $grp + '))'
        $grpSearcher.PropertiesToLoad.Add('member') | Out-Null
        $grpResult = $grpSearcher.FindOne()
        if ($grpResult) {
            $memberCount = $grpResult.Properties['member'].Count
            Write-Host ('[INFO] ' + $grp + ': ' + $memberCount + ' members')
            $grpResult.Properties['member'] | Select-Object -First 3 | ForEach-Object {
                $memberCN = ($_ -split ',')[0] -replace 'CN=',''
                Write-Host ('    - ' + $memberCN)
            }
        }
    } catch {}
}

# Service accounts (non-interactive accounts with elevated context)
Write-Host '[INFO] Step 4/4: Service account enumeration...'
try {
    $svcSearcher = New-Object System.DirectoryServices.DirectorySearcher
    $svcSearcher.Filter = '(&(objectClass=user)(servicePrincipalName=*)(!(userAccountControl:1.2.840.113556.1.4.803:=2)))'
    $svcSearcher.PropertiesToLoad.AddRange(@('cn','servicePrincipalName','description')) | Out-Null
    $svcSearcher.SizeLimit = 20
    $svcResults = $svcSearcher.FindAll()
    Write-Host ('[INFO] Kerberoastable service accounts (SPN set): ' + $svcResults.Count)
    $svcResults | Select-Object -First 8 | ForEach-Object {
        $p = $_.Properties
        Write-Host ('    ' + $p['cn'][0] + ' | SPN count=' + $p['servicePrincipalName'].Count)
    }
} catch { Write-Host ('[INFO] Service accounts: ' + $_.Exception.Message.Split([char]10)[0]) }
Write-Host '[SUCCESS] T1591.004 emulation completed'""",
    "cleanup_command": "Write-Host '[INFO] T1591.004 cleanup: no artefacts created - read-only LDAP queries'",
    "detection_rule": "LDAP bulk user title/department query + privileged group membership enumeration + SPN discovery (T1591.004 role recon pattern)",
},

# ── T1590.001 ─────────────────────────────────────────────────────────────────
"T1590.001": {
    "description": (
        "Simulates enumerating domain properties from a foothold machine (T1590.001). "
        "Enumerates AD domain functional level, password policy, account lockout policy, "
        "domain SID, FSMO role holders, Kerberos policy, and domain controller list. "
        "Also queries the domain's DNS zone for SOA details. Read-only."
    ),
    "required_tags": [],
    "command": r"""Write-Host '[START] T1590.001 - Domain Properties (AD domain config + policy enumeration)'

# Domain functional level and policy
Write-Host '[INFO] Step 1/4: Domain functional level and identification...'
try {
    $domain = [System.DirectoryServices.ActiveDirectory.Domain]::GetCurrentDomain()
    Write-Host ('[INFO] Domain: ' + $domain.Name)
    Write-Host ('[INFO] Forest: ' + $domain.Forest.Name)
    Write-Host ('[INFO] Domain mode: ' + $domain.DomainMode)
    Write-Host ('[INFO] Forest mode: ' + $domain.Forest.ForestMode)
    Write-Host ('[INFO] Domain controllers: ' + @($domain.DomainControllers).Count)
    $domain.DomainControllers | ForEach-Object {
        Write-Host ('    DC: ' + $_.Name + ' | OS: ' + $_.OSVersion + ' | Site: ' + $_.SiteName + ' | Roles: ' + ($_.Roles -join ','))
    }
} catch { Write-Host ('[INFO] Domain: ' + $_.Exception.Message.Split([char]10)[0]) }

# Password and lockout policy
Write-Host '[INFO] Step 2/4: Default domain password and lockout policy...'
try {
    $policySearcher = New-Object System.DirectoryServices.DirectorySearcher
    $policySearcher.Filter = '(objectClass=domainDNS)'
    $policySearcher.PropertiesToLoad.AddRange(@('lockoutThreshold','lockoutDuration','lockoutObservationWindow','maxPwdAge','minPwdAge','minPwdLength','pwdHistoryLength','pwdProperties')) | Out-Null
    $policyResult = $policySearcher.FindOne()
    if ($policyResult) {
        $p = $policyResult.Properties
        $maxAge = if ($p['maxPwdAge'].Count -gt 0) { [math]::Round([TimeSpan]::FromTicks([Math]::Abs($p['maxPwdAge'][0])).TotalDays,0) } else { 'N/A' }
        $minLen = if ($p['minPwdLength'].Count -gt 0) { $p['minPwdLength'][0] } else { 'N/A' }
        $lockThr = if ($p['lockoutThreshold'].Count -gt 0) { $p['lockoutThreshold'][0] } else { 'N/A' }
        $pwdHist = if ($p['pwdHistoryLength'].Count -gt 0) { $p['pwdHistoryLength'][0] } else { 'N/A' }
        Write-Host ('    Max password age: ' + $maxAge + ' days')
        Write-Host ('    Min password length: ' + $minLen + ' chars')
        Write-Host ('    Password history: ' + $pwdHist + ' passwords')
        Write-Host ('    Lockout threshold: ' + $lockThr + ' attempts')
    }
} catch { Write-Host ('[INFO] Password policy: ' + $_.Exception.Message.Split([char]10)[0]) }

# FSMO role holders
Write-Host '[INFO] Step 3/4: FSMO role holders...'
try {
    $dom = [System.DirectoryServices.ActiveDirectory.Domain]::GetCurrentDomain()
    Write-Host ('    PDC Emulator: ' + $dom.PdcRoleOwner.Name)
    Write-Host ('    RID Master: ' + $dom.RidRoleOwner.Name)
    Write-Host ('    Infrastructure Master: ' + $dom.InfrastructureRoleOwner.Name)
    $forest = [System.DirectoryServices.ActiveDirectory.Forest]::GetCurrentForest()
    Write-Host ('    Schema Master: ' + $forest.SchemaRoleOwner.Name)
    Write-Host ('    Domain Naming Master: ' + $forest.NamingRoleOwner.Name)
} catch { Write-Host ('[INFO] FSMO: ' + $_.Exception.Message.Split([char]10)[0]) }

# Domain SID
Write-Host '[INFO] Step 4/4: Domain SID and Kerberos policy...'
try {
    $domSid = (New-Object System.Security.Principal.NTAccount($env:USERDOMAIN)).Translate([System.Security.Principal.SecurityIdentifier]).AccountDomainSid.Value
    Write-Host ('    Domain SID: ' + $domSid)
} catch {}
try {
    $krb = Get-WmiObject -Namespace 'root\cimv2' -Query "SELECT * FROM Win32_ComputerSystem" | Select-Object Domain, PartOfDomain
    Write-Host ('    Domain joined: ' + $krb.PartOfDomain + ' | Domain: ' + $krb.Domain)
} catch {}
Write-Host '[SUCCESS] T1590.001 emulation completed'""",
    "cleanup_command": "Write-Host '[INFO] T1590.001 cleanup: no artefacts created - read-only LDAP queries'",
    "detection_rule": "LDAP domainDNS policy read + FSMO enumeration + domain SID translation (T1590.001 domain properties recon pattern)",
},

# ── T1590.002 ─────────────────────────────────────────────────────────────────
"T1590.002": {
    "description": (
        "Simulates DNS enumeration of the victim network from a foothold machine (T1590.002). "
        "Performs comprehensive DNS record enumeration: A, AAAA, MX, NS, TXT, SOA, SRV, CNAME, PTR. "
        "Attempts zone transfer (AXFR). Enumerates internal DNS zones via WMI if domain-joined. "
        "Performs reverse DNS lookups on local subnet. Read-only."
    ),
    "required_tags": ["excalibur_recon_target_domain"],
    "command": r"""Write-Host '[START] T1590.002 - DNS Enumeration (comprehensive DNS record + zone recon)'
$domain = '#{excalibur_recon_target_domain}'

# All record types
Write-Host '[INFO] Step 1/4: Comprehensive DNS record enumeration...'
$recordTypes = @('A','AAAA','MX','NS','TXT','SOA','CNAME','SRV','DNSKEY','DS','CAA')
foreach ($rtype in $recordTypes) {
    try {
        $recs = Resolve-DnsName -Name $domain -Type $rtype -ErrorAction SilentlyContinue -DnsOnly
        if ($recs) {
            Write-Host ('[INFO] ' + $rtype + ' (' + @($recs).Count + ' records):')
            $recs | Select-Object -First 5 | ForEach-Object {
                $val = if ($_.IPAddress) { $_.IPAddress } elseif ($_.NameHost) { $_.NameHost } elseif ($_.NameExchange) { 'MX:' + $_.NameExchange } elseif ($_.PrimaryServer) { 'SOA:' + $_.PrimaryServer } elseif ($_.Strings) { $_.Strings -join ' ' } else { $_.ToString().Substring(0,[Math]::Min(100,$_.ToString().Length)) }
                Write-Host ('    ' + [string]$val)
            }
        }
    } catch {}
}

# Zone transfer attempt (AXFR)
Write-Host '[INFO] Step 2/4: Zone transfer attempt (AXFR)...'
try {
    $ns = Resolve-DnsName -Name $domain -Type NS -ErrorAction SilentlyContinue | Select-Object -ExpandProperty NameHost
    foreach ($nsHost in $ns | Select-Object -First 3) {
        try {
            $axfr = & nslookup.exe -type=axfr $domain $nsHost 2>&1
            $zoneRecords = $axfr | Where-Object { $_ -match 'internet address|mail exchanger|name server' }
            Write-Host ('[INFO] AXFR from ' + $nsHost + ': ' + $(if (@($zoneRecords).Count -gt 0) { 'SUCCESS - ' + @($zoneRecords).Count + ' records' } else { 'FAILED/REFUSED (expected)' }))
        } catch {}
    }
} catch { Write-Host ('[INFO] AXFR: ' + $_.Exception.Message.Split([char]10)[0]) }

# Internal DNS zones via WMI (if DC)
Write-Host '[INFO] Step 3/4: Internal DNS zones (WMI query)...'
try {
    $dnsZones = Get-WmiObject -Namespace 'root\MicrosoftDNS' -Class MicrosoftDNS_Zone -ErrorAction Stop
    Write-Host ('[INFO] DNS zones on this server: ' + @($dnsZones).Count)
    $dnsZones | Select-Object -First 10 | ForEach-Object { Write-Host ('    Zone: ' + $_.Name + ' | type=' + $_.ZoneType + ' | reverse=' + $_.Reverse) }
} catch { Write-Host ('[INFO] DNS WMI zones: not a DNS server or access denied') }

# Reverse DNS on local subnet
Write-Host '[INFO] Step 4/4: Reverse DNS on local subnet...'
$localIP = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notmatch '^127' } | Select-Object -First 1).IPAddress
if ($localIP) {
    $subnet = $localIP -replace '\.\d+$',''
    Write-Host ('[INFO] Performing PTR lookups on ' + $subnet + '.1-20...')
    1..20 | ForEach-Object {
        $ip = $subnet + '.' + $_
        try { $ptr = [System.Net.Dns]::GetHostEntry($ip); Write-Host ('    ' + $ip + ' -> ' + $ptr.HostName) } catch {}
    }
}
Write-Host '[SUCCESS] T1590.002 emulation completed'""",
    "cleanup_command": "Write-Host '[INFO] T1590.002 cleanup: no artefacts created - DNS queries only'",
    "detection_rule": "Multi-type DNS query burst + AXFR zone transfer attempt + WMI DNS zone query + PTR sweep (T1590.002 DNS recon pattern)",
},

# ── T1590.003 ─────────────────────────────────────────────────────────────────
"T1590.003": {
    "description": (
        "Simulates enumerating network trust dependencies from a foothold machine (T1590.003). "
        "Enumerates AD forest/domain trusts, DFS namespace shares, Kerberos cross-realm delegation, "
        "and credential delegation settings (CredSSP, unconstrained delegation). "
        "Identifies trust paths that could be abused for lateral movement. Read-only."
    ),
    "required_tags": [],
    "command": r"""Write-Host '[START] T1590.003 - Network Trust Dependencies (trust + delegation + DFS recon)'

# Forest and domain trust enumeration
Write-Host '[INFO] Step 1/4: Forest and domain trust relationships...'
try {
    $forest = [System.DirectoryServices.ActiveDirectory.Forest]::GetCurrentForest()
    Write-Host ('[INFO] Forest: ' + $forest.Name + ' | Domains: ' + @($forest.Domains).Count + ' | Sites: ' + @($forest.Sites).Count)
    $forestTrusts = $forest.GetAllTrustRelationships()
    Write-Host ('[INFO] Forest-level trusts: ' + @($forestTrusts).Count)
    $forestTrusts | ForEach-Object { Write-Host ('    ' + $_.SourceName + ' <-> ' + $_.TargetName + ' [' + $_.TrustDirection + '] [' + $_.TrustType + '] [SIDFiltering=' + $_.SidFilteringEnabled + ']') }
    $dom = [System.DirectoryServices.ActiveDirectory.Domain]::GetCurrentDomain()
    $domTrusts = $dom.GetAllTrustRelationships()
    Write-Host ('[INFO] Domain-level trusts: ' + @($domTrusts).Count)
    $domTrusts | ForEach-Object { Write-Host ('    ' + $_.SourceName + ' <-> ' + $_.TargetName + ' [' + $_.TrustDirection + ']') }
} catch { Write-Host ('[INFO] Trust enum: ' + $_.Exception.Message.Split([char]10)[0]) }

# Unconstrained delegation (high-value trust abuse targets)
Write-Host '[INFO] Step 2/4: Unconstrained delegation (Kerberos trust abuse targets)...'
try {
    $delSearcher = New-Object System.DirectoryServices.DirectorySearcher
    $delSearcher.Filter = '(userAccountControl:1.2.840.113556.1.4.803:=524288)'  # TRUSTED_FOR_DELEGATION
    $delSearcher.PropertiesToLoad.AddRange(@('cn','distinguishedName','operatingSystem')) | Out-Null
    $delSearcher.SizeLimit = 20
    $uncDel = $delSearcher.FindAll()
    Write-Host ('[INFO] Unconstrained delegation computers/accounts: ' + $uncDel.Count)
    $uncDel | ForEach-Object {
        $p = $_.Properties
        Write-Host ('    [UNCONSTRAINED] ' + $p['cn'][0] + $(if ($p['operatingSystem'].Count -gt 0) { ' | OS: ' + $p['operatingSystem'][0] } else { '' }))
    }
} catch { Write-Host ('[INFO] Delegation: ' + $_.Exception.Message.Split([char]10)[0]) }

# DFS namespace shares
Write-Host '[INFO] Step 3/4: DFS namespace shares (shared infrastructure)...'
try {
    $dfsOutput = & dfsutil.exe /root:\\$env:USERDNSDOMAIN\SYSVOL 2>&1
    Write-Host ('[INFO] DFS SYSVOL: ' + ($dfsOutput | Select-Object -First 3) -join ' ')
} catch {}
try {
    $dfsShares = Get-WmiObject -Class Win32_Share -ErrorAction SilentlyContinue | Where-Object { $_.Name -notmatch '^[A-Z]\$|^ADMIN\$|^IPC\$' }
    Write-Host ('[INFO] Non-default shares on this host: ' + @($dfsShares).Count)
    $dfsShares | ForEach-Object { Write-Host ('    ' + $_.Name + ' -> ' + $_.Path + ' (' + $_.Description + ')') }
} catch {}

# CredSSP configuration (credential delegation settings)
Write-Host '[INFO] Step 4/4: CredSSP credential delegation configuration...'
try {
    $credSSP = Get-WSManCredSSP -ErrorAction SilentlyContinue
    if ($credSSP) { Write-Host ('[INFO] CredSSP client: ' + $credSSP[0]) }
} catch {}
$credSSPRegPath = 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\CredentialsDelegation'
if (Test-Path $credSSPRegPath -ErrorAction SilentlyContinue) {
    $credPolicies = Get-ItemProperty $credSSPRegPath -ErrorAction SilentlyContinue
    Write-Host ('[INFO] CredSSP delegation policies:')
    $credPolicies.PSObject.Properties | Where-Object { $_.Name -notmatch '^PS' } | ForEach-Object { Write-Host ('    ' + $_.Name + ' = ' + $_.Value) }
}
Write-Host '[SUCCESS] T1590.003 emulation completed'""",
    "cleanup_command": "Write-Host '[INFO] T1590.003 cleanup: no artefacts created - read-only LDAP and registry queries'",
    "detection_rule": "AD trust + unconstrained delegation LDAP query + DFS share enum + CredSSP registry read (T1590.003 network trust recon pattern)",
},

# ── T1590.004 ─────────────────────────────────────────────────────────────────
"T1590.004": {
    "description": (
        "Simulates enumerating network topology from a foothold machine (T1590.004). "
        "Maps local network topology: network adapters, IP addresses, default gateways, routes, "
        "ARP cache (reveals other hosts), LLDP/CDP neighbor info (if available), traceroute to "
        "external hosts, and subnets visible in the ARP table. Read-only."
    ),
    "required_tags": [],
    "command": r"""Write-Host '[START] T1590.004 - Network Topology (adapter + routing + ARP + traceroute mapping)'

# Network adapters and IP configuration
Write-Host '[INFO] Step 1/4: Network adapter configuration...'
try {
    $adapters = Get-NetIPConfiguration -ErrorAction SilentlyContinue
    foreach ($adapter in $adapters | Where-Object { $_.IPv4Address }) {
        Write-Host ('[INFO] Adapter: ' + $adapter.InterfaceAlias)
        Write-Host ('    IPv4: ' + ($adapter.IPv4Address | Select-Object -ExpandProperty IPAddress) + '/' + ($adapter.IPv4Address | Select-Object -ExpandProperty PrefixLength))
        Write-Host ('    Gateway: ' + ($adapter.IPv4DefaultGateway | Select-Object -ExpandProperty NextHop))
        Write-Host ('    DNS: ' + ($adapter.DNSServer | Where-Object { $_.AddressFamily -eq 2 } | Select-Object -ExpandProperty ServerAddresses) -join ', ')
    }
} catch { Write-Host ('[INFO] Adapters: ' + $_.Exception.Message.Split([char]10)[0]) }

# Routing table
Write-Host '[INFO] Step 2/4: Routing table...'
try {
    $routes = Get-NetRoute -ErrorAction SilentlyContinue | Where-Object { $_.DestinationPrefix -ne '255.255.255.255/32' -and $_.DestinationPrefix -ne 'ff00::/8' } | Sort-Object RouteMetric
    Write-Host ('[INFO] Routes: ' + @($routes).Count)
    $routes | Where-Object { $_.DestinationPrefix -match '^\d' } | Select-Object -First 15 | ForEach-Object {
        Write-Host ('    ' + $_.DestinationPrefix.PadRight(20) + ' via ' + $_.NextHop.PadRight(16) + ' metric=' + $_.RouteMetric + ' if=' + $_.InterfaceAlias)
    }
} catch {}

# ARP cache (reveals other hosts on segment)
Write-Host '[INFO] Step 3/4: ARP cache (live hosts on local segment)...'
try {
    $arpEntries = Get-NetNeighbor -ErrorAction SilentlyContinue | Where-Object { $_.State -ne 'Unreachable' -and $_.IPAddress -notmatch '^(169|224|240|255)' }
    Write-Host ('[INFO] ARP entries: ' + @($arpEntries).Count)
    $arpEntries | Select-Object -First 20 | ForEach-Object {
        $hostname = ''
        try { $hostname = ' -> ' + [System.Net.Dns]::GetHostEntry($_.IPAddress).HostName } catch {}
        Write-Host ('    ' + $_.IPAddress.PadRight(18) + ' | MAC: ' + $_.LinkLayerAddress + ' | ' + $_.State + $hostname)
    }
    # Unique subnets visible
    $subnets = $arpEntries | ForEach-Object { ($_.IPAddress -split '\.')[-4..-2] -join '.' + '.0/24' } | Sort-Object -Unique
    Write-Host ('[INFO] Subnets visible in ARP cache: ' + ($subnets -join ', '))
} catch {}

# Traceroute to detect network segmentation
Write-Host '[INFO] Step 4/4: Network path (tracert - detect segmentation)...'
try {
    $traceOutput = & tracert.exe -d -h 10 -w 500 8.8.8.8 2>&1 | Select-Object -First 15
    $hops = $traceOutput | Where-Object { $_ -match '^\s+\d+' }
    Write-Host ('[INFO] Network path hops: ' + @($hops).Count)
    $hops | ForEach-Object { Write-Host ('    ' + $_.Trim()) }
} catch { Write-Host ('[INFO] Traceroute: ' + $_.Exception.Message.Split([char]10)[0]) }
Write-Host '[SUCCESS] T1590.004 emulation completed'""",
    "cleanup_command": "Write-Host '[INFO] T1590.004 cleanup: no artefacts created - read-only network queries'",
    "detection_rule": "Get-NetIPConfiguration + Get-NetRoute + Get-NetNeighbor ARP + tracert.exe execution from non-network-tool process (T1590.004 topology recon pattern)",
},

# ── T1590.005 ─────────────────────────────────────────────────────────────────
"T1590.005": {
    "description": (
        "Simulates enumerating IP addresses in use at the victim organization from a foothold machine (T1590.005). "
        "Enumerates all IP addresses from network adapters, ARP table, netstat connections, "
        "DNS records, and AD computer objects. Builds a comprehensive IP inventory. Read-only."
    ),
    "required_tags": ["excalibur_recon_target_domain"],
    "command": r"""Write-Host '[START] T1590.005 - IP Addresses (comprehensive IP inventory from foothold)'
$domain = '#{excalibur_recon_target_domain}'

# Local adapter IP addresses
Write-Host '[INFO] Step 1/4: Local IP address inventory...'
try {
    $allIPs = Get-NetIPAddress -ErrorAction SilentlyContinue | Where-Object { $_.AddressFamily -eq 'IPv4' -and $_.IPAddress -notmatch '^169' }
    Write-Host ('[INFO] Local IPs: ' + @($allIPs).Count)
    $allIPs | ForEach-Object { Write-Host ('    ' + $_.IPAddress + '/' + $_.PrefixLength + ' on ' + $_.InterfaceAlias + ' [' + $_.Type + ']') }
} catch {}

# Active TCP connections (reveals internal server IPs)
Write-Host '[INFO] Step 2/4: Active network connections (netstat-style)...'
try {
    $connections = Get-NetTCPConnection -State Established -ErrorAction SilentlyContinue
    $uniqueRemote = $connections | Select-Object -ExpandProperty RemoteAddress | Sort-Object -Unique | Where-Object { $_ -notmatch '^(127|::1|0\.0\.0\.0)' }
    Write-Host ('[INFO] Unique remote IPs in established connections: ' + @($uniqueRemote).Count)
    $uniqueRemote | Select-Object -First 20 | ForEach-Object {
        $hostname = ''; try { $hostname = ' [' + [System.Net.Dns]::GetHostEntry($_).HostName + ']' } catch {}
        Write-Host ('    ' + $_ + $hostname)
    }
} catch {}

# AD computer objects (IP inventory via DNS)
Write-Host '[INFO] Step 3/4: AD computer object IP resolution...'
try {
    $compSearcher = New-Object System.DirectoryServices.DirectorySearcher
    $compSearcher.Filter = '(objectClass=computer)'
    $compSearcher.PropertiesToLoad.AddRange(@('cn','operatingSystem','dNSHostName')) | Out-Null
    $compSearcher.SizeLimit = 30
    $computers = $compSearcher.FindAll()
    Write-Host ('[INFO] AD computers: ' + $computers.Count)
    $computers | Select-Object -First 15 | ForEach-Object {
        $p = $_.Properties
        $cn = $p['cn'][0]
        $dns = if ($p['dNSHostName'].Count -gt 0) { $p['dNSHostName'][0] } else { $cn }
        $os = if ($p['operatingSystem'].Count -gt 0) { $p['operatingSystem'][0] } else { '' }
        $ip = ''
        try { $ip = [System.Net.Dns]::GetHostAddresses($dns) | Where-Object { $_.AddressFamily -eq 'InterNetwork' } | Select-Object -First 1 -ExpandProperty IPAddressToString } catch {}
        Write-Host ('    ' + $cn.PadRight(25) + ' | IP: ' + $ip.PadRight(16) + ' | OS: ' + $os)
    }
} catch { Write-Host ('[INFO] AD computers: ' + $_.Exception.Message.Split([char]10)[0]) }

# External IP enumeration for target domain
Write-Host '[INFO] Step 4/4: External IP enumeration for target domain...'
try {
    $extIPs = [System.Net.Dns]::GetHostAddresses($domain) | Where-Object { $_.AddressFamily -eq 'InterNetwork' } | Select-Object -ExpandProperty IPAddressToString
    Write-Host ('[INFO] ' + $domain + ' external IPs: ' + ($extIPs -join ', '))
    foreach ($ip in $extIPs | Select-Object -First 3) {
        try {
            $ipResp = Invoke-WebRequest -Uri ('https://ipinfo.io/' + $ip + '/json') -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
            $ipData = $ipResp.Content | ConvertFrom-Json
            Write-Host ('    ' + $ip + ' | org=' + $ipData.org + ' | country=' + $ipData.country)
        } catch {}
    }
} catch { Write-Host ('[INFO] External IPs: ' + $_.Exception.Message.Split([char]10)[0]) }
Write-Host '[SUCCESS] T1590.005 emulation completed'""",
    "cleanup_command": "Write-Host '[INFO] T1590.005 cleanup: no artefacts created - read-only network and LDAP queries'",
    "detection_rule": "Get-NetIPAddress + Get-NetTCPConnection + AD computer DNS resolution + ipinfo.io IP queries (T1590.005 IP inventory recon pattern)",
},

# ── T1590.006 ─────────────────────────────────────────────────────────────────
"T1590.006": {
    "description": (
        "Simulates enumerating network security appliances from a foothold machine (T1590.006). "
        "Identifies firewall, proxy, IDS/IPS, WAF, and NAC presence via: registry keys, "
        "running processes, proxy settings (WinHTTP/WPAD), Windows Firewall rules, "
        "event log security software events, and ARP-level gateway fingerprinting. Read-only."
    ),
    "required_tags": [],
    "command": r"""Write-Host '[START] T1590.006 - Network Security Appliances (firewall + proxy + IDS/WAF detection)'

# Proxy configuration detection
Write-Host '[INFO] Step 1/5: Proxy configuration...'
try {
    $proxySettings = Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -ErrorAction SilentlyContinue
    if ($proxySettings.ProxyEnable -eq 1) {
        Write-Host ('[INFO] HTTP Proxy ENABLED: ' + $proxySettings.ProxyServer)
        Write-Host ('    Bypass: ' + $proxySettings.ProxyOverride)
    } else { Write-Host '[INFO] HTTP Proxy: disabled' }
    if ($proxySettings.AutoConfigURL) { Write-Host ('[INFO] PAC/WPAD URL: ' + $proxySettings.AutoConfigURL) }
} catch {}
try {
    $winhttp = & netsh.exe winhttp show proxy 2>&1
    Write-Host ('[INFO] WinHTTP proxy: ' + ($winhttp -join ' '))
} catch {}

# Windows Firewall rules
Write-Host '[INFO] Step 2/5: Windows Firewall rules...'
try {
    $fwProfiles = Get-NetFirewallProfile -ErrorAction SilentlyContinue
    $fwProfiles | ForEach-Object {
        Write-Host ('[INFO] Firewall profile ' + $_.Name + ': Enabled=' + $_.Enabled + ' | DefaultInbound=' + $_.DefaultInboundAction + ' | DefaultOutbound=' + $_.DefaultOutboundAction)
    }
    $customRules = Get-NetFirewallRule -ErrorAction SilentlyContinue | Where-Object { $_.Enabled -eq 'True' -and $_.Direction -eq 'Outbound' -and $_.Action -eq 'Block' } | Select-Object -First 10
    Write-Host ('[INFO] Custom outbound block rules: ' + @($customRules).Count)
    $customRules | ForEach-Object { Write-Host ('    Block: ' + $_.DisplayName) }
} catch {}

# Security software processes (AV/EDR/FW agents)
Write-Host '[INFO] Step 3/5: Security software process detection...'
$securityProcs = @(
    @{Name='MsMpEng'; Product='Microsoft Defender'},
    @{Name='SenseIR'; Product='MDE EDR Agent'},
    @{Name='CylanceSvc'; Product='Cylance'},
    @{Name='CrowdStrike'; Product='CrowdStrike Falcon'},
    @{Name='bdagent'; Product='Bitdefender'},
    @{Name='SentinelAgent'; Product='SentinelOne'},
    @{Name='cb'; Product='Carbon Black'},
    @{Name='ntrtscan'; Product='Trend Micro'},
    @{Name='savservice'; Product='Sophos'},
    @{Name='xagt'; Product='FireEye HX'},
    @{Name='McShield'; Product='McAfee'},
    @{Name='symantec'; Product='Symantec'}
)
foreach ($sp in $securityProcs) {
    $proc = Get-Process -Name $sp.Name -ErrorAction SilentlyContinue
    if ($proc) { Write-Host ('[INFO] SECURITY AGENT FOUND: ' + $sp.Product + ' (PID: ' + ($proc | Select-Object -First 1).Id + ')') }
}

# NAC / 802.1X configuration
Write-Host '[INFO] Step 4/5: NAC / 802.1X authentication configuration...'
try {
    $dot1x = & netsh.exe lan show settings 2>&1
    Write-Host ('[INFO] LAN 802.1X settings: ' + ($dot1x | Where-Object { $_ -match 'authen|enabled' } | Select-Object -First 3) -join ' | ')
} catch {}
try {
    $wlan = & netsh.exe wlan show settings 2>&1
    Write-Host ('[INFO] WLAN settings: ' + ($wlan | Where-Object { $_ -match 'authen|802' } | Select-Object -First 3) -join ' | ')
} catch {}

# Check for SSL inspection (MITM proxy) indicators
Write-Host '[INFO] Step 5/5: SSL inspection / MITM proxy indicators...'
try {
    $trustedCerts = Get-ChildItem Cert:\LocalMachine\Root | Where-Object { $_.Issuer -match 'proxy|inspect|bluecoat|forcepoint|zscaler|netskope|palo alto|cisco' -or $_.Subject -match 'proxy|inspect' }
    if (@($trustedCerts).Count -gt 0) {
        Write-Host ('[INFO] SSL inspection certificates in Trusted Root:')
        $trustedCerts | ForEach-Object { Write-Host ('    Subject: ' + $_.Subject + ' | Issuer: ' + $_.Issuer) }
    } else { Write-Host '[INFO] No obvious SSL inspection certificates found in Trusted Root' }
} catch {}
Write-Host '[SUCCESS] T1590.006 emulation completed'""",
    "cleanup_command": "Write-Host '[INFO] T1590.006 cleanup: no artefacts created - read-only registry and process queries'",
    "detection_rule": "Proxy registry read + firewall rule enumeration + security process detection + cert store access (T1590.006 security appliance recon pattern)",
},

# ── T1589.001 ─────────────────────────────────────────────────────────────────
"T1589.001": {
    "description": (
        "Simulates enumerating credentials from a foothold machine (T1589.001). "
        "Maps credential storage locations and types: Windows Credential Manager (cmdkey), "
        "browser saved passwords database paths, environment variables containing credentials, "
        "configuration files with plaintext passwords, PowerShell history with typed credentials, "
        "and registry keys with stored credentials. Read-only — no credential extraction."
    ),
    "required_tags": [],
    "command": r"""Write-Host '[START] T1589.001 - Credentials Enumeration (credential storage surface mapping)'

# Windows Credential Manager
Write-Host '[INFO] Step 1/6: Windows Credential Manager (cmdkey /list)...'
try {
    $cmdkeyOutput = & cmdkey.exe /list 2>&1
    $entries = $cmdkeyOutput | Where-Object { $_ -match 'Target:|Type:|User:|Saved' }
    Write-Host ('[INFO] Credential Manager entries: ' + [math]::Ceiling(@($entries).Count / 3))
    $entries | Select-Object -First 15 | ForEach-Object { Write-Host ('    ' + $_.Trim()) }
} catch { Write-Host ('[INFO] cmdkey: ' + $_.Exception.Message) }

# Browser credential databases
Write-Host '[INFO] Step 2/6: Browser credential database paths...'
$browserCreds = @(
    @{Browser='Chrome'; Path=Join-Path $env:LOCALAPPDATA 'Google\Chrome\User Data\Default\Login Data'},
    @{Browser='Edge'; Path=Join-Path $env:LOCALAPPDATA 'Microsoft\Edge\User Data\Default\Login Data'},
    @{Browser='Firefox'; Path=Join-Path $env:APPDATA 'Mozilla\Firefox\Profiles'},
    @{Browser='Brave'; Path=Join-Path $env:LOCALAPPDATA 'BraveSoftware\Brave-Browser\User Data\Default\Login Data'}
)
foreach ($bc in $browserCreds) {
    $exists = Test-Path $bc.Path
    $size = if ($exists -and -not (Get-Item $bc.Path -ErrorAction SilentlyContinue).PSIsContainer) { (Get-Item $bc.Path).Length } else { 0 }
    Write-Host ('[INFO] ' + $bc.Browser + ' creds: ' + $(if ($exists) { 'FOUND (' + [math]::Round($size/1KB,1) + ' KB) at ' + $bc.Path } else { 'not found' }))
}

# Environment variables with credentials
Write-Host '[INFO] Step 3/6: Environment variables (credential exposure)...'
$credEnvVars = [System.Environment]::GetEnvironmentVariables() | ForEach-Object { $_.GetEnumerator() } |
    Where-Object { $_.Key -match 'password|passwd|secret|key|token|api|cred|auth|pwd' -and $_.Key -notmatch 'PROCESSOR|PATH' }
if (@($credEnvVars).Count -gt 0) {
    Write-Host ('[INFO] Credential-related environment variables: ' + @($credEnvVars).Count)
    $credEnvVars | ForEach-Object { Write-Host ('    [ENV] ' + $_.Key + ' = ' + $_.Value.Substring(0,[Math]::Min(30,$_.Value.Length)) + '...') }
} else { Write-Host '[INFO] No credential environment variables found' }

# PowerShell history
Write-Host '[INFO] Step 4/6: PowerShell history (typed credentials)...'
$psHistoryPath = (Get-PSReadLineOption -ErrorAction SilentlyContinue).HistorySavePath
if (-not $psHistoryPath) { $psHistoryPath = Join-Path $env:APPDATA 'Microsoft\Windows\PowerShell\PSReadLine\ConsoleHost_history.txt' }
if (Test-Path $psHistoryPath) {
    $histLines = Get-Content $psHistoryPath -ErrorAction SilentlyContinue
    Write-Host ('[INFO] PS history: ' + @($histLines).Count + ' lines at ' + $psHistoryPath)
    $credLines = $histLines | Where-Object { $_ -match 'password|passwd|secret|apikey|-cred|SecureString|ConvertTo-SecureString|credential' } | Select-Object -First 5
    if (@($credLines).Count -gt 0) {
        Write-Host ('[INFO] Credential-related commands in PS history: ' + @($credLines).Count)
        $credLines | ForEach-Object { Write-Host ('    ' + $_.Substring(0,[Math]::Min(100,$_.Length))) }
    }
}

# Registry credential keys
Write-Host '[INFO] Step 5/6: Registry credential storage...'
$credRegPaths = @(
    'HKCU:\SOFTWARE\SimonTatham\PuTTY\Sessions',
    'HKCU:\SOFTWARE\TightVNC\Server',
    'HKCU:\SOFTWARE\ORL\WinVNC3\Password',
    'HKCU:\SOFTWARE\RealVNC\WinVNC4'
)
foreach ($rp in $credRegPaths) {
    if (Test-Path $rp -ErrorAction SilentlyContinue) {
        Write-Host ('[INFO] Credential registry key FOUND: ' + $rp)
        Get-ChildItem $rp -ErrorAction SilentlyContinue | Select-Object -First 3 | ForEach-Object { Write-Host ('    ' + $_.Name) }
    }
}

# Config files with passwords in common locations
Write-Host '[INFO] Step 6/6: Config files with credential patterns...'
$searchPaths = @($env:USERPROFILE, $env:APPDATA, 'C:\inetpub', 'C:\xampp\htdocs')
foreach ($sp in $searchPaths | Where-Object { Test-Path $_ -ErrorAction SilentlyContinue }) {
    Get-ChildItem $sp -Include @('*.config','*.ini','*.env','.env','web.config','appsettings.json') -Recurse -ErrorAction SilentlyContinue |
        Select-Object -First 5 | ForEach-Object {
            try {
                $content = Get-Content $_.FullName -Raw -ErrorAction SilentlyContinue
                if ($content -match 'password\s*=|passwd\s*=|connectionString|api_key') {
                    Write-Host ('[INFO] Potential credential file: ' + $_.FullName)
                }
            } catch {}
        }
}
Write-Host '[SUCCESS] T1589.001 emulation completed'""",
    "cleanup_command": "Write-Host '[INFO] T1589.001 cleanup: no artefacts created - read-only credential surface mapping'",
    "detection_rule": "cmdkey.exe + browser Login Data access + PS history read + credential registry keys + config file scan (T1589.001 credential surface recon pattern)",
},

# ── T1589.002 ─────────────────────────────────────────────────────────────────
"T1589.002": {
    "description": (
        "Simulates enumerating email addresses from a foothold machine (T1589.002). "
        "Collects email addresses from AD user objects (mail attribute), Outlook contacts "
        "(contacts folder MRU), certificate SANs, and public OSINT sources (Hunter.io API pattern, "
        "crt.sh cert email fields). Maps email address format for targeted phishing. Read-only."
    ),
    "required_tags": ["excalibur_recon_target_domain"],
    "command": r"""Write-Host '[START] T1589.002 - Email Addresses (AD + Outlook + OSINT email enumeration)'
$domain = '#{excalibur_recon_target_domain}'
$ua = 'MorganaTest-T1589.002-EmailRecon/1.0'

# AD email attribute enumeration
Write-Host '[INFO] Step 1/4: AD user email (mail attribute) enumeration...'
try {
    $emailSearcher = New-Object System.DirectoryServices.DirectorySearcher
    $emailSearcher.Filter = '(&(objectClass=user)(mail=*))'
    $emailSearcher.PropertiesToLoad.AddRange(@('cn','mail','department','title')) | Out-Null
    $emailSearcher.SizeLimit = 50
    $results = $emailSearcher.FindAll()
    Write-Host ('[INFO] Users with email addresses: ' + $results.Count)
    $emails = $results | ForEach-Object { $_.Properties['mail'][0] }
    # Detect email format pattern
    $patterns = $emails | ForEach-Object {
        $parts = $_ -split '@'
        if ($parts[0] -match '^([a-z]+)\.([a-z]+)$') { 'firstname.lastname' }
        elseif ($parts[0] -match '^([a-z])([a-z]+)$') { 'firstinitial+lastname' }
        elseif ($parts[0] -match '^([a-z]+)([a-z])$') { 'firstname+lastinitial' }
        else { 'other' }
    } | Group-Object | Sort-Object Count -Descending
    Write-Host ('[INFO] Email format patterns detected:')
    $patterns | Select-Object -First 3 | ForEach-Object { Write-Host ('    ' + $_.Name + ': ' + $_.Count + ' users') }
    Write-Host ('[INFO] Sample emails:')
    $emails | Select-Object -First 10 | ForEach-Object { Write-Host ('    ' + $_) }
} catch { Write-Host ('[INFO] AD email enum: ' + $_.Exception.Message.Split([char]10)[0]) }

# Outlook local contacts
Write-Host '[INFO] Step 2/4: Outlook contacts (local address book)...'
$outlookNKPath = Join-Path $env:LOCALAPPDATA 'Microsoft\Outlook'
if (Test-Path $outlookNKPath) {
    $nkFiles = Get-ChildItem $outlookNKPath -Filter '*.nk2' -ErrorAction SilentlyContinue
    $ostFiles = Get-ChildItem $outlookNKPath -Filter '*.ost' -ErrorAction SilentlyContinue
    Write-Host ('[INFO] Outlook NK2 autocomplete files: ' + @($nkFiles).Count)
    Write-Host ('[INFO] Outlook OST data files: ' + @($ostFiles).Count)
    $ostFiles | Select-Object -First 3 | ForEach-Object { Write-Host ('    OST: ' + $_.Name + ' (' + [math]::Round($_.Length/1MB,1) + ' MB)') }
}

# Hunter.io email discovery pattern
Write-Host '[INFO] Step 3/4: Hunter.io email discovery API...'
try {
    $hunterResp = Invoke-WebRequest -Uri ('https://api.hunter.io/v2/domain-search?domain=' + $domain + '&limit=10&api_key=MorganaSimKey') `
        -Headers @{'User-Agent'=$ua} -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
    $hunterData = $hunterResp.Content | ConvertFrom-Json
    if ($hunterData.data) {
        Write-Host ('[INFO] Hunter.io: ' + $hunterData.data.total + ' emails | format: ' + $hunterData.data.pattern)
        $hunterData.data.emails | Select-Object -First 5 | ForEach-Object { Write-Host ('    ' + $_.value + ' [confidence=' + $_.confidence + '%]') }
    }
} catch { Write-Host ('[INFO] Hunter.io: ' + $_.Exception.Message.Split([char]10)[0] + ' (outbound logged by MDE)') }

# crt.sh email fields in certificate metadata
Write-Host '[INFO] Step 4/4: Certificate transparency email fields...'
try {
    $crtResp = Invoke-WebRequest -Uri ('https://crt.sh/?q=%25.' + $domain + '&output=json') `
        -Headers @{'User-Agent'=$ua} -TimeoutSec 10 -UseBasicParsing -ErrorAction Stop
    $crtData = $crtResp.Content | ConvertFrom-Json
    if ($crtData) {
        $emails = $crtData | Select-Object -ExpandProperty name_value | Where-Object { $_ -match '@' } | Sort-Object -Unique
        Write-Host ('[INFO] Emails in certificate SANs: ' + @($emails).Count)
        $emails | Select-Object -First 10 | ForEach-Object { Write-Host ('    ' + $_) }
    }
} catch { Write-Host ('[INFO] crt.sh emails: ' + $_.Exception.Message.Split([char]10)[0]) }
Write-Host '[SUCCESS] T1589.002 emulation completed'""",
    "cleanup_command": "Write-Host '[INFO] T1589.002 cleanup: no artefacts created - read-only email enumeration'",
    "detection_rule": "AD mail attribute bulk read + Outlook NK2/OST access + Hunter.io + crt.sh email queries (T1589.002 email address recon pattern)",
},

# ── T1589.003 ─────────────────────────────────────────────────────────────────
"T1589.003": {
    "description": (
        "Simulates enumerating employee names from a foothold machine (T1589.003). "
        "Collects employee names from AD user objects (displayName, givenName, sn), "
        "constructs username patterns (firstname.lastname, flastname), enumerates local user accounts, "
        "and performs LinkedIn-style OSINT to identify employee names. "
        "Maps full name to username format for targeted attacks. Read-only."
    ),
    "required_tags": ["excalibur_recon_target_domain"],
    "command": r"""Write-Host '[START] T1589.003 - Employee Names (AD + local + OSINT name enumeration)'
$domain = '#{excalibur_recon_target_domain}'
$ua = 'MorganaTest-T1589.003-EmployeeNameRecon/1.0'

# AD displayName/givenName/surname enumeration
Write-Host '[INFO] Step 1/4: AD employee name enumeration...'
try {
    $nameSearcher = New-Object System.DirectoryServices.DirectorySearcher
    $nameSearcher.Filter = '(&(objectClass=user)(displayName=*)(!(userAccountControl:1.2.840.113556.1.4.803:=2)))'
    $nameSearcher.PropertiesToLoad.AddRange(@('displayName','givenName','sn','sAMAccountName','mail','department','title')) | Out-Null
    $nameSearcher.SizeLimit = 50
    $results = $nameSearcher.FindAll()
    Write-Host ('[INFO] AD users with display names: ' + $results.Count)
    Write-Host '[INFO] Employee list (name -> username -> email):'
    $results | Select-Object -First 20 | ForEach-Object {
        $p = $_.Properties
        $display = if ($p['displayName'].Count -gt 0) { $p['displayName'][0] } else { '' }
        $sam = if ($p['sAMAccountName'].Count -gt 0) { $p['sAMAccountName'][0] } else { '' }
        $mail = if ($p['mail'].Count -gt 0) { $p['mail'][0] } else { '' }
        $dept = if ($p['department'].Count -gt 0) { $p['department'][0] } else { '' }
        Write-Host ('    ' + $display.PadRight(30) + ' | user=' + $sam.PadRight(20) + ' | ' + $mail)
    }
    # Detect username format from names
    $results | Select-Object -First 5 | ForEach-Object {
        $p = $_.Properties
        if ($p['givenName'].Count -gt 0 -and $p['sn'].Count -gt 0 -and $p['sAMAccountName'].Count -gt 0) {
            $first = $p['givenName'][0].ToLower()
            $last = $p['sn'][0].ToLower()
            $sam = $p['sAMAccountName'][0].ToLower()
            if ($sam -eq ($first + '.' + $last)) { Write-Host ('    Pattern: firstname.lastname') }
            elseif ($sam -eq ($first[0] + $last)) { Write-Host ('    Pattern: firstinitial+lastname') }
            elseif ($sam -eq ($first + $last[0])) { Write-Host ('    Pattern: firstname+lastinitial') }
        }
    }
} catch { Write-Host ('[INFO] AD names: ' + $_.Exception.Message.Split([char]10)[0]) }

# Local user accounts
Write-Host '[INFO] Step 2/4: Local user account names...'
try {
    $localUsers = Get-LocalUser -ErrorAction SilentlyContinue
    Write-Host ('[INFO] Local accounts: ' + @($localUsers).Count)
    $localUsers | Where-Object { $_.Enabled } | ForEach-Object {
        Write-Host ('    ' + $_.Name + ' | enabled=' + $_.Enabled + ' | lastlogon=' + $_.LastLogon)
    }
} catch { & net.exe user 2>&1 | Where-Object { $_ -match '\S' } | Select-Object -First 10 | ForEach-Object { Write-Host ('    ' + $_) } }

# LinkedIn OSINT URL construction (generates telemetry)
Write-Host '[INFO] Step 3/4: LinkedIn employee search (OSINT URL pattern)...'
$orgName = $domain -replace '\.[^.]+$',''
$linkedInSearchUrls = @(
    'https://www.linkedin.com/company/' + $orgName + '/people/',
    'https://www.linkedin.com/search/results/people/?currentCompany=' + [System.Uri]::EscapeDataString($orgName),
    'https://www.linkedin.com/search/results/people/?keywords=' + [System.Uri]::EscapeDataString($orgName + ' employee')
)
foreach ($url in $linkedInSearchUrls) {
    try {
        $req = [System.Net.WebRequest]::Create($url); $req.Timeout = 3000; $req.Method = 'HEAD'
        $req.Headers.Add('User-Agent', $ua)
        $resp = $req.GetResponse(); Write-Host ('[INFO] LinkedIn: ' + $url.Substring(0,70) + ' -> ' + [int]$resp.StatusCode); $resp.Close()
    } catch [System.Net.WebException] { Write-Host ('[INFO] LinkedIn: HTTP ' + $(if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { 'timeout' })) } catch {}
}

# Username wordlist generation from found names
Write-Host '[INFO] Step 4/4: Generating username wordlist from enumerated names...'
$generatedUsernames = @()
$netUserOutput = & net.exe user 2>&1
$names = $netUserOutput | Where-Object { $_ -match '^\s+\S' } | ForEach-Object { $_.Trim() -split '\s{2,}' } | Where-Object { $_ -and $_ -notmatch '^-' }
Write-Host ('[INFO] Generated username patterns for ' + @($names).Count + ' accounts:')
$names | Select-Object -First 5 | ForEach-Object { Write-Host ('    Account: ' + $_) }
Write-Host '[SUCCESS] T1589.003 emulation completed'""",
    "cleanup_command": "Write-Host '[INFO] T1589.003 cleanup: no artefacts created - read-only name enumeration'",
    "detection_rule": "AD displayName bulk LDAP query + Get-LocalUser + LinkedIn OSINT URL requests (T1589.003 employee name recon pattern)",
},

# ── T1592.001 ─────────────────────────────────────────────────────────────────
"T1592.001": {
    "description": (
        "Simulates enumerating victim hardware from a foothold machine (T1592.001). "
        "Enumerates physical hardware: CPU model/cores/speed, RAM capacity, disk drives/capacity/type, "
        "GPU, BIOS/UEFI manufacturer and version, TPM presence, network adapter models, "
        "and USB/PCI device inventory. Generates WMI process telemetry in MDE. Read-only."
    ),
    "required_tags": [],
    "command": r"""Write-Host '[START] T1592.001 - Hardware Enumeration (CPU/RAM/disk/BIOS/TPM inventory)'

# CPU information
Write-Host '[INFO] Step 1/6: CPU inventory...'
try {
    $cpus = Get-WmiObject -Class Win32_Processor -ErrorAction SilentlyContinue
    $cpus | ForEach-Object {
        Write-Host ('[INFO] CPU: ' + $_.Name.Trim())
        Write-Host ('    Cores: ' + $_.NumberOfCores + ' physical | ' + $_.NumberOfLogicalProcessors + ' logical')
        Write-Host ('    Speed: ' + $_.MaxClockSpeed + ' MHz | Socket: ' + $_.SocketDesignation)
        Write-Host ('    Architecture: ' + $_.Architecture + ' | L2: ' + [math]::Round($_.L2CacheSize/1024,1) + ' MB')
    }
} catch { Write-Host ('[INFO] CPU: ' + $_.Exception.Message) }

# RAM
Write-Host '[INFO] Step 2/6: RAM inventory...'
try {
    $ram = Get-WmiObject -Class Win32_PhysicalMemory -ErrorAction SilentlyContinue
    $totalRAM = ($ram | Measure-Object -Property Capacity -Sum).Sum / 1GB
    Write-Host ('[INFO] RAM: ' + [math]::Round($totalRAM,1) + ' GB total across ' + @($ram).Count + ' modules')
    $ram | ForEach-Object { Write-Host ('    Slot: ' + $_.DeviceLocator + ' | ' + [math]::Round($_.Capacity/1GB,0) + ' GB | ' + $_.Speed + ' MHz | ' + $_.MemoryType) }
} catch {}

# Disk drives
Write-Host '[INFO] Step 3/6: Disk drive inventory...'
try {
    $disks = Get-WmiObject -Class Win32_DiskDrive -ErrorAction SilentlyContinue
    $disks | ForEach-Object {
        Write-Host ('[INFO] Disk: ' + $_.Model + ' | Size: ' + [math]::Round($_.Size/1GB,0) + ' GB | Interface: ' + $_.InterfaceType + ' | SN: ' + $_.SerialNumber.Trim())
    }
    Get-WmiObject -Class Win32_LogicalDisk -ErrorAction SilentlyContinue | Where-Object { $_.DriveType -eq 3 } | ForEach-Object {
        Write-Host ('    Volume ' + $_.DeviceID + ': ' + [math]::Round($_.Size/1GB,0) + ' GB total | ' + [math]::Round($_.FreeSpace/1GB,1) + ' GB free | FS=' + $_.FileSystem)
    }
} catch {}

# BIOS/UEFI
Write-Host '[INFO] Step 4/6: BIOS/UEFI information...'
try {
    $bios = Get-WmiObject -Class Win32_BIOS -ErrorAction SilentlyContinue
    Write-Host ('[INFO] BIOS: ' + $bios.Manufacturer + ' | Version: ' + $bios.SMBIOSBIOSVersion + ' | Date: ' + $bios.ReleaseDate.Substring(0,8))
    $cs = Get-WmiObject -Class Win32_ComputerSystem -ErrorAction SilentlyContinue
    Write-Host ('[INFO] System: ' + $cs.Manufacturer + ' ' + $cs.Model + ' | Serial: ' + (Get-WmiObject Win32_BIOS).SerialNumber.Trim())
} catch {}

# TPM
Write-Host '[INFO] Step 5/6: TPM (Trusted Platform Module) presence...'
try {
    $tpm = Get-WmiObject -Namespace 'root\cimv2\Security\MicrosoftTpm' -Class Win32_Tpm -ErrorAction Stop
    Write-Host ('[INFO] TPM: Present | IsReady=' + $tpm.IsReadyInformation + ' | SpecVersion=' + $tpm.SpecVersion)
} catch { Write-Host '[INFO] TPM: not found or access denied' }

# GPU
Write-Host '[INFO] Step 6/6: GPU inventory...'
try {
    $gpus = Get-WmiObject -Class Win32_VideoController -ErrorAction SilentlyContinue
    $gpus | ForEach-Object {
        Write-Host ('[INFO] GPU: ' + $_.Name + ' | VRAM: ' + [math]::Round($_.AdapterRAM/1MB,0) + ' MB | Driver: ' + $_.DriverVersion)
    }
} catch {}
Write-Host '[SUCCESS] T1592.001 emulation completed'""",
    "cleanup_command": "Write-Host '[INFO] T1592.001 cleanup: no artefacts created - read-only WMI queries'",
    "detection_rule": "WMI Win32_Processor + Win32_PhysicalMemory + Win32_DiskDrive + Win32_BIOS + Win32_Tpm bulk query (T1592.001 hardware recon pattern)",
},

# ── T1592.002 ─────────────────────────────────────────────────────────────────
"T1592.002": {
    "description": (
        "Simulates enumerating victim software from a foothold machine (T1592.002). "
        "Enumerates installed software via registry uninstall keys (HKLM + HKCU + WOW6432Node), "
        "running processes with version information, Windows optional features, .NET framework "
        "versions, PowerShell version, and installed security software. Identifies vulnerable "
        "software versions for exploitation. Read-only."
    ),
    "required_tags": [],
    "command": r"""Write-Host '[START] T1592.002 - Software Enumeration (installed software + versions)'

# Installed software via registry
Write-Host '[INFO] Step 1/5: Installed software (registry uninstall keys)...'
try {
    $swPaths = @(
        'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*',
        'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*',
        'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*'
    )
    $software = $swPaths | ForEach-Object { Get-ItemProperty $_ -ErrorAction SilentlyContinue } |
        Where-Object { $_.DisplayName } |
        Select-Object DisplayName, DisplayVersion, Publisher, InstallDate |
        Sort-Object DisplayName -Unique
    Write-Host ('[INFO] Total installed: ' + @($software).Count + ' applications')
    # Security-relevant software
    $secSoftware = $software | Where-Object { $_.DisplayName -match 'antivirus|defender|endpoint|security|EDR|SIEM|splunk|qualys|nessus|burp|wireshark|metasploit|nmap' }
    Write-Host ('[INFO] Security-relevant software: ' + @($secSoftware).Count)
    $secSoftware | ForEach-Object { Write-Host ('    [SEC] ' + $_.DisplayName + ' v' + $_.DisplayVersion + ' by ' + $_.Publisher) }
    Write-Host '[INFO] All software (first 20):'
    $software | Select-Object -First 20 | ForEach-Object { Write-Host ('    ' + $_.DisplayName + ' v' + $_.DisplayVersion) }
} catch { Write-Host ('[INFO] Installed software: ' + $_.Exception.Message) }

# Running processes with versions
Write-Host '[INFO] Step 2/5: Running processes with version info...'
try {
    $procs = Get-Process | Where-Object { $_.MainModule } | Select-Object Name, Id, @{N='Version';E={try{$_.MainModule.FileVersionInfo.FileVersion}catch{''}}}, @{N='Path';E={try{$_.MainModule.FileName}catch{''}}} | Sort-Object Name -Unique
    Write-Host ('[INFO] Running processes: ' + @($procs).Count)
    $procs | Select-Object -First 15 | ForEach-Object { Write-Host ('    ' + $_.Name.PadRight(25) + ' v' + $_.Version) }
} catch {}

# .NET Framework versions
Write-Host '[INFO] Step 3/5: .NET Framework versions...'
try {
    $dotnetPath = 'HKLM:\SOFTWARE\Microsoft\NET Framework Setup\NDP'
    $dotnetVersions = Get-ChildItem $dotnetPath -ErrorAction SilentlyContinue | ForEach-Object {
        $props = Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue
        if ($props.Install -eq 1 -or $props.Version) { $_.PSChildName + ' v' + $props.Version }
    } | Where-Object { $_ }
    Write-Host ('[INFO] .NET versions: ' + ($dotnetVersions -join ' | '))
    # .NET 4.5+
    $net45 = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full' -ErrorAction SilentlyContinue
    if ($net45) { Write-Host ('[INFO] .NET 4.5+ release: ' + $net45.Release + ' | version: ' + $net45.Version) }
} catch {}

# PowerShell version
Write-Host '[INFO] Step 4/5: PowerShell version and CLM status...'
Write-Host ('[INFO] PowerShell version: ' + $PSVersionTable.PSVersion.ToString())
Write-Host ('[INFO] Language mode: ' + $ExecutionContext.SessionState.LanguageMode)

# Windows features and roles
Write-Host '[INFO] Step 5/5: Windows optional features (relevant)...'
try {
    $features = Get-WindowsOptionalFeature -Online -ErrorAction SilentlyContinue | Where-Object { $_.State -eq 'Enabled' -and $_.FeatureName -match 'IIS|Hyper-V|WSL|Telnet|RDS|DirectAccess|VPN|NFS|SMB1' }
    Write-Host ('[INFO] Notable Windows features enabled: ' + @($features).Count)
    $features | ForEach-Object { Write-Host ('    ' + $_.FeatureName) }
} catch { Write-Host ('[INFO] Windows features: ' + $_.Exception.Message.Split([char]10)[0]) }
Write-Host '[SUCCESS] T1592.002 emulation completed'""",
    "cleanup_command": "Write-Host '[INFO] T1592.002 cleanup: no artefacts created - read-only registry and WMI queries'",
    "detection_rule": "Registry uninstall key bulk read + Get-Process mainmodule version + .NET registry + Get-WindowsOptionalFeature (T1592.002 software recon pattern)",
},

# ── T1592.003 ─────────────────────────────────────────────────────────────────
"T1592.003": {
    "description": (
        "Simulates enumerating victim firmware from a foothold machine (T1592.003). "
        "Queries BIOS/UEFI firmware version via WMI, checks for Secure Boot status, "
        "enumerates firmware update history, checks for known vulnerable firmware versions, "
        "and reads firmware-related registry keys. Also checks UEFI boot entries. Read-only."
    ),
    "required_tags": [],
    "command": r"""Write-Host '[START] T1592.003 - Firmware Enumeration (BIOS/UEFI/Secure Boot/firmware recon)'

# BIOS/UEFI firmware details
Write-Host '[INFO] Step 1/5: BIOS/UEFI firmware inventory...'
try {
    $bios = Get-WmiObject -Class Win32_BIOS -ErrorAction SilentlyContinue
    Write-Host ('[INFO] Manufacturer: ' + $bios.Manufacturer)
    Write-Host ('[INFO] BIOS Name: ' + $bios.Name)
    Write-Host ('[INFO] Version: ' + $bios.SMBIOSBIOSVersion)
    Write-Host ('[INFO] Release date: ' + $bios.ReleaseDate)
    Write-Host ('[INFO] SMBIOS major: ' + $bios.SMBIOSMajorVersion + '.' + $bios.SMBIOSMinorVersion)
    $cs = Get-WmiObject -Class Win32_ComputerSystem -ErrorAction SilentlyContinue
    Write-Host ('[INFO] System board: ' + $cs.Manufacturer + ' ' + $cs.Model)
    $board = Get-WmiObject -Class Win32_BaseBoard -ErrorAction SilentlyContinue
    if ($board) { Write-Host ('[INFO] Motherboard: ' + $board.Manufacturer + ' ' + $board.Product + ' | SN: ' + $board.SerialNumber.Trim()) }
} catch { Write-Host ('[INFO] BIOS WMI: ' + $_.Exception.Message) }

# Secure Boot status
Write-Host '[INFO] Step 2/5: Secure Boot and UEFI status...'
try {
    $secureBoot = Confirm-SecureBootUEFI -ErrorAction Stop
    Write-Host ('[INFO] Secure Boot: ENABLED=' + $secureBoot)
} catch { Write-Host ('[INFO] Secure Boot: not supported or access denied - ' + $_.Exception.Message.Split([char]10)[0]) }
try {
    $uefiPolicy = Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\SecureBoot\State' -ErrorAction SilentlyContinue
    if ($uefiPolicy) { Write-Host ('[INFO] UEFI Secure Boot state: ' + $uefiPolicy.UEFISecureBootEnabled) }
} catch {}

# Firmware update history
Write-Host '[INFO] Step 3/5: Firmware update history...'
try {
    $fwUpdates = Get-WmiObject -Namespace 'root\cimv2' -Query "SELECT * FROM Win32_ReliabilityRecords WHERE SourceName='Microsoft-Windows-WindowsUpdateClient'" -ErrorAction SilentlyContinue |
        Select-Object -First 5
    Write-Host ('[INFO] Recent firmware-related events: ' + @($fwUpdates).Count)
    $fwUpdates | ForEach-Object { Write-Host ('    ' + $_.TimeGenerated + ' | ' + $_.Message.Substring(0,[Math]::Min(100,$_.Message.Length))) }
} catch {}

# TPM firmware version
Write-Host '[INFO] Step 4/5: TPM firmware version...'
try {
    $tpm = Get-WmiObject -Namespace 'root\cimv2\Security\MicrosoftTpm' -Class Win32_Tpm -ErrorAction Stop
    Write-Host ('[INFO] TPM SpecVersion: ' + $tpm.SpecVersion)
    Write-Host ('[INFO] TPM ManufacturerId: ' + $tpm.ManufacturerId)
    Write-Host ('[INFO] TPM ManufacturerVersion: ' + $tpm.ManufacturerVersion)
    Write-Host ('[INFO] TPM PhysicalPresenceVersionInfo: ' + $tpm.PhysicalPresenceVersionInfo)
} catch { Write-Host ('[INFO] TPM: ' + $_.Exception.Message.Split([char]10)[0]) }

# UEFI boot entries
Write-Host '[INFO] Step 5/5: UEFI boot entries...'
try {
    $bcdedit = & bcdedit.exe /enum firmware 2>&1
    $bootEntries = $bcdedit | Where-Object { $_ -match 'description|device|path' }
    Write-Host ('[INFO] UEFI boot entries:')
    $bootEntries | Select-Object -First 10 | ForEach-Object { Write-Host ('    ' + $_.Trim()) }
} catch { Write-Host ('[INFO] bcdedit: ' + $_.Exception.Message.Split([char]10)[0]) }
Write-Host '[SUCCESS] T1592.003 emulation completed'""",
    "cleanup_command": "Write-Host '[INFO] T1592.003 cleanup: no artefacts created - read-only WMI and registry queries'",
    "detection_rule": "Win32_BIOS WMI + Confirm-SecureBootUEFI + Win32_Tpm query + bcdedit.exe firmware enum (T1592.003 firmware recon pattern)",
},

# ── T1592.004 ─────────────────────────────────────────────────────────────────
"T1592.004": {
    "description": (
        "Simulates enumerating victim client configurations from a foothold machine (T1592.004). "
        "Enumerates browser configuration, security settings, proxy config, certificate store, "
        "group policy applied settings, security product configurations (Defender exclusions, "
        "audit policy), AppLocker/WDAC policy, and PowerShell script block logging status. Read-only."
    ),
    "required_tags": [],
    "command": r"""Write-Host '[START] T1592.004 - Client Configurations (security config + policy + browser enumeration)'

# PowerShell and script execution policy
Write-Host '[INFO] Step 1/6: PowerShell configuration and execution policy...'
try {
    Write-Host ('[INFO] PS Version: ' + $PSVersionTable.PSVersion.ToString() + ' | Edition: ' + $PSVersionTable.PSEdition)
    Write-Host ('[INFO] Language mode: ' + $ExecutionContext.SessionState.LanguageMode)
    $execPolicies = Get-ExecutionPolicy -List | ForEach-Object { $_.Scope + '=' + $_.ExecutionPolicy }
    Write-Host ('[INFO] Execution policies: ' + ($execPolicies -join ' | '))
    $scriptBlockLogging = Get-ItemProperty 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\PowerShell\ScriptBlockLogging' -ErrorAction SilentlyContinue
    Write-Host ('[INFO] ScriptBlock logging: ' + $(if ($scriptBlockLogging.EnableScriptBlockLogging -eq 1) { 'ENABLED' } else { 'disabled' }))
    $transcription = Get-ItemProperty 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\PowerShell\Transcription' -ErrorAction SilentlyContinue
    Write-Host ('[INFO] PS Transcription: ' + $(if ($transcription.EnableTranscripting -eq 1) { 'ENABLED - output to: ' + $transcription.OutputDirectory } else { 'disabled' }))
} catch { Write-Host ('[INFO] PS config: ' + $_.Exception.Message.Split([char]10)[0]) }

# Defender configuration
Write-Host '[INFO] Step 2/6: Microsoft Defender configuration...'
try {
    $defPref = Get-MpPreference -ErrorAction Stop
    Write-Host ('[INFO] Defender RTP: ' + $defPref.DisableRealtimeMonitoring)
    Write-Host ('[INFO] Defender cloud: ' + $defPref.MAPSReporting + ' | CloudBlockLevel=' + $defPref.CloudBlockLevel)
    Write-Host ('[INFO] Defender exclusion paths: ' + @($defPref.ExclusionPath).Count)
    $defPref.ExclusionPath | Select-Object -First 5 | ForEach-Object { Write-Host ('    Excluded: ' + $_) }
    Write-Host ('[INFO] Defender exclusion processes: ' + @($defPref.ExclusionProcess).Count)
    $defPref.ExclusionProcess | Select-Object -First 5 | ForEach-Object { Write-Host ('    Excluded proc: ' + $_) }
} catch { Write-Host ('[INFO] Defender config: ' + $_.Exception.Message.Split([char]10)[0]) }

# AppLocker policy
Write-Host '[INFO] Step 3/6: AppLocker / WDAC policy...'
try {
    $appLockerSvc = Get-Service -Name AppIDSvc -ErrorAction SilentlyContinue
    Write-Host ('[INFO] AppLocker service (AppIDSvc): ' + $(if ($appLockerSvc) { $appLockerSvc.Status } else { 'not installed' }))
    $appLockerPolicy = Get-AppLockerPolicy -Effective -ErrorAction SilentlyContinue
    if ($appLockerPolicy) {
        Write-Host ('[INFO] AppLocker rules: ' + @($appLockerPolicy.RuleCollections).Count + ' rule collections')
        $appLockerPolicy.RuleCollections | ForEach-Object { Write-Host ('    Collection: ' + $_.RuleCollectionType + ' | EnforcementMode: ' + $_.EnforcementMode) }
    }
} catch { Write-Host ('[INFO] AppLocker: not configured or access denied') }

# Audit policy
Write-Host '[INFO] Step 4/6: Audit policy configuration...'
try {
    $auditOutput = & auditpol.exe /get /category:* 2>&1 | Where-Object { $_ -match 'Success|Failure' -and $_ -notmatch 'No Auditing' } | Select-Object -First 15
    Write-Host ('[INFO] Enabled audit categories:')
    $auditOutput | ForEach-Object { Write-Host ('    ' + $_.Trim()) }
} catch {}

# Browser security settings
Write-Host '[INFO] Step 5/6: Browser security configuration...'
$browserSecKeys = @(
    @{Key='HKCU:\SOFTWARE\Microsoft\Internet Explorer\Security'; Label='IE Security zones'},
    @{Key='HKLM:\SOFTWARE\Policies\Microsoft\Edge'; Label='Edge policy'},
    @{Key='HKLM:\SOFTWARE\Policies\Google\Chrome'; Label='Chrome policy'}
)
foreach ($bk in $browserSecKeys) {
    if (Test-Path $bk.Key -ErrorAction SilentlyContinue) {
        Write-Host ('[INFO] ' + $bk.Label + ' policy configured:')
        Get-ItemProperty $bk.Key -ErrorAction SilentlyContinue | Select-Object -Property * -ExcludeProperty PS* | ForEach-Object {
            $_.PSObject.Properties | Select-Object -First 5 | ForEach-Object { Write-Host ('    ' + $_.Name + ' = ' + $_.Value) }
        }
    }
}

# UAC configuration
Write-Host '[INFO] Step 6/6: UAC (User Account Control) configuration...'
try {
    $uac = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System' -ErrorAction SilentlyContinue
    Write-Host ('[INFO] UAC EnableLUA: ' + $uac.EnableLUA + ' | ConsentPromptBehaviorAdmin: ' + $uac.ConsentPromptBehaviorAdmin + ' | PromptOnSecureDesktop: ' + $uac.PromptOnSecureDesktop)
} catch {}
Write-Host '[SUCCESS] T1592.004 emulation completed'""",
    "cleanup_command": "Write-Host '[INFO] T1592.004 cleanup: no artefacts created - read-only registry and policy queries'",
    "detection_rule": "Get-MpPreference + Get-AppLockerPolicy + auditpol.exe + PS ScriptBlockLogging registry read + UAC policy read (T1592.004 client config recon pattern)",
},

}  # end SCRIPTS dict


def is_placeholder(cmd: str) -> bool:
    """Return True if the command is a placeholder (does nothing useful)."""
    return (
        "Executing reconnaissance operation" in cmd
        or cmd.strip() in (
            "Write-Host '[START] T1596.004 - CDNs'; Write-Host '[INFO] Executing reconnaissance operation'; Write-Host '[SUCCESS] T1596.004 completed successfully'",
        )
    )


def main():
    print(f"[START] Loading {FILENAME}...")
    with open(FILENAME, "r", encoding="utf-8") as f:
        data = json.load(f)

    updated = 0
    for script in data["scripts"]:
        tcode = script.get("tcode", "")
        if tcode not in SCRIPTS:
            continue

        spec = SCRIPTS[tcode]

        if spec.get("fix_only"):
            # Only add missing fields
            for key, val in spec.items():
                if key == "fix_only":
                    continue
                if key not in script:
                    script[key] = val
                    print(f"  [FIX] {tcode}: added missing field '{key}'")
            updated += 1
            continue

        # Check if placeholder
        current_cmd = script.get("command", "")
        if not is_placeholder(current_cmd):
            print(f"  [SKIP] {tcode}: already has real command")
            continue

        # Update all fields
        script["description"] = spec["description"]
        script["required_tags"] = spec["required_tags"]
        script["command"] = spec["command"]
        script["cleanup_command"] = spec["cleanup_command"]
        script["detection_rule"] = spec["detection_rule"]
        script["sentinel_connector"] = "Microsoft Defender for Endpoint"
        script["source"] = "excalibur"
        script["package_id"] = "excalibur-reconnaissance-v1"
        print(f"  [UPDATED] {tcode}: {script['name']}")
        updated += 1

    print(f"\n[INFO] Scripts updated: {updated}")
    print(f"[INFO] Writing {FILENAME}...")
    with open(FILENAME, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"[SUCCESS] Done. Validating JSON...")

    # Quick validation
    with open(FILENAME, "r", encoding="utf-8") as f:
        data2 = json.load(f)
    placeholders = [s for s in data2["scripts"] if is_placeholder(s.get("command", ""))]
    print(f"[INFO] Remaining placeholders: {len(placeholders)}")
    if placeholders:
        for p in placeholders:
            print(f"  [STILL PLACEHOLDER] {p['tcode']}: {p['name']}")
    else:
        print("[SUCCESS] All sub-technique scripts have been updated!")
    print(f"[INFO] Total scripts in pack: {len(data2['scripts'])}")


if __name__ == "__main__":
    main()
