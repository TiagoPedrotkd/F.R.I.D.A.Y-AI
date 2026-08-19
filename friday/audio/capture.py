"""Audio capture: buffer type and microphone recording with VAD."""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import numpy as np
import sounddevice as sd

from friday.audio.vad import is_silence, rms_db
from friday.pipeline.errors import RecordingTimeoutError

logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=1)

_BLOCK_S = 0.1


@dataclass
class AudioBuffer:
    samples: np.ndarray
    sample_rate: int

    @property
    def is_empty(self) -> bool:
        return self.samples.size == 0

    @property
    def peak_db(self) -> float:
        if self.samples.size == 0:
            return -100.0
        peak = float(np.max(np.abs(self.samples)))
        if peak <= 1e-10:
            return -100.0
        return 20.0 * float(np.log10(peak))

    @property
    def speech_level_db(self) -> float:
        return rms_db(self.samples)

    @property
    def duration_seconds(self) -> float:
        return self.samples.size / self.sample_rate if self.sample_rate else 0.0


def _record_blocking(
    sample_rate: int,
    max_record_seconds: float,
    wait_timeout_seconds: float,
    silence_ms: int,
    silence_threshold_db: float,
    input_device: int | None = None,
    speech_start_db: float | None = None,
    end_drop_db: float = 12.0,
) -> AudioBuffer:
    """Wait for speech, then record until silence or max duration."""
    start_threshold = speech_start_db if speech_start_db is not None else silence_threshold_db
    block_samples = int(sample_rate * _BLOCK_S)
    max_wait_blocks = max(1, int(wait_timeout_seconds / _BLOCK_S))
    max_record_blocks = max(1, int(max_record_seconds / _BLOCK_S))
    silence_blocks_needed = max(1, int(silence_ms / (_BLOCK_S * 1000)))

    chunks: list[np.ndarray] = []
    speech_started = False
    silent_run = 0
    record_blocks = 0
    session_peak_db = -100.0
    noise_floor_db = -100.0
    calibrated = False
    calibrate_blocks = 5  # 0.5s noise floor sample

    with sd.InputStream(
        samplerate=sample_rate,
        channels=1,
        dtype="float32",
        device=input_device,
    ) as stream:
        for block_idx in range(max_wait_blocks + max_record_blocks):
            data, _ = stream.read(block_samples)
            mono = data[:, 0] if data.ndim > 1 else data.flatten()
            level = rms_db(mono)

            if not calibrated:
                noise_floor_db = max(noise_floor_db, level)
                if block_idx + 1 >= calibrate_blocks:
                    calibrated = True
                    if noise_floor_db > -20.0:
                        logger.warning(
                            "Microfone com ruido alto (%.1f dB). "
                            "Desactiva 'Mistura estereo' em Definicoes > Som > Entrada.",
                            noise_floor_db,
                        )
                    else:
                        logger.info("Ruido de fundo: %.1f dB", noise_floor_db)
                continue

            if not speech_started:
                if block_idx >= max_wait_blocks:
                    raise RecordingTimeoutError("Nenhuma fala detectada no tempo limite")
                margin = 4.0 if noise_floor_db > -20.0 else 8.0
                if level < noise_floor_db + margin:
                    continue
                speech_started = True
                session_peak_db = level
                chunks.append(mono.copy())
                record_blocks = 1
                logger.info(
                    "Fala detectada a %.1f dB (fundo %.1f dB, margem %.0f dB)",
                    level,
                    noise_floor_db,
                    margin,
                )
                continue

            chunks.append(mono.copy())
            record_blocks += 1
            session_peak_db = max(session_peak_db, level)

            if record_blocks >= max_record_blocks:
                logger.info("Gravacao limitada a %.0fs", max_record_seconds)
                break

            dropped = session_peak_db - level
            end_of_speech = dropped >= end_drop_db or is_silence(mono, silence_threshold_db)
            if end_of_speech:
                silent_run += 1
                if silent_run >= silence_blocks_needed:
                    break
            else:
                silent_run = 0

    if not chunks:
        return AudioBuffer(samples=np.array([], dtype=np.float32), sample_rate=sample_rate)

    samples = np.concatenate(chunks)
    while chunks and is_silence(chunks[-1], silence_threshold_db):
        chunks.pop()
    if chunks:
        samples = np.concatenate(chunks)

    duration = samples.size / sample_rate
    level = rms_db(samples)
    logger.info("Captured %.2fs at %.1f dB RMS (peak session %.1f dB)", duration, level, session_peak_db)

    if duration > max_record_seconds * 0.95:
        logger.warning(
            "Gravacao longa — possivel ruido continuo no microfone. "
            "Desactiva 'Mistura estereo' nas definicoes de som Windows."
        )

    return AudioBuffer(samples=samples, sample_rate=sample_rate)


async def capture_until_silence(
    sample_rate: int = 16000,
    timeout: float = 10.0,
    silence_ms: int = 800,
    silence_threshold_db: float = -40.0,
    input_device: int | None = None,
    speech_start_db: float | None = None,
    wait_timeout: float | None = None,
) -> AudioBuffer:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        _executor,
        _record_blocking,
        sample_rate,
        timeout,
        wait_timeout if wait_timeout is not None else 15.0,
        silence_ms,
        silence_threshold_db,
        input_device,
        speech_start_db,
    )
