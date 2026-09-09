#Requires -Version 5.1
<#
.SYNOPSIS
    Live gates smoke for Fases 2–5 (IMAP, HA, Google, Finanças).

.DESCRIPTION
    Probes local services without printing secrets or PII.
    Writes docs/fase-N/live-smoke-last.json and prints a gate summary.
    IMAP requires EMAIL_* in .env; HA/Google/Finance use existing config.
#>
param(
    [switch]$RequireImap,
    [switch]$RequireInvestments
)

$ErrorActionPreference = "Continue"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $Root
$py = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }

function Test-EnvPresent([string]$Name) {
    $line = Get-Content (Join-Path $Root ".env") -ErrorAction SilentlyContinue |
        Where-Object { $_ -match "^$([regex]::Escape($Name))=" } |
        Select-Object -First 1
    if (-not $line) { return $false }
    $val = ($line -split "=", 2)[1].Trim()
    return -not [string]::IsNullOrWhiteSpace($val)
}

function Get-Json([string]$Url, [int]$TimeoutSec = 30) {
    try {
        return @{ ok = $true; data = (Invoke-RestMethod -Uri $Url -TimeoutSec $TimeoutSec) }
    } catch {
        $code = $null
        if ($_.Exception.Response) { $code = [int]$_.Exception.Response.StatusCode }
        return @{ ok = $false; status = $code; err = $_.Exception.Message }
    }
}

$at = (Get-Date).ToUniversalTime().ToString("o")
$gates = [ordered]@{}

Write-Host "=== Fases 2-5 live gates ===" -ForegroundColor Cyan

# --- Fase 2 IMAP ---
$imapKeys = @("EMAIL_ENABLED", "IMAP_HOST", "IMAP_USER", "IMAP_PASSWORD")
$imapPresent = @{}
foreach ($k in $imapKeys) { $imapPresent[$k] = Test-EnvPresent $k }
$imapConfigured = ($imapPresent["EMAIL_ENABLED"] -and $imapPresent["IMAP_HOST"] -and $imapPresent["IMAP_USER"] -and $imapPresent["IMAP_PASSWORD"])
$imapOk = $false
$imapDetail = "EMAIL_*/IMAP_* em falta no .env"
if ($imapConfigured) {
    $code = @'
from friday.config import get_settings
from friday.productivity.email_client import list_emails, EmailSettings
s = get_settings()
cfg = EmailSettings(
    imap_host=s.imap_host, imap_port=s.imap_port, imap_user=s.imap_user,
    imap_password=s.imap_password, imap_folder=s.imap_folder,
)
msgs = list_emails(cfg, limit=3)
print("ok", len(msgs))
'@
    $out = $code | & $py - 2>&1
    if ($LASTEXITCODE -eq 0 -and ("$out" -match "^ok")) {
        $imapOk = $true
        $imapDetail = "$out".Trim()
    } else {
        $imapDetail = ("IMAP smoke falhou: " + ("$out".Trim()))
    }
}
$gates["fase2_imap"] = @{ ok = $imapOk; detail = $imapDetail; configured = $imapConfigured }
if ($RequireImap -and -not $imapOk) { $gates["fase2_imap"].required_fail = $true }

# --- Fase 3 HA ---
$haHttp = $false
try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:8123/" -TimeoutSec 5 -UseBasicParsing
    $haHttp = ($r.StatusCode -ge 200 -and $r.StatusCode -lt 500)
} catch { $haHttp = $false }
$haApi = Get-Json "http://127.0.0.1:8090/v1/ha/status"
$haEnt = Get-Json "http://127.0.0.1:8090/v1/ha/entities?limit=5"
$haOk = $haHttp -and $haApi.ok -and $haEnt.ok
$gates["fase3_ha"] = @{
    ok = $haOk
    detail = "http=$haHttp api=$($haApi.ok) entities=$($haEnt.ok)"
}

# --- Fase 4 Google ---
$g = Get-Json "http://127.0.0.1:8090/v1/google/status"
$mail = Get-Json "http://127.0.0.1:8090/v1/mail/messages?limit=3" 45
$agenda = Get-Json "http://127.0.0.1:8090/v1/agenda/events?days=14" 45
$health = Get-Json "http://127.0.0.1:8090/v1/health/status"
$syncOk = $false
try {
    $sync = Invoke-RestMethod -Uri "http://127.0.0.1:8090/v1/health/sync" -Method POST -ContentType "application/json" -Body "{}" -TimeoutSec 90
    $syncOk = [bool]$sync.ok
} catch { $syncOk = $false }
# CalDAV fallback (isolated Settings; does not mutate .env)
$caldavFallback = $false
$fb = & $py -c "from friday.config import Settings; from friday.productivity.calendar_provider import list_events; s=Settings(GOOGLE_ENABLED=False, CALDAV_ENABLED=True, CALDAV_URL='http://127.0.0.1:5232/friday/friday/', CALDAV_USER='friday', CALDAV_PASSWORD='friday'); print(len(list_events(s, days=7)))" 2>&1
if ($LASTEXITCODE -eq 0) { $caldavFallback = $true }
$googleOk = $g.ok -and $g.data.connected -and $mail.ok -and $agenda.ok -and $health.ok -and $syncOk -and $caldavFallback
$gates["fase4_google"] = @{
    ok = $googleOk
    detail = "connected=$($g.data.connected) mail=$($mail.ok) agenda=$($agenda.ok) health_sync=$syncOk caldav_fallback=$caldavFallback"
}

# --- Fase 5 Finanças ---
$fin = Get-Json "http://127.0.0.1:8090/v1/finance/summary"
$finStatus = Get-Json "http://127.0.0.1:8090/v1/finance/status"
$inv = Get-Json "http://127.0.0.1:8090/v1/finance/investments"
$skillOk = $false
$sk = & $py -c "import asyncio; from friday.config import get_settings; from friday.skills.registry import default_registry; s=default_registry(get_settings()).get('get_finance_summary'); r=asyncio.run(s.execute({})); print('ok' if r.success else 'fail')" 2>&1
if ($LASTEXITCODE -eq 0 -and ("$sk".Trim() -eq "ok")) { $skillOk = $true }
$salarySet = $false
$txCount = 0
$recurringSet = $false
$invoiceFiles = @(Get-ChildItem (Join-Path $Root "data\integrations\finance\invoices") -File -ErrorAction SilentlyContinue).Count
$positions = 0
if ($fin.ok) {
    $salarySet = ($null -ne $fin.data.salary_monthly -and $fin.data.salary_monthly -ne 0)
    $txCount = [int]($fin.data.transactions_count)
    $recurringSet = [bool]$fin.data.recurring_imputed
}
if ($inv.ok -and $inv.data.summary -and $inv.data.summary.brokers) {
    foreach ($b in @($inv.data.summary.brokers.PSObject.Properties)) {
        $positions += [int]$b.Value.positions_count
    }
}
$investOk = ($positions -gt 0)
$finCoreOk = $fin.ok -and $finStatus.ok -and $salarySet -and ($txCount -gt 0) -and $recurringSet -and ($invoiceFiles -gt 0) -and $skillOk
$finOk = $finCoreOk -and ((-not $RequireInvestments) -or $investOk)
$gates["fase5_financas"] = @{
    ok = $finOk
    detail = "salary=$salarySet tx=$txCount recurring=$recurringSet invoices=$invoiceFiles skill=$skillOk positions=$positions"
    investments_pending = (-not $investOk)
}

# Write per-fase reports
function Write-Report([string]$Fase, [hashtable]$Payload) {
    $dir = Join-Path $Root "docs\$Fase"
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    $payload = [ordered]@{ at = $at; gates = $Payload }
    ($payload | ConvertTo-Json -Depth 8) | Set-Content (Join-Path $dir "live-smoke-last.json") -Encoding utf8
}

Write-Report "fase-2" @{ imap = $gates["fase2_imap"] }
Write-Report "fase-3" @{ home_assistant = $gates["fase3_ha"] }
Write-Report "fase-4" @{ google = $gates["fase4_google"] }
Write-Report "fase-5" @{ financas = $gates["fase5_financas"] }

$passed = $true
foreach ($k in $gates.Keys) {
    $g0 = $gates[$k]
    $color = if ($g0.ok) { "Green" } else { "Yellow" }
    if ($g0.required_fail) { $color = "Red"; $passed = $false }
    if ($k -ne "fase2_imap" -and -not $g0.ok) { $passed = $false }
    if ($k -eq "fase2_imap" -and $RequireImap -and -not $g0.ok) { $passed = $false }
    Write-Host ("[{0}] {1} {2}" -f ($(if ($g0.ok) { "OK" } else { "OPEN" }), $k, $g0.detail)) -ForegroundColor $color
}

Write-Host ""
Write-Host "Reports: docs/fase-{2,3,4,5}/live-smoke-last.json"
if ($passed) { Write-Host "Live gates summary: PASS (IMAP opcional se sem -RequireImap)" -ForegroundColor Green; exit 0 }
Write-Host "Live gates summary: OPEN items remain" -ForegroundColor Yellow
exit 1
