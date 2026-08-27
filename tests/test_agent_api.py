"""Tests for agent-api (sessions, chat, confirm, monitors, status)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

API_DIR = Path(__file__).resolve().parents[1] / "services" / "agent-api"
sys.path.insert(0, str(API_DIR))

from fastapi.testclient import TestClient  # noqa: E402

import main as agent_main  # noqa: E402
from friday.llm.tool_runner import ChatReply  # noqa: E402
from friday.safety.confirmation import PendingAction  # noqa: E402
from session_store import store  # noqa: E402


@pytest.fixture(autouse=True)
def _clear_sessions():
    store._sessions.clear()
    yield
    store._sessions.clear()


@pytest.fixture
def client():
    return TestClient(agent_main.app)


def test_health(client: TestClient):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["service"] == "friday-agent-api"


def test_status_demo_when_llm_down(client: TestClient):
    with patch.object(
        agent_main,
        "_probe_llm",
        new=AsyncMock(return_value={"ok": False, "via": "lm_studio", "model": "x", "error": "down"}),
    ):
        r = client.get("/v1/status")
    assert r.status_code == 200
    body = r.json()
    assert body["demo"] is True
    assert body["backend"] is True


def test_session_lifecycle(client: TestClient):
    r = client.post("/v1/sessions")
    assert r.status_code == 200
    sid = r.json()["id"]
    assert sid

    g = client.get(f"/v1/sessions/{sid}")
    assert g.status_code == 200
    assert g.json()["id"] == sid

    d = client.delete(f"/v1/sessions/{sid}")
    assert d.status_code == 200
    assert client.get(f"/v1/sessions/{sid}").status_code == 404


def test_chat_mocked_toolrunner(client: TestClient):
    sid = client.post("/v1/sessions").json()["id"]
    reply = ChatReply(
        text="Sao 10 horas.",
        tool_rounds=1,
        skill_metadata={"kind": "datetime"},
    )
    with patch("session_store.ToolRunner") as TR:
        TR.return_value.chat_with_tools = AsyncMock(return_value=reply)
        r = client.post("/v1/chat", json={"session_id": sid, "text": "Que horas sao?"})
    assert r.status_code == 200
    body = r.json()
    assert "10 horas" in body["reply"]
    assert body["activity"]
    assert body["session"]["last_language"] in ("pt", "en")


def test_confirm_flow(client: TestClient):
    sid = client.post("/v1/sessions").json()["id"]
    session = store.get(sid)
    assert session is not None
    session.gate.request(
        PendingAction(
            action="send_email",
            target="a@b.c",
            summary="enviar email",
            consequences="envia",
        )
    )
    r = client.post(
        "/v1/confirm",
        json={"session_id": sid, "decision": "confirm"},
    )
    assert r.status_code == 200
    assert r.json()["decision"] == "confirmed"
    assert session.gate.pending is None


def test_confirm_cancel(client: TestClient):
    sid = client.post("/v1/sessions").json()["id"]
    session = store.get(sid)
    assert session is not None
    session.gate.request(
        PendingAction(action="delete", target="x", summary="apagar ficheiro")
    )
    r = client.post(
        "/v1/confirm",
        json={"session_id": sid, "decision": "cancel"},
    )
    assert r.status_code == 200
    assert r.json()["decision"] == "denied"


def test_monitor_ssrf_path_traversal(client: TestClient):
    # Starlette may normalize ".." before the route (404); helper still rejects.
    assert client.get("/monitors/../config.py").status_code in (400, 404)
    assert client.get("/monitors/nope.html").status_code == 404
    with pytest.raises(agent_main.HTTPException) as exc_info:
        agent_main._safe_monitor_path("../secrets.env")
    assert exc_info.value.status_code == 400
    with pytest.raises(agent_main.HTTPException) as exc_info:
        agent_main._safe_monitor_path("missing_snapshot.html")
    assert exc_info.value.status_code == 404


def test_monitor_serves_world_html(client: TestClient):
    r = client.get("/monitors/world.html")
    assert r.status_code == 200
    assert "html" in r.headers.get("content-type", "").lower()


def test_chat_unknown_session(client: TestClient):
    r = client.post("/v1/chat", json={"session_id": "missing", "text": "ola"})
    assert r.status_code == 404
