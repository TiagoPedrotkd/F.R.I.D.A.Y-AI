"""Audio preprocessing before STT."""

from __future__ import annotations

import numpy as np

from friday.audio.vad import rms_db


def preprocess_for_stt(samples: np.ndarray) -> np.ndarray:
    """High-pass, remove DC, peak-normalize for Whisper."""
    if samples.size == 0:
        return samples.astype(np.float32)

    x = samples.astype(np.float64)
    x = x - np.mean(x)

    # Simple high-pass emphasises speech over low hum
    hp = np.diff(x, prepend=x[0])
    x = 0.65 * x + 0.35 * hp

    peak = float(np.max(np.abs(x)))
    if peak > 1e-6:
        x = x * (0.92 / peak)

    return x.astype(np.float32)


def has_speech_energy(samples: np.ndarray, min_db: float = -50.0) -> bool:
    return rms_db(samples) >= min_db
