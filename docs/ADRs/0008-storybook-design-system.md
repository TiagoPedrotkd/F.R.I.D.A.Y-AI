# ADR 0008 — Storybook para o design system HUD

## Context

Tokens em CSS e ~24 componentes sem playground; onboarding visual lento.

## Decision

Documentar o HUD com **Storybook 8 + Vite**, tokens tipados em `system.ts`, e Markdown (`DESIGN_SYSTEM.md`, `COMPONENTS.md`). Stories cobrem primitivos + componentes representativos (não 100% cobertura).

## Consequences

- `npm run storybook` em `apps/web`.
- Theming dark/light/HC via toolbar + `applyTheme`.
- Chromatic / visual regression fora de âmbito por agora.
