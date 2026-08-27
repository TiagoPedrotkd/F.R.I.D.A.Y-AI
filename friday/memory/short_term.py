"""Short-term conversation memory (in-session) + lightweight session context."""

from __future__ import annotations

from collections import deque
from typing import Any


class ShortTermMemory:
    """Keeps the last N chat messages and session context for tool continuity."""

    def __init__(self, max_messages: int = 10) -> None:
        self._max = max_messages
        self._messages: deque[dict[str, Any]] = deque(maxlen=max_messages)
        self.last_country: str | None = None
        self.last_news_context: str | None = None  # news | finance | briefing
        self.last_language: str = "pt"
        self.last_monitor_type: str | None = None  # world | finance

    @property
    def messages(self) -> list[dict[str, Any]]:
        return list(self._messages)

    def add_user(self, text: str) -> None:
        self._messages.append({"role": "user", "content": text})

    def add_assistant(self, text: str) -> None:
        self._messages.append({"role": "assistant", "content": text})

    def update_from_skill_metadata(self, metadata: dict[str, Any] | None) -> None:
        if not metadata:
            return
        country = metadata.get("country")
        if country and str(country).upper() not in ("", "WW"):
            self.last_country = str(country).upper()
        kind = metadata.get("kind")
        if kind in ("news", "finance", "briefing"):
            self.last_news_context = str(kind)
        if kind == "monitor":
            mon = metadata.get("auto_open_monitor") or metadata.get("monitor_type")
            if mon in ("world", "finance"):
                self.last_monitor_type = mon
        lang = metadata.get("language")
        if lang:
            self.last_language = str(lang)

    def set_language_hint(self, user_text: str) -> None:
        # Crude: if utterance has many ASCII letters and common EN words, mark en
        lowered = user_text.casefold()
        en_markers = (
            "what time",
            "hello",
            "please",
            "search",
            "news",
            "how are",
            "thank",
        )
        if any(m in lowered for m in en_markers):
            self.last_language = "en"

    def clear(self) -> None:
        self._messages.clear()
        self.last_country = None
        self.last_news_context = None
        self.last_language = "pt"
        self.last_monitor_type = None

    def __len__(self) -> int:
        return len(self._messages)
