param(
    [switch]$Health
)

# Runs a safe backend readiness check without applying migrations.
# Use -Health only when the Django server is already running.
$ErrorActionPreference = "Stop"

function Read-EnvFile {
    param([string]$Path)
    $values = @{}
    if (-not (Test-Path $Path)) {
        return $values
    }
    foreach ($line in Get-Content $Path) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith("#") -or -not $trimmed.Contains("=")) {
            continue
        }
        $parts = $trimmed.Split("=", 2)
        $values[$parts[0].Trim()] = $parts[1].Trim().Trim('"').Trim("'")
    }
    return $values
}

function Get-EnvValue {
    param(
        [hashtable]$Values,
        [string]$Name,
        [string]$Default
    )
    if ($Values.ContainsKey($Name) -and $Values[$Name]) {
        return $Values[$Name]
    }
    return $Default
}

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$EnvPath = Join-Path $ProjectRoot ".env"

Set-Location $ProjectRoot

if (-not (Test-Path $EnvPath)) {
    throw "Missing .env. Run: copy .env.example .env"
}

$envValues = Read-EnvFile $EnvPath
$dbHost = Get-EnvValue $envValues "DB_HOST" "127.0.0.1"
$dbPort = [int](Get-EnvValue $envValues "DB_PORT" "5432")

$socket = New-Object Net.Sockets.TcpClient
try {
    $connectTask = $socket.ConnectAsync($dbHost, $dbPort)
    try {
        $connected = $connectTask.Wait(5000) -and $socket.Connected
    } catch {
        $connected = $false
    }
} finally {
    $socket.Dispose()
}

if ($connected) {
    Write-Host "PostgreSQL port check passed at ${dbHost}:${dbPort}."
} else {
    Write-Warning "PostgreSQL is not reachable at ${dbHost}:${dbPort}. Start Docker/PostgreSQL before migrations or live smoke testing."
}

$venvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    $python = $venvPython
} else {
    $python = "python"
    Write-Warning "Using system Python because .venv was not found."
}

& $python manage.py check

if ($Health) {
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/v1/health/" -UseBasicParsing -TimeoutSec 5
        Write-Host "Backend health returned HTTP $($response.StatusCode)."
    } catch {
        Write-Warning "Backend health URL is not reachable. Start backend first with scripts\windows\start-backend.ps1."
    }
}
