"""openWakeWord wake-word detector."""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from collections.abc import AsyncIterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

from friday.wake.setup_models import ensure_wake_models

logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=1)

_BUILTIN_WAKE_WORDS = frozenset(
    {"alexa", "hey_mycroft", "hey_jarvis", "hey_rhasspy", "timer", "weather"}
)


def resolve_wake_model(
    keyword: str,
    models_dir: Path,
    model_path: str = "",
    inference_framework: str = "tflite",
) -> tuple[str, str]:
    """Return (model_spec, display_name) for openWakeWord Model."""
    if model_path:
        path = Path(model_path)
        if not path.is_absolute():
            path = models_dir / path
        if path.exists():
            return str(path), path.stem
        raise FileNotFoundError(f"Wake model not found: {path}")

    wake_dir = models_dir / "wake"
    for ext in (".onnx", ".tflite"):
        candidate = wake_dir / f"{keyword}{ext}"
        if candidate.exists():
            return str(candidate), keyword

    if keyword in _BUILTIN_WAKE_WORDS:
        return keyword, keyword

    available = ", ".join(sorted(_BUILTIN_WAKE_WORDS))
    raise ValueError(
        f"Wake word '{keyword}' has no pretrained model. "
        f"Use a built-in name ({available}), set WAKE_MODEL_PATH to a custom "
        f".onnx/.tflite file, or place models/wake/{keyword}.onnx. "
        f"For testing without wake-word, set VOICE_PUSH_TO_TALK=true."
    )


class WakeDetector:
    """Listens continuously and yields when wake keyword is detected."""

    def __init__(
        self,
        keyword: str = "hey_jarvis",
        threshold: float = 0.5,
        sample_rate: int = 16000,
        push_to_talk: bool = False,
        models_dir: Path | None = None,
        model_path: str = "",
        inference_framework: str = "tflite",
        input_device: int | None = None,
        trigger_mode: str = "wake",
        speech_threshold_db: float = -42.0,
    ) -> None:
        self._keyword = keyword
        self._threshold = threshold
        self._sample_rate = sample_rate
        self._push_to_talk = push_to_talk
        self._models_dir = models_dir or Path("models")
        self._model_path = model_path
        self._inference_framework = inference_framework
        self._input_device = input_device
        self._trigger_mode = trigger_mode.strip().lower()
        self._speech_threshold_db = speech_threshold_db
        self._model = None
        self._resolved_name = keyword
        self._listening = threading.Event()
        self._listening.set()
        self._stop = threading.Event()

    def pause(self) -> None:
        """Release mic so capture/TTS can use audio devices exclusively."""
        self._listening.clear()

    def resume(self) -> None:
        """Resume wake-word listening after a turn completes."""
        if self._model is not None:
            self._model.reset()
        self._listening.set()

    def _ensure_model(self):
        if self._model is None:
            from openwakeword.model import Model

            spec, display = resolve_wake_model(
                self._keyword,
                self._models_dir,
                self._model_path,
                self._inference_framework,
            )
            self._resolved_name = display

            framework = self._inference_framework
            model_kwargs: dict = {}

            if framework == "tflite":
                try:
                    import tflite_runtime  # noqa: F401
                except ImportError:
                    logger.warning(
                        "tflite-runtime not found; falling back to ONNX inference"
                    )
                    framework = "onnx"

            if (
                framework == "onnx"
                and not Path(spec).exists()
                and spec in _BUILTIN_WAKE_WORDS
            ):
                melspec, embedding, wake_path = ensure_wake_models(
                    spec, self._models_dir
                )
                spec = str(wake_path)
                model_kwargs = {
                    "melspec_model_path": str(melspec),
                    "embedding_model_path": str(embedding),
                }
            elif framework == "onnx" and Path(spec).exists():
                melspec, embedding, _ = ensure_wake_models(
                    "hey_jarvis", self._models_dir
                )
                model_kwargs = {
                    "melspec_model_path": str(melspec),
                    "embedding_model_path": str(embedding),
                }

            logger.info(
                "Loading wake model '%s' (framework=%s)",
                display,
                framework,
            )
            self._model = Model(
                wakeword_models=[spec],
                inference_framework=framework,
                **model_kwargs,
            )

    def _listen_loop(self, queue: asyncio.Queue[str], loop: asyncio.AbstractEventLoop):
        import sounddevice as sd

        self._ensure_model()
        chunk_samples = 1280  # 80ms @ 16kHz

        while not self._stop.is_set():
            if not self._listening.is_set():
                time.sleep(0.05)
                continue

            try:
                with sd.InputStream(
                    samplerate=self._sample_rate,
                    channels=1,
                    dtype="float32",
                    blocksize=chunk_samples,
                    device=self._input_device,
                ) as stream:
                    logger.info(
                        "Wake-word listening on device %s",
                        self._input_device if self._input_device is not None else "default",
                    )
                    ticks = 0
                    while self._listening.is_set() and not self._stop.is_set():
                        data, _ = stream.read(chunk_samples)
                        mono = data[:, 0] if data.ndim > 1 else data.flatten()
                        pcm = (mono * 32767).astype(np.int16)
                        predictions = self._model.predict(pcm)
                        ticks += 1
                        if ticks % 25 == 0:
                            top = max(predictions.values()) if predictions else 0.0
                            from friday.audio.vad import rms_db
                            logger.debug(
                                "Mic level=%.1f dB wake_max=%.2f",
                                rms_db(mono),
                                top,
                            )
                        for name, score in predictions.items():
                            if score >= self._threshold:
                                logger.info(
                                    "Wake word detected: %s (%.2f)", name, score
                                )
                                self._listening.clear()
                                asyncio.run_coroutine_threadsafe(
                                    queue.put(name), loop
                                )
                                return
            except Exception:
                if not self._stop.is_set():
                    logger.exception("Wake listen iteration failed")
                time.sleep(0.2)

    def _speech_listen_loop(
        self, queue: asyncio.Queue[str], loop: asyncio.AbstractEventLoop
    ):
        """Start a turn when the user speaks (any language)."""
        import sounddevice as sd

        from friday.audio.vad import is_silence, rms_db

        chunk_samples = 1600  # 100ms @ 16kHz
        speech_blocks = 0
        blocks_needed = 2  # ~200ms of speech

        while not self._stop.is_set():
            if not self._listening.is_set():
                time.sleep(0.05)
                continue

            try:
                with sd.InputStream(
                    samplerate=self._sample_rate,
                    channels=1,
                    dtype="float32",
                    blocksize=chunk_samples,
                    device=self._input_device,
                ) as stream:
                    logger.info(
                        "Modo voz: fala em portugues (device %s)",
                        self._input_device if self._input_device is not None else "default",
                    )
                    ticks = 0
                    while self._listening.is_set() and not self._stop.is_set():
                        data, _ = stream.read(chunk_samples)
                        mono = data[:, 0] if data.ndim > 1 else data.flatten()
                        ticks += 1
                        if ticks % 20 == 0:
                            logger.info(
                                "A escutar... mic=%.0f dB (fala para activar)",
                                rms_db(mono),
                            )
                        if is_silence(mono, self._speech_threshold_db):
                            speech_blocks = 0
                            continue
                        speech_blocks += 1
                        if speech_blocks >= blocks_needed:
                            logger.info("Voz detectada — a gravar")
                            self._listening.clear()
                            asyncio.run_coroutine_threadsafe(
                                queue.put("speech"), loop
                            )
                            return
            except Exception:
                if not self._stop.is_set():
                    logger.exception("Speech listen iteration failed")
                time.sleep(0.2)

    async def listen(self) -> AsyncIterator[str]:
        if self._push_to_talk or self._trigger_mode == "push":
            while True:
                logger.info(">>> Push-to-talk: fala agora...")
                await asyncio.sleep(2.0)
                yield "push_to_talk"
            return

        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[str] = asyncio.Queue()
        use_speech = self._trigger_mode == "speech"

        def _run():
            try:
                while not self._stop.is_set():
                    if use_speech:
                        self._speech_listen_loop(queue, loop)
                    else:
                        self._listen_loop(queue, loop)
            except Exception:
                logger.exception("Wake detector failed")

        loop.run_in_executor(_executor, _run)
        while True:
            event = await queue.get()
            yield event
