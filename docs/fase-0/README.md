# Fase 0 — Fundações e Ambiente de Desenvolvimento

Documentação interna da Fase 0 do projeto F.R.I.D.A.Y-AI.

## Índice

| Documento | Descrição |
|---|---|
| [decisoes-hardware.md](decisoes-hardware.md) | Escolha de hardware e bootstrap do host final |
| [gestao-secrets.md](gestao-secrets.md) | Política de secrets, rotação e resposta a leaks |
| [lm-studio-setup.md](lm-studio-setup.md) | Instalação e configuração do LM Studio |
| [rede-local.md](rede-local.md) | Acesso ao serviço na LAN e firewall |
| [contas-api.md](contas-api.md) | APIs cloud (preparatório Fase 1) |
| [checklist-conclusao.md](checklist-conclusao.md) | Critérios de fecho da Fase 0 |

## Convenções Git

### Branches

- `main` — código estável, sempre deployável
- `feature/<nome>` — trabalho em curso (ex.: `feature/fase-1-orchestrator`)

### Commits

Formato sugerido: `<tipo>: <descrição curta>`

Tipos: `feat`, `fix`, `docs`, `chore`, `refactor`

Exemplo: `feat: add healthcheck LLM endpoint`

### O que entra no repo

- Código fonte, Dockerfiles, `docker-compose.yml`
- Documentação (`docs/`)
- `.env.example` (placeholders apenas)

### O que NÃO entra no repo

- `.env` com valores reais
- API keys, certificados, tokens
- Dados pessoais ou dumps de configuração local
