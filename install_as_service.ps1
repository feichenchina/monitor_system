# Monitor System Windows Service Installation Script
# This script creates a native Windows Service that runs the Monitor System Backend.
# It uses a C# wrapper (compiled on-the-fly) to correctly handle Service Control Manager (SCM) signals.

$ServiceName = "MonitorSystem"
$ServiceDisplayName = "Monitor System Service"
$ServiceDescription = "A background monitor system server that runs independently of user sessions."

# Check for Administrator privileges
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Warning "This script requires Administrator privileges."
    Write-Warning "Please re-run PowerShell as Administrator."
    exit 1
}

$ScriptRoot = $PSScriptRoot
Set-Location $ScriptRoot

# Check for frontend build
$FrontendDist = Join-Path $ScriptRoot "frontend\dist"
if (-not (Test-Path $FrontendDist)) {
    Write-Warning "Frontend build not found at $FrontendDist."
    Write-Warning "The service will start, but the web interface will not be available."
    Write-Warning "Please run 'npm run build' in the 'frontend' directory if you need the web UI."
}

# Find pythonw.exe
$PythonPath = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
if (-not $PythonPath) {
    # Try 'py' if 'pythonw.exe' is not in path
    $PythonPath = (Get-Command py -ErrorAction SilentlyContinue).Source
    if ($PythonPath) {
        # 'py' might not be pythonw, but it's a start. 
        # Actually, if we use 'py', it might open a window.
        # Let's try to find pythonw in the same directory as py or python
        $PythonDir = Split-Path (Get-Command python.exe -ErrorAction SilentlyContinue).Source
        $PythonPath = Join-Path $PythonDir "pythonw.exe"
    }
}

if (-not (Test-Path $PythonPath)) {
    Write-Error "Could not find pythonw.exe. Please ensure Python is installed and in your PATH."
    exit 1
}

# Arguments for the service
# We use uvicorn to run the FastAPI app
$Arguments = "-m uvicorn main:app --app-dir backend --host 0.0.0.0 --port 8000 --no-use-colors"
$WorkingDirectory = $ScriptRoot

# Stop and remove existing service if it exists
if (Get-Service $ServiceName -ErrorAction SilentlyContinue) {
    Write-Host "Stopping existing service: $ServiceName..."
    Stop-Service $ServiceName -ErrorAction SilentlyContinue
    # Give it some time to stop
    Start-Sleep -Seconds 2
    Write-Host "Removing existing service: $ServiceName..."
    & sc.exe delete $ServiceName | Out-Null
}

# Define the C# wrapper code
$Source = @"
using System;
using System.Diagnostics;
using System.ServiceProcess;
using System.IO;

public class MonitorService : ServiceBase
{
    private Process _process;
    private string _pythonPath = @"$PythonPath";
    private string _arguments = @"$Arguments";
    private string _workingDir = @"$WorkingDirectory";

    public MonitorService()
    {
        this.ServiceName = "$ServiceName";
    }

    protected override void OnStart(string[] args)
    {
        try
        {
            ProcessStartInfo startInfo = new ProcessStartInfo();
            startInfo.FileName = _pythonPath;
            startInfo.Arguments = _arguments;
            startInfo.WorkingDirectory = _workingDir;
            startInfo.UseShellExecute = false;
            startInfo.CreateNoWindow = true;

            _process = Process.Start(startInfo);
            
            if (_process == null || _process.HasExited)
            {
                throw new Exception("Failed to start monitor process.");
            }
        }
        catch (Exception ex)
        {
            EventLog.WriteEntry("MonitorService", "Error starting service: " + ex.Message, EventLogEntryType.Error);
            throw;
        }
    }

    protected override void OnStop()
    {
        if (_process != null && !_process.HasExited)
        {
            try
            {
                _process.Kill();
                _process.WaitForExit(5000);
            }
            catch (Exception ex)
            {
                EventLog.WriteEntry("MonitorService", "Error stopping process: " + ex.Message, EventLogEntryType.Warning);
            }
        }
    }

    public static void Main()
    {
        ServiceBase.Run(new MonitorService());
    }
}
"@

# Create a temporary directory for the executable
$BinPath = Join-Path $ScriptRoot "bin"
if (-not (Test-Path $BinPath)) {
    New-Item -ItemType Directory -Path $BinPath | Out-Null
}
$ExePath = Join-Path $BinPath "MonitorService.exe"

# Compile the C# code to an executable
Write-Host "Compiling service wrapper..."
try {
    Add-Type -TypeDefinition $Source -Language CSharp -OutputAssembly $ExePath -OutputType ConsoleApplication -ReferencedAssemblies "System.ServiceProcess", "System.Configuration.Install"
} catch {
    Write-Error "Compilation failed: $($_.Exception.Message)"
    exit 1
}

if (Test-Path $ExePath) {
    Write-Host "Service wrapper compiled at: $ExePath"
    
    # Create the Windows Service
    Write-Host "Creating Windows Service: $ServiceName..."
    New-Service -Name $ServiceName -BinaryPathName "`"$ExePath`"" -DisplayName $ServiceDisplayName -Description $ServiceDescription -StartupType Automatic
    
    # Start the service
    Write-Host "Starting service..."
    Start-Service $ServiceName
    
    Write-Host "`nSuccessfully installed and started $ServiceName as a Windows Service!"
    Write-Host "It will now run automatically on system startup, even if no user is logged in."
} else {
    Write-Error "Failed to compile the service wrapper."
}
