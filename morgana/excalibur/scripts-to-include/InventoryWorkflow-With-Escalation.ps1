<#
===============================================================================
INVENTORY WORKFLOW - USER -> ADMIN -> SYSTEM
===============================================================================

PURPOSE
-------
This script performs an authorised Windows detection-validation workflow that
moves through three normal Windows security contexts:

    STANDARD / CURRENT USER
            |
            v
    ADMINISTRATOR via normal Windows UAC approval
            |
            v
    LOCAL SYSTEM via Windows Scheduled Task

The privilege transition is intentional and interactive.

THIS SCRIPT DOES NOT BYPASS UAC.

If the current user is a standard user, Windows will request authorised
administrator credentials.

If the current user is already a local administrator but PowerShell is not
elevated, Windows will display the normal UAC consent prompt.

No credentials are stored, supplied, captured, or automated by this script.


SUPPORTED OPERATING SYSTEMS
---------------------------
- Windows 11
- Windows Server 2022 with an interactive desktop / UAC environment

NOTE:
For this specific user-to-admin workflow, Windows Server Core is not the
preferred target because the test intentionally relies on an interactive UAC
approval/credential prompt.


REQUIREMENTS
------------
- Windows PowerShell 5.1
- Start the script from a normal, NON-ELEVATED PowerShell session
- An authorised administrator must approve the UAC prompt
- Windows Task Scheduler service must be available
- No Internet connection is required


WORKFLOW
--------
STAGE 1 - CURRENT USER

The initial process runs as the current logged-on user.

It creates:

    %LOCALAPPDATA%\InventoryWorkflowCache\user\

and writes:

    user_context_YYYYMMDD_HHMMSS.txt

The user stage collects:

    - whoami /all
    - hostname
    - systeminfo
    - ipconfig /all
    - route print
    - arp -a
    - netstat -ano
    - tasklist /v


STAGE 2 - UAC / ADMINISTRATOR

The script then launches a second PowerShell process using:

    Start-Process powershell.exe -Verb RunAs

Windows displays the normal UAC prompt.

The administrator must manually approve the prompt or enter authorised
administrator credentials.

The elevated process creates:

    C:\ProgramData\InventoryWorkflowCache\

and writes:

    admin_context_YYYYMMDD_HHMMSS.txt


STAGE 3 - LOCAL SYSTEM

The elevated process creates the Scheduled Task:

    InventoryMaintenance

The task runs as:

    NT AUTHORITY\SYSTEM

and launches:

    C:\ProgramData\InventoryWorkflowCache\InventoryCollector.ps1

The SYSTEM collector writes:

    C:\ProgramData\InventoryWorkflowCache\data\
        inventory_YYYYMMDD_HHMMSS.txt

It then changes ACLs on the generated SYSTEM-stage directory and output file.


WHAT THIS SCRIPT DOES NOT DO
----------------------------
- Does not bypass UAC
- Does not exploit a vulnerability
- Does not dump credentials
- Does not capture passwords
- Does not store administrator credentials
- Does not disable Microsoft Defender
- Does not disable Windows logging
- Does not clear Event Logs
- Does not obfuscate or encode PowerShell
- Does not download external content
- Does not perform lateral movement
- Does not perform network exfiltration


HOW TO RUN
----------
IMPORTANT:
Start from a NORMAL PowerShell session.

Do not initially use "Run as Administrator" if you want to exercise the full
user -> admin -> SYSTEM transition.

Example:

    Set-Location C:\Temp

    .\InventoryWorkflow.ps1


The script will:

    1. Run the user-stage collection
    2. Display the Windows UAC prompt
    3. Continue only after authorised elevation
    4. Create the SYSTEM Scheduled Task
    5. Schedule it approximately two minutes later


TO START THE SYSTEM TASK IMMEDIATELY
------------------------------------
Run:

    .\InventoryWorkflow.ps1 -RunNow

The same UAC prompt will occur, then the elevated stage will create and
immediately start the SYSTEM Scheduled Task.


CLEANUP
-------
From a normal PowerShell window:

    .\InventoryWorkflow.ps1 -Cleanup

The script removes the current user's generated artifacts and asks for normal
UAC approval to remove the administrator/SYSTEM-stage task and artifacts.


QUICK VALIDATION
----------------
User-stage file:

    Get-ChildItem "$env:LOCALAPPDATA\InventoryWorkflowCache\user"

SYSTEM task:

    Get-ScheduledTask -TaskName "InventoryMaintenance"

SYSTEM-stage files:

    Get-ChildItem "C:\ProgramData\InventoryWorkflowCache\data"

Full validation and troubleshooting instructions are included at the bottom.

===============================================================================
#>

[CmdletBinding()]
param(
    [switch]$ElevatedStage,
    [switch]$RunNow,
    [switch]$Cleanup,

    [string]$OriginalUser,
    [string]$OriginalUserLocalAppData
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = "Stop"

$TaskName       = "InventoryMaintenance"
$SystemBasePath = "C:\ProgramData\InventoryWorkflowCache"
$SystemDataPath = Join-Path $SystemBasePath "data"
$CollectorPath  = Join-Path $SystemBasePath "InventoryCollector.ps1"

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

function Invoke-Collection {

    param(
        [Parameter(Mandatory=$true)]
        [string]$OutputFile,

        [Parameter(Mandatory=$true)]
        [string]$StageName
    )

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
Stage          : $StageName
Timestamp      : $(Get-Date -Format o)
Computer       : $env:COMPUTERNAME
Execution User : $([Security.Principal.WindowsIdentity]::GetCurrent().Name)
"@ | Out-File `
        -FilePath $OutputFile `
        -Encoding utf8

    Add-Section "User context" {
        & "$env:SystemRoot\System32\whoami.exe" /all
    }

    Add-Section "Host name" {
        & "$env:SystemRoot\System32\hostname.exe"
    }

    Add-Section "System information" {
        & "$env:SystemRoot\System32\systeminfo.exe"
    }

    Add-Section "IP configuration" {
        & "$env:SystemRoot\System32\ipconfig.exe" /all
    }

    Add-Section "Routing table" {
        & "$env:SystemRoot\System32\route.exe" print
    }

    Add-Section "ARP cache" {
        & "$env:SystemRoot\System32\arp.exe" -a
    }

    Add-Section "Network connections" {
        & "$env:SystemRoot\System32\netstat.exe" -ano
    }

    Add-Section "Running processes" {
        & "$env:SystemRoot\System32\tasklist.exe" /v
    }

    Add-Content `
        -Path $OutputFile `
        -Value "`r`nCollection complete."
}

function Start-ElevatedStage {

    param(
        [switch]$RunNowForElevatedStage,
        [switch]$CleanupForElevatedStage
    )

    $ScriptPath = $PSCommandPath

    if ([string]::IsNullOrWhiteSpace($ScriptPath)) {
        throw "Unable to determine the current script path."
    }

    $CurrentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $UserName        = $CurrentIdentity.Name
    $UserLocalAppData = $env:LOCALAPPDATA

    $Arguments = @(
        "-NoProfile"
        "-File `"$ScriptPath`""
        "-ElevatedStage"
        "-OriginalUser `"$UserName`""
        "-OriginalUserLocalAppData `"$UserLocalAppData`""
    )

    if ($RunNowForElevatedStage) {
        $Arguments += "-RunNow"
    }

    if ($CleanupForElevatedStage) {
        $Arguments += "-Cleanup"
    }

    Write-Host ""
    Write-Host "Windows will now request authorised administrator approval."
    Write-Host ""

    try {

        Start-Process `
            -FilePath "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" `
            -Verb RunAs `
            -ArgumentList ($Arguments -join " ")
    }
    catch {

        Write-Error "Elevation was cancelled or could not be started: $($_.Exception.Message)"
        exit 1
    }
}

# =============================================================================
# STAGE 1 - CURRENT USER
# =============================================================================

if (-not $ElevatedStage) {

    $CurrentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $CurrentUser     = $CurrentIdentity.Name
    $CurrentIsAdmin  = Test-IsAdministrator

    Write-Host ""
    Write-Host "============================================================"
    Write-Host " Stage 1 - Current User"
    Write-Host "============================================================"
    Write-Host ""
    Write-Host "User:"
    Write-Host "  $CurrentUser"
    Write-Host ""
    Write-Host "Already elevated:"
    Write-Host "  $CurrentIsAdmin"
    Write-Host ""

    $UserBasePath = Join-Path $env:LOCALAPPDATA "InventoryWorkflowCache"
    $UserDataPath = Join-Path $UserBasePath "user"

    if ($Cleanup) {

        Write-Step "Removing current-user artifacts."

        if (Test-Path $UserBasePath) {

            Remove-Item `
                -Path $UserBasePath `
                -Recurse `
                -Force `
                -ErrorAction SilentlyContinue
        }

        if ($CurrentIsAdmin) {

            Write-Step "Current process is already elevated. Continuing cleanup."

            $ElevatedStage = $true
            $OriginalUser = $CurrentUser
            $OriginalUserLocalAppData = $env:LOCALAPPDATA
        }
        else {

            Start-ElevatedStage -CleanupForElevatedStage
            exit 0
        }
    }
    else {

        Write-Step "Creating current-user working directory."

        New-Item `
            -Path $UserDataPath `
            -ItemType Directory `
            -Force | Out-Null

        $UserTimestamp = Get-Date -Format "yyyyMMdd_HHmmss"
        $UserOutput = Join-Path `
            $UserDataPath `
            "user_context_$UserTimestamp.txt"

        Write-Step "Collecting current-user context."

        Invoke-Collection `
            -OutputFile $UserOutput `
            -StageName "Current User"

        Write-Host ""
        Write-Host "User-stage output:"
        Write-Host "  $UserOutput"
        Write-Host ""

        if ($CurrentIsAdmin) {

            Write-Host "The current PowerShell process is already elevated."
            Write-Host "For a true user -> admin transition, start this script from"
            Write-Host "a non-elevated PowerShell session."
            Write-Host ""

            $ElevatedStage = $true
            $OriginalUser = $CurrentUser
            $OriginalUserLocalAppData = $env:LOCALAPPDATA
        }
        else {

            Start-ElevatedStage -RunNowForElevatedStage:$RunNow
            exit 0
        }
    }
}

# =============================================================================
# STAGE 2 - ADMINISTRATOR
# =============================================================================

if ($ElevatedStage) {

    if (-not (Test-IsAdministrator)) {

        Write-Error "The elevated stage requires an Administrator token."
        exit 1
    }

    $AdminIdentity = [Security.Principal.WindowsIdentity]::GetCurrent().Name

    Write-Host ""
    Write-Host "============================================================"
    Write-Host " Stage 2 - Administrator"
    Write-Host "============================================================"
    Write-Host ""
    Write-Host "Original user:"
    Write-Host "  $OriginalUser"
    Write-Host ""
    Write-Host "Administrator context:"
    Write-Host "  $AdminIdentity"
    Write-Host ""

    # =========================================================================
    # ELEVATED CLEANUP
    # =========================================================================

    if ($Cleanup) {

        Write-Step "Stopping SYSTEM Scheduled Task if required."

        try {
            Stop-ScheduledTask `
                -TaskName $TaskName `
                -ErrorAction SilentlyContinue
        }
        catch {}

        Write-Step "Removing SYSTEM Scheduled Task."

        try {
            Unregister-ScheduledTask `
                -TaskName $TaskName `
                -Confirm:$false `
                -ErrorAction SilentlyContinue
        }
        catch {}

        if (Test-Path $SystemBasePath) {

            Write-Step "Resetting generated SYSTEM-stage ACLs."

            try {
                & "$env:SystemRoot\System32\icacls.exe" `
                    $SystemBasePath `
                    /reset `
                    /T `
                    /C | Out-Null
            }
            catch {}

            Write-Step "Removing SYSTEM-stage generated files."

            Remove-Item `
                -Path $SystemBasePath `
                -Recurse `
                -Force `
                -ErrorAction SilentlyContinue
        }

        Write-Host ""
        Write-Host "Elevated cleanup completed."
        exit 0
    }

    # =========================================================================
    # ADMIN CONTEXT COLLECTION
    # =========================================================================

    Write-Step "Creating administrator/SYSTEM working directory."

    New-Item `
        -Path $SystemDataPath `
        -ItemType Directory `
        -Force | Out-Null

    $AdminTimestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $AdminOutput = Join-Path `
        $SystemBasePath `
        "admin_context_$AdminTimestamp.txt"

    Write-Step "Collecting administrator context."

    Invoke-Collection `
        -OutputFile $AdminOutput `
        -StageName "Administrator"

    Write-Host ""
    Write-Host "Administrator-stage output:"
    Write-Host "  $AdminOutput"
    Write-Host ""

    # =========================================================================
    # CREATE SYSTEM COLLECTOR
    # =========================================================================

    $Collector = @'
Set-StrictMode -Version 2.0
$ErrorActionPreference = "Continue"

$BasePath = "C:\ProgramData\InventoryWorkflowCache"
$DataPath = Join-Path $BasePath "data"

if (-not (Test-Path $DataPath)) {
    New-Item `
        -Path $DataPath `
        -ItemType Directory `
        -Force | Out-Null
}

$Timestamp  = Get-Date -Format "yyyyMMdd_HHmmss"
$OutputFile = Join-Path $DataPath "inventory_$Timestamp.txt"

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
Stage          : System
Timestamp      : $(Get-Date -Format o)
Computer       : $env:COMPUTERNAME
Execution User : $([Security.Principal.WindowsIdentity]::GetCurrent().Name)
"@ | Out-File `
        -FilePath $OutputFile `
        -Encoding utf8


Add-Section "User context" {
    & "$env:SystemRoot\System32\whoami.exe" /all
}

Add-Section "Host name" {
    & "$env:SystemRoot\System32\hostname.exe"
}

Add-Section "System information" {
    & "$env:SystemRoot\System32\systeminfo.exe"
}

Add-Section "Operating system information" {
    Get-CimInstance Win32_OperatingSystem |
        Format-List *
}

Add-Section "Computer system information" {
    Get-CimInstance Win32_ComputerSystem |
        Format-List *
}

Add-Section "Installed hotfixes" {
    Get-HotFix |
        Sort-Object InstalledOn -Descending |
        Format-Table -AutoSize
}

Add-Section "IP configuration" {
    & "$env:SystemRoot\System32\ipconfig.exe" /all
}

Add-Section "Routing table" {
    & "$env:SystemRoot\System32\route.exe" print
}

Add-Section "ARP cache" {
    & "$env:SystemRoot\System32\arp.exe" -a
}

Add-Section "Network connections" {
    & "$env:SystemRoot\System32\netstat.exe" -ano
}

Add-Section "Running processes" {
    & "$env:SystemRoot\System32\tasklist.exe" /v
}

Add-Content `
    -Path $OutputFile `
    -Value "`r`nCollection complete."


# Restrict generated SYSTEM-stage artifacts.

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
    $DataPath `
    /inheritance:r | Out-Null

& $Icacls `
    $DataPath `
    /grant:r `
    "*S-1-5-18:(OI)(CI)(F)" `
    "*S-1-5-32-544:(OI)(CI)(F)" | Out-Null


Write-Output "Collection completed."
Write-Output "Output: $OutputFile"

'@

    Write-Step "Writing SYSTEM collector."

    Set-Content `
        -Path $CollectorPath `
        -Value $Collector `
        -Encoding UTF8

    # =========================================================================
    # STAGE 3 - CREATE LOCAL SYSTEM SCHEDULED TASK
    # =========================================================================

    Write-Step "Creating LOCAL SYSTEM Scheduled Task."

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
        -Description "Inventory maintenance" `
        -Force | Out-Null

    Write-Host ""
    Write-Host "============================================================"
    Write-Host " Stage 3 - LOCAL SYSTEM Scheduled Task"
    Write-Host "============================================================"
    Write-Host ""
    Write-Host "Task:"
    Write-Host "  $TaskName"
    Write-Host ""
    Write-Host "Run as:"
    Write-Host "  NT AUTHORITY\SYSTEM"
    Write-Host ""
    Write-Host "Scheduled execution:"
    Write-Host "  $TriggerTime"
    Write-Host ""
    Write-Host "Collector:"
    Write-Host "  $CollectorPath"
    Write-Host ""

    if ($RunNow) {

        Write-Step "Starting SYSTEM Scheduled Task immediately."

        & "$env:SystemRoot\System32\schtasks.exe" `
            /Run `
            /TN $TaskName

        Write-Host ""
        Write-Host "SYSTEM task submitted for execution."
    }

    Write-Host ""
    Write-Host "Workflow prepared successfully."
    Write-Host ""
}


<#
===============================================================================
POST-RUN VALIDATION AND TROUBLESHOOTING
===============================================================================


1. VERIFY THE USER-STAGE OUTPUT
-------------------------------------------------------------------------------

From the ORIGINAL user's normal PowerShell session:

Get-ChildItem "$env:LOCALAPPDATA\InventoryWorkflowCache\user"


Expected:

    user_context_YYYYMMDD_HHMMSS.txt


Read it:

Get-Content "$env:LOCALAPPDATA\InventoryWorkflowCache\user\user_context_*.txt"


Check the execution identity:

Select-String `
    -Path "$env:LOCALAPPDATA\InventoryWorkflowCache\user\user_context_*.txt" `
    -Pattern "Execution User"


This should identify the original/current user.


2. VERIFY THE ADMINISTRATOR-STAGE OUTPUT
-------------------------------------------------------------------------------

From an elevated PowerShell session:

Get-ChildItem "C:\ProgramData\InventoryWorkflowCache\admin_context_*.txt"


Read it:

Get-Content "C:\ProgramData\InventoryWorkflowCache\admin_context_*.txt"


Check identity:

Select-String `
    -Path "C:\ProgramData\InventoryWorkflowCache\admin_context_*.txt" `
    -Pattern "Execution User"


This should show the administrator account/context used after the UAC prompt.


3. CHECK THAT THE SYSTEM SCHEDULED TASK EXISTS
-------------------------------------------------------------------------------

Get-ScheduledTask -TaskName "InventoryMaintenance"


Short view:

Get-ScheduledTask -TaskName "InventoryMaintenance" |
    Select-Object `
        TaskName,
        State,
        @{Name="UserId";Expression={$_.Principal.UserId}},
        @{Name="LogonType";Expression={$_.Principal.LogonType}},
        @{Name="RunLevel";Expression={$_.Principal.RunLevel}}


Expected:

    UserId    : SYSTEM
    LogonType : ServiceAccount
    RunLevel  : Highest


4. CHECK SYSTEM TASK LAST RUN TIME AND RESULT
-------------------------------------------------------------------------------

Get-ScheduledTaskInfo -TaskName "InventoryMaintenance"


Review:

    LastRunTime
    LastTaskResult
    NextRunTime


Expected successful result:

    LastTaskResult : 0


If:

    LastTaskResult : 267011

this corresponds to:

    0x41303
    SCHED_S_TASK_HAS_NOT_RUN


5. MANUALLY START THE SYSTEM TASK
-------------------------------------------------------------------------------

Start-ScheduledTask -TaskName "InventoryMaintenance"


Alternative:

schtasks.exe /Run /TN "InventoryMaintenance"


6. VERIFY SYSTEM-STAGE OUTPUT
-------------------------------------------------------------------------------

Get-ChildItem "C:\ProgramData\InventoryWorkflowCache\data"


Expected:

    inventory_YYYYMMDD_HHMMSS.txt


Show latest:

Get-ChildItem "C:\ProgramData\InventoryWorkflowCache\data\inventory_*.txt" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1 Name, Length, LastWriteTime, FullName


7. VERIFY THAT SYSTEM REALLY EXECUTED THE COLLECTOR
-------------------------------------------------------------------------------

Select-String `
    -Path "C:\ProgramData\InventoryWorkflowCache\data\inventory_*.txt" `
    -Pattern "Execution User"


Expected:

    Execution User : NT AUTHORITY\SYSTEM


Also check:

Select-String `
    -Path "C:\ProgramData\InventoryWorkflowCache\data\inventory_*.txt" `
    -Pattern "S-1-5-18|NT AUTHORITY\\SYSTEM"


8. VERIFY EXPECTED SYSTEM COLLECTION
-------------------------------------------------------------------------------

Select-String `
    -Path "C:\ProgramData\InventoryWorkflowCache\data\inventory_*.txt" `
    -Pattern "User context|Host name|System information|Operating system information|Computer system information|Installed hotfixes|IP configuration|Routing table|ARP cache|Network connections|Running processes|Collection complete"


9. CHECK ALL OUTPUT FILES FOR ERRORS
-------------------------------------------------------------------------------

User stage:

Select-String `
    -Path "$env:LOCALAPPDATA\InventoryWorkflowCache\user\user_context_*.txt" `
    -Pattern "ERROR:"


Administrator stage:

Select-String `
    -Path "C:\ProgramData\InventoryWorkflowCache\admin_context_*.txt" `
    -Pattern "ERROR:"


SYSTEM stage:

Select-String `
    -Path "C:\ProgramData\InventoryWorkflowCache\data\inventory_*.txt" `
    -Pattern "ERROR:"


No results means no collector section reported an error.


10. CHECK SYSTEM-STAGE ACL
-------------------------------------------------------------------------------

icacls.exe "C:\ProgramData\InventoryWorkflowCache\data"


Expected entries include:

    BUILTIN\Administrators:(OI)(CI)(F)
    NT AUTHORITY\SYSTEM:(OI)(CI)(F)


Output files:

icacls.exe "C:\ProgramData\InventoryWorkflowCache\data\inventory_*.txt"


Expected entries include:

    BUILTIN\Administrators:(F)
    NT AUTHORITY\SYSTEM:(F)


11. CONFIRM ACL INHERITANCE WAS REMOVED
-------------------------------------------------------------------------------

(Get-Acl "C:\ProgramData\InventoryWorkflowCache\data").AreAccessRulesProtected


Expected:

    True


12. CHECK TASK SCHEDULER OPERATIONAL LOG
-------------------------------------------------------------------------------

Get-WinEvent -ListLog "Microsoft-Windows-TaskScheduler/Operational" |
    Select-Object LogName, IsEnabled, RecordCount, LastWriteTime


If:

    IsEnabled : False


enable it from an elevated PowerShell session:

wevtutil.exe set-log "Microsoft-Windows-TaskScheduler/Operational" /enabled:true


Verify:

Get-WinEvent -ListLog "Microsoft-Windows-TaskScheduler/Operational" |
    Select-Object LogName, IsEnabled, RecordCount, LastWriteTime


IMPORTANT:
Enabling the log does not recreate historical events.

If necessary, run the SYSTEM task again:

Start-ScheduledTask -TaskName "InventoryMaintenance"


13. VIEW SYSTEM TASK EVENTS
-------------------------------------------------------------------------------

Get-WinEvent `
    -LogName "Microsoft-Windows-TaskScheduler/Operational" `
    -MaxEvents 100 |
Where-Object {
    $_.Message -like "*InventoryMaintenance*"
} |
Select-Object TimeCreated, Id, Message |
Format-List


Useful Task Scheduler event IDs can include:

    100 - Task started
    102 - Task completed
    110 - Task instance launched
    129 - Process launched
    200 - Action started
    201 - Action completed
    325 - Task queued


A SYSTEM execution should contain a message similar to:

    Task Scheduler started ...
    "\InventoryMaintenance"
    for user "NT AUTHORITY\SYSTEM"


14. FULL TASK DETAILS
-------------------------------------------------------------------------------

schtasks.exe /Query /TN "InventoryMaintenance" /V /FO LIST


Review:

    Status
    Last Run Time
    Last Result
    Task To Run
    Run As User
    Scheduled Task State


15. CHECK WINDOWS SECURITY LOG AROUND THE ELEVATION
-------------------------------------------------------------------------------

Run this from an elevated PowerShell session.

Whether each event is present depends on the machine's audit policy.

$Start = (Get-Date).AddMinutes(-30)

Get-WinEvent -FilterHashtable @{
    LogName   = 'Security'
    StartTime = $Start
    Id        = 4624,4648,4672
} -ErrorAction SilentlyContinue |
Select-Object TimeCreated, Id, Message |
Format-List


Potentially useful events:

    4624 - Successful logon

    4648 - Logon attempted using explicit credentials
           May be relevant if alternate administrator credentials were used.

    4672 - Special privileges assigned to a new logon


NOTE:
Do not assume all three will always appear. This depends on how UAC was
approved, account type, Windows configuration, and audit policy.


16. OPTIONAL PROCESS CREATION SECURITY EVENTS
-------------------------------------------------------------------------------

If Audit Process Creation is enabled:

Get-WinEvent -FilterHashtable @{
    LogName   = 'Security'
    StartTime = (Get-Date).AddMinutes(-30)
    Id        = 4688
} -ErrorAction SilentlyContinue |
Where-Object {
    $_.Message -match 'powershell.exe|whoami.exe|systeminfo.exe|ipconfig.exe|route.exe|arp.exe|netstat.exe|tasklist.exe|icacls.exe'
} |
Select-Object TimeCreated, Id, Message |
Format-List


17. CHECK TASK SCHEDULER SERVICE
-------------------------------------------------------------------------------

Get-Service Schedule


Expected:

    Status : Running


18. CHECK MDE SERVICE IF DEFENDER XDR HUNTING IS PART OF THE TEST
-------------------------------------------------------------------------------

Get-Service Sense


The script itself does not require Microsoft Defender for Endpoint.

MDE is only required for Defender XDR telemetry and Advanced Hunting.


19. EXPECTED END-TO-END CHAIN
-------------------------------------------------------------------------------

    Standard / current user
              |
              v
    powershell.exe
              |
              +--> discovery commands
              |
              v
    user_context_*.txt
              |
              v
    Windows UAC prompt
              |
              v
    Administrator-approved PowerShell
              |
              +--> administrator context discovery
              |
              v
    admin_context_*.txt
              |
              v
    Scheduled Task registration
              |
              v
    InventoryMaintenance
              |
              v
    NT AUTHORITY\SYSTEM
              |
              v
    powershell.exe InventoryCollector.ps1
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
    inventory_*.txt
              |
              v
    icacls.exe ACL changes


20. SUCCESS CRITERIA
-------------------------------------------------------------------------------

The workflow is successful when:

    [1] user_context_*.txt exists

    [2] User-stage file shows the original user

    [3] Normal Windows UAC elevation occurred

    [4] admin_context_*.txt exists

    [5] Administrator-stage file shows the elevated administrator context

    [6] InventoryMaintenance Scheduled Task exists

    [7] Task principal is SYSTEM

    [8] SYSTEM-stage inventory_*.txt exists

    [9] SYSTEM-stage file reports NT AUTHORITY\SYSTEM

    [10] Expected discovery sections are present

    [11] No unexpected ERROR: entries appear

    [12] Generated SYSTEM-stage ACLs were modified

    [13] AreAccessRulesProtected returns True


21. IMPORTANT INTERPRETATION
-------------------------------------------------------------------------------

This workflow demonstrates a real Windows security-context transition:

    user -> administrator -> SYSTEM

but it does NOT demonstrate exploitation-based privilege escalation.

The user-to-administrator transition requires normal authorised Windows UAC
approval or authorised administrator credentials.

It is therefore suitable for validating SOC visibility and correlation around
privilege transitions without introducing an exploit or UAC bypass.


22. CLEANUP
-------------------------------------------------------------------------------

From the original user's normal PowerShell session:

.\InventoryWorkflow.ps1 -Cleanup


The script will:

    - remove the original user's InventoryWorkflowCache
    - request normal UAC approval
    - remove InventoryMaintenance
    - reset generated ACLs
    - remove C:\ProgramData\InventoryWorkflowCache


After cleanup, verify from elevated PowerShell:

Get-ScheduledTask `
    -TaskName "InventoryMaintenance" `
    -ErrorAction SilentlyContinue


Test-Path "C:\ProgramData\InventoryWorkflowCache"


From the original user session:

Test-Path "$env:LOCALAPPDATA\InventoryWorkflowCache"


Expected:

    Task is no longer returned

    Both Test-Path commands return:
        False


===============================================================================
END POST-RUN VALIDATION AND TROUBLESHOOTING
===============================================================================
#>
