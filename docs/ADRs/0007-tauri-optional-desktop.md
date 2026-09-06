# ADR 0007 — Web first, Tauri opcional

## Context

Queremos UI rápida em browser durante o desenvolvimento, com opção desktop nativa depois.

## Decision

**`apps/web` (Vite/React)** é a app principal. **`apps/desktop` (Tauri)** é shell opcional; `platform/` abstrai links/audio/`VITE_AGENT_API_BASE`.

## Consequences

- DX: `npm run dev` + proxy Vite.
- Desktop precisa de base URL absoluta para a API.
- Não bloquear features web por APIs só-Tauri.
