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
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, StreamingResponse
from pydantic import BaseModel, Field

from friday.audio.capture import AudioBuffer
from friday.config import get_settings
from friday.obs import new_request_id
from friday.safety.confirmation import PendingAction
from friday.tts.piper_engine import PiperEngine

from session_store import _execute_gated_action, run_chat, run_chat_stream, store

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


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    rid = request.headers.get("x-request-id") or new_request_id()
    request.state.request_id = rid
    response = await call_next(request)
    response.headers["X-Request-Id"] = rid
    return response


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
    stream: bool = False
    # regenerate: drop last assistant turn before answering again
    regenerate: bool = False
    # continue: ask model to continue previous assistant reply
    continue_reply: bool = False


class FeedbackRequest(BaseModel):
    session_id: str
    message_id: str | None = None
    rating: Literal["up", "down", "meh"] = "up"
    reply_text: str | None = None
    user_text: str | None = None
    comment: str | None = None
    grounding_score: float | None = None
    domain: str | None = None
    pillar: str | None = None


class PrefsUpdate(BaseModel):
    language: Literal["pt", "en"] | None = None
    tts_enabled: bool | None = None
    volume: float | None = Field(default=None, ge=0.0, le=1.0)
    rate: float | None = Field(default=None, ge=0.5, le=2.0)
    autoplay: bool | None = None
    interrupt: bool | None = None
    auto_open_monitors: bool | None = None
    high_contrast: bool | None = None
    reduced_motion: bool | None = None
    user_address: str | None = None
    theme: Literal["dark", "light"] | None = None
    productivity_patterns: dict[str, Any] | None = None
    user_profile: dict[str, Any] | None = None
    integrations_enabled: dict[str, Any] | None = None


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
    # UI prefs.rate (1.0 = normal). Mapped to Piper length_scale (inverse feel: higher rate = faster = lower scale).
    rate: float | None = Field(default=None, ge=0.5, le=2.0)
    language: str | None = Field(default=None, max_length=16)


async def _probe_llm() -> dict[str, Any]:
    settings = get_settings()
    # Prefer healthcheck proxy — short timeouts so /v1/status never hangs the UI
    try:
        async with httpx.AsyncClient(timeout=2.5) as client:
            r = await client.get(f"{HEALTHCHECK_URL.rstrip('/')}/health/llm")
            data = r.json()
            ok = r.status_code == 200 and data.get("llm", {}).get("ok", False)
            if ok:
                return {
                    "ok": True,
                    "via": "healthcheck",
                    "model": data.get("llm", {}).get("model") or settings.lm_studio_model,
                    "error": None,
                }
    except Exception as exc:
        logger.debug("Healthcheck LLM probe failed: %s", exc)

    base = settings.lm_studio_base_url_host.rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=2.5) as client:
            r = await client.get(f"{base}/models")
            ok = r.status_code == 200
            if ok:
                return {
                    "ok": True,
                    "via": "lm_studio",
                    "model": settings.lm_studio_model,
                    "error": None,
                }
    except Exception as exc:
        logger.debug("LM Studio probe failed: %s", exc)

    fb = (settings.llm_fallback_base_url or "").strip().rstrip("/")
    if fb:
        try:
            async with httpx.AsyncClient(timeout=2.5) as client:
                r = await client.get(f"{fb}/models")
                if r.status_code == 200:
                    return {
                        "ok": True,
                        "via": "fallback",
                        "model": settings.llm_fallback_model or settings.lm_studio_model,
                        "error": None,
                    }
        except Exception as exc:
            logger.debug("Fallback LLM probe failed: %s", exc)

    return {
        "ok": False,
        "via": "lm_studio",
        "model": settings.lm_studio_model,
        "error": "LLM primary and fallback unavailable",
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


@app.get("/health/ready")
async def health_ready():
    """Deep readiness: LLM reachable, RAG index present, sessions disk writable."""
    settings = get_settings()
    llm = await _probe_llm()
    checks: dict[str, Any] = {"llm": llm}

    # Disk
    sessions = Path(settings.sessions_dir)
    try:
        sessions.mkdir(parents=True, exist_ok=True)
        probe = sessions / ".ready_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        checks["disk"] = {"ok": True, "path": str(sessions)}
    except OSError as exc:
        checks["disk"] = {"ok": False, "error": str(exc)}

    # RAG — filesystem/warm probe only (never load embedding weights here;
    # cold load blocks the single uvicorn worker for minutes).
    try:
        from friday.rag.doc_store import probe_rag_index

        checks["rag"] = probe_rag_index(settings)
    except Exception as exc:
        checks["rag"] = {"ok": False, "error": str(exc)}

    ready = bool(llm.get("ok")) and bool(checks.get("disk", {}).get("ok"))
    return {
        "status": "ready" if ready else "degraded",
        "ready": ready,
        "service": SERVICE_NAME,
        "version": APP_VERSION,
        "checks": checks,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@app.post("/v1/admin/rag-reload")
async def rag_reload():
    from friday.rag.doc_store import reload_doc_store

    store_docs = reload_doc_store(get_settings())
    return {
        "ok": True,
        "backend": store_docs.backend,
        "available": store_docs.available,
    }


@app.get("/v1/alerts")
async def productivity_alerts():
    """Proactive FRIDAY suggestions (rate-limited)."""
    from friday.productivity.alerts import compute_alerts
    from friday.productivity.context import build_productivity_context

    settings = get_settings()
    ctx = build_productivity_context(settings)
    alerts = compute_alerts(settings, ctx=ctx)
    return {"alerts": alerts, "context_time": ctx.get("current_time")}


@app.get("/v1/metrics/summary")
async def metrics_summary():
    from friday.quality.metrics_dashboard import summarize_metrics

    return summarize_metrics()


@app.get("/v1/metrics/dashboard")
async def metrics_dashboard():
    from friday.quality.metrics_dashboard import render_dashboard_html, summarize_metrics

    html = render_dashboard_html(summarize_metrics())
    return Response(content=html, media_type="text/html; charset=utf-8")


@app.post("/v1/admin/feedback-export")
async def feedback_export():
    from friday.quality.feedback_to_datasets import export_feedback_datasets

    settings = get_settings()
    return export_feedback_datasets(settings.feedback_path)


@app.get("/v1/status")
async def status():
    llm = await _probe_llm()
    demo = not llm["ok"]
    settings = get_settings()
    return {
        "status": "ok" if llm["ok"] else "degraded",
        "service": SERVICE_NAME,
        "version": APP_VERSION,
        "backend": True,
        "llm": llm,
        "demo": demo,
        "auto_open_monitors": settings.auto_open_monitors,
        "web_source_required": settings.web_source_required,
        "fallback_configured": bool(settings.llm_fallback_base_url),
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


@app.get("/v1/sessions")
async def list_sessions(limit: int = 40):
    return {"sessions": store.list_summaries(limit=max(1, min(limit, 100)))}


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
            "preview": getattr(p, "preview", None) or {},
        }
    return {
        "id": session.id,
        "last_country": session.memory.last_country,
        "last_news_context": session.memory.last_news_context,
        "last_language": session.memory.last_language,
        "last_monitor_type": session.memory.last_monitor_type,
        "pending_confirmation": pending,
        "auto_open_monitors": get_settings().auto_open_monitors,
        "messages": session.memory.messages,
        "session_summary": session.memory.session_summary,
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

    text = body.text.strip()
    if body.regenerate:
        # Remove last assistant message so we redo from last user turn
        msgs = session.memory.messages
        if msgs and msgs[-1].get("role") == "assistant":
            session.memory._messages.pop()
        if msgs and session.memory.messages and session.memory.messages[-1].get("role") == "user":
            text = str(session.memory.messages[-1]["content"])
            session.memory._messages.pop()
    elif body.continue_reply:
        text = (
            "Continua a resposta anterior de forma natural, sem repetir o que ja disseste."
            if not text or text in ("continuar", "continua", "continue")
            else text
        )

    if body.stream:
        return StreamingResponse(
            run_chat_stream(session, text),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    result = await run_chat(session, text)
    return result


@app.post("/v1/uploads")
async def upload_file(
    session_id: str,
    file: UploadFile = File(...),
):
    """Accept text/markdown/pdf/image attachments for the next chat turn context."""
    from friday.safety.uploads import (
        detect_kind,
        extract_text_payload,
        safe_filename,
        session_upload_bytes,
    )

    session = store.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    settings = get_settings()
    upload_dir = Path(settings.sessions_dir).parent / "uploads" / session_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    max_file = 8_000_000
    max_session = 32_000_000
    if session_upload_bytes(upload_dir) > max_session:
        raise HTTPException(413, "Quota de anexos da sessao excedida (max 32MB)")

    safe = safe_filename(file.filename or "upload.bin")
    data = await file.read()
    if len(data) > max_file:
        raise HTTPException(413, "Ficheiro demasiado grande (max 8MB)")
    if not data:
        raise HTTPException(400, "Ficheiro vazio")

    content_type = (file.content_type or "").lower()
    kind, mime = detect_kind(data, safe, content_type)

    # Reject claimed images/PDFs that fail magic-byte validation
    claimed_image = content_type.startswith("image/") or safe.lower().endswith(
        (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp")
    )
    claimed_pdf = safe.lower().endswith(".pdf") or content_type == "application/pdf"
    if claimed_image and kind != "image":
        raise HTTPException(400, "Anexo rejeitado: assinatura de imagem invalida")
    if claimed_pdf and kind != "pdf":
        raise HTTPException(400, "Anexo rejeitado: PDF invalido")

    dest = upload_dir / safe
    dest.write_bytes(data)

    extracted = extract_text_payload(data, kind, safe)
    vision = False

    if kind == "text":
        session.memory.add_user(f"Anexo (text): {safe}\n{extracted}".strip())
    elif kind == "image":
        vision = bool(settings.llm_vision_enabled)
        session.pending_attachments.append(
            {
                "path": str(dest),
                "filename": safe,
                "kind": "image",
                "mime": mime,
            }
        )
    elif kind == "pdf":
        session.memory.add_user(f"Anexo (pdf): {safe}\n{extracted}".strip())
    else:
        session.memory.add_user(f"Anexo (file): {safe}\n{extracted}".strip())

    store._save(session)
    return {
        "ok": True,
        "filename": safe,
        "kind": kind,
        "mime": mime or None,
        "vision": vision,
        "pending": len(session.pending_attachments),
        "chars": len(extracted),
        "preview": extracted[:400],
        # Do not expose absolute filesystem paths to the client
    }


@app.post("/v1/feedback")
async def feedback(body: FeedbackRequest):
    from friday.llm.domain_router import route_domains
    from friday.llm.quality import update_domain_stats
    from friday.quality.feedback import FeedbackStore

    settings = get_settings()
    domain = body.domain
    pillar = body.pillar
    ranked = None
    if (not domain or not pillar) and body.user_text:
        ranked = route_domains(body.user_text)
        if ranked:
            if not domain:
                domain = ranked[0]["domain"]
            if not pillar:
                pillar = ranked[0].get("pillar")
    if not domain:
        domain = "general"
    fb = FeedbackStore(settings.feedback_path)
    row = fb.append(
        {
            "session_id": body.session_id,
            "message_id": body.message_id,
            "rating": body.rating,
            "reply_text": (body.reply_text or "")[:4000],
            "user_text": (body.user_text or "")[:2000],
            "comment": (body.comment or "")[:1000],
            "grounding_score": body.grounding_score,
            "domain": domain,
            "pillar": pillar,
        }
    )
    try:
        stats_path = Path(settings.feedback_path).parent / "domain_stats.json"
        update_domain_stats(stats_path, domain or "general", body.rating)
    except Exception:
        pass
    return {"ok": True, "stored": row}


@app.get("/v1/specialists")
async def list_specialists_endpoint():
    from friday.llm.specialists_registry import list_specialists

    return {"specialists": list_specialists()}


@app.get("/v1/prefs")
async def get_prefs(user_id: str = "default"):
    from friday.llm.prompts import PROMPT_VERSION
    from friday.memory.prefs_store import PrefsStore

    settings = get_settings()
    prefs = PrefsStore(settings.prefs_dir).get(user_id)
    return {"user_id": user_id, "prefs": prefs, "prompt_version": PROMPT_VERSION}


@app.put("/v1/prefs")
async def put_prefs(body: PrefsUpdate, user_id: str = "default"):
    from friday.memory.prefs_store import PrefsStore

    settings = get_settings()
    store = PrefsStore(settings.prefs_dir)
    patch = {k: v for k, v in body.model_dump().items() if v is not None}
    if isinstance(patch.get("user_profile"), dict):
        current = store.get(user_id)
        merged = dict(current.get("user_profile") or {})
        merged.update(patch["user_profile"])
        patch["user_profile"] = merged
    if isinstance(patch.get("integrations_enabled"), dict):
        current = store.get(user_id)
        merged_i = dict(current.get("integrations_enabled") or {})
        merged_i.update(patch["integrations_enabled"])
        patch["integrations_enabled"] = merged_i
    if isinstance(patch.get("productivity_patterns"), dict):
        current = store.get(user_id)
        merged = dict(current.get("productivity_patterns") or {})
        merged.update(patch["productivity_patterns"])
        patch["productivity_patterns"] = merged
    prefs = store.update(patch, user_id=user_id)
    return {"user_id": user_id, "prefs": prefs}


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
        msg, meta, next_pending = await _execute_gated_action(
            action, get_settings(), session
        )
        session.memory.add_assistant(msg)
        await session.emit(
            "state",
            {"state": "awaiting_confirmation" if next_pending else "idle"},
        )
        return {
            "ok": True,
            "decision": "confirmed",
            "reply": msg,
            "metadata": meta,
            "pending_confirmation": {
                "action": next_pending.action,
                "target": next_pending.target,
                "summary": next_pending.summary,
                "consequences": next_pending.consequences,
                "preview": next_pending.preview,
            }
            if next_pending
            else None,
            "action": {
                "action": action.action,
                "target": action.target,
                "summary": action.summary,
            },
        }
    if status == "denied" and action:
        session.workflow = None
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
        # prefs.rate > 1 → speak faster → slightly lower Piper length_scale
        length_scale = None
        if body.rate is not None:
            length_scale = max(0.5, min(2.0, 1.0 / float(body.rate)))
        lang = (body.language or "pt").strip() or "pt"
        piper = _get_piper()
        wav = await asyncio.to_thread(
            lambda: piper.synthesize_bytes(
                body.text,
                length_scale=length_scale,
                lang=lang,
            )
        )
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
    asyncio.create_task(_periodic_productivity_alerts())


async def _periodic_productivity_alerts() -> None:
    """Push proactive alerts to live sessions every ~60s (rate-limited inside compute)."""
    await asyncio.sleep(5)
    while True:
        try:
            from friday.productivity.alerts import compute_alerts
            from friday.productivity.context import build_productivity_context

            settings = get_settings()
            ctx = build_productivity_context(settings)
            alerts = compute_alerts(settings, ctx=ctx)
            if alerts:
                for session in store.active_sessions():
                    await session.emit("alerts", {"alerts": alerts})
        except Exception as exc:
            logger.debug("periodic alerts: %s", exc)
        await asyncio.sleep(60)


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("AGENT_API_PORT", "8090"))
    host = os.getenv("AGENT_API_HOST", "127.0.0.1")
    uvicorn.run("main:app", host=host, port=port, reload=False)
