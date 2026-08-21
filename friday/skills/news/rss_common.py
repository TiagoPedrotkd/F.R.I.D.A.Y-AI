"""Shared helpers for RSS news and local monitors."""

from __future__ import annotations

import html
import json
import logging
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

_MONITORS_DIR = Path(__file__).resolve().parent.parent.parent / "monitors"
_DATA_DIR = _MONITORS_DIR / "data"

DEFAULT_WORLD_FEEDS = (
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://feeds.bbci.co.uk/news/rss.xml",
)

DEFAULT_FINANCE_FEEDS = (
    "https://feeds.bbci.co.uk/news/business/rss.xml",
    "https://www.cnbc.com/id/100003114/device/rss/rss.html",
)


def parse_feed_csv(raw: str | None, defaults: tuple[str, ...]) -> list[str]:
    if not raw or not raw.strip():
        return list(defaults)
    return [u.strip() for u in raw.split(",") if u.strip()]


def _strip_html(summary: str) -> str:
    if "<" not in summary:
        return summary
    import re

    summary = re.sub(r"<[^>]+>", " ", summary)
    return re.sub(r"\s+", " ", summary).strip()


def _entry_headline(entry: Any) -> dict[str, str] | None:
    title = (getattr(entry, "title", None) or "").strip()
    if not title:
        return None
    link = (getattr(entry, "link", None) or "").strip()
    summary = _strip_html((getattr(entry, "summary", None) or "")[:200])
    return {"title": title, "link": link, "summary": summary}


def _fetch_one_feed(feed_url: str) -> list[Any]:
    import feedparser

    with httpx.Client(timeout=15.0, follow_redirects=True) as client:
        resp = client.get(feed_url, headers={"User-Agent": "FRIDAY-AI/0.2"})
        resp.raise_for_status()
        return list(feedparser.parse(resp.content).entries)


def fetch_rss_headlines(feed_urls: list[str], limit: int = 8) -> list[dict[str, str]]:
    headlines: list[dict[str, str]] = []
    seen: set[str] = set()

    for feed_url in feed_urls:
        try:
            entries = _fetch_one_feed(feed_url)
        except Exception as exc:
            logger.warning("RSS failed %s: %s", feed_url, exc)
            continue

        for entry in entries:
            item = _entry_headline(entry)
            if not item or item["title"] in seen:
                continue
            seen.add(item["title"])
            headlines.append(item)
            if len(headlines) >= limit:
                return headlines
    return headlines


def guess_lat_lon(text: str) -> tuple[float, float] | None:
    """Heuristic region → coordinates for map markers (not precise geocoding)."""
    t = text.casefold()
    regions: list[tuple[tuple[str, ...], tuple[float, float]]] = [
        (("ukraine", "ucrania", "kyiv", "kiev"), (50.45, 30.52)),
        (("russia", "russia", "moscow", "moscovo"), (55.75, 37.62)),
        (("china", "beijing", "pequim", "taiwan"), (39.90, 116.40)),
        (("israel", "gaza", "palestine", "palestina"), (31.5, 34.75)),
        (("iran", "tehran", "irao"), (35.69, 51.39)),
        (("usa", "united states", "washington", "estados unidos"), (38.90, -77.04)),
        (("uk", "britain", "london", "reino unido", "inglaterra"), (51.50, -0.12)),
        (("france", "franca", "paris"), (48.86, 2.35)),
        (("germany", "alemanha", "berlin"), (52.52, 13.40)),
        (("portugal", "lisboa", "lisbon"), (38.72, -9.14)),
        (("spain", "espanha", "madrid"), (40.42, -3.70)),
        (("brazil", "brasil", "brasilia"), (-15.79, -47.88)),
        (("india", "india", "delhi", "new delhi"), (28.61, 77.21)),
        (("japan", "japao", "tokyo", "toquio"), (35.68, 139.69)),
        (("korea", "coreia", "seoul", "seul"), (37.57, 126.98)),
        (("africa", "nigeria", "kenya", "south africa"), (0.0, 20.0)),
        (("middle east", "medio oriente", "saudi"), (24.7, 46.7)),
        (("europe", "europa", "eu "), (50.0, 10.0)),
        (("market", "stock", "wall street", "nasdaq", "economia"), (40.71, -74.01)),
        (("oil", "petroleo", "opec"), (25.2, 55.3)),
    ]
    for keys, coords in regions:
        if any(k in t for k in keys):
            return coords
    return (20.0, 0.0)  # default: mid Atlantic / world view center-ish


def _enrich_headlines(headlines: list[dict[str, str]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for h in headlines:
        blob = f"{h.get('title', '')} {h.get('summary', '')}"
        latlon = guess_lat_lon(blob)
        item = dict(h)
        if latlon:
            item["lat"], item["lon"] = latlon
        out.append(item)
    return out


def _render_snapshot(kind: str, title: str, headlines: list[dict[str, str]], updated: str) -> str:
    accent = "#3d8bfd" if kind == "world" else "#6bcf7f"
    bg = "#0f1419" if kind == "world" else "#10140f"
    enriched = _enrich_headlines(headlines)
    items = []
    markers_js = []
    for h in enriched:
        link = html.escape(h.get("link") or "#")
        t = html.escape(h.get("title") or "")
        s = html.escape(h.get("summary") or "")
        items.append(
            f'<article><a href="{link}" target="_blank" rel="noopener">{t}</a>'
            f'{f"<div class=summary>{s}</div>" if s else ""}</article>'
        )
        lat, lon = h.get("lat", 20.0), h.get("lon", 0.0)
        popup = (
            html.escape(h.get("title") or "")
            .replace("\\", "\\\\")
            .replace("'", "\\'")
        )
        markers_js.append(
            f"L.marker([{lat},{lon}]).addTo(map).bindPopup('{popup}');"
        )
    body = "\n".join(items) or "<p>Sem headlines.</p>"
    markers_block = "\n".join(markers_js)
    return f"""<!DOCTYPE html>
<html lang="pt"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{html.escape(title)}</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<style>
body{{margin:0;font-family:Segoe UI,system-ui,sans-serif;background:{bg};color:#e7ecf1}}
header{{padding:1rem 1.25rem;border-bottom:1px solid #243041}}
h1{{margin:0;font-size:1.2rem}}
#meta{{color:#8b9aab;font-size:.85rem;margin-top:.3rem}}
.layout{{display:grid;grid-template-columns:1.2fr 1fr;min-height:calc(100vh - 70px)}}
@media(max-width:900px){{.layout{{grid-template-columns:1fr}}}}
#map{{min-height:420px;background:#1a2330}}
#list{{padding:1rem 1.25rem;overflow:auto;max-height:calc(100vh - 70px)}}
article{{padding:.75rem 0;border-bottom:1px solid #1c2734}}
a{{color:{accent};text-decoration:none}} a:hover{{text-decoration:underline}}
.summary{{color:#8b9aab;font-size:.88rem;margin-top:.2rem}}
</style></head><body>
<header><h1>{html.escape(title)}</h1>
<div id="meta">Actualizado: {html.escape(updated)} — mapa aproximado por palavras-chave</div></header>
<div class="layout">
  <div id="map"></div>
  <div id="list">{body}</div>
</div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const map = L.map('map').setView([20, 0], 2);
L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
  maxZoom: 6,
  attribution: '&copy; OpenStreetMap'
}}).addTo(map);
{markers_block}
</script>
</body></html>
"""


def write_monitor_data(kind: str, headlines: list[dict[str, str]]) -> Path:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    updated = datetime.now(timezone.utc).isoformat()
    path = _DATA_DIR / f"{kind}.json"
    payload = {"updated_at": updated, "kind": kind, "headlines": headlines}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    title = "FRIDAY World Monitor" if kind == "world" else "FRIDAY Finance Monitor"
    snap = _MONITORS_DIR / f"{kind}_snapshot.html"
    snap.write_text(
        _render_snapshot(kind, title, headlines, updated),
        encoding="utf-8",
    )
    return snap


def open_monitor(kind: str, override_url: str = "") -> tuple[bool, str]:
    """Open external URL or local HTML snapshot. Returns (ok, message)."""
    if override_url.strip():
        url = override_url.strip()
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https", "file"):
            return False, "URL do monitor invalida."
        webbrowser.open(url)
        return True, f"A abrir o monitor ({url})."

    snap = (_MONITORS_DIR / f"{kind}_snapshot.html").resolve()
    if not snap.is_file():
        # Ensure a usable snapshot exists (templates with fetch() break on file://)
        write_monitor_data(kind, [])
        snap = (_MONITORS_DIR / f"{kind}_snapshot.html").resolve()
    if not snap.is_file():
        return False, "Nao consegui abrir o monitor (ficheiro em falta)."
    webbrowser.open(snap.as_uri())
    return True, f"A abrir o monitor {kind}."


def summarize_headlines(headlines: list[dict[str, str]], label: str) -> str:
    if not headlines:
        return ""
    bullets = [f"- {h['title']}" for h in headlines[:8]]
    return f"{label}\n" + "\n".join(bullets)
