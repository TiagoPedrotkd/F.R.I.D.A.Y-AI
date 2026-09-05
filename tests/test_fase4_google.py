"""Fase 4 — Google OAuth, health cache, calendar/email providers (mocked)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from friday.config import Settings
from friday.integrations.google_health import empty_day, list_days, write_day
from friday.integrations.google_oauth import (
    GoogleOAuthError,
    build_auth_url,
    google_configured,
    save_tokens,
    status,
)
from friday.productivity.calendar_provider import calendar_available, use_google
from friday.productivity.email_provider import email_available
from friday.skills.registry import default_registry


def _settings(**kwargs) -> Settings:
    base = {
        "GOOGLE_ENABLED": True,
        "GOOGLE_CLIENT_ID": "cid.apps.googleusercontent.com",
        "GOOGLE_CLIENT_SECRET": "secret",
        "GOOGLE_REDIRECT_URI": "http://127.0.0.1:8090/v1/google/callback",
        "CALDAV_ENABLED": True,
        "CALDAV_URL": "http://127.0.0.1:5232/friday/",
        "EMAIL_ENABLED": False,
    }
    base.update(kwargs)
    return Settings(**base)


def test_fase4_docs_exist():
    root = Path("docs/fase-4")
    for name in (
        "README.md",
        "google-oauth.md",
        "saude.md",
        "calendar-gmail.md",
        "skills-contract.md",
        "checklist-conclusao.md",
    ):
        assert (root / name).is_file(), name


def test_google_configured():
    assert google_configured(_settings())
    assert not google_configured(_settings(GOOGLE_ENABLED=False))


def test_build_auth_url():
    out = build_auth_url(_settings())
    assert "accounts.google.com" in out["url"]
    assert "state" in out


def test_build_auth_url_requires_config():
    with pytest.raises(GoogleOAuthError):
        build_auth_url(_settings(GOOGLE_CLIENT_ID=""))


def test_oauth_status(tmp_path: Path):
    s = _settings(GOOGLE_TOKEN_PATH=str(tmp_path / "tok.json"))
    st = status(s)
    assert st["enabled"] is True
    assert st["connected"] is False
    save_tokens({"refresh_token": "r", "access_token": "a"}, s)
    assert status(s)["connected"] is True


def test_health_cache_roundtrip(tmp_path: Path, monkeypatch):
    # Point prefs_dir parent so integrations_root lands under tmp
    prefs = tmp_path / "prefs"
    prefs.mkdir()
    s = Settings(PREFS_DIR=str(prefs), GOOGLE_ENABLED=False)
    row = empty_day()
    row["steps"] = 1234
    row["source"] = "test"
    write_day(row, s)
    listed = list_days(s, limit=5)
    assert listed["count"] >= 1
    assert listed["days"][0]["steps"] == 1234


def test_calendar_available_caldav_fallback():
    s = _settings(GOOGLE_ENABLED=False)
    assert calendar_available(s) is True
    assert use_google(s) is False


def test_email_available_false_when_disabled():
    s = _settings(GOOGLE_ENABLED=False, EMAIL_ENABLED=False)
    assert email_available(s) is False


def test_health_day_skill_registered():
    reg = default_registry(Settings())
    assert "get_health_summary" in reg.names()
    assert "get_health_day" in reg.names()


def test_google_status_endpoint(tmp_path: Path):
    import sys

    API_DIR = Path(__file__).resolve().parents[1] / "services" / "agent-api"
    sys.path.insert(0, str(API_DIR))
    from fastapi.testclient import TestClient

    import main as agent_main
    from unittest.mock import MagicMock, patch

    client = TestClient(agent_main.app)
    settings = MagicMock()
    settings.google_enabled = True
    settings.google_client_id = "cid"
    settings.google_client_secret = "sec"
    settings.google_redirect_uri = "http://127.0.0.1:8090/v1/google/callback"
    settings.google_token_path = tmp_path / "t.json"
    with patch.object(agent_main, "get_settings", return_value=settings):
        with patch("friday.integrations.google_oauth.get_settings", return_value=settings):
            r = client.get("/v1/google/status")
    assert r.status_code == 200
    assert r.json()["enabled"] is True
