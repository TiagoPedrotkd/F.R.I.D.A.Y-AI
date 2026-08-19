# Rede Local — Acesso ao Healthcheck

O serviço `friday-healthcheck` expõe a porta **8080** na interface `0.0.0.0`, acessível na LAN.

## Endpoints

| Endpoint | Descrição |
|---|---|
| `GET /health` | Status do serviço (sem LLM) |
| `GET /ready` | Readiness probe |
| `GET /health/llm` | Teste de conectividade com LM Studio |

## Acesso local (mesma máquina)

```
http://localhost:8080/health
http://localhost:8080/health/llm
```

## Acesso na LAN (outro dispositivo)

1. Obter IP da máquina Windows:

   ```powershell
   ipconfig
   ```

   Procurar **IPv4** da interface Wi-Fi ou Ethernet (ex.: `192.168.1.42`).

2. No outro dispositivo (telefone, tablet, outro PC):

   ```
   http://192.168.1.42:8080/health
   http://192.168.1.42:8080/health/llm
   ```

## Firewall Windows

Permitir tráfego inbound na porta 8080:

```powershell
New-NetFirewallRule -DisplayName "FRIDAY Healthcheck" `
  -Direction Inbound -Protocol TCP -LocalPort 8080 -Action Allow
```

Para remover a regra:

```powershell
Remove-NetFirewallRule -DisplayName "FRIDAY Healthcheck"
```

## Docker — binding de portas

Em [`docker-compose.yml`](../../docker-compose.yml):

```yaml
ports:
  - "${HEALTHCHECK_PORT:-8080}:8080"
```

O formato `"8080:8080"` faz bind em todas as interfaces (`0.0.0.0`), permitindo acesso LAN.

## Teste de validação Fase 0

- [ ] `curl http://localhost:8080/health` → 200
- [ ] `curl http://<IP-LAN>:8080/health` → 200 (de outro dispositivo)
- [ ] `curl http://<IP-LAN>:8080/health/llm` → 200 (com LM Studio activo)

## Notas de segurança

- A Fase 0 expõe endpoints **sem autenticação** — adequado apenas para rede doméstica confiável
- Fases futuras devem adicionar autenticação ou restringir acesso (reverse proxy, VPN)
- Não expor a porta 8080 à internet pública sem protecção
