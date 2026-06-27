"""Compatibility tests for verify_requirements.py."""

from __future__ import annotations

import pytest

import verify_requirements


def test_verify_requirements_delegates_to_dependency_surface_validator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed_argv: list[str] | None = None

    def fake_validator(argv: list[str] | None = None) -> int:
        nonlocal observed_argv
        observed_argv = argv
        return 23

    monkeypatch.setattr(verify_requirements, "check_python_dependency_surfaces", fake_validator)

    assert verify_requirements.main(["--repo-root", "/tmp/example"]) == 23
    assert observed_argv == ["--repo-root", "/tmp/example"]
