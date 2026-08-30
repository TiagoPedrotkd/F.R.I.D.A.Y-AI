# Guia LM Studio — Fase 2 Piloto

## Política

- **Não** alterar `LM_STUDIO_MODEL` no `.env` do repositório.
- Testar o piloto com variável de ambiente temporária na sessão PowerShell.
- Rollback: repor `microsoft/phi-4`.

## Pré-requisitos

1. Pipeline Fase 2 concluído (`checkpoints/sft-fase2-pilot/adapter`).
2. Manifesto gerado:

```powershell
python -m friday_llm.export.manifest --adapter friday-llm/checkpoints/sft-fase2-pilot/adapter
```

## Opção A — Adapter PEFT (rápida)

1. Abrir LM Studio e carregar o modelo base (`Qwen/Qwen2.5-0.5B` no piloto smoke, ou `Qwen2.5-7B` quando disponível).
2. Se o LM Studio suportar LoRA/adapter na UI, apontar para:
   `friday-llm/checkpoints/sft-fase2-pilot/adapter`
3. Anotar o **model id** que o LM Studio expõe na API.

## Opção B — GGUF (recomendada para inferência estável)

1. Fundir adapter (opcional, se VRAM permitir):

```python
# script local — não commitar tokens
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer
base = "Qwen/Qwen2.5-0.5B"
adapter = "friday-llm/checkpoints/sft-fase2-pilot/adapter"
model = AutoModelForCausalLM.from_pretrained(base, torch_dtype="auto", device_map="cpu")
model = PeftModel.from_pretrained(model, adapter)
model = model.merge_and_unload()
model.save_pretrained("friday-llm/export/merged-fase2-pilot")
```

2. Converter com [llama.cpp](https://github.com/ggerganov/llama.cpp) `convert_hf_to_gguf.py`.
3. Quantizar (ex. `Q4_K_M`) se necessário.
4. Importar GGUF no LM Studio.

## Avaliação temporária

```powershell
$env:LM_STUDIO_MODEL = "<seu-modelo-piloto>"
python -m friday_llm.evaluation.run_baseline --out friday-llm/reports/phase2_eval_pilot.json
python -m friday_llm.training.pilot.cli --config friday-llm/configs/fase2_pilot.yaml --only report --skip-train
```

Comparar com `friday-llm/reports/baseline_phi4.json`.

## Rollback

```powershell
Remove-Item Env:LM_STUDIO_MODEL -ErrorAction SilentlyContinue
# ou
$env:LM_STUDIO_MODEL = "microsoft/phi-4"
```

O agente F.R.I.D.A.Y. volta ao Phi-4 de produção.

---

## Fase 6 — Modelo final (GGUF)

### Pipeline automatizado

```powershell
pip install -e ".[llm]"

# Validar → merge → GGUF → manifest → relatório (eval opcional)
python -m friday_llm.export.cli --config friday-llm/configs/fase6_export.yaml

# Só merge HF (sem llama.cpp)
python -m friday_llm.export.cli --only merge

# GGUF (requer llama.cpp em LLAMA_CPP_PATH)
python -m friday_llm.export.cli --only gguf
```

Config: [`configs/fase6_export.yaml`](../configs/fase6_export.yaml) — adapters, quantização (`Q4_K_M`, `Q5_K_M`), paths.

### Carregar no LM Studio

1. Importar `friday-llm/export/gguf/*-Q4_K_M.gguf`
2. Anotar **model id** na API (ex. `friday-qwen25-smoke-v1-Q4_K_M`)
3. Teste temporário:

```powershell
$env:LM_STUDIO_MODEL = "<model-id-lm-studio>"
python -m friday_llm.evaluation.run_baseline --out friday-llm/reports/phase6_eval_final.json
python -m friday_llm.export.cli --config friday-llm/configs/fase6_export.yaml --only eval --run-eval
```

### Rollback

Ver [`rollback.md`](rollback.md).
