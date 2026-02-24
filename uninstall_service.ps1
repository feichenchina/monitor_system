# Uninstall Monitor System Windows Service Script
# This script removes the Windows Service and cleans up the temporary files.

$ServiceName = "MonitorSystem"

# Check for Administrator privileges
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Warning "This script requires Administrator privileges."
    Write-Warning "Please re-run PowerShell as Administrator."
    exit 1
}

# Stop the service if it exists and is running
if (Get-Service $ServiceName -ErrorAction SilentlyContinue) {
    Write-Host "Stopping service: $ServiceName..."
    Stop-Service $ServiceName -ErrorAction SilentlyContinue
    
    # Wait for the service to stop
    Write-Host "Waiting for service to stop..."
    Start-Sleep -Seconds 2
    
    # Remove the service
    Write-Host "Removing service: $ServiceName..."
    & sc.exe delete $ServiceName | Out-Null
    
    if (-not (Get-Service $ServiceName -ErrorAction SilentlyContinue)) {
        Write-Host "Service $ServiceName removed successfully."
    } else {
        Write-Error "Failed to remove service $ServiceName."
    }
} else {
    Write-Host "Service $ServiceName is not installed."
}

# Clean up the bin directory
$ScriptRoot = $PSScriptRoot
$BinPath = Join-Path $ScriptRoot "bin"
if (Test-Path $BinPath) {
    Write-Host "Cleaning up bin directory: $BinPath..."
    # Attempt to remove the file, if it's locked, just ignore it
    Remove-Item $BinPath -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "Clean up complete."
}
