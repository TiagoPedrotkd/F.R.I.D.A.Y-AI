# Checklist de Conclusão — Fase 0

Marca cada item quando validado.

## Critérios do documento de planeamento

- [ ] **Docker Compose** — `docker compose up -d` sobe sem erros
- [ ] **Docker Compose** — `docker compose down` para e limpa sem erros
- [ ] **API LLM** — `GET /health/llm` devolve 200 com resposta do LM Studio
- [ ] **Git + secrets** — `.env` ignorado; nenhum secret no repo
- [ ] **Documentação** — README + `docs/fase-0/` permitem reproduzir o setup

## Entregável Hello World

- [ ] LM Studio instalado e Local Server activo na porta 1234
- [ ] `http://localhost:1234/v1/models` responde no host Windows
- [ ] `.env` criado a partir de `.env.example` com modelo correcto
- [ ] Container `friday-healthcheck` healthy no Docker
- [ ] `http://localhost:8080/health` → 200 JSON
- [ ] `http://localhost:8080/health/llm` → 200 JSON com `llm.ok: true`
- [ ] Acesso LAN funcional de outro dispositivo (opcional mas recomendado)

## Componentes da Fase 0

### Hardware
- [ ] Decisão documentada em [decisoes-hardware.md](decisoes-hardware.md)
- [ ] Checklist bootstrap host final definido

### Containerização
- [ ] `docker-compose.yml` válido (`docker compose config`)
- [ ] Serviço healthcheck com `/health` e `/health/llm`
- [ ] Healthcheck Docker (container healthy)

### Secrets
- [ ] `.gitignore` reforçado
- [ ] `.env.example` versionado
- [ ] Política em [gestao-secrets.md](gestao-secrets.md)

### Git
- [ ] Estrutura `services/` e `docs/fase-0/` versionada
- [ ] Convenções em [README.md](README.md)

### Rede
- [ ] [rede-local.md](rede-local.md) com IP, porta e firewall
- [ ] *(Opcional)* Plano VLAN IoT para Fase 3

### LLM
- [ ] [lm-studio-setup.md](lm-studio-setup.md) completo
- [ ] Integração OpenAI-compatible funcional
- [ ] [contas-api.md](contas-api.md) preparatório Fase 1

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
| Concluída em | _preencher_ |
| Validado por | _preencher_ |
| Notas | _preencher_ |
