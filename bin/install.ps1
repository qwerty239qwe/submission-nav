$ErrorActionPreference = "Stop"

$binDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $binDir
$setupScript = Join-Path $repoRoot "scripts\setup.ps1"

if (-not (Test-Path $setupScript)) {
    throw "Missing setup script: $setupScript"
}

Write-Host "submission-nav setup"
Write-Host "Repository: $repoRoot"

& $setupScript

Write-Host ""
Write-Host "submission-nav is ready. Restart your agent host if it is already running."
