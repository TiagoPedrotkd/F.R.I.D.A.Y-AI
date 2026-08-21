"""Microphone health check and device probing."""

from __future__ import annotations

import logging

import numpy as np
import sounddevice as sd

from friday.audio.portaudio_util import wasapi_extra_for
from friday.audio.vad import rms_db

logger = logging.getLogger(__name__)

_NOISE_FLOOR_WARN_DB = -20.0
_SAMPLE_S = 0.6


def measure_input_level(
    input_device: int | None,
    *,
    seconds: float = _SAMPLE_S,
) -> float | None:
    """
    Return RMS dB of a short input sample, or None if the device cannot open.
    """
    try:
        info = sd.query_devices(input_device, kind="input")
        native_sr = int(info["default_samplerate"])
        frames = int(seconds * native_sr)
        recording = sd.rec(
            frames,
            samplerate=native_sr,
            channels=1,
            dtype="float32",
            device=input_device,
            extra_settings=wasapi_extra_for(input_device),
            blocking=True,
        )
        mono = recording[:, 0] if recording.ndim > 1 else recording.flatten()
        return rms_db(mono)
    except Exception as exc:
        logger.warning(
            "Nao foi possivel medir o microfone (device %s): %s",
            input_device,
            exc,
        )
        return None


def check_input_health(input_device: int | None) -> bool:
    """
    Warn if input looks like stereo mix / saturated noise.
    Returns True if level looks OK for speech capture.
    """
    level = measure_input_level(input_device)
    try:
        name = sd.query_devices(input_device, kind="input")["name"]
    except Exception:
        name = str(input_device)

    if level is None:
        logger.error(
            "Sem microfone utilizavel (%s). "
            "Sem mic fisico o modo voz nao ouve nada — usa VOICE_TRIGGER=text "
            "no .env para escrever em vez de falar, ou liga um microfone USB.",
            name,
        )
        return False

    logger.info("Nivel de entrada (silencio): %.1f dB — %s", level, name)

    if level <= _NOISE_FLOOR_WARN_DB:
        return True

    logger.error(
        "Microfone com sinal continuo alto (%.1f dB). "
        "Provavel causa: Mistura Estereo activa, ganho maximo, ou sem mic "
        "(so colunas — o 'Microfone Realtek' pode ser ruido fantasma).\n"
        "  1. Liga um microfone USB ou headset com mic\n"
        "  2. Ou define VOICE_TRIGGER=text no .env (escrever em vez de falar)\n"
        "  3. Painel de som → desactiva 'Mistura estereo' se nao precisares",
        level,
    )
    return False


def is_likely_loopback_noise(samples: np.ndarray) -> bool:
    """Detect constant loud signal typical of stereo mix / loopback."""
    if samples.size == 0:
        return False
    level = rms_db(samples)
    peak = float(np.max(np.abs(samples)))
    if level > -15.0 and peak > 0.3:
        crest = peak / (float(np.sqrt(np.mean(samples**2))) + 1e-9)
        return crest < 4.0
    return level > -10.0
