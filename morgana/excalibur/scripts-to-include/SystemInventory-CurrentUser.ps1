<#
===============================================================================
SYSTEM INVENTORY - CURRENT USER VERSION
===============================================================================

PURPOSE
-------
This script performs a controlled Windows host-information collection workflow
for authorised security detection validation.

Unlike the administrator/SYSTEM version, this script:

- DOES NOT require an elevated PowerShell session
- Creates the Scheduled Task for the CURRENT USER
- Runs the task with LIMITED privileges
- Stores all generated artifacts inside the current user's LOCALAPPDATA
- Changes ACLs only on files/directories created by the current user

SUPPORTED OPERATING SYSTEMS
---------------------------
- Windows 11
- Windows Server 2022
- Windows Server 2022 Core should also work because no GUI is required.

REQUIREMENTS
------------
- Windows PowerShell 5.1
- The user must be allowed to create Scheduled Tasks for their own account
- The user should remain logged on when the task executes
- No Internet connection is required
- Administrator privileges are NOT required

IMPORTANT
---------
This version uses an Interactive Scheduled Task.

That means the task is intended to run while the same user is logged on.

It does not request stored credentials and does not attempt to run with
elevated or SYSTEM privileges.

WHAT THE SCRIPT DOES
--------------------
1. Creates a working directory under:

       %LOCALAPPDATA%\SystemInventoryCache\

   Example:

       C:\Users\<user>\AppData\Local\SystemInventoryCache\

2. Creates collector:

       %LOCALAPPDATA%\SystemInventoryCache\InventoryCollector.ps1

3. Creates Scheduled Task:

       SystemInventory-User

4. Runs the task as:

       CURRENT LOGGED-ON USER
       RunLevel: Limited

5. Collects:
       - Current user/security context
       - Hostname
       - Operating system information
       - Computer/system information
       - Installed hotfixes visible to the user
       - IP configuration
       - Routing table
       - ARP cache
       - Network connections
       - Running processes visible to the user

6. Stores output in:

       %LOCALAPPDATA%\SystemInventoryCache\data\

   Example:

       inventory_20260821_143000.txt

7. Changes ACLs on the generated directory and output file:
       - Removes inherited permissions
       - Grants Full Control to the current user
       - Grants Full Control to LOCAL SYSTEM

WHAT THE SCRIPT DOES NOT DO
---------------------------
- Does not require Administrator
- Does not run as SYSTEM
- Does not request elevation
- Does not bypass UAC
- Does not disable Microsoft Defender
- Does not disable Windows logging
- Does not clear Event Logs
- Does not use encoded or obfuscated PowerShell
- Does not download files
- Does not connect to external infrastructure
- Does not collect passwords or credentials
- Does not perform lateral movement
- Does not exfiltrate collected information

HOW TO RUN
----------

1. Open a normal PowerShell window.
   Do NOT use "Run as Administrator".

2. Go to the directory containing this script, for example:

       Set-Location C:\Temp

3. Create the Scheduled Task and allow it to execute approximately
   two minutes later:

       .\SystemInventory-CurrentUser.ps1

4. To create the task and request immediate execution:

       .\SystemInventory-CurrentUser.ps1 -RunNow

5. To manually run an already-created task:

       Start-ScheduledTask -TaskName "SystemInventory-User"

6. When testing is complete:

       .\SystemInventory-CurrentUser.ps1 -Cleanup


QUICK VALIDATION
----------------

Check task:

       Get-ScheduledTask -TaskName "SystemInventory-User"

Check execution result:

       Get-ScheduledTaskInfo -TaskName "SystemInventory-User"

Check generated files:

       Get-ChildItem "$env:LOCALAPPDATA\SystemInventoryCache\data"

Check directory permissions:

       icacls.exe "$env:LOCALAPPDATA\SystemInventoryCache\data"

Detailed validation and troubleshooting instructions are included at the
bottom of this file.

===============================================================================
#>

[CmdletBinding()]
param(
    [switch]$RunNow,
    [switch]$Cleanup
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = "Stop"

$TaskName      = "SystemInventory-User"
$BasePath      = Join-Path $env:LOCALAPPDATA "SystemInventoryCache"
$StagePath     = Join-Path $BasePath "data"
$CollectorPath = Join-Path $BasePath "InventoryCollector.ps1"

$CurrentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
$CurrentUser     = $CurrentIdentity.Name
$CurrentUserSid  = $CurrentIdentity.User.Value

function Write-Step {
    param([string]$Message)
    Write-Host "[+] $Message"
}

Write-Host ""
Write-Host "Current user:"
Write-Host "  $CurrentUser"
Write-Host ""
Write-Host "Current user SID:"
Write-Host "  $CurrentUserSid"
Write-Host ""

# =============================================================================
# CLEANUP
# =============================================================================

if ($Cleanup) {

    Write-Step "Stopping scheduled task if required."

    try {
        Stop-ScheduledTask `
            -TaskName $TaskName `
            -ErrorAction SilentlyContinue
    }
    catch {}

    Write-Step "Removing scheduled task."

    try {
        Unregister-ScheduledTask `
            -TaskName $TaskName `
            -Confirm:$false `
            -ErrorAction SilentlyContinue
    }
    catch {}

    if (Test-Path $BasePath) {

        Write-Step "Resetting generated ACLs."

        try {
            & "$env:SystemRoot\System32\icacls.exe" `
                $BasePath `
                /reset `
                /T `
                /C | Out-Null
        }
        catch {}

        Write-Step "Removing generated files."

        Remove-Item `
            -Path $BasePath `
            -Recurse `
            -Force `
            -ErrorAction SilentlyContinue
    }

    Write-Host ""
    Write-Host "Cleanup completed."
    exit 0
}

# =============================================================================
# CREATE LOCAL WORKING DIRECTORY
# =============================================================================

Write-Step "Creating user working directory."

New-Item `
    -Path $StagePath `
    -ItemType Directory `
    -Force | Out-Null

# =============================================================================
# CREATE COLLECTOR SCRIPT
# =============================================================================

$Collector = @'
Set-StrictMode -Version 2.0
$ErrorActionPreference = "Continue"

$BasePath  = Join-Path $env:LOCALAPPDATA "SystemInventoryCache"
$StagePath = Join-Path $BasePath "data"

if (-not (Test-Path $StagePath)) {
    New-Item `
        -Path $StagePath `
        -ItemType Directory `
        -Force | Out-Null
}

$CurrentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
$CurrentUserSid  = $CurrentIdentity.User.Value

$Timestamp  = Get-Date -Format "yyyyMMdd_HHmmss"
$OutputFile = Join-Path $StagePath "inventory_$Timestamp.txt"

function Add-Section {

    param(
        [Parameter(Mandatory=$true)]
        [string]$Title,

        [Parameter(Mandatory=$true)]
        [scriptblock]$Command
    )

    Add-Content `
        -Path $OutputFile `
        -Value "`r`n============================================================"

    Add-Content `
        -Path $OutputFile `
        -Value $Title

    Add-Content `
        -Path $OutputFile `
        -Value "============================================================"

    try {

        $Result = & $Command 2>&1 |
            Out-String -Width 4096

        Add-Content `
            -Path $OutputFile `
            -Value $Result
    }
    catch {

        Add-Content `
            -Path $OutputFile `
            -Value "ERROR: $($_.Exception.Message)"
    }
}

@"
System inventory
Timestamp      : $(Get-Date -Format o)
Computer       : $env:COMPUTERNAME
Execution User : $([Security.Principal.WindowsIdentity]::GetCurrent().Name)
"@ | Out-File `
        -FilePath $OutputFile `
        -Encoding utf8


Add-Section `
    -Title "User context" `
    -Command {
        & "$env:SystemRoot\System32\whoami.exe" /all
    }


Add-Section `
    -Title "Host name" `
    -Command {
        & "$env:SystemRoot\System32\hostname.exe"
    }


Add-Section `
    -Title "System information" `
    -Command {
        & "$env:SystemRoot\System32\systeminfo.exe"
    }


Add-Section `
    -Title "Operating system information" `
    -Command {
        Get-CimInstance Win32_OperatingSystem |
            Format-List *
    }


Add-Section `
    -Title "Computer system information" `
    -Command {
        Get-CimInstance Win32_ComputerSystem |
            Format-List *
    }


Add-Section `
    -Title "Installed hotfixes" `
    -Command {
        Get-HotFix |
            Sort-Object InstalledOn -Descending |
            Format-Table -AutoSize
    }


Add-Section `
    -Title "IP configuration" `
    -Command {
        & "$env:SystemRoot\System32\ipconfig.exe" /all
    }


Add-Section `
    -Title "Routing table" `
    -Command {
        & "$env:SystemRoot\System32\route.exe" print
    }


Add-Section `
    -Title "ARP cache" `
    -Command {
        & "$env:SystemRoot\System32\arp.exe" -a
    }


Add-Section `
    -Title "Network connections" `
    -Command {
        & "$env:SystemRoot\System32\netstat.exe" -ano
    }


Add-Section `
    -Title "Running processes" `
    -Command {
        & "$env:SystemRoot\System32\tasklist.exe" /v
    }


Add-Content `
    -Path $OutputFile `
    -Value "`r`nCollection complete."


# =============================================================================
# MODIFY ACLS ON USER-OWNED GENERATED ARTIFACTS
#
# Current user SID = dynamically resolved
# S-1-5-18        = LOCAL SYSTEM
# =============================================================================

$Icacls = "$env:SystemRoot\System32\icacls.exe"

$UserFileAce   = "*$($CurrentUserSid):(F)"
$SystemFileAce = "*S-1-5-18:(F)"

$UserDirAce    = "*$($CurrentUserSid):(OI)(CI)(F)"
$SystemDirAce  = "*S-1-5-18:(OI)(CI)(F)"

& $Icacls `
    $OutputFile `
    /inheritance:r | Out-Null

& $Icacls `
    $OutputFile `
    /grant:r `
    $UserFileAce `
    $SystemFileAce | Out-Null

& $Icacls `
    $StagePath `
    /inheritance:r | Out-Null

& $Icacls `
    $StagePath `
    /grant:r `
    $UserDirAce `
    $SystemDirAce | Out-Null


Write-Output "Collection completed."
Write-Output "Output: $OutputFile"

'@

Write-Step "Writing collector."

Set-Content `
    -Path $CollectorPath `
    -Value $Collector `
    -Encoding UTF8

# =============================================================================
# CREATE CURRENT-USER SCHEDULED TASK
# =============================================================================

Write-Step "Creating Scheduled Task for current user."

$PowerShellExe =
    "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"

$ActionArguments = (
    '-NoProfile ' +
    '-NonInteractive ' +
    '-File "' + $CollectorPath + '"'
)

$Action = New-ScheduledTaskAction `
    -Execute $PowerShellExe `
    -Argument $ActionArguments

$TriggerTime = (Get-Date).AddMinutes(2)

$Trigger = New-ScheduledTaskTrigger `
    -Once `
    -At $TriggerTime

# Run as the current logged-on user, without elevation.
$Principal = New-ScheduledTaskPrincipal `
    -UserId $CurrentUser `
    -LogonType Interactive `
    -RunLevel Limited

$Settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Principal $Principal `
    -Settings $Settings `
    -Description "System inventory" `
    -Force | Out-Null


Write-Host ""
Write-Host "Scheduled Task created:"
Write-Host "  $TaskName"

Write-Host ""
Write-Host "Run as:"
Write-Host "  $CurrentUser"

Write-Host ""
Write-Host "Run level:"
Write-Host "  Limited"

Write-Host ""
Write-Host "Scheduled execution:"
Write-Host "  $TriggerTime"

Write-Host ""
Write-Host "Collector:"
Write-Host "  $CollectorPath"

Write-Host ""
Write-Host "Output directory:"
Write-Host "  $StagePath"


# =============================================================================
# OPTIONAL IMMEDIATE EXECUTION
# =============================================================================

if ($RunNow) {

    Write-Host ""
    Write-Step "Starting scheduled task."

    Start-ScheduledTask `
        -TaskName $TaskName

    Write-Host ""
    Write-Host "Task submitted for execution."
}


Write-Host ""
Write-Host "============================================================"
Write-Host " Current-user inventory task ready"
Write-Host "============================================================"

Write-Host ""
Write-Host "Run manually:"
Write-Host '  Start-ScheduledTask -TaskName "SystemInventory-User"'

Write-Host ""
Write-Host "Cleanup:"
Write-Host "  .\SystemInventory-CurrentUser.ps1 -Cleanup"

Write-Host ""


<#
===============================================================================
POST-RUN VALIDATION AND TROUBLESHOOTING
===============================================================================


1. CONFIRM THAT POWERSHELL IS NOT ELEVATED
-------------------------------------------------------------------------------

The script does not require Administrator privileges.

To view the current identity:

whoami.exe

To inspect the current token:

whoami.exe /groups


2. CHECK THAT THE SCHEDULED TASK EXISTS
-------------------------------------------------------------------------------

Get-ScheduledTask -TaskName "SystemInventory-User"


Short view:

Get-ScheduledTask -TaskName "SystemInventory-User" |
    Select-Object TaskName, State


3. CHECK WHICH USER THE TASK RUNS AS
-------------------------------------------------------------------------------

Get-ScheduledTask -TaskName "SystemInventory-User" |
    Select-Object `
        TaskName,
        State,
        @{Name="UserId";Expression={$_.Principal.UserId}},
        @{Name="LogonType";Expression={$_.Principal.LogonType}},
        @{Name="RunLevel";Expression={$_.Principal.RunLevel}}


Expected:

    UserId    = current logged-on user
    LogonType = Interactive
    RunLevel  = Limited


4. CHECK LAST RUN TIME AND RESULT
-------------------------------------------------------------------------------

Get-ScheduledTaskInfo -TaskName "SystemInventory-User"


Review:

    LastRunTime
    LastTaskResult
    NextRunTime


A successful execution normally shows:

    LastTaskResult : 0


If Windows shows:

    267011

this corresponds to:

    0x41303
    SCHED_S_TASK_HAS_NOT_RUN


5. MANUALLY START THE TASK
-------------------------------------------------------------------------------

Start-ScheduledTask -TaskName "SystemInventory-User"


Alternative:

schtasks.exe /Run /TN "SystemInventory-User"


6. CHECK THE USER WORKING DIRECTORY
-------------------------------------------------------------------------------

$InventoryPath = Join-Path $env:LOCALAPPDATA "SystemInventoryCache"

$InventoryPath

Test-Path $InventoryPath


Expected:

    True


7. CHECK THAT THE OUTPUT DIRECTORY EXISTS
-------------------------------------------------------------------------------

$DataPath = Join-Path $env:LOCALAPPDATA "SystemInventoryCache\data"

Test-Path $DataPath


Expected:

    True


8. CHECK THAT AN OUTPUT FILE WAS CREATED
-------------------------------------------------------------------------------

Get-ChildItem "$env:LOCALAPPDATA\SystemInventoryCache\data"


Expected filename:

    inventory_YYYYMMDD_HHMMSS.txt


Show latest:

Get-ChildItem "$env:LOCALAPPDATA\SystemInventoryCache\data\inventory_*.txt" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1 Name, Length, LastWriteTime, FullName


9. READ COLLECTED INFORMATION
-------------------------------------------------------------------------------

Get-Content "$env:LOCALAPPDATA\SystemInventoryCache\data\inventory_*.txt"


10. VERIFY EXPECTED COLLECTION SECTIONS
-------------------------------------------------------------------------------

Select-String `
    -Path "$env:LOCALAPPDATA\SystemInventoryCache\data\inventory_*.txt" `
    -Pattern "User context|Host name|System information|Operating system information|Computer system information|Installed hotfixes|IP configuration|Routing table|ARP cache|Network connections|Running processes|Collection complete"


11. CHECK FOR ERRORS
-------------------------------------------------------------------------------

Select-String `
    -Path "$env:LOCALAPPDATA\SystemInventoryCache\data\inventory_*.txt" `
    -Pattern "ERROR:"


If no output is returned, no collector section reported an error.


12. CHECK DIRECTORY ACL
-------------------------------------------------------------------------------

icacls.exe "$env:LOCALAPPDATA\SystemInventoryCache\data"


Expected entries should include:

    <CURRENT USER>:(OI)(CI)(F)
    NT AUTHORITY\SYSTEM:(OI)(CI)(F)


13. CHECK OUTPUT FILE ACL
-------------------------------------------------------------------------------

icacls.exe "$env:LOCALAPPDATA\SystemInventoryCache\data\inventory_*.txt"


Expected entries should include:

    <CURRENT USER>:(F)
    NT AUTHORITY\SYSTEM:(F)


14. CONFIRM THAT ACL INHERITANCE WAS REMOVED
-------------------------------------------------------------------------------

(Get-Acl "$env:LOCALAPPDATA\SystemInventoryCache\data").AreAccessRulesProtected


Expected:

    True


15. CHECK TASK SCHEDULER SERVICE
-------------------------------------------------------------------------------

Get-Service Schedule


Expected:

    Status : Running


16. CHECK TASK SCHEDULER OPERATIONAL EVENT LOG
-------------------------------------------------------------------------------

Get-WinEvent -ListLog "Microsoft-Windows-TaskScheduler/Operational" |
    Select-Object LogName, IsEnabled, RecordCount, LastWriteTime


If:

    IsEnabled : False

the Task Scheduler Operational log is disabled.


17. ENABLE TASK SCHEDULER OPERATIONAL LOG
-------------------------------------------------------------------------------

IMPORTANT:

Enabling this Windows Event Log normally requires an elevated Administrator
PowerShell session.

The inventory simulation itself does NOT require Administrator.

If an authorised administrator is available, the log can be enabled with:

wevtutil.exe set-log "Microsoft-Windows-TaskScheduler/Operational" /enabled:true


Verify:

Get-WinEvent -ListLog "Microsoft-Windows-TaskScheduler/Operational" |
    Select-Object LogName, IsEnabled, RecordCount, LastWriteTime


Enabling this log does NOT recreate historical events.

After it has been enabled, execute the user task again:

Start-ScheduledTask -TaskName "SystemInventory-User"


18. VIEW TASK SCHEDULER EVENTS
-------------------------------------------------------------------------------

Get-WinEvent `
    -LogName "Microsoft-Windows-TaskScheduler/Operational" `
    -MaxEvents 100 |
Where-Object {
    $_.Message -like "*SystemInventory-User*"
} |
Select-Object TimeCreated, Id, Message |
Format-List


Useful events can include:

    100 - Task started
    102 - Task completed
    110 - Task instance launched
    129 - Process launched
    200 - Action started
    201 - Action completed
    325 - Task queued


19. QUERY FULL TASK DETAILS
-------------------------------------------------------------------------------

schtasks.exe /Query /TN "SystemInventory-User" /V /FO LIST


Review:

    Status
    Last Run Time
    Last Result
    Task To Run
    Run As User
    Scheduled Task State


20. VERIFY THE COLLECTOR EXISTS
-------------------------------------------------------------------------------

Test-Path "$env:LOCALAPPDATA\SystemInventoryCache\InventoryCollector.ps1"


Expected:

    True


21. QUICK END-TO-END VALIDATION
-------------------------------------------------------------------------------

Expected workflow:

    Standard user
          |
          v
    Scheduled Task created for current user
          |
          v
    Task executes with LIMITED token
          |
          v
    powershell.exe executes InventoryCollector.ps1
          |
          +--> whoami.exe
          +--> hostname.exe
          +--> systeminfo.exe
          +--> Get-CimInstance
          +--> Get-HotFix
          +--> ipconfig.exe
          +--> route.exe
          +--> arp.exe
          +--> netstat.exe
          +--> tasklist.exe
          |
          v
    inventory_*.txt created in LOCALAPPDATA
          |
          v
    collected information written locally
          |
          v
    icacls.exe modifies ACLs on user-owned artifacts


VALIDATION IS SUCCESSFUL WHEN
-----------------------------

    [1] SystemInventory-User Scheduled Task exists

    [2] Principal is the current user

    [3] RunLevel is Limited

    [4] inventory_*.txt exists

    [5] Output contains expected sections

    [6] No unexpected ERROR: entries appear

    [7] ACL contains current user and SYSTEM

    [8] AreAccessRulesProtected returns True


22. WINDOWS 11 / WINDOWS SERVER 2022 CHECKS
-------------------------------------------------------------------------------

PowerShell version:

$PSVersionTable.PSVersion


Task Scheduler:

Get-Service Schedule


If Microsoft Defender for Endpoint telemetry is part of the test:

Get-Service Sense


NOTE:
MDE is not required for the script itself.


23. IMPORTANT DIFFERENCE FROM THE SYSTEM VERSION
-------------------------------------------------------------------------------

Administrator/SYSTEM version:

    Administrator launches script
            |
            v
    Scheduled Task runs as SYSTEM
            |
            v
    C:\ProgramData\...


Current-user version:

    Standard user launches script
            |
            v
    Scheduled Task runs as same user
            |
            v
    %LOCALAPPDATA%\...


This produces a different detection scenario and is useful for validating
behaviour that does not depend on prior privilege escalation.


24. CLEANUP
-------------------------------------------------------------------------------

.\SystemInventory-CurrentUser.ps1 -Cleanup


After cleanup:

Get-ScheduledTask `
    -TaskName "SystemInventory-User" `
    -ErrorAction SilentlyContinue


Test-Path "$env:LOCALAPPDATA\SystemInventoryCache"


Expected:

    Scheduled Task is no longer returned

    Test-Path returns:
        False


===============================================================================
END POST-RUN VALIDATION AND TROUBLESHOOTING
===============================================================================
#>
