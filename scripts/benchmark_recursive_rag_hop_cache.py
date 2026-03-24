#!/usr/bin/env python3
"""Bounded local benchmark artifact: C3 hop-level vector memo (recursive path).

RU: Локальное воспроизводимое доказательство без внешнего кэша и без новых API.
EN: Reproducible evidence for PR review — no Redis, no new endpoints, no response fields.

Run from repo root::

    python3 scripts/benchmark_recursive_rag_hop_cache.py

Exit code 0 prints JSON lines with counters and wall-clock for the patched harness only.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Tests set this before importing app; keep parity for imports that read env.
os.environ.setdefault("TESTING", "true")


def _ctx(query: str, chunks: list[Any], confidence: float = 0.7) -> Any:
    from core.rag.contracts import RAGContext

    return RAGContext(
        query=query,
        refined_queries=[query],
        chunks=chunks,
        confidence=confidence,
        hops=1,
        latency_ms=1,
    )


def _run_harness(*, optimization_enabled: bool) -> dict[str, Any]:
    import core.rag.recursive_retrieval as recursive
    import core.rag.vector_rag as vector_rag
    from core.rag.contracts import RAGChunk

    # Match tests/test_recursive_rag.py hop-cache scenario (three hops, revisit query).
    prev_hops = recursive.MAX_RAG_HOPS
    prev_ref = recursive.MAX_REFINEMENT_PASSES
    prev_ver = recursive.MAX_VERIFICATION_QUERIES
    prev_gain = recursive.MIN_CONFIDENCE_GAIN_PER_HOP
    prev_retrieve = vector_rag.retrieve_context_structured
    prev_refine = recursive._refine_query

    setattr(recursive, "MAX_RAG_HOPS", 3)
    setattr(recursive, "MAX_REFINEMENT_PASSES", 5)
    setattr(recursive, "MAX_VERIFICATION_QUERIES", 0)
    setattr(recursive, "MIN_CONFIDENCE_GAIN_PER_HOP", -1.0)

    calls = {"n": 0}

    def _fake_retrieve(query: str, **_: Any) -> Any:
        calls["n"] += 1
        return _ctx(
            query,
            [
                RAGChunk(
                    chunk_id=f"doc-{len(query)}",
                    file="doc.md",
                    content=f"fiber vegetables nutrition guidance token{len(query)}",
                    score=0.7,
                )
            ],
            confidence=0.7,
        )

    def _fake_refine(current: str, *_args: Any, **_kwargs: Any) -> str:
        if current == "first":
            return "second"
        if current == "second":
            return "first"
        return current

    setattr(vector_rag, "retrieve_context_structured", _fake_retrieve)
    setattr(recursive, "_refine_query", _fake_refine)

    t0 = time.perf_counter()
    try:
        result = recursive.retrieve_recursive_context_structured(
            "first",
            optimization_enabled=optimization_enabled,
        )
    finally:
        setattr(recursive, "MAX_RAG_HOPS", prev_hops)
        setattr(recursive, "MAX_REFINEMENT_PASSES", prev_ref)
        setattr(recursive, "MAX_VERIFICATION_QUERIES", prev_ver)
        setattr(recursive, "MIN_CONFIDENCE_GAIN_PER_HOP", prev_gain)
        setattr(vector_rag, "retrieve_context_structured", prev_retrieve)
        setattr(recursive, "_refine_query", prev_refine)

    elapsed_ms = int((time.perf_counter() - t0) * 1000)

    stats = result.optimization_stats
    out: dict[str, Any] = {
        "optimization_enabled": optimization_enabled,
        "elapsed_ms": elapsed_ms,
        "vector_retrieve_calls": calls["n"],
        "hop_vector_cache_hits": None,
        "hop_vector_retrieve_calls": None,
        "stop_reason": None,
        "chunks": len(result.chunks),
    }
    if stats is not None:
        out["hop_vector_cache_hits"] = stats.get("hop_vector_cache_hits")
        out["hop_vector_retrieve_calls"] = stats.get("hop_vector_retrieve_calls")
        out["stop_reason"] = str(stats.get("stop_reason"))
    return out


def _run_fail_safe() -> dict[str, Any]:
    from unittest.mock import patch

    import core.rag.recursive_retrieval as recursive
    import core.rag.vector_rag as vector_rag
    from core.rag.recursive_retrieval import retrieve_recursive_context_structured

    def _boom(*_: Any, **__: Any) -> Any:
        raise RuntimeError("benchmark boom")

    prev = vector_rag.retrieve_context_structured
    setattr(vector_rag, "retrieve_context_structured", _boom)
    try:
        # Silence exc_info logging from the intentional failure path (stderr noise).
        with patch.object(recursive.logger, "warning"):
            result = retrieve_recursive_context_structured("x", optimization_enabled=True)
        return {
            "scenario": "fail_safe",
            "chunks": len(result.chunks),
            "confidence": result.confidence,
            "optimization_stats_present": result.optimization_stats is not None,
        }
    finally:
        setattr(vector_rag, "retrieve_context_structured", prev)


def main() -> int:
    rows = [
        {"scenario": "flag_off_parity", **_run_harness(optimization_enabled=False)},
        {"scenario": "flag_on_memo", **_run_harness(optimization_enabled=True)},
    ]
    rows.append(_run_fail_safe())
    for row in rows:
        print(json.dumps(row, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
