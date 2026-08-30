# Fase 0 — Relatório de auditoria F.R.I.D.A.Y. LLM

**Data:** 2026-08-29  
**Estado:** aprovado via implementação do plano piloto.

## Hardware

| Recurso | Valor |
|---------|--------|
| OS | Windows 10.0.26200 |
| CPU | Intel Core i7-14700KF (20C/28T) |
| RAM | ~32 GB |
| GPU | NVIDIA GeForce RTX 3060, 12288 MiB |
| Driver | 610.62 (CUDA UMD 13.3) |
| Disco livre | C ~342 GB · D ~1346 GB |
| Python | 3.11 (.venv) |

## Modelo / integração actual

- `LM_STUDIO_MODEL=microsoft/phi-4`
- Cliente OpenAI-compatible → `http://localhost:1234/v1`
- Tools: OpenAI function calling + JSON fallback + intent router
- Memória Chroma ≠ RAG documental

## Estratégia escolhida

| Item | Escolha |
|------|---------|
| Base CPT | `Qwen/Qwen2.5-7B` (Base) |
| Smoke infra (opcional mais leve) | `Qwen/Qwen2.5-0.5B` se 7B download for bloqueado |
| Método | QLoRA local |
| Corpus piloto | FineWeb2-HQ subset + SFT curado (tools reais) |
| Cloud | Não no piloto |
| Produção | Phi-4 permanece default até troca configurável |

## Limitações

- QLoRA + subset pequeno ≠ LLM de conhecimento geral.
- FineWeb ≠ tempo real; factos actuais via tools/RAG.
- Não redistribuir pesos sem rever licenças do corpus.
