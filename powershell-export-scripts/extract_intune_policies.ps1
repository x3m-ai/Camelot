<#
.SYNOPSIS
    Merlino Intune Policies Extractor - Export Microsoft Intune policies to Merlino Universal Catalogue format

.DESCRIPTION
    This script extracts all policies from a Microsoft Intune tenant and converts them into 
    Merlino's Universal Catalogue format for import into the Merlino Excel Add-in.
    
    The script:
    - Supports two authentication modes:
        ServicePrincipal  (default) — App registration with client secret, no user interaction,
                                      ideal for automation and pipelines.
        Interactive       — Device Code Flow. The user authenticates with their own Entra ID
                            credentials. Works from any machine including servers with no browser.
                            Requires appropriate Entra ID role on the user account (see below).
    - Authenticates and then retrieves ALL active policies from Microsoft Intune / Azure at every level.
    - Retrieves ALL active policies from Microsoft Intune / Azure at every level:
      * Device Configuration policies
      * Configuration Policies (ASR, Antivirus, Firewall, etc.)
      * Device Compliance policies
      * Endpoint Security Intents (EDR, Disk Encryption, etc.)
      * App Protection Policies (MAM for iOS, Android, Windows)
      * App Configuration policies
      * Security Baseline templates
      * Conditional Access Policies (Azure AD - blocking/audit rules)
      * Group Policy Configurations (hybrid-joined devices)
      * Enrollment Restrictions (device enrollment controls)
      * PowerShell Scripts deployed via Intune
      * Remediation Scripts (Proactive Remediations / Device Health Scripts)
      * Windows Autopilot Deployment Profiles
      * Windows Feature Update Policies
      * Windows Quality Update Policies
      * Endpoint Privilege Management elevations
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

.PARAMETER AuthMode
    Authentication mode: ServicePrincipal (default) or Interactive
    Interactive uses Device Code Flow - no browser needed, works from any machine.

.PARAMETER Source
    Source identifier for Catalogue records (e.g., "Microsoft Intune Production")
    If not provided, will prompt interactively

.EXAMPLE
    .\extract_intune_policies.ps1 -AuthMode Interactive -TenantId "YOUR-TENANT-ID"
    Interactive login via Device Code Flow. User authenticates with their Entra ID account.
    Requires Global Reader or Intune Administrator + Security Reader role on the user.

.EXAMPLE
    .\extract_intune_policies.ps1
    Service Principal mode with default parameters. Prompts for Source name.

.EXAMPLE
    .\extract_intune_policies.ps1 -TenantId "YOUR-TENANT-ID" -ClientId "YOUR-CLIENT-ID" -ClientSecret "YOUR-SECRET" -Source "Production"
    Service Principal mode with all credentials specified inline.

.NOTES
    File Name      : extract_intune_policies.ps1
    Author         : X3M.AI - Merlino Team
    Prerequisite   : PowerShell 5.1 or higher

    
    --- MODE: ServicePrincipal ---
    Required Azure AD App Registration Permissions (Application permissions):
    - DeviceManagementConfiguration.Read.All      (device configs, compliance, intents, baselines)
    - DeviceManagementApps.Read.All               (app protection, app config policies)
    - DeviceManagementManagedDevices.Read.All     (managed devices, scripts, remediations)
    - DeviceManagementServiceConfig.Read.All      (enrollment restrictions, autopilot profiles)
    - DeviceManagementRBAC.Read.All               (role definitions and scope tags)
    - Policy.Read.All                             (Conditional Access policies - Entra ID)
    - GroupMember.Read.All                        (optional: resolve group names in CA policies)

    --- MODE: Interactive (Device Code Flow) ---
    Entra ID role required on the USER account (one of the following):
    - Global Reader                  [RECOMMENDED] covers all areas including Conditional Access
    - Intune Administrator           covers all Intune device management areas
    - Security Reader                covers Conditional Access + security policies
    NOTE: Intune Administrator alone does NOT cover Conditional Access - pair with Security Reader
          if you do not want to assign Global Reader.

    No App Registration needed for Interactive mode. The script uses the well-known
    Microsoft Graph PowerShell public client app (14d82eec-204b-4c2f-b7e8-296a70dab67e).
    
    API Versions: v1.0 and beta endpoints
    
    This script uses REST API directly via Invoke-RestMethod.
    No PowerShell modules are required.
    
.NOTES
    Author:  Nino Crudele
    LinkedIn: https://www.linkedin.com/in/ninocrudele
    Website:  https://merlino.x3m.ai
    License:  MIT

.LINK
    https://merlino-addin.x3m.ai
    https://docs.microsoft.com/en-us/graph/api/resources/intune-graph-overview
#>

<#
==============================================================================
  QUICK START - COPY AND RUN ONE OF THESE COMMANDS
==============================================================================

  -- INTERACTIVE LOGIN (recommended - no App Registration needed) ------------

  .\extract_intune_policies.ps1 `
    -AuthMode Interactive `
    -TenantId "YOUR-TENANT-ID" `
    -Source "Intune Production" `
    -OutputFolder "C:\Temp"

  PERMISSIONS REQUIRED ON THE USER ACCOUNT (Entra ID roles):
  --------------------------------------------------------------------------
  Option A - Recommended (full coverage):
    Global Reader
      -> All Intune areas + Conditional Access + Security policies

  Option B - Granular (if you cannot assign Global Reader):
    Intune Administrator
      -> Device configs, compliance, security baselines, enrollment,
         app protection, scripts, remediations, update policies
    + Security Reader
      -> Conditional Access policies, security alerts

  NOTE: Conditional Access Policies require Policy.Read.All scope.
        This scope needs ADMIN CONSENT the first time the Interactive
        login is used. A Global Admin must approve the consent screen
        or pre-grant it via:
        Entra ID -> Enterprise Applications -> Microsoft Graph PowerShell
        -> Permissions -> Grant admin consent for [your tenant]

  -- SERVICE PRINCIPAL (automation / pipelines / no user interaction) ---------

  .\extract_intune_policies.ps1 `
    -AuthMode ServicePrincipal `
    -TenantId "YOUR-TENANT-ID" `
    -ClientId "YOUR-APP-CLIENT-ID" `
    -ClientSecret "YOUR-APP-SECRET" `
    -Source "Intune Production" `
    -OutputFolder "C:\Temp"

  PERMISSIONS REQUIRED ON THE APP REGISTRATION (Application permissions):
  --------------------------------------------------------------------------
  Permission                              Covers
  --------------------------------------  ------------------------------------
  DeviceManagementConfiguration.Read.All  Device configs, ASR, AV, Firewall,
                                          Security Baselines, Group Policy,
                                          PS Scripts, Remediations
  DeviceManagementApps.Read.All           App Protection (MAM iOS/Android/Win)
                                          App Configuration policies
  DeviceManagementManagedDevices.Read.All Managed devices, Health scripts
  DeviceManagementServiceConfig.Read.All  Enrollment Restrictions,
                                          Autopilot Deployment Profiles,
                                          Feature/Quality Update policies
  DeviceManagementRBAC.Read.All           RBAC Role Definitions, Scope Tags
  Policy.Read.All                         Conditional Access Policies (Entra)
  GroupMember.Read.All                    (optional) Resolve group names in CA

  HOW TO CREATE THE APP REGISTRATION:
    1. Entra ID -> App registrations -> New registration
    2. Name: e.g. "Merlino-Intune-Extractor"
    3. API permissions -> Add permission -> Microsoft Graph -> Application
       -> Add each permission above -> Grant admin consent
    4. Certificates & secrets -> New client secret -> copy the Value (not ID)

  -- OUTPUT --------------------------------------------------------------------

  Two files are created in OutputFolder:
    intune-policies-<tenant>-<timestamp>.json              <- raw API response
    merlino-catalogue-intune-<tenant>-<timestamp>.json     <- ready for import

  Import the second file into Merlino: Sources taskpane -> Catalogue -> Import

==============================================================================
#>

#Requires -Version 5.1

param(
  [ValidateSet('ServicePrincipal','Interactive')]
  [string] $AuthMode = 'ServicePrincipal',
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
    Write-Host "  [OK] Compare policies between Development and Production" -ForegroundColor Green
    Write-Host "  [OK] Filter Catalogue by environment" -ForegroundColor Green
    Write-Host "  [OK] Track policy changes across environments" -ForegroundColor Green
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

    $bodyHash = @{
      client_id     = $ClientId
      client_secret = $ClientSecret
      scope         = "https://graph.microsoft.com/.default"
      grant_type    = "client_credentials"
    }

    Write-Host "Sending authentication request..." -ForegroundColor DarkGray

    $response = Invoke-RestMethod -Uri $tokenUri -Method POST -Body $bodyHash -ContentType "application/x-www-form-urlencoded" -ErrorAction Stop
    
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

function Get-AccessTokenInteractive {
  param(
    [Parameter(Mandatory)][string]$TenantId
  )

  # Well-known Microsoft Graph PowerShell public client app — no registration required.
  # Supports delegated (user-based) access to Graph API.
  $PublicClientId = "14d82eec-204b-4c2f-b7e8-296a70dab67e"

  $scopes = @(
    "DeviceManagementConfiguration.Read.All",
    "DeviceManagementApps.Read.All",
    "DeviceManagementManagedDevices.Read.All",
    "DeviceManagementServiceConfig.Read.All",
    "DeviceManagementRBAC.Read.All",
    "Policy.Read.All"
  )

  $deviceCodeUri = "https://login.microsoftonline.com/$TenantId/oauth2/v2.0/devicecode"
  $tokenUri      = "https://login.microsoftonline.com/$TenantId/oauth2/v2.0/token"

  # Step 1: Request device code
  $dcBodyHash = @{
    client_id = $PublicClientId
    scope     = ($scopes -join " ")
  }
  try {
    $dcResponse = Invoke-RestMethod -Uri $deviceCodeUri -Method POST -Body $dcBodyHash -ContentType "application/x-www-form-urlencoded" -ErrorAction Stop
  }
  catch {
    Write-Host "Error requesting device code: $($_.Exception.Message)" -ForegroundColor Red
    throw
  }

  # Step 2: Show instructions to the user
  Write-Host "`n========================================" -ForegroundColor Cyan
  Write-Host "  INTERACTIVE LOGIN - Device Code Flow  " -ForegroundColor Cyan
  Write-Host "========================================" -ForegroundColor Cyan
  Write-Host ""
  Write-Host "1. Open a browser and navigate to:" -ForegroundColor White
  Write-Host "   $($dcResponse.verification_uri)" -ForegroundColor Yellow
  Write-Host ""
  Write-Host "2. Enter this code:" -ForegroundColor White
  Write-Host "   $($dcResponse.user_code)" -ForegroundColor Green
  Write-Host ""
  Write-Host "3. Sign in with your Entra ID account." -ForegroundColor White
  Write-Host "   Required role: Global Reader  (or Intune Administrator + Security Reader)" -ForegroundColor DarkGray
  Write-Host ""
  Write-Host "Waiting for authentication..." -ForegroundColor DarkGray

  # Step 3: Poll for token
  $interval  = if ($dcResponse.interval) { [int]$dcResponse.interval } else { 5 }
  $expiresIn = if ($dcResponse.expires_in) { [int]$dcResponse.expires_in } else { 900 }
  $deadline  = (Get-Date).AddSeconds($expiresIn)

  $pollBodyHash = @{
    client_id   = $PublicClientId
    grant_type  = "urn:ietf:params:oauth:grant-type:device_code"
    device_code = $dcResponse.device_code
  }

  while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds $interval
    try {
      $tokenResponse = Invoke-RestMethod -Uri $tokenUri -Method POST -Body $pollBodyHash -ContentType "application/x-www-form-urlencoded" -ErrorAction Stop
      Write-Host "Authentication successful!" -ForegroundColor Green
      Write-Host ""
      return $tokenResponse.access_token
    }
    catch {
      # PS 5.1: Invoke-RestMethod closes the response stream before the catch block.
      # $_.ErrorDetails.Message contains the raw JSON body of the error response.
      $errCode = "unknown"
      $rawBody = $_.ErrorDetails.Message
      if (-not [string]::IsNullOrEmpty($rawBody)) {
        try {
          $parsed  = $rawBody | ConvertFrom-Json
          $errCode = $parsed.error
        } catch { }
      }

      if ($errCode -eq "authorization_pending") {
        Write-Host "  Waiting..." -ForegroundColor DarkGray
        continue
      }
      elseif ($errCode -eq "slow_down") {
        $interval += 5
        continue
      }
      elseif ($errCode -eq "authorization_declined") {
        Write-Host "Authentication was declined by the user." -ForegroundColor Red
        throw "User declined authentication."
      }
      elseif ($errCode -eq "expired_token") {
        Write-Host "Device code expired. Please run the script again." -ForegroundColor Red
        throw "Device code expired."
      }
      else {
        Write-Host "Unexpected error during token poll: $errCode | $rawBody" -ForegroundColor Red
        throw $_
      }
    }
  }

  throw "Authentication timed out. The device code expired before the user completed sign-in."
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

function Get-IntuneConditionalAccessPolicies {
  param([Parameter(Mandatory)][string]$AccessToken)

  Write-Host "Retrieving Conditional Access Policies (Entra ID / Azure AD)..." -ForegroundColor Yellow
  try {
    $policies = Get-AllGraphPages -InitialUri "https://graph.microsoft.com/v1.0/identity/conditionalAccess/policies" -AccessToken $AccessToken
    Write-Host "Found $($policies.Count) Conditional Access policies" -ForegroundColor Green
    return $policies
  }
  catch {
    Write-Host "  [!] Skipped - Error: $($_.Exception.Message)" -ForegroundColor DarkYellow
    Write-Host "  [!] Requires Policy.Read.All with admin consent in the tenant." -ForegroundColor DarkYellow
    Write-Host "      In Interactive mode: a Global Admin must consent the scope at first login," -ForegroundColor DarkYellow
    Write-Host "      or grant admin consent via Entra ID > App registrations > Microsoft Graph PS" -ForegroundColor DarkYellow
    return @()
  }
}

function Get-IntuneGroupPolicyConfigurations {
  param([Parameter(Mandatory)][string]$AccessToken)

  Write-Host "Retrieving Group Policy Configurations (hybrid-joined devices)..." -ForegroundColor Yellow
  try {
    $configs = Get-AllGraphPages -InitialUri "https://graph.microsoft.com/beta/deviceManagement/groupPolicyConfigurations" -AccessToken $AccessToken
    Write-Host "Found $($configs.Count) Group Policy Configurations" -ForegroundColor Green

    $enhanced = @()
    foreach ($cfg in $configs) {
      try {
        $definitionValues = Get-AllGraphPages -InitialUri "https://graph.microsoft.com/beta/deviceManagement/groupPolicyConfigurations/$($cfg.id)/definitionValues?`$expand=definition" -AccessToken $AccessToken
        $cfg | Add-Member -NotePropertyName "definitionValues" -NotePropertyValue $definitionValues -Force
      }
      catch {
        Write-Host "    [!] Could not get definition values for $($cfg.displayName)" -ForegroundColor DarkYellow
      }
      $enhanced += $cfg
    }
    return $enhanced
  }
  catch {
    Write-Host "  [!] Skipped - Error: $($_.Exception.Message)" -ForegroundColor DarkYellow
    return @()
  }
}

function Get-IntuneEnrollmentConfigurations {
  param([Parameter(Mandatory)][string]$AccessToken)

  Write-Host "Retrieving Enrollment Restrictions..." -ForegroundColor Yellow
  try {
    $configs = Get-AllGraphPages -InitialUri "https://graph.microsoft.com/v1.0/deviceManagement/deviceEnrollmentConfigurations" -AccessToken $AccessToken
    Write-Host "Found $($configs.Count) Enrollment Configurations" -ForegroundColor Green
    return $configs
  }
  catch {
    Write-Host "  [!] Skipped - Error: $($_.Exception.Message)" -ForegroundColor DarkYellow
    return @()
  }
}

function Get-IntuneDeviceManagementScripts {
  param([Parameter(Mandatory)][string]$AccessToken)

  Write-Host "Retrieving PowerShell Scripts deployed via Intune..." -ForegroundColor Yellow
  try {
    $scripts = Get-AllGraphPages -InitialUri "https://graph.microsoft.com/beta/deviceManagement/deviceManagementScripts" -AccessToken $AccessToken
    Write-Host "Found $($scripts.Count) PowerShell Scripts" -ForegroundColor Green
    return $scripts
  }
  catch {
    Write-Host "  [!] Skipped - Error: $($_.Exception.Message)" -ForegroundColor DarkYellow
    Write-Host "  [!] 403: DeviceManagementConfiguration.Read.All requires admin consent for this endpoint." -ForegroundColor DarkYellow
    return @()
  }
}

function Get-IntuneDeviceHealthScripts {
  param([Parameter(Mandatory)][string]$AccessToken)

  Write-Host "Retrieving Remediation Scripts (Proactive Remediations)..." -ForegroundColor Yellow
  try {
    $scripts = Get-AllGraphPages -InitialUri "https://graph.microsoft.com/beta/deviceManagement/deviceHealthScripts" -AccessToken $AccessToken
    Write-Host "Found $($scripts.Count) Device Health / Remediation Scripts" -ForegroundColor Green
    return $scripts
  }
  catch {
    Write-Host "  [!] Skipped - Error: $($_.Exception.Message)" -ForegroundColor DarkYellow
    Write-Host "  [!] 403: Requires Intune Administrator role or DeviceManagementConfiguration.Read.All with admin consent." -ForegroundColor DarkYellow
    return @()
  }
}

function Get-IntuneAutopilotProfiles {
  param([Parameter(Mandatory)][string]$AccessToken)

  Write-Host "Retrieving Windows Autopilot Deployment Profiles..." -ForegroundColor Yellow
  try {
    $profiles = Get-AllGraphPages -InitialUri "https://graph.microsoft.com/v1.0/deviceManagement/windowsAutopilotDeploymentProfiles" -AccessToken $AccessToken
    Write-Host "Found $($profiles.Count) Autopilot Deployment Profiles" -ForegroundColor Green
    return $profiles
  }
  catch {
    if ($_.Exception.Message -like "*(400)*") {
      Write-Host "  [!] Skipped - Autopilot not licensed or enabled in this tenant." -ForegroundColor DarkYellow
    } else {
      Write-Host "  [!] Skipped - Error: $($_.Exception.Message)" -ForegroundColor DarkYellow
    }
    return @()
  }
}

function Get-IntuneFeatureUpdatePolicies {
  param([Parameter(Mandatory)][string]$AccessToken)

  Write-Host "Retrieving Windows Feature Update Policies..." -ForegroundColor Yellow
  try {
    $policies = Get-AllGraphPages -InitialUri "https://graph.microsoft.com/beta/deviceManagement/windowsFeatureUpdateProfiles" -AccessToken $AccessToken
    Write-Host "Found $($policies.Count) Feature Update Policies" -ForegroundColor Green
    return $policies
  }
  catch {
    Write-Host "  [!] Skipped - Error: $($_.Exception.Message)" -ForegroundColor DarkYellow
    return @()
  }
}

function Get-IntuneQualityUpdatePolicies {
  param([Parameter(Mandatory)][string]$AccessToken)

  Write-Host "Retrieving Windows Quality Update Policies..." -ForegroundColor Yellow
  try {
    $policies = Get-AllGraphPages -InitialUri "https://graph.microsoft.com/beta/deviceManagement/windowsQualityUpdateProfiles" -AccessToken $AccessToken
    Write-Host "Found $($policies.Count) Quality Update Policies" -ForegroundColor Green
    return $policies
  }
  catch {
    Write-Host "  [!] Skipped - Error: $($_.Exception.Message)" -ForegroundColor DarkYellow
    return @()
  }
}

function Get-IntunePrivilegeManagement {
  param([Parameter(Mandatory)][string]$AccessToken)

  Write-Host "Retrieving Endpoint Privilege Management elevations..." -ForegroundColor Yellow
  try {
    $elevations = Get-AllGraphPages -InitialUri "https://graph.microsoft.com/beta/deviceManagement/privilegeManagementElevations" -AccessToken $AccessToken
    Write-Host "Found $($elevations.Count) Privilege Management elevation rules" -ForegroundColor Green
    return $elevations
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

  # Windows Update / Patch Management / Feature Update / Quality Update
  if ($PolicyName -like "*Update*" -or $PolicyName -like "*Patch*" -or $PolicyType -like "*FeatureUpdate*" -or $PolicyType -like "*QualityUpdate*") {
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

  # Conditional Access — identity-based blocking/audit
  if ($PolicyType -like "*conditionalAccess*") {
    $tcodes += @("T1078", "T1556", "T1110", "T1621")  # Valid Accounts, Modify Auth, Brute Force, MFA Request Generation
  }

  # Group Policy Configurations (hybrid join)
  if ($PolicyType -like "*groupPolicyConfiguration*") {
    $tcodes += @("T1484.001", "T1059", "T1562")  # Domain Policy Modification, Scripting, Impair Defenses
  }

  # Enrollment Restrictions
  if ($PolicyType -like "*enrollmentConfiguration*") {
    $tcodes += @("T1078", "T1200")  # Valid Accounts, Hardware Additions
  }

  # PowerShell Scripts deployed via Intune
  if ($PolicyType -like "*deviceManagementScript*") {
    $tcodes += @("T1059.001", "T1072", "T1569")  # PowerShell, Software Deployment Tools, System Services
  }

  # Remediation / Device Health Scripts
  if ($PolicyType -like "*deviceHealthScript*") {
    $tcodes += @("T1059.001", "T1562", "T1072")  # PowerShell, Impair Defenses, Software Deployment Tools
  }

  # Autopilot Profiles (device provisioning controls)
  if ($PolicyType -like "*autopilot*") {
    $tcodes += @("T1078", "T1200")  # Valid Accounts, Hardware Additions
  }

  # Endpoint Privilege Management
  if ($PolicyType -like "*privilegeManagement*") {
    $tcodes += @("T1078.003", "T1548.002", "T1134")  # Local Accounts, Bypass UAC, Access Token Manipulation
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
        "#microsoft.graph.windowsAutopilotDeploymentProfile" {
          $policyType = "Microsoft.Graph/deviceManagement/windowsAutopilotDeploymentProfiles"
          $priority = "Medium"
        }
        "#microsoft.graph.windowsFeatureUpdateProfile" {
          $policyType = "Microsoft.Graph/deviceManagement/windowsFeatureUpdateProfiles"
          $priority = "Medium"
        }
        "#microsoft.graph.windowsQualityUpdateProfile" {
          $policyType = "Microsoft.Graph/deviceManagement/windowsQualityUpdateProfiles"
          $priority = "Medium"
        }
        "#microsoft.graph.deviceManagementScript" {
          $policyType = "Microsoft.Graph/deviceManagement/deviceManagementScripts"
          $priority = "High"
        }
        "#microsoft.graph.deviceHealthScript" {
          $policyType = "Microsoft.Graph/deviceManagement/deviceHealthScripts"
          $priority = "High"
        }
        "#microsoft.graph.deviceEnrollmentConfiguration" {
          $policyType = "Microsoft.Graph/deviceManagement/deviceEnrollmentConfigurations"
          $priority = "High"
        }
        "#microsoft.graph.groupPolicyConfiguration" {
          $policyType = "Microsoft.Graph/deviceManagement/groupPolicyConfigurations"
          $priority = "High"
        }
      }
    }
    # Conditional Access Policies (no @odata.type, identified by 'state' field)
    elseif ($policy.PSObject.Properties['state'] -and $policy.PSObject.Properties['conditions']) {
      $policyType = "Microsoft.Graph/identity/conditionalAccess/policies"
      $priority = "High"
    }

    # Determine if policy is enabled
    # In Intune a policy is active by default. Only explicit state fields indicate disabled.
    # roleScopeTagIds being empty means global scope (not disabled), so we do NOT use it.
    $isEnabled = $true
    if ($policy.PSObject.Properties['state']) {
      # Conditional Access: state = 'enabled' | 'disabled' | 'enabledForReportingButNotEnforced'
      $isEnabled = ($policy.state -ne 'disabled')
    }
    elseif ($policy.PSObject.Properties['isEnabled']) {
      $isEnabled = [bool]$policy.isEnabled
    }
    elseif ($policy.PSObject.Properties['isAssigned']) {
      # isAssigned=false means policy exists but is not assigned to any group yet — still created/active
      # We still import it so the analyst can see it, but flag it
      $isEnabled = $true
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
Write-Host "=== Merlino Intune Policy Extractor ===" -ForegroundColor Green
Write-Host "Auth mode: $AuthMode" -ForegroundColor Yellow

# Load required assemblies for URL encoding
Add-Type -AssemblyName System.Web

# ---- Authentication ----
Write-Host "`nAuthenticating..." -ForegroundColor Cyan

try {
  if ($AuthMode -eq 'Interactive') {
    if ([string]::IsNullOrWhiteSpace($TenantId) -or $TenantId -eq "YOUR-TENANT-ID-HERE") {
      $TenantId = Read-Host "Enter your Tenant ID (Directory ID)"
    }
    Write-Host "Tenant ID: $TenantId" -ForegroundColor Gray
    $accessToken = Get-AccessTokenInteractive -TenantId $TenantId
  }
  else {
    Write-Host "Using Service Principal authentication (bypasses Conditional Access)" -ForegroundColor Yellow
    Write-Host "Client ID: $ClientId" -ForegroundColor Gray
    Write-Host "Tenant ID: $TenantId" -ForegroundColor Gray
    $accessToken = Get-AccessToken -ClientId $ClientId -ClientSecret $ClientSecret -TenantId $TenantId
  }
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
  $deviceConfigs = @(Get-IntuneDeviceConfigurations -AccessToken $accessToken)
  $allPolicies += $deviceConfigs

  # Get Configuration Policies (ASR, Antivirus settings, etc.)
  $configPolicies = @(Get-IntuneConfigurationPolicies -AccessToken $accessToken)
  $allPolicies += $configPolicies

  # Get Compliance Policies
  $compliancePolicies = @(Get-IntuneCompliancePolicies -AccessToken $accessToken)
  $allPolicies += $compliancePolicies

  # Get Endpoint Security Intents (Antivirus, Firewall, EDR, Disk Encryption, etc.)
  $intents = @(Get-IntuneIntents -AccessToken $accessToken)
  $allPolicies += $intents

  # Get App Protection Policies (MAM - iOS, Android, Windows)
  $appProtectionPolicies = @(Get-IntuneAppProtectionPolicies -AccessToken $accessToken)
  $allPolicies += $appProtectionPolicies

  # Get App Configuration Policies
  $appConfigPolicies = @(Get-IntuneAppConfigurationPolicies -AccessToken $accessToken)
  $allPolicies += $appConfigPolicies

  # Get Security Baselines
  $securityBaselines = @(Get-IntuneSecurityBaselines -AccessToken $accessToken)
  $allPolicies += $securityBaselines

  # Get Conditional Access Policies (Entra ID / Azure AD)
  $conditionalAccessPolicies = @(Get-IntuneConditionalAccessPolicies -AccessToken $accessToken)
  $allPolicies += $conditionalAccessPolicies

  # Get Group Policy Configurations (hybrid-joined devices)
  $groupPolicyConfigs = @(Get-IntuneGroupPolicyConfigurations -AccessToken $accessToken)
  $allPolicies += $groupPolicyConfigs

  # Get Enrollment Restrictions
  $enrollmentConfigs = @(Get-IntuneEnrollmentConfigurations -AccessToken $accessToken)
  $allPolicies += $enrollmentConfigs

  # Get PowerShell Scripts deployed via Intune
  $deviceScripts = @(Get-IntuneDeviceManagementScripts -AccessToken $accessToken)
  $allPolicies += $deviceScripts

  # Get Remediation Scripts (Proactive Remediations / Device Health Scripts)
  $healthScripts = @(Get-IntuneDeviceHealthScripts -AccessToken $accessToken)
  $allPolicies += $healthScripts

  # Get Windows Autopilot Deployment Profiles
  $autopilotProfiles = @(Get-IntuneAutopilotProfiles -AccessToken $accessToken)
  $allPolicies += $autopilotProfiles

  # Get Windows Feature Update Policies
  $featureUpdatePolicies = @(Get-IntuneFeatureUpdatePolicies -AccessToken $accessToken)
  $allPolicies += $featureUpdatePolicies

  # Get Windows Quality Update Policies
  $qualityUpdatePolicies = @(Get-IntuneQualityUpdatePolicies -AccessToken $accessToken)
  $allPolicies += $qualityUpdatePolicies

  # Get Endpoint Privilege Management elevations
  $privilegeElevations = @(Get-IntunePrivilegeManagement -AccessToken $accessToken)
  $allPolicies += $privilegeElevations

  Write-Host "`n=== SUMMARY ===" -ForegroundColor Cyan
  Write-Host "Device Configurations:              $($deviceConfigs.Count)" -ForegroundColor White
  Write-Host "Configuration Policies (ASR/AV):    $($configPolicies.Count)" -ForegroundColor White
  Write-Host "Compliance Policies:                $($compliancePolicies.Count)" -ForegroundColor White
  Write-Host "Endpoint Security Intents:          $($intents.Count)" -ForegroundColor White
  Write-Host "App Protection Policies:            $($appProtectionPolicies.Count)" -ForegroundColor White
  Write-Host "App Configuration Policies:         $($appConfigPolicies.Count)" -ForegroundColor White
  Write-Host "Security Baselines:                 $($securityBaselines.Count)" -ForegroundColor White
  Write-Host "Conditional Access Policies:        $($conditionalAccessPolicies.Count)" -ForegroundColor Cyan
  Write-Host "Group Policy Configurations:        $($groupPolicyConfigs.Count)" -ForegroundColor Cyan
  Write-Host "Enrollment Restrictions:            $($enrollmentConfigs.Count)" -ForegroundColor Cyan
  Write-Host "PowerShell Scripts (Intune):        $($deviceScripts.Count)" -ForegroundColor Cyan
  Write-Host "Remediation Scripts:                $($healthScripts.Count)" -ForegroundColor Cyan
  Write-Host "Autopilot Profiles:                 $($autopilotProfiles.Count)" -ForegroundColor Cyan
  Write-Host "Feature Update Policies:            $($featureUpdatePolicies.Count)" -ForegroundColor Cyan
  Write-Host "Quality Update Policies:            $($qualityUpdatePolicies.Count)" -ForegroundColor Cyan
  Write-Host "Privilege Management Elevations:    $($privilegeElevations.Count)" -ForegroundColor Cyan
  Write-Host "`nTotal policies collected: $($allPolicies.Count)" -ForegroundColor Green
  
  if ($allPolicies.Count -gt 0) {
    Write-Host "`n[i] Successfully extracted all Intune / Azure AD policies!" -ForegroundColor Green
    Write-Host "  Coverage: Device Configs, Compliance, Security Intents, App Protection," -ForegroundColor DarkGray
    Write-Host "            Conditional Access, Group Policy, Enrollment, Scripts," -ForegroundColor DarkGray
    Write-Host "            Remediations, Autopilot, Update Policies, Privilege Management" -ForegroundColor DarkGray
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

