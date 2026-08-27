"""Piper text-to-speech engine."""

from __future__ import annotations

import asyncio
import logging
import shutil
import subprocess
import tempfile
import wave
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from friday.audio.playback import play_wav
from friday.config import Settings
from friday.tts.speech_text import prepare_speech_text

logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=1)
_REPO_ROOT = Path(__file__).resolve().parents[2]


def resolve_piper_voice(voice: str) -> Path:
    """Resolve PIPER_VOICE against repo root when relative (API cwd differs)."""
    path = Path(voice)
    if path.is_file():
        return path.resolve()
    candidate = (_REPO_ROOT / voice).resolve()
    if candidate.is_file():
        return candidate
    stem = Path(voice).name
    for alt in (
        _REPO_ROOT / "models" / "piper" / stem,
        _REPO_ROOT / "models" / "piper" / f"{stem}.onnx",
    ):
        if alt.is_file():
            return alt.resolve()
    return path


class PiperEngine:
    def __init__(self, settings: Settings, output_device: int | None = None) -> None:
        self._settings = settings
        self._voice = str(resolve_piper_voice(settings.piper_voice))
        self._executable = settings.piper_executable or shutil.which("piper")
        self._voice_instance = None
        self._output_device = output_device

    def _get_voice(self):
        if self._voice_instance is None:
            try:
                from piper import PiperVoice
            except ModuleNotFoundError as exc:
                raise RuntimeError(
                    "Pacote Piper em falta. No venv do projecto: "
                    'pip install -e ".[voice]" '
                    "(ou define PIPER_EXECUTABLE para o binario piper)."
                ) from exc

            model = Path(self._voice)
            if not model.is_file():
                raise RuntimeError(
                    f"Modelo Piper nao encontrado: {self._voice}. "
                    "Confirma PIPER_VOICE no .env (caminho relativo a raiz do repo)."
                )
            self._voice_instance = PiperVoice.load(str(model))
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

    def synthesize_to_path(self, text: str) -> Path:
        """Synthesize speech to a temp WAV file (caller must delete)."""
        return self._synthesize_blocking(text)

    def synthesize_bytes(self, text: str) -> bytes:
        """Return WAV bytes without playing audio."""
        path = self._synthesize_blocking(text)
        try:
            return path.read_bytes()
        finally:
            path.unlink(missing_ok=True)

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
