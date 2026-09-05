"""Google OAuth 2.0 (local installed-app / localhost callback) — Fase 4."""

from __future__ import annotations

import json
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from friday.config import Settings, get_settings

# Calendar + Gmail + Fitness (legacy Google Fit scopes still usable on personal Testing apps)
DEFAULT_SCOPES = (
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/fitness.activity.read",
    "https://www.googleapis.com/auth/fitness.sleep.read",
    "https://www.googleapis.com/auth/fitness.heart_rate.read",
)

AUTH_URI = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URI = "https://oauth2.googleapis.com/token"


class GoogleOAuthError(RuntimeError):
    pass


def _token_path(settings: Settings) -> Path:
    return Path(settings.google_token_path)


def load_tokens(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    path = _token_path(settings)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_tokens(tokens: dict[str, Any], settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    path = _token_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(tokens, indent=2), encoding="utf-8")


def clear_tokens(settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    path = _token_path(settings)
    if path.is_file():
        path.unlink()


def google_configured(settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    return bool(
        settings.google_enabled
        and (settings.google_client_id or "").strip()
        and (settings.google_client_secret or "").strip()
    )


def google_connected(settings: Settings | None = None) -> bool:
    tokens = load_tokens(settings)
    return bool(tokens.get("refresh_token") or tokens.get("access_token"))


def status(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    tokens = load_tokens(settings)
    return {
        "enabled": bool(settings.google_enabled),
        "configured": google_configured(settings),
        "connected": google_connected(settings),
        "has_refresh_token": bool(tokens.get("refresh_token")),
        "scopes": list(DEFAULT_SCOPES),
        "redirect_uri": settings.google_redirect_uri,
    }


def build_auth_url(settings: Settings | None = None, *, state: str | None = None) -> dict[str, str]:
    settings = settings or get_settings()
    if not google_configured(settings):
        raise GoogleOAuthError(
            "Google nao configurado (GOOGLE_ENABLED + CLIENT_ID + CLIENT_SECRET)."
        )
    st = state or secrets.token_urlsafe(24)
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": " ".join(DEFAULT_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": st,
        "include_granted_scopes": "true",
    }
    return {"url": f"{AUTH_URI}?{urllib.parse.urlencode(params)}", "state": st}


def _post_token(body: dict[str, str]) -> dict[str, Any]:
    data = urllib.parse.urlencode(body).encode("utf-8")
    req = urllib.request.Request(
        TOKEN_URI,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:  # noqa: S310
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")[:400]
        raise GoogleOAuthError(f"Token exchange HTTP {exc.code}: {detail}") from exc
    except Exception as exc:
        raise GoogleOAuthError(f"Token exchange falhou: {exc}") from exc


def exchange_code(code: str, settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    if not google_configured(settings):
        raise GoogleOAuthError("Google nao configurado.")
    code = (code or "").strip()
    if not code:
        raise GoogleOAuthError("code em falta.")
    raw = _post_token(
        {
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": settings.google_redirect_uri,
            "grant_type": "authorization_code",
        }
    )
    existing = load_tokens(settings)
    merged = {**existing, **raw}
    if not merged.get("refresh_token") and existing.get("refresh_token"):
        merged["refresh_token"] = existing["refresh_token"]
    merged["obtained_at"] = int(time.time())
    if "expires_in" in raw:
        merged["expires_at"] = int(time.time()) + int(raw["expires_in"])
    save_tokens(merged, settings)
    return {"ok": True, "connected": True}


def refresh_access_token(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    tokens = load_tokens(settings)
    refresh = tokens.get("refresh_token")
    if not refresh:
        raise GoogleOAuthError("Sem refresh_token — reconecta a conta Google.")
    raw = _post_token(
        {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "refresh_token": str(refresh),
            "grant_type": "refresh_token",
        }
    )
    merged = {**tokens, **raw}
    merged["obtained_at"] = int(time.time())
    if "expires_in" in raw:
        merged["expires_at"] = int(time.time()) + int(raw["expires_in"])
    save_tokens(merged, settings)
    return merged


def get_access_token(settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    if not google_configured(settings):
        raise GoogleOAuthError("Google nao configurado.")
    tokens = load_tokens(settings)
    access = tokens.get("access_token")
    expires_at = int(tokens.get("expires_at") or 0)
    if access and expires_at > int(time.time()) + 60:
        return str(access)
    if tokens.get("refresh_token"):
        refreshed = refresh_access_token(settings)
        return str(refreshed.get("access_token") or "")
    if access:
        return str(access)
    raise GoogleOAuthError("Sem access_token — conecta Google em Definições.")


def google_request(
    url: str,
    *,
    settings: Settings | None = None,
    method: str = "GET",
    body: dict[str, Any] | None = None,
    timeout: float = 20.0,
) -> Any:
    token = get_access_token(settings)
    data = None
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            raw = resp.read().decode("utf-8")
            if not raw:
                return {"ok": True, "status": resp.status}
            return json.loads(raw)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")[:400]
        raise GoogleOAuthError(f"Google HTTP {exc.code}: {detail}") from exc
    except Exception as exc:
        raise GoogleOAuthError(f"Google unreachable: {exc}") from exc
