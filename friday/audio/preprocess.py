"""Audio preprocessing before STT / WebRTC VAD."""

from __future__ import annotations

import numpy as np
from scipy.signal import butter, sosfilt

from friday.audio.vad import rms_db

_SAMPLE_RATE = 16000
_sos_cache: dict[tuple[int, int], np.ndarray] = {}


def _highpass_sos(cutoff_hz: float, sample_rate: int = _SAMPLE_RATE) -> np.ndarray:
    key = (int(cutoff_hz), int(sample_rate))
    if key not in _sos_cache:
        _sos_cache[key] = butter(4, cutoff_hz, btype="high", fs=sample_rate, output="sos")
    return _sos_cache[key]


def highpass(
    samples: np.ndarray,
    cutoff_hz: float = 100.0,
    sample_rate: int = _SAMPLE_RATE,
) -> np.ndarray:
    if samples.size == 0:
        return samples.astype(np.float32)
    filtered = sosfilt(_highpass_sos(cutoff_hz, sample_rate), samples.astype(np.float64))
    return filtered.astype(np.float32)


def noise_gate(
    samples: np.ndarray,
    *,
    threshold_db: float = -40.0,
    calibrated_floor_db: float | None = None,
    sample_rate: int = _SAMPLE_RATE,
) -> np.ndarray:
    """Zero 20 ms chunks whose RMS is below an adaptive threshold."""
    if samples.size == 0:
        return samples.astype(np.float32)

    if calibrated_floor_db is not None:
        threshold_db = max(calibrated_floor_db + 3.0, -40.0)

    frame = max(1, int(sample_rate * 0.02))
    out = samples.astype(np.float32).copy()
    for start in range(0, out.size, frame):
        chunk = out[start : start + frame]
        if rms_db(chunk) < threshold_db:
            out[start : start + frame] = 0.0
    return out


def peak_normalize(samples: np.ndarray, target_peak: float = 0.92) -> np.ndarray:
    if samples.size == 0:
        return samples.astype(np.float32)
    peak = float(np.max(np.abs(samples)))
    if peak <= 1e-6:
        return samples.astype(np.float32)
    return (samples.astype(np.float64) * (target_peak / peak)).astype(np.float32)


def preprocess_for_stt(
    samples: np.ndarray,
    *,
    highpass_hz: float = 100.0,
    calibrated_floor_db: float | None = None,
    sample_rate: int = _SAMPLE_RATE,
) -> np.ndarray:
    """Remove DC, high-pass, adaptive noise gate, peak-normalize."""
    if samples.size == 0:
        return samples.astype(np.float32)

    x = samples.astype(np.float64)
    x = x - np.mean(x)
    x = highpass(x.astype(np.float32), cutoff_hz=highpass_hz, sample_rate=sample_rate)
    x = noise_gate(
        x,
        calibrated_floor_db=calibrated_floor_db,
        sample_rate=sample_rate,
    )
    return peak_normalize(x)


def has_speech_energy(samples: np.ndarray, min_db: float = -50.0) -> bool:
    return rms_db(samples) >= min_db
