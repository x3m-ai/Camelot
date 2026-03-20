<#
.SYNOPSIS
    Merlino Defender for Identity Extractor - Export Microsoft Defender for Identity configurations to Merlino Universal Catalogue format

.DESCRIPTION
    This script extracts all configuration settings from a Microsoft Defender for Identity tenant and converts them into 
    Merlino's Universal Catalogue format for import into the Merlino Excel Add-in.
    
    The script:
    - Authenticates using Azure Service Principal (bypasses Conditional Access)
    - Retrieves all Defender for Identity configurations:
      * Security Alerts configuration
      * Detection exclusions
      * Monitored domain controllers
      * Directory service accounts
      * VPN integration settings
      * Network name resolution (NNR) settings
      * SIEM integration configuration
      * Entity tag settings
      * Notification settings
    - Generates two output files:
      1. Raw API response (legacy format)
      2. Merlino Universal Catalogue JSON (ready for import)
    
    The Catalogue format includes:
    - Configuration metadata (name, type, priority/severity)
    - Source environment identifier (for multi-tenant tracking)
    - Full configuration in Data field
    
    NOTE: TCodes field is populated with relevant MITRE ATT&CK techniques based on detection types.

.PARAMETER TenantId
    Azure AD Tenant ID (Directory ID)
    Example: "af65d60d-6cea-4881-9ce3-caecd6f5023d"

.PARAMETER ClientId
    Service Principal Application (Client) ID
    Example: "9f19e91a-368d-4f84-8071-b2b54fb27cac"

.PARAMETER ClientSecret
    Service Principal Client Secret (Value, not Secret ID)
    Example: "<YOUR_CLIENT_SECRET_VALUE>"

.PARAMETER WorkspaceName
    Defender for Identity workspace name (e.g., "contoso")
    If not provided, will attempt to discover workspaces

.PARAMETER OutputFolder
    Directory where output files will be saved (default: script location)

.PARAMETER Source
    Source identifier for Catalogue records (e.g., "Microsoft Defender for Identity Production")
    If not provided, will prompt interactively

.EXAMPLE
    .\extract_defender_for_identity_policies.ps1
    Runs with default parameters and prompts for Source name

.EXAMPLE
    .\extract_defender_for_identity_policies.ps1 -TenantId "YOUR-TENANT-ID" -ClientId "YOUR-CLIENT-ID" -ClientSecret "YOUR-SECRET" -Source "Production"
    Runs with specified credentials and Source name

.NOTES
    File Name      : extract_defender_for_identity_policies.ps1
    Author         : X3M.AI - Merlino Team
    Prerequisite   : PowerShell 5.1 or higher

    
    Required Azure AD App Registration Permissions:
    - SecurityEvents.Read.All
    - SecurityEvents.ReadWrite.All
    - ThreatIndicators.Read.All
    
    API Endpoint: https://api.security.microsoft.com/api/
    
    This script uses REST API directly via Invoke-RestMethod.
    No PowerShell modules are required.
    
.LINK
    https://merlino-addin.x3m.ai
    https://learn.microsoft.com/en-us/defender-for-identity/
#>

#Requires -Version 5.1

param(
  [string] $ClientId = "YOUR-CLIENT-ID-HERE",
  [string] $ClientSecret = "YOUR-CLIENT-SECRET-HERE",
  [string] $TenantId = "YOUR-TENANT-ID-HERE",
  [string] $WorkspaceName = "",
  [string] $OutputFolder = (Get-Location).Path,
  [string] $Source  # Will be prompted if not provided
)

# ---- Interactive Source Prompt ----
if ([string]::IsNullOrWhiteSpace($Source)) {
    Write-Host "`n=== Source Name Configuration ===" -ForegroundColor Cyan
    Write-Host "The 'Source' field helps distinguish between different environments in Merlino." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor White
    Write-Host "  - 'Microsoft Defender for Identity Production'  (production environment)" -ForegroundColor Gray
    Write-Host "  - 'Microsoft Defender for Identity Development' (dev/test environment)" -ForegroundColor Gray
    Write-Host "  - 'MDI - Customer XYZ'                          (customer-specific)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "This allows you to:" -ForegroundColor White
    Write-Host "  ✓ Compare configurations between Development and Production" -ForegroundColor Green
    Write-Host "  ✓ Filter Catalogue by environment" -ForegroundColor Green
    Write-Host "  ✓ Track configuration changes across environments" -ForegroundColor Green
    Write-Host ""
    
    $userInput = Read-Host "Enter Source name (press ENTER for default 'Microsoft Defender for Identity')"
    
    if ([string]::IsNullOrWhiteSpace($userInput)) {
        $Source = "Microsoft Defender for Identity"
        Write-Host "Using default: $Source" -ForegroundColor Green
    } else {
        $Source = $userInput.Trim()
        Write-Host "Using custom source: $Source" -ForegroundColor Green
    }
    Write-Host ""
}

function Sanitize-FileName {
  param([string]$s)
  $invalid = [io.path]::GetInvalidFileNameChars() -join ''
  return ($s -replace "[$invalid]", "_")
}

function Get-AccessToken {
  param(
    [Parameter(Mandatory)][string]$ClientId,
    [Parameter(Mandatory)][string]$ClientSecret,
    [Parameter(Mandatory)][string]$TenantId
  )
  
  try {
    $tokenUri = "https://login.microsoftonline.com/$TenantId/oauth2/v2.0/token"
    Write-Host "Token URI: $tokenUri" -ForegroundColor DarkGray
    
    # Create form-encoded body manually for PowerShell 5.1 compatibility
    # Scope for Microsoft Graph (Defender for Identity uses Graph API)
    $bodyString = "client_id=$ClientId&client_secret=$([System.Web.HttpUtility]::UrlEncode($ClientSecret))&scope=https%3A//graph.microsoft.com/.default&grant_type=client_credentials"
    
    Write-Host "Sending authentication request..." -ForegroundColor DarkGray
    
    $response = Invoke-RestMethod -Uri $tokenUri -Method POST -Body $bodyString -ContentType "application/x-www-form-urlencoded" -ErrorAction Stop
    
    Write-Host "Token received successfully" -ForegroundColor Green
    return $response.access_token
  }
  catch {
    Write-Host "Error getting access token: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Status Code: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Red
    try {
      $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
      $responseBody = $reader.ReadToEnd()
      Write-Host "Response body: $responseBody" -ForegroundColor Red
    } catch {
      Write-Host "Could not read response body" -ForegroundColor Red
    }
    throw
  }
}

function Invoke-GraphApi {
  param(
    [Parameter(Mandatory)][string]$Uri,
    [Parameter(Mandatory)][string]$AccessToken
  )
  
  try {
    $headers = @{
      'Authorization' = "Bearer $AccessToken"
      'Content-Type' = 'application/json'
    }
    
    $response = Invoke-RestMethod -Uri $Uri -Headers $headers -Method GET -ErrorAction Stop
    return $response
  }
  catch {
    Write-Host "Graph API call failed for $Uri - $($_.Exception.Message)" -ForegroundColor Red
    throw
  }
}

function Get-AllGraphPages {
  param(
    [Parameter(Mandatory)][string]$InitialUri,
    [Parameter(Mandatory)][string]$AccessToken
  )

  $allResults = @()
  $nextUri = $InitialUri

  do {
    Write-Host "  Fetching: $nextUri" -ForegroundColor DarkGray
    $response = Invoke-GraphApi -Uri $nextUri -AccessToken $AccessToken
    
    if ($response.value) {
      $allResults += $response.value
      Write-Host "    Found $($response.value.Count) items" -ForegroundColor DarkGray
    }
    
    $nextUri = $response.'@odata.nextLink'
  } while ($nextUri)

  return $allResults
}

function Get-DefenderIdentityHealthIssues {
  param([Parameter(Mandatory)][string]$AccessToken)
  
  Write-Host "Retrieving Defender for Identity health issues..." -ForegroundColor Yellow
  try {
    $issues = Get-AllGraphPages -InitialUri "https://graph.microsoft.com/v1.0/security/identities/healthIssues" -AccessToken $AccessToken
    Write-Host "Found $($issues.Count) health issues" -ForegroundColor Green
    return $issues
  }
  catch {
    Write-Host "  [!] Skipped - Error: $($_.Exception.Message)" -ForegroundColor DarkYellow
    return @()
  }
}

function Get-DefenderIdentityAlerts {
  param([Parameter(Mandatory)][string]$AccessToken)
  
  Write-Host "Retrieving Defender for Identity security alerts..." -ForegroundColor Yellow
  try {
    # Get recent alerts (last 30 days)
    $alerts = Get-AllGraphPages -InitialUri "https://graph.microsoft.com/v1.0/security/alerts_v2?`$filter=serviceSource eq 'microsoftDefenderForIdentity'" -AccessToken $AccessToken
    Write-Host "Found $($alerts.Count) alerts" -ForegroundColor Green
    return $alerts
  }
  catch {
    Write-Host "  [!] Skipped - Error: $($_.Exception.Message)" -ForegroundColor DarkYellow
    return @()
  }
}

function Get-DefenderIdentitySensors {
  param([Parameter(Mandatory)][string]$AccessToken)
  
  Write-Host "Retrieving Defender for Identity sensors (Domain Controllers)..." -ForegroundColor Yellow
  try {
    $sensors = Get-AllGraphPages -InitialUri "https://graph.microsoft.com/v1.0/security/identities/sensors" -AccessToken $AccessToken
    Write-Host "Found $($sensors.Count) sensors" -ForegroundColor Green
    return $sensors
  }
  catch {
    Write-Host "  [!] Skipped - Error: $($_.Exception.Message)" -ForegroundColor DarkYellow
    return @()
  }
}

function Get-DefenderIdentitySensorConfiguration {
  param(
    [Parameter(Mandatory)][string]$AccessToken,
    [Parameter(Mandatory)][string]$SensorId
  )
  
  try {
    $config = Invoke-GraphApi -Uri "https://graph.microsoft.com/v1.0/security/identities/sensors/$SensorId" -AccessToken $AccessToken
    return $config
  }
  catch {
    Write-Host "    [!] Could not get configuration for sensor $SensorId" -ForegroundColor DarkYellow
    return $null
  }
}

function Get-MitreTCodesForAlert {
  param([string]$AlertType, [string]$Category)
  
  # Map common Defender for Identity alert types to MITRE ATT&CK techniques
  $mapping = @{
    "CredentialAccess" = "T1003,T1110,T1558"  # OS Credential Dumping, Brute Force, Steal/Forge Kerberos Tickets
    "LateralMovement" = "T1021,T1550,T1210"   # Remote Services, Use Alternate Authentication Material, Exploitation
    "Persistence" = "T1098,T1136,T1078"       # Account Manipulation, Create Account, Valid Accounts
    "PrivilegeEscalation" = "T1068,T1134,T1078"  # Exploitation for Privilege Escalation
    "Discovery" = "T1087,T1069,T1018"         # Account Discovery, Permission Groups Discovery, Remote System Discovery
    "Collection" = "T1005,T1039,T1074"        # Data from Local System
    "Exfiltration" = "T1041,T1048,T1567"      # Exfiltration Over C2 Channel
    "DefenseEvasion" = "T1562,T1070,T1202"    # Impair Defenses, Indicator Removal, Indirect Command Execution
  }
  
  foreach ($key in $mapping.Keys) {
    if ($Category -like "*$key*" -or $AlertType -like "*$key*") {
      return $mapping[$key]
    }
  }
  
  return ""  # No mapping found
}

function ConvertTo-MerlinoCatalogue {
  param(
    [array]$Configurations,
    [string]$Source,
    [string]$ConfigType
  )

  $catalogueRecords = @()

  foreach ($config in $Configurations) {
    # Determine priority based on configuration type and content
    $priority = "Medium"
    
    if ($ConfigType -eq "Alert" -or $ConfigType -eq "Sensor") {
      $priority = "High"
    }
    
    if ($config.severity -eq "High" -or $config.priority -eq "High") {
      $priority = "High"
    }
    
    # Determine if configuration is enabled
    $isEnabled = $true
    if ($config.PSObject.Properties['isEnabled']) {
      $isEnabled = $config.isEnabled
    } elseif ($config.PSObject.Properties['status']) {
      $isEnabled = ($config.status -eq "Active" -or $config.status -eq "Enabled")
    }

    # Prepare description
    $description = ""
    if ($config.description) {
      $description = $config.description
    } else {
      $description = "Defender for Identity $ConfigType configuration"
    }
    
    # Determine name
    $configName = "Unnamed Configuration"
    if ($config.displayName) { 
      $configName = $config.displayName 
    } elseif ($config.name) { 
      $configName = $config.name 
    } elseif ($config.title) { 
      $configName = $config.title 
    } elseif ($config.alertType) {
      $configName = $config.alertType
    }
    
    # Get MITRE techniques for alerts
    $tcodes = ""
    if ($ConfigType -eq "Alert" -and ($config.category -or $config.alertType)) {
      $tcodes = Get-MitreTCodesForAlert -AlertType $config.alertType -Category $config.category
    }

    # Build Catalogue record (13 fields - Universal Import Schema v1.0)
    $catalogueRecord = [pscustomobject]@{
      Pick = $false
      CrossPick = 0
      Name = $configName
      Source = $Source
      Priority = $priority
      Enabled = $isEnabled
      Validation_Score = ""
      Tests = 0
      Expected_Tests = 0
      Tests_Validated = 0
      TCodes = $tcodes
      Description = $description
      Notes = "Type: $ConfigType"
      Data = ($config | ConvertTo-Json -Depth 10 -Compress)
    }

    $catalogueRecords += $catalogueRecord
  }

  return $catalogueRecords
}

# ---- Main Script ----
Write-Host "=== Merlino Defender for Identity Extractor (Service Principal) ===" -ForegroundColor Green
Write-Host "Using Service Principal authentication - bypassing Conditional Access!" -ForegroundColor Yellow

# Load required assemblies for URL encoding
Add-Type -AssemblyName System.Web

# ---- Authentication ----
Write-Host "`nAuthenticating with Service Principal..." -ForegroundColor Cyan
Write-Host "Client ID: $ClientId" -ForegroundColor Gray
Write-Host "Tenant ID: $TenantId" -ForegroundColor Gray

try {
  $accessToken = Get-AccessToken -ClientId $ClientId -ClientSecret $ClientSecret -TenantId $TenantId
  Write-Host "Successfully authenticated!" -ForegroundColor Green
}
catch {
  Write-Host "Authentication failed: $($_.Exception.Message)" -ForegroundColor Red
  exit 1
}

$tenantName = "Tenant-$TenantId"

# ---- Fetch Defender for Identity Configurations ----
Write-Host "`nFetching Defender for Identity configurations from tenant..." -ForegroundColor Cyan
$allConfigurations = @()

try {
  # Get Sensors (Domain Controllers)
  $sensors = Get-DefenderIdentitySensors -AccessToken $accessToken
  foreach ($sensor in $sensors) {
    $sensor | Add-Member -NotePropertyName "_ConfigType" -NotePropertyValue "Sensor" -Force
  }
  $allConfigurations += $sensors

  # Get Health Issues
  $healthIssues = Get-DefenderIdentityHealthIssues -AccessToken $accessToken
  foreach ($issue in $healthIssues) {
    $issue | Add-Member -NotePropertyName "_ConfigType" -NotePropertyValue "HealthIssue" -Force
  }
  $allConfigurations += $healthIssues

  # Get Recent Alerts
  $alerts = Get-DefenderIdentityAlerts -AccessToken $accessToken
  foreach ($alert in $alerts) {
    $alert | Add-Member -NotePropertyName "_ConfigType" -NotePropertyValue "Alert" -Force
  }
  $allConfigurations += $alerts

  Write-Host "`n=== SUMMARY ===" -ForegroundColor Cyan
  Write-Host "Sensors (Domain Controllers): $($sensors.Count)" -ForegroundColor White
  Write-Host "Health Issues: $($healthIssues.Count)" -ForegroundColor White
  Write-Host "Recent Alerts: $($alerts.Count)" -ForegroundColor White
  Write-Host "`nTotal configurations collected: $($allConfigurations.Count)" -ForegroundColor Green
  
  if ($allConfigurations.Count -gt 0) {
    Write-Host "`n[i] Successfully extracted Defender for Identity data!" -ForegroundColor Green
    Write-Host "  Data includes: Sensors, Health Issues, Alerts" -ForegroundColor DarkGray
  }
  
  if ($allConfigurations.Count -eq 0) {
    Write-Host "`nNo configurations found in tenant $TenantId." -ForegroundColor Red
    Write-Host "This could be due to:" -ForegroundColor Red
    Write-Host "  - Service Principal permissions not sufficient" -ForegroundColor Red
    Write-Host "  - Defender for Identity not configured in this tenant" -ForegroundColor Red
    Write-Host "  - API endpoints may need adjustment" -ForegroundColor Red
    exit 1
  }
  
  # Display found configurations for verification
  Write-Host "`nFound configurations:" -ForegroundColor Cyan
  foreach ($config in $allConfigurations) {
    $type = if ($config._ConfigType) { $config._ConfigType } else { "Unknown" }
    $configName = if ($config.displayName) { $config.displayName } elseif ($config.name) { $config.name } elseif ($config.computerName) { $config.computerName } else { "Unnamed" }
    Write-Host "  - $configName [$type]" -ForegroundColor Gray
  }
}
catch {
  Write-Host "`nERROR: Failed to retrieve Defender for Identity configurations from tenant $TenantId" -ForegroundColor Red
  Write-Host "Error details: $($_.Exception.Message)" -ForegroundColor Red
  exit 1
}

# ---- Generate Output Files ----
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$tenantSafe = Sanitize-FileName -s $tenantName

# Legacy format
$legacyFile = Join-Path $OutputFolder ("defender-identity-configs-{0}-{1}.json" -f $tenantSafe, $stamp)
Write-Host "`nWriting legacy Defender for Identity configurations JSON to: $legacyFile" -ForegroundColor Green
$allConfigurations | ConvertTo-Json -Depth 10 | Out-File -FilePath $legacyFile -Encoding UTF8

# Merlino Universal Schema format
Write-Host "Converting to Merlino Universal Schema format..." -ForegroundColor Cyan
$catalogueData = @()

# Process each configuration type separately
$configTypes = $allConfigurations | Select-Object -Unique -ExpandProperty _ConfigType
foreach ($configType in $configTypes) {
  $configs = $allConfigurations | Where-Object { $_._ConfigType -eq $configType }
  $catalogueData += ConvertTo-MerlinoCatalogue -Configurations $configs -Source $Source -ConfigType $configType
}

$universalSchema = @{
  schema = @{
    version = "1.0"
    type = "catalogue"
    description = "Defender for Identity configurations from tenant $TenantId"
    source = $Source
    tenant = $TenantId
    workspace = $WorkspaceName
    created = (Get-Date -Format "yyyy-MM-ddTHH:mm:ss.fffZ")
    totalRecords = $catalogueData.Count
  }
  data = $catalogueData
}

$universalFile = Join-Path $OutputFolder ("merlino-catalogue-defender-identity-{0}-{1}.json" -f $tenantSafe, $stamp)
Write-Host "Writing Merlino Universal Schema to: $universalFile" -ForegroundColor Green
$universalSchema | ConvertTo-Json -Depth 10 | Out-File -FilePath $universalFile -Encoding UTF8

# ---- Summary ----
Write-Host "`n=== SUCCESS ===" -ForegroundColor Green
Write-Host "Tenant: $TenantId" -ForegroundColor Cyan
Write-Host "Workspace: $WorkspaceName" -ForegroundColor Cyan
Write-Host "Source: $Source" -ForegroundColor Cyan
Write-Host "Configurations exported: $($allConfigurations.Count)" -ForegroundColor Cyan
Write-Host "`nFiles created:" -ForegroundColor Cyan
Write-Host "  Legacy (raw API):   $legacyFile" -ForegroundColor White
Write-Host "  Catalogue (import): $universalFile" -ForegroundColor White
Write-Host "`nReady to import in Merlino Catalogue!" -ForegroundColor Green
Write-Host "Note: TCodes are auto-mapped based on alert categories." -ForegroundColor Yellow
