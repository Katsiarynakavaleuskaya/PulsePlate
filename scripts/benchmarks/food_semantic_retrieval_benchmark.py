#!/usr/bin/env python3
"""Benchmark for W4 semantic retrieval path.

RU: Бенчмарк для W4 semantic retrieval пути.
EN: Benchmark for W4 semantic retrieval path.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import logging
import os
from pathlib import Path
import sqlite3
import tempfile
import time
from typing import Any
from urllib.parse import quote_plus

DEFAULT_MAX_P95_MS = 50.0
SEMANTIC_FLAG_KEY = "FEATURE_FOOD_SEARCH_SEMANTIC_ENABLED"


@dataclass
class ScenarioResult:
    name: str
    endpoint: str
    semantic_enabled: bool
    samples_ms: list[float]

    @property
    def p50(self) -> float:
        return _percentile(self.samples_ms, 50)

    @property
    def p95(self) -> float:
        return _percentile(self.samples_ms, 95)

    @property
    def p99(self) -> float:
        return _percentile(self.samples_ms, 99)


def _percentile(values: list[float], percentile: int) -> float:
    if not 0 <= percentile <= 100:
        raise ValueError(f"percentile must be between 0 and 100 inclusive, got {percentile}")
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    sorted_values = sorted(values)
    index = (len(sorted_values) - 1) * (percentile / 100)
    lower = int(index)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = index - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def _extract_query_term(canonical_name: str | None) -> str:
    text = canonical_name or ""
    buffer: list[str] = []
    for char in text:
        if char.isalpha():
            buffer.append(char)
            continue
        if len(buffer) >= 3:
            return "".join(buffer).lower()
        buffer.clear()
    if len(buffer) >= 3:
        return "".join(buffer).lower()
    return "apple"


def _create_temp_food_db(src_db: Path, tmp_dir: Path) -> tuple[Path, str]:
    tmp_db = tmp_dir / "food.sqlite"
    tmp_db.write_bytes(src_db.read_bytes())

    with sqlite3.connect(tmp_db) as con:
        row = con.execute("SELECT canonical_name FROM foods ORDER BY id ASC LIMIT 1").fetchone()
        if row is None:
            raise RuntimeError("foods table is empty; cannot run semantic benchmark")
        query_term = _extract_query_term(str(row[0] or ""))

    return tmp_db, query_term


def _expect_non_empty_list(response: Any) -> None:
    payload = response.json()
    if not isinstance(payload, list) or len(payload) == 0:
        raise ValueError("expected non-empty list payload")


def _configure_semantic_flag(enabled: bool) -> None:
    os.environ[SEMANTIC_FLAG_KEY] = "true" if enabled else "false"

    from app.services import food_store

    # Reset cached semantic backend to ensure each scenario observes current flag state.
    food_store.reset_semantic_search_backend_adapter()


def _run_scenario(
    *,
    client: Any,
    name: str,
    endpoint: str,
    semantic_enabled: bool,
    warmup: int,
    iterations: int,
) -> ScenarioResult:
    _configure_semantic_flag(semantic_enabled)

    for _ in range(warmup):
        response = client.get(endpoint)
        if response.status_code != 200:
            raise RuntimeError(
                f"warmup status mismatch for {name}: expected=200 got={response.status_code}"
            )
        _expect_non_empty_list(response)

    samples_ms: list[float] = []
    for _ in range(iterations):
        start = time.perf_counter()
        response = client.get(endpoint)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        if response.status_code != 200:
            raise RuntimeError(
                f"status mismatch for {name}: expected=200 got={response.status_code}"
            )
        _expect_non_empty_list(response)
        samples_ms.append(elapsed_ms)

    return ScenarioResult(
        name=name,
        endpoint=endpoint,
        semantic_enabled=semantic_enabled,
        samples_ms=samples_ms,
    )


def _format_results(results: list[ScenarioResult]) -> str:
    lines = [
        "Scenario | Semantic flag | Endpoint | p50 (ms) | p95 (ms) | p99 (ms)",
        "--- | --- | --- | ---: | ---: | ---:",
    ]
    for result in results:
        lines.append(
            f"{result.name} | {result.semantic_enabled} | `{result.endpoint}` | "
            f"{result.p50:.2f} | {result.p95:.2f} | {result.p99:.2f}"
        )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="W4 semantic retrieval benchmark")
    parser.add_argument("--iterations", type=int, default=120)
    parser.add_argument("--warmup", type=int, default=20)
    parser.add_argument("--db-path", type=Path, default=Path("data/food.sqlite"))
    parser.add_argument("--max-p95-ms", type=float, default=DEFAULT_MAX_P95_MS)
    parser.add_argument("--output-json", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.iterations < 1:
        raise ValueError("iterations must be >= 1")
    if args.warmup < 0:
        raise ValueError("warmup must be >= 0")

    src_db = args.db_path
    if not src_db.exists():
        raise FileNotFoundError(f"food db not found: {src_db}")

    original_food_db_path = os.environ.get("FOOD_DB_PATH")
    original_semantic_flag = os.environ.get(SEMANTIC_FLAG_KEY)
    results: list[ScenarioResult] = []

    with tempfile.TemporaryDirectory(prefix="food-semantic-bench-") as tmp_dir_raw:
        tmp_db, query_term = _create_temp_food_db(src_db=src_db, tmp_dir=Path(tmp_dir_raw))
        os.environ["FOOD_DB_PATH"] = str(tmp_db)

        try:
            from fastapi.testclient import TestClient
            from app.main import app

            endpoint = f"/api/v1/foods?query={quote_plus(query_term)}&limit=20&offset=0"
            scenarios = [
                {"name": "legacy_flag_off", "semantic_enabled": False},
                {"name": "semantic_flag_on", "semantic_enabled": True},
                {"name": "rollback_flag_off", "semantic_enabled": False},
            ]

            logging.getLogger("httpx").setLevel(logging.WARNING)
            with TestClient(app, raise_server_exceptions=False) as client:
                for scenario in scenarios:
                    results.append(
                        _run_scenario(
                            client=client,
                            name=scenario["name"],
                            endpoint=endpoint,
                            semantic_enabled=scenario["semantic_enabled"],
                            warmup=args.warmup,
                            iterations=args.iterations,
                        )
                    )
        finally:
            if original_food_db_path is None:
                os.environ.pop("FOOD_DB_PATH", None)
            else:
                os.environ["FOOD_DB_PATH"] = original_food_db_path

            if original_semantic_flag is None:
                os.environ.pop(SEMANTIC_FLAG_KEY, None)
            else:
                os.environ[SEMANTIC_FLAG_KEY] = original_semantic_flag

    for result in results:
        if result.p95 > args.max_p95_ms:
            raise RuntimeError(
                f"p95 threshold exceeded for {result.name}: {result.p95:.2f}ms > {args.max_p95_ms:.2f}ms"
            )

    print(_format_results(results))

    if args.output_json is not None:
        payload = {
            "iterations": args.iterations,
            "warmup": args.warmup,
            "db_path": str(args.db_path),
            "max_p95_ms": args.max_p95_ms,
            "results": [
                {
                    "name": item.name,
                    "semantic_enabled": item.semantic_enabled,
                    "endpoint": item.endpoint,
                    "p50_ms": round(item.p50, 4),
                    "p95_ms": round(item.p95, 4),
                    "p99_ms": round(item.p99, 4),
                }
                for item in results
            ],
        }
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
