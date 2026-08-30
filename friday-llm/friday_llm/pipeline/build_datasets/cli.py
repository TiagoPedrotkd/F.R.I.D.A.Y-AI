"""Build cleaned CPT / SFT / RAG datasets from pilot or Fase 1 config."""

from __future__ import annotations

import argparse
import json
import logging
import random
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from friday_llm.pipeline.build_datasets.rag_chunker import chunk_documents
from friday_llm.pipeline.build_datasets.sft_builder import build_sft_dataset, validate_sft_tools
from friday_llm.pipeline.cleaning.clean import CleanStats, clean_document
from friday_llm.pipeline.deduplication.dedupe import approx_dedupe, exact_dedupe
from friday_llm.pipeline.ingest.fineweb import (
    local_fixture_docs,
    stream_fineweb2_multilang,
    write_raw_batch,
)
from friday_llm.pipeline.ingest.repo_docs import ingest_repo_markdown, write_extracted_batch
from friday_llm.pipeline.quality.contamination import (
    build_forbidden_corpus,
    is_eval_contaminated,
)
from friday_llm.pipeline.registry.catalog import update_catalog_from_build
from friday_llm.util import content_hash, estimate_tokens, load_yaml, read_jsonl, resolve_path, write_jsonl

logger = logging.getLogger(__name__)


def _synthetic_cpt_seed(n: int = 40) -> list[dict]:
    """Offline seed so the pipeline works without HF access."""
    paragraphs_pt = [
        "A arquitectura de um assistente local separa conhecimento nos pesos, "
        "documentos recuperados por RAG e dados actuais obtidos por ferramentas.",
        "O portugues europeu prefere telemovel a celular e autocarro a onibus "
        "em muitos contextos do quotidiano em Portugal.",
        "Uma API OpenAI-compatible expoe chat completions em HTTP; o LM Studio "
        "oferece esse contrato em localhost para modelos GGUF.",
        "O pre-treino continuado melhora fluencia e vocabulario, mas nao substitui "
        "fontes exactas nem informacao em tempo real.",
        "Tool calling exige schemas reais: get_current_datetime, get_world_news, "
        "search_web e fetch_url sao exemplos no projecto F.R.I.D.A.Y.",
    ]
    paragraphs_en = [
        "Continued pretraining on curated web text can improve language modeling "
        "loss without teaching volatile facts as permanent knowledge.",
        "Quantized LoRA adapters allow supervised fine-tuning of 7B models on a "
        "consumer GPU with twelve gigabytes of VRAM.",
        "Retrieval-augmented generation should always cite sources and admit "
        "failure when no document was retrieved.",
        "Evaluation sets must never leak into training; otherwise reported gains "
        "are contaminated and unreliable.",
        "Exporting adapters to GGUF enables local inference inside LM Studio "
        "without replacing the production model identifier automatically.",
    ]
    docs = []
    for i in range(n):
        if i % 2 == 0:
            text = " ".join(paragraphs_pt[i % len(paragraphs_pt)] for _ in range(3))
            lang, variant = "por", "pt-PT"
        else:
            text = " ".join(paragraphs_en[i % len(paragraphs_en)] for _ in range(3))
            lang, variant = "eng", ""
        text = (text + " ") * 4
        docs.append(
            {
                "document_id": f"synth-{i:04d}",
                "text": text.strip(),
                "source": "synthetic_pilot_seed",
                "url": "",
                "crawl": "local-synth-v0",
                "captured_at": datetime.now(timezone.utc).isoformat(),
                "language": lang,
                "variant": variant,
                "license": "Apache-2.0",
            }
        )
    return docs


def _is_fase1_config(cfg: dict[str, Any]) -> bool:
    paths = cfg.get("paths") or {}
    return "extracted" in paths and "deduplicated" in paths


def _contamination_checker(
    forbidden_hashes: set[str],
    forbidden_shingles: list[set[str]],
):
    def _check(text: str) -> bool:
        return is_eval_contaminated(
            text,
            forbidden_hashes=forbidden_hashes,
            forbidden_shingles=forbidden_shingles,
        )

    return _check


def _language_mix_stats(docs: list[dict[str, Any]]) -> dict[str, Any]:
    langs = Counter(str(d.get("language") or "und") for d in docs)
    variants = Counter(str(d.get("variant") or "") for d in docs if d.get("variant"))
    return {"languages": dict(langs), "variants": dict(variants)}


def _verify_no_eval_in_corpus(
    cpt_rows: list[dict[str, Any]],
    sft_rows: list[dict[str, Any]],
    eval_path: Path,
) -> dict[str, Any]:
    forbidden_hashes, forbidden_shingles = build_forbidden_corpus(str(eval_path), None)
    leaks: list[str] = []
    for row in cpt_rows:
        text = str(row.get("text") or "")
        if is_eval_contaminated(
            text, forbidden_hashes=forbidden_hashes, forbidden_shingles=forbidden_shingles
        ):
            leaks.append(f"cpt:{content_hash(text)[:12]}")
    for row in sft_rows:
        for msg in row.get("messages") or []:
            content = str(msg.get("content") or "")
            if content and is_eval_contaminated(
                content,
                forbidden_hashes=forbidden_hashes,
                forbidden_shingles=forbidden_shingles,
            ):
                leaks.append(f"sft:{content_hash(content)[:12]}")
    return {"eval_leaks": leaks, "ok": len(leaks) == 0}


def _write_phase1_report(
    report: dict[str, Any],
    *,
    md_path: Path,
    json_path: Path,
) -> None:
    md_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Fase 1 — Relatório de Dados (FRIDAY LLM)",
        "",
        f"**Run:** `{report.get('run_id')}`  ",
        f"**Gerado:** {report.get('built_at')}",
        "",
        "## Orçamento",
        "",
        f"- Documentos CPT: **{report.get('cpt_docs')}** (máx. {report.get('max_documents')})",
        f"- Tokens CPT estimados: **{report.get('cpt_tokens_est')}** (máx. {report.get('max_cpt_tokens')})",
        "",
        "## Pipeline por estágio",
        "",
        f"| Estágio | Documentos |",
        f"|---------|------------|",
        f"| Raw (FineWeb) | {report.get('raw_docs')} |",
        f"| Cleaned | {report.get('cleaned_docs')} |",
        f"| Deduplicated | {report.get('deduped_docs')} |",
        f"| CPT final | {report.get('cpt_docs')} |",
        "",
        "### Filtros de limpeza",
        "",
        f"```json\n{json.dumps(report.get('clean_stats', {}), ensure_ascii=False, indent=2)}\n```",
        "",
        f"- Exact dedupe dropped: {report.get('exact_dedupe_dropped')}",
        f"- MinHash dedupe dropped: {report.get('approx_dedupe_dropped')}",
        "",
        "## Mix linguístico CPT",
        "",
        f"```json\n{json.dumps(report.get('language_mix', {}), ensure_ascii=False, indent=2)}\n```",
        "",
        "## Datasets",
        "",
        f"- CPT: `{report.get('cpt_path')}`",
        f"- SFT train: `{report.get('sft_train_path')}` ({report.get('sft_train')} exemplos)",
        f"- SFT holdout: `{report.get('sft_holdout_path')}` ({report.get('sft_holdout')})",
        f"- RAG chunks: `{report.get('rag_path')}` ({report.get('rag_chunks')} chunks)",
        f"- Eval (inalterado): `{report.get('eval_path')}`",
        "",
        "## Validação eval",
        "",
        f"- Sem leak: **{report.get('eval_validation', {}).get('ok')}**",
        "",
        "## Avisos",
        "",
        "- Este subset **não** representa conhecimento geral da web.",
        "- O conjunto de avaliação **nunca** entra em CPT/SFT.",
        "- `data/chroma/` e `data/news_cache/` estão excluídos.",
        "- Phi-4 em produção permanece inalterado nesta fase.",
        "",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def build_fase1_from_config(config_path: str, *, allow_network: bool = True) -> dict:
    cfg = load_yaml(config_path)
    paths = cfg["paths"]
    cleaning = cfg.get("cleaning") or {}
    dedupe_cfg = cfg.get("dedupe") or {}
    seed = int(cfg.get("seed") or 42)
    random.seed(seed)

    raw_dir = resolve_path(paths["raw"])
    extracted_dir = resolve_path(paths["extracted"])
    cleaned_dir = resolve_path(paths["cleaned"])
    dedup_dir = resolve_path(paths["deduplicated"])
    pretrain_dir = resolve_path(paths["pretraining"])
    sft_dir = resolve_path(paths["sft"])
    rag_dir = resolve_path(paths["rag"])
    eval_path = resolve_path(paths["evaluation"])
    registry_path = resolve_path(paths["registry"])

    for d in (raw_dir, extracted_dir, cleaned_dir, dedup_dir, pretrain_dir, sft_dir, rag_dir):
        d.mkdir(parents=True, exist_ok=True)

    max_documents = int(cfg.get("max_documents") or 500)
    max_cpt_tokens = int(cfg.get("max_cpt_tokens") or 2_000_000)

    # --- Ingest FineWeb ---
    docs: list[dict] = []
    source_note = "synthetic"
    if allow_network:
        fw = cfg.get("fineweb") or {}
        configs = fw.get("configs") or [
            {"name": "por_Latn", "language": "por", "max_samples": 350},
            {"name": "eng_Latn", "language": "eng", "max_samples": 150},
        ]
        try:
            docs = stream_fineweb2_multilang(
                configs,
                max_documents=max_documents,
                max_tokens=max_cpt_tokens,
            )
            source_note = "fineweb_stream"
            logger.info("Streamed %s FineWeb documents", len(docs))
        except Exception as exc:  # noqa: BLE001
            logger.warning("FineWeb stream failed (%s); using synthetic seed", exc)

    if not docs:
        fixture = raw_dir / "synthetic_seed.jsonl"
        docs = local_fixture_docs(fixture) or _synthetic_cpt_seed()
        write_raw_batch(docs, fixture)
        source_note = "synthetic"

    raw_out = raw_dir / f"fase1_raw_{source_note}.jsonl"
    write_jsonl(raw_out, docs)

    # --- Ingest repo docs (RAG source, extracted/) ---
    repo_cfg = cfg.get("repo_docs") or {}
    extracted_docs = list(
        ingest_repo_markdown(
            repo_cfg.get("globs") or ["docs/**/*.md"],
            license_name=str(repo_cfg.get("license") or "Apache-2.0"),
            language=str(repo_cfg.get("language") or "pt"),
            excluded_paths=cfg.get("excluded_paths"),
        )
    )
    extracted_path = extracted_dir / "repo_docs.jsonl"
    write_extracted_batch(extracted_docs, extracted_path)

    # --- Clean CPT docs ---
    sft_seed_path = resolve_path((cfg.get("sft") or {}).get("seed_file") or "friday-llm/data/sft/seed_sft.jsonl")
    holdout_seed = resolve_path(sft_dir / "seed_sft_holdout.jsonl")
    forbidden_hashes, forbidden_shingles = build_forbidden_corpus(
        str(eval_path),
        str(holdout_seed) if holdout_seed.is_file() else None,
    )
    checker = _contamination_checker(forbidden_hashes, forbidden_shingles)

    stats = CleanStats()
    cleaned: list[dict] = []
    for doc in docs:
        c = clean_document(
            doc,
            min_chars=int(cleaning.get("min_chars") or 200),
            max_chars=int(cleaning.get("max_chars") or 50_000),
            drop_pii=bool(cleaning.get("drop_pii", True)),
            check_quality=True,
            contamination_checker=checker,
            stats=stats,
        )
        if c:
            cleaned.append(c)

    cleaned_path = cleaned_dir / "fase1_cleaned.jsonl"
    write_jsonl(cleaned_path, cleaned)
    cleaned_pre_dedupe_count = len(cleaned)
    clean_stats_path = cleaned_dir / "clean_stats.json"
    clean_stats_path.write_text(
        json.dumps(stats.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # --- Dedupe ---
    if cleaning.get("exact_dedupe", True):
        cleaned, exact_dropped = exact_dedupe(cleaned)
    else:
        exact_dropped = 0
    cleaned, approx_dropped = approx_dedupe(
        cleaned,
        threshold=float(cleaning.get("minhash_threshold") or 0.85),
        method=str(dedupe_cfg.get("method") or "minhash"),
        num_perm=int(cleaning.get("minhash_perms") or 128),
        seed=seed,
    )

    dedup_path = dedup_dir / "cpt_deduped.jsonl"
    write_jsonl(dedup_path, cleaned)

    # --- CPT output with token budget ---
    cpt_rows = [
        {"text": d["text"], "metadata": {k: d[k] for k in d if k != "text"}}
        for d in cleaned
    ]
    token_total = 0
    capped: list[dict] = []
    for row in cpt_rows[:max_documents]:
        t = estimate_tokens(str(row.get("text") or ""))
        if token_total + t > max_cpt_tokens:
            break
        capped.append(row)
        token_total += t
    cpt_path = pretrain_dir / "cpt_fase1.jsonl"
    write_jsonl(cpt_path, capped)

    # --- SFT ---
    sft_seed_rows = read_jsonl(sft_seed_path)
    sft_cfg = cfg.get("sft") or {}
    train, holdout, sft_meta = build_sft_dataset(
        sft_seed_rows,
        expand_from_registry=bool(sft_cfg.get("expand_from_registry", True)),
        holdout_ratio=float(sft_cfg.get("holdout_ratio") or 0.15),
        seed=seed,
    )
    if sft_meta.get("invalid_tools"):
        logger.warning("SFT invalid tools: %s", sft_meta["invalid_tools"])
    sft_train_path = sft_dir / "fase1_sft_train.jsonl"
    sft_holdout_path = sft_dir / "fase1_sft_holdout.jsonl"
    write_jsonl(sft_train_path, train)
    write_jsonl(sft_holdout_path, holdout)

    # --- RAG chunks ---
    rag_cfg = cfg.get("rag") or {}
    rag_chunks = chunk_documents(
        extracted_docs,
        chunk_chars=int(rag_cfg.get("chunk_chars") or 2000),
        chunk_overlap=int(rag_cfg.get("chunk_overlap") or 200),
    )
    rag_path = rag_dir / "chunks.jsonl"
    write_jsonl(rag_path, rag_chunks)

    # --- Eval validation ---
    eval_validation = _verify_no_eval_in_corpus(capped, train + holdout, eval_path)

    # --- Catalog ---
    update_catalog_from_build(
        registry_path,
        cpt_path=cpt_path,
        sft_train_path=sft_train_path,
        sft_holdout_path=sft_holdout_path,
        rag_path=rag_path,
        eval_path=eval_path,
    )

    report: dict[str, Any] = {
        "run_id": cfg.get("run_id"),
        "built_at": datetime.now(timezone.utc).isoformat(),
        "source_note": source_note,
        "max_documents": max_documents,
        "max_cpt_tokens": max_cpt_tokens,
        "raw_path": str(raw_out),
        "extracted_path": str(extracted_path),
        "cleaned_path": str(cleaned_path),
        "dedup_path": str(dedup_path),
        "cpt_path": str(cpt_path),
        "sft_train_path": str(sft_train_path),
        "sft_holdout_path": str(sft_holdout_path),
        "rag_path": str(rag_path),
        "eval_path": str(eval_path),
        "raw_docs": len(docs),
        "extracted_docs": len(extracted_docs),
        "cleaned_docs": cleaned_pre_dedupe_count,
        "deduped_docs": len(cleaned),
        "cpt_docs": len(capped),
        "cpt_tokens_est": token_total,
        "rag_chunks": len(rag_chunks),
        "clean_stats": stats.to_dict(),
        "exact_dedupe_dropped": exact_dropped,
        "approx_dedupe_dropped": approx_dropped,
        "language_mix": _language_mix_stats(cleaned),
        "sft_train": len(train),
        "sft_holdout": len(holdout),
        "sft_meta": sft_meta,
        "eval_validation": eval_validation,
        "sft_tool_validation": validate_sft_tools(train + holdout),
        "content_hash_sample": content_hash(json.dumps(capped[:3], ensure_ascii=False)),
    }

    reports_dir = resolve_path("friday-llm/reports")
    _write_phase1_report(
        report,
        md_path=reports_dir / "phase1_data_report.md",
        json_path=reports_dir / "phase1_data_stats.json",
    )
    logger.info("Fase 1 report → %s", reports_dir / "phase1_data_report.md")
    return report


def build_pilot_from_config(config_path: str, *, allow_network: bool = True) -> dict:
    cfg = load_yaml(config_path)
    paths = cfg["paths"]
    cleaning = cfg.get("cleaning") or {}
    seed = int(cfg.get("seed") or 42)
    random.seed(seed)

    raw_dir = resolve_path(paths["raw"])
    cleaned_dir = resolve_path(paths["cleaned"])
    pretrain_dir = resolve_path(paths["pretraining"])
    sft_dir = resolve_path(paths["sft"])
    raw_dir.mkdir(parents=True, exist_ok=True)
    cleaned_dir.mkdir(parents=True, exist_ok=True)
    pretrain_dir.mkdir(parents=True, exist_ok=True)

    docs: list[dict] = []
    source_note = "synthetic"
    if allow_network:
        fw = cfg.get("fineweb") or {}
        try:
            from friday_llm.pipeline.ingest.fineweb import stream_fineweb2

            docs = list(
                stream_fineweb2(
                    max_samples=int(fw.get("max_samples") or 400),
                    language_hint=str(fw.get("language_hint") or "por"),
                )
            )
            source_note = "fineweb_stream"
            logger.info("Streamed %s FineWeb documents", len(docs))
        except Exception as exc:  # noqa: BLE001
            logger.warning("FineWeb stream failed (%s); using synthetic seed", exc)

    if not docs:
        fixture = raw_dir / "synthetic_seed.jsonl"
        docs = local_fixture_docs(fixture) or _synthetic_cpt_seed()
        write_raw_batch(docs, fixture)
        source_note = "synthetic"

    raw_out = raw_dir / f"pilot_raw_{source_note}.jsonl"
    write_jsonl(raw_out, docs)

    stats = CleanStats()
    cleaned = []
    for doc in docs:
        c = clean_document(
            doc,
            min_chars=int(cleaning.get("min_chars") or 200),
            max_chars=int(cleaning.get("max_chars") or 50_000),
            drop_pii=bool(cleaning.get("drop_pii", True)),
            stats=stats,
        )
        if c:
            cleaned.append(c)

    if cleaning.get("exact_dedupe", True):
        cleaned, exact_dropped = exact_dedupe(cleaned)
    else:
        exact_dropped = 0
    cleaned, approx_dropped = approx_dedupe(cleaned)

    cleaned_path = cleaned_dir / "pilot_cleaned.jsonl"
    write_jsonl(cleaned_path, cleaned)

    cpt_rows = [{"text": d["text"], "metadata": {k: d[k] for k in d if k != "text"}} for d in cleaned]
    max_docs = int(cfg.get("max_documents") or len(cpt_rows))
    cpt_rows = cpt_rows[:max_docs]
    cpt_path = pretrain_dir / "pilot_cpt.jsonl"
    write_jsonl(cpt_path, cpt_rows)

    sft_seed = resolve_path((cfg.get("sft") or {}).get("seed_file") or "friday-llm/data/sft/seed_sft.jsonl")
    sft_rows = read_jsonl(sft_seed)
    holdout_ratio = float((cfg.get("sft") or {}).get("holdout_ratio") or 0.15)
    random.shuffle(sft_rows)
    n_hold = max(1, int(len(sft_rows) * holdout_ratio)) if sft_rows else 0
    holdout = sft_rows[:n_hold]
    train = sft_rows[n_hold:] or sft_rows
    write_jsonl(sft_dir / "seed_sft_train.jsonl", train)
    write_jsonl(sft_dir / "seed_sft_holdout.jsonl", holdout)

    report = {
        "run_id": cfg.get("run_id"),
        "built_at": datetime.now(timezone.utc).isoformat(),
        "source_note": source_note,
        "raw_path": str(raw_out),
        "cleaned_path": str(cleaned_path),
        "cpt_path": str(cpt_path),
        "clean_stats": stats.to_dict(),
        "exact_dedupe_dropped": exact_dropped,
        "approx_dedupe_dropped": approx_dropped,
        "cpt_docs": len(cpt_rows),
        "sft_train": len(train),
        "sft_holdout": len(holdout),
        "content_hash_sample": content_hash(json.dumps(cpt_rows[:3], ensure_ascii=False)),
    }
    report_path = resolve_path("friday-llm/reports") / "pilot_build_stats.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Build report → %s", report_path)
    return report


def build_from_config(config_path: str, *, allow_network: bool = True) -> dict:
    cfg = load_yaml(config_path)
    if _is_fase1_config(cfg):
        return build_fase1_from_config(config_path, allow_network=allow_network)
    return build_pilot_from_config(config_path, allow_network=allow_network)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Build FRIDAY LLM datasets")
    parser.add_argument(
        "--config",
        default="friday-llm/configs/pilot.yaml",
        help="Pilot or Fase 1 YAML config",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Skip FineWeb network stream; use synthetic seed only",
    )
    args = parser.parse_args(argv)
    report = build_from_config(args.config, allow_network=not args.offline)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
