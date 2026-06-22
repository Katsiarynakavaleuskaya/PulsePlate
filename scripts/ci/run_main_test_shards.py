#!/usr/bin/env python3
"""Run main-branch pytest shards without pytest-xdist."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import multiprocessing
import os
import signal
import subprocess  # nosec B404: subprocess is required for bounded local shard isolation without shell (remove-by: 2026-07-31, ref: PR-1748)
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

DEFAULT_SHARD_COUNT = 2
DEFAULT_MAX_PARALLEL = 2
DEFAULT_FAULTHANDLER_TIMEOUT_SECONDS = 300
DEFAULT_SHARD_TIMEOUT_SECONDS = 1800
DEFAULT_ARTIFACT_LABEL = "pymain"
JUNIT_FAMILY = "legacy"
SLOW_MARK_EXPRESSION = "not slow"
PYTEST_BASETEMP_ROOT_NAME = "pulseplate-main-test-shards"
PYTEST_BASETEMP_FALLBACK_ROOT_NAME = "pulseplate-main-test-shards-external"
POSIX_TEMP_ROOT = Path(os.sep) / "tmp"
WINDOWS_TEMP_ROOT = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "Temp"
SERIAL_MAIN_TEST_PATHS = frozenset({Path("tests/test_design_token_parity.py")})


@dataclass(frozen=True)
class TestFile:
    """A pytest file with a deterministic balancing weight."""

    path: Path
    weight: int


@dataclass
class TestShard:
    """A collection of pytest files assigned to one process."""

    index: int
    artifact_label: str = DEFAULT_ARTIFACT_LABEL
    files: list[TestFile] = field(default_factory=list)
    weight: int = 0

    def add(self, test_file: TestFile) -> None:
        self.files.append(test_file)
        self.weight += test_file.weight

    @property
    def coverage_file(self) -> str:
        return f".coverage.{self.artifact_label}-main-shard-{self.index}"

    @property
    def junit_file(self) -> str:
        return f"tests/results-{self.artifact_label}-shard-{self.index}.xml"


def discover_test_files(
    repo_root: Path,
    excluded_paths: frozenset[Path] = frozenset(),
) -> list[TestFile]:
    """Return all first-class pytest files for the main suite."""

    tests_root = repo_root / "tests"
    disabled_root = tests_root / "disabled_hypothesis"
    discovered: list[TestFile] = []
    for test_path in sorted(tests_root.rglob("test_*.py")):
        if disabled_root in test_path.parents:
            continue
        relative_path = test_path.relative_to(repo_root)
        if relative_path in excluded_paths:
            continue
        if any(part.startswith(".") for part in relative_path.parts):
            continue
        discovered.append(
            TestFile(
                path=relative_path,
                weight=max(test_path.stat().st_size, 1),
            )
        )
    return discovered


def discover_serial_test_files(repo_root: Path) -> list[TestFile]:
    """Return tests that must run outside the process-parallel main shards."""

    discovered: list[TestFile] = []
    for relative_path in sorted(SERIAL_MAIN_TEST_PATHS):
        test_path = repo_root / relative_path
        if test_path.is_file():
            discovered.append(TestFile(path=relative_path, weight=max(test_path.stat().st_size, 1)))
    return discovered


def build_serial_shards(repo_root: Path, artifact_label: str) -> list[TestShard]:
    """Build deterministic serial shard wrappers for global/toolchain tests."""

    serial_tests = discover_serial_test_files(repo_root)
    if not serial_tests:
        return []
    return [
        TestShard(
            index=0,
            artifact_label=artifact_label,
            files=serial_tests,
            weight=sum(test_file.weight for test_file in serial_tests),
        )
    ]


def normalize_python_label(value: str) -> str:
    """Return a stable artifact label such as ``py312`` for a Python version."""

    label = value.strip().lower()
    if not label:
        raise ValueError("python version label must not be empty")
    if label.startswith("python-"):
        label = label.removeprefix("python-")
    if label.startswith("python"):
        label = label.removeprefix("python")
    if label.startswith("py"):
        label = label.removeprefix("py")
    label = label.replace(".", "").replace("_", "").replace("-", "")
    if not label.isalnum():
        raise ValueError(f"unsupported python version label: {value!r}")
    return validate_artifact_label(f"py{label}")


def validate_artifact_label(value: str) -> str:
    """Return an explicit artifact label after path-safe validation."""

    label = value.strip().lower()
    if not label.startswith("py") or len(label) <= 2 or not label.isalnum():
        raise ValueError(
            "artifact label must start with 'py' and contain only ASCII letters or digits"
        )
    return label


def partition_test_files(
    test_files: Sequence[TestFile],
    shard_count: int,
    artifact_label: str = DEFAULT_ARTIFACT_LABEL,
) -> list[TestShard]:
    """Greedily balance files by size while keeping deterministic shard output."""

    if shard_count < 1:
        raise ValueError("shard_count must be >= 1")
    if not test_files:
        raise ValueError("no pytest files discovered")

    effective_shard_count = min(shard_count, len(test_files))
    shards = [
        TestShard(index=index, artifact_label=artifact_label)
        for index in range(1, effective_shard_count + 1)
    ]
    for test_file in sorted(test_files, key=lambda item: (-item.weight, str(item.path))):
        shard = min(shards, key=lambda item: (item.weight, item.index))
        shard.add(test_file)

    for shard in shards:
        shard.files.sort(key=lambda item: str(item.path))
    return shards


def external_temp_root(repo_root: Path) -> Path:
    """Return a temp root that is guaranteed to live outside the repo tree."""

    resolved_repo_root = repo_root.resolve()
    candidates = [Path(tempfile.gettempdir())]
    if os.name == "posix":
        candidates.append(POSIX_TEMP_ROOT)
    elif os.name == "nt":
        candidates.append(WINDOWS_TEMP_ROOT)

    for candidate in candidates:
        resolved_candidate = candidate.resolve()
        if not resolved_candidate.is_relative_to(resolved_repo_root):
            return resolved_candidate

    raise RuntimeError("unable to resolve pytest basetemp root outside repo")


def shard_basetemp_dir(repo_root: Path, shard: TestShard) -> Path:
    """Return a deterministic external pytest base temp directory for one shard."""

    resolved_repo_root = repo_root.resolve()
    repo_key = hashlib.sha256(str(resolved_repo_root).encode("utf-8")).hexdigest()[:12]
    temp_root = external_temp_root(repo_root)
    for root_name in (PYTEST_BASETEMP_ROOT_NAME, PYTEST_BASETEMP_FALLBACK_ROOT_NAME):
        candidate = temp_root / root_name / repo_key / f"{shard.artifact_label}-shard-{shard.index}"
        if not candidate.resolve().is_relative_to(resolved_repo_root):
            return candidate
    raise RuntimeError("unable to resolve pytest basetemp path outside repo")


def build_pytest_args(shard: TestShard, repo_root: Path) -> list[str]:
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
        "--basetemp",
        str(shard_basetemp_dir(repo_root, shard)),
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
    env.pop("PYTEST_XDIST_WORKER", None)
    env["MAIN_TEST_SHARD"] = str(shard.index)
    env["MAIN_TEST_SHARD_LABEL"] = shard.artifact_label
    env["COVERAGE_FILE"] = str(repo_root / shard.coverage_file)
    env["COV_CORE_DATAFILE"] = str(repo_root / shard.coverage_file)
    env.setdefault("PYTEST_FAULTHANDLER_TIMEOUT_S", str(DEFAULT_FAULTHANDLER_TIMEOUT_SECONDS))
    return env


def shard_timeout_seconds(base_env: Mapping[str, str]) -> int:
    """Return the watchdog timeout for one pytest shard subprocess."""

    raw_value = base_env.get("MAIN_TEST_SHARD_TIMEOUT_SECONDS", "").strip()
    if not raw_value:
        return DEFAULT_SHARD_TIMEOUT_SECONDS
    try:
        timeout = int(raw_value)
    except ValueError:
        print(
            f"MAIN_TEST_SHARD_TIMEOUT_INVALID value={raw_value!r} "
            f"default={DEFAULT_SHARD_TIMEOUT_SECONDS}",
            file=sys.stderr,
            flush=True,
        )
        return DEFAULT_SHARD_TIMEOUT_SECONDS
    if timeout < 60:
        print(
            f"MAIN_TEST_SHARD_TIMEOUT_TOO_LOW value={timeout} "
            f"default={DEFAULT_SHARD_TIMEOUT_SECONDS}",
            file=sys.stderr,
            flush=True,
        )
        return DEFAULT_SHARD_TIMEOUT_SECONDS
    return timeout


def run_shard_child(repo_root: Path, shard: TestShard, base_env: dict[str, str]) -> int:
    """Run one pytest shard inside a disposable interpreter process."""

    import pytest

    shard_basetemp_dir(repo_root, shard).parent.mkdir(parents=True, exist_ok=True)
    pytest_args = build_pytest_args(shard, repo_root)
    env = build_shard_env(base_env, shard, repo_root)
    os.environ.pop("PYTEST_XDIST_WORKER", None)
    os.environ.update(env)
    os.chdir(repo_root)
    print(
        f"MAIN_TEST_SHARD_STARTED label={shard.artifact_label} index={shard.index} "
        f"files={len(shard.files)} weight={shard.weight} junit={shard.junit_file}",
        flush=True,
    )
    sys.argv = ["pytest"]
    exit_code = pytest.main(pytest_args)
    print(
        f"MAIN_TEST_SHARD_FINISHED label={shard.artifact_label} "
        f"index={shard.index} exit_code={exit_code}",
        flush=True,
    )
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(int(exit_code))


def run_shard(repo_root: Path, shard: TestShard, base_env: dict[str, str]) -> int:
    """Run one pytest shard in a child interpreter and return its exit code."""

    env = build_shard_env(base_env, shard, repo_root)
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--repo-root",
        str(repo_root),
        "--artifact-label",
        shard.artifact_label,
        "--run-shard-index",
        str(shard.index),
        "--shard-weight",
        str(shard.weight),
    ]
    for test_file in shard.files:
        command.extend(["--shard-file", str(test_file.path)])

    timeout = shard_timeout_seconds(base_env)
    process: subprocess.Popen[bytes] | None = None
    previous_handlers: dict[signal.Signals, Any] = {}

    def terminate_child_for_signal(signum: int, _frame: Any) -> None:
        if process is not None:
            _terminate_process_group(process)
        raise SystemExit(128 + signum)

    if os.name == "posix":
        for signum in (signal.SIGTERM, signal.SIGINT):
            previous_handlers[signum] = signal.getsignal(signum)
            signal.signal(signum, terminate_child_for_signal)
    try:
        process = subprocess.Popen(  # nosec B603: argv uses the current Python interpreter and explicit repo-local shard runner without shell (remove-by: 2026-07-31, ref: PR-1748)
            command,
            cwd=repo_root,
            env=env,
            start_new_session=(os.name == "posix"),
        )
        return int(process.wait(timeout=timeout))
    except subprocess.TimeoutExpired:
        if process is not None:
            _terminate_process_group(process)
        print(
            f"MAIN_TEST_SHARD_TIMEOUT_FAILED label={shard.artifact_label} "
            f"index={shard.index} timeout_seconds={timeout}",
            file=sys.stderr,
            flush=True,
        )
        for test_file in shard.files:
            print(
                f"MAIN_TEST_SHARD_TIMEOUT_FILE label={shard.artifact_label} "
                f"index={shard.index} path={test_file.path}",
                file=sys.stderr,
                flush=True,
            )
        return 124
    finally:
        for signum, previous_handler in previous_handlers.items():
            signal.signal(signum, previous_handler)


def _terminate_process_group(process: subprocess.Popen[bytes]) -> None:
    """Terminate a shard subprocess and its descendants without waiting for timeout."""

    if process.poll() is not None:
        return
    try:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGTERM)
        else:
            process.terminate()
        process.wait(timeout=10)
    except ProcessLookupError:
        return
    except subprocess.TimeoutExpired:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
        process.wait(timeout=10)


def _build_explicit_shard(args: argparse.Namespace, artifact_label: str) -> TestShard:
    """Build the shard requested by a parent runner invocation."""

    if args.run_shard_index is None:
        raise ValueError("run_shard_index is required for explicit shard mode")
    if not args.shard_file:
        raise ValueError("at least one --shard-file is required for explicit shard mode")

    shard = TestShard(
        index=args.run_shard_index,
        artifact_label=artifact_label,
        weight=args.shard_weight,
    )
    for test_file in args.shard_file:
        shard.files.append(TestFile(path=Path(test_file), weight=1))
    return shard


def run_coverage_command(repo_root: Path, args: Sequence[str]) -> int:
    """Run a coverage command after all pytest shards pass."""

    import coverage.cmdline

    old_cwd = Path.cwd()
    old_coverage_file = os.environ.pop("COVERAGE_FILE", None)
    old_cov_core_datafile = os.environ.pop("COV_CORE_DATAFILE", None)
    try:
        os.chdir(repo_root)
        return int(coverage.cmdline.main(list(args)) or 0)
    finally:
        if old_coverage_file is not None:
            os.environ["COVERAGE_FILE"] = old_coverage_file
        if old_cov_core_datafile is not None:
            os.environ["COV_CORE_DATAFILE"] = old_cov_core_datafile
        os.chdir(old_cwd)


def remove_previous_outputs(repo_root: Path, shards: Sequence[TestShard]) -> None:
    """Remove stale shard coverage and JUnit files before execution."""

    labels = {shard.artifact_label for shard in shards}
    for label in labels:
        for coverage_file in repo_root.glob(f".coverage.{label}-main-shard-*"):
            coverage_file.unlink()
        for junit_file in (repo_root / "tests").glob(f"results-{label}-shard-*.xml"):
            junit_file.unlink()
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
        except Exception as exc:
            print(
                f"MAIN_TEST_SHARD_EXCEPTION index={shard_index} "
                f"type={type(exc).__name__} message={exc}",
                file=sys.stderr,
                flush=True,
            )
            results[shard_index] = 1
    return results


def _log_coverage_failure(phase: str, returncode: int) -> None:
    """Log the coverage phase that failed after all shards completed."""

    print(
        f"MAIN_TEST_COVERAGE_{phase.upper()}_FAILED exit_code={returncode}",
        file=sys.stderr,
        flush=True,
    )


def _terminate_executor_workers(
    executor: concurrent.futures.ProcessPoolExecutor,
) -> None:
    """Terminate process-pool workers after a fail-fast shard result."""

    worker_processes = list((getattr(executor, "_processes", None) or {}).values())
    for worker_process in worker_processes:
        if worker_process.is_alive():
            worker_process.terminate()
    for worker_process in worker_processes:
        worker_process.join(timeout=10)
        if worker_process.is_alive():
            worker_process.kill()
            worker_process.join(timeout=10)


def _cancel_inflight_shards(
    executor: concurrent.futures.ProcessPoolExecutor,
    futures: Mapping[concurrent.futures.Future[int], int],
) -> None:
    """Cancel submitted shards once one shard has already failed."""

    for future, shard_index in sorted(futures.items(), key=lambda item: item[1]):
        future.cancel()
        print(
            f"MAIN_TEST_SHARD_CANCELLED index={shard_index} reason=fail_fast",
            file=sys.stderr,
            flush=True,
        )
    _terminate_executor_workers(executor)
    executor.shutdown(wait=False, cancel_futures=True)


def run_all_shards(
    repo_root: Path,
    shards: Sequence[TestShard],
    max_parallel: int,
    base_env: dict[str, str],
    extra_coverage_files: Sequence[str] = (),
) -> int:
    """Run all shards, then combine and enforce coverage if all pass."""

    if max_parallel < 1:
        raise ValueError("max_parallel must be >= 1")
    if not shards:
        raise ValueError("at least one shard is required")

    process_context = multiprocessing.get_context("spawn")
    results: dict[int, int] = {}
    pending_shards = iter(shards)
    failure_seen = False
    executor = concurrent.futures.ProcessPoolExecutor(
        max_workers=min(max_parallel, len(shards)),
        mp_context=process_context,
    )
    executor_shutdown = False
    try:
        futures: dict[concurrent.futures.Future[int], int] = {}
        for shard in pending_shards:
            futures[executor.submit(run_shard, repo_root, shard, base_env)] = shard.index
            if len(futures) >= max_parallel:
                break

        while futures:
            done, _ = concurrent.futures.wait(
                futures,
                return_when=concurrent.futures.FIRST_COMPLETED,
            )
            completed_results = collect_shard_results({future: futures[future] for future in done})
            results.update(completed_results)
            if any(exit_code != 0 for exit_code in completed_results.values()):
                failure_seen = True
            for future in done:
                del futures[future]
            if failure_seen:
                _cancel_inflight_shards(executor, futures)
                executor_shutdown = True
                futures.clear()
                break
            for shard in pending_shards:
                futures[executor.submit(run_shard, repo_root, shard, base_env)] = shard.index
                if len(futures) >= max_parallel:
                    break
    finally:
        if not executor_shutdown:
            executor.shutdown(wait=True)

    failing_shards = [
        shard_index for shard_index, exit_code in sorted(results.items()) if exit_code != 0
    ]
    if failing_shards:
        print(f"MAIN_TEST_SHARDS_FAILED shards={failing_shards}", file=sys.stderr)
        return 1

    coverage_files = [*extra_coverage_files, *[shard.coverage_file for shard in shards]]
    combine_status = run_coverage_command(repo_root, ["combine", *coverage_files])
    if combine_status != 0:
        _log_coverage_failure("combine", combine_status)
        return combine_status
    xml_status = run_coverage_command(repo_root, ["xml"])
    if xml_status != 0:
        _log_coverage_failure("xml", xml_status)
        return xml_status
    report_status = run_coverage_command(repo_root, ["report", "-m", "--fail-under=97"])
    if report_status != 0:
        _log_coverage_failure("report", report_status)
    return report_status


def run_serial_shards(
    repo_root: Path,
    serial_shards: Sequence[TestShard],
    base_env: dict[str, str],
) -> int:
    """Run global/toolchain tests sequentially before process-parallel shards."""

    for shard in serial_shards:
        exit_code = run_shard(repo_root, shard, base_env)
        if exit_code != 0:
            print(
                f"MAIN_TEST_SERIAL_SHARD_FAILED label={shard.artifact_label} "
                f"index={shard.index} exit_code={exit_code}",
                file=sys.stderr,
                flush=True,
            )
            return exit_code
    return 0


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--shard-count", type=int, default=DEFAULT_SHARD_COUNT)
    parser.add_argument("--max-parallel", type=int, default=DEFAULT_MAX_PARALLEL)
    parser.add_argument(
        "--python-version",
        default=os.environ.get("MATRIX_PYTHON_VERSION"),
        help="Python version used for artifact labels, for example 3.12 or 3.13.",
    )
    parser.add_argument(
        "--artifact-label",
        help="Override the normalized artifact label used for coverage and JUnit files.",
    )
    parser.add_argument(
        "--list-shards",
        action="store_true",
        help="Print deterministic shard assignment without running pytest.",
    )
    parser.add_argument(
        "--run-shard-index",
        type=int,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--shard-file",
        action="append",
        default=[],
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--shard-weight",
        type=int,
        default=0,
        help=argparse.SUPPRESS,
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    repo_root = args.repo_root.resolve()
    artifact_label = (
        validate_artifact_label(args.artifact_label)
        if args.artifact_label
        else normalize_python_label(
            args.python_version or f"{sys.version_info.major}.{sys.version_info.minor}"
        )
    )
    if args.run_shard_index is not None:
        shard = _build_explicit_shard(args, artifact_label)
        return run_shard_child(repo_root, shard, os.environ.copy())

    serial_shards = build_serial_shards(repo_root, artifact_label)
    test_files = discover_test_files(repo_root, excluded_paths=SERIAL_MAIN_TEST_PATHS)
    shards = partition_test_files(test_files, args.shard_count, artifact_label)

    for serial_shard in serial_shards:
        print(
            f"MAIN_TEST_SERIAL_PLAN label={serial_shard.artifact_label} "
            f"index={serial_shard.index} files={len(serial_shard.files)} "
            f"weight={serial_shard.weight}",
            flush=True,
        )
        if args.list_shards:
            for test_file in serial_shard.files:
                print(f"  {test_file.path}")

    for shard in shards:
        print(
            f"MAIN_TEST_SHARD_PLAN label={shard.artifact_label} index={shard.index} "
            f"files={len(shard.files)} weight={shard.weight}",
            flush=True,
        )
        if args.list_shards:
            for test_file in shard.files:
                print(f"  {test_file.path}")

    if args.list_shards:
        return 0

    all_shards = [*serial_shards, *shards]
    remove_previous_outputs(repo_root, all_shards)
    base_env = os.environ.copy()
    serial_status = run_serial_shards(repo_root, serial_shards, base_env)
    if serial_status != 0:
        return serial_status
    return run_all_shards(
        repo_root,
        shards,
        args.max_parallel,
        base_env,
        extra_coverage_files=[shard.coverage_file for shard in serial_shards],
    )


if __name__ == "__main__":
    raise SystemExit(main())
