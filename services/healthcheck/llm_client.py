"""LM Studio client via OpenAI-compatible API."""

import os
from dataclasses import dataclass

from openai import APIConnectionError, APIStatusError, OpenAI


@dataclass(frozen=True)
class LlmConfig:
    base_url: str
    model: str
    api_key: str


@dataclass(frozen=True)
class LlmHealthResult:
    ok: bool
    model: str
    response_preview: str | None = None
    error: str | None = None


def load_config() -> LlmConfig:
    return LlmConfig(
        base_url=os.getenv("LM_STUDIO_BASE_URL", "http://host.docker.internal:1234/v1"),
        model=os.getenv("LM_STUDIO_MODEL", "microsoft/phi-4"),
        api_key=os.getenv("LM_STUDIO_API_KEY", "lm-studio"),
    )


def check_llm(config: LlmConfig | None = None) -> LlmHealthResult:
    cfg = config or load_config()
    client = OpenAI(base_url=cfg.base_url, api_key=cfg.api_key)

    try:
        response = client.chat.completions.create(
            model=cfg.model,
            messages=[{"role": "user", "content": "Reply with exactly: OK"}],
            max_tokens=16,
            temperature=0,
        )
        content = (response.choices[0].message.content or "").strip()
        preview = content[:120] if content else "(empty response)"
        return LlmHealthResult(ok=True, model=cfg.model, response_preview=preview)
    except APIConnectionError:
        return LlmHealthResult(
            ok=False,
            model=cfg.model,
            error="Cannot reach LM Studio. Check LM_STUDIO_BASE_URL and that the server is running.",
        )
    except APIStatusError as exc:
        return LlmHealthResult(
            ok=False,
            model=cfg.model,
            error=f"LM Studio API error (HTTP {exc.status_code})",
        )
    except Exception as exc:
        return LlmHealthResult(
            ok=False,
            model=cfg.model,
            error=f"Unexpected error: {type(exc).__name__}",
        )
