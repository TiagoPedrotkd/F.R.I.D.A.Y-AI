"""GGUF conversion and quantization via llama.cpp (optional local install)."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from friday_llm.util import resolve_path

logger = logging.getLogger(__name__)


def find_llama_cpp(explicit_path: str | Path | None = None) -> Path | None:
    """Locate llama.cpp install (env, explicit path, or common locations)."""
    candidates: list[Path] = []
    if explicit_path:
        candidates.append(Path(explicit_path))
    env = os.getenv("LLAMA_CPP_PATH", "").strip()
    if env:
        candidates.append(Path(env))
    home = Path.home()
    candidates.extend(
        [
            home / "llama.cpp",
            home / "src" / "llama.cpp",
            Path("C:/llama.cpp"),
            Path("D:/llama.cpp"),
        ]
    )
    which_quant = shutil.which("llama-quantize")
    if which_quant:
        candidates.append(Path(which_quant).parent.parent)

    for root in candidates:
        if not root.is_dir():
            continue
        convert = root / "convert_hf_to_gguf.py"
        if convert.is_file():
            return root
        # Built binary layout
        if (root / "build" / "bin" / "Release" / "llama-quantize.exe").is_file():
            return root
        if (root / "build" / "bin" / "llama-quantize").is_file():
            return root
    return None


def _quantize_binary(llama_root: Path) -> Path | None:
    for rel in (
        "llama-quantize",
        "build/bin/llama-quantize",
        "build/bin/Release/llama-quantize.exe",
        "build/bin/Release/llama-quantize",
    ):
        p = llama_root / rel
        if p.is_file():
            return p
    found = shutil.which("llama-quantize")
    return Path(found) if found else None


def convert_hf_to_gguf(
    merged_dir: str | Path,
    out_f16_gguf: str | Path,
    *,
    llama_cpp_path: str | Path | None = None,
) -> dict[str, Any]:
    """Convert merged HF model to F16 GGUF."""
    llama_root = find_llama_cpp(llama_cpp_path)
    if llama_root is None:
        return {"status": "error", "error": "llama.cpp not found", "path": None}

    convert_script = llama_root / "convert_hf_to_gguf.py"
    if not convert_script.is_file():
        return {
            "status": "error",
            "error": f"convert_hf_to_gguf.py missing in {llama_root}",
            "path": None,
        }

    merged = resolve_path(merged_dir)
    out = resolve_path(out_f16_gguf)
    out.parent.mkdir(parents=True, exist_ok=True)

    cmd = [sys.executable, str(convert_script), str(merged), "--outfile", str(out)]
    logger.info("Running: %s", " ".join(cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        return {
            "status": "error",
            "error": (proc.stderr or proc.stdout or "convert failed")[:500],
            "path": None,
        }
    if not out.is_file():
        return {"status": "error", "error": "GGUF output not created", "path": None}
    return {"status": "ok", "path": str(out), "quant": "f16"}


def quantize_gguf(
    f16_path: str | Path,
    out_path: str | Path,
    quant: str,
    *,
    llama_cpp_path: str | Path | None = None,
) -> dict[str, Any]:
    """Quantize F16 GGUF to target format (e.g. Q4_K_M)."""
    llama_root = find_llama_cpp(llama_cpp_path)
    if llama_root is None:
        return {"status": "error", "error": "llama.cpp not found", "path": None, "quant": quant}

    quant_bin = _quantize_binary(llama_root)
    if quant_bin is None:
        return {
            "status": "error",
            "error": "llama-quantize binary not found",
            "path": None,
            "quant": quant,
        }

    src = resolve_path(f16_path)
    dst = resolve_path(out_path)
    dst.parent.mkdir(parents=True, exist_ok=True)

    cmd = [str(quant_bin), str(src), str(dst), quant]
    logger.info("Running: %s", " ".join(cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        return {
            "status": "error",
            "error": (proc.stderr or proc.stdout or "quantize failed")[:500],
            "path": None,
            "quant": quant,
        }
    if not dst.is_file():
        return {"status": "error", "error": "quantized GGUF not created", "path": None, "quant": quant}
    return {"status": "ok", "path": str(dst), "quant": quant}


def export_gguf_pipeline(
    merged_dir: str | Path,
    gguf_dir: str | Path,
    basename: str,
    quant_levels: list[str],
    *,
    llama_cpp_path: str | Path | None = None,
    skip_if_missing: bool = True,
) -> dict[str, Any]:
    """Full F16 convert + quantize pipeline."""
    llama_root = find_llama_cpp(llama_cpp_path)
    if llama_root is None:
        if skip_if_missing:
            return {
                "status": "skipped",
                "reason": "llama.cpp not found",
                "files": [],
                "errors": [],
            }
        raise FileNotFoundError(
            "llama.cpp not found. Set LLAMA_CPP_PATH or install llama.cpp locally."
        )

    out_dir = resolve_path(gguf_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    f16_path = out_dir / f"{basename}-f16.gguf"

    files: list[dict[str, Any]] = []
    errors: list[str] = []

    conv = convert_hf_to_gguf(merged_dir, f16_path, llama_cpp_path=llama_root)
    if conv["status"] != "ok":
        errors.append(str(conv.get("error")))
        return {"status": "error", "files": files, "errors": errors}

    files.append({"path": conv["path"], "quant": "f16"})

    for quant in quant_levels:
        q_path = out_dir / f"{basename}-{quant}.gguf"
        qres = quantize_gguf(f16_path, q_path, quant, llama_cpp_path=llama_root)
        if qres["status"] == "ok":
            files.append({"path": qres["path"], "quant": quant})
        else:
            errors.append(f"{quant}: {qres.get('error')}")

    status = "converted" if any(f["quant"] != "f16" for f in files) else "partial"
    if errors and not files:
        status = "error"
    elif errors:
        status = "partial"
    return {"status": status, "files": files, "errors": errors}
