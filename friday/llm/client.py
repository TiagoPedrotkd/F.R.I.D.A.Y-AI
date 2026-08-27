"""OpenAI-compatible client for Bionic / LM Studio."""

from __future__ import annotations

import logging
import time
from typing import NoReturn

import httpx
from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI

from friday.config import Settings
from friday.pipeline.errors import APITimeoutError as PipelineTimeoutError
from friday.pipeline.errors import ModelUnavailableError, NetworkError

logger = logging.getLogger(__name__)


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


class LlmClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        timeout = httpx.Timeout(settings.llm_timeout_seconds, connect=5.0)
        self._client = OpenAI(
            base_url=settings.lm_studio_base_url_host,
            api_key=settings.lm_studio_api_key,
            timeout=timeout,
            max_retries=0,
        )
        self.model = settings.lm_studio_model

    def list_model_ids(self) -> list[str]:
        try:
            models = self._client.models.list()
            return [m.id for m in models.data]
        except Exception as exc:
            logger.debug("Could not list models: %s", exc)
            return []

    def _ping_completion(self, model: str, *, timeout_s: float) -> None:
        ping = OpenAI(
            base_url=self._settings.lm_studio_base_url_host,
            api_key=self._settings.lm_studio_api_key,
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
        Verify LM Studio is up and the configured model can produce a token.
        First load of large models (e.g. Phi-4) can take tens of seconds.
        """
        base = self._settings.lm_studio_base_url_host
        # Fast path: is the server listening?
        try:
            with httpx.Client(timeout=httpx.Timeout(5.0, connect=3.0)) as http:
                resp = http.get(f"{base.rstrip('/')}/models")
                resp.raise_for_status()
        except httpx.ConnectError as exc:
            raise NetworkError(
                f"Nao consegui ligar a {base}: servidor recusou a ligacao. "
                "Abre o LM Studio e inicia o Local Server (porta 1234)."
            ) from exc
        except Exception as exc:
            raise NetworkError(
                f"Nao consegui ligar a {base}: {exc}"
            ) from exc

        # Cold start can be slow — allow up to max(60, configured timeout)
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
                self._ping_completion(self.model, timeout_s=ping_timeout)
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
                    raise ModelUnavailableError(
                        f"Modelo '{self.model}' nao responde a tempo. "
                        "No LM Studio: confirma que o modelo esta em Load "
                        "(barra de progresso concluida) e o Local Server ON. "
                        f"Primeira resposta do Phi-4 pode demorar >{ping_timeout:.0f}s."
                    ) from exc
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
                raise ModelUnavailableError(
                    f"Modelo '{self.model}' nao responde a tempo. "
                    "Espera o Load terminar no LM Studio e volta a correr. "
                    f"(timeout {ping_timeout:.0f}s)"
                ) from exc
            except APIStatusError as exc:
                _raise_from_status(
                    exc,
                    unloaded_msg=(
                        f"Modelo '{self.model}' esta unloaded. "
                        "No LM Studio: escolhe o modelo, Load, e Server ON."
                    ),
                )
        raise ModelUnavailableError(str(last_exc))

    def create_completion(self, **kwargs):
        last_exc: Exception | None = None
        for attempt in range(2):
            try:
                return self._client.chat.completions.create(model=self.model, **kwargs)
            except APIConnectionError as exc:
                last_exc = exc
                if attempt == 0:
                    time.sleep(0.5)
                    continue
                raise NetworkError(str(exc)) from exc
            except APITimeoutError as exc:
                raise PipelineTimeoutError(str(exc)) from exc
            except APIStatusError as exc:
                _raise_from_status(
                    exc,
                    unloaded_msg=(
                        "Modelo nao carregado no LM Studio. "
                        "Carrega o modelo e mantem o servidor local activo."
                    ),
                )
        raise NetworkError(str(last_exc))
