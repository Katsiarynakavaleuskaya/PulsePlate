#!/usr/bin/env python3
"""Canonical deterministic gate bundle for the product AI runtime rail.

RU: Узкий launcher для `PR-A5` runtime gates без новой eval-системы.
EN: Narrow launcher for `PR-A5` runtime gates without introducing a parallel eval framework.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence

AI_RUNTIME_GATE_TEST_NODES: tuple[str, ...] = (
    "tests/test_logic_philosophy_replay_eval.py",
    "tests/test_agent_run_summary_artifact.py",
    "tests/test_philosophy_validator.py",
    "tests/test_recursive_rag.py",
    "tests/test_rag_orchestration.py",
    "tests/test_vector_rag.py",
)


def build_pytest_args(extra_args: Sequence[str] | None = None) -> list[str]:
    """Build deterministic pytest args for the canonical AI runtime gate bundle."""

    pytest_args = ["-q", *AI_RUNTIME_GATE_TEST_NODES]
    if extra_args:
        pytest_args.extend(extra_args)
    return pytest_args


def run_gate_bundle(
    *,
    pytest_runner: Callable[[Sequence[str]], int],
    extra_args: Sequence[str] | None = None,
) -> int:
    """Execute the canonical gate bundle through the provided pytest runner."""

    return int(pytest_runner(build_pytest_args(extra_args)))


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ai_runtime_gate_bundle",
        description="Run the canonical deterministic product AI runtime gate bundle.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Print the canonical test nodes without executing them.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_arg_parser()
    args, extra_pytest_args = parser.parse_known_args(list(argv) if argv is not None else None)
    if args.list:
        for node in AI_RUNTIME_GATE_TEST_NODES:
            print(node)
        return 0

    import pytest

    return run_gate_bundle(pytest_runner=pytest.main, extra_args=extra_pytest_args)


if __name__ == "__main__":
    raise SystemExit(main())
