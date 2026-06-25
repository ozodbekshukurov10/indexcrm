param(
    [switch]$Install
)

# Starts the local Next.js POS frontend on port 3001.
# Use -Install only when dependencies need to be installed.
$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$FrontendDir = Join-Path $ProjectRoot "frontend\pos"
$EnvLocalPath = Join-Path $FrontendDir ".env.local"
$PackageJsonPath = Join-Path $FrontendDir "package.json"
$NodeModulesPath = Join-Path $FrontendDir "node_modules"

if (-not (Test-Path $PackageJsonPath)) {
    throw "Missing frontend package.json. Expected path: frontend\pos\package.json"
}

if (-not (Test-Path $EnvLocalPath)) {
    throw "Missing frontend\pos\.env.local. Run: cd frontend\pos; copy .env.local.example .env.local"
}

$npmCommand = Get-Command npm.cmd -ErrorAction SilentlyContinue
if (-not $npmCommand) {
    throw "npm.cmd was not found. Install Node.js, then retry."
}

Set-Location $FrontendDir

if (-not (Test-Path $NodeModulesPath)) {
    if ($Install) {
        & $npmCommand.Source install
    } else {
        throw "node_modules is missing. Run: .\scripts\windows\start-frontend.ps1 -Install"
    }
}

Write-Host "Starting Next.js POS at http://127.0.0.1:3001"
& $npmCommand.Source run dev
