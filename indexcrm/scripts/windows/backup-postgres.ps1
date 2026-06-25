param(
    [string]$BackupDir,
    [string]$Database,
    [string]$DbUser,
    [string]$DbHost,
    [string]$DbPort
)

# Creates a timestamped PostgreSQL custom-format backup outside the project folder.
# Defaults come from .env when present: DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT.
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
$envValues = Read-EnvFile $EnvPath

if (-not (Test-Path $EnvPath)) {
    Write-Warning "Missing .env. Using local defaults: index/index on localhost:5432."
}

if (-not $BackupDir) {
    $BackupDir = Join-Path (Split-Path $ProjectRoot -Parent) "index_backups"
}

if (-not $Database) {
    $Database = Get-EnvValue $envValues "DB_NAME" "index"
}
if (-not $DbUser) {
    $DbUser = Get-EnvValue $envValues "DB_USER" "index"
}
if (-not $DbHost) {
    $DbHost = Get-EnvValue $envValues "DB_HOST" "localhost"
}
if (-not $DbPort) {
    $DbPort = Get-EnvValue $envValues "DB_PORT" "5432"
}
$dbPassword = Get-EnvValue $envValues "DB_PASSWORD" ""

$pgDump = Get-Command pg_dump -ErrorAction SilentlyContinue
if (-not $pgDump) {
    throw "pg_dump was not found. Install PostgreSQL client tools or add them to PATH."
}

New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupFile = Join-Path $BackupDir "index-$stamp.dump"

$previousPassword = $env:PGPASSWORD
try {
    if ($dbPassword) {
        $env:PGPASSWORD = $dbPassword
    } else {
        Write-Warning "DB_PASSWORD was not found in .env. pg_dump may prompt for a password."
    }

    $dumpArgs = @(
        "--format=custom",
        "--no-owner",
        "--no-acl",
        "--host", $DbHost,
        "--port", $DbPort,
        "--username", $DbUser,
        "--file", $backupFile,
        $Database
    )
    & $pgDump.Source @dumpArgs
} finally {
    $env:PGPASSWORD = $previousPassword
}

$fileInfo = Get-Item $backupFile
if ($fileInfo.Length -le 0) {
    throw "Backup file was created but is empty: $backupFile"
}

Write-Host "Backup created: $backupFile"
Write-Host "Store this file outside the project folder and test restore on a non-production database."
