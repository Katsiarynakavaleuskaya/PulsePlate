"""Regression tests for the Python 3.12 main-suite shard runner."""

from __future__ import annotations

import os
from pathlib import Path

import coverage.cmdline
import pytest

from scripts.ci import run_py312_main_shards as runner


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


def test_partition_test_files_rejects_invalid_input() -> None:
    with pytest.raises(ValueError, match="shard_count"):
        runner.partition_test_files([runner.TestFile(Path("tests/test_alpha.py"), 1)], 0)

    with pytest.raises(ValueError, match="no pytest files"):
        runner.partition_test_files([], 1)


def test_build_pytest_args_disables_xdist_and_emits_junit() -> None:
    shard = runner.TestShard(
        index=2,
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
    shard = runner.TestShard(index=1)
    env = runner.build_shard_env({"EXISTING": "1"}, shard, tmp_path)

    assert env["EXISTING"] == "1"
    assert env["PYTEST_XDIST_WORKER"] == "py312main1"
    assert env["COVERAGE_FILE"] == str(tmp_path / ".coverage.py312-main-shard-1")
    assert env["COV_CORE_DATAFILE"] == str(tmp_path / ".coverage.py312-main-shard-1")
    assert env["PYTEST_FAULTHANDLER_TIMEOUT_S"] == "300"


def test_remove_previous_outputs_deletes_stale_shard_files(tmp_path: Path) -> None:
    shard = runner.TestShard(index=1)
    coverage_file = tmp_path / shard.coverage_file
    junit_file = tmp_path / shard.junit_file
    coverage_file.write_text("old", encoding="utf-8")
    junit_file.parent.mkdir(parents=True, exist_ok=True)
    junit_file.write_text("old", encoding="utf-8")

    runner.remove_previous_outputs(tmp_path, [shard])

    assert not coverage_file.exists()
    assert not junit_file.exists()


def test_run_all_shards_returns_failure_without_coverage_combine(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    shard = runner.TestShard(index=1)
    calls: list[str] = []

    def fake_run_shard(
        repo_root: Path,
        test_shard: runner.TestShard,
        base_env: dict[str, str],
    ) -> int:
        calls.append(f"shard:{test_shard.index}:{repo_root == tmp_path}:{bool(base_env)}")
        return 5

    def fake_coverage(repo_root: Path, args: list[str]) -> int:
        calls.append(f"coverage:{args}")
        return 0

    monkeypatch.setattr(runner, "run_shard", fake_run_shard)
    monkeypatch.setattr(runner, "run_coverage_command", fake_coverage)

    assert runner.run_all_shards(tmp_path, [shard], 1, os.environ.copy()) == 1
    assert calls == ["shard:1:True:True"]


def test_run_all_shards_combines_coverage_after_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    shard = runner.TestShard(index=1)
    coverage_calls: list[list[str]] = []

    monkeypatch.setattr(
        runner,
        "run_shard",
        lambda repo_root, test_shard, base_env: 0,
    )

    def fake_coverage(repo_root: Path, args: list[str]) -> int:
        coverage_calls.append(list(args))
        return 0

    monkeypatch.setattr(runner, "run_coverage_command", fake_coverage)

    assert runner.run_all_shards(tmp_path, [shard], 1, os.environ.copy()) == 0
    assert coverage_calls == [
        ["combine", ".coverage.py312-main-shard-1"],
        ["xml"],
        ["report", "-m", "--fail-under=97"],
    ]


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
