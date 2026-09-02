"""Append-only user feedback store for retraining loops."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class FeedbackStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: dict[str, Any]) -> dict[str, Any]:
        row = {
            "ts": time.time(),
            **record,
        }
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        return row
