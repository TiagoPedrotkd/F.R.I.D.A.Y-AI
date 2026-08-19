# Decisões de Hardware — F.R.I.D.A.Y-AI

## Contexto

Orçamento inicial: **0€**. O PC Windows actual (`192.168.10.131`, GPU NVIDIA dedicada) actua como hub para todas as fases iniciais. Hardware adicional só quando houver orçamento.

## Hardware actual (0€)

| Componente | Uso | Estado |
|---|---|---|
| **PC Windows** (hub) | Docker, LM Studio, dev, orquestração | Activo — Fase 0 validada |
| **GPU NVIDIA dedicada** | LLM, Whisper, Frigate | Disponível |
| **Router VLAN-capable** | Segmentação IoT | Disponível — configurar antes Fase 3 |
| **Disco interno PC** | OS + modelos + gravações | Em uso |

### Papel do PC Windows

| Função | Detalhe |
|---|---|
| Desenvolvimento | Cursor, Git, Docker Desktop |
| LLM local | LM Studio (API OpenAI-compatible) |
| Inferência GPU | Modelos 7B–14B quantizados |
| Orquestração | Docker Compose |

O container Docker acede ao LM Studio via `host.docker.internal:1234`.

### Regra de carga

Serviços pesados (LM Studio, Frigate, Whisper) **só arrancam após confirmação no login** — ver [`scripts/friday-start.ps1`](../../scripts/friday-start.ps1).

---

## Roadmap de compras (por ordem de impacto)

| Prioridade | Produto | Preço ref. | Fase | Porquê |
|---|---|---|---|---|
| **P1** | SSD 1TB NVMe (Samsung 990 Evo, WD SN770) | ~€60–80 | 3 | Gravações Frigate + backups; separar de OS |
| **P2** | Google Coral USB Accelerator | ~€60–90 | 3 | Detecção objectos Frigate sem sobrecarregar GPU |
| **P3** | Mini-PC Beelink EQ12 (N100, 16GB, 500GB) | ~€180–220 | 3+ | Hub 24/7: HA + Vaultwarden + Frigate; PC fica para dev/LLM |
| **P4** | Câmara IP PoE RTSP (Reolink RLC-810A, Dahua IPC) | ~€40–80/câm | 3 | Stream local; sem cloud; compatível Frigate |
| **P5** | Switch PoE managed (TP-Link Omada SG2008P/SG2210P) | ~€80–120 | 3 | VLAN por porta + PoE para câmaras |
| **P6** | Microfone USB (Fifine K669B, Blue Yeti) | ~€25–40 | 1 | STT local Whisper; sem cloud |
| **P7** | Raspberry Pi 5 (8GB) + SSD | ~€90 + €30 | 3 | Coordinator Zigbee/Z-Wave (SkyConnect) se IoT wireless |

**Não comprar agora:** VPS, NAS dedicado, wearables — incorporar quando souberes dispositivos concretos.

---

## Mapeamento hardware → fases

| Fase | Carga no PC | Hardware extra |
|---|---|---|
| 0–1 Voz + núcleo | LM Studio + Whisper + Piper (GPU) | Mic USB (P6) |
| 2 Produtividade | Leve (APIs HTTPS) | — |
| 3 Casa + câmaras | **Pesado** (Frigate + HA) | SSD (P1), Coral (P2), câmaras (P4), switch (P5) |
| 4 Saúde wearables | Leve (import local) | Depende do relógio |
| 5 Finanças | Leve (Open Banking) | — |
| 6 Passwords | Leve (Vaultwarden) | Mini-PC 24/7 (P3) se acesso sempre |
| 7 Código | LM Studio modelos coder | GPU actual |

---

## Opções avaliadas (referência)

| Opção | Specs | Custo | Prós | Contras |
|---|---|---|---|---|
| **A — Raspberry Pi 5 (8GB)** | ARM, 8GB | ~€90 | Baixo consumo | LLMs pesados limitados |
| **B — Mini-PC N100 (16GB)** | x86, 16GB | ~€200–300 | Frigate, HA, margem | Custo inicial |
| **C — VPS (Hetzner)** | Cloud | ~€5/mês | Sem hardware | Latência câmaras, privacidade |

**Recomendação futura:** Opção B (Beelink EQ12) como hub 24/7 quando orçamento permitir.

---

## Checklist — Bootstrap Mini-PC (quando P3 chegar)

- [ ] Instalar Ubuntu Server 24.04 LTS
- [ ] SSH com chave (desactivar password login)
- [ ] Docker Engine + Compose plugin
- [ ] Clonar repo FRIDAY-AI
- [ ] Transferir `.env` de forma segura (SCP/USB — nunca Git)
- [ ] Migrar Frigate + HA + Vaultwarden para Mini-PC
- [ ] PC Windows fica para dev + LM Studio pesado
- [ ] IP fixo ou reserva DHCP
- [ ] Backup `.env` encriptado offline
- [ ] `docker compose up -d` e validar serviços

---

## Documentos relacionados

- [Arquitectura geral](../arquitectura/visao-geral.md)
- [Rede VLAN](../arquitectura/rede-vlan.md)
- [LM Studio setup](lm-studio-setup.md)
