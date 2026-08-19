#Requires -Version 5.1
<#
.SYNOPSIS
    Aggregate p50/p95 latency from turn_complete JSON log lines.
.DESCRIPTION
    Pipe voice loop stdout or pass a log file:
      .\scripts\benchmark-latency.ps1 -LogFile logs\voice.log
#>
param(
    [string]$LogFile = ""
)

function Get-Percentile {
    param([double[]]$Values, [double]$P)
    if ($Values.Count -eq 0) { return $null }
    $sorted = $Values | Sort-Object
    $idx = [math]::Ceiling(($P / 100.0) * $sorted.Count) - 1
    $idx = [math]::Max(0, [math]::Min($idx, $sorted.Count - 1))
    return $sorted[$idx]
}

$lines = @()
if ($LogFile -and (Test-Path $LogFile)) {
    $lines = Get-Content $LogFile
} else {
    Write-Host "No log file provided. Usage:" -ForegroundColor Yellow
    Write-Host "  python -m friday.pipeline.loop 2>&1 | Tee-Object logs\voice.log"
    Write-Host "  .\scripts\benchmark-latency.ps1 -LogFile logs\voice.log"
    exit 1
}

$wakeToTts = @()
foreach ($line in $lines) {
    if ($line -notmatch '"event"\s*:\s*"turn_complete"') { continue }
    try {
        $obj = $line | ConvertFrom-Json
        if ($null -ne $obj.wake_to_tts_ms) {
            $wakeToTts += [double]$obj.wake_to_tts_ms
        }
    } catch {
        # try extracting JSON substring
        if ($line -match '\{.*"event"\s*:\s*"turn_complete".*\}') {
            try {
                $obj = $Matches[0] | ConvertFrom-Json
                $wakeToTts += [double]$obj.wake_to_tts_ms
            } catch { }
        }
    }
}

if ($wakeToTts.Count -eq 0) {
    Write-Host "No turn_complete events found in log." -ForegroundColor Red
    exit 1
}

$p50 = Get-Percentile -Values $wakeToTts -P 50
$p95 = Get-Percentile -Values $wakeToTts -P 95

Write-Host ""
Write-Host "Latency benchmark ($($wakeToTts.Count) turns)" -ForegroundColor Cyan
Write-Host "  p50 wake_to_tts_ms: $([int]$p50) ms"
Write-Host "  p95 wake_to_tts_ms: $([int]$p95) ms"
Write-Host ""
if ($p50 -gt 4000) {
    Write-Host "p50 exceeds 4s target — see docs/fase-1/latency-benchmark.md" -ForegroundColor Yellow
}
