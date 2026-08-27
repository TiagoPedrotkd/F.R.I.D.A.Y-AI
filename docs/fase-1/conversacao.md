# Contrato conversacional — Fase 1

A FRIDAY combina **conversa geral** (modelo local) com **ferramentas**
(skills). O utilizador fala naturalmente; nao ha palavras magicas obrigatorias.

## Arquitectura

```text
STT / texto → ToolRunner
               ├─ intent_router (frases obvias PT/EN)
               └─ LM Studio (tool calling / JSON fallback)
                    → SkillRegistry → resposta
                    → prepare_speech_text → Piper TTS
```

Sessao (`ShortTermMemory`): historico curto + `last_country`,
`last_news_context`, `last_language`, `last_monitor_type`.

## 1. Conversacao geral (sem tool)

Cumprimentos, explicacoes, resumos, reescrita, traducao, escrita, brainstorm,
planeamento, comparacoes e programacao — o modelo local responde directamente.
Limitacao: conhecimento do modelo; factos actualizados exigem tools.

## 2. Ferramentas reais (voice registry)

| Skill | Quando usar |
|-------|-------------|
| `get_current_datetime` | Hora, data, dia da semana (alias: `get_current_time`) |
| `get_world_news` | Briefing mundial ou por pais (`country=JP`) — headlines |
| `get_world_finance_news` | Briefing financeiro por pais — **nao** cotacoes |
| `get_country_briefing` | Noticias + financas num so turno |
| `list_supported_countries` | Lista de paises com feeds |
| `open_world_monitor` | Abrir painel mundial / do pais |
| `open_finance_world_monitor` | Abrir painel financeiro |
| `search_web` | Pesquisa Internet (DuckDuckGo / ddgs) com fontes |
| `fetch_url` | Ler texto principal de um URL http(s) |
| `get_system_info` | SO / Python / hostname |
| `word_count` | Contar palavras/caracteres/linhas |
| `format_json` | Validar e pretty-print JSON |
| `summarize` / `explain_code` | Resumo / explicacao de codigo (tambem MCP) |
| `remember` / `recall` | Memoria longa entre sessoes |
| `tell_joke` | Piada curta |

**Nao existem:** `read_webpage`, `get_system_status`.

Paises piloto: WW, PT, ES, FR, DE, GB, US, BR, JP.
Continuidade: apos "noticias do Japao", "e as financas?" reutiliza `JP`.

## 3. Monitores

`AUTO_OPEN_MONITORS=false` (default): briefing + "Queres que abra o mapa?"
`AUTO_OPEN_MONITORS=true`: abre o snapshot e confirma na resposta.
Pedido directo "Abre o monitor..." chama sempre `open_*_monitor`.
URLs externas: `WORLD_MONITOR_URL`, `FINANCE_MONITOR_URL`.

## 4. LM Studio

| Variavel | Uso |
|----------|-----|
| `LM_STUDIO_BASE_URL_HOST` | API OpenAI-compatible (ex. `http://localhost:1234/v1`) |
| `LM_STUDIO_MODEL` | ID do modelo carregado |
| `LM_STUDIO_API_KEY` | Placeholder (ex. `lm-studio`) |
| `LLM_TIMEOUT_SECONDS` | Timeout das chamadas |
| `LLM_MAX_TOOL_ROUNDS` | Maximos ciclos tool |

O modelo deve estar em **Load** e o Local Server **ON** antes do voice loop.

## 5. Limitacoes

- Noticias: so headlines RSS; nao artigo completo.
- Financas: headlines; nunca cotacoes inventadas.
- `fetch_url`: bloqueia localhost/IPs privados; so conteudo textual.
- `search_web`: depende de ddgs; falha devolve mensagem honesta.

## 6. Confirmacao (accoes futuras)

Antes de email, apagar ficheiros, calendario, comandos perigosos, compras ou
accoes irreversiveis: `friday.safety.confirmation.ConfirmationGate`.
Uma resposta "sim" antiga nao autoriza uma accao nova.

## 7. MCP

Subset (stdio): tools `summarize`, `explain_code`, `get_current_datetime`,
`get_system_info`, `remember`, `recall`; prompts `summarize`, `explain_code`.
News/search/monitors existem no voice loop, nao no MCP nesta fase.
Ver [mcp.md](mcp.md).

## 8. Testes

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -q
```

Aceitacao conversacional: `tests/test_conversational_acceptance.py`.

## Intent router

`friday/llm/intent_router.py` mapeia frases obvias (PT/EN) para skills,
incluindo hora, pais, continuidade e monitores — nao depende so do tool calling.
