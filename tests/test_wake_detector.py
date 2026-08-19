"""Tests for wake word model resolution."""

import pytest

from friday.wake.detector import resolve_wake_model


def test_builtin_wake_word(tmp_path):
    spec, name = resolve_wake_model("hey_jarvis", tmp_path)
    assert spec == "hey_jarvis"
    assert name == "hey_jarvis"


def test_unknown_wake_word_raises(tmp_path):
    with pytest.raises(ValueError, match="hey_friday"):
        resolve_wake_model("hey_friday", tmp_path)


def test_custom_model_path(tmp_path):
    wake_dir = tmp_path / "wake"
    wake_dir.mkdir()
    model = wake_dir / "hey_friday.onnx"
    model.write_bytes(b"fake")
    spec, name = resolve_wake_model("hey_friday", tmp_path)
    assert spec == str(model)
    assert name == "hey_friday"
