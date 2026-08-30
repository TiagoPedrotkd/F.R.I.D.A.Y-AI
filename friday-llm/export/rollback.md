# Rollback — modelo de produção

## Política

O repositório **nunca** altera automaticamente `LM_STUDIO_MODEL` no `.env`.
A produção permanece em `microsoft/phi-4` até troca manual e reversível.

## Repor Phi-4 (produção)

```powershell
# Sessão actual
Remove-Item Env:LM_STUDIO_MODEL -ErrorAction SilentlyContinue
$env:LM_STUDIO_MODEL = "microsoft/phi-4"

# Ou no .env (editar manualmente)
# LM_STUDIO_MODEL=microsoft/phi-4
```

## Checklist após rollback

1. **LM Studio** — carregar `microsoft/phi-4` (ou modelo de produção habitual).
2. **Agente voz** — `friday-voice` ou web UI: pedir hora/notícias; confirmar resposta.
3. **Eval baseline** — `python -m friday_llm.evaluation.run_baseline` deve usar Phi-4.
4. **RAG** — `search_docs` continua disponível (independente do modelo LLM).

## Testar modelo exportado (temporário)

```powershell
$env:LM_STUDIO_MODEL = "<model-id-do-gguf-no-lm-studio>"
python -m friday_llm.evaluation.run_baseline --out friday-llm/reports/phase6_eval_final.json
```

## Artefactos a manter

- `friday-llm/export/gguf/*.gguf` — não apagar; útil para re-teste.
- `friday-llm/reports/export_manifest.json` — hashes e rollback metadata.
- `friday-llm/export/merged-friday-v1/` — HF fundido (regenerável via `export.cli --only merge`).

## Referências

- Guia LM Studio: [`lm_studio_guide.md`](lm_studio_guide.md)
- Pipeline export: [`README.md`](README.md)
