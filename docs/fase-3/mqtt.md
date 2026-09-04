# MQTT (Mosquitto) — Fase 3.0

Broker local para HA / futuros sensores / Frigate.

## Arranque

```powershell
docker compose --profile mqtt up -d
```

## Portas

| Porta | Bind | Uso |
|-------|------|-----|
| 1883 | `127.0.0.1` | MQTT sem TLS (LAN local apenas) |

## Config

Ficheiro: `deploy/mosquitto/mosquitto.conf`  
Auth: anónima desactivada em produção futura; 3.0 usa allow_anonymous true **só em localhost**.

## Variáveis

```env
MQTT_HOST=127.0.0.1
MQTT_PORT=1883
MQTT_USERNAME=
MQTT_PASSWORD=
```

HA deve apontar o broker MQTT para `host.docker.internal:1883` ou o hostname do serviço `mosquitto` na rede compose.
