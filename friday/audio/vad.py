"""Voice activity detection helpers."""

from __future__ import annotations

import numpy as np


def rms_db(samples: np.ndarray) -> float:
    if samples.size == 0:
        return -100.0
    rms = float(np.sqrt(np.mean(samples.astype(np.float64) ** 2)))
    if rms <= 1e-10:
        return -100.0
    return 20.0 * float(np.log10(rms))


def is_silence(samples: np.ndarray, threshold_db: float = -40.0) -> bool:
    return rms_db(samples) < threshold_db
