"""Tests for TTS text preparation."""

from friday.tts.speech_text import prepare_speech_text
from friday.tts.piper_engine import prepare_speech_text as reexport


def test_strips_markdown():
    text = prepare_speech_text("**Ola** e `isto` e normal.")
    assert "**" not in text
    assert "`" not in text
    assert "Ola" in text


def test_replaces_urls():
    text = prepare_speech_text("Veja https://www.example.com/path/long")
    assert "https://" not in text
    assert "example.com" in text


def test_list_to_speech():
    text = prepare_speech_text("- Um\n- Dois\n- Tres")
    assert "-" not in text or "Um" in text
    assert "Um" in text and "Dois" in text


def test_soft_truncates_at_sentence():
    long = "Primeira frase longa. " + "Segunda frase. " + "x" * 2000
    result = prepare_speech_text(long, max_chars=80)
    assert result.endswith(".")
    assert len(result) <= 80


def test_reexport_from_piper():
    assert reexport("**Oi**") == prepare_speech_text("**Oi**")


def test_synthesize_bytes_reads_and_deletes(tmp_path, monkeypatch):
    from friday.config import Settings
    from friday.tts.piper_engine import PiperEngine

    wav = tmp_path / "out.wav"
    wav.write_bytes(b"RIFF....WAVEfmt ")

    engine = PiperEngine(Settings())
    monkeypatch.setattr(engine, "_synthesize_blocking", lambda text: wav)
    data = engine.synthesize_bytes("ola")
    assert data.startswith(b"RIFF")
    assert not wav.exists()
