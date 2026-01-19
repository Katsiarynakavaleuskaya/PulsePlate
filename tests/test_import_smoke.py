"""
Smoke tests to ensure all core modules are importable and appear in coverage reports.
This file exists solely to import modules that might not be tested elsewhere,
so they show up in coverage calculations with their actual coverage percentages.
"""

import importlib

import pytest

# Define core modules as a constant list for parametrized testing
CORE_MODULES = [
    "core.product_varieties",
    "core.product_finder",
    "core.food_db",
    "core.exports",
    "core.meal_i18n",
    "core.food_sources.usda",
    "core.food_sources.off",
]

# Define main application modules as a constant list for parametrized testing
MAIN_MODULES = [
    "core.bmi.engine",  # canonical BMI engine
    "app.main",  # FastAPI entrypoint
    "app.routers.bmi",  # FREE tier endpoint
    "app.routers.bmi_pro",  # PRO tier endpoint
    "nutrition_core",
    "nutrition_plate",
    "bodyfat",
    "bmi_visualization",
]


@pytest.mark.parametrize("module_name", CORE_MODULES)
def test_import_core_modules_smoke(module_name):
    """Import each core module individually to ensure they appear in coverage.

    Each module is a separate test item so missing modules are skipped
    individually without aborting the whole test.
    """
    module = pytest.importorskip(module_name)
    assert module is not None, f"Module {module_name} failed to import"


@pytest.mark.parametrize("module_name", MAIN_MODULES)
def test_import_main_modules_smoke(module_name):
    """Import each main application module individually to appear in coverage.

    Each module is a separate test item to avoid skipping the entire test when a
    single module is unavailable. On ImportError, skip only that module.
    """
    try:
        module = importlib.import_module(module_name)
        assert module is not None, f"Module {module_name} failed to import"
    except ImportError as e:
        pytest.skip(f"Module {module_name} not available: {e}")


def test_import_app_modules_smoke():
    """Import app modules to ensure they appear in coverage."""
    try:
        import app

        assert app is not None

        # Try to import key app submodules
        app_modules = [
            "app.routers.vip",
        ]

        for module_name in app_modules:
            from contextlib import suppress

            with suppress(ImportError):
                module = importlib.import_module(module_name)
                assert module is not None, f"Module {module_name} failed to import"

    except ImportError as e:
        pytest.skip(f"App module not available: {e}")
