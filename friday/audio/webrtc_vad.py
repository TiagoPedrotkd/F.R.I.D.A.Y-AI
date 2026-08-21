"""WebRTC VAD wrapper (Mozilla) for 16 kHz speech frames."""

from __future__ import annotations

import logging

import numpy as np

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000
FRAME_MS = 20
SAMPLES_PER_FRAME = SAMPLE_RATE * FRAME_MS // 1000  # 320


def float_to_pcm16_bytes(frame: np.ndarray) -> bytes:
    """Convert float32 mono frame (-1..1) to little-endian int16 bytes."""
    clipped = np.clip(frame.astype(np.float64), -1.0, 1.0)
    pcm = (clipped * 32767.0).astype(np.int16)
    return pcm.tobytes()


class WebRtcVad:
    """Frame-level VAD using webrtcvad (aggressiveness 0–3)."""

    def __init__(self, aggressiveness: int = 3) -> None:
        import webrtcvad

        mode = max(0, min(3, int(aggressiveness)))
        self._vad = webrtcvad.Vad(mode)
        self.aggressiveness = mode
        self.frame_ms = FRAME_MS
        self.samples_per_frame = SAMPLES_PER_FRAME
        logger.debug("WebRTC VAD mode=%d (%d ms frames)", mode, FRAME_MS)

    def is_speech_frame(self, frame: np.ndarray) -> bool:
        """
        Return True if the frame contains speech.

        frame must be exactly SAMPLES_PER_FRAME samples at 16 kHz float mono.
        """
        if frame.size != SAMPLES_PER_FRAME:
            raise ValueError(
                f"WebRTC frame must be {SAMPLES_PER_FRAME} samples, got {frame.size}"
            )
        return bool(self._vad.is_speech(float_to_pcm16_bytes(frame), SAMPLE_RATE))

    def iter_frames(self, audio_16k: np.ndarray) -> list[np.ndarray]:
        """Split audio into complete 20 ms frames (drop trailing incomplete)."""
        n = (audio_16k.size // SAMPLES_PER_FRAME) * SAMPLES_PER_FRAME
        if n == 0:
            return []
        reshaped = audio_16k[:n].reshape(-1, SAMPLES_PER_FRAME)
        return [reshaped[i].astype(np.float32) for i in range(reshaped.shape[0])]

    def speech_mask(self, audio_16k: np.ndarray) -> list[bool]:
        return [self.is_speech_frame(f) for f in self.iter_frames(audio_16k)]

    def count_trailing_silence_ms(self, speech_flags: list[bool]) -> int:
        """Milliseconds of trailing non-speech frames."""
        trailing = 0
        for flag in reversed(speech_flags):
            if flag:
                break
            trailing += 1
        return trailing * FRAME_MS

    def speech_ratio(self, audio_16k: np.ndarray) -> float:
        flags = self.speech_mask(audio_16k)
        if not flags:
            return 0.0
        return sum(1 for f in flags if f) / len(flags)
