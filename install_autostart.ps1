$StartupPath = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
$ShortcutPath = "$StartupPath\MonitorSystem.lnk"
$ScriptRoot = $PSScriptRoot
$TargetFile = "$ScriptRoot\start_silent.vbs"
$WorkingDir = "$ScriptRoot"

$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $TargetFile
$Shortcut.WorkingDirectory = $WorkingDir
$Shortcut.Description = "Auto-start Monitor System"
$Shortcut.Save()

Write-Host "Shortcut created at: $ShortcutPath"
