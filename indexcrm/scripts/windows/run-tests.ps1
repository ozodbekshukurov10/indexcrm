param(
    [switch]$Frontend,
    [switch]$Build
)

# Runs the backend test gate, with optional frontend typecheck/build.
# This does not require the local PostgreSQL service when test settings are used.
$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$FrontendDir = Join-Path $ProjectRoot "frontend\pos"

Set-Location $ProjectRoot

$venvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    $python = $venvPython
} else {
    $python = "python"
    Write-Warning "Using system Python because .venv was not found."
}

& $python manage.py check
& $python -m pytest

if ($Frontend) {
    $npmCommand = Get-Command npm.cmd -ErrorAction SilentlyContinue
    if (-not $npmCommand) {
        throw "npm.cmd was not found. Install Node.js to run frontend checks."
    }
    if (-not (Test-Path (Join-Path $FrontendDir "node_modules"))) {
        throw "frontend\pos\node_modules is missing. Run: cd frontend\pos; npm.cmd install"
    }

    Set-Location $FrontendDir
    & $npmCommand.Source run typecheck
    if ($Build) {
        & $npmCommand.Source run build
    }
}
