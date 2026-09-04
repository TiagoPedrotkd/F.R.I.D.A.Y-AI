# Fase 3 — Casa inteligente + câmaras

**Estado:** fundação 3.0 (docs + Mosquitto + Home Assistant + skills read-only).  
Frigate com câmaras RTSP reais = Fase 3.1 (quando houver hardware).

## Objectivo

Hub local: Home Assistant + MQTT; vídeo 100% local via Frigate (futuro).  
**Sem** treino LLM, Open Banking, ou exposição à internet.

## Documentos

| Doc | Conteúdo |
|------|----------|
| [checklist-conclusao.md](checklist-conclusao.md) | Gates código vs live |
| [home-assistant.md](home-assistant.md) | HA Docker + token + skills |
| [mqtt.md](mqtt.md) | Mosquitto |
| [frigate.md](frigate.md) | Profile Frigate (stub até câmaras) |
| [skills-contract.md](skills-contract.md) | Skills HA read-only |

## Ordem (hoje)

1. `docker compose --profile mqtt --profile homeassistant up -d`
2. Criar long-lived token no HA → `.env` (`HA_TOKEN`, `HA_ENABLED=true`)
3. Reiniciar agent-api; perguntar “estado da casa”
4. `.\scripts\fase3_acceptance.ps1`

## Rede

Câmaras / IoT no Guest ou VLAN IoT (já parcial no Cudy); hub na Main (`192.168.10.131`).  
Ver [checklist-vlan.md](../arquitectura/checklist-vlan.md).

## Fora de âmbito (3.0)

- Câmaras físicas / Coral / SSD gravações
- Acções HA (ligar luzes) com ConfirmationGate → 3.1
- Mini-PC dedicado
- CPT / cutover Phi-4
