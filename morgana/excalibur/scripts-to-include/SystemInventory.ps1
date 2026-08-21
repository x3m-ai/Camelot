<#
===============================================================================
SYSTEM INVENTORY - DETECTION VALIDATION SCRIPT
===============================================================================

PURPOSE
-------
This script performs a controlled Windows host-information collection workflow
for authorised security detection validation.

It creates a Windows Scheduled Task, executes the collection as LOCAL SYSTEM,
stores the collected information locally, and changes permissions on the
generated artifacts.

SUPPORTED OPERATING SYSTEMS
---------------------------
- Windows 11
- Windows Server 2022
- Windows Server 2022 Core should also work because no GUI is required.

REQUIREMENTS
------------
- Windows PowerShell 5.1
- Run from an elevated PowerShell session (Run as Administrator)
- Windows Task Scheduler service must be available
- No Internet connection is required

WHAT THE SCRIPT DOES
--------------------
1. Creates:
       C:\ProgramData\SystemInventoryCache\

2. Creates collector:
       C:\ProgramData\SystemInventoryCache\InventoryCollector.ps1

3. Creates Scheduled Task:
       SystemInventory

4. Runs the task as:
       NT AUTHORITY\SYSTEM

5. Collects:
       - Current user/security context
       - Hostname
       - Operating system information
       - Computer/system information
       - Installed hotfixes
       - IP configuration
       - Routing table
       - ARP cache
       - Active/listening network connections
       - Running processes

6. Stores output in:
       C:\ProgramData\SystemInventoryCache\data\

   Example:
       inventory_20260821_141500.txt

7. Changes ACLs on the generated directory and output file:
       - Removes inherited permissions
       - Grants Full Control to SYSTEM
       - Grants Full Control to local Administrators

WHAT THE SCRIPT DOES NOT DO
---------------------------
- Does not disable Microsoft Defender
- Does not disable Windows logging
- Does not clear Event Logs
- Does not use encoded or obfuscated PowerShell
- Does not download files
- Does not connect to external infrastructure
- Does not collect passwords or credentials
- Does not perform lateral movement
- Does not perform persistence beyond the explicitly created Scheduled Task
- Does not exfiltrate collected information

HOW TO RUN
----------

1. Open PowerShell as Administrator.

2. Go to the directory containing this script, for example:

       Set-Location C:\Temp

3. Create the Scheduled Task and allow it to execute at its scheduled time:

       .\SystemInventory.ps1

   The task is scheduled approximately two minutes after creation.

4. To create the task and request immediate execution:

       .\SystemInventory.ps1 -RunNow

5. To manually run an already-created task:

       Start-ScheduledTask -TaskName "SystemInventory"

6. When testing is complete, remove the task and generated artifacts:

       .\SystemInventory.ps1 -Cleanup


QUICK VALIDATION AFTER EXECUTION
--------------------------------

Check task:

       Get-ScheduledTask -TaskName "SystemInventory"

Check execution result:

       Get-ScheduledTaskInfo -TaskName "SystemInventory"

Check generated files:

       Get-ChildItem "C:\ProgramData\SystemInventoryCache\data"

Check permissions:

       icacls.exe "C:\ProgramData\SystemInventoryCache\data"

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

$TaskName      = "SystemInventory"
$BasePath      = "C:\ProgramData\SystemInventoryCache"
$StagePath     = Join-Path $BasePath "data"
$CollectorPath = Join-Path $BasePath "InventoryCollector.ps1"

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
    Write-Error "Run this script from an elevated PowerShell session."
    exit 1
}

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

Write-Step "Creating working directory."

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

$BasePath  = "C:\ProgramData\SystemInventoryCache"
$StagePath = Join-Path $BasePath "data"

if (-not (Test-Path $StagePath)) {
    New-Item `
        -Path $StagePath `
        -ItemType Directory `
        -Force | Out-Null
}

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
Execution User : $env:USERNAME
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
# MODIFY GENERATED ARTIFACT PERMISSIONS
#
# S-1-5-18       = LOCAL SYSTEM
# S-1-5-32-544   = BUILTIN\Administrators
# =============================================================================

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


Write-Output "Collection completed."
Write-Output "Output: $OutputFile"

'@

Write-Step "Writing collector."

Set-Content `
    -Path $CollectorPath `
    -Value $Collector `
    -Encoding UTF8

# =============================================================================
# CREATE SCHEDULED TASK
# =============================================================================

Write-Step "Creating scheduled task."

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
    -Description "System inventory" `
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
Write-Host "Output directory:"
Write-Host "  $StagePath"


# =============================================================================
# OPTIONAL IMMEDIATE EXECUTION
# =============================================================================

if ($RunNow) {

    Write-Host ""
    Write-Step "Starting scheduled task."

    & "$env:SystemRoot\System32\schtasks.exe" `
        /Run `
        /TN $TaskName

    Write-Host ""
    Write-Host "Task submitted for execution."
}


Write-Host ""
Write-Host "============================================================"
Write-Host " System inventory task ready"
Write-Host "============================================================"

Write-Host ""
Write-Host "Run manually:"
Write-Host '  Start-ScheduledTask -TaskName "SystemInventory"'

Write-Host ""
Write-Host "Cleanup:"
Write-Host "  .\SystemInventory.ps1 -Cleanup"

Write-Host ""


<#
===============================================================================
POST-RUN VALIDATION AND TROUBLESHOOTING
===============================================================================


1. CHECK THAT THE SCHEDULED TASK EXISTS
-------------------------------------------------------------------------------

Get-ScheduledTask -TaskName "SystemInventory"


Short view:

Get-ScheduledTask -TaskName "SystemInventory" |
    Select-Object TaskName, State


Expected:
    TaskName : SystemInventory


2. CHECK LAST RUN TIME AND RESULT
-------------------------------------------------------------------------------

Get-ScheduledTaskInfo -TaskName "SystemInventory"


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

This can appear before the first successful Scheduled Task execution.


3. MANUALLY START THE TASK
-------------------------------------------------------------------------------

Start-ScheduledTask -TaskName "SystemInventory"


Alternative:

schtasks.exe /Run /TN "SystemInventory"


Wait several seconds before validating the results.


4. CHECK THAT THE OUTPUT DIRECTORY EXISTS
-------------------------------------------------------------------------------

Test-Path "C:\ProgramData\SystemInventoryCache\data"


Expected:

    True


5. CHECK THAT AN OUTPUT FILE WAS CREATED
-------------------------------------------------------------------------------

Get-ChildItem "C:\ProgramData\SystemInventoryCache\data"


Expected file format:

    inventory_YYYYMMDD_HHMMSS.txt


Show the latest file:

Get-ChildItem "C:\ProgramData\SystemInventoryCache\data\inventory_*.txt" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1 Name, Length, LastWriteTime, FullName


6. READ THE COLLECTED INFORMATION
-------------------------------------------------------------------------------

Get-Content "C:\ProgramData\SystemInventoryCache\data\inventory_*.txt"


7. VERIFY EXPECTED COLLECTION SECTIONS
-------------------------------------------------------------------------------

Select-String `
    -Path "C:\ProgramData\SystemInventoryCache\data\inventory_*.txt" `
    -Pattern "User context|Host name|System information|Operating system information|Computer system information|Installed hotfixes|IP configuration|Routing table|ARP cache|Network connections|Running processes|Collection complete"


Expected sections include:

    User context
    Host name
    System information
    Operating system information
    Computer system information
    Installed hotfixes
    IP configuration
    Routing table
    ARP cache
    Network connections
    Running processes
    Collection complete


8. CHECK THE OUTPUT FOR ERRORS
-------------------------------------------------------------------------------

Select-String `
    -Path "C:\ProgramData\SystemInventoryCache\data\inventory_*.txt" `
    -Pattern "ERROR:"


If the command returns no results, no collector section reported an error.


9. CHECK STAGING DIRECTORY PERMISSIONS
-------------------------------------------------------------------------------

icacls.exe "C:\ProgramData\SystemInventoryCache\data"


Expected entries include:

    BUILTIN\Administrators:(OI)(CI)(F)
    NT AUTHORITY\SYSTEM:(OI)(CI)(F)


Expected command result:

    Successfully processed 1 files; Failed processing 0 files


10. CHECK OUTPUT FILE PERMISSIONS
-------------------------------------------------------------------------------

icacls.exe "C:\ProgramData\SystemInventoryCache\data\inventory_*.txt"


Expected entries include:

    BUILTIN\Administrators:(F)
    NT AUTHORITY\SYSTEM:(F)


11. CONFIRM THAT ACL INHERITANCE WAS REMOVED
-------------------------------------------------------------------------------

(Get-Acl "C:\ProgramData\SystemInventoryCache\data").AreAccessRulesProtected


Expected:

    True


True confirms that inherited ACLs have been removed/protected on the generated
staging directory.


12. CHECK TASK SCHEDULER SERVICE
-------------------------------------------------------------------------------

Get-Service Schedule


Expected:

    Status : Running


13. CHECK TASK SCHEDULER OPERATIONAL EVENT LOG
-------------------------------------------------------------------------------

Get-WinEvent -ListLog "Microsoft-Windows-TaskScheduler/Operational" |
    Select-Object LogName, IsEnabled, RecordCount, LastWriteTime


If:

    IsEnabled : False

the Task Scheduler Operational log is disabled.


14. ENABLE TASK SCHEDULER OPERATIONAL LOG
-------------------------------------------------------------------------------

Run from an elevated PowerShell session:

wevtutil.exe set-log "Microsoft-Windows-TaskScheduler/Operational" /enabled:true


Verify:

Get-WinEvent -ListLog "Microsoft-Windows-TaskScheduler/Operational" |
    Select-Object LogName, IsEnabled, RecordCount, LastWriteTime


Expected:

    IsEnabled : True


IMPORTANT:
Enabling this log does NOT recreate historical Task Scheduler events.

If the original execution occurred while the log was disabled, run the task
again after enabling the log:

Start-ScheduledTask -TaskName "SystemInventory"


15. VIEW TASK SCHEDULER EVENTS
-------------------------------------------------------------------------------

Get-WinEvent `
    -LogName "Microsoft-Windows-TaskScheduler/Operational" `
    -MaxEvents 100 |
Where-Object {
    $_.Message -like "*SystemInventory*"
} |
Select-Object TimeCreated, Id, Message |
Format-List


Useful events include:

    100 - Task started
    102 - Task completed
    110 - Task instance launched
    129 - Process launched
    200 - Action started
    201 - Action completed
    325 - Task queued


For example, a successful execution can show:

    Task Scheduler started ...
    "\SystemInventory"
    for user "NT AUTHORITY\SYSTEM"


and:

    Task Scheduler launched action
    "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"


16. QUERY FULL TASK DETAILS WITH SCHTASKS
-------------------------------------------------------------------------------

schtasks.exe /Query /TN "SystemInventory" /V /FO LIST


Review:

    Status
    Last Run Time
    Last Result
    Task To Run
    Run As User
    Scheduled Task State


17. VERIFY THAT THE COLLECTOR SCRIPT EXISTS
-------------------------------------------------------------------------------

Test-Path "C:\ProgramData\SystemInventoryCache\InventoryCollector.ps1"


Expected:

    True


18. QUICK END-TO-END VALIDATION
-------------------------------------------------------------------------------

Expected workflow:

    Scheduled Task created
            |
            v
    Task executes as SYSTEM
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
    inventory_*.txt created
            |
            v
    collected information written locally
            |
            v
    icacls.exe modifies generated ACLs


VALIDATION IS SUCCESSFUL WHEN
-----------------------------

    [1] SystemInventory Scheduled Task exists

    [2] Task Scheduler confirms that the task executed

    [3] Task runs as NT AUTHORITY\SYSTEM

    [4] inventory_*.txt exists

    [5] Output file contains all expected sections

    [6] No unexpected ERROR: entries appear

    [7] Directory ACL contains SYSTEM and Administrators

    [8] Output file ACL contains SYSTEM and Administrators

    [9] AreAccessRulesProtected returns True


19. WINDOWS 11 / WINDOWS SERVER 2022 CHECKS
-------------------------------------------------------------------------------

PowerShell version:

$PSVersionTable.PSVersion


Expected:
    Windows PowerShell 5.1 is supported.


Task Scheduler:

Get-Service Schedule


On a Defender for Endpoint onboarded machine, the following may also be useful:

Get-Service Sense


NOTE:
The script itself does not require Microsoft Defender for Endpoint.
MDE is only required if Defender XDR telemetry/hunting is part of the test.


20. CLEANUP
-------------------------------------------------------------------------------

From the directory containing the original script:

.\SystemInventory.ps1 -Cleanup


The cleanup removes:

    Scheduled Task:
        SystemInventory

    Directory:
        C:\ProgramData\SystemInventoryCache\

    Collector:
        InventoryCollector.ps1

    Generated output:
        inventory_*.txt


After cleanup, verify:

Get-ScheduledTask -TaskName "SystemInventory" -ErrorAction SilentlyContinue

Test-Path "C:\ProgramData\SystemInventoryCache"


Expected:

    Scheduled Task is no longer returned

    Test-Path returns:
        False


===============================================================================
END POST-RUN VALIDATION AND TROUBLESHOOTING
===============================================================================
#>
