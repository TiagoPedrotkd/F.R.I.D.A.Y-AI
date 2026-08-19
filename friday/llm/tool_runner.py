"""Tool-calling loop with native API and JSON fallback."""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from typing import Any

from friday.config import Settings
from friday.llm.client import LlmClient
from friday.llm.prompts import FRIDAY_SYSTEM_PROMPT, JSON_FALLBACK_INSTRUCTION
from friday.skills.registry import SkillRegistry

logger = logging.getLogger(__name__)


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

    async def chat_with_tools(
        self,
        user_text: str,
        history: list[dict[str, Any]] | None = None,
    ) -> ChatReply:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": FRIDAY_SYSTEM_PROMPT},
        ]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_text})

        tools = self._registry.to_openai_tools()
        rounds = 0
        max_rounds = self._settings.llm_max_tool_rounds

        while rounds <= max_rounds:
            response = self._client.create_completion(
                messages=messages,
                tools=tools if tools else None,
                tool_choice="auto" if tools else None,
                max_tokens=256,
                temperature=0.7,
            )
            message = response.choices[0].message
            tool_calls = _extract_native_tool_calls(message)

            if not tool_calls and message.content:
                action, reply_text, fallback_call = _parse_json_fallback(message.content)
                if action == "call_tool" and fallback_call:
                    tool_calls = [fallback_call]
                elif action == "respond":
                    return ChatReply(
                        text=reply_text or "Desculpa, nao percebi.",
                        tool_rounds=rounds,
                    )

            if not tool_calls:
                reply_text = (message.content or "").strip()
                return ChatReply(text=reply_text or "Desculpa, nao percebi.", tool_rounds=rounds)

            if rounds >= max_rounds:
                return ChatReply(
                    text="Precisei de demasiadas ferramentas para responder.",
                    tool_rounds=rounds,
                )

            messages.append(message.model_dump(exclude_none=True))
            for tc in tool_calls:
                result = await self._registry.execute(tc.name, tc.arguments)
                content = result.content if result.success else f"Error: {result.error}"
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": content,
                    }
                )
            rounds += 1

        return ChatReply(text="Nao consegui completar a resposta.", tool_rounds=rounds)
