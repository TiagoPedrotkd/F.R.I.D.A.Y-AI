# Cutover modelo próprio

**Pré-requisito de produto:** não fazer cutover enquanto o chat SSE / escala frontend estiver a mudar — bisect fica confuso. Prod continua `microsoft/phi-4` até o gate abaixo. Vaultwarden (Fase 6) e coder LLM (Fase 7) são architecture-only e só avançam depois do stream estável + necessidade real.

1. Treinar / seleccionar melhor adapter (`friday-llm/checkpoints/...`).
2. Export GGUF (`python -m friday_llm.export.cli ...`) se aplicável.
3. Carregar no LM Studio.
4. Definir `LM_STUDIO_MODEL` no `.env` para o novo id.
5. Smoke: `scripts/training/cutover_smoke.ps1`.
6. Rollback: repor `LM_STUDIO_MODEL=microsoft/phi-4` ([friday-llm/export/rollback.md](../../friday-llm/export/rollback.md)).

**Nunca** cutover automático sem gate de eval.
