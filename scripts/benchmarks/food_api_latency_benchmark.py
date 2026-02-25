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
import sqlite3
import tempfile
import time
from typing import Any, Callable
from urllib.parse import quote_plus

DEFAULT_BENCH_BARCODE = "0123456789012"
DEFAULT_MISS_BARCODE = "9999999999999"
ResponseValidator = Callable[[Any], None]


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


def _create_temp_food_db(src_db: Path, injected_barcode: str, tmp_dir: Path) -> tuple[Path, str]:
    """Create temporary benchmark DB and inject one deterministic barcode hit row."""
    tmp_db = tmp_dir / "food.sqlite"
    tmp_db.write_bytes(src_db.read_bytes())

    with sqlite3.connect(tmp_db) as con:
        row = con.execute("SELECT id, canonical_name FROM foods ORDER BY id ASC LIMIT 1").fetchone()
        if row is None:
            raise RuntimeError("foods table is empty; cannot run benchmark")
        row_id = row[0]
        canonical_name = str(row[1] or "")
        con.execute("UPDATE foods SET gtin = ? WHERE id = ?", (injected_barcode, row_id))
        con.commit()

    query_term = _extract_query_term(canonical_name)
    return tmp_db, query_term


def _extract_query_term(canonical_name: str | None) -> str:
    """Pick the first alpha token (unicode-aware) with length >= 3."""
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


def _expect_non_empty_list(response: Any) -> None:
    payload = response.json()
    if not isinstance(payload, list) or len(payload) == 0:
        raise ValueError("expected non-empty list payload")


def _expect_empty_list(response: Any) -> None:
    payload = response.json()
    if not isinstance(payload, list) or len(payload) != 0:
        raise ValueError("expected empty list payload")


def _expect_detail_contains(expected_fragment: str) -> ResponseValidator:
    def _validator(response: Any) -> None:
        payload = response.json()
        detail = payload.get("detail") if isinstance(payload, dict) else None
        if not isinstance(detail, str) or expected_fragment not in detail:
            raise ValueError(f"expected error detail containing '{expected_fragment}'")

    return _validator


def _validate_response(
    *, name: str, phase: str, response: Any, validator: ResponseValidator | None
) -> None:
    if validator is None:
        return
    try:
        validator(response)
    except Exception as exc:  # pragma: no cover - defensive error wrapping
        raise RuntimeError(f"{phase} validation failed for {name}: {exc}") from exc


def _run_scenario(
    *,
    client: Any,
    name: str,
    endpoint: str,
    expected_status: int,
    validator: ResponseValidator | None,
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
        _validate_response(name=name, phase="warmup", response=response, validator=validator)

    samples_ms: list[float] = []
    for _ in range(iterations):
        start = time.perf_counter()
        response = client.get(endpoint)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        if response.status_code != expected_status:
            raise RuntimeError(
                f"status mismatch for {name}: expected={expected_status} got={response.status_code}"
            )
        _validate_response(name=name, phase="measure", response=response, validator=validator)
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
    parser.add_argument("--db-path", type=Path, default=Path("data/food.sqlite"))
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

    src_db = args.db_path
    if not src_db.exists():
        raise FileNotFoundError(f"food db not found: {src_db}")

    original_food_db_path = os.environ.get("FOOD_DB_PATH")
    results: list[ScenarioResult] = []

    with tempfile.TemporaryDirectory(prefix="food-bench-") as tmp_dir_raw:
        tmp_db, query_term = _create_temp_food_db(
            src_db=src_db,
            injected_barcode=args.bench_barcode,
            tmp_dir=Path(tmp_dir_raw),
        )
        os.environ["FOOD_DB_PATH"] = str(tmp_db)

        try:
            from fastapi.testclient import TestClient
            from app.main import app

            scenarios = [
                {
                    "name": "foods_list_hit",
                    "endpoint": f"/api/v1/foods?query={quote_plus(query_term)}&limit=20&offset=0",
                    "expected_status": 200,
                    "validator": _expect_non_empty_list,
                },
                {
                    "name": "foods_search_alias_hit",
                    "endpoint": (
                        f"/api/v1/foods/search?query={quote_plus(query_term)}&limit=20&offset=0"
                    ),
                    "expected_status": 200,
                    "validator": _expect_non_empty_list,
                },
                {
                    "name": "foods_list_no_results",
                    "endpoint": "/api/v1/foods?query=zzzzzzzzzz&limit=20&offset=0",
                    "expected_status": 200,
                    "validator": _expect_empty_list,
                },
                {
                    "name": "barcode_miss",
                    "endpoint": f"/api/v1/foods/barcode/{args.miss_barcode}",
                    "expected_status": 404,
                    "validator": _expect_detail_contains("Food not found"),
                },
                {
                    "name": "barcode_malformed",
                    "endpoint": "/api/v1/foods/barcode/abc",
                    "expected_status": 422,
                    "validator": _expect_detail_contains("at least one digit"),
                },
            ]
            if args.include_barcode_hit:
                scenarios.insert(
                    3,
                    {
                        "name": "barcode_hit",
                        "endpoint": f"/api/v1/foods/barcode/{args.bench_barcode}",
                        "expected_status": 200,
                        "validator": None,
                    },
                )

            logging.getLogger("httpx").setLevel(logging.WARNING)
            with TestClient(app, raise_server_exceptions=False) as client:
                for scenario in scenarios:
                    results.append(
                        _run_scenario(
                            client=client,
                            name=scenario["name"],
                            endpoint=scenario["endpoint"],
                            expected_status=scenario["expected_status"],
                            validator=scenario["validator"],
                            warmup=args.warmup,
                            iterations=args.iterations,
                        )
                    )
        finally:
            if original_food_db_path is None:
                os.environ.pop("FOOD_DB_PATH", None)
            else:
                os.environ["FOOD_DB_PATH"] = original_food_db_path

    print(_format_results(results))

    if args.output_json is not None:
        payload = {
            "iterations": args.iterations,
            "warmup": args.warmup,
            "db_path": str(args.db_path),
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
