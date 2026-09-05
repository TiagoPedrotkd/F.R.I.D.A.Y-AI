# Google OAuth — Fase 4

## Cloud Console

1. [Google Cloud Console](https://console.cloud.google.com/) → criar/seleccionar projecto.
2. APIs & Services → Enable: **Google Calendar API**, **Gmail API**, **Fitness API**.
3. OAuth consent screen → External → **Testing** → adicionar o teu email como test user.
4. Credentials → Create OAuth client ID → **Desktop app** (ou Web com redirect abaixo).
5. Copiar Client ID / Secret para `.env`.

## `.env`

```env
GOOGLE_ENABLED=true
GOOGLE_CLIENT_ID=....apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=....
GOOGLE_REDIRECT_URI=http://127.0.0.1:8090/v1/google/callback
GOOGLE_TOKEN_PATH=data/secrets/google_tokens.json
```

## Rotas agent-api

| Método | Rota | Função |
|--------|------|--------|
| GET | `/v1/google/status` | enabled / configured / connected |
| GET | `/v1/google/auth-url` | URL de consentimento |
| GET | `/v1/google/callback?code=&state=` | troca code → tokens |
| POST | `/v1/google/disconnect` | apaga tokens locais |

## Scopes (Testing)

- `calendar`, `gmail.modify`
- `fitness.activity.read`, `fitness.sleep.read`, `fitness.heart_rate.read`

Scopes de **Google Health API** (Restricted) podem exigir revisão — ver [saude.md](saude.md) para Fitbit legado.
