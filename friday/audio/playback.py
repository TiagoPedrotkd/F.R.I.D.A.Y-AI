"""Play PCM/WAV audio through default output device."""

from __future__ import annotations

import logging
import wave
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import sounddevice as sd

from friday.audio.resample import resample
from friday.audio.portaudio_util import wasapi_extra_for

logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=1)


def _device_native_sr(device: int | None) -> int | None:
    if device is None:
        return None
    return int(sd.query_devices(device, kind="output")["default_samplerate"])


def _to_mono(audio: np.ndarray) -> np.ndarray:
    if audio.ndim == 1:
        return audio.astype(np.float32, copy=False)
    return audio.mean(axis=1).astype(np.float32)


def _play_wav_blocking(path: Path, output_device: int | None = None) -> None:
    with wave.open(str(path), "rb") as wf:
        sample_rate = wf.getframerate()
        channels = wf.getnchannels()
        frames = wf.readframes(wf.getnframes())
        audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
        if channels > 1:
            audio = audio.reshape(-1, channels)
        audio = _to_mono(audio)

        target_sr = _device_native_sr(output_device)
        if target_sr and target_sr != sample_rate:
            logger.debug(
                "Resampling playback %d Hz -> %d Hz for device %s",
                sample_rate,
                target_sr,
                output_device,
            )
            audio = resample(audio, sample_rate, target_sr)
            sample_rate = target_sr

        extra = wasapi_extra_for(output_device)
        try:
            sd.play(
                audio,
                sample_rate,
                device=output_device,
                extra_settings=extra,
            )
            sd.wait()
        except sd.PortAudioError as exc:
            if output_device is not None:
                logger.warning(
                    "Playback failed on device %s (%s) — retrying system default",
                    output_device,
                    exc,
                )
                sd.play(audio, sample_rate)
                sd.wait()
                return
            raise


def _play_pcm_blocking(
    samples: np.ndarray,
    sample_rate: int,
    output_device: int | None = None,
) -> None:
    audio = _to_mono(samples)
    target_sr = _device_native_sr(output_device)
    if target_sr and target_sr != sample_rate:
        audio = resample(audio, sample_rate, target_sr)
        sample_rate = target_sr
    extra = wasapi_extra_for(output_device)
    sd.play(audio, sample_rate, device=output_device, extra_settings=extra)
    sd.wait()


async def play_wav(path: Path, output_device: int | None = None) -> None:
    import asyncio

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(_executor, _play_wav_blocking, path, output_device)


async def play_pcm(
    samples: np.ndarray,
    sample_rate: int,
    output_device: int | None = None,
) -> None:
    import asyncio

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        _executor,
        _play_pcm_blocking,
        samples,
        sample_rate,
        output_device,
    )
