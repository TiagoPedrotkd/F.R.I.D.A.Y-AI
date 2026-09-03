"""Lightweight user productivity patterns (prefs + defaults)."""

from __future__ import annotations

from typing import Any

from friday.config import Settings, get_settings
from friday.memory.prefs_store import PrefsStore

_PATTERN_DEFAULTS: dict[str, Any] = {
    "timezone": "Europe/Lisbon",
    "working_hours": "9:00-18:00",
    "do_not_disturb": "22:00-8:00",
    "preferred_meeting_duration": 30,
    "preferred_event_duration": 30,
    "preferred_meeting_hour": 14,
    "email_response_time_hours": 4.5,
    "typical_events_per_day": 3,
    "confirmed_creates": 0,
    "confirmed_sends": 0,
}


def get_user_patterns(settings: Settings | None = None, user_id: str = "default") -> dict[str, Any]:
    settings = settings or get_settings()
    patterns = dict(_PATTERN_DEFAULTS)
    try:
        prefs = PrefsStore(settings.prefs_dir).get(user_id)
        stored = prefs.get("productivity_patterns")
        if isinstance(stored, dict):
            for k, v in stored.items():
                if k in _PATTERN_DEFAULTS:
                    patterns[k] = v
        if prefs.get("user_address"):
            patterns["user_address"] = prefs["user_address"]
    except Exception:
        pass
    return patterns


def bump_pattern_counter(key: str, *, user_id: str = "default", delta: int = 1) -> dict[str, Any]:
    settings = get_settings()
    store = PrefsStore(settings.prefs_dir)
    prefs = store.get(user_id)
    patterns = dict(_PATTERN_DEFAULTS)
    raw = prefs.get("productivity_patterns")
    if isinstance(raw, dict):
        patterns.update({k: v for k, v in raw.items() if k in _PATTERN_DEFAULTS})
    if key in patterns and isinstance(patterns[key], (int, float)):
        patterns[key] = int(patterns[key]) + delta
    # Persist via prefs update — productivity_patterns allowed in store defaults
    return store.update({"productivity_patterns": patterns}, user_id=user_id)
