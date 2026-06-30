<#
.SYNOPSIS
    Merlino Sentinel Rules Extractor - Export Microsoft Sentinel alert rules to Merlino Universal Catalogue format

.DESCRIPTION
    This script extracts all alert rules from a Microsoft Sentinel workspace and converts them into 
    Merlino's Universal Catalogue format for import into the Merlino Excel Add-in.
    
    The script:
    - Authenticates using one of two methods:
        a) Service Principal (client credentials) - recommended for automation/CI
        b) Interactive browser login via Connect-AzAccount (-InteractiveLogin switch) - recommended for manual use
    - Retrieves all Sentinel alert rules from the specified workspace
    - Maps rules to MITRE ATT&CK techniques (if available)
    - Generates two output files:
      1. Raw API response (legacy format)
      2. Merlino Universal Catalogue JSON (ready for import)
    
    The Catalogue format includes:
    - Rule metadata (name, severity, enabled status)
    - MITRE ATT&CK technique mappings (TCodes field)
    - Source environment identifier (for multi-tenant tracking)
    - Full rule configuration in Data field

.PARAMETER TenantId
    Azure AD Tenant ID (Directory ID)
    Example: "af65d60d-6cea-4881-9ce3-caecd6f5023d"

.PARAMETER ClientId
    Service Principal Application (Client) ID
    Example: "1cbd4b17-6ec9-47c9-a425-beb98f6ddcd4"

.PARAMETER ClientSecret
    Service Principal Client Secret (Value, not Secret ID)
    Example: "<YOUR_CLIENT_SECRET_VALUE>"

.PARAMETER SubscriptionId
    Azure Subscription ID containing the Sentinel workspace
    Example: "46270230-d55e-4d1a-b572-87635ce7a440"

.PARAMETER ResourceGroupName
    Resource Group name containing the Sentinel workspace
    Example: "rg-merlino"

.PARAMETER WorkspaceName
    Sentinel workspace name (Log Analytics workspace)
    Example: "sentinel-merlino-workspace"

.PARAMETER OutputFolder
    Directory where output files will be saved (default: script location)

.PARAMETER Source
    Source identifier for Catalogue records (e.g., "Microsoft Sentinel Production")
    If not provided, will prompt interactively

.PARAMETER InteractiveLogin
    Switch. When specified, authenticates interactively via browser (Connect-AzAccount).
    Requires the Az.Accounts PowerShell module. ClientId and ClientSecret are not needed.
    Example: .\extract_sentinel_rules.ps1 -InteractiveLogin -TenantId "YOUR-TENANT-ID" -SubscriptionId "YOUR-SUB-ID" ...

.EXAMPLE
    .\extract_sentinel_rules.ps1
    Runs with default parameters and prompts for Source name

.EXAMPLE
    .\extract_sentinel_rules.ps1 -TenantId "YOUR-TENANT-ID" -ClientId "YOUR-CLIENT-ID" -ClientSecret "YOUR-SECRET" -Source "Production"
    Runs with specified credentials and Source name

.EXAMPLE
    .\extract_sentinel_rules.ps1 -InteractiveLogin -TenantId "YOUR-TENANT-ID" -SubscriptionId "YOUR-SUB-ID" -ResourceGroupName "rg-sentinel" -WorkspaceName "my-workspace" -Source "Production"
    Runs with interactive browser login (no service principal required)

.NOTES
    File Name      : extract_sentinel_rules.ps1
    Author         : X3M.AI - Merlino Team
    Prerequisite   : PowerShell 5.1 or higher

    
    Authentication options:

    SERVICE PRINCIPAL (default):
    - Requires an Azure AD App Registration with client credentials
    - Required RBAC: Microsoft Sentinel Reader (or Contributor) on the workspace
    - Parameters: -TenantId, -ClientId, -ClientSecret, -SubscriptionId

    INTERACTIVE LOGIN (-InteractiveLogin switch):
    - Requires the Az.Accounts PowerShell module (auto-installed if missing)
    - Opens a browser window for sign-in (supports MFA, Conditional Access)
    - Required RBAC: Microsoft Sentinel Reader (or higher) on the subscription
    - Parameters: -TenantId, -SubscriptionId (no ClientId/ClientSecret needed)
    - Compatible with Az.Accounts 2.x, 3.x, 4.x, 5.x (SecureString handled automatically)
    
    API Version: 2023-02-01
    
.NOTES
    Author:  Nino Crudele
    LinkedIn: https://www.linkedin.com/in/ninocrudele
    Website:  https://merlino.x3m.ai
    License:  MIT

.LINK
    https://merlino-addin.x3m.ai
    https://docs.microsoft.com/en-us/rest/api/securityinsights/
#>

#Requires -Version 5.1
param(
    [string]$TenantId = "YOUR-TENANT-ID-HERE",
    [string]$ClientId = "YOUR-CLIENT-ID-HERE", 
    [string]$ClientSecret = "YOUR-CLIENT-SECRET-HERE",
    [string]$SubscriptionId = "YOUR-SUBSCRIPTION-ID-HERE",
    [string]$ResourceGroupName = "YOUR-RESOURCE-GROUP-NAME",
    [string]$WorkspaceName = "YOUR-SENTINEL-WORKSPACE-NAME",
    [string]$OutputFolder = $PSScriptRoot,
    [string]$Source,  # Will be prompted if not provided
    [switch]$InteractiveLogin  # Use browser-based interactive login instead of service principal
)

# ---- Interactive Source Prompt ----
if ([string]::IsNullOrWhiteSpace($Source)) {
    Write-Host "`n=== Source Name Configuration ===" -ForegroundColor Cyan
    Write-Host "The 'Source' field helps distinguish between different environments in Merlino." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor White
    Write-Host "  - 'Microsoft Sentinel Production'  (production environment)" -ForegroundColor Gray
    Write-Host "  - 'Microsoft Sentinel Development' (dev/test environment)" -ForegroundColor Gray
    Write-Host "  - 'Sentinel - Customer XYZ'        (customer-specific)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "This allows you to:" -ForegroundColor White
    Write-Host "  [OK] Compare rules between Development and Production" -ForegroundColor Green
    Write-Host "  [OK] Filter Catalogue by environment" -ForegroundColor Green
    Write-Host "  [OK] Track rule changes across environments" -ForegroundColor Green
    Write-Host ""
    
    $userInput = Read-Host "Enter Source name (press ENTER for default 'Microsoft Sentinel')"
    
    if ([string]::IsNullOrWhiteSpace($userInput)) {
        $Source = "Microsoft Sentinel"
        Write-Host "Using default: $Source" -ForegroundColor Green
    } else {
        $Source = $userInput.Trim()
        Write-Host "Using custom source: $Source" -ForegroundColor Green
    }
    Write-Host ""
}

function Get-ServicePrincipalToken {
    param($TenantId, $ClientId, $ClientSecret)
    
    Write-Host "Authenticating with Service Principal..." -ForegroundColor Cyan
    $tokenUri = "https://login.microsoftonline.com/$TenantId/oauth2/v2.0/token"
    
    $body = @{
        grant_type    = "client_credentials"
        client_id     = $ClientId
        client_secret = $ClientSecret
        scope         = "https://management.azure.com/.default"
    }
    
    try {
        $response = Invoke-RestMethod -Uri $tokenUri -Method POST -Body $body -ContentType "application/x-www-form-urlencoded"
        Write-Host "Authentication successful!" -ForegroundColor Green
        return $response.access_token
    }
    catch {
        Write-Host "ERROR: Authentication failed - $($_.Exception.Message)" -ForegroundColor Red
        throw
    }
}

function Get-InteractiveToken {
    param($TenantId, $SubscriptionId)

    Write-Host "Authenticating interactively via browser..." -ForegroundColor Cyan
    Write-Host "A browser window will open for sign-in." -ForegroundColor Yellow

    if (-not (Get-Module -ListAvailable -Name Az.Accounts)) {
        Write-Host "Az.Accounts module not found. Installing (CurrentUser scope)..." -ForegroundColor Yellow
        Install-Module -Name Az.Accounts -Scope CurrentUser -Force -AllowClobber
    }

    Import-Module Az.Accounts -ErrorAction Stop

    $connectParams = @{ TenantId = $TenantId }
    if (-not [string]::IsNullOrWhiteSpace($SubscriptionId) -and $SubscriptionId -ne "YOUR-SUBSCRIPTION-ID-HERE") {
        $connectParams.SubscriptionId = $SubscriptionId
    }

    Connect-AzAccount @connectParams | Out-Null

    $tokenObj = Get-AzAccessToken -ResourceUrl "https://management.azure.com/"
    $rawToken = $tokenObj.Token
    if ($rawToken -is [System.Security.SecureString]) {
        $bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($rawToken)
        $rawToken = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
        [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }
    Write-Host "Authentication successful!" -ForegroundColor Green
    return $rawToken
}

function Get-SentinelAlertRules {
    param($AccessToken, $SubscriptionId, $ResourceGroupName, $WorkspaceName)
    
    $headers = @{ Authorization = "Bearer $AccessToken"; "Content-Type" = "application/json" }
    $uri = "https://management.azure.com/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroupName/providers/Microsoft.OperationalInsights/workspaces/$WorkspaceName/providers/Microsoft.SecurityInsights/alertRules?api-version=2023-02-01"
    
    Write-Host "Fetching Sentinel alert rules..." -ForegroundColor Cyan
    
    try {
        $response = Invoke-RestMethod -Uri $uri -Headers $headers -Method GET
        Write-Host "Found $($response.value.Count) alert rules" -ForegroundColor Green
        return $response.value
    }
    catch {
        Write-Host "ERROR: Failed to get alert rules - $($_.Exception.Message)" -ForegroundColor Red
        throw
    }
}

Write-Host "=== Merlino Sentinel Extractor ===" -ForegroundColor Green

try {
    if ($InteractiveLogin) {
        $token = Get-InteractiveToken -TenantId $TenantId -SubscriptionId $SubscriptionId
    } else {
        $token = Get-ServicePrincipalToken -TenantId $TenantId -ClientId $ClientId -ClientSecret $ClientSecret
    }
    $rules = Get-SentinelAlertRules -AccessToken $token -SubscriptionId $SubscriptionId -ResourceGroupName $ResourceGroupName -WorkspaceName $WorkspaceName
    
    if ($rules.Count -eq 0) {
        Write-Host "No rules found" -ForegroundColor Yellow
        exit
    }
    
    Write-Host "`nFound rules:" -ForegroundColor Cyan
    foreach ($rule in $rules) {
        $name = if ($rule.properties.displayName) { $rule.properties.displayName } else { $rule.name }
        $severity = if ($rule.properties.severity) { $rule.properties.severity } else { "Unknown" }
        Write-Host "  - $name [$severity]" -ForegroundColor Gray
    }
    
    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    
    # Legacy format (raw Sentinel API response)
    $legacyFile = "sentinel-alertRules-$WorkspaceName-$timestamp.json"
    $rules | ConvertTo-Json -Depth 10 | Out-File (Join-Path $OutputFolder $legacyFile) -Encoding UTF8
    
    # Universal Catalogue format (Merlino import-ready)
    $catalogue = @()
    foreach ($rule in $rules) {
        # Extract fields from Sentinel rule
        $displayName = if ($rule.properties.displayName) { $rule.properties.displayName } else { $rule.name }
        $severity = if ($rule.properties.severity) { $rule.properties.severity } else { "Medium" }
        $enabled = if ($null -ne $rule.properties.enabled) { $rule.properties.enabled } else { $false }
        $description = if ($rule.properties.description) { $rule.properties.description } else { "" }
        
        # Extract techniques (comma-separated string)
        $techniques = ""
        if ($rule.properties.techniques -and $rule.properties.techniques.Count -gt 0) {
            $techniques = ($rule.properties.techniques -join ",")
        }
        
        # Build Catalogue record
        $catalogue += [pscustomobject]@{
            Pick = $false
            CrossPick = 0
            Name = $displayName
            Source = $Source
            Priority = $severity
            Enabled = $enabled
            Validation_Score = ""
            Tests = 0
            Expected_Tests = 0
            Tests_Validated = 0
            TCodes = $techniques
            Description = $description
            Notes = ""
            Data = ($rule | ConvertTo-Json -Depth 10 -Compress)
        }
    }
    
    # Wrap in schema envelope
    $schema = @{
        schema = @{
            version = "1.0"
            type = "catalogue"
            description = "Microsoft Sentinel alert rules from workspace $WorkspaceName"
            source = $Source
            workspace = $WorkspaceName
            created = (Get-Date -Format "yyyy-MM-ddTHH:mm:ss.fffZ")
            totalRecords = $catalogue.Count
        }
        data = $catalogue
    }
    
    $catalogueFile = "merlino-catalogue-sentinel-$WorkspaceName-$timestamp.json"
    $schema | ConvertTo-Json -Depth 12 | Out-File (Join-Path $OutputFolder $catalogueFile) -Encoding UTF8
    
    Write-Host "`n=== SUCCESS ===" -ForegroundColor Green
    Write-Host "Rules exported: $($rules.Count)" -ForegroundColor Cyan
    Write-Host "Source: $Source" -ForegroundColor Cyan
    Write-Host "`nFiles created:" -ForegroundColor Yellow
    Write-Host "  Legacy (raw API):  $legacyFile" -ForegroundColor Gray
    Write-Host "  Catalogue (import): $catalogueFile" -ForegroundColor Green
    Write-Host "`nReady to import in Merlino Catalogue!" -ForegroundColor Yellow
    
} catch {
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
}
