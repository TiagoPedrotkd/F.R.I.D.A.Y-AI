"""faster-whisper speech-to-text engine."""

from __future__ import annotations

import logging

import numpy as np

from friday.audio.capture import AudioBuffer
from friday.audio.vad import rms_db

logger = logging.getLogger(__name__)


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

    def _ensure_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel

            compute_type = "float16" if self._device == "cuda" else "int8"
            try:
                self._model = WhisperModel(
                    self._model_size,
                    device=self._device,
                    compute_type=compute_type,
                )
            except Exception:
                logger.warning("CUDA unavailable, falling back to CPU/base model")
                self._model = WhisperModel("base", device="cpu", compute_type="int8")

    def transcribe(self, audio: AudioBuffer, language: str = "pt") -> str:
        self._ensure_model()
        samples = audio.samples.astype(np.float32)
        if samples.size == 0:
            return ""

        segments, info = self._model.transcribe(
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

        if not text:
            logger.warning(
                "STT vazio (duracao=%.1fs, nivel=%.1f dB)",
                audio.duration_seconds,
                rms_db(samples),
            )
        return text
