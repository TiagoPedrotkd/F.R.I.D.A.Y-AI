"""Audio input/output device selection for sounddevice."""

from __future__ import annotations

import logging
from typing import Any

import sounddevice as sd

logger = logging.getLogger(__name__)

_STEREO_MIX_HINTS = (
    "mistura",
    "stereo mix",
    "stereo input",
    "what u hear",
    "loopback",
)


def _hostapi_name(hostapi_index: int) -> str:
    try:
        return str(sd.query_hostapis(hostapi_index)["name"])
    except Exception:
        return ""


def _hostapi_priority(hostapi_index: int) -> int:
    name = _hostapi_name(hostapi_index).casefold()
    if "wasapi" in name:
        return 0
    if "wdm-ks" in name:
        return 2
    if "directsound" in name:
        return 3
    if "mme" in name:
        return 4
    return 1


def _is_stereo_mix(name: str) -> bool:
    lowered = name.casefold()
    return any(hint in lowered for hint in _STEREO_MIX_HINTS)


def list_devices() -> list[dict[str, Any]]:
    """Return all host audio devices with index and channel counts."""
    devices = []
    for idx, dev in enumerate(sd.query_devices()):
        devices.append(
            {
                "index": idx,
                "name": dev["name"],
                "hostapi": _hostapi_name(int(dev["hostapi"])),
                "max_input_channels": dev["max_input_channels"],
                "max_output_channels": dev["max_output_channels"],
                "default_samplerate": dev["default_samplerate"],
            }
        )
    return devices


def _normalize(value: str) -> str:
    return value.strip().casefold()


def resolve_device(
    spec: str | int | None,
    *,
    kind: str,
) -> int | None:
    """
    Resolve device spec to a sounddevice index.

    spec: empty/None → system default for kind ('input' or 'output')
          int or numeric string → exact index
          text → substring match (case-insensitive) on device name
    """
    if spec is None or (isinstance(spec, str) and not spec.strip()):
        return None

    if isinstance(spec, int):
        return spec

    text = str(spec).strip()
    if text.isdigit():
        return int(text)

    needle = _normalize(text)
    matches: list[tuple[int, dict]] = []

    for idx, dev in enumerate(sd.query_devices()):
        name = dev["name"]
        if needle not in _normalize(name):
            continue
        if kind == "input" and dev["max_input_channels"] < 1:
            continue
        if kind == "output" and dev["max_output_channels"] < 1:
            continue
        if kind == "input" and _is_stereo_mix(name):
            logger.debug("Skipping stereo mix device [%d]: %s", idx, name)
            continue
        matches.append((idx, dev))

    if not matches:
        available = [
            f"{d['index']}: {d['name']} ({d['hostapi']})"
            for d in list_devices()
            if (kind == "input" and d["max_input_channels"] > 0)
            or (kind == "output" and d["max_output_channels"] > 0)
        ]
        raise ValueError(
            f"No {kind} device matching '{spec}'. "
            f"Run: python -m friday.audio.devices"
        )

    def _priority(item: tuple[int, dict]) -> tuple[int, int]:
        idx, dev = item
        return (_hostapi_priority(int(dev["hostapi"])), idx)

    matches.sort(key=_priority)
    idx, dev = matches[0]
    host = _hostapi_name(int(dev["hostapi"]))
    if len(matches) > 1:
        logger.info(
            "Using %s device [%d]: %s (%s)",
            kind,
            idx,
            dev["name"],
            host,
        )
    else:
        logger.info("Using %s device [%d]: %s (%s)", kind, idx, dev["name"], host)
    return idx


def resolve_input_device(spec: str | int | None) -> int | None:
    return resolve_device(spec, kind="input")


def resolve_output_device(spec: str | int | None) -> int | None:
    return resolve_device(spec, kind="output")


def print_devices() -> None:
    """CLI helper — list input/output devices."""
    print("\n=== Dispositivos de ENTRADA (microfone) ===")
    for d in list_devices():
        if d["max_input_channels"] > 0:
            mix = " [STEREO MIX — evitar]" if _is_stereo_mix(d["name"]) else ""
            print(f"  [{d['index']:2d}] {d['name']} ({d['hostapi']}){mix}")

    print("\n=== Dispositivos de SAIDA (altifalantes) ===")
    for d in list_devices():
        if d["max_output_channels"] > 0:
            print(f"  [{d['index']:2d}] {d['name']} ({d['hostapi']})")

    print(
        "\nRecomendado no .env:\n"
        "  VOICE_TRIGGER=enter\n"
        "  AUDIO_INPUT_DEVICE=Realtek\n"
        "  AUDIO_OUTPUT_DEVICE=Realtek\n"
        "Ou indice WASAPI, ex.: AUDIO_INPUT_DEVICE=21\n"
    )


if __name__ == "__main__":
    print_devices()
