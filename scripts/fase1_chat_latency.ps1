#Requires -Version 5.1
<#
.SYNOPSIS
    Chat-path latency smoke (agent-api), complement to wake-to-TTS voice benchmark.
.DESCRIPTION
    Measures N text chat round-trips against a running agent-api + LM Studio.

Usage:
  .\scripts\run-agent-api.ps1   # separately
  .\scripts\fase1_chat_latency.ps1 -N 5
#>
param(
    [int]$N = 5,
    [string]$Base = "http://127.0.0.1:8090",
    [int]$MaxP50Ms = 8000
)

$ErrorActionPreference = "Stop"
$latencies = @()

Write-Host "Creating session..."
$session = Invoke-RestMethod -Method Post -Uri "$Base/v1/sessions" -TimeoutSec 15
$sid = $session.id
$prompts = @(
    "Que horas sao?",
    "Como te chamas?",
    "Conta uma piada curta.",
    "O que podes fazer?",
    "Qual e a capital de Portugal?"
)

for ($i = 0; $i -lt $N; $i++) {
    $text = $prompts[$i % $prompts.Count]
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $body = @{ session_id = $sid; text = $text; stream = $false } | ConvertTo-Json
    $null = Invoke-RestMethod -Method Post -Uri "$Base/v1/chat" `
        -ContentType "application/json" -Body $body -TimeoutSec 180
    $sw.Stop()
    $ms = [int]$sw.Elapsed.TotalMilliseconds
    $latencies += $ms
    Write-Host ("  [{0}] {1} ms - {2}" -f ($i + 1), $ms, $text)
}

$sorted = $latencies | Sort-Object
$p50 = $sorted[[math]::Max(0, [math]::Ceiling(0.5 * $sorted.Count) - 1)]
$p95 = $sorted[[math]::Max(0, [math]::Ceiling(0.95 * $sorted.Count) - 1)]

$outDir = Join-Path (Resolve-Path (Join-Path $PSScriptRoot "..")) "docs\fase-1"
$out = Join-Path $outDir "chat-latency-last.json"
@{
    at = (Get-Date).ToUniversalTime().ToString("o")
    n = $N
    latencies_ms = $latencies
    p50_ms = $p50
    p95_ms = $p95
    path = "agent-api /v1/chat"
} | ConvertTo-Json | Set-Content $out -Encoding utf8

Write-Host ""
Write-Host ("Chat latency p50={0} ms p95={1} ms (soft target p50 under {2} ms)" -f $p50, $p95, $MaxP50Ms)
Write-Host "Wrote $out"
if ($p50 -gt $MaxP50Ms) {
    Write-Host "p50 above soft target - check LM Studio load / GPU contention." -ForegroundColor Yellow
    exit 2
}
exit 0
