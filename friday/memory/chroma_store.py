"""Long-term memory stub — Chroma integration planned for Fase 1.4."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ChromaStore:
    """Interface-only stub for cross-session memory."""

    def __init__(self, persist_dir: str | None = None) -> None:
        self._persist_dir = persist_dir
        self._available = False
        logger.info("ChromaStore stub initialized (Fase 1.4)")

    @property
    def available(self) -> bool:
        return self._available

    def add(self, text: str, metadata: dict[str, Any] | None = None) -> None:
        pass

    def query(self, text: str, n: int = 3) -> list[str]:
        return []

    def close(self) -> None:
        pass
