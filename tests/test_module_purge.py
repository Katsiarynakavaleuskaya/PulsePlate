import sys
from types import ModuleType

from module_purge import purge_modules


def _restore_sys_modules(snapshot: dict[str, ModuleType]) -> None:
    """Restore sys.modules to a prior snapshot."""
    sys.modules.clear()
    sys.modules.update(snapshot)


def test_purge_modules_respects_exclusions_and_removes_only_targets() -> None:
    original_modules: dict[str, ModuleType] = dict(sys.modules)

    sys.modules.update(
        {
            # candidates for removal
            "legacy_app.foo": ModuleType("legacy_app.foo"),
            "app.main": ModuleType("app.main"),
            # must be preserved
            "app.models": ModuleType("app.models"),
            "app.models.plan": ModuleType("app.models.plan"),
            "core.db": ModuleType("core.db"),
            # unrelated
            "random.module": ModuleType("random.module"),
        }
    )

    try:
        purge_modules(prefixes=("legacy_app", "app.main"))

        assert "legacy_app.foo" not in sys.modules
        assert "app.main" not in sys.modules

        # protected by default
        assert "app.models" in sys.modules
        assert "app.models.plan" in sys.modules
        assert "core.db" in sys.modules

        # unrelated untouched
        assert "random.module" in sys.modules
    finally:
        _restore_sys_modules(original_modules)
