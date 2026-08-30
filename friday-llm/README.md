# F.R.I.D.A.Y. LLM (personalização local)

Pipeline local para **pré-treino continuado (CPT)**, **SFT**, **RAG documental** e
**exportação GGUF** compatível com LM Studio. Complementa o agente existente —
não o substitui automaticamente.

## Princípios

- Conhecimento nos pesos ≠ documentos RAG ≠ dados actuais via tools.
- Nunca misturar `data/chroma/` (memória pessoal) com datasets de treino.
- O modelo de produção continua a ser `LM_STUDIO_MODEL` (default `microsoft/phi-4`)
  até troca **explícita e reversível**.
- Subsets piloto **não** significam que o modelo “aprendeu tudo”.

## Hardware alvo (hub actual)

- RTX 3060 12 GB → QLoRA 7B–8B; sem cloud no piloto.

## Estrutura

Ver árvore em `friday-llm/`. Dados pesados e checkpoints estão no `.gitignore`.

## Comandos rápidos

```powershell
# Baseline contra o modelo actual no LM Studio (sem treino)
python -m friday_llm.evaluation.run_baseline

# Pipeline piloto (Fase 0)
python -m friday_llm.pipeline.build_datasets.cli --config friday-llm/configs/pilot.yaml

# Fase 1 — dados (CPT/SFT/RAG; offline usa seed sintético)
python -m friday_llm.pipeline.build_datasets.cli --config friday-llm/configs/fase1_data.yaml
python -m friday_llm.pipeline.build_datasets.cli --config friday-llm/configs/fase1_data.yaml --offline

# Actualizar catálogo após build
python -m friday_llm.pipeline.registry.catalog --cpt friday-llm/data/pretraining/cpt_fase1.jsonl --sft-train friday-llm/data/sft/fase1_sft_train.jsonl --sft-holdout friday-llm/data/sft/fase1_sft_holdout.jsonl --rag friday-llm/data/rag/chunks.jsonl

# Smoke CPT / SFT (requer extras [llm])
pip install -e ".[llm]"
python -m friday_llm.training.continued_pretraining.smoke --config friday-llm/configs/cpt_smoke.yaml
python -m friday_llm.training.sft.smoke --config friday-llm/configs/sft_smoke.yaml
```

## Fase 1 — Dados

Orçamento: **~500 documentos / ~2M tokens** CPT (FineWeb2 `por_Latn` + `eng_Latn` stream),
SFT expandido com templates do `SkillRegistry`, RAG a partir de `docs/**/*.md`.

Relatório: [`reports/phase1_data_report.md`](reports/phase1_data_report.md) e
[`reports/phase1_data_stats.json`](reports/phase1_data_stats.json).

## Fase 2 — Piloto de treino

Subset Fase 1 → CPT LoRA → SFT com adapter CPT → checkpoint retomável → eval vs baseline → export LM Studio.

```powershell
# Pipeline completo (CPT + SFT + manifest + relatório; eval LM Studio opcional)
python -m friday_llm.training.pilot.cli --config friday-llm/configs/fase2_pilot.yaml

# Só CPT ou SFT; retomar após interrupção
python -m friday_llm.training.pilot.cli --config friday-llm/configs/fase2_pilot.yaml --only cpt
python -m friday_llm.training.pilot.cli --config friday-llm/configs/fase2_pilot.yaml --only sft --resume

# Eval no LM Studio (modelo piloto carregado; variável temporária)
$env:LM_STUDIO_MODEL = "<seu-modelo-piloto>"
python -m friday_llm.training.pilot.cli --config friday-llm/configs/fase2_pilot.yaml --only eval --run-eval --skip-train

# Manifesto + guia
python -m friday_llm.export.manifest --adapter friday-llm/checkpoints/sft-fase2-pilot/adapter
```

Guia LM Studio: [`export/lm_studio_guide.md`](export/lm_studio_guide.md)  
Relatório: [`reports/phase2_pilot_report.md`](reports/phase2_pilot_report.md)

## Fase 3 — Pré-treino continuado (CPT)

Corpus Fase 1 aprovado → CPT **Qwen2.5-7B** QLoRA (fp16 fallback no Windows) → eval intermédia → melhor checkpoint.

```powershell
pip install -e ".[llm]"

# Aprovar corpus + treinar + seleccionar melhor adapter + relatório
python -m friday_llm.training.cpt.cli --config friday-llm/configs/fase3_cpt.yaml

# Passos isolados
python -m friday_llm.training.corpus.approval --data friday-llm/data/pretraining/cpt_fase1.jsonl
python -m friday_llm.training.cpt.cli --config friday-llm/configs/fase3_cpt.yaml --only train --resume
python -m friday_llm.training.continued_pretraining.select_checkpoint --run-dir friday-llm/checkpoints/cpt-fase3
```

Pré-requisitos: build Fase 1 com dados reais; VRAM ~12 GB; `seq_length` 1024 com batch 1 e grad accum 8.

Relatório: [`reports/phase3_cpt_report.md`](reports/phase3_cpt_report.md)  
Melhor adapter: `checkpoints/cpt-fase3-best/adapter`

## Fase 4 — SFT (conversação, personalidade, tools, segurança)

Dataset curado (templates + seed) → aprovação → SFT **Qwen2.5-7B** encadeado ao CPT Fase 3 → melhor checkpoint → eval por categoria vs baseline Phi-4.

```powershell
pip install -e ".[llm]"

# Build dataset + aprovar + relatório (sem treino GPU)
python -m friday_llm.pipeline.build_datasets.sft_fase4_builder
python -m friday_llm.training.sft.approval
python -m friday_llm.training.sft.cli --config friday-llm/configs/fase4_sft.yaml --only report

# Pipeline completo (treino requer GPU + adapter CPT)
python -m friday_llm.training.sft.cli --config friday-llm/configs/fase4_sft.yaml

# Passos isolados
python -m friday_llm.training.sft.cli --config friday-llm/configs/fase4_sft.yaml --only train --resume
python -m friday_llm.training.continued_pretraining.select_checkpoint --run-dir friday-llm/checkpoints/sft-fase4 --dest friday-llm/checkpoints/sft-fase4-best/adapter --metrics friday-llm/reports/sft_checkpoint_metrics.jsonl
```

`friday_eval.jsonl` **nunca** entra no treino. Phi-4 em produção permanece inalterado.

Relatório: [`reports/phase4_sft_report.md`](reports/phase4_sft_report.md)  
Melhor adapter: `checkpoints/sft-fase4-best/adapter`

## Fase 5 — RAG e integração

Corpus repo + seeds → embeddings locais → Chroma `friday_docs` em `data/rag_chroma/` → skill `search_docs` no agente (CLI + web).

**Separado da memória pessoal:** `data/chroma/` (`friday_memory`) ≠ `data/rag_chroma/` (`friday_docs`).

```powershell
pip install -e ".[rag,voice,api]"

# Build corpus + indexar + smoke + relatório
python -m friday_llm.rag.cli --config friday-llm/configs/fase5_rag.yaml

# Passos isolados
python -m friday_llm.rag.cli --only build
python -m friday_llm.rag.cli --only index
python -m friday_llm.rag.cli --only smoke --query "Como ligar ao LM Studio?"

# Agente (Phi-4 inalterado; usa search_docs via intent router)
friday-voice   # ou web UI + agent-api
```

Variáveis: `RAG_ENABLED`, `RAG_BACKEND` (`embedding`|`keyword`), `RAG_CORPUS_PATH`, `RAG_INDEX_DIR`, `RAG_EMBEDDING_MODEL`, `RAG_TOP_K`.

Relatório: [`reports/phase5_rag_report.md`](reports/phase5_rag_report.md)

## Fase 6 — Modelo final (export GGUF)

Merge CPT+SFT → HF → GGUF quantizado → LM Studio → eval gate vs Phi-4 → rollback documentado.

```powershell
pip install -e ".[llm]"

# Pipeline completo (GGUF skipped se llama.cpp ausente)
python -m friday_llm.export.cli --config friday-llm/configs/fase6_export.yaml

# Eval com modelo carregado no LM Studio
$env:LM_STUDIO_MODEL = "<model-id>"
python -m friday_llm.export.cli --config friday-llm/configs/fase6_export.yaml --only eval --run-eval

# E2E manual (PowerShell)
./scripts/phase6_e2e.ps1
```

Para 7B: `use_smoke_model: false` e adapters `cpt-fase3-best` + `sft-fase4-best` em `fase6_export.yaml`.

Relatório: [`reports/phase6_export_report.md`](reports/phase6_export_report.md)  
Rollback: [`export/rollback.md`](export/rollback.md)

## Documentação

- Relatório Fase 0: [`reports/phase0_audit.md`](reports/phase0_audit.md)
- Export LM Studio: [`export/README.md`](export/README.md)
