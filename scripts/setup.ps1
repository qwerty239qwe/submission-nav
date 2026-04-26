$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir

function Test-Command {
    param([string]$Name)
    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

if (-not (Test-Command "uv")) {
    Write-Host "Missing required helper runtime: uv" -ForegroundColor Yellow
    Write-Host "Install it from https://docs.astral.sh/uv/getting-started/installation/" -ForegroundColor Yellow
    throw "uv is required for the local helper runtime."
}

Write-Host "Preparing local helper environment..."
Push-Location $scriptDir
try {
    uv sync
}
finally {
    Pop-Location
}

$envExample = Join-Path $repoRoot ".env.example"
$envFile = Join-Path $repoRoot ".env"
if ((Test-Path $envExample) -and -not (Test-Path $envFile)) {
    Copy-Item $envExample $envFile
    Write-Host "Created repo-local .env from .env.example"
}

Write-Host "Helper runtime is ready."
