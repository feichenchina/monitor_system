$ErrorActionPreference = "Stop"

# Ensure we are in the script's directory
$ScriptRoot = $PSScriptRoot
Set-Location $ScriptRoot

Write-Host "Checking Python installation..."
try {
    py --version
}
catch {
    Write-Error "Python is not installed. Please install Python first."
    exit 1
}

Write-Host "Installing dependencies..."
py -m pip install -r backend/requirements.txt

# 检查并启动前端开发服务器（如果安装了 npm）
Write-Host "Checking Node/npm installation..."
$npmAvailable = $true
try {
    npm --version | Out-Null
} catch {
    $npmAvailable = $false
}
if ($npmAvailable) {
    Write-Host "Installing frontend dependencies and starting dev server in a new window..."
    Start-Process -FilePath "cmd.exe" -ArgumentList "/k cd frontend && npm install && npm run dev" -WorkingDirectory $ScriptRoot
} else {
    Write-Warning 'npm not found; skipping frontend dev server. Please install Node/npm or run "npm run dev" in the frontend directory manually.'
}

Write-Host "Starting Server Monitor..."
Start-Process "http://127.0.0.1:9000"

# Start FastAPI server
# Using py -m uvicorn to ensure we use the installed module
py -m uvicorn main:app --app-dir backend --reload --host 0.0.0.0 --port 9000
