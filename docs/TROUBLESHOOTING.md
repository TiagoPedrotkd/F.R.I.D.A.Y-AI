# Troubleshooting — F.R.I.D.A.Y-AI

Problemas frequentes no dia-a-dia. Setup base: [SETUP.md](../SETUP.md).

## API / UI

### UI: “API sem resposta (timeout)”

- Confirma `.\scripts\run-agent-api.ps1` a correr em `:8090`
- `curl http://127.0.0.1:8090/health` — se falhar, a UI vai a demo/timeout
- Segundo processo na mesma porta → erro de bind; mata o PID antigo
- Status lento: HA probe / healthchecks mortos — ver logs da API

### Porta 5173 ou 8090 ocupada

```powershell
netstat -ano | findstr :8090
netstat -ano | findstr :5173
# Task Manager → finaliza PID, ou: Stop-Process -Id <pid>
```

### Vite proxy / CORS

Em browser, a UI usa proxy Vite `/v1` → `8090`. Em Tauri, `VITE_AGENT_API_BASE` ou default `http://127.0.0.1:8090`.

### Chat sem LLM

LM Studio Local Server em `:1234`, modelo carregado, `LM_STUDIO_MODEL` no `.env` **exacto**. Sem isso a app pode cair em modo demo.

## Finanças

### Open Banking / GoCardless / Enable Banking

**Removido.** Finanças são ledger local (`friday/integrations/finance_ledger.py`). Não configures `ENABLE_BANKING_*`.

### 404 em `/v1/finance/*`

Reinicia a agent-api após pull — rotas novas só existem no processo actualizado.

## Frontend / tooling

### Husky não corre no commit (Windows)

```powershell
cd <repo-root>
npm install
npx husky
git config core.hooksPath .husky
```

PowerShell execution policy: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` se scripts `.ps1` forem bloqueados.

### ESLint / Prettier discordam

Prettier manda no estilo; `eslint-config-prettier` desliga regras de estilo do ESLint. Corre `npm run format` em `apps/web`.

### Erro Zod “Resposta inválida do servidor”

O cliente valida JSON com schemas em `apps/web/src/api/schemas.ts`. A API pode ter mudado o shape — alinha schema ou corrige o backend. Ver [ADR 0005](ADRs/0005-zod-api-validation.md).

### Storybook

```powershell
cd apps\web
npm run storybook
```

Se falhar o alias `@/`, confirma `.storybook/main.ts` `viteFinal` alias.

### Testes: `scrollIntoView is not a function`

Já polyfillado em `apps/web/src/test/setup.ts`. Se voltares a ver o erro, garante que o setupFile do Vitest está activo.

## Python

### `ModuleNotFoundError: friday`

Activa o venv e instala o pacote editável (`pip install -e .`) a partir da raiz.

### Pytest falha só em finanças

Dados em `data/integrations/finance/` — testes usam fixtures; não depends de Open Banking.
