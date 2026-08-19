"""F.R.I.D.A.Y-AI Phase 0 healthcheck service."""

import os
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from llm_client import check_llm, load_config

APP_VERSION = "0.1.0-phase0"
SERVICE_NAME = "friday-healthcheck"

app = FastAPI(title="F.R.I.D.A.Y Healthcheck", version=APP_VERSION)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": SERVICE_NAME,
        "version": APP_VERSION,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@app.get("/ready")
async def ready():
    return {"status": "ready", "service": SERVICE_NAME}


@app.get("/health/llm")
async def health_llm():
    config = load_config()
    result = check_llm(config)

    payload = {
        "status": "ok" if result.ok else "degraded",
        "service": SERVICE_NAME,
        "llm": {
            "provider": "lm-studio",
            "base_url": config.base_url,
            "model": result.model,
            "ok": result.ok,
        },
        "timestamp": datetime.now(UTC).isoformat(),
    }

    if result.ok:
        payload["llm"]["response_preview"] = result.response_preview
    else:
        payload["llm"]["error"] = result.error

    status_code = 200 if result.ok else 503
    return JSONResponse(content=payload, status_code=status_code)


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("HEALTHCHECK_PORT", "8080"))
    host = os.getenv("HEALTHCHECK_HOST", "0.0.0.0")
    uvicorn.run("main:app", host=host, port=port, reload=False)
