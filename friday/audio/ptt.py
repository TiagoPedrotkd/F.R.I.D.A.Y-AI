"""Push-to-talk via Enter key (reliable on Windows)."""

from __future__ import annotations

import asyncio
import logging
import sys

logger = logging.getLogger(__name__)


async def wait_for_enter(prompt: str = "") -> None:
    """Block until user presses Enter in the terminal."""
    msg = prompt or "\n>>> ENTER → fala LOGO em portugues (3-5 segundos)... "
    loop = asyncio.get_running_loop()

    def _read():
        sys.stdout.write(msg)
        sys.stdout.flush()
        input()

    await loop.run_in_executor(None, _read)
    logger.info("ENTER recebido — a gravar")
