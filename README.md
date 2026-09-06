# F.R.I.D.A.Y-AI

Assistente Pessoal Inteligente — monorepo (agente local + treino LLM opcional).

## Onboarding (30 min)

**Novo no repo?** Segue [SETUP.md](SETUP.md) — do `git clone` à UI em http://127.0.0.1:5173.

```powershell
.\scripts\setup.ps1
.\scripts\run-agent-api.ps1   # terminal 1
.\scripts\run-web-ui.ps1      # terminal 2
```

Contribuir: [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) · Problemas: [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) · ADRs: [docs/ADRs/](docs/ADRs/)

## Mapa rápido

| Área | Onde |
|------|------|
| Layout do monorepo | [docs/REPO_LAYOUT.md](docs/REPO_LAYOUT.md) |
| Docs | [docs/README.md](docs/README.md) · [docs/fase-3/](docs/fase-3/) casa inteligente |

| Runtime | `friday/` + `services/agent-api` + `apps/web` |
| Treino | `friday-llm/` · [docs/fase-llm/](docs/fase-llm/) |
| Scripts | `scripts/run`, `acceptance`, `training`, `ops` |

Produção LLM: **Phi-4** via LM Studio até cutover manual.

## Fase 0 — Quick Start

Entregável: container Docker na rede local que valida conectividade com **LM Studio** (LLM local).

### Pré-requisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows)
- [LM Studio](https://lmstudio.ai) com Local Server activo na porta 1234

### Setup

```powershell
git clone https://github.com/TiagoPedrotkd/F.R.I.D.A.Y-AI.git
cd F.R.I.D.A.Y-AI
copy .env.example .env
# Editar .env — definir LM_STUDIO_MODEL com o nome exacto do modelo carregado
docker compose up -d --build
```

Guia detalhado do LM Studio: [docs/fase-0/lm-studio-setup.md](docs/fase-0/lm-studio-setup.md)

### Validar

```powershell
curl http://localhost:8080/health
curl http://localhost:8080/health/llm
```

- `/health` → serviço OK
- `/health/llm` → 200 com `llm.ok: true` se LM Studio estiver activo

### Parar

```powershell
docker compose down
```

## Documentação Fase 0

| Documento | Conteúdo |
|---|---|
| [docs/fase-0/README.md](docs/fase-0/README.md) | Índice e convenções Git |
| [docs/fase-0/lm-studio-setup.md](docs/fase-0/lm-studio-setup.md) | Instalação LM Studio |
| [docs/fase-0/gestao-secrets.md](docs/fase-0/gestao-secrets.md) | Política de secrets |
| [docs/fase-0/rede-local.md](docs/fase-0/rede-local.md) | Acesso LAN e firewall |
| [docs/fase-0/checklist-conclusao.md](docs/fase-0/checklist-conclusao.md) | Critérios de fecho |

## Arquitectura (Fase 0)

```
[Dispositivo LAN] → :8080/health/llm → [Docker: healthcheck] → host.docker.internal:1234 → [LM Studio @ 192.168.10.131]
```

LM Studio corre neste PC (IP LAN `192.168.10.131`). O container usa `host.docker.internal` para o alcançar.

## Arquitectura

Documentação completa em [`docs/arquitectura/`](docs/arquitectura/visao-geral.md):

- [Visão geral](docs/arquitectura/visao-geral.md) — fases, software, SPOFs
- [Rede VLAN](docs/arquitectura/rede-vlan.md) — topologia IoT (configurar antes da Fase 3)
- [Hardware](docs/fase-0/decisoes-hardware.md) — roadmap de compras P1–P7

## Arranque condicional

No login, o FRIDAY pergunta se queres iniciar serviços. Instalação:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\register-startup-task.ps1
```

Ver [`scripts/README.md`](scripts/README.md).

## Licença

Ver [LICENSE](LICENSE).
