"""Import hygiene guard: ensure a single Base instance across all models.

This test catches dual-Base/dual-namespace issues that cause mapper registry
conflicts under pytest-xdist.
"""

import pytest
import warnings

# Suppress ResourceWarning for SQLite connections (cleaned up at session end)
warnings.filterwarnings("ignore", category=ResourceWarning, message=".*unclosed database.*")


def test_single_base_instance() -> None:
    """Verify all model modules share the same Base from core.db.

    Ensures deterministic import order: purge → import core.db → import models → assert.
    This prevents dual-Base issues when modules are purged and re-imported.
    """
    from module_purge import purge_modules

    # 1) Purge modules to ensure clean state
    # Note: module_purge protects core.db by default, but we want to ensure order
    purge_modules(prefixes=("core.db", "app.models"))

    # 2) Guarantee order: import core.db first
    import core.db  # noqa: F401

    # 3) Then import models (they will use the Base from core.db)
    import app.models.events as ev

    # 4) Assert they share the same Base instance
    try:
        assert (
            ev.Base is core.db.Base
        ), f"app.models.events.Base ({id(ev.Base)}) is not core.db.Base ({id(core.db.Base)})"
    finally:
        # Close any connections opened during import
        if hasattr(core.db, "engine") and core.db.engine is not None:
            core.db.engine.dispose()


def test_app_import_is_clean() -> None:
    """Verify app package imports without dynamic module magic."""
    import app

    # Should have app attribute
    assert hasattr(app, "app"), "app package should export 'app'"

    # Should NOT have remnants of old dynamic import system
    assert not hasattr(app, "_mod"), "app should not have _mod (old dynamic import)"
    assert not hasattr(app, "app_module"), "app should not have app_module (old dynamic import)"
    assert not hasattr(app, "_RebindingModuleSpec"), "app should not have _RebindingModuleSpec"
