"""Plan incremental CPT days: cumulative docs + rising max_steps."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from friday_llm.training.common import find_latest_checkpoint, read_trainer_state
from friday_llm.util import content_hash, estimate_tokens, read_jsonl, resolve_path, write_jsonl

logger = logging.getLogger(__name__)

SOURCE_DEFAULT = "friday-llm/data/pretraining/cpt_fase1.jsonl"
CUMULATIVE_DEFAULT = "friday-llm/data/pretraining/incremental/corpus_cumulative.jsonl"
MANIFEST_DEFAULT = "friday-llm/data/pretraining/incremental/day_manifest.jsonl"
USED_HASHES_DEFAULT = "friday-llm/data/pretraining/incremental/used_hashes.json"
OUTPUT_DIR_DEFAULT = "friday-llm/checkpoints/cpt-incremental"
PROGRESS_JSON = "friday-llm/reports/incremental/progress.json"
PROGRESS_MD = "friday-llm/reports/incremental/progress.md"
CONFIG_DIR = "friday-llm/configs/incremental"


def steps_for_new_docs(n_new: int, *, steps_per_doc: int = 4, min_steps: int = 20) -> int:
    """Optimizer steps budget for a new batch — sized by docs, not by wall clock."""
    if n_new <= 0:
        return 0
    return max(min_steps, int(n_new) * int(steps_per_doc))


def _row_hash(row: dict[str, Any]) -> str:
    if row.get("content_hash"):
        return str(row["content_hash"])
    return content_hash(str(row.get("text") or ""))


def _load_used_hashes(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    return set(data.get("hashes") or [])


def _save_used_hashes(path: Path, hashes: set[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"hashes": sorted(hashes), "count": len(hashes)}, indent=2),
        encoding="utf-8",
    )


def _current_global_step(output_dir: Path) -> int:
    ckpt = find_latest_checkpoint(output_dir)
    if not ckpt:
        return 0
    state = read_trainer_state(Path(ckpt))
    return int(state.get("global_step") or 0)


def _progress_bar(done: int, total: int, width: int = 24) -> str:
    if total <= 0:
        return "[" + ("-" * width) + "]"
    filled = int(width * min(done, total) / total)
    if done > 0 and filled == 0:
        filled = 1
    return "[" + ("#" * filled) + ("-" * (width - filled)) + "]"


class IncrementalState:
    def __init__(
        self,
        *,
        source: str = SOURCE_DEFAULT,
        cumulative: str = CUMULATIVE_DEFAULT,
        manifest: str = MANIFEST_DEFAULT,
        used_hashes: str = USED_HASHES_DEFAULT,
        output_dir: str = OUTPUT_DIR_DEFAULT,
        pool_total: int | None = None,
        config_dir: str = CONFIG_DIR,
        progress_json: str = PROGRESS_JSON,
        progress_md: str = PROGRESS_MD,
        data_file_rel: str = "friday-llm/data/pretraining/incremental/corpus_cumulative.jsonl",
        output_dir_rel: str = "friday-llm/checkpoints/cpt-incremental",
    ) -> None:
        self.source = resolve_path(source)
        self.cumulative = resolve_path(cumulative)
        self.manifest = resolve_path(manifest)
        self.used_hashes_path = resolve_path(used_hashes)
        self.output_dir = resolve_path(output_dir)
        self.pool_total = pool_total
        self.config_dir = resolve_path(config_dir)
        self.progress_json = resolve_path(progress_json)
        self.progress_md = resolve_path(progress_md)
        self.data_file_rel = data_file_rel
        self.output_dir_rel = output_dir_rel


DOMAIN_KEYWORDS = (
    "friday",
    "assistant",
    "llm",
    "local",
    "rag",
    "python",
    "windows",
    "docker",
    "whisper",
    "piper",
    "chroma",
    "qwen",
    "lora",
    "fine-tun",
    "mcp",
    "agent",
    "privacy",
    "self-host",
    "vlan",
    "home assistant",
)


def _domain_score(text: str) -> int:
    lowered = text.casefold()
    return sum(1 for kw in DOMAIN_KEYWORDS if kw in lowered)


def prepare_day(
    day: int,
    add: int,
    *,
    state: IncrementalState | None = None,
    steps_per_doc: int = 4,
    min_steps: int = 20,
    use_smoke_model: bool = False,
    write_script: bool = True,
    prefer_domain: bool = False,
    domain_source: str = "friday-llm/data/pretraining/incremental/domain_docs.jsonl",
) -> dict[str, Any]:
    """
    Add `add` unused docs to the cumulative corpus and emit day config + progress.

    Returns a summary dict with paths and training command hints.
    """
    if day < 1:
        raise ValueError("day must be >= 1")
    if add < 1:
        raise ValueError("add must be >= 1")

    st = state or IncrementalState()
    source_rows = read_jsonl(st.source)
    if not source_rows:
        raise FileNotFoundError(f"No source corpus at {st.source}")

    used = _load_used_hashes(st.used_hashes_path)
    available = [r for r in source_rows if _row_hash(r) not in used]

    domain_rows: list[dict[str, Any]] = []
    domain_path = resolve_path(domain_source)
    if prefer_domain and domain_path.is_file():
        domain_rows = [
            r for r in read_jsonl(domain_path) if _row_hash(r) not in used
        ]

    if prefer_domain:
        # Domain corpus first, then FineWeb scored by domain keywords
        scored_pool = sorted(
            available,
            key=lambda r: _domain_score(str(r.get("text") or "")),
            reverse=True,
        )
        merged: list[dict[str, Any]] = []
        seen_h: set[str] = set()
        for r in domain_rows + scored_pool:
            h = _row_hash(r)
            if h in seen_h:
                continue
            seen_h.add(h)
            merged.append(r)
        available = merged

    if len(available) < add:
        raise ValueError(
            f"Only {len(available)} unused docs left in pool "
            f"(requested {add}, pool={len(source_rows)}, used={len(used)})"
        )

    new_rows = available[:add]
    new_hashes = [_row_hash(r) for r in new_rows]
    for h in new_hashes:
        used.add(h)

    cumulative_rows = read_jsonl(st.cumulative)
    cumulative_rows.extend(new_rows)
    write_jsonl(st.cumulative, cumulative_rows)
    _save_used_hashes(st.used_hashes_path, used)

    manifest_rows = read_jsonl(st.manifest)
    manifest_rows.append(
        {
            "day": day,
            "added": add,
            "hashes": new_hashes,
            "cumulative_docs": len(cumulative_rows),
            "at": datetime.now(timezone.utc).isoformat(),
        }
    )
    write_jsonl(st.manifest, manifest_rows)

    already = _current_global_step(st.output_dir)
    planned_prev = 0
    if st.progress_json.is_file():
        try:
            planned_prev = int(
                json.loads(st.progress_json.read_text(encoding="utf-8")).get("max_steps") or 0
            )
        except (json.JSONDecodeError, OSError, TypeError, ValueError):
            planned_prev = 0
    # Resume from trainer step when available; otherwise keep prior planned ceiling
    # so preparing day N+1 before day N finishes still raises max_steps.
    base = max(already, planned_prev)
    delta = steps_for_new_docs(add, steps_per_doc=steps_per_doc, min_steps=min_steps)
    max_steps = base + delta

    tokens_est = sum(estimate_tokens(str(r.get("text") or "")) for r in cumulative_rows)
    pool_total = st.pool_total or len(source_rows)

    cfg = {
        "run_id": f"cpt-incremental-day-{day}",
        "seed": 42,
        "phase": "incremental",
        "day": day,
        "model_config": "friday-llm/configs/base_model.yaml",
        "use_smoke_model": use_smoke_model,
        "data_file": st.data_file_rel,
        "output_dir": st.output_dir_rel,
        "report_path": f"friday-llm/reports/incremental/cpt_day_{day}.json",
        "require_approval": False,
        "checkpoint_metrics_path": "friday-llm/reports/incremental/checkpoint_metrics.jsonl",
        "max_steps": max_steps,
        "seq_length": 1024,
        "per_device_train_batch_size": 1,
        "gradient_accumulation_steps": 8,
        "learning_rate": 2.0e-5,
        "warmup_steps": max(1, min(10, delta // 4)),
        "logging_steps": max(1, min(10, delta // 4)),
        "save_steps": max(5, min(50, delta)),
        "eval_steps": max(5, min(50, delta)),
        "save_total_limit": 3,
        "resume_from_checkpoint": True,
        "load_best_model_at_end": True,
        "metric_for_best_model": "eval_loss",
        "greater_is_better": False,
        "fp16": False,
        "bf16": False,
        "optim": "paged_adamw_8bit",
        "gradient_checkpointing": True,
        "report_to": "none",
        "notes": (
            f"Incremental day {day}: +{add} docs "
            f"(cumulative={len(cumulative_rows)}"
            f"{', prefer_domain' if prefer_domain else ''}"
            f"). Steps {base}->{max_steps}."
        ),
    }

    config_dir = st.config_dir
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / f"cpt_day_{day}.yaml"
    _write_yaml(config_path, cfg)

    script_path = None
    if write_script:
        script_path = resolve_path(f"scripts/cpt_day_{day}.ps1")
        script_path.parent.mkdir(parents=True, exist_ok=True)
        script_path.write_text(_ps1_script(day), encoding="utf-8")

    progress = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "day": day,
        "docs_in_pool": pool_total,
        "docs_used": len(used),
        "docs_remaining": pool_total - len(used),
        "cumulative_docs": len(cumulative_rows),
        "tokens_est": tokens_est,
        "added_this_day": add,
        "global_step_before": already,
        "planned_base": base,
        "max_steps": max_steps,
        "steps_delta": delta,
        "output_dir": str(st.output_dir),
        "config_path": str(config_path),
        "script_path": str(script_path) if script_path else None,
        "use_smoke_model": use_smoke_model,
        "bar": _progress_bar(len(used), pool_total),
    }
    _write_progress(progress, json_path=st.progress_json, md_path=st.progress_md)

    logger.info(
        "Day %s prepared: +%s docs → cumulative %s, max_steps %s→%s",
        day,
        add,
        len(cumulative_rows),
        base,
        max_steps,
    )
    return progress


def read_progress() -> dict[str, Any]:
    path = resolve_path(PROGRESS_JSON)
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_progress(
    progress: dict[str, Any],
    *,
    json_path: Path | None = None,
    md_path: Path | None = None,
) -> None:
    json_path = json_path or resolve_path(PROGRESS_JSON)
    md_path = md_path or resolve_path(PROGRESS_MD)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(progress, ensure_ascii=False, indent=2), encoding="utf-8")

    used = progress.get("docs_used", 0)
    total = progress.get("docs_in_pool", 0) or 1
    pct = 100.0 * used / total
    lines = [
        "# CPT incremental — progresso",
        "",
        f"**Actualizado:** {progress.get('updated_at')}",
        "",
        "```",
        f"Pool  {progress.get('bar')}  {used}/{total} ({pct:.1f}%)",
        "```",
        "",
        "| Campo | Valor |",
        "|-------|-------|",
        f"| Dia | {progress.get('day')} |",
        f"| Docs adicionados neste dia | {progress.get('added_this_day')} |",
        f"| Corpus cumulativo | {progress.get('cumulative_docs')} |",
        f"| Tokens (est.) | {progress.get('tokens_est')} |",
        f"| Steps base -> max_steps | {progress.get('planned_base', progress.get('global_step_before'))} -> {progress.get('max_steps')} |",
        f"| Trainer global_step | {progress.get('global_step_before')} |",
        f"| Delta steps | {progress.get('steps_delta')} |",
        f"| Smoke 0.5B | {progress.get('use_smoke_model')} |",
        f"| Config | `{progress.get('config_path')}` |",
        f"| Script | `{progress.get('script_path')}` |",
        "",
        "Regra: treina os docs pedidos (corpus cumulativo). O tempo pode ser < 1h.",
        "",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")


def _write_yaml(path: Path, cfg: dict[str, Any]) -> None:
    import yaml

    path.write_text(
        yaml.safe_dump(cfg, allow_unicode=True, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )


def _ps1_script(day: int) -> str:
    cfg_arg = f"friday-llm/configs/incremental/cpt_day_{day}.yaml"
    return f"""# CPT incremental - Dia {day}
# Docs primeiro; duracao flexivel (pode ser menos de 1h).
$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))

$env:TRANSFORMERS_NO_TF = "1"
$env:USE_TF = "0"
$env:USE_TORCH = "1"
$env:PYTHONIOENCODING = "utf-8"

Write-Host "CPT incremental Dia {day} - config {cfg_arg}"
python -m friday_llm.training.continued_pretraining.smoke --config {cfg_arg}
if ($LASTEXITCODE -ne 0) {{ exit $LASTEXITCODE }}
Write-Host "Dia {day} concluido. Ver friday-llm/reports/incremental/progress.md"
"""
