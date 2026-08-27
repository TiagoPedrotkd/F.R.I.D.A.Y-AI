"""Agent API session store and helpers."""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

from friday.config import Settings, get_settings
from friday.llm.tool_runner import ToolRunner
from friday.memory.short_term import ShortTermMemory
from friday.safety.confirmation import ConfirmationGate
from friday.skills.registry import default_registry


@dataclass
class Session:
    id: str
    memory: ShortTermMemory
    gate: ConfirmationGate
    created_at: float = field(default_factory=time.time)
    event_queue: asyncio.Queue = field(default_factory=asyncio.Queue)

    async def emit(self, event_type: str, data: dict[str, Any] | None = None) -> None:
        await self.event_queue.put(
            {"type": event_type, "data": data or {}, "ts": time.time()}
        )


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def create(self) -> Session:
        sid = uuid.uuid4().hex
        session = Session(
            id=sid,
            memory=ShortTermMemory(max_messages=get_settings().max_context_messages),
            gate=ConfirmationGate(),
        )
        self._sessions[sid] = session
        return session

    def get(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    def delete(self, session_id: str) -> bool:
        return self._sessions.pop(session_id, None) is not None


store = SessionStore()


def _friendly_tool_label(name: str) -> str:
    labels = {
        "get_current_datetime": "A consultar a hora",
        "get_world_news": "A consultar as noticias",
        "get_world_finance_news": "A consultar noticias financeiras",
        "get_country_briefing": "A preparar briefing do pais",
        "search_web": "A pesquisar na Web",
        "fetch_url": "A verificar a pagina",
        "open_world_monitor": "A abrir o monitor mundial",
        "open_finance_world_monitor": "A abrir o monitor financeiro",
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
    headlines = []
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
                }
            )
    # Headlines inferred from news-like replies are left to frontend parsing of content
    # when metadata has headlines_only
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
    # Prefer snapshot (data-rich); API generates it on demand if missing
    country_code = meta.get("country")
    monitor_path = None
    if monitor_kind:
        monitor_path = f"/monitors/{monitor_kind}_snapshot.html"
        if country_code and str(country_code).upper() != "WW":
            monitor_path += f"?country={str(country_code).upper()}"
    return {
        "sources": sources,
        "headlines_only": bool(meta.get("headlines_only")),
        "not_realtime_prices": bool(meta.get("not_realtime_prices")),
        "country": meta.get("country"),
        "kind": meta.get("kind"),
        "opened": meta.get("opened"),
        "monitor_kind": monitor_kind,
        "offer_monitor": offer_monitor,
        "monitor_path": monitor_path,
    }


async def run_chat(session: Session, text: str, settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    await session.emit("state", {"state": "thinking"})
    await session.emit("activity", {"label": "A interpretar o pedido…", "status": "running"})

    registry = default_registry(settings)
    # Disable auto browser open in API context — UI opens monitors
    for name in ("get_world_news", "get_world_finance_news", "get_country_briefing"):
        try:
            skill = registry.get(name)
            if hasattr(skill, "_auto_open"):
                skill._auto_open = False  # type: ignore[attr-defined]
        except Exception:
            pass

    runner = ToolRunner(settings, registry, session=session.memory)
    await session.emit("activity", {"label": "A processar…", "status": "running"})

    # Detect pending confirmation flow
    if session.gate.pending is not None:
        status, action = session.gate.interpret(text)
        if status == "confirmed" and action:
            await session.emit("state", {"state": "idle"})
            msg = f"Confirmado: {action.summary}."
            session.memory.add_user(text)
            session.memory.add_assistant(msg)
            return {
                "reply": msg,
                "metadata": {"kind": "confirmation", "decision": "confirmed"},
                "activity": [{"label": "Confirmacao aceite.", "status": "done"}],
                "ui": {},
                "pending_confirmation": None,
            }
        if status == "denied" and action:
            await session.emit("state", {"state": "idle"})
            msg = f"Cancelado: {action.summary}."
            session.memory.add_user(text)
            session.memory.add_assistant(msg)
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
                "pending_confirmation": {
                    "action": pending.action,
                    "target": pending.target,
                    "summary": pending.summary,
                    "consequences": pending.consequences,
                },
            }

    try:
        reply = await runner.chat_with_tools(
            text, session.memory.messages, session=session.memory
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

    session.memory.add_user(text)
    session.memory.add_assistant(reply.text)
    if reply.skill_metadata:
        session.memory.update_from_skill_metadata(reply.skill_metadata)

    meta = reply.skill_metadata or {}
    skill_hint = meta.get("kind")
    activity = build_activity(
        {
            "news": "get_world_news",
            "finance": "get_world_finance_news",
            "briefing": "get_country_briefing",
            "monitor": "open_world_monitor",
        }.get(str(skill_hint))
        if skill_hint
        else None,
        meta,
    )
    ui = extract_ui_payload(reply.text, meta)

    # Optional: if reply asks for confirmation patterns from ConfirmationGate policy
    pending = None
    if session.gate.pending:
        p = session.gate.pending
        pending = {
            "action": p.action,
            "target": p.target,
            "summary": p.summary,
            "consequences": p.consequences,
        }
        await session.emit("state", {"state": "awaiting_confirmation"})
    else:
        await session.emit("state", {"state": "idle"})

    await session.emit("activity", {"steps": activity})
    await session.emit("done", {"reply_preview": reply.text[:120]})

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
    }


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
