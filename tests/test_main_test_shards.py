"""Regression tests for the main-suite shard runner."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import Future
from pathlib import Path

import pytest

from scripts.ci import run_main_test_shards as runner
from scripts.ci import run_py312_main_shards as py312_wrapper

REPO_ROOT = Path(__file__).resolve().parents[1]


def _write_test_file(repo_root: Path, relative_path: str, content: str) -> Path:
    path = repo_root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_discover_test_files_includes_edges_and_excludes_disabled(tmp_path: Path) -> None:
    _write_test_file(tmp_path, "tests/test_alpha.py", "def test_alpha(): pass\n")
    _write_test_file(tmp_path, "tests/edges/test_beta.py", "def test_beta(): pass\n")
    _write_test_file(
        tmp_path,
        "tests/disabled_hypothesis/test_gamma.py",
        "def test_gamma(): pass\n",
    )
    _write_test_file(tmp_path, "tests/helper_alpha.py", "VALUE = 1\n")

    discovered = runner.discover_test_files(tmp_path)

    assert [test_file.path.as_posix() for test_file in discovered] == [
        "tests/edges/test_beta.py",
        "tests/test_alpha.py",
    ]


def test_build_test_file_normalizes_relative_path_and_weight(tmp_path: Path) -> None:
    test_path = _write_test_file(
        tmp_path,
        "tests/test_alpha.py",
        "def test_alpha(): pass\n",
    )

    test_file = runner.build_test_file(tmp_path, test_path)

    assert test_file == runner.TestFile(Path("tests/test_alpha.py"), test_path.stat().st_size)


def test_discover_test_files_excludes_serial_main_tests(tmp_path: Path) -> None:
    _write_test_file(tmp_path, "tests/test_alpha.py", "def test_alpha(): pass\n")
    _write_test_file(
        tmp_path,
        "tests/test_design_token_parity.py",
        "def test_design_token_parity(): pass\n",
    )

    discovered = runner.discover_test_files(
        tmp_path,
        excluded_paths=runner.SERIAL_MAIN_TEST_PATHS,
    )

    assert [test_file.path.as_posix() for test_file in discovered] == ["tests/test_alpha.py"]


def test_build_serial_shards_selects_toolchain_sensitive_tests(tmp_path: Path) -> None:
    design_tokens = _write_test_file(
        tmp_path,
        "tests/test_design_token_parity.py",
        "def test_design_token_parity(): pass\n",
    )

    serial_shards = runner.build_serial_shards(tmp_path, "py311")

    assert len(serial_shards) == 1
    assert serial_shards[0].index == 0
    assert serial_shards[0].artifact_label == "py311"
    assert serial_shards[0].coverage_file == ".coverage.py311-main-shard-0"
    assert serial_shards[0].junit_file == "tests/results-py311-shard-0.xml"
    assert serial_shards[0].files == [
        runner.TestFile(Path("tests/test_design_token_parity.py"), design_tokens.stat().st_size)
    ]


def test_partition_test_files_balances_by_weight_and_keeps_all_files() -> None:
    files = [
        runner.TestFile(Path("tests/test_big.py"), 100),
        runner.TestFile(Path("tests/test_medium.py"), 60),
        runner.TestFile(Path("tests/test_small.py"), 20),
        runner.TestFile(Path("tests/test_tiny.py"), 10),
    ]

    shards = runner.partition_test_files(files, shard_count=2)

    assert [shard.weight for shard in shards] == [100, 90]
    assert {test_file.path.as_posix() for shard in shards for test_file in shard.files} == {
        "tests/test_big.py",
        "tests/test_medium.py",
        "tests/test_small.py",
        "tests/test_tiny.py",
    }


def test_partition_test_files_never_returns_empty_shards() -> None:
    files = [runner.TestFile(Path("tests/test_only.py"), 100)]

    shards = runner.partition_test_files(files, shard_count=4)

    assert len(shards) == 1
    assert shards[0].files == files


def test_partition_test_files_rejects_invalid_input() -> None:
    with pytest.raises(ValueError, match="shard_count"):
        runner.partition_test_files([runner.TestFile(Path("tests/test_alpha.py"), 1)], 0)

    with pytest.raises(ValueError, match="no pytest files"):
        runner.partition_test_files([], 1)


@pytest.mark.parametrize(
    ("raw_label", "expected_label"),
    [
        ("3.12", "py312"),
        ("3.13", "py313"),
        ("python-3.13", "py313"),
        ("py313", "py313"),
    ],
)
def test_normalize_python_label(raw_label: str, expected_label: str) -> None:
    assert runner.normalize_python_label(raw_label) == expected_label


@pytest.mark.parametrize("unsafe_label", ["", "313", "py3.13", "py313/../../x", "py313-*"])
def test_validate_artifact_label_rejects_unsafe_values(unsafe_label: str) -> None:
    with pytest.raises(ValueError, match="artifact label"):
        runner.validate_artifact_label(unsafe_label)


def test_py312_compatibility_wrapper_keeps_legacy_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, list[str]] = {}

    def fake_runner(args: list[str]) -> int:
        captured["args"] = args
        return 0

    monkeypatch.setattr(py312_wrapper, "run_main_test_shards", fake_runner)

    assert py312_wrapper.main(["--shard-count", "2"]) == 0
    assert captured["args"] == ["--python-version", "3.12", "--shard-count", "2"]


def test_py312_compatibility_wrapper_preserves_explicit_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, list[str]] = {}

    def fake_runner(args: list[str]) -> int:
        captured["args"] = args
        return 0

    monkeypatch.setattr(py312_wrapper, "run_main_test_shards", fake_runner)

    assert py312_wrapper.main(["--python-version", "3.13", "--shard-count", "2"]) == 0
    assert captured["args"] == ["--python-version", "3.13", "--shard-count", "2"]


def test_py312_compatibility_wrapper_executes_as_legacy_file(tmp_path: Path) -> None:
    _write_test_file(tmp_path, "tests/test_alpha.py", "def test_alpha(): pass\n")
    (tmp_path / "pyproject.toml").write_text("[tool.pytest.ini_options]\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/ci/run_py312_main_shards.py",
            "--repo-root",
            str(tmp_path),
            "--shard-count",
            "1",
            "--list-shards",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert "MAIN_TEST_SHARD_PLAN label=py312 index=1 files=1" in result.stdout
    assert "tests/test_alpha.py" in result.stdout


def test_shard_basetemp_dir_is_unique_deterministic_and_external(tmp_path: Path) -> None:
    first = runner.TestShard(index=1, artifact_label="py313")
    second = runner.TestShard(index=2, artifact_label="py313")

    first_basetemp = runner.shard_basetemp_dir(tmp_path, first)
    second_basetemp = runner.shard_basetemp_dir(tmp_path, second)

    assert first_basetemp == runner.shard_basetemp_dir(tmp_path, first)
    assert first_basetemp != second_basetemp
    assert first_basetemp.name == "py313-shard-1"
    assert second_basetemp.name == "py313-shard-2"
    assert first_basetemp.parent.parent == (
        Path(tempfile.gettempdir()).resolve() / runner.PYTEST_BASETEMP_ROOT_NAME
    )
    assert not first_basetemp.resolve().is_relative_to(tmp_path.resolve())
    assert not second_basetemp.resolve().is_relative_to(tmp_path.resolve())


def test_shard_basetemp_dir_avoids_repo_local_temp_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_local_temp = tmp_path / "tmp"
    repo_local_temp.mkdir()
    shard = runner.TestShard(index=1, artifact_label="py313")
    monkeypatch.setattr(runner.tempfile, "gettempdir", lambda: str(repo_local_temp))

    basetemp = runner.shard_basetemp_dir(tmp_path, shard)

    fallback_root = runner.POSIX_TEMP_ROOT if os.name == "posix" else runner.WINDOWS_TEMP_ROOT
    assert basetemp.parent.parent == fallback_root.resolve() / runner.PYTEST_BASETEMP_ROOT_NAME
    assert not basetemp.resolve().is_relative_to(tmp_path.resolve())


def test_shard_basetemp_dir_rechecks_final_path_collision(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / runner.PYTEST_BASETEMP_ROOT_NAME
    repo_root.mkdir()
    shard = runner.TestShard(index=1, artifact_label="py313")
    monkeypatch.setattr(runner.tempfile, "gettempdir", lambda: str(tmp_path))

    basetemp = runner.shard_basetemp_dir(repo_root, shard)

    assert runner.PYTEST_BASETEMP_FALLBACK_ROOT_NAME in basetemp.parts
    assert not basetemp.resolve().is_relative_to(repo_root.resolve())


def test_build_pytest_args_disables_xdist_and_emits_junit(tmp_path: Path) -> None:
    shard = runner.TestShard(
        index=2,
        artifact_label="py313",
        files=[runner.TestFile(Path("tests/test_alpha.py"), 10)],
        weight=10,
    )

    pytest_args = runner.build_pytest_args(shard, tmp_path)

    assert pytest_args[:2] == ["-c", "pyproject.toml"]
    assert "-p" in pytest_args
    assert "no:xdist" in pytest_args
    assert "-n" not in pytest_args
    assert "--dist" not in pytest_args
    assert "-m" in pytest_args
    assert runner.DEFAULT_MARK_EXPRESSION in pytest_args
    assert "--durations-min=10.0" in pytest_args
    assert "--basetemp" in pytest_args
    assert pytest_args[pytest_args.index("--basetemp") + 1] == str(
        runner.shard_basetemp_dir(tmp_path, shard)
    )
    assert f"junit_family={runner.JUNIT_FAMILY}" in pytest_args
    assert shard.junit_file in pytest_args
    assert "tests/test_alpha.py" in pytest_args


def test_build_pytest_args_accepts_nightly_marker_and_diagnostics(tmp_path: Path) -> None:
    shard = runner.TestShard(
        index=2,
        artifact_label="py313",
        files=[runner.TestFile(Path("tests/test_alpha.py"), 10)],
        weight=10,
    )

    pytest_args = runner.build_pytest_args(
        shard,
        tmp_path,
        marker_expression="not demo",
        durations_min="1.0",
        report_chars="fEsxXw",
    )

    assert pytest_args[pytest_args.index("-m") + 1] == "not demo"
    assert "--durations-min=1.0" in pytest_args
    assert pytest_args[pytest_args.index("-r") + 1] == "fEsxXw"
    assert "-p" in pytest_args
    assert "no:xdist" in pytest_args
    assert "-n" not in pytest_args
    assert "--dist" not in pytest_args


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"marker_expression": ""}, "marker expression"),
        ({"marker_expression": "not demo\nor slow"}, "marker expression"),
        ({"durations_min": "-1"}, "durations-min"),
        ({"durations_min": "slow"}, "durations-min"),
        ({"report_chars": ""}, "report-chars"),
        ({"report_chars": "f\nw"}, "report-chars"),
    ],
)
def test_build_pytest_args_rejects_unsafe_cli_values(
    tmp_path: Path,
    kwargs: dict[str, str],
    message: str,
) -> None:
    shard = runner.TestShard(
        index=1,
        artifact_label="py313",
        files=[runner.TestFile(Path("tests/test_alpha.py"), 10)],
        weight=10,
    )

    with pytest.raises(ValueError, match=message):
        runner.build_pytest_args(shard, tmp_path, **kwargs)


def test_build_pytest_args_omits_cov_args_when_pytest_cov_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    shard = runner.TestShard(
        index=1,
        artifact_label="py313",
        files=[runner.TestFile(Path("tests/test_alpha.py"), 10)],
        weight=10,
    )
    monkeypatch.setattr(runner, "pytest_cov_available", lambda: False)

    pytest_args = runner.build_pytest_args(shard, tmp_path)

    assert "--cov=." not in pytest_args
    assert "--cov-report=" not in pytest_args


def test_build_pytest_args_includes_cov_args_when_pytest_cov_is_available(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    shard = runner.TestShard(
        index=1,
        artifact_label="py313",
        files=[runner.TestFile(Path("tests/test_alpha.py"), 10)],
        weight=10,
    )
    monkeypatch.setattr(runner, "pytest_cov_available", lambda: True)

    pytest_args = runner.build_pytest_args(shard, tmp_path)

    assert "--cov=." in pytest_args
    assert "--cov-report=" in pytest_args


def test_build_shard_env_isolates_database_and_coverage(tmp_path: Path) -> None:
    shard = runner.TestShard(index=1, artifact_label="py313")
    env = runner.build_shard_env(
        {"EXISTING": "1", "PYTEST_XDIST_WORKER": "gw0"},
        shard,
        tmp_path,
    )

    assert env["EXISTING"] == "1"
    assert "PYTEST_XDIST_WORKER" not in env
    assert env["MAIN_TEST_SHARD"] == "1"
    assert env["MAIN_TEST_SHARD_LABEL"] == "py313"
    assert env["COVERAGE_FILE"] == str(tmp_path / ".coverage.py313-main-shard-1")
    assert env["COV_CORE_DATAFILE"] == str(tmp_path / ".coverage.py313-main-shard-1")
    assert env["PYTEST_FAULTHANDLER_TIMEOUT_S"] == "300"


def test_build_shard_env_scopes_bayesian_history_when_persisting(tmp_path: Path) -> None:
    shard = runner.TestShard(index=3, artifact_label="py313")
    env = runner.build_shard_env(
        {
            "BAYESIAN_PERSIST": "1",
            "BAYESIAN_HISTORY_PATH": "/tmp/test_execution_history.json",
        },
        shard,
        tmp_path,
    )

    assert env["BAYESIAN_HISTORY_PATH"] == "/tmp/test_execution_history-py313-shard-3.json"


def test_build_shard_env_keeps_parent_scoped_bayesian_history_idempotent(
    tmp_path: Path,
) -> None:
    shard = runner.TestShard(index=3, artifact_label="py313")
    parent_env = runner.build_shard_env(
        {
            "BAYESIAN_PERSIST": "1",
            "BAYESIAN_HISTORY_PATH": "/tmp/test_execution_history.json",
        },
        shard,
        tmp_path,
    )

    child_env = runner.build_shard_env(parent_env, shard, tmp_path)

    assert child_env["BAYESIAN_HISTORY_PATH"] == "/tmp/test_execution_history-py313-shard-3.json"


def test_build_shard_env_leaves_bayesian_history_alone_when_not_persisting(tmp_path: Path) -> None:
    shard = runner.TestShard(index=3, artifact_label="py313")
    env = runner.build_shard_env(
        {"BAYESIAN_HISTORY_PATH": "/tmp/test_execution_history.json"},
        shard,
        tmp_path,
    )

    assert env["BAYESIAN_HISTORY_PATH"] == "/tmp/test_execution_history.json"


def test_shard_timeout_seconds_validates_env(capsys: pytest.CaptureFixture[str]) -> None:
    assert runner.shard_timeout_seconds({}) == runner.DEFAULT_SHARD_TIMEOUT_SECONDS
    assert runner.shard_timeout_seconds({"MAIN_TEST_SHARD_TIMEOUT_SECONDS": "120"}) == 120
    assert runner.shard_timeout_seconds({"MAIN_TEST_SHARD_TIMEOUT_SECONDS": "bad"}) == (
        runner.DEFAULT_SHARD_TIMEOUT_SECONDS
    )
    assert "MAIN_TEST_SHARD_TIMEOUT_INVALID" in capsys.readouterr().err
    assert runner.shard_timeout_seconds({"MAIN_TEST_SHARD_TIMEOUT_SECONDS": "10"}) == (
        runner.DEFAULT_SHARD_TIMEOUT_SECONDS
    )
    assert "MAIN_TEST_SHARD_TIMEOUT_TOO_LOW" in capsys.readouterr().err


def test_run_shard_invokes_explicit_child_interpreter(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    shard = runner.TestShard(
        index=3,
        artifact_label="py313",
        files=[runner.TestFile(Path("tests/test_alpha.py"), 10)],
        weight=10,
    )
    captured: dict[str, object] = {}

    class FakeProcess:
        pid = 999_999

        def poll(self) -> int:
            return 5

        def wait(self, *, timeout: int) -> int:
            captured["timeout"] = timeout
            return 5

    def fake_popen(
        command: list[str],
        *,
        cwd: Path,
        env: dict[str, str],
        start_new_session: bool,
    ) -> FakeProcess:
        captured["command"] = command
        captured["cwd"] = cwd
        captured["env"] = env
        captured["start_new_session"] = start_new_session
        return FakeProcess()

    monkeypatch.setattr(subprocess, "Popen", fake_popen)

    assert (
        runner.run_shard(
            tmp_path,
            shard,
            {
                "BAYESIAN_PERSIST": "1",
                "BAYESIAN_HISTORY_PATH": "/tmp/test_execution_history.json",
                "PYTEST_XDIST_WORKER": "gw0",
            },
        )
        == 5
    )

    command = captured["command"]
    assert isinstance(command, list)
    assert command[:2] == [sys.executable, str(Path(runner.__file__).resolve())]
    assert "--run-shard-index" in command
    assert command[command.index("--run-shard-index") + 1] == "3"
    assert "--shard-file" in command
    assert command[command.index("--shard-file") + 1] == "tests/test_alpha.py"
    assert captured["cwd"] == tmp_path
    assert captured["timeout"] == runner.DEFAULT_SHARD_TIMEOUT_SECONDS
    assert captured["start_new_session"] == (os.name == "posix")
    env = captured["env"]
    assert isinstance(env, dict)
    assert "PYTEST_XDIST_WORKER" not in env
    assert env["MAIN_TEST_SHARD"] == "3"
    assert env["COVERAGE_FILE"] == str(tmp_path / ".coverage.py313-main-shard-3")
    assert env["BAYESIAN_HISTORY_PATH"] == "/tmp/test_execution_history-py313-shard-3.json"


def test_run_shard_fails_timeout_even_with_clean_artifacts(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    shard = runner.TestShard(
        index=4,
        artifact_label="py312",
        files=[runner.TestFile(Path("tests/test_alpha.py"), 10)],
        weight=10,
    )
    junit_path = tmp_path / shard.junit_file
    junit_path.parent.mkdir(parents=True, exist_ok=True)
    junit_path.write_text(
        '<testsuite tests="2" failures="0" errors="0" skipped="0"></testsuite>',
        encoding="utf-8",
    )
    (tmp_path / shard.coverage_file).write_text("coverage", encoding="utf-8")

    class FakeTimeoutProcess:
        pid = 999_999

        def poll(self) -> None:
            return None

        def wait(self, *, timeout: int) -> int:
            raise subprocess.TimeoutExpired(cmd=["pytest"], timeout=timeout)

    def fake_popen(*args: object, **kwargs: object) -> FakeTimeoutProcess:
        return FakeTimeoutProcess()

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    monkeypatch.setattr(runner, "_terminate_process_group", lambda process: None)

    assert runner.run_shard(tmp_path, shard, {}) == 124
    stderr = capsys.readouterr().err
    assert "MAIN_TEST_SHARD_TIMEOUT_FAILED" in stderr
    assert "MAIN_TEST_SHARD_TIMEOUT_FILE label=py312 index=4 path=tests/test_alpha.py" in stderr


def test_run_shard_fails_timeout_without_clean_artifacts(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    shard = runner.TestShard(
        index=4,
        artifact_label="py312",
        files=[runner.TestFile(Path("tests/test_alpha.py"), 10)],
        weight=10,
    )

    class FakeTimeoutProcess:
        pid = 999_999

        def poll(self) -> None:
            return None

        def wait(self, *, timeout: int) -> int:
            raise subprocess.TimeoutExpired(cmd=["pytest"], timeout=timeout)

    def fake_popen(*args: object, **kwargs: object) -> FakeTimeoutProcess:
        return FakeTimeoutProcess()

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    monkeypatch.setattr(runner, "_terminate_process_group", lambda process: None)

    assert runner.run_shard(tmp_path, shard, {}) == 124
    assert "MAIN_TEST_SHARD_TIMEOUT_FAILED" in capsys.readouterr().err


def test_run_shard_child_forces_exit_after_pytest_returns(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    shard = runner.TestShard(
        index=1,
        artifact_label="py312",
        files=[runner.TestFile(Path("tests/test_alpha.py"), 10)],
        weight=10,
    )
    original_cwd = Path.cwd()
    captured: dict[str, object] = {}

    def fake_pytest_main(pytest_args: list[str]) -> int:
        captured["pytest_args"] = pytest_args
        captured["cwd"] = Path.cwd()
        captured["argv"] = list(sys.argv)
        return 7

    def fake_exit(exit_code: int) -> None:
        raise SystemExit(exit_code)

    monkeypatch.setattr(pytest, "main", fake_pytest_main)
    monkeypatch.setattr(runner.os, "_exit", fake_exit)

    basetemp = runner.shard_basetemp_dir(tmp_path, shard)
    try:
        with pytest.raises(SystemExit) as exc_info:
            runner.run_shard_child(tmp_path, shard, {})

        assert exc_info.value.code == 7
        assert captured["cwd"] == tmp_path
        assert captured["argv"] == ["pytest"]
        pytest_args = captured["pytest_args"]
        assert isinstance(pytest_args, list)
        assert "--basetemp" in pytest_args
        assert pytest_args[pytest_args.index("--basetemp") + 1] == str(basetemp)
        assert basetemp.parent.is_dir()
        assert "tests/test_alpha.py" in pytest_args
    finally:
        os.chdir(original_cwd)
        shutil.rmtree(basetemp.parent, ignore_errors=True)

    assert not basetemp.parent.exists()


def test_remove_previous_outputs_deletes_stale_shard_files(tmp_path: Path) -> None:
    shard = runner.TestShard(index=1, artifact_label="py312")
    coverage_file = tmp_path / shard.coverage_file
    junit_file = tmp_path / shard.junit_file
    htmlcov_file = tmp_path / "htmlcov" / "index.html"
    coverage_file.write_text("old", encoding="utf-8")
    junit_file.parent.mkdir(parents=True, exist_ok=True)
    junit_file.write_text("old", encoding="utf-8")
    htmlcov_file.parent.mkdir(parents=True, exist_ok=True)
    htmlcov_file.write_text("<html></html>", encoding="utf-8")

    runner.remove_previous_outputs(tmp_path, [shard])

    assert not coverage_file.exists()
    assert not junit_file.exists()
    assert not htmlcov_file.parent.exists()


def test_run_all_shards_rejects_invalid_parallelism(tmp_path: Path) -> None:
    shard = runner.TestShard(index=1)

    with pytest.raises(ValueError, match="max_parallel"):
        runner.run_all_shards(tmp_path, [shard], 0, {})

    with pytest.raises(ValueError, match="at least one shard"):
        runner.run_all_shards(tmp_path, [], 1, {})


def test_run_all_shards_stops_refilling_after_first_failure(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Fail-closed shards should surface promptly instead of scheduling all pending work."""

    shards = [
        runner.TestShard(index=1, files=[runner.TestFile(Path("tests/test_1.py"), 1)]),
        runner.TestShard(index=2, files=[runner.TestFile(Path("tests/test_2.py"), 1)]),
        runner.TestShard(index=3, files=[runner.TestFile(Path("tests/test_3.py"), 1)]),
        runner.TestShard(index=4, files=[runner.TestFile(Path("tests/test_4.py"), 1)]),
    ]
    submitted: list[int] = []
    shutdown_calls: list[tuple[bool, bool]] = []

    class FakeExecutor:
        _processes: dict[int, object] = {}

        def __init__(self, **kwargs: object) -> None:
            del kwargs

        def shutdown(self, *, wait: bool, cancel_futures: bool = False) -> None:
            shutdown_calls.append((wait, cancel_futures))

        def submit(
            self,
            func: object,
            repo_root: Path,
            shard: runner.TestShard,
            base_env: dict[str, str],
            *args: object,
        ) -> Future[int]:
            del func, repo_root, base_env, args
            submitted.append(shard.index)
            future: Future[int] = Future()
            if shard.index == 1:
                future.set_result(124)
            return future

    def fake_wait(
        futures: set[Future[int]] | dict[Future[int], int],
        *,
        return_when: object,
    ) -> tuple[set[Future[int]], set[Future[int]]]:
        assert return_when is runner.concurrent.futures.FIRST_COMPLETED
        first = next(iter(futures))
        remaining = set(futures) - {first}
        return {first}, remaining

    monkeypatch.setattr(runner.concurrent.futures, "ProcessPoolExecutor", FakeExecutor)
    monkeypatch.setattr(runner.concurrent.futures, "wait", fake_wait)
    monkeypatch.setattr(
        runner,
        "run_coverage_command",
        lambda *args, **kwargs: pytest.fail("coverage must not run after shard failure"),
    )

    assert runner.run_all_shards(tmp_path, shards, 2, {}) == 1
    assert submitted == [1, 2]
    assert shutdown_calls == [(False, True)]
    stderr = capsys.readouterr().err
    assert "MAIN_TEST_SHARD_CANCELLED index=2 reason=fail_fast" in stderr
    assert "MAIN_TEST_SHARDS_FAILED shards=[1]" in stderr


def test_run_all_shards_max_parallel_one_uses_child_process_isolation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    first_test_path = _write_test_file(
        tmp_path,
        "tests/test_child_process_isolation_first.py",
        "\n".join(
            [
                "import os",
                "import sys",
                "from pathlib import Path",
                "",
                "def test_mutates_process_state():",
                "    os.environ['MAIN_PARENT_LEAK_PROBE'] = 'child-only'",
                "    os.chdir(Path.cwd() / 'tests')",
                "    assert 'PYTEST_XDIST_WORKER' not in os.environ",
                "    assert os.environ['MAIN_TEST_SHARD'] == '1'",
                "    assert os.environ['MAIN_TEST_SHARD_LABEL'] == 'py313'",
                "    assert sys.argv == ['pytest']",
                "",
            ]
        ),
    )
    second_test_path = _write_test_file(
        tmp_path,
        "tests/test_child_process_isolation_second.py",
        "\n".join(
            [
                "import os",
                "",
                "def test_does_not_see_previous_shard_state():",
                "    assert os.environ.get('MAIN_PARENT_LEAK_PROBE') is None",
                "    assert 'PYTEST_XDIST_WORKER' not in os.environ",
                "    assert os.environ['MAIN_TEST_SHARD'] == '2'",
                "    assert os.environ['MAIN_TEST_SHARD_LABEL'] == 'py313'",
                "",
            ]
        ),
    )
    (tmp_path / "pyproject.toml").write_text("[tool.pytest.ini_options]\n", encoding="utf-8")
    first_shard = runner.TestShard(
        index=1,
        artifact_label="py313",
        files=[runner.TestFile(first_test_path.relative_to(tmp_path), 1)],
        weight=1,
    )
    second_shard = runner.TestShard(
        index=2,
        artifact_label="py313",
        files=[runner.TestFile(second_test_path.relative_to(tmp_path), 1)],
        weight=1,
    )
    original_cwd = Path.cwd()
    original_probe = os.environ.get("MAIN_PARENT_LEAK_PROBE")
    original_worker = os.environ.get("PYTEST_XDIST_WORKER")
    base_env = {
        key: value
        for key, value in os.environ.items()
        if key not in {"MAIN_PARENT_LEAK_PROBE", "PYTEST_XDIST_WORKER"}
    }
    coverage_calls: list[list[str]] = []

    def fake_coverage(repo_root: Path, args: list[str]) -> int:
        assert repo_root == tmp_path
        coverage_calls.append(list(args))
        return 0

    monkeypatch.setattr(runner, "run_coverage_command", fake_coverage)

    assert runner.run_all_shards(tmp_path, [first_shard, second_shard], 1, base_env) == 0
    assert Path.cwd() == original_cwd
    assert os.environ.get("MAIN_PARENT_LEAK_PROBE") == original_probe
    assert os.environ.get("PYTEST_XDIST_WORKER") == original_worker
    assert coverage_calls == [
        ["combine", ".coverage.py313-main-shard-1", ".coverage.py313-main-shard-2"],
        ["xml"],
        ["report", "-m", "--fail-under=97"],
    ]


def test_run_all_shards_combines_serial_coverage_before_parallel_shards(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    shard = runner.TestShard(
        index=1,
        artifact_label="py311",
        files=[runner.TestFile(Path("tests/test_alpha.py"), 1)],
        weight=1,
    )
    coverage_calls: list[list[str]] = []
    submitted: list[int] = []

    class FakeExecutor:
        def __init__(self, **kwargs: object) -> None:
            del kwargs

        def shutdown(self, *, wait: bool, cancel_futures: bool = False) -> None:
            assert wait is True
            assert cancel_futures is False

        def submit(
            self,
            func: object,
            repo_root: Path,
            submitted_shard: runner.TestShard,
            base_env: dict[str, str],
            *args: object,
        ) -> Future[int]:
            del func, args
            assert repo_root == tmp_path
            assert base_env == {}
            submitted.append(submitted_shard.index)
            future: Future[int] = Future()
            future.set_result(0)
            return future

    def fake_wait(
        futures: set[Future[int]] | dict[Future[int], int],
        *,
        return_when: object,
    ) -> tuple[set[Future[int]], set[Future[int]]]:
        assert return_when is runner.concurrent.futures.FIRST_COMPLETED
        return set(futures), set()

    def fake_coverage(repo_root: Path, args: list[str]) -> int:
        assert repo_root == tmp_path
        coverage_calls.append(list(args))
        return 0

    monkeypatch.setattr(runner.concurrent.futures, "ProcessPoolExecutor", FakeExecutor)
    monkeypatch.setattr(runner.concurrent.futures, "wait", fake_wait)
    monkeypatch.setattr(runner, "run_coverage_command", fake_coverage)

    assert (
        runner.run_all_shards(
            tmp_path,
            [shard],
            1,
            {},
            extra_coverage_files=[".coverage.py311-main-shard-0"],
        )
        == 0
    )
    assert submitted == [1]
    assert coverage_calls == [
        ["combine", ".coverage.py311-main-shard-0", ".coverage.py311-main-shard-1"],
        ["xml"],
        ["report", "-m", "--fail-under=97"],
    ]


def test_run_all_shards_generates_htmlcov_when_requested(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    shard = runner.TestShard(
        index=1,
        artifact_label="py313",
        files=[runner.TestFile(Path("tests/test_alpha.py"), 1)],
        weight=1,
    )
    coverage_calls: list[list[str]] = []

    class FakeExecutor:
        def __init__(self, **kwargs: object) -> None:
            del kwargs

        def shutdown(self, *, wait: bool, cancel_futures: bool = False) -> None:
            assert wait is True
            assert cancel_futures is False

        def submit(
            self,
            func: object,
            repo_root: Path,
            submitted_shard: runner.TestShard,
            base_env: dict[str, str],
            *args: object,
        ) -> Future[int]:
            del func, repo_root, submitted_shard, base_env, args
            future: Future[int] = Future()
            future.set_result(0)
            return future

    def fake_wait(
        futures: set[Future[int]] | dict[Future[int], int],
        *,
        return_when: object,
    ) -> tuple[set[Future[int]], set[Future[int]]]:
        assert return_when is runner.concurrent.futures.FIRST_COMPLETED
        return set(futures), set()

    def fake_coverage(repo_root: Path, args: list[str]) -> int:
        assert repo_root == tmp_path
        coverage_calls.append(list(args))
        return 0

    monkeypatch.setattr(runner.concurrent.futures, "ProcessPoolExecutor", FakeExecutor)
    monkeypatch.setattr(runner.concurrent.futures, "wait", fake_wait)
    monkeypatch.setattr(runner, "run_coverage_command", fake_coverage)

    assert runner.run_all_shards(tmp_path, [shard], 1, {}, htmlcov=True) == 0
    assert coverage_calls == [
        ["combine", ".coverage.py313-main-shard-1"],
        ["xml"],
        ["html"],
        ["report", "-m", "--fail-under=97"],
    ]


def test_run_serial_shards_stops_before_parallel_phase_on_failure(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    serial_shard = runner.TestShard(
        index=0,
        artifact_label="py311",
        files=[runner.TestFile(Path("tests/test_design_token_parity.py"), 1)],
        weight=1,
    )

    monkeypatch.setattr(runner, "run_shard", lambda *args, **kwargs: 5)

    assert runner.run_serial_shards(tmp_path, [serial_shard], {}) == 5
    assert (
        "MAIN_TEST_SERIAL_SHARD_FAILED label=py311 index=0 exit_code=5" in capsys.readouterr().err
    )


def test_main_stops_before_parallel_shards_when_serial_tests_fail(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _write_test_file(tmp_path, "tests/test_alpha.py", "def test_alpha(): pass\n")
    _write_test_file(
        tmp_path,
        "tests/test_design_token_parity.py",
        "def test_design_token_parity(): pass\n",
    )
    captured_serial: dict[str, object] = {}

    def fake_run_serial(
        repo_root: Path,
        serial_shards: list[runner.TestShard],
        base_env: dict[str, str],
        *args: object,
    ) -> int:
        del base_env, args
        captured_serial["repo_root"] = repo_root
        captured_serial["serial_paths"] = [
            test_file.path.as_posix()
            for serial_shard in serial_shards
            for test_file in serial_shard.files
        ]
        return 5

    monkeypatch.setattr(runner, "run_serial_shards", fake_run_serial)
    monkeypatch.setattr(
        runner,
        "run_all_shards",
        lambda *args, **kwargs: pytest.fail("parallel shards must not run"),
    )

    assert (
        runner.main(
            [
                "--repo-root",
                str(tmp_path),
                "--python-version",
                "3.11",
                "--shard-count",
                "2",
            ]
        )
        == 5
    )
    assert captured_serial == {
        "repo_root": tmp_path.resolve(),
        "serial_paths": ["tests/test_design_token_parity.py"],
    }


def test_main_passes_serial_coverage_into_parallel_combine(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _write_test_file(tmp_path, "tests/test_alpha.py", "def test_alpha(): pass\n")
    _write_test_file(
        tmp_path,
        "tests/test_design_token_parity.py",
        "def test_design_token_parity(): pass\n",
    )
    captured: dict[str, object] = {}

    def fake_run_serial(
        repo_root: Path,
        serial_shards: list[runner.TestShard],
        base_env: dict[str, str],
        *args: object,
    ) -> int:
        del base_env, args
        captured["serial_repo_root"] = repo_root
        captured["serial_coverage"] = [serial_shard.coverage_file for serial_shard in serial_shards]
        return 0

    def fake_run_all(
        repo_root: Path,
        shards: list[runner.TestShard],
        max_parallel: int,
        base_env: dict[str, str],
        extra_coverage_files: list[str],
        *args: object,
        **kwargs: object,
    ) -> int:
        del base_env, args, kwargs
        captured["parallel_repo_root"] = repo_root
        captured["parallel_paths"] = [
            test_file.path.as_posix() for shard in shards for test_file in shard.files
        ]
        captured["max_parallel"] = max_parallel
        captured["extra_coverage_files"] = extra_coverage_files
        return 0

    monkeypatch.setattr(runner, "run_serial_shards", fake_run_serial)
    monkeypatch.setattr(runner, "run_all_shards", fake_run_all)

    assert (
        runner.main(
            [
                "--repo-root",
                str(tmp_path),
                "--python-version",
                "3.11",
                "--shard-count",
                "2",
                "--max-parallel",
                "1",
            ]
        )
        == 0
    )
    assert captured == {
        "serial_repo_root": tmp_path.resolve(),
        "serial_coverage": [".coverage.py311-main-shard-0"],
        "parallel_repo_root": tmp_path.resolve(),
        "parallel_paths": ["tests/test_alpha.py"],
        "max_parallel": 1,
        "extra_coverage_files": [".coverage.py311-main-shard-0"],
    }


def test_collect_shard_results_reports_worker_exceptions(
    capsys: pytest.CaptureFixture[str],
) -> None:
    success: Future[int] = Future()
    failure: Future[int] = Future()
    success.set_result(0)
    failure.set_exception(RuntimeError("native crash"))

    results = runner.collect_shard_results({success: 1, failure: 2})

    assert results == {1: 0, 2: 1}
    assert "MAIN_TEST_SHARD_EXCEPTION index=2 type=RuntimeError message=native crash" in (
        capsys.readouterr().err
    )


def test_collect_shard_results_propagates_termination_signals() -> None:
    interrupted: Future[int] = Future()
    interrupted.set_exception(KeyboardInterrupt())

    with pytest.raises(KeyboardInterrupt):
        runner.collect_shard_results({interrupted: 1})


@pytest.mark.parametrize(
    ("phase", "coverage_calls", "expected_status"),
    [
        ("combine", [(["combine", ".coverage.py313-main-shard-1"], 2)], 2),
        (
            "xml",
            [
                (["combine", ".coverage.py313-main-shard-1"], 0),
                (["xml"], 3),
            ],
            3,
        ),
        (
            "report",
            [
                (["combine", ".coverage.py313-main-shard-1"], 0),
                (["xml"], 0),
                (["report", "-m", "--fail-under=97"], 4),
            ],
            4,
        ),
        (
            "html",
            [
                (["combine", ".coverage.py313-main-shard-1"], 0),
                (["xml"], 0),
                (["html"], 6),
            ],
            6,
        ),
    ],
)
def test_run_all_shards_logs_coverage_phase_failures(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    phase: str,
    coverage_calls: list[tuple[list[str], int]],
    expected_status: int,
) -> None:
    test_path = _write_test_file(tmp_path, "tests/test_alpha.py", "def test_alpha(): pass\n")
    (tmp_path / "pyproject.toml").write_text("[tool.pytest.ini_options]\n", encoding="utf-8")
    shard = runner.TestShard(
        index=1,
        artifact_label="py313",
        files=[runner.TestFile(test_path.relative_to(tmp_path), 1)],
        weight=1,
    )

    pending_calls = list(coverage_calls)

    def fake_coverage(repo_root: Path, args: list[str]) -> int:
        assert repo_root == tmp_path
        expected_args, status = pending_calls.pop(0)
        assert args == expected_args
        return status

    monkeypatch.setattr(runner, "run_coverage_command", fake_coverage)

    assert (
        runner.run_all_shards(
            tmp_path,
            [shard],
            1,
            {},
            htmlcov=(phase == "html"),
        )
        == expected_status
    )
    assert pending_calls == []
    assert f"MAIN_TEST_COVERAGE_{phase.upper()}_FAILED exit_code={expected_status}" in (
        capsys.readouterr().err
    )


def test_run_coverage_command_uses_coverage_api(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}
    monkeypatch.setenv("COVERAGE_FILE", "outside-coverage")
    monkeypatch.setenv("COV_CORE_DATAFILE", "outside-cov-core")

    def fake_main(args: list[str]) -> int:
        captured["args"] = args
        captured["cwd"] = Path.cwd()
        captured["coverage_file"] = os.environ.get("COVERAGE_FILE")
        captured["cov_core_datafile"] = os.environ.get("COV_CORE_DATAFILE")
        return 0

    assert runner.run_coverage_command(tmp_path, ["xml"], coverage_main=fake_main) == 0
    assert captured == {
        "args": ["xml"],
        "cwd": tmp_path,
        "coverage_file": None,
        "cov_core_datafile": None,
    }
    assert os.environ["COVERAGE_FILE"] == "outside-coverage"
    assert os.environ["COV_CORE_DATAFILE"] == "outside-cov-core"
