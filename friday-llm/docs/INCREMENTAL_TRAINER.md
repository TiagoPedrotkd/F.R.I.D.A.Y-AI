# Treino incremental CPT — guia coach

## Reset (2026-09-04)

O run anterior foi arquivado em `friday-llm/checkpoints/archive/cpt-incremental-20260904/`.
O progresso voltou a **dia 0**. Próximos dias devem usar `--prefer-domain` e packs por domínio
(ver [docs/fase-llm/domain-packs.md](../../docs/fase-llm/domain-packs.md)).

## CPT vs RAG vs LoRA (comportamento)

| Camada | Serve para | Nao serve para |
|--------|------------|----------------|
| **CPT incremental** | Base linguistica / dominio local partilhado | Factos que mudam (ports, manuais) |
| **RAG + GraphRAG leve** | Factos e relacoes actualizaveis | Substituir o tom do assistente |
| **SFT / LoRA behavior** | Tom, formato, tool-use, CoT | Memorizar documentacao |

Seed de comportamento: `friday-llm/data/sft/behavior/seed_behavior.jsonl`.
Comparativo: [docs/fase-llm/rag-moe.md](../../docs/fase-llm/rag-moe.md).

Dia 1 ja concluido (checkpoint-40). Proximo dia (quando quiseres GPU):

```powershell
python -m friday_llm.training.incremental.cli --day 2 --add 15 --prefer-domain --train
```

## Regra

**Os documentos que defines mandam.** O ciclo treina esses docs no corpus cumulativo.
A ~1h é só um tecto confortável opcional — o dia pode acabar em 15–40 min.

## Fluxo diário

1. Decide N (ex.: `Dia 1: 10 documentos`).
2. Prepara + treina:

```powershell
$env:TRANSFORMERS_NO_TF = "1"; $env:USE_TF = "0"; $env:USE_TORCH = "1"
python -m friday_llm.training.incremental.cli --day 1 --add 10 --train
```

Ou só prepara e corre o script gerado:

```powershell
python -m friday_llm.training.incremental.cli --day 1 --add 10
.\scripts\cpt_day_1.ps1
# (wrapper → scripts\training\cpt_day_1.ps1)
```

3. Vê o progresso:

```powershell
python -m friday_llm.training.incremental.cli --status
# ou abre friday-llm/reports/incremental/progress.md
```

## O que a acumulação faz

| Peça | Caminho / regra |
|------|-----------------|
| Pool | `data/pretraining/cpt_fase1.jsonl` (~471 docs) |
| Cumulativo | `data/pretraining/incremental/corpus_cumulative.jsonl` |
| Manifesto | `data/pretraining/incremental/day_manifest.jsonl` |
| Adapter | `checkpoints/cpt-incremental/` (mesmo dir + resume) |
| Steps | `max(trainer_step, planned) + N×4` (mín. 20 por dia) |
| Progresso | `reports/incremental/progress.{json,md}` |

Dia N = todos os docs até hoje (10+15=25). Não se treina só o batch novo em cima de um adapter “esquecido” — o corpus cumulativo é rejogado e o `max_steps` sobe.

## Smoke (prova de infra)

```powershell
python -m friday_llm.training.incremental.cli --day 1 --add 10 --smoke --train
```

Usa Qwen2.5-0.5B. O alvo real é **Qwen2.5-7B QLoRA** (sem `--smoke`).

## Interromper / retomar

Podes Ctrl+C. No dia seguinte:

- Sem docs novos: corre de novo o mesmo `cpt_day_N.ps1` (resume até `max_steps`).
- Com docs novos: `--day N+1 --add M` (sobe `max_steps` e acrescenta ao cumulativo).

## Depois do CPT (quando houver docs suficientes)

Ver `AFTER_INCREMENTAL_SFT.md` e `scripts/incremental_after_cpt.ps1`:

1. Select best adapter de `cpt-incremental`
2. SFT Fase 4 apontando a esse adapter
3. Export / eval vs Phi-4
4. Troca **manual** de produção se o gate passar

## Fora de âmbito

- Encher a GPU até 60 min sem docs novos
- Substituir RAG
- Mudar Phi-4 automaticamente
