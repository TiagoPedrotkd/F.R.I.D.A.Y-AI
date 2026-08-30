# Relatório de entrega — FRIDAY LLM (secção 24)

**Data:** 2026-08-29  
**Run:** friday-llm-personalization  
**Produção:** `LM_STUDIO_MODEL=microsoft/phi-4` (inalterado)

---

## Resumo executivo

O pipeline Fases 0–6 está **operacional**. Nesta sessão foram concluídos dados reais FineWeb, índice RAG com embeddings, integração MCP `search_docs`, export smoke validado, e **treino CPT 7B em curso** na RTX 3060. SFT 7B e export final 7B estão encadeados automaticamente após o CPT (`scripts/phase4_6_after_cpt.ps1`).

| Critério (sec. 23) | Estado |
|--------------------|--------|
| Corpus CPT aprovado (~500 docs) | ✅ 471 docs, ~357k tokens |
| CPT 7B treinado + checkpoint best | 🔄 Em curso (~10/300 steps) |
| SFT 7B treinado + checkpoint best | ⏳ Após CPT |
| Merge HF + manifest | ✅ Smoke 0.5B; 7B após SFT |
| GGUF Q4/Q5 | ⚠️ Requer llama.cpp local |
| Eval pós-treino vs baseline | ⏳ `run_eval=false` (Phi-4 baseline 46.7%) |
| RAG embeddings + search_docs | ✅ 57 chunks indexados |
| MCP `search_docs` | ✅ Registado em `friday-mcp` |
| Modelo no LM Studio (produção) | ❌ Phi-4 mantido de propósito |

---

## Fase 0 — Auditoria

- Hardware: RTX 3060 12 GB, i7-14700KF, 32 GB RAM — ver [`phase0_audit.md`](phase0_audit.md)
- PyTorch CUDA: `2.6.0+cu124` (instalado nesta sessão; anteriormente era build CPU)

## Fase 1 — Dados

| Artefacto | Valor |
|-----------|-------|
| Fonte CPT | FineWeb stream (`por_Latn` + `eng_Latn`) |
| Documentos CPT | 471 |
| Tokens estimados | 357 121 |
| SFT train/holdout | 43 / 7 (fase1) · 51 / 10 (fase4) |
| RAG chunks | 54–57 |
| Eval leaks | 0 |

Relatório: [`phase1_data_report.md`](phase1_data_report.md)

**Correções aplicadas:** fallback multi-config em `fineweb.py`; config `eng_Latn` para FineWeb-2.

## Fase 2 — Piloto smoke

- Checkpoints: `cpt-smoke`, `sft-smoke` (Qwen2.5-0.5B)
- Baseline Phi-4: pass_rate **0.467** ([`baseline_phi4.json`](baseline_phi4.json))

## Fase 3 — CPT 7B

- Corpus aprovado: [`corpus_approval.json`](corpus_approval.json)
- Treino: `Qwen/Qwen2.5-7B` QLoRA, 300 steps, seq 1024
- Log: [`cpt_fase3_train.log`](cpt_fase3_train.log)
- ETA treino: ~2,5 h (30 s/step na RTX 3060)
- Output: `checkpoints/cpt-fase3/` → `cpt-fase3-best/adapter`

## Fase 4 — SFT 7B

- Dataset: `data/sft/fase4_sft_train.jsonl` (51 exemplos)
- Aprovação: [`sft_approval.json`](sft_approval.json)
- **Aguarda** conclusão CPT; script automático: `scripts/phase4_6_after_cpt.ps1`

## Fase 5 — RAG

| Item | Detalhe |
|------|---------|
| Corpus | repo docs + seeds |
| Chunks | 57 |
| Índice | `data/rag_chroma/chroma` |
| Embedding | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` |
| Backend runtime | keyword + embedding (Chroma) |
| Skill | `friday/skills/rag/search_docs.py` |
| MCP | `search_docs` em `friday/mcp_server/server.py` |

**Nota técnica:** `sentence-transformers` causa crash pyarrow no Windows global; embeddings via `friday_llm/rag/embeddings.py` (transformers mean-pool).

Relatório: [`phase5_rag_report.md`](phase5_rag_report.md)

## Fase 6 — Export

| Modo | Estado |
|------|--------|
| Smoke (0.5B) | Merge OK → `export/merged-friday-v1/` |
| GGUF | Skipped — llama.cpp não encontrado |
| Manifest | [`export_manifest.json`](export_manifest.json) |
| Rollback | [`export/rollback.md`](../export/rollback.md) |

Após SFT 7B, re-export com `use_smoke_model: false` (script actualiza `fase6_export.yaml`).

---

## Dependências e ambiente

| Pacote | Versão / nota |
|--------|----------------|
| torch | 2.6.0+cu124 |
| transformers | 4.48.3 |
| peft | 0.14.0 |
| bitsandbytes | 0.50.2 (Windows) |
| protobuf | 6.x (Chroma); conflito com mediapipe/tf global |
| numpy | <2.1 |

Recomendação: usar `.venv` dedicado ao projecto para evitar conflitos com tensorflow/mediapipe no Python global.

---

## Comandos pós-CPT (manual se o script falhar)

```powershell
$env:TRANSFORMERS_NO_TF = "1"
python -m friday_llm.training.sft.cli --config friday-llm/configs/fase4_sft.yaml
# Editar fase6_export.yaml: use_smoke_model false, adapters cpt-fase3-best + sft-fase4-best
python -m friday_llm.export.cli --config friday-llm/configs/fase6_export.yaml
# Opcional: eval com modelo carregado no LM Studio
python -m friday_llm.evaluation.run_baseline --model <seu-modelo-gguf>
```

GGUF: instalar [llama.cpp](https://github.com/ggerganov/llama.cpp) e definir `llama_cpp.path` em `fase6_export.yaml`.

---

## Testes

```
58 passed — friday-llm/tests/
```

---

## O que permanece por fazer (operacional)

1. **Aguardar CPT + SFT** (~3–4 h total na RTX 3060)
2. **Instalar llama.cpp** e re-correr export para GGUF
3. **Eval gate** com modelo candidato no LM Studio (`run_eval: true`)
4. **Troca manual** de `LM_STUDIO_MODEL` quando satisfeito com o modelo Friday (nunca automático)

---

## Ficheiros novos/alterados nesta sessão

- `friday/mcp_server/server.py` — tool `search_docs`
- `friday-llm/friday_llm/rag/embeddings.py` — embeddings Windows-safe
- `friday-llm/friday_llm/pipeline/ingest/fineweb.py` — fallback configs HF
- `friday-llm/configs/fase1_data.yaml`, `fase5_rag.yaml`
- `scripts/phase4_6_after_cpt.ps1` — encadeamento SFT + export
- `pyproject.toml` — pins numpy/protobuf/torch

**Phi-4 em produção não foi alterado.**
