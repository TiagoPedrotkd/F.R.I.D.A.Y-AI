# Prepare next incremental day preferring domain-relevant docs (no train).
# Run AFTER Day 5 CPT finishes, e.g.:
#   python -m friday_llm.training.incremental.build_domain_corpus
#   .\scripts\cpt_prepare_domain_day.ps1 -Day 6 -Add 20
# Then train with GPU free:
#   .\scripts\cpt_day_6.ps1

param(
    [Parameter(Mandatory = $true)][int]$Day,
    [int]$Add = 20
)

$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot "..\.."))
$env:PYTHONIOENCODING = "utf-8"

Write-Host "Refreshing domain corpus from repo docs..."
python -m friday_llm.training.incremental.build_domain_corpus
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Preparing day $Day (+$Add docs, prefer-domain)..."
python -m friday_llm.training.incremental.cli --day $Day --add $Add --prefer-domain
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "Done. Train later with: .\scripts\cpt_day_$Day.ps1"
