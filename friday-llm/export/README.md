# Exportação GGUF / LM Studio

## Política

- Guardar adapter PEFT em `friday-llm/checkpoints/*/adapter/`.
- **Não** alterar `LM_STUDIO_MODEL` automaticamente.
- Rollback: [`rollback.md`](rollback.md) — repor `microsoft/phi-4`.

## Fase 6 — Pipeline automatizado

```powershell
pip install -e ".[llm]"

# Completo (merge + GGUF se llama.cpp disponível + manifest + relatório)
python -m friday_llm.export.cli --config friday-llm/configs/fase6_export.yaml

# Passos isolados
python -m friday_llm.export.cli --only validate
python -m friday_llm.export.cli --only merge
python -m friday_llm.export.cli --only gguf
python -m friday_llm.export.cli --only manifest
python -m friday_llm.export.cli --only eval --run-eval
```

Configurável em [`configs/fase6_export.yaml`](../configs/fase6_export.yaml):
- `cpt_adapter` / `sft_adapter` (smoke ou fase4-best)
- `use_smoke_model` para Qwen2.5-0.5B em dev
- `quantization`: Q4_K_M (RTX 3060), Q5_K_M opcional
- `LLAMA_CPP_PATH` ou `llama_cpp.path` para conversão GGUF

## Fluxo manual (legado)

1. Fundir adapters com `merge.py` ou CLI `--only merge`
2. Converter com [llama.cpp](https://github.com/ggerganov/llama.cpp)
3. Quantizar Q4_K_M
4. Carregar no LM Studio
5. Eval temporária com `LM_STUDIO_MODEL` na sessão
6. Manifesto: `friday-llm/reports/export_manifest.json`

## Script de manifesto (standalone)

```powershell
python -m friday_llm.export.manifest --adapter friday-llm/checkpoints/sft-smoke/adapter
```

Guia LM Studio: [`lm_studio_guide.md`](lm_studio_guide.md)
