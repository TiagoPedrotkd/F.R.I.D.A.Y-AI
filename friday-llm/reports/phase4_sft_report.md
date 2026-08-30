# Fase 4 — Relatório SFT (FRIDAY LLM)

**Run:** `friday-fase4-sft`  
**Gerado:** 2026-08-29T22:06:25.552340+00:00

## Dataset

- Train: **51** | Holdout: **10**
- Categorias: `{"tool_calling": 39, "honesty": 3, "safety": 6, "rag": 3, "voice_style": 4, "clarify": 1, "conversation": 2, "personality": 3}`
- Eval leak dropped: 0

- Aprovado: **True**
- Hash: `f0c2af183417e637…`

## Treino SFT


## Avaliação vs baseline

| Métrica | Phi-4 baseline | Pós-SFT | Delta |
|---------|----------------|---------|-------|
| pass_rate | 0.467 | — | — |
| tool_call_rate | 0.0 | — | — |

### Por categoria (baseline)

```json
{
  "clarify": {
    "n": 1,
    "passed": 1,
    "pass_rate": 1.0,
    "tool_call_rate": null
  },
  "coding": {
    "n": 1,
    "passed": 1,
    "pass_rate": 1.0,
    "tool_call_rate": null
  },
  "english": {
    "n": 1,
    "passed": 1,
    "pass_rate": 1.0,
    "tool_call_rate": null
  },
  "honesty": {
    "n": 1,
    "passed": 0,
    "pass_rate": 0.0,
    "tool_call_rate": null
  },
  "rag": {
    "n": 1,
    "passed": 1,
    "pass_rate": 1.0,
    "tool_call_rate": null
  },
  "safety": {
    "n": 2,
    "passed": 2,
    "pass_rate": 1.0,
    "tool_call_rate": null
  },
  "tool_calling": {
    "n": 5,
    "passed": 0,
    "pass_rate": 0.0,
    "tool_call_rate": null
  },
  "unknown": {
    "n": 2,
    "passed": 0,
    "pass_rate": 0.0,
    "tool_call_rate": null
  },
  "voice_style": {
    "n": 1,
    "passed": 1,
    "pass_rate": 1.0,
    "tool_call_rate": null
  }
}
```

### Por categoria (pós-SFT)

```json
{}
```

## Avisos

- Dataset curado ≠ comportamento completo de produção.
- Phi-4 em produção permanece inalterado.
