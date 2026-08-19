"""Tests for TTS text preparation."""

from friday.tts.piper_engine import prepare_speech_text


def test_strips_markdown():
    text = prepare_speech_text("**Ola** e `isto` e normal.")
    assert "**" not in text
    assert "`" not in text
    assert "Ola" in text


def test_truncates_at_sentence():
    long = "Primeira frase longa. " + "Segunda frase. " + "x" * 400
    result = prepare_speech_text(long, max_chars=80)
    assert result.endswith(".")
    assert len(result) <= 80
