# Scripts — F.R.I.D.A.Y-AI

## Arranque condicional

No login do Windows, o FRIDAY pergunta se queres iniciar os serviços.

### Instalação Task Scheduler (uma vez, Admin)

```powershell
powershell -ExecutionPolicy Bypass -File scripts\register-startup-task.ps1
```

Tarefa registada: **`FRIDAY-AI-Startup`** (At logon)

### Configurar caminho LM Studio (se auto-detect falhar)

```powershell
copy scripts\friday-config.ps1.example scripts\friday-config.ps1
# Editar scripts\friday-config.ps1 — definir $LmStudioExe com caminho completo
```

Ou variável de ambiente permanente:

```powershell
[System.Environment]::SetEnvironmentVariable("LM_STUDIO_EXE", "C:\caminho\LM Studio.exe", "User")
```

### Teste manual

```powershell
powershell -ExecutionPolicy Bypass -File scripts\friday-start.ps1
```

### Remover tarefa agendada

```powershell
Unregister-ScheduledTask -TaskName "FRIDAY-AI-Startup" -Confirm:$false
```

## Ficheiros

| Script | Descrição |
|---|---|
| [`friday-start.ps1`](friday-start.ps1) | Popup login → LM Studio + `docker compose up -d` |
| [`register-startup-task.ps1`](register-startup-task.ps1) | Regista Task Scheduler (Admin) |
| [`friday-config.ps1.example`](friday-config.ps1.example) | Template config local (copiar para `friday-config.ps1`) |
| [`find-lm-studio.ps1`](find-lm-studio.ps1) | Detecta caminho LM Studio para `friday-config.ps1` |
| [`cpt_day_N.ps1`](cpt_day_5.ps1) | CPT incremental dia N |
| [`cpt_prepare_domain_day.ps1`](cpt_prepare_domain_day.ps1) | Prepara dia seguinte com docs de dominio (sem treinar) |
| [`incremental_after_cpt.ps1`](incremental_after_cpt.ps1) | Select-best + SFT apos CPT |
| [`incremental_export_eval.ps1`](incremental_export_eval.ps1) | SFT → export GGUF/HF → eval gate opcional |
| [`eval_nightly.ps1`](eval_nightly.ps1) | Smoke eval periodico vs LM Studio |
| [`rag_ingest_repo.ps1`](rag_ingest_repo.ps1) | Rebuild/reindex RAG a partir de docs do repo |
| [`register-rag-ingest-task.ps1`](register-rag-ingest-task.ps1) | Agenda RAG ingest semanal (Admin) |
| [`model_cutover.ps1`](model_cutover.ps1) | Troca/rollback `LM_STUDIO_MODEL` no `.env` |
| [`cpt_finish_day5_then_domain.ps1`](cpt_finish_day5_then_domain.ps1) | Fecha Day 5 CPT + prepara Day 6 dominio |

## Comportamento

1. Login Windows → Task Scheduler executa `friday-start.ps1`
2. Popup: "Queres iniciar o F.R.I.D.A.Y-AI?"
3. **Sim** → LM Studio (auto-detect ou config) + Docker Compose
4. **Não** → nada; PC sem carga FRIDAY
