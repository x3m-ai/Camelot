<#
.SYNOPSIS
    Merlino Sentinel Rules Extractor (Azure CLI) - Export Microsoft Sentinel alert rules using az cli authentication

.DESCRIPTION
    This script extracts all alert rules from a Microsoft Sentinel workspace using AZURE CLI authentication.
    Simpler and more reliable than device code flow - uses 'az login' for authentication.
    
    The script:
    - Uses Azure CLI for authentication (az login)
    - Retrieves access token via 'az account get-access-token'
    - Retrieves all Sentinel alert rules from the specified workspace
    - Maps rules to MITRE ATT&CK techniques (if available)
    - Generates two output files:
      1. Raw API response (AllSentinelRules.json or timestamped)
      2. Merlino Universal Catalogue JSON (ready for import)
    
    PREREQUISITES:
    - Azure CLI installed (https://docs.microsoft.com/en-us/cli/azure/install-azure-cli)
    - Run 'az login' before this script OR let the script do it for you

.PARAMETER TenantId
    Azure Tenant ID (optional - uses default tenant if not specified)
    Example: "b9563cbc-9874-41ab-b448-7e0f61aff3eb"

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

.PARAMETER SkipLogin
    Skip 'az login' if you're already authenticated

.EXAMPLE
    .\extract_sentinel_rules_azcli.ps1
    Runs with interactive prompts for all parameters

.EXAMPLE
    .\extract_sentinel_rules_azcli.ps1 -TenantId "b9563cbc-9874-41ab-b448-7e0f61aff3eb" -SubscriptionId "YOUR-SUB-ID" -ResourceGroupName "rg-sentinel" -WorkspaceName "sentinel-ws"
    Runs with specified parameters

.EXAMPLE
    .\extract_sentinel_rules_azcli.ps1 -SkipLogin -SubscriptionId "YOUR-SUB-ID" -ResourceGroupName "rg-sentinel" -WorkspaceName "sentinel-ws"
    Runs without re-authenticating (assumes az login was already done)

.NOTES
    File Name      : extract_sentinel_rules_azcli.ps1
    Author         : X3M.AI - Merlino Team
    Prerequisite   : Azure CLI, PowerShell 5.1+
    Copyright      : 2026 X3M.AI - All rights reserved
    
    Required Azure Permissions:
    - Microsoft.SecurityInsights/alertRules/read
    - Microsoft.OperationalInsights/workspaces/read
    
    API Version: 2023-02-01
    
.NOTES
    Author:  Nino Crudele
    LinkedIn: https://www.linkedin.com/in/ninocrudele
    Website:  https://merlino.x3m.ai
    License:  MIT

.LINK
    https://merlino-addin.x3m.ai
    https://docs.microsoft.com/en-us/cli/azure/
#>

#Requires -Version 5.1

param(
    [string]$TenantId = "",
    [string]$SubscriptionId = "",
    [string]$ResourceGroupName = "",
    [string]$WorkspaceName = "",
    [string]$OutputFolder = $PSScriptRoot,
    [string]$Source = "",
    [switch]$SkipLogin
)

# ---- Helper Functions ----

function Test-AzureCLI {
    try {
        $azVersion = az version 2>$null | ConvertFrom-Json
        if ($azVersion) {
            Write-Host "[OK] Azure CLI detected: v$($azVersion.'azure-cli')" -ForegroundColor Green
            return $true
        }
    }
    catch {
        # Ignore
    }
    
    Write-Host "[ERROR] Azure CLI not found!" -ForegroundColor Red
    Write-Host "Please install Azure CLI from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Quick install options:" -ForegroundColor Cyan
    Write-Host "  Windows: winget install Microsoft.AzureCLI" -ForegroundColor Gray
    Write-Host "  macOS:   brew install azure-cli" -ForegroundColor Gray
    Write-Host "  Linux:   curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash" -ForegroundColor Gray
    return $false
}

function Get-AzAccessToken {
    param(
        [string]$Resource = "https://management.azure.com"
    )
    
    Write-Host "Retrieving access token..." -ForegroundColor Cyan
    
    try {
        $token = az account get-access-token --resource $Resource --query accessToken --output tsv 2>$null
        
        if ([string]::IsNullOrWhiteSpace($token)) {
            throw "Empty token returned"
        }
        
        Write-Host "[OK] Access token retrieved successfully" -ForegroundColor Green
        return $token
    }
    catch {
        Write-Host "[ERROR] Failed to get access token: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "Try running 'az login' first" -ForegroundColor Yellow
        throw
    }
}

function Invoke-SentinelApi {
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
        Write-Host "[ERROR] API call failed: $($_.Exception.Message)" -ForegroundColor Red
        if ($_.Exception.Response) {
            $statusCode = $_.Exception.Response.StatusCode.Value__
            Write-Host "  HTTP Status: $statusCode" -ForegroundColor Red
            
            if ($statusCode -eq 403) {
                Write-Host "  You don't have permission to access this resource." -ForegroundColor Yellow
                Write-Host "  Required role: Microsoft Sentinel Reader or Security Reader" -ForegroundColor Yellow
            }
            elseif ($statusCode -eq 404) {
                Write-Host "  Resource not found. Check subscription, resource group, and workspace names." -ForegroundColor Yellow
            }
        }
        throw
    }
}

function ConvertTo-MerlinoCatalogue {
    param(
        [array]$Rules,
        [string]$Source
    )

    $catalogueRecords = @()

    foreach ($rule in $Rules) {
        # Extract MITRE techniques
        $tcodes = ""
        if ($rule.properties.techniques -and $rule.properties.techniques.Count -gt 0) {
            $tcodes = ($rule.properties.techniques -join ",")
        }
        
        # Determine priority from severity
        $priority = "Medium"
        switch ($rule.properties.severity) {
            "High" { $priority = "High" }
            "Medium" { $priority = "Medium" }
            "Low" { $priority = "Low" }
            "Informational" { $priority = "Low" }
        }
        
        # Check if rule is enabled
        $isEnabled = $rule.properties.enabled -eq $true

        # Build Catalogue record (Universal Import Schema v1.0)
        $catalogueRecord = [pscustomobject]@{
            Pick = $false
            CrossPick = 0
            Name = $rule.properties.displayName
            Source = $Source
            Priority = $priority
            Enabled = $isEnabled
            Validation_Score = ""
            Tests = 0
            Expected_Tests = 0
            Tests_Validated = 0
            TCodes = $tcodes
            Description = $rule.properties.description
            Notes = "Tactics: $($rule.properties.tactics -join ', ')"
            Data = ($rule | ConvertTo-Json -Depth 10 -Compress)
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
Write-Host ""
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "  Merlino Sentinel Rules Extractor (Azure CLI Method)" -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host ""

# Check Azure CLI is installed
if (-not (Test-AzureCLI)) {
    exit 1
}

# Prompt for parameters if not provided
if ([string]::IsNullOrWhiteSpace($SubscriptionId)) {
    Write-Host "Azure Subscription ID is required." -ForegroundColor Yellow
    $SubscriptionId = Read-Host "Enter your Azure Subscription ID"
}

if ([string]::IsNullOrWhiteSpace($ResourceGroupName)) {
    Write-Host "`nResource Group name is required." -ForegroundColor Yellow
    $ResourceGroupName = Read-Host "Enter your Resource Group name"
}

if ([string]::IsNullOrWhiteSpace($WorkspaceName)) {
    Write-Host "`nSentinel Workspace name is required." -ForegroundColor Yellow
    $WorkspaceName = Read-Host "Enter your Sentinel Workspace name"
}

# Prompt for Source if not provided
if ([string]::IsNullOrWhiteSpace($Source)) {
    Write-Host "`n--- Source Name Configuration ---" -ForegroundColor Cyan
    Write-Host "The 'Source' field helps distinguish between different environments in Merlino." -ForegroundColor White
    Write-Host "Examples: 'Microsoft Sentinel Production', 'Sentinel - Customer XYZ'" -ForegroundColor Gray
    
    $Source = Read-Host "Enter Source name (ENTER for default 'Microsoft Sentinel')"
    if ([string]::IsNullOrWhiteSpace($Source)) {
        $Source = "Microsoft Sentinel"
    }
}

Write-Host ""
Write-Host "Configuration:" -ForegroundColor Cyan
Write-Host "  Tenant:         $( if ($TenantId) { $TenantId } else { '(default)' } )" -ForegroundColor Gray
Write-Host "  Subscription:   $SubscriptionId" -ForegroundColor Gray
Write-Host "  Resource Group: $ResourceGroupName" -ForegroundColor Gray
Write-Host "  Workspace:      $WorkspaceName" -ForegroundColor Gray
Write-Host "  Source:         $Source" -ForegroundColor Gray
Write-Host "  Output Folder:  $OutputFolder" -ForegroundColor Gray
Write-Host ""

# ---- STEP 1: Azure CLI Login ----
if (-not $SkipLogin) {
    Write-Host "--- Step 1: Azure Authentication ---" -ForegroundColor Cyan
    
    $loginCmd = "az login"
    if (-not [string]::IsNullOrWhiteSpace($TenantId)) {
        $loginCmd = "az login --tenant $TenantId"
        Write-Host "Logging in to tenant: $TenantId" -ForegroundColor Yellow
    }
    else {
        Write-Host "Logging in to default tenant..." -ForegroundColor Yellow
    }
    
    Write-Host "Running: $loginCmd" -ForegroundColor Gray
    Write-Host ""
    
    try {
        if (-not [string]::IsNullOrWhiteSpace($TenantId)) {
            $loginResult = az login --tenant $TenantId 2>&1
        }
        else {
            $loginResult = az login 2>&1
        }
        
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[ERROR] Azure login failed" -ForegroundColor Red
            Write-Host $loginResult -ForegroundColor Red
            exit 1
        }
        
        Write-Host "[OK] Azure login successful" -ForegroundColor Green
    }
    catch {
        Write-Host "[ERROR] Azure login failed: $($_.Exception.Message)" -ForegroundColor Red
        exit 1
    }
}
else {
    Write-Host "--- Step 1: Azure Authentication (SKIPPED) ---" -ForegroundColor Cyan
    Write-Host "Using existing az login session" -ForegroundColor Yellow
}

# Set subscription context
Write-Host ""
Write-Host "Setting subscription context..." -ForegroundColor Cyan
try {
    az account set --subscription $SubscriptionId 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to set subscription"
    }
    Write-Host "[OK] Subscription set: $SubscriptionId" -ForegroundColor Green
}
catch {
    Write-Host "[ERROR] Failed to set subscription: $SubscriptionId" -ForegroundColor Red
    Write-Host "Make sure you have access to this subscription" -ForegroundColor Yellow
    exit 1
}

# ---- STEP 2: Get Access Token ----
Write-Host ""
Write-Host "--- Step 2: Get Access Token ---" -ForegroundColor Cyan

$accessToken = Get-AzAccessToken -Resource "https://management.azure.com"

# ---- STEP 3: Build API URL and Fetch Rules ----
Write-Host ""
Write-Host "--- Step 3: Fetch Sentinel Alert Rules ---" -ForegroundColor Cyan

$apiVersion = "2023-02-01"
$sentinelUri = "https://management.azure.com/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroupName/providers/Microsoft.OperationalInsights/workspaces/$WorkspaceName/providers/Microsoft.SecurityInsights/alertRules?api-version=$apiVersion"

Write-Host "API Endpoint:" -ForegroundColor Gray
Write-Host "  $sentinelUri" -ForegroundColor DarkGray
Write-Host ""

try {
    $response = Invoke-SentinelApi -Uri $sentinelUri -AccessToken $accessToken
    $rules = $response.value
    Write-Host "[OK] Retrieved $($rules.Count) alert rules" -ForegroundColor Green
}
catch {
    Write-Host "[ERROR] Failed to retrieve Sentinel rules" -ForegroundColor Red
    exit 1
}

if ($rules.Count -eq 0) {
    Write-Host ""
    Write-Host "[WARNING] No alert rules found in workspace!" -ForegroundColor Yellow
    Write-Host "Possible causes:" -ForegroundColor Yellow
    Write-Host "  - The workspace has no rules configured" -ForegroundColor Gray
    Write-Host "  - User lacks permissions to read rules" -ForegroundColor Gray
    Write-Host "  - Workspace name or resource group is incorrect" -ForegroundColor Gray
    exit 1
}

# ---- STEP 4: Save Output Files ----
Write-Host ""
Write-Host "--- Step 4: Save Output Files ---" -ForegroundColor Cyan

# Create output folder if it doesn't exist
if (-not (Test-Path $OutputFolder)) {
    New-Item -ItemType Directory -Path $OutputFolder -Force | Out-Null
}

# Generate timestamp and sanitized workspace name
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$workspaceSafe = Sanitize-FileName -s $WorkspaceName

# File 1: Raw API response (AllSentinelRules.json format as requested)
$rawFile = Join-Path $OutputFolder "AllSentinelRules.json"
Write-Host "Writing raw API response to: $rawFile" -ForegroundColor White
$response | ConvertTo-Json -Depth 100 | Out-File -FilePath $rawFile -Encoding UTF8
Write-Host "  [OK] Raw JSON saved" -ForegroundColor Green

# File 2: Timestamped legacy format
$legacyFile = Join-Path $OutputFolder ("sentinel-rules-{0}-{1}.json" -f $workspaceSafe, $stamp)
Write-Host "Writing timestamped rules to: $legacyFile" -ForegroundColor White
$rules | ConvertTo-Json -Depth 10 | Out-File -FilePath $legacyFile -Encoding UTF8
Write-Host "  [OK] Timestamped JSON saved" -ForegroundColor Green

# File 3: Merlino Universal Schema format
Write-Host "Converting to Merlino Universal Schema format..." -ForegroundColor Cyan
$catalogueData = ConvertTo-MerlinoCatalogue -Rules $rules -Source $Source

$universalSchema = @{
    schema = @{
        version = "1.0"
        type = "catalogue"
        description = "Microsoft Sentinel alert rules exported from $WorkspaceName"
        created = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
        source = "Microsoft Sentinel"
        workspace = $WorkspaceName
        resourceGroup = $ResourceGroupName
        subscriptionId = $SubscriptionId
        extractionMethod = "Azure CLI (az login)"
    }
    data = $catalogueData
}

$universalFile = Join-Path $OutputFolder ("merlino-catalogue-sentinel-{0}-{1}.json" -f $workspaceSafe, $stamp)
Write-Host "Writing Merlino Universal Schema to: $universalFile" -ForegroundColor White
$universalSchema | ConvertTo-Json -Depth 10 | Out-File -FilePath $universalFile -Encoding UTF8
Write-Host "  [OK] Catalogue JSON saved" -ForegroundColor Green

# ---- Summary ----
Write-Host ""
Write-Host "======================================================" -ForegroundColor Green
Write-Host "  EXTRACTION COMPLETE" -ForegroundColor Green
Write-Host "======================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Workspace:      $WorkspaceName" -ForegroundColor Cyan
Write-Host "Source:         $Source" -ForegroundColor Cyan
Write-Host "Rules exported: $($rules.Count)" -ForegroundColor Cyan
Write-Host ""
Write-Host "Output files:" -ForegroundColor Cyan
Write-Host "  1. Raw API:     $rawFile" -ForegroundColor White
Write-Host "  2. Timestamped: $legacyFile" -ForegroundColor White
Write-Host "  3. Catalogue:   $universalFile" -ForegroundColor White
Write-Host ""
Write-Host "Ready to import in Merlino Catalogue!" -ForegroundColor Green
Write-Host "TCodes are extracted from rule techniques when available." -ForegroundColor Yellow
Write-Host ""

# Rule type breakdown
$ruleTypes = $rules | Group-Object { $_.kind } | Sort-Object Count -Descending
if ($ruleTypes) {
    Write-Host "Rule Types Breakdown:" -ForegroundColor Cyan
    foreach ($type in $ruleTypes) {
        Write-Host "  $($type.Name): $($type.Count)" -ForegroundColor Gray
    }
}

# Techniques summary
$rulesWithTechniques = ($rules | Where-Object { $_.properties.techniques -and $_.properties.techniques.Count -gt 0 }).Count
Write-Host ""
Write-Host "MITRE Coverage: $rulesWithTechniques / $($rules.Count) rules have technique mappings" -ForegroundColor Cyan
