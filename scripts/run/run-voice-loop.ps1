#Requires -Version 5.1
<#
.SYNOPSIS
    Start the FRIDAY Fase 1 voice loop on Windows host.
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $RepoRoot

if (-not (Test-Path ".env")) {
    Write-Warning ".env not found — copy from .env.example and configure LM Studio URL."
}

$venvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    $Python = $venvPython
} else {
    $Python = "python"
}

Write-Host "Starting FRIDAY voice loop..." -ForegroundColor Cyan
& $Python -m friday.pipeline.loop @args
