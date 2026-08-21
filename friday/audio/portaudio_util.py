"""Shared PortAudio / WASAPI helpers."""

from __future__ import annotations

import sounddevice as sd


def hostapi_name(device: int | None) -> str:
    if device is None:
        return ""
    try:
        info = sd.query_devices(device)
        return str(sd.query_hostapis(int(info["hostapi"]))["name"])
    except Exception:
        return ""


def is_wasapi_device(device: int | None) -> bool:
    return "wasapi" in hostapi_name(device).casefold()


def wasapi_extra_for(device: int | None):
    """Return WasapiSettings only for WASAPI devices (MME rejects them)."""
    if not is_wasapi_device(device):
        return None
    try:
        return sd.WasapiSettings(exclusive=False)
    except AttributeError:
        return None
