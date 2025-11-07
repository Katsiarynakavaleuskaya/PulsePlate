from dataclasses import dataclass
from typing import Any, Dict

import pytest


def test_run_tests_fast_success(monkeypatch: pytest.MonkeyPatch) -> None:
    # Import inside to ensure test discovery works even if path changes
    from scripts import run_tests_bayesian as runner

    @dataclass
    class DummyCompleted:
        returncode: int = 0
        stdout: str = "OK\n"
        stderr: str = ""

    def fake_run(*args: Any, **kwargs: Any) -> DummyCompleted:
        return DummyCompleted()

    monkeypatch.setattr("subprocess.run", fake_run)

    result: Dict[str, Any] = runner.run_tests_fast()
    assert result["success"] is True
    assert result["returncode"] == 0
    assert isinstance(result.get("output"), str)
