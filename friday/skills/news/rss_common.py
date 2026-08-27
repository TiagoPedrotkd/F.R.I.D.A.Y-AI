"""Shared helpers for RSS news and local monitors."""

from __future__ import annotations

# Bump when monitor HTML chrome changes so stale snapshots get rewritten.
SNAPSHOT_TEMPLATE_VERSION = "hud-v2"

import hashlib
import html
import json
import logging
import os
import time
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from friday.skills.news.countries import CountryProfile

logger = logging.getLogger(__name__)

_MONITORS_DIR = Path(__file__).resolve().parent.parent.parent / "monitors"
_DATA_DIR = _MONITORS_DIR / "data"
_REPO_ROOT = Path(__file__).resolve().parents[3]
_CACHE_DIR = _REPO_ROOT / "data" / "news_cache"
_CACHE_TTL_SECONDS = 10 * 60

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


def _cache_key(feed_urls: list[str], limit: int) -> str:
    blob = f"{limit}|{'|'.join(feed_urls)}"
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:24]


def _read_cache(key: str) -> list[dict[str, str]] | None:
    path = _CACHE_DIR / f"{key}.json"
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if time.time() - float(payload.get("ts", 0)) > _CACHE_TTL_SECONDS:
            return None
        headlines = payload.get("headlines")
        if isinstance(headlines, list):
            return headlines
    except Exception as exc:
        logger.debug("news cache read failed: %s", exc)
    return None


def _write_cache(key: str, headlines: list[dict[str, str]]) -> None:
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path = _CACHE_DIR / f"{key}.json"
        path.write_text(
            json.dumps({"ts": time.time(), "headlines": headlines}, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception as exc:
        logger.debug("news cache write failed: %s", exc)


def fetch_rss_headlines(
    feed_urls: list[str],
    limit: int = 8,
    *,
    use_cache: bool = True,
) -> list[dict[str, str]]:
    if use_cache:
        key = _cache_key(feed_urls, limit)
        cached = _read_cache(key)
        if cached is not None:
            return cached[:limit]

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
                break
        if len(headlines) >= limit:
            break

    if use_cache and headlines:
        _write_cache(_cache_key(feed_urls, limit), headlines)
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
    return (20.0, 0.0)


def _enrich_headlines(
    headlines: list[dict[str, str]],
    *,
    default_lat_lon: tuple[float, float] | None = None,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for h in headlines:
        blob = f"{h.get('title', '')} {h.get('summary', '')}"
        latlon = guess_lat_lon(blob)
        if latlon == (20.0, 0.0) and default_lat_lon:
            latlon = default_lat_lon
        item = dict(h)
        if latlon:
            item["lat"], item["lon"] = latlon
        out.append(item)
    return out


def _render_snapshot(
    kind: str,
    title: str,
    headlines: list[dict[str, str]],
    updated: str,
    *,
    map_center: tuple[float, float] = (20.0, 0.0),
    map_zoom: int = 2,
    meta_note: str = "mapa aproximado por palavras-chave",
) -> str:
    is_finance = "finance" in kind
    accent = "#6bcf7f" if is_finance else "#5cefff"
    label = "FINANCE MONITOR" if is_finance else "WORLD MONITOR"
    enriched = _enrich_headlines(headlines, default_lat_lon=map_center)
    items = []
    markers_js = []
    for i, h in enumerate(enriched, start=1):
        link = html.escape(h.get("link") or "#")
        t = html.escape(h.get("title") or "")
        s = html.escape(h.get("summary") or "")
        idx = f"{i:02d}"
        items.append(
            f'<article class="holo-card">'
            f'<span class="idx">{idx}</span>'
            f'<div class="body">'
            f'<a href="{link}" target="_blank" rel="noopener">{t}</a>'
            f'{f"<p class=summary>{s}</p>" if s else ""}'
            f"</div></article>"
        )
        lat, lon = h.get("lat", map_center[0]), h.get("lon", map_center[1])
        popup = (
            html.escape(h.get("title") or "")
            .replace("\\", "\\\\")
            .replace("'", "\\'")
        )
        markers_js.append(
            f"L.circleMarker([{lat},{lon}],{{radius:6,color:'{accent}',"
            f"fillColor:'{accent}',fillOpacity:0.75,weight:1}})"
            f".addTo(map).bindPopup('{popup}');"
        )
    body = "\n".join(items) or '<p class="empty">Sem headlines.</p>'
    markers_block = "\n".join(markers_js)
    center_lat, center_lon = map_center
    safe_title = html.escape(title)
    safe_updated = html.escape(updated)
    safe_meta = html.escape(meta_note)
    return f"""<!DOCTYPE html>
<html lang="pt">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="friday-snapshot-version" content="{SNAPSHOT_TEMPLATE_VERSION}">
<title>{safe_title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;600;700&family=Source+Sans+3:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<style>
:root {{
  --cyan: {accent};
  --bg: #000208;
  --text: #e8fbff;
  --muted: #6eb8c9;
  --line: rgba(92, 239, 255, 0.18);
  --glow: 0 0 22px rgba(92, 239, 255, 0.4);
}}
* {{ box-sizing: border-box; }}
html, body {{ height: 100%; margin: 0; }}
body {{
  font-family: "Source Sans 3", system-ui, sans-serif;
  color: var(--text);
  background:
    radial-gradient(ellipse 55% 45% at 50% 28%, rgba(40, 160, 220, 0.16), transparent 60%),
    radial-gradient(ellipse 80% 70% at 50% 100%, rgba(0, 40, 80, 0.4), transparent 55%),
    var(--bg);
  overflow-x: hidden;
}}
body::before {{
  content: "";
  pointer-events: none;
  position: fixed;
  inset: 0;
  z-index: 0;
  opacity: 0.32;
  background-image:
    linear-gradient(var(--line) 1px, transparent 1px),
    linear-gradient(90deg, var(--line) 1px, transparent 1px);
  background-size: 56px 56px;
  mask-image: radial-gradient(ellipse 72% 68% at 50% 42%, black 8%, transparent 75%);
}}
body::after {{
  content: "";
  pointer-events: none;
  position: fixed;
  inset: 0;
  z-index: 40;
  background:
    radial-gradient(ellipse 90% 80% at 50% 50%, transparent 42%, rgba(0,0,0,0.55) 100%),
    repeating-linear-gradient(0deg, transparent, transparent 3px, rgba(0,0,0,0.035) 4px);
}}
.hud {{
  position: relative;
  z-index: 2;
  min-height: 100%;
  display: flex;
  flex-direction: column;
  padding: 0.85rem 1rem 1rem;
}}
.corners {{
  pointer-events: none;
  position: fixed;
  inset: 10px;
  z-index: 50;
  border: 1px solid rgba(92,239,255,0.1);
}}
.corners i {{
  position: absolute;
  width: 22px;
  height: 22px;
  border-color: var(--cyan);
  border-style: solid;
  filter: drop-shadow(0 0 6px var(--cyan));
}}
.corners .tl {{ left: 0; top: 0; border-width: 2px 0 0 2px; }}
.corners .tr {{ right: 0; top: 0; border-width: 2px 2px 0 0; }}
.corners .bl {{ left: 0; bottom: 0; border-width: 0 0 2px 2px; }}
.corners .br {{ right: 0; bottom: 0; border-width: 0 2px 2px 0; }}
.topbar {{
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem 1.25rem;
  margin-bottom: 0.85rem;
  padding: 0.35rem 0.25rem 0.75rem;
  border-bottom: 1px solid rgba(92,239,255,0.16);
}}
.brand-block {{ flex: 1; min-width: 12rem; }}
.eyebrow {{
  margin: 0;
  font-family: Rajdhani, system-ui, sans-serif;
  font-size: 0.68rem;
  font-weight: 600;
  letter-spacing: 0.3em;
  text-transform: uppercase;
  color: var(--cyan);
  text-shadow: 0 0 10px rgba(92,239,255,0.5);
}}
.brand {{
  margin: 0.1rem 0 0;
  font-family: Rajdhani, system-ui, sans-serif;
  font-size: clamp(1.5rem, 3.2vw, 2rem);
  font-weight: 700;
  letter-spacing: 0.32em;
  color: var(--cyan);
  text-shadow: 0 0 22px rgba(92,239,255,0.7);
}}
.subtitle {{
  margin: 0.35rem 0 0;
  font-family: Rajdhani, system-ui, sans-serif;
  font-size: 0.95rem;
  letter-spacing: 0.12em;
  color: var(--text);
  opacity: 0.9;
}}
.meta {{
  text-align: right;
  color: var(--muted);
  font-size: 0.8rem;
  letter-spacing: 0.04em;
  max-width: 22rem;
}}
.status-pills {{
  display: flex;
  gap: 0.75rem;
  align-items: center;
  font-family: Rajdhani, system-ui, sans-serif;
  font-size: 0.7rem;
  letter-spacing: 0.18em;
  color: var(--muted);
}}
.status-pills b {{
  display: inline-block;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--cyan);
  box-shadow: 0 0 8px var(--cyan);
  margin-right: 0.35rem;
}}
.layout {{
  flex: 1;
  display: grid;
  grid-template-columns: 1.2fr 1fr;
  gap: 0.9rem;
  min-height: 0;
}}
@media (max-width: 900px) {{
  .layout {{ grid-template-columns: 1fr; }}
  .meta {{ text-align: left; max-width: none; }}
}}
.holo {{
  position: relative;
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: linear-gradient(160deg, rgba(20,60,90,0.24), rgba(0,10,24,0.18));
  border: 1px solid rgba(92,239,255,0.28);
  backdrop-filter: blur(10px);
  box-shadow: 0 0 28px rgba(40,180,255,0.1), inset 0 0 40px rgba(40,180,255,0.04);
}}
.holo::before, .holo::after {{
  content: "";
  position: absolute;
  width: 12px;
  height: 12px;
  border-color: var(--cyan);
  border-style: solid;
  opacity: 0.9;
  pointer-events: none;
  z-index: 2;
}}
.holo::before {{ top: -1px; left: -1px; border-width: 2px 0 0 2px; }}
.holo::after {{ right: -1px; bottom: -1px; border-width: 0 2px 2px 0; }}
.holo-h {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0.85rem;
  border-bottom: 1px solid rgba(92,239,255,0.16);
  font-family: Rajdhani, system-ui, sans-serif;
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.28em;
  text-transform: uppercase;
  color: var(--cyan);
  text-shadow: 0 0 10px rgba(92,239,255,0.35);
}}
#map {{
  flex: 1;
  min-height: 420px;
  background: #04101c;
}}
#list {{
  flex: 1;
  overflow: auto;
  padding: 0.35rem 0.7rem 0.8rem;
  max-height: calc(100vh - 170px);
}}
.holo-card {{
  display: flex;
  gap: 0.65rem;
  padding: 0.7rem 0.15rem;
  border-bottom: 1px solid rgba(92,239,255,0.12);
}}
.idx {{
  font-family: Rajdhani, system-ui, sans-serif;
  font-size: 0.78rem;
  color: rgba(92,239,255,0.45);
  padding-top: 0.12rem;
}}
a {{
  color: var(--cyan);
  text-decoration: none;
  font-weight: 600;
  letter-spacing: 0.01em;
  text-shadow: 0 0 8px rgba(92,239,255,0.2);
}}
a:hover {{ text-decoration: underline; filter: drop-shadow(0 0 6px var(--cyan)); }}
.summary {{
  color: var(--muted);
  font-size: 0.86rem;
  margin: 0.28rem 0 0;
  line-height: 1.35;
}}
.empty {{ color: var(--muted); padding: 1rem 0.25rem; }}
.foot {{
  margin-top: 0.85rem;
  text-align: center;
  font-family: Rajdhani, system-ui, sans-serif;
  font-size: 0.65rem;
  letter-spacing: 0.5em;
  color: rgba(92,239,255,0.4);
  text-shadow: 0 0 10px rgba(92,239,255,0.25);
}}
.leaflet-container {{ background: #04101c; font-family: inherit; }}
.leaflet-tile-pane {{
  filter: invert(1) hue-rotate(180deg) brightness(0.82) contrast(1.08) saturate(0.3);
}}
.leaflet-control-attribution {{
  background: rgba(0, 8, 16, 0.78) !important;
  color: var(--muted) !important;
}}
.leaflet-control-attribution a {{ color: var(--cyan) !important; }}
.leaflet-popup-content-wrapper {{
  background: rgba(4,16,28,0.94);
  color: var(--text);
  border: 1px solid rgba(92,239,255,0.35);
  border-radius: 2px;
  box-shadow: var(--glow);
}}
.leaflet-popup-tip {{ background: rgba(4,16,28,0.94); }}
</style>
</head>
<body>
<div class="corners" aria-hidden="true">
  <i class="tl"></i><i class="tr"></i><i class="bl"></i><i class="br"></i>
</div>
<div class="hud">
  <header class="topbar">
    <div class="brand-block">
      <p class="eyebrow">Friday OS · {label}</p>
      <p class="brand">F.R.I.D.A.Y.</p>
      <p class="subtitle">{safe_title}</p>
    </div>
    <div class="status-pills" title="Monitor local">
      <span><b></b>API</span>
      <span><b></b>GEO</span>
      <span><b></b>RSS</span>
    </div>
    <div class="meta">Actualizado: {safe_updated}<br>{safe_meta}</div>
  </header>
  <div class="layout">
    <section class="holo">
      <div class="holo-h"><span>Geo</span><span>Mapa</span></div>
      <div id="map"></div>
    </section>
    <section class="holo">
      <div class="holo-h"><span>Comms</span><span>{len(enriched):02d}</span></div>
      <div id="list">{body}</div>
    </section>
  </div>
  <footer class="foot">FRIDAY SYSTEMS</footer>
</div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const map = L.map('map', {{ zoomControl: true }}).setView([{center_lat}, {center_lon}], {int(map_zoom)});
L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
  maxZoom: 8,
  attribution: '&copy; OpenStreetMap'
}}).addTo(map);
{markers_block}
</script>
</body>
</html>
"""


def write_monitor_data(
    kind: str,
    headlines: list[dict[str, str]],
    *,
    profile: CountryProfile | None = None,
    title: str | None = None,
) -> Path:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    updated = datetime.now(timezone.utc).isoformat()
    country = profile.code if profile else "WW"
    path = _DATA_DIR / f"{kind}_{country}.json"
    payload = {
        "updated_at": updated,
        "kind": kind,
        "country": country,
        "headlines": headlines,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if country == "WW":
        (_DATA_DIR / f"{kind}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    if title is None:
        if profile and profile.code != "WW":
            label = "noticias" if kind == "world" else "financas"
            title = f"FRIDAY — {profile.name_pt} ({label})"
        else:
            title = "FRIDAY World Monitor" if kind == "world" else "FRIDAY Finance Monitor"

    map_center = profile.lat_lon if profile else (20.0, 0.0)
    map_zoom = profile.map_zoom if profile else 2
    meta = (
        f"pais {profile.name_pt} · fontes RSS · sem cotacoes inventadas"
        if profile and profile.code != "WW"
        else "mapa aproximado · fontes RSS · sem cotacoes inventadas"
    )
    snap = _MONITORS_DIR / f"{kind}_snapshot.html"
    snap.write_text(
        _render_snapshot(
            kind,
            title,
            headlines,
            updated,
            map_center=map_center,
            map_zoom=map_zoom,
            meta_note=meta,
        ),
        encoding="utf-8",
    )
    return snap


def open_monitor(kind: str, override_url: str = "") -> tuple[bool, str]:
    """Open external URL or local HTML snapshot. Returns (ok, message).

    When FRIDAY_NO_BROWSER=1 (agent-api), prepare the snapshot but do not
    call webbrowser — the UI opens /monitors/... instead.
    """
    headless = os.getenv("FRIDAY_NO_BROWSER", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )

    if override_url.strip():
        url = override_url.strip()
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https", "file"):
            return False, "URL do monitor invalida."
        if headless:
            return True, f"Monitor pronto ({url}) — abrir na interface."
        webbrowser.open(url)
        return True, f"A abrir o monitor ({url})."

    snap = (_MONITORS_DIR / f"{kind}_snapshot.html").resolve()
    if not snap.is_file():
        write_monitor_data(kind, [])
        snap = (_MONITORS_DIR / f"{kind}_snapshot.html").resolve()
    if not snap.is_file():
        return False, "Nao consegui abrir o monitor (ficheiro em falta)."
    if headless:
        return True, f"Monitor {kind} pronto — abrir na interface."
    webbrowser.open(snap.as_uri())
    return True, f"A abrir o monitor {kind}."


def summarize_headlines(headlines: list[dict[str, str]], label: str) -> str:
    if not headlines:
        return ""
    bullets = [f"- {h['title']}" for h in headlines[:8]]
    return f"{label}\n" + "\n".join(bullets)
