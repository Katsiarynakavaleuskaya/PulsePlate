from typing import Any, Dict
import subprocess

import pytest


def test_run_tests_fast_success(monkeypatch: pytest.MonkeyPatch) -> None:
    # Import inside to ensure test discovery works even if path changes
    from scripts import run_tests_bayesian as runner

    def fake_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        # Use subprocess.CompletedProcess directly instead of Mock
        return subprocess.CompletedProcess(
            args=args[0] if args else [],
            returncode=0,
            stdout="OK\n",
            stderr="",
        )

    monkeypatch.setattr("subprocess.run", fake_run)

    result: Dict[str, Any] = runner.run_tests_fast()
    assert result["success"] is True
    assert result["returncode"] == 0
    assert isinstance(result.get("output"), str)
