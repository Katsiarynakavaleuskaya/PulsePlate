"""
Simple import-smoke tests. Fail on ImportError to keep coverage meaningful.
"""

import pytest


@pytest.mark.parametrize(
    "module_name",
    [
        "core.exports_simple",
        "core.food_apis.unified_db",
        "core.food_apis.update_manager",
        "core.food_db",
        "core.food_merge",
        "core.menu_engine",
        "core.menu_engine_new",
        "core.plate",
        "core.product_finder",
        "core.product_varieties",
        "core.rag.simple_rag",
        "core.recipe_db",
        "core.recipe_db_new",
        "core.recipe_synth",
        "core.recommendations",
        "core.region_catalog",
        "core.rules_who",
        "core.targets",
        "core.time_utils",
    ],
)
def test_import_module_smoke(module_name: str) -> None:
    __import__(module_name)


def test_package_structure_smoke() -> None:
    import core
    import core.food_apis

    assert core is not None
    assert core.food_apis is not None
