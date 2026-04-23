#!/usr/bin/env python3
"""Run Python 3.12 main-branch pytest shards without pytest-xdist."""

from __future__ import annotations

import argparse
import concurrent.futures
import multiprocessing
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Sequence

DEFAULT_SHARD_COUNT = 2
DEFAULT_MAX_PARALLEL = 2
DEFAULT_FAULTHANDLER_TIMEOUT_SECONDS = 300
JUNIT_FAMILY = "legacy"
SLOW_MARK_EXPRESSION = "not slow"


@dataclass(frozen=True)
class TestFile:
    """A pytest file with a deterministic balancing weight."""

    path: Path
    weight: int


@dataclass
class TestShard:
    """A collection of pytest files assigned to one process."""

    index: int
    files: list[TestFile] = field(default_factory=list)
    weight: int = 0

    def add(self, test_file: TestFile) -> None:
        self.files.append(test_file)
        self.weight += test_file.weight

    @property
    def coverage_file(self) -> str:
        return f".coverage.py312-main-shard-{self.index}"

    @property
    def junit_file(self) -> str:
        return f"tests/results-py312-shard-{self.index}.xml"


def discover_test_files(repo_root: Path) -> list[TestFile]:
    """Return all first-class pytest files for the main suite."""

    tests_root = repo_root / "tests"
    disabled_root = tests_root / "disabled_hypothesis"
    discovered: list[TestFile] = []
    for test_path in sorted(tests_root.rglob("test_*.py")):
        if disabled_root in test_path.parents:
            continue
        if any(part.startswith(".") for part in test_path.relative_to(repo_root).parts):
            continue
        discovered.append(
            TestFile(
                path=test_path.relative_to(repo_root),
                weight=max(test_path.stat().st_size, 1),
            )
        )
    return discovered


def partition_test_files(test_files: Sequence[TestFile], shard_count: int) -> list[TestShard]:
    """Greedily balance files by size while keeping deterministic shard output."""

    if shard_count < 1:
        raise ValueError("shard_count must be >= 1")
    if not test_files:
        raise ValueError("no pytest files discovered")

    shards = [TestShard(index=index) for index in range(1, shard_count + 1)]
    for test_file in sorted(test_files, key=lambda item: (-item.weight, str(item.path))):
        shard = min(shards, key=lambda item: (item.weight, item.index))
        shard.add(test_file)

    for shard in shards:
        shard.files.sort(key=lambda item: str(item.path))
    return shards


def build_pytest_args(shard: TestShard) -> list[str]:
    """Build one no-xdist pytest argv for a shard."""

    return [
        "-c",
        "pyproject.toml",
        "-p",
        "no:xdist",
        "-m",
        SLOW_MARK_EXPRESSION,
        "--durations=25",
        "--durations-min=10.0",
        "-o",
        f"faulthandler_timeout={DEFAULT_FAULTHANDLER_TIMEOUT_SECONDS}",
        "--cov=.",
        "--cov-report=",
        "--junitxml",
        shard.junit_file,
        "-o",
        f"junit_family={JUNIT_FAMILY}",
        *[str(test_file.path) for test_file in shard.files],
    ]


def build_shard_env(base_env: dict[str, str], shard: TestShard, repo_root: Path) -> dict[str, str]:
    """Return an isolated environment for one pytest shard."""

    env = base_env.copy()
    env["PYTEST_XDIST_WORKER"] = f"py312main{shard.index}"
    env["COVERAGE_FILE"] = str(repo_root / shard.coverage_file)
    env["COV_CORE_DATAFILE"] = str(repo_root / shard.coverage_file)
    env.setdefault("PYTEST_FAULTHANDLER_TIMEOUT_S", str(DEFAULT_FAULTHANDLER_TIMEOUT_SECONDS))
    return env


def run_shard(repo_root: Path, shard: TestShard, base_env: dict[str, str]) -> int:
    """Run one pytest shard and return its process exit code."""

    import pytest

    pytest_args = build_pytest_args(shard)
    env = build_shard_env(base_env, shard, repo_root)
    os.environ.update(env)
    os.chdir(repo_root)
    print(
        f"PY312_SHARD_STARTED index={shard.index} files={len(shard.files)} "
        f"weight={shard.weight} junit={shard.junit_file}",
        flush=True,
    )
    exit_code = pytest.main(pytest_args)
    print(
        f"PY312_SHARD_FINISHED index={shard.index} exit_code={exit_code}",
        flush=True,
    )
    return int(exit_code)


def run_coverage_command(repo_root: Path, args: Sequence[str]) -> int:
    """Run a coverage command after all pytest shards pass."""

    import coverage.cmdline

    old_cwd = Path.cwd()
    try:
        os.chdir(repo_root)
        return int(coverage.cmdline.main(list(args)) or 0)
    finally:
        os.chdir(old_cwd)


def remove_previous_outputs(repo_root: Path, shards: Sequence[TestShard]) -> None:
    """Remove stale shard coverage and JUnit files before execution."""

    for coverage_file in repo_root.glob(".coverage.py312-main-shard-*"):
        coverage_file.unlink()
    for shard in shards:
        junit_path = repo_root / shard.junit_file
        if junit_path.exists():
            junit_path.unlink()


def collect_shard_results(
    futures: Mapping[concurrent.futures.Future[int], int],
) -> dict[int, int]:
    """Collect shard results and preserve diagnostics for crashed worker processes."""

    results: dict[int, int] = {}
    for future, shard_index in futures.items():
        try:
            results[shard_index] = future.result()
        except BaseException as exc:
            print(
                f"PY312_SHARD_EXCEPTION index={shard_index} "
                f"type={type(exc).__name__} message={exc}",
                file=sys.stderr,
                flush=True,
            )
            results[shard_index] = 1
    return results


def run_all_shards(
    repo_root: Path,
    shards: Sequence[TestShard],
    max_parallel: int,
    base_env: dict[str, str],
) -> int:
    """Run all shards, then combine and enforce coverage if all pass."""

    if max_parallel < 1:
        raise ValueError("max_parallel must be >= 1")
    if not shards:
        raise ValueError("at least one shard is required")

    process_context = multiprocessing.get_context("spawn")
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=min(max_parallel, len(shards)),
        mp_context=process_context,
    ) as executor:
        futures = {
            executor.submit(run_shard, repo_root, shard, base_env): shard.index for shard in shards
        }
        results = collect_shard_results(futures)

    failing_shards = [
        shard_index for shard_index, exit_code in sorted(results.items()) if exit_code != 0
    ]
    if failing_shards:
        print(f"PY312_SHARDS_FAILED shards={failing_shards}", file=sys.stderr)
        return 1

    coverage_files = [shard.coverage_file for shard in shards]
    combine_status = run_coverage_command(repo_root, ["combine", *coverage_files])
    if combine_status != 0:
        return combine_status
    xml_status = run_coverage_command(repo_root, ["xml"])
    if xml_status != 0:
        return xml_status
    return run_coverage_command(repo_root, ["report", "-m", "--fail-under=97"])


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--shard-count", type=int, default=DEFAULT_SHARD_COUNT)
    parser.add_argument("--max-parallel", type=int, default=DEFAULT_MAX_PARALLEL)
    parser.add_argument(
        "--list-shards",
        action="store_true",
        help="Print deterministic shard assignment without running pytest.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    repo_root = args.repo_root.resolve()
    test_files = discover_test_files(repo_root)
    shards = partition_test_files(test_files, args.shard_count)

    for shard in shards:
        print(
            f"PY312_SHARD_PLAN index={shard.index} files={len(shard.files)} "
            f"weight={shard.weight}",
            flush=True,
        )
        if args.list_shards:
            for test_file in shard.files:
                print(f"  {test_file.path}")

    if args.list_shards:
        return 0

    remove_previous_outputs(repo_root, shards)
    return run_all_shards(repo_root, shards, args.max_parallel, os.environ.copy())


if __name__ == "__main__":
    raise SystemExit(main())
