"""Resample audio to target sample rate."""

from __future__ import annotations

import numpy as np


def resample(audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    if orig_sr == target_sr:
        return audio.astype(np.float32, copy=False)
    if audio.size == 0:
        return audio.astype(np.float32)
    duration = audio.shape[0] / orig_sr
    target_len = max(1, int(round(duration * target_sr)))
    x_orig = np.linspace(0.0, duration, num=audio.shape[0], endpoint=False)
    x_target = np.linspace(0.0, duration, num=target_len, endpoint=False)
    return np.interp(x_target, x_orig, audio.astype(np.float64)).astype(np.float32)
