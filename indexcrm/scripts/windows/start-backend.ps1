param(
    [switch]$InstallDependencies,
    [switch]$Migrate,
    [switch]$SeedDemoData
)

# Starts the local Django backend for MVP/demo use.
# Optional switches keep install, migrations, and demo seeding explicit.
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

$venvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    $python = $venvPython
} else {
    $python = "python"
    Write-Warning "Using system Python because .venv was not found. Recommended: python -m venv .venv"
}

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

if (-not $connected) {
    Write-Warning "PostgreSQL is not reachable at ${dbHost}:${dbPort}. Start Docker/PostgreSQL before migrations or live POS testing."
}

if ($InstallDependencies) {
    & $python -m pip install -r requirements.txt
}

& $python manage.py check

if ($Migrate) {
    & $python manage.py migrate
}

if ($SeedDemoData) {
    & $python manage.py seed_demo_data
}

Write-Host "Starting Django at http://127.0.0.1:8000"
& $python manage.py runserver 127.0.0.1:8000
