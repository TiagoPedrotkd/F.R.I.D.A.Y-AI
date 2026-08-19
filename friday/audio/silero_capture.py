"""Reliable recording with relative energy VAD (works with noisy Windows mics)."""

from __future__ import annotations

from functools import partial

import numpy as np
import sounddevice as sd

from friday.audio.capture import AudioBuffer
from friday.audio.preprocess import preprocess_for_stt
from friday.audio.resample import resample
from friday.audio.vad import is_silence, rms_db

logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=1)

TARGET_SR = 16000
_BLOCK_S = 0.1
_CALIBRATE_S = 0.4


def _wasapi_extra():
    try:
        return sd.WasapiSettings(exclusive=False)
    except AttributeError:
        return None


def _native_sample_rate(device: int | None) -> int:
    info = sd.query_devices(device, kind="input")
    return int(info["default_samplerate"])


def _record_blocking(
    input_device: int | None,
    max_seconds: float = 8.0,
    *,
    silence_ms: int = 900,
    end_drop_db: float = 6.0,
    noise_floor_db: float | None = None,
) -> AudioBuffer:
    native_sr = _native_sample_rate(input_device)
    extra = _wasapi_extra()
    block_frames = max(1, int(_BLOCK_S * native_sr))
    calibrate_blocks = 0 if noise_floor_db is not None else max(1, int(_CALIBRATE_S / _BLOCK_S))
    max_blocks = max(1, int(max_seconds / _BLOCK_S))
    silence_blocks = max(1, int(silence_ms / (_BLOCK_S * 1000)))

    logger.info(
        "A gravar (device %s @ %d Hz, max %.0fs)...",
        input_device if input_device is not None else "default",
        native_sr,
        max_seconds,
    )

    chunks: list[np.ndarray] = []
    floor_db = noise_floor_db if noise_floor_db is not None else -100.0
    speech_started = False
    session_peak_db = -100.0
    silent_run = 0
    record_blocks = 0

    if calibrate_blocks == 0:
        margin = 2.0 if floor_db > -15.0 else 6.0
        start_threshold = floor_db + margin
        logger.info(
            "Usando ruido de fundo pre-calibrado: %.1f dB (margem +%.0f dB)",
            floor_db,
            margin,
        )

    with sd.InputStream(
        samplerate=native_sr,
        channels=1,
        dtype="float32",
        device=input_device,
        blocksize=block_frames,
        extra_settings=extra,
    ) as stream:
        for block_idx in range(calibrate_blocks + max_blocks):
            block, _overflowed = stream.read(block_frames)
            mono = block[:, 0] if block.ndim > 1 else block.flatten()
            level = rms_db(mono)

            if block_idx < calibrate_blocks:
                floor_db = max(floor_db, level)
                continue

            if block_idx == calibrate_blocks:
                margin = 2.0 if floor_db > -15.0 else 6.0
                logger.info(
                    "Ruido de fundo: %.1f dB (margem fala +%.0f dB)",
                    floor_db,
                    margin,
                )
                start_threshold = floor_db + margin
                continue

            if not speech_started:
                if level < start_threshold:
                    continue
                speech_started = True
                session_peak_db = level
                chunks.append(mono.copy())
                record_blocks = 1
                logger.info(
                    "Fala detectada a %.1f dB (fundo %.1f dB)",
                    level,
                    floor_db,
                )
                continue

            chunks.append(mono.copy())
            record_blocks += 1
            session_peak_db = max(session_peak_db, level)

            if record_blocks >= max_blocks:
                break

            dropped = session_peak_db - level
            if dropped >= end_drop_db or is_silence(mono, floor_db + 2.0):
                silent_run += 1
                if silent_run >= silence_blocks:
                    logger.info("Fim de frase apos %.2fs", sum(c.size for c in chunks) / native_sr)
                    break
            else:
                silent_run = 0

    if not chunks:
        logger.warning("Nenhuma fala detectada acima do ruido de fundo")
        return AudioBuffer(samples=np.array([], dtype=np.float32), sample_rate=TARGET_SR)

    mono = np.concatenate(chunks)
    duration = mono.size / native_sr
    level = rms_db(mono)
    logger.info(
        "Gravacao: %.2fs a %.1f dB RMS (pico %.1f dB)",
        duration,
        level,
        session_peak_db,
    )

    audio_16k = resample(mono, native_sr, TARGET_SR)
    processed = preprocess_for_stt(audio_16k)
    logger.info("Audio preprocessado: %.1f dB RMS", rms_db(processed))

    return AudioBuffer(samples=processed, sample_rate=TARGET_SR)


async def record_utterance(
    input_device: int | None = None,
    max_seconds: float = 8.0,
    noise_floor_db: float | None = None,
) -> AudioBuffer:
    loop = asyncio.get_running_loop()
    fn = partial(
        _record_blocking,
        input_device,
        max_seconds,
        silence_ms=900,
        end_drop_db=6.0,
        noise_floor_db=noise_floor_db,
    )
    return await loop.run_in_executor(_executor, fn)
