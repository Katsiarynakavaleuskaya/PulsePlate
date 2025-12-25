import sys

from module_purge import purge_modules


def test_purge_modules_respects_exclusions_and_removes_only_targets() -> None:
    # Import real modules to avoid mutating sys.modules directly in this test.
    import legacy_app  # noqa: F401
    import app.main  # noqa: F401
    import app.models  # noqa: F401
    import core.db  # noqa: F401

    purge_modules(prefixes=("legacy_app", "app.main"))

    assert "legacy_app" not in sys.modules
    assert "app.main" not in sys.modules

    # protected by default excludes inside module_purge
    assert "app.models" in sys.modules
    assert "core.db" in sys.modules

    # Restore baseline for subsequent tests.
    import legacy_app as _legacy_app  # noqa: F401
    import app.main as _app_main  # noqa: F401


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
