"""Tool-calling loop with native API, intent router, and JSON fallback."""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from friday.config import Settings
from friday.llm.client import LlmClient
from friday.llm.grounding import (
    INVENTED_REFUSAL_EN,
    INVENTED_REFUSAL_PT,
    NO_SOURCE_REFUSAL_EN,
    NO_SOURCE_REFUSAL_PT,
    SOURCE_REQUIRED_INSTRUCTION,
    extract_urls_from_tool_meta,
    grounding_score,
    needs_web_grounding,
    snippets_from_meta,
)
from friday.llm.intent_router import match_skill_with_args
from friday.llm.planner import plan_steps_hybrid
from friday.llm.prompts import JSON_FALLBACK_INSTRUCTION, PROMPT_VERSION, build_system_prompt
from friday.llm.stream_tools import parse_tool_arguments
from friday.llm.vision import build_user_content
from friday.memory.context_budget import trim_messages_to_budget
from friday.memory.short_term import ShortTermMemory
from friday.obs import TurnObs, get_request_id
from friday.quality.confidence import confidence_report
from friday.skills.registry import SkillRegistry

logger = logging.getLogger(__name__)

_FRIENDLY_FAILURES = (
    "Nao consegui consultar essa informacao neste momento.",
    "A ferramenta nao esta a responder. Quer que tente novamente?",
    "Nao consegui abrir essa pagina.",
    "O servidor local parece estar indisponivel.",
    "Nao encontrei resultados suficientes.",
    "Preciso que confirme o endereco.",
)

_COUNTRY_SKILLS = frozenset(
    {
        "get_world_news",
        "get_world_finance_news",
        "get_country_briefing",
        "get_news",
        "get_finance",
        "country_update",
        "open_world_monitor",
        "open_finance_world_monitor",
    }
)

_WEB_SKILLS = frozenset({"search_web", "fetch_url", "research_web"})


@dataclass
class ChatReply:
    text: str
    tool_rounds: int = 0
    skill_metadata: dict[str, Any] | None = None
    grounding: dict[str, Any] | None = None
    prompt_version: str = PROMPT_VERSION
    confidence: dict[str, Any] | None = None


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


def _parse_tool_arguments(raw: str | dict | None) -> dict[str, Any]:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def _extract_native_tool_calls(message) -> list[ToolCall]:
    calls: list[ToolCall] = []
    for tc in message.tool_calls or []:
        fn = tc.function
        calls.append(
            ToolCall(
                id=tc.id,
                name=fn.name,
                arguments=_parse_tool_arguments(fn.arguments),
            )
        )
    return calls


def _parse_json_fallback(content: str) -> tuple[str, str | None, ToolCall | None]:
    """Returns (action, reply_text, optional ToolCall)."""
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        inner = lines[1:-1] if len(lines) > 2 else lines
        text = "\n".join(inner).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return "respond", content.strip(), None

    action = data.get("action", "respond")
    if action == "call_tool":
        return "call_tool", "", ToolCall(
            id=f"json_{uuid.uuid4().hex[:8]}",
            name=data.get("name", ""),
            arguments=data.get("arguments") or {},
        )
    reply = data.get("text") or data.get("content") or ""
    return "respond", reply, None


def _looks_like_time_refusal(text: str) -> bool:
    lowered = text.casefold()
    markers = (
        "nao tenho acesso",
        "não tenho acesso",
        "tempo real",
        "não consigo obter a hora",
        "nao consigo obter a hora",
        "não posso verificar a hora",
        "nao posso verificar a hora",
        "não tenho informacoes de tempo",
        "nao tenho informacoes de tempo",
        "relógio no seu",
        "relogio no seu",
    )
    return any(m in lowered for m in markers)


def _looks_like_news_refusal(text: str) -> bool:
    lowered = text.casefold()
    markers = (
        "nao tenho acesso a noticias",
        "não tenho acesso a notícias",
        "nao consigo obter noticias",
        "não consigo obter notícias",
        "nao tenho informacoes actualizadas",
        "não tenho informações atualizadas",
        "nao posso consultar noticias",
    )
    return any(m in lowered for m in markers)


def _friendly_skill_error(error: str | None, skill_name: str) -> str:
    if error and error.strip():
        return error.strip()
    if skill_name.startswith("fetch") or skill_name.startswith("open_"):
        return "Nao consegui abrir essa pagina."
    if "news" in skill_name or "search" in skill_name:
        return "Nao consegui consultar essa informacao neste momento."
    return _FRIENDLY_FAILURES[0]


def _inject_session_country(
    skill_name: str,
    arguments: dict[str, Any],
    session: ShortTermMemory | None,
) -> dict[str, Any]:
    args = dict(arguments or {})
    if skill_name not in _COUNTRY_SKILLS:
        return args
    if args.get("country"):
        return args
    if session and session.last_country:
        args["country"] = session.last_country
    return args


def _merge_meta(
    base: dict[str, Any] | None, new: dict[str, Any] | None
) -> dict[str, Any] | None:
    if not base and not new:
        return None
    out: dict[str, Any] = dict(base or {})
    if not new:
        return out
    # Accumulate URLs/results across tool rounds
    urls = list(extract_urls_from_tool_meta(out))
    urls.extend(extract_urls_from_tool_meta(new))
    results = list(out.get("results") or [])
    if new.get("results"):
        results.extend(new["results"])
    out.update(new)
    if results:
        out["results"] = results
    if urls and "url" not in out:
        out["url"] = urls[0]
    out["_all_urls"] = list(dict.fromkeys(urls))
    return out


class ToolRunner:
    def __init__(
        self,
        settings: Settings,
        registry: SkillRegistry,
        client: LlmClient | None = None,
        session: ShortTermMemory | None = None,
        state_emit: Callable[[str], Awaitable[None]] | None = None,
        token_emit: Callable[[str], Awaitable[None]] | None = None,
        address_override: str | None = None,
    ) -> None:
        self._settings = settings
        self._registry = registry
        self._client = client or LlmClient(settings)
        self._session = session
        self._state_emit = state_emit
        self._token_emit = token_emit
        self._address_override = address_override

    def bind_session(self, session: ShortTermMemory) -> None:
        self._session = session

    async def _emit_state(self, state: str) -> None:
        if self._state_emit:
            await self._state_emit(state)

    async def _emit_token(self, token: str) -> None:
        if self._token_emit:
            await self._token_emit(token)

    def _known_skill(self, name: str) -> bool:
        return name in self._registry.names()

    def _apply_grounding(
        self,
        text: str,
        *,
        user_text: str,
        last_meta: dict[str, Any] | None,
        used_web: bool,
    ) -> ChatReply:
        tool_urls = list(
            (last_meta or {}).get("_all_urls")
            or extract_urls_from_tool_meta(last_meta)
        )
        snippets = snippets_from_meta(last_meta)
        g = grounding_score(
            text,
            tool_urls=tool_urls,
            used_web_tools=used_web,
            snippets=snippets,
        )
        meta = dict(last_meta or {})
        meta["grounding"] = g
        require = bool(self._settings.web_source_required) and needs_web_grounding(
            user_text
        )
        lang = (self._session.last_language if self._session else "pt") or "pt"
        if require and not g["grounded"] and not used_web:
            refusal = (
                NO_SOURCE_REFUSAL_EN if lang.startswith("en") else NO_SOURCE_REFUSAL_PT
            )
            g = {**g, "score": 0.0, "grounded": False, "refused": True}
            meta["grounding"] = g
            conf = confidence_report(refusal, grounding=g, tool_rounds=0)
            meta["confidence"] = conf
            return ChatReply(
                text=refusal,
                tool_rounds=0,
                skill_metadata=meta,
                grounding=g,
                confidence=conf,
            )
        if used_web and g.get("inventing"):
            refusal = (
                INVENTED_REFUSAL_EN if lang.startswith("en") else INVENTED_REFUSAL_PT
            )
            g = {**g, "grounded": False, "refused": True, "score": min(float(g.get("score") or 0), 0.35)}
            meta["grounding"] = g
            conf = confidence_report(refusal, grounding=g, tool_rounds=0)
            meta["confidence"] = conf
            return ChatReply(
                text=refusal,
                tool_rounds=0,
                skill_metadata=meta,
                grounding=g,
                confidence=conf,
            )
        conf = confidence_report(text, grounding=g, tool_rounds=0)
        meta["confidence"] = conf
        return ChatReply(
            text=text,
            tool_rounds=0,
            skill_metadata=meta or None,
            grounding=g,
            confidence=conf,
        )

    async def _run_skill_direct(
        self,
        skill_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> ChatReply:
        if not self._known_skill(skill_name):
            return ChatReply(
                text=(
                    f"Nao tenho a ferramenta '{skill_name}'. "
                    "Posso usar apenas as ferramentas disponiveis."
                ),
                tool_rounds=1,
            )
        args = _inject_session_country(skill_name, arguments or {}, self._session)
        await self._emit_state("tool_calling")
        result = await self._registry.execute(skill_name, args)
        if self._session:
            self._session.update_from_skill_metadata(result.metadata)
        if not result.success:
            return ChatReply(
                text=_friendly_skill_error(result.error, skill_name),
                tool_rounds=1,
                skill_metadata=result.metadata,
            )
        logger.info("Intent router -> %s %s", skill_name, args)
        meta = dict(result.metadata or {})
        if skill_name in _WEB_SKILLS:
            g = grounding_score(
                result.content,
                tool_urls=extract_urls_from_tool_meta(meta),
                used_web_tools=True,
            )
            meta["grounding"] = g
            return ChatReply(
                text=result.content,
                tool_rounds=1,
                skill_metadata=meta,
                grounding=g,
            )
        return ChatReply(
            text=result.content,
            tool_rounds=1,
            skill_metadata=meta,
        )

    def _address(self) -> str:
        if self._address_override and self._address_override.strip():
            return self._address_override.strip()
        return self._settings.friday_user_address

    def _build_messages(
        self,
        user_text: str,
        history: list[dict[str, Any]] | None,
        memory_note: str,
        attachments: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": build_system_prompt(self._address()),
            },
            {
                "role": "system",
                "content": JSON_FALLBACK_INSTRUCTION,
            },
        ]
        try:
            from friday.productivity.context import (
                build_productivity_context,
                format_context_block,
            )

            ctx = build_productivity_context(self._settings)
            messages.append(
                {"role": "system", "content": format_context_block(ctx)}
            )
        except Exception as exc:
            logger.debug("productivity context skipped: %s", exc)
        if self._settings.web_source_required and needs_web_grounding(user_text):
            messages.append(
                {"role": "system", "content": SOURCE_REQUIRED_INSTRUCTION}
            )
        if history:
            messages.extend(history)
        content = build_user_content(user_text + memory_note, attachments)
        messages.append({"role": "user", "content": content})
        budget = int(self._settings.llm_context_token_budget or 0)
        if budget > 0:
            messages = trim_messages_to_budget(messages, max_tokens=budget)
        return messages

    @staticmethod
    def _has_images(attachments: list[dict[str, Any]] | None) -> bool:
        return any(
            str(a.get("kind") or "").casefold() == "image" and a.get("path")
            for a in (attachments or [])
        )

    async def chat_with_tools(
        self,
        user_text: str,
        history: list[dict[str, Any]] | None = None,
        session: ShortTermMemory | None = None,
        attachments: list[dict[str, Any]] | None = None,
    ) -> ChatReply:
        if session is not None:
            self._session = session
        if self._session:
            self._session.set_language_hint(user_text)

        use_vision = self._has_images(attachments)

        # With images, skip intent/planner so the VLM sees the pixels.
        if not use_vision:
            routed = match_skill_with_args(user_text)
            if routed and self._known_skill(routed[0]):
                return await self._run_skill_direct(routed[0], routed[1])

            planned = plan_steps_hybrid(
                user_text,
                skill_names=list(self._registry.names()),
                client=self._client,
                mode=getattr(self._settings, "llm_planner_mode", "aggressive"),
                max_per_minute=int(
                    getattr(self._settings, "llm_planner_max_per_minute", 12) or 12
                ),
            )
            if planned and all(self._known_skill(s.skill) for s in planned):
                return await self._run_plan(planned, user_text)
        else:
            try:
                self._client.ensure_vision_ready()
            except Exception as exc:
                logger.warning("Vision unavailable: %s", exc)
                return ChatReply(
                    text=(
                        "Nao tenho um modelo vision carregado no LM Studio. "
                        "Carrega um VLM (qwen2-vl, llava, pixtral, …) ou define "
                        "LM_STUDIO_VISION_MODEL, e tenta de novo."
                    ),
                    tool_rounds=0,
                    skill_metadata={"kind": "vision", "error": str(exc)},
                )

        memory_hits: list[str] = []
        memory_note = ""
        try:
            from friday.memory.chroma_store import get_shared_store

            store = get_shared_store()
            if store.available:
                memory_hits = store.query(user_text, n=2) or []
                if memory_hits:
                    memory_note = (
                        "\n\n[Memoria relevante]\n"
                        + "\n".join(f"- {h}" for h in memory_hits)
                    )
        except Exception:
            memory_note = ""
            memory_hits = []

        messages = self._build_messages(
            user_text, history, memory_note, attachments=attachments
        )
        tools = None if use_vision else self._registry.to_openai_tools()
        rounds = 0
        max_rounds = self._settings.llm_max_tool_rounds
        last_meta: dict[str, Any] | None = None
        used_web = False
        if memory_hits:
            last_meta = {
                "results": [
                    {
                        "title": "Memoria pessoal",
                        "url": "",
                        "snippet": h[:280],
                        "source": "friday_memory",
                        "kind": "memory",
                    }
                    for h in memory_hits
                ],
                "kind": "memory",
            }
        if use_vision:
            last_meta = _merge_meta(
                last_meta,
                {
                    "kind": "vision",
                    "vision": True,
                    "attachments": [
                        {
                            "filename": a.get("filename"),
                            "kind": a.get("kind"),
                        }
                        for a in (attachments or [])
                    ],
                    "vision_model": self._client.resolve_model(vision=True),
                },
            )

        while rounds <= max_rounds:
            response = self._client.create_completion(
                messages=messages,
                tools=tools if tools else None,
                vision=use_vision,
                tool_choice="auto" if tools else None,
                max_tokens=512,
                temperature=0.3,
            )
            message = response.choices[0].message
            tool_calls = _extract_native_tool_calls(message)

            if not tool_calls and message.content:
                action, reply_text, fallback_call = _parse_json_fallback(
                    message.content
                )
                if action == "call_tool" and fallback_call:
                    tool_calls = [fallback_call]
                elif action == "respond":
                    text = reply_text or "Desculpa, nao percebi."
                    if _looks_like_time_refusal(text):
                        return await self._run_skill_direct("get_current_datetime")
                    if _looks_like_news_refusal(text):
                        return await self._run_skill_direct("get_world_news")
                    reply = self._apply_grounding(
                        text,
                        user_text=user_text,
                        last_meta=last_meta,
                        used_web=used_web,
                    )
                    reply.tool_rounds = rounds
                    return reply

            if not tool_calls:
                reply_text = (message.content or "").strip()
                if _looks_like_time_refusal(reply_text):
                    return await self._run_skill_direct("get_current_datetime")
                if _looks_like_news_refusal(reply_text):
                    return await self._run_skill_direct("get_world_news")
                reply = self._apply_grounding(
                    reply_text or "Desculpa, nao percebi.",
                    user_text=user_text,
                    last_meta=last_meta,
                    used_web=used_web,
                )
                reply.tool_rounds = rounds
                return reply

            if rounds >= max_rounds:
                return ChatReply(
                    text="Precisei de demasiadas ferramentas para responder.",
                    tool_rounds=rounds,
                    skill_metadata=last_meta,
                )

            messages.append(message.model_dump(exclude_none=True))
            for tc in tool_calls:
                if not self._known_skill(tc.name):
                    content = (
                        f"Ferramenta desconhecida: {tc.name}. "
                        "Nao existe read_webpage nem get_system_status; "
                        "usa fetch_url ou get_system_info."
                    )
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": content,
                        }
                    )
                    continue
                args = _inject_session_country(tc.name, tc.arguments, self._session)
                await self._emit_state("tool_calling")
                import time as _time

                t0 = _time.perf_counter()
                result = await self._registry.execute(tc.name, args)
                tool_ms = (_time.perf_counter() - t0) * 1000
                logger.info(
                    json.dumps(
                        {
                            "event": "tool_call",
                            "request_id": get_request_id(),
                            "skill": tc.name,
                            "ms": round(tool_ms, 1),
                            "ok": result.success,
                        },
                        ensure_ascii=False,
                    )
                )
                if self._session:
                    self._session.update_from_skill_metadata(result.metadata)
                last_meta = _merge_meta(last_meta, result.metadata)
                if tc.name in _WEB_SKILLS:
                    used_web = True
                if result.success:
                    content = result.content
                else:
                    content = _friendly_skill_error(result.error, tc.name)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": content,
                    }
                )
            rounds += 1

        return ChatReply(
            text="Nao consegui completar a resposta.",
            tool_rounds=rounds,
            skill_metadata=last_meta,
        )

    async def _continue_after_streamed_tools(
        self,
        *,
        messages: list[dict[str, Any]],
        tool_calls: list[ToolCall],
        user_text: str,
        last_meta: dict[str, Any] | None,
        use_vision: bool,
    ) -> ChatReply:
        """Execute tools from a streamed first pass, then complete (no re-probe)."""
        used_web = False
        assistant_tool_msg: dict[str, Any] = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": json.dumps(tc.arguments or {}),
                    },
                }
                for tc in tool_calls
            ],
        }
        messages = list(messages) + [assistant_tool_msg]
        for tc in tool_calls:
            if not self._known_skill(tc.name):
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": f"Ferramenta desconhecida: {tc.name}.",
                    }
                )
                continue
            args = _inject_session_country(tc.name, tc.arguments, self._session)
            await self._emit_state("tool_calling")
            import time as _time

            t0 = _time.perf_counter()
            result = await self._registry.execute(tc.name, args)
            logger.info(
                json.dumps(
                    {
                        "event": "tool_call",
                        "request_id": get_request_id(),
                        "skill": tc.name,
                        "ms": round((_time.perf_counter() - t0) * 1000, 1),
                        "ok": result.success,
                    },
                    ensure_ascii=False,
                )
            )
            if self._session:
                self._session.update_from_skill_metadata(result.metadata)
            last_meta = _merge_meta(last_meta, result.metadata)
            if tc.name in _WEB_SKILLS:
                used_web = True
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": (
                        result.content
                        if result.success
                        else _friendly_skill_error(result.error, tc.name)
                    ),
                }
            )

        # Stream final answer after tools (tokens yielded by caller)
        parts: list[str] = []
        try:
            for kind, payload in self._client.stream_message(
                messages=messages,
                max_tokens=512,
                temperature=0.3,
                vision=use_vision,
            ):
                if kind == "token":
                    parts.append(str(payload))
                elif kind == "final" and not parts and payload.content:
                    parts.append(payload.content)
        except Exception:
            response = self._client.create_completion(
                messages=messages,
                max_tokens=512,
                temperature=0.3,
                vision=use_vision,
            )
            parts.append(response.choices[0].message.content or "")

        text = "".join(parts).strip() or "Desculpa, nao percebi."
        reply = self._apply_grounding(
            text,
            user_text=user_text,
            last_meta=last_meta,
            used_web=used_web,
        )
        reply.tool_rounds = 1
        return reply

    async def _run_plan(
        self,
        steps: list,
        user_text: str,
    ) -> ChatReply:
        """Execute a deterministic multi-step plan and synthesize a short reply."""
        parts: list[str] = []
        meta: dict[str, Any] | None = None
        used_web = False
        for step in steps:
            await self._emit_state("tool_calling")
            args = _inject_session_country(step.skill, step.arguments, self._session)
            result = await self._registry.execute(step.skill, args)
            if self._session:
                self._session.update_from_skill_metadata(result.metadata)
            meta = _merge_meta(meta, result.metadata)
            if step.skill in _WEB_SKILLS:
                used_web = True
            label = step.reason or step.skill
            if result.success:
                parts.append(f"[{label}]\n{result.content}")
            else:
                parts.append(
                    f"[{label}] {_friendly_skill_error(result.error, step.skill)}"
                )
        combined = "\n\n".join(parts).strip()
        reply = self._apply_grounding(
            combined,
            user_text=user_text,
            last_meta=meta,
            used_web=used_web,
        )
        reply.tool_rounds = len(steps)
        if meta:
            meta["plan_steps"] = [s.skill for s in steps]
            reply.skill_metadata = meta
        return reply

    async def stream_chat(
        self,
        user_text: str,
        history: list[dict[str, Any]] | None = None,
        session: ShortTermMemory | None = None,
        attachments: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[tuple[str, Any]]:
        """
        Yield ('token', str) for live tokens and ('done', ChatReply) at the end.

        Single-pass stream: no probe completion. If the stream emits tool_calls,
        execute tools then stream (or complete) the final answer.
        """
        if session is not None:
            self._session = session
        if self._session:
            self._session.set_language_hint(user_text)

        use_vision = self._has_images(attachments)
        obs = TurnObs()

        if not use_vision:
            routed = match_skill_with_args(user_text)
            if routed and self._known_skill(routed[0]):
                reply = await self._run_skill_direct(routed[0], routed[1])
                async for t in self._emit_text_as_tokens(reply.text):
                    yield ("token", t)
                obs.finish(path="intent", tools=routed[0])
                yield ("done", reply)
                return

            planned = plan_steps_hybrid(
                user_text,
                skill_names=list(self._registry.names()),
                client=self._client,
                mode=getattr(self._settings, "llm_planner_mode", "aggressive"),
                max_per_minute=int(
                    getattr(self._settings, "llm_planner_max_per_minute", 12) or 12
                ),
            )
            if planned and all(self._known_skill(s.skill) for s in planned):
                reply = await self._run_plan(planned, user_text)
                async for t in self._emit_text_as_tokens(reply.text):
                    yield ("token", t)
                obs.finish(path="plan", steps=[s.skill for s in planned])
                yield ("done", reply)
                return
        else:
            try:
                self._client.ensure_vision_ready()
            except Exception as exc:
                reply = ChatReply(
                    text=(
                        "Nao tenho um modelo vision carregado no LM Studio. "
                        "Carrega um VLM ou define LM_STUDIO_VISION_MODEL."
                    ),
                    skill_metadata={"kind": "vision", "error": str(exc)},
                )
                async for t in self._emit_text_as_tokens(reply.text):
                    yield ("token", t)
                yield ("done", reply)
                return

        memory_note = ""
        last_meta: dict[str, Any] | None = None
        try:
            from friday.memory.chroma_store import get_shared_store

            store = get_shared_store()
            if store.available:
                hits = store.query(user_text, n=2) or []
                if hits:
                    memory_note = (
                        "\n\n[Memoria relevante]\n"
                        + "\n".join(f"- {h}" for h in hits)
                    )
                    last_meta = {
                        "results": [
                            {
                                "title": "Memoria pessoal",
                                "url": "",
                                "snippet": h[:280],
                                "source": "friday_memory",
                                "kind": "memory",
                            }
                            for h in hits
                        ],
                        "kind": "memory",
                    }
        except Exception:
            memory_note = ""

        if use_vision:
            last_meta = _merge_meta(
                last_meta,
                {
                    "kind": "vision",
                    "vision": True,
                    "vision_model": self._client.resolve_model(vision=True),
                },
            )

        messages = self._build_messages(
            user_text, history, memory_note, attachments=attachments
        )
        tools = None if use_vision else self._registry.to_openai_tools()

        # Drop JSON-fallback system for cleaner prose stream when no tools expected;
        # keep tools available so the model can still call them in one pass.
        stream_msgs = list(messages)
        if not use_vision:
            stream_msgs = [
                m
                for m in stream_msgs
                if not (
                    m.get("role") == "system"
                    and JSON_FALLBACK_INSTRUCTION[:40] in str(m.get("content") or "")
                )
            ]
            stream_msgs.append(
                {
                    "role": "system",
                    "content": (
                        "Responde em prosa natural. Se precisares de uma ferramenta, "
                        "usa tool calls nativos (nao JSON)."
                    ),
                }
            )

        await self._emit_state("speaking")
        parts: list[str] = []
        tool_calls: list[ToolCall] = []
        try:
            for kind, payload in self._client.stream_message(
                messages=stream_msgs,
                tools=tools if tools else None,
                tool_choice="auto" if tools else None,
                max_tokens=512,
                temperature=0.3,
                vision=use_vision,
            ):
                if kind == "token":
                    parts.append(str(payload))
                    await self._emit_token(str(payload))
                    yield ("token", str(payload))
                elif kind == "final":
                    if payload.has_tools:
                        tool_calls = [
                            ToolCall(
                                id=tc.id or f"stream_{tc.name}",
                                name=tc.name,
                                arguments=parse_tool_arguments(tc.arguments),
                            )
                            for tc in payload.tool_calls
                            if tc.name
                        ]
                    elif not parts and payload.content:
                        parts.append(payload.content)
        except Exception as exc:
            logger.warning("stream_message failed (%s); falling back to chat_with_tools", exc)
            reply = await self.chat_with_tools(
                user_text, history, session=session, attachments=attachments
            )
            async for t in self._emit_text_as_tokens(reply.text):
                yield ("token", t)
            yield ("done", reply)
            return

        if tool_calls:
            await self._emit_state("tool_calling")
            reply = await self._continue_after_streamed_tools(
                messages=messages,
                tool_calls=tool_calls,
                user_text=user_text,
                last_meta=last_meta,
                use_vision=use_vision,
            )
            await self._emit_state("speaking")
            async for t in self._emit_text_as_tokens(reply.text):
                yield ("token", t)
            obs.finish(path="stream_tools", tool_names=[t.name for t in tool_calls])
            yield ("done", reply)
            return

        full = "".join(parts).strip()
        if not full:
            reply = await self.chat_with_tools(
                user_text, history, session=session, attachments=attachments
            )
            async for t in self._emit_text_as_tokens(reply.text):
                yield ("token", t)
            yield ("done", reply)
            return

        reply = self._apply_grounding(
            full,
            user_text=user_text,
            last_meta=last_meta,
            used_web=False,
        )
        obs.finish(path="stream", chars=len(full))
        yield ("done", reply)

    async def _emit_text_as_tokens(self, text: str) -> AsyncIterator[str]:
        step = 16
        for i in range(0, len(text or ""), step):
            chunk = text[i : i + step]
            await self._emit_token(chunk)
            yield chunk
