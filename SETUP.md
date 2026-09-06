# Setup em ~30 minutos — F.R.I.D.A.Y-AI

Do `git clone` até a UI a falar com a API. Guia Windows-first; WSL/macOS: `scripts/setup.sh`.

## Pré-requisitos

| Ferramenta | Versão | Notas |
|------------|--------|--------|
| Node.js | **20+** | [nodejs.org](https://nodejs.org) |
| npm | 10+ | vem com Node |
| Python | **3.11+** | agent-api / `friday` |
| Git | 2.x | |
| LM Studio | latest | Local Server `:1234` (opcional no 1º arranque, necessário para chat real) |

Opcional: Docker Desktop (só Fase 0 healthcheck).

## Passo a passo (30 min)

### 1. Clonar (2 min)

```powershell
git clone https://github.com/TiagoPedrotkd/F.R.I.D.A.Y-AI.git
cd F.R.I.D.A.Y-AI
```

### 2. Setup automático (5–10 min)

```powershell
.\scripts\setup.ps1
```

Isto instala deps da raiz (Husky) + `apps/web`, copia `.env` se faltar, activa git hooks.

WSL/macOS:

```bash
chmod +x scripts/setup.sh && ./scripts/setup.sh
```

### 3. Ambiente Python da API (5–10 min)

Na raiz do repo (ajusta ao teu fluxo local se já tiveres venv):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
# ou o requirements indicado em docs/REPO_LAYOUT.md / pyproject.toml
```

Edita `.env`: define `LM_STUDIO_MODEL` com o nome exacto do modelo no LM Studio.

### 4. Arrancar (5 min)

**Terminal A — API (`:8090`):**

```powershell
.\scripts\run-agent-api.ps1
```

**Terminal B — Web (`:5173`):**

```powershell
.\scripts\run-web-ui.ps1
```

Abre http://127.0.0.1:5173

### 5. Validar (2 min)

```powershell
curl http://127.0.0.1:8090/health
# UI: estado API/LM no header (ConnectionStatus)
```

## Onde está o quê

| Queres… | Vai a… |
|---------|--------|
| Layout pastas | [docs/REPO_LAYOUT.md](docs/REPO_LAYOUT.md) |
| Contribuir / PR | [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) |
| Erros comuns | [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) |
| Decisões de arquitectura | [docs/ADRs/](docs/ADRs/) |
| Design system UI | [apps/web/docs/DESIGN_SYSTEM.md](apps/web/docs/DESIGN_SYSTEM.md) |
| Pastas frontend | [apps/web/docs/FOLDER_STRUCTURE.md](apps/web/docs/FOLDER_STRUCTURE.md) |

## Comandos úteis (web)

```powershell
cd apps\web
npm run dev
npm test
npm run lint
npm run format
npm run storybook
```

## Git hooks

No `git commit`, Husky corre `lint-staged` (Prettier + ESLint só nos ficheiros staged em `apps/web`).  
Se o hook não correr: `npx husky` na raiz (ver TROUBLESHOOTING).
