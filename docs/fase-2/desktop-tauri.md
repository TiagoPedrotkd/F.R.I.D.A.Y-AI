# Desktop Tauri — Fase 2

Plano detalhado (origem Fase 1): ver também [../fase-1/desktop-tauri.md](../fase-1/desktop-tauri.md).

## Localização

Scaffold: [`apps/desktop`](../../apps/desktop)

## Desenvolvimento

```powershell
# Terminal A — API
.\scripts\run-agent-api.ps1
# Terminal B — Vite (ou usar build servido pelo Tauri)
cd apps\web; npm run dev
# Terminal C — Tauri
cd apps\desktop; npm run tauri dev
```

`VITE_AGENT_API_BASE=http://127.0.0.1:8090` no ambiente desktop.

## Build instalador

```powershell
cd apps\desktop
npm run tauri build
```

Gera instalador NSIS/MSI sob `apps/desktop/src-tauri/target/release/bundle/`.

## Sidecar

O arranque do `agent-api` faz-se via script host (`scripts/run-agent-api.ps1`) — **sem secrets no bundle**. A UI mostra estado via `/v1/status`.
