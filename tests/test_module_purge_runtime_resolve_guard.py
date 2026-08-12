from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_runtime_resolve_after_purge_returns_new_module_object() -> None:
    """RU: Guard против stale module refs после purge/reload под xdist.
    EN: Guard against stale module refs after purge/reload under xdist.

    Если кто-то снова начнёт держать ссылку на legacy_app, а потом вызывать purge,
    последующие monkeypatch/setattr могут патчить stale объект. Этот тест гарантирует,
    что runtime-resolve действительно возвращает новый объект модуля после purge.
    """
    scenario = textwrap.dedent("""\
        from module_purge import purge_modules
        from tests.helpers.module_resolve import resolve_legacy_app

        legacy_before = resolve_legacy_app()
        purge_modules(prefixes=("legacy_app",))
        legacy_after = resolve_legacy_app()

        assert legacy_after.__name__ == "legacy_app"
        assert legacy_after is not legacy_before
        """)
    result = subprocess.run(
        [sys.executable, "-c", scenario],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
