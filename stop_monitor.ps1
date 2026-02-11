$ErrorActionPreference = "SilentlyContinue"
$procs = Get-CimInstance Win32_Process -Filter "Name LIKE 'python%.exe' AND CommandLine LIKE '%backend\\main.py%'"
if ($procs) {
    $procs | ForEach-Object {
        Stop-Process -Id $_.ProcessId -Force
        Write-Host "Stopped process PID: $($_.ProcessId)" -ForegroundColor Green
    }
} else {
    Write-Host "No running monitor process found." -ForegroundColor Yellow
}
