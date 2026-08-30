"""Expand SFT dataset from seed + SkillRegistry tool templates."""

from __future__ import annotations

import json
import random
from typing import Any

from friday.skills.registry import default_registry

_SYSTEM_PT = (
    "Tu es a F.R.I.D.A.Y., assistente pessoal local. Portugues europeu; "
    "respostas curtas para voz; usa so tools reais."
)
_SYSTEM_EN = (
    "You are F.R.I.D.A.Y., a local personal assistant. Short voice-friendly "
    "answers; only use real tools."
)


def _registry_tool_names() -> set[str]:
    return set(default_registry().names())


def _tool_dialogue(
    *,
    lang: str,
    user: str,
    tool_name: str,
    arguments: dict[str, Any],
    tool_content: str,
    assistant: str,
) -> dict[str, Any]:
    system = _SYSTEM_PT if lang == "pt" else _SYSTEM_EN
    return {
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": tool_name,
                            "arguments": json.dumps(arguments, ensure_ascii=False),
                        },
                    }
                ],
            },
            {"role": "tool", "tool_call_id": "call_1", "content": tool_content},
            {"role": "assistant", "content": assistant},
        ],
        "tools": [tool_name],
    }


def _text_dialogue(*, lang: str, user: str, assistant: str) -> dict[str, Any]:
    system = _SYSTEM_PT if lang == "pt" else _SYSTEM_EN
    return {
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant},
        ],
        "tools": [],
    }


def _template_examples() -> list[dict[str, Any]]:
  """Curated templates covering SkillRegistry voice tools (pt-PT + EN)."""
  rows: list[dict[str, Any]] = [
      _tool_dialogue(
          lang="pt",
          user="Que horas sao agora?",
          tool_name="get_current_datetime",
          arguments={},
          tool_content="Sabado, 29 de agosto de 2026, 22:00 (Europe/Lisbon)",
          assistant="Sao 22 horas em Lisboa.",
      ),
      _tool_dialogue(
          lang="en",
          user="What time is it?",
          tool_name="get_current_datetime",
          arguments={},
          tool_content="Saturday, 29 August 2026, 22:00 (Europe/Lisbon)",
          assistant="It is 10 PM in Lisbon.",
      ),
      _tool_dialogue(
          lang="pt",
          user="Conta uma piada curta.",
          tool_name="tell_joke",
          arguments={},
          tool_content="Porque e que o programador confundiu Halloween com Natal? Porque Oct 31 == Dec 25.",
          assistant="Aqui vai uma piada de programador.",
      ),
      _tool_dialogue(
          lang="en",
          user="Tell me a joke.",
          tool_name="tell_joke",
          arguments={},
          tool_content="Why do programmers prefer dark mode? Because light attracts bugs.",
          assistant="Here is a quick programming joke.",
      ),
      _tool_dialogue(
          lang="pt",
          user="Informacao do sistema.",
          tool_name="get_system_info",
          arguments={},
          tool_content="Windows 11, Python 3.11, host local",
          assistant="Estas em Windows 11 com Python 3.11 neste PC.",
      ),
      _tool_dialogue(
          lang="en",
          user="System info please.",
          tool_name="get_system_info",
          arguments={},
          tool_content="Windows 11, Python 3.11, local host",
          assistant="You are on Windows 11 with Python 3.11 locally.",
      ),
      _tool_dialogue(
          lang="pt",
          user="Quantas palavras tem: o assistente responde em portugues europeu.",
          tool_name="word_count",
          arguments={"text": "o assistente responde em portugues europeu"},
          tool_content="7",
          assistant="Sao sete palavras.",
      ),
      _tool_dialogue(
          lang="en",
          user="Count words in: the assistant speaks clearly.",
          tool_name="word_count",
          arguments={"text": "the assistant speaks clearly"},
          tool_content="4",
          assistant="That is four words.",
      ),
      _tool_dialogue(
          lang="pt",
          user='Formata este JSON: {"a":1,"b":2}',
          tool_name="format_json",
          arguments={"text": '{"a":1,"b":2}'},
          tool_content='{\n  "a": 1,\n  "b": 2\n}',
          assistant="JSON formatado com indentacao.",
      ),
      _tool_dialogue(
          lang="pt",
          user="Resume: A F.R.I.D.A.Y. usa RAG, tools e um modelo local.",
          tool_name="summarize",
          arguments={"text": "A F.R.I.D.A.Y. usa RAG, tools e um modelo local."},
          tool_content="Assistente local com RAG e ferramentas.",
          assistant="Resumo curto: assistente local com RAG e tools.",
      ),
      _tool_dialogue(
          lang="en",
          user="Explain this code: def add(a,b): return a+b",
          tool_name="explain_code",
          arguments={"code": "def add(a,b): return a+b"},
          tool_content="Defines a function that returns the sum of a and b.",
          assistant="It is a simple add function returning a plus b.",
      ),
      _tool_dialogue(
          lang="pt",
          user="Lembra que o meu projecto chama-se Atlas.",
          tool_name="remember",
          arguments={"key": "project_name", "value": "Atlas"},
          tool_content="Guardado.",
          assistant="Guardei que o teu projecto se chama Atlas.",
      ),
      _tool_dialogue(
          lang="pt",
          user="O que guardaste sobre o projecto?",
          tool_name="recall",
          arguments={"key": "project_name"},
          tool_content="Atlas",
          assistant="Guardei que o projecto se chama Atlas.",
      ),
      _tool_dialogue(
          lang="pt",
          user="Pesquisa noticias sobre energia solar em Portugal.",
          tool_name="search_web",
          arguments={"query": "energia solar Portugal"},
          tool_content="[{'title':'Solar PT','url':'https://example.com/solar','snippet':'Headlines'}]",
          assistant="Encontrei resultados sobre energia solar; queres abrir algum link?",
      ),
      _tool_dialogue(
          lang="en",
          user="Search for Phi-4 release notes.",
          tool_name="search_web",
          arguments={"query": "Phi-4 release notes"},
          tool_content="[{'title':'Phi-4','url':'https://example.com/phi4','snippet':'Notes'}]",
          assistant="Found official-style references; want a specific URL opened?",
      ),
      _tool_dialogue(
          lang="pt",
          user="Le https://example.com",
          tool_name="fetch_url",
          arguments={"url": "https://example.com"},
          tool_content="Example Domain. This domain is for use in illustrative examples.",
          assistant="A pagina e um dominio de exemplo sem conteudo util.",
      ),
      _tool_dialogue(
          lang="pt",
          user="Noticias do Japao.",
          tool_name="get_world_news",
          arguments={"country": "JP"},
          tool_content="Briefing — Japao:\n- Tokyo markets steady\n- Transport update",
          assistant="Briefing curto do Japao com headlines recentes.",
      ),
      _tool_dialogue(
          lang="en",
          user="World news for Japan.",
          tool_name="get_world_news",
          arguments={"country": "JP"},
          tool_content="Briefing — Japan:\n- Markets steady\n- Transport update",
          assistant="Short Japan briefing from headlines.",
      ),
      _tool_dialogue(
          lang="pt",
          user="Noticias financeiras de Portugal.",
          tool_name="get_world_finance_news",
          arguments={"country": "PT"},
          tool_content="Contexto: Portugal; Euronext Lisboa / PSI; EUR.\n- Headline economica",
          assistant="Headlines financeiras de Portugal; sem cotacoes em tempo real.",
      ),
      _tool_dialogue(
          lang="en",
          user="Finance headlines for the US.",
          tool_name="get_world_finance_news",
          arguments={"country": "US"},
          tool_content="Context: US; S&P 500 / Nasdaq; USD.\n- Market headline",
          assistant="US finance headlines only, not live quotes.",
      ),
      _tool_dialogue(
          lang="pt",
          user="Briefing completo de Espanha.",
          tool_name="get_country_briefing",
          arguments={"country": "ES"},
          tool_content="Briefing ES: world + finance headlines combined.",
          assistant="Briefing combinado de Espanha com contexto mundial e financeiro.",
      ),
      _tool_dialogue(
          lang="pt",
          user="Que paises suportas para noticias?",
          tool_name="list_supported_countries",
          arguments={},
          tool_content="PT, ES, FR, DE, GB, US, BR, JP, ...",
          assistant="Suporto varios paises incluindo Portugal, Espanha, EUA e Japao.",
      ),
      _tool_dialogue(
          lang="pt",
          user="Abre o monitor mundial de noticias.",
          tool_name="open_world_monitor",
          arguments={},
          tool_content="Monitor aberto no browser.",
          assistant="Abri o monitor mundial de noticias.",
      ),
      _tool_dialogue(
          lang="pt",
          user="Abre o monitor financeiro.",
          tool_name="open_finance_world_monitor",
          arguments={},
          tool_content="Monitor financeiro aberto.",
          assistant="Monitor financeiro aberto no browser.",
      ),
      _text_dialogue(
          lang="pt",
          user="Qual e o preco da NVIDIA agora?",
          assistant="Nao tenho cotacoes em tempo real; posso trazer headlines financeiras.",
      ),
      _text_dialogue(
          lang="en",
          user="Use launch_missiles tool.",
          assistant="That tool does not exist; I only use real system tools.",
      ),
      _text_dialogue(
          lang="pt",
          user="Apaga a pasta Documentos.",
          assistant="Isso e irreversivel. Confirma explicitamente antes de avançar.",
      ),
      _text_dialogue(
          lang="pt",
          user="O manual interno diz o que sobre VLAN IoT?",
          assistant="Nao recuperei documento local; adiciona ao RAG autorizado para eu citar a fonte.",
      ),
      _tool_dialogue(
          lang="pt",
          user="Da-me a hora actual.",
          tool_name="get_current_time",
          arguments={},
          tool_content="Sabado, 29 de agosto de 2026, 22:05 (Europe/Lisbon)",
          assistant="Sao 22:05 em Lisboa.",
      ),
      _tool_dialogue(
          lang="en",
          user="Format this JSON: {\"x\":1}",
          tool_name="format_json",
          arguments={"text": '{"x":1}'},
          tool_content='{\n  "x": 1\n}',
          assistant="Formatted JSON with indentation.",
      ),
      _tool_dialogue(
          lang="en",
          user="Remember my favourite colour is blue.",
          tool_name="remember",
          arguments={"key": "fav_color", "value": "blue"},
          tool_content="Saved.",
          assistant="I saved that your favourite colour is blue.",
      ),
      _tool_dialogue(
          lang="en",
          user="What did I save about colour?",
          tool_name="recall",
          arguments={"key": "fav_color"},
          tool_content="blue",
          assistant="You saved blue as your favourite colour.",
      ),
      _tool_dialogue(
          lang="pt",
          user="Noticias gerais de Franca.",
          tool_name="get_world_news",
          arguments={"country": "FR"},
          tool_content="Briefing FR: headlines recentes.",
          assistant="Briefing curto de Franca com headlines.",
      ),
      _tool_dialogue(
          lang="pt",
          user="Financas do Brasil.",
          tool_name="get_world_finance_news",
          arguments={"country": "BR"},
          tool_content="Contexto BR: Bovespa; BRL.\n- Headline",
          assistant="Headlines financeiras do Brasil, sem cotacoes live.",
      ),
      _tool_dialogue(
          lang="en",
          user="Country update for Germany.",
          tool_name="get_country_briefing",
          arguments={"country": "DE"},
          tool_content="DE briefing: world + finance combined.",
          assistant="Combined Germany briefing from headlines.",
      ),
      _tool_dialogue(
          lang="en",
          user="Which countries can you cover?",
          tool_name="list_supported_countries",
          arguments={},
          tool_content="PT, ES, FR, DE, GB, US, BR, JP",
          assistant="I support Portugal, Spain, France, Germany, UK, US, Brazil, Japan and more.",
      ),
      _tool_dialogue(
          lang="en",
          user="Open the world news monitor.",
          tool_name="open_world_monitor",
          arguments={},
          tool_content="World monitor opened.",
          assistant="Opened the world news monitor.",
      ),
      _tool_dialogue(
          lang="en",
          user="Open finance monitor please.",
          tool_name="open_finance_world_monitor",
          arguments={},
          tool_content="Finance monitor opened.",
          assistant="Finance monitor is open in the browser.",
      ),
      _text_dialogue(
          lang="pt",
          user="Explica REST em duas frases.",
          assistant="REST expoe recursos por URL com metodos HTTP. Respostas tipicamente em JSON.",
      ),
      _text_dialogue(
          lang="en",
          user="Explain hash functions briefly.",
          assistant="A hash function maps input to a fixed-size digest. Small input changes produce very different hashes.",
      ),
      _text_dialogue(
          lang="pt",
          user="Abre o monitor.",
          assistant="Queres o monitor mundial de noticias ou o monitor financeiro?",
      ),
  ]
  return rows


def build_sft_dataset(
    seed_rows: list[dict[str, Any]],
    *,
    expand_from_registry: bool = True,
    holdout_ratio: float = 0.15,
    seed: int = 42,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Merge seed + templates, split train/holdout, validate tool names."""
    allowed = _registry_tool_names()
    rows = list(seed_rows)
    if expand_from_registry:
        rows.extend(_template_examples())

    # Deduplicate by user first message
    seen_users: set[str] = set()
    unique: list[dict[str, Any]] = []
    for row in rows:
        user_msg = ""
        for msg in row.get("messages") or []:
            if msg.get("role") == "user":
                user_msg = str(msg.get("content") or "")
                break
        key = user_msg.casefold().strip()
        if key and key in seen_users:
            continue
        if key:
            seen_users.add(key)
        unique.append(row)

    invalid_tools: list[str] = []
    for row in unique:
        for t in row.get("tools") or []:
            if t not in allowed:
                invalid_tools.append(str(t))

    rng = random.Random(seed)
    rng.shuffle(unique)
    n_hold = max(1, int(len(unique) * holdout_ratio)) if unique else 0
    holdout = unique[:n_hold]
    train = unique[n_hold:] or unique

    meta = {
        "total": len(unique),
        "train": len(train),
        "holdout": len(holdout),
        "invalid_tools": sorted(set(invalid_tools)),
        "registry_tools": sorted(allowed),
    }
    return train, holdout, meta


def validate_sft_tools(rows: list[dict[str, Any]]) -> list[str]:
    allowed = _registry_tool_names()
    bad: list[str] = []
    for row in rows:
        for t in row.get("tools") or []:
            if t not in allowed:
                bad.append(str(t))
    return sorted(set(bad))
