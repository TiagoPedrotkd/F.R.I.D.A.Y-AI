# Cutover modelo próprio

1. Treinar / seleccionar melhor adapter (`friday-llm/checkpoints/...`).
2. Export GGUF (`python -m friday_llm.export.cli ...`) se aplicável.
3. Carregar no LM Studio.
4. Definir `LM_STUDIO_MODEL` no `.env` para o novo id.
5. Smoke: `scripts/training/cutover_smoke.ps1`.
6. Rollback: repor `LM_STUDIO_MODEL=microsoft/phi-4` ([friday-llm/export/rollback.md](../../friday-llm/export/rollback.md)).

**Nunca** cutover automático sem gate de eval.
