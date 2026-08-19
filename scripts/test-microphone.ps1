#Requires -Version 5.1
<#
.SYNOPSIS
    Test which microphone device actually receives audio.
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$venvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$Python = if (Test-Path $venvPython) { $venvPython } else { "python" }

Write-Host "Fala durante o teste (~3 segundos por dispositivo)..." -ForegroundColor Cyan
& $Python -m friday.audio.mic_test
