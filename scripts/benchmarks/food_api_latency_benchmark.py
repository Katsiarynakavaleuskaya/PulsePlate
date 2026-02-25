#!/usr/bin/env python3
"""Latency benchmark for Wave 2-C food endpoints.

RU: Бенчмарк latency для food endpoint'ов Wave 2-C.
EN: Latency benchmark for Wave 2-C food endpoints.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import logging
import os
from pathlib import Path
import re
import shutil
import sqlite3
import tempfile
import time
from typing import Any

DEFAULT_BENCH_BARCODE = "0123456789012"
DEFAULT_MISS_BARCODE = "9999999999999"


@dataclass
class ScenarioResult:
    name: str
    endpoint: str
    expected_status: int
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
    """Return percentile value for already measured latencies."""
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


def _create_temp_food_db(src_db: Path, injected_barcode: str) -> tuple[Path, str]:
    """Create temporary benchmark DB and inject one deterministic barcode hit row."""
    tmp_dir = Path(tempfile.mkdtemp(prefix="food-bench-"))
    tmp_db = tmp_dir / "food.sqlite"
    shutil.copy2(src_db, tmp_db)

    with sqlite3.connect(tmp_db) as con:
        row = con.execute("SELECT id, canonical_name FROM foods ORDER BY id ASC LIMIT 1").fetchone()
        if row is None:
            raise RuntimeError("foods table is empty; cannot run benchmark")
        row_id = row[0]
        canonical_name = str(row[1] or "")
        con.execute("UPDATE foods SET gtin = ? WHERE id = ?", (injected_barcode, row_id))
        con.commit()

    token = canonical_name.split()[0] if canonical_name.strip() else ""
    query_term = re.sub(r"[^A-Za-z0-9]+", "", token).lower() or "apple"
    return tmp_db, query_term


def _run_scenario(
    *,
    client: Any,
    name: str,
    endpoint: str,
    expected_status: int,
    warmup: int,
    iterations: int,
) -> ScenarioResult:
    """Run warmup + measured requests for one endpoint scenario."""
    for _ in range(warmup):
        response = client.get(endpoint)
        if response.status_code != expected_status:
            raise RuntimeError(
                f"warmup status mismatch for {name}: expected={expected_status} got={response.status_code}"
            )

    samples_ms: list[float] = []
    for _ in range(iterations):
        start = time.perf_counter()
        response = client.get(endpoint)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        if response.status_code != expected_status:
            raise RuntimeError(
                f"status mismatch for {name}: expected={expected_status} got={response.status_code}"
            )
        samples_ms.append(elapsed_ms)

    return ScenarioResult(
        name=name,
        endpoint=endpoint,
        expected_status=expected_status,
        samples_ms=samples_ms,
    )


def _format_results(results: list[ScenarioResult]) -> str:
    lines = [
        "Scenario | Endpoint | Status | p50 (ms) | p95 (ms) | p99 (ms)",
        "--- | --- | ---: | ---: | ---: | ---:",
    ]
    for result in results:
        lines.append(
            f"{result.name} | `{result.endpoint}` | {result.expected_status} | "
            f"{result.p50:.2f} | {result.p95:.2f} | {result.p99:.2f}"
        )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Wave 2-C latency benchmark for food APIs")
    parser.add_argument("--iterations", type=int, default=150)
    parser.add_argument("--warmup", type=int, default=20)
    parser.add_argument("--bench-barcode", default=DEFAULT_BENCH_BARCODE)
    parser.add_argument("--miss-barcode", default=DEFAULT_MISS_BARCODE)
    parser.add_argument("--include-barcode-hit", action="store_true")
    parser.add_argument("--output-json", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.iterations < 1:
        raise ValueError("iterations must be >= 1")
    if args.warmup < 0:
        raise ValueError("warmup must be >= 0")

    src_db = Path("data/food.sqlite")
    if not src_db.exists():
        raise FileNotFoundError(f"food db not found: {src_db}")

    tmp_db, query_term = _create_temp_food_db(src_db=src_db, injected_barcode=args.bench_barcode)
    os.environ["FOOD_DB_PATH"] = str(tmp_db)

    from fastapi.testclient import TestClient
    from app.main import app

    scenarios = [
        {
            "name": "foods_list_hit",
            "endpoint": f"/api/v1/foods?query={query_term}&limit=20&offset=0",
            "expected_status": 200,
        },
        {
            "name": "foods_search_alias_hit",
            "endpoint": f"/api/v1/foods/search?query={query_term}&limit=20&offset=0",
            "expected_status": 200,
        },
        {
            "name": "foods_list_no_results",
            "endpoint": "/api/v1/foods?query=zzzzzzzzzz&limit=20&offset=0",
            "expected_status": 200,
        },
        {
            "name": "barcode_miss",
            "endpoint": f"/api/v1/foods/barcode/{args.miss_barcode}",
            "expected_status": 404,
        },
        {
            "name": "barcode_malformed",
            "endpoint": "/api/v1/foods/barcode/abc",
            "expected_status": 422,
        },
    ]
    if args.include_barcode_hit:
        scenarios.insert(
            3,
            {
                "name": "barcode_hit",
                "endpoint": f"/api/v1/foods/barcode/{args.bench_barcode}",
                "expected_status": 200,
            },
        )

    results: list[ScenarioResult] = []
    logging.getLogger("httpx").setLevel(logging.WARNING)
    with TestClient(app, raise_server_exceptions=False) as client:
        for scenario in scenarios:
            results.append(
                _run_scenario(
                    client=client,
                    name=scenario["name"],
                    endpoint=scenario["endpoint"],
                    expected_status=scenario["expected_status"],
                    warmup=args.warmup,
                    iterations=args.iterations,
                )
            )

    print(_format_results(results))

    if args.output_json is not None:
        payload = {
            "iterations": args.iterations,
            "warmup": args.warmup,
            "results": [
                {
                    "name": item.name,
                    "endpoint": item.endpoint,
                    "expected_status": item.expected_status,
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
