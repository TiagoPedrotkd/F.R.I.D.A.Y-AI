"""Download openWakeWord ONNX models if missing."""

from __future__ import annotations

import logging
import urllib.request
from pathlib import Path

logger = logging.getLogger(__name__)

_RELEASE_BASE = "https://github.com/dscripka/openWakeWord/releases/download/v0.5.1"

# Shared feature models + per-keyword wake models
_FEATURE_MODELS = ("melspectrogram.onnx", "embedding_model.onnx")
_WAKE_MODELS = {
    "hey_jarvis": "hey_jarvis_v0.1.onnx",
    "hey_mycroft": "hey_mycroft_v0.1.onnx",
    "hey_rhasspy": "hey_rhasspy_v0.1.onnx",
    "alexa": "alexa_v0.1.onnx",
    "timer": "timer_v0.1.onnx",
    "weather": "weather_v0.1.onnx",
}


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Downloading %s -> %s", dest.name, dest)
    urllib.request.urlretrieve(url, dest)


def ensure_wake_models(keyword: str, models_dir: Path) -> tuple[Path, Path, Path]:
    """Ensure feature + wake ONNX models exist. Returns (melspec, embedding, wake)."""
    wake_dir = models_dir / "wake"
    wake_dir.mkdir(parents=True, exist_ok=True)

    paths: list[Path] = []
    for name in _FEATURE_MODELS:
        dest = wake_dir / name
        if not dest.exists():
            _download(f"{_RELEASE_BASE}/{name}", dest)
        paths.append(dest)

    wake_file = _WAKE_MODELS.get(keyword)
    if wake_file is None:
        # Custom keyword — caller must provide WAKE_MODEL_PATH
        raise ValueError(f"No bundled wake model for '{keyword}'")

    wake_path = wake_dir / wake_file
    if not wake_path.exists():
        _download(f"{_RELEASE_BASE}/{wake_file}", wake_path)

    return paths[0], paths[1], wake_path
