"""Enter-triggered utterance capture with WebRTC VAD auto-timeout."""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from functools import partial

import numpy as np
import sounddevice as sd

from friday.audio.capture import AudioBuffer
from friday.audio.portaudio_util import wasapi_extra_for
from friday.audio.preprocess import highpass, noise_gate, preprocess_for_stt
from friday.audio.resample import resample
from friday.audio.vad import rms_db
from friday.audio.webrtc_vad import FRAME_MS, SAMPLES_PER_FRAME, WebRtcVad

logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=1)

TARGET_SR = 16000


def _native_sample_rate(device: int | None) -> int:
    info = sd.query_devices(device, kind="input")
    return int(info["default_samplerate"])


@dataclass
class _VadState:
    speech_chunks: list[np.ndarray] = field(default_factory=list)
    speech_started: bool = False
    silent_run: int = 0
    speech_frames: int = 0
    total_frames: int = 0
    leftover: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.float32))


def _prepare_frame(
    frame: np.ndarray,
    *,
    highpass_hz: float,
    noise_floor_db: float | None,
) -> np.ndarray:
    framed = highpass(frame, cutoff_hz=highpass_hz, sample_rate=TARGET_SR)
    return noise_gate(
        framed,
        calibrated_floor_db=noise_floor_db,
        sample_rate=TARGET_SR,
    )


def _consume_speech_frame(state: _VadState, frame: np.ndarray, is_speech: bool, silence_needed: int) -> bool:
    """Update VAD state; return True when silence timeout reached."""
    state.total_frames += 1
    if is_speech:
        if not state.speech_started:
            logger.info("WebRTC: fala detectada")
        state.speech_started = True
        state.silent_run = 0
        state.speech_frames += 1
        state.speech_chunks.append(frame.copy())
        return False

    if not state.speech_started:
        return False

    state.speech_chunks.append(frame.copy())
    state.silent_run += 1
    return state.silent_run >= silence_needed


def _ingest_block(
    state: _VadState,
    mono: np.ndarray,
    *,
    native_sr: int,
    vad: WebRtcVad,
    highpass_hz: float,
    noise_floor_db: float | None,
    silence_needed: int,
) -> bool:
    """Resample block into 20 ms frames and run VAD. Return True to stop."""
    audio_16k = resample(mono.astype(np.float32), native_sr, TARGET_SR)
    if state.leftover.size:
        audio_16k = np.concatenate([state.leftover, audio_16k])

    n_complete = (audio_16k.size // SAMPLES_PER_FRAME) * SAMPLES_PER_FRAME
    state.leftover = audio_16k[n_complete:].astype(np.float32)
    if n_complete == 0:
        return False

    for i in range(0, n_complete, SAMPLES_PER_FRAME):
        frame = audio_16k[i : i + SAMPLES_PER_FRAME].astype(np.float32)
        framed = _prepare_frame(frame, highpass_hz=highpass_hz, noise_floor_db=noise_floor_db)
        if _consume_speech_frame(state, frame, vad.is_speech_frame(framed), silence_needed):
            return True
    return False


def _record_blocking(
    input_device: int | None,
    max_seconds: float = 8.0,
    *,
    silence_ms: int = 2000,
    vad_mode: int = 3,
    highpass_hz: float = 100.0,
    noise_floor_db: float | None = None,
) -> AudioBuffer:
    native_sr = _native_sample_rate(input_device)
    extra = wasapi_extra_for(input_device)
    native_frame = max(1, int(round(native_sr * FRAME_MS / 1000.0)))
    max_frames = max(1, int(max_seconds * 1000 / FRAME_MS))
    silence_needed = max(1, int(silence_ms / FRAME_MS))
    vad = WebRtcVad(aggressiveness=vad_mode)
    state = _VadState()

    logger.info(
        "A gravar (device %s @ %d Hz, max %.0fs, WebRTC mode=%d, silence=%dms)...",
        input_device if input_device is not None else "default",
        native_sr,
        max_seconds,
        vad_mode,
        silence_ms,
    )

    with sd.InputStream(
        samplerate=native_sr,
        channels=1,
        dtype="float32",
        device=input_device,
        blocksize=native_frame,
        extra_settings=extra,
    ) as stream:
        for _ in range(max_frames):
            block, _overflowed = stream.read(native_frame)
            mono = block[:, 0] if block.ndim > 1 else block.flatten()
            if _ingest_block(
                state,
                mono,
                native_sr=native_sr,
                vad=vad,
                highpass_hz=highpass_hz,
                noise_floor_db=noise_floor_db,
                silence_needed=silence_needed,
            ):
                break

    if not state.speech_chunks or state.speech_frames == 0:
        logger.warning(
            "WebRTC: nenhuma fala (frames=%d) — nao enviar ruido ao Whisper",
            state.total_frames,
        )
        return AudioBuffer(samples=np.array([], dtype=np.float32), sample_rate=TARGET_SR)

    raw = np.concatenate(state.speech_chunks)
    logger.info(
        "WebRTC: speech_frames=%d silence_ms=%d total_frames=%d dur=%.2fs",
        state.speech_frames,
        state.silent_run * FRAME_MS,
        state.total_frames,
        raw.size / TARGET_SR,
    )

    processed = preprocess_for_stt(
        raw,
        highpass_hz=highpass_hz,
        calibrated_floor_db=noise_floor_db,
        sample_rate=TARGET_SR,
    )
    logger.info("Audio preprocessado: %.1f dB RMS", rms_db(processed))
    return AudioBuffer(samples=processed, sample_rate=TARGET_SR)


async def record_utterance(
    input_device: int | None = None,
    max_seconds: float = 8.0,
    *,
    silence_ms: int = 2000,
    vad_mode: int = 3,
    highpass_hz: float = 100.0,
    noise_floor_db: float | None = None,
) -> AudioBuffer:
    loop = asyncio.get_running_loop()
    fn = partial(
        _record_blocking,
        input_device,
        max_seconds,
        silence_ms=silence_ms,
        vad_mode=vad_mode,
        highpass_hz=highpass_hz,
        noise_floor_db=noise_floor_db,
    )
    return await loop.run_in_executor(_executor, fn)
