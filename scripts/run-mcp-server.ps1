#Requires -Version 5.1
<#
.SYNOPSIS
    Start the F.R.I.D.A.Y MCP server (stdio) for Cursor / MCP clients.
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$venvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$Python = if (Test-Path $venvPython) { $venvPython } else { "python" }

Write-Host "Starting FRIDAY MCP server (stdio)..." -ForegroundColor Cyan
& $Python -m friday.mcp_server.server @args
