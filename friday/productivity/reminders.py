"""Local reminder queue for workflow follow-ups (file-backed)."""

from __future__ import annotations

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

from friday.config import Settings, get_settings


def _path(settings: Settings | None = None) -> Path:
    settings = settings or get_settings()
    return Path(settings.prefs_dir).parent / "reminders" / "queue.jsonl"


def schedule_reminder(
    *,
    title: str,
    fire_at_iso: str,
    message: str,
    settings: Settings | None = None,
) -> dict[str, Any]:
    path = _path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    item = {
        "id": uuid4().hex[:12],
        "title": title,
        "fire_at": fire_at_iso,
        "message": message,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "fired": False,
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")
    return item


def due_reminders(
    settings: Settings | None = None,
    *,
    now: datetime | None = None,
    tz_name: str = "Europe/Lisbon",
) -> list[dict[str, Any]]:
    path = _path(settings)
    if not path.is_file():
        return []
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo("Europe/Lisbon")
    now = now or datetime.now(tz)
    due: list[dict[str, Any]] = []
    kept: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if item.get("fired"):
            kept.append(json.dumps(item, ensure_ascii=False))
            continue
        try:
            fire = datetime.fromisoformat(str(item.get("fire_at") or "").replace("Z", "+00:00"))
            if fire.tzinfo is None:
                fire = fire.replace(tzinfo=tz)
            fire = fire.astimezone(tz)
        except Exception:
            kept.append(json.dumps(item, ensure_ascii=False))
            continue
        if fire <= now:
            item["fired"] = True
            due.append(item)
        kept.append(json.dumps(item, ensure_ascii=False))
    path.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
    return due
