"""Microphone health check and device probing."""

from __future__ import annotations

import logging

import numpy as np
import sounddevice as sd

from friday.audio.vad import rms_db

logger = logging.getLogger(__name__)

_NOISE_FLOOR_WARN_DB = -20.0
_SAMPLE_S = 0.6


def _wasapi_extra():
    try:
        return sd.WasapiSettings(exclusive=False)
    except AttributeError:
        return None


def measure_input_level(
    input_device: int | None,
    *,
    seconds: float = _SAMPLE_S,
) -> float:
    """Return RMS dB of a short input sample (silence expected)."""
    info = sd.query_devices(input_device, kind="input")
    native_sr = int(info["default_samplerate"])
    frames = int(seconds * native_sr)
    extra = _wasapi_extra()

    recording = sd.rec(
        frames,
        samplerate=native_sr,
        channels=1,
        dtype="float32",
        device=input_device,
        extra_settings=extra,
        blocking=True,
    )
    mono = recording[:, 0] if recording.ndim > 1 else recording.flatten()
    return rms_db(mono)


def check_input_health(input_device: int | None) -> bool:
    """
    Warn if input looks like stereo mix / saturated noise.
    Returns True if level looks OK for speech capture.
    """
    level = measure_input_level(input_device)
    dev = sd.query_devices(input_device, kind="input")
    name = dev["name"]

    logger.info("Nivel de entrada (silencio): %.1f dB — %s", level, name)

    if level <= _NOISE_FLOOR_WARN_DB:
        return True

    logger.error(
        "Microfone com sinal continuo alto (%.1f dB). "
        "Provavel causa: Mistura Estereo activa ou ganho maximo.\n"
        "  1. Windows → Definicoes → Som → Entrada → escolhe 'Microfone Realtek'\n"
        "  2. Painel de controlo → Som → Gravacao → desactiva 'Mistura estereo'\n"
        "  3. Propriedades do microfone → Niveis → baixa o volume para ~70%%\n"
        "  4. Ou define AUDIO_INPUT_DEVICE=1 no .env (MME)",
        level,
    )
    return False


def is_likely_loopback_noise(samples: np.ndarray) -> bool:
    """Detect constant loud signal typical of stereo mix / loopback."""
    if samples.size == 0:
        return False
    level = rms_db(samples)
    peak = float(np.max(np.abs(samples)))
    # Loud and nearly full-scale without dynamic range
    if level > -15.0 and peak > 0.3:
        # Low crest factor: hum/loopback vs speech
        crest = peak / (float(np.sqrt(np.mean(samples**2))) + 1e-9)
        return crest < 4.0
    return level > -10.0
