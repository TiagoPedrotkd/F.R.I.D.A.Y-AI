"""Tool-calling loop with native API, intent router, and JSON fallback."""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from typing import Any

from friday.config import Settings
from friday.llm.client import LlmClient
from friday.llm.intent_router import match_skill, match_skill_with_args
from friday.llm.prompts import FRIDAY_SYSTEM_PROMPT, JSON_FALLBACK_INSTRUCTION
from friday.skills.registry import SkillRegistry

logger = logging.getLogger(__name__)

_FRIENDLY_FAILURES = (
    "Nao consegui consultar essa informacao neste momento.",
    "A ferramenta nao esta a responder. Quer que tente novamente?",
    "Nao consegui abrir essa pagina.",
    "O servidor local parece estar indisponivel.",
    "Nao encontrei resultados suficientes.",
    "Preciso que confirme o endereco.",
)


@dataclass
class ChatReply:
    text: str
    tool_rounds: int = 0


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


def _parse_tool_arguments(raw: str | dict | None) -> dict[str, Any]:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def _extract_native_tool_calls(message) -> list[ToolCall]:
    calls: list[ToolCall] = []
    for tc in message.tool_calls or []:
        fn = tc.function
        calls.append(
            ToolCall(
                id=tc.id,
                name=fn.name,
                arguments=_parse_tool_arguments(fn.arguments),
            )
        )
    return calls


def _parse_json_fallback(content: str) -> tuple[str, str | None, ToolCall | None]:
    """Returns (action, reply_text, optional ToolCall)."""
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        inner = lines[1:-1] if len(lines) > 2 else lines
        text = "\n".join(inner).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return "respond", content.strip(), None

    action = data.get("action", "respond")
    if action == "call_tool":
        return "call_tool", "", ToolCall(
            id=f"json_{uuid.uuid4().hex[:8]}",
            name=data.get("name", ""),
            arguments=data.get("arguments") or {},
        )
    reply = data.get("text") or data.get("content") or ""
    return "respond", reply, None


def _looks_like_time_refusal(text: str) -> bool:
    lowered = text.casefold()
    markers = (
        "nao tenho acesso",
        "não tenho acesso",
        "tempo real",
        "não consigo obter a hora",
        "nao consigo obter a hora",
        "não posso verificar a hora",
        "nao posso verificar a hora",
        "não tenho informacoes de tempo",
        "nao tenho informacoes de tempo",
        "relógio no seu",
        "relogio no seu",
    )
    return any(m in lowered for m in markers)


def _looks_like_news_refusal(text: str) -> bool:
    lowered = text.casefold()
    markers = (
        "nao tenho acesso a noticias",
        "não tenho acesso a notícias",
        "nao consigo obter noticias",
        "não consigo obter notícias",
        "nao tenho informacoes actualizadas",
        "não tenho informações atualizadas",
        "nao posso consultar noticias",
    )
    return any(m in lowered for m in markers)


def _friendly_skill_error(error: str | None, skill_name: str) -> str:
    if error and error.strip():
        return error.strip()
    if skill_name.startswith("fetch") or skill_name.startswith("open_"):
        return "Nao consegui abrir essa pagina."
    if "news" in skill_name or "search" in skill_name:
        return "Nao consegui consultar essa informacao neste momento."
    return _FRIENDLY_FAILURES[0]


class ToolRunner:
    def __init__(
        self,
        settings: Settings,
        registry: SkillRegistry,
        client: LlmClient | None = None,
    ) -> None:
        self._settings = settings
        self._registry = registry
        self._client = client or LlmClient(settings)

    async def _run_skill_direct(
        self,
        skill_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> ChatReply:
        result = await self._registry.execute(skill_name, arguments or {})
        if not result.success:
            return ChatReply(
                text=_friendly_skill_error(result.error, skill_name),
                tool_rounds=1,
            )
        logger.info("Intent router -> %s", skill_name)
        return ChatReply(text=result.content, tool_rounds=1)

    async def chat_with_tools(
        self,
        user_text: str,
        history: list[dict[str, Any]] | None = None,
    ) -> ChatReply:
        routed = match_skill_with_args(user_text)
        if routed and routed[0] in self._registry.names():
            return await self._run_skill_direct(routed[0], routed[1])

        # Inject long-term memory hints for general conversation
        memory_note = ""
        try:
            from friday.memory.chroma_store import get_shared_store

            store = get_shared_store()
            if store.available:
                hits = store.query(user_text, n=2)
                if hits:
                    memory_note = (
                        "\n\n[Memoria relevante]\n"
                        + "\n".join(f"- {h}" for h in hits)
                    )
        except Exception:
            memory_note = ""

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": FRIDAY_SYSTEM_PROMPT},
            {
                "role": "system",
                "content": JSON_FALLBACK_INSTRUCTION,
            },
        ]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_text + memory_note})

        tools = self._registry.to_openai_tools()
        rounds = 0
        max_rounds = self._settings.llm_max_tool_rounds

        while rounds <= max_rounds:
            response = self._client.create_completion(
                messages=messages,
                tools=tools if tools else None,
                tool_choice="auto" if tools else None,
                max_tokens=512,
                temperature=0.3,
            )
            message = response.choices[0].message
            tool_calls = _extract_native_tool_calls(message)

            if not tool_calls and message.content:
                action, reply_text, fallback_call = _parse_json_fallback(message.content)
                if action == "call_tool" and fallback_call:
                    tool_calls = [fallback_call]
                elif action == "respond":
                    text = reply_text or "Desculpa, nao percebi."
                    if _looks_like_time_refusal(text):
                        return await self._run_skill_direct("get_current_datetime")
                    if _looks_like_news_refusal(text):
                        return await self._run_skill_direct("get_world_news")
                    return ChatReply(text=text, tool_rounds=rounds)

            if not tool_calls:
                reply_text = (message.content or "").strip()
                if _looks_like_time_refusal(reply_text):
                    return await self._run_skill_direct("get_current_datetime")
                if _looks_like_news_refusal(reply_text):
                    return await self._run_skill_direct("get_world_news")
                return ChatReply(text=reply_text or "Desculpa, nao percebi.", tool_rounds=rounds)

            if rounds >= max_rounds:
                return ChatReply(
                    text="Precisei de demasiadas ferramentas para responder.",
                    tool_rounds=rounds,
                )

            messages.append(message.model_dump(exclude_none=True))
            for tc in tool_calls:
                result = await self._registry.execute(tc.name, tc.arguments)
                if result.success:
                    content = result.content
                else:
                    content = _friendly_skill_error(result.error, tc.name)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": content,
                    }
                )
            rounds += 1

        return ChatReply(text="Nao consegui completar a resposta.", tool_rounds=rounds)
