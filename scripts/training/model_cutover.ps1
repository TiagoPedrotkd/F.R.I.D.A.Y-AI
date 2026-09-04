# Switch production model pointer in .env (manual cutover helper).
# Does NOT load weights — only updates LM_STUDIO_MODEL and writes a rollback stamp.
#
# Usage:
#   .\scripts\model_cutover.ps1 -Model "friday-qwen25-incremental-v1"
#   .\scripts\model_cutover.ps1 -Model "friday-qwen25-incremental-v1" -Smoke
#   .\scripts\model_cutover.ps1 -Rollback

param(
    [string]$Model = "",
    [switch]$Rollback,
    [switch]$Smoke,
    [double]$MinPassRate = 0.5
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $Root
$envPath = Join-Path $Root ".env"
$stampPath = Join-Path $Root "friday-llm\reports\incremental\model_cutover.json"

if (-not (Test-Path $envPath)) {
    Write-Error ".env not found"
}

function Set-LmModel([string]$value) {
    $lines = Get-Content $envPath
    $found = $false
    $out = foreach ($line in $lines) {
        if ($line -match '^\s*LM_STUDIO_MODEL\s*=') {
            $found = $true
            "LM_STUDIO_MODEL=$value"
        } else {
            $line
        }
    }
    if (-not $found) { $out += "LM_STUDIO_MODEL=$value" }
    $out | Set-Content -Path $envPath -Encoding utf8
}

$current = ""
Get-Content $envPath | ForEach-Object {
    if ($_ -match '^\s*LM_STUDIO_MODEL\s*=\s*(.+)\s*$') { $current = $Matches[1].Trim() }
}

if ($Rollback) {
    if (-not (Test-Path $stampPath)) { Write-Error "No cutover stamp at $stampPath" }
    $stamp = Get-Content $stampPath -Raw | ConvertFrom-Json
    $prev = [string]$stamp.previous_model
    if (-not $prev) { Write-Error "Stamp missing previous_model" }
    Set-LmModel $prev
    Write-Host "Rolled back LM_STUDIO_MODEL -> $prev"
    Write-Host "Reload the model in LM Studio manually."
    if ($Smoke) {
        & (Join-Path $PSScriptRoot "cutover_smoke.ps1") -MinPassRate $MinPassRate
        exit $LASTEXITCODE
    }
    exit 0
}

if (-not $Model) {
    Write-Error "Provide -Model <id> or -Rollback"
}

@{
    at = (Get-Date).ToUniversalTime().ToString("o")
    previous_model = $current
    new_model = $Model
} | ConvertTo-Json | Set-Content -Path $stampPath -Encoding utf8

Set-LmModel $Model
Write-Host "Cutover recorded: $current -> $Model"
Write-Host "Stamp: $stampPath"
Write-Host "Load '$Model' in LM Studio, then restart agent-api."
Write-Host "Rollback later: .\scripts\model_cutover.ps1 -Rollback"

if ($Smoke) {
    Write-Host "Running post-cutover smoke..."
    & (Join-Path $PSScriptRoot "cutover_smoke.ps1") -MinPassRate $MinPassRate
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Smoke failed — rolling back automatically." -ForegroundColor Yellow
        Set-LmModel $current
        Write-Host "Restored LM_STUDIO_MODEL -> $current"
        exit 2
    }
}
