# Decisões de Hardware — Fase 0

## Contexto

A Fase 0 corre na **máquina Windows atual** como ambiente de desenvolvimento. O deploy num host dedicado fica para quando o hardware final estiver disponível.

## Opções avaliadas

| Opção | Specs | Custo | Prós | Contras |
|---|---|---|---|---|
| **A — Raspberry Pi 5 (8GB)** | ARM, 8GB RAM | ~€90 | Baixo consumo, silencioso | LLMs locais pesados limitados |
| **B — Mini-PC (Intel N100, 16GB)** | x86, 16GB RAM | ~€200–300 | Margem para crescer, Frigate/câmaras | Custo inicial maior |
| **C — VPS (Hetzner, etc.)** | Cloud, variável | ~€5/mês | Sem hardware local | Latência câmaras, menos privacidade |

## Recomendação para deploy futuro

**Opção B — Mini-PC Intel N100 (16GB RAM)** para quem leva o projeto a sério a médio prazo.

Justificação:

- Suporta LM Studio com modelos maiores
- Margem para Frigate (processamento de vídeo) na Fase 3
- x86 compatível com ecossistema Docker mainstream
- Consumo razoável para servidor 24/7 caseiro

## Papel do Windows (Fase 0)

| Função | Detalhe |
|---|---|
| Desenvolvimento | Cursor, Git, Docker Desktop |
| LLM local | LM Studio corre no host Windows |
| Testes | `docker compose up` + acesso LAN |

O container Docker acede ao LM Studio via `host.docker.internal:1234`.

## Checklist — Bootstrap do host final

Quando o Mini-PC/VPS estiver disponível:

- [ ] Instalar OS (Ubuntu Server 24.04 LTS recomendado)
- [ ] Configurar acesso SSH com chave (desativar password login)
- [ ] Instalar Docker Engine + Docker Compose plugin
- [ ] Clonar repo: `git clone https://github.com/TiagoPedrotkd/F.R.I.D.A.Y-AI.git`
- [ ] Transferir `.env` de forma segura (SCP/USB — nunca via Git)
- [ ] Se LM Studio local no host: instalar e carregar modelo
- [ ] `docker compose up -d` e validar `/health/llm`
- [ ] Configurar arranque automático (systemd ou `restart: unless-stopped`)
- [ ] IP fixo ou reserva DHCP no router
- [ ] Backup do `.env` encriptado offline
