# Check for Administrator privileges
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Warning "This script requires Administrator privileges to install for all users."
    Write-Warning "Please re-run PowerShell as Administrator."
    exit 1
}

$StartupPath = [Environment]::GetFolderPath('CommonStartup')
$ShortcutPath = "$StartupPath\MonitorSystem.lnk"
$ScriptRoot = $PSScriptRoot
$TargetFile = "$ScriptRoot\start_silent.vbs"
$WorkingDir = "$ScriptRoot"

$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $TargetFile
$Shortcut.WorkingDirectory = $WorkingDir
$Shortcut.Description = "Auto-start Monitor System (All Users)"
$Shortcut.Save()

Write-Host "Shortcut created successfully for ALL USERS at: $ShortcutPath"
