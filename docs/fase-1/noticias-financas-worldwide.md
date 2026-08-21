# Notícias e finanças worldwide (por país)

**Estado:** desenho completo — **ainda não implementado**.  
**Objectivo:** escolher um país (ou região) e perceber o que se passa em
**notícias** e **finanças**, com a mesma qualidade que um briefing mundial genérico.

Relacionado: [conversacao.md](conversacao.md) · [skills-contract.md](skills-contract.md)

---

## 1. Problema

Hoje as skills de news/finance são “mundo genérico” (feeds BBC/CNBC fixos +
mapa por palavras-chave). O utilizador quer:

> “O que se passa no **Japão**?” → notícias locais + contexto  
> “Finanças no **Brasil**” → mercados, índices, moeda, headlines económicas  
> “Compara **Alemanha** e **França**” (opcional, fase 2)

Sem inventar factos: tudo vem de feeds/APIs; falhas são admitidas.

---

## 2. Princípios

| Princípio | Detalhe |
|-----------|---------|
| País primeiro | O argumento principal é `country` (ISO 3166-1 alpha-2) |
| Local-first | Preferir RSS públicos; cloud só como fallback opcional |
| Honestidade | Sem headlines inventadas; “Nao consegui obter feeds de JP” |
| Mesmo contrato | Continua a ser `Skill` + `SkillResult`; loop não muda |
| PT por defeito | Resposta em português europeu; `language` opcional |
| Privacidade | Sem tracking; User-Agent `FRIDAY-AI`; timeouts curtos |

---

## 3. Experiência do utilizador

### Frases alvo (intent)

| Frase | Skill | Args |
|-------|--------|------|
| “Poe-me a par” / “briefing mundial” | `get_world_news` | `country=` (vazio = world) |
| “Notícias do Japão” | `get_world_news` | `country=JP` |
| “O que se passa no Brasil?” | `get_world_news` | `country=BR` |
| “Headlines nos EUA em inglês” | `get_world_news` | `country=US`, `language=en` |
| “Briefing financeiro” | `get_world_finance_news` | `country=` (world) |
| “Finanças na Alemanha” | `get_world_finance_news` | `country=DE` |
| “Mercados no Japão” | `get_world_finance_news` | `country=JP` |
| “Abre o monitor do Brasil” | `open_world_monitor` | `country=BR` |
| “Painel financeiro dos EUA” | `open_finance_world_monitor` | `country=US` |
| “Notícias e finanças em Portugal” | (duas tools ou skill composta) | `country=PT` |

### Resposta falada (estrutura)

1. Uma frase de contexto: país + hora local aproximada (via `get_current_datetime` com TZ do país, se útil).
2. 4–8 bullets de headlines (título + fonte curta).
3. Bloco financeiro (se pedido ou skill finance): índice principal, moeda, 3–5 headlines económicas.
4. “Abri o monitor de [país]” se `open_monitor=true` (default como hoje).

---

## 4. Modelo de dados

### País (`CountryProfile`)

Ficheiro sugerido (implementação futura): `friday/skills/news/countries.py`

```text
code: "JP"
names_pt: ["japao", "japão", "japan"]
names_en: ["japan"]
timezone: "Asia/Tokyo"
language_default: "ja"          # língua local das fontes
reply_language_default: "pt"    # língua da resposta FRIDAY
news_feeds: [url, ...]
finance_feeds: [url, ...]
markets:
  - name: "Nikkei 225"
    symbol_hint: "N225"         # só para display / search; não inventar cotações
  - name: "USD/JPY"
currency: "JPY"
lat_lon: [35.68, 139.69]        # centro do mapa no monitor
region: "asia"                  # asia | europe | americas | africa | me | oceania
```

### Catálogo inicial (piloto — expandível)

| Código | País | Índice / foco | Moeda | TZ |
|--------|------|---------------|-------|-----|
| `WW` | Mundo (default) | feeds actuais | — | UTC |
| `PT` | Portugal | PSI / Euronext Lisboa | EUR | Europe/Lisbon |
| `ES` | Espanha | IBEX 35 | EUR | Europe/Madrid |
| `FR` | França | CAC 40 | EUR | Europe/Paris |
| `DE` | Alemanha | DAX | EUR | Europe/Berlin |
| `GB` | Reino Unido | FTSE 100 | GBP | Europe/London |
| `US` | Estados Unidos | S&P 500 / Nasdaq | USD | America/New_York |
| `BR` | Brasil | Bovespa | BRL | America/Sao_Paulo |
| `JP` | Japão | Nikkei 225 | JPY | Asia/Tokyo |
| `CN` | China | Shanghai / Hang Seng* | CNY | Asia/Shanghai |
| `IN` | Índia | Nifty 50 | INR | Asia/Kolkata |
| `KR` | Coreia do Sul | KOSPI | KRW | Asia/Seoul |
| `AU` | Austrália | ASX 200 | AUD | Australia/Sydney |
| `CA` | Canadá | TSX | CAD | America/Toronto |
| `MX` | México | IPC | MXN | America/Mexico_City |
| `ZA` | África do Sul | JSE | ZAR | Africa/Johannesburg |
| `AE` | Emirados / Golfo | mercados regionais | AED | Asia/Dubai |
| `IT` | Itália | FTSE MIB | EUR | Europe/Rome |
| `NL` | Países Baixos | AEX | EUR | Europe/Amsterdam |
| `CH` | Suíça | SMI | CHF | Europe/Zurich |

\*HK pode ser perfil separado `HK` se os feeds forem distintos.

> **Nota:** cotações em tempo real exactas exigem API (muitas pagas). No MVP:
> headlines financeiras + **contexto** (índice/moeda mencionados) + opcional
> `search_web` para “Nikkei today” se não houver feed de preços. Nunca inventar números.

---

## 5. Skills — contrato alargado

### `get_world_news`

```json
{
  "type": "object",
  "properties": {
    "country": {
      "type": "string",
      "description": "ISO 3166-1 alpha-2 (JP, BR, US) ou vazio para mundo"
    },
    "language": {
      "type": "string",
      "description": "Idioma preferido das headlines (pt, en, ...)"
    },
    "topic": {
      "type": "string",
      "description": "Opcional: politics, tech, sports, climate, ..."
    },
    "limit": { "type": "integer", "default": 8 },
    "open_monitor": { "type": "boolean", "default": true }
  }
}
```

### `get_world_finance_news`

Mesmos campos + opcional:

```json
{
  "include_fx": { "type": "boolean", "default": true },
  "include_commodities": { "type": "boolean", "default": false }
}
```

### Monitores

- `open_world_monitor` / `open_finance_world_monitor`  
  - `country` opcional → abre snapshot filtrado (`world_JP_snapshot.html` ou query no HTML).
- URLs externas: `WORLD_MONITOR_URL`, `FINANCE_MONITOR_URL` continuam a ter prioridade se definidas.

### Skills extra (recomendadas — adicionar se quiseres o pacote completo)

| Skill | Função |
|-------|--------|
| `get_country_briefing` | Notícias **+** finanças num só turno (país obrigatório) |
| `list_supported_countries` | Lista códigos/nomes que a FRIDAY conhece |
| `compare_countries_news` | 2 países, headlines lado a lado (fase 2) |
| `get_market_hours` | Mercado aberto/fechado + TZ (derivado do perfil) |

Alias úteis: `get_news`, `get_finance`, `country_update`.

---

## 6. Fontes de dados

### Estratégia em camadas

1. **RSS do perfil do país** (`news_feeds` / `finance_feeds`)
2. **Agregador com `gl`/`hl`** (ex. Google News RSS por país — verificar ToS/uso)
3. **Fallback** `search_web` com query `"top news {country}"` / `"markets {country}"` e aviso “via pesquisa, nao feed dedicado”
4. **Nunca** LLM como fonte de headlines

### Exemplos de feeds (a validar na implementação)

| País | Notícias (exemplos) | Finanças (exemplos) |
|------|---------------------|---------------------|
| WW | BBC World, Reuters world | BBC Business, CNBC |
| PT | Público / Observador RSS (se estáveis) | Económico / JE |
| US | NPR / BBC US / AP | CNBC, MarketWatch RSS |
| BR | G1 / Folha (RSS) | InfoMoney / Valor (se RSS) |
| JP | NHK World / Japan Times | Nikkei Asia (se RSS) |
| DE | DW / Spiegel | Handelsblatt / DW business |
| GB | BBC UK | BBC Business UK |

Manter a lista **fora do código hardcode espalhado**: um único módulo/YAML
`data/country_feeds.yaml` (ou Python) versionado no repo, override por `.env`:

```env
NEWS_COUNTRY_FEEDS_JP=https://...,https://...
NEWS_FINANCE_FEEDS_BR=https://...
NEWS_DEFAULT_COUNTRY=
NEWS_FEED_TIMEOUT_SECONDS=15
NEWS_MAX_HEADLINES=8
```

---

## 7. Monitor (UI)

Snapshot HTML por país (ou um template com dados embutidos):

- Título: `FRIDAY — Japão (notícias)` / `FRIDAY — Brasil (finanças)`
- Mapa centrado no `lat_lon` do país (zoom 5–6), markers só desse briefing
- Lista de headlines + link
- Rodapé: “Actualizado … · fontes RSS · sem cotações inventadas”
- Modo mundo (`WW`): comportamento actual (vista global)

Ficheiros sugeridos:

```text
friday/monitors/
  world_snapshot.html          # WW ou último pedido
  finance_snapshot.html
  data/world_JP.json
  data/finance_BR.json
  country_snapshot.html        # template único parametrizado
```

---

## 8. Intent router

Extrair país de PT/EN:

- “no/na/em/do/da/dos/das {país}”
- “{país} news / markets / finance”
- Sinónimos do `CountryProfile.names_*`
- Ambiguidade (“Coreia”) → preferir `KR` ou perguntar (fase 2: clarificação)

Ordem: **monitor explícito** → **finance+país** → **news+país** → **world genérico**.

---

## 9. Integração MCP (opcional)

Expor no servidor MCP:

- tools: `get_world_news`, `get_world_finance_news`, `get_country_briefing`, `list_supported_countries`
- resource: `friday://countries` → JSON do catálogo

Assim o Cursor também pode pedir “briefing JP”.

---

## 10. Continuidade e memória

- Após um briefing JP, “e as finanças?” → mesma `country=JP` via short-term (última país mencionada no metadata da skill).
- `remember`: “O utilizador segue mercados JP” → `recall` sugere briefing JP.

Campo sugerido em metadata da skill: `{"country": "JP", "kind": "news"}`.

---

## 11. Falhas e limites

| Situação | Comportamento |
|----------|----------------|
| País desconhecido | “Ainda nao tenho feeds para X. Paises suportados: …” + `list_supported_countries` |
| Todos os feeds down | Mensagem honesta + oferecer `search_web` |
| Sem cotações real-time | Não inventar; só headlines / “consulta o monitor” |
| Paywall / HTML pesado | Título + link; não fingir artigo completo |
| Conflito de nome | Preferir ISO; logar ambiguidade |

---

## 12. Segurança e ética

- Só fontes públicas; respeitar robots/ToS dos feeds
- Não scrapear agressivamente (timeout, cache 5–15 min por país)
- Sem conselho de investimento (“isto nao e aconselhamento financeiro”)
- Cache em `data/news_cache/` (gitignored)

---

## 13. Fases de implementação

| Fase | Entrega | Critério de pronto |
|------|---------|-------------------|
| **A** | `CountryProfile` + 8 países piloto + `country` nas 2 skills | “Notícias do Japão” devolve headlines reais |
| **B** | Intent PT/EN + monitores por país | Abre snapshot centrado no país |
| **C** | `get_country_briefing` + `list_supported_countries` + cache | Um pedido = news+finance |
| **D** | Expandir catálogo (18+), topic filter, MCP | Cobertura worldwide útil |
| **E** | `compare_countries_*`, market hours, FX via search controlado | Extras |

Ordem recomendada: **A → B → C**; D/E quando a base estiver estável.

---

## 14. Testes

- Unit: parse país (“Japão”→`JP`, “japan”→`JP`)
- Unit: feeds vazios / 1 feed OK
- Integration (opcional CI): 1 feed estável por piloto
- Intent: tabela de frases PT/EN
- Snapshot: HTML gerado contém título do país e ≥1 article se mock feeds

---

## 15. Docs a actualizar na implementação

- [skills-contract.md](skills-contract.md) — parâmetros `country`
- [conversacao.md](conversacao.md) — exemplos por país
- [.env.example](../../.env.example) — overrides de feeds
- Este ficheiro — marcar fases A/B/… como feitas

---

## 16. Fora de âmbito (não misturar aqui)

- Trading automático, Open Banking, carteiras pessoais (fases posteriores)
- Geopolítica tipo “World Monitor” comercial completo (podes ligar URL externa)
- Tradução automática de todos os artigos (só títulos + summary curto)

---

## Resumo

O utilizador escolhe um **país**; a FRIDAY usa um **perfil** (feeds + TZ + mercados + mapa),
corre as skills de **notícias** e/ou **finanças**, fala um briefing honesto e
pode abrir um **monitor** desse país. Mundo (`WW`) continua a ser o default
quando não há país na frase.
