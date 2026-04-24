"""Regression tests for the main-suite shard runner."""

from __future__ import annotations

import os
from concurrent.futures import Future
from pathlib import Path

import coverage.cmdline
import pytest

from scripts.ci import run_main_test_shards as runner
from scripts.ci import run_py312_main_shards as py312_wrapper


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


def test_build_pytest_args_disables_xdist_and_emits_junit() -> None:
    shard = runner.TestShard(
        index=2,
        artifact_label="py313",
        files=[runner.TestFile(Path("tests/test_alpha.py"), 10)],
        weight=10,
    )

    pytest_args = runner.build_pytest_args(shard)

    assert pytest_args[:2] == ["-c", "pyproject.toml"]
    assert "-p" in pytest_args
    assert "no:xdist" in pytest_args
    assert "-m" in pytest_args
    assert runner.SLOW_MARK_EXPRESSION in pytest_args
    assert f"junit_family={runner.JUNIT_FAMILY}" in pytest_args
    assert shard.junit_file in pytest_args
    assert "tests/test_alpha.py" in pytest_args


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


def test_remove_previous_outputs_deletes_stale_shard_files(tmp_path: Path) -> None:
    shard = runner.TestShard(index=1, artifact_label="py312")
    coverage_file = tmp_path / shard.coverage_file
    junit_file = tmp_path / shard.junit_file
    coverage_file.write_text("old", encoding="utf-8")
    junit_file.parent.mkdir(parents=True, exist_ok=True)
    junit_file.write_text("old", encoding="utf-8")

    runner.remove_previous_outputs(tmp_path, [shard])

    assert not coverage_file.exists()
    assert not junit_file.exists()


def test_run_all_shards_rejects_invalid_parallelism(tmp_path: Path) -> None:
    shard = runner.TestShard(index=1)

    with pytest.raises(ValueError, match="max_parallel"):
        runner.run_all_shards(tmp_path, [shard], 0, {})

    with pytest.raises(ValueError, match="at least one shard"):
        runner.run_all_shards(tmp_path, [], 1, {})


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

    assert runner.run_all_shards(tmp_path, [shard], 1, {}) == expected_status
    assert pending_calls == []
    assert f"MAIN_TEST_COVERAGE_{phase.upper()}_FAILED exit_code={expected_status}" in (
        capsys.readouterr().err
    )


def test_run_coverage_command_uses_coverage_api(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}

    def fake_main(args: list[str]) -> int:
        captured["args"] = args
        captured["cwd"] = Path.cwd()
        return 0

    monkeypatch.setattr(coverage.cmdline, "main", fake_main)

    assert runner.run_coverage_command(tmp_path, ["xml"]) == 0
    assert captured == {
        "args": ["xml"],
        "cwd": tmp_path,
    }
