"""Disk-backed persistence for agent-api sessions."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from friday.memory.short_term import ShortTermMemory

logger = logging.getLogger(__name__)


class SessionPersistence:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, session_id: str) -> Path:
        safe = "".join(c for c in session_id if c.isalnum() or c in "-_")
        return self.root / f"{safe}.json"

    def save(
        self,
        session_id: str,
        memory: ShortTermMemory,
        *,
        extra: dict[str, Any] | None = None,
    ) -> None:
        payload = {
            "id": session_id,
            "updated_at": time.time(),
            "memory": memory.to_dict(),
            "extra": extra or {},
        }
        path = self.path_for(session_id)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)

    def load(self, session_id: str) -> dict[str, Any] | None:
        path = self.path_for(session_id)
        if not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Failed to load session %s: %s", session_id, exc)
            return None

    def delete(self, session_id: str) -> bool:
        path = self.path_for(session_id)
        if path.is_file():
            path.unlink()
            return True
        return False

    def list_sessions(self, *, limit: int = 50) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for path in sorted(self.root.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            if path.name.endswith(".tmp"):
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            mem = data.get("memory") or {}
            msgs = mem.get("messages") or []
            preview = ""
            for m in reversed(msgs):
                if m.get("role") == "user" and m.get("content"):
                    preview = str(m["content"])[:120]
                    break
            rows.append(
                {
                    "id": data.get("id") or path.stem,
                    "updated_at": data.get("updated_at"),
                    "message_count": len(msgs),
                    "preview": preview,
                    "last_country": mem.get("last_country"),
                    "last_language": mem.get("last_language"),
                }
            )
            if len(rows) >= limit:
                break
        return rows
