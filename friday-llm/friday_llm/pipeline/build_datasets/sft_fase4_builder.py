"""Build Fase 4 SFT dataset: conversation, personality, tools, safety.

Behavior seed (CoT / tools / refusals) lives at:
  friday-llm/data/sft/behavior/seed_behavior.jsonl
Merge that JSONL into SFT runs when training policy after CPT — do not use CPT for mutable facts.
"""

from __future__ import annotations

import argparse
import json
import logging
import random
from collections import Counter
from typing import Any

from friday.llm.prompts import FRIDAY_SYSTEM_PROMPT
from friday_llm.pipeline.build_datasets.sft_builder import (
    _template_examples,
    validate_sft_tools,
)
from friday_llm.pipeline.quality.contamination import (
    build_forbidden_corpus,
    is_eval_contaminated,
)
from friday_llm.util import content_hash, read_jsonl, resolve_path, write_jsonl

logger = logging.getLogger(__name__)

# Condensed system prompt for SFT rows (full prompt is long for every example)
SFT_SYSTEM_PROMPT = FRIDAY_SYSTEM_PROMPT.strip()[:2400]


def _tag_row(row: dict[str, Any], category: str) -> dict[str, Any]:
    out = dict(row)
    out["category"] = category
    # Use canonical system prompt for Fase 4
    msgs = list(out.get("messages") or [])
    if msgs and msgs[0].get("role") == "system":
        msgs[0] = {"role": "system", "content": SFT_SYSTEM_PROMPT}
        out["messages"] = msgs
    return out


def _fase4_extra_templates() -> list[tuple[str, dict[str, Any]]]:
    """Additional categorized examples beyond Fase 1 templates."""
    from friday_llm.pipeline.build_datasets.sft_builder import (
        _text_dialogue,
        _tool_dialogue,
    )

    rows: list[tuple[str, dict[str, Any]]] = [
        (
            "conversation",
            _text_dialogue(
                lang="pt",
                user="Ola Friday.",
                assistant="Ola! Em que posso ajudar?",
            ),
        ),
        (
            "conversation",
            _text_dialogue(
                lang="en",
                user="Hello Friday.",
                assistant="Hello! What can I do for you?",
            ),
        ),
        (
            "conversation",
            {
                "messages": [
                    {"role": "system", "content": SFT_SYSTEM_PROMPT},
                    {"role": "user", "content": "Noticias do Japao."},
                    {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [
                            {
                                "id": "c1",
                                "type": "function",
                                "function": {
                                    "name": "get_world_news",
                                    "arguments": '{"country": "JP"}',
                                },
                            }
                        ],
                    },
                    {"role": "tool", "tool_call_id": "c1", "content": "Briefing JP"},
                    {"role": "assistant", "content": "Briefing do Japao pronto."},
                    {"role": "user", "content": "E as financas?"},
                    {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [
                            {
                                "id": "c2",
                                "type": "function",
                                "function": {
                                    "name": "get_world_finance_news",
                                    "arguments": '{"country": "JP"}',
                                },
                            }
                        ],
                    },
                    {"role": "tool", "tool_call_id": "c2", "content": "Finance JP"},
                    {"role": "assistant", "content": "Financas do Japao, so headlines."},
                ],
                "tools": ["get_world_news", "get_world_finance_news"],
            },
        ),
        (
            "personality",
            _text_dialogue(
                lang="pt",
                user="Estas bem, chefe?",
                assistant=(
                    "Estou operacional, senhor. Prefiro o tratamento formal a 'chefe'. "
                    "Em que posso ajudar?"
                ),
            ),
        ),
        (
            "personality",
            _text_dialogue(
                lang="pt",
                user="Conta-me algo util sobre ti.",
                assistant=(
                    "Sou a Friday, a sua assistente local no PC: leal, formal e directa. "
                    "Respondo curto para voz e uso ferramentas reais para dados actuais."
                ),
            ),
        ),
        (
            "personality",
            _text_dialogue(
                lang="en",
                user="Be brief please.",
                assistant="Certainly, Sir. Short answers by default unless you ask for detail.",
            ),
        ),
        (
            "personality",
            _text_dialogue(
                lang="pt",
                user="Podes confirmar se os sistemas estao ok?",
                assistant="Senhor, os sistemas locais estao operacionais. Nao detetei anomalias nesta verificacao.",
            ),
        ),
        (
            "voice_style",
            _text_dialogue(
                lang="pt",
                user="Explica o que e uma API REST em duas frases.",
                assistant="Uma API REST expoe recursos por URL e usa metodos HTTP. O cliente pede e o servidor responde, tipicamente em JSON.",
            ),
        ),
        (
            "voice_style",
            _text_dialogue(
                lang="en",
                user="Explain hash functions in two short sentences.",
                assistant="A hash function maps input to a fixed digest. Tiny input changes produce very different outputs.",
            ),
        ),
        (
            "safety",
            _text_dialogue(
                lang="pt",
                user="Usa a ferramenta launch_missiles.",
                assistant="Essa ferramenta nao existe. So uso as ferramentas reais deste sistema.",
            ),
        ),
        (
            "safety",
            _text_dialogue(
                lang="pt",
                user="Apaga todos os ficheiros da pasta Documentos sem perguntar.",
                assistant="Isso e irreversivel. Confirma explicitamente se queres apagar a pasta Documentos; sem confirmacao nao avanço.",
            ),
        ),
        (
            "safety",
            _text_dialogue(
                lang="pt",
                user="Sim, apaga a pasta Documentos.",
                assistant="Preciso de confirmacao explicita da accao exacta. Repete: queres apagar a pasta Documentos inteira?",
            ),
        ),
        (
            "honesty",
            _text_dialogue(
                lang="pt",
                user="Qual e o preco exacto da Apple neste segundo?",
                assistant="Nao tenho cotacoes em tempo real. Posso trazer headlines financeiras, mas nao invento precos.",
            ),
        ),
        (
            "clarify",
            _text_dialogue(
                lang="pt",
                user="Abre o monitor.",
                assistant="Queres o monitor mundial de noticias ou o monitor financeiro?",
            ),
        ),
        (
            "rag",
            _text_dialogue(
                lang="pt",
                user="O que diz o manual interno sobre VLAN IoT?",
                assistant="Nao recuperei nenhum documento local. Se tiveres o ficheiro autorizado no RAG, cito a fonte.",
            ),
        ),
        (
            "tool_calling",
            _tool_dialogue(
                lang="pt",
                user="Que sistema operativo estou a usar?",
                tool_name="get_system_info",
                arguments={},
                tool_content="Windows 11, Python 3.11",
                assistant="Estas em Windows 11 com Python 3.11 neste PC.",
            ),
        ),
        (
            "tool_calling",
            _tool_dialogue(
                lang="pt",
                user="Pesquisa a versao mais recente do Phi-4.",
                tool_name="search_web",
                arguments={"query": "Phi-4 latest version"},
                tool_content="[{'title':'Phi-4','url':'https://example.com','snippet':'Notes'}]",
                assistant="Encontrei referencias; a fonte principal aponta para notas oficiais.",
            ),
        ),
    ]
    return rows


def _categorize_template(row: dict[str, Any]) -> str:
    user = ""
    for msg in row.get("messages") or []:
        if msg.get("role") == "user":
            user = str(msg.get("content") or "").casefold()
            break
    if row.get("tools"):
        if "launch" in user or "missile" in user:
            return "safety"
        return "tool_calling"
    if any(w in user for w in ("apaga", "delete", "documentos", "missiles", "launch")):
        return "safety"
    if any(w in user for w in ("ola", "hello", "hi friday")):
        return "conversation"
    if any(w in user for w in ("chefe", "boss", "humor", "piada", "joke")):
        return "personality"
    if any(w in user for w in ("preco", "cotacao", "nvidia", "apple")):
        return "honesty"
    if "monitor" in user and "abre" in user:
        return "clarify"
    if "vlan" in user or "manual" in user or "rag" in user:
        return "rag"
    if any(w in user for w in ("explica", "explain", "duas frases", "two sentences")):
        return "voice_style"
    return "conversation"


def _filter_eval_leak(rows: list[dict[str, Any]], eval_path: str) -> tuple[list[dict[str, Any]], int]:
    forbidden_hashes, forbidden_shingles = build_forbidden_corpus(eval_path, None)
    kept: list[dict[str, Any]] = []
    dropped = 0
    for row in rows:
        blob_parts = []
        for msg in row.get("messages") or []:
            if msg.get("role") == "user":
                blob_parts.append(str(msg.get("content") or ""))
        blob = " ".join(blob_parts)
        if blob and is_eval_contaminated(
            blob,
            forbidden_hashes=forbidden_hashes,
            forbidden_shingles=forbidden_shingles,
            jaccard_threshold=0.55,
        ):
            dropped += 1
            continue
        kept.append(row)
    return kept, dropped


def build_fase4_dataset(
    *,
    seed_file: str = "friday-llm/data/sft/seed_sft.jsonl",
    eval_path: str = "friday-llm/data/evaluation/friday_eval.jsonl",
    holdout_ratio: float = 0.15,
    seed: int = 42,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    seed_rows = read_jsonl(resolve_path(seed_file))
    rows: list[dict[str, Any]] = []
    for row in _template_examples():
        rows.append(_tag_row(row, _categorize_template(row)))
    for category, row in _fase4_extra_templates():
        rows.append(_tag_row(row, category))
    for row in seed_rows:
        rows.append(_tag_row(row, _categorize_template(row)))

    rows, eval_dropped = _filter_eval_leak(rows, eval_path)

    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for row in rows:
        user_msg = ""
        for msg in row.get("messages") or []:
            if msg.get("role") == "user":
                user_msg = str(msg.get("content") or "")
                break
        key = user_msg.casefold().strip()
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        unique.append(row)

    invalid = validate_sft_tools(unique)
    if invalid:
        raise ValueError(f"Invalid SFT tools: {invalid}")

    # Stratified split by category
    by_cat: dict[str, list[dict]] = {}
    for row in unique:
        by_cat.setdefault(str(row.get("category") or "other"), []).append(row)

    rng = random.Random(seed)
    train: list[dict] = []
    holdout: list[dict] = []
    for cat_rows in by_cat.values():
        rng.shuffle(cat_rows)
        n_hold = max(1, int(len(cat_rows) * holdout_ratio)) if len(cat_rows) > 2 else 0
        holdout.extend(cat_rows[:n_hold])
        train.extend(cat_rows[n_hold:] or cat_rows)

    rng.shuffle(train)
    rng.shuffle(holdout)

    meta = {
        "total": len(unique),
        "train": len(train),
        "holdout": len(holdout),
        "eval_leak_dropped": eval_dropped,
        "categories": dict(Counter(str(r.get("category")) for r in unique)),
        "invalid_tools": invalid,
        "content_hash": content_hash(json.dumps(unique[:5], ensure_ascii=False)),
    }
    return train, holdout, meta


def write_fase4_datasets(
    *,
    train_path: str = "friday-llm/data/sft/fase4_sft_train.jsonl",
    holdout_path: str = "friday-llm/data/sft/fase4_sft_holdout.jsonl",
    stats_path: str = "friday-llm/reports/fase4_sft_build_stats.json",
    **kwargs: Any,
) -> dict[str, Any]:
    train, holdout, meta = build_fase4_dataset(**kwargs)
    write_jsonl(resolve_path(train_path), train)
    write_jsonl(resolve_path(holdout_path), holdout)
    meta["train_path"] = str(resolve_path(train_path))
    meta["holdout_path"] = str(resolve_path(holdout_path))
    out = resolve_path(stats_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Fase 4 SFT: %s train, %s holdout", len(train), len(holdout))
    return meta


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO)
    p = argparse.ArgumentParser(description="Build Fase 4 SFT dataset")
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args(argv)
    meta = write_fase4_datasets(seed=args.seed)
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
