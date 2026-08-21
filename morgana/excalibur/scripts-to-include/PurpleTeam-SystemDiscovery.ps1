<#
.SYNOPSIS
    Purple Team Windows System Discovery Simulation

.DESCRIPTION
    Creates and executes a Windows Scheduled Task that performs a controlled
    sequence of discovery commands, writes the collected output to a local
    staging directory, and modifies the ACLs of the staged data.

    ATT&CK techniques exercised:
      T1053.005 - Scheduled Task/Job: Scheduled Task
      T1033     - System Owner/User Discovery
      T1082     - System Information Discovery
      T1016     - System Network Configuration Discovery
      T1049     - System Network Connections Discovery
      T1057     - Process Discovery
      T1074.001 - Data Staged: Local Data Staging
      T1222.001 - File and Directory Permissions Modification: Windows Permissions

    Intended only for authorised Purple Team and detection-validation activity.

.EXAMPLE
    .\PurpleTeam-SystemDiscovery.ps1

    Creates the simulation and schedules it to run approximately two minutes later.

.EXAMPLE
    .\PurpleTeam-SystemDiscovery.ps1 -RunNow

    Creates the simulation and immediately starts the scheduled task.

.EXAMPLE
    .\PurpleTeam-SystemDiscovery.ps1 -Cleanup

    Stops and removes the task, restores inherited ACLs where possible,
    and removes the simulation directory.
#>

[CmdletBinding()]
param(
    [switch]$RunNow,
    [switch]$Cleanup
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = "Stop"

$TaskName      = "PurpleTeam-SystemDiscovery"
$BasePath      = "C:\ProgramData\PurpleTeamSimulation"
$StagePath     = Join-Path $BasePath "staging"
$CollectorPath = Join-Path $BasePath "SystemDiscoveryCollector.ps1"

function Test-IsAdministrator {
    $Identity  = [Security.Principal.WindowsIdentity]::GetCurrent()
    $Principal = New-Object Security.Principal.WindowsPrincipal($Identity)

    return $Principal.IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator
    )
}

function Write-Step {
    param([string]$Message)

    Write-Host "[+] $Message"
}

if (-not (Test-IsAdministrator)) {
    Write-Error "This simulation must be run from an elevated PowerShell session."
    exit 1
}

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

if ($Cleanup) {

    Write-Step "Stopping scheduled task if it is running."

    try {
        Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
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

        Write-Step "Resetting file and directory ACL inheritance."

        try {
            & "$env:SystemRoot\System32\icacls.exe" `
                $BasePath `
                /reset `
                /T `
                /C | Out-Null
        }
        catch {}

        Write-Step "Removing simulation directory."

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

# ---------------------------------------------------------------------------
# Local staging directory - T1074.001
# ---------------------------------------------------------------------------

Write-Step "Creating local staging directory."

New-Item `
    -Path $StagePath `
    -ItemType Directory `
    -Force | Out-Null

# ---------------------------------------------------------------------------
# Collector payload
# ---------------------------------------------------------------------------

$Collector = @'
Set-StrictMode -Version 2.0
$ErrorActionPreference = "Continue"

$BasePath  = "C:\ProgramData\PurpleTeamSimulation"
$StagePath = Join-Path $BasePath "staging"

if (-not (Test-Path $StagePath)) {
    New-Item -Path $StagePath -ItemType Directory -Force | Out-Null
}

$Timestamp  = Get-Date -Format "yyyyMMdd_HHmmss"
$OutputFile = Join-Path $StagePath "system_discovery_$Timestamp.txt"

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
        $Result = & $Command 2>&1 | Out-String -Width 4096

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
PURPLE TEAM SECURITY TEST
=========================

Simulation      : Scheduled Discovery and Local Data Staging
Timestamp       : $(Get-Date -Format o)
Computer        : $env:COMPUTERNAME
Execution User  : $env:USERNAME

ATT&CK Techniques
-----------------
T1053.005  Scheduled Task
T1033      System Owner/User Discovery
T1082      System Information Discovery
T1016      System Network Configuration Discovery
T1049      System Network Connections Discovery
T1057      Process Discovery
T1074.001  Local Data Staging
T1222.001  Windows Permissions Modification

"@ | Out-File `
        -FilePath $OutputFile `
        -Encoding utf8

# ---------------------------------------------------------------------------
# T1033 - System Owner/User Discovery
# ---------------------------------------------------------------------------

Add-Section `
    -Title "T1033 - SYSTEM OWNER / USER DISCOVERY - whoami /all" `
    -Command {
        & "$env:SystemRoot\System32\whoami.exe" /all
    }

# ---------------------------------------------------------------------------
# T1082 - System Information Discovery
# ---------------------------------------------------------------------------

Add-Section `
    -Title "T1082 - HOSTNAME DISCOVERY - hostname" `
    -Command {
        & "$env:SystemRoot\System32\hostname.exe"
    }

Add-Section `
    -Title "T1082 - SYSTEM INFORMATION DISCOVERY - systeminfo" `
    -Command {
        & "$env:SystemRoot\System32\systeminfo.exe"
    }

Add-Section `
    -Title "T1082 - OPERATING SYSTEM INFORMATION - CIM" `
    -Command {
        Get-CimInstance Win32_OperatingSystem |
            Format-List *
    }

Add-Section `
    -Title "T1082 - COMPUTER SYSTEM INFORMATION - CIM" `
    -Command {
        Get-CimInstance Win32_ComputerSystem |
            Format-List *
    }

Add-Section `
    -Title "T1082 - INSTALLED HOTFIXES" `
    -Command {
        Get-HotFix |
            Sort-Object InstalledOn -Descending |
            Format-Table -AutoSize
    }

# ---------------------------------------------------------------------------
# T1016 - System Network Configuration Discovery
# ---------------------------------------------------------------------------

Add-Section `
    -Title "T1016 - IP CONFIGURATION - ipconfig /all" `
    -Command {
        & "$env:SystemRoot\System32\ipconfig.exe" /all
    }

Add-Section `
    -Title "T1016 - ROUTING TABLE - route print" `
    -Command {
        & "$env:SystemRoot\System32\route.exe" print
    }

Add-Section `
    -Title "T1016 - ARP CACHE - arp -a" `
    -Command {
        & "$env:SystemRoot\System32\arp.exe" -a
    }

# ---------------------------------------------------------------------------
# T1049 - System Network Connections Discovery
# ---------------------------------------------------------------------------

Add-Section `
    -Title "T1049 - NETWORK CONNECTIONS - netstat -ano" `
    -Command {
        & "$env:SystemRoot\System32\netstat.exe" -ano
    }

# ---------------------------------------------------------------------------
# T1057 - Process Discovery
# ---------------------------------------------------------------------------

Add-Section `
    -Title "T1057 - PROCESS DISCOVERY - tasklist /v" `
    -Command {
        & "$env:SystemRoot\System32\tasklist.exe" /v
    }

# ---------------------------------------------------------------------------
# Local staging marker - T1074.001
# ---------------------------------------------------------------------------

Add-Content `
    -Path $OutputFile `
    -Value "`r`nLOCAL DATA STAGING COMPLETE - T1074.001"

# ---------------------------------------------------------------------------
# T1222.001 - Windows File/Directory Permissions Modification
#
# Remove inherited ACLs and retain Full Control for:
#   S-1-5-18       = LOCAL SYSTEM
#   S-1-5-32-544   = BUILTIN\Administrators
#
# Using SIDs avoids dependency on the Windows display language.
# ---------------------------------------------------------------------------

$Icacls = "$env:SystemRoot\System32\icacls.exe"

& $Icacls `
    $OutputFile `
    /inheritance:r | Out-Null

& $Icacls `
    $OutputFile `
    /grant:r `
    "*S-1-5-18:(F)" `
    "*S-1-5-32-544:(F)" | Out-Null

& $Icacls `
    $StagePath `
    /inheritance:r | Out-Null

& $Icacls `
    $StagePath `
    /grant:r `
    "*S-1-5-18:(OI)(CI)(F)" `
    "*S-1-5-32-544:(OI)(CI)(F)" | Out-Null

Write-Output "Purple Team simulation completed."
Write-Output "Output: $OutputFile"
'@

Write-Step "Writing collector script."

Set-Content `
    -Path $CollectorPath `
    -Value $Collector `
    -Encoding UTF8

# ---------------------------------------------------------------------------
# T1053.005 - Scheduled Task
# ---------------------------------------------------------------------------

Write-Step "Creating scheduled task."

$PowerShellExe = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"

$ActionArguments = (
    '-NoProfile ' +
    '-NonInteractive ' +
    '-ExecutionPolicy Bypass ' +
    '-File "' + $CollectorPath + '"'
)

$Action = New-ScheduledTaskAction `
    -Execute $PowerShellExe `
    -Argument $ActionArguments

$TriggerTime = (Get-Date).AddMinutes(2)

$Trigger = New-ScheduledTaskTrigger `
    -Once `
    -At $TriggerTime

$Principal = New-ScheduledTaskPrincipal `
    -UserId "SYSTEM" `
    -LogonType ServiceAccount `
    -RunLevel Highest

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
    -Description "Purple Team ATT&CK System Discovery Simulation" `
    -Force | Out-Null

Write-Host ""
Write-Host "Scheduled task created:"
Write-Host "  $TaskName"
Write-Host ""
Write-Host "Scheduled execution:"
Write-Host "  $TriggerTime"
Write-Host ""
Write-Host "Collector:"
Write-Host "  $CollectorPath"
Write-Host ""
Write-Host "Staging directory:"
Write-Host "  $StagePath"

# ---------------------------------------------------------------------------
# Optional immediate execution
#
# schtasks.exe is intentionally used here so that the task invocation itself
# also produces a normal Windows process/command-line observable.
# ---------------------------------------------------------------------------

if ($RunNow) {

    Write-Host ""
    Write-Step "Starting scheduled task immediately."

    & "$env:SystemRoot\System32\schtasks.exe" `
        /Run `
        /TN $TaskName

    Write-Host ""
    Write-Host "The task has been submitted for execution."
}

Write-Host ""
Write-Host "============================================================"
Write-Host " Purple Team simulation ready"
Write-Host "============================================================"
Write-Host ""
Write-Host "Run immediately:"
Write-Host "  .\PurpleTeam-SystemDiscovery.ps1 -RunNow"
Write-Host ""
Write-Host "Cleanup:"
Write-Host "  .\PurpleTeam-SystemDiscovery.ps1 -Cleanup"
Write-Host ""


<#
===============================================================================
POST-RUN VALIDATION / TROUBLESHOOTING
===============================================================================

Use the following commands after running the simulation.

------------------------------------------------------------------------------
1. CHECK THAT THE SCHEDULED TASK EXISTS
------------------------------------------------------------------------------

Get-ScheduledTask -TaskName "PurpleTeam-SystemDiscovery"

Expected:
- The task should be returned.
- TaskName should be PurpleTeam-SystemDiscovery.

For a shorter view:

Get-ScheduledTask -TaskName "PurpleTeam-SystemDiscovery" |
    Select-Object TaskName, State


------------------------------------------------------------------------------
2. CHECK LAST RUN TIME AND RESULT
------------------------------------------------------------------------------

Get-ScheduledTaskInfo -TaskName "PurpleTeam-SystemDiscovery"

Check:

    LastRunTime
    LastTaskResult
    NextRunTime

A LastTaskResult of 0 normally indicates successful completion.

NOTE:
Immediately after task creation, Windows may temporarily show:

    LastTaskResult : 267011

267011 = 0x41303 = SCHED_S_TASK_HAS_NOT_RUN

If the task has subsequently been started, run the command again after a few
seconds and verify the Task Scheduler Operational log as described below.


------------------------------------------------------------------------------
3. START THE TASK MANUALLY IF REQUIRED
------------------------------------------------------------------------------

Start-ScheduledTask -TaskName "PurpleTeam-SystemDiscovery"

Alternative using schtasks.exe:

schtasks.exe /Run /TN "PurpleTeam-SystemDiscovery"


------------------------------------------------------------------------------
4. CHECK THAT THE COLLECTION FILE EXISTS
------------------------------------------------------------------------------

Get-ChildItem "C:\ProgramData\PurpleTeamSimulation\staging"

A file similar to this should exist:

    system_discovery_YYYYMMDD_HHMMSS.txt

To display the most recently created collection file:

Get-ChildItem "C:\ProgramData\PurpleTeamSimulation\staging\system_discovery_*.txt" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1 Name, Length, LastWriteTime, FullName


------------------------------------------------------------------------------
5. READ THE COLLECTED DATA
------------------------------------------------------------------------------

Get-Content "C:\ProgramData\PurpleTeamSimulation\staging\system_discovery_*.txt"


------------------------------------------------------------------------------
6. CONFIRM THAT ALL DISCOVERY SECTIONS WERE EXECUTED
------------------------------------------------------------------------------

Select-String `
    -Path "C:\ProgramData\PurpleTeamSimulation\staging\system_discovery_*.txt" `
    -Pattern "T1033|T1082|T1016|T1049|T1057|T1074"


Expected sections include:

    T1033      System Owner/User Discovery
    T1082      System Information Discovery
    T1016      System Network Configuration Discovery
    T1049      System Network Connections Discovery
    T1057      Process Discovery
    T1074.001  Local Data Staging


------------------------------------------------------------------------------
7. CHECK FOR ERRORS INSIDE THE COLLECTION FILE
------------------------------------------------------------------------------

Select-String `
    -Path "C:\ProgramData\PurpleTeamSimulation\staging\system_discovery_*.txt" `
    -Pattern "ERROR:"

If this command returns no results, no collector command reported an error.


------------------------------------------------------------------------------
8. VERIFY THE STAGING MARKER
------------------------------------------------------------------------------

Select-String `
    -Path "C:\ProgramData\PurpleTeamSimulation\staging\system_discovery_*.txt" `
    -Pattern "LOCAL DATA STAGING COMPLETE"

Expected:

    LOCAL DATA STAGING COMPLETE - T1074.001


------------------------------------------------------------------------------
9. CHECK DIRECTORY PERMISSIONS
------------------------------------------------------------------------------

icacls.exe "C:\ProgramData\PurpleTeamSimulation\staging"

Expected permissions should include:

    BUILTIN\Administrators:(OI)(CI)(F)
    NT AUTHORITY\SYSTEM:(OI)(CI)(F)

Expected result:

    Successfully processed 1 files; Failed processing 0 files


------------------------------------------------------------------------------
10. CHECK COLLECTION FILE PERMISSIONS
------------------------------------------------------------------------------

icacls.exe "C:\ProgramData\PurpleTeamSimulation\staging\system_discovery_*.txt"

Expected permissions should include:

    BUILTIN\Administrators:(F)
    NT AUTHORITY\SYSTEM:(F)


------------------------------------------------------------------------------
11. VERIFY THAT ACL INHERITANCE WAS REMOVED
------------------------------------------------------------------------------

(Get-Acl "C:\ProgramData\PurpleTeamSimulation\staging").AreAccessRulesProtected

Expected:

    True

True means ACL inheritance is disabled/protected, which confirms the
T1222.001 Windows Permissions Modification portion of the simulation.


------------------------------------------------------------------------------
12. CHECK TASK SCHEDULER OPERATIONAL LOG
------------------------------------------------------------------------------

First check whether the Task Scheduler Operational log is enabled:

Get-WinEvent -ListLog "Microsoft-Windows-TaskScheduler/Operational" |
    Select-Object LogName, IsEnabled, RecordCount, LastWriteTime


If IsEnabled is False, enable it from an elevated PowerShell session:

wevtutil.exe set-log "Microsoft-Windows-TaskScheduler/Operational" /enabled:true


Verify again:

Get-WinEvent -ListLog "Microsoft-Windows-TaskScheduler/Operational" |
    Select-Object LogName, IsEnabled, RecordCount, LastWriteTime


IMPORTANT:
Enabling this log does NOT recreate previous events.

If the log was disabled during the original simulation, enable it and then
run the task again:

Start-ScheduledTask -TaskName "PurpleTeam-SystemDiscovery"


------------------------------------------------------------------------------
13. VIEW TASK SCHEDULER EVENTS FOR THIS SIMULATION
------------------------------------------------------------------------------

Get-WinEvent `
    -LogName "Microsoft-Windows-TaskScheduler/Operational" `
    -MaxEvents 100 |
Where-Object {
    $_.Message -like "*PurpleTeam-SystemDiscovery*"
} |
Select-Object TimeCreated, Id, Message |
Format-List


Useful Task Scheduler events may include:

    Event ID 100  - Task started
    Event ID 102  - Task completed
    Event ID 110  - Task instance launched
    Event ID 129  - Process launched
    Event ID 200  - Action started
    Event ID 201  - Action completed
    Event ID 325  - Task instance queued


A successful execution should show events similar to:

    Task Scheduler started ... "\PurpleTeam-SystemDiscovery"
    for user "NT AUTHORITY\SYSTEM"

and:

    Task Scheduler launched action
    "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"


------------------------------------------------------------------------------
14. QUERY THE TASK WITH SCHTASKS FOR FULL DETAILS
------------------------------------------------------------------------------

schtasks.exe /Query /TN "PurpleTeam-SystemDiscovery" /V /FO LIST

Review:

    Status
    Last Run Time
    Last Result
    Task To Run
    Run As User
    Scheduled Task State


------------------------------------------------------------------------------
15. VERIFY THAT THE WINDOWS TASK SCHEDULER SERVICE IS RUNNING
------------------------------------------------------------------------------

Get-Service Schedule

Expected:

    Status : Running


------------------------------------------------------------------------------
16. QUICK END-TO-END VALIDATION
------------------------------------------------------------------------------

The expected behaviour chain is:

    Scheduled Task created
            |
            v
    Task runs as SYSTEM
            |
            v
    powershell.exe launches collector
            |
            +--> whoami.exe
            +--> hostname.exe
            +--> systeminfo.exe
            +--> ipconfig.exe
            +--> route.exe
            +--> arp.exe
            +--> netstat.exe
            +--> tasklist.exe
            |
            v
    Local collection file created
            |
            v
    Local Data Staging completed
            |
            v
    icacls.exe modifies permissions


Validation is considered successful when:

    [1] PurpleTeam-SystemDiscovery exists
    [2] Task Scheduler confirms execution
    [3] system_discovery_*.txt exists
    [4] Discovery sections are present in the file
    [5] LOCAL DATA STAGING COMPLETE is present
    [6] No unexpected ERROR: entries are present
    [7] ACLs show SYSTEM and Administrators
    [8] AreAccessRulesProtected returns True


------------------------------------------------------------------------------
17. CLEANUP
------------------------------------------------------------------------------

When testing is complete:

.\PurpleTeam-SystemDiscovery.ps1 -Cleanup

This removes:

    - Scheduled Task: PurpleTeam-SystemDiscovery
    - C:\ProgramData\PurpleTeamSimulation\
    - Collector script
    - Staged collection files

===============================================================================
END POST-RUN VALIDATION / TROUBLESHOOTING
===============================================================================
#>

