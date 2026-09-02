"""Export feedback hard-cases into SFT chat rows and eval items."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from friday.quality.feedback_report import _read_jsonl, build_feedback_report

_SYSTEM = (
    "Tu es a F.R.I.D.A.Y., assistente pessoal local. Portugues europeu; "
    "respostas curtas para voz; usa so tools reais; nao inventes factos."
)

_CORRECTION = (
    "A resposta anterior foi marcada como incorrecta pelo utilizador"
    "{comment}. Reformula com honestidade: se faltarem fontes, diz que nao "
    "confirmas; se for um pedido de ferramenta, chama a tool correcta."
)


def _down_rows(feedback_path: Path) -> list[dict[str, Any]]:
    return [r for r in _read_jsonl(feedback_path) if str(r.get("rating")) == "down"]


def hard_case_to_sft_row(row: dict[str, Any]) -> dict[str, Any] | None:
    user = str(row.get("user_text") or row.get("user") or "").strip()
    bad = str(row.get("reply_text") or row.get("assistant") or "").strip()
    if not user:
        return None
    comment = str(row.get("comment") or "").strip()
    comment_bit = f" ({comment})" if comment else ""
    # Preference-style repair: show bad answer then corrected refusal/honest reply
    assistant = (
        "Nao consigo confirmar isso com confianca a partir das fontes disponiveis. "
        "Queres que pesquise de novo ou reformule o pedido?"
    )
    return {
        "messages": [
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": user},
            {"role": "assistant", "content": bad or "(resposta vazia)"},
            {
                "role": "user",
                "content": _CORRECTION.format(comment=comment_bit),
            },
            {"role": "assistant", "content": assistant},
        ],
        "meta": {
            "source": "feedback_down",
            "session_id": row.get("session_id"),
            "grounding_score": row.get("grounding_score"),
            "ts": row.get("ts"),
        },
    }


def hard_case_to_eval_item(row: dict[str, Any], *, idx: int) -> dict[str, Any] | None:
    user = str(row.get("user_text") or row.get("user") or "").strip()
    if not user:
        return None
    return {
        "id": f"feedback_hard_{idx:04d}",
        "category": "feedback_hard",
        "language": "pt-PT",
        "input": user,
        "rubric": (
            "Nao inventar; preferir tools/pesquisa ou recusa honesta. "
            f"Comentario user: {str(row.get('comment') or '')[:120]}"
        ),
        "expect_tool": None,
        "source": "feedback_down",
    }


def export_feedback_datasets(
    feedback_path: str | Path = "data/feedback/feedback.jsonl",
    *,
    sft_out: str | Path = "friday-llm/data/sft/feedback_hard_sft.jsonl",
    eval_out: str | Path = "friday-llm/data/evaluation/feedback_hard_eval.jsonl",
    report_dir: str | Path = "data/feedback/reports",
) -> dict[str, Any]:
    fb = Path(feedback_path)
    report = build_feedback_report(fb, out_dir=report_dir)
    downs = _down_rows(fb)

    sft_rows: list[dict[str, Any]] = []
    eval_rows: list[dict[str, Any]] = []
    for i, row in enumerate(downs):
        sft = hard_case_to_sft_row(row)
        if sft:
            sft_rows.append(sft)
        ev = hard_case_to_eval_item(row, idx=i)
        if ev:
            eval_rows.append(ev)

    sft_path = Path(sft_out)
    eval_path = Path(eval_out)
    sft_path.parent.mkdir(parents=True, exist_ok=True)
    eval_path.parent.mkdir(parents=True, exist_ok=True)
    with sft_path.open("w", encoding="utf-8") as fh:
        for row in sft_rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    with eval_path.open("w", encoding="utf-8") as fh:
        for row in eval_rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    # Stable "latest" pointers
    latest_sft = sft_path.parent / "feedback_hard_sft_latest.jsonl"
    latest_eval = eval_path.parent / "feedback_hard_eval_latest.jsonl"
    latest_sft.write_text(sft_path.read_text(encoding="utf-8"), encoding="utf-8")
    latest_eval.write_text(eval_path.read_text(encoding="utf-8"), encoding="utf-8")

    out = {
        **report,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "sft_rows": len(sft_rows),
        "eval_rows": len(eval_rows),
        "sft_path": str(sft_path),
        "eval_path": str(eval_path),
        "sft_latest": str(latest_sft),
        "eval_latest": str(latest_eval),
    }
    pointer = Path(report_dir) / "feedback_datasets_latest.json"
    pointer.parent.mkdir(parents=True, exist_ok=True)
    pointer.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def main() -> None:
    import argparse

    p = argparse.ArgumentParser(description="Export feedback hard cases to SFT/eval")
    p.add_argument("--feedback", default="data/feedback/feedback.jsonl")
    p.add_argument("--sft-out", default="friday-llm/data/sft/feedback_hard_sft.jsonl")
    p.add_argument(
        "--eval-out", default="friday-llm/data/evaluation/feedback_hard_eval.jsonl"
    )
    p.add_argument("--report-dir", default="data/feedback/reports")
    args = p.parse_args()
    out = export_feedback_datasets(
        args.feedback,
        sft_out=args.sft_out,
        eval_out=args.eval_out,
        report_dir=args.report_dir,
    )
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
