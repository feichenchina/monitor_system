$ErrorActionPreference = "Stop"

# Fix console encoding to UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"

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

# 检查并构建前端（如果尚未构建）
$FrontendDist = Join-Path $ScriptRoot "frontend\dist"
$npmAvailable = $true
try {
    npm --version | Out-Null
} catch {
    $npmAvailable = $false
}

if (-not (Test-Path $FrontendDist)) {
    if ($npmAvailable) {
        Write-Host "Frontend build not found. Building frontend..."
        Push-Location "frontend"
        try {
            npm install
            npm run build
        } finally {
            Pop-Location
        }
    } else {
        Write-Warning "Frontend build not found and npm is not available. The web interface may not work."
    }
}

# 检查并启动前端开发服务器（如果安装了 npm）
# 注意：现在后端已经托管了静态文件，普通用户直接访问 8000 端口即可
# 开发人员可以继续使用 dev server
if ($npmAvailable) {
    Write-Host "Starting frontend dev server in a new window (for development)..."
    Start-Process -FilePath "cmd.exe" -ArgumentList "/k cd frontend && npm run dev" -WorkingDirectory $ScriptRoot
} else {
    Write-Warning 'npm not found; skipping frontend dev server.'
}

Write-Host "Starting Server Monitor..."
Write-Host "You can access the application at http://127.0.0.1:8000"

Start-Process "http://127.0.0.1:8000"

# Start FastAPI server
# Using py -m uvicorn to ensure we use the installed module
# Added --no-use-colors to prevent garbled ANSI codes in some terminals
py -m uvicorn main:app --app-dir backend --reload --host 0.0.0.0 --port 8000 --no-use-colors
