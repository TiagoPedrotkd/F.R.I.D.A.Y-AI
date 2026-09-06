# Contributing — F.R.I.D.A.Y-AI

Obrigado por contribuir. Setup inicial: [SETUP.md](../SETUP.md).

## Fluxo rápido

1. Branch a partir de `main` (ou branch de feature activa): `git checkout -b feat/descricao-curta`
2. Código + testes
3. `cd apps/web && npm run lint && npm test` (UI)
4. Commit — Husky corre Prettier/ESLint nos ficheiros staged
5. Push + PR com resumo e plano de teste

## Onde pôr código

| Área | Pasta |
|------|--------|
| UI React | `apps/web/src/` — ver [FOLDER_STRUCTURE](../apps/web/docs/FOLDER_STRUCTURE.md) |
| API / skills runtime | `friday/`, `services/agent-api/` |
| Docs de fase | `docs/fase-*` |
| Decisões | `docs/ADRs/` (novo ADR se mudar arquitectura) |

**Frontend:** feature-first (`features/chat`, etc.), alias `@/`, UI sem domínio em `ui/` quando extrair.

## Qualidade

- **Lint/format web:** `npm run lint` / `npm run format` em `apps/web`
- **Testes web:** Vitest — `npm test`; coverage: `npm run test:coverage`
- **Não** fazer force-push a `main`
- Não commitar secrets (`.env`, PEMs, `data/secrets/`)

## Checklist de PR

- [ ] SETUP local funciona / mudanças testadas
- [ ] Lint verde em `apps/web` se tocaste TS/TSX
- [ ] Testes novos ou actualizados quando há lógica
- [ ] Docs actualizados se mudaste contratos/API ou pastas
- [ ] Sem reformatação massiva não relacionada

## Commits

Mensagens curtas em PT ou EN, focadas no *porquê*. Exemplos:

- `feat(web): lazy-load FinancasPanel`
- `fix(api): timeout status probe`
- `docs: add SETUP 30min onboarding`

## CI

PRs que tocam `apps/web` devem passar em `.github/workflows/web-ci.yml` (lint, test, build).
