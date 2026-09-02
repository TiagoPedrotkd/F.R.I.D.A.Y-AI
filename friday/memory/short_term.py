"""Short-term conversation memory (in-session) + lightweight session context."""

from __future__ import annotations

from collections import deque
from typing import Any, Callable

from friday.memory.context_budget import estimate_tokens, format_summary_message


class ShortTermMemory:
    """Keeps the last N chat messages, optional rolling summary, and session context."""

    def __init__(
        self,
        max_messages: int = 10,
        *,
        summarize_fn: Callable[[list[dict[str, Any]]], str] | None = None,
        keep_recent: int = 6,
    ) -> None:
        self._max = max_messages
        self._messages: deque[dict[str, Any]] = deque(maxlen=max_messages)
        self.session_summary: str = ""
        self._summarize_fn = summarize_fn
        self._keep_recent = max(2, keep_recent)
        self.last_country: str | None = None
        self.last_news_context: str | None = None  # news | finance | briefing
        self.last_language: str = "pt"
        self.last_monitor_type: str | None = None  # world | finance

    @property
    def messages(self) -> list[dict[str, Any]]:
        return list(self._messages)

    def history_for_llm(self) -> list[dict[str, Any]]:
        """Messages plus optional rolling summary as a leading system note."""
        out: list[dict[str, Any]] = []
        if self.session_summary.strip():
            out.append(format_summary_message(self.session_summary))
        out.extend(self.messages)
        return out

    def add_user(self, text: str) -> None:
        self._maybe_compact_before_append()
        self._messages.append({"role": "user", "content": text})

    def add_assistant(self, text: str) -> None:
        self._maybe_compact_before_append()
        self._messages.append({"role": "assistant", "content": text})

    def _maybe_compact_before_append(self) -> None:
        """When the deque is full, fold oldest turns into session_summary."""
        if len(self._messages) < self._max:
            return
        if len(self._messages) < self._keep_recent + 2:
            return
        overflow = list(self._messages)[: -self._keep_recent]
        if not overflow:
            return
        chunk = self._fold_messages(overflow)
        if self.session_summary:
            self.session_summary = f"{self.session_summary}\n{chunk}".strip()
        else:
            self.session_summary = chunk
        # Cap summary size (~800 tokens worth of chars)
        max_chars = 3200
        if len(self.session_summary) > max_chars:
            self.session_summary = "…\n" + self.session_summary[-(max_chars - 2) :]
        recent = list(self._messages)[-self._keep_recent :]
        self._messages.clear()
        for m in recent:
            self._messages.append(m)

    def _fold_messages(self, msgs: list[dict[str, Any]]) -> str:
        if self._summarize_fn:
            try:
                return self._summarize_fn(msgs).strip()
            except Exception:
                pass
        lines: list[str] = []
        for m in msgs:
            role = m.get("role", "?")
            raw = m.get("content")
            if isinstance(raw, list):
                bits: list[str] = []
                for part in raw:
                    if isinstance(part, dict) and part.get("type") == "text":
                        bits.append(str(part.get("text") or ""))
                    elif isinstance(part, dict) and (
                        part.get("type") == "image_url" or part.get("image_url")
                    ):
                        bits.append("[imagem]")
                    elif isinstance(part, str):
                        bits.append(part)
                content = " ".join(b for b in bits if b).strip().replace("\n", " ")
            else:
                content = str(raw or "").strip().replace("\n", " ")
            if len(content) > 180:
                content = content[:177] + "…"
            if content:
                lines.append(f"- {role}: {content}")
        return "\n".join(lines)

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
        self.session_summary = ""
        self.last_country = None
        self.last_news_context = None
        self.last_language = "pt"
        self.last_monitor_type = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_messages": self._max,
            "messages": self.messages,
            "session_summary": self.session_summary,
            "last_country": self.last_country,
            "last_news_context": self.last_news_context,
            "last_language": self.last_language,
            "last_monitor_type": self.last_monitor_type,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ShortTermMemory:
        mem = cls(max_messages=int(data.get("max_messages") or 10))
        mem.session_summary = str(data.get("session_summary") or "")
        mem.last_country = data.get("last_country")
        mem.last_news_context = data.get("last_news_context")
        mem.last_language = str(data.get("last_language") or "pt")
        mem.last_monitor_type = data.get("last_monitor_type")
        for m in data.get("messages") or []:
            if isinstance(m, dict) and m.get("role") and m.get("content") is not None:
                mem._messages.append(
                    {"role": str(m["role"]), "content": str(m["content"])}
                )
        return mem

    def __len__(self) -> int:
        return len(self._messages)


# re-export for convenience
__all__ = ["ShortTermMemory", "estimate_tokens"]
