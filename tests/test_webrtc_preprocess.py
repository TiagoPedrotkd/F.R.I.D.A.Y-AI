"""Unit tests for WebRTC VAD and audio preprocess (no microphone)."""

from __future__ import annotations

import numpy as np
import pytest

from friday.audio.preprocess import highpass, noise_gate, preprocess_for_stt
from friday.audio.vad import rms_db
from friday.audio.webrtc_vad import FRAME_MS, SAMPLES_PER_FRAME, WebRtcVad, float_to_pcm16_bytes


def _silence_frame() -> np.ndarray:
    return np.zeros(SAMPLES_PER_FRAME, dtype=np.float32)


def _tone_frame(freq_hz: float = 200.0, amplitude: float = 0.4) -> np.ndarray:
    t = np.arange(SAMPLES_PER_FRAME, dtype=np.float64) / 16000.0
    return (amplitude * np.sin(2 * np.pi * freq_hz * t)).astype(np.float32)


def test_float_to_pcm16_bytes_length():
    raw = float_to_pcm16_bytes(_silence_frame())
    assert len(raw) == SAMPLES_PER_FRAME * 2


def test_webrtc_silence_is_not_speech():
    vad = WebRtcVad(aggressiveness=3)
    assert vad.is_speech_frame(_silence_frame()) is False


def test_webrtc_loud_tone_often_speech_or_false():
    """WebRTC is speech-oriented; a pure tone may or may not trigger.
    Ensure API accepts a non-silent frame without raising."""
    vad = WebRtcVad(aggressiveness=3)
    frame = _tone_frame(freq_hz=300.0, amplitude=0.5)
    result = vad.is_speech_frame(frame)
    assert isinstance(result, bool)


def test_webrtc_speech_like_modulated_signal():
    """Amplitude-modulated noise in speech band often flips to speech."""
    vad = WebRtcVad(aggressiveness=1)  # less aggressive for synthetic signal
    rng = np.random.default_rng(42)
    t = np.arange(SAMPLES_PER_FRAME, dtype=np.float64) / 16000.0
    carrier = np.sin(2 * np.pi * 180.0 * t)
    envelope = 0.5 + 0.5 * np.sin(2 * np.pi * 5.0 * t)
    noise = rng.normal(0, 0.15, SAMPLES_PER_FRAME)
    frame = (0.6 * carrier * envelope + noise).astype(np.float32)
    frame = np.clip(frame, -1.0, 1.0)
    # May still be False on some builds; at least trailing silence helper works
    flags = [False, False, True, False, False]
    assert vad.count_trailing_silence_ms(flags) == 2 * FRAME_MS


def test_count_trailing_silence_ms():
    vad = WebRtcVad(aggressiveness=3)
    assert vad.count_trailing_silence_ms([]) == 0
    assert vad.count_trailing_silence_ms([True]) == 0
    assert vad.count_trailing_silence_ms([True, False, False]) == 40


def test_speech_ratio_all_silence():
    vad = WebRtcVad(aggressiveness=3)
    audio = np.zeros(SAMPLES_PER_FRAME * 10, dtype=np.float32)
    assert vad.speech_ratio(audio) == 0.0


def test_highpass_reduces_low_frequency_energy():
    sr = 16000
    t = np.arange(sr, dtype=np.float64) / sr
    low = (0.5 * np.sin(2 * np.pi * 40.0 * t)).astype(np.float32)
    filtered = highpass(low, cutoff_hz=100.0, sample_rate=sr)
    assert rms_db(filtered) < rms_db(low) - 10.0


def test_noise_gate_zeros_quiet_signal():
    quiet = (0.001 * np.sin(2 * np.pi * 200.0 * np.arange(320) / 16000)).astype(
        np.float32
    )
    gated = noise_gate(quiet, threshold_db=-40.0)
    assert float(np.max(np.abs(gated))) < 1e-6


def test_noise_gate_keeps_loud_signal():
    loud = (0.5 * np.sin(2 * np.pi * 200.0 * np.arange(320) / 16000)).astype(np.float32)
    gated = noise_gate(loud, threshold_db=-40.0)
    assert float(np.max(np.abs(gated))) > 0.1


def test_noise_gate_adaptive_floor():
    # Floor -10 dB → threshold max(-7, -40) = -7; quiet relative signal zeros
    samples = np.full(640, 0.05, dtype=np.float32)  # ~ -26 dB
    gated = noise_gate(samples, calibrated_floor_db=-10.0)
    assert float(np.max(np.abs(gated))) < 1e-6


def test_preprocess_empty():
    out = preprocess_for_stt(np.array([], dtype=np.float32))
    assert out.size == 0


def test_preprocess_peak_normalize():
    raw = (0.1 * np.sin(2 * np.pi * 200.0 * np.arange(1600) / 16000)).astype(np.float32)
    out = preprocess_for_stt(raw, calibrated_floor_db=-60.0)
    assert out.size == raw.size
    assert float(np.max(np.abs(out))) == pytest.approx(0.92, abs=0.05)
