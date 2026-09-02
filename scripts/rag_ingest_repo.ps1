# Rebuild + reindex document RAG from repo markdown (scheduled / manual).
# Separates knowledge base (data/rag_chroma) from personal memory (data/chroma).
#
# Usage:
#   .\scripts\rag_ingest_repo.ps1
#   .\scripts\rag_ingest_repo.ps1 -SkipIndex   # so build chunks only

param(
    [switch]$SkipIndex
)

$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))
$env:PYTHONIOENCODING = "utf-8"

Write-Host "RAG ingest: build corpus from repo docs..."
$env:TRANSFORMERS_NO_TF = "1"
$env:TRANSFORMERS_NO_FLAX = "1"
$env:TOKENIZERS_PARALLELISM = "false"
python -m friday_llm.rag.cli --config friday-llm/configs/fase5_rag.yaml --only build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipIndex) {
    Write-Host "RAG ingest: index embeddings -> data/rag_chroma..."
    python -m friday_llm.rag.cli --config friday-llm/configs/fase5_rag.yaml --only index
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "RAG ingest: smoke search..."
python -m friday_llm.rag.cli --config friday-llm/configs/fase5_rag.yaml --only smoke
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "RAG ingest: quality gate (recall@k / MRR)..."
python -m friday_llm.rag.cli --config friday-llm/configs/fase5_rag.yaml --only gate
if ($LASTEXITCODE -ne 0) {
    Write-Host "QUALITY GATE FAILED — ingest not accepted." -ForegroundColor Red
    exit $LASTEXITCODE
}

# Notify running agent-api to hot-reload (best-effort)
try {
    Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8090/v1/admin/rag-reload" -TimeoutSec 5 | Out-Null
    Write-Host "Notified agent-api rag-reload"
} catch {
    Write-Host "agent-api reload skipped (not running): $($_.Exception.Message)"
}

Write-Host @"

Done.
  Knowledge (RAG): data/rag_chroma  (friday_docs)
  Personal memory: data/chroma      (friday_memory)
Schedule weekly via Task Scheduler if desired.
"@
