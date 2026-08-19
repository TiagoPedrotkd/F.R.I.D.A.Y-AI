# Checklist de Conclusão — Fase 0

Marca cada item quando validado.

## Critérios do documento de planeamento

- [x] **Docker Compose** — `docker compose up -d` sobe sem erros
- [x] **Docker Compose** — `docker compose down` para e limpa sem erros
- [x] **API LLM** — `GET /health/llm` devolve 200 com resposta do LM Studio
- [x] **Git + secrets** — `.env` ignorado; nenhum secret no repo
- [x] **Documentação** — README + `docs/fase-0/` permitem reproduzir o setup

## Entregável Hello World

- [x] LM Studio instalado e Local Server activo na porta 1234
- [x] `http://localhost:1234/v1/models` responde no host Windows
- [x] `.env` criado a partir de `.env.example` com modelo correcto
- [x] Container `friday-healthcheck` healthy no Docker
- [x] `http://localhost:8080/health` → 200 JSON
- [x] `http://localhost:8080/health/llm` → 200 JSON com `llm.ok: true`
- [x] Acesso LAN funcional de outro dispositivo (telemóvel na rede Main)

## Componentes da Fase 0

### Hardware
- [x] Decisão documentada em [decisoes-hardware.md](decisoes-hardware.md)
- [x] Checklist bootstrap host final definido

### Containerização
- [x] `docker-compose.yml` válido (`docker compose config`)
- [x] Serviço healthcheck com `/health` e `/health/llm`
- [x] Healthcheck Docker (container healthy)

### Secrets
- [x] `.gitignore` reforçado
- [x] `.env.example` versionado
- [x] Política em [gestao-secrets.md](gestao-secrets.md)

### Git
- [x] Estrutura `services/` e `docs/fase-0/` versionada
- [x] Convenções em [README.md](README.md)

### Rede
- [x] [rede-local.md](rede-local.md) com IP, porta e firewall
- [x] IoT isolado via Guest Network Cudy — [rede-vlan-cudy-wr11000.md](../arquitectura/rede-vlan-cudy-wr11000.md)

### LLM
- [x] [lm-studio-setup.md](lm-studio-setup.md) completo
- [x] Integração OpenAI-compatible funcional
- [x] [contas-api.md](contas-api.md) preparatório Fase 1

### Arranque condicional
- [x] [friday-start.ps1](../../scripts/friday-start.ps1) com auto-detect LM Studio
- [x] [register-startup-task.ps1](../../scripts/register-startup-task.ps1) — Task Scheduler `FRIDAY-AI-Startup`
- [x] Config local opcional: [friday-config.ps1.example](../../scripts/friday-config.ps1.example)

## Comandos de validação rápida

```powershell
# Na raiz do repo
docker compose config
docker compose up -d --build
curl http://localhost:8080/health
curl http://localhost:8080/health/llm
docker compose down
git check-ignore -v .env
```

## Data de conclusão

| Campo | Valor |
|---|---|
| Concluída em | 2026-08-19 |
| Validado por | Tiago Pedro |
| Notas | Hello World LAN validado no telemóvel (Main OK, Guest bloqueado). Firewall Windows regra FRIDAY-Healthcheck. IoT via Guest Network Cudy WR11000. |
