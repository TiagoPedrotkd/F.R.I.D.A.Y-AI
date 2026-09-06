# ADR 0004 — Zustand + state machine

## Context

A UI precisa de um estado de sessão partilhado (mensagens, mic, TTS, painéis) e de transições válidas (idle → listening → thinking → …).

## Decision

- **Zustand** (`state/store.ts`) como store único da app.
- **Machine** explícita (`state/machine.ts` + `ALLOWED`) para transições; `transition()` rejeita arestas ilegais.

## Consequences

- Testes de machine table-driven; UI (FridayCore) deriva labels do estado.
- Store grande (~1k LOC) — fatias por domínio ficam para fase futura.
- Evita Redux Toolkit / React Query nesta fase (fetch local via client + hooks pontuais).
