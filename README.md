# F.R.I.D.A.Y-AI

Assistente Pessoal Inteligente — projecto modular em 9 fases (0–8).

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

## Licença

Ver [LICENSE](LICENSE).
