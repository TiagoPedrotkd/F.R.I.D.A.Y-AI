"""faster-whisper speech-to-text engine."""

from __future__ import annotations

import logging

import numpy as np

from friday.audio.capture import AudioBuffer
from friday.audio.vad import rms_db

logger = logging.getLogger(__name__)


def _is_cuda_runtime_error(exc: BaseException) -> bool:
    msg = str(exc).lower()
    needles = (
        "cublas",
        "cuda",
        "cudnn",
        "gpu",
        "nvrtc",
        "cubin",
        "out of memory",
    )
    return any(n in msg for n in needles)


class WhisperEngine:
    def __init__(
        self,
        model_size: str = "small",
        device: str = "cuda",
        vad_filter: bool = False,
    ) -> None:
        self._model_size = model_size
        self._device = device
        self._vad_filter = vad_filter
        self._model = None

    def _load_model(self, device: str, model_size: str):
        from faster_whisper import WhisperModel

        compute_type = "float16" if device == "cuda" else "int8"
        return WhisperModel(model_size, device=device, compute_type=compute_type)

    def _ensure_model(self) -> None:
        if self._model is not None:
            return

        if self._device == "cuda":
            try:
                self._model = self._load_model("cuda", self._model_size)
                logger.info(
                    "Whisper carregado em CUDA (model=%s)", self._model_size
                )
                return
            except Exception as exc:
                logger.warning(
                    "CUDA indisponivel no load (%s) — a usar CPU", exc
                )

        self._device = "cpu"
        # Prefer configured size on CPU when feasible; fall back to base if needed
        try:
            self._model = self._load_model("cpu", self._model_size)
        except Exception:
            logger.warning(
                "Falha a carregar '%s' em CPU — a usar 'base'", self._model_size
            )
            self._model = self._load_model("cpu", "base")
            self._model_size = "base"
        logger.info("Whisper carregado em CPU (model=%s)", self._model_size)

    def _fallback_to_cpu(self, reason: BaseException) -> None:
        logger.warning(
            "Whisper CUDA falhou em runtime (%s) — a recarregar em CPU", reason
        )
        self._model = None
        self._device = "cpu"
        self._ensure_model()

    def _transcribe_once(self, samples: np.ndarray, language: str) -> str:
        segments, _info = self._model.transcribe(
            samples,
            language=language,
            beam_size=5,
            vad_filter=self._vad_filter,
            condition_on_previous_text=False,
            initial_prompt=(
                "Comandos em portugues: que horas sao, conta uma piada, "
                "qual e a data de hoje."
            ),
            no_speech_threshold=0.4,
        )
        parts = [seg.text.strip() for seg in segments if seg.text.strip()]
        text = " ".join(parts)

        if not text and self._vad_filter:
            logger.info("VAD removeu tudo — a tentar sem VAD")
            segments, _ = self._model.transcribe(
                samples,
                language=language,
                beam_size=1,
                vad_filter=False,
                condition_on_previous_text=False,
            )
            parts = [seg.text.strip() for seg in segments if seg.text.strip()]
            text = " ".join(parts)

        return text

    def transcribe(self, audio: AudioBuffer, language: str = "pt") -> str:
        self._ensure_model()
        samples = audio.samples.astype(np.float32)
        if samples.size == 0:
            return ""

        try:
            text = self._transcribe_once(samples, language)
        except Exception as exc:
            if self._device == "cuda" and _is_cuda_runtime_error(exc):
                self._fallback_to_cpu(exc)
                text = self._transcribe_once(samples, language)
            else:
                raise

        if not text:
            logger.warning(
                "STT vazio (duracao=%.1fs, nivel=%.1f dB)",
                audio.duration_seconds,
                rms_db(samples),
            )
        return text
