"""Import hygiene guard: ensure a single Base instance across all models.

This test catches dual-Base/dual-namespace issues that cause mapper registry
conflicts under pytest-xdist.
"""

import pytest
import warnings

# Suppress ResourceWarning for SQLite connections (cleaned up at session end)
warnings.filterwarnings("ignore", category=ResourceWarning, message=".*unclosed database.*")


def test_single_base_instance() -> None:
    """Verify all model modules share the same Base from core.db."""
    import core.db
    import app.models.events as ev

    try:
        assert (
            ev.Base is core.db.Base
        ), f"app.models.events.Base ({id(ev.Base)}) is not core.db.Base ({id(core.db.Base)})"
    finally:
        # Close any connections opened during import
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
