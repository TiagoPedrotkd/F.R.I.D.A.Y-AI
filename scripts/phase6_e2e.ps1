# Fase 6 — E2E smoke (manual; requer LM Studio + agent-api opcional)
# Uso: .\scripts\phase6_e2e.ps1 [-ModelId "friday-qwen25-smoke-v1-Q4_K_M"]

param(
    [string]$ModelId = "",
    [string]$Config = "friday-llm/configs/fase6_export.yaml",
    [string]$AgentApi = "http://127.0.0.1:8090"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$prevModel = $env:LM_STUDIO_MODEL
$restored = $false

function Restore-Model {
    if ($restored) { return }
    if ($null -ne $prevModel) {
        $env:LM_STUDIO_MODEL = $prevModel
    } else {
        Remove-Item Env:LM_STUDIO_MODEL -ErrorAction SilentlyContinue
    }
    $restored = $true
}

try {
    Write-Host "== Fase 6 E2E ==" -ForegroundColor Cyan

    # 1. LM Studio health
    $healthUrl = if ($env:HEALTHCHECK_URL) { $env:HEALTHCHECK_URL } else { "http://127.0.0.1:8080" }
    try {
        Invoke-RestMethod -Uri "$healthUrl/health" -TimeoutSec 5 | Out-Null
        Write-Host "[OK] Healthcheck $healthUrl" -ForegroundColor Green
    } catch {
        Write-Warning "Healthcheck indisponivel em $healthUrl — continua se LM Studio estiver manualmente activo."
    }

    if ($ModelId) {
        $env:LM_STUDIO_MODEL = $ModelId
        Write-Host "[INFO] LM_STUDIO_MODEL = $ModelId" -ForegroundColor Yellow
    } elseif (-not $env:LM_STUDIO_MODEL) {
        Write-Warning "Defina -ModelId ou LM_STUDIO_MODEL para eval do modelo exportado."
    }

    # 2. Eval baseline / gate
    if ($env:LM_STUDIO_MODEL -and $env:LM_STUDIO_MODEL -ne "microsoft/phi-4") {
        python -m friday_llm.export.cli --config $Config --only eval --run-eval
        Write-Host "[OK] Eval candidato gravada em friday-llm/reports/phase6_eval_final.json" -ForegroundColor Green
    } else {
        Write-Host "[SKIP] Eval candidato (modelo exportado nao definido)" -ForegroundColor DarkYellow
    }

    # 3. Relatorio
    python -m friday_llm.export.cli --config $Config --only report
    Write-Host "[OK] Relatorio phase6_export_report.md" -ForegroundColor Green

    # 4. Smoke agent-api (opcional)
    try {
        $body = @{ text = "Que horas sao?" } | ConvertTo-Json
        $session = Invoke-RestMethod -Method Post -Uri "$AgentApi/v1/sessions" -ContentType "application/json"
        $sid = $session.id
        $chat = Invoke-RestMethod -Method Post -Uri "$AgentApi/v1/sessions/$sid/chat" -Body $body -ContentType "application/json"
        if ($chat.reply) {
            Write-Host "[OK] Agent-api chat smoke: $($chat.reply.Substring(0, [Math]::Min(80, $chat.reply.Length)))..." -ForegroundColor Green
        }
    } catch {
        Write-Warning "Agent-api smoke ignorado: $_"
    }

    Write-Host "`nRollback: Remove-Item Env:LM_STUDIO_MODEL; ou veja friday-llm/export/rollback.md" -ForegroundColor Cyan
} finally {
    Restore-Model
}
