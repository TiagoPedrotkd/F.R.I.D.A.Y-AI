"""Agent API session store and helpers."""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator

from friday.config import Settings, get_settings
from friday.llm.prompts import PROMPT_VERSION
from friday.llm.tool_runner import ToolRunner
from friday.memory.session_persistence import SessionPersistence
from friday.memory.short_term import ShortTermMemory
from friday.safety.confirmation import ConfirmationGate, PendingAction
from friday.skills.registry import default_registry


async def _execute_gated_action(
    action: PendingAction, settings: Settings, session: "Session | None" = None
) -> tuple[str, dict[str, Any], PendingAction | None]:
    """Run confirmed skill payload; returns (reply, metadata, next_pending)."""
    next_pending: PendingAction | None = None
    if not action.payload:
        msg = f"Confirmado: {action.summary}."
        meta: dict[str, Any] = {"kind": "confirmation", "decision": "confirmed"}
    else:
        registry = default_registry(settings)
        args = dict(action.payload)
        args["confirmed"] = True
        result = await registry.execute(action.action, args)
        if result.success:
            msg = result.content or f"Confirmado: {action.summary}."
            meta = {
                "kind": "confirmation",
                "decision": "confirmed",
                "executed": action.action,
                **(result.metadata or {}),
            }
        else:
            err = result.error or "falha ao executar"
            msg = f"Confirmado, mas falhou: {err}"
            meta = {
                "kind": "confirmation",
                "decision": "confirmed",
                "error": err,
            }

    if session is not None and session.workflow:
        session.workflow.index += 1
        if not session.workflow.done():
            next_pending = session.workflow.to_pending()
            if next_pending:
                session.gate.request(next_pending)
                msg = f"{msg}\n\nProximo passo: {next_pending.prompt_message()}"
        else:
            session.workflow = None
    return msg, meta, next_pending


def _pending_from_skill_meta(meta: dict[str, Any] | None) -> PendingAction | None:
    if not meta or meta.get("kind") != "confirmation_required":
        return None
    pending = meta.get("pending") or {}
    if not pending.get("action"):
        return None
    return PendingAction(
        action=str(pending["action"]),
        target=str(pending.get("target") or ""),
        summary=str(pending.get("summary") or ""),
        consequences=str(pending.get("consequences") or ""),
        payload=dict(pending.get("payload") or {}),
        preview=dict(pending.get("preview") or {}),
    )


def _pending_dict(p: PendingAction | None) -> dict[str, Any] | None:
    if p is None:
        return None
    return {
        "action": p.action,
        "target": p.target,
        "summary": p.summary,
        "consequences": p.consequences,
        "preview": p.preview or {},
    }


@dataclass
class Session:
    id: str
    memory: ShortTermMemory
    gate: ConfirmationGate
    created_at: float = field(default_factory=time.time)
    event_queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    pending_attachments: list[dict[str, Any]] = field(default_factory=list)
    workflow: Any = None

    async def emit(self, event_type: str, data: dict[str, Any] | None = None) -> None:
        await self.event_queue.put(
            {"type": event_type, "data": data or {}, "ts": time.time()}
        )

    def take_attachments(self) -> list[dict[str, Any]]:
        """Consume pending uploads for the next chat turn."""
        items = list(self.pending_attachments)
        self.pending_attachments.clear()
        return items


class SessionStore:
    def __init__(self, persist_dir: Path | None = None) -> None:
        self._sessions: dict[str, Session] = {}
        settings = get_settings()
        root = Path(persist_dir or settings.sessions_dir)
        self._persist = SessionPersistence(root)

    def create(self) -> Session:
        sid = uuid.uuid4().hex
        session = Session(
            id=sid,
            memory=ShortTermMemory(max_messages=get_settings().max_context_messages),
            gate=ConfirmationGate(),
        )
        self._sessions[sid] = session
        self._save(session)
        return session

    def get(self, session_id: str) -> Session | None:
        hit = self._sessions.get(session_id)
        if hit:
            return hit
        data = self._persist.load(session_id)
        if not data:
            return None
        mem = ShortTermMemory.from_dict(data.get("memory") or data)
        session = Session(
            id=session_id,
            memory=mem,
            gate=ConfirmationGate(),
            created_at=float(data.get("updated_at") or time.time()),
        )
        self._sessions[session_id] = session
        return session

    def active_sessions(self) -> list[Session]:
        return list(self._sessions.values())

    def delete(self, session_id: str) -> bool:
        self._persist.delete(session_id)
        return self._sessions.pop(session_id, None) is not None

    def list_summaries(self, *, limit: int = 50) -> list[dict[str, Any]]:
        return self._persist.list_sessions(limit=limit)

    def _save(self, session: Session) -> None:
        try:
            self._persist.save(session.id, session.memory)
        except OSError:
            pass


store = SessionStore()


def _friendly_tool_label(name: str) -> str:
    labels = {
        "get_current_datetime": "A consultar a hora",
        "get_world_news": "A consultar as noticias",
        "get_world_finance_news": "A consultar noticias financeiras",
        "get_country_briefing": "A preparar briefing do pais",
        "search_web": "A pesquisar na Web",
        "research_web": "A investigar fontes na Web",
        "search_docs": "A pesquisar documentos internos",
        "fetch_url": "A verificar a pagina",
        "calculate": "A calcular",
        "open_world_monitor": "A abrir o monitor mundial",
        "open_finance_world_monitor": "A abrir o monitor financeiro",
        "vision": "A analisar a imagem",
    "get_system_info": "A ler informacao do computador",
        "word_count": "A contar palavras",
        "format_json": "A formatar JSON",
        "remember": "A guardar na memoria",
        "recall": "A recordar",
        "tell_joke": "A preparar uma piada",
        "summarize": "A resumir",
        "explain_code": "A explicar codigo",
        "list_supported_countries": "A listar paises",
    }
    return labels.get(name, f"A executar {name}")


def build_activity(skill_name: str | None, metadata: dict | None) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = [
        {"label": "A interpretar o pedido…", "status": "done"},
    ]
    if skill_name:
        steps.append(
            {
                "label": _friendly_tool_label(skill_name),
                "status": "done",
                "tool": skill_name,
            }
        )
    steps.append({"label": "A preparar a resposta…", "status": "done"})
    steps.append({"label": "Concluído.", "status": "done"})
    if metadata and metadata.get("opened") is False and metadata.get("kind") in (
        "news",
        "finance",
        "briefing",
    ):
        steps.append(
            {
                "label": "Monitor disponivel (abrir manualmente)",
                "status": "done",
                "monitor": metadata.get("auto_open_monitor") or metadata.get("kind"),
            }
        )
    return steps


def extract_ui_payload(reply_text: str, metadata: dict | None) -> dict[str, Any]:
    meta = metadata or {}
    sources = []
    results = meta.get("results") or []
    for r in results:
        if isinstance(r, dict):
            sources.append(
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "snippet": r.get("snippet", ""),
                    "source": r.get("source", ""),
                    "date": r.get("date"),
                    "kind": r.get("kind"),
                }
            )
    if meta.get("url") and not any(s.get("url") == meta.get("url") for s in sources):
        sources.append(
            {
                "title": meta.get("title") or meta.get("url"),
                "url": meta.get("url"),
                "snippet": "",
                "source": meta.get("source") or "",
            }
        )
    monitor_kind = None
    if meta.get("auto_open_monitor") in ("world", "finance"):
        monitor_kind = meta["auto_open_monitor"]
    elif meta.get("monitor_type") in ("world", "finance"):
        monitor_kind = meta["monitor_type"]
    elif meta.get("kind") == "finance":
        monitor_kind = "finance"
    elif meta.get("kind") in ("news", "briefing", "monitor"):
        monitor_kind = "world"

    offer_monitor = bool(
        monitor_kind
        or meta.get("kind") in ("news", "finance", "briefing", "monitor")
    )
    country_code = meta.get("country")
    monitor_path = None
    if monitor_kind:
        monitor_path = f"/monitors/{monitor_kind}_snapshot.html"
        if country_code and str(country_code).upper() != "WW":
            monitor_path += f"?country={str(country_code).upper()}"
    grounding = meta.get("grounding") or {}
    if meta.get("kind") == "document":
        for s in sources:
            s.setdefault("kind", "document")
    if meta.get("kind") == "memory":
        for s in sources:
            s.setdefault("kind", "memory")
    if meta.get("kind") == "research" or meta.get("pages"):
        for s in sources:
            s.setdefault("kind", s.get("kind") or "web")
    return {
        "sources": sources,
        "headlines_only": bool(meta.get("headlines_only")),
        "not_realtime_prices": bool(meta.get("not_realtime_prices")),
        "country": meta.get("country"),
        "kind": meta.get("kind"),
        "document_search": meta.get("kind") == "document",
        "personal_memory": meta.get("kind") == "memory",
        "opened": meta.get("opened"),
        "monitor_kind": monitor_kind,
        "offer_monitor": offer_monitor,
        "monitor_path": monitor_path,
        "grounding_score": grounding.get("score"),
        "grounded": grounding.get("grounded"),
        "plan_steps": meta.get("plan_steps"),
        "confidence": meta.get("confidence"),
        "confidence_score": (meta.get("confidence") or {}).get("score"),
        "confidence_level": (meta.get("confidence") or {}).get("level"),
        "hallucination_risk": (meta.get("confidence") or {}).get("hallucination_risk"),
    }


def _finalize_chat(
    session: Session,
    text: str,
    reply,
    attachments: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    from friday.llm.vision import attachment_memory_note

    note = attachment_memory_note(attachments)
    user_for_memory = f"{text}\n{note}".strip() if note else text
    session.memory.add_user(user_for_memory)
    session.memory.add_assistant(reply.text)
    if reply.skill_metadata:
        session.memory.update_from_skill_metadata(reply.skill_metadata)

    meta = dict(reply.skill_metadata or {})
    if reply.grounding:
        meta["grounding"] = reply.grounding
    if reply.confidence:
        meta["confidence"] = reply.confidence
    skill_hint = meta.get("kind")
    activity = build_activity(
        {
            "news": "get_world_news",
            "finance": "get_world_finance_news",
            "briefing": "get_country_briefing",
            "monitor": "open_world_monitor",
            "document": "search_docs",
            "calculate": "calculate",
            "research": "research_web",
            "vision": "vision",
        }.get(str(skill_hint))
        if skill_hint
        else None,
        meta,
    )
    ui = extract_ui_payload(reply.text, meta)
    store._save(session)

    pending = None
    return {
        "reply": reply.text,
        "metadata": meta,
        "activity": activity,
        "ui": ui,
        "session": {
            "last_country": session.memory.last_country,
            "last_news_context": session.memory.last_news_context,
            "last_language": session.memory.last_language,
        },
        "pending_confirmation": pending,
        "tool_rounds": reply.tool_rounds,
        "grounding": reply.grounding,
        "confidence": reply.confidence or meta.get("confidence"),
        "prompt_version": getattr(reply, "prompt_version", None) or PROMPT_VERSION,
    }


async def run_chat(session: Session, text: str, settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    await session.emit("state", {"state": "thinking"})
    await session.emit("activity", {"label": "A interpretar o pedido…", "status": "running"})

    registry = default_registry(settings)
    for name in ("get_world_news", "get_world_finance_news", "get_country_briefing"):
        try:
            skill = registry.get(name)
            if hasattr(skill, "_auto_open"):
                skill._auto_open = False  # type: ignore[attr-defined]
        except Exception:
            pass

    runner = ToolRunner(
        settings,
        registry,
        session=session.memory,
        state_emit=lambda state: session.emit("state", {"state": state}),
        address_override=_address_from_prefs(),
    )
    await session.emit("activity", {"label": "A processar…", "status": "running"})

    if session.gate.pending is not None:
        status, action = session.gate.interpret(text)
        if status == "confirmed" and action:
            msg, meta, next_pending = await _execute_gated_action(
                action, settings, session
            )
            await session.emit(
                "state",
                {
                    "state": "awaiting_confirmation"
                    if next_pending
                    else "idle"
                },
            )
            session.memory.add_user(text)
            session.memory.add_assistant(msg)
            store._save(session)
            return {
                "reply": msg,
                "metadata": meta,
                "activity": [{"label": "Confirmacao aceite.", "status": "done"}],
                "ui": {},
                "pending_confirmation": _pending_dict(next_pending),
            }
        if status == "denied" and action:
            session.workflow = None
            await session.emit("state", {"state": "idle"})
            msg = f"Cancelado: {action.summary}."
            session.memory.add_user(text)
            session.memory.add_assistant(msg)
            store._save(session)
            return {
                "reply": msg,
                "metadata": {"kind": "confirmation", "decision": "denied"},
                "activity": [{"label": "Confirmacao cancelada.", "status": "done"}],
                "ui": {},
                "pending_confirmation": None,
            }
        if status == "waiting":
            await session.emit("state", {"state": "awaiting_confirmation"})
            pending = session.gate.pending
            assert pending is not None
            return {
                "reply": pending.prompt_message(),
                "metadata": {"kind": "confirmation"},
                "activity": [{"label": "A aguardar confirmacao…", "status": "running"}],
                "ui": {},
                "pending_confirmation": _pending_dict(pending),
            }

    try:
        attachments = session.take_attachments()
        reply = await runner.chat_with_tools(
            text,
            session.memory.history_for_llm(),
            session=session.memory,
            attachments=attachments or None,
        )
    except Exception as exc:
        await session.emit("error", {"message": str(exc)})
        await session.emit("state", {"state": "error"})
        return {
            "reply": "Nao consegui completar o pedido. Verifica o LM Studio e tenta novamente.",
            "metadata": {},
            "activity": [{"label": "Erro.", "status": "failed"}],
            "ui": {},
            "pending_confirmation": None,
            "error": str(exc),
        }

    # Skills that need ConfirmationGate (create event / send email)
    skill_meta = getattr(reply, "skill_metadata", None) or {}
    pending_action = _pending_from_skill_meta(skill_meta)
    if pending_action is not None and session.gate.pending is None:
        wf_data = skill_meta.get("workflow")
        if isinstance(wf_data, dict) and wf_data.get("steps"):
            from friday.productivity.workflows import WorkflowQueue, WorkflowStep

            steps = [
                WorkflowStep(
                    action=str(s.get("action") or ""),
                    target=str(s.get("target") or ""),
                    summary=str(s.get("summary") or ""),
                    consequences=str(s.get("consequences") or ""),
                    payload=dict(s.get("payload") or {}),
                    preview=dict(s.get("preview") or {}),
                )
                for s in wf_data["steps"]
                if isinstance(s, dict)
            ]
            session.workflow = WorkflowQueue(
                steps=steps,
                index=int(wf_data.get("index") or 0),
                label=str(wf_data.get("label") or ""),
            )
        session.gate.request(pending_action)
        reply.text = pending_action.prompt_message()

    result = _finalize_chat(session, text, reply, attachments=attachments)

    if session.gate.pending:
        result["pending_confirmation"] = _pending_dict(session.gate.pending)
        await session.emit("state", {"state": "awaiting_confirmation"})
    else:
        await session.emit("state", {"state": "idle"})

    await session.emit("activity", {"steps": result["activity"]})
    await session.emit("done", {"reply_preview": reply.text[:120]})
    return result


def _address_from_prefs() -> str | None:
    try:
        from friday.memory.prefs_store import PrefsStore

        prefs = PrefsStore(get_settings().prefs_dir).get("default")
        addr = prefs.get("user_address")
        if addr and str(addr).strip():
            return str(addr).strip()
    except Exception:
        pass
    return None


async def run_chat_stream(
    session: Session, text: str, settings: Settings | None = None
) -> AsyncIterator[str]:
    """SSE generator with true token streaming when possible."""
    settings = settings or get_settings()
    await session.emit("state", {"state": "thinking"})

    registry = default_registry(settings)
    for name in ("get_world_news", "get_world_finance_news", "get_country_briefing"):
        try:
            skill = registry.get(name)
            if hasattr(skill, "_auto_open"):
                skill._auto_open = False  # type: ignore[attr-defined]
        except Exception:
            pass

    async def _state(state: str) -> None:
        await session.emit("state", {"state": state})

    async def _token(tok: str) -> None:
        await session.emit("token", {"text": tok})

    runner = ToolRunner(
        settings,
        registry,
        session=session.memory,
        state_emit=_state,
        token_emit=_token,
        address_override=_address_from_prefs(),
    )

    reply = None
    attachments = session.take_attachments()
    try:
        async for kind, payload in runner.stream_chat(
            text,
            session.memory.history_for_llm(),
            session=session.memory,
            attachments=attachments or None,
        ):
            if kind == "token":
                yield f"event: token\ndata: {json.dumps({'text': payload}, ensure_ascii=False)}\n\n"
            elif kind == "done":
                reply = payload
    except Exception as exc:
        await session.emit("error", {"message": str(exc)})
        await session.emit("state", {"state": "error"})
        err = {
            "reply": "Nao consegui completar o pedido. Verifica o LM Studio e tenta novamente.",
            "error": str(exc),
        }
        yield f"event: error\ndata: {json.dumps(err, ensure_ascii=False)}\n\n"
        return

    if reply is None:
        yield f"event: error\ndata: {json.dumps({'error': 'empty reply'}, ensure_ascii=False)}\n\n"
        return

    result = _finalize_chat(session, text, reply, attachments=attachments)
    await session.emit("state", {"state": "idle"})
    await session.emit("activity", {"steps": result["activity"]})
    await session.emit("done", result)
    yield f"event: done\ndata: {json.dumps(result, ensure_ascii=False)}\n\n"


async def event_stream(session: Session) -> AsyncIterator[str]:
    """Yield SSE lines until client disconnects (caller cancels)."""
    while True:
        try:
            event = await asyncio.wait_for(session.event_queue.get(), timeout=25.0)
        except asyncio.TimeoutError:
            yield f"event: ping\ndata: {json.dumps({'ok': True})}\n\n"
            continue
        et = event.get("type", "message")
        payload = json.dumps(event, ensure_ascii=False)
        yield f"event: {et}\ndata: {payload}\n\n"
