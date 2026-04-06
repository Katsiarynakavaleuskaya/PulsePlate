"""Tests for `scripts.metatron_lab` compose validation helpers."""

from __future__ import annotations

import subprocess

import pytest

from scripts.metatron_lab.compose_guard import (
    LAB_PROFILES,
    compose_file_for_repo,
    operator_checklist_lines,
    repo_root,
    run_compose_config_q,
    validate_all_profiles,
)


def test_operator_checklist_includes_adr_and_roe() -> None:
    text = "\n".join(operator_checklist_lines())
    assert "ADR_METATRON" in text
    assert "METATRON_LAB_RULES_OF_ENGAGEMENT" in text
    assert "artifacts/security_lab" in text


def test_lab_profiles_tuple() -> None:
    assert LAB_PROFILES == ("metatron-lab-isolation", "metatron-lab-runner")


def test_compose_file_exists() -> None:
    root = repo_root()
    path = compose_file_for_repo(root)
    assert path.is_file()


def test_validate_all_profiles_missing_docker(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("scripts.metatron_lab.compose_guard.shutil.which", lambda _name: None)
    assert validate_all_profiles() == 2


def test_validate_all_profiles_success(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def _which(name: str) -> str | None:
        return "/opt/bin/docker" if name == "docker" else None

    def _run(
        cmd: list[str] | tuple[str, ...],
        **_kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        calls.append(list(cmd))
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("scripts.metatron_lab.compose_guard.shutil.which", _which)
    monkeypatch.setattr("scripts.metatron_lab.compose_guard.subprocess.run", _run)

    assert validate_all_profiles() == 0
    assert len(calls) == len(LAB_PROFILES)
    for i, profile in enumerate(LAB_PROFILES):
        assert calls[i][0] == "/opt/bin/docker"
        assert calls[i][1] == "compose"
        assert profile in calls[i]


def test_run_compose_config_q_invokes_docker_binary(monkeypatch: pytest.MonkeyPatch) -> None:
    recorded: dict[str, object] = {}

    def _run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        recorded["args"] = args
        recorded["kwargs"] = kwargs
        return subprocess.CompletedProcess(args=(), returncode=0, stdout="", stderr="")

    monkeypatch.setattr("scripts.metatron_lab.compose_guard.subprocess.run", _run)
    root = repo_root()
    run_compose_config_q(root, "metatron-lab-isolation", "/usr/bin/docker")
    cmd = recorded["args"]
    assert isinstance(cmd, tuple) and len(cmd) == 1
    inner = cmd[0]
    assert isinstance(inner, list)
    assert inner[0] == "/usr/bin/docker"
    assert inner[1] == "compose"
