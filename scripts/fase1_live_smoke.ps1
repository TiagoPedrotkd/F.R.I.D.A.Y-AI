#Requires -Version 5.1
<#
.SYNOPSIS
    Live API smoke covering web-ui checklist items (no browser automation).
#>
param(
    [string]$Base = "http://127.0.0.1:8090"
)

$ErrorActionPreference = "Stop"
$results = [ordered]@{}

function Ok([string]$Name, [bool]$Pass, [string]$Detail = "") {
    $script:results[$Name] = @{ ok = $Pass; detail = $Detail }
    $c = if ($Pass) { "Green" } else { "Red" }
    Write-Host ("[{0}] {1} {2}" -f ($(if ($Pass) { "OK" } else { "FAIL" }), $Name, $Detail)) -ForegroundColor $c
}

Write-Host "=== Fase 1 live UI-path smoke (API) ===" -ForegroundColor Cyan

$status = Invoke-RestMethod -Uri "$Base/v1/status" -TimeoutSec 10
Ok "status_backend" ([bool]$status.backend) ("demo=$($status.demo) llm=$($status.llm.ok)")
Ok "status_llm" ([bool]$status.llm.ok) ("model=$($status.llm.model)")

$session = Invoke-RestMethod -Method Post -Uri "$Base/v1/sessions" -TimeoutSec 15
$sid = $session.id
Ok "session_create" ([bool]$sid) $sid

# Text chat - time
$body = @{ session_id = $sid; text = "Que horas sao?"; stream = $false } | ConvertTo-Json
$chat = Invoke-RestMethod -Method Post -Uri "$Base/v1/chat" -ContentType "application/json" -Body $body -TimeoutSec 180
Ok "chat_time" ([bool]$chat.reply) (($chat.reply.ToString().Substring(0, [Math]::Min(80, $chat.reply.ToString().Length))) -replace "`n", " ")

# Joke
$body = @{ session_id = $sid; text = "Conta uma piada curta."; stream = $false } | ConvertTo-Json
$joke = Invoke-RestMethod -Method Post -Uri "$Base/v1/chat" -ContentType "application/json" -Body $body -TimeoutSec 180
Ok "chat_joke" ([bool]$joke.reply) ""

# News (may be slow / network)
try {
    $body = @{ session_id = $sid; text = "Noticias mundiais"; stream = $false } | ConvertTo-Json
    $news = Invoke-RestMethod -Method Post -Uri "$Base/v1/chat" -ContentType "application/json" -Body $body -TimeoutSec 180
    $hasSources = $false
    if ($news.ui -and $news.ui.sources) { $hasSources = ($news.ui.sources.Count -gt 0) }
    Ok "chat_news" ([bool]$news.reply) ("sources=$hasSources kind=$($news.ui.kind)")
} catch {
    Ok "chat_news" $false $_.Exception.Message
}

# Finance
try {
    $body = @{ session_id = $sid; text = "Noticias de financas"; stream = $false } | ConvertTo-Json
    $fin = Invoke-RestMethod -Method Post -Uri "$Base/v1/chat" -ContentType "application/json" -Body $body -TimeoutSec 180
    Ok "chat_finance" ([bool]$fin.reply) ("kind=$($fin.ui.kind)")
} catch {
    Ok "chat_finance" $false $_.Exception.Message
}

# Monitor HTML
try {
    $mon = Invoke-WebRequest -Uri "$Base/monitors/world_snapshot.html" -TimeoutSec 10 -UseBasicParsing
    Ok "monitor_html" ($mon.StatusCode -eq 200) ("bytes=$($mon.RawContentLength)")
} catch {
    # try alternate names
    try {
        $mon = Invoke-WebRequest -Uri "$Base/monitors/world" -TimeoutSec 10 -UseBasicParsing
        Ok "monitor_html" ($mon.StatusCode -eq 200) "monitors/world"
    } catch {
        Ok "monitor_html" $false $_.Exception.Message
    }
}

# Confirmation demo
try {
    $conf = Invoke-RestMethod -Method Post -Uri "$Base/v1/demo/pending-confirmation?session_id=$sid" -TimeoutSec 15
    $pending = $null -ne $conf.pending_confirmation
    Ok "confirm_demo" $pending ("summary=$($conf.pending_confirmation.summary)")
    if ($pending) {
        $cancel = Invoke-RestMethod -Method Post -Uri "$Base/v1/confirm" -ContentType "application/json" `
            -Body (@{ session_id = $sid; decision = "cancel" } | ConvertTo-Json) -TimeoutSec 15
        Ok "confirm_cancel" ([bool]$cancel.reply) $cancel.decision
    }
} catch {
    Ok "confirm_demo" $false $_.Exception.Message
}

# Prefs roundtrip
try {
    $prefs = Invoke-RestMethod -Uri "$Base/v1/prefs" -TimeoutSec 10
    $put = Invoke-RestMethod -Method Put -Uri "$Base/v1/prefs" -ContentType "application/json" `
        -Body (@{ user_address = "Senhor"; theme = "dark" } | ConvertTo-Json) -TimeoutSec 10
    Ok "prefs" ($null -ne $put.prefs) ""
} catch {
    Ok "prefs" $false $_.Exception.Message
}

# TTS bytes (OutFile avoids PS binary Content null-ref on WAV)
$ttsOut = Join-Path $env:TEMP ("friday_fase1_tts_{0}.wav" -f [guid]::NewGuid().ToString("N"))
try {
    $tts = Invoke-WebRequest -Method Post -Uri "$Base/v1/tts" -ContentType "application/json" `
        -Body (@{ text = "Ola Senhor. Sao horas." } | ConvertTo-Json) -TimeoutSec 90 -OutFile $ttsOut -PassThru
    $len = 0
    if (Test-Path $ttsOut) { $len = [int](Get-Item -LiteralPath $ttsOut).Length }
    $code = 0
    if ($null -ne $tts -and $null -ne $tts.StatusCode) { $code = [int]$tts.StatusCode }
    elseif ($len -gt 100) { $code = 200 }
    Ok "tts_wav" ($code -eq 200 -and $len -gt 100) ("bytes=$len")
} catch {
    Ok "tts_wav" $false $_.Exception.Message
}

# STT path (proxy for mic→STT): reuse Piper WAV → Whisper
try {
    if (-not (Test-Path $ttsOut) -or ((Get-Item -LiteralPath $ttsOut).Length -lt 100)) {
        Ok "stt_from_wav" $false "no tts wav for stt"
    } else {
        $sttForm = @{
            audio    = Get-Item -LiteralPath $ttsOut
            language = "pt"
        }
        $stt = Invoke-RestMethod -Method Post -Uri "$Base/v1/stt" -Form $sttForm -TimeoutSec 180
        $sttText = [string]$stt.text
        Ok "stt_from_wav" ($sttText.Trim().Length -gt 0) ("text=$($sttText.Substring(0, [Math]::Min(60, $sttText.Length)))")
    }
} catch {
    Ok "stt_from_wav" $false $_.Exception.Message
} finally {
    Remove-Item -LiteralPath $ttsOut -Force -ErrorAction SilentlyContinue
}

# Sessions list
try {
    $list = Invoke-RestMethod -Uri "$Base/v1/sessions" -TimeoutSec 10
    Ok "sessions_list" ($list.sessions.Count -ge 1) ("n=$($list.sessions.Count)")
} catch {
    Ok "sessions_list" $false $_.Exception.Message
}

$failed = @($results.GetEnumerator() | Where-Object { -not $_.Value.ok }).Count
$out = Join-Path (Resolve-Path (Join-Path $PSScriptRoot "..")) "docs\fase-1\live-smoke-last.json"
@{
    at = (Get-Date).ToUniversalTime().ToString("o")
    base = $Base
    failed = $failed
    checks = $results
} | ConvertTo-Json -Depth 6 | Set-Content $out -Encoding utf8

Write-Host ""
Write-Host "Wrote $out (failed=$failed)"
if ($failed -gt 0) { exit 1 }
Write-Host "Live smoke PASSED." -ForegroundColor Green
exit 0
