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

__all__ = ["PiperEngine", "resolve_piper_voice", "clamp_length_scale", "prepare_speech_text"]


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


def clamp_length_scale(value: float | None, default: float = 1.0) -> float:
    """Keep Piper length_scale in a safe speakable range."""
    try:
        scale = float(default if value is None else value)
    except (TypeError, ValueError):
        scale = float(default)
    return max(0.5, min(2.0, scale))


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

    def _default_length_scale(self) -> float:
        return clamp_length_scale(getattr(self._settings, "piper_length_scale", 1.0), 1.0)

    def _synthesize_blocking(
        self,
        text: str,
        *,
        length_scale: float | None = None,
        lang: str = "pt",
    ) -> Path:
        speech_text = prepare_speech_text(text, lang=lang)
        if not speech_text:
            raise ValueError("Empty TTS text after normalization")

        scale = clamp_length_scale(
            length_scale if length_scale is not None else self._default_length_scale(),
            self._default_length_scale(),
        )

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
                "--length_scale",
                str(scale),
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
            try:
                from piper.config import SynthesisConfig

                voice.synthesize_wav(
                    speech_text,
                    wf,
                    syn_config=SynthesisConfig(length_scale=scale),
                )
            except TypeError:
                # Older piper without syn_config
                voice.synthesize_wav(speech_text, wf)
            except Exception:
                logger.warning("Piper SynthesisConfig failed; synthesizing without length_scale")
                voice.synthesize_wav(speech_text, wf)
        return out_path

    def synthesize_to_path(
        self,
        text: str,
        *,
        length_scale: float | None = None,
        lang: str = "pt",
    ) -> Path:
        """Synthesize speech to a temp WAV file (caller must delete)."""
        return self._synthesize_blocking(text, length_scale=length_scale, lang=lang)

    def synthesize_bytes(
        self,
        text: str,
        *,
        length_scale: float | None = None,
        lang: str = "pt",
    ) -> bytes:
        """Return WAV bytes without playing audio."""
        path = self._synthesize_blocking(text, length_scale=length_scale, lang=lang)
        try:
            return path.read_bytes()
        finally:
            path.unlink(missing_ok=True)

    async def speak(
        self,
        text: str,
        *,
        length_scale: float | None = None,
        lang: str = "pt",
    ) -> None:
        if not text.strip():
            return
        loop = asyncio.get_running_loop()
        wav_path = await loop.run_in_executor(
            _executor,
            lambda: self._synthesize_blocking(text, length_scale=length_scale, lang=lang),
        )
        try:
            await play_wav(wav_path, output_device=self._output_device)
        finally:
            wav_path.unlink(missing_ok=True)
