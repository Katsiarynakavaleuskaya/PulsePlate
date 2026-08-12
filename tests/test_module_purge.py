import subprocess
import sys
import textwrap
from pathlib import Path

from module_purge import purge_modules

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_purge_modules_respects_exclusions_and_removes_only_targets() -> None:
    scenario = textwrap.dedent("""\
        import sys

        from module_purge import purge_modules

        import legacy_app
        import app.main
        import app.models
        import core.db

        purge_modules(prefixes=("legacy_app", "app.main"))

        assert "legacy_app" not in sys.modules
        assert "app.main" not in sys.modules
        assert "app.models" in sys.modules
        assert "core.db" in sys.modules

        import legacy_app
        import app.main
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


def test_purge_modules_noop_on_empty_prefixes() -> None:
    original_modules = dict(sys.modules)

    # Empty prefixes should be filtered out and result in a no-op.
    purge_modules(prefixes=("",))
    purge_modules(prefixes=())
    assert sys.modules == original_modules


def test_purge_modules_never_removes_default_excludes() -> None:
    import app.models  # noqa: F401
    import core.db  # noqa: F401

    # These match prefixes, but must be protected by default excludes.
    purge_modules(prefixes=("app.models", "core.db"))
    assert "app.models" in sys.modules
    assert "core.db" in sys.modules
