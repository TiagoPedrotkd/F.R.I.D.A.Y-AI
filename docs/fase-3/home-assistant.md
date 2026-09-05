# Home Assistant — Fase 3.0

## Como corre

**Home Assistant Container** (Docker Compose) — **não** é Home Assistant OS.  
Por isso **não há Add-ons** (Matter Server add-on não aparece). Precisas do contentor `matter-server` em separado, ou de outra integração (ex. HomeKit Device).

## Arranque

```powershell
docker compose --profile mqtt --profile homeassistant up -d
```

Sobe: Mosquitto + HA + **Matter Server** (`friday-matter-server`).

UI: [http://127.0.0.1:8123](http://127.0.0.1:8123) no PC.  
App telemóvel (mesma Wi‑Fi/LAN): `http://192.168.10.131:8123` (IP do hub).  
A porta `8123` está aberta na LAN — **não** faças port-forward no router.

## Variáveis (`.env`)

```env
HA_ENABLED=false
HA_URL=http://127.0.0.1:8123
HA_TOKEN=
HA_PORT=8123
```

1. Perfil HA → Security → Long-Lived Access Tokens → Create  
2. Colocar o token em `HA_TOKEN`  
3. `HA_ENABLED=true` e reiniciar agent-api  

## Matter (IKEA / Thread) no Docker

No Container, `localhost` **dentro** do HA é o próprio contentor HA — não o Matter Server.

1. Confirma `friday-matter-server` a correr (`docker ps`).
2. Settings → Devices & Services → Matter → Submit com:
   ```text
   ws://matter-server:5580/ws
   ```
   (nome do serviço Compose; **não** uses `ws://localhost:5580/ws`).

### Limite no Windows (Docker Desktop)

Matter/Thread precisa muitas vezes de rede host / mDNS fiável. No Docker Desktop Windows isso é frágil. Se a comissão falhar:

## Alternativa recomendada para IKEA: HomeKit Device

1. Cancela / fecha o diálogo Matter.  
2. Settings → Devices & Services → **Add Integration** → **HomeKit Device**.  
3. Na app IKEA: Settings → Integrations → Apple HomeKit → código de 8 dígitos.  
4. Introduz o código no HA.

Não precisa de Matter Server.

## Skills + painel Casa

Com `HA_ENABLED=true` e token válido:

- Chat: `ha_get_status`, `ha_list_entities`, `ha_get_state`, `ha_call_service` (com confirmação)
- UI FRIDAY: botão **Casa** → estado, luzes, switches, energia; acções pedem confirmação
- API: `/v1/ha/status`, `/v1/ha/entities`, `/v1/ha/energy`, `/v1/ha/action`

Ver [skills-contract.md](skills-contract.md).

## Segurança

- Porta só em `127.0.0.1`  
- Token só no `.env`  
- Sem port-forward / cloud HA  
