"""Local contact book for name → email disambiguation."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from friday.config import Settings, get_settings


def contacts_path(settings: Settings | None = None) -> Path:
    settings = settings or get_settings()
    return Path(settings.prefs_dir).parent / "contacts" / "default.json"


def load_contacts(settings: Settings | None = None) -> list[dict[str, Any]]:
    path = contacts_path(settings)
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return [c for c in data if isinstance(c, dict) and c.get("name")]
        if isinstance(data, dict) and isinstance(data.get("contacts"), list):
            return [c for c in data["contacts"] if isinstance(c, dict)]
    except (OSError, json.JSONDecodeError):
        pass
    return []


def save_contacts(contacts: list[dict[str, Any]], settings: Settings | None = None) -> Path:
    path = contacts_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"contacts": contacts}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def resolve_contact(query: str, settings: Settings | None = None) -> dict[str, Any]:
    """
    Returns:
      {"status": "exact"|"ambiguous"|"none", "matches": [...], "email": optional}
    """
    q = (query or "").strip()
    if not q:
        return {"status": "none", "matches": []}
    if "@" in q:
        return {"status": "exact", "matches": [{"name": q, "email": q}], "email": q}

    contacts = load_contacts(settings)
    norm = re.sub(r"\s+", " ", q.casefold())
    matches: list[dict[str, Any]] = []
    for c in contacts:
        name = str(c.get("name") or "")
        email = str(c.get("email") or "")
        aliases = c.get("aliases") or []
        hay = " ".join([name, email, *[str(a) for a in aliases]]).casefold()
        if norm in hay or any(norm == str(a).casefold() for a in [name, *aliases]):
            matches.append({"name": name, "email": email, "role": c.get("role")})
    # unique by email
    seen: set[str] = set()
    uniq: list[dict[str, Any]] = []
    for m in matches:
        em = str(m.get("email") or "")
        if em in seen:
            continue
        seen.add(em)
        uniq.append(m)
    if len(uniq) == 1:
        return {"status": "exact", "matches": uniq, "email": uniq[0].get("email")}
    if len(uniq) > 1:
        return {"status": "ambiguous", "matches": uniq}
    return {"status": "none", "matches": []}
