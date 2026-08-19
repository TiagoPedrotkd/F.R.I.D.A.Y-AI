"""OpenAI-compatible client for Bionic / LM Studio."""

from __future__ import annotations

import time

import httpx
from openai import APIConnectionError, APITimeoutError, OpenAI

from friday.config import Settings
from friday.pipeline.errors import APITimeoutError as PipelineTimeoutError
from friday.pipeline.errors import NetworkError


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
        raise NetworkError(str(last_exc))
