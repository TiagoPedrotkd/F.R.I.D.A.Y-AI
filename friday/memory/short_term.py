"""Short-term conversation memory (in-session)."""

from __future__ import annotations

from collections import deque
from typing import Any


class ShortTermMemory:
    """Keeps the last N chat messages for LLM context."""

    def __init__(self, max_messages: int = 10) -> None:
        self._max = max_messages
        self._messages: deque[dict[str, Any]] = deque(maxlen=max_messages)

    @property
    def messages(self) -> list[dict[str, Any]]:
        return list(self._messages)

    def add_user(self, text: str) -> None:
        self._messages.append({"role": "user", "content": text})

    def add_assistant(self, text: str) -> None:
        self._messages.append({"role": "assistant", "content": text})

    def clear(self) -> None:
        self._messages.clear()

    def __len__(self) -> int:
        return len(self._messages)
