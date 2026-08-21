"""Terminal text / Enter helpers."""

from __future__ import annotations

import asyncio
import logging
import sys

logger = logging.getLogger(__name__)


async def wait_for_enter(prompt: str = "") -> None:
    """Block until user presses Enter in the terminal."""
    msg = prompt or (
        "\n>>> ENTER → fala em portugues "
        "(para sozinho apos ~2s de silencio)... "
    )
    loop = asyncio.get_running_loop()

    def _read():
        sys.stdout.write(msg)
        sys.stdout.flush()
        input()

    await loop.run_in_executor(None, _read)
    logger.info("ENTER recebido — a gravar")


async def read_text_line(prompt: str = "") -> str:
    """Read a typed line (for PCs without a microphone)."""
    msg = prompt or "\n>>> Escreve a pergunta e ENTER (sem microfone)... "
    loop = asyncio.get_running_loop()

    def _read() -> str:
        sys.stdout.write(msg)
        sys.stdout.flush()
        return input().strip()

    text = await loop.run_in_executor(None, _read)
    logger.info("Texto recebido: %s", text)
    return text
