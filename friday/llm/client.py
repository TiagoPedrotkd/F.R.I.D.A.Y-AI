"""OpenAI-compatible client for LM Studio with optional Ollama/llama.cpp fallback."""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from typing import Any, NoReturn

import httpx
from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI

from friday.config import Settings
from friday.llm.stream_tools import (
    StreamResult,
    accumulate_stream_chunk,
    finalize_tool_bufs,
)
from friday.llm.vision import looks_like_vision_model, pick_vision_model
from friday.pipeline.errors import APITimeoutError as PipelineTimeoutError
from friday.pipeline.errors import ModelUnavailableError, NetworkError

logger = logging.getLogger(__name__)

_TINY_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
)


def _is_unloaded_error(exc: APIStatusError) -> bool:
    try:
        body = str(exc.response.json())
    except Exception:
        body = str(exc)
    lowered = body.casefold()
    return "unloaded" in lowered or "not loaded" in lowered or "no model" in lowered


def _status_error_body(exc: APIStatusError) -> str:
    try:
        return str(exc.response.json())
    except Exception:
        return str(exc)


def _raise_from_status(exc: APIStatusError, *, unloaded_msg: str) -> NoReturn:
    if _is_unloaded_error(exc):
        raise ModelUnavailableError(unloaded_msg) from exc
    body = _status_error_body(exc)
    raise ModelUnavailableError(f"LLM erro {exc.status_code}: {body}") from exc


def _make_openai(base_url: str, api_key: str, timeout_s: float) -> OpenAI:
    return OpenAI(
        base_url=base_url,
        api_key=api_key,
        timeout=httpx.Timeout(timeout_s, connect=5.0),
        max_retries=0,
    )


class LlmClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        timeout = float(settings.llm_timeout_seconds)
        self._client = _make_openai(
            settings.lm_studio_base_url_host,
            settings.lm_studio_api_key,
            timeout,
        )
        self.model = settings.lm_studio_model
        self._active_base = settings.lm_studio_base_url_host
        self._fallback: OpenAI | None = None
        self._fallback_model = (settings.llm_fallback_model or "").strip()
        self._vision_model_cache: str | None = None
        self._vision_verified_at: float = 0.0
        self._vision_verified_model: str | None = None
        fb = (settings.llm_fallback_base_url or "").strip()
        if fb:
            self._fallback = _make_openai(
                fb,
                settings.llm_fallback_api_key,
                timeout,
            )
            if not self._fallback_model:
                self._fallback_model = settings.lm_studio_model

    def list_model_ids(self) -> list[str]:
        try:
            models = self._client.models.list()
            return [m.id for m in models.data]
        except Exception as exc:
            logger.debug("Could not list models: %s", exc)
            return []

    def resolve_model(self, *, vision: bool = False) -> str:
        """Return chat or vision model id for the active backend."""
        if not vision or not self._settings.llm_vision_enabled:
            return self.model

        preferred = (self._settings.lm_studio_vision_model or "").strip()
        if self._fallback and self._client is self._fallback:
            preferred = (
                (self._settings.llm_fallback_vision_model or "").strip() or preferred
            )

        if preferred:
            return preferred

        if self._vision_model_cache:
            return self._vision_model_cache

        if looks_like_vision_model(self.model):
            self._vision_model_cache = self.model
            return self.model

        picked = pick_vision_model(
            self.list_model_ids(),
            preferred="",
            fallback=self.model,
        )
        if picked:
            self._vision_model_cache = picked
            logger.info("Vision model auto-detected: %s", picked)
            return picked

        logger.warning(
            "Nenhum modelo vision detectado; a usar %s (pode falhar com imagens)",
            self.model,
        )
        return self.model

    def ensure_vision_ready(self) -> str:
        """
        Resolve vision model, try LM Studio load if missing, verify with tiny multimodal ping.
        Caches successful verification for LLM_VISION_PING_TTL_SECONDS to stay stable/fast.
        """
        if not self._settings.llm_vision_enabled:
            raise ModelUnavailableError("LLM_VISION_ENABLED=false")

        ttl = float(self._settings.llm_vision_ping_ttl_seconds or 0)
        now = time.time()
        if (
            self._vision_verified_model
            and ttl > 0
            and (now - self._vision_verified_at) < ttl
        ):
            self._vision_model_cache = self._vision_verified_model
            return self._vision_verified_model

        model = self.resolve_model(vision=True)
        available = self.list_model_ids()
        # Prefer an already-listed vision model over a configured id that is not loaded
        if available:
            loaded_vision = [m for m in available if looks_like_vision_model(m)]
            if loaded_vision and model not in available:
                preferred = pick_vision_model(
                    loaded_vision,
                    preferred=(self._settings.lm_studio_vision_model or "").strip(),
                )
                if preferred:
                    logger.info(
                        "Vision: a usar modelo ja carregado %s (em vez de %s)",
                        preferred,
                        model,
                    )
                    model = preferred

        if available and model not in available and not any(
            model in mid or mid in model for mid in available
        ):
            loaded = self._try_load_lm_studio_model(model)
            if not loaded:
                # Last resort: any loaded VLM
                alt = pick_vision_model(available)
                if alt:
                    model = alt
                else:
                    raise ModelUnavailableError(
                        f"Modelo vision '{model}' nao esta carregado no LM Studio. "
                        "Carrega um VLM leve (moondream / qwen2-vl-2b / llava) "
                        "ou define LM_STUDIO_VISION_MODEL."
                    )

        import base64

        data_url = "data:image/png;base64," + base64.b64encode(_TINY_PNG).decode("ascii")
        try:
            self._client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "ok"},
                            {"type": "image_url", "image_url": {"url": data_url}},
                        ],
                    }
                ],
                max_tokens=1,
                temperature=0,
            )
        except Exception as exc:
            raise ModelUnavailableError(
                f"Vision ping falhou para '{model}': {exc}. "
                "No LM Studio carrega um VLM compativel e tenta de novo."
            ) from exc
        self._vision_model_cache = model
        self._vision_verified_model = model
        self._vision_verified_at = now
        logger.info("Vision model ready: %s (ttl=%.0fs)", model, ttl)
        return model

    def _try_load_lm_studio_model(self, model_id: str) -> bool:
        """Best-effort LM Studio native load API (v0)."""
        base = self._active_base.rstrip("/")
        # http://localhost:1234/v1 -> http://localhost:1234
        root = base[:-3] if base.endswith("/v1") else base
        endpoints = [
            f"{root}/api/v0/models/load",
            f"{root}/api/v1/models/load",
        ]
        for url in endpoints:
            try:
                with httpx.Client(timeout=httpx.Timeout(120.0, connect=5.0)) as http:
                    resp = http.post(url, json={"model": model_id})
                    if resp.status_code < 400:
                        logger.info("LM Studio load requested for %s via %s", model_id, url)
                        # refresh cache
                        self._vision_model_cache = model_id
                        return True
            except Exception as exc:
                logger.debug("LM Studio load %s failed: %s", url, exc)
        return False

    def _ping_completion(self, client: OpenAI, model: str, *, timeout_s: float) -> None:
        ping = OpenAI(
            base_url=str(client.base_url),
            api_key=client.api_key,
            timeout=httpx.Timeout(timeout_s, connect=5.0),
            max_retries=0,
        )
        ping.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "ok"}],
            max_tokens=1,
            temperature=0,
        )

    def ensure_model_ready(self) -> None:
        """
        Verify primary (LM Studio) is up; if not and fallback exists, try fallback.
        """
        base = self._settings.lm_studio_base_url_host
        try:
            with httpx.Client(timeout=httpx.Timeout(5.0, connect=3.0)) as http:
                resp = http.get(f"{base.rstrip('/')}/models")
                resp.raise_for_status()
        except httpx.ConnectError as exc:
            if self._try_activate_fallback():
                return
            raise NetworkError(
                f"Nao consegui ligar a {base}: servidor recusou a ligacao. "
                "Abre o LM Studio e inicia o Local Server (porta 1234), "
                "ou configura LLM_FALLBACK_BASE_URL (Ollama)."
            ) from exc
        except Exception as exc:
            if self._try_activate_fallback():
                return
            raise NetworkError(f"Nao consegui ligar a {base}: {exc}") from exc

        ping_timeout = max(60.0, float(self._settings.llm_timeout_seconds))
        last_exc: Exception | None = None
        for attempt in range(1, 3):
            try:
                logger.info(
                    "A verificar modelo '%s' (tentativa %d/2, timeout %.0fs)...",
                    self.model,
                    attempt,
                    ping_timeout,
                )
                self._ping_completion(self._client, self.model, timeout_s=ping_timeout)
                logger.info("LLM model ready: %s", self.model)
                return
            except APIConnectionError as exc:
                last_exc = exc
                msg = str(exc).casefold()
                if "timeout" in msg or "timed out" in msg:
                    logger.warning(
                        "Ping ao modelo demorou demasiado (tentativa %d/2)",
                        attempt,
                    )
                    if attempt < 2:
                        time.sleep(2.0)
                        continue
                    if self._try_activate_fallback():
                        return
                    raise ModelUnavailableError(
                        f"Modelo '{self.model}' nao responde a tempo. "
                        "No LM Studio: confirma que o modelo esta em Load "
                        "(barra de progresso concluida) e o Local Server ON. "
                        f"Primeira resposta do Phi-4 pode demorar >{ping_timeout:.0f}s."
                    ) from exc
                if self._try_activate_fallback():
                    return
                raise NetworkError(f"Nao consegui ligar a {base}: {exc}") from exc
            except APITimeoutError as exc:
                last_exc = exc
                logger.warning(
                    "Timeout no ping do modelo (tentativa %d/2)",
                    attempt,
                )
                if attempt < 2:
                    time.sleep(2.0)
                    continue
                if self._try_activate_fallback():
                    return
                raise ModelUnavailableError(
                    f"Modelo '{self.model}' nao responde a tempo. "
                    "Espera o Load terminar no LM Studio e volta a correr. "
                    f"(timeout {ping_timeout:.0f}s)"
                ) from exc
            except APIStatusError as exc:
                if self._try_activate_fallback():
                    return
                _raise_from_status(
                    exc,
                    unloaded_msg=(
                        f"Modelo '{self.model}' esta unloaded. "
                        "No LM Studio: escolhe o modelo, Load, e Server ON."
                    ),
                )
        if self._try_activate_fallback():
            return
        raise ModelUnavailableError(str(last_exc))

    def _try_activate_fallback(self) -> bool:
        if not self._fallback or not self._fallback_model:
            return False
        fb_url = self._settings.llm_fallback_base_url
        try:
            with httpx.Client(timeout=httpx.Timeout(5.0, connect=3.0)) as http:
                resp = http.get(f"{fb_url.rstrip('/')}/models")
                resp.raise_for_status()
            self._ping_completion(
                self._fallback,
                self._fallback_model,
                timeout_s=max(30.0, float(self._settings.llm_timeout_seconds)),
            )
        except Exception as exc:
            logger.warning("Fallback LLM indisponivel (%s): %s", fb_url, exc)
            return False
        self._client = self._fallback
        self.model = self._fallback_model
        self._active_base = fb_url
        self._vision_model_cache = None
        self._vision_verified_model = None
        self._vision_verified_at = 0.0
        logger.warning(
            "A usar LLM fallback: %s model=%s",
            fb_url,
            self._fallback_model,
        )
        return True

    def create_completion(self, **kwargs: Any):
        vision = bool(kwargs.pop("vision", False))
        model = kwargs.pop("model", None) or self.resolve_model(vision=vision)
        last_exc: Exception | None = None
        for attempt in range(2):
            try:
                return self._client.chat.completions.create(model=model, **kwargs)
            except APIConnectionError as exc:
                last_exc = exc
                if attempt == 0 and self._try_activate_fallback():
                    model = self.resolve_model(vision=vision)
                    continue
                if attempt == 0:
                    time.sleep(0.5)
                    continue
                raise NetworkError(str(exc)) from exc
            except APITimeoutError as exc:
                if self._try_activate_fallback():
                    try:
                        model = self.resolve_model(vision=vision)
                        return self._client.chat.completions.create(
                            model=model, **kwargs
                        )
                    except Exception as fb_exc:
                        raise PipelineTimeoutError(str(fb_exc)) from fb_exc
                raise PipelineTimeoutError(str(exc)) from exc
            except APIStatusError as exc:
                if self._try_activate_fallback():
                    try:
                        model = self.resolve_model(vision=vision)
                        return self._client.chat.completions.create(
                            model=model, **kwargs
                        )
                    except APIStatusError as fb_exc:
                        _raise_from_status(
                            fb_exc,
                            unloaded_msg=(
                                "Modelo fallback nao carregado. "
                                "Verifica Ollama / llama-server."
                            ),
                        )
                _raise_from_status(
                    exc,
                    unloaded_msg=(
                        "Modelo nao carregado no LM Studio. "
                        "Carrega o modelo e mantem o servidor local activo."
                    ),
                )
        raise NetworkError(str(last_exc))

    def stream_completion(self, **kwargs: Any) -> Iterator[str]:
        """Yield text deltas from a streaming chat completion."""
        vision = bool(kwargs.pop("vision", False))
        model = kwargs.pop("model", None) or self.resolve_model(vision=vision)
        kwargs = {**kwargs, "stream": True}
        try:
            stream = self._client.chat.completions.create(model=model, **kwargs)
        except (APIConnectionError, APITimeoutError, APIStatusError):
            if not self._try_activate_fallback():
                raise
            model = self.resolve_model(vision=vision)
            stream = self._client.chat.completions.create(model=model, **kwargs)
        for chunk in stream:
            try:
                delta = chunk.choices[0].delta
            except (IndexError, AttributeError):
                continue
            text = getattr(delta, "content", None)
            if text:
                yield text

    def stream_message(self, **kwargs: Any) -> Iterator[tuple[str, Any]]:
        """
        Single-pass stream. Yields ('token', str) then one ('final', StreamResult).
        Accumulates native tool_call deltas without a separate probe completion.
        """
        vision = bool(kwargs.pop("vision", False))
        model = kwargs.pop("model", None) or self.resolve_model(vision=vision)
        kwargs = {**kwargs, "stream": True}
        try:
            stream = self._client.chat.completions.create(model=model, **kwargs)
        except (APIConnectionError, APITimeoutError, APIStatusError):
            if not self._try_activate_fallback():
                raise
            model = self.resolve_model(vision=vision)
            stream = self._client.chat.completions.create(model=model, **kwargs)

        state = StreamResult()
        tool_bufs: dict[int, Any] = {}
        for chunk in stream:
            delta_text = accumulate_stream_chunk(state, chunk, tool_bufs=tool_bufs)
            if delta_text:
                yield ("token", delta_text)
        finalize_tool_bufs(state, tool_bufs)
        yield ("final", state)
