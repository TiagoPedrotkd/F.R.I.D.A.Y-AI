# LM Studio — Setup para Fase 0

O F.R.I.D.A.Y-AI usa LM Studio como servidor LLM local, exposto via API compatible com OpenAI.

> **Nota:** Versoes recentes do LM Studio no Windows podem usar o executavel **Bionic.exe**
> (ex.: `D:\Models\LM_STUDIO\Bionic\Bionic.exe`). O script `scripts/find-lm-studio.ps1` detecta automaticamente.

## Pré-requisitos

- Windows 10/11 (máquina de dev atual)
- GPU dedicada recomendada (NVIDIA) para modelos maiores; CPU funciona para modelos pequenos
- ~4–8 GB RAM livres consoante o modelo

## Instalação

1. Descarregar LM Studio em [https://lmstudio.ai](https://lmstudio.ai)
2. Instalar e abrir a aplicação
3. Na aba **Discover**, pesquisar e descarregar um modelo (ex.: `Llama 3.2 3B Instruct` para testes leves)
4. Na aba **Chat**, carregar o modelo descarregado

## Ativar servidor local (API)

1. Ir à aba **Local Server** (ícone `<->` na barra lateral)
2. Selecionar o modelo carregado
3. Clicar **Start Server**
4. Confirmar que o servidor está a escutar na porta **1234** (default)

## Validar conectividade

PowerShell (substituir pelo IP/host do LM Studio):

```powershell
Invoke-RestMethod -Uri "http://192.168.10.131:1234/v1/models"
```

Deve devolver JSON com a lista de modelos disponíveis.

Teste de chat:

```powershell
$body = @{
  model = "microsoft/phi-4"
  messages = @(@{ role = "user"; content = "Reply with exactly: OK" })
  max_tokens = 16
  temperature = 0
} | ConvertTo-Json -Depth 4

Invoke-RestMethod -Uri "http://192.168.10.131:1234/v1/chat/completions" `
  -Method Post -ContentType "application/json" -Body $body
```

## Configurar `.env`

Copiar o nome exacto do modelo para `LM_STUDIO_MODEL` em [`.env`](../../.env):

**LM Studio no mesmo PC que corre Docker** (setup actual — IP LAN `192.168.10.131`):

```env
# Container Docker → LM Studio no mesmo PC
LM_STUDIO_BASE_URL=http://host.docker.internal:1234/v1
LM_STUDIO_MODEL=microsoft/phi-4
LM_STUDIO_API_KEY=lm-studio
```

> **Nota:** `http://192.168.10.131:1234/v1` funciona no browser e noutros dispositivos LAN,
> mas **não** dentro do container Docker no mesmo PC (limitação NAT/hairpin).
> O healthcheck usa `host.docker.internal` para alcançar o LM Studio local.

**LM Studio noutro host na LAN:**

```env
LM_STUDIO_BASE_URL=http://<IP-OUTRO-HOST>:1234/v1
LM_STUDIO_MODEL=<nome-exacto-do-modelo>
LM_STUDIO_API_KEY=lm-studio
```

Para obter o nome exacto, consultar a resposta de `/v1/models` ou o dropdown do Local Server.

## Docker → LM Studio

| Cenário | URL LM Studio | `LM_STUDIO_BASE_URL` no `.env` |
|---|---|---|
| LM Studio no mesmo PC (IP LAN `192.168.10.131`) | `http://192.168.10.131:1234/v1` (LAN) | `http://host.docker.internal:1234/v1` |
| LM Studio noutro host LAN | `http://<IP>:1234/v1` | `http://<IP>:1234/v1` |

O container **nunca** usa `localhost` — dentro do Docker, `localhost` é o próprio container.

Para LM Studio no mesmo PC, [`docker-compose.yml`](../../docker-compose.yml) inclui `extra_hosts: host.docker.internal:host-gateway`.

## Troubleshooting

| Problema | Solução |
|---|---|
| `/health/llm` devolve 503 "Cannot reach LM Studio" | Confirmar Local Server activo; testar `http://<IP>:1234/v1/models` |
| HTTP 404 no chat | `LM_STUDIO_MODEL` não coincide com o modelo carregado — verificar `/v1/models` |
| Resposta lenta | Modelo grande em CPU; usar modelo menor para testes |
| Porta ocupada | Alterar porta no LM Studio e actualizar `LM_STUDIO_BASE_URL` |

## CORS

O healthcheck corre server-side (Python → LM Studio), por isso CORS do browser **não** afecta o endpoint `/health/llm`. CORS só importa se expuseres a API LM Studio directamente a clients web.
