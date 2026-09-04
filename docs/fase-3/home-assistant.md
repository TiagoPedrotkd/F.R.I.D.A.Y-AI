# Home Assistant — Fase 3.0

## Arranque

```powershell
docker compose --profile mqtt --profile homeassistant up -d
```

UI: [http://127.0.0.1:8123](http://127.0.0.1:8123) (bind localhost).  
Onboarding no browser na primeira vez.

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

## Skills FRIDAY (read-only)

Ver [skills-contract.md](skills-contract.md). Sem serviços `turn_on` nesta passagem.

## Segurança

- Porta só em `127.0.0.1`  
- Token só no `.env`  
- Sem port-forward / cloud HA  
