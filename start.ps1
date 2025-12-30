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

Write-Host "Starting Server Monitor..."
Start-Process "http://127.0.0.1:8000"

# Start FastAPI server
# Using py -m uvicorn to ensure we use the installed module
py -m uvicorn main:app --app-dir backend --reload --host 0.0.0.0 --port 8000
