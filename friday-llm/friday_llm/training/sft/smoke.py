"""QLoRA SFT smoke (wrapper)."""

from __future__ import annotations

import argparse
import json
import logging

from friday_llm.training.sft.run import run_sft

logger = logging.getLogger(__name__)


def run_smoke(config_path: str) -> dict:
    return run_sft(config_path, force_resume=False)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO)
    p = argparse.ArgumentParser()
    p.add_argument("--config", default="friday-llm/configs/sft_smoke.yaml")
    args = p.parse_args(argv)
    print(json.dumps(run_smoke(args.config), indent=2))


if __name__ == "__main__":
    main()
