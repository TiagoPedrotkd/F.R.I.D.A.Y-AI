"""Test which microphone devices receive audio."""

from __future__ import annotations

import sys

import numpy as np
import sounddevice as sd

from friday.audio.vad import rms_db


def main() -> int:
    print()
    best: tuple[float, int, str] | None = None

    for dev in range(len(sd.query_devices())):
        info = sd.query_devices(dev)
        if info["max_input_channels"] < 1:
            continue
        name = info["name"]
        try:
            chunks: list[np.ndarray] = []
            with sd.InputStream(
                device=dev,
                samplerate=16000,
                channels=1,
                dtype="float32",
                blocksize=1600,
            ) as stream:
                for _ in range(30):
                    data, _ = stream.read(1600)
                    chunks.append(data[:, 0])
            level = rms_db(np.concatenate(chunks))
            tag = "OK" if level > -60 else "silencio"
            print(f"  [{dev:2d}] {level:6.1f} dB  {tag:8s}  {name}")
            if level > -60 and (best is None or level > best[0]):
                best = (level, dev, name)
        except Exception as exc:
            print(f"  [{dev:2d}] ERRO   {name}: {exc}")

    print()
    if best:
        print(f"Recomendado: AUDIO_INPUT_DEVICE={best[1]}  # {best[2]}")
        return 0
    print(
        "Nenhum microfone detectou audio. "
        "Verifica permissoes Windows e dispositivo predefinido."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
