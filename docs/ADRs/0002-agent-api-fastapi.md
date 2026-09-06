# ADR 0002 — FastAPI agent-api como gateway

## Context

O runtime Python (`friday/`) precisa de uma superfície HTTP para a UI (chat SSE, prefs, integrações, finanças).

## Decision

Expor **`services/agent-api`** (FastAPI) em `:8090` como único gateway da UI. Skills, memória e integrações ficam em `friday/`; a API orquestra.

## Consequences

- UI não importa Python directamente; contratos REST/SSE versionados sob `/v1`.
- Reinício da API é necessário após mudanças de rotas.
- Scripts `run-agent-api.ps1` são o caminho canónico de arranque.
