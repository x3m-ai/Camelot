<#
.SYNOPSIS
    Merlino Defender for Endpoint Extractor - Export MDE recommendations and alerts to Merlino Universal Catalogue format

.DESCRIPTION
    This script extracts security recommendations and alerts from Microsoft Defender for Endpoint
    and converts them into Merlino's Universal Catalogue format for import into the Merlino Excel Add-in.
    
    The script:
    - Authenticates using Azure Service Principal (bypasses Conditional Access)
    - Retrieves data from Defender for Endpoint API:
      * Security Recommendations (Threat & Vulnerability Management)
      * Security Alerts (with native MITRE ATT&CK techniques)
      * Exposure and Configuration Scores
    - Generates two output files:
      1. Raw API response (legacy format)
      2. Merlino Universal Catalogue JSON (ready for import)
    
    The Catalogue format includes:
    - Recommendation/Alert metadata (name, type, priority/severity)
    - Source environment identifier (for multi-tenant tracking)
    - MITRE ATT&CK techniques (native from alerts, mapped for recommendations)
    - Full configuration in Data field
    
    NOTE: Alerts already include mitreTechniques from Microsoft API.
          Recommendations are mapped to MITRE techniques based on category and remediation type.

.PARAMETER TenantId
    Azure AD Tenant ID (Directory ID)
    Example: "af65d60d-6cea-4881-9ce3-caecd6f5023d"

.PARAMETER ClientId
    Service Principal Application (Client) ID
    Example: "9f19e91a-368d-4f84-8071-b2b54fb27cac"

.PARAMETER ClientSecret
    Service Principal Client Secret (Value, not Secret ID)
    Example: "<YOUR_CLIENT_SECRET_VALUE>"

.PARAMETER OutputFolder
    Directory where output files will be saved (default: script location)

.PARAMETER Source
    Source identifier for Catalogue records (e.g., "Microsoft Defender for Endpoint Production")
    If not provided, will prompt interactively

.EXAMPLE
    .\extract_defender_endpoint_policies.ps1
    Runs with default parameters and prompts for Source name

.EXAMPLE
    .\extract_defender_endpoint_policies.ps1 -TenantId "YOUR-TENANT-ID" -ClientId "YOUR-CLIENT-ID" -ClientSecret "YOUR-SECRET" -Source "MDE Production"
    Runs with specified credentials and Source name

.NOTES
    File Name      : extract_defender_endpoint_policies.ps1
    Author         : X3M.AI - Merlino Team
    Prerequisite   : PowerShell 5.1 or higher
   
    
    Required Azure AD App Registration Permissions:
    - SecurityRecommendation.Read.All (Application permission)
    - Alert.ReadWrite.All (Application permission)
    
    API Base URL: https://api.security.microsoft.com
    
    This script uses REST API directly via Invoke-RestMethod.
    No PowerShell modules are required.
    
.NOTES
    Author:  Nino Crudele
    LinkedIn: https://www.linkedin.com/in/ninocrudele
    Website:  https://merlino.x3m.ai
    License:  MIT

.LINK
    https://merlino-addin.x3m.ai
    https://learn.microsoft.com/en-us/defender-endpoint/api/apis-intro
#>

#Requires -Version 5.1

param(
  [string] $ClientId = "YOUR-CLIENT-ID-HERE",
  [string] $ClientSecret = "YOUR-CLIENT-SECRET-HERE",
  [string] $TenantId = "YOUR-TENANT-ID-HERE",
  [string] $OutputFolder = (Get-Location).Path,
  [string] $Source  # Will be prompted if not provided
)

# ---- Helper Functions ----

function Get-AccessToken {
  param(
    [Parameter(Mandatory)][string]$TenantId,
    [Parameter(Mandatory)][string]$ClientId,
    [Parameter(Mandatory)][string]$ClientSecret
  )

  Write-Host "`nAuthenticating with Service Principal..." -ForegroundColor Cyan
  Write-Host "Client ID: $ClientId" -ForegroundColor Gray
  Write-Host "Tenant ID: $TenantId" -ForegroundColor Gray

  $tokenUrl = "https://login.microsoftonline.com/$TenantId/oauth2/v2.0/token"
  Write-Host "Token URI: $tokenUrl" -ForegroundColor Gray

  $body = @{
    client_id     = $ClientId
    scope         = "https://api.security.microsoft.com/.default"
    client_secret = $ClientSecret
    grant_type    = "client_credentials"
  }

  try {
    Write-Host "Sending authentication request..." -ForegroundColor Yellow
    $response = Invoke-RestMethod -Method Post -Uri $tokenUrl -Body $body -ContentType "application/x-www-form-urlencoded"
    Write-Host "Token received successfully" -ForegroundColor Green
    return $response.access_token
  }
  catch {
    Write-Host "[ERROR] Authentication failed: $($_.Exception.Message)" -ForegroundColor Red
    throw
  }
}

function Invoke-DefenderApi {
  param(
    [Parameter(Mandatory)][string]$Uri,
    [Parameter(Mandatory)][string]$AccessToken
  )

  $headers = @{
    "Authorization" = "Bearer $AccessToken"
    "Content-Type" = "application/json"
  }

  try {
    $response = Invoke-RestMethod -Method Get -Uri $Uri -Headers $headers
    return $response
  }
  catch {
    Write-Host "  [!] API call failed: $($_.Exception.Message)" -ForegroundColor Red
    throw
  }
}

function Get-AllDefenderPages {
  param(
    [Parameter(Mandatory)][string]$InitialUri,
    [Parameter(Mandatory)][string]$AccessToken
  )

  $allResults = @()
  $nextUri = $InitialUri

  do {
    Write-Host "  Fetching: $nextUri" -ForegroundColor DarkGray
    $response = Invoke-DefenderApi -Uri $nextUri -AccessToken $AccessToken
    
    if ($response.value) {
      $allResults += $response.value
      Write-Host "    Found $($response.value.Count) items" -ForegroundColor DarkGray
    }
    
    $nextUri = $response.'@odata.nextLink'
  } while ($nextUri)

  return $allResults
}

function Get-DefenderEndpointRecommendations {
  param([Parameter(Mandatory)][string]$AccessToken)
  
  Write-Host "Retrieving Defender for Endpoint security recommendations..." -ForegroundColor Yellow
  try {
    $recommendations = Get-AllDefenderPages -InitialUri "https://api.security.microsoft.com/api/recommendations" -AccessToken $AccessToken
    Write-Host "Found $($recommendations.Count) recommendations" -ForegroundColor Green
    return $recommendations
  }
  catch {
    Write-Host "  [!] Skipped - Error: $($_.Exception.Message)" -ForegroundColor DarkYellow
    return @()
  }
}

function Get-DefenderEndpointAlerts {
  param([Parameter(Mandatory)][string]$AccessToken)
  
  Write-Host "Retrieving Defender for Endpoint security alerts..." -ForegroundColor Yellow
  try {
    # Get recent active alerts
    $alerts = Get-AllDefenderPages -InitialUri "https://api.security.microsoft.com/api/alerts?`$filter=status ne 'Resolved'" -AccessToken $AccessToken
    Write-Host "Found $($alerts.Count) active alerts" -ForegroundColor Green
    return $alerts
  }
  catch {
    Write-Host "  [!] Skipped - Error: $($_.Exception.Message)" -ForegroundColor DarkYellow
    return @()
  }
}

function Get-DefenderEndpointScores {
  param([Parameter(Mandatory)][string]$AccessToken)
  
  Write-Host "Retrieving Defender for Endpoint security scores..." -ForegroundColor Yellow
  $scores = @{}
  
  try {
    Write-Host "  Getting Exposure Score..." -ForegroundColor DarkGray
    $exposureScore = Invoke-DefenderApi -Uri "https://api.security.microsoft.com/api/exposureScore" -AccessToken $AccessToken
    $scores.ExposureScore = $exposureScore.score
    Write-Host "    Exposure Score: $($exposureScore.score)" -ForegroundColor Green
  }
  catch {
    Write-Host "    [!] Could not retrieve Exposure Score" -ForegroundColor DarkYellow
    $scores.ExposureScore = "N/A"
  }
  
  try {
    Write-Host "  Getting Configuration Score..." -ForegroundColor DarkGray
    $configScore = Invoke-DefenderApi -Uri "https://api.security.microsoft.com/api/configurationScore" -AccessToken $AccessToken
    $scores.ConfigurationScore = $configScore.score
    Write-Host "    Configuration Score: $($configScore.score)" -ForegroundColor Green
  }
  catch {
    Write-Host "    [!] Could not retrieve Configuration Score" -ForegroundColor DarkYellow
    $scores.ConfigurationScore = "N/A"
  }
  
  return $scores
}

function Get-MitreTCodesForRecommendation {
  param(
    [string]$RecommendationCategory,
    [string]$RemediationType,
    [string]$ProductName
  )
  
  # Map Defender for Endpoint recommendations to MITRE ATT&CK techniques
  # Based on recommendation category and remediation type
  
  # Application updates/patches
  if ($RemediationType -eq "Update" -or $RecommendationCategory -eq "Application") {
    return "T1068,T1203,T1210"  # Exploitation for Privilege Escalation, Client Execution, Remote Services
  }
  
  # Security configurations
  if ($RecommendationCategory -eq "SecurityControl" -or $RecommendationCategory -eq "Accounts") {
    return "T1078,T1110,T1556"  # Valid Accounts, Brute Force, Modify Authentication Process
  }
  
  # Antivirus/EDR
  if ($ProductName -like "*defender*" -or $ProductName -like "*antivirus*") {
    return "T1562.001,T1070,T1036"  # Disable Security Tools, Indicator Removal, Masquerading
  }
  
  # Firewall
  if ($ProductName -like "*firewall*") {
    return "T1562.004,T1090,T1095"  # Disable Firewall, Proxy, Non-Application Layer Protocol
  }
  
  # OS updates
  if ($ProductName -like "*windows*" -and $RemediationType -eq "Update") {
    return "T1068,T1211,T1574"  # Exploitation for Privilege Escalation, Defense Evasion, Hijack Execution Flow
  }
  
  # BitLocker/Encryption
  if ($ProductName -like "*bitlocker*" -or $ProductName -like "*encryption*") {
    return "T1486,T1005,T1561"  # Data Encrypted for Impact, Data from Local System, Disk Wipe
  }
  
  # Network security
  if ($RecommendationCategory -like "*Network*") {
    return "T1071,T1090,T1571"  # Application Layer Protocol, Proxy, Non-Standard Port
  }
  
  # Default for other recommendations
  return "T1068,T1203"  # Generic exploitation techniques
}

function ConvertTo-MerlinoCatalogue {
  param(
    [array]$Items,
    [string]$Source,
    [string]$ItemType
  )

  $catalogueRecords = @()

  foreach ($item in $Items) {
    # Determine priority based on severity/score
    $priority = "Medium"
    
    if ($item.severity -eq "High" -or $item.severityScore -gt 7) {
      $priority = "High"
    } elseif ($item.severity -eq "Low" -or $item.severityScore -lt 4) {
      $priority = "Low"
    }
    
    # Determine if item is active/enabled
    $isEnabled = $true
    if ($item.status -eq "Resolved" -or $item.status -eq "Inactive") {
      $isEnabled = $false
    }
    
    # Determine name
    $itemName = "Unnamed Item"
    if ($ItemType -eq "Recommendation") {
      if ($item.recommendationName) { 
        $itemName = $item.recommendationName 
      } elseif ($item.productName) {
        $itemName = "Update $($item.productName)"
      }
    } elseif ($ItemType -eq "Alert") {
      if ($item.title) {
        $itemName = $item.title
      } elseif ($item.alertType) {
        $itemName = $item.alertType
      }
    }
    
    # Get MITRE techniques
    $tcodes = ""
    if ($ItemType -eq "Alert" -and $item.mitreTechniques) {
      # Alerts already have MITRE techniques from API
      $tcodes = $item.mitreTechniques -join ","
    } elseif ($ItemType -eq "Recommendation") {
      # Map recommendations to MITRE techniques
      $tcodes = Get-MitreTCodesForRecommendation -RecommendationCategory $item.recommendationCategory -RemediationType $item.remediationType -ProductName $item.productName
    }
    
    # Prepare description
    $description = ""
    if ($item.description) {
      $description = $item.description
    } elseif ($item.recommendationCategory) {
      $description = "Defender for Endpoint $($item.recommendationCategory) recommendation"
    } else {
      $description = "Defender for Endpoint $ItemType"
    }
    
    # Calculate validation score for recommendations
    $validationScore = ""
    if ($ItemType -eq "Recommendation" -and $item.exposedMachinesCount -and $item.totalMachineCount) {
      if ($item.totalMachineCount -gt 0) {
        $coverage = [math]::Round((($item.totalMachineCount - $item.exposedMachinesCount) / $item.totalMachineCount) * 100, 2)
        $validationScore = "$coverage%"
      }
    }

    # Build Catalogue record (13 fields - Universal Import Schema v1.0)
    $catalogueRecord = [pscustomobject]@{
      Pick = $false
      CrossPick = 0
      Name = $itemName
      Source = $Source
      Priority = $priority
      Enabled = $isEnabled
      Validation_Score = $validationScore
      Tests = 0
      Expected_Tests = 0
      Tests_Validated = 0
      TCodes = $tcodes
      Description = $description
      Notes = "Type: $ItemType | Category: $($item.recommendationCategory)$($item.category)"
      Data = ($item | ConvertTo-Json -Depth 10 -Compress)
    }

    $catalogueRecords += $catalogueRecord
  }

  return $catalogueRecords
}

function Sanitize-FileName {
  param([string]$s)
  return $s -replace '[\\/:*?"<>|]', '-'
}

# ---- Main Script ----
Write-Host "=== Merlino Defender for Endpoint Extractor (Service Principal) ===" -ForegroundColor Green
Write-Host "Using Service Principal authentication - bypassing Conditional Access!" -ForegroundColor Yellow

# Prompt for Source if not provided
if (-not $Source) {
  Write-Host "`n=== Source Name Configuration ===" -ForegroundColor Cyan
  Write-Host "The 'Source' field helps distinguish between different environments in Merlino.`n" -ForegroundColor White
  Write-Host "Examples:" -ForegroundColor Yellow
  Write-Host "  - 'Microsoft Defender for Endpoint Production'  (production environment)" -ForegroundColor Gray
  Write-Host "  - 'Microsoft Defender for Endpoint Development' (dev/test environment)" -ForegroundColor Gray
  Write-Host "  - 'MDE - Customer XYZ'                          (customer-specific)`n" -ForegroundColor Gray
  Write-Host "This allows you to:" -ForegroundColor White
  Write-Host "  [CHECK] Compare recommendations between Development and Production" -ForegroundColor Green
  Write-Host "  [CHECK] Filter Catalogue by environment" -ForegroundColor Green
  Write-Host "  [CHECK] Track security posture changes across environments`n" -ForegroundColor Green
  
  $Source = Read-Host "Enter Source name (press ENTER for default 'Microsoft Defender for Endpoint')"
  if ([string]::IsNullOrWhiteSpace($Source)) {
    $Source = "Microsoft Defender for Endpoint"
  }
  Write-Host "Using default: $Source`n" -ForegroundColor Cyan
}

# Get Access Token
$accessToken = Get-AccessToken -TenantId $TenantId -ClientId $ClientId -ClientSecret $ClientSecret
Write-Host "Successfully authenticated!`n" -ForegroundColor Green

Write-Host "Fetching Defender for Endpoint data...`n" -ForegroundColor Cyan

# Get all data
$recommendations = Get-DefenderEndpointRecommendations -AccessToken $accessToken
$alerts = Get-DefenderEndpointAlerts -AccessToken $accessToken
$scores = Get-DefenderEndpointScores -AccessToken $accessToken

# Summary
Write-Host "`n=== SUMMARY ===" -ForegroundColor Cyan
Write-Host "Security Recommendations: $($recommendations.Count)" -ForegroundColor White
Write-Host "Active Alerts: $($alerts.Count)" -ForegroundColor White
Write-Host "Exposure Score: $($scores.ExposureScore)" -ForegroundColor White
Write-Host "Configuration Score: $($scores.ConfigurationScore)" -ForegroundColor White
Write-Host "`nTotal items collected: $($recommendations.Count + $alerts.Count)" -ForegroundColor Green

# Combine all configurations with type marker
$allConfigurations = @()

foreach ($rec in $recommendations) {
  $rec | Add-Member -MemberType NoteProperty -Name "_ItemType" -Value "Recommendation" -Force
  $allConfigurations += $rec
}

foreach ($alert in $alerts) {
  $alert | Add-Member -MemberType NoteProperty -Name "_ItemType" -Value "Alert" -Force
  $allConfigurations += $alert
}

if ($allConfigurations.Count -eq 0) {
  Write-Host "`n[WARNING] No data retrieved from Defender for Endpoint!" -ForegroundColor Yellow
  Write-Host "This could mean:" -ForegroundColor Yellow
  Write-Host "  - Defender for Endpoint is not configured in this tenant" -ForegroundColor Gray
  Write-Host "  - Service Principal lacks required permissions" -ForegroundColor Gray
  Write-Host "  - No active recommendations or alerts in the tenant" -ForegroundColor Gray
  exit 1
}

Write-Host "`n[SUCCESS] Successfully extracted Defender for Endpoint data!" -ForegroundColor Green
Write-Host "  Data includes: Recommendations, Alerts, Security Scores" -ForegroundColor Gray
Write-Host "`nRequired permissions:" -ForegroundColor Yellow
Write-Host "  - SecurityRecommendation.Read.All" -ForegroundColor Gray
Write-Host "  - Alert.ReadWrite.All" -ForegroundColor Gray

# Generate timestamp and sanitized tenant name
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$tenantName = "Tenant-$TenantId"
$tenantSafe = Sanitize-FileName -s $tenantName

# Legacy format
$legacyFile = Join-Path $OutputFolder ("defender-endpoint-configs-{0}-{1}.json" -f $tenantSafe, $stamp)
Write-Host "`nWriting legacy Defender for Endpoint configurations JSON to: $legacyFile" -ForegroundColor Green
$allConfigurations | ConvertTo-Json -Depth 10 | Out-File -FilePath $legacyFile -Encoding UTF8

# Merlino Universal Schema format
Write-Host "Converting to Merlino Universal Schema format..." -ForegroundColor Cyan
$catalogueData = @()

# Process each item type separately
$itemTypes = $allConfigurations | Select-Object -Unique -ExpandProperty _ItemType
foreach ($itemType in $itemTypes) {
  $items = $allConfigurations | Where-Object { $_._ItemType -eq $itemType }
  $catalogueData += ConvertTo-MerlinoCatalogue -Items $items -Source $Source -ItemType $itemType
}

$universalSchema = @{
  schema = @{
    version = "1.0"
    source = "Microsoft Defender for Endpoint"
    generatedAt = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
    tenantId = $TenantId
    exposureScore = $scores.ExposureScore
    configurationScore = $scores.ConfigurationScore
  }
  data = $catalogueData
}

$universalFile = Join-Path $OutputFolder ("merlino-catalogue-defender-endpoint-{0}-{1}.json" -f $tenantSafe, $stamp)
Write-Host "Writing Merlino Universal Schema to: $universalFile" -ForegroundColor Green
$universalSchema | ConvertTo-Json -Depth 10 | Out-File -FilePath $universalFile -Encoding UTF8

# ---- Summary ----
Write-Host "`n=== SUCCESS ===" -ForegroundColor Green
Write-Host "Tenant: $TenantId" -ForegroundColor Cyan
Write-Host "Source: $Source" -ForegroundColor Cyan
Write-Host "Items exported: $($allConfigurations.Count)" -ForegroundColor Cyan
Write-Host "  - Recommendations: $($recommendations.Count)" -ForegroundColor Gray
Write-Host "  - Alerts: $($alerts.Count)" -ForegroundColor Gray
Write-Host "`nFiles created:" -ForegroundColor Cyan
Write-Host "  Legacy (raw API):   $legacyFile" -ForegroundColor White
Write-Host "  Catalogue (import): $universalFile" -ForegroundColor White
Write-Host "`nReady to import in Merlino Catalogue!" -ForegroundColor Green
Write-Host "Note: Alerts include native MITRE techniques from Microsoft. Recommendations are auto-mapped." -ForegroundColor Yellow
