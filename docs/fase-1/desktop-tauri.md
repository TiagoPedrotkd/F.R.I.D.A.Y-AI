# Desktop Tauri — Fase 2

> Implementação e scaffold: ver [../fase-2/desktop-tauri.md](../fase-2/desktop-tauri.md) e `apps/desktop/`.

## Objectivo

Empacotar a mesma UI (`apps/web`) como app desktop Windows “F.R.I.D.A.Y.” com Tauri 2, mantendo `apps/web` para diagnóstico no browser.

## Passos previstos

1. **Scaffold** `apps/desktop` (Tauri 2) com `frontendDist` / `devUrl` apontando para o build / Vite de `apps/web`.
2. **Adapters** em `apps/web/src/platform/`:
   - `links.ts` → `@tauri-apps/plugin-shell` `open`
   - `storage.ts` → opcional plugin store (ou manter localStorage)
   - `audio.ts` → mic nativo se necessário; senão WebView MediaRecorder
   - `config.ts` → `VITE_AGENT_API_BASE` / default `http://127.0.0.1:8090` no Tauri
3. **Sidecar / serviços locais**: documentar arranque do `agent-api` (e opcionalmente healthcheck) via script host ou sidecar Tauri — **sem secrets no bundle**.
4. **Detecção LM Studio / API**: ecrã “ligar serviços” que corre scripts do host e reflecte `/v1/status`.
5. **Branding**: ícone + nome “F.R.I.D.A.Y.”; permissões de mic / rede local.
6. **Installer**: MSI ou NSIS via `tauri build` (documentar target Windows).
7. Manter browser UI para debug; desktop como distribuição.

## Fora de âmbito até Fase 2

- Publicar instalador na Fase 1.
- Ligação browser→MCP.
- Substituir o CLI `friday-voice`.
