#!/usr/bin/env python3
"""Run main-branch pytest shards without pytest-xdist."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import importlib.util
import math
import os
import signal
import subprocess  # nosec B404: subprocess is required for bounded local shard isolation without shell (remove-by: 2026-07-31, ref: PR-1748)
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

DEFAULT_SHARD_COUNT = 2
DEFAULT_MAX_PARALLEL = 2
DEFAULT_FAULTHANDLER_TIMEOUT_SECONDS = 300
DEFAULT_SHARD_TIMEOUT_SECONDS = 1800
DEFAULT_COVERAGE_TIMEOUT_SECONDS = 1200
DEFAULT_ARTIFACT_LABEL = "pymain"
JUNIT_FAMILY = "legacy"
SLOW_MARK_EXPRESSION = "not slow"
DEFAULT_MARK_EXPRESSION = SLOW_MARK_EXPRESSION
DEFAULT_DURATIONS_MIN_SECONDS = "10.0"
BAYESIAN_PERSIST_TRUTHY = {"1", "true", "yes", "on"}
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


@dataclass
class RunningShard:
    """A live pytest shard subprocess owned directly by the parent runner."""

    shard: TestShard
    process: subprocess.Popen[bytes]
    started_at: float
    timeout_seconds: int


def build_test_file(repo_root: Path, test_path: Path) -> TestFile:
    """Return the normalized shard metadata for one pytest file."""

    return TestFile(
        path=test_path.relative_to(repo_root),
        weight=max(test_path.stat().st_size, 1),
    )


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
        discovered.append(build_test_file(repo_root, test_path))
    return discovered


def discover_serial_test_files(repo_root: Path) -> list[TestFile]:
    """Return tests that must run outside the process-parallel main shards."""

    discovered: list[TestFile] = []
    for relative_path in sorted(SERIAL_MAIN_TEST_PATHS):
        test_path = repo_root / relative_path
        if test_path.is_file():
            discovered.append(build_test_file(repo_root, test_path))
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


def validate_marker_expression(value: str) -> str:
    """Return a non-empty single-line pytest mark expression."""

    marker_expression = value.strip()
    if not marker_expression:
        raise ValueError("marker expression must not be empty")
    if "\n" in marker_expression or "\r" in marker_expression:
        raise ValueError("marker expression must be a single line")
    return marker_expression


def validate_single_line_option(value: str, *, option_name: str) -> str:
    """Return a non-empty single-line CLI option value."""

    option_value = value.strip()
    if not option_value:
        raise ValueError(f"{option_name} must not be empty")
    if "\n" in option_value or "\r" in option_value:
        raise ValueError(f"{option_name} must be a single line")
    return option_value


def validate_durations_min(value: str) -> str:
    """Return a non-negative pytest durations-min value."""

    durations_min = validate_single_line_option(value, option_name="durations-min")
    try:
        parsed_value = float(durations_min)
    except ValueError as exc:
        raise ValueError("durations-min must be numeric") from exc
    if not math.isfinite(parsed_value) or parsed_value < 0:
        raise ValueError("durations-min must be finite and non-negative")
    return durations_min


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


def pytest_cov_available() -> bool:
    """Return whether the active interpreter can load pytest-cov."""

    return importlib.util.find_spec("pytest_cov") is not None


def build_pytest_args(
    shard: TestShard,
    repo_root: Path,
    marker_expression: str = DEFAULT_MARK_EXPRESSION,
    durations_min: str = DEFAULT_DURATIONS_MIN_SECONDS,
    report_chars: str | None = None,
) -> list[str]:
    """Build one no-xdist pytest argv for a shard."""

    marker_expression = validate_marker_expression(marker_expression)
    durations_min = validate_durations_min(durations_min)
    pytest_args = [
        "-c",
        "pyproject.toml",
        "-p",
        "no:xdist",
        "-m",
        marker_expression,
        "--durations=25",
        f"--durations-min={durations_min}",
        "-o",
        f"faulthandler_timeout={DEFAULT_FAULTHANDLER_TIMEOUT_SECONDS}",
        "--basetemp",
        str(shard_basetemp_dir(repo_root, shard)),
        "--junitxml",
        shard.junit_file,
        "-o",
        f"junit_family={JUNIT_FAMILY}",
        *[str(test_file.path) for test_file in shard.files],
    ]
    if report_chars is not None:
        pytest_args.extend(
            ["-r", validate_single_line_option(report_chars, option_name="report-chars")]
        )
    if pytest_cov_available():
        junit_index = pytest_args.index("--junitxml")
        pytest_args[junit_index:junit_index] = ["--cov=.", "--cov-report="]
    return pytest_args


def bayesian_persist_enabled(base_env: Mapping[str, str]) -> bool:
    """Return whether Bayesian history persistence is enabled for a shard run."""

    return base_env.get("BAYESIAN_PERSIST", "").strip().lower() in BAYESIAN_PERSIST_TRUTHY


def shard_bayesian_history_path(base_env: Mapping[str, str], shard: TestShard) -> str:
    """Return a shard-local Bayesian history path to avoid process write races."""

    raw_path = base_env.get("BAYESIAN_HISTORY_PATH", "test_execution_history.json").strip()
    history_path = Path(raw_path or "test_execution_history.json")
    shard_suffix = f"{shard.artifact_label}-shard-{shard.index}"
    if history_path.stem.endswith(f"-{shard_suffix}"):
        return str(history_path)
    scoped_name = f"{history_path.stem}-{shard_suffix}{history_path.suffix}"
    return str(history_path.with_name(scoped_name))


def build_shard_env(base_env: dict[str, str], shard: TestShard, repo_root: Path) -> dict[str, str]:
    """Return an isolated environment for one pytest shard."""

    env = base_env.copy()
    env.pop("PYTEST_XDIST_WORKER", None)
    env["MAIN_TEST_SHARD"] = str(shard.index)
    env["MAIN_TEST_SHARD_LABEL"] = shard.artifact_label
    env["COVERAGE_FILE"] = str(repo_root / shard.coverage_file)
    env["COV_CORE_DATAFILE"] = str(repo_root / shard.coverage_file)
    env.setdefault("PYTEST_FAULTHANDLER_TIMEOUT_S", str(DEFAULT_FAULTHANDLER_TIMEOUT_SECONDS))
    if bayesian_persist_enabled(base_env):
        env["BAYESIAN_HISTORY_PATH"] = shard_bayesian_history_path(base_env, shard)
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


def coverage_timeout_seconds(base_env: Mapping[str, str]) -> int:
    """Return the watchdog timeout for one post-shard coverage phase."""

    raw_value = base_env.get("MAIN_TEST_COVERAGE_TIMEOUT_SECONDS", "").strip()
    if not raw_value:
        return DEFAULT_COVERAGE_TIMEOUT_SECONDS
    try:
        timeout = int(raw_value)
    except ValueError:
        print(
            f"MAIN_TEST_COVERAGE_TIMEOUT_INVALID value={raw_value!r} "
            f"default={DEFAULT_COVERAGE_TIMEOUT_SECONDS}",
            file=sys.stderr,
            flush=True,
        )
        return DEFAULT_COVERAGE_TIMEOUT_SECONDS
    if timeout < 60:
        print(
            f"MAIN_TEST_COVERAGE_TIMEOUT_TOO_LOW value={timeout} "
            f"default={DEFAULT_COVERAGE_TIMEOUT_SECONDS}",
            file=sys.stderr,
            flush=True,
        )
        return DEFAULT_COVERAGE_TIMEOUT_SECONDS
    return timeout


def run_shard_child(
    repo_root: Path,
    shard: TestShard,
    base_env: dict[str, str],
    marker_expression: str = DEFAULT_MARK_EXPRESSION,
    durations_min: str = DEFAULT_DURATIONS_MIN_SECONDS,
    report_chars: str | None = None,
) -> int:
    """Run one pytest shard inside a disposable interpreter process."""

    import pytest

    shard_basetemp_dir(repo_root, shard).parent.mkdir(parents=True, exist_ok=True)
    pytest_args = build_pytest_args(
        shard,
        repo_root,
        marker_expression,
        durations_min,
        report_chars,
    )
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


def run_shard(
    repo_root: Path,
    shard: TestShard,
    base_env: dict[str, str],
    marker_expression: str = DEFAULT_MARK_EXPRESSION,
    durations_min: str = DEFAULT_DURATIONS_MIN_SECONDS,
    report_chars: str | None = None,
) -> int:
    """Run one pytest shard in a child interpreter and return its exit code."""

    running_shard = start_shard_process(
        repo_root,
        shard,
        base_env,
        marker_expression,
        durations_min,
        report_chars,
    )
    return wait_for_shard_process(running_shard)


def build_shard_command(
    repo_root: Path,
    shard: TestShard,
    marker_expression: str = DEFAULT_MARK_EXPRESSION,
    durations_min: str = DEFAULT_DURATIONS_MIN_SECONDS,
    report_chars: str | None = None,
) -> list[str]:
    """Build the explicit child-interpreter command for one shard."""

    marker_expression = validate_marker_expression(marker_expression)
    durations_min = validate_durations_min(durations_min)
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
        "--marker-expression",
        marker_expression,
        "--durations-min",
        durations_min,
    ]
    if report_chars is not None:
        command.extend(
            [
                "--report-chars",
                validate_single_line_option(report_chars, option_name="report-chars"),
            ]
        )
    for test_file in shard.files:
        command.extend(["--shard-file", str(test_file.path)])
    return command


def start_shard_process(
    repo_root: Path,
    shard: TestShard,
    base_env: dict[str, str],
    marker_expression: str = DEFAULT_MARK_EXPRESSION,
    durations_min: str = DEFAULT_DURATIONS_MIN_SECONDS,
    report_chars: str | None = None,
) -> RunningShard:
    """Start one explicit shard subprocess and return its process metadata."""

    env = build_shard_env(base_env, shard, repo_root)
    command = build_shard_command(
        repo_root,
        shard,
        marker_expression,
        durations_min,
        report_chars,
    )
    timeout = shard_timeout_seconds(base_env)
    process = subprocess.Popen(  # nosec B603: argv uses the current Python interpreter and explicit repo-local shard runner without shell (remove-by: 2026-07-31, ref: PR-1748)
        command,
        cwd=repo_root,
        env=env,
        start_new_session=(os.name == "posix"),
    )
    return RunningShard(
        shard=shard,
        process=process,
        started_at=time.monotonic(),
        timeout_seconds=timeout,
    )


def wait_for_shard_process(running_shard: RunningShard) -> int:
    """Wait for one shard subprocess with timeout diagnostics."""

    process: subprocess.Popen[bytes] | None = None
    previous_handlers: dict[signal.Signals, Any] = {}
    shard = running_shard.shard
    timeout = running_shard.timeout_seconds

    def terminate_child_for_signal(signum: int, _frame: Any) -> None:
        if process is not None:
            _terminate_process_group(process)
        raise SystemExit(128 + signum)

    if os.name == "posix":
        for signum in (signal.SIGTERM, signal.SIGINT):
            previous_handlers[signum] = signal.getsignal(signum)
            signal.signal(signum, terminate_child_for_signal)
    try:
        process = running_shard.process
        return int(process.wait(timeout=timeout))
    except subprocess.TimeoutExpired:
        if process is not None:
            _terminate_process_group(process)
        log_shard_timeout(shard, timeout)
        return 124
    finally:
        for signum, previous_handler in previous_handlers.items():
            signal.signal(signum, previous_handler)


def log_shard_timeout(shard: TestShard, timeout: int) -> None:
    """Log timeout context for a shard and its selected files."""

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


def run_coverage_command(
    repo_root: Path,
    args: Sequence[str],
    coverage_main: Callable[[list[str]], int | None] | None = None,
    timeout_seconds: int = DEFAULT_COVERAGE_TIMEOUT_SECONDS,
) -> int:
    """Run a coverage command after all pytest shards pass."""

    if timeout_seconds < 1:
        raise ValueError("coverage timeout must be >= 1")

    if coverage_main is None:
        env = os.environ.copy()
        env.pop("COVERAGE_FILE", None)
        env.pop("COV_CORE_DATAFILE", None)
        try:
            result = subprocess.run(  # nosec B603: argv uses sys.executable and coverage module without shell (remove-by: 2026-07-31, ref: PR-2020)
                [sys.executable, "-m", "coverage", *args],
                cwd=repo_root,
                env=env,
                check=False,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            print(
                "MAIN_TEST_COVERAGE_COMMAND_TIMEOUT "
                f"phase={args[0] if args else 'unknown'} timeout_seconds={timeout_seconds}",
                file=sys.stderr,
                flush=True,
            )
            return 124
        return int(result.returncode)

    old_cwd = Path.cwd()
    old_coverage_file = os.environ.pop("COVERAGE_FILE", None)
    old_cov_core_datafile = os.environ.pop("COV_CORE_DATAFILE", None)
    try:
        os.chdir(repo_root)
        return int(coverage_main(list(args)) or 0)
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
    htmlcov_path = repo_root / "htmlcov"
    if htmlcov_path.is_dir():
        import shutil

        shutil.rmtree(htmlcov_path)


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


def _log_coverage_phase_started(
    phase: str,
    args: Sequence[str],
    timeout_seconds: int,
) -> None:
    """Log a coverage phase before running it so timeout context is visible."""

    print(
        f"MAIN_TEST_COVERAGE_{phase.upper()}_STARTED "
        f"timeout_seconds={timeout_seconds} args={list(args)!r}",
        file=sys.stderr,
        flush=True,
    )


def _log_coverage_phase_succeeded(phase: str) -> None:
    """Log coverage phase success for post-shard diagnostics."""

    print(
        f"MAIN_TEST_COVERAGE_{phase.upper()}_SUCCEEDED",
        file=sys.stderr,
        flush=True,
    )


def run_coverage_phase(
    repo_root: Path,
    phase: str,
    args: Sequence[str],
    timeout_seconds: int,
) -> int:
    """Run one coverage phase with start/success/failure diagnostics."""

    _log_coverage_phase_started(phase, args, timeout_seconds)
    status = run_coverage_command(repo_root, args, timeout_seconds=timeout_seconds)
    if status != 0:
        _log_coverage_failure(phase, status)
        return status
    _log_coverage_phase_succeeded(phase)
    return 0


def run_all_shards(
    repo_root: Path,
    shards: Sequence[TestShard],
    max_parallel: int,
    base_env: dict[str, str],
    extra_coverage_files: Sequence[str] = (),
    marker_expression: str = DEFAULT_MARK_EXPRESSION,
    durations_min: str = DEFAULT_DURATIONS_MIN_SECONDS,
    report_chars: str | None = None,
    htmlcov: bool = False,
) -> int:
    """Run all shards, then combine and enforce coverage if all pass."""

    if max_parallel < 1:
        raise ValueError("max_parallel must be >= 1")
    if not shards:
        raise ValueError("at least one shard is required")
    marker_expression = validate_marker_expression(marker_expression)
    durations_min = validate_durations_min(durations_min)

    results: dict[int, int] = {}
    pending_shards = iter(shards)
    failure_seen = False
    running_shards: dict[int, RunningShard] = {}
    previous_handlers: dict[signal.Signals, Any] = {}
    poll_interval_seconds = 0.25
    try:

        def terminate_running_for_signal(signum: int, _frame: Any) -> None:
            for running_shard in running_shards.values():
                _terminate_process_group(running_shard.process)
            raise SystemExit(128 + signum)

        if os.name == "posix":
            for signum in (signal.SIGTERM, signal.SIGINT):
                previous_handlers[signum] = signal.getsignal(signum)
                signal.signal(signum, terminate_running_for_signal)

        def submit_until_full() -> None:
            while len(running_shards) < max_parallel:
                try:
                    shard = next(pending_shards)
                except StopIteration:
                    return
                running_shards[shard.index] = start_shard_process(
                    repo_root,
                    shard,
                    base_env,
                    marker_expression,
                    durations_min,
                    report_chars,
                )

        submit_until_full()
        while running_shards:
            now = time.monotonic()
            for shard_index, running_shard in list(running_shards.items()):
                exit_code = running_shard.process.poll()
                if exit_code is not None:
                    results[shard_index] = int(exit_code)
                    del running_shards[shard_index]
                    if exit_code != 0:
                        failure_seen = True
                    continue
                elapsed = now - running_shard.started_at
                if elapsed >= running_shard.timeout_seconds:
                    _terminate_process_group(running_shard.process)
                    log_shard_timeout(running_shard.shard, running_shard.timeout_seconds)
                    results[shard_index] = 124
                    del running_shards[shard_index]
                    failure_seen = True

            if failure_seen:
                for shard_index, running_shard in sorted(running_shards.items()):
                    print(
                        f"MAIN_TEST_SHARD_CANCELLED index={shard_index} reason=fail_fast",
                        file=sys.stderr,
                        flush=True,
                    )
                    _terminate_process_group(running_shard.process)
                running_shards.clear()
                break

            submit_until_full()
            if running_shards:
                time.sleep(poll_interval_seconds)
    finally:
        for running_shard in running_shards.values():
            _terminate_process_group(running_shard.process)
        running_shards.clear()
        for signum, previous_handler in previous_handlers.items():
            signal.signal(signum, previous_handler)

    failing_shards = [
        shard_index for shard_index, exit_code in sorted(results.items()) if exit_code != 0
    ]
    if failing_shards:
        print(f"MAIN_TEST_SHARDS_FAILED shards={failing_shards}", file=sys.stderr)
        return 1

    coverage_timeout = coverage_timeout_seconds(base_env)
    coverage_files = [*extra_coverage_files, *[shard.coverage_file for shard in shards]]
    combine_status = run_coverage_phase(
        repo_root,
        "combine",
        ["combine", *coverage_files],
        coverage_timeout,
    )
    if combine_status != 0:
        return combine_status
    xml_status = run_coverage_phase(repo_root, "xml", ["xml"], coverage_timeout)
    if xml_status != 0:
        return xml_status
    if htmlcov:
        html_status = run_coverage_phase(repo_root, "html", ["html"], coverage_timeout)
        if html_status != 0:
            return html_status
    return run_coverage_phase(
        repo_root,
        "report",
        ["report", "-m", "--fail-under=97"],
        coverage_timeout,
    )


def run_serial_shards(
    repo_root: Path,
    serial_shards: Sequence[TestShard],
    base_env: dict[str, str],
    marker_expression: str = DEFAULT_MARK_EXPRESSION,
    durations_min: str = DEFAULT_DURATIONS_MIN_SECONDS,
    report_chars: str | None = None,
) -> int:
    """Run global/toolchain tests sequentially before process-parallel shards."""

    marker_expression = validate_marker_expression(marker_expression)
    durations_min = validate_durations_min(durations_min)
    for shard in serial_shards:
        exit_code = run_shard(
            repo_root,
            shard,
            base_env,
            marker_expression,
            durations_min,
            report_chars,
        )
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
        "--marker-expression",
        default=DEFAULT_MARK_EXPRESSION,
        help=(
            "Pytest marker expression for shard execution. Defaults to the main-CI "
            "contract 'not slow'."
        ),
    )
    parser.add_argument(
        "--durations-min",
        default=DEFAULT_DURATIONS_MIN_SECONDS,
        help="Value for pytest --durations-min. Defaults to the main-CI contract 10.0.",
    )
    parser.add_argument(
        "--report-chars",
        help="Optional pytest -r summary characters, for example fEsxXw.",
    )
    parser.add_argument(
        "--htmlcov",
        action="store_true",
        help="Generate the htmlcov coverage report after coverage.xml succeeds.",
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
        return run_shard_child(
            repo_root,
            shard,
            os.environ.copy(),
            validate_marker_expression(args.marker_expression),
            validate_durations_min(args.durations_min),
            args.report_chars,
        )

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
    marker_expression = validate_marker_expression(args.marker_expression)
    durations_min = validate_durations_min(args.durations_min)
    serial_status = run_serial_shards(
        repo_root,
        serial_shards,
        base_env,
        marker_expression,
        durations_min,
        args.report_chars,
    )
    if serial_status != 0:
        return serial_status
    return run_all_shards(
        repo_root,
        shards,
        args.max_parallel,
        base_env,
        extra_coverage_files=[shard.coverage_file for shard in serial_shards],
        marker_expression=marker_expression,
        durations_min=durations_min,
        report_chars=args.report_chars,
        htmlcov=args.htmlcov,
    )


if __name__ == "__main__":
    raise SystemExit(main())
