<#
.SYNOPSIS
    Merlino Intune Policies Extractor - Export Microsoft Intune policies to Merlino Universal Catalogue format

.DESCRIPTION
    This script extracts all policies from a Microsoft Intune tenant and converts them into 
    Merlino's Universal Catalogue format for import into the Merlino Excel Add-in.
    
    The script:
    - Authenticates using Azure Service Principal (bypasses Conditional Access)
    - Retrieves all Intune policies from multiple areas:
      * Device Configuration policies
      * Configuration Policies (ASR, Antivirus, Firewall, etc.)
      * Device Compliance policies
      * Endpoint Security Intents (EDR, Disk Encryption, etc.)
      * App Protection Policies (MAM for iOS, Android, Windows)
      * App Configuration policies
      * Security Baseline templates
    - Generates two output files:
      1. Raw API response (legacy format)
      2. Merlino Universal Catalogue JSON (ready for import)
    
    The Catalogue format includes:
    - Policy metadata (name, type, priority/severity)
    - Source environment identifier (for multi-tenant tracking)
    - Full policy configuration in Data field
    
    NOTE: TCodes field is empty by default as Intune does not provide native MITRE ATT&CK mappings.
          Users can manually map policies to techniques after import.

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
    Source identifier for Catalogue records (e.g., "Microsoft Intune Production")
    If not provided, will prompt interactively

.EXAMPLE
    .\extract_intune_policies.ps1
    Runs with default parameters and prompts for Source name

.EXAMPLE
    .\extract_intune_policies.ps1 -TenantId "YOUR-TENANT-ID" -ClientId "YOUR-CLIENT-ID" -ClientSecret "YOUR-SECRET" -Source "Production"
    Runs with specified credentials and Source name

.NOTES
    File Name      : extract_intune_policies.ps1
    Author         : X3M.AI - Merlino Team
    Prerequisite   : PowerShell 5.1 or higher

    
    Required Azure AD App Registration Permissions:
    - DeviceManagementConfiguration.Read.All
    - DeviceManagementApps.Read.All
    - DeviceManagementManagedDevices.Read.All
    
    API Versions: v1.0 and beta endpoints
    
    This script uses REST API directly via Invoke-RestMethod.
    No PowerShell modules are required.
    
.LINK
    https://merlino-addin.x3m.ai
    https://docs.microsoft.com/en-us/graph/api/resources/intune-graph-overview
#>
#>


#Requires -Version 5.1

param(
  [string] $ClientId = "YOUR-CLIENT-ID-HERE",
  [string] $ClientSecret = "YOUR-CLIENT-SECRET-HERE",
  [string] $TenantId = "YOUR-TENANT-ID-HERE",
  [string] $OutputFolder = (Get-Location).Path,
  [string] $Source  # Will be prompted if not provided
)

# ---- Interactive Source Prompt ----
if ([string]::IsNullOrWhiteSpace($Source)) {
    Write-Host "`n=== Source Name Configuration ===" -ForegroundColor Cyan
    Write-Host "The 'Source' field helps distinguish between different environments in Merlino." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor White
    Write-Host "  - 'Microsoft Intune Production'  (production environment)" -ForegroundColor Gray
    Write-Host "  - 'Microsoft Intune Development' (dev/test environment)" -ForegroundColor Gray
    Write-Host "  - 'Intune - Customer XYZ'        (customer-specific)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "This allows you to:" -ForegroundColor White
    Write-Host "  ✓ Compare policies between Development and Production" -ForegroundColor Green
    Write-Host "  ✓ Filter Catalogue by environment" -ForegroundColor Green
    Write-Host "  ✓ Track policy changes across environments" -ForegroundColor Green
    Write-Host ""
    
    $userInput = Read-Host "Enter Source name (press ENTER for default 'Microsoft Intune')"
    
    if ([string]::IsNullOrWhiteSpace($userInput)) {
        $Source = "Microsoft Intune"
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

function Get-IntuneDeviceConfigurations {
  param([Parameter(Mandatory)][string]$AccessToken)
  
  Write-Host "Retrieving Device Configuration policies..." -ForegroundColor Yellow
  try {
    $configs = Get-AllGraphPages -InitialUri "https://graph.microsoft.com/v1.0/deviceManagement/deviceConfigurations" -AccessToken $AccessToken
    Write-Host "Found $($configs.Count) Device Configuration policies" -ForegroundColor Green
    return $configs
  }
  catch {
    Write-Host "  [!] Skipped - Error: $($_.Exception.Message)" -ForegroundColor DarkYellow
    return @()
  }
}

function Get-IntuneConfigurationPolicies {
  param([Parameter(Mandatory)][string]$AccessToken)
  
  Write-Host "Retrieving Configuration Policies (ASR, Antivirus, etc.)..." -ForegroundColor Yellow
  try {
    $policies = Get-AllGraphPages -InitialUri "https://graph.microsoft.com/beta/deviceManagement/configurationPolicies" -AccessToken $AccessToken
    Write-Host "Found $($policies.Count) Configuration Policies" -ForegroundColor Green
    
    # Get detailed settings for each policy
    $enhancedPolicies = @()
    foreach ($policy in $policies) {
      Write-Host "  Getting settings for: $($policy.name)" -ForegroundColor DarkGray
      try {
        $settings = Get-AllGraphPages -InitialUri "https://graph.microsoft.com/beta/deviceManagement/configurationPolicies/$($policy.id)/settings" -AccessToken $AccessToken
        $policy | Add-Member -NotePropertyName "settings" -NotePropertyValue $settings -Force
        $policy | Add-Member -NotePropertyName "displayName" -NotePropertyValue $policy.name -Force # Normalize name field
        $enhancedPolicies += $policy
      }
      catch {
        Write-Host "    [!] Could not get settings for policy $($policy.name)" -ForegroundColor DarkYellow
        $policy | Add-Member -NotePropertyName "displayName" -NotePropertyValue $policy.name -Force
        $enhancedPolicies += $policy
      }
    }
    return $enhancedPolicies
  }
  catch {
    Write-Host "  [!] Skipped - Error: $($_.Exception.Message)" -ForegroundColor DarkYellow
    return @()
  }
}

function Get-IntuneCompliancePolicies {
  param([Parameter(Mandatory)][string]$AccessToken)
  
  Write-Host "Retrieving Device Compliance policies..." -ForegroundColor Yellow
  try {
    $policies = Get-AllGraphPages -InitialUri "https://graph.microsoft.com/v1.0/deviceManagement/deviceCompliancePolicies" -AccessToken $AccessToken
    Write-Host "Found $($policies.Count) Device Compliance policies" -ForegroundColor Green
    return $policies
  }
  catch {
    Write-Host "  [!] Skipped - Error: $($_.Exception.Message)" -ForegroundColor DarkYellow
    return @()
  }
}

function Get-IntuneIntents {
  param([Parameter(Mandatory)][string]$AccessToken)
  
  Write-Host "Retrieving Endpoint Security Intents (Antivirus, Firewall, EDR, etc.)..." -ForegroundColor Yellow
  try {
    $intents = Get-AllGraphPages -InitialUri "https://graph.microsoft.com/beta/deviceManagement/intents" -AccessToken $AccessToken
    Write-Host "Found $($intents.Count) Endpoint Security Intents" -ForegroundColor Green
    
    # Get detailed settings for each intent
    $enhancedIntents = @()
    foreach ($intent in $intents) {
      Write-Host "  Getting settings for: $($intent.displayName)" -ForegroundColor DarkGray
      try {
        $settings = Get-AllGraphPages -InitialUri "https://graph.microsoft.com/beta/deviceManagement/intents/$($intent.id)/settings" -AccessToken $AccessToken
        $intent | Add-Member -NotePropertyName "settings" -NotePropertyValue $settings -Force
        $enhancedIntents += $intent
      }
      catch {
        Write-Host "    [!] Could not get settings for intent $($intent.displayName)" -ForegroundColor DarkYellow
        $enhancedIntents += $intent
      }
    }
    return $enhancedIntents
  }
  catch {
    Write-Host "  [!] Skipped - Error: $($_.Exception.Message)" -ForegroundColor DarkYellow
    return @()
  }
}

function Get-IntuneAppProtectionPolicies {
  param([Parameter(Mandatory)][string]$AccessToken)
  
  Write-Host "Retrieving App Protection Policies (MAM)..." -ForegroundColor Yellow
  $allAppPolicies = @()
  
  try {
    # iOS/iPadOS App Protection Policies
    Write-Host "  Fetching iOS App Protection Policies..." -ForegroundColor DarkGray
    $iosPolicies = Get-AllGraphPages -InitialUri "https://graph.microsoft.com/beta/deviceAppManagement/iosManagedAppProtections" -AccessToken $AccessToken
    Write-Host "  Found $($iosPolicies.Count) iOS App Protection policies" -ForegroundColor Green
    $allAppPolicies += $iosPolicies
    
    # Android App Protection Policies
    Write-Host "  Fetching Android App Protection Policies..." -ForegroundColor DarkGray
    $androidPolicies = Get-AllGraphPages -InitialUri "https://graph.microsoft.com/beta/deviceAppManagement/androidManagedAppProtections" -AccessToken $AccessToken
    Write-Host "  Found $($androidPolicies.Count) Android App Protection policies" -ForegroundColor Green
    $allAppPolicies += $androidPolicies
    
    # Windows App Protection Policies
    Write-Host "  Fetching Windows App Protection Policies..." -ForegroundColor DarkGray
    $windowsPolicies = Get-AllGraphPages -InitialUri "https://graph.microsoft.com/beta/deviceAppManagement/windowsManagedAppProtections" -AccessToken $AccessToken
    Write-Host "  Found $($windowsPolicies.Count) Windows App Protection policies" -ForegroundColor Green
    $allAppPolicies += $windowsPolicies
    
    Write-Host "Total App Protection Policies: $($allAppPolicies.Count)" -ForegroundColor Green
    return $allAppPolicies
  }
  catch {
    Write-Host "  [!] Skipped - Error: $($_.Exception.Message)" -ForegroundColor DarkYellow
    return $allAppPolicies
  }
}

function Get-IntuneAppConfigurationPolicies {
  param([Parameter(Mandatory)][string]$AccessToken)
  
  Write-Host "Retrieving App Configuration Policies..." -ForegroundColor Yellow
  try {
    $policies = Get-AllGraphPages -InitialUri "https://graph.microsoft.com/beta/deviceAppManagement/mobileAppConfigurations" -AccessToken $AccessToken
    Write-Host "Found $($policies.Count) App Configuration policies" -ForegroundColor Green
    return $policies
  }
  catch {
    Write-Host "  [!] Skipped - Error: $($_.Exception.Message)" -ForegroundColor DarkYellow
    return @()
  }
}

function Get-IntuneSecurityBaselines {
  param([Parameter(Mandatory)][string]$AccessToken)
  
  Write-Host "Retrieving Security Baselines..." -ForegroundColor Yellow
  try {
    $baselines = Get-AllGraphPages -InitialUri "https://graph.microsoft.com/beta/deviceManagement/templates" -AccessToken $AccessToken
    Write-Host "Found $($baselines.Count) Security Baseline templates" -ForegroundColor Green
    return $baselines
  }
  catch {
    Write-Host "  [!] Skipped - Error: $($_.Exception.Message)" -ForegroundColor DarkYellow
    return @()
  }
}

function Get-MitreTCodesForIntunePolicy {
  param(
    [string]$PolicyName, 
    [string]$PolicyType,
    [string]$TemplateDisplayName,
    [object]$Settings
  )
  
  # Map Intune policy types to MITRE ATT&CK techniques
  $tcodes = @()
  
  # ASR (Attack Surface Reduction) Rules
  if ($PolicyName -like "*ASR*" -or $PolicyName -like "*Attack Surface*" -or $TemplateDisplayName -like "*Attack Surface*") {
    $tcodes += @("T1566", "T1204", "T1059", "T1053", "T1055")  # Phishing, User Execution, Command Scripting, Scheduled Task, Process Injection
  }
  
  # Antivirus / Defender policies
  if ($PolicyName -like "*Antivirus*" -or $PolicyName -like "*Defender*" -or $TemplateDisplayName -like "*Antivirus*") {
    $tcodes += @("T1562.001", "T1036", "T1027")  # Disable Security Tools, Masquerading, Obfuscated Files
  }
  
  # Firewall policies
  if ($PolicyName -like "*Firewall*" -or $TemplateDisplayName -like "*Firewall*") {
    $tcodes += @("T1562.004", "T1090", "T1095")  # Disable Firewall, Proxy, Non-Application Layer Protocol
  }
  
  # BitLocker / Disk Encryption
  if ($PolicyName -like "*BitLocker*" -or $PolicyName -like "*Encryption*" -or $TemplateDisplayName -like "*Disk Encryption*") {
    $tcodes += @("T1486", "T1005", "T1561")  # Data Encrypted for Impact, Data from Local System, Disk Wipe
  }
  
  # EDR (Endpoint Detection and Response)
  if ($PolicyName -like "*EDR*" -or $TemplateDisplayName -like "*Endpoint detection*") {
    $tcodes += @("T1562.001", "T1070", "T1070.001")  # Disable Security Tools, Indicator Removal, Clear Windows Event Logs
  }
  
  # Compliance Policies (Password, Device Health)
  if ($PolicyType -like "*Compliance*") {
    $tcodes += @("T1078", "T1110", "T1552")  # Valid Accounts, Brute Force, Unsecured Credentials
  }
  
  # App Protection (MAM)
  if ($PolicyType -like "*AppProtection*" -or $PolicyType -like "*ManagedAppProtection*") {
    $tcodes += @("T1530", "T1552.001", "T1005")  # Data from Cloud Storage, Credentials In Files, Data from Local System
  }
  
  # Windows Update / Patch Management
  if ($PolicyName -like "*Update*" -or $PolicyName -like "*Patch*") {
    $tcodes += @("T1068", "T1211")  # Exploitation for Privilege Escalation, Exploitation for Defense Evasion
  }
  
  # Password / Authentication policies
  if ($PolicyName -like "*Password*" -or $PolicyName -like "*Authentication*" -or $PolicyName -like "*MFA*") {
    $tcodes += @("T1110", "T1078", "T1556")  # Brute Force, Valid Accounts, Modify Authentication Process
  }
  
  # Device Control / USB restrictions
  if ($PolicyName -like "*Device Control*" -or $PolicyName -like "*USB*" -or $PolicyName -like "*Removable*") {
    $tcodes += @("T1091", "T1052", "T1200")  # Replication Through Removable Media, Exfiltration Over Physical Medium, Hardware Additions
  }
  
  # Application Control / AppLocker
  if ($PolicyName -like "*AppLocker*" -or $PolicyName -like "*Application Control*" -or $PolicyName -like "*App Control*") {
    $tcodes += @("T1204", "T1059", "T1218")  # User Execution, Command and Scripting, System Binary Proxy Execution
  }
  
  # Credential Guard / Credential Protection
  if ($PolicyName -like "*Credential*" -or $TemplateDisplayName -like "*Credential*") {
    $tcodes += @("T1003", "T1555", "T1552")  # OS Credential Dumping, Credentials from Password Stores, Unsecured Credentials
  }
  
  # Exploit Protection
  if ($PolicyName -like "*Exploit Protection*" -or $PolicyName -like "*EMET*") {
    $tcodes += @("T1068", "T1203", "T1210")  # Exploitation for Privilege Escalation, Exploitation for Client Execution, Exploitation of Remote Services
  }
  
  # Remove duplicates and return as comma-separated string
  $uniqueTCodes = $tcodes | Select-Object -Unique
  return ($uniqueTCodes -join ",")
}

function ConvertTo-MerlinoCatalogue {
  param(
    [array]$Policies,
    [string]$Source
  )

  $catalogueRecords = @()

  foreach ($policy in $Policies) {
    # Determine policy type and priority
    $policyType = "Microsoft.Graph/deviceManagement/deviceConfigurations"
    $priority = "Medium"
    
    # Handle Configuration Policies (ASR policies)
    if ($policy.technologies -or ($policy.name -and -not $policy.'@odata.type')) {
      $policyType = "Microsoft.Graph/deviceManagement/configurationPolicies"
      
      $policyName = if ($policy.name) { $policy.name } else { $policy.displayName }
      if ($policyName -like "*ASR*" -or $policyName -like "*Attack*" -or $policyName -like "*Identity*") {
        $priority = "High"
      }
    }
    # Handle traditional policy types
    elseif ($policy.'@odata.type') {
      switch ($policy.'@odata.type') {
        "#microsoft.graph.deviceManagementIntent" { 
          $policyType = "Microsoft.Graph/deviceManagement/intents"
          if ($policy.templateDisplayName -like "*Attack Surface*" -or $policy.templateDisplayName -like "*Antivirus*" -or $policy.templateDisplayName -like "*Firewall*" -or $policy.templateDisplayName -like "*EDR*") {
            $priority = "High"
          }
        }
        "#microsoft.graph.deviceCompliancePolicy" { 
          $policyType = "Microsoft.Graph/deviceManagement/deviceCompliancePolicies"
          $priority = "High"
        }
        "#microsoft.graph.iosManagedAppProtection" {
          $policyType = "Microsoft.Graph/deviceAppManagement/iosManagedAppProtections"
          $priority = "Medium"
        }
        "#microsoft.graph.androidManagedAppProtection" {
          $policyType = "Microsoft.Graph/deviceAppManagement/androidManagedAppProtections"
          $priority = "Medium"
        }
        "#microsoft.graph.windowsManagedAppProtection" {
          $policyType = "Microsoft.Graph/deviceAppManagement/windowsManagedAppProtections"
          $priority = "Medium"
        }
        "#microsoft.graph.iosLobAppProvisioningConfiguration" {
          $policyType = "Microsoft.Graph/deviceAppManagement/mobileAppConfigurations"
          $priority = "Low"
        }
        "#microsoft.graph.deviceManagementTemplate" {
          $policyType = "Microsoft.Graph/deviceManagement/templates"
          $priority = "High"
        }
      }
    }

    # Determine if policy is enabled
    $isEnabled = $true
    if ($policy.PSObject.Properties['isAssigned']) {
      $isEnabled = $policy.isAssigned
    } elseif ($policy.PSObject.Properties['roleScopeTagIds']) {
      $isEnabled = $policy.roleScopeTagIds.Count -gt 0
    }

    # Prepare description
    $description = ""
    if ($policy.description) {
      $description = $policy.description
    } else {
      $description = "Intune policy: $policyType"
    }
    
    # Get policy name for MITRE mapping
    $policyName = if ($policy.displayName) { $policy.displayName } elseif ($policy.name) { $policy.name } else { "" }
    $templateName = if ($policy.templateDisplayName) { $policy.templateDisplayName } else { "" }
    
    # Map to MITRE ATT&CK techniques
    $tcodes = Get-MitreTCodesForIntunePolicy -PolicyName $policyName -PolicyType $policyType -TemplateDisplayName $templateName -Settings $policy.settings

    # Build Catalogue record (13 fields - Universal Import Schema v1.0)
    $catalogueRecord = [pscustomobject]@{
      Pick = $false
      CrossPick = 0
      Name = if ($policyName) { $policyName } else { "Unnamed Policy" }
      Source = $Source
      Priority = $priority
      Enabled = $isEnabled
      Validation_Score = ""
      Tests = 0
      Expected_Tests = 0
      Tests_Validated = 0
      TCodes = $tcodes
      Description = $description
      Notes = ""
      Data = ($policy | ConvertTo-Json -Depth 10 -Compress)
    }

    $catalogueRecords += $catalogueRecord
  }

  return $catalogueRecords
}

# ---- Main Script ----
Write-Host "=== Merlino Intune Policy Extractor (Service Principal) ===" -ForegroundColor Green
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

# ---- Fetch Real Intune Policies ----
Write-Host "`nFetching Intune policies from ALL areas of the tenant..." -ForegroundColor Cyan
$allPolicies = @()

try {
  # Get Device Configurations
  $deviceConfigs = Get-IntuneDeviceConfigurations -AccessToken $accessToken
  $allPolicies += $deviceConfigs

  # Get Configuration Policies (ASR, Antivirus settings, etc.)
  $configPolicies = Get-IntuneConfigurationPolicies -AccessToken $accessToken
  $allPolicies += $configPolicies

  # Get Compliance Policies
  $compliancePolicies = Get-IntuneCompliancePolicies -AccessToken $accessToken
  $allPolicies += $compliancePolicies

  # Get Endpoint Security Intents (Antivirus, Firewall, EDR, Disk Encryption, etc.)
  $intents = Get-IntuneIntents -AccessToken $accessToken
  $allPolicies += $intents

  # Get App Protection Policies (MAM - iOS, Android, Windows)
  $appProtectionPolicies = Get-IntuneAppProtectionPolicies -AccessToken $accessToken
  $allPolicies += $appProtectionPolicies

  # Get App Configuration Policies
  $appConfigPolicies = Get-IntuneAppConfigurationPolicies -AccessToken $accessToken
  $allPolicies += $appConfigPolicies

  # Get Security Baselines
  $securityBaselines = Get-IntuneSecurityBaselines -AccessToken $accessToken
  $allPolicies += $securityBaselines

  Write-Host "`n=== SUMMARY ===" -ForegroundColor Cyan
  Write-Host "Device Configurations: $($deviceConfigs.Count)" -ForegroundColor White
  Write-Host "Configuration Policies (ASR/AV): $($configPolicies.Count)" -ForegroundColor White
  Write-Host "Compliance Policies: $($compliancePolicies.Count)" -ForegroundColor White
  Write-Host "Endpoint Security Intents: $($intents.Count)" -ForegroundColor White
  Write-Host "App Protection Policies: $($appProtectionPolicies.Count)" -ForegroundColor White
  Write-Host "App Configuration Policies: $($appConfigPolicies.Count)" -ForegroundColor White
  Write-Host "Security Baselines: $($securityBaselines.Count)" -ForegroundColor White
  Write-Host "`nTotal policies collected: $($allPolicies.Count)" -ForegroundColor Green
  
  if ($allPolicies.Count -gt 0) {
    Write-Host "`n[i] Successfully extracted all core Intune policies!" -ForegroundColor Green
    Write-Host "  Policies cover: Device Configs, Compliance, Security, App Protection" -ForegroundColor DarkGray
    Write-Host "  - DeviceManagementConfiguration.Read.All" -ForegroundColor DarkGray
    Write-Host "  - DeviceManagementManagedDevices.Read.All" -ForegroundColor DarkGray
  }
  
  if ($allPolicies.Count -eq 0) {
    Write-Host "`nNo policies found in tenant $TenantId." -ForegroundColor Red
    Write-Host "This could be due to:" -ForegroundColor Red
    Write-Host "  - Service Principal permissions not sufficient" -ForegroundColor Red
    Write-Host "  - No policies configured in this tenant" -ForegroundColor Red
    exit 1
  }
  
  # Display found policies for verification
  Write-Host "`nFound policies:" -ForegroundColor Cyan
  foreach ($policy in $allPolicies) {
    $type = "Unknown"
    if ($policy.'@odata.type' -eq "#microsoft.graph.deviceManagementIntent") { $type = "Endpoint Security Intent" }
    elseif ($policy.'@odata.type' -eq "#microsoft.graph.deviceConfiguration") { $type = "Device Configuration" }
    elseif ($policy.'@odata.type' -eq "#microsoft.graph.deviceCompliancePolicy") { $type = "Compliance Policy" }
    elseif ($policy.'@odata.type' -eq "#microsoft.graph.iosManagedAppProtection") { $type = "iOS App Protection" }
    elseif ($policy.'@odata.type' -eq "#microsoft.graph.androidManagedAppProtection") { $type = "Android App Protection" }
    elseif ($policy.'@odata.type' -eq "#microsoft.graph.windowsManagedAppProtection") { $type = "Windows App Protection" }
    elseif ($policy.'@odata.type' -like "*MobileAppConfiguration*") { $type = "App Configuration" }
    elseif ($policy.'@odata.type' -eq "#microsoft.graph.windowsUpdateForBusinessConfiguration") { $type = "Windows Update" }
    elseif ($policy.'@odata.type' -eq "#microsoft.graph.deviceManagementScript") { $type = "PowerShell Script" }
    elseif ($policy.'@odata.type' -eq "#microsoft.graph.deviceHealthScript") { $type = "Remediation Script" }
    elseif ($policy.'@odata.type' -eq "#microsoft.graph.deviceManagementTemplate") { $type = "Security Baseline" }
    elseif ($policy.technologies) { $type = "Configuration Policy" }
    
    $policyName = if ($policy.displayName) { $policy.displayName } elseif ($policy.name) { $policy.name } else { "Unnamed" }
    Write-Host "  - $policyName [$type]" -ForegroundColor Gray
  }
}
catch {
  Write-Host "`nERROR: Failed to retrieve Intune policies from tenant $TenantId" -ForegroundColor Red
  Write-Host "Error details: $($_.Exception.Message)" -ForegroundColor Red
  exit 1
}

# ---- Generate Output Files ----
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$tenantSafe = Sanitize-FileName -s $tenantName

# Legacy format
$legacyFile = Join-Path $OutputFolder ("intune-policies-{0}-{1}.json" -f $tenantSafe, $stamp)
Write-Host "`nWriting legacy Intune policies JSON to: $legacyFile" -ForegroundColor Green
$allPolicies | ConvertTo-Json -Depth 10 | Out-File -FilePath $legacyFile -Encoding UTF8

# Merlino Universal Schema format
Write-Host "Converting to Merlino Universal Schema format..." -ForegroundColor Cyan
$catalogueData = ConvertTo-MerlinoCatalogue -Policies $allPolicies -Source $Source

$universalSchema = @{
  schema = @{
    version = "1.0"
    type = "catalogue"
    description = "Intune policies from tenant $TenantId"
    source = $Source
    tenant = $TenantId
    created = (Get-Date -Format "yyyy-MM-ddTHH:mm:ss.fffZ")
    totalRecords = $catalogueData.Count
  }
  data = $catalogueData
}

$universalFile = Join-Path $OutputFolder ("merlino-catalogue-intune-{0}-{1}.json" -f $tenantSafe, $stamp)
Write-Host "Writing Merlino Universal Schema to: $universalFile" -ForegroundColor Green
$universalSchema | ConvertTo-Json -Depth 10 | Out-File -FilePath $universalFile -Encoding UTF8

# ---- Summary ----
Write-Host "`n=== SUCCESS ===" -ForegroundColor Green
Write-Host "Tenant: $TenantId" -ForegroundColor Cyan
Write-Host "Source: $Source" -ForegroundColor Cyan
Write-Host "Policies exported: $($allPolicies.Count)" -ForegroundColor Cyan
Write-Host "`nFiles created:" -ForegroundColor Cyan
Write-Host "  Legacy (raw API):   $legacyFile" -ForegroundColor White
Write-Host "  Catalogue (import): $universalFile" -ForegroundColor White
Write-Host "`nReady to import in Merlino Catalogue!" -ForegroundColor Green
Write-Host "Note: TCodes are auto-mapped based on policy types and names." -ForegroundColor Yellow

