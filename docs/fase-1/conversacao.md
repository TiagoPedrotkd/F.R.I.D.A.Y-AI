# Contrato conversacional — Fase 1

A FRIDAY combina **conversa geral** (modelo local) com **ferramentas**
(skills). O utilizador fala naturalmente; nao ha palavras magicas obrigatorias.

## 1. Conversacao geral (sem tool)

Cumprimentos, explicacoes, resumos, reescrita, traducao, escrita, brainstorm,
planeamento, comparacoes e programacao — o Phi-4 (ou outro LLM local) responde
directamente, usando o historico da sessao (`MAX_CONTEXT_MESSAGES`, default 20).

Limitacao: conhecimento do modelo; factos actualizados exigem tools.

## 2. Ferramentas

| Skill | Quando usar |
|-------|-------------|
| `get_current_datetime` | Hora, data, dia da semana (alias: `get_current_time`) |
| `get_world_news` | Briefing mundial; abre World Monitor (mapa) |
| `get_world_finance_news` | Briefing financeiro; abre Finance Monitor |
| `open_world_monitor` | Abrir painel mundial |
| `open_finance_world_monitor` | Abrir painel financeiro |
| `search_web` | Pesquisa Internet (DuckDuckGo) |
| `fetch_url` | Ler texto principal de um URL |
| `get_system_info` | SO / Python / hostname |
| `word_count` | Contar palavras/caracteres/linhas |
| `format_json` | Validar e pretty-print JSON |
| `summarize` / `explain_code` | Resumo / explicacao de codigo (tambem MCP) |
| `remember` / `recall` | Memoria longa entre sessoes |
| `tell_joke` | Piada curta |

Monitores locais: `friday/monitors/*_snapshot.html` com **mapa Leaflet** + lista.
URLs externas: `WORLD_MONITOR_URL`, `FINANCE_MONITOR_URL`.

### Roadmap: notícias / finanças por país

Desenho completo (ainda nao implementado): escolher país (JP, BR, US, …) e
obter briefing de notícias e/ou finanças + monitor centrado nesse país.
Ver [noticias-financas-worldwide.md](noticias-financas-worldwide.md).

## 3. Continuidade

Referencias como "continua", "explica melhor", "em ingles" usam a memoria
short-term da sessao. Entre sessoes: `remember` / `recall` (Chroma ou JSONL
em `data/chroma/`).

## MCP

Ver [mcp.md](mcp.md) — prompts `summarize` e `explain_code` + tools.

## 4. Falhas

A FRIDAY admite falhas ("Nao consegui consultar..."). Nunca inventa hora,
noticias, resultados web, nem finge que abriu uma app.

## Intent router

Para modelos locais que ignoram tool-calling, `friday/llm/intent_router.py`
mapeia frases obvias (PT/EN) directamente para skills.
