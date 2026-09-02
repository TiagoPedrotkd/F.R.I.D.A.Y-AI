"""Streaming chat helpers: single-pass stream with optional tool-call accumulation."""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AccumulatedToolCall:
    id: str = ""
    name: str = ""
    arguments: str = ""

    def to_tool_call_dict(self) -> dict[str, Any]:
        return {
            "id": self.id or f"call_{self.name}",
            "type": "function",
            "function": {
                "name": self.name,
                "arguments": self.arguments or "{}",
            },
        }


@dataclass
class StreamResult:
    content: str = ""
    tool_calls: list[AccumulatedToolCall] = field(default_factory=list)

    @property
    def has_tools(self) -> bool:
        return bool(self.tool_calls and any(t.name for t in self.tool_calls))


def accumulate_stream_chunk(
    state: StreamResult,
    chunk: Any,
    *,
    tool_bufs: dict[int, AccumulatedToolCall],
) -> str | None:
    """
    Update StreamResult from one OpenAI stream chunk.
    Returns text delta if any (for live UI tokens).
    """
    try:
        choice = chunk.choices[0]
        delta = choice.delta
    except (IndexError, AttributeError):
        return None

    text = getattr(delta, "content", None)
    if text:
        state.content += text
        return text

    raw_tools = getattr(delta, "tool_calls", None) or []
    for tc in raw_tools:
        idx = int(getattr(tc, "index", 0) or 0)
        buf = tool_bufs.get(idx)
        if buf is None:
            buf = AccumulatedToolCall()
            tool_bufs[idx] = buf
        tid = getattr(tc, "id", None)
        if tid:
            buf.id = str(tid)
        fn = getattr(tc, "function", None)
        if fn is not None:
            name = getattr(fn, "name", None)
            if name:
                buf.name = str(name)
            args = getattr(fn, "arguments", None)
            if args:
                buf.arguments += str(args)
    return None


def finalize_tool_bufs(
    state: StreamResult, tool_bufs: dict[int, AccumulatedToolCall]
) -> None:
    if not tool_bufs:
        return
    state.tool_calls = [tool_bufs[i] for i in sorted(tool_bufs)]


def parse_tool_arguments(raw: str) -> dict[str, Any]:
    try:
        data = json.loads(raw or "{}")
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}
