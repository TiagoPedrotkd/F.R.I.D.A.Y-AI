# ADR 0003 — Frontend feature folders + alias `@/`

## Context

`apps/web/src/components` cresceu flat; imports relativos profundos e ficheiros >200 LOC dificultam manutenção.

## Decision

Adoptar **feature-first** (`src/features/<domain>/`), alias Vite/TS `@/` → `src/`, limites de LOC documentados em `apps/web/docs/FOLDER_STRUCTURE.md`. Piloto: `features/chat`.

## Consequences

- Migração incremental (não big-bang).
- Painéis grandes (Finanças) devem partir em `sections/`.
- Novos ecrãs não devem ir para o flat `components/` legado.
