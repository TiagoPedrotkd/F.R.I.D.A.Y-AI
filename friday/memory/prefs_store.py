"""Server-side user preferences (persisted under data/prefs)."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

_DEFAULTS: dict[str, Any] = {
    "language": "pt",
    "tts_enabled": True,
    "volume": 0.9,
    "rate": 1.0,
    "autoplay": True,
    "interrupt": True,
    "auto_open_monitors": False,
    "high_contrast": False,
    "reduced_motion": False,
    "user_address": None,
    "theme": "dark",
}


class PrefsStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, user_id: str = "default") -> Path:
        safe = "".join(c for c in user_id if c.isalnum() or c in "-_") or "default"
        return self.root / f"{safe}.json"

    def get(self, user_id: str = "default") -> dict[str, Any]:
        path = self._path(user_id)
        data = dict(_DEFAULTS)
        if path.is_file():
            try:
                loaded = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    data.update({k: v for k, v in loaded.items() if k in _DEFAULTS or k == "updated_at"})
            except (OSError, json.JSONDecodeError):
                pass
        return data

    def update(self, patch: dict[str, Any], user_id: str = "default") -> dict[str, Any]:
        current = self.get(user_id)
        for key, value in patch.items():
            if key in _DEFAULTS:
                current[key] = value
        current["updated_at"] = time.time()
        path = self._path(user_id)
        path.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
        return current
