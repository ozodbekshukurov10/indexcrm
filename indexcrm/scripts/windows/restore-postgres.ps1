param(
    [Parameter(Mandatory = $true)]
    [string]$BackupFile,
    [string]$Database,
    [string]$DbUser,
    [string]$DbHost,
    [string]$DbPort
)

# Restores a PostgreSQL dump after an explicit typed confirmation.
# Test restore on a non-production database before trusting it for a pilot machine.
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

if (-not (Test-Path $BackupFile)) {
    throw "Backup file was not found: $BackupFile"
}

$resolvedBackupFile = (Resolve-Path $BackupFile).Path

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

Write-Warning "RESTORE CAN OVERWRITE OR DELETE CURRENT DATABASE DATA."
Write-Host "Recommended: test restore on a non-production database first."
Write-Host "Target: ${DbUser}@${DbHost}:${DbPort}/${Database}"
Write-Host "Backup: $resolvedBackupFile"
$confirmation = Read-Host "Type RESTORE to continue"
if ($confirmation -ne "RESTORE") {
    Write-Host "Restore cancelled."
    exit 1
}

$extension = [IO.Path]::GetExtension($resolvedBackupFile).ToLowerInvariant()
$command = if ($extension -eq ".sql") { "psql" } else { "pg_restore" }
$pgCommand = Get-Command $command -ErrorAction SilentlyContinue
if (-not $pgCommand) {
    throw "$command was not found. Install PostgreSQL client tools or add them to PATH."
}

$previousPassword = $env:PGPASSWORD
try {
    if ($dbPassword) {
        $env:PGPASSWORD = $dbPassword
    } else {
        Write-Warning "DB_PASSWORD was not found in .env. Restore may prompt for a password."
    }

    if ($extension -eq ".sql") {
        $restoreArgs = @(
            "--host", $DbHost,
            "--port", $DbPort,
            "--username", $DbUser,
            "--dbname", $Database,
            "--file", $resolvedBackupFile
        )
        & $pgCommand.Source @restoreArgs
    } else {
        $restoreArgs = @(
            "--clean",
            "--if-exists",
            "--no-owner",
            "--no-acl",
            "--host", $DbHost,
            "--port", $DbPort,
            "--username", $DbUser,
            "--dbname", $Database,
            $resolvedBackupFile
        )
        & $pgCommand.Source @restoreArgs
    }
} finally {
    $env:PGPASSWORD = $previousPassword
}

Write-Host "Restore command completed."
Write-Host "Next: run .\.venv\Scripts\python.exe manage.py check"
Write-Host "Next: run .\.venv\Scripts\python.exe manage.py migrate"
