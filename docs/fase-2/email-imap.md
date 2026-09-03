# Email IMAP/SMTP — Fase 2

Leitura via `imaplib`, envio via `smtplib` — sem middleware cloud.

## Variáveis (`.env`)

```env
EMAIL_ENABLED=true
IMAP_HOST=imap.example.com
IMAP_PORT=993
IMAP_USER=eu@example.com
IMAP_PASSWORD=
IMAP_FOLDER=INBOX
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=
EMAIL_USE_SSL=true
```

Se `SMTP_USER` / `SMTP_PASSWORD` estiverem vazios, reutilizam-se os valores IMAP.

## Skills

| Skill | Confirmação |
|-------|-------------|
| `list_emails` | Não |
| `read_email` | Não |
| `send_email` | Sim (`ConfirmationGate`) |

## Segurança

- Nunca gravar passwords no bundle Tauri
- Envio só após confirmação explícita (UI ou “sim”)
