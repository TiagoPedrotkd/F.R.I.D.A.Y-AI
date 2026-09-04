# RAG, GraphRAG leve, LoRA e Agentes

Comparativo alinhado à FRIDAY (Chroma + Phi-4 em produção).

| Técnica | Objectivo | Na FRIDAY | Custo | Actualização |
|---------|----------|-----------|-------|--------------|
| **RAG** | Factos / manuais | `search_docs` + `data/rag_chroma` | Baixo | Instantânea (re-ingest) |
| **GraphRAG leve** | Relacoes | `search_knowledge_graph` + `data/rag_graph` | Baixo | Após rebuild KG |
| **QLoRA / SFT** | Tom, formato, tool-use | CPT base + SFT behavior / specialists | Médio (GPU) | Periodica |
| **Agentes / CoT** | Logica | Prompt v8 + reflect no `tool_runner` | Baixo | Constante |

## Regra de ouro

- **Factos mutaveis** → RAG (nao CPT).
- **Relacoes / arquitectura** → grafo leve.
- **Comportamento** → SFT / LoRA (nao injectar manuais nos pesos).
- **Raciocinio** → prompt + reflect; hedges se reflect falhar.

## Comandos

```powershell
# Re-index RAG
python -m friday_llm.rag.cli --config friday-llm/configs/fase5_rag.yaml

# Rebuild grafo
python -m friday_llm.rag.build_kg

# CPT dia N (base; prefer-domain)
python -m friday_llm.training.incremental.cli --day 2 --add 15 --prefer-domain --train
```

Ver tambem: [domain-packs.md](domain-packs.md), [INCREMENTAL_TRAINER.md](../../friday-llm/docs/INCREMENTAL_TRAINER.md).
