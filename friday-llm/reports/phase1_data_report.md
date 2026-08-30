# Fase 1 — Relatório de Dados (FRIDAY LLM)

**Run:** `friday-fase1-data`  
**Gerado:** 2026-08-30T18:28:14.154721+00:00

## Orçamento

- Documentos CPT: **471** (máx. 500)
- Tokens CPT estimados: **357121** (máx. 2000000)

## Pipeline por estágio

| Estágio | Documentos |
|---------|------------|
| Raw (FineWeb) | 500 |
| Cleaned | 471 |
| Deduplicated | 471 |
| CPT final | 471 |

### Filtros de limpeza

```json
{
  "input_docs": 500,
  "kept": 471,
  "dropped": 29,
  "reasons": {
    "pii": 29,
    "truncated": 1
  }
}
```

- Exact dedupe dropped: 0
- MinHash dedupe dropped: 0

## Mix linguístico CPT

```json
{
  "languages": {
    "por": 332,
    "en": 139
  },
  "variants": {
    "pt-BR": 104,
    "pt-und": 224,
    "pt-PT": 4
  }
}
```

## Datasets

- CPT: `D:\Repositories\F.R.I.D.A.Y-AI\friday-llm\data\pretraining\cpt_fase1.jsonl`
- SFT train: `D:\Repositories\F.R.I.D.A.Y-AI\friday-llm\data\sft\fase1_sft_train.jsonl` (43 exemplos)
- SFT holdout: `D:\Repositories\F.R.I.D.A.Y-AI\friday-llm\data\sft\fase1_sft_holdout.jsonl` (7)
- RAG chunks: `D:\Repositories\F.R.I.D.A.Y-AI\friday-llm\data\rag\chunks.jsonl` (54 chunks)
- Eval (inalterado): `D:\Repositories\F.R.I.D.A.Y-AI\friday-llm\data\evaluation\friday_eval.jsonl`

## Validação eval

- Sem leak: **True**

## Avisos

- Este subset **não** representa conhecimento geral da web.
- O conjunto de avaliação **nunca** entra em CPT/SFT.
- `data/chroma/` e `data/news_cache/` estão excluídos.
- Phi-4 em produção permanece inalterado nesta fase.
