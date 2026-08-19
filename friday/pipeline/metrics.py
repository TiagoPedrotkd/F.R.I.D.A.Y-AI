"""Per-turn latency instrumentation."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class LatencyMetrics:
    """Tracks stage timestamps for one conversational turn."""

    started_at: float = field(default_factory=time.perf_counter)
    marks: dict[str, float] = field(default_factory=dict)

    @classmethod
    def start(cls) -> LatencyMetrics:
        return cls()

    def mark(self, name: str) -> None:
        self.marks[name] = time.perf_counter()

    def _ms_since(self, start_key: str, end_key: str) -> int | None:
        if start_key not in self.marks or end_key not in self.marks:
            return None
        return int((self.marks[end_key] - self.marks[start_key]) * 1000)

    def summary(self) -> dict:
        end = self.marks.get("tts_end", time.perf_counter())
        total_ms = int((end - self.started_at) * 1000)
        capture_ms = self._ms_since("started", "capture_end")
        stt_ms = self._ms_since("capture_end", "stt_end")
        llm_ms = self._ms_since("stt_end", "llm_end")
        tts_ms = self._ms_since("llm_end", "tts_end")
        return {
            "event": "turn_complete",
            "wake_to_tts_ms": total_ms,
            "capture_ms": capture_ms,
            "stt_ms": stt_ms,
            "llm_ms": llm_ms,
            "tts_ms": tts_ms,
        }

    def log(self) -> None:
        self.mark("tts_end") if "tts_end" not in self.marks else None
        payload = self.summary()
        logger.info(json.dumps(payload, ensure_ascii=False))
