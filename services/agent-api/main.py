"""F.R.I.D.A.Y agent API — chat, sessions, SSE, STT/TTS, monitors."""

from __future__ import annotations

import asyncio
import io
import json
import logging
import os
import wave
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import httpx
import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, StreamingResponse
from pydantic import BaseModel, Field

from friday.audio.capture import AudioBuffer
from friday.config import get_settings
from friday.safety.confirmation import PendingAction
from friday.tts.piper_engine import PiperEngine

from session_store import run_chat, store

_MONITORS_DIR = Path(__file__).resolve().parents[2] / "friday" / "monitors"

logger = logging.getLogger(__name__)

APP_VERSION = "0.1.0-phase1"
SERVICE_NAME = "friday-agent-api"
HEALTHCHECK_URL = os.getenv("HEALTHCHECK_URL", "http://127.0.0.1:8080")

# Skills must not open the host browser from the API process
os.environ.setdefault("FRIDAY_NO_BROWSER", "1")

app = FastAPI(title="F.R.I.D.A.Y Agent API", version=APP_VERSION)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
        "tauri://localhost",
        "http://tauri.localhost",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_piper: PiperEngine | None = None
_whisper = None


def _get_piper() -> PiperEngine:
    global _piper
    if _piper is None:
        _piper = PiperEngine(get_settings())
    return _piper


def _get_whisper():
    global _whisper
    if _whisper is None:
        from friday.stt.whisper_engine import WhisperEngine

        s = get_settings()
        # Agent-api defaults to CPU: CUDA without cublas blocks the whole process.
        # Set WHISPER_DEVICE=cuda and FRIDAY_WHISPER_CUDA=1 to opt in.
        device = s.whisper_device
        if device == "cuda" and os.getenv("FRIDAY_WHISPER_CUDA", "").strip().lower() not in (
            "1",
            "true",
            "yes",
        ):
            logger.warning(
                "Whisper: a usar CPU no agent-api (define FRIDAY_WHISPER_CUDA=1 para CUDA)"
            )
            device = "cpu"
        _whisper = WhisperEngine(
            model_size=s.whisper_model if device == "cuda" else min_model(s.whisper_model),
            device=device,
            vad_filter=s.whisper_vad_filter,
        )
    return _whisper


def min_model(name: str) -> str:
    # Keep configured model on CPU unless it's huge; "small" is OK on CPU.
    return name or "base"


class ChatRequest(BaseModel):
    session_id: str
    text: str = Field(min_length=1, max_length=8000)


class ConfirmRequest(BaseModel):
    session_id: str
    decision: Literal["confirm", "cancel"]
    # Optional: seed a pending action for demo / future skills
    action: str | None = None
    target: str | None = None
    summary: str | None = None
    consequences: str | None = None


class TtsRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    session_id: str | None = None


async def _probe_llm() -> dict[str, Any]:
    settings = get_settings()
    # Prefer healthcheck proxy — short timeouts so /v1/status never hangs the UI
    try:
        async with httpx.AsyncClient(timeout=2.5) as client:
            r = await client.get(f"{HEALTHCHECK_URL.rstrip('/')}/health/llm")
            data = r.json()
            ok = r.status_code == 200 and data.get("llm", {}).get("ok", False)
            return {
                "ok": ok,
                "via": "healthcheck",
                "model": data.get("llm", {}).get("model") or settings.lm_studio_model,
                "error": data.get("llm", {}).get("error"),
            }
    except Exception as exc:
        logger.debug("Healthcheck LLM probe failed: %s", exc)

    base = settings.lm_studio_base_url_host.rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=2.5) as client:
            r = await client.get(f"{base}/models")
            ok = r.status_code == 200
            return {
                "ok": ok,
                "via": "lm_studio",
                "model": settings.lm_studio_model,
                "error": None if ok else f"HTTP {r.status_code}",
            }
    except Exception as exc:
        return {
            "ok": False,
            "via": "lm_studio",
            "model": settings.lm_studio_model,
            "error": str(exc),
        }


@app.get("/")
async def root():
    return {
        "service": SERVICE_NAME,
        "version": APP_VERSION,
        "docs": "/docs",
        "status": "/v1/status",
        "ui_hint": "Abre a interface em http://127.0.0.1:5173",
    }


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": SERVICE_NAME,
        "version": APP_VERSION,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@app.get("/v1/status")
async def status():
    llm = await _probe_llm()
    demo = not llm["ok"]
    return {
        "status": "ok" if llm["ok"] else "degraded",
        "service": SERVICE_NAME,
        "version": APP_VERSION,
        "backend": True,
        "llm": llm,
        "demo": demo,
        "auto_open_monitors": get_settings().auto_open_monitors,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@app.post("/v1/sessions")
async def create_session():
    session = store.create()
    return {
        "id": session.id,
        "last_country": session.memory.last_country,
        "last_language": session.memory.last_language,
        "auto_open_monitors": get_settings().auto_open_monitors,
    }


@app.get("/v1/sessions/{session_id}")
async def get_session(session_id: str):
    session = store.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    pending = None
    if session.gate.pending:
        p = session.gate.pending
        pending = {
            "action": p.action,
            "target": p.target,
            "summary": p.summary,
            "consequences": p.consequences,
        }
    return {
        "id": session.id,
        "last_country": session.memory.last_country,
        "last_news_context": session.memory.last_news_context,
        "last_language": session.memory.last_language,
        "last_monitor_type": session.memory.last_monitor_type,
        "pending_confirmation": pending,
        "auto_open_monitors": get_settings().auto_open_monitors,
    }


@app.delete("/v1/sessions/{session_id}")
async def delete_session(session_id: str):
    if not store.delete(session_id):
        raise HTTPException(404, "Session not found")
    return {"ok": True}


@app.post("/v1/chat")
async def chat(body: ChatRequest):
    session = store.get(body.session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    result = await run_chat(session, body.text.strip())
    return result


@app.post("/v1/confirm")
async def confirm(body: ConfirmRequest):
    session = store.get(body.session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    # Allow seeding pending action (demo / API clients)
    if body.action and body.summary and body.target and session.gate.pending is None:
        session.gate.request(
            PendingAction(
                action=body.action,
                target=body.target,
                summary=body.summary,
                consequences=body.consequences or "",
            )
        )

    if session.gate.pending is None:
        raise HTTPException(400, "No pending confirmation")

    text = "sim" if body.decision == "confirm" else "nao"
    status, action = session.gate.interpret(text)
    if status == "confirmed" and action:
        msg = f"Confirmado: {action.summary}."
        session.memory.add_assistant(msg)
        await session.emit("state", {"state": "idle"})
        return {
            "ok": True,
            "decision": "confirmed",
            "reply": msg,
            "action": {
                "action": action.action,
                "target": action.target,
                "summary": action.summary,
            },
        }
    if status == "denied" and action:
        msg = f"Cancelado: {action.summary}."
        session.memory.add_assistant(msg)
        await session.emit("state", {"state": "idle"})
        return {
            "ok": True,
            "decision": "denied",
            "reply": msg,
            "action": {
                "action": action.action,
                "target": action.target,
                "summary": action.summary,
            },
        }
    raise HTTPException(400, "Could not resolve confirmation")


@app.get("/v1/sessions/{session_id}/events")
async def session_events(session_id: str):
    session = store.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    from session_store import event_stream

    return StreamingResponse(
        event_stream(session),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/v1/demo/pending-confirmation")
async def demo_pending(session_id: str, summary: str = "enviar um email de teste"):
    """Seed a pending confirmation for UI / demo testing."""
    session = store.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    msg = session.gate.request(
        PendingAction(
            action="send_email",
            target="demo@example.com",
            summary=summary,
            consequences="A mensagem seria enviada (demo — nao envia de verdade).",
        )
    )
    await session.emit("state", {"state": "awaiting_confirmation"})
    return {
        "reply": msg,
        "pending_confirmation": {
            "action": "send_email",
            "target": "demo@example.com",
            "summary": summary,
            "consequences": "A mensagem seria enviada (demo — nao envia de verdade).",
        },
    }


def _wav_bytes_to_buffer(data: bytes) -> AudioBuffer:
    with wave.open(io.BytesIO(data), "rb") as wf:
        channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        rate = wf.getframerate()
        frames = wf.readframes(wf.getnframes())
    if sampwidth == 2:
        samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    elif sampwidth == 4:
        samples = np.frombuffer(frames, dtype=np.int32).astype(np.float32) / 2147483648.0
    else:
        samples = np.frombuffer(frames, dtype=np.uint8).astype(np.float32) / 128.0 - 1.0
    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1)
    return AudioBuffer(samples=samples, sample_rate=rate)


@app.post("/v1/stt")
async def stt(
    audio: UploadFile = File(...),
    language: str = "pt",
    session_id: str | None = None,
):
    raw = await audio.read()
    if not raw:
        raise HTTPException(400, "Empty audio")
    content_type = (audio.content_type or "").lower()
    filename = (audio.filename or "").lower()
    try:
        if "wav" in content_type or filename.endswith(".wav"):
            buf = _wav_bytes_to_buffer(raw)
        else:
            # Try WAV anyway (frontend should send WAV)
            try:
                buf = _wav_bytes_to_buffer(raw)
            except Exception as exc:
                raise HTTPException(
                    400,
                    "Formato de audio nao suportado. Envia WAV (PCM).",
                ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(400, f"Audio invalido: {exc}") from exc

    if session_id:
        session = store.get(session_id)
        if session:
            await session.emit("state", {"state": "transcribing"})

    try:
        engine = _get_whisper()
        # Never block the asyncio loop with Whisper load/transcribe
        text = await asyncio.to_thread(engine.transcribe, buf, language)
    except Exception as exc:
        logger.exception("STT failed")
        raise HTTPException(503, f"STT indisponivel: {exc}") from exc

    if session_id:
        session = store.get(session_id)
        if session:
            await session.emit("partial_transcript", {"text": text})
            await session.emit("state", {"state": "idle"})

    return {"text": text, "language": language}


@app.post("/v1/tts")
async def tts(body: TtsRequest):
    if body.session_id:
        session = store.get(body.session_id)
        if session:
            await session.emit("state", {"state": "speaking"})
    try:
        wav = await asyncio.to_thread(_get_piper().synthesize_bytes, body.text)
    except Exception as exc:
        logger.exception("TTS failed")
        raise HTTPException(503, f"TTS indisponivel: {exc}") from exc
    finally:
        if body.session_id:
            session = store.get(body.session_id)
            if session:
                await session.emit("state", {"state": "idle"})

    return Response(content=wav, media_type="audio/wav")


def _refresh_snapshot_html(kind: str, country: str | None = None) -> None:
    """Rewrite snapshot HTML from latest JSON so UI chrome stays current."""
    if kind not in ("world", "finance"):
        return
    try:
        from friday.skills.news.countries import get_profile
        from friday.skills.news.rss_common import write_monitor_data

        data_dir = _MONITORS_DIR / "data"
        payload = None
        profile = None
        country_key = (country or "").strip().upper() or None
        if country_key and country_key != "WW":
            country_path = data_dir / f"{kind}_{country_key}.json"
            if country_path.is_file():
                payload = json.loads(country_path.read_text(encoding="utf-8"))
                profile = get_profile(country_key)
        if payload is None:
            # Prefer newest country-specific file
            candidates = sorted(
                data_dir.glob(f"{kind}_*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            for c in candidates:
                if c.name.endswith("_WW.json"):
                    continue
                payload = json.loads(c.read_text(encoding="utf-8"))
                profile = get_profile(str(payload.get("country") or ""))
                break
        if payload is None:
            generic = data_dir / f"{kind}.json"
            if generic.is_file():
                payload = json.loads(generic.read_text(encoding="utf-8"))
                profile = get_profile(str((payload or {}).get("country") or "WW"))
        headlines = (payload or {}).get("headlines") or []
        write_monitor_data(kind, headlines, profile=profile)
    except Exception as exc:
        logger.warning("Snapshot refresh failed for %s: %s", kind, exc)


def _safe_monitor_path(name: str, *, country: str | None = None) -> Path:
    """Resolve monitor file under monitors dir; reject path traversal."""
    if not name or ".." in name or "/" in name or "\\" in name:
        raise HTTPException(400, "Invalid monitor path")
    base = _MONITORS_DIR.resolve()
    target = (base / name).resolve()
    try:
        target.relative_to(base)
    except ValueError as exc:
        raise HTTPException(400, "Invalid monitor path") from exc

    if name.endswith("_snapshot.html"):
        kind = name.replace("_snapshot.html", "")
        if kind in ("world", "finance"):
            from friday.skills.news.rss_common import SNAPSHOT_TEMPLATE_VERSION

            needs_refresh = bool(country)
            if not needs_refresh and not target.is_file():
                needs_refresh = True
            if target.is_file():
                try:
                    text = target.read_text(encoding="utf-8", errors="ignore")
                    if (
                        f'name="friday-snapshot-version" content="{SNAPSHOT_TEMPLATE_VERSION}"'
                        not in text
                    ):
                        needs_refresh = True
                except OSError:
                    needs_refresh = True
            if needs_refresh:
                _refresh_snapshot_html(kind, country=country)

    if not target.is_file() and name.endswith("_snapshot.html"):
        kind = name.replace("_snapshot.html", "")
        if kind in ("world", "finance"):
            try:
                from friday.skills.news.rss_common import write_monitor_data

                write_monitor_data(kind, [])
            except Exception as exc:
                logger.warning("Failed to generate monitor snapshot %s: %s", name, exc)

    if not target.is_file():
        raise HTTPException(404, "Monitor not found")
    return target


@app.get("/monitors/{name}")
async def get_monitor(name: str, country: str | None = None):
    path = _safe_monitor_path(name, country=country)
    return FileResponse(path, media_type="text/html; charset=utf-8")


@app.on_event("startup")
async def _refresh_monitors_on_startup() -> None:
    for kind in ("world", "finance"):
        _refresh_snapshot_html(kind)


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("AGENT_API_PORT", "8090"))
    host = os.getenv("AGENT_API_HOST", "127.0.0.1")
    uvicorn.run("main:app", host=host, port=port, reload=False)
