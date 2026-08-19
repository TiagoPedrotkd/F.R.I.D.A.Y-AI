"""Piper text-to-speech engine."""

from __future__ import annotations

import asyncio
import logging
import re
import shutil
import subprocess
import tempfile
import wave
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from friday.audio.playback import play_wav
from friday.config import Settings

logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=1)

_MAX_TTS_CHARS = 320


def prepare_speech_text(text: str, max_chars: int = _MAX_TTS_CHARS) -> str:
    """Normalize LLM output for natural TTS playback."""
    cleaned = text.strip()
    cleaned = re.sub(r"```.*?```", "", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"\*\*([^*]+)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"\*([^*]+)\*", r"\1", cleaned)
    cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    if len(cleaned) <= max_chars:
        return cleaned

    cut = cleaned[:max_chars]
    for sep in (". ", "? ", "! ", "; "):
        idx = cut.rfind(sep)
        if idx > max_chars // 2:
            return cut[: idx + 1].strip()
    if len(cleaned) <= max_chars:
        return cut.rstrip()
    return cut[: max_chars - 3].rstrip() + "..."


class PiperEngine:
    def __init__(self, settings: Settings, output_device: int | None = None) -> None:
        self._settings = settings
        self._voice = settings.piper_voice
        self._executable = settings.piper_executable or shutil.which("piper")
        self._voice_instance = None
        self._output_device = output_device

    def _get_voice(self):
        if self._voice_instance is None:
            from piper import PiperVoice

            self._voice_instance = PiperVoice.load(self._voice)
        return self._voice_instance

    def _synthesize_blocking(self, text: str) -> Path:
        speech_text = prepare_speech_text(text)
        if not speech_text:
            raise ValueError("Empty TTS text after normalization")

        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.close()
        out_path = Path(tmp.name)

        if self._executable:
            cmd = [
                self._executable,
                "--model",
                self._voice,
                "--output_file",
                str(out_path),
            ]
            proc = subprocess.run(
                cmd,
                input=speech_text,
                text=True,
                capture_output=True,
                check=False,
            )
            if proc.returncode != 0:
                raise RuntimeError(f"Piper CLI failed: {proc.stderr}")
            return out_path

        voice = self._get_voice()
        with wave.open(str(out_path), "wb") as wf:
            voice.synthesize_wav(speech_text, wf)
        return out_path

    async def speak(self, text: str) -> None:
        if not text.strip():
            return
        loop = asyncio.get_running_loop()
        wav_path = await loop.run_in_executor(
            _executor, self._synthesize_blocking, text
        )
        try:
            await play_wav(wav_path, output_device=self._output_device)
        finally:
            wav_path.unlink(missing_ok=True)
