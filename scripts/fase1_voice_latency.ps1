#Requires -Version 5.1
<#
.SYNOPSIS
    Measure voice-equivalent path latency via agent-api (STT skip + chat + TTS).
.DESCRIPTION
    Emulates a turn without mic/wake: chat then TTS, writes turn_complete JSON
    and aggregates p50/p95 (same schema as voice loop metrics).
#>
param(
    [string]$Base = "http://127.0.0.1:8090",
    [int]$N = 3,
    [string]$OutLog = ""
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
if (-not $OutLog) {
    $OutLog = Join-Path $Root "docs\fase-1\voice-latency-last.log"
}

$session = Invoke-RestMethod -Method Post -Uri "$Base/v1/sessions" -TimeoutSec 15
$sid = $session.id
$prompts = @(
    "Que horas sao?",
    "Conta uma piada curta.",
    "Como te chamas?"
)

$lines = New-Object System.Collections.Generic.List[string]
Write-Host "Voice-path latency via API (n=$N) session=$sid" -ForegroundColor Cyan

for ($i = 0; $i -lt $N; $i++) {
    $text = $prompts[$i % $prompts.Count]
    $t0 = [Diagnostics.Stopwatch]::StartNew()
    # capture/stt skipped in text-equivalent path
    $captureMs = 0
    $sttMs = 0

    $sw = [Diagnostics.Stopwatch]::StartNew()
    $body = @{ session_id = $sid; text = $text; stream = $false } | ConvertTo-Json
    $chat = Invoke-RestMethod -Method Post -Uri "$Base/v1/chat" -ContentType "application/json" -Body $body -TimeoutSec 180
    $llmMs = [int]$sw.ElapsedMilliseconds

    $reply = [string]$chat.reply
    if (-not $reply) { $reply = "ok" }
    if ($reply.Length -gt 220) { $reply = $reply.Substring(0, 220) }

    $ttsOut = Join-Path $env:TEMP ("friday_voice_lat_{0}.wav" -f $i)
    $sw.Restart()
    Invoke-WebRequest -Method Post -Uri "$Base/v1/tts" -ContentType "application/json" `
        -Body (@{ text = $reply; session_id = $sid } | ConvertTo-Json) -TimeoutSec 90 -OutFile $ttsOut | Out-Null
    $ttsMs = [int]$sw.ElapsedMilliseconds
    Remove-Item -LiteralPath $ttsOut -Force -ErrorAction SilentlyContinue

    $total = [int]$t0.ElapsedMilliseconds
    $obj = [ordered]@{
        event          = "turn_complete"
        wake_to_tts_ms = $total
        capture_ms     = $captureMs
        stt_ms         = $sttMs
        llm_ms         = $llmMs
        tts_ms         = $ttsMs
        path           = "api_text_equivalent"
        prompt         = $text
    }
    $json = ($obj | ConvertTo-Json -Compress)
    $lines.Add($json)
    Write-Host ("  [{0}] total={1}ms llm={2}ms tts={3}ms - {4}" -f ($i + 1), $total, $llmMs, $ttsMs, $text)
}

Set-Content -Path $OutLog -Value $lines -Encoding utf8
& (Join-Path $PSScriptRoot "benchmark-latency.ps1") -LogFile $OutLog
$benchExit = $LASTEXITCODE

$vals = @()
foreach ($line in $lines) {
    $o = $line | ConvertFrom-Json
    $vals += [double]$o.wake_to_tts_ms
}
$sorted = $vals | Sort-Object
function Pct([double[]]$V, [double]$P) {
    if ($V.Count -eq 0) { return $null }
    $idx = [math]::Ceiling(($P / 100.0) * $V.Count) - 1
    $idx = [math]::Max(0, [math]::Min($idx, $V.Count - 1))
    return $V[$idx]
}
$report = @{
    at      = (Get-Date).ToUniversalTime().ToString("o")
    path    = "agent-api chat+tts (text-equivalent voice path)"
    n       = $N
    p50_ms  = [int](Pct -V $sorted -P 50)
    p95_ms  = [int](Pct -V $sorted -P 95)
    samples = $vals
    log     = $OutLog
}
$outJson = Join-Path $Root "docs\fase-1\voice-latency-last.json"
$report | ConvertTo-Json -Depth 4 | Set-Content $outJson -Encoding utf8
Write-Host "Wrote $outJson"
exit $benchExit
