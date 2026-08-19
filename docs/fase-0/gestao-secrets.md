# Gestão de Secrets — Fase 0

## Princípio

Passwords, API keys e credenciais **nunca** entram no repositório Git. O código lê secrets apenas via variáveis de ambiente (ficheiro `.env` local).

## Fluxo de setup

1. Copiar o template: `cp .env.example .env` (Windows: `copy .env.example .env`)
2. Editar `.env` com valores locais (modelo LM Studio, porta, etc.)
3. Confirmar que `.env` está ignorado: `git check-ignore -v .env`
4. Arrancar serviços: `docker compose up --build`

## O que nunca commitar

| Tipo | Exemplos |
|---|---|
| Ficheiros de ambiente | `.env`, `.env.local`, `.env.production` |
| Certificados | `*.pem`, `*.key`, `*.p12` |
| Credenciais JSON | `credentials.json`, tokens OAuth |
| Pastas de secrets | `secrets/` |

O ficheiro [`.env.example`](../.env.example) contém **apenas placeholders** — é seguro versionar.

## Fase 0 — LM Studio (local)

Na Fase 0 usamos LM Studio localmente. A API key padrão (`lm-studio`) não é um secret real — o servidor corre na tua máquina. Mesmo assim, mantemos o padrão `.env` para consistência com fases futuras.

## Fase 1+ — APIs cloud (preparatório)

Quando integrares Anthropic ou OpenAI:

- Criar keys nos dashboards oficiais
- Guardar apenas em `.env` local
- Ativar **billing alerts** no provider
- Documentar rotação em [`contas-api.md`](contas-api.md)

Variáveis previstas (não necessárias na Fase 0):

```
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
```

## Rotação de secrets

1. Gerar nova key no provider
2. Atualizar `.env` local
3. Reiniciar containers: `docker compose down && docker compose up -d`
4. Revogar key antiga no dashboard
5. Se a key antiga esteve exposta: assumir comprometida e auditar uso

## Resposta a leak acidental

Se uma key for commitada ou partilhada:

1. **Revogar imediatamente** a key no dashboard do provider
2. Remover do histórico Git se foi commitada (`git filter-repo` ou suporte GitHub)
3. Gerar nova key e atualizar `.env`
4. Rever logs de billing/uso no provider

## Transferência segura para host final

Quando fizeres deploy no Mini-PC/VPS (pós-Fase 0):

- **Nunca** transferir `.env` via Git
- Usar SCP/SFTP encriptado, USB offline, ou gestor de passwords
- Confirmar permissões do ficheiro no host (`chmod 600 .env`)
