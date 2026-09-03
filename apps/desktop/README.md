# F.R.I.D.A.Y. Desktop (Tauri 2)

Empacota [`apps/web`](../web) como app Windows. Browser continua para debug.

## Pré-requisitos

- Node 20+
- Rust (`rustup`)
- WebView2 (Windows 10/11)

## Dev

```powershell
# API
..\..\scripts\run-agent-api.ps1
# Vite
cd ..\web; npm run dev
# Tauri (outro terminal)
cd ..\desktop
$env:VITE_AGENT_API_BASE="http://127.0.0.1:8090"
npm install
npm run tauri dev
```

## Build

```powershell
cd apps\desktop
npm install
npm run tauri build
```

Instalador em `src-tauri/target/release/bundle/`.
