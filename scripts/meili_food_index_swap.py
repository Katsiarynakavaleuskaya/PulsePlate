#!/usr/bin/env python3
"""Offline Meilisearch foods index build / validate / warm / swap CLI.

Run from repository root (``PYTHONPATH`` = repo root). Uses env:
``MEILI_URL``, ``MEILI_KEY``, ``MEILI_FOODS_INDEX`` / ``MEILI_SWAP_PRIMARY_INDEX``,
``MEILI_SWAP_CANDIDATE_INDEX`` or ``MEILI_SWAP_CANDIDATE_UID``, optional batch/timeouts.

RU: Операторский CLI для zero-downtime смены индекса без публичного HTTP-роута.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any, TextIO


def _optional_load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    root = Path(__file__).resolve().parents[1]
    for name in (".env",):
        p = root / name
        if p.is_file():
            load_dotenv(p)
            return


def _int_env(key: str, default: int) -> int:
    raw = os.environ.get(key)
    if raw is None or str(raw).strip() == "":
        return default
    return int(str(raw).strip())


def _float_env(key: str, default: float) -> float:
    raw = os.environ.get(key)
    if raw is None or str(raw).strip() == "":
        return default
    return float(str(raw).strip())


def _meili_swap_config_from_env():
    from app.services.meili_swap_orchestration import MeiliSwapConfig

    base = (os.environ.get("MEILI_URL") or "").strip()
    if not base:
        raise SystemExit("MEILI_URL is required")

    primary = (
        os.environ.get("MEILI_SWAP_PRIMARY_INDEX") or os.environ.get("MEILI_FOODS_INDEX") or ""
    ).strip()
    candidate = (
        os.environ.get("MEILI_SWAP_CANDIDATE_INDEX")
        or os.environ.get("MEILI_SWAP_CANDIDATE_UID")
        or ""
    ).strip()
    if not primary:
        raise SystemExit("Set MEILI_FOODS_INDEX or MEILI_SWAP_PRIMARY_INDEX")
    if not candidate:
        raise SystemExit("Set MEILI_SWAP_CANDIDATE_INDEX or MEILI_SWAP_CANDIDATE_UID")

    api_key = os.environ.get("MEILI_KEY")
    if api_key is not None and str(api_key).strip() == "":
        api_key = None

    timeout = _float_env("MEILI_TIMEOUT_SECONDS", 30.0)
    return MeiliSwapConfig(
        base_url=base,
        primary_index=primary,
        candidate_index=candidate,
        api_key=api_key,
        timeout_seconds=timeout,
    )


def _iter_jsonl_documents(fp: TextIO) -> Iterable[Mapping[str, Any]]:
    for line in fp:
        line = line.strip()
        if not line:
            continue
        yield json.loads(line)


def _configure_verbose(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(level=level, format="%(levelname)s %(name)s: %(message)s")
    logging.getLogger("meili_food_index_swap").setLevel(level)
    logging.getLogger("app.services.meili_swap_orchestration").setLevel(level)


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Meilisearch foods index swap orchestration CLI")
    p.add_argument(
        "--verbose",
        action="store_true",
        help="Enable DEBUG logs for this CLI and app.services.meili_swap_orchestration",
    )
    sub = p.add_subparsers(dest="command", required=True)

    def add_docs_arg(sp: argparse.ArgumentParser) -> None:
        sp.add_argument(
            "--documents",
            required=True,
            help="Path to JSONL document stream (one JSON object per line)",
        )

    sp_build = sub.add_parser("build", help="Recreate candidate index and bulk-load documents")
    add_docs_arg(sp_build)
    sp_build.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help="Override MEILI_SWAP_BATCH_SIZE (default 500)",
    )
    sp_build.add_argument(
        "--no-recreate",
        action="store_true",
        help="Do not delete/recreate candidate index before load",
    )

    sub.add_parser("validate", help="Read candidate index stats (numberOfDocuments)")

    sp_warm = sub.add_parser("warm", help="Run warm-up searches against candidate")
    sp_warm.add_argument(
        "--queries",
        default="",
        help='Comma-separated queries (default: "",a,rice)',
    )

    sub.add_parser("swap", help="POST /swap-indexes for primary/candidate pair")

    sp_pipe = sub.add_parser("pipeline", help="build → validate → warm → swap")
    add_docs_arg(sp_pipe)
    sp_pipe.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help="Override MEILI_SWAP_BATCH_SIZE (default 500)",
    )
    sp_pipe.add_argument(
        "--no-recreate",
        action="store_true",
        help="Do not delete/recreate candidate index before load",
    )
    sp_pipe.add_argument(
        "--skip-swap",
        action="store_true",
        help="Stop after warm (no swap-indexes)",
    )
    sp_pipe.add_argument(
        "--allow-empty-swap",
        action="store_true",
        help="Allow pipeline with empty document set (advanced recovery; still swaps if not skipped)",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    _configure_verbose(bool(args.verbose))
    _optional_load_dotenv()

    from app.services.meili_swap_orchestration import MeiliSwapOrchestrator

    cfg = _meili_swap_config_from_env()
    batch_size = _int_env("MEILI_SWAP_BATCH_SIZE", 500)
    if getattr(args, "batch_size", None) is not None:
        batch_size = int(args.batch_size)

    with MeiliSwapOrchestrator(cfg) as orch:
        if args.command == "build":
            path = Path(args.documents)
            with path.open(encoding="utf-8") as fp:
                docs = list(_iter_jsonl_documents(fp))
            n = orch.orchestrate_build(
                docs,
                batch_size=batch_size,
                recreate_candidate=not args.no_recreate,
            )
            print(f"indexed={n}")
            return 0

        if args.command == "validate":
            n = orch.orchestrate_validate(expected_documents=None)
            print(f"numberOfDocuments={n}")
            return 0

        if args.command == "warm":
            queries: tuple[str, ...]
            if args.queries.strip():
                queries = tuple(q.strip() for q in args.queries.split(",") if q.strip())
            else:
                queries = ("", "a", "rice")
            orch.orchestrate_warm(queries=queries)
            print("warm_ok=1")
            return 0

        if args.command == "swap":
            orch.perform_index_swap()
            print("swap_ok=1")
            return 0

        if args.command == "pipeline":
            path = Path(args.documents)
            with path.open(encoding="utf-8") as fp:
                docs = list(_iter_jsonl_documents(fp))
            orch.run_full_pipeline(
                docs,
                batch_size=batch_size,
                recreate_candidate=not args.no_recreate,
                skip_swap=bool(args.skip_swap),
                allow_empty_swap=bool(args.allow_empty_swap),
            )
            print("pipeline_ok=1")
            return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
