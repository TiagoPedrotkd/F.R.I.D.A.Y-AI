# Exemplo pronto — Dia 1 (10 documentos)

## Pedido

> Dia 1: 10 documentos

## O que acontece

1. Tira 10 docs ainda não usados de `cpt_fase1.jsonl`.
2. Append a `corpus_cumulative.jsonl` (10 docs).
3. Escreve `configs/incremental/cpt_day_1.yaml` com `max_steps ≈ 40` (10×4).
4. Gera `scripts/cpt_day_1.ps1`.
5. Actualiza `reports/incremental/progress.md`.
6. Treina Qwen2.5-7B QLoRA até completar esses steps (muitas vezes ~15–40 min na 3060 — **não** forçado a 1h).

## Comando (copia/cola)

Na raiz do repo:

```powershell
$env:TRANSFORMERS_NO_TF = "1"
$env:USE_TF = "0"
$env:USE_TORCH = "1"
$env:PYTHONIOENCODING = "utf-8"

python -m friday_llm.training.incremental.cli --day 1 --add 10 --train
```

Só preparar (sem treinar ainda):

```powershell
python -m friday_llm.training.incremental.cli --day 1 --add 10
.\scripts\cpt_day_1.ps1
```

## Verificar progresso

```powershell
python -m friday_llm.training.incremental.cli --status
Get-Content friday-llm\reports\incremental\progress.md
```

## Dia 2 (exemplo)

> Dia 2: 15 documentos

```powershell
python -m friday_llm.training.incremental.cli --day 2 --add 15 --train
```

Cumulativo passa a 25 docs; `max_steps` sobe a partir do base do Dia 1 + steps do batch novo.
