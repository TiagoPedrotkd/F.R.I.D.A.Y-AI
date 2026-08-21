"""Benchmark microphone noise floor and WebRTC speech ratio."""

from __future__ import annotations

import argparse
import sys

import numpy as np
import sounddevice as sd

from friday.audio.devices import _hostapi_name, _is_stereo_mix
from friday.audio.portaudio_util import wasapi_extra_for
from friday.audio.resample import resample
from friday.audio.vad import rms_db
from friday.audio.webrtc_vad import WebRtcVad

TARGET_SR = 16000
_NOISE_WARN_DB = -20.0


def _crest_factor(samples: np.ndarray) -> float:
    if samples.size == 0:
        return 0.0
    peak = float(np.max(np.abs(samples)))
    rms = float(np.sqrt(np.mean(samples.astype(np.float64) ** 2))) + 1e-9
    return peak / rms


def probe_device(index: int, duration: float, vad: WebRtcVad) -> dict | None:
    info = sd.query_devices(index)
    if info["max_input_channels"] < 1:
        return None
    name = str(info["name"])
    if _is_stereo_mix(name):
        return {
            "index": index,
            "name": name,
            "hostapi": _hostapi_name(int(info["hostapi"])),
            "skipped": True,
            "reason": "stereo mix",
        }

    native_sr = int(info["default_samplerate"])
    frames = int(duration * native_sr)
    extra = wasapi_extra_for(index)
    try:
        recording = sd.rec(
            frames,
            samplerate=native_sr,
            channels=1,
            dtype="float32",
            device=index,
            extra_settings=extra,
            blocking=True,
        )
    except Exception as exc:
        return {
            "index": index,
            "name": name,
            "hostapi": _hostapi_name(int(info["hostapi"])),
            "error": str(exc),
        }

    mono = recording[:, 0] if recording.ndim > 1 else recording.flatten()
    audio_16k = resample(mono.astype(np.float32), native_sr, TARGET_SR)
    level = rms_db(audio_16k)
    crest = _crest_factor(audio_16k)
    speech_pct = vad.speech_ratio(audio_16k) * 100.0

    return {
        "index": index,
        "name": name,
        "hostapi": _hostapi_name(int(info["hostapi"])),
        "native_sr": native_sr,
        "rms_db": level,
        "crest": crest,
        "speech_pct": speech_pct,
        "noisy": level > _NOISE_WARN_DB,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Benchmark mic noise + WebRTC VAD")
    parser.add_argument("--duration", type=float, default=5.0, help="Seconds per device")
    parser.add_argument(
        "--device",
        type=int,
        default=None,
        help="Probe only this device index",
    )
    args = parser.parse_args(argv)

    print(
        f"\nMic benchmark ({args.duration:.0f}s/device) — "
        "fica em silencio para medir ruido de fundo.\n"
    )
    vad = WebRtcVad(aggressiveness=3)
    results: list[dict] = []

    indices = (
        [args.device]
        if args.device is not None
        else list(range(len(sd.query_devices())))
    )

    for idx in indices:
        if idx is None:
            continue
        row = probe_device(idx, args.duration, vad)
        if row is None:
            continue
        results.append(row)

        if row.get("skipped"):
            print(f"  [{idx:2d}] SKIP  {row['name']} ({row['reason']})")
            continue
        if "error" in row:
            print(f"  [{idx:2d}] ERRO  {row['name']}: {row['error']}")
            continue

        warn = "  << RUIDO ALTO" if row["noisy"] else ""
        print(
            f"  [{idx:2d}] {row['rms_db']:6.1f} dB  crest={row['crest']:4.1f}  "
            f"webrtc_speech={row['speech_pct']:5.1f}%  "
            f"{row['name']} ({row['hostapi']}){warn}"
        )

    noisy = [r for r in results if r.get("noisy")]
    print()
    if noisy:
        print(
            "Aviso: ruido continuo > -20 dB. Desactiva 'Mistura estereo', "
            "baixa o ganho do microfone, ou testa um USB mic.\n"
            "Ver docs/fase-1/mic-troubleshooting.md"
        )
        return 2

    usable = [r for r in results if "rms_db" in r and r["rms_db"] > -90]
    if usable:
        best = min(usable, key=lambda r: r["rms_db"])
        print(
            f"Mais silencioso: AUDIO_INPUT_DEVICE={best['index']}  "
            f"# {best['name']} ({best['rms_db']:.1f} dB)"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
