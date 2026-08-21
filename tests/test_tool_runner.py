"""Tests for LLM tool runner."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock

import pytest

from friday.config import Settings
from friday.llm.tool_runner import ToolRunner, _parse_json_fallback
from friday.skills.registry import default_registry


@dataclass
class FakeFunction:
    name: str
    arguments: str


@dataclass
class FakeToolCall:
    id: str
    function: FakeFunction


@dataclass
class FakeMessage:
    content: str | None = None
    tool_calls: list | None = None

    def model_dump(self, exclude_none=False):
        d: dict[str, Any] = {"role": "assistant"}
        if self.content is not None:
            d["content"] = self.content
        if self.tool_calls:
            d["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in self.tool_calls
            ]
        return d


@dataclass
class FakeChoice:
    message: FakeMessage


@dataclass
class FakeResponse:
    choices: list[FakeChoice]


class FakeLlmClient:
    def __init__(self, responses: list[FakeResponse]):
        self._responses = responses
        self._index = 0
        self.model = "test-model"

    def create_completion(self, **kwargs):
        resp = self._responses[self._index]
        self._index += 1
        return resp


def test_parse_json_fallback_respond():
    action, text, call = _parse_json_fallback(
        '{"action":"respond","text":"Ola!"}'
    )
    assert action == "respond"
    assert text == "Ola!"
    assert call is None


def test_parse_json_fallback_call_tool():
    action, text, call = _parse_json_fallback(
        '{"action":"call_tool","name":"get_current_time","arguments":{}}'
    )
    assert action == "call_tool"
    assert call is not None
    assert call.name == "get_current_time"


@pytest.mark.asyncio
async def test_native_tool_call_then_reply():
    registry = default_registry()
    settings = Settings()
    client = FakeLlmClient(
        [
            FakeResponse(
                [
                    FakeChoice(
                        FakeMessage(
                            tool_calls=[
                                FakeToolCall(
                                    "tc1",
                                    FakeFunction("get_current_time", "{}"),
                                )
                            ]
                        )
                    )
                ]
            ),
            FakeResponse([FakeChoice(FakeMessage(content="Sao 15:00."))]),
        ]
    )
    runner = ToolRunner(settings, registry, client=client)  # type: ignore[arg-type]
    # Avoid intent router: question must not match time/joke patterns
    reply = await runner.chat_with_tools("Qual e a temperatura exterior?")
    assert reply.tool_rounds == 1
    assert "15:00" in reply.text or "Sao" in reply.text


@pytest.mark.asyncio
async def test_json_fallback_respond():
    registry = default_registry()
    settings = Settings()
    client = FakeLlmClient(
        [
            FakeResponse(
                [
                    FakeChoice(
                        FakeMessage(
                            content='{"action":"respond","text":"Estou bem, obrigado."}'
                        )
                    )
                ]
            )
        ]
    )
    runner = ToolRunner(settings, registry, client=client)  # type: ignore[arg-type]
    reply = await runner.chat_with_tools("Como estas?")
    assert "Estou bem" in reply.text
    assert reply.tool_rounds == 0


@pytest.mark.asyncio
async def test_intent_router_bypasses_llm_for_time():
    registry = default_registry()
    settings = Settings()

    class BoomClient:
        model = "test"

        def create_completion(self, **kwargs):
            raise AssertionError("LLM should not be called for time intent")

    runner = ToolRunner(settings, registry, client=BoomClient())  # type: ignore[arg-type]
    reply = await runner.chat_with_tools("Que horas são?")
    assert reply.tool_rounds == 1
    assert "Sao" in reply.text or "sao" in reply.text.casefold()
