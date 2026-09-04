#Requires -Version 5.1
<#
.SYNOPSIS
    Benchmark microphone noise floor and WebRTC speech ratio.
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $RepoRoot

$venvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$Python = if (Test-Path $venvPython) { $venvPython } else { "python" }

Write-Host "Fica em silencio durante o benchmark..." -ForegroundColor Cyan
& $Python -m friday.audio.mic_benchmark @args
