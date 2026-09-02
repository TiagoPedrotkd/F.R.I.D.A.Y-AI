"""Turn / tool latency + request-scoped observability helpers."""

from __future__ import annotations

import json
import logging
import time
import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("friday.obs")

request_id_var: ContextVar[str] = ContextVar("friday_request_id", default="")


def new_request_id() -> str:
    rid = uuid.uuid4().hex[:12]
    request_id_var.set(rid)
    return rid


def get_request_id() -> str:
    return request_id_var.get() or ""


@dataclass
class TurnObs:
    request_id: str = field(default_factory=get_request_id)
    started_at: float = field(default_factory=time.perf_counter)
    tools: list[dict[str, Any]] = field(default_factory=list)
    marks: dict[str, float] = field(default_factory=dict)

    def mark(self, name: str) -> None:
        self.marks[name] = time.perf_counter()

    def tool(self, name: str, *, ms: float, ok: bool) -> None:
        self.tools.append({"name": name, "ms": round(ms, 1), "ok": ok})

    def finish(self, **extra: Any) -> dict[str, Any]:
        total_ms = round((time.perf_counter() - self.started_at) * 1000, 1)
        payload = {
            "event": "chat_turn",
            "request_id": self.request_id or get_request_id(),
            "total_ms": total_ms,
            "tools": self.tools,
            **extra,
        }
        logger.info(json.dumps(payload, ensure_ascii=False))
        try:
            from friday.quality.metrics_dashboard import append_turn_metric

            append_turn_metric(payload)
        except Exception:
            pass
        return payload
