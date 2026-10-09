from __future__ import annotations

import ast
import hashlib
import json
import resource
import subprocess
import sys
import textwrap
import time
from pathlib import Path
from typing import Any, Literal, Mapping, cast

import pytest

import scripts.ci.check_legacy_growth_guard as legacy_guard

REPO_ROOT = Path(__file__).resolve().parents[1]


# Independent finite ownership inventory; do not derive test membership from the guard.
_CONSOL_API_KEY_SYMBOLS = (
    "api_key_header",
    "get_api_key",
    "_get_api_key_dynamic",
    "validate_app_api_key",
    "require_app_api_key",
)
_CONSOL_LEGACY_GETTERS = ("get_api_key", "_get_api_key_dynamic")
_CONSOL_OPENAPI_SYMBOLS = (
    "_OPENAPI_ALLOWED_PREFIXES",
    "_OPENAPI_ALLOWED_EXACT",
    "_is_openapi_public_path",
    "_collect_schema_refs",
    "_prune_unreferenced_schema_components",
    "_build_canonical_openapi",
    "_install_openapi_builder",
)
_CONSOL_GETTER_IMPORTS = "from app.routers.api_key import _get_api_key_dynamic, get_api_key\n"
_CONSOL_API_KEY_REBINDING_ERRORS = {
    "get_api_key": (
        "legacy_app.py: canonical API-key compatibility re-export must not be rebound: get_api_key"
    ),
    "_get_api_key_dynamic": (
        "legacy_app.py: canonical API-key compatibility re-export must not be rebound: "
        "_get_api_key_dynamic"
    ),
    "api_key_header": (
        "legacy_app.py: canonical API-key dependency must not be rebound: api_key_header"
    ),
    "validate_app_api_key": (
        "legacy_app.py: canonical API-key dependency must not be rebound: validate_app_api_key"
    ),
    "require_app_api_key": (
        "legacy_app.py: canonical API-key dependency must not be rebound: require_app_api_key"
    ),
}


def _canonical_api_key_owner_source() -> str:
    """Load the real whole owner without importing application runtime."""
    return (REPO_ROOT / legacy_guard.CANONICAL_API_KEY).read_text(encoding="utf-8")


def _validate_api_key_dependency_ownership(
    legacy_source: str,
    app_sources: dict[str, str],
) -> list[str]:
    """Supply an absent owner input; preserve explicit corrupt inputs and strict validation."""
    sources = {legacy_guard.CANONICAL_API_KEY: _canonical_api_key_owner_source(), **app_sources}
    return legacy_guard.validate_api_key_dependency_ownership(legacy_source, sources)


def _consol_openapi_errors(
    addition: str,
    *,
    postponed_annotations: bool = False,
) -> list[str]:
    """Use the existing five-source fixture and real ownership validator."""
    sources = list(_openapi_ownership_sources())
    sources[3] += textwrap.dedent(addition)
    if postponed_annotations:
        sources[3] = "from __future__ import annotations\n" + sources[3]
    return legacy_guard.validate_application_metadata_openapi_ownership(*sources)


RETIRED_LEGACY_PYTHON_BINDINGS = (
    "admin_status",
    "cleanup_expired_logs",
    "debug_env",
    "get_database_status",
    "force_database_update",
    "check_for_updates",
    "rollback_database",
    "bmi_endpoint",
    "plan_endpoint",
    "bmi_endpoint_v1",
    "_resolve_build_targets_callable",
    "PlateDependencies",
    "_compute_premium_plate",
    "api_premium_plate",
    "build_fallback_plate",
    "align_macros_with_targets",
    "aggregate_day_micros",
    "premium_targets_legacy",
    "api_who_targets",
    "api_nutrient_gaps",
    "analyze_nutrient_gaps",
    "make_daily_menu",
    "make_weekly_menu",
    "repair_week_plan",
    "make_plate",
    "build_nutrition_targets",
    "to_csv_day",
    "to_pdf_day",
    "to_csv_week",
    "to_pdf_week",
    "WeeklyPlanFlexibleRequest",
    "INSIGHT_TEXT_MAX_LENGTH",
    "InsightRequest",
    "RAGSourceItem",
    "InsightResponse",
    "INSIGHT_TEMP_UNAVAILABLE_MESSAGE",
    "_execute_insight_request",
    "insight_v1",
    "insight",
    "DB_TO_ALIAS_NUTRIENT_MAP",
    "PlateServiceDependencies",
    "_convert_db_nutrients_to_alias_format",
    "_aggregate_meal_micronutrients",
    "_get_recipe_ingredients_for_meal",
    "_aggregate_day_micronutrients",
    "_macros_to_kcal",
    "sanitize_plate_data",
    "_iter_exception_chain",
    "_is_missing_nh3_error",
    "_raise_missing_nh3_http_error",
    "calculate_heuristic_macros",
    "MANDATORY_MICRO_DEFAULTS",
    "MAX_DAILY_KCAL",
    "MICRO_ALIAS_MAP",
    "MIN_DAILY_KCAL",
    "_alias_micros",
    "_clamp_daily_kcal",
    "_ensure_priority_micros",
    "_generate_who_targets_response",
    "_fallback_targets_response",
    "analyze_nutrient_gaps_response",
    "_OPENAPI_ALLOWED_PREFIXES",
    "_OPENAPI_ALLOWED_EXACT",
    "_is_openapi_public_path",
    "_collect_schema_refs",
    "_prune_unreferenced_schema_components",
    "_build_canonical_openapi",
    "_install_openapi_builder",
    "BMRRequest",
    "BMRRequestLegacy",
    "BMRResponse",
    "NutrientGapsRequest",
    "NutrientGapsResponse",
    "PlateRequest",
    "PlateResponse",
    "VisualShape",
    "WHOTargetsRequest",
    "WHOTargetsResponse",
    "Activity",
    "DietFlag",
    "Goal",
    "Sex",
    "build_who_targets_ui_labels",
    "DataClass",
    "get_retention_manager",
    "LogRetentionManager",
    "_log_retention_manager",
    "TargetsIn",
    "CanonicalTargetsIn",
    "LegacyWeekPlanRequest",
    "WeeklyMenuResponse",
    "get_session",
    "Language",
    "normalize_lang",
    "t",
    "FIBER_MIN_G",
    "_short_git_sha",
    "_is_truthy",
    "_LEGACY_IMPORT_COMPAT_REEXPORTS",
)

RETIRED_PRO_NUTRITION_BINDINGS = RETIRED_LEGACY_PYTHON_BINDINGS[10:20]
RETIRED_PLANNING_EXPORT_BINDINGS = RETIRED_LEGACY_PYTHON_BINDINGS[20:31]
RETIRED_INSIGHT_BINDINGS = RETIRED_LEGACY_PYTHON_BINDINGS[31:39]
RETIRED_PLATE_HELPER_BINDINGS = RETIRED_LEGACY_PYTHON_BINDINGS[39:51]
RETIRED_NUTRITION_UTILITY_BINDINGS = RETIRED_LEGACY_PYTHON_BINDINGS[51:58]
RETIRED_TARGETS_GAPS_SERVICE_BINDINGS = RETIRED_LEGACY_PYTHON_BINDINGS[58:61]
RETIRED_OPENAPI_BINDINGS = RETIRED_LEGACY_PYTHON_BINDINGS[61:68]
RETIRED_NUTRITION_CONTRACT_BINDINGS = RETIRED_LEGACY_PYTHON_BINDINGS[68:83]
RETIRED_LOG_RETENTION_BINDINGS = RETIRED_LEGACY_PYTHON_BINDINGS[83:87]
RETIRED_PLANNING_SCHEMA_BINDINGS = RETIRED_LEGACY_PYTHON_BINDINGS[87:91]
RETIRED_CORE_UTILITY_BINDINGS = RETIRED_LEGACY_PYTHON_BINDINGS[91:99]


def test_retired_insight_binding_tail_is_exact_and_disjoint() -> None:
    """Keep the eight retired Insight names distinct from earlier cohorts."""
    assert RETIRED_INSIGHT_BINDINGS == (
        "INSIGHT_TEXT_MAX_LENGTH",
        "InsightRequest",
        "RAGSourceItem",
        "InsightResponse",
        "INSIGHT_TEMP_UNAVAILABLE_MESSAGE",
        "_execute_insight_request",
        "insight_v1",
        "insight",
    )
    assert set(RETIRED_LEGACY_PYTHON_BINDINGS[:31]).isdisjoint(RETIRED_INSIGHT_BINDINGS)


def test_retired_plate_helper_binding_tail_is_exact_and_disjoint() -> None:
    """Require exactly twelve new Plate names without replacing earlier retirements."""
    assert RETIRED_PLATE_HELPER_BINDINGS == (
        "DB_TO_ALIAS_NUTRIENT_MAP",
        "PlateServiceDependencies",
        "_convert_db_nutrients_to_alias_format",
        "_aggregate_meal_micronutrients",
        "_get_recipe_ingredients_for_meal",
        "_aggregate_day_micronutrients",
        "_macros_to_kcal",
        "sanitize_plate_data",
        "_iter_exception_chain",
        "_is_missing_nh3_error",
        "_raise_missing_nh3_http_error",
        "calculate_heuristic_macros",
    )
    assert len(RETIRED_LEGACY_PYTHON_BINDINGS[:51]) == 51
    assert len(set(RETIRED_LEGACY_PYTHON_BINDINGS[:51])) == 51
    assert set(RETIRED_LEGACY_PYTHON_BINDINGS[:39]).isdisjoint(RETIRED_PLATE_HELPER_BINDINGS)


def test_retired_nutrition_utility_tail_is_exact_and_disjoint() -> None:
    assert RETIRED_NUTRITION_UTILITY_BINDINGS == (
        "MANDATORY_MICRO_DEFAULTS",
        "MAX_DAILY_KCAL",
        "MICRO_ALIAS_MAP",
        "MIN_DAILY_KCAL",
        "_alias_micros",
        "_clamp_daily_kcal",
        "_ensure_priority_micros",
    )
    assert len(RETIRED_LEGACY_PYTHON_BINDINGS[:58]) == 58
    assert len(set(RETIRED_LEGACY_PYTHON_BINDINGS[:58])) == 58
    assert set(RETIRED_LEGACY_PYTHON_BINDINGS[:51]).isdisjoint(RETIRED_NUTRITION_UTILITY_BINDINGS)


def test_retired_targets_gaps_service_tail_is_exact_and_disjoint() -> None:
    assert RETIRED_TARGETS_GAPS_SERVICE_BINDINGS == (
        "_generate_who_targets_response",
        "_fallback_targets_response",
        "analyze_nutrient_gaps_response",
    )
    assert len(RETIRED_LEGACY_PYTHON_BINDINGS[:61]) == 61
    assert len(set(RETIRED_LEGACY_PYTHON_BINDINGS[:61])) == 61
    assert set(RETIRED_LEGACY_PYTHON_BINDINGS[:58]).isdisjoint(
        RETIRED_TARGETS_GAPS_SERVICE_BINDINGS
    )


def test_retired_openapi_tail_is_exact_and_disjoint() -> None:
    assert RETIRED_OPENAPI_BINDINGS == (
        "_OPENAPI_ALLOWED_PREFIXES",
        "_OPENAPI_ALLOWED_EXACT",
        "_is_openapi_public_path",
        "_collect_schema_refs",
        "_prune_unreferenced_schema_components",
        "_build_canonical_openapi",
        "_install_openapi_builder",
    )
    assert len(RETIRED_LEGACY_PYTHON_BINDINGS[:68]) == 68
    assert len(set(RETIRED_LEGACY_PYTHON_BINDINGS[:68])) == 68
    assert set(RETIRED_LEGACY_PYTHON_BINDINGS[:61]).isdisjoint(RETIRED_OPENAPI_BINDINGS)


def test_retired_nutrition_contract_tail_is_exact_and_disjoint() -> None:
    assert RETIRED_NUTRITION_CONTRACT_BINDINGS == (
        "BMRRequest",
        "BMRRequestLegacy",
        "BMRResponse",
        "NutrientGapsRequest",
        "NutrientGapsResponse",
        "PlateRequest",
        "PlateResponse",
        "VisualShape",
        "WHOTargetsRequest",
        "WHOTargetsResponse",
        "Activity",
        "DietFlag",
        "Goal",
        "Sex",
        "build_who_targets_ui_labels",
    )
    assert len(RETIRED_LEGACY_PYTHON_BINDINGS[:83]) == 83
    assert len(set(RETIRED_LEGACY_PYTHON_BINDINGS[:83])) == 83
    assert set(RETIRED_LEGACY_PYTHON_BINDINGS[:68]).isdisjoint(RETIRED_NUTRITION_CONTRACT_BINDINGS)


def test_retired_log_retention_tail_is_exact_and_disjoint() -> None:
    """Pin the four-name cohort separately from earlier legacy retirements."""
    assert RETIRED_LOG_RETENTION_BINDINGS == (
        "DataClass",
        "get_retention_manager",
        "LogRetentionManager",
        "_log_retention_manager",
    )
    assert len(RETIRED_LEGACY_PYTHON_BINDINGS[:87]) == 87
    assert len(set(RETIRED_LEGACY_PYTHON_BINDINGS[:87])) == 87
    assert set(RETIRED_LEGACY_PYTHON_BINDINGS[:83]).isdisjoint(RETIRED_LOG_RETENTION_BINDINGS)


def test_retired_planning_schema_tail_is_exact_and_disjoint() -> None:
    """Keep the four-name schema cohort exact and disjoint from the original 87."""
    assert RETIRED_PLANNING_SCHEMA_BINDINGS == (
        "TargetsIn",
        "CanonicalTargetsIn",
        "LegacyWeekPlanRequest",
        "WeeklyMenuResponse",
    )
    assert len(RETIRED_LEGACY_PYTHON_BINDINGS[:91]) == 91
    assert len(set(RETIRED_LEGACY_PYTHON_BINDINGS[:91])) == 91
    assert set(RETIRED_LEGACY_PYTHON_BINDINGS[:87]).isdisjoint(RETIRED_PLANNING_SCHEMA_BINDINGS)


def test_retired_core_utility_tail_is_exact_and_disjoint() -> None:
    """Preserve the original 91 names and append only the exact utility cohort."""
    assert RETIRED_CORE_UTILITY_BINDINGS == (
        "get_session",
        "Language",
        "normalize_lang",
        "t",
        "FIBER_MIN_G",
        "_short_git_sha",
        "_is_truthy",
        "_LEGACY_IMPORT_COMPAT_REEXPORTS",
    )
    assert len(RETIRED_LEGACY_PYTHON_BINDINGS[:91]) == 91
    assert len(set(RETIRED_LEGACY_PYTHON_BINDINGS[:91])) == 91
    assert set(RETIRED_LEGACY_PYTHON_BINDINGS[:91]).isdisjoint(RETIRED_CORE_UTILITY_BINDINGS)
    assert len(RETIRED_LEGACY_PYTHON_BINDINGS) == 99
    assert len(set(RETIRED_LEGACY_PYTHON_BINDINGS)) == 99


@pytest.mark.parametrize("binding_name", RETIRED_CORE_UTILITY_BINDINGS)
@pytest.mark.parametrize(
    "source_template",
    [
        "{name} = canonical\n",
        "{name}: object = canonical\n",
        "{name}: object\n",
        "from core.i18n import canonical as {name}\n",
        "def {name}():\n    return None\n",
        "class {name}:\n    pass\n",
        "del {name}\n",
        "def mutate():\n    global {name}\n",
    ],
    ids=[
        "assignment",
        "annotation",
        "uninitialized-annotation",
        "import-alias",
        "function",
        "class",
        "delete",
        "global",
    ],
)
def test_retired_core_utility_binding_carrier(binding_name: str, source_template: str) -> None:
    """Reject each existing supported static carrier, including the facade-only tuple."""
    assert legacy_guard.validate_retired_legacy_python_bindings(
        source_template.format(name=binding_name)
    ) == [f"legacy_app.py: retired Python compatibility binding is forbidden: {binding_name}"]


@pytest.mark.parametrize(
    ("binding_name", "canonical_module"),
    (
        ("get_session", "core.db"),
        ("Language", "core.i18n"),
        ("normalize_lang", "core.i18n"),
        ("t", "core.i18n"),
        ("FIBER_MIN_G", "core.targets"),
        ("_short_git_sha", "app.utils.helpers"),
        ("_is_truthy", "app.utils.feature_flags"),
    ),
)
@pytest.mark.parametrize("same_name_alias", (False, True), ids=("direct", "same-name-alias"))
def test_retired_core_utility_guard_rejects_exact_canonical_reimport(
    binding_name: str, canonical_module: str, same_name_alias: bool
) -> None:
    """Canonical imports cannot restore a retired utility name in the facade."""
    suffix = f" as {binding_name}" if same_name_alias else ""
    source = f"from {canonical_module} import {binding_name}{suffix}\n"
    assert legacy_guard.validate_retired_legacy_python_bindings(source) == [
        f"legacy_app.py: retired Python compatibility binding is forbidden: {binding_name}"
    ]


@pytest.mark.parametrize("binding_name", RETIRED_PLANNING_SCHEMA_BINDINGS)
@pytest.mark.parametrize(
    "source_template",
    [
        "{name} = canonical\n",
        "from app.schemas.nutrition_targets import canonical as {name}\n",
        "def {name}():\n    return None\n",
        "class {name}:\n    pass\n",
        "del {name}\n",
        "def mutate():\n    global {name}\n",
    ],
    ids=["assignment", "import-alias", "function", "class", "delete", "global"],
)
def test_retired_planning_schema_binding_carrier(binding_name: str, source_template: str) -> None:
    """Reject each supported static binding form for every retired planning schema."""
    assert legacy_guard.validate_retired_legacy_python_bindings(
        source_template.format(name=binding_name)
    ) == [f"legacy_app.py: retired Python compatibility binding is forbidden: {binding_name}"]


@pytest.mark.parametrize(
    ("binding_name", "source"),
    (
        ("TargetsIn", "from app.schemas.nutrition_targets import TargetsIn\n"),
        (
            "CanonicalTargetsIn",
            "from app.schemas.nutrition_targets import TargetsIn as CanonicalTargetsIn\n",
        ),
        (
            "LegacyWeekPlanRequest",
            "from app.schemas.legacy_premium_weekly_plan import LegacyWeekPlanRequest\n",
        ),
        (
            "WeeklyMenuResponse",
            "from app.schemas.legacy_premium_weekly_plan import WeeklyMenuResponse\n",
        ),
    ),
)
def test_retired_planning_schema_guard_rejects_exact_canonical_reimport(
    binding_name: str, source: str
) -> None:
    """Reject canonical schema re-imports that would restore retired facade names."""
    assert legacy_guard.validate_retired_legacy_python_bindings(source) == [
        f"legacy_app.py: retired Python compatibility binding is forbidden: {binding_name}"
    ]


@pytest.mark.parametrize("binding_name", RETIRED_LOG_RETENTION_BINDINGS)
@pytest.mark.parametrize(
    "source_template",
    [
        "{name} = canonical\n",
        "{name}: object = canonical\n",
        "from core.log_retention import canonical as {name}\n",
        "def {name}():\n    return None\n",
        "class {name}:\n    pass\n",
        "del {name}\n",
        "def mutate():\n    global {name}\n",
    ],
    ids=["assignment", "annotation", "import-alias", "function", "class", "delete", "global"],
)
def test_retired_log_retention_binding_carrier(binding_name: str, source_template: str) -> None:
    """Reject each recognized static carrier of a retired retention name."""
    assert legacy_guard.validate_retired_legacy_python_bindings(
        source_template.format(name=binding_name)
    ) == [f"legacy_app.py: retired Python compatibility binding is forbidden: {binding_name}"]


@pytest.mark.parametrize("binding_name", RETIRED_LOG_RETENTION_BINDINGS[:3])
def test_retired_log_retention_guard_rejects_exact_canonical_reimport(
    binding_name: str,
) -> None:
    """Reject re-exporting a canonical core symbol through the legacy facade."""
    assert legacy_guard.validate_retired_legacy_python_bindings(
        f"from core.log_retention import {binding_name}\n"
    ) == [f"legacy_app.py: retired Python compatibility binding is forbidden: {binding_name}"]


@pytest.mark.parametrize("binding_name", RETIRED_NUTRITION_CONTRACT_BINDINGS)
@pytest.mark.parametrize(
    "source_template",
    [
        "{name} = canonical\n",
        "from app.schemas.premium_contracts import canonical as {name}\n",
        "def {name}():\n    return None\n",
        "class {name}:\n    pass\n",
        "del {name}\n",
        "def mutate():\n    global {name}\n",
    ],
    ids=["assignment", "import-alias", "function", "class", "delete", "global"],
)
def test_retired_nutrition_contract_binding_carrier(
    binding_name: str, source_template: str
) -> None:
    assert legacy_guard.validate_retired_legacy_python_bindings(
        source_template.format(name=binding_name)
    ) == [f"legacy_app.py: retired Python compatibility binding is forbidden: {binding_name}"]


@pytest.mark.parametrize("binding_name", RETIRED_NUTRITION_CONTRACT_BINDINGS)
def test_retired_nutrition_contract_guard_rejects_exact_canonical_reimport(
    binding_name: str,
) -> None:
    canonical_module = (
        "app.schemas.bmr"
        if binding_name in {"BMRRequest", "BMRRequestLegacy", "BMRResponse"}
        else "app.schemas.premium_contracts"
    )
    source = f"from {canonical_module} import {binding_name}\n"

    assert legacy_guard.validate_retired_legacy_python_bindings(source) == [
        f"legacy_app.py: retired Python compatibility binding is forbidden: {binding_name}"
    ]


@pytest.mark.parametrize("binding_name", RETIRED_OPENAPI_BINDINGS)
def test_retired_openapi_guard_rejects_exact_canonical_reimport(
    binding_name: str,
) -> None:
    source = f"from app.bootstrap.openapi import {binding_name}\n"

    assert legacy_guard.validate_retired_legacy_python_bindings(source) == [
        f"legacy_app.py: retired Python compatibility binding is forbidden: {binding_name}"
    ]
    sources = list(_openapi_ownership_sources())
    sources[0] += source
    assert legacy_guard.validate_application_metadata_openapi_ownership(*sources) == [
        f"legacy_app.py: canonical OpenAPI re-export must not be rebound: {binding_name}"
    ]


def test_retired_openapi_reimport_fails_aggregate_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_read = legacy_guard._read

    def read_with_reintroduced_import(path: Path, repo_root: Path, errors: list[str]) -> str | None:
        source = original_read(path, repo_root, errors)
        if path == REPO_ROOT / "legacy_app.py" and source is not None:
            return source + "\nfrom app.bootstrap.openapi import _install_openapi_builder\n"
        return source

    monkeypatch.setattr(legacy_guard, "_read", read_with_reintroduced_import)

    errors = legacy_guard.validate_repo(REPO_ROOT)

    assert errors == [
        "legacy_app.py: retired Python compatibility binding is forbidden: "
        "_install_openapi_builder",
        "legacy_app.py: canonical OpenAPI re-export must not be rebound: "
        "_install_openapi_builder",
    ]


def test_current_legacy_app_passes_growth_guard() -> None:
    source = (REPO_ROOT / "legacy_app.py").read_text(encoding="utf-8")

    assert legacy_guard.validate_legacy_growth(source) == []
    assert legacy_guard.ALLOWED_LEGACY_ROUTE_FACTS == frozenset()


def test_current_legacy_app_passes_retired_python_binding_guard() -> None:
    source = (REPO_ROOT / "legacy_app.py").read_text(encoding="utf-8")

    assert legacy_guard.validate_retired_legacy_python_bindings(source) == []
    assert legacy_guard.RETIRED_LEGACY_PYTHON_BINDINGS == frozenset(RETIRED_LEGACY_PYTHON_BINDINGS)


@pytest.mark.parametrize("binding_name", RETIRED_LEGACY_PYTHON_BINDINGS)
def test_legacy_growth_guard_rejects_each_retired_python_binding(
    binding_name: str,
) -> None:
    source = f"async def {binding_name}():\n    return None\n"

    assert legacy_guard.validate_retired_legacy_python_bindings(source) == [
        f"legacy_app.py: retired Python compatibility binding is forbidden: {binding_name}"
    ]


@pytest.mark.parametrize(
    "binding_name", RETIRED_PRO_NUTRITION_BINDINGS + RETIRED_PLATE_HELPER_BINDINGS
)
@pytest.mark.parametrize(
    "source_template",
    [
        "{name} = canonical\n",
        "from app.services.pro_nutrition_plate import canonical as {name}\n",
        "def {name}():\n    return None\n",
        "class {name}:\n    pass\n",
        "del {name}\n",
        "def mutate():\n    global {name}\n",
    ],
    ids=["assignment", "import-alias", "function", "class", "delete", "global"],
)
def test_legacy_growth_guard_rejects_each_pro_nutrition_binding_carrier(
    binding_name: str,
    source_template: str,
) -> None:
    """Reject each retired nutrition name through the existing recognized carriers."""
    source = source_template.format(name=binding_name)

    assert legacy_guard.validate_retired_legacy_python_bindings(source) == [
        f"legacy_app.py: retired Python compatibility binding is forbidden: {binding_name}"
    ]


@pytest.mark.parametrize("binding_name", RETIRED_TARGETS_GAPS_SERVICE_BINDINGS)
@pytest.mark.parametrize(
    "source_template",
    [
        "{name} = canonical\n",
        "from app.services.pro_nutrition_targets import canonical as {name}\n",
        "def {name}():\n    return None\n",
        "class {name}:\n    pass\n",
        "del {name}\n",
        "def mutate():\n    global {name}\n",
    ],
    ids=["assignment", "import-alias", "function", "class", "delete", "global"],
)
def test_legacy_growth_guard_rejects_each_targets_gaps_service_binding_carrier(
    binding_name: str,
    source_template: str,
) -> None:
    source = source_template.format(name=binding_name)

    assert legacy_guard.validate_retired_legacy_python_bindings(source) == [
        f"legacy_app.py: retired Python compatibility binding is forbidden: {binding_name}"
    ]


@pytest.mark.parametrize("binding_name", RETIRED_NUTRITION_UTILITY_BINDINGS)
@pytest.mark.parametrize(
    "source_template",
    [
        "{name} = canonical\n",
        "from core.nutrition_utils import canonical as {name}\n",
        "def {name}():\n    return None\n",
        "class {name}:\n    pass\n",
        "del {name}\n",
        "def mutate():\n    global {name}\n",
    ],
    ids=["assignment", "import-alias", "function", "class", "delete", "global"],
)
def test_legacy_growth_guard_rejects_each_nutrition_utility_binding_carrier(
    binding_name: str,
    source_template: str,
) -> None:
    source = source_template.format(name=binding_name)

    assert legacy_guard.validate_retired_legacy_python_bindings(source) == [
        f"legacy_app.py: retired Python compatibility binding is forbidden: {binding_name}"
    ]


@pytest.mark.parametrize("binding_name", RETIRED_PLANNING_EXPORT_BINDINGS)
@pytest.mark.parametrize(
    "source_template",
    [
        "{name} = canonical\n",
        "from core.menu_engine import canonical as {name}\n",
        "def {name}():\n    return None\n",
        "class {name}:\n    pass\n",
        "del {name}\n",
        "def mutate():\n    global {name}\n",
    ],
    ids=["assignment", "import-alias", "function", "class", "delete", "global"],
)
def test_legacy_growth_guard_rejects_each_planning_export_binding_carrier(
    binding_name: str,
    source_template: str,
) -> None:
    source = source_template.format(name=binding_name)

    assert legacy_guard.validate_retired_legacy_python_bindings(source) == [
        f"legacy_app.py: retired Python compatibility binding is forbidden: {binding_name}"
    ]


@pytest.mark.parametrize("binding_name", RETIRED_INSIGHT_BINDINGS)
@pytest.mark.parametrize(
    "source_template",
    [
        "{name} = canonical\n",
        "from app.schemas.insight import canonical as {name}\n",
        "def {name}():\n    return None\n",
        "class {name}:\n    pass\n",
        "del {name}\n",
        "def mutate():\n    global {name}\n",
    ],
    ids=["assignment", "import-alias", "function", "class", "delete", "global"],
)
def test_legacy_growth_guard_rejects_each_insight_binding_carrier(
    binding_name: str,
    source_template: str,
) -> None:
    source = source_template.format(name=binding_name)

    assert legacy_guard.validate_retired_legacy_python_bindings(source) == [
        f"legacy_app.py: retired Python compatibility binding is forbidden: {binding_name}"
    ]


def test_legacy_growth_guard_rejects_retired_plan_export_dynamic_import_fact() -> None:
    source = textwrap.dedent("""
        import importlib

        _plan_mod = importlib.import_module("app.routers.plan_export")
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:dynamic:app.routers.plan_export -> _plan_mod"
    ]


@pytest.mark.parametrize(
    "source",
    [
        "admin_status = canonical\n",
        "admin_status: object\n",
        "del admin_status\n",
        "from app.services.admin_operations import admin_status\n",
        "from app.services.admin_operations import canonical as admin_status\n",
        "def mutate():\n    global admin_status\n",
    ],
    ids=["assignment", "annotation", "delete", "direct-import", "aliased-import", "global"],
)
def test_legacy_growth_guard_rejects_representative_retired_binding_carriers(
    source: str,
) -> None:
    assert legacy_guard.validate_retired_legacy_python_bindings(source) == [
        "legacy_app.py: retired Python compatibility binding is forbidden: admin_status"
    ]


def test_legacy_growth_guard_rejects_blanket_star_import() -> None:
    source = "from app.services.admin_operations import *\n"

    assert (
        "legacy_app.py: star import is forbidden after legacy Python binding retirement"
        in legacy_guard.validate_retired_legacy_python_bindings(source)
    )


def test_legacy_growth_guard_rejects_module_level_getattr() -> None:
    source = textwrap.dedent("""
        def __getattr__(name: str):
            return canonical[name]
        """)

    assert legacy_guard.validate_retired_legacy_python_bindings(source) == [
        "legacy_app.py: module-level __getattr__ is forbidden after legacy Python "
        "binding retirement"
    ]


def test_retired_binding_guard_rejects_protected_global_getattr() -> None:
    source = textwrap.dedent("""
        def initialize() -> None:
            global __getattr__
            __getattr__ = resolver

        initialize()
        """)

    assert legacy_guard.validate_retired_legacy_python_bindings(source) == [
        "legacy_app.py: module-level __getattr__ is forbidden after legacy Python "
        "binding retirement"
    ]


def test_retired_binding_guard_allows_unrelated_global_and_local_getattr() -> None:
    source = textwrap.dedent("""
        def initialize() -> None:
            global unrelated_name
            unrelated_name = resolver

            def __getattr__(name: str) -> object:
                return name

        class CompatibilityProxy:
            def __getattr__(self, name: str) -> object:
                return name

        initialize()
        """)

    assert legacy_guard.validate_retired_legacy_python_bindings(source) == []


def test_retired_binding_guard_rejects_lambda_default_module_binding() -> None:
    source = "holder = lambda value=(admin_status := canonical): value\n"

    assert legacy_guard.validate_retired_legacy_python_bindings(source) == [
        "legacy_app.py: retired Python compatibility binding is forbidden: admin_status"
    ]


def test_retired_binding_guard_ignores_named_expression_in_lambda_body() -> None:
    source = "holder = lambda: (admin_status := canonical)\n"

    assert legacy_guard.validate_retired_legacy_python_bindings(source) == []


def test_legacy_growth_guard_allows_out_of_scope_binding_shapes() -> None:
    source = textwrap.dedent("""
        "admin_status is retired only as a legacy_app module binding"
        # admin_status in a comment is not a binding.
        from app.services.admin_operations import admin_status as canonical_admin_status

        _admin_status = canonical_admin_status
        admin_status_v2 = canonical_admin_status
        holder.admin_status = canonical_admin_status

        def local_scope(admin_status: object) -> object:
            local_copy = admin_status
            return local_copy

        def nested_scope() -> None:
            admin_status = canonical_admin_status

        class CompatibilityProxy:
            admin_status = canonical_admin_status
        """)

    assert legacy_guard.validate_retired_legacy_python_bindings(source) == []


@pytest.mark.parametrize(
    "filename",
    [
        "app/services/admin_operations.py",
        "app/services/bmi_compat.py",
        "app/services/pro_nutrition_plate.py",
        "app/services/pro_nutrition_targets.py",
        "app/routers/legacy_premium_nutrition.py",
    ],
)
def test_retired_binding_guard_ignores_canonical_owner_modules(filename: str) -> None:
    source = textwrap.dedent("""
        async def admin_status():
            return None

        async def api_premium_plate():
            return None
        """)

    assert (
        legacy_guard.validate_retired_legacy_python_bindings(
            source,
            filename=filename,
        )
        == []
    )


def test_retired_legacy_python_binding_guard_fails_closed_on_syntax_error() -> None:
    assert legacy_guard.validate_retired_legacy_python_bindings("def broken(:\n") == [
        "legacy_app.py:1: syntax error: invalid syntax"
    ]


def test_current_lifecycle_ownership_passes_growth_guard() -> None:
    legacy_source = (REPO_ROOT / "legacy_app.py").read_text(encoding="utf-8")
    food_source = (REPO_ROOT / "app/bootstrap/food_search.py").read_text(encoding="utf-8")
    lifespan_source = (REPO_ROOT / "app/bootstrap/lifespan.py").read_text(encoding="utf-8")

    assert (
        legacy_guard.validate_lifecycle_ownership(
            legacy_source,
            food_source,
            lifespan_source,
        )
        == []
    )


def test_current_api_key_dependency_ownership_passes_growth_guard() -> None:
    legacy_source = (REPO_ROOT / "legacy_app.py").read_text(encoding="utf-8")
    app_sources = {
        path.relative_to(REPO_ROOT).as_posix(): path.read_text(encoding="utf-8")
        for path in (REPO_ROOT / "app").rglob("*.py")
    }

    assert legacy_guard.validate_api_key_dependency_ownership(legacy_source, app_sources) == []


def _openapi_ownership_sources() -> tuple[str, str, str, str, str]:
    return (
        textwrap.dedent("""
            from app.application_metadata import build_application_metadata
            metadata = build_application_metadata(runtime_env="production")
            """),
        "from settings import get_runtime_env_name\n",
        "from fastapi import FastAPI\n",
        textwrap.dedent("""
            from legacy_app import app as _legacy_app
            from app.bootstrap.openapi import (
                apply_public_openapi_input_policy,
                install_canonical_openapi_builder,
                validate_openapi_builder_state,
            )
            """),
        "import importlib\n",
    )


def test_current_metadata_openapi_ownership_passes_growth_guard() -> None:
    sources = tuple(
        (REPO_ROOT / path).read_text(encoding="utf-8")
        for path in (
            "legacy_app.py",
            "app/application_metadata.py",
            "app/bootstrap/openapi.py",
            "app/main.py",
            "app/__init__.py",
        )
    )

    assert legacy_guard.validate_application_metadata_openapi_ownership(*sources) == []


@pytest.mark.parametrize(
    ("source_index", "addition", "expected_fragment"),
    [
        (
            0,
            "\ndef _install_openapi_builder(app):\n    return app\n",
            "OpenAPI implementation must be canonical",
        ),
        (
            0,
            "\n_install_openapi_builder = replacement\n",
            "canonical OpenAPI re-export must not be rebound",
        ),
        (
            0,
            "\nfrom foreign_openapi import _install_openapi_builder\n",
            "canonical OpenAPI re-export must not be rebound",
        ),
        (
            0,
            "\nfrom foreign_openapi import replacement as _install_openapi_builder\n",
            "canonical OpenAPI re-export must not be rebound",
        ),
        (
            0,
            "\nif True:\n    from foreign_openapi import _install_openapi_builder\n",
            "canonical OpenAPI re-export must not be rebound",
        ),
        (
            0,
            "\nif True:\n    def _install_openapi_builder(app):\n        return app\n",
            "canonical OpenAPI re-export must not be rebound",
        ),
        (
            0,
            "\ntry:\n    pass\nexcept Exception as _install_openapi_builder:\n    pass\n",
            "canonical OpenAPI re-export must not be rebound",
        ),
        (
            0,
            "\ndel _install_openapi_builder\n",
            "canonical OpenAPI re-export must not be rebound",
        ),
        (
            0,
            "\n@((_install_openapi_builder := decorator))\ndef decorated():\n    pass\n",
            "canonical OpenAPI re-export must not be rebound",
        ),
        (
            0,
            "\ndef with_default(value=(_install_openapi_builder := replacement)):\n    pass\n",
            "canonical OpenAPI re-export must not be rebound",
        ),
        (
            0,
            "\nclass Rebound((_install_openapi_builder := Base)):\n    pass\n",
            "canonical OpenAPI re-export must not be rebound",
        ),
        (
            0,
            "\n[(_install_openapi_builder := value) for value in values]\n",
            "canonical OpenAPI re-export must not be rebound",
        ),
        (
            0,
            "\nmatch value:\n    case _install_openapi_builder:\n        pass\n",
            "canonical OpenAPI re-export must not be rebound",
        ),
        (
            0,
            "\nfrom foreign_openapi import *\n",
            "canonical OpenAPI re-export must not be rebound",
        ),
        (
            0,
            "\ndef mutate_global():\n    global _install_openapi_builder\n",
            "canonical OpenAPI re-export must not be rebound",
        ),
        (
            0,
            '\nglobals()["_install_openapi_builder"] = replacement\n',
            "canonical OpenAPI re-export must not be rebound",
        ),
        (
            0,
            '\nnamespace = globals()\nnamespace["_install_openapi_builder"] = replacement\n',
            "canonical OpenAPI re-export must not be rebound",
        ),
        (
            0,
            '\ndef mutate():\n    import sys as system\n    setattr(system.modules[__name__], "_install_openapi_builder", replacement)\n',
            "canonical OpenAPI re-export must not be rebound",
        ),
        (
            0,
            textwrap.dedent("""
                import sys as system
                current_module = system.modules[__name__]
                assign = setattr
                installer_name = "_install_" + "openapi_builder"
                assign(current_module, installer_name, replacement)
                """),
            "canonical OpenAPI re-export must not be rebound",
        ),
        (
            0,
            "\nimport sys\nsys.modules[__name__]._install_openapi_builder = replacement\n",
            "canonical OpenAPI re-export must not be rebound",
        ),
        (
            0,
            '\nglobals().update({"_install_openapi_builder": replacement})\n',
            "canonical OpenAPI re-export must not be rebound",
        ),
        (
            0,
            '\nglobals().__setitem__("_install_openapi_builder", replacement)\n',
            "canonical OpenAPI re-export must not be rebound",
        ),
        (
            0,
            '\nglobals().__delitem__("_install_openapi_builder")\n',
            "canonical OpenAPI re-export must not be rebound",
        ),
        (
            0,
            '\nglobals().pop("_install_openapi_builder")\n',
            "canonical OpenAPI re-export must not be rebound",
        ),
        (
            0,
            "\nglobals().pop(dynamic_name)\n",
            "canonical OpenAPI re-export must not be rebound",
        ),
        (
            0,
            "\nglobals().popitem()\n",
            "canonical OpenAPI re-export must not be rebound",
        ),
        (
            0,
            "\nglobals().clear()\n",
            "canonical OpenAPI re-export must not be rebound",
        ),
        (
            0,
            '\nglobals().setdefault("_install_openapi_builder", replacement)\n',
            "canonical OpenAPI re-export must not be rebound",
        ),
        (
            0,
            '\nmodule.__dict__["_install_openapi_builder"] = replacement\n',
            "canonical OpenAPI re-export must not be rebound",
        ),
        (
            1,
            "\nimport os\nvalue = os.getenv('APP_ENV')\n",
            "direct environment parsing is forbidden",
        ),
        (
            2,
            "\nimport legacy_app\n",
            "reverse legacy/main import is forbidden",
        ),
        (
            2,
            "\nfrom app import main\n",
            "reverse legacy/main import is forbidden",
        ),
        (
            2,
            '\nfrom importlib import import_module as load\nload("".join(["legacy", "_app"]))\n',
            "reverse legacy/main import is forbidden",
        ),
        (
            2,
            '\nimport importlib\nload = importlib.import_module\nload("".join(["legacy", "_app"]))\n',
            "reverse legacy/main import is forbidden",
        ),
        (
            2,
            '\nfrom importlib import import_module\nimport_module(".main", package="app")\n',
            "reverse legacy/main import is forbidden",
        ),
        (
            2,
            '\nfrom importlib import import_module\nimport_module("..main", package="app.bootstrap")\n',
            "reverse legacy/main import is forbidden",
        ),
        (
            2,
            '\nmodule = __import__("app", fromlist=["main"]).main\n',
            "reverse legacy/main import is forbidden",
        ),
        (
            2,
            '\nimport importlib\nloader = getattr(importlib, "import_module")\nloader("legacy_app")\n',
            "reverse legacy/main import is forbidden",
        ),
        (
            2,
            '\ndef load():\n    loader = __import__\n    return loader("legacy_app")\n',
            "reverse legacy/main import is forbidden",
        ),
        (
            2,
            '\nfrom builtins import __import__ as loader\nloader("legacy_app")\n',
            "reverse legacy/main import is forbidden",
        ),
        (
            2,
            '\nimport builtins\nloader = getattr(builtins, "__import__")\nloader("legacy_app")\n',
            "reverse legacy/main import is forbidden",
        ),
        (
            2,
            '\nloader = __builtins__["__import__"]\nloader("legacy_app")\n',
            "reverse legacy/main import is forbidden",
        ),
        (
            2,
            '\nimport builtins\nloader = getattr(builtins, "__" + "import__")\nloader("legacy_app")\n',
            "reverse legacy/main import is forbidden",
        ),
        (
            2,
            '\nloader = __builtins__["".join(["__", "import__"])]\nloader("legacy_app")\n',
            "reverse legacy/main import is forbidden",
        ),
        (
            2,
            '\nmodule = __import__("app", fromlist=dynamic_fromlist)\n',
            "reverse legacy/main import is forbidden",
        ),
        (
            2,
            "\nfrom .. import main\n",
            "reverse legacy/main import is forbidden",
        ),
        (
            3,
            "\nfrom legacy_app import _install_openapi_builder\n",
            "OpenAPI symbol must not be imported through legacy",
        ),
        (
            3,
            "\nimport legacy_app as legacy\nlegacy._install_openapi_builder(app)\n",
            "OpenAPI symbol must not be accessed through legacy",
        ),
        (
            3,
            "\nimport legacy_app as legacy\ncompat = legacy\ncompat._install_openapi_builder(app)\n",
            "OpenAPI symbol must not be accessed through legacy",
        ),
        (
            3,
            '\nimport legacy_app as legacy\ncompat = legacy\ngetattr(compat, "_install_openapi_builder")(app)\n',
            "OpenAPI symbol must not be accessed through legacy",
        ),
        (
            3,
            '\ndef fetch():\n    if enabled:\n        import importlib as il\n        compat = il.import_module("legacy_app")\n        return compat._install_openapi_builder\n',
            "OpenAPI symbol must not be accessed through legacy",
        ),
        (
            3,
            '\ndef fetch():\n    import importlib as il\n    compat = il.import_module("legacy_app")\n    name = "_install_" + "openapi_builder"\n    return getattr(compat, name)\n',
            "OpenAPI symbol must not be accessed through legacy",
        ),
        (
            4,
            "\ninstaller = getattr(legacy, '_install_openapi_builder')\n",
            "legacy OpenAPI installer lookup is forbidden",
        ),
        (
            4,
            "\ninstaller = legacy._install_openapi_builder\n",
            "legacy OpenAPI installer lookup is forbidden",
        ),
        (
            4,
            '\nlegacy = _legacy()\ninstaller_name = "_install_" + "openapi_builder"\ninstaller = getattr(legacy, installer_name)\n',
            "legacy OpenAPI installer lookup is forbidden",
        ),
        (
            4,
            '\ninstaller_name = f"_install_openapi_builder"\ninstaller = getattr(_legacy(), installer_name)\n',
            "legacy OpenAPI installer lookup is forbidden",
        ),
        (
            4,
            '\ndef fetch():\n    name = "_install_" + "openapi_builder"\n    return getattr(_legacy(), name)\n',
            "legacy OpenAPI installer lookup is forbidden",
        ),
        (
            4,
            '\nnamespace = vars(_legacy())\ninstaller = namespace["_install_openapi_builder"]\n',
            "legacy OpenAPI installer lookup is forbidden",
        ),
        (
            4,
            '\nlegacy = _legacy()\ninstaller_name = "_install_openapi_builder"\ninstaller = vars(legacy)[installer_name]\n',
            "legacy OpenAPI installer lookup is forbidden",
        ),
        (
            4,
            '\nlegacy = _legacy()\ninstaller = vars(legacy).get("_install_openapi_builder")\n',
            "legacy OpenAPI installer lookup is forbidden",
        ),
        (
            4,
            "\nlegacy = _legacy()\ninstaller = vars(legacy).get(dynamic_name)\n",
            "legacy OpenAPI installer lookup is forbidden",
        ),
        (
            4,
            '\nlegacy = _legacy()\ninstaller = legacy.__dict__.__getitem__("_install_openapi_builder")\n',
            "legacy OpenAPI installer lookup is forbidden",
        ),
        (
            4,
            "\nsetattr(app, 'openapi', replacement)\n",
            "OpenAPI callable/cache mutation is forbidden",
        ),
        (
            4,
            '\napp.__dict__["openapi"] = replacement\n',
            "OpenAPI callable/cache mutation is forbidden",
        ),
        (
            4,
            '\nvars(app).update({"openapi": replacement})\n',
            "OpenAPI callable/cache mutation is forbidden",
        ),
        (
            4,
            '\nnamespace = vars(app)\nnamespace["openapi"] = replacement\n',
            "OpenAPI callable/cache mutation is forbidden",
        ),
        (
            4,
            '\nvars(app).pop("openapi")\n',
            "OpenAPI callable/cache mutation is forbidden",
        ),
        (
            4,
            "\nvars(app).clear()\n",
            "OpenAPI callable/cache mutation is forbidden",
        ),
        (
            4,
            '\nobject.__setattr__(app, "openapi", replacement)\n',
            "OpenAPI callable/cache mutation is forbidden",
        ),
        (
            4,
            "\napp.openapi_schema += replacement\n",
            "OpenAPI callable/cache mutation is forbidden",
        ),
    ],
)
def test_metadata_openapi_ownership_guard_rejects_reintroduction(
    source_index: int,
    addition: str,
    expected_fragment: str,
) -> None:
    sources = list(_openapi_ownership_sources())
    sources[source_index] += addition

    errors = legacy_guard.validate_application_metadata_openapi_ownership(*sources)

    assert any(expected_fragment in error for error in errors)


def test_metadata_openapi_ownership_guard_ignores_nested_local_rebinding() -> None:
    sources = list(_openapi_ownership_sources())
    sources[0] += textwrap.dedent("""
        def helper():
            _collect_schema_refs = object()
            return _collect_schema_refs
        """)

    errors = legacy_guard.validate_application_metadata_openapi_ownership(*sources)

    assert errors == []


def test_metadata_openapi_ownership_guard_ignores_facade_comment_and_docstring() -> None:
    sources = list(_openapi_ownership_sources())
    sources[4] += textwrap.dedent('''
        """Do not restore the legacy _install_openapi_builder lookup."""
        # _install_openapi_builder is intentionally absent.
        ''')

    errors = legacy_guard.validate_application_metadata_openapi_ownership(*sources)

    assert errors == []


def test_metadata_openapi_ownership_guard_allows_unrelated_relative_main_symbol() -> None:
    sources = list(_openapi_ownership_sources())
    sources[2] += "\nfrom .helpers import main\n"

    errors = legacy_guard.validate_application_metadata_openapi_ownership(*sources)

    assert errors == []


def test_metadata_openapi_ownership_guard_rejects_dynamic_import_in_canonical_owner() -> None:
    sources = list(_openapi_ownership_sources())
    sources[2] += textwrap.dedent("""
        from importlib import import_module
        import_module(".helpers", package="app.bootstrap")
        """)

    errors = legacy_guard.validate_application_metadata_openapi_ownership(*sources)

    assert errors == ["app/bootstrap/openapi.py: reverse legacy/main import is forbidden"]


def test_metadata_openapi_ownership_guard_allows_unrelated_namespace_mutations() -> None:
    sources = list(_openapi_ownership_sources())
    sources[0] += '\nglobals().pop("unrelated", None)\n'
    sources[4] += '\nvars(app).setdefault("unrelated", value)\n'

    errors = legacy_guard.validate_application_metadata_openapi_ownership(*sources)

    assert errors == []


def test_metadata_openapi_ownership_guard_allows_other_module_alias() -> None:
    sources = list(_openapi_ownership_sources())
    sources[0] += textwrap.dedent("""
        import sys as system
        other_module = system.modules["app"]
        value = other_module.__name__
        """)

    errors = legacy_guard.validate_application_metadata_openapi_ownership(*sources)

    assert errors == []


def test_metadata_openapi_ownership_guard_respects_safe_alias_reassignment() -> None:
    sources = list(_openapi_ownership_sources())
    sources[0] += textwrap.dedent("""
        import sys as system
        current_module = system.modules[__name__]
        current_module = object()
        assign = setattr
        installer_name = "_install_" + "openapi_builder"
        assign(current_module, installer_name, replacement)
        """)

    errors = legacy_guard.validate_application_metadata_openapi_ownership(*sources)

    assert errors == []


def test_metadata_openapi_ownership_guard_respects_nested_alias_shadowing() -> None:
    sources = list(_openapi_ownership_sources())
    sources[0] += textwrap.dedent("""
        import sys as system
        current_module = system.modules[__name__]
        assign = setattr

        def configure_unrelated_object():
            current_module = object()
            installer_name = "_install_" + "openapi_builder"
            assign(current_module, installer_name, replacement)
        """)

    errors = legacy_guard.validate_application_metadata_openapi_ownership(*sources)

    assert errors == []


@pytest.mark.parametrize(
    "main_addition",
    [
        textwrap.dedent("""
            import legacy_app as legacy
            compat = legacy
            compat = object()
            value = compat._install_openapi_builder
            """),
        textwrap.dedent("""
            import legacy_app as legacy
            compat = object()
            value = getattr(compat, "_install_openapi_builder")
            compat = legacy
            """),
    ],
    ids=["safe-reassignment", "lookup-before-legacy-assignment"],
)
def test_metadata_openapi_ownership_guard_allows_ordered_alias_controls(
    main_addition: str,
) -> None:
    sources = list(_openapi_ownership_sources())
    sources[3] += main_addition

    errors = legacy_guard.validate_application_metadata_openapi_ownership(*sources)

    assert errors == []


def test_metadata_openapi_ownership_guard_rejects_lookup_before_safe_reassignment() -> None:
    sources = list(_openapi_ownership_sources())
    sources[3] += textwrap.dedent("""
        import legacy_app as legacy
        compat = legacy
        value = getattr(compat, "_install_openapi_builder")
        compat = object()
        """)

    errors = legacy_guard.validate_application_metadata_openapi_ownership(*sources)

    assert errors == ["app/main.py: OpenAPI symbol must not be accessed through legacy"]


@pytest.mark.parametrize(
    ("mutation_kind", "expected_fragment"),
    [
        (
            "missing_metadata_factory",
            "canonical application metadata factory import is required",
        ),
        (
            "legacy_openapi_mutation",
            "OpenAPI callable/cache mutation is forbidden",
        ),
    ],
)
def test_metadata_openapi_ownership_guard_rejects_missing_legacy_contracts(
    mutation_kind: str,
    expected_fragment: str,
) -> None:
    sources = list(_openapi_ownership_sources())
    if mutation_kind == "missing_metadata_factory":
        sources[0] = sources[0].replace(
            "from app.application_metadata import build_application_metadata\n",
            "",
        )
    else:
        sources[0] += "\nsetattr(app, 'openapi', replacement)\n"

    errors = legacy_guard.validate_application_metadata_openapi_ownership(*sources)

    assert any(expected_fragment in error for error in errors)


def test_metadata_openapi_ownership_guard_fails_closed_on_syntax_error() -> None:
    sources = list(_openapi_ownership_sources())
    sources[2] = "def broken(:\n"

    errors = legacy_guard.validate_application_metadata_openapi_ownership(*sources)

    assert errors == ["app/bootstrap/openapi.py:1: syntax error: invalid syntax"]


@pytest.mark.parametrize("symbol", _CONSOL_API_KEY_SYMBOLS)
@pytest.mark.parametrize("keyword", ["def", "async def"], ids=["function", "async-function"])
def test_api_key_ownership_guard_rejects_legacy_implementation(symbol: str, keyword: str) -> None:
    legacy_source = (
        "from app.routers.api_key import (\n"
        "    _get_api_key_dynamic as _get_api_key_dynamic,\n"
        "    get_api_key as get_api_key,\n"
        ")\n"
        f"{keyword} {symbol}():\n    return 'legacy'\n"
    )

    errors = _validate_api_key_dependency_ownership(legacy_source, {})

    assert errors == [f"legacy_app.py: API-key dependency must not be defined locally: {symbol}"]


@pytest.mark.parametrize("symbol", _CONSOL_API_KEY_SYMBOLS)
@pytest.mark.parametrize(
    "rebind_statement",
    [
        "{symbol} = replacement",
        "{symbol}: object = replacement",
        "{symbol} += replacement",
        "({symbol} := replacement)",
    ],
    ids=["assign", "annotated-assign", "augmented-assign", "named-expression"],
)
def test_api_key_ownership_guard_rejects_legacy_rebinding(
    symbol: str,
    rebind_statement: str,
) -> None:
    legacy_source = (
        "from app.routers.api_key import (\n"
        "    _get_api_key_dynamic as _get_api_key_dynamic,\n"
        "    get_api_key as get_api_key,\n"
        ")\n"
        "replacement = object()\n"
        f"{rebind_statement.format(symbol=symbol)}\n"
    )

    errors = _validate_api_key_dependency_ownership(legacy_source, {})

    assert errors == [_CONSOL_API_KEY_REBINDING_ERRORS[symbol]]


@pytest.mark.parametrize(
    "rebind_statement",
    [
        "import other as get_api_key",
        "for get_api_key in values:\n    pass",
        "if enabled:\n    get_api_key = replacement",
        "with context() as get_api_key:\n    pass",
        "try:\n    pass\nexcept Exception as get_api_key:\n    pass",
    ],
    ids=["import", "for", "conditional", "with", "except"],
)
def test_api_key_ownership_guard_rejects_bounded_module_bindings(
    rebind_statement: str,
) -> None:
    legacy_source = (
        "from app.routers.api_key import (\n"
        "    _get_api_key_dynamic,\n"
        "    get_api_key,\n"
        ")\n"
        f"{rebind_statement}\n"
    )

    assert _validate_api_key_dependency_ownership(legacy_source, {}) == [
        "legacy_app.py: canonical API-key compatibility re-export must not be rebound: get_api_key"
    ]


def test_api_key_ownership_guard_allows_nested_local_binding() -> None:
    legacy_source = (
        "from app.routers.api_key import (\n"
        "    _get_api_key_dynamic,\n"
        "    get_api_key,\n"
        ")\n"
        "def local_scope():\n"
        "    local_value = object()\n"
        "    return local_value\n"
    )

    assert _validate_api_key_dependency_ownership(legacy_source, {}) == []


@pytest.mark.parametrize("keyword", ["def", "async def"])
@pytest.mark.parametrize("symbol", _CONSOL_API_KEY_SYMBOLS)
def test_api_key_ownership_guard_allows_nested_local_function(
    keyword: str,
    symbol: str,
) -> None:
    legacy_source = (
        "from app.routers.api_key import (\n"
        "    _get_api_key_dynamic,\n"
        "    get_api_key,\n"
        ")\n"
        "def local_scope():\n"
        f"    {keyword} {symbol}():\n"
        "        return 'local'\n"
        f"    return {symbol}\n"
    )

    assert _validate_api_key_dependency_ownership(legacy_source, {}) == []


@pytest.mark.parametrize("keyword", ["def", "async def"])
@pytest.mark.parametrize("symbol", _CONSOL_API_KEY_SYMBOLS)
@pytest.mark.parametrize(
    "compound_template",
    [
        "if enabled:\n    {definition}",
        "try:\n    {definition}\nexcept Exception:\n    pass",
        "with context():\n    {definition}",
        "for item in values:\n    {definition}",
    ],
    ids=["if", "try", "with", "for"],
)
def test_api_key_ownership_guard_rejects_conditional_module_definitions(
    keyword: str,
    symbol: str,
    compound_template: str,
) -> None:
    definition = f"{keyword} {symbol}():\n        return 'legacy'"
    legacy_source = (
        "from app.routers.api_key import _get_api_key_dynamic, get_api_key\n"
        "enabled = True\nvalues = [object()]\n"
        "class context:\n"
        "    def __enter__(self): return self\n"
        "    def __exit__(self, *args): return False\n"
        f"{compound_template.format(definition=definition)}\n"
    )

    assert _validate_api_key_dependency_ownership(legacy_source, {}) == [
        f"legacy_app.py: API-key dependency must not be defined locally: {symbol}"
    ]


def test_legacy_growth_guard_rejects_api_key_header_reintroduction() -> None:
    errors = legacy_guard.validate_legacy_growth("from app.routers.api_key import api_key_header\n")

    assert errors == [
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:app.routers.api_key:api_key_header"
    ]


@pytest.mark.parametrize("symbol", _CONSOL_API_KEY_SYMBOLS)
def test_api_key_ownership_guard_rejects_reverse_import(symbol: str) -> None:
    legacy_source = (
        "from app.routers.api_key import (\n"
        "    _get_api_key_dynamic as _get_api_key_dynamic,\n"
        "    get_api_key as get_api_key,\n"
        ")\n"
    )

    errors = _validate_api_key_dependency_ownership(
        legacy_source,
        {"app/routers/example.py": f"from legacy_app import {symbol}\n"},
    )

    assert errors == [
        "app/routers/example.py: canonical code must import API-key dependency "
        f"from app/routers/api_key.py, not legacy_app: {symbol}"
    ]


def test_api_key_ownership_guard_rejects_dynamic_legacy_lookup() -> None:
    legacy_source = (
        "from app.routers.api_key import (\n"
        "    _get_api_key_dynamic as _get_api_key_dynamic,\n"
        "    get_api_key as get_api_key,\n"
        ")\n"
    )

    errors = _validate_api_key_dependency_ownership(
        legacy_source,
        {
            "app/main.py": (
                "import legacy_app as legacy\n"
                'dependency = getattr(legacy, "_get_api_key_dynamic", None)\n'
            )
        },
    )

    assert errors == [
        "app/main.py: dynamic legacy API-key dependency lookup is forbidden: _get_api_key_dynamic"
    ]


@pytest.mark.parametrize("symbol", _CONSOL_API_KEY_SYMBOLS)
def test_api_key_ownership_guard_rejects_legacy_module_attribute_access(symbol: str) -> None:
    legacy_source = (
        "from app.routers.api_key import (\n"
        "    _get_api_key_dynamic as _get_api_key_dynamic,\n"
        "    get_api_key as get_api_key,\n"
        ")\n"
    )

    errors = _validate_api_key_dependency_ownership(
        legacy_source,
        {"app/main.py": f"import legacy_app as legacy\ndependency = legacy.{symbol}\n"},
    )

    assert errors == [
        f"app/main.py: legacy API-key dependency attribute access is forbidden: {symbol}"
    ]


def test_api_key_ownership_guard_rejects_legacy_star_import() -> None:
    legacy_source = (
        "from app.routers.api_key import (\n    _get_api_key_dynamic,\n    get_api_key,\n)\n"
    )

    assert _validate_api_key_dependency_ownership(
        legacy_source,
        {"app/main.py": "from legacy_app import *\ndependency = get_api_key\n"},
    ) == ["app/main.py: canonical code must not use a legacy_app star import"]


def test_api_key_ownership_guard_rejects_legacy_namespace_lookup() -> None:
    legacy_source = "from app.routers.api_key import _get_api_key_dynamic, get_api_key\n"
    source = 'import legacy_app as legacy\ndependency = legacy.__dict__["get_api_key"]\n'

    assert _validate_api_key_dependency_ownership(
        legacy_source,
        {"app/main.py": source},
    ) == ["app/main.py: legacy API-key dependency namespace lookup is forbidden: get_api_key"]


def test_api_key_ownership_guard_allows_unrelated_star_import() -> None:
    legacy_source = (
        "from app.routers.api_key import (\n    _get_api_key_dynamic,\n    get_api_key,\n)\n"
    )

    assert (
        _validate_api_key_dependency_ownership(
            legacy_source,
            {"app/main.py": "from unrelated_module import *\n"},
        )
        == []
    )


@pytest.mark.parametrize(
    "source",
    [
        (
            "import importlib\n"
            'dependency = getattr(importlib.import_module("legacy_app"), '
            '"_get_api_key_dynamic", None)\n'
        ),
        (
            "from importlib import import_module as load_module\n"
            'dependency = getattr(load_module("legacy_app"), "get_api_key", None)\n'
        ),
    ],
)
def test_api_key_ownership_guard_rejects_dynamic_import_legacy_lookup(source: str) -> None:
    legacy_source = (
        "from app.routers.api_key import (\n"
        "    _get_api_key_dynamic as _get_api_key_dynamic,\n"
        "    get_api_key as get_api_key,\n"
        ")\n"
    )

    errors = _validate_api_key_dependency_ownership(
        legacy_source,
        {"app/main.py": source},
    )

    expected_symbol = "_get_api_key_dynamic" if "_get_api_key_dynamic" in source else "get_api_key"
    assert errors == [
        f"app/main.py: dynamic legacy API-key dependency lookup is forbidden: {expected_symbol}"
    ]


@pytest.mark.parametrize(
    ("source", "expected_error"),
    [
        (
            "def dependency():\n"
            "    import legacy_app as legacy\n"
            "    return legacy.get_api_key\n",
            "app/main.py: legacy API-key dependency attribute access is forbidden: get_api_key",
        ),
        (
            "def dependency():\n"
            "    import importlib as il\n"
            '    return getattr(il.import_module("legacy_app"), "get_api_key")\n',
            "app/main.py: dynamic legacy API-key dependency lookup is forbidden: get_api_key",
        ),
        (
            "def dependency():\n"
            "    from importlib import import_module as load\n"
            '    return getattr(load("legacy_app"), "_get_api_key_dynamic")\n',
            "app/main.py: dynamic legacy API-key dependency lookup is forbidden: "
            "_get_api_key_dynamic",
        ),
        (
            "def dependency():\n" "    import legacy_app\n" "    return legacy_app.get_api_key\n",
            "app/main.py: legacy API-key dependency attribute access is forbidden: get_api_key",
        ),
        (
            "def dependency():\n"
            "    import importlib as il\n"
            '    legacy = il.import_module("legacy_app")\n'
            "    return legacy.get_api_key\n",
            "app/main.py: legacy API-key dependency attribute access is forbidden: get_api_key",
        ),
    ],
    ids=[
        "nested-module-alias",
        "nested-importlib-direct",
        "nested-import-from",
        "nested-module-plain",
        "nested-importlib-intermediate",
    ],
)
def test_api_key_ownership_guard_rejects_nested_legacy_aliases(
    source: str,
    expected_error: str,
) -> None:
    legacy_source = "from app.routers.api_key import _get_api_key_dynamic, get_api_key\n"

    assert _validate_api_key_dependency_ownership(
        legacy_source,
        {"app/main.py": source},
    ) == [expected_error]


def test_api_key_ownership_guard_respects_parameter_shadowing_and_sibling_scopes() -> None:
    legacy_source = "from app.routers.api_key import _get_api_key_dynamic, get_api_key\n"
    source = textwrap.dedent("""
        import legacy_app as legacy

        def safe(legacy):
            return legacy.get_api_key

        def unsafe():
            import legacy_app as compat
            return compat._get_api_key_dynamic
        """)
    expected = [
        "app/main.py: legacy API-key dependency attribute access is forbidden: "
        "_get_api_key_dynamic"
    ]

    assert (
        _validate_api_key_dependency_ownership(legacy_source, {"app/main.py": source}) == expected
    )
    assert (
        _validate_api_key_dependency_ownership(legacy_source, {"app/main.py": source}) == expected
    )


def test_api_key_ownership_guard_rejects_maybe_legacy_conditional_alias() -> None:
    legacy_source = "from app.routers.api_key import _get_api_key_dynamic, get_api_key\n"
    source = "if enabled:\n" "    import legacy_app as legacy\n" "dependency = legacy.get_api_key\n"

    assert _validate_api_key_dependency_ownership(legacy_source, {"app/main.py": source}) == [
        "app/main.py: legacy API-key dependency attribute access is forbidden: get_api_key"
    ]


def test_api_key_ownership_guard_transfers_legacy_loop_target() -> None:
    legacy_source = "from app.routers.api_key import _get_api_key_dynamic, get_api_key\n"
    source = (
        "import importlib\n"
        'for legacy in [importlib.import_module("legacy_app")]:\n'
        "    dependency = legacy.get_api_key\n"
    )

    assert _validate_api_key_dependency_ownership(legacy_source, {"app/main.py": source}) == [
        "app/main.py: legacy API-key dependency attribute access is forbidden: get_api_key"
    ]


@pytest.mark.parametrize(
    "source",
    [
        textwrap.dedent("""
            import legacy_app as legacy
            for _ in [1]:
                alias = legacy
                break
                alias = object()
            else:
                alias = object()
            value = alias.get_api_key
            """),
        textwrap.dedent("""
            import legacy_app as legacy
            for _ in [1]:
                alias = legacy
                continue
                alias = object()
            else:
                pass
            value = alias.get_api_key
            """),
        textwrap.dedent("""
            import legacy_app as legacy
            while enabled:
                alias = legacy
                break
                alias = object()
            else:
                alias = object()
            value = alias.get_api_key
            """),
        textwrap.dedent("""
            async def dependency(values):
                import legacy_app as legacy
                async for _ in values:
                    alias = legacy
                    break
                    alias = object()
                else:
                    alias = object()
                return alias.get_api_key
            """),
        textwrap.dedent("""
            import legacy_app as legacy
            a = b = object()
            for index in [1, 2, 3]:
                if index == 3:
                    break
                a = b
                b = legacy
            else:
                a = object()
            value = a.get_api_key
            """),
        textwrap.dedent("""
            import legacy_app as legacy
            alias = carried = object()
            while (alias := carried):
                carried = legacy
                if stop:
                    break
            else:
                alias = object()
            value = alias.get_api_key
            """),
        textwrap.dedent("""
            import legacy_app as legacy
            values = []
            for _ in [*values]:
                alias = object()
                break
            else:
                alias = legacy
            value = alias.get_api_key
            """),
    ],
    ids=[
        "for-break",
        "for-continue",
        "while-break",
        "async-for-break",
        "for-loop-carried-two-hop",
        "while-condition-loop-carried",
        "for-starred-may-be-empty",
    ],
)
def test_api_key_ownership_guard_preserves_loop_control_aliases(source: str) -> None:
    legacy_source = "from app.routers.api_key import _get_api_key_dynamic, get_api_key\n"

    assert _validate_api_key_dependency_ownership(legacy_source, {"app/main.py": source}) == [
        "app/main.py: legacy API-key dependency attribute access is forbidden: get_api_key"
    ]


def test_api_key_ownership_guard_applies_finally_to_loop_break_alias() -> None:
    legacy_source = "from app.routers.api_key import _get_api_key_dynamic, get_api_key\n"
    source = textwrap.dedent("""
        import legacy_app as legacy
        for _ in [1]:
            alias = object()
            try:
                break
            finally:
                alias = legacy
            alias = object()
        else:
            alias = object()
        value = alias.get_api_key
        """)

    assert _validate_api_key_dependency_ownership(
        legacy_source,
        {"app/main.py": source},
    ) == ["app/main.py: legacy API-key dependency attribute access is forbidden: get_api_key"]


def test_api_key_ownership_guard_allows_finally_to_clear_loop_break_alias() -> None:
    legacy_source = "from app.routers.api_key import _get_api_key_dynamic, get_api_key\n"
    source = textwrap.dedent("""
        import legacy_app as legacy
        for _ in [1]:
            alias = legacy
            try:
                break
            finally:
                alias = object()
            alias = legacy
        else:
            alias = object()
        value = alias.get_api_key
        """)

    assert (
        _validate_api_key_dependency_ownership(
            legacy_source,
            {"app/main.py": source},
        )
        == []
    )


@pytest.mark.parametrize(
    "source",
    [
        textwrap.dedent("""
            import legacy_app as legacy
            for _ in [1]:
                alias = legacy
                continue
            else:
                alias = object()
            value = alias.get_api_key
            """),
        textwrap.dedent("""
            import legacy_app as legacy
            for _ in [1]:
                alias = legacy
                for _inner in [1]:
                    break
            else:
                alias = object()
            value = alias.get_api_key
            """),
        textwrap.dedent("""
            import legacy_app as legacy
            for _ in [1]:
                alias = object()
                break
                alias = legacy
            value = alias.get_api_key
            """),
        textwrap.dedent("""
            import legacy_app as legacy
            for _ in [1]:
                alias = object()
                continue
                alias = legacy
            else:
                alias = object()
            value = alias.get_api_key
            """),
        textwrap.dedent("""
            import legacy_app as legacy
            for _ in [1]:
                alias = object()
                break
            else:
                alias = legacy
            value = alias.get_api_key
            """),
    ],
    ids=[
        "normal-continue-exhaustion",
        "nested-loop-break",
        "unreachable-after-break",
        "unreachable-after-continue",
        "unreachable-else",
    ],
)
def test_api_key_ownership_guard_preserves_loop_control_precision(source: str) -> None:
    legacy_source = "from app.routers.api_key import _get_api_key_dynamic, get_api_key\n"

    assert (
        _validate_api_key_dependency_ownership(
            legacy_source,
            {"app/main.py": source},
        )
        == []
    )


@pytest.mark.parametrize(
    "source",
    [
        textwrap.dedent("""
            import legacy_app as legacy
            alias = object()
            for _ in [1]:
                match value:
                    case _:
                        break
            else:
                alias = legacy
            value = alias.get_api_key
            """),
        textwrap.dedent("""
            import legacy_app as legacy
            alias = object()
            for _ in [1]:
                match value:
                    case captured:
                        continue
                alias = legacy
            value = alias.get_api_key
            """),
    ],
    ids=["wildcard-break", "capture-continue"],
)
def test_api_key_ownership_guard_respects_exhaustive_match_loop_control(
    source: str,
) -> None:
    legacy_source = "from app.routers.api_key import _get_api_key_dynamic, get_api_key\n"

    assert (
        _validate_api_key_dependency_ownership(
            legacy_source,
            {"app/main.py": source},
        )
        == []
    )


def test_api_key_ownership_guard_keeps_guarded_match_fallthrough() -> None:
    legacy_source = "from app.routers.api_key import _get_api_key_dynamic, get_api_key\n"
    source = textwrap.dedent("""
        import legacy_app as legacy
        alias = object()
        for _ in [1]:
            match value:
                case _ if enabled:
                    break
            alias = legacy
        value = alias.get_api_key
        """)

    assert _validate_api_key_dependency_ownership(
        legacy_source,
        {"app/main.py": source},
    ) == ["app/main.py: legacy API-key dependency attribute access is forbidden: get_api_key"]


def test_api_key_ownership_guard_visits_match_value_patterns() -> None:
    legacy_source = "from app.routers.api_key import _get_api_key_dynamic, get_api_key\n"
    source = textwrap.dedent("""
        import legacy_app as legacy

        match value:
            case legacy.get_api_key:
                pass
        """)

    assert _validate_api_key_dependency_ownership(
        legacy_source,
        {"app/main.py": source},
    ) == ["app/main.py: legacy API-key dependency attribute access is forbidden: get_api_key"]


def test_api_key_ownership_guard_carries_failed_match_guard_side_effects() -> None:
    legacy_source = "from app.routers.api_key import _get_api_key_dynamic, get_api_key\n"
    source = textwrap.dedent("""
        import legacy_app as legacy
        alias = object()

        match subject:
            case _ if (alias := legacy) is None:
                pass
            case _:
                value = alias.get_api_key
        """)

    assert _validate_api_key_dependency_ownership(
        legacy_source,
        {"app/main.py": source},
    ) == ["app/main.py: legacy API-key dependency attribute access is forbidden: get_api_key"]


def test_api_key_ownership_guard_transfers_match_capture_subject() -> None:
    legacy_source = "from app.routers.api_key import _get_api_key_dynamic, get_api_key\n"
    source = textwrap.dedent("""
        import legacy_app as legacy

        match legacy:
            case captured:
                value = captured.get_api_key
        """)

    assert _validate_api_key_dependency_ownership(
        legacy_source,
        {"app/main.py": source},
    ) == ["app/main.py: legacy API-key dependency attribute access is forbidden: get_api_key"]


@pytest.mark.parametrize(
    "match_statement",
    [
        textwrap.dedent("""
            match {"module": legacy}:
                case {"module": alias}:
                    value = alias.get_api_key
            """),
        textwrap.dedent("""
            match [legacy]:
                case [alias]:
                    value = alias.get_api_key
            """),
    ],
    ids=["mapping", "sequence"],
)
def test_api_key_ownership_guard_transfers_nested_match_capture(
    match_statement: str,
) -> None:
    legacy_source = "from app.routers.api_key import _get_api_key_dynamic, get_api_key\n"
    source = "import legacy_app as legacy\n" + match_statement

    assert _validate_api_key_dependency_ownership(
        legacy_source,
        {"app/main.py": source},
    ) == ["app/main.py: legacy API-key dependency attribute access is forbidden: get_api_key"]


def test_api_key_ownership_guard_treats_match_mapping_rest_as_local_binding() -> None:
    legacy_source = "from app.routers.api_key import _get_api_key_dynamic, get_api_key\n"
    source = textwrap.dedent("""
        import legacy_app as alias

        def dependency(payload):
            match payload:
                case {**alias}:
                    return alias.get_api_key
        """)

    assert (
        _validate_api_key_dependency_ownership(
            legacy_source,
            {"app/main.py": source},
        )
        == []
    )


@pytest.mark.parametrize(
    ("guard", "body", "tail", "expected"),
    [
        (
            "True",
            "break",
            "alias = legacy",
            [],
        ),
        (
            "False",
            "value = legacy.get_api_key",
            "alias = object()",
            [],
        ),
    ],
)
def test_api_key_ownership_guard_respects_constant_match_guards(
    guard: str,
    body: str,
    tail: str,
    expected: list[str],
) -> None:
    legacy_source = "from app.routers.api_key import _get_api_key_dynamic, get_api_key\n"
    source = textwrap.dedent(f"""
        import legacy_app as legacy
        alias = object()
        for _ in [1]:
            match subject:
                case _ if {guard}:
                    {body}
            {tail}
        value = alias.get_api_key
        """)

    assert (
        _validate_api_key_dependency_ownership(
            legacy_source,
            {"app/main.py": source},
        )
        == expected
    )


@pytest.mark.parametrize(
    ("final_action", "expected"),
    [
        ("continue", []),
        (
            "break",
            ["app/main.py: legacy API-key dependency attribute access is forbidden: get_api_key"],
        ),
    ],
)
def test_api_key_ownership_guard_applies_finally_control_override(
    final_action: str,
    expected: list[str],
) -> None:
    pending_action = "break" if final_action == "continue" else "continue"
    legacy_source = "from app.routers.api_key import _get_api_key_dynamic, get_api_key\n"
    source = textwrap.dedent(f"""
        import legacy_app as legacy
        alias = legacy
        for _ in [1]:
            try:
                {pending_action}
            finally:
                {final_action}
        else:
            alias = object()
        value = alias.get_api_key
        """)

    assert (
        _validate_api_key_dependency_ownership(
            legacy_source,
            {"app/main.py": source},
        )
        == expected
    )


@pytest.mark.parametrize(
    "source",
    [
        textwrap.dedent("""
            while False:
                import legacy_app as legacy
                value = legacy.get_api_key
            """),
        textwrap.dedent("""
            for _ in []:
                import legacy_app as legacy
                value = legacy.get_api_key
            """),
        textwrap.dedent("""
            for _ in ():
                import legacy_app as legacy
                value = legacy.get_api_key
            """),
        textwrap.dedent("""
            def dependency():
                return None
                import legacy_app as legacy
                return legacy.get_api_key
            """),
        textwrap.dedent("""
            def dependency():
                raise RuntimeError
                import legacy_app as legacy
                return legacy.get_api_key
            """),
    ],
    ids=["while-false", "empty-list", "empty-tuple", "return", "raise"],
)
def test_api_key_ownership_guard_ignores_statically_unreachable_aliases(source: str) -> None:
    legacy_source = "from app.routers.api_key import _get_api_key_dynamic, get_api_key\n"

    assert (
        _validate_api_key_dependency_ownership(
            legacy_source,
            {"app/main.py": source},
        )
        == []
    )


@pytest.mark.parametrize("terminal", ["return None", "raise RuntimeError"])
def test_api_key_ownership_guard_replays_terminal_state_through_finally(
    terminal: str,
) -> None:
    legacy_source = "from app.routers.api_key import _get_api_key_dynamic, get_api_key\n"
    source = textwrap.dedent(f"""
        def dependency():
            import legacy_app as legacy
            try:
                alias = legacy
                {terminal}
            finally:
                value = alias.get_api_key
        """)

    assert _validate_api_key_dependency_ownership(
        legacy_source,
        {"app/main.py": source},
    ) == ["app/main.py: legacy API-key dependency attribute access is forbidden: get_api_key"]


@pytest.mark.parametrize(
    ("try_action", "finally_action", "expected"),
    [
        ("break", "return None", []),
        (
            "return None",
            "break",
            ["app/main.py: legacy API-key dependency attribute access is forbidden: get_api_key"],
        ),
    ],
)
def test_api_key_ownership_guard_applies_terminal_finally_override(
    try_action: str,
    finally_action: str,
    expected: list[str],
) -> None:
    legacy_source = "from app.routers.api_key import _get_api_key_dynamic, get_api_key\n"
    source = textwrap.dedent(f"""
        def dependency():
            import legacy_app as legacy
            for _ in [1]:
                try:
                    {try_action}
                finally:
                    {finally_action}
            value = legacy.get_api_key
        """)

    assert (
        _validate_api_key_dependency_ownership(
            legacy_source,
            {"app/main.py": source},
        )
        == expected
    )


@pytest.mark.parametrize(
    ("handler", "expect_violation"),
    [("except:", False), ("except TypeError:", True)],
)
def test_api_key_ownership_guard_distinguishes_provably_caught_raise_paths(
    handler: str, expect_violation: bool
) -> None:
    legacy_source = "from app.routers.api_key import _get_api_key_dynamic, get_api_key\n"
    source = textwrap.dedent(f"""
        def dependency():
            alias = object()
            try:
                import legacy_app as legacy
                alias = legacy
                raise ValueError()
            {handler}
                alias = None
            finally:
                value = alias.get_api_key
        """)
    actual = _validate_api_key_dependency_ownership(
        legacy_source,
        {"app/main.py": source},
    )

    if expect_violation:
        assert actual == [
            "app/main.py: legacy API-key dependency attribute access is forbidden: get_api_key"
        ]
    else:
        assert actual == []


@pytest.mark.parametrize(
    "try_body",
    [
        textwrap.dedent("""
            if flag:
                import legacy_app as legacy
                alias = legacy
                return dangerous()
            """),
        textwrap.dedent("""
            import legacy_app as legacy
            alias = legacy
            dangerous()
            alias = object()
            """),
    ],
    ids=["branch-return-value", "intermediate-call"],
)
def test_api_key_ownership_guard_preserves_try_exception_entry_state(
    try_body: str,
) -> None:
    legacy_source = "from app.routers.api_key import _get_api_key_dynamic, get_api_key\n"
    indented_body = textwrap.indent(try_body, " " * 8)
    source = (
        "def dependency():\n"
        "    alias = object()\n"
        "    try:\n"
        f"{indented_body}"
        "    except Exception:\n"
        "        value = alias.get_api_key\n"
    )

    assert _validate_api_key_dependency_ownership(
        legacy_source,
        {"app/main.py": source},
    ) == ["app/main.py: legacy API-key dependency attribute access is forbidden: get_api_key"]


@pytest.mark.parametrize(
    "source",
    [
        textwrap.dedent("""
            def dependency():
                alias = object()
                try:
                    import legacy_app as legacy
                    alias = legacy
                    dangerous()
                    alias = object()
                finally:
                    value = alias.get_api_key
            """),
        textwrap.dedent("""
            def dependency():
                alias = object()
                try:
                    dangerous()
                except Exception:
                    import legacy_app as legacy
                    alias = legacy
                    dangerous()
                    alias = object()
                finally:
                    value = alias.get_api_key
            """),
        textwrap.dedent("""
            def dependency():
                alias = object()
                try:
                    pass
                except Exception:
                    pass
                else:
                    import legacy_app as legacy
                    alias = legacy
                    dangerous()
                    alias = object()
                finally:
                    value = alias.get_api_key
            """),
    ],
    ids=["try-body", "handler-body", "else-body"],
)
def test_api_key_ownership_guard_replays_implicit_exceptions_through_finally(
    source: str,
) -> None:
    legacy_source = "from app.routers.api_key import _get_api_key_dynamic, get_api_key\n"

    assert _validate_api_key_dependency_ownership(
        legacy_source,
        {"app/main.py": source},
    ) == ["app/main.py: legacy API-key dependency attribute access is forbidden: get_api_key"]


def test_api_key_ownership_guard_visits_exception_handler_type() -> None:
    legacy_source = "from app.routers.api_key import _get_api_key_dynamic, get_api_key\n"
    source = textwrap.dedent("""
        import legacy_app as legacy

        try:
            dangerous()
        except legacy.get_api_key:
            pass
        """)

    assert _validate_api_key_dependency_ownership(
        legacy_source,
        {"app/main.py": source},
    ) == ["app/main.py: legacy API-key dependency attribute access is forbidden: get_api_key"]


@pytest.mark.parametrize(
    "source",
    [
        textwrap.dedent("""
            import legacy_app as legacy
            alias, other = legacy, object()
            value = alias.get_api_key
            """),
        textwrap.dedent("""
            import legacy_app as legacy
            for alias in [legacy, object()]:
                value = alias.get_api_key
            """),
        textwrap.dedent("""
            import legacy_app as legacy
            for alias, other in [(legacy, object())]:
                value = alias.get_api_key
            """),
        textwrap.dedent("""
            import legacy_app as legacy
            values = [alias.get_api_key for alias in [legacy]]
            """),
        textwrap.dedent("""
            import legacy_app as legacy
            values = [(alias := legacy) for _ in [1]]
            value = alias.get_api_key
            """),
    ],
    ids=[
        "assignment-destructure",
        "multi-element-loop",
        "loop-destructure",
        "comprehension-target",
        "comprehension-walrus",
    ],
)
def test_api_key_ownership_guard_transfers_structural_bindings(source: str) -> None:
    legacy_source = "from app.routers.api_key import _get_api_key_dynamic, get_api_key\n"

    assert _validate_api_key_dependency_ownership(
        legacy_source,
        {"app/main.py": source},
    ) == ["app/main.py: legacy API-key dependency attribute access is forbidden: get_api_key"]


@pytest.mark.parametrize("function_keyword", ["def", "async def"])
def test_api_key_ownership_guard_visits_parameter_annotations(
    function_keyword: str,
) -> None:
    legacy_source = "from app.routers.api_key import _get_api_key_dynamic, get_api_key\n"
    source = (
        "import legacy_app as legacy\n"
        f"{function_keyword} dependency(value: legacy.get_api_key):\n"
        "    pass\n"
    )

    assert _validate_api_key_dependency_ownership(
        legacy_source,
        {"app/main.py": source},
    ) == ["app/main.py: legacy API-key dependency attribute access is forbidden: get_api_key"]


def test_api_key_ownership_guard_joins_conditional_expression_alias() -> None:
    legacy_source = "from app.routers.api_key import _get_api_key_dynamic, get_api_key\n"
    source = textwrap.dedent("""
        import legacy_app as legacy
        alias = legacy if enabled else object()
        value = alias.get_api_key
        """)

    assert _validate_api_key_dependency_ownership(
        legacy_source,
        {"app/main.py": source},
    ) == ["app/main.py: legacy API-key dependency attribute access is forbidden: get_api_key"]


@pytest.mark.parametrize(
    "source",
    [
        textwrap.dedent("""
            alias = object()
            def dependency():
                return alias.get_api_key
            import legacy_app as alias
            """),
        textwrap.dedent("""
            import legacy_app as alias
            def dependency():
                return alias.get_api_key
            dependency()
            alias = None
            """),
        textwrap.dedent("""
            def outer():
                alias = None
                def inner():
                    return alias.get_api_key
                import legacy_app as alias
                return inner()
            """),
    ],
    ids=["late-module-import", "early-call-before-safe-rebind", "late-closure-import"],
)
def test_api_key_ownership_guard_preserves_late_bound_aliases(source: str) -> None:
    legacy_source = "from app.routers.api_key import _get_api_key_dynamic, get_api_key\n"

    assert _validate_api_key_dependency_ownership(
        legacy_source,
        {"app/main.py": source},
    ) == ["app/main.py: legacy API-key dependency attribute access is forbidden: get_api_key"]


@pytest.mark.parametrize(
    "deferred",
    [
        "dependency = lambda alias=legacy: alias.get_api_key",
        (
            "def expose(alias):\n"
            "    return alias.get_api_key\n"
            "dependency = lambda: expose(legacy)"
        ),
    ],
    ids=["default-binding", "helper-replay"],
)
def test_api_key_ownership_guard_inspects_deferred_lambda_execution(
    deferred: str,
) -> None:
    legacy_source = "from app.routers.api_key import _get_api_key_dynamic, get_api_key\n"
    source = "import legacy_app as legacy\n" f"{deferred}\n"

    assert _validate_api_key_dependency_ownership(
        legacy_source,
        {"app/main.py": source},
    ) == ["app/main.py: legacy API-key dependency attribute access is forbidden: get_api_key"]


@pytest.mark.parametrize("operator", ["and", "or"])
def test_api_key_ownership_guard_joins_boolean_short_circuit_state(operator: str) -> None:
    legacy_source = "from app.routers.api_key import _get_api_key_dynamic, get_api_key\n"
    source = (
        "import legacy_app as legacy\n"
        "alias = None\n"
        f"(alias := legacy) {operator} flag {operator} (alias := None)\n"
        "value = alias.get_api_key\n"
    )

    assert _validate_api_key_dependency_ownership(
        legacy_source,
        {"app/main.py": source},
    ) == ["app/main.py: legacy API-key dependency attribute access is forbidden: get_api_key"]


@pytest.mark.parametrize(
    ("lookup", "expected_kind"),
    [
        (
            "(alias := legacy).get_api_key",
            "legacy API-key dependency attribute access",
        ),
        (
            '(alias := legacy).__dict__["get_api_key"]',
            "legacy API-key dependency namespace lookup",
        ),
        (
            'getattr((alias := legacy), "get_api_key")',
            "dynamic legacy API-key dependency lookup",
        ),
    ],
    ids=["attribute", "namespace", "getattr"],
)
def test_api_key_ownership_guard_resolves_named_expression_value(
    lookup: str,
    expected_kind: str,
) -> None:
    legacy_source = "from app.routers.api_key import _get_api_key_dynamic, get_api_key\n"
    source = f"import legacy_app as legacy\nvalue = {lookup}\n"

    assert _validate_api_key_dependency_ownership(
        legacy_source,
        {"app/main.py": source},
    ) == [f"app/main.py: {expected_kind} is forbidden: get_api_key"]


def test_api_key_ownership_guard_preserves_intra_expression_exception_state() -> None:
    legacy_source = "from app.routers.api_key import _get_api_key_dynamic, get_api_key\n"
    source = textwrap.dedent("""
        import legacy_app as legacy
        alias = None
        try:
            result = ((alias := legacy), dangerous(), (alias := None))
        except Exception:
            value = alias.get_api_key
        """)

    assert _validate_api_key_dependency_ownership(
        legacy_source,
        {"app/main.py": source},
    ) == ["app/main.py: legacy API-key dependency attribute access is forbidden: get_api_key"]


def test_api_key_ownership_guard_isolates_deferred_lambda_exception_state() -> None:
    legacy_source = "from app.routers.api_key import _get_api_key_dynamic, get_api_key\n"
    source = textwrap.dedent("""
        import legacy_app as legacy
        alias = object()
        try:
            deferred = lambda: ((alias := legacy), dangerous())
        except Exception:
            value = alias.get_api_key
        """)

    assert (
        _validate_api_key_dependency_ownership(
            legacy_source,
            {"app/main.py": source},
        )
        == []
    )


def test_api_key_ownership_guard_chains_exception_handler_type_state() -> None:
    legacy_source = "from app.routers.api_key import _get_api_key_dynamic, get_api_key\n"
    source = textwrap.dedent("""
        import legacy_app as legacy
        alias = object()
        try:
            dangerous()
        except ((alias := legacy), ValueError)[1]:
            pass
        except TypeError:
            value = alias.get_api_key
        """)

    assert _validate_api_key_dependency_ownership(
        legacy_source,
        {"app/main.py": source},
    ) == ["app/main.py: legacy API-key dependency attribute access is forbidden: get_api_key"]


def test_api_key_ownership_guard_chains_exception_group_handlers() -> None:
    legacy_source = "from app.routers.api_key import _get_api_key_dynamic, get_api_key\n"
    source = textwrap.dedent("""
        import legacy_app as legacy
        alias = object()
        try:
            dangerous()
        except* ValueError:
            alias = legacy
        except* TypeError:
            value = alias.get_api_key
        """)

    assert _validate_api_key_dependency_ownership(
        legacy_source,
        {"app/main.py": source},
    ) == ["app/main.py: legacy API-key dependency attribute access is forbidden: get_api_key"]


@pytest.mark.parametrize(
    ("symbol_binding", "expected"),
    [
        (
            "symbol = get_name()",
            ["app/main.py: legacy API-key dependency namespace lookup is forbidden: <dynamic>"],
        ),
        ('symbol = "other"', []),
    ],
)
def test_api_key_ownership_guard_handles_dynamic_namespace_subscript(
    symbol_binding: str,
    expected: list[str],
) -> None:
    legacy_source = "from app.routers.api_key import _get_api_key_dynamic, get_api_key\n"
    source = (
        "import legacy_app as legacy\n" f"{symbol_binding}\n" "value = legacy.__dict__[symbol]\n"
    )

    assert (
        _validate_api_key_dependency_ownership(
            legacy_source,
            {"app/main.py": source},
        )
        == expected
    )


def test_api_key_ownership_guard_fails_closed_on_loop_iteration_budget() -> None:
    aliases = [f"alias_{index}" for index in range(40)]
    initializers = " = ".join(aliases) + " = object()\n"
    transfers = "".join(
        f"    {aliases[index]} = {aliases[index + 1]}\n" for index in range(len(aliases) - 1)
    )
    source = (
        "import legacy_app as legacy\n"
        f"{initializers}"
        "for _ in values:\n"
        f"{transfers}"
        f"    {aliases[-1]} = legacy\n"
    )
    legacy_source = "from app.routers.api_key import _get_api_key_dynamic, get_api_key\n"

    with pytest.raises(
        RuntimeError,
        match=r"loop binding analysis did not converge within 32 iterations",
    ):
        _validate_api_key_dependency_ownership(
            legacy_source,
            {"app/main.py": source},
        )


def test_api_key_ownership_guard_enforces_global_loop_iteration_budget() -> None:
    legacy_source = "from app.routers.api_key import _get_api_key_dynamic, get_api_key\n"

    def source_with_loops(count: int) -> str:
        return "".join(f"for item_{index} in values:\n    pass\n" for index in range(count))

    assert (
        _validate_api_key_dependency_ownership(
            legacy_source,
            {"app/main.py": source_with_loops(128)},
        )
        == []
    )
    with pytest.raises(
        legacy_guard.LegacyGrowthAnalysisError,
        match=r"app/main.py: loop binding analysis exceeded 128 total iterations",
    ):
        _validate_api_key_dependency_ownership(
            legacy_source,
            {"app/main.py": source_with_loops(129)},
        )


def test_api_key_ownership_guard_preserves_budget_for_loop_body_bindings() -> None:
    legacy_source = "from app.routers.api_key import _get_api_key_dynamic, get_api_key\n"
    source = "".join(
        f"for item_{index} in values:\n    value_{index} = object()\n" for index in range(128)
    )

    assert (
        _validate_api_key_dependency_ownership(
            legacy_source,
            {"app/main.py": source},
        )
        == []
    )


@pytest.mark.parametrize("method", ["get", "__getitem__"])
def test_api_key_ownership_guard_rejects_namespace_mapping_calls(method: str) -> None:
    legacy_source = "from app.routers.api_key import _get_api_key_dynamic, get_api_key\n"
    source = (
        "import legacy_app as legacy\n" f'dependency = legacy.__dict__.{method}("get_api_key")\n'
    )

    assert _validate_api_key_dependency_ownership(legacy_source, {"app/main.py": source}) == [
        "app/main.py: legacy API-key dependency namespace lookup is forbidden: get_api_key"
    ]


@pytest.mark.parametrize(
    ("lookup", "error_kind"),
    [
        ("getattr(legacy, get_name())", "dynamic legacy API-key dependency lookup"),
        ("legacy.__dict__.get(symbol)", "legacy API-key dependency namespace lookup"),
    ],
)
def test_api_key_ownership_guard_rejects_explicitly_dynamic_member_lookup(
    lookup: str,
    error_kind: str,
) -> None:
    legacy_source = "from app.routers.api_key import _get_api_key_dynamic, get_api_key\n"
    source = "import legacy_app as legacy\nsymbol = get_name()\ndependency = " f"{lookup}\n"

    assert _validate_api_key_dependency_ownership(legacy_source, {"app/main.py": source}) == [
        f"app/main.py: {error_kind} is forbidden: <dynamic>"
    ]


def test_api_key_ownership_guard_preserves_try_prefix_state_in_handler() -> None:
    legacy_source = "from app.routers.api_key import _get_api_key_dynamic, get_api_key\n"
    source = textwrap.dedent("""
        try:
            import legacy_app as legacy
            1 / 0
        except Exception:
            dependency = legacy.get_api_key
        """)

    assert _validate_api_key_dependency_ownership(legacy_source, {"app/main.py": source}) == [
        "app/main.py: legacy API-key dependency attribute access is forbidden: get_api_key"
    ]


def test_api_key_ownership_guard_resolves_nonlocal_alias_before_reassignment() -> None:
    legacy_source = "from app.routers.api_key import _get_api_key_dynamic, get_api_key\n"
    source = textwrap.dedent("""
        def outer():
            import legacy_app as legacy

            def inner():
                nonlocal legacy
                dependency = legacy.get_api_key
                legacy = object()
                return dependency

            return inner
        """)

    assert _validate_api_key_dependency_ownership(legacy_source, {"app/main.py": source}) == [
        "app/main.py: legacy API-key dependency attribute access is forbidden: get_api_key"
    ]


def test_api_key_ownership_guard_accepts_direct_identity_preserving_reexports() -> None:
    legacy_source = (
        "from app.routers.api_key import (\n    _get_api_key_dynamic,\n    get_api_key,\n)\n"
    )

    assert _validate_api_key_dependency_ownership(legacy_source, {}) == []


def test_api_key_ownership_guard_requires_module_level_reexports() -> None:
    legacy_source = textwrap.dedent("""
        def compatibility_imports():
            from app.routers.api_key import _get_api_key_dynamic, get_api_key
            return _get_api_key_dynamic, get_api_key
        """)

    assert _validate_api_key_dependency_ownership(legacy_source, {}) == [
        "legacy_app.py: canonical API-key compatibility re-export must preserve identity: "
        "_get_api_key_dynamic",
        "legacy_app.py: canonical API-key compatibility re-export must preserve identity: "
        "get_api_key",
    ]


@pytest.mark.parametrize(
    ("source", "expected_symbol"),
    [
        (
            "import importlib\n"
            'legacy = importlib.import_module("legacy_app")\n'
            "dependency = legacy.get_api_key\n",
            "get_api_key",
        ),
        (
            "import legacy_app as legacy\n"
            "compat = legacy\n"
            "dependency = compat._get_api_key_dynamic\n",
            "_get_api_key_dynamic",
        ),
        (
            "import legacy_app as legacy\n"
            'symbol = "get_api_key"\n'
            "dependency = getattr(legacy, symbol)\n",
            "get_api_key",
        ),
    ],
    ids=["literal-importlib", "one-hop-alias", "static-getattr-name"],
)
def test_api_key_ownership_guard_rejects_bounded_ordinary_aliases(
    source: str,
    expected_symbol: str,
) -> None:
    legacy_source = (
        "from app.routers.api_key import (\n"
        "    _get_api_key_dynamic as _get_api_key_dynamic,\n"
        "    get_api_key as get_api_key,\n"
        ")\n"
    )

    errors = _validate_api_key_dependency_ownership(
        legacy_source,
        {"app/main.py": source},
    )

    assert errors == [
        (
            f"app/main.py: legacy API-key dependency attribute access is forbidden: {expected_symbol}"
            if "getattr" not in source
            else f"app/main.py: dynamic legacy API-key dependency lookup is forbidden: "
            f"{expected_symbol}"
        )
    ]


@pytest.mark.parametrize(
    "source",
    [
        'import importlib\nmodule = importlib.import_module("json")\nvalue = module.dumps\n',
        "import legacy_app as legacy\ncompat = object()\nvalue = compat.get_api_key\n",
        'import legacy_app as legacy\nsymbol = "other"\nvalue = getattr(legacy, symbol)\n',
    ],
    ids=["nonlegacy-import", "safe-reassignment", "unrelated-getattr-name"],
)
def test_api_key_ownership_guard_allows_bounded_ordinary_alias_controls(source: str) -> None:
    legacy_source = (
        "from app.routers.api_key import (\n"
        "    _get_api_key_dynamic as _get_api_key_dynamic,\n"
        "    get_api_key as get_api_key,\n"
        ")\n"
    )

    assert (
        _validate_api_key_dependency_ownership(
            legacy_source,
            {"app/main.py": source},
        )
        == []
    )


def test_api_key_ownership_guard_rejects_lookup_before_safe_reassignment() -> None:
    legacy_source = (
        "from app.routers.api_key import (\n    _get_api_key_dynamic,\n    get_api_key,\n)\n"
    )
    source = (
        "import legacy_app as legacy\n"
        "compat = legacy\n"
        "dependency = compat.get_api_key\n"
        "compat = object()\n"
    )

    assert _validate_api_key_dependency_ownership(legacy_source, {"app/main.py": source}) == [
        "app/main.py: legacy API-key dependency attribute access is forbidden: get_api_key"
    ]


def test_api_key_ownership_guard_allows_lookup_before_legacy_assignment() -> None:
    legacy_source = (
        "from app.routers.api_key import (\n    _get_api_key_dynamic,\n    get_api_key,\n)\n"
    )
    source = (
        "import legacy_app as legacy\n"
        "compat = object()\n"
        "dependency = compat.get_api_key\n"
        "compat = legacy\n"
    )

    assert _validate_api_key_dependency_ownership(legacy_source, {"app/main.py": source}) == []


def test_api_key_ownership_guard_rejects_single_alias_used_in_expression() -> None:
    legacy_source = (
        "from app.routers.api_key import (\n    _get_api_key_dynamic,\n    get_api_key,\n)\n"
    )
    source = "import legacy_app as legacy\ncompat = legacy\nregister(compat.get_api_key)\n"

    assert _validate_api_key_dependency_ownership(legacy_source, {"app/main.py": source}) == [
        "app/main.py: legacy API-key dependency attribute access is forbidden: get_api_key"
    ]


def test_api_key_ownership_guard_allows_safe_alias_used_in_expression() -> None:
    legacy_source = (
        "from app.routers.api_key import (\n    _get_api_key_dynamic,\n    get_api_key,\n)\n"
    )
    source = "import legacy_app as legacy\ncompat = object()\nregister(compat.get_api_key)\n"

    assert _validate_api_key_dependency_ownership(legacy_source, {"app/main.py": source}) == []


@pytest.mark.parametrize(
    ("legacy_source", "expected"),
    [
        (
            "async def lifespan(app):\n    yield\n",
            "legacy_app.py: lifecycle implementation must be canonical",
        ),
        (
            '@app.on_event("startup")\nasync def start():\n    pass\n',
            "legacy_app.py: startup/shutdown event registration is forbidden",
        ),
        (
            'app.add_event_handler("startup", start)\n',
            "legacy_app.py: startup/shutdown event registration is forbidden",
        ),
        (
            "app.router.on_shutdown.append(stop)\n",
            "legacy_app.py: startup/shutdown event registration is forbidden",
        ),
        (
            "callbacks = app.router.on_startup\ncallbacks.append(start)\n",
            "legacy_app.py: startup/shutdown event registration is forbidden",
        ),
        (
            'getattr(app.router, "on_startup").append(start)\n',
            "legacy_app.py: startup/shutdown event registration is forbidden",
        ),
        (
            'app.router.__getattribute__("on_startup").append(start)\n',
            "legacy_app.py: startup/shutdown event registration is forbidden",
        ),
        (
            'object.__getattribute__(app.router, "on_shutdown").append(stop)\n',
            "legacy_app.py: startup/shutdown event registration is forbidden",
        ),
        (
            'register = app.__getattribute__("on_event")\n'
            '@register("shutdown")\n'
            "async def stop():\n    pass\n",
            "legacy_app.py: startup/shutdown event registration is forbidden",
        ),
        (
            'app.router.__dict__["on_startup"].append(start)\n',
            "legacy_app.py: startup/shutdown event registration is forbidden",
        ),
        (
            'vars(app.router)["on_shutdown"].append(stop)\n',
            "legacy_app.py: startup/shutdown event registration is forbidden",
        ),
        (
            'getattr(app.router, "__dict__")["on_startup"].append(start)\n',
            "legacy_app.py: startup/shutdown event registration is forbidden",
        ),
        (
            'app.router.__dict__.update({"on_startup": [start]})\n',
            "legacy_app.py: startup/shutdown event registration is forbidden",
        ),
        (
            "app.router.lifespan_context = wrapper\n",
            "legacy_app.py: lifespan_context mutation is forbidden",
        ),
        (
            'register = app.on_event\n@register("startup")\nasync def start():\n    pass\n',
            "legacy_app.py: startup/shutdown event registration is forbidden",
        ),
        (
            'register = getattr(app, "on_event")\n@register("shutdown")\nasync def stop():\n    pass\n',
            "legacy_app.py: startup/shutdown event registration is forbidden",
        ),
        (
            "from fastapi import FastAPI\n"
            "async def runtime_context(app):\n    yield\n"
            "app = FastAPI(lifespan=runtime_context)\n",
            "legacy_app.py: FastAPI lifespan must use the canonical re-export",
        ),
        (
            "from fastapi import FastAPI\napp = FastAPI()\n",
            "legacy_app.py: FastAPI lifespan must use the canonical re-export",
        ),
        (
            'from fastapi import FastAPI\napp = FastAPI(**{"title": "PulsePlate"})\n',
            "legacy_app.py: FastAPI lifespan must use the canonical re-export",
        ),
        (
            "from fastapi.applications import FastAPI\n"
            "async def runtime_context(app):\n    yield\n"
            "app = FastAPI(lifespan=runtime_context)\n",
            "legacy_app.py: FastAPI lifespan must use the canonical re-export",
        ),
        (
            "import fastapi.applications\n"
            "async def runtime_context(app):\n    yield\n"
            "app = fastapi.applications.FastAPI(lifespan=runtime_context)\n",
            "legacy_app.py: FastAPI lifespan must use the canonical re-export",
        ),
        (
            "from fastapi import applications\napp = applications.FastAPI()\n",
            "legacy_app.py: FastAPI lifespan must use the canonical re-export",
        ),
        (
            "from fastapi import FastAPI\n"
            "async def runtime_context(app):\n    yield\n"
            'app = FastAPI(**{"lifespan": runtime_context})\n',
            "legacy_app.py: FastAPI lifespan must use the canonical re-export",
        ),
        (
            "from fastapi import FastAPI\n"
            "async def runtime_context(app):\n    yield\n"
            'options = {"lifespan": runtime_context}\n'
            "app = FastAPI(**options)\n",
            "legacy_app.py: FastAPI lifespan must use the canonical re-export",
        ),
        (
            "from fastapi import FastAPI\noptions = build_options()\napp = FastAPI(**options)\n",
            "legacy_app.py: FastAPI lifespan must use the canonical re-export",
        ),
        (
            "from fastapi import FastAPI\n"
            "from app.bootstrap.lifespan import application_lifespan as lifespan\n"
            "async def runtime_context(app):\n    yield\n"
            "lifespan = runtime_context\n"
            "app = FastAPI(lifespan=lifespan)\n",
            "legacy_app.py: FastAPI lifespan must use the canonical re-export",
        ),
        (
            "from fastapi import FastAPI\n"
            "from app.bootstrap.lifespan import application_lifespan as lifespan\n"
            "def build_app(lifespan):\n"
            "    return FastAPI(lifespan=lifespan)\n",
            "legacy_app.py: FastAPI lifespan must use the canonical re-export",
        ),
        (
            "from fastapi import FastAPI\n"
            "from app.bootstrap.lifespan import application_lifespan as lifespan\n"
            "async def runtime_context(app):\n    yield\n"
            "lifespan = runtime_context\n"
            'options = {"lifespan": lifespan}\n'
            "app = FastAPI(**options)\n",
            "legacy_app.py: FastAPI lifespan must use the canonical re-export",
        ),
        (
            "from fastapi import FastAPI\n"
            "async def runtime_context(app):\n    yield\n"
            "key = 'title'\n"
            "key = 'lifespan'\n"
            "options = {key: runtime_context}\n"
            "app = FastAPI(**options)\n",
            "legacy_app.py: FastAPI lifespan must use the canonical re-export",
        ),
    ],
)
def test_lifecycle_guard_rejects_legacy_ownership(
    legacy_source: str,
    expected: str,
) -> None:
    errors = legacy_guard.validate_lifecycle_ownership(
        legacy_source,
        "pass\n",
        "pass\n",
    )

    assert errors == [expected]


@pytest.mark.parametrize(
    "food_source",
    [
        "app.router.lifespan_context = wrapper\n",
        "del app.router.lifespan_context\n",
        'setattr(app.router, "lifespan_context", wrapper)\n',
        'import builtins\nbuiltins.setattr(app.router, "lifespan_context", wrapper)\n',
        'from builtins import setattr as assign\nassign(app.router, "lifespan_context", wrapper)\n',
        'object.__setattr__(app.router, "lifespan_context", wrapper)\n',
        'app.router.__setattr__("lifespan_context", wrapper)\n',
        'assign = object.__setattr__\nassign(app.router, "lifespan_context", wrapper)\n',
        'vars(app.router)["lifespan_context"] = wrapper\n',
        'app.router.__dict__["lifespan_context"] = wrapper\n',
        'del app.router.__dict__["lifespan_context"]\n',
        'del vars(app.router)["lifespan_context"]\n',
        'app.router.__dict__.update({"lifespan_context": wrapper})\n',
        'vars(app.router).update({"lifespan_context": wrapper})\n',
        'app.router.__dict__.update(**{"lifespan_context": wrapper})\n',
        'options = {"lifespan_context": wrapper}\nvars(app.router).update(**options)\n',
        "vars(app.router).update(**build_options())\n",
        'vars(app.router).__ior__({"lifespan_context": wrapper})\n',
        'app.router.__dict__ |= {"lifespan_context": wrapper}\n',
        'app.router.__dict__ = app.router.__dict__ | {"lifespan_context": wrapper}\n',
        'getattr(app.router, "__dict__").update({"lifespan_context": wrapper})\n',
        'app.router.__getattribute__("__dict__").update({"lifespan_context": wrapper})\n',
        'dict.__setitem__(app.router.__dict__, "lifespan_context", wrapper)\n',
        'mutate = dict.__setitem__\nmutate(vars(app.router), "lifespan_context", wrapper)\n',
        "dict.clear(vars(app.router))\n",
        'app.router.__dict__.setdefault("lifespan_context", wrapper)\n',
        'vars(app.router).setdefault("lifespan_context", wrapper)\n',
        'app.router.__dict__.pop("lifespan_context")\n',
        'vars(app.router).__delitem__("lifespan_context")\n',
        "app.router.__dict__.clear()\n",
    ],
)
def test_lifecycle_guard_rejects_food_search_lifespan_wrapping(
    food_source: str,
) -> None:
    errors = legacy_guard.validate_lifecycle_ownership(
        "pass\n",
        food_source,
        "pass\n",
    )

    lifespan_error = "app/bootstrap/food_search.py: lifespan_context mutation is forbidden"
    event_error = "app/bootstrap/food_search.py: startup/shutdown event registration is forbidden"
    assert lifespan_error in errors
    assert set(errors) <= {lifespan_error, event_error}


@pytest.mark.parametrize(
    "food_source",
    [
        'app.add_event_handler("startup", start)\n',
        "app.router.on_shutdown.append(stop)\n",
        'app.router.__dict__.update({"on_startup": [start]})\n',
        'dict.update(app.router.__dict__, {"on_startup": [start]})\n',
        'mutate = dict.update\nmutate(vars(app.router), {"on_startup": [start]})\n',
        "from builtins import dict as mapping\n"
        "mutate = mapping.update\n"
        'mutate(vars(app.router), {"on_shutdown": [stop]})\n',
        "from builtins import dict as mapping\n"
        'mapping.__setitem__(vars(app.router), "on_shutdown", [stop])\n',
    ],
)
def test_lifecycle_guard_rejects_food_search_event_registration(
    food_source: str,
) -> None:
    errors = legacy_guard.validate_lifecycle_ownership(
        "pass\n",
        food_source,
        "pass\n",
    )

    assert errors == [
        "app/bootstrap/food_search.py: startup/shutdown event registration is forbidden"
    ]


@pytest.mark.parametrize(
    "food_source",
    [
        'vars(app.state).update({"food_search_strategy": strategy})\n',
        'vars(app.state).update(**{"food_search_strategy": strategy})\n',
        'vars(app.state).__ior__({"food_search_strategy": strategy})\n',
        'getattr(app.state, "__dict__").update({"food_search_strategy": strategy})\n',
        'app.state.__dict__ = {"food_search_strategy": strategy}\n',
        'dict.update(vars(app.state), {"food_search_strategy": strategy})\n',
        'mutate = dict.update\nmutate(vars(app.state), {"food_search_strategy": strategy})\n',
        'some_object.__dict__.update({"x": value})\n',
        'vars(app.state).setdefault("food_search_strategy", strategy)\n',
    ],
)
def test_lifecycle_guard_allows_unrelated_namespace_mutation(food_source: str) -> None:
    assert legacy_guard.validate_lifecycle_ownership("pass\n", food_source, "pass\n") == []


@pytest.mark.parametrize(
    ("lifespan_source", "expected"),
    [
        (
            "import legacy_app\n",
            "app/bootstrap/lifespan.py: forbidden facade import: legacy_app",
        ),
        (
            "import sys\nvalue = sys.modules.get('app')\n",
            "app/bootstrap/lifespan.py: dynamic facade lookup is forbidden",
        ),
        (
            "import sys as _sys\nvalue = _sys.modules.get('app')\n",
            "app/bootstrap/lifespan.py: dynamic facade lookup is forbidden",
        ),
        (
            "from sys import modules as loaded\nvalue = loaded.get('legacy_app')\n",
            "app/bootstrap/lifespan.py: dynamic facade lookup is forbidden",
        ),
        (
            "import importlib\nvalue = importlib.import_module('legacy_app')\n",
            "app/bootstrap/lifespan.py: dynamic facade lookup is forbidden",
        ),
        (
            "from importlib import import_module as load\nvalue = load('app')\n",
            "app/bootstrap/lifespan.py: dynamic facade lookup is forbidden",
        ),
        (
            "value = __import__('legacy_app')\n",
            "app/bootstrap/lifespan.py: dynamic facade lookup is forbidden",
        ),
        (
            "value = __import__('app.main')\n",
            "app/bootstrap/lifespan.py: dynamic facade lookup is forbidden",
        ),
        (
            "value = __builtins__['__import__']('legacy_app')\n",
            "app/bootstrap/lifespan.py: dynamic facade lookup is forbidden",
        ),
        (
            "value = __builtins__.__import__('app.main')\n",
            "app/bootstrap/lifespan.py: dynamic facade lookup is forbidden",
        ),
        (
            "import importlib\nvalue = importlib.import_module('legacy_app.runtime')\n",
            "app/bootstrap/lifespan.py: dynamic facade lookup is forbidden",
        ),
        (
            "from importlib import import_module\n"
            "module_name = 'app.bootstrap.' + 'lifespan'\n"
            "value = import_module(module_name)\n",
            "app/bootstrap/lifespan.py: dynamic facade lookup is forbidden",
        ),
        (
            "from importlib import import_module\n"
            "module_name = 'json'\n"
            "module_name = 'app.main'\n"
            "value = import_module(name=module_name)\n",
            "app/bootstrap/lifespan.py: dynamic facade lookup is forbidden",
        ),
        (
            "from importlib import import_module\nvalue = import_module(resolve_module_name())\n",
            "app/bootstrap/lifespan.py: dynamic facade lookup is forbidden",
        ),
        (
            "from importlib import import_module\n"
            "module_name = 'json'\n"
            "def load(module_name):\n"
            "    return import_module(module_name)\n",
            "app/bootstrap/lifespan.py: dynamic facade lookup is forbidden",
        ),
        (
            "from importlib import import_module\nvalue = import_module('.main', package='app')\n",
            "app/bootstrap/lifespan.py: dynamic facade lookup is forbidden",
        ),
        (
            'import builtins\nvalue = builtins.__dict__["__import__"]("legacy_app")\n',
            "app/bootstrap/lifespan.py: dynamic facade lookup is forbidden",
        ),
        (
            'import builtins\nvalue = vars(builtins)["__import__"]("app.main")\n',
            "app/bootstrap/lifespan.py: dynamic facade lookup is forbidden",
        ),
        (
            'import importlib\nvalue = importlib.__dict__["import_module"]("legacy_app")\n',
            "app/bootstrap/lifespan.py: dynamic facade lookup is forbidden",
        ),
        (
            'import importlib\nvalue = vars(importlib)["import_module"]("app")\n',
            "app/bootstrap/lifespan.py: dynamic facade lookup is forbidden",
        ),
        (
            'import importlib\nvalue = importlib.__dict__.get("import_module")("legacy_app")\n',
            "app/bootstrap/lifespan.py: dynamic facade lookup is forbidden",
        ),
        (
            'import builtins\nvalue = vars(builtins).get("__import__")("app.main")\n',
            "app/bootstrap/lifespan.py: dynamic facade lookup is forbidden",
        ),
        (
            'import importlib\nvalue = importlib.__dict__.__getitem__("import_module")("app")\n',
            "app/bootstrap/lifespan.py: dynamic facade lookup is forbidden",
        ),
        (
            "import importlib\n"
            'value = object.__getattribute__(importlib, "import_module")("legacy_app")\n',
            "app/bootstrap/lifespan.py: dynamic facade lookup is forbidden",
        ),
        (
            'import importlib\nvalue = importlib.__getattribute__("import_module")("app")\n',
            "app/bootstrap/lifespan.py: dynamic facade lookup is forbidden",
        ),
        (
            "import importlib\n"
            "getter = importlib.__getattribute__\n"
            'value = getter("import_module")("legacy_app")\n',
            "app/bootstrap/lifespan.py: dynamic facade lookup is forbidden",
        ),
        (
            "import importlib\n"
            'value = getattr(importlib, "__getattribute__")("import_module")("app")\n',
            "app/bootstrap/lifespan.py: dynamic facade lookup is forbidden",
        ),
        (
            "import app.main\n",
            "app/bootstrap/lifespan.py: forbidden facade import: app.main",
        ),
        (
            "from app.main import app\n",
            "app/bootstrap/lifespan.py: forbidden facade import: app.main",
        ),
        (
            "value = app_module.start_background_updates\n",
            "app/bootstrap/lifespan.py: forbidden legacy dependency lookup: app_module",
        ),
    ],
)
def test_lifecycle_guard_rejects_legacy_dependency_resolution(
    lifespan_source: str,
    expected: str,
) -> None:
    errors = legacy_guard.validate_lifecycle_ownership(
        "pass\n",
        "pass\n",
        lifespan_source,
    )

    assert expected in errors


@pytest.mark.parametrize("loop_header", ["for _ in [1]:", "while True:"])
def test_lifecycle_guard_preserves_dynamic_loader_across_loop_break_else(
    loop_header: str,
) -> None:
    lifespan_source = textwrap.dedent(f"""
        import importlib

        {loop_header}
            loader = importlib.import_module
            break
        else:
            loader = object()

        value = loader("legacy_app")
        """)

    assert legacy_guard.validate_lifecycle_ownership(
        "pass\n",
        "pass\n",
        lifespan_source,
    ) == ["app/bootstrap/lifespan.py: dynamic facade lookup is forbidden"]


@pytest.mark.parametrize("alternate", ["FastAPI", "FastAPI()"], ids=["class", "app"])
def test_lifecycle_guard_preserves_loader_possibility_across_fastapi_join(
    alternate: str,
) -> None:
    lifespan_source = textwrap.dedent(f"""
        import importlib
        from fastapi import FastAPI

        if enabled:
            loader = importlib.import_module
        else:
            loader = {alternate}

        value = loader("legacy_app")
        """)

    assert legacy_guard.validate_lifecycle_ownership(
        "pass\n",
        "pass\n",
        lifespan_source,
    ) == ["app/bootstrap/lifespan.py: dynamic facade lookup is forbidden"]


def test_lifecycle_guard_preserves_fastapi_possibility_independently() -> None:
    legacy_source = textwrap.dedent("""
        from fastapi import FastAPI
        from importlib import import_module

        if enabled:
            constructor = import_module
        else:
            constructor = FastAPI

        app = constructor("json", lifespan=handler)
        """)

    assert legacy_guard.validate_lifecycle_ownership(
        legacy_source,
        "pass\n",
        "pass\n",
    ) == ["legacy_app.py: FastAPI lifespan must use the canonical re-export"]


def test_lifecycle_guard_allows_non_fastapi_import_callable_conflict() -> None:
    legacy_source = textwrap.dedent("""
        from contextlib import asynccontextmanager
        from importlib import import_module

        if enabled:
            constructor = import_module
        else:
            constructor = asynccontextmanager

        value = constructor("json", lifespan=handler)
        """)

    assert (
        legacy_guard.validate_lifecycle_ownership(
            legacy_source,
            "pass\n",
            "pass\n",
        )
        == []
    )


@pytest.mark.parametrize(
    ("legacy_source", "lifespan_source"),
    [
        (
            textwrap.dedent("""
                from fastapi import FastAPI

                if False:
                    app = FastAPI()
                """),
            "pass\n",
        ),
        (
            textwrap.dedent("""
                from fastapi import FastAPI

                while False:
                    app = FastAPI()
                """),
            "pass\n",
        ),
        (
            "pass\n",
            textwrap.dedent("""
                import importlib

                if False:
                    value = importlib.import_module("legacy_app")
                """),
        ),
        (
            "pass\n",
            textwrap.dedent("""
                from importlib import import_module

                for _ in []:
                    value = import_module("legacy_app")
                """),
        ),
        (
            "pass\n",
            textwrap.dedent("""
                import sys

                if False:
                    value = sys.modules["legacy_app"]
                """),
        ),
    ],
    ids=[
        "legacy-if-false-fastapi",
        "legacy-while-false-fastapi",
        "lifespan-if-false-import-module",
        "lifespan-empty-for-import-module",
        "lifespan-if-false-sys-modules",
    ],
)
def test_lifecycle_guard_ignores_statically_unreachable_calls(
    legacy_source: str,
    lifespan_source: str,
) -> None:
    assert (
        legacy_guard.validate_lifecycle_ownership(
            legacy_source,
            "pass\n",
            lifespan_source,
        )
        == []
    )


def test_lifecycle_guard_resolves_named_expression_import_callable() -> None:
    lifespan_source = textwrap.dedent("""
        from importlib import import_module

        value = (loader := import_module)("legacy_app")
        """)

    assert legacy_guard.validate_lifecycle_ownership(
        "pass\n",
        "pass\n",
        lifespan_source,
    ) == ["app/bootstrap/lifespan.py: dynamic facade lookup is forbidden"]


def test_lifecycle_guard_resolves_named_expression_fastapi_constructor() -> None:
    legacy_source = textwrap.dedent("""
        from fastapi import FastAPI

        app = (constructor := FastAPI)(lifespan=runtime_context)
        """)

    assert legacy_guard.validate_lifecycle_ownership(
        legacy_source,
        "pass\n",
        "pass\n",
    ) == ["legacy_app.py: FastAPI lifespan must use the canonical re-export"]


def test_lifecycle_guard_allows_benign_callable_conflicts() -> None:
    lifespan_source = textwrap.dedent("""
        import json
        import pathlib

        if enabled:
            loader = json.loads
        else:
            loader = pathlib.Path

        value = loader("legacy_app")
        """)

    assert (
        legacy_guard.validate_lifecycle_ownership(
            "pass\n",
            "pass\n",
            lifespan_source,
        )
        == []
    )


def test_lifecycle_reference_collection_terminates_on_conflicting_aliases() -> None:
    legacy_source = textwrap.dedent("""
        from fastapi import FastAPI

        async def runtime_context(app):
            yield

        alias = FastAPI
        alias = getattr
        app = alias(lifespan=runtime_context)
        """)

    assert legacy_guard.validate_lifecycle_ownership(
        legacy_source,
        "pass\n",
        "pass\n",
    ) == ["legacy_app.py: FastAPI lifespan must use the canonical re-export"]


@pytest.mark.parametrize(
    "assignments",
    [
        "alias = FastAPI\nalias = getattr\n",
        "alias = getattr\nalias = FastAPI\n",
        "alias = FastAPI\nalias = getattr\nalias = FastAPI\n",
    ],
    ids=["static-then-builtin", "builtin-then-static", "three-way"],
)
def test_lifecycle_reference_conflicts_are_order_independent_and_deterministic(
    assignments: str,
) -> None:
    legacy_source = (
        "from fastapi import FastAPI\n"
        "async def runtime_context(app):\n    yield\n"
        f"{assignments}"
        "constructor = alias\n"
        "app = constructor(lifespan=runtime_context)\n"
    )
    expected = ["legacy_app.py: FastAPI lifespan must use the canonical re-export"]

    assert legacy_guard.validate_lifecycle_ownership(legacy_source, "pass\n", "pass\n") == expected
    assert legacy_guard.validate_lifecycle_ownership(legacy_source, "pass\n", "pass\n") == expected


@pytest.mark.parametrize(
    "assignments",
    ["alias = FastAPI\nalias = getattr\n", "alias = getattr\nalias = FastAPI\n"],
)
def test_lifecycle_conflicted_constructor_without_kwargs_fails_closed(
    assignments: str,
) -> None:
    legacy_source = "from fastapi import FastAPI\n" f"{assignments}" "app = alias()\n"

    assert legacy_guard.validate_lifecycle_ownership(legacy_source, "pass\n", "pass\n") == [
        "legacy_app.py: FastAPI lifespan must use the canonical re-export"
    ]


def test_lifecycle_guard_rejects_local_fastapi_constructor_alias() -> None:
    legacy_source = textwrap.dedent("""
        from fastapi import FastAPI

        def create_app():
            constructor = FastAPI
            return constructor()
        """)

    assert legacy_guard.validate_lifecycle_ownership(legacy_source, "pass\n", "pass\n") == [
        "legacy_app.py: FastAPI lifespan must use the canonical re-export"
    ]


def test_lifecycle_module_alias_ignores_nested_local_rebinding() -> None:
    legacy_source = textwrap.dedent("""
        from fastapi import FastAPI
        from app.bootstrap.lifespan import application_lifespan as lifespan

        def harmless():
            lifespan = object()
            return lifespan

        app = FastAPI(lifespan=lifespan)
        """)

    assert legacy_guard.validate_lifecycle_ownership(legacy_source, "pass\n", "pass\n") == []


@pytest.mark.parametrize("with_else", [False, True])
def test_lifecycle_conditional_fastapi_constructor_fails_closed(with_else: bool) -> None:
    else_branch = "else:\n    constructor = object\n" if with_else else ""
    legacy_source = (
        "from fastapi import FastAPI\n"
        "if enabled:\n"
        "    constructor = FastAPI\n"
        f"{else_branch}"
        "app = constructor()\n"
    )

    assert legacy_guard.validate_lifecycle_ownership(legacy_source, "pass\n", "pass\n") == [
        "legacy_app.py: FastAPI lifespan must use the canonical re-export"
    ]


@pytest.mark.parametrize(
    "alternate",
    ["object", "applications.FastAPI"],
    ids=["non-fastapi", "second-fastapi-alias"],
)
def test_lifecycle_conditional_fastapi_constructor_accepts_canonical_lifespan(
    alternate: str,
) -> None:
    legacy_source = textwrap.dedent(f"""
        import fastapi.applications as applications
        from fastapi import FastAPI
        from app.bootstrap.lifespan import application_lifespan

        if enabled:
            constructor = FastAPI
        else:
            constructor = {alternate}

        app = constructor(lifespan=application_lifespan)
        """)

    assert (
        legacy_guard.validate_lifecycle_ownership(
            legacy_source,
            "pass\n",
            "pass\n",
        )
        == []
    )


@pytest.mark.parametrize("replacement", ["safe_constructor", "function"])
def test_lifecycle_guard_clears_branch_marker_after_unconditional_safe_rebinding(
    replacement: str,
) -> None:
    final_binding = (
        "def constructor(*, lifespan):\n    return lifespan\n"
        if replacement == "function"
        else "constructor = safe_constructor\n"
    )
    legacy_source = (
        "from fastapi import FastAPI\n"
        "if enabled:\n"
        "    constructor = FastAPI\n"
        "else:\n"
        "    constructor = object\n"
        f"{final_binding}"
        "app = constructor(lifespan=handler)\n"
    )

    assert (
        legacy_guard.validate_lifecycle_ownership(
            legacy_source,
            "pass\n",
            "pass\n",
        )
        == []
    )


def test_lifecycle_guard_treats_unconditional_definition_as_latest_binding() -> None:
    legacy_source = textwrap.dedent("""
        from fastapi import FastAPI

        constructor = FastAPI

        def constructor(*, lifespan):
            return lifespan

        app = constructor(lifespan=handler)
        """)

    assert (
        legacy_guard.validate_lifecycle_ownership(
            legacy_source,
            "pass\n",
            "pass\n",
        )
        == []
    )


def test_lifecycle_guard_accepts_canonical_lifespan_in_static_keyword_mapping() -> None:
    legacy_source = textwrap.dedent("""
        from fastapi import FastAPI
        from app.bootstrap.lifespan import application_lifespan as lifespan

        options = {"lifespan": lifespan}
        app = FastAPI(**options)
        """)

    assert legacy_guard.validate_lifecycle_ownership(legacy_source, "pass\n", "pass\n") == []


@pytest.mark.parametrize(
    "constructor",
    [
        'fastapi.__dict__["FastAPI"]',
        'vars(fastapi)["FastAPI"]',
        'fastapi.__dict__.get("FastAPI")',
        'vars(fastapi).get("FastAPI")',
        'fastapi.__dict__.__getitem__("FastAPI")',
        'object.__getattribute__(fastapi, "FastAPI")',
        'getattr(fastapi, "__getattribute__")("FastAPI")',
    ],
)
def test_lifecycle_guard_rejects_namespace_mediated_fastapi_constructor(
    constructor: str,
) -> None:
    legacy_source = textwrap.dedent(f"""
        import fastapi

        async def runtime_context(app):
            yield

        app = {constructor}(lifespan=runtime_context)
        """)

    assert legacy_guard.validate_lifecycle_ownership(
        legacy_source,
        "pass\n",
        "pass\n",
    ) == ["legacy_app.py: FastAPI lifespan must use the canonical re-export"]


def test_lifecycle_guard_rejects_static_mapping_that_escapes_before_expansion() -> None:
    legacy_source = textwrap.dedent("""
        from fastapi import FastAPI
        from app.bootstrap.lifespan import application_lifespan as lifespan

        options = {"lifespan": lifespan}
        alias = options
        app = FastAPI(**options)
        """)

    assert legacy_guard.validate_lifecycle_ownership(
        legacy_source,
        "pass\n",
        "pass\n",
    ) == ["legacy_app.py: FastAPI lifespan must use the canonical re-export"]


def test_lifecycle_guard_allows_static_canonical_submodule_imports() -> None:
    lifespan_source = "from app.bootstrap.food_search import configure_food_search_backend\n"

    assert (
        legacy_guard.validate_lifecycle_ownership(
            "pass\n",
            "pass\n",
            lifespan_source,
        )
        == []
    )


def test_lifecycle_guard_allows_statically_known_nonfacade_dynamic_import() -> None:
    lifespan_source = textwrap.dedent("""
        from importlib import import_module

        module_name = "json"
        value = import_module(module_name)
        """)

    assert (
        legacy_guard.validate_lifecycle_ownership(
            "pass\n",
            "pass\n",
            lifespan_source,
        )
        == []
    )


def test_legacy_seam_doc_passes_contract() -> None:
    text = (REPO_ROOT / "docs/architecture/LEGACY_COMPATIBILITY_SEAM.md").read_text(
        encoding="utf-8"
    )

    assert legacy_guard.validate_legacy_seam_doc(text) == []


def test_legacy_growth_guard_allows_shrinkage() -> None:
    source = "from fastapi import FastAPI\napp = FastAPI()\n"

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_rejects_new_route() -> None:
    source = textwrap.dedent("""
        from fastapi import FastAPI

        app = FastAPI()

        @app.post("/api/v1/new-runtime")
        async def new_runtime_route():
            return {"ok": True}
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "decorator:post:/api/v1/new-runtime -> new_runtime_route"
    ]


@pytest.mark.parametrize(
    ("registration", "expected"),
    [
        (
            'app.get("/api/v1/dynamic-app")(handler)',
            "registration:get:/api/v1/dynamic-app",
        ),
        (
            'router = app.router\nrouter.post("/api/v1/dynamic-router")(handler)',
            "registration:router.post:/api/v1/dynamic-router",
        ),
        (
            'route = app.get\nroute("/api/v1/dynamic-method")(handler)',
            "registration:dynamic:/api/v1/dynamic-method",
        ),
        (
            'register = app.middleware("http")\nregister(handler)',
            "registration:middleware:http",
        ),
    ],
    ids=["app", "router", "route-method", "middleware"],
)
def test_legacy_growth_guard_rejects_derived_dynamic_app_rebinding(
    registration: str,
    expected: str,
) -> None:
    source = textwrap.dedent("""
        _existing_app = app

        def _resolve_app():
            return _existing_app

        app = _resolve_app()
        """) + registration + "\n"

    assert legacy_guard.validate_legacy_growth(source) == [
        f"legacy_app.py: unexpected legacy route growth: {expected}"
    ]


@pytest.mark.parametrize(
    ("setup", "registration", "expected"),
    [
        (
            "import functools\n" 'register = functools.partial(app.get, "/api/v1/partial-route")\n',
            "register()(handler)",
            "registration:get:<missing>",
        ),
        (
            'register = {"route": app.get}["route"]\n',
            'register("/api/v1/mapping-route")(handler)',
            "registration:get:/api/v1/mapping-route",
        ),
        (
            'routes = {"route": app.get}\nregister = routes["route"]\n',
            'register("/api/v1/assigned-mapping-route")(handler)',
            "registration:get:/api/v1/assigned-mapping-route",
        ),
        (
            "register = [app.get][0]\n",
            'register("/api/v1/sequence-route")(handler)',
            "registration:get:/api/v1/sequence-route",
        ),
        (
            "register = app.get.__call__\n",
            'register("/api/v1/call-route")(handler)',
            "registration:get:/api/v1/call-route",
        ),
    ],
    ids=["partial", "mapping", "assigned-mapping", "sequence", "dunder-call"],
)
def test_legacy_growth_guard_preserves_opaque_route_callable_provenance(
    setup: str,
    registration: str,
    expected: str,
) -> None:
    source = f"{setup}{registration}\n"

    assert legacy_guard.validate_legacy_growth(source) == [
        f"legacy_app.py: unexpected legacy route growth: {expected}"
    ]


def test_legacy_growth_guard_does_not_unwrap_shadowed_partial() -> None:
    source = textwrap.dedent("""
        from functools import partial

        partial = safe_partial
        register = partial(app.get)
        register("/api/v1/not-a-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_preserves_route_decorator_through_partial() -> None:
    source = textwrap.dedent("""
        from functools import partial

        decorator = partial(app.get("/api/v1/partial-decorator"))
        decorator(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/partial-decorator"
    ]


def test_legacy_growth_guard_uses_last_duplicate_literal_mapping_value() -> None:
    source = textwrap.dedent("""
        register = {"route": app.get, "route": None}["route"]
        register("/api/v1/not-a-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_resolves_later_static_mapping_unpack() -> None:
    source = textwrap.dedent("""
        routes = {"route": app.get}
        register = {"route": None, **routes}["route"]
        register("/api/v1/unpacked-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: " "registration:get:/api/v1/unpacked-route"
    ]


def test_legacy_growth_guard_honors_later_literal_after_mapping_unpack() -> None:
    source = textwrap.dedent("""
        routes = {"route": app.get}
        register = {**routes, "route": None}["route"]
        register("/api/v1/not-a-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


@pytest.mark.parametrize(
    ("mapping", "expected"),
    [
        (
            "{True: None, 1: app.get}",
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:get:/api/v1/equal-numeric-key-route"
            ],
        ),
        ("{1: app.get, 1.0: None}", []),
    ],
    ids=["later-equivalent-sensitive", "later-equivalent-safe"],
)
def test_legacy_growth_guard_uses_python_numeric_key_equivalence(
    mapping: str,
    expected: list[str],
) -> None:
    source = (
        f"register = {mapping}[True]\n" 'register("/api/v1/equal-numeric-key-route")(handler)\n'
    )

    assert legacy_guard.validate_legacy_growth(source) == expected


def test_legacy_growth_guard_keeps_unresolved_mapping_unpack_fail_closed() -> None:
    source = textwrap.dedent("""
        routes = resolve_routes()
        register = {"route": None, **routes}["route"]
        register("/api/v1/unresolved-unpack-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:dynamic:/api/v1/unresolved-unpack-route"
    ]


def test_legacy_growth_guard_honors_later_literal_after_unresolved_unpack() -> None:
    source = textwrap.dedent("""
        routes = resolve_routes()
        register = {**routes, "route": None}["route"]
        register("/api/v1/not-a-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_keeps_known_safe_mapping_unpack_clean() -> None:
    source = textwrap.dedent("""
        routes = {"route": None}
        register = {"route": None, **routes}["route"]
        register("/api/v1/not-a-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_honors_later_known_safe_mapping_unpack() -> None:
    source = textwrap.dedent("""
        routes = {"route": None}
        register = {"route": app.get, **routes}["route"]
        register("/api/v1/not-a-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_invalidates_mutated_static_mapping() -> None:
    source = textwrap.dedent("""
        routes = {"route": None}
        routes.update(resolve_routes())
        register = {"route": None, **routes}["route"]
        register("/api/v1/mutated-mapping-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:dynamic:/api/v1/mutated-mapping-route"
    ]


def test_legacy_growth_guard_invalidates_escaped_mapping_by_identity() -> None:
    source = textwrap.dedent("""
        routes = {"route": None}
        alias = routes

        def rebind(value):
            global routes
            routes = {"route": None}

        rebind(routes)
        register = {"route": app.get, **alias}["route"]
        register("/api/v1/escaped-mapping-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:dynamic:/api/v1/escaped-mapping-route"
    ]


def test_legacy_growth_guard_snapshots_mapping_unpack_before_rebinding() -> None:
    source = textwrap.dedent("""
        base = {"route": app.get}
        routes = {**base}
        base = {"route": None}
        register = {"route": None, **routes}["route"]
        register("/api/v1/copied-before-rebind")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/copied-before-rebind"
    ]


def test_legacy_growth_guard_snapshots_mapping_value_before_rebinding() -> None:
    source = textwrap.dedent("""
        method = app.get
        routes = {"route": method}
        method = None
        register = routes["route"]
        register("/api/v1/value-before-rebind")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/value-before-rebind"
    ]


@pytest.mark.parametrize(
    "mutation, expected_method",
    [
        ('del routes["route"]', "get"),
        ('routes |= {"route": app.get}', "dynamic"),
        ('mutate = routes.update\nmutate({"route": app.get})', "dynamic"),
    ],
    ids=["delete", "in-place-union", "bound-mutator"],
)
def test_legacy_growth_guard_invalidates_mapping_mutation_aliases(
    mutation: str,
    expected_method: str,
) -> None:
    source = (
        'routes = {"route": None}\n'
        "alias = routes\n"
        f"{mutation}\n"
        'register = {"route": app.get, **alias}["route"]\n'
        'register("/api/v1/mutated-alias-route")(handler)\n'
    )

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        f"registration:{expected_method}:/api/v1/mutated-alias-route"
    ]


def test_legacy_growth_guard_keeps_in_place_mapping_rebinding_fail_closed() -> None:
    source = textwrap.dedent("""
        routes = {"route": None}
        routes |= {"route": app.get}
        register = routes["route"]
        register("/api/v1/in-place-union-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:dynamic:/api/v1/in-place-union-route"
    ]


@pytest.mark.parametrize(
    "escape",
    [
        """
        def mutate(value=routes):
            value["route"] = app.get

        mutate()
        """,
        """
        def get_routes():
            return routes

        alias = get_routes()
        alias["route"] = app.get
        """,
        """
        holder.routes = routes
        holder.routes["route"] = app.get
        """,
        """
        holder = [routes]
        holder[0]["route"] = app.get
        """,
        """
        holder = {"value": routes}
        holder["value"]["route"] = app.get
        """,
        """
        def mutate(*args):
            args[0]["route"] = app.get

        mutate(*(routes,))
        """,
        """
        def mutate(**kwargs):
            kwargs["routes"]["route"] = app.get

        mutate(**{"routes": routes})
        """,
    ],
    ids=[
        "default-argument",
        "returned-alias",
        "attribute-storage",
        "sequence-storage",
        "mapping-storage",
        "starred-argument",
        "expanded-keyword",
    ],
)
def test_legacy_growth_guard_invalidates_escaped_mapping_identities(
    escape: str,
) -> None:
    source = (
        'routes = {"route": None}\n'
        f"{textwrap.dedent(escape)}"
        'register = {"route": app.get, **routes}["route"]\n'
        'register("/api/v1/escaped-identity-route")(handler)\n'
    )

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:dynamic:/api/v1/escaped-identity-route"
    ]


def test_legacy_growth_guard_invalidates_pre_and_post_call_mapping_identities() -> None:
    source = textwrap.dedent("""
        routes = {"route": None}

        def mutate(value):
            value["route"] = app.get

        def factory():
            global routes
            routes = {"route": None}
            return mutate

        factory()(routes)
        register = {"route": app.get, **routes}["route"]
        register("/api/v1/evaluation-order-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:dynamic:/api/v1/evaluation-order-route"
    ]


def test_legacy_growth_guard_bounds_long_static_mapping_chains() -> None:
    source = 'mapping_0 = {"route": None}\n' + "".join(
        f"mapping_{index} = {{**mapping_{index - 1}}}\n" for index in range(1, 1_101)
    )
    source += (
        'register = {"route": app.get, **mapping_1100}["route"]\n'
        'register("/api/v1/not-a-route")(handler)\n'
    )

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_uses_unary_numeric_key_equivalence() -> None:
    source = textwrap.dedent("""
        register = {-1: app.get, -1.0: None}[-1]
        register("/api/v1/not-a-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


@pytest.mark.parametrize(
    "invocation",
    [
        "Child().install(app)",
        "Child.install(app)",
    ],
    ids=["instance", "class"],
)
def test_legacy_growth_guard_replays_inherited_class_helpers(invocation: str) -> None:
    decorator = "@classmethod\n    " if invocation == "Child.install(app)" else ""
    receiver = "cls, " if decorator else "self, "
    source = (
        "class Base:\n"
        f"    {decorator}def install({receiver}target):\n"
        '        target.get("/api/v1/inherited-route")(handler)\n'
        "\n"
        "class Child(Base):\n"
        "    pass\n"
        "\n"
        f"{invocation}\n"
    )

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: " "registration:get:/api/v1/inherited-route"
    ]


def test_legacy_growth_guard_replays_transitive_aliased_inherited_helper() -> None:
    source = textwrap.dedent("""
        class Base:
            def install(self, target):
                target.get("/api/v1/transitive-inherited-route")(handler)

        Alias = Base

        class Middle(Alias):
            pass

        class Child(Middle):
            pass

        Child().install(app)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/transitive-inherited-route"
    ]


def test_legacy_growth_guard_keeps_inherited_helper_non_app_argument_clean() -> None:
    source = textwrap.dedent("""
        class Base:
            def install(self, target):
                target.get("/api/v1/not-a-route")(handler)

        class Child(Base):
            pass

        Child().install(object())
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


@pytest.mark.parametrize(
    "child_body",
    [
        """
            def install(self, target):
                return None
        """,
        """
            install = None
        """,
    ],
    ids=["method", "non-callable"],
)
def test_legacy_growth_guard_honors_definite_inherited_helper_override(
    child_body: str,
) -> None:
    source = (
        "class Base:\n"
        "    def install(self, target):\n"
        '        target.get("/api/v1/not-a-route")(handler)\n'
        "\n"
        "class Child(Base):\n"
        f"{textwrap.indent(textwrap.dedent(child_body).strip(), '    ')}\n"
        "\n"
        "Child().install(app)\n"
    )

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_honors_inherited_helper_mro_precedence() -> None:
    source = textwrap.dedent("""
        class Safe:
            def install(self, target):
                return None

        class Dangerous:
            def install(self, target):
                target.get("/api/v1/not-a-route")(handler)

        class Child(Safe, Dangerous):
            pass

        Child().install(app)
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_keeps_conditional_helper_override_fail_closed() -> None:
    source = textwrap.dedent("""
        class Base:
            def install(self, target):
                target.get("/api/v1/conditional-inherited-route")(handler)

        class Child(Base):
            if enabled:
                def install(self, target):
                    return None

        Child().install(app)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/conditional-inherited-route"
    ]


def test_legacy_growth_guard_uses_c3_member_precedence_in_diamonds() -> None:
    source = textwrap.dedent("""
        class Root:
            def install(self, target):
                return None

        class Left(Root):
            pass

        class Right(Root):
            def install(self, target):
                target.get("/api/v1/diamond-danger")(handler)

        class Child(Left, Right):
            pass

        Child().install(app)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: " "registration:get:/api/v1/diamond-danger"
    ]


def test_legacy_growth_guard_excludes_class_global_bindings_from_members() -> None:
    source = textwrap.dedent("""
        class Base:
            def install(self, target):
                target.get("/api/v1/class-global-danger")(handler)

        class Child(Base):
            global install
            install = None

        Child().install(app)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/class-global-danger"
    ]


def test_legacy_growth_guard_excludes_class_nonlocal_bindings_from_members() -> None:
    source = textwrap.dedent("""
        class Base:
            def install(self, target):
                target.get("/api/v1/class-nonlocal-danger")(handler)

        def build():
            install = None

            class Child(Base):
                nonlocal install
                install = None

            return Child

        build()().install(app)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/class-nonlocal-danger"
    ]


def test_legacy_growth_guard_preserves_method_after_value_less_annotation() -> None:
    source = textwrap.dedent("""
        class Child:
            def install(self, target):
                target.get("/api/v1/annotated-direct-danger")(handler)

            install: object

        Child().install(app)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/annotated-direct-danger"
    ]


@pytest.mark.parametrize(
    ("wrapper", "parameters", "target", "invocation"),
    [
        ("staticmethod", "target", "target", "Child().install(app)"),
        ("classmethod", "cls, target", "target", "Child.install(app)"),
    ],
)
def test_legacy_growth_guard_resolves_class_callable_wrappers(
    wrapper: str,
    parameters: str,
    target: str,
    invocation: str,
) -> None:
    source = textwrap.dedent(f"""
        def dangerous_install({parameters}):
            {target}.get("/api/v1/wrapped-class-danger")(handler)

        class Child:
            install = {wrapper}(dangerous_install)

        {invocation}
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/wrapped-class-danger"
    ]


def test_legacy_growth_guard_resolves_inherited_classmethod_wrapper() -> None:
    source = textwrap.dedent("""
        def dangerous_install(cls, target):
            target.get("/api/v1/inherited-classmethod-danger")(handler)

        class Base:
            install = classmethod(dangerous_install)

        class Child(Base):
            pass

        Child.install(app)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/inherited-classmethod-danger"
    ]


def test_legacy_growth_guard_keeps_safe_classmethod_wrapper_clean() -> None:
    source = textwrap.dedent("""
        def harmless_install(cls, target):
            return None

        class Child:
            install = classmethod(harmless_install)

        Child.install(app)
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_scopes_classmethod_wrapper_to_owning_member() -> None:
    source = textwrap.dedent("""
        def dangerous_install(target):
            target.get("/api/v1/shared-classmethod-danger")(handler)

        class Plain:
            install = dangerous_install

        class Wrapped:
            install = classmethod(dangerous_install)

        Plain.install(app)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/shared-classmethod-danger"
    ]


def test_legacy_growth_guard_scopes_staticmethod_wrapper_to_owning_member() -> None:
    source = textwrap.dedent("""
        def dangerous_install(self, target):
            target.get("/api/v1/shared-staticmethod-danger")(handler)

        class Plain:
            install = dangerous_install

        class Wrapped:
            install = staticmethod(dangerous_install)

        Plain().install(app)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/shared-staticmethod-danger"
    ]


def test_legacy_growth_guard_preserves_plain_alternative_to_staticmethod() -> None:
    source = textwrap.dedent("""
        def dangerous_install(self, target):
            target.get("/api/v1/conditional-plain-danger")(handler)

        class Child:
            if condition:
                install = staticmethod(dangerous_install)
            else:
                install = dangerous_install

        Child().install(app)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/conditional-plain-danger"
    ]


def test_legacy_growth_guard_preserves_staticmethod_alternative_to_plain() -> None:
    source = textwrap.dedent("""
        def dangerous_install(target):
            target.get("/api/v1/conditional-staticmethod-danger")(handler)

        class Child:
            if condition:
                install = staticmethod(dangerous_install)
            else:
                install = dangerous_install

        Child().install(app)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/conditional-staticmethod-danger"
    ]


def test_legacy_growth_guard_preserves_bound_classmethod_alias() -> None:
    source = textwrap.dedent("""
        class Installer:
            @classmethod
            def install(cls, target):
                target.get("/api/v1/classmethod-alias-danger")(handler)

        install = Installer.install
        install(app)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/classmethod-alias-danger"
    ]


def test_legacy_growth_guard_preserves_bound_instance_method_alias() -> None:
    source = textwrap.dedent("""
        class Installer:
            def install(self, target):
                target.get("/api/v1/instance-method-alias-danger")(handler)

        install = Installer().install
        install(app)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/instance-method-alias-danger"
    ]


def test_legacy_growth_guard_unions_replayed_class_site_members() -> None:
    source = textwrap.dedent("""
        def dangerous(self, target):
            target.get("/api/v1/replay-overwrite-hidden")(handler)

        def harmless(self, target):
            return None

        def factory(value):
            class Child:
                install = value

            return Child

        Dangerous = factory(dangerous)
        Safe = factory(harmless)
        Dangerous().install(app)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/replay-overwrite-hidden"
    ]


@pytest.mark.parametrize(
    "container",
    [
        """
        if enabled:
            class Installer:
                def install(self, target):
                    target.get("/api/v1/conditional-class-danger")(handler)
        """,
        """
        for _ in values:
            class Installer:
                def install(self, target):
                    target.get("/api/v1/conditional-class-danger")(handler)
        """,
    ],
    ids=["branch", "loop"],
)
def test_legacy_growth_guard_preserves_possible_class_references(
    container: str,
) -> None:
    source = textwrap.dedent(container) + "\nInstaller().install(app)\n"

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/conditional-class-danger"
    ]


def test_legacy_growth_guard_converges_for_nested_loop_function_bindings() -> None:
    source = textwrap.dedent("""
        def configure():
            for _ in values:
                def install(target):
                    target.get("/api/v1/local-loop-def")(handler)

            install(app)

        configure()
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: " "registration:get:/api/v1/local-loop-def"
    ]


def test_legacy_growth_guard_converges_for_self_nested_iterable_provenance() -> None:
    source = textwrap.dedent("""
        def install(target):
            target.get("/api/v1/not-called-from-self-nested-list")(handler)

        items = [install]
        for _ in values:
            items = [items]
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_iterable_provenance_normalization_is_bounded_idempotent_and_fail_closed() -> None:
    binding = legacy_guard._ResolvedBinding(
        reference="pulseplate.app.get",
        string=None,
    )
    for _ in range(20):
        binding = legacy_guard._ResolvedBinding(
            reference=legacy_guard._KNOWN_NON_APP_REFERENCE,
            string=None,
            iterable_element=binding,
        )

    normalized = legacy_guard._normalize_resolved_binding(binding)
    cursor = normalized
    node_count = 1
    while cursor.iterable_element is not None:
        cursor = cursor.iterable_element
        node_count += 1

    assert node_count <= legacy_guard._MAX_ITERABLE_ELEMENT_BINDING_DEPTH + 2
    assert cursor.reference == legacy_guard._POSSIBLE_APP_CALL_REFERENCE
    assert legacy_guard._normalize_resolved_binding(normalized) == normalized
    assert legacy_guard._ApiKeyLookupVisitor._argument_binding_may_register(normalized)


def test_legacy_growth_guard_keeps_deep_iterable_overflow_fail_closed() -> None:
    source = textwrap.dedent("""
        def consume(level0):
            for level1 in level0:
                for level2 in level1:
                    for level3 in level2:
                        for level4 in level3:
                            for level5 in level4:
                                for level6 in level5:
                                    for level7 in level6:
                                        for level8 in level7:
                                            for level9 in level8:
                                                level9("/api/v1/deep-provenance")(handler)

        deep = [[[[[[[[[app.get]]]]]]]]]
        consume(deep)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:dynamic:/api/v1/deep-provenance"
    ]


@pytest.mark.parametrize(
    "safe_rebinding",
    [
        "app = None",
        "safe_app = None\napp = safe_app",
        "app = lambda: None",
        "def app():\n    return None",
        "class app:\n    pass",
    ],
    ids=["literal", "name", "lambda", "function", "class"],
)
def test_legacy_growth_guard_clears_dynamic_app_after_definite_safe_rebinding(
    safe_rebinding: str,
) -> None:
    source = (
        "app = resolve_app()\n" f"{safe_rebinding}\n" 'app.get("/api/v1/not-a-route")(handler)\n'
    )

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_keeps_unknown_name_app_rebinding_fail_closed() -> None:
    source = textwrap.dedent("""
        app = resolve_app()
        app = safe_app
        app.get("/api/v1/unknown-name-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/unknown-name-route"
    ]


def test_legacy_growth_guard_clears_dynamic_app_after_builtin_object_rebinding() -> None:
    source = textwrap.dedent("""
        app = resolve_app()
        app = object()
        app.get("/api/v1/not-a-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_keeps_globals_object_rebinding_fail_closed() -> None:
    source = textwrap.dedent("""
        app = resolve_app()
        globals()["object"] = lambda: app
        app = object()
        app.get("/api/v1/globals-object-rebind")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/globals-object-rebind"
    ]


@pytest.mark.parametrize("namespace", ["globals()", "vars()"], ids=["globals", "vars"])
def test_legacy_growth_guard_preserves_module_object_factory_provenance(
    namespace: str,
) -> None:
    source = textwrap.dedent(f"""
        {namespace}["object"] = lambda: app
        route = object().get
        route("/api/v1/module-object-factory")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:dynamic:/api/v1/module-object-factory"
    ]


@pytest.mark.parametrize(
    "constructor",
    ["object()", "builtins.object()"],
    ids=["implicit-builtin", "direct-builtin-attribute"],
)
def test_legacy_growth_guard_keeps_poisoned_builtins_object_fail_closed(
    constructor: str,
) -> None:
    source = textwrap.dedent(f"""
        import builtins

        app = resolve_app()
        builtins.object = lambda: app
        app = {constructor}
        app.get("/api/v1/builtins-object-rebind")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/builtins-object-rebind"
    ]


def test_legacy_growth_guard_preserves_app_bound_to_builtins_object() -> None:
    source = textwrap.dedent("""
        import builtins

        builtins.object = app
        object.get("/api/v1/object-app-instance")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/object-app-instance"
    ]


@pytest.mark.parametrize(
    ("capture", "mutation"),
    [
        ("", 'object.__setattr__(builtins, "object", lambda: app)'),
        ("", 'builtins.object.__setattr__(builtins, "object", lambda: app)'),
        (
            "descriptor = object\n",
            'descriptor.__setattr__(builtins, "object", lambda: app)',
        ),
    ],
    ids=["implicit-builtin", "builtins-attribute", "captured-builtin"],
)
def test_legacy_growth_guard_tracks_builtin_object_descriptor_mutation(
    capture: str,
    mutation: str,
) -> None:
    source = (
        textwrap.dedent("""
        import builtins

        app = resolve_app()
        """)
        + capture
        + mutation
        + "\n"
        + textwrap.dedent("""
        app = object()
        app.get("/api/v1/descriptor-route")(handler)
        """)
    )

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/descriptor-route"
    ]


def test_legacy_growth_guard_does_not_poison_foreign_descriptor_target() -> None:
    source = textwrap.dedent("""
        import builtins

        class Box:
            pass

        app = resolve_app()
        box = Box()
        object.__setattr__(box, "object", lambda: app)
        app = object()
        app.get("/api/v1/not-a-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


@pytest.mark.parametrize(
    ("use_captured", "expected_error"),
    [
        (
            'route_app = captured()\nroute_app.get("/api/v1/captured-object-route")(handler)',
            "legacy_app.py: unexpected legacy route growth: "
            "registration:get:/api/v1/captured-object-route",
        ),
        (
            "router = captured()\napp.include_router(router)",
            "legacy_app.py: unexpected legacy route growth: " "registration:include_router:router",
        ),
        (
            "def invoke(factory):\n"
            "    return factory()\n"
            "route_app = invoke(captured)\n"
            'route_app.get("/api/v1/helper-captured-object-route")(handler)',
            "legacy_app.py: unexpected legacy route growth: "
            "registration:get:/api/v1/helper-captured-object-route",
        ),
    ],
    ids=["route", "router", "helper"],
)
def test_legacy_growth_guard_preserves_poisoned_object_capture_provenance(
    use_captured: str,
    expected_error: str,
) -> None:
    source = textwrap.dedent("""
        import builtins

        app = resolve_app()
        original_object = builtins.object
        builtins.object = lambda: app
        captured = builtins.object
        builtins.object = original_object
        """) + f"{use_captured}\n"

    assert legacy_guard.validate_legacy_growth(source) == [expected_error]


def test_legacy_growth_guard_rejects_poisoned_object_capture_as_decorator_factory() -> None:
    source = textwrap.dedent("""
        import builtins

        app = resolve_app()
        original_object = builtins.object
        builtins.object = lambda: app.get("/api/v1/poisoned-decorator-factory")
        captured = builtins.object
        builtins.object = original_object

        @captured()
        def poisoned_decorator_factory():
            return None
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "decorator:dynamic:<missing> -> poisoned_decorator_factory"
    ]


@pytest.mark.parametrize(
    ("setup", "factory_expression"),
    [
        ("holder = (captured,)\n", "holder[0]"),
        ('factories = {"factory": captured}\n', 'factories["factory"]'),
        ("", "partial(captured)"),
        (
            "def identity(factory):\n" "    return factory\n",
            "identity(captured)",
        ),
        ("", "(lambda factory: factory)(captured)"),
        (
            "class Holder:\n" "    factory = captured\n",
            "Holder.factory",
        ),
        (
            "class Holder:\n" "    factory = captured\n",
            'getattr(Holder, "factory")',
        ),
    ],
    ids=[
        "tuple-index",
        "mapping-index",
        "partial",
        "helper-wrapper",
        "lambda-wrapper",
        "class-attribute",
        "getattr-alias",
    ],
)
def test_legacy_growth_guard_rejects_wrapped_poisoned_object_decorator_factories(
    setup: str,
    factory_expression: str,
) -> None:
    source = (
        textwrap.dedent("""
        import builtins
        from functools import partial

        app = resolve_app()
        original_object = builtins.object
        builtins.object = lambda: app.get("/api/v1/poisoned-wrapped-decorator")
        captured = builtins.object
        builtins.object = original_object
        """)
        + setup
        + textwrap.dedent(f"""
        @{factory_expression}()
        def poisoned_wrapped_decorator_factory():
            return None
        """)
    )

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "decorator:dynamic:<missing> -> poisoned_wrapped_decorator_factory"
    ]


def test_legacy_growth_guard_preserves_loop_bound_class_factory_provenance() -> None:
    source = textwrap.dedent("""
        import builtins

        app = resolve_app()
        original_object = builtins.object
        builtins.object = lambda: app.get("/api/v1/looped-class-factory")
        captured = builtins.object
        builtins.object = original_object

        class Holder:
            for _ in [1]:
                factory = captured

        @Holder.factory()
        def looped_class_factory():
            return None
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "decorator:dynamic:<missing> -> looped_class_factory"
    ]


def test_legacy_growth_guard_preserves_identity_map_mapping_values() -> None:
    source = textwrap.dedent("""
        routes = {"route": app.get}

        for route in map(lambda value: value, routes.values()):
            route("/api/v1/identity-map-value")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/identity-map-value"
    ]


def test_legacy_growth_guard_preserves_chain_mapping_values() -> None:
    source = textwrap.dedent("""
        from itertools import chain

        routes = {"route": app.get}

        for route in chain(routes.values()):
            route("/api/v1/chain-mapping-value")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/chain-mapping-value"
    ]


def test_legacy_growth_guard_preserves_islice_mapping_values() -> None:
    source = textwrap.dedent("""
        from itertools import islice

        routes = {"route": app.get}
        for route in islice(routes.values(), 1):
            route("/api/v1/islice-map-value")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/islice-map-value"
    ]


@pytest.mark.parametrize(
    "arguments",
    ["0", "0, 0", "1, 1"],
    ids=["zero-stop", "zero-range", "equal-range"],
)
def test_legacy_growth_guard_keeps_proven_empty_islice_clean(arguments: str) -> None:
    source = textwrap.dedent(f"""
        from itertools import islice

        routes = {{"route": app.get}}
        for route in islice(routes.values(), {arguments}):
            route("/api/v1/not-a-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_preserves_chain_from_iterable_mapping_values() -> None:
    source = textwrap.dedent("""
        from itertools import chain

        routes = {"route": app.get}

        for route in chain.from_iterable([routes.values()]):
            route("/api/v1/chain-from-iterable")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/chain-from-iterable"
    ]


def test_legacy_growth_guard_preserves_static_dict_comprehension_mapping() -> None:
    source = textwrap.dedent("""
        routes = {key: registrar for key, registrar in [("route", app.get)]}
        route = routes.get("route")
        route("/api/v1/dict-comprehension")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/dict-comprehension"
    ]


def test_legacy_growth_guard_preserves_filtered_dict_comprehension_mapping() -> None:
    source = textwrap.dedent("""
        routes = {
            key: registrar
            for key, registrar in [("route", app.get)]
            if True
        }
        route = routes.get("route")
        route("/api/v1/filtered-dict-comprehension")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/filtered-dict-comprehension"
    ]


def test_legacy_growth_guard_preserves_bound_items_pair_values() -> None:
    source = textwrap.dedent("""
        routes = {"route": app.get}

        for pair in routes.items():
            route = pair[1]
            route("/api/v1/bound-items-pair")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:dynamic:/api/v1/bound-items-pair"
    ]


def test_legacy_growth_guard_applies_known_mapping_update_last_write_wins() -> None:
    source = textwrap.dedent("""
        safe_register = lambda _path: lambda _handler: None
        routes = {"route": app.get}
        routes.update({"route": safe_register})
        route = routes.get("route")
        route("/api/v1/known-update")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_preserves_literal_mapping_copy() -> None:
    source = textwrap.dedent("""
        route = {"route": app.get}.copy().get("route")
        route("/api/v1/literal-copy")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: registration:get:/api/v1/literal-copy"
    ]


def test_legacy_growth_guard_preserves_fixed_literal_values_for_starred_assignment() -> None:
    source = textwrap.dedent("""
        safe_register = lambda _path: lambda _handler: None
        route, *rest = [safe_register, app.get]
        route("/api/v1/starred-safe")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_resolves_direct_class_registrar_member() -> None:
    source = textwrap.dedent("""
        class Holder:
            factory = app.get

        @Holder.factory("/api/v1/direct-class-member")
        def direct_class_member():
            return None
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "decorator:get:/api/v1/direct-class-member -> direct_class_member"
    ]


@pytest.mark.parametrize(
    ("setup", "decorator"),
    [
        ("", "property"),
        ("from functools import cached_property", "cached_property"),
    ],
    ids=["property", "cached-property"],
)
def test_legacy_growth_guard_resolves_descriptor_registrar_member(
    setup: str,
    decorator: str,
) -> None:
    source = textwrap.dedent(f"""
        {setup}

        class Holder:
            @{decorator}
            def factory(self):
                return app.get

        Holder().factory("/api/v1/descriptor-member")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/descriptor-member"
    ]


@pytest.mark.parametrize(
    "factory_expression",
    ["Holder().factory", 'getattr(Holder(), "factory")'],
    ids=["attribute", "getattr"],
)
def test_legacy_growth_guard_rejects_poisoned_object_instance_decorator_factory(
    factory_expression: str,
) -> None:
    source = textwrap.dedent(f"""
        import builtins

        app = resolve_app()
        original_object = builtins.object
        builtins.object = lambda: app.get("/api/v1/poisoned-instance-decorator")
        captured = builtins.object
        builtins.object = original_object

        class Holder:
            def __init__(self):
                self.factory = captured

        @{factory_expression}()
        def poisoned_instance_decorator_factory():
            return None
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "decorator:dynamic:<missing> -> poisoned_instance_decorator_factory"
    ]


def test_legacy_growth_guard_does_not_trust_unreachable_instance_rebind() -> None:
    source = textwrap.dedent("""
        import builtins

        app = resolve_app()
        original_object = builtins.object
        builtins.object = lambda: app.get("/api/v1/poisoned-unreachable-instance")
        captured = builtins.object
        builtins.object = original_object

        def safe_factory():
            return lambda function: function

        class Holder:
            factory = captured

            def __init__(self):
                return
                self.factory = safe_factory

        @Holder().factory()
        def poisoned_unreachable_instance_rebind():
            return None
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "decorator:dynamic:<missing> -> poisoned_unreachable_instance_rebind"
    ]


def test_legacy_growth_guard_keeps_reachable_instance_factory_after_false_exit() -> None:
    source = textwrap.dedent("""
        import builtins

        app = resolve_app()
        original_object = builtins.object
        builtins.object = lambda: app.get("/api/v1/poisoned-reachable-instance")
        captured = builtins.object
        builtins.object = original_object

        class Holder:
            def __init__(self):
                if False:
                    return
                self.factory = captured

        @Holder().factory()
        def poisoned_reachable_instance_factory():
            return None
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "decorator:dynamic:<missing> -> poisoned_reachable_instance_factory"
    ]


@pytest.mark.parametrize(
    ("holder_setup", "factory_expression", "function_name"),
    [
        (
            """
            class Holder:
                factory = safe_factory

                def __init__(self, enabled):
                    if enabled:
                        self.factory = captured
            """,
            "Holder(True).factory",
            "poisoned_conditional_instance_factory",
        ),
        (
            """
            class Holder:
                if enabled:
                    factory = captured
            """,
            "Holder.factory",
            "poisoned_conditional_class_factory",
        ),
        (
            """
            class Holder:
                factory = safe_factory

            if enabled:
                Holder.factory = captured
            """,
            "Holder.factory",
            "poisoned_conditional_module_factory",
        ),
        (
            """
            class Holder:
                factory = safe_factory

            if enabled:
                setattr(Holder, "factory", captured)
            """,
            "Holder.factory",
            "poisoned_conditional_setattr_factory",
        ),
        (
            """
            class Holder:
                factory = captured

                def __init__(self):
                    while True:
                        return
                    self.factory = safe_factory
            """,
            "Holder().factory",
            "poisoned_terminal_loop_factory",
        ),
    ],
    ids=[
        "instance-if",
        "class-if",
        "module-if",
        "module-setattr-if",
        "terminal-loop",
    ],
)
def test_legacy_growth_guard_rejects_poisoned_control_flow_decorator_factories(
    holder_setup: str,
    factory_expression: str,
    function_name: str,
) -> None:
    source = (
        textwrap.dedent(f"""
        import builtins

        app = resolve_app()
        original_object = builtins.object
        builtins.object = lambda: app.get("/api/v1/{function_name}")
        captured = builtins.object
        builtins.object = original_object

        def safe_factory():
            return lambda function: function

        enabled = True
        """)
        + textwrap.dedent(holder_setup)
        + textwrap.dedent(f"""

        @{factory_expression}()
        def {function_name}():
            return None
        """)
    )

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        f"decorator:dynamic:<missing> -> {function_name}"
    ]


def test_legacy_growth_guard_rejects_inherited_poisoned_decorator_factory() -> None:
    source = textwrap.dedent("""
        import builtins

        app = resolve_app()
        original_object = builtins.object
        builtins.object = lambda: app.get("/api/v1/inherited-poisoned-factory")
        captured = builtins.object
        builtins.object = original_object

        class Base:
            factory = captured

        class Holder(Base):
            pass

        @Holder.factory()
        def inherited_poisoned_decorator_factory():
            return None
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "decorator:dynamic:<missing> -> inherited_poisoned_decorator_factory"
    ]


def test_legacy_growth_guard_allows_proven_safe_inherited_factory_override() -> None:
    source = textwrap.dedent("""
        import builtins

        app = resolve_app()
        original_object = builtins.object
        builtins.object = lambda: app.get("/api/v1/inherited-poisoned-factory")
        captured = builtins.object
        builtins.object = original_object

        def safe_factory():
            return lambda function: function

        class Base:
            factory = captured

        class Holder(Base):
            if True:
                factory = safe_factory

        @Holder.factory()
        def inherited_safe_override():
            return None
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_rejects_staticmethod_wrapped_poisoned_factory() -> None:
    source = textwrap.dedent("""
        import builtins

        app = resolve_app()
        original_object = builtins.object
        builtins.object = lambda: app.get("/api/v1/staticmethod-poisoned-factory")
        captured = builtins.object
        builtins.object = original_object

        class Base:
            factory = captured

        class Holder(Base):
            factory = staticmethod(captured)

        @Holder.factory()
        def staticmethod_poisoned_factory():
            return None
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "decorator:dynamic:<missing> -> staticmethod_poisoned_factory"
    ]


def test_legacy_growth_guard_allows_safe_staticmethod_factory_override() -> None:
    source = textwrap.dedent("""
        import builtins

        app = resolve_app()
        original_object = builtins.object
        builtins.object = lambda: app.get("/api/v1/staticmethod-poisoned-factory")
        captured = builtins.object
        builtins.object = original_object

        class Base:
            factory = captured

        class Holder(Base):
            @staticmethod
            def factory():
                return lambda function: function

        @Holder.factory()
        def safe_staticmethod_factory():
            return None
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


@pytest.mark.parametrize(
    "safe_rebind",
    [
        "Holder.factory = safe_factory",
        'setattr(Holder, "factory", safe_factory)',
    ],
    ids=["attribute-assignment", "setattr"],
)
def test_legacy_growth_guard_keeps_safely_rebound_class_decorator_factory(
    safe_rebind: str,
) -> None:
    source = textwrap.dedent(f"""
        import builtins

        app = resolve_app()
        original_object = builtins.object
        builtins.object = lambda: app.get("/api/v1/not-a-poisoned-class-decorator")
        captured = builtins.object
        builtins.object = original_object

        def safe_factory():
            return lambda function: function

        class Holder:
            factory = captured

        {safe_rebind}

        @Holder.factory()
        def safely_rebound_decorator_factory():
            return None
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


@pytest.mark.parametrize(
    ("setup", "factory_expression"),
    [
        ("holder = (captured,)\n", "holder[0]"),
        ('factories = {"factory": captured}\n', 'factories["factory"]'),
        ("", "partial(captured)"),
        (
            "def identity(factory):\n" "    return factory\n",
            "identity(captured)",
        ),
        ("", "(lambda factory: factory)(captured)"),
        (
            "class Holder:\n" "    factory = captured\n",
            "Holder.factory",
        ),
        (
            "class Holder:\n" "    factory = captured\n",
            'getattr(Holder, "factory")',
        ),
    ],
    ids=[
        "tuple-index",
        "mapping-index",
        "partial",
        "helper-wrapper",
        "lambda-wrapper",
        "class-attribute",
        "getattr-alias",
    ],
)
def test_legacy_growth_guard_keeps_wrapped_safe_object_decorator_factories(
    setup: str,
    factory_expression: str,
) -> None:
    source = (
        textwrap.dedent("""
        import builtins
        from functools import partial

        app = resolve_app()
        captured = builtins.object
        builtins.object = lambda: app.get("/api/v1/not-a-poisoned-decorator")
        """)
        + setup
        + textwrap.dedent(f"""
        @{factory_expression}()
        def safe_wrapped_decorator_factory():
            return None
        """)
    )

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_keeps_safe_object_capture_after_namespace_poisoning() -> None:
    source = textwrap.dedent("""
        import builtins

        app = resolve_app()
        captured = builtins.object
        builtins.object = lambda: app
        captured().get("/api/v1/not-a-route")(handler)

        @captured()
        def safe_capture_control():
            return None
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


@pytest.mark.parametrize(
    "mutation",
    [
        "__builtins__.object = lambda: app",
        '__builtins__["object"] = lambda: app',
        '__import__("builtins").object = lambda: app',
        '__import__(*["builtins"]).object = lambda: app',
        '__import__(*(*["builtins"],)).object = lambda: app',
        '__import__(**{"name": "builtins"}).object = lambda: app',
    ],
    ids=[
        "dunder-builtins-attribute",
        "dunder-builtins-mapping",
        "builtin-importer",
        "starred-builtin-importer",
        "nested-starred-builtin-importer",
        "unpacked-keyword-builtin-importer",
    ],
)
def test_legacy_growth_guard_tracks_implicit_builtins_namespace_poisoning(
    mutation: str,
) -> None:
    source = textwrap.dedent(f"""
        app = resolve_app()
        {mutation}
        app = object()
        app.get("/api/v1/implicit-builtins-object-rebind")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/implicit-builtins-object-rebind"
    ]


def test_legacy_growth_guard_keeps_unresolved_builtin_import_fail_closed() -> None:
    source = textwrap.dedent("""
        app = resolve_app()
        __import__(*resolve_import_arguments()).object = lambda: app
        app = object()
        app.get("/api/v1/unresolved-builtin-import")(handler)
        """)
    expected = [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/unresolved-builtin-import"
    ]

    assert legacy_guard.validate_legacy_growth(source) == expected
    assert legacy_guard.validate_legacy_growth(source) == expected


def test_legacy_growth_guard_keeps_deep_builtin_import_star_fail_closed() -> None:
    nested_arguments = '*["builtins"]'
    for _depth in range(10):
        nested_arguments = f"*({nested_arguments},)"
    source = textwrap.dedent(f"""
        app = resolve_app()
        __import__({nested_arguments}).object = lambda: app
        app = object()
        app.get("/api/v1/deep-builtin-import")(handler)
        """)
    expected = [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/deep-builtin-import"
    ]

    assert legacy_guard.validate_legacy_growth(source) == expected
    assert legacy_guard.validate_legacy_growth(source) == expected


def test_legacy_growth_guard_keeps_exact_foreign_import_namespace_clean() -> None:
    source = textwrap.dedent("""
        app = resolve_app()
        __import__(*["types"]).object = lambda: app
        app = object()
        app.get("/api/v1/not-a-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_does_not_trust_shadowed_builtin_importer() -> None:
    source = textwrap.dedent("""
        class Box:
            pass

        def __import__(_name):
            return Box()

        app = resolve_app()
        __import__("builtins").object = lambda: app
        app = object()
        app.get("/api/v1/not-a-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


@pytest.mark.parametrize(
    "foreign_target",
    [
        'vars(some_obj)["object"]',
        'some_obj.__dict__["object"]',
    ],
    ids=["vars-object", "foreign-dunder-dict"],
)
def test_legacy_growth_guard_does_not_poison_object_for_foreign_namespaces(
    foreign_target: str,
) -> None:
    source = textwrap.dedent(f"""
        class Box:
            pass

        some_obj = Box()
        {foreign_target} = lambda: app
        app = object()
        app.get("/api/v1/not-a-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


@pytest.mark.parametrize(
    "setup, mutation",
    [
        (
            "def globals():\n    return {}\n",
            'globals()["object"] = lambda: app',
        ),
        (
            "def vars(_value=None):\n    return {}\nbox = object()\n",
            'vars(box)["object"] = lambda: app',
        ),
        (
            "class Fake:\n    pass\n" "fake = Fake()\n" "fake.modules = {__name__: Fake()}\n",
            'fake.modules[__name__].__dict__["object"] = lambda: app',
        ),
    ],
    ids=["shadowed-globals", "shadowed-vars", "foreign-modules-shape"],
)
def test_legacy_growth_guard_requires_proven_object_namespace(
    setup: str,
    mutation: str,
) -> None:
    source = (
        f"{setup}\n" f"{mutation}\n" "app = object()\n" 'app.get("/api/v1/not-a-route")(handler)\n'
    )

    assert legacy_guard.validate_legacy_growth(source) == []


@pytest.mark.parametrize(
    "mutation",
    [
        'globals()["object"] = lambda: app',
        "builtins.object = lambda: app",
    ],
    ids=["globals", "builtins"],
)
def test_legacy_growth_guard_propagates_object_poisoning_from_called_helper(
    mutation: str,
) -> None:
    source = textwrap.dedent(f"""
        import builtins

        app = resolve_app()

        def mutate():
            {mutation}

        mutate()
        app = object()
        app.get("/api/v1/helper-object-rebind")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/helper-object-rebind"
    ]


@pytest.mark.parametrize(
    ("setup", "helper_result", "mutation"),
    [
        ("import builtins", "builtins", 'setattr(expose(), "object", lambda: app)'),
        ("import builtins", "builtins", "expose().object = lambda: app"),
        ("import builtins", "vars(builtins)", 'expose()["object"] = lambda: app'),
        ("import builtins", "builtins.__dict__", 'expose()["object"] = lambda: app'),
        (
            "import builtins; import sys",
            "sys.modules[__name__].__dict__",
            'expose()["object"] = lambda: app',
        ),
    ],
    ids=["setattr", "attribute", "mapping", "builtins-dunder-dict", "module-dunder-dict"],
)
def test_legacy_growth_guard_replays_helper_returned_builtin_namespace(
    setup: str,
    helper_result: str,
    mutation: str,
) -> None:
    source = textwrap.dedent(f"""
        {setup}

        def expose():
            return {helper_result}

        app = resolve_app()
        {mutation}
        app = object()
        app.get("/api/v1/helper-namespace-rebind")(handler)
        """)
    expected = [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/helper-namespace-rebind"
    ]

    assert legacy_guard.validate_legacy_growth(source) == expected
    assert legacy_guard.validate_legacy_growth(source) == expected


@pytest.mark.parametrize(
    ("setup", "helper_result", "mutation"),
    [
        ("import types", "types", 'setattr(expose(), "object", lambda: app)'),
        (
            "class Box:\n    pass\nbox = Box()",
            "vars(box)",
            'expose()["object"] = lambda: app',
        ),
        (
            "class Box:\n    pass\nbox = Box()",
            "box.__dict__",
            'expose()["object"] = lambda: app',
        ),
    ],
    ids=["foreign-module", "arbitrary-object-mapping", "foreign-dunder-dict"],
)
def test_legacy_growth_guard_does_not_poison_helper_returned_foreign_namespace(
    setup: str,
    helper_result: str,
    mutation: str,
) -> None:
    source = (
        f"{setup}\n\n"
        "def expose():\n"
        f"    return {helper_result}\n\n"
        "app = resolve_app()\n"
        f"{mutation}\n"
        "app = object()\n"
        'app.get("/api/v1/not-a-route")(handler)\n'
    )

    assert legacy_guard.validate_legacy_growth(source) == []


@pytest.mark.parametrize(
    "mutation",
    [
        ("mutate = builtins.__dict__.__setitem__\n" 'mutate("object", lambda: app)'),
        (
            "def mutate():\n"
            "    assign = builtins.__dict__.__setitem__\n"
            '    assign("object", lambda: app)\n'
            "mutate()"
        ),
        ("mutate = sys.modules[__name__].__dict__.__setitem__\n" 'mutate("object", lambda: app)'),
    ],
    ids=["builtins-alias", "called-helper", "module-alias"],
)
def test_legacy_growth_guard_tracks_aliased_namespace_mutators(
    mutation: str,
) -> None:
    source = (
        "import builtins\n"
        "import sys\n\n"
        "app = resolve_app()\n"
        f"{mutation}\n"
        "app = object()\n"
        'app.get("/api/v1/aliased-namespace-mutator")(handler)\n'
    )
    expected = [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/aliased-namespace-mutator"
    ]

    assert legacy_guard.validate_legacy_growth(source) == expected
    assert legacy_guard.validate_legacy_growth(source) == expected


@pytest.mark.parametrize("method", ["__init__", "__ior__"])
@pytest.mark.parametrize(
    "namespace",
    ["builtins.__dict__", "sys.modules[__name__].__dict__"],
    ids=["builtins", "current-module"],
)
@pytest.mark.parametrize("aliased", [False, True], ids=["direct", "alias"])
def test_legacy_growth_guard_tracks_update_like_namespace_mutators(
    method: str,
    namespace: str,
    aliased: bool,
) -> None:
    target = f"{namespace}.{method}"
    mutation = (
        f"mutate = {target}\n" 'mutate({"object": lambda: app})'
        if aliased
        else f'{target}({{"object": lambda: app}})'
    )
    source = (
        "import builtins\n"
        "import sys\n\n"
        "app = resolve_app()\n"
        f"{mutation}\n"
        "app = object()\n"
        'app.get("/api/v1/update-like-namespace-mutator")(handler)\n'
    )
    expected = [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/update-like-namespace-mutator"
    ]

    assert legacy_guard.validate_legacy_growth(source) == expected
    assert legacy_guard.validate_legacy_growth(source) == expected


@pytest.mark.parametrize("method", ["__init__", "__ior__"])
@pytest.mark.parametrize(
    ("setup", "namespace", "key"),
    [
        ("import builtins", "builtins.__dict__", "safe_name"),
        ("class Box:\n    pass\nbox = Box()", "box.__dict__", "object"),
    ],
    ids=["safe-key", "foreign-namespace"],
)
def test_legacy_growth_guard_keeps_update_like_mutator_controls_clean(
    method: str,
    setup: str,
    namespace: str,
    key: str,
) -> None:
    source = (
        f"{setup}\n\n"
        "app = resolve_app()\n"
        f"{namespace}.{method}({{{key!r}: lambda: app}})\n"
        "app = object()\n"
        'app.get("/api/v1/not-a-route")(handler)\n'
    )

    assert legacy_guard.validate_legacy_growth(source) == []


@pytest.mark.parametrize(
    "namespace",
    ["builtins.__dict__", "sys.modules[__name__].__dict__"],
    ids=["builtins", "current-module"],
)
def test_legacy_growth_guard_tracks_namespace_alias_augmented_union(
    namespace: str,
) -> None:
    source = (
        "import builtins\n"
        "import sys\n\n"
        "app = resolve_app()\n"
        f"namespace = {namespace}\n"
        'namespace |= {"safe_name": lambda: None}\n'
        'namespace |= {"object": lambda: app}\n'
        "app = object()\n"
        'app.get("/api/v1/namespace-alias-augmented-union")(handler)\n'
    )
    expected = [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/namespace-alias-augmented-union"
    ]

    assert legacy_guard.validate_legacy_growth(source) == expected
    assert legacy_guard.validate_legacy_growth(source) == expected


@pytest.mark.parametrize(
    ("setup", "namespace", "key"),
    [
        ("import builtins", "builtins.__dict__", "safe_name"),
        (
            "import sys",
            "sys.modules[__name__].__dict__",
            "safe_name",
        ),
        ("class Box:\n    pass\nbox = Box()", "box.__dict__", "object"),
    ],
    ids=["builtins-safe-key", "module-safe-key", "foreign-namespace"],
)
def test_legacy_growth_guard_keeps_augmented_union_controls_clean(
    setup: str,
    namespace: str,
    key: str,
) -> None:
    source = (
        f"{setup}\n\n"
        f"namespace = {namespace}\n"
        "app = resolve_app()\n"
        f"namespace |= {{{key!r}: lambda: app}}\n"
        "app = object()\n"
        'app.get("/api/v1/not-a-route")(handler)\n'
    )

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_joins_protected_namespace_aliases() -> None:
    source = (
        "import builtins\n"
        "import os\n"
        "import sys\n\n"
        "app = resolve_app()\n"
        "namespace = (\n"
        "    builtins.__dict__\n"
        '    if os.getenv("USE_BUILTINS")\n'
        "    else sys.modules[__name__].__dict__\n"
        ")\n"
        'namespace |= {"safe_name": lambda: None}\n'
        'namespace |= {"object": lambda: app}\n'
        "app = object()\n"
        'app.get("/api/v1/joined-protected-namespace")(handler)\n'
    )
    expected = [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/joined-protected-namespace"
    ]

    assert legacy_guard.validate_legacy_growth(source) == expected
    assert legacy_guard.validate_legacy_growth(source) == expected


def test_legacy_growth_guard_keeps_safe_protected_namespace_join_clean() -> None:
    source = (
        "import builtins\n"
        "import os\n"
        "import sys\n\n"
        "namespace = (\n"
        "    builtins.__dict__\n"
        '    if os.getenv("USE_BUILTINS")\n'
        "    else sys.modules[__name__].__dict__\n"
        ")\n"
        "app = resolve_app()\n"
        'namespace |= {"safe_name": lambda: app}\n'
        "app = object()\n"
        'app.get("/api/v1/not-a-route")(handler)\n'
    )

    assert legacy_guard.validate_legacy_growth(source) == []


@pytest.mark.parametrize("method", ["__init__", "__ior__"])
@pytest.mark.parametrize(
    "namespace",
    ["builtins.__dict__", "sys.modules[__name__].__dict__"],
    ids=["builtins", "current-module"],
)
@pytest.mark.parametrize("aliased", [False, True], ids=["direct", "alias"])
def test_legacy_growth_guard_tracks_unbound_dict_namespace_mutators(
    method: str,
    namespace: str,
    aliased: bool,
) -> None:
    target = f"dict.{method}"
    mutation = (
        f"mutate = {target}\n" f'mutate({namespace}, {{"object": lambda: app}})'
        if aliased
        else f'{target}({namespace}, {{"object": lambda: app}})'
    )
    source = (
        "import builtins\n"
        "import sys\n\n"
        "app = resolve_app()\n"
        f"{mutation}\n"
        "app = object()\n"
        'app.get("/api/v1/unbound-dict-namespace-mutator")(handler)\n'
    )
    expected = [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/unbound-dict-namespace-mutator"
    ]

    assert legacy_guard.validate_legacy_growth(source) == expected
    assert legacy_guard.validate_legacy_growth(source) == expected


@pytest.mark.parametrize("method", ["__init__", "__ior__"])
@pytest.mark.parametrize(
    ("setup", "namespace", "key"),
    [
        ("import builtins", "builtins.__dict__", "safe_name"),
        ("class Box:\n    pass\nbox = Box()", "box.__dict__", "object"),
    ],
    ids=["safe-key", "foreign-namespace"],
)
def test_legacy_growth_guard_keeps_unbound_dict_mutator_controls_clean(
    method: str,
    setup: str,
    namespace: str,
    key: str,
) -> None:
    source = (
        f"{setup}\n\n"
        "app = resolve_app()\n"
        f"dict.{method}({namespace}, {{{key!r}: lambda: app}})\n"
        "app = object()\n"
        'app.get("/api/v1/not-a-route")(handler)\n'
    )

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_requires_proven_builtin_dict_mutator() -> None:
    source = (
        "class FakeDict:\n"
        "    @staticmethod\n"
        "    def __ior__(_namespace, _value):\n"
        "        return None\n\n"
        "dict = FakeDict\n"
        "import builtins\n\n"
        "app = resolve_app()\n"
        'dict.__ior__(builtins.__dict__, {"object": lambda: app})\n'
        "app = object()\n"
        'app.get("/api/v1/not-a-route")(handler)\n'
    )

    assert legacy_guard.validate_legacy_growth(source) == []


@pytest.mark.parametrize(
    "binding",
    [
        (
            'if os.getenv("USE_MUTATOR"):\n'
            "    mutate = dict.__ior__\n"
            "else:\n"
            "    mutate = lambda *_args: None"
        ),
        ("mutate = (dict.update " 'if os.getenv("USE_MUTATOR") else (lambda *_args: None))'),
    ],
    ids=["statement-ior", "expression-update"],
)
@pytest.mark.parametrize(
    "namespace",
    ["builtins.__dict__", "sys.modules[__name__].__dict__"],
    ids=["builtins", "current-module"],
)
def test_legacy_growth_guard_joins_unbound_dict_namespace_mutators(
    binding: str,
    namespace: str,
) -> None:
    source = (
        "import builtins\n"
        "import os\n"
        "import sys\n\n"
        "app = resolve_app()\n"
        f"{binding}\n"
        f'mutate({namespace}, {{"object": lambda: app}})\n'
        "app = object()\n"
        'app.get("/api/v1/joined-unbound-dict-mutator")(handler)\n'
    )
    expected = [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/joined-unbound-dict-mutator"
    ]

    assert legacy_guard.validate_legacy_growth(source) == expected
    assert legacy_guard.validate_legacy_growth(source) == expected


@pytest.mark.parametrize(
    ("setup", "namespace", "key"),
    [
        ("import builtins", "builtins.__dict__", "safe_name"),
        ("class Box:\n    pass\nbox = Box()", "box.__dict__", "object"),
        (
            "class FakeDict:\n"
            "    @staticmethod\n"
            "    def __ior__(_namespace, _value):\n"
            "        return None\n"
            "dict = FakeDict\n"
            "import builtins",
            "builtins.__dict__",
            "object",
        ),
    ],
    ids=["safe-key", "foreign-namespace", "shadowed-dict"],
)
def test_legacy_growth_guard_keeps_unbound_dict_mutator_joins_clean(
    setup: str,
    namespace: str,
    key: str,
) -> None:
    source = (
        f"{setup}\n"
        "import os\n\n"
        "mutate = (dict.__ior__ "
        'if os.getenv("USE_MUTATOR") else (lambda *_args: None))\n'
        "app = resolve_app()\n"
        f"mutate({namespace}, {{{key!r}: lambda: app}})\n"
        "app = object()\n"
        'app.get("/api/v1/not-a-route")(handler)\n'
    )

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_keeps_foreign_aliased_mutator_clean() -> None:
    source = textwrap.dedent("""
        class Box:
            pass

        box = Box()
        mutate = box.__dict__.__setitem__
        app = resolve_app()
        mutate("object", lambda: app)
        app = object()
        app.get("/api/v1/not-a-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


@pytest.mark.parametrize(
    "binding",
    [
        (
            'if os.getenv("USE_MUTATOR"):\n'
            "    mutate = builtins.__dict__.__setitem__\n"
            "else:\n"
            "    mutate = lambda *_args: None"
        ),
        (
            "mutate = lambda *_args: None\n"
            'if os.getenv("USE_MUTATOR"):\n'
            "    mutate = builtins.__dict__.__setitem__"
        ),
        (
            "mutate = (sys.modules[__name__].__dict__.__setitem__ "
            'if os.getenv("USE_MUTATOR") else (lambda *_args: None))'
        ),
        (
            "mutate = (builtins.__dict__.__setitem__ "
            'if os.getenv("USE_MUTATOR") '
            "else sys.modules[__name__].__dict__.__setitem__)"
        ),
    ],
    ids=["if-else", "one-armed-if", "module-if-expression", "cross-namespace"],
)
def test_legacy_growth_guard_joins_aliased_namespace_mutators(
    binding: str,
) -> None:
    source = (
        "import builtins\n"
        "import os\n"
        "import sys\n\n"
        "app = resolve_app()\n"
        f"{binding}\n"
        'mutate("object", lambda: app)\n'
        "app = object()\n"
        'app.get("/api/v1/joined-namespace-mutator")(handler)\n'
    )
    expected = [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/joined-namespace-mutator"
    ]

    assert legacy_guard.validate_legacy_growth(source) == expected
    assert legacy_guard.validate_legacy_growth(source) == expected


@pytest.mark.parametrize(
    "mutator",
    [
        "builtins.__dict__.__setitem__",
        "sys.modules[__name__].__dict__.__setitem__",
    ],
    ids=["builtins", "current-module"],
)
def test_legacy_growth_guard_keeps_other_sensitive_reference_at_mutator_join(
    mutator: str,
) -> None:
    source = (
        "import builtins\n"
        "import os\n"
        "import sys\n\n"
        "app = resolve_app()\n"
        'if os.getenv("USE_MUTATOR"):\n'
        f"    action = {mutator}\n"
        "else:\n"
        "    action = app.add_api_route\n"
        'action("/api/v1/mixed-sensitive-join", handler)\n'
    )
    expected = [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:dynamic:/api/v1/mixed-sensitive-join"
    ]

    assert legacy_guard.validate_legacy_growth(source) == expected
    assert legacy_guard.validate_legacy_growth(source) == expected


def test_legacy_growth_guard_keeps_mutator_at_non_callable_app_join() -> None:
    source = (
        "import builtins\n"
        "import os\n\n"
        "app = resolve_app()\n"
        'if os.getenv("USE_MUTATOR"):\n'
        "    action = builtins.__dict__.__setitem__\n"
        "else:\n"
        "    action = app\n"
        'action("object", lambda: app)\n'
        "app = object()\n"
        'app.get("/api/v1/app-object-mutator-join")(handler)\n'
    )
    expected = [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/app-object-mutator-join"
    ]

    assert legacy_guard.validate_legacy_growth(source) == expected
    assert legacy_guard.validate_legacy_growth(source) == expected


@pytest.mark.parametrize(
    ("setup", "binding", "key"),
    [
        (
            "import builtins\nimport os",
            (
                'mutate = (builtins.__dict__.__setitem__ if os.getenv("USE_MUTATOR") '
                "else (lambda *_args: None))"
            ),
            "safe_name",
        ),
        (
            "import os\nclass Box:\n    pass\nbox = Box()",
            (
                'mutate = (box.__dict__.__setitem__ if os.getenv("USE_MUTATOR") '
                "else (lambda *_args: None))"
            ),
            "object",
        ),
    ],
    ids=["safe-key", "foreign-namespace"],
)
def test_legacy_growth_guard_keeps_safe_namespace_mutator_joins_clean(
    setup: str,
    binding: str,
    key: str,
) -> None:
    source = (
        f"{setup}\n\n"
        "app = resolve_app()\n"
        f"{binding}\n"
        f'mutate("{key}", lambda: app)\n'
        "app = object()\n"
        'app.get("/api/v1/not-a-route")(handler)\n'
    )

    assert legacy_guard.validate_legacy_growth(source) == []


@pytest.mark.parametrize(
    "target",
    [
        'globals()["object"], other',
        '[globals()["object"], other]',
    ],
    ids=["tuple", "list"],
)
def test_legacy_growth_guard_recurses_into_destructured_object_targets(
    target: str,
) -> None:
    source = textwrap.dedent(f"""
        app = resolve_app()
        {target} = (lambda: app), None
        app = object()
        app.get("/api/v1/destructured-object-rebind")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/destructured-object-rebind"
    ]


@pytest.mark.parametrize(
    "setup, mutation",
    [
        ("", '*globals()["object"], other = [lambda: app], None'),
        ("", 'for globals()["object"] in [lambda: app]:\n    pass'),
        (
            "from contextlib import nullcontext\n",
            'with nullcontext(lambda: app) as globals()["object"]:\n    pass',
        ),
        (
            "import builtins\nnamespace = vars(builtins)\n",
            'namespace["object"] = lambda: app',
        ),
        (
            "import builtins\n",
            'setattr(builtins, "object", lambda: app)',
        ),
        (
            "import builtins\n",
            'vars(builtins).__setitem__("object", lambda: app)',
        ),
    ],
    ids=[
        "starred-target",
        "for-target",
        "with-target",
        "namespace-alias",
        "setattr",
        "mapping-mutator",
    ],
)
def test_legacy_growth_guard_poisoning_covers_real_mutation_paths(
    setup: str,
    mutation: str,
) -> None:
    source = (
        f"{setup}\n"
        "app = resolve_app()\n"
        f"{mutation}\n"
        "app = object()\n"
        'app.get("/api/v1/object-mutation-path")(handler)\n'
    )

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/object-mutation-path"
    ]


def test_legacy_growth_guard_propagates_module_object_deletion_from_called_helper() -> None:
    source = textwrap.dedent("""
        globals()["object"] = lambda: app

        def restore():
            del globals()["object"]

        restore()
        app = resolve_app()
        app = object()
        app.get("/api/v1/not-a-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_keeps_shadowed_object_call_fail_closed() -> None:
    source = textwrap.dedent("""
        app = resolve_app()
        object = resolve_constructor()
        app = object()
        app.get("/api/v1/shadowed-object")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: " "registration:get:/api/v1/shadowed-object"
    ]


@pytest.mark.parametrize(
    "delete_statement",
    ["del object", "del (object, other)", "del [object, other]"],
    ids=["direct", "tuple", "list"],
)
def test_legacy_growth_guard_restores_builtin_object_after_module_delete(
    delete_statement: str,
) -> None:
    source = (
        "object = safe_constructor\n"
        "other = safe_value\n"
        f"{delete_statement}\n"
        "app = resolve_app()\n"
        "app = object()\n"
        'app.get("/api/v1/not-a-route")(handler)\n'
    )

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_keeps_deleted_function_local_object_fail_closed() -> None:
    source = textwrap.dedent("""
        def install(app, object):
            del object
            app = object()
            app.get("/api/v1/deleted-local-object")(handler)

        install(app, safe_constructor)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/deleted-local-object"
    ]


def test_legacy_growth_guard_does_not_promote_unrelated_unknown_binding() -> None:
    source = textwrap.dedent("""
        candidate = resolve_candidate()
        candidate.get("/api/v1/not-a-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_rejects_dynamic_router_rebinding() -> None:
    source = textwrap.dedent("""
        router = app.router
        router = resolve_router()
        getattr(router, "get")("/api/v1/dynamic-router-getattr")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:router.get:/api/v1/dynamic-router-getattr"
    ]


@pytest.mark.parametrize(
    ("path", "owner"),
    [
        ("/api/v1/premium/plate", "api_premium_plate"),
        ("/api/v1/premium/bmr", "api_premium_bmr"),
        ("/premium_bmr", "premium_bmr_legacy"),
        ("/api/v1/premium/targets", "api_who_targets"),
        ("/premium_targets", "premium_targets_legacy"),
        ("/api/v1/premium/gaps", "api_nutrient_gaps"),
        ("/api/v1/premium/plan/week", "api_weekly_menu"),
    ],
)
def test_legacy_growth_guard_rejects_reintroduced_premium_routes(
    path: str,
    owner: str,
) -> None:
    source = textwrap.dedent(f"""
        @app.post("{path}")
        async def {owner}():
            return {{"ok": True}}
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        f"legacy_app.py: unexpected legacy route growth: decorator:post:{path} -> {owner}"
    ]


def test_legacy_growth_guard_rejects_reintroduced_legal_routes() -> None:
    source = textwrap.dedent("""
        @app.get("/privacy")
        async def privacy():
            return {"privacy_policy": "legacy"}

        @app.get("/terms", include_in_schema=False)
        async def terms():
            return {"terms_of_use": "legacy"}
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: decorator:get:/privacy -> privacy",
        "legacy_app.py: unexpected legacy route growth: decorator:get:/terms -> terms",
    ]


def test_legacy_growth_guard_rejects_reintroduced_health_routes() -> None:
    source = textwrap.dedent("""
        @app.get("/health")
        async def health():
            return {"status": "legacy"}

        @app.get("/api/v1/health", include_in_schema=False)
        async def health_v1():
            return await health()

        @app.get("/health/db", include_in_schema=False)
        async def database_health():
            return {"status": "ok"}

        @app.get("/ready", include_in_schema=False)
        async def ready():
            return {"status": "ok"}
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: decorator:get:/api/v1/health -> health_v1",
        "legacy_app.py: unexpected legacy route growth: decorator:get:/health -> health",
        "legacy_app.py: unexpected legacy route growth: "
        "decorator:get:/health/db -> database_health",
        "legacy_app.py: unexpected legacy route growth: decorator:get:/ready -> ready",
    ]


def test_legacy_growth_guard_rejects_reintroduced_favicon_route() -> None:
    source = textwrap.dedent("""
        @app.get("/favicon.ico")
        async def favicon():
            return Response(status_code=204)
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: decorator:get:/favicon.ico -> favicon"
    ]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            textwrap.dedent("""
                @app.post("/bmi")
                async def bmi_endpoint():
                    return {"ok": True}
                """),
            "legacy_app.py: unexpected legacy route growth: decorator:post:/bmi -> bmi_endpoint",
        ),
        (
            textwrap.dedent("""
                @app.post("/plan")
                async def plan_endpoint():
                    return {"ok": True}
                """),
            "legacy_app.py: unexpected legacy route growth: decorator:post:/plan -> plan_endpoint",
        ),
        (
            textwrap.dedent("""
                @app.post("/api/v1/bmi")
                async def bmi_endpoint_v1():
                    return {"ok": True}
                """),
            (
                "legacy_app.py: unexpected legacy route growth: "
                "decorator:post:/api/v1/bmi -> bmi_endpoint_v1"
            ),
        ),
    ],
)
def test_legacy_growth_guard_rejects_reintroduced_bmi_plan_routes(
    source: str,
    expected: str,
) -> None:
    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [expected]


def test_legacy_growth_guard_rejects_reintroduced_bmi_router_registration() -> None:
    source = textwrap.dedent("""
        from app.routers.bmi import router as bmi_router
        from app.routers.bmi_pro import router as bmi_pro_router
        from app.routers.bmi_pro_legacy_alias import router as bmi_pro_legacy_alias_router

        app.include_router(bmi_router)
        app.include_router(bmi_pro_router)
        app.include_router(bmi_pro_legacy_alias_router)
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:include_router:bmi_pro_legacy_alias_router",
        "legacy_app.py: unexpected legacy route growth: registration:include_router:bmi_pro_router",
        "legacy_app.py: unexpected legacy route growth: registration:include_router:bmi_router",
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:app.routers.bmi:router -> bmi_router",
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:app.routers.bmi_pro:router -> bmi_pro_router",
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:app.routers.bmi_pro_legacy_alias:router -> "
        "bmi_pro_legacy_alias_router",
    ]


def test_legacy_growth_guard_rejects_reintroduced_export_alias_routes() -> None:
    source = textwrap.dedent("""
        @app.get("/api/v1/premium/exports/day/{plan_id}.csv")
        async def export_daily_plan_csv_route():
            return Response()

        @app.post("/api/v1/export/pdf")
        async def export_pdf_generic_route():
            return Response()

        @app.get("/api/v1/premium/exports/week/{plan_id}.csv")
        async def export_weekly_plan_csv_route():
            return Response()

        @app.get("/api/v1/premium/exports/day/{plan_id}.pdf")
        async def export_daily_plan_pdf_route():
            return Response()

        @app.get("/api/v1/premium/exports/week/{plan_id}.pdf")
        async def export_weekly_plan_pdf_route():
            return Response()
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "decorator:get:/api/v1/premium/exports/day/{plan_id}.csv -> "
        "export_daily_plan_csv_route",
        "legacy_app.py: unexpected legacy route growth: "
        "decorator:get:/api/v1/premium/exports/day/{plan_id}.pdf -> "
        "export_daily_plan_pdf_route",
        "legacy_app.py: unexpected legacy route growth: "
        "decorator:get:/api/v1/premium/exports/week/{plan_id}.csv -> "
        "export_weekly_plan_csv_route",
        "legacy_app.py: unexpected legacy route growth: "
        "decorator:get:/api/v1/premium/exports/week/{plan_id}.pdf -> "
        "export_weekly_plan_pdf_route",
        "legacy_app.py: unexpected legacy route growth: "
        "decorator:post:/api/v1/export/pdf -> export_pdf_generic_route",
    ]


def test_legacy_growth_guard_rejects_reintroduced_admin_debug_routes() -> None:
    source = textwrap.dedent("""
        @app.get("/debug_env")
        async def debug_env():
            return {"ok": True}

        @app.get("/api/v1/admin/status")
        async def admin_status():
            return {"ok": True}

        @app.post("/admin/logs/cleanup")
        async def cleanup_expired_logs():
            return {"ok": True}

        @app.get("/api/v1/admin/db-status")
        async def get_database_status():
            return {"ok": True}

        @app.post("/api/v1/admin/force-update")
        async def force_database_update():
            return {"ok": True}

        @app.get("/api/v1/admin/check-updates")
        async def check_for_updates():
            return {"ok": True}

        @app.post("/api/v1/admin/rollback")
        async def rollback_database():
            return {"ok": True}
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "decorator:get:/api/v1/admin/check-updates -> check_for_updates",
        "legacy_app.py: unexpected legacy route growth: "
        "decorator:get:/api/v1/admin/db-status -> get_database_status",
        "legacy_app.py: unexpected legacy route growth: "
        "decorator:get:/api/v1/admin/status -> admin_status",
        "legacy_app.py: unexpected legacy route growth: decorator:get:/debug_env -> debug_env",
        "legacy_app.py: unexpected legacy route growth: "
        "decorator:post:/admin/logs/cleanup -> cleanup_expired_logs",
        "legacy_app.py: unexpected legacy route growth: "
        "decorator:post:/api/v1/admin/force-update -> force_database_update",
        "legacy_app.py: unexpected legacy route growth: "
        "decorator:post:/api/v1/admin/rollback -> rollback_database",
    ]


def test_legacy_growth_guard_rejects_new_router_registration() -> None:
    source = "app.include_router(new_router)\n"

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: registration:include_router:new_router"
    ]


def test_legacy_growth_guard_rejects_add_api_route_registration() -> None:
    source = 'app.add_api_route("/api/v1/new-runtime", new_runtime_route)\n'

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:add_api_route:/api/v1/new-runtime"
    ]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            'app.add_route("/api/v1/new-runtime", new_runtime_route)\n',
            "legacy_app.py: unexpected legacy route growth: "
            "registration:add_route:/api/v1/new-runtime",
        ),
        (
            'app.router.add_api_route("/api/v1/new-runtime", new_runtime_route)\n',
            "legacy_app.py: unexpected legacy route growth: "
            "registration:router.add_api_route:/api/v1/new-runtime",
        ),
        (
            'app.add_websocket_route("/ws/new-runtime", new_runtime_ws)\n',
            "legacy_app.py: unexpected legacy route growth: "
            "registration:add_websocket_route:/ws/new-runtime",
        ),
    ],
)
def test_legacy_growth_guard_rejects_router_api_registration_aliases(
    source: str,
    expected: str,
) -> None:
    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [expected]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            textwrap.dedent("""
                legacy = app
                legacy.add_api_route("/api/v1/new-runtime", new_runtime_route)
                """),
            "legacy_app.py: unexpected legacy route growth: "
            "registration:add_api_route:/api/v1/new-runtime",
        ),
        (
            textwrap.dedent("""
                legacy = app

                @legacy.post("/api/v1/new-runtime")
                async def new_runtime_route():
                    return {"ok": True}
                """),
            "legacy_app.py: unexpected legacy route growth: "
            "decorator:post:/api/v1/new-runtime -> new_runtime_route",
        ),
        (
            textwrap.dedent("""
                legacy = app
                legacy_router = legacy.router
                legacy_router.add_api_route("/api/v1/new-runtime", new_runtime_route)
                """),
            "legacy_app.py: unexpected legacy route growth: "
            "registration:router.add_api_route:/api/v1/new-runtime",
        ),
    ],
)
def test_legacy_growth_guard_rejects_app_alias_registrations(
    source: str,
    expected: str,
) -> None:
    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [expected]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            textwrap.dedent("""
                @app.route("/api/v1/new-runtime")
                async def new_runtime_route():
                    return {"ok": True}
                """),
            "legacy_app.py: unexpected legacy route growth: "
            "decorator:route:/api/v1/new-runtime -> new_runtime_route",
        ),
        (
            textwrap.dedent("""
                @app.websocket_route("/ws/new-runtime")
                async def new_runtime_ws(websocket):
                    pass
                """),
            "legacy_app.py: unexpected legacy route growth: "
            "decorator:websocket_route:/ws/new-runtime -> new_runtime_ws",
        ),
    ],
)
def test_legacy_growth_guard_rejects_route_decorator_aliases(
    source: str,
    expected: str,
) -> None:
    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [expected]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            'registered = app.add_api_route("/api/v1/new-runtime", new_runtime_route)\n',
            "legacy_app.py: unexpected legacy route growth: "
            "registration:add_api_route:/api/v1/new-runtime",
        ),
        (
            "registered = app.add_middleware(NewRuntimeMiddleware)\n",
            "legacy_app.py: unexpected legacy route growth: "
            "registration:add_middleware:NewRuntimeMiddleware",
        ),
        (
            "registered = app.include_router(new_router)\n",
            "legacy_app.py: unexpected legacy route growth: registration:include_router:new_router",
        ),
    ],
)
def test_legacy_growth_guard_rejects_non_expression_app_registrations(
    source: str,
    expected: str,
) -> None:
    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [expected]


def test_legacy_growth_guard_rejects_add_middleware() -> None:
    source = "app.add_middleware(NewRuntimeMiddleware)\n"

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:add_middleware:NewRuntimeMiddleware"
    ]


def test_legacy_growth_guard_rejects_reassigned_getattr_route_method_as_dynamic() -> None:
    source = textwrap.dedent("""
        method = "get"
        method = "post"
        getattr(app, method)("/api/v1/reassigned")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: " "registration:dynamic:/api/v1/reassigned"
    ]


def test_legacy_growth_guard_clears_route_marker_after_safe_rebinding() -> None:
    source = textwrap.dedent("""
        if enabled:
            method = "get"
        else:
            method = "safe_method"
        method = "safe_method"
        getattr(app, method)("/api/v1/not-a-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_respects_route_method_parameter_shadowing() -> None:
    source = textwrap.dedent("""
        method = "get"

        def register(method):
            getattr(app, method)("/api/v1/shadowed")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: " "registration:dynamic:/api/v1/shadowed"
    ]


def test_legacy_growth_guard_respects_bound_route_callable_parameter_shadowing() -> None:
    source = textwrap.dedent("""
        route = app.get

        def register(route):
            route("/api/v1/shadowed")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_ignores_statically_unreachable_route_call() -> None:
    source = textwrap.dedent("""
        if False:
            app.get("/api/v1/unreachable")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_clears_bound_route_callable_after_safe_rebinding() -> None:
    source = textwrap.dedent("""
        safe_route = None
        route = app.get
        route = safe_route
        route("/api/v1/not-a-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_ignores_dead_fastapi_app_alias() -> None:
    source = textwrap.dedent("""
        from fastapi import FastAPI

        if False:
            alias = FastAPI()
        alias.get("/api/v1/not-a-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_resolves_getattr_alias_for_route_method() -> None:
    source = textwrap.dedent("""
        lookup = getattr
        lookup(app, "get")("/api/v1/getter-alias")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: " "registration:get:/api/v1/getter-alias"
    ]


def test_legacy_growth_guard_respects_shadowed_getattr() -> None:
    source = textwrap.dedent("""
        getattr = safe_getattr
        getattr(app, "get")("/api/v1/not-a-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_preserves_conditional_getattr_alias() -> None:
    source = textwrap.dedent("""
        if enabled:
            lookup = getattr
        else:
            lookup = safe_getattr
        lookup(app, "get")("/api/v1/conditional-getter")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/conditional-getter"
    ]


def test_legacy_growth_guard_rejects_assigned_dynamic_route_method() -> None:
    source = textwrap.dedent("""
        route = getattr(app, resolve_method())
        route("/api/v1/dynamic-assignment")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:dynamic:/api/v1/dynamic-assignment"
    ]


@pytest.mark.parametrize(
    ("assignment", "action"),
    [("alias = app", "get"), ("alias = app.router", "router.get")],
)
def test_legacy_growth_guard_rejects_local_route_aliases(
    assignment: str,
    action: str,
) -> None:
    source = textwrap.dedent(f"""
        def register():
            {assignment}
            alias.get("/api/v1/local-alias")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        f"registration:{action}:/api/v1/local-alias"
    ]


@pytest.mark.parametrize(
    ("legacy_value", "action"),
    [("app", "get"), ("app.router", "router.get")],
)
def test_legacy_growth_guard_rejects_conditional_route_alias(
    legacy_value: str,
    action: str,
) -> None:
    source = textwrap.dedent(f"""
        if enabled:
            alias = {legacy_value}
        else:
            alias = object()
        alias.get("/api/v1/conditional")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        f"registration:{action}:/api/v1/conditional"
    ]


@pytest.mark.parametrize(
    "source",
    [
        textwrap.dedent("""
            for _ in [1]:
                alias = app
                break
                alias = object()
            else:
                alias = object()
            alias.get("/api/v1/loop-else")(handler)
            """),
        textwrap.dedent("""
            while enabled:
                alias = app
                break
                alias = object()
            else:
                alias = object()
            alias.get("/api/v1/loop-else")(handler)
            """),
    ],
    ids=["for-break", "while-break"],
)
def test_legacy_growth_guard_preserves_route_alias_across_loop_break_else(
    source: str,
) -> None:
    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: " "registration:get:/api/v1/loop-else"
    ]


def test_legacy_growth_guard_rejects_middleware_decorator() -> None:
    source = textwrap.dedent("""
        @app.middleware("http")
        async def new_legacy_middleware(request, call_next):
            return await call_next(request)
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "decorator:middleware:http -> new_legacy_middleware"
    ]


@pytest.mark.parametrize(
    "source",
    [
        'app.middleware("http")(new_legacy_middleware)\n',
        'legacy = app\nlegacy.middleware("http")(new_legacy_middleware)\n',
        'middleware = app.middleware\nmiddleware("http")(new_legacy_middleware)\n',
        (
            'middleware = app.middleware\nregister_http = middleware("http")\n'
            "register_http(new_legacy_middleware)\n"
        ),
        'register = getattr(app, "middleware")\nregister("http")(handler)\n',
        ('method = "middleware"\nregister = getattr(app, method)\nregister("http")(handler)\n'),
    ],
)
def test_legacy_growth_guard_rejects_functional_middleware_registration(
    source: str,
) -> None:
    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == ["legacy_app.py: unexpected legacy route growth: registration:middleware:http"]


@pytest.mark.parametrize(
    "use",
    [
        "register_http(handler)",
        "@register_http\nasync def handler(request, call_next):\n    return await call_next(request)",
    ],
    ids=["functional", "decorator"],
)
def test_legacy_growth_guard_clears_middleware_factory_after_safe_rebinding(
    use: str,
) -> None:
    source = (
        "safe_register = None\n"
        'register_http = app.middleware("http")\n'
        "register_http = safe_register\n"
        f"{use}\n"
    )

    assert legacy_guard.validate_legacy_growth(source) == []


@pytest.mark.parametrize(
    ("use", "expected_error"),
    [
        (
            "register_http(handler)",
            "legacy_app.py: unexpected legacy route growth: registration:middleware:http",
        ),
        (
            "@register_http\nasync def handler(request, call_next):\n    return await call_next(request)",
            "legacy_app.py: unexpected legacy route growth: decorator:middleware:http -> handler",
        ),
    ],
    ids=["functional", "decorator"],
)
def test_legacy_growth_guard_rejects_middleware_factory_called_before_safe_rebinding(
    use: str,
    expected_error: str,
) -> None:
    source = (
        "safe_register = None\n"
        "def install():\n"
        f"{textwrap.indent(use, '    ')}\n"
        'register_http = app.middleware("http")\n'
        "install()\n"
        "register_http = safe_register\n"
    )

    assert legacy_guard.validate_legacy_growth(source) == [expected_error]


@pytest.mark.parametrize(
    "use",
    [
        "register_http(handler)",
        "@register_http\nasync def handler(request, call_next):\n    return await call_next(request)",
    ],
    ids=["functional", "decorator"],
)
def test_legacy_growth_guard_respects_middleware_factory_parameter_shadowing(
    use: str,
) -> None:
    source = (
        'register_http = app.middleware("http")\n\n'
        "def register(register_http):\n"
        f"{textwrap.indent(use, '    ')}\n"
    )

    assert legacy_guard.validate_legacy_growth(source) == []


@pytest.mark.parametrize(
    "invocation",
    [
        "install(register_http)",
        "install(registrar=register_http)",
        "install(*(register_http,))",
        'install(**{"registrar": register_http})',
    ],
    ids=["positional", "keyword", "starred", "double-starred"],
)
def test_legacy_growth_guard_replays_helper_with_resolved_arguments(invocation: str) -> None:
    source = textwrap.dedent(f"""
        def install(registrar):
            registrar(handler)

        register_http = app.middleware("http")
        {invocation}
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: registration:middleware:http"
    ]


@pytest.mark.parametrize(
    "invocation",
    [
        'install((route := app.get), route, "/api/v1/named-positional")',
        ("install(first=(route := app.get), registrar=route, " 'path="/api/v1/named-keyword")'),
    ],
    ids=["positional", "keyword"],
)
def test_legacy_growth_guard_resolves_arguments_in_python_evaluation_order(
    invocation: str,
) -> None:
    source = textwrap.dedent(f"""
        def install(first, registrar, path):
            registrar(path)(handler)

        {invocation}
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: registration:dynamic:path"
    ]


@pytest.mark.parametrize(
    ("registrars", "expected"),
    [
        (("app.get", "safe_register"), []),
        (
            ("safe_register", "app.get"),
            ["legacy_app.py: unexpected legacy route growth: " "registration:dynamic:path"],
        ),
    ],
    ids=["safe-last", "dangerous-last"],
)
def test_legacy_growth_guard_uses_last_value_for_duplicate_static_dict_keys(
    registrars: tuple[str, str],
    expected: list[str],
) -> None:
    first, second = registrars
    source = textwrap.dedent(f"""
        def install(registrar, path):
            registrar(path)(handler)

        install(**{{
            "registrar": {first},
            "registrar": {second},
            "path": "/api/v1/duplicate-dict",
        }})
        """)

    assert legacy_guard.validate_legacy_growth(source) == expected


def test_legacy_growth_guard_argument_evaluator_detaches_parent_scope_chain() -> None:
    tree = ast.parse(
        "def install(first, registrar):\n"
        "    registrar('/api/v1/hidden')(handler)\n"
        "install((route := app.get), route)\n"
    )
    function = tree.body[0]
    call_statement = tree.body[1]
    assert isinstance(function, ast.FunctionDef)
    assert isinstance(call_statement, ast.Expr)
    assert isinstance(call_statement.value, ast.Call)

    visitor = legacy_guard._ApiKeyLookupVisitor(
        filename="legacy_app.py",
        errors=[],
        initial_references={"app": "pulseplate.app"},
        preserve_route_method_conflicts=True,
    )
    original_parent = visitor.scope
    visitor.scope = legacy_guard._LexicalBindings(
        parent=original_parent,
        scope_kind="comprehension",
    )
    original_references = dict(original_parent.references)

    visitor._resolve_call_argument_bindings(function, call_statement.value)

    assert original_parent.references == original_references
    assert original_parent.resolve_reference("route") is None


def test_legacy_growth_guard_propagates_global_callable_rebinding() -> None:
    source = textwrap.dedent("""
        def dangerous(registrar):
            registrar("/api/v1/global-rebind")(handler)

        def safe(registrar):
            return registrar

        install = safe

        def replace():
            global install
            install = dangerous

        replace()
        install(app.get)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:dynamic:/api/v1/global-rebind"
    ]


def test_legacy_growth_guard_propagates_safe_global_callable_rebinding() -> None:
    source = textwrap.dedent("""
        def dangerous(registrar):
            registrar("/api/v1/not-a-route")(handler)

        def safe(registrar):
            return registrar

        install = dangerous

        def replace():
            global install
            install = safe

        replace()
        install(app.get)
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_propagates_nested_global_callable_rebinding() -> None:
    source = textwrap.dedent("""
        def dangerous(registrar):
            registrar("/api/v1/nested-global-rebind")(handler)

        def safe(registrar):
            return registrar

        install = safe

        def outer_replace():
            global install

            def inner_replace():
                global install
                install = dangerous

            inner_replace()

        outer_replace()
        install(app.get)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:dynamic:/api/v1/nested-global-rebind"
    ]


def test_legacy_growth_guard_propagates_nested_safe_global_rebinding() -> None:
    source = textwrap.dedent("""
        def dangerous(registrar):
            registrar("/api/v1/not-a-route")(handler)

        def safe(registrar):
            return registrar

        install = dangerous

        def outer_replace():
            global install

            def inner_replace():
                global install
                install = safe

            inner_replace()

        outer_replace()
        install(app.get)
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_sandboxes_dormant_nested_global_rebinding() -> None:
    source = textwrap.dedent("""
        def dangerous(registrar):
            registrar("/api/v1/dormant-global-rebind")(handler)

        def safe(registrar):
            return registrar

        install = safe

        def outer():
            def dormant():
                def inner_replace():
                    global install
                    install = dangerous

                inner_replace()

        outer()
        install(app.get)
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_propagates_nonlocal_callable_rebinding() -> None:
    source = textwrap.dedent("""
        def outer():
            def dangerous(registrar):
                registrar("/api/v1/nonlocal-rebind")(handler)

            def safe(registrar):
                return registrar

            install = safe

            def replace():
                nonlocal install
                install = dangerous

            replace()
            install(app.get)

        outer()
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:dynamic:/api/v1/nonlocal-rebind"
    ]


def test_legacy_growth_guard_propagates_deep_nonlocal_callable_rebinding() -> None:
    source = textwrap.dedent("""
        def outer():
            def dangerous(registrar):
                registrar("/api/v1/deep-nonlocal-rebind")(handler)

            def safe(registrar):
                return registrar

            install = safe

            def middle():
                def replace():
                    nonlocal install
                    install = dangerous

                replace()

            middle()
            install(app.get)

        outer()
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:dynamic:/api/v1/deep-nonlocal-rebind"
    ]


def test_legacy_growth_guard_joins_conditional_global_callable_rebinding() -> None:
    source = textwrap.dedent("""
        def dangerous(registrar):
            registrar("/api/v1/conditional-global-rebind")(handler)

        def safe(registrar):
            return registrar

        install = safe

        def replace(enabled):
            global install
            if enabled:
                install = dangerous

        replace(runtime_flag)
        install(app.get)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:dynamic:/api/v1/conditional-global-rebind"
    ]


@pytest.mark.parametrize(
    ("signature", "invocation"),
    [
        ("registrar, /", "install(register_http)"),
        ("*, registrar", "install(registrar=register_http)"),
        ('registrar=app.middleware("http")', "install()"),
    ],
    ids=["positional-only", "keyword-only", "default"],
)
def test_legacy_growth_guard_replays_helper_parameter_kinds(
    signature: str,
    invocation: str,
) -> None:
    source = textwrap.dedent(f"""
        def install({signature}):
            registrar(handler)

        register_http = app.middleware("http")
        {invocation}
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: registration:middleware:http"
    ]


def test_legacy_growth_guard_freezes_default_binding_at_function_definition() -> None:
    source = textwrap.dedent("""
        register_http = app.middleware("http")

        def install(registrar=register_http):
            registrar(handler)

        register_http = safe_register
        install()
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: registration:middleware:http"
    ]


@pytest.mark.parametrize(
    ("signature", "access", "invocation", "path"),
    [
        (
            "*registrars",
            "registrars[0]",
            "install(app.get)",
            "/api/v1/vararg-route",
        ),
        (
            "**registrars",
            'registrars["route"]',
            "install(route=app.get)",
            "/api/v1/kwarg-route",
        ),
    ],
    ids=["vararg", "kwarg"],
)
def test_legacy_growth_guard_keeps_declared_variadics_fail_closed(
    signature: str,
    access: str,
    invocation: str,
    path: str,
) -> None:
    source = textwrap.dedent(f"""
        def install({signature}):
            {access}("{path}")(handler)

        {invocation}
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: " f"registration:dynamic:{path}"
    ]


@pytest.mark.parametrize(
    ("signature", "access", "invocation"),
    [
        ("*registrars", "registrars[0]", "install(safe_register)"),
        (
            "**registrars",
            'registrars["route"]',
            "install(route=safe_register)",
        ),
    ],
    ids=["vararg", "kwarg"],
)
def test_legacy_growth_guard_clears_safe_declared_variadics(
    signature: str,
    access: str,
    invocation: str,
) -> None:
    source = textwrap.dedent(f"""
        def install({signature}):
            {access}("/api/v1/not-a-route")(handler)

        {invocation}
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_respects_safe_argument_shadowing() -> None:
    source = textwrap.dedent("""
        registrar = app.middleware("http")

        def install(registrar):
            registrar(handler)

        install(safe_register)
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_keeps_unresolved_starred_arguments_fail_closed() -> None:
    source = textwrap.dedent("""
        def install(registrar):
            registrar("/api/v1/dynamic-star")(handler)

        install(*resolve_arguments())
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:dynamic:/api/v1/dynamic-star"
    ]


def test_legacy_growth_guard_replays_exact_nested_same_name_function() -> None:
    source = textwrap.dedent("""
        def install(registrar):
            registrar(handler)

        def outer():
            def install(registrar):
                return registrar

            install(app.middleware("http"))

        outer()
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_preserves_aliased_function_identity_after_rebinding() -> None:
    source = textwrap.dedent("""
        def install(registrar):
            registrar(handler)

        original_install = install

        def install(registrar):
            return registrar

        install(app.middleware("http"))
        original_install(app.middleware("http"))
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: registration:middleware:http"
    ]


def test_legacy_growth_guard_keeps_dangerous_callable_across_branch_join() -> None:
    source = textwrap.dedent("""
        def install(registrar):
            registrar(handler)

        if enabled:
            selected = install
        else:
            selected = safe_install

        selected(app.middleware("http"))
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: registration:middleware:http"
    ]


def test_legacy_growth_guard_clears_helper_after_safe_rebinding() -> None:
    source = textwrap.dedent("""
        def install(registrar):
            registrar(handler)

        install = safe_install
        install(app.middleware("http"))
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_stops_recursive_function_replay_by_identity() -> None:
    source = textwrap.dedent("""
        def install(registrar):
            registrar(handler)
            install(registrar)

        install(app.middleware("http"))
        """)

    first = legacy_guard.validate_legacy_growth(source)
    second = legacy_guard.validate_legacy_growth(source)

    assert first == ["legacy_app.py: unexpected legacy route growth: registration:middleware:http"]
    assert second == first


def test_legacy_growth_guard_stops_mutual_recursion_by_function_identity() -> None:
    source = textwrap.dedent("""
        def first(registrar):
            second(registrar)

        def second(registrar):
            registrar(handler)
            first(registrar)

        first(app.middleware("http"))
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: registration:middleware:http"
    ]


def test_legacy_growth_guard_does_not_replay_plain_async_call() -> None:
    source = textwrap.dedent("""
        safe_register = None
        register_http = safe_register

        async def install():
            register_http(handler)

        register_http = app.middleware("http")
        install()
        register_http = safe_register
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_replays_asyncio_run_call_chain() -> None:
    source = textwrap.dedent("""
        import asyncio

        async def install(registrar):
            registrar(handler)

        async def start():
            await install(app.middleware("http"))

        asyncio.run(start())
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: registration:middleware:http"
    ]


def test_legacy_growth_guard_does_not_replay_await_in_uncalled_helper() -> None:
    source = textwrap.dedent("""
        async def install(registrar):
            registrar(handler)

        async def start():
            await install(app.middleware("http"))
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_skips_invalid_excess_argument_call() -> None:
    source = textwrap.dedent("""
        def install(registrar):
            registrar(handler)

        install(app.middleware("http"), unexpected)
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_does_not_replay_uniterated_generator_helper() -> None:
    source = textwrap.dedent("""
        def install(registrar):
            yield registrar(handler)

        install(app.middleware("http"))
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_replays_iterated_generator_helper() -> None:
    source = textwrap.dedent("""
        def install(registrar):
            yield registrar(handler)

        for item in install(app.middleware("http")):
            pass
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: registration:middleware:http"
    ]


def test_legacy_growth_guard_defers_unconsumed_generator_expression_body() -> None:
    source = textwrap.dedent("""
        def install(registrar):
            registrar(handler)

        pending = (install(app.middleware("http")) for item in ())
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


@pytest.mark.parametrize(
    "source",
    [
        "def install(registrar):\n"
        "    registrar(handler)\n"
        'list(install(app.middleware("http")) for _ in [1])\n',
        "def install(registrar):\n"
        "    yield registrar(handler)\n"
        '[item for item in install(app.middleware("http"))]\n',
        "def install(registrar):\n"
        "    yield registrar(handler)\n"
        "def outer(registrar):\n"
        "    yield from install(registrar)\n"
        'list(outer(app.middleware("http")))\n',
    ],
    ids=["consumed-generator-expression", "list-comprehension", "yield-from"],
)
def test_legacy_growth_guard_replays_executed_generator_paths(source: str) -> None:
    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: registration:middleware:http"
    ]


@pytest.mark.parametrize(
    "source",
    [
        "def install(registrar):\n"
        "    yield registrar(handler)\n"
        'pending = install(app.middleware("http"))\n'
        "list(pending)\n",
        "def install(registrar):\n"
        "    registrar(handler)\n"
        'pending = (install(app.middleware("http")) for _ in [1])\n'
        "list(pending)\n",
        "def install(registrar):\n"
        "    registrar(handler)\n"
        "def consume(items):\n"
        "    for item in items:\n"
        "        pass\n"
        'consume(install(app.middleware("http")) for _ in [1])\n',
    ],
    ids=["generator-alias", "generator-expression-alias", "generator-argument"],
)
def test_legacy_growth_guard_replays_aliased_generator_values(source: str) -> None:
    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: registration:middleware:http"
    ]


@pytest.mark.parametrize(
    "source",
    [
        "def install(registrar):\n"
        "    registrar(handler)\n"
        'list(install(app.middleware("http")) for _ in ())\n',
        "def install(registrar):\n"
        "    registrar(handler)\n"
        'list(install(app.middleware("http")) for _ in [1] if False)\n',
        'pending = ((registrar := app.middleware("http")) for _ in ())\n' "registrar(handler)\n",
    ],
    ids=["empty-iterable", "false-filter", "unconsumed-named-expression"],
)
def test_legacy_growth_guard_skips_unreachable_generator_bodies(source: str) -> None:
    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_freezes_generator_expression_outer_iterator() -> None:
    source = textwrap.dedent("""
        registrars = [app.middleware("http")]
        pending = (registrar(handler) for registrar in registrars)
        registrars = [safe_register]
        list(pending)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: registration:middleware:http"
    ]


def test_legacy_growth_guard_does_not_reevaluate_generator_outer_iterable() -> None:
    source = textwrap.dedent("""
        safe_register = None
        registrar = safe_register

        def make_items():
            global registrar
            registrar = app.middleware("http")
            return [1]

        pending = (registrar(handler) for _ in make_items())
        registrar = safe_register
        list(pending)
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_does_not_replay_exhausted_generator_alias() -> None:
    source = textwrap.dedent("""
        registrar = safe_register
        pending = (registrar(handler) for _ in [1])
        list(pending)
        registrar = app.middleware("http")
        list(pending)
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_skips_empty_later_comprehension_iterable() -> None:
    source = textwrap.dedent("""
        def install(registrar):
            registrar(handler)

        list(
            install(app.middleware("http"))
            for _ in [1]
            for ignored in ()
        )
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_skips_postponed_annotation_calls() -> None:
    source = textwrap.dedent("""
        from __future__ import annotations

        def install(registrar):
            registrar(handler)

        def endpoint(argument: install(app.middleware("http"))):
            pass
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_honors_decorator_replacement_before_replay() -> None:
    source = textwrap.dedent("""
        def safe_install(registrar):
            return registrar

        def wrap(function):
            return safe_install

        @wrap
        def install(registrar):
            registrar(handler)

        install(app.middleware("http"))
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_replays_identity_decorated_helper() -> None:
    source = textwrap.dedent("""
        def wrap(function):
            return function

        @wrap
        def install(registrar):
            registrar(handler)

        install(app.middleware("http"))
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: registration:middleware:http"
    ]


def test_legacy_growth_guard_does_not_retain_async_decorator_target() -> None:
    source = textwrap.dedent("""
        async def wrap(function):
            return safe_install

        @wrap
        def install(registrar):
            registrar(handler)

        install(app.middleware("http"))
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_snapshots_decorator_before_defaults() -> None:
    source = textwrap.dedent("""
        def identity(function):
            return function

        def replace(function):
            return safe_install

        decorator = identity

        @decorator
        def install(registrar, marker=(decorator := replace)):
            registrar(handler)

        install(app.middleware("http"))
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: registration:middleware:http"
    ]


def test_legacy_growth_guard_evaluates_defaults_before_annotations() -> None:
    source = textwrap.dedent("""
        def install(registrar):
            registrar(handler)

        registrar = safe_install

        def endpoint(
            value: install(registrar) = (registrar := app.middleware("http")),
        ):
            pass
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: registration:middleware:http"
    ]


def test_legacy_growth_guard_replays_returned_closure_with_definition_scope() -> None:
    source = textwrap.dedent("""
        def factory(original):
            def wrapped(registrar):
                original(registrar)

            return wrapped

        def install(registrar):
            registrar(handler)

        replacement = factory(install)
        replacement(app.middleware("http"))
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: registration:middleware:http"
    ]


def test_legacy_growth_guard_keeps_multiple_closure_instances_distinct() -> None:
    source = textwrap.dedent("""
        def make(original):
            def wrapped(registrar):
                original(registrar)

            return wrapped

        def install(registrar):
            registrar(handler)

        dangerous = make(install)
        safe = make(safe_install)
        dangerous(app.middleware("http"))
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: registration:middleware:http"
    ]


def test_legacy_growth_guard_captures_arguments_in_evaluation_order() -> None:
    source = textwrap.dedent("""
        def install(registrar, marker):
            registrar(handler)

        registrar = app.middleware("http")
        install(registrar, (registrar := safe_install))
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: registration:middleware:http"
    ]


def test_legacy_growth_guard_tracks_direct_attribute_of_returned_app() -> None:
    source = textwrap.dedent("""
        def build():
            return app

        build().get("/api/v1/returned-app")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:dynamic:/api/v1/returned-app"
    ]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            'class app:\n    app.get("/api/v1/class-body")(handler)\n',
            "registration:get:/api/v1/class-body",
        ),
        (
            "items = [app]\n"
            "for app in items:\n"
            '    app.get("/api/v1/loop-binding")(handler)\n',
            "registration:get:/api/v1/loop-binding",
        ),
        (
            "import contextlib\n"
            "with contextlib.nullcontext(app) as app:\n"
            '    app.get("/api/v1/with-binding")(handler)\n',
            "registration:get:/api/v1/with-binding",
        ),
    ],
    ids=["class-body", "loop-binding", "with-binding"],
)
def test_legacy_growth_guard_preserves_preexisting_app_during_binders(
    source: str,
    expected: str,
) -> None:
    assert legacy_guard.validate_legacy_growth(source) == [
        f"legacy_app.py: unexpected legacy route growth: {expected}"
    ]


@pytest.mark.parametrize(
    "source",
    [
        "items = [app]\n" "for alias in items:\n" '    alias.get("/api/v1/loop-alias")(handler)\n',
        "import contextlib\n"
        "with contextlib.nullcontext(app) as alias:\n"
        '    alias.get("/api/v1/with-alias")(handler)\n',
    ],
    ids=["loop", "with"],
)
def test_legacy_growth_guard_propagates_app_to_new_binder_name(source: str) -> None:
    assert len(legacy_guard.validate_legacy_growth(source)) == 1


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            "def install(registrar):\n"
            "    registrar(handler)\n"
            "match install:\n"
            "    case alias:\n"
            '        alias(app.middleware("http"))\n',
            "registration:middleware:http",
        ),
        (
            "def install(registrar):\n"
            '    registrar("/api/v1/match-capture")(handler)\n'
            "match install:\n"
            "    case alias:\n"
            "        alias(app.get)\n",
            "registration:dynamic:/api/v1/match-capture",
        ),
        (
            "import contextlib\n"
            "def install(registrar):\n"
            "    registrar(handler)\n"
            "with contextlib.nullcontext(install) as alias:\n"
            '    alias(app.middleware("http"))\n',
            "registration:middleware:http",
        ),
        (
            "from contextlib import nullcontext\n"
            "def install(registrar):\n"
            '    registrar("/api/v1/with-capture")(handler)\n'
            "with nullcontext(enter_result=install) as alias:\n"
            "    alias(app.get)\n",
            "registration:dynamic:/api/v1/with-capture",
        ),
    ],
    ids=["match-middleware", "match-route", "with-middleware", "with-route-keyword"],
)
def test_legacy_growth_guard_preserves_callable_provenance_across_binders(
    source: str,
    expected: str,
) -> None:
    assert legacy_guard.validate_legacy_growth(source) == [
        f"legacy_app.py: unexpected legacy route growth: {expected}"
    ]


@pytest.mark.parametrize(
    "collection",
    ["[install]", "(install,)", "{install}", "first"],
    ids=["list", "tuple", "set", "nested-alias"],
)
def test_legacy_growth_guard_preserves_named_collection_element_callables(
    collection: str,
) -> None:
    prefix = "first = [install]\n" if collection == "first" else ""
    source = (
        "def install(registrar):\n"
        "    registrar(handler)\n"
        f"{prefix}"
        f"helpers = {collection}\n"
        "for alias in helpers:\n"
        '    alias(app.middleware("http"))\n'
    )

    first = legacy_guard.validate_legacy_growth(source)
    second = legacy_guard.validate_legacy_growth(source)

    assert first == ["legacy_app.py: unexpected legacy route growth: registration:middleware:http"]
    assert second == first


@pytest.mark.parametrize(
    "gather_body",
    [
        'await asyncio.gather(install(app.middleware("http")))',
        'pending = install(app.middleware("http"))\n' "await asyncio.gather(safe(), pending)",
        'pending = [install(app.middleware("http"))]\n' "await asyncio.gather(*pending)",
    ],
    ids=["direct", "named-coroutine", "starred-known-collection"],
)
def test_legacy_growth_guard_replays_awaited_asyncio_gather_arguments(
    gather_body: str,
) -> None:
    source = (
        "import asyncio\n\n"
        "async def install(registrar):\n"
        "    registrar(handler)\n\n"
        "async def safe():\n"
        "    return None\n\n"
        "async def start():\n"
        f"{textwrap.indent(gather_body, '    ')}\n\n"
        "asyncio.run(start())\n"
    )

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: registration:middleware:http"
    ]


@pytest.mark.parametrize(
    ("helper", "execution"),
    [
        (
            "async def install(registrar):\n" "    registrar(handler)\n",
            "async def start():\n"
            '    await asyncio.shield(install(app.middleware("http")))\n'
            "asyncio.run(start())",
        ),
        (
            "def install(registrar):\n" "    registrar(handler)\n",
            'list(map(install, [app.middleware("http")]))',
        ),
        (
            "def install(registrar):\n" "    yield None\n" "    registrar(handler)\n",
            # The guard intentionally treats a consumed generator as fail-closed
            # rather than attempting yield-by-yield control-flow interpretation.
            'next(install(app.middleware("http")))',
        ),
    ],
    ids=["asyncio-shield", "eager-map-callback", "next-fail-closed"],
)
def test_legacy_growth_guard_closes_executor_and_consumer_callback_paths(
    helper: str,
    execution: str,
) -> None:
    source = "import asyncio\n\n" f"{helper}\n" f"{execution}\n"

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: registration:middleware:http"
    ]


@pytest.mark.parametrize(
    ("helper", "binding", "invocation"),
    [
        (
            "def install(registrar):\n" "    registrar(handler)\n",
            'run = partial(install, app.middleware("http"))',
            "run()",
        ),
        (
            "def install(prefix, registrar):\n" "    registrar(handler)\n",
            'run = partial(install, "prefix")',
            'run(app.middleware("http"))',
        ),
    ],
    ids=["fully-bound", "forwarded-argument"],
)
def test_legacy_growth_guard_replays_invoked_partial_helpers(
    helper: str,
    binding: str,
    invocation: str,
) -> None:
    source = "from functools import partial\n\n" f"{helper}\n" f"{binding}\n" f"{invocation}\n"

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: registration:middleware:http"
    ]


def test_legacy_growth_guard_preserves_unresolved_partial_vararg_shape() -> None:
    source = textwrap.dedent("""
        from functools import partial

        def install(*registrars):
            for registrar in registrars:
                registrar("/api/v1/partial-star")(handler)

        seed = [app.get]
        run = partial(install, *seed)
        run()
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:dynamic:/api/v1/partial-star"
    ]


@pytest.mark.parametrize(
    "dispatch",
    [
        'registrars["route"]("/api/v1/partial-kwargs")(handler)',
        ('[(route("/api/v1/partial-kwargs")(handler)) ' "for route in registrars.values()]"),
        ('[(route("/api/v1/partial-kwargs")(handler)) ' "for _name, route in registrars.items()]"),
    ],
    ids=["subscript", "values", "items"],
)
def test_legacy_growth_guard_preserves_unresolved_partial_kwarg_value_shape(
    dispatch: str,
) -> None:
    source = (
        "from functools import partial\n\n"
        "def install(**registrars):\n"
        f"    {dispatch}\n\n"
        'seed = {"route": app.get}\n'
        "run = partial(install, **seed)\n"
        "run()\n"
    )

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:dynamic:/api/v1/partial-kwargs"
    ]


def test_legacy_growth_guard_preserves_items_key_value_shape() -> None:
    source = textwrap.dedent("""
        def inspect(**registrars):
            for name, route in registrars.items():
                name("/api/v1/not-a-route")(handler)
                route("/api/v1/items-value")(handler)

        inspect(route=app.get)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: " "registration:dynamic:/api/v1/items-value"
    ]


def test_legacy_growth_guard_preserves_registrar_values_through_filter() -> None:
    source = textwrap.dedent("""
        routes = {"route": app.get}

        for route in filter(None, routes.values()):
            route("/api/v1/filtered-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: " "registration:get:/api/v1/filtered-route"
    ]


def test_legacy_growth_guard_replays_consumed_filter_predicate() -> None:
    source = textwrap.dedent("""
        routes = {"route": app.get}

        list(
            filter(
                lambda route: route("/api/v1/filter-callback")(handler),
                routes.values(),
            )
        )
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:dynamic:/api/v1/filter-callback"
    ]


def test_legacy_growth_guard_skips_filter_callback_for_proven_empty_input() -> None:
    source = textwrap.dedent("""
        list(
            filter(
                lambda route: route("/api/v1/not-a-route")(handler),
                [],
            )
        )
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


@pytest.mark.parametrize("wrapper_name", ["filter", "map"])
def test_legacy_growth_guard_does_not_replay_shadowed_builtin_callback(
    wrapper_name: str,
) -> None:
    source = textwrap.dedent(f"""
        def {wrapper_name}(callback, iterable):
            return []

        routes = {{"route": app.get}}
        list(
            {wrapper_name}(
                lambda route: route("/api/v1/shadowed-callback")(handler),
                routes.values(),
            )
        )
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_preserves_registrar_values_through_comprehension() -> None:
    source = textwrap.dedent("""
        routes = {"route": app.get}

        for route in [candidate for candidate in routes.values()]:
            route("/api/v1/comprehension-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/comprehension-route"
    ]


def test_legacy_growth_guard_preserves_bound_mapping_lookup_alias() -> None:
    source = textwrap.dedent("""
        routes = {"route": app.get}
        getter = routes.get
        route = getter("route")
        route("/api/v1/bound-lookup-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/bound-lookup-route"
    ]


@pytest.mark.parametrize(
    "dispatch",
    [
        (
            "route = next(iter(registrars.values()))\n"
            '    route("/api/v1/wrapped-mapping-value")(handler)'
        ),
        (
            "for route in list(registrars.values()):\n"
            '        route("/api/v1/wrapped-mapping-value")(handler)'
        ),
    ],
    ids=["next-iter-values", "list-values"],
)
def test_legacy_growth_guard_preserves_mapping_values_through_builtin_wrappers(
    dispatch: str,
) -> None:
    source = "def inspect(**registrars):\n" f"    {dispatch}\n\n" "inspect(route=app.get)\n"

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:dynamic:/api/v1/wrapped-mapping-value"
    ]


@pytest.mark.parametrize(
    "lookup",
    [
        'routes.get("route")',
        'routes.pop("route")',
        'routes.setdefault("route")',
        'routes.__getitem__("route")',
    ],
    ids=["get", "pop", "setdefault", "dunder-getitem"],
)
def test_legacy_growth_guard_preserves_mapping_value_lookup_results(
    lookup: str,
) -> None:
    source = textwrap.dedent(f"""
        def install(**routes):
            route = {lookup}
            route("/api/v1/mapping-lookup-route")(handler)

        install(route=app.get)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:dynamic:/api/v1/mapping-lookup-route"
    ]


@pytest.mark.parametrize("method", ["get", "pop", "setdefault"])
def test_legacy_growth_guard_expands_static_mapping_lookup_arguments(method: str) -> None:
    source = textwrap.dedent(f"""
        def safe(*args, **kwargs):
            return None

        routes = {{"route": app.get}}
        route = routes.{method}(*("route", safe))
        route("/api/v1/static-star-lookup-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/static-star-lookup-route"
    ]


@pytest.mark.parametrize("method", ["get", "pop", "setdefault"])
def test_legacy_growth_guard_keeps_safe_static_mapping_lookup_clean(method: str) -> None:
    source = textwrap.dedent(f"""
        def safe(*args, **kwargs):
            return None

        routes = {{"route": safe}}
        route = routes.{method}(*("route", app.get))
        route("/api/v1/not-a-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_keeps_unresolved_mapping_lookup_star_fail_closed() -> None:
    source = textwrap.dedent("""
        routes = {"route": safe}
        route = routes.get(*resolve_arguments())
        route("/api/v1/unresolved-star-lookup")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:dynamic:/api/v1/unresolved-star-lookup"
    ]


def test_legacy_growth_guard_bounds_nested_static_star_expansion() -> None:
    nested_arguments = '*["route"]'
    for _depth in range(10):
        nested_arguments = f"*({nested_arguments},)"
    source = textwrap.dedent(f"""
        routes = {{"route": safe}}
        route = routes.get({nested_arguments})
        route("/api/v1/deep-star-lookup")(handler)
        """)
    expected = [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:dynamic:/api/v1/deep-star-lookup"
    ]

    assert legacy_guard.validate_legacy_growth(source) == expected
    assert legacy_guard.validate_legacy_growth(source) == expected


def test_legacy_growth_guard_uses_proven_mapping_get_default_for_missing_key() -> None:
    source = textwrap.dedent("""
        routes = {"other": app.get}
        route = routes.get("route", safe)
        route("/api/v1/not-a-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


@pytest.mark.parametrize("pairs", ['[("other", app.get)]', '(("other", app.get),)'])
def test_legacy_growth_guard_preserves_keys_from_dict_pair_iterables(pairs: str) -> None:
    source = textwrap.dedent(f"""
        routes = dict({pairs})
        route = routes.get("route", safe)
        route("/api/v1/not-a-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_preserves_registrar_from_dict_pair_iterable() -> None:
    source = textwrap.dedent("""
        routes = dict([("route", app.get)])
        route = routes.get("route", safe)
        route("/api/v1/pair-iterable-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/pair-iterable-route"
    ]


@pytest.mark.parametrize("keys", ['"abc"', 'b"abc"'])
def test_legacy_growth_guard_expands_literal_dict_fromkeys_iterables(keys: str) -> None:
    source = textwrap.dedent(f"""
        routes = dict.fromkeys({keys}, app.get)
        route = routes.get("route", safe)
        route("/api/v1/not-a-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_preserves_literal_dict_fromkeys_registrar() -> None:
    source = textwrap.dedent("""
        routes = dict.fromkeys("route", app.get)
        route = routes.get("r", safe)
        route("/api/v1/fromkeys-literal-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/fromkeys-literal-route"
    ]


def test_legacy_growth_guard_preserves_variadic_mapping_keys_for_missing_lookup() -> None:
    source = textwrap.dedent("""
        def safe(path):
            return lambda handler: handler

        def install(**routes):
            route = routes.get("route", safe)
            route("/api/v1/not-a-route")(handler)

        install(other=app.get)
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


@pytest.mark.parametrize(
    ("mapping", "lookup"),
    [
        ('{"route": safe}', 'routes.pop("route")'),
        ('{"route": safe}', 'routes.setdefault("route", app.get)'),
        ('{"other": app.get}', 'routes.pop("route", safe)'),
        ('{"other": app.get}', 'routes.setdefault("route", safe)'),
    ],
    ids=[
        "pop-present-safe-value",
        "setdefault-present-safe-value",
        "pop-missing-safe-default",
        "setdefault-missing-safe-default",
    ],
)
def test_legacy_growth_guard_uses_pre_mutation_mapping_lookup_result(
    mapping: str,
    lookup: str,
) -> None:
    source = textwrap.dedent(f"""
        routes = {mapping}
        route = {lookup}
        route("/api/v1/not-a-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


@pytest.mark.parametrize(
    "lookup",
    [
        'routes.get("route", (lambda: safe)())',
        'routes.get("route", choose())',
        'routes.pop("route", (lambda: safe)())',
        'routes.setdefault("route", (lambda: safe)())',
    ],
    ids=["get-lambda", "get-helper", "pop-lambda", "setdefault-lambda"],
)
def test_legacy_growth_guard_replays_safe_mapping_lookup_defaults(lookup: str) -> None:
    source = textwrap.dedent(f"""
        def safe(*args, **kwargs):
            return None

        def choose():
            return safe

        routes = {{}}
        route = {lookup}
        route("/api/v1/not-a-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_invalidates_mapping_during_default_replay() -> None:
    source = textwrap.dedent("""
        def safe(*args, **kwargs):
            return None

        routes = {"route": safe}

        def poison():
            routes["route"] = app.get
            return safe

        route = routes.pop("route", poison())
        route("/api/v1/default-mutated-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:dynamic:/api/v1/default-mutated-route"
    ]


@pytest.mark.parametrize(
    ("initial_route", "replacement_route", "expected"),
    [
        (
            "app.get",
            "safe",
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:get:/api/v1/owner-rebind-route"
            ],
        ),
        ("safe", "app.get", []),
    ],
    ids=["sensitive-owner-rebound-safe", "safe-owner-rebound-sensitive"],
)
@pytest.mark.parametrize("method", ["get", "pop", "setdefault"])
def test_legacy_growth_guard_binds_mapping_owner_before_default_replay(
    method: str,
    initial_route: str,
    replacement_route: str,
    expected: list[str],
) -> None:
    source = textwrap.dedent(f"""
        def safe(*args, **kwargs):
            return None

        routes = {{"route": {initial_route}}}

        def replace():
            global routes
            routes = {{"route": {replacement_route}}}
            return safe

        route = routes.{method}("route", replace())
        route("/api/v1/owner-rebind-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == expected


@pytest.mark.parametrize("method", ["get", "pop", "setdefault"])
@pytest.mark.parametrize(
    "receiver",
    ["make_routes()", '(lambda: {"route": app.get})()'],
    ids=["helper", "lambda"],
)
def test_legacy_growth_guard_evaluates_mapping_receiver_before_arguments(
    method: str,
    receiver: str,
) -> None:
    source = textwrap.dedent(f"""
        def safe(*args, **kwargs):
            return None

        def make_routes():
            return {{"route": app.get}}

        route = {receiver}.{method}("route", safe)
        route("/api/v1/receiver-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: " "registration:get:/api/v1/receiver-route"
    ]


@pytest.mark.parametrize("method", ["get", "pop", "setdefault"])
def test_legacy_growth_guard_preserves_default_for_empty_mapping_receiver(
    method: str,
) -> None:
    source = textwrap.dedent(f"""
        def make_routes():
            return {{}}

        route = make_routes().{method}("route", app.get)
        route("/api/v1/receiver-default-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/receiver-default-route"
    ]


@pytest.mark.parametrize("method", ["get", "pop", "setdefault"])
def test_legacy_growth_guard_ignores_unreachable_receiver_default(method: str) -> None:
    source = textwrap.dedent(f"""
        def safe(*args, **kwargs):
            return None

        def make_routes():
            return {{"route": safe}}

        route = make_routes().{method}("route", app.get)
        route("/api/v1/not-a-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


@pytest.mark.parametrize(
    "dispatch",
    [
        (
            "for _index, route in enumerate(routes.values()):\n"
            '        route("/api/v1/enumerated-route")(handler)'
        ),
        (
            "pairs = list(enumerate(routes.values()))\n"
            "    for _index, route in pairs:\n"
            '        route("/api/v1/enumerated-route")(handler)'
        ),
        (
            "pair = next(iter(enumerate(routes.values())))\n"
            "    _index, route = pair\n"
            '    route("/api/v1/enumerated-route")(handler)'
        ),
        (
            "pair = next(iter(enumerate(routes.values())))\n"
            "    route = pair[1]\n"
            '    route("/api/v1/enumerated-route")(handler)'
        ),
    ],
    ids=["direct", "list-alias", "next-destructure", "next-subscript"],
)
def test_legacy_growth_guard_preserves_enumerated_mapping_value_shape(
    dispatch: str,
) -> None:
    source = "def install(**routes):\n" f"    {dispatch}\n\n" "install(route=app.get)\n"

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:dynamic:/api/v1/enumerated-route"
    ]


def test_legacy_growth_guard_keeps_safe_enumerated_values_non_sensitive() -> None:
    source = textwrap.dedent("""
        for _index, route in list(enumerate([safe])):
            route("/api/v1/not-a-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_expands_static_enumerate_arguments() -> None:
    source = textwrap.dedent("""
        routes = {"route": app.get}
        for _index, route in enumerate(*[routes.values()]):
            route("/api/v1/static-star-enumerate")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/static-star-enumerate"
    ]


def test_legacy_growth_guard_keeps_safe_static_enumerate_clean() -> None:
    source = textwrap.dedent("""
        for _index, route in enumerate(*[[safe]]):
            route("/api/v1/not-a-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_keeps_unresolved_enumerate_star_fail_closed() -> None:
    source = textwrap.dedent("""
        for _index, route in enumerate(*resolve_iterables()):
            route("/api/v1/unresolved-star-enumerate")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:dynamic:/api/v1/unresolved-star-enumerate"
    ]


@pytest.mark.parametrize(
    "dispatch",
    [
        (
            "for _index, route in zip((0,), routes.values()):\n"
            '        route("/api/v1/zipped-route")(handler)'
        ),
        (
            "for route, _index in zip(routes.values(), (0,)):\n"
            '        route("/api/v1/zipped-route")(handler)'
        ),
        (
            "pairs = list(zip((0,), routes.values()))\n"
            "    for _index, route in pairs:\n"
            '        route("/api/v1/zipped-route")(handler)'
        ),
        (
            "pair = next(iter(zip((0,), routes.values())))\n"
            "    route = pair[1]\n"
            '    route("/api/v1/zipped-route")(handler)'
        ),
    ],
    ids=["direct", "reversed", "list-alias", "next-subscript"],
)
def test_legacy_growth_guard_preserves_zipped_mapping_value_shape(
    dispatch: str,
) -> None:
    source = "def install(**routes):\n" f"    {dispatch}\n\n" "install(route=app.get)\n"

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:dynamic:/api/v1/zipped-route"
    ]


def test_legacy_growth_guard_detects_indexed_pair_subscript_callee() -> None:
    source = textwrap.dedent("""
        routes = {"route": app.get}
        for pair in zip(["route"], routes.values()):
            pair[1]("/api/v1/zipped-subscript-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:dynamic:/api/v1/zipped-subscript-route"
    ]


def test_legacy_growth_guard_keeps_safe_zipped_values_non_sensitive() -> None:
    source = textwrap.dedent("""
        for _index, route in list(zip((0,), [safe])):
            route("/api/v1/not-a-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_keeps_unresolved_zip_star_fail_closed() -> None:
    source = textwrap.dedent("""
        for _index, route in zip(*resolve_iterables()):
            route("/api/v1/unresolved-star-zip")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:dynamic:/api/v1/unresolved-star-zip"
    ]


@pytest.mark.parametrize(
    ("selector", "default_arguments"),
    [
        ("max", "default=app.get"),
        ("min", "default=app.get"),
        ("max", '**{"default": app.get}'),
        ("min", '**{"default": app.get}'),
    ],
    ids=["max-explicit", "min-explicit", "max-unpacked", "min-unpacked"],
)
def test_legacy_growth_guard_preserves_builtin_selector_default(
    selector: str,
    default_arguments: str,
) -> None:
    source = textwrap.dedent(f"""
        route = {selector}([], {default_arguments})
        route("/api/v1/selector-default-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/selector-default-route"
    ]


def test_legacy_growth_guard_keeps_unresolved_selector_kwargs_fail_closed() -> None:
    source = textwrap.dedent("""
        route = max([], **resolve_options())
        route("/api/v1/unresolved-selector-default")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:dynamic:/api/v1/unresolved-selector-default"
    ]


@pytest.mark.parametrize(
    "source",
    [
        """
        def safe(*args, **kwargs):
            return None

        def install(registrar=safe):
            registrar("/api/v1/unresolved-star-default")(handler)

        install(*resolve_args())
        """,
        """
        def safe(*args, **kwargs):
            return None

        def install(prefix, registrar=safe):
            registrar("/api/v1/unresolved-star-default")(handler)

        install("prefix", *resolve_args())
        """,
        """
        def safe(*args, **kwargs):
            return None

        def install(*, registrar=safe):
            registrar("/api/v1/unresolved-star-default")(handler)

        install(**resolve_options())
        """,
    ],
    ids=["positional-default", "explicit-prefix", "keyword-only-default"],
)
def test_legacy_growth_guard_joins_unresolved_calls_with_defaults(source: str) -> None:
    expected = [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:dynamic:/api/v1/unresolved-star-default"
    ]

    assert legacy_guard.validate_legacy_growth(textwrap.dedent(source)) == expected


@pytest.mark.parametrize(
    "invocation",
    [
        "install(safe, *resolve_args())",
        "install(registrar=safe, **resolve_options())",
    ],
    ids=["explicit-positional", "explicit-keyword"],
)
def test_legacy_growth_guard_keeps_explicit_registrar_ahead_of_unresolved_values(
    invocation: str,
) -> None:
    source = textwrap.dedent(f"""
        def safe(*args, **kwargs):
            return None

        def install(registrar=safe, *args, **kwargs):
            registrar("/api/v1/not-a-route")(handler)

        {invocation}
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_preserves_variadic_shape_through_tuple_unpacking() -> None:
    source = textwrap.dedent("""
        def install(*routes):
            (route,) = routes
            route("/api/v1/unpacked-variadic-route")(handler)

        install(*[app.get])
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:dynamic:/api/v1/unpacked-variadic-route"
    ]


def test_legacy_growth_guard_preserves_variadic_shape_through_starred_unpacking() -> None:
    source = textwrap.dedent("""
        def install(*routes):
            first, *rest = routes
            for route in rest:
                route("/api/v1/starred-unpacked-variadic-route")(handler)

        install(*[safe, app.get])
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:dynamic:/api/v1/starred-unpacked-variadic-route"
    ]


def test_legacy_growth_guard_keeps_safe_wrapped_and_unpacked_values_non_sensitive() -> None:
    source = textwrap.dedent("""
        def safe(*args, **kwargs):
            return None

        def inspect(*routes, **registrars):
            (route,) = routes
            route("/api/v1/not-a-route")(handler)
            for wrapped in list(registrars.values()):
                wrapped("/api/v1/not-a-route")(handler)
            selected = max([], **{"default": safe})
            selected("/api/v1/not-a-route")(handler)

        inspect(*[safe], route=safe)
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


@pytest.mark.parametrize(
    "invocation",
    [
        "install(*[safe])",
        'install(**{"route": safe})',
    ],
    ids=["known-safe-varargs", "known-safe-kwargs"],
)
def test_legacy_growth_guard_keeps_known_safe_variadic_values_non_sensitive(
    invocation: str,
) -> None:
    source = textwrap.dedent(f"""
        def safe(*args, **kwargs):
            return None

        def install(*registrars, **routes):
            for registrar in registrars:
                registrar(handler)
            for route in routes.values():
                route("/api/v1/not-a-route")(handler)

        {invocation}
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


@pytest.mark.parametrize(
    "execution",
    [
        '    asyncio.gather(install(app.middleware("http")))',
        "    async with asyncio.TaskGroup() as group:\n"
        '        group.create_task(install(app.middleware("http")))',
    ],
    ids=["unawaited-gather", "task-group"],
)
def test_legacy_growth_guard_replays_scheduled_coroutines_in_running_async_flow(
    execution: str,
) -> None:
    source = (
        "import asyncio\n\n"
        "async def install(registrar):\n"
        "    registrar(handler)\n\n"
        "async def start():\n"
        f"{execution}\n\n"
        "asyncio.run(start())\n"
    )

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: registration:middleware:http"
    ]


@pytest.mark.parametrize(
    "source",
    [
        "from functools import partial\n\n"
        "def install(registrar):\n"
        "    registrar(handler)\n\n"
        'run = partial(install, app.middleware("http"))\n',
        "import asyncio\n\n"
        "async def install(registrar):\n"
        "    registrar(handler)\n\n"
        "async def start():\n"
        '    asyncio.gather(install(app.middleware("http")))\n',
        "import asyncio\n\n"
        "async def install(registrar):\n"
        "    registrar(handler)\n\n"
        "async def start():\n"
        "    async with asyncio.TaskGroup() as group:\n"
        "        pass\n"
        '    group.create_task(install(app.middleware("http")))\n\n'
        "asyncio.run(start())\n",
    ],
    ids=[
        "partial-not-invoked",
        "gather-in-uninvoked-coroutine",
        "task-group-after-exit",
    ],
)
def test_legacy_growth_guard_does_not_replay_unexecuted_callback_paths(source: str) -> None:
    assert legacy_guard.validate_legacy_growth(source) == []


@pytest.mark.parametrize(
    "source",
    [
        "import contextlib\n"
        "with contextlib.nullcontext() as alias:\n"
        '    getattr(alias, "get", safe)("/api/v1/safe")(handler)\n',
        "def install(registrar):\n"
        "    registrar(handler)\n"
        "helpers = [install]\n"
        'helpers(app.middleware("http"))\n',
        "def safe(registrar):\n"
        "    pass\n"
        "helpers = [safe]\n"
        "for alias in helpers:\n"
        '    alias(app.middleware("http"))\n',
        "async def install(registrar):\n"
        "    registrar(handler)\n"
        'list(map(install, [app.middleware("http")]))\n',
        "def install(registrar):\n"
        "    yield registrar(handler)\n"
        'list(map(install, [app.middleware("http")]))\n',
    ],
    ids=[
        "nullcontext-default",
        "collection-not-callable",
        "safe-element",
        "map-async-callback-not-awaited",
        "map-generator-result-not-consumed",
    ],
)
def test_legacy_growth_guard_keeps_callable_binder_negative_controls(
    source: str,
) -> None:
    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_applies_local_class_decorator_result() -> None:
    source = textwrap.dedent("""
        def expose(cls):
            return app

        @expose
        class alias:
            pass

        alias.get("/api/v1/decorated-class")(handler)
        """)

    assert len(legacy_guard.validate_legacy_growth(source)) == 1


@pytest.mark.parametrize(
    "source",
    [
        'install = lambda target: target.get("/api/v1/lambda")(handler)\ninstall(app)\n',
        'install = lambda target: target.get("/api/v1/lambda-alias")(handler)\n'
        "alias = install\nalias(app)\n",
    ],
    ids=["direct", "alias"],
)
def test_legacy_growth_guard_replays_invoked_lambda_helpers(source: str) -> None:
    assert len(legacy_guard.validate_legacy_growth(source)) == 1


def test_legacy_growth_guard_seeds_deferred_lambda_defaults() -> None:
    source = "deferred = lambda target=app: " 'target.get("/api/v1/lambda-default")(handler)\n'

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: " "registration:get:/api/v1/lambda-default"
    ]


def test_legacy_growth_guard_replays_helpers_inside_deferred_lambda() -> None:
    source = textwrap.dedent("""
        def install(registrar):
            registrar("/api/v1/lambda-helper")(handler)

        deferred = lambda: install(app.get)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:dynamic:/api/v1/lambda-helper"
    ]


def test_legacy_growth_guard_consumes_generator_expression_returned_by_lambda() -> None:
    source = "deferred = lambda: " '(app.get("/api/v1/lambda-generator")(handler) for _ in [1])\n'

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/lambda-generator"
    ]


def test_legacy_growth_guard_deduplicates_invoked_lambda_definition_finding() -> None:
    source = 'deferred = lambda: app.get("/api/v1/lambda-once")(handler)\n' "deferred()\n"

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: " "registration:get:/api/v1/lambda-once"
    ]


def test_legacy_growth_guard_keeps_safe_deferred_lambda_non_sensitive() -> None:
    source = "deferred = lambda value=object(): value\n"

    assert legacy_guard.validate_legacy_growth(source) == []


@pytest.mark.parametrize(
    "source",
    [
        "class Installer:\n"
        "    @staticmethod\n"
        "    def install(target):\n"
        '        target.get("/api/v1/static-method")(handler)\n'
        "Installer.install(app)\n",
        "class Installer:\n"
        "    @classmethod\n"
        "    def install(cls, target):\n"
        '        target.get("/api/v1/class-method")(handler)\n'
        "Installer.install(app)\n",
        "class Installer:\n"
        "    def install(self, target):\n"
        '        target.get("/api/v1/instance-method")(handler)\n'
        "Installer().install(app)\n",
    ],
    ids=["staticmethod", "classmethod", "instance-method"],
)
def test_legacy_growth_guard_replays_class_method_helpers(source: str) -> None:
    assert len(legacy_guard.validate_legacy_growth(source)) == 1


@pytest.mark.parametrize("consumer", ["sorted", "max", "min", "frozenset"])
def test_legacy_growth_guard_replays_additional_eager_consumers(consumer: str) -> None:
    source = textwrap.dedent(f"""
        def install(registrar):
            yield registrar(handler)

        pending = install(app.middleware("http"))
        {consumer}(pending)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: registration:middleware:http"
    ]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            "def install(registrar):\n"
            "    return registrar\n"
            'install(app.middleware("http"))(handler)\n',
            "registration:middleware:http",
        ),
        (
            "def install():\n"
            "    return app.get\n"
            'install()("/api/v1/returned-route")(handler)\n',
            "registration:get:/api/v1/returned-route",
        ),
    ],
    ids=["middleware", "route"],
)
def test_legacy_growth_guard_tracks_helper_return_bindings(
    source: str,
    expected: str,
) -> None:
    assert legacy_guard.validate_legacy_growth(source) == [
        f"legacy_app.py: unexpected legacy route growth: {expected}"
    ]


@pytest.mark.parametrize(
    "execution",
    ["await pending", "asyncio.create_task(pending)"],
    ids=["await-alias", "create-task-alias"],
)
def test_legacy_growth_guard_replays_executed_coroutine_alias(execution: str) -> None:
    source = textwrap.dedent(f"""
        import asyncio

        async def install(registrar):
            registrar(handler)

        async def start():
            pending = install(app.middleware("http"))
            {execution}

        asyncio.run(start())
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: registration:middleware:http"
    ]


@pytest.mark.parametrize(
    ("returned", "invocation", "expected"),
    [
        (
            "app.get",
            'registrar("/api/v1/awaited-return")(handler)',
            "registration:dynamic:/api/v1/awaited-return",
        ),
        (
            'app.middleware("http")',
            "registrar(handler)",
            "registration:middleware:http",
        ),
    ],
    ids=["route", "middleware"],
)
def test_legacy_growth_guard_tracks_awaited_helper_return_bindings(
    returned: str,
    invocation: str,
    expected: str,
) -> None:
    source = textwrap.dedent(f"""
        import asyncio

        async def build():
            return {returned}

        async def start():
            registrar = await build()
            {invocation}

        asyncio.run(start())
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        f"legacy_app.py: unexpected legacy route growth: {expected}"
    ]


@pytest.mark.parametrize(
    "execution",
    ["pending = await build(registrar); await pending", "await (await build(registrar))"],
    ids=["assigned-double-await", "nested-double-await"],
)
def test_legacy_growth_guard_tracks_coroutine_returned_by_awaited_helper(
    execution: str,
) -> None:
    source = textwrap.dedent(f"""
        import asyncio

        async def install(registrar):
            registrar(handler)

        async def build(registrar):
            return install(registrar)

        async def start():
            registrar = app.middleware("http")
            {execution}

        asyncio.run(start())
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: registration:middleware:http"
    ]


def test_legacy_growth_guard_merges_deferred_branch_outward_effects() -> None:
    source = textwrap.dedent("""
        import asyncio

        install = safe_install

        async def make_dangerous():
            global install

            def register(registrar):
                registrar(handler)

            install = register

        async def make_safe():
            global install
            install = safe_install

        pending = make_dangerous() if enabled else make_safe()
        asyncio.run(pending)
        install(app.middleware("http"))
        """)

    first = legacy_guard.validate_legacy_growth(source)
    second = legacy_guard.validate_legacy_growth(source)

    assert first == ["legacy_app.py: unexpected legacy route growth: registration:middleware:http"]
    assert second == first


@pytest.mark.parametrize(
    ("source", "registrar"),
    [
        (
            "from app.security.rate_limit import wire_rate_limiting\nwire_rate_limiting(app)\n",
            "wire_rate_limiting",
        ),
        (
            "from app.security.rate_limit import wire_rate_limiting as wire\n"
            "alias = wire\nalias(app)\n",
            "wire_rate_limiting",
        ),
        (
            "import app.security.rate_limit as rate_limit\nrate_limit.wire_rate_limiting(app)\n",
            "wire_rate_limiting",
        ),
        (
            "import app.security.rate_limit\napp.security.rate_limit.wire_rate_limiting(app)\n",
            "wire_rate_limiting",
        ),
        (
            "import app.security.rate_limit as rate_limit\n"
            'wire = getattr(rate_limit, "wire_rate_limiting")\nwire(app)\n',
            "wire_rate_limiting",
        ),
        (
            "from app.security import rate_limit\nrate_limit.wire_rate_limiting(app)\n",
            "wire_rate_limiting",
        ),
        (
            "from app.bootstrap import http_stack\n"
            "http_stack.register_http_middleware_stack(app)\n",
            "register_http_middleware_stack",
        ),
        (
            "import app.security.rate_limit as rate_limit\n"
            'registrar_name = "wire_rate_limiting"\n'
            "wire = getattr(rate_limit, registrar_name)\nwire(app)\n",
            "wire_rate_limiting",
        ),
        (
            "import app.security.rate_limit as rate_limit\n"
            'wire = getattr(rate_limit, "wire_" + "rate_limiting")\nwire(app)\n',
            "wire_rate_limiting",
        ),
        (
            "import app.security.rate_limit as rate_limit\n"
            'suffix = "rate_limiting"\n'
            'wire = getattr(rate_limit, f"wire_{suffix}")\nwire(app)\n',
            "wire_rate_limiting",
        ),
        (
            "from importlib import import_module as load\n"
            'module = load("app.security.rate_limit")\n'
            "module.wire_rate_limiting(app)\n",
            "wire_rate_limiting",
        ),
        (
            "from importlib import import_module\n"
            'module_name = "app.bootstrap.http_stack"\n'
            'registrar_name = "register_http_middleware_stack"\n'
            "getattr(import_module(module_name), registrar_name)(app)\n",
            "register_http_middleware_stack",
        ),
        (
            "import importlib\n"
            'importlib.import_module(".http_stack", "app.bootstrap")'
            ".register_http_middleware_stack(app)\n",
            "register_http_middleware_stack",
        ),
        (
            "from importlib import import_module\n"
            'module_name = ".rate_limit"\n'
            'package_name = "app.security"\n'
            "getattr(\n"
            "    import_module(name=module_name, package=package_name),\n"
            '    "wire_rate_limiting",\n'
            ")(app)\n",
            "wire_rate_limiting",
        ),
        (
            "from app.bootstrap.http_stack import register_http_middleware_stack\n"
            "register_http_middleware_stack(app)\n",
            "register_http_middleware_stack",
        ),
    ],
)
def test_legacy_growth_guard_rejects_runtime_middleware_registrars(
    source: str,
    registrar: str,
) -> None:
    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: forbidden legacy runtime registration: "
        f"runtime_registration:{registrar}:app"
    ]


@pytest.mark.parametrize(
    ("source", "registrar"),
    [
        (
            "from app.security.rate_limit import *\n",
            "wire_rate_limiting",
        ),
        (
            "from app.bootstrap.http_stack import *\n",
            "register_http_middleware_stack",
        ),
    ],
)
def test_legacy_growth_guard_rejects_forbidden_runtime_registrar_star_imports(
    source: str,
    registrar: str,
) -> None:
    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: forbidden legacy runtime registration: "
        f"runtime_registration:{registrar}:star_import"
    ]


def test_legacy_growth_guard_keeps_module_string_binding_with_shadowed_parameter() -> None:
    source = (
        "from importlib import import_module\n"
        'module_name = "app.bootstrap.http_stack"\n'
        'registrar_name = "register_http_middleware_stack"\n'
        "def harmless(registrar_name):\n"
        "    return registrar_name\n"
        "getattr(import_module(module_name), registrar_name)(app)\n"
    )

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: forbidden legacy runtime registration: "
        "runtime_registration:register_http_middleware_stack:app"
    ]


def test_legacy_growth_guard_rejects_aliased_add_middleware() -> None:
    source = "add = app.add_middleware\nregister = add\nregister(NewMiddleware)\n"

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: registration:add_middleware:NewMiddleware"
    ]


def test_legacy_growth_guard_rejects_getattr_add_middleware() -> None:
    source = 'register = getattr(app, "add_middleware")\nregister(NewMiddleware)\n'

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: registration:add_middleware:NewMiddleware"
    ]


def test_legacy_growth_guard_rejects_new_router_import() -> None:
    source = "from app.routers.new_surface import router as new_router\n"

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:app.routers.new_surface:router -> new_router"
    ]


def test_legacy_growth_guard_rejects_legal_router_import() -> None:
    source = "from app.routers.legal import build_terms_endpoint_payload\n"

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:app.routers.legal:build_terms_endpoint_payload"
    ]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            textwrap.dedent("""
                from app.routers.pro_registration import register_pro_routes as _register_pro_routes

                pro_router, premium_week_router = _register_pro_routes(app)
                """),
            "legacy_app.py: unexpected app.routers import growth: "
            "router_import:app.routers.pro_registration:register_pro_routes -> "
            "_register_pro_routes",
        ),
        (
            textwrap.dedent("""
                from app.routers.vip_registration import register_vip_routes

                register_vip_routes(app)
                """),
            "legacy_app.py: unexpected app.routers import growth: "
            "router_import:app.routers.vip_registration:register_vip_routes",
        ),
    ],
)
def test_legacy_growth_guard_rejects_reintroduced_paid_tier_registration_imports(
    source: str,
    expected: str,
) -> None:
    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [expected]


def test_legacy_growth_guard_rejects_reintroduced_plan_export_router_registration() -> None:
    source = textwrap.dedent("""
        from app.routers.plan_export import export_router, plan_router

        app.include_router(export_router, dependencies=[protected_dependency])
        app.include_router(plan_router, dependencies=[protected_dependency])
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: registration:include_router:export_router",
        "legacy_app.py: unexpected legacy route growth: registration:include_router:plan_router",
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:app.routers.plan_export:export_router",
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:app.routers.plan_export:plan_router",
    ]


def test_legacy_growth_guard_rejects_reintroduced_aliased_plan_export_registration() -> None:
    source = textwrap.dedent("""
        from app.routers.plan_export import export_router as canonical_export_router
        from app.routers.plan_export import plan_router as canonical_plan_router

        app.include_router(canonical_export_router, dependencies=[protected_dependency])
        app.include_router(canonical_plan_router, dependencies=[protected_dependency])
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:include_router:canonical_export_router",
        "legacy_app.py: unexpected legacy route growth: "
        "registration:include_router:canonical_plan_router",
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:app.routers.plan_export:export_router -> canonical_export_router",
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:app.routers.plan_export:plan_router -> canonical_plan_router",
    ]


def test_legacy_growth_guard_rejects_reintroduced_shoplist_export_registration() -> None:
    source = textwrap.dedent("""
        from app.routers.shoplist_export import router as shoplist_router

        app.include_router(shoplist_router, dependencies=[protected_dependency])
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:include_router:shoplist_router",
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:app.routers.shoplist_export:router -> shoplist_router",
    ]


def test_legacy_growth_guard_rejects_reintroduced_aliased_shoplist_export_registration() -> None:
    source = textwrap.dedent("""
        from app.routers.shoplist_export import router as canonical_shoplist_router

        app.include_router(canonical_shoplist_router, dependencies=[protected_dependency])
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:include_router:canonical_shoplist_router",
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:app.routers.shoplist_export:router -> canonical_shoplist_router",
    ]


def test_legacy_growth_guard_rejects_reintroduced_bodyfat_factory_registration() -> None:
    source = textwrap.dedent("""
        from app.routers.bodyfat import get_router as get_bodyfat_router

        app.include_router(get_bodyfat_router(), prefix="/api/v1")
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:include_router:get_bodyfat_router()",
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:app.routers.bodyfat:get_router -> get_bodyfat_router",
    ]


def test_legacy_growth_guard_rejects_direct_bodyfat_router_registration() -> None:
    source = textwrap.dedent("""
        from app.routers.bodyfat import router

        app.include_router(router)
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: registration:include_router:router",
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:app.routers.bodyfat:router",
    ]


def test_legacy_growth_guard_rejects_aliased_bodyfat_router_registration() -> None:
    source = textwrap.dedent("""
        from app.routers.bodyfat import router as canonical_bodyfat_router

        app.include_router(canonical_bodyfat_router)
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:include_router:canonical_bodyfat_router",
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:app.routers.bodyfat:router -> canonical_bodyfat_router",
    ]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            textwrap.dedent("""
                from app.routers.business import router as business_router

                app.include_router(business_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:business_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:app.routers.business:router -> business_router",
            ],
        ),
        (
            textwrap.dedent("""
                from app.routers.business import router as canonical_business_router

                app.include_router(canonical_business_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:canonical_business_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:app.routers.business:router -> canonical_business_router",
            ],
        ),
        (
            textwrap.dedent("""
                import app.routers.business as business_routes

                app.include_router(business_routes.router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:business_routes.router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:import:app.routers.business -> business_routes",
            ],
        ),
        (
            textwrap.dedent("""
                import importlib

                business_router = importlib.import_module("app.routers.business").router
                app.include_router(business_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:business_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.business -> business_router",
            ],
        ),
        (
            textwrap.dedent("""
                import importlib

                if (business_router := importlib.import_module("app.routers.business").router):
                    app.include_router(business_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:business_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.business -> business_router",
            ],
        ),
    ],
)
def test_legacy_growth_guard_rejects_business_router_reintroduction(
    source: str,
    expected: list[str],
) -> None:
    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            textwrap.dedent("""
                from app.routers import bayes_adherence

                app.include_router(bayes_adherence.router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:bayes_adherence.router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:app.routers:bayes_adherence",
            ],
        ),
        (
            textwrap.dedent("""
                from app.routers import nutrition_log as nutrition_routes

                app.include_router(nutrition_routes.router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:nutrition_routes.router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:app.routers:nutrition_log -> nutrition_routes",
            ],
        ),
        (
            textwrap.dedent("""
                from app.routers.legacy_nutrition_alias import (
                    router as legacy_nutrition_alias_router,
                )

                app.include_router(legacy_nutrition_alias_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:legacy_nutrition_alias_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:app.routers.legacy_nutrition_alias:router -> "
                "legacy_nutrition_alias_router",
            ],
        ),
        (
            textwrap.dedent("""
                import app.routers.nutrition_log as nutrition_log_module

                app.include_router(nutrition_log_module.router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:nutrition_log_module.router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:import:app.routers.nutrition_log -> nutrition_log_module",
            ],
        ),
        (
            textwrap.dedent("""
                import importlib

                bayes_router = importlib.import_module("app.routers.bayes_adherence").router
                app.include_router(bayes_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:bayes_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.bayes_adherence -> bayes_router",
            ],
        ),
        (
            textwrap.dedent("""
                import importlib

                nutrition_router, _ = (
                    importlib.import_module("app.routers.nutrition_log").router,
                    None,
                )
                app.include_router(nutrition_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:nutrition_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.nutrition_log -> nutrition_router",
            ],
        ),
        (
            textwrap.dedent("""
                from importlib import import_module

                if (alias_router := import_module("app.routers.legacy_nutrition_alias").router):
                    app.include_router(alias_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:alias_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.legacy_nutrition_alias -> alias_router",
            ],
        ),
    ],
)
def test_legacy_growth_guard_rejects_nutrition_state_router_reintroduction(
    source: str,
    expected: list[str],
) -> None:
    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            textwrap.dedent("""
                from app.routers.shopping_list_pro import router as shopping_list_pro_router

                app.include_router(shopping_list_pro_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:shopping_list_pro_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:app.routers.shopping_list_pro:router -> "
                "shopping_list_pro_router",
            ],
        ),
        (
            textwrap.dedent("""
                from app.routers.shoplist_day import router as shoplist_day_router

                app.include_router(shoplist_day_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:shoplist_day_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:app.routers.shoplist_day:router -> shoplist_day_router",
            ],
        ),
        (
            textwrap.dedent("""
                from app.routers.shopping_list_pro import router as canonical_shopping_router

                app.include_router(canonical_shopping_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:canonical_shopping_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:app.routers.shopping_list_pro:router -> "
                "canonical_shopping_router",
            ],
        ),
        (
            textwrap.dedent("""
                import app.routers.shoplist_day as shoplist_day_module

                app.include_router(shoplist_day_module.router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:shoplist_day_module.router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:import:app.routers.shoplist_day -> shoplist_day_module",
            ],
        ),
        (
            textwrap.dedent("""
                import importlib

                shopping_router = importlib.import_module("app.routers.shopping_list_pro").router
                app.include_router(shopping_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:shopping_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.shopping_list_pro -> shopping_router",
            ],
        ),
        (
            textwrap.dedent("""
                import importlib

                shopping_router, _ = (
                    importlib.import_module("app.routers.shoplist_day").router,
                    None,
                )
                app.include_router(shopping_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:shopping_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.shoplist_day -> shopping_router",
            ],
        ),
        (
            textwrap.dedent("""
                from importlib import import_module

                if (shopping_router := import_module("app.routers.shoplist_day").router):
                    app.include_router(shopping_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:shopping_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.shoplist_day -> shopping_router",
            ],
        ),
    ],
)
def test_legacy_growth_guard_rejects_shopping_list_router_reintroduction(
    source: str,
    expected: list[str],
) -> None:
    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            textwrap.dedent("""
                from app.routers.foods import router as foods_router

                app.include_router(foods_router, include_in_schema=False)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:foods_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:app.routers.foods:router -> foods_router",
            ],
        ),
        (
            textwrap.dedent("""
                from app.routers.catalog import router as catalog_router

                app.include_router(catalog_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:catalog_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:app.routers.catalog:router -> catalog_router",
            ],
        ),
        (
            textwrap.dedent("""
                from app.routers.foods import router as canonical_foods_router

                app.include_router(canonical_foods_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:canonical_foods_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:app.routers.foods:router -> canonical_foods_router",
            ],
        ),
        (
            textwrap.dedent("""
                import app.routers.catalog as catalog_routes

                app.include_router(catalog_routes.router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:catalog_routes.router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:import:app.routers.catalog -> catalog_routes",
            ],
        ),
        (
            textwrap.dedent("""
                import importlib

                food_router = importlib.import_module("app.routers.foods").router
                app.include_router(food_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:food_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.foods -> food_router",
            ],
        ),
        (
            textwrap.dedent("""
                import importlib

                catalog_router, _ = (
                    importlib.import_module("app.routers.catalog").router,
                    None,
                )
                app.include_router(catalog_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:catalog_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.catalog -> catalog_router",
            ],
        ),
        (
            textwrap.dedent("""
                from importlib import import_module

                if (food_router := import_module("app.routers.foods").router):
                    app.include_router(food_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:food_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.foods -> food_router",
            ],
        ),
        (
            textwrap.dedent("""
                import importlib

                wrapper_router = APIRouter()
                wrapper_router.include_router(
                    importlib.import_module("app.routers.catalog").router
                )
                app.include_router(wrapper_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:wrapper_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.catalog -> wrapper_router.include_router",
            ],
        ),
    ],
)
def test_legacy_growth_guard_rejects_food_catalog_router_reintroduction(
    source: str,
    expected: list[str],
) -> None:
    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            textwrap.dedent("""
                from app.routers.users import router

                app.include_router(router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: registration:include_router:router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:app.routers.users:router",
            ],
        ),
        (
            textwrap.dedent("""
                from app.routers.users import router as users_router

                app.include_router(users_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:users_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:app.routers.users:router -> users_router",
            ],
        ),
        (
            textwrap.dedent("""
                import app.routers.users as users_routes

                app.include_router(users_routes.router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:users_routes.router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:import:app.routers.users -> users_routes",
            ],
        ),
        (
            textwrap.dedent("""
                import importlib

                module_name = "app.routers." + "users"
                users_router = importlib.import_module(module_name).router
                app.include_router(users_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:users_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.users -> users_router",
            ],
        ),
        (
            textwrap.dedent("""
                from importlib import import_module

                if (users_router := import_module("app.routers.users").router):
                    app.include_router(users_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:users_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.users -> users_router",
            ],
        ),
        (
            textwrap.dedent("""
                import importlib

                wrapper_router = APIRouter()
                wrapper_router.include_router(
                    importlib.import_module("app.routers.users").router
                )
                app.include_router(wrapper_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:wrapper_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.users -> wrapper_router.include_router",
            ],
        ),
    ],
)
def test_legacy_growth_guard_rejects_users_router_reintroduction(
    source: str,
    expected: list[str],
) -> None:
    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            textwrap.dedent("""
                from app.routers.restaurants import router

                app.include_router(router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: registration:include_router:router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:app.routers.restaurants:router",
            ],
        ),
        (
            textwrap.dedent("""
                from app.routers.restaurants import router as restaurants_router

                app.include_router(restaurants_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:restaurants_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:app.routers.restaurants:router -> restaurants_router",
            ],
        ),
        (
            textwrap.dedent("""
                import app.routers.restaurants as restaurant_routes

                app.include_router(restaurant_routes.router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:restaurant_routes.router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:import:app.routers.restaurants -> restaurant_routes",
            ],
        ),
        (
            textwrap.dedent("""
                import importlib

                restaurants_router = importlib.import_module("app.routers.restaurants").router
                app.include_router(restaurants_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:restaurants_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.restaurants -> restaurants_router",
            ],
        ),
        (
            textwrap.dedent("""
                import importlib

                module_name = "app.routers." + "restaurants"
                restaurants_router = importlib.import_module(module_name).router
                app.include_router(restaurants_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:restaurants_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.restaurants -> restaurants_router",
            ],
        ),
        (
            textwrap.dedent("""
                import importlib

                restaurants_router, _ = (
                    importlib.import_module("app.routers.restaurants").router,
                    None,
                )
                app.include_router(restaurants_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:restaurants_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.restaurants -> restaurants_router",
            ],
        ),
        (
            textwrap.dedent("""
                from importlib import import_module

                if (restaurants_router := import_module("app.routers.restaurants").router):
                    app.include_router(restaurants_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:restaurants_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.restaurants -> restaurants_router",
            ],
        ),
        (
            textwrap.dedent("""
                import importlib

                wrapper_router = APIRouter()
                wrapper_router.include_router(
                    importlib.import_module("app.routers.restaurants").router
                )
                app.include_router(wrapper_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:wrapper_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.restaurants -> wrapper_router.include_router",
            ],
        ),
    ],
    ids=[
        "direct_import",
        "aliased_import",
        "module_qualified_import",
        "dynamic_literal_import",
        "dynamic_computed_import",
        "destructured_dynamic_import",
        "walrus_dynamic_import",
        "nested_wrapper_dynamic_import",
    ],
)
def test_legacy_growth_guard_rejects_restaurants_router_reintroduction(
    source: str,
    expected: list[str],
) -> None:
    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            textwrap.dedent("""
                from app.routers.recipes import router as recipes_router

                app.include_router(recipes_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:recipes_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:app.routers.recipes:router -> recipes_router",
            ],
        ),
        (
            textwrap.dedent("""
                from app.routers.nutrition_recommendations import (
                    router as nutrition_recommendations_router,
                )

                app.include_router(nutrition_recommendations_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:nutrition_recommendations_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:app.routers.nutrition_recommendations:router -> "
                "nutrition_recommendations_router",
            ],
        ),
        (
            textwrap.dedent("""
                from app.routers.recipes import router as canonical_recipes_router

                app.include_router(canonical_recipes_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:canonical_recipes_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:app.routers.recipes:router -> canonical_recipes_router",
            ],
        ),
        (
            textwrap.dedent("""
                import app.routers.recipes as recipe_routes

                app.include_router(recipe_routes.router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:recipe_routes.router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:import:app.routers.recipes -> recipe_routes",
            ],
        ),
        (
            textwrap.dedent("""
                import importlib

                module_name = "app.routers." + "recipes"
                recipe_router = importlib.import_module(module_name).router
                app.include_router(recipe_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:recipe_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.recipes -> recipe_router",
            ],
        ),
        (
            textwrap.dedent("""
                import importlib

                family = "nutrition_recommendations"
                module_name = f"app.routers.{family}"
                nutrition_router = importlib.import_module(module_name).router
                app.include_router(nutrition_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:nutrition_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.nutrition_recommendations -> "
                "nutrition_router",
            ],
        ),
        (
            textwrap.dedent("""
                import importlib

                nutrition_recommendations_router, _ = (
                    importlib.import_module("app.routers.nutrition_recommendations").router,
                    None,
                )
                app.include_router(nutrition_recommendations_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:nutrition_recommendations_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.nutrition_recommendations -> "
                "nutrition_recommendations_router",
            ],
        ),
        (
            textwrap.dedent("""
                from importlib import import_module

                if (recipes_router := import_module("app.routers.recipes").router):
                    app.include_router(recipes_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:recipes_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.recipes -> recipes_router",
            ],
        ),
        (
            textwrap.dedent("""
                from importlib import import_module

                getattr(app, "include_router")(
                    import_module("app.routers.recipes").router
                )
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:import_module('app.routers.recipes').router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.recipes -> "
                "getattr(app, 'include_router')",
            ],
        ),
        (
            textwrap.dedent("""
                from importlib import import_module

                method = "include_" + "router"
                getattr(app, method)(
                    import_module("app.routers.recipes").router
                )
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:import_module('app.routers.recipes').router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.recipes -> getattr(app, method)",
            ],
        ),
        (
            textwrap.dedent("""
                import importlib

                wrapper_router = APIRouter()
                wrapper_router.include_router(
                    importlib.import_module("app.routers.nutrition_recommendations").router
                )
                app.include_router(wrapper_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:wrapper_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.nutrition_recommendations -> "
                "wrapper_router.include_router",
            ],
        ),
    ],
)
def test_legacy_growth_guard_rejects_recipe_nutrition_reference_router_reintroduction(
    source: str,
    expected: list[str],
) -> None:
    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            textwrap.dedent("""
                import importlib

                module_name = "app.routers." + "foods"
                recipes_router = importlib.import_module(module_name).router
                app.include_router(recipes_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:recipes_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.foods -> recipes_router",
            ],
        ),
        (
            textwrap.dedent("""
                import importlib

                module_name = ".".join(["app", "routers", "catalog"])
                users_router = importlib.import_module(module_name).router
                app.include_router(users_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:users_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.catalog -> users_router",
            ],
        ),
        (
            textwrap.dedent("""
                import importlib

                family = "catalog"
                module_name = f"app.routers.{family}"
                restaurants_router = importlib.import_module(module_name).router
                app.include_router(restaurants_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:restaurants_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.catalog -> restaurants_router",
            ],
        ),
        (
            textwrap.dedent("""
                import importlib
                import os

                family = os.getenv("ROUTER_FAMILY", "foods")
                module_name = f"app.routers.{family}"
                nutrition_recommendations_router = importlib.import_module(module_name).router
                app.include_router(nutrition_recommendations_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:nutrition_recommendations_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:<unresolved app.routers import> -> "
                "nutrition_recommendations_router",
            ],
        ),
        (
            textwrap.dedent("""
                import importlib
                import os

                module_name = os.getenv("LEGACY_ROUTER_MODULE")
                recipes_router = importlib.import_module(module_name).router
                app.include_router(recipes_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:recipes_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:<unresolved dynamic router import> -> recipes_router",
            ],
        ),
        (
            textwrap.dedent("""
                import os
                from importlib import import_module

                module = import_module(os.getenv("LEGACY_ROUTER_MODULE"))
                recipes_router.include_router(module.router)
                app.include_router(recipes_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:recipes_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:<unresolved dynamic router import> -> "
                "recipes_router.include_router",
            ],
        ),
        (
            textwrap.dedent("""
                import os
                from importlib import import_module

                module = import_module(os.getenv("LEGACY_ROUTER_MODULE"))
                router = module.router
                recipes_router.include_router(router)
                app.include_router(recipes_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:recipes_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:<unresolved dynamic router import> -> "
                "recipes_router.include_router",
            ],
        ),
        (
            textwrap.dedent("""
                import importlib

                recipes_router = importlib.import_module(name="app.routers.foods").router
                app.include_router(recipes_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:recipes_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.foods -> recipes_router",
            ],
        ),
    ],
)
def test_legacy_growth_guard_rejects_computed_food_catalog_dynamic_import_alias_bypass(
    source: str,
    expected: list[str],
) -> None:
    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == expected


def test_legacy_growth_guard_allows_unregistered_dynamic_import_without_router_use() -> None:
    source = textwrap.dedent("""
        import os
        from importlib import import_module

        module = import_module(os.getenv("LEGACY_HELPER_MODULE"))
        value = module.VALUE
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_rejects_module_qualified_bodyfat_router_registration() -> None:
    source = textwrap.dedent("""
        import app.routers.bodyfat as bodyfat_routes

        app.include_router(bodyfat_routes.router)
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:include_router:bodyfat_routes.router",
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:import:app.routers.bodyfat -> bodyfat_routes",
    ]


def test_legacy_growth_guard_rejects_dynamic_bodyfat_router_hidden_as_allowed_name() -> None:
    source = textwrap.dedent("""
        import importlib

        business_router = importlib.import_module("app.routers.bodyfat").router
        app.include_router(business_router)
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:include_router:business_router",
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:dynamic:app.routers.bodyfat -> business_router",
    ]


def test_legacy_growth_guard_rejects_dunder_import_bodyfat_router_hidden_as_allowed_name() -> None:
    source = textwrap.dedent("""
        business_router = __import__("app.routers.bodyfat", fromlist=["router"]).router
        app.include_router(business_router)
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:include_router:business_router",
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:dynamic:app.routers.bodyfat -> business_router",
    ]


def test_legacy_growth_guard_rejects_aliased_import_module_bodyfat_router() -> None:
    source = textwrap.dedent("""
        from importlib import import_module as load_router_module

        business_router = load_router_module("app.routers.bodyfat").router
        app.include_router(business_router)
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:include_router:business_router",
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:dynamic:app.routers.bodyfat -> business_router",
    ]


def test_legacy_growth_guard_rejects_aliased_builtin_import_bodyfat_router() -> None:
    source = textwrap.dedent("""
        from builtins import __import__ as load_router_module

        business_router = load_router_module("app.routers.bodyfat", fromlist=["router"]).router
        app.include_router(business_router)
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:include_router:business_router",
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:dynamic:app.routers.bodyfat -> business_router",
    ]


def test_legacy_growth_guard_rejects_simple_import_module_alias_bodyfat_router() -> None:
    source = textwrap.dedent("""
        import importlib

        load_router_module = importlib.import_module
        business_router = load_router_module("app.routers.bodyfat").router
        app.include_router(business_router)
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:include_router:business_router",
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:dynamic:app.routers.bodyfat -> business_router",
    ]


def test_legacy_growth_guard_rejects_simple_dunder_import_alias_bodyfat_router() -> None:
    source = textwrap.dedent("""
        load_router_module = __import__
        business_router = load_router_module("app.routers.bodyfat", fromlist=["router"]).router
        app.include_router(business_router)
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:include_router:business_router",
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:dynamic:app.routers.bodyfat -> business_router",
    ]


def test_legacy_growth_guard_rejects_destructured_dynamic_bodyfat_router() -> None:
    source = textwrap.dedent("""
        import importlib

        business_router, _ = (importlib.import_module("app.routers.bodyfat").router, None)
        app.include_router(business_router)
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:include_router:business_router",
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:dynamic:app.routers.bodyfat -> business_router",
    ]


def test_legacy_growth_guard_rejects_walrus_dynamic_bodyfat_router() -> None:
    source = textwrap.dedent("""
        import importlib

        if (business_router := importlib.import_module("app.routers.bodyfat").router):
            app.include_router(business_router)
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:include_router:business_router",
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:dynamic:app.routers.bodyfat -> business_router",
    ]


def test_legacy_growth_guard_rejects_walrus_import_function_alias_bodyfat_router() -> None:
    source = textwrap.dedent("""
        import importlib

        if (load_router_module := importlib.import_module):
            business_router = load_router_module("app.routers.bodyfat").router
            app.include_router(business_router)
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:include_router:business_router",
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:dynamic:app.routers.bodyfat -> business_router",
    ]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            textwrap.dedent("""
                from app.routers import test as test_router

                app.include_router(test_router.router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:test_router.router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:app.routers:test -> test_router",
            ],
        ),
        (
            textwrap.dedent("""
                from app.routers.test import router as canonical_test_router

                app.include_router(canonical_test_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:canonical_test_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:app.routers.test:router -> canonical_test_router",
            ],
        ),
        (
            textwrap.dedent("""
                import app.routers.test as test_router

                app.include_router(test_router.router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:test_router.router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:import:app.routers.test -> test_router",
            ],
        ),
        (
            textwrap.dedent("""
                import importlib

                test_router = importlib.import_module("app.routers.test")
                app.include_router(test_router.router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:test_router.router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.test -> test_router",
            ],
        ),
        (
            textwrap.dedent("""
                from importlib import import_module

                if (test_router := import_module("app.routers.test")):
                    app.include_router(test_router.router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:test_router.router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.test -> test_router",
            ],
        ),
    ],
)
def test_legacy_growth_guard_rejects_reintroduced_test_router_registration(
    source: str,
    expected: list[str],
) -> None:
    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == expected


def test_legacy_growth_guard_rejects_nested_dynamic_bodyfat_router_registration() -> None:
    source = textwrap.dedent("""
        import importlib

        app.include_router(importlib.import_module("app.routers.bodyfat").router)
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:include_router:importlib.import_module('app.routers.bodyfat').router",
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:dynamic:app.routers.bodyfat -> app.include_router",
    ]


def test_legacy_growth_guard_rejects_nested_dynamic_bodyfat_router_composition() -> None:
    source = textwrap.dedent("""
        from fastapi import APIRouter
        import importlib

        business_router = APIRouter()
        business_router.include_router(importlib.import_module("app.routers.bodyfat").router)
        app.include_router(business_router)
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:include_router:business_router",
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:dynamic:app.routers.bodyfat -> business_router.include_router",
    ]


def test_legacy_growth_guard_rejects_reintroduced_restaurant_moderation_registration() -> None:
    source = textwrap.dedent("""
        from app.routers.restaurants import moderation_router as restaurant_moderation_router

        app.include_router(
            restaurant_moderation_router,
            dependencies=[Depends(_get_api_key_dynamic)],
            include_in_schema=False,
        )
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:include_router:restaurant_moderation_router",
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:app.routers.restaurants:moderation_router -> "
        "restaurant_moderation_router",
        "legacy_app.py: sensitive app surface grew for api_key: 1 > 0",
    ]


def test_legacy_growth_guard_rejects_direct_restaurant_moderation_import() -> None:
    source = textwrap.dedent("""
        from app.routers.restaurants import moderation_router

        app.include_router(moderation_router, dependencies=[Depends(_get_api_key_dynamic)])
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:include_router:moderation_router",
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:app.routers.restaurants:moderation_router",
        "legacy_app.py: sensitive app surface grew for api_key: 1 > 0",
    ]


def test_legacy_growth_guard_rejects_normal_router_import() -> None:
    source = "import app.routers.new_surface as new_surface\n"

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:import:app.routers.new_surface -> new_surface"
    ]


def test_legacy_growth_guard_rejects_sensitive_call_growth() -> None:
    source = "def call(provider):\n    return provider.generate('unsafe')\n"

    errors = legacy_guard.validate_legacy_growth(
        source,
        sensitive_call_limits={key: 0 for key in legacy_guard.SENSITIVE_CALL_KEYWORDS},
    )

    assert errors == ["legacy_app.py: sensitive call family grew for provider: 1 > 0"]


@pytest.mark.parametrize(
    ("keyword", "source"),
    [
        (
            "api_key",
            "\n".join(
                "api_key_guard()" for _ in range(legacy_guard.SENSITIVE_CALL_LIMITS["api_key"] + 1)
            ),
        ),
        ("auth", "auth_guard()\n"),
        ("entitlement", "entitlement.check()\n"),
        (
            "llm",
            "\n".join(
                "llm.generate()" for _ in range(legacy_guard.SENSITIVE_CALL_LIMITS["llm"] + 1)
            ),
        ),
        ("provider", "provider.generate()\nprovider.generate()\n"),
        ("quota", "quota.consume()\nquota.consume()\n"),
    ],
)
def test_legacy_growth_guard_rejects_current_baseline_sensitive_growth(
    keyword: str,
    source: str,
) -> None:
    errors = legacy_guard.validate_legacy_growth(source)

    limit = legacy_guard.SENSITIVE_CALL_LIMITS[keyword]
    assert errors == [
        f"legacy_app.py: sensitive call family grew for {keyword}: {limit + 1} > {limit}"
    ]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            "from providers.openai import client\nclient.generate('unsafe')\n",
            "legacy_app.py: sensitive call family grew for provider: 1 > 0",
        ),
        (
            "from core.llm import model as m\nm.generate('unsafe')\n",
            "legacy_app.py: sensitive call family grew for llm: 1 > 0",
        ),
        (
            "from core import llm as l\nl.model.generate('unsafe')\n",
            "legacy_app.py: sensitive call family grew for llm: 1 > 0",
        ),
    ],
)
def test_legacy_growth_guard_rejects_sensitive_import_alias_calls(
    source: str,
    expected: str,
) -> None:
    errors = legacy_guard.validate_legacy_growth(
        source,
        sensitive_call_limits={key: 0 for key in legacy_guard.SENSITIVE_CALL_KEYWORDS},
    )

    assert errors == [expected]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            textwrap.dedent("""
                auth_alias = auth_guard
                guard = auth_alias
                guard()
                """),
            "legacy_app.py: sensitive call family grew for auth: 1 > 0",
        ),
        (
            textwrap.dedent("""
                from app.auth import auth_guard as imported_guard

                guard = imported_guard
                guard()
                """),
            "legacy_app.py: sensitive call family grew for auth: 1 > 0",
        ),
    ],
)
def test_legacy_growth_guard_rejects_sensitive_local_assignment_alias_calls(
    source: str,
    expected: str,
) -> None:
    errors = legacy_guard.validate_legacy_growth(
        source,
        sensitive_call_limits={key: 0 for key in legacy_guard.SENSITIVE_CALL_KEYWORDS},
    )

    assert errors == [expected]


def test_legacy_growth_guard_rejects_auth_dependency_on_reintroduced_route() -> None:
    source = textwrap.dedent("""
        @app.post("/api/v1/insight", dependencies=[Depends(auth_guard)])
        def insight_v1_route():
            return {"ok": True}
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "decorator:post:/api/v1/insight -> insight_v1_route",
        "legacy_app.py: sensitive app surface grew for auth: 1 > 0",
    ]


def test_legacy_growth_guard_rejects_auth_dependency_on_allowed_router() -> None:
    source = "app.include_router(_vip_mod.router, dependencies=[Depends(auth_guard)])\n"

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:include_router:_vip_mod.router",
        "legacy_app.py: sensitive app surface grew for auth: 1 > 0",
    ]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            textwrap.dedent("""
                deps = [Depends(auth_guard)]

                @app.post("/api/v1/insight", dependencies=deps)
                def insight_v1_route():
                    return {"ok": True}
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "decorator:post:/api/v1/insight -> insight_v1_route",
                "legacy_app.py: sensitive app surface grew for auth: 1 > 0",
            ],
        ),
        (
            textwrap.dedent("""
                deps = [Depends(auth_guard)]
                app.include_router(_vip_mod.router, dependencies=deps)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:_vip_mod.router",
                "legacy_app.py: sensitive app surface grew for auth: 1 > 0",
            ],
        ),
    ],
    ids=[
        "decorator_dependency_alias",
        "include_router_dependency_alias",
    ],
)
def test_legacy_growth_guard_rejects_sensitive_dependency_aliases(
    source: str,
    expected: list[str],
) -> None:
    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == expected


def test_legacy_growth_guard_rejects_api_key_surface_growth_on_current_baseline() -> None:
    source = (REPO_ROOT / "legacy_app.py").read_text(encoding="utf-8")
    limit = legacy_guard.SENSITIVE_APP_SURFACE_LIMITS["api_key"]
    source += textwrap.dedent("""

        @app.post("/api/v1/insight", dependencies=[Depends(api_key_guard)])
        def insight_v1_route():
            return {"ok": True}
        """) * (limit + 1)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "decorator:post:/api/v1/insight -> insight_v1_route",
        f"legacy_app.py: sensitive app surface grew for api_key: {limit + 1} > {limit}",
    ]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            textwrap.dedent("""
                @app.post("/api/v1/insight")
                async def insight_v1_route():
                    return {"ok": True}
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "decorator:post:/api/v1/insight -> insight_v1_route",
            ],
        ),
        (
            textwrap.dedent("""
                @app.post("/insight")
                async def insight_route():
                    return {"ok": True}
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "decorator:post:/insight -> insight_route",
            ],
        ),
        (
            'app.router.add_api_route("/api/v1/insight", handler, methods=["POST"])\n',
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:router.add_api_route:/api/v1/insight",
            ],
        ),
        (
            'app.add_api_route("/insight", handler, methods=["POST"])\n',
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:add_api_route:/insight",
            ],
        ),
        (
            textwrap.dedent("""
                legacy = app

                @legacy.post("/insight")
                async def wrapped_insight_route():
                    return {"ok": True}
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "decorator:post:/insight -> wrapped_insight_route",
            ],
        ),
        (
            "app.include_router(insight_router)\n",
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:insight_router",
            ],
        ),
        (
            textwrap.dedent("""
                import importlib

                _mod = importlib.import_module("app.routers.legacy_insight")
                app.include_router(_mod.router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:_mod.router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.legacy_insight -> _mod",
            ],
        ),
    ],
    ids=[
        "direct_decorator_v1",
        "direct_decorator_legacy",
        "router_add_api_route",
        "app_add_api_route",
        "aliased_app_wrapper",
        "include_router",
        "dynamic_imported_router",
    ],
)
def test_legacy_growth_guard_blocks_insight_route_reintroduction(
    source: str,
    expected: list[str],
) -> None:
    """Extracted insight routes must never regrow inside legacy_app.py."""

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == expected


def test_legacy_growth_guard_ignores_comments_and_strings() -> None:
    source = textwrap.dedent("""
        "# @app.post('/not-real')"
        # app.include_router(fake_router)
        def route_text():
            return "app.include_router(fake_router)"
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


@pytest.mark.parametrize(
    "mutation",
    [
        'getattr(builtins, "__dict__")["object"] = lambda: app',
        'sys.modules["builtins"].object = lambda: app',
    ],
    ids=["getattr-builtins-dict", "sys-modules-builtins"],
)
def test_legacy_growth_guard_tracks_projected_builtins_object_mutations(
    mutation: str,
) -> None:
    source = textwrap.dedent(f"""
        import builtins
        import sys

        {mutation}
        value = object()
        value.get("/api/v1/projected-builtins-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/projected-builtins-route"
    ]


def test_legacy_growth_guard_preserves_poisoned_object_helper_return() -> None:
    source = textwrap.dedent("""
        import builtins

        builtins.object = lambda: app

        def make():
            return object()

        value = make()
        value.get("/api/v1/helper-object-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/helper-object-route"
    ]


def test_legacy_growth_guard_tracks_imported_builtins_dictionary_mutation() -> None:
    source = textwrap.dedent("""
        from builtins import __dict__ as namespace

        namespace["object"] = lambda: app
        value = object()
        value.get("/api/v1/imported-builtins-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/imported-builtins-route"
    ]


def test_legacy_growth_guard_captures_rhs_before_object_target_mutation() -> None:
    source = textwrap.dedent("""
        globals()["object"], value = (lambda: app), object()
        value.get("/api/v1/not-a-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


@pytest.mark.parametrize(
    "loop",
    [
        (
            "for route in dict.values(routes):\n"
            '    route("/api/v1/unbound-iterator-route")(handler)'
        ),
        (
            "for _name, route in dict.items(routes):\n"
            '    route("/api/v1/unbound-iterator-route")(handler)'
        ),
    ],
    ids=["values", "items"],
)
def test_legacy_growth_guard_preserves_unbound_dict_iterator_values(loop: str) -> None:
    source = 'routes = {"route": app.get}\n' f"{loop}\n"

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/unbound-iterator-route"
    ]


@pytest.mark.parametrize(
    "alias, loop",
    [
        (
            "values",
            "for route in iterator():\n" '    route("/api/v1/bound-iterator-route")(handler)',
        ),
        (
            "items",
            "for _name, route in iterator():\n"
            '    route("/api/v1/bound-iterator-route")(handler)',
        ),
    ],
)
def test_legacy_growth_guard_preserves_bound_dict_iterator_aliases(
    alias: str,
    loop: str,
) -> None:
    source = 'routes = {"route": app.get}\n' f"iterator = routes.{alias}\n" f"{loop}\n"

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/bound-iterator-route"
    ]


def test_legacy_growth_guard_preserves_dict_fromkeys_registrar_mapping() -> None:
    source = textwrap.dedent("""
        routes = dict.fromkeys(["route"], app.get)
        route = routes["route"]
        route("/api/v1/fromkeys-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: " "registration:get:/api/v1/fromkeys-route"
    ]


def test_legacy_growth_guard_reuses_mapping_after_known_key_pop() -> None:
    source = textwrap.dedent("""
        def safe_register(*args, **kwargs):
            return None

        routes = {"route": app.get}
        routes.pop("route")
        route = routes.get("route", safe_register)
        route("/api/v1/not-a-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_updates_aliases_after_known_key_pop() -> None:
    source = textwrap.dedent("""
        def safe_register(*args, **kwargs):
            return None

        routes = {"route": app.get}
        alias = routes
        routes.pop("route")
        route = alias.get("route", safe_register)
        route("/api/v1/not-a-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_preserves_other_keys_after_known_key_pop() -> None:
    source = textwrap.dedent("""
        routes = {"route": app.get, "other": app.post}
        routes.pop("route")
        route = routes["other"]
        route("/api/v1/remaining-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:post:/api/v1/remaining-route"
    ]


@pytest.mark.parametrize(
    "pop_call",
    ['routes.pop("route", None)', 'dict.pop(routes, "route", None)'],
    ids=["bound", "unbound"],
)
def test_legacy_growth_guard_preserves_mapping_after_absent_key_pop(pop_call: str) -> None:
    source = textwrap.dedent(f"""
        routes = {{"other": app.get}}
        {pop_call}
        route = routes.get("route", safe)
        route("/api/v1/not-a-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_preserves_other_registrar_after_absent_key_pop() -> None:
    source = textwrap.dedent("""
        routes = {"other": app.get}
        routes.pop("route", None)
        route = routes.get("other", safe)
        route("/api/v1/other-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: " "registration:get:/api/v1/other-route"
    ]


@pytest.mark.parametrize(
    ("right", "expected"),
    [
        (
            "{}",
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:get:/api/v1/dict-union-route"
            ],
        ),
        ('{"route": safe_register}', []),
    ],
    ids=["preserved", "overwritten-safe"],
)
def test_legacy_growth_guard_preserves_dict_union_mapping(
    right: str,
    expected: list[str],
) -> None:
    source = textwrap.dedent(f"""
        def safe_register(*args, **kwargs):
            return None

        routes = {{"route": app.get}}
        cloned = routes | {right}
        route = cloned["route"]
        route("/api/v1/dict-union-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == expected


@pytest.mark.parametrize("selector", ["max", "min"])
def test_legacy_growth_guard_ignores_unreachable_selector_default(selector: str) -> None:
    source = textwrap.dedent(f"""
        def safe_register(*args, **kwargs):
            return None

        route = {selector}([safe_register], default=app.get)
        route("/api/v1/not-a-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_keeps_reachable_selector_default_fail_closed() -> None:
    source = textwrap.dedent("""
        route = max([], default=app.get)
        route("/api/v1/empty-selector-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/empty-selector-route"
    ]


@pytest.mark.parametrize(
    ("mapping", "expected"),
    [
        ('{"route": app.get, "route": safe_register}', []),
        (
            '{"route": safe_register, "route": app.get}',
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:get:/api/v1/repeated-key-route"
            ],
        ),
    ],
    ids=["overwritten-safe", "overwritten-sensitive"],
)
def test_legacy_growth_guard_uses_last_static_mapping_value(
    mapping: str,
    expected: list[str],
) -> None:
    source = textwrap.dedent(f"""
        def safe_register(*args, **kwargs):
            return None

        routes = {mapping}
        for route in routes.values():
            route("/api/v1/repeated-key-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == expected


def test_legacy_growth_guard_ignores_unreachable_empty_zip_body() -> None:
    source = textwrap.dedent("""
        routes = {"route": app.get}
        for _name, route in zip([], routes.values()):
            route("/api/v1/not-a-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


@pytest.mark.parametrize(
    ("lookup", "method"),
    [
        ('routes = dict(route=app.get)\nroute = routes["route"]', "get"),
        (
            (
                "def install(**registrars):\n"
                '    route = dict.get(registrars, "route")\n'
                '    route("/api/v1/static-mapping-route")(handler)\n'
                "install(route=app.get)"
            ),
            "dynamic",
        ),
        (
            ('routes = {"route": app.get}\n' 'route = dict.pop(routes, "route")'),
            "get",
        ),
        (
            ('routes = {"route": app.get}\n' 'route = dict.setdefault(routes, "route")'),
            "get",
        ),
        (
            ('routes = {"route": app.get}\n' 'route = dict.__getitem__(routes, "route")'),
            "get",
        ),
        (
            ('routes = {"route": app.get}\n' "cloned = routes.copy()\n" 'route = cloned["route"]'),
            "get",
        ),
        (
            ('routes = {"route": app.get}\n' "_name, route = routes.popitem()"),
            "get",
        ),
    ],
    ids=[
        "dict-constructor",
        "unbound-get",
        "unbound-pop",
        "unbound-setdefault",
        "unbound-dunder-getitem",
        "mapping-copy",
        "popitem",
    ],
)
def test_legacy_growth_guard_preserves_static_mapping_projections(
    lookup: str,
    method: str,
) -> None:
    trailing_call = (
        ""
        if 'route("/api/v1/static-mapping-route")' in lookup
        else '\nroute("/api/v1/static-mapping-route")(handler)'
    )

    assert legacy_guard.validate_legacy_growth(f"{lookup}{trailing_call}\n") == [
        "legacy_app.py: unexpected legacy route growth: "
        f"registration:{method}:/api/v1/static-mapping-route"
    ]


def test_legacy_growth_guard_preserves_empty_mapping_after_singleton_popitem() -> None:
    source = textwrap.dedent("""
        def safe_register(*args, **kwargs):
            return lambda handler: handler

        routes = {"route": app.get}
        routes.popitem()
        route = routes.get("route", safe_register)
        route("/api/v1/not-a-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_preserves_setdefault_insertion_in_mapping_state() -> None:
    source = textwrap.dedent("""
        routes = {}
        routes.setdefault("route", app.get)
        route = routes["route"]
        route("/api/v1/setdefault-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/setdefault-route"
    ]


def test_legacy_growth_guard_uses_mapping_state_after_default_clear() -> None:
    source = textwrap.dedent("""
        def safe(*args, **kwargs):
            return None

        routes = {"route": app.get}

        def clear():
            routes.clear()
            return safe

        route = routes.get("route", clear())
        route("/api/v1/not-a-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_preserves_empty_mapping_alias_after_clear() -> None:
    source = textwrap.dedent("""
        def safe_register(*args, **kwargs):
            return None

        routes = {"route": app.get}
        routes.clear()
        route = routes.get("route", safe_register)
        route("/api/v1/not-a-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_preserves_mapping_after_literal_key_delete() -> None:
    source = textwrap.dedent("""
        def safe_register(*args, **kwargs):
            return None

        routes = {"route": app.get}
        del routes["route"]
        route = routes.get("route", safe_register)
        route("/api/v1/not-a-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_preserves_safe_zip_slots_beyond_pairs() -> None:
    source = textwrap.dedent("""
        routes = {"route": app.get}
        for route, _middle, other in zip(routes.values(), [1], [2]):
            other("/api/v1/not-a-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_ignores_unreachable_next_default() -> None:
    source = textwrap.dedent("""
        def safe(*args, **kwargs):
            return None

        route = next(iter([safe]), app.get)
        route("/api/v1/not-a-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_uses_first_static_next_element() -> None:
    source = textwrap.dedent("""
        route = next(iter([safe, app.get]))
        route("/api/v1/not-a-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_preserves_first_static_next_registrar() -> None:
    source = textwrap.dedent("""
        route = next(iter([app.get, safe]))
        route("/api/v1/first-next-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/first-next-route"
    ]


def test_legacy_growth_guard_keeps_reachable_next_default_fail_closed() -> None:
    source = textwrap.dedent("""
        route = next(iter([]), app.get)
        route("/api/v1/empty-next-route")(handler)
        """)

    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:get:/api/v1/empty-next-route"
    ]


def test_legacy_growth_guard_fails_closed_on_syntax_error() -> None:
    errors = legacy_guard.validate_legacy_growth("def broken(:\n")

    assert errors == ["legacy_app.py:1: syntax error: invalid syntax"]


def test_legacy_seam_doc_rejects_missing_marker() -> None:
    text = (REPO_ROOT / "docs/architecture/LEGACY_COMPATIBILITY_SEAM.md").read_text(
        encoding="utf-8"
    )
    text = text.replace("<!-- LEGACY_SEAM_OPENAPI_CHANGED: false -->\n", "")

    errors = legacy_guard.validate_legacy_seam_doc(text)

    assert (
        "docs/architecture/LEGACY_COMPATIBILITY_SEAM.md: missing marker LEGACY_SEAM_OPENAPI_CHANGED"
        in errors
    )


def test_legacy_repo_validation_rejects_empty_doc(tmp_path: Path) -> None:
    (tmp_path / "legacy_app.py").write_text("", encoding="utf-8")
    doc_path = tmp_path / "docs/architecture/LEGACY_COMPATIBILITY_SEAM.md"
    doc_path.parent.mkdir(parents=True)
    doc_path.write_text("", encoding="utf-8")

    errors = legacy_guard.validate_repo(tmp_path)

    assert (
        "docs/architecture/LEGACY_COMPATIBILITY_SEAM.md: missing marker LEGACY_SEAM_STATUS"
        in errors
    )
    assert "app: canonical source scan root is missing" in errors


def test_legacy_repo_validation_fails_closed_when_legacy_source_is_unreadable(
    tmp_path: Path,
) -> None:
    (tmp_path / "legacy_app.py").mkdir()

    errors = legacy_guard.validate_repo(tmp_path)

    assert "legacy_app.py: unable to read: IsADirectoryError" in errors


def test_legacy_repo_validation_preserves_logical_legacy_path_for_symlink(
    tmp_path: Path,
) -> None:
    target_path = tmp_path / "legacy-target.py"
    target_path.write_text("admin_status = canonical\n", encoding="utf-8")
    (tmp_path / "legacy_app.py").symlink_to(target_path.name)

    errors = legacy_guard.validate_repo(tmp_path)

    assert (
        "legacy_app.py: retired Python compatibility binding is forbidden: admin_status" in errors
    )


def test_legacy_repo_validation_preserves_logical_route_path_for_symlink(
    tmp_path: Path,
) -> None:
    target_path = tmp_path / "legacy-route-target.py"
    target_path.write_text(
        '@app.get("/unexpected")\nasync def unexpected_route():\n    return None\n',
        encoding="utf-8",
    )
    (tmp_path / "legacy_app.py").symlink_to(target_path.name)

    errors = legacy_guard.validate_repo(tmp_path)

    assert (
        "legacy_app.py: unexpected legacy route growth: "
        "decorator:get:/unexpected -> unexpected_route" in errors
    )
    assert not any(
        error.startswith("legacy-route-target.py: unexpected legacy route growth")
        for error in errors
    )


def test_legacy_growth_guard_cli_reports_global_loop_budget_without_traceback(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (tmp_path / "legacy_app.py").write_text(_CONSOL_GETTER_IMPORTS, encoding="utf-8")
    owner_path = tmp_path / legacy_guard.CANONICAL_API_KEY
    owner_path.parent.mkdir(parents=True)
    owner_path.write_text(_canonical_api_key_owner_source(), encoding="utf-8")
    main_path = tmp_path / "app/main.py"
    main_path.write_text(
        "".join(f"for item_{index} in values:\n    pass\n" for index in range(129)),
        encoding="utf-8",
    )

    exit_code = legacy_guard.main(["--repo-root", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "ERROR: app/main.py: loop binding analysis exceeded 128 total iterations" in captured.err
    assert "Traceback" not in captured.err


def test_legacy_growth_guard_cli_passes(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = legacy_guard.main(["--repo-root", str(REPO_ROOT)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "legacy compatibility seam guard passed" in captured.out


@pytest.mark.parametrize(
    "class_binding",
    [
        pytest.param("route_map = routes", id="S22-N1-direct"),
        pytest.param("route_map: dict = routes", id="S22-N2-annotated"),
        pytest.param("(route_map,) = (routes,)", id="S22-N3-tuple"),
        pytest.param("[route_map] = [routes]", id="S22-N4-list"),
        pytest.param("([route_map],) = ([routes],)", id="S22-N5-tuple-list"),
        pytest.param("[(route_map,)] = [(routes,)]", id="S22-N5-list-tuple"),
        pytest.param(
            "route_map, other_alias = routes, routes", id="S22-N5-shared-identity-aliases"
        ),
    ],
)
def test_legacy_growth_guard_invalidates_mapping_published_in_class(class_binding: str) -> None:
    """A resolved mapping published as an actual class member loses static certainty."""
    source = (
        'routes = {"route": None}\n'
        "class Holder:\n"
        f"    {class_binding}\n"
        'Holder.route_map["route"] = app.get\n'
        'register = {"route": app.get, **routes}["route"]\n'
        'register("/api/v1/class-alias-mutation")(handler)\n'
    )
    assert legacy_guard.validate_legacy_growth(source) == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:dynamic:/api/v1/class-alias-mutation"
    ]


@pytest.mark.parametrize(
    "binding",
    [
        pytest.param("route_map = routes", id="S22-A1-direct"),
        pytest.param("(route_map,) = (routes,)", id="S22-A1-tuple"),
        pytest.param("[route_map] = [routes]", id="S22-A1-list"),
        pytest.param("([route_map],) = ([routes],)", id="S22-A1-nested"),
    ],
)
def test_legacy_growth_guard_keeps_unpublished_local_mapping_static(binding: str) -> None:
    """Ordinary resolved local aliases do not publish into a class namespace."""
    source = (
        'routes = {"route": None}\n'
        f"{binding}\n"
        'register = {"route": app.get, **route_map}["route"]\n'
        'register("/api/v1/not-a-route")(handler)\n'
    )
    assert legacy_guard.validate_legacy_growth(source) == []


@pytest.mark.parametrize(
    "setup",
    [
        pytest.param(
            'other = {"unrelated": None}\nclass Holder:\n    route_map = other\n',
            id="S22-A2-unrelated-identity",
        ),
        pytest.param(
            "class Holder:\n    route_map: dict\n    unrelated = object()\n",
            id="S22-A3-no-value-annotation",
        ),
        pytest.param(
            "class Holder:\n    global route_map\n    route_map = routes\n",
            id="S22-A6-global-outward",
        ),
    ],
)
def test_legacy_growth_guard_distinguishes_class_member_publication(setup: str) -> None:
    """Only the delivered mapping identity at an actual member invalidates safe routes."""
    source = (
        'routes = {"route": None}\n'
        + setup
        + 'register = {"route": app.get, **routes}["route"]\n'
        + 'register("/api/v1/not-a-route")(handler)\n'
    )
    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_keeps_class_nonlocal_mapping_outward() -> None:
    """A class nonlocal assignment is an enclosing alias rather than a member publication."""
    source = textwrap.dedent("""
        def configure():
            route_map = None
            routes = {"route": None}
            class Holder:
                nonlocal route_map
                route_map = routes
            register = {"route": app.get, **routes}["route"]
            register("/api/v1/not-a-route")(handler)
        configure()
        """)
    assert legacy_guard.validate_legacy_growth(source) == []


@pytest.mark.parametrize(
    ("source", "expected_error"),
    [
        pytest.param(
            "def lookup():\n    return legacy._install_openapi_builder\n"
            "import legacy_app as legacy\n",
            "app/main.py: OpenAPI symbol must not be accessed through legacy",
            id="S23-N1-function-attribute",
        ),
        pytest.param(
            "def lookup():\n    return getattr(legacy, installer_attr)\n"
            'import legacy_app as legacy\ninstaller_attr = "_install_openapi_builder"\n',
            "app/main.py: OpenAPI symbol must not be accessed through legacy",
            id="S23-N2-function-late-string",
        ),
        pytest.param(
            "class Lookup:\n    def value(self):\n"
            "        return legacy._install_openapi_builder\nimport legacy_app as legacy\n",
            "app/main.py: OpenAPI symbol must not be accessed through legacy",
            id="S23-N3-method-attribute",
        ),
        pytest.param(
            "class Lookup:\n    def value(self):\n"
            "        return getattr(legacy, installer_attr)\n"
            'import legacy_app as legacy\ninstaller_attr = "_install_openapi_builder"\n',
            "app/main.py: OpenAPI symbol must not be accessed through legacy",
            id="S23-N3-method-late-string",
        ),
        pytest.param(
            "lookup = lambda: legacy._install_openapi_builder\nimport legacy_app as legacy\n",
            "app/main.py: OpenAPI symbol must not be accessed through legacy",
            id="S23-N3-lambda-attribute",
        ),
        pytest.param(
            "lookup = lambda: getattr(legacy, installer_attr)\n"
            'import legacy_app as legacy\ninstaller_attr = "_install_openapi_builder"\n',
            "app/main.py: OpenAPI symbol must not be accessed through legacy",
            id="S23-N3-lambda-late-string",
        ),
        pytest.param(
            "def outer():\n    def inner():\n        def leaf():\n"
            "            return legacy._install_openapi_builder\n"
            "        return leaf\n    return inner\nimport legacy_app as legacy\n",
            "app/main.py: OpenAPI symbol must not be accessed through legacy",
            id="S23-N4-three-level-attribute",
        ),
        pytest.param(
            "def outer():\n    return lambda: lambda: getattr(legacy, installer_attr)\n"
            'import legacy_app as legacy\ninstaller_attr = "_install_openapi_builder"\n',
            "app/main.py: OpenAPI symbol must not be accessed through legacy",
            id="S23-N4-nested-lambda-string",
        ),
        pytest.param(
            "def outer():\n    import legacy_app as legacy\n"
            "    def inner():\n        return legacy._install_openapi_builder\n    return inner\n",
            "app/main.py: OpenAPI symbol must not be accessed through legacy",
            id="S23-N5-enclosing-receiver",
        ),
        pytest.param(
            "def outer():\n    import legacy_app as legacy\n"
            "    def inner():\n        nonlocal legacy\n"
            "        return legacy._install_openapi_builder\n    return inner\n",
            "app/main.py: OpenAPI symbol must not be accessed through legacy",
            id="S23-N5-nonlocal-receiver",
        ),
        pytest.param(
            'def outer():\n    installer_attr = "_install_openapi_builder"\n'
            "    def inner():\n        nonlocal installer_attr\n"
            "        return getattr(legacy, installer_attr)\n    return inner\n"
            "import legacy_app as legacy\n",
            "app/main.py: OpenAPI symbol must not be accessed through legacy",
            id="S23-N5-nonlocal-name",
        ),
        pytest.param(
            "def outer():\n    import legacy_app as legacy\n"
            '    installer_attr = "_install_openapi_builder"\n'
            "    def inner():\n        nonlocal legacy, installer_attr\n"
            "        value = getattr(legacy, installer_attr)\n"
            '        legacy = object()\n        installer_attr = "other"\n'
            "        return value\n    return inner\n",
            "app/main.py: OpenAPI symbol must not be accessed through legacy",
            id="S23-N6-early-nonlocal-before-safe",
        ),
        pytest.param(
            "def outer():\n    import legacy_app as legacy\n"
            "    def middle():\n        def inner():\n            nonlocal legacy\n"
            "            return legacy._install_openapi_builder\n"
            "        return inner\n    return middle\n",
            "app/main.py: OpenAPI symbol must not be accessed through legacy",
            id="S23-N7-nonlocal-skips-middle",
        ),
        pytest.param(
            "def outer():\n    def inner():\n        import legacy_app as legacy\n"
            "        return legacy._install_openapi_builder\n    return inner\n",
            "app/main.py: OpenAPI symbol must not be accessed through legacy",
            id="S23-N8-nested-import-attribute",
        ),
        pytest.param(
            "def lookup():\n    import legacy_app as legacy\n"
            '    return getattr(legacy, "_install_openapi_builder")\n',
            "app/main.py: OpenAPI symbol must not be accessed through legacy",
            id="S23-N8-local-import-getattr",
        ),
        pytest.param(
            "def outer():\n    def inner():\n"
            "        from legacy_app import _install_openapi_builder as installer\n"
            "        return installer\n    return inner\n",
            "app/main.py: OpenAPI symbol must not be imported through legacy: "
            "_install_openapi_builder",
            id="S23-N8-nested-from-import",
        ),
        pytest.param(
            "import legacy_app as legacy\n"
            'def lookup(legacy=getattr(legacy, "_install_openapi_builder")):\n'
            "    return legacy\n",
            "app/main.py: OpenAPI symbol must not be accessed through legacy",
            id="S23-N9-defining-default",
        ),
        pytest.param(
            "def outer():\n    def inner(legacy):\n"
            "        return legacy._install_openapi_builder\n    return inner\n"
            "import legacy_app as legacy\n",
            None,
            id="S23-A1-nested-receiver-parameter",
        ),
        pytest.param(
            "def outer():\n    def inner(installer_attr):\n"
            "        return getattr(legacy, installer_attr)\n    return inner\n"
            'import legacy_app as legacy\ninstaller_attr = "_install_openapi_builder"\n',
            None,
            id="S23-A2-nested-name-parameter",
        ),
        pytest.param(
            "def outer():\n    def inner():\n        legacy = object()\n"
            "        return legacy._install_openapi_builder\n    return inner\n"
            "import legacy_app as legacy\n",
            None,
            id="S23-A3-local-receiver-attribute",
        ),
        pytest.param(
            "def outer():\n    def inner():\n        legacy = object()\n"
            '        return getattr(legacy, "_install_openapi_builder")\n    return inner\n'
            "import legacy_app as legacy\n",
            None,
            id="S23-A3-local-receiver-getattr",
        ),
        pytest.param(
            'def outer():\n    def inner():\n        installer_attr = "other"\n'
            "        return getattr(legacy, installer_attr)\n    return inner\n"
            'import legacy_app as legacy\ninstaller_attr = "_install_openapi_builder"\n',
            None,
            id="S23-A4-local-safe-name",
        ),
        pytest.param(
            "def outer():\n    return lambda legacy: legacy._install_openapi_builder\n"
            "import legacy_app as legacy\n",
            None,
            id="S23-A5-lambda-receiver-parameter",
        ),
        pytest.param(
            "def outer():\n"
            "    return lambda: lambda installer_attr: getattr(legacy, installer_attr)\n"
            'import legacy_app as legacy\ninstaller_attr = "_install_openapi_builder"\n',
            None,
            id="S23-A5-nested-lambda-name-parameter",
        ),
        pytest.param(
            "class Lookup:\n    def value(self, legacy):\n"
            "        return legacy._install_openapi_builder\nimport legacy_app as legacy\n",
            None,
            id="S23-A6-method-parameter",
        ),
        pytest.param(
            "class Lookup:\n    def value(self):\n        legacy = object()\n"
            '        return getattr(legacy, "_install_openapi_builder")\n'
            "import legacy_app as legacy\n",
            None,
            id="S23-A6-method-local",
        ),
        pytest.param(
            "def outer():\n    legacy = object()\n    def inner():\n"
            "        return legacy._install_openapi_builder\n    return inner\n"
            "import legacy_app as legacy\n",
            None,
            id="S23-A7-enclosing-safe-receiver",
        ),
        pytest.param(
            'def outer():\n    installer_attr = "other"\n    def inner():\n'
            "        return getattr(legacy, installer_attr)\n    return inner\n"
            'import legacy_app as legacy\ninstaller_attr = "_install_openapi_builder"\n',
            None,
            id="S23-A7-enclosing-safe-name",
        ),
        pytest.param(
            "def outer():\n    legacy = object()\n    def inner():\n        nonlocal legacy\n"
            "        return legacy._install_openapi_builder\n    return inner\n"
            "import legacy_app as legacy\n",
            None,
            id="S23-A8-safe-nonlocal-receiver",
        ),
        pytest.param(
            'def outer():\n    installer_attr = "other"\n'
            "    def inner():\n        nonlocal installer_attr\n"
            "        return getattr(legacy, installer_attr)\n    return inner\n"
            'import legacy_app as legacy\ninstaller_attr = "_install_openapi_builder"\n',
            None,
            id="S23-A8-safe-nonlocal-name",
        ),
        pytest.param(
            "def outer():\n    legacy = object()\n    def middle():\n        def inner():\n"
            "            nonlocal legacy\n            return legacy._install_openapi_builder\n"
            "        return inner\n    return middle\nimport legacy_app as legacy\n",
            None,
            id="S23-A9-safe-three-level-nonlocal",
        ),
        pytest.param(
            "other = object()\ndef lookup(legacy=other):\n"
            '    return getattr(legacy, "_install_openapi_builder")\nimport legacy_app as legacy\n',
            None,
            id="S23-A11-nonlegacy-default",
        ),
        pytest.param(
            'import legacy_app as legacy\nvalue = getattr(legacy, "unrelated")\n',
            None,
            id="S23-A11-unrelated-member",
        ),
        pytest.param(
            "import legacy_app as legacy\ndef outer():\n"
            "    make = lambda choice=(legacy := object()): choice\n"
            "    return legacy._install_openapi_builder\n",
            None,
            id="S23-A3-lambda-default-local-binder",
        ),
        pytest.param(
            "import legacy_app as legacy\ndef outer():\n"
            "    make = lambda: (legacy := object())\n"
            "    return legacy._install_openapi_builder\n",
            "app/main.py: OpenAPI symbol must not be accessed through legacy",
            id="S23-N9-lambda-body-not-enclosing-binder",
        ),
    ],
)
def test_metadata_openapi_ownership_guard_uses_own_lexical_provenance(
    source: str, expected_error: str | None
) -> None:
    """Preserve the protected spelling while independently varying receiver/name ownership."""
    expected = [expected_error] if expected_error is not None else []
    assert _consol_openapi_errors(source) == expected


@pytest.mark.parametrize(
    ("source", "forbidden"),
    [
        pytest.param(
            'import legacy_app as legacy\nif first:\n    name = "_install_openapi_builder"\n'
            'else:\n    name = "other"\nif second:\n    name = "different"\n'
            "value = getattr(legacy, name)\n",
            True,
            id="openapi-absorbing-repeated-safe-join",
        ),
        pytest.param(
            'import legacy_app as legacy\nif first:\n    name = "_install_openapi_builder"\n'
            "if second:\n    pass\nvalue = getattr(legacy, name)\n",
            True,
            id="openapi-absorbing-missing-binding",
        ),
        pytest.param(
            "import legacy_app as legacy\ndef member():\n    if enabled:\n"
            '        return "_install_openapi_builder"\n    return "other"\n'
            "value = getattr(legacy, member())\n",
            True,
            id="openapi-call-result-join",
        ),
        pytest.param(
            'import legacy_app as legacy\nvalue = getattr(legacy, "get_api_key")\n',
            False,
            id="api-name-is-not-openapi-name",
        ),
        pytest.param(
            "import legacy_app as legacy\npick = getattr\n"
            'value = pick(legacy, "_install_openapi_builder")\n',
            True,
            id="openapi-builtin-getattr-alias",
        ),
        pytest.param(
            "import legacy_app as legacy\ngetattr = object()\n"
            'value = getattr(legacy, "_install_openapi_builder")\n',
            False,
            id="openapi-shadowed-getattr",
        ),
    ],
)
def test_metadata_openapi_ownership_guard_preserves_family_string_provenance(
    source: str, forbidden: bool
) -> None:
    """Possible names survive shared joins without crossing the finite family boundary."""
    expected = (
        ["app/main.py: OpenAPI symbol must not be accessed through legacy"] if forbidden else []
    )
    assert _consol_openapi_errors(source) == expected


@pytest.mark.parametrize(
    "member_expression",
    [
        pytest.param('"_install_" + "openapi_builder"', id="concatenation"),
        pytest.param("f\"_install_{'openapi'}_builder\"", id="formatted-value"),
        pytest.param('(member := "_install_openapi_builder")', id="named-expression"),
        pytest.param('"customOPENAPIHook"', id="casefold-nonenumerated-openapi"),
        pytest.param('"_collect_schema_refs"', id="exact-name-without-openapi-substring"),
    ],
)
def test_metadata_openapi_ownership_guard_preserves_supported_name_expressions(
    member_expression: str,
) -> None:
    """Use the existing finite string recognizer and existing casefold/exact-name contract."""
    source = f"import legacy_app as legacy\nvalue = getattr(legacy, {member_expression})\n"
    assert _consol_openapi_errors(source) == [
        "app/main.py: OpenAPI symbol must not be accessed through legacy"
    ]


@pytest.mark.parametrize("postponed", [False, True], ids=["active", "postponed"])
def test_metadata_openapi_ownership_guard_preserves_annotation_execution_context(
    postponed: bool,
) -> None:
    """A postponed annotation supplies no visited snapshot; an evaluated default still does."""
    annotation = (
        "import legacy_app as legacy\n"
        'def lookup(value: getattr(legacy, "_install_openapi_builder")):\n'
        "    return value\n"
    )
    expected = (
        [] if postponed else ["app/main.py: OpenAPI symbol must not be accessed through legacy"]
    )
    assert _consol_openapi_errors(annotation, postponed_annotations=postponed) == expected
    default = (
        "import legacy_app as legacy\n"
        'def lookup(value=getattr(legacy, "_install_openapi_builder")):\n'
        "    return value\n"
    )
    assert _consol_openapi_errors(default, postponed_annotations=postponed) == [
        "app/main.py: OpenAPI symbol must not be accessed through legacy"
    ]


@pytest.mark.parametrize(
    ("symbol", "handler"),
    [
        pytest.param(symbol, handler.format(symbol=symbol), id=f"{kind}-{symbol}")
        for symbol in _CONSOL_API_KEY_SYMBOLS
        for kind, handler in (
            ("type", "except ({symbol} := ReplacementError):\n    pass\n"),
            (
                "tuple-type",
                "except (ReplacementError, ({symbol} := ReplacementError)):\n    pass\n",
            ),
            (
                "lambda-default",
                "except (lambda choice=({symbol} := ReplacementError): choice)():\n    pass\n",
            ),
        )
    ],
)
def test_api_key_ownership_guard_rejects_exception_type_and_default_rebinding(
    symbol: str, handler: str
) -> None:
    """Full owner and genuine exception prerequisites isolate the protected containing binder."""
    source = (
        _CONSOL_GETTER_IMPORTS
        + "class ReplacementError(Exception):\n    pass\n"
        + "try:\n    raise ReplacementError()\n"
        + handler
    )
    assert _validate_api_key_dependency_ownership(source, {}) == [
        _CONSOL_API_KEY_REBINDING_ERRORS[symbol]
    ]


@pytest.mark.parametrize("compound", ["if", "try", "with", "for"])
def test_api_key_ownership_guard_rejects_compound_exception_type_rebinding(compound: str) -> None:
    """Module compounds preserve the module scope of an exception-type walrus."""
    handler = (
        "try:\n    raise ReplacementError()\n"
        "except (get_api_key := ReplacementError):\n    pass\n"
    )
    templates = {
        "if": "if enabled:\n{body}",
        "try": "try:\n{body}except Exception:\n    pass\n",
        "with": "with context():\n{body}",
        "for": "for item in values:\n{body}",
    }
    source = (
        _CONSOL_GETTER_IMPORTS
        + "class ReplacementError(Exception):\n    pass\n"
        + templates[compound].format(body=textwrap.indent(handler, "    "))
    )
    assert _validate_api_key_dependency_ownership(source, {}) == [
        _CONSOL_API_KEY_REBINDING_ERRORS["get_api_key"]
    ]


@pytest.mark.parametrize(
    ("symbol", "definition"),
    [
        pytest.param(symbol, definition.format(symbol=symbol), id=f"{kind}-{symbol}")
        for symbol in _CONSOL_API_KEY_SYMBOLS
        for kind, definition in (
            ("function-default", "def child(value=({symbol} := ReplacementError)):\n    pass\n"),
            ("async-default", "async def child(value=({symbol} := ReplacementError)):\n    pass\n"),
            ("keyword-default", "def child(*, value=({symbol} := ReplacementError)):\n    pass\n"),
            ("decorator", "@({symbol} := ReplacementError)\ndef child():\n    pass\n"),
            (
                "parameter-annotation",
                "def child(value: ({symbol} := ReplacementError)):\n    pass\n",
            ),
            ("return-annotation", "def child() -> ({symbol} := ReplacementError):\n    pass\n"),
            ("class-base", "class Child(({symbol} := ReplacementError)):\n    pass\n"),
            ("class-keyword", "class Child(metaclass=({symbol} := ReplacementError)):\n    pass\n"),
        )
    ],
)
def test_api_key_ownership_guard_rejects_defining_scope_header_rebinding(
    symbol: str, definition: str
) -> None:
    """Headers/defaults bind in the containing scope while function and class bodies stay local."""
    source = _CONSOL_GETTER_IMPORTS + "class ReplacementError(Exception):\n    pass\n" + definition
    assert _validate_api_key_dependency_ownership(source, {}) == [
        _CONSOL_API_KEY_REBINDING_ERRORS[symbol]
    ]


@pytest.mark.parametrize(
    "handler",
    [
        pytest.param("except:\n    pass\n", id="S24-A1-bare"),
        pytest.param("except ReplacementError:\n    pass\n", id="S24-A1-ordinary"),
        pytest.param(
            "except (unrelated := ReplacementError) as caught:\n    pass\n",
            id="S24-A2-unrelated-type-and-alias",
        ),
    ],
)
def test_api_key_ownership_guard_accepts_unrelated_exception_binding(handler: str) -> None:
    """The same type visitor must not invent a protected module Store for ordinary handlers."""
    source = (
        _CONSOL_GETTER_IMPORTS
        + "class ReplacementError(Exception):\n    pass\n"
        + "try:\n    raise ReplacementError()\n"
        + handler
    )
    assert _validate_api_key_dependency_ownership(source, {}) == []


@pytest.mark.parametrize(
    ("symbol", "local_source"),
    [
        pytest.param(symbol, local.format(symbol=symbol), id=f"{kind}-{symbol}")
        for symbol in _CONSOL_API_KEY_SYMBOLS
        for kind, local in (
            (
                "handler-local",
                "def enclosing():\n    try:\n        raise ReplacementError()\n"
                "    except ({symbol} := ReplacementError):\n        pass\n",
            ),
            (
                "lambda-body",
                "try:\n    raise ReplacementError()\n"
                "except (lambda: ({symbol} := ReplacementError))():\n    pass\n",
            ),
            (
                "enclosing-function-default",
                "def enclosing():\n    def child(value=({symbol} := ReplacementError)):\n"
                "        return value\n    return child\n",
            ),
            (
                "enclosing-lambda-default",
                "def enclosing():\n    return lambda value=({symbol} := ReplacementError): value\n",
            ),
        )
    ],
)
def test_api_key_ownership_guard_accepts_genuine_local_type_and_default_bindings(
    symbol: str, local_source: str
) -> None:
    """Protected spelling in a genuine body/enclosing local scope is not a module rebinding."""
    source = (
        _CONSOL_GETTER_IMPORTS + "class ReplacementError(Exception):\n    pass\n" + local_source
    )
    assert _validate_api_key_dependency_ownership(source, {}) == []


def _canonical_api_key_owner_without(symbol: str) -> str:
    """Remove only one declaration from the real full input while retaining its other content."""
    source = _canonical_api_key_owner_source()
    declaration = (
        "api_key_header = APIKeyHeader" if symbol == "api_key_header" else f"def {symbol}("
    )
    renamed = (
        "removed_api_key_header = APIKeyHeader"
        if symbol == "api_key_header"
        else f"def removed_{symbol}("
    )
    assert source.count(declaration) == 1
    return source.replace(declaration, renamed, 1)


def test_api_key_ownership_guard_requires_real_owner_source() -> None:
    """A direct strict call must reject actual owner absence, bypassing input augmentation."""
    assert legacy_guard.validate_api_key_dependency_ownership(_CONSOL_GETTER_IMPORTS, {}) == [
        "app/routers/api_key.py: canonical API-key owner source is missing"
    ]


def test_api_key_ownership_guard_rejects_empty_owner_source() -> None:
    """An explicit empty input cannot be replaced with the real owner by the fixture helper."""
    expected = sorted(
        f"app/routers/api_key.py: canonical API-key owner symbol is missing: {name}"
        for name in _CONSOL_API_KEY_SYMBOLS
    )
    sources = {legacy_guard.CANONICAL_API_KEY: ""}
    assert (
        legacy_guard.validate_api_key_dependency_ownership(_CONSOL_GETTER_IMPORTS, sources)
        == expected
    )
    assert _validate_api_key_dependency_ownership(_CONSOL_GETTER_IMPORTS, sources) == expected
    assert sources == {legacy_guard.CANONICAL_API_KEY: ""}


def test_api_key_ownership_guard_rejects_malformed_owner_source() -> None:
    """The actual production parser owns the canonical-path syntax diagnostic."""
    malformed_source = "def broken(:\n"
    sources = {legacy_guard.CANONICAL_API_KEY: malformed_source}
    expected = ["app/routers/api_key.py:1: syntax error: invalid syntax"]
    assert (
        legacy_guard.validate_api_key_dependency_ownership(_CONSOL_GETTER_IMPORTS, sources)
        == expected
    )
    assert _validate_api_key_dependency_ownership(_CONSOL_GETTER_IMPORTS, sources) == expected


@pytest.mark.parametrize("symbol", _CONSOL_API_KEY_SYMBOLS)
def test_api_key_ownership_guard_requires_each_real_owner_binding(symbol: str) -> None:
    """Each missing binding is tested against an otherwise complete real owner input."""
    sources = {legacy_guard.CANONICAL_API_KEY: _canonical_api_key_owner_without(symbol)}
    assert legacy_guard.validate_api_key_dependency_ownership(_CONSOL_GETTER_IMPORTS, sources) == [
        f"app/routers/api_key.py: canonical API-key owner symbol is missing: {symbol}"
    ]


@pytest.mark.parametrize(
    ("symbol", "witness"),
    [
        pytest.param(symbol, witness, id=f"{kind}-{symbol}")
        for symbol in _CONSOL_API_KEY_SYMBOLS
        for kind, witness in (
            ("nested-only", "def local_owner():\n    {symbol} = object()\n"),
            ("bare-annotation", "{symbol}: object\n"),
            ("conditional-only", "if enabled:\n    {symbol} = object()\n"),
            ("delete", "del {symbol}\n"),
        )
    ],
)
def test_api_key_ownership_guard_rejects_non_module_owner_witness(
    symbol: str, witness: str
) -> None:
    """Nested/bare/possible bindings and deletion cannot witness a definite owner binding."""
    owner = (
        _canonical_api_key_owner_source()
        if witness.startswith("del ")
        else _canonical_api_key_owner_without(symbol)
    )
    owner += "\n" + witness.format(symbol=symbol)
    assert legacy_guard.validate_api_key_dependency_ownership(
        _CONSOL_GETTER_IMPORTS, {legacy_guard.CANONICAL_API_KEY: owner}
    ) == [f"app/routers/api_key.py: canonical API-key owner symbol is missing: {symbol}"]


@pytest.mark.parametrize(
    ("symbol", "binding"),
    [
        pytest.param(symbol, binding.format(symbol=symbol), id=f"{kind}-{symbol}")
        for symbol in _CONSOL_API_KEY_SYMBOLS
        for kind, binding in (
            ("import", "import unrelated as {symbol}\n"),
            ("from-import", "from unrelated import value as {symbol}\n"),
            ("for-target", "for {symbol} in values:\n    pass\n"),
            ("with-target", "with context() as {symbol}:\n    pass\n"),
            ("except-alias", "try:\n    pass\nexcept Exception as {symbol}:\n    pass\n"),
            ("conditional-store", "if enabled:\n    {symbol} = replacement\n"),
            ("class", "class {symbol}:\n    pass\n"),
            ("tuple-store", "({symbol}, other) = (replacement, None)\n"),
            ("list-store", "[{symbol}] = [replacement]\n"),
        )
    ],
)
def test_api_key_ownership_guard_rejects_full_inventory_module_bindings(
    symbol: str, binding: str
) -> None:
    """All five protected names, not just the two imports, reject supported module carriers."""
    assert _validate_api_key_dependency_ownership(_CONSOL_GETTER_IMPORTS + binding, {}) == [
        _CONSOL_API_KEY_REBINDING_ERRORS[symbol]
    ]


@pytest.mark.parametrize(
    ("imports", "missing", "rebound"),
    [
        pytest.param(
            "from unrelated import _get_api_key_dynamic, get_api_key\n",
            _CONSOL_LEGACY_GETTERS,
            _CONSOL_LEGACY_GETTERS,
            id="wrong-module",
        ),
        pytest.param(
            "from app.routers.api_key import _get_api_key_dynamic, get_api_key as renamed\n",
            ("get_api_key",),
            (),
            id="renamed-getter",
        ),
        pytest.param(
            "from app.routers.api_key import _get_api_key_dynamic\n",
            ("get_api_key",),
            (),
            id="missing-getter",
        ),
        pytest.param(
            "from app.routers.api_key import get_api_key\n",
            ("_get_api_key_dynamic",),
            (),
            id="missing-dynamic-getter",
        ),
        pytest.param(
            "if enabled:\n    from app.routers.api_key import _get_api_key_dynamic, get_api_key\n",
            _CONSOL_LEGACY_GETTERS,
            (),
            id="conditional-only",
        ),
    ],
)
def test_api_key_ownership_guard_requires_exact_two_absolute_imports(
    imports: str, missing: tuple[str, ...], rebound: tuple[str, ...]
) -> None:
    """Wrong, renamed, missing or conditional imports cannot witness unconditional identity."""
    expected = [
        f"legacy_app.py: canonical API-key compatibility re-export must preserve identity: {name}"
        for name in missing
    ] + [_CONSOL_API_KEY_REBINDING_ERRORS[name] for name in rebound]
    assert _validate_api_key_dependency_ownership(imports, {}) == sorted(expected)


@pytest.mark.parametrize("level", [1, 2], ids=["relative-one", "relative-two"])
def test_api_key_ownership_guard_rejects_relative_reexports(level: int) -> None:
    """Matching module text with nonzero ImportFrom.level fails both existing import sites."""
    source = f"from {'.' * level}app.routers.api_key import _get_api_key_dynamic, get_api_key\n"
    expected = [
        f"legacy_app.py: canonical API-key compatibility re-export must preserve identity: {name}"
        for name in _CONSOL_LEGACY_GETTERS
    ] + [_CONSOL_API_KEY_REBINDING_ERRORS[name] for name in _CONSOL_LEGACY_GETTERS]
    assert _validate_api_key_dependency_ownership(source, {}) == sorted(expected)


@pytest.mark.parametrize(
    ("symbol", "level"),
    [
        pytest.param(symbol, level, id=f"level-{level}-{symbol}")
        for symbol in _CONSOL_LEGACY_GETTERS
        for level in (1, 2)
    ],
)
def test_api_key_ownership_guard_does_not_exempt_later_relative_import(
    symbol: str, level: int
) -> None:
    """Valid initial absolute exports cannot hide a subsequent relative replacement."""
    source = _CONSOL_GETTER_IMPORTS + f"from {'.' * level}app.routers.api_key import {symbol}\n"
    assert _validate_api_key_dependency_ownership(source, {}) == [
        _CONSOL_API_KEY_REBINDING_ERRORS[symbol]
    ]


@pytest.mark.parametrize(
    "symbol", ["api_key_header", "validate_app_api_key", "require_app_api_key"]
)
def test_api_key_ownership_guard_rejects_extra_legacy_reexport(symbol: str) -> None:
    """The other three canonical bindings never become legitimate compatibility imports."""
    source = _CONSOL_GETTER_IMPORTS + f"from app.routers.api_key import {symbol}\n"
    assert _validate_api_key_dependency_ownership(source, {}) == [
        _CONSOL_API_KEY_REBINDING_ERRORS[symbol]
    ]


@pytest.mark.parametrize(
    ("symbol", "lookup"),
    [
        pytest.param(symbol, lookup.format(symbol=symbol), id=f"{kind}-{symbol}")
        for symbol in _CONSOL_API_KEY_SYMBOLS
        for kind, lookup in (
            ("vars-subscript", 'dependency = vars(legacy)["{symbol}"]\n'),
            ("dict-subscript", 'dependency = legacy.__dict__["{symbol}"]\n'),
            ("namespace-get", 'dependency = vars(legacy).get("{symbol}")\n'),
            ("namespace-getitem", 'dependency = legacy.__dict__.__getitem__("{symbol}")\n'),
            ("builtin-dict-get", 'dependency = dict.get(vars(legacy), "{symbol}")\n'),
            (
                "unbound-dict-getitem-vars",
                'dependency = dict.__getitem__(vars(legacy), "{symbol}")\n',
            ),
            (
                "unbound-dict-getitem-dict",
                'dependency = dict.__getitem__(legacy.__dict__, "{symbol}")\n',
            ),
            ("bound-namespace-method", 'pick = vars(legacy).get\ndependency = pick("{symbol}")\n'),
            (
                "static-mapping",
                'owners = {{"selected": vars(legacy)}}\n'
                'dependency = owners["selected"]["{symbol}"]\n',
            ),
        )
    ],
)
def test_api_key_ownership_guard_rejects_full_inventory_namespace_consumers(
    symbol: str, lookup: str
) -> None:
    """Existing namespace/mapping consumers apply all five names with real owner input."""
    source = "import legacy_app as legacy\n" + lookup
    assert _validate_api_key_dependency_ownership(
        _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
    ) == [
        f"app/routers/example.py: legacy API-key dependency namespace lookup is forbidden: {symbol}"
    ]


@pytest.mark.parametrize("symbol", _CONSOL_API_KEY_SYMBOLS)
def test_api_key_ownership_guard_rejects_full_inventory_getattr(symbol: str) -> None:
    """All five names are rejected through the same actual legacy getter consumer."""
    source = f'import legacy_app as legacy\ndependency = getattr(legacy, "{symbol}")\n'
    assert _validate_api_key_dependency_ownership(
        _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
    ) == [
        f"app/routers/example.py: dynamic legacy API-key dependency lookup is forbidden: {symbol}"
    ]


@pytest.mark.parametrize("symbol", _CONSOL_API_KEY_SYMBOLS)
def test_api_key_ownership_guard_rejects_legacy_getattr_at_owner_path(symbol: str) -> None:
    """Canonical filename does not exempt a proven legacy receiver in complete real owner input."""
    owner = _canonical_api_key_owner_source() + (
        f'\nimport legacy_app as legacy\nforbidden = getattr(legacy, "{symbol}")\n'
    )
    assert legacy_guard.validate_api_key_dependency_ownership(
        _CONSOL_GETTER_IMPORTS, {legacy_guard.CANONICAL_API_KEY: owner}
    ) == [
        f"app/routers/api_key.py: dynamic legacy API-key dependency lookup is forbidden: {symbol}"
    ]


@pytest.mark.parametrize(
    "imports",
    [
        pytest.param(_CONSOL_GETTER_IMPORTS, id="bare-same-names"),
        pytest.param(
            "from app.routers.api_key import _get_api_key_dynamic as _get_api_key_dynamic, "
            "get_api_key as get_api_key\n",
            id="explicit-as-same-names",
        ),
    ],
)
def test_api_key_ownership_guard_accepts_full_owner_and_two_absolute_imports(imports: str) -> None:
    """Real owner plus exactly two absolute identity-preserving imports satisfies the contract."""
    assert (
        legacy_guard.validate_api_key_dependency_ownership(
            imports, {legacy_guard.CANONICAL_API_KEY: _canonical_api_key_owner_source()}
        )
        == []
    )


@pytest.mark.parametrize(
    ("symbol", "local"),
    [
        pytest.param(symbol, local.format(symbol=symbol), id=f"{kind}-{symbol}")
        for symbol in _CONSOL_API_KEY_SYMBOLS
        for kind, local in (
            ("assignment", "def local_scope():\n    {symbol} = object()\n    return {symbol}\n"),
            ("parameter", "def local_scope({symbol}):\n    return {symbol}\n"),
            ("lambda-body", "local_value = lambda: ({symbol} := object())\n"),
        )
    ],
)
def test_api_key_ownership_guard_accepts_all_five_genuine_legacy_locals(
    symbol: str, local: str
) -> None:
    """Full-five protection preserves actual local scope with identical protected spelling."""
    assert _validate_api_key_dependency_ownership(_CONSOL_GETTER_IMPORTS + local, {}) == []


@pytest.mark.parametrize(
    "addition",
    [
        pytest.param("", id="unchanged-real-owner"),
        pytest.param(
            'other = object()\nvalue = getattr(other, "get_api_key", get_api_key)\n',
            id="nonlegacy-getattr-default",
        ),
        pytest.param(
            'def local_lookup(legacy):\n    return getattr(legacy, "get_api_key", get_api_key)\n',
            id="nonlegacy-parameter",
        ),
        pytest.param(
            "def local_lookup(legacy=object()):\n"
            '    return getattr(legacy, "_get_api_key_dynamic", None)\n',
            id="nonlegacy-function-default",
        ),
    ],
)
def test_api_key_ownership_guard_preserves_nonlegacy_owner_getattr(addition: str) -> None:
    """The real owner's getter and nonlegacy receiver/default/parameter stay admissible."""
    owner = _canonical_api_key_owner_source() + "\n" + addition
    assert (
        legacy_guard.validate_api_key_dependency_ownership(
            _CONSOL_GETTER_IMPORTS, {legacy_guard.CANONICAL_API_KEY: owner}
        )
        == []
    )


@pytest.mark.parametrize(
    ("source", "forbidden"),
    [
        pytest.param(
            'import legacy_app as legacy\nif first:\n    name = "get_api_key"\n'
            'else:\n    name = "other"\nif second:\n    name = "different"\n'
            "value = getattr(legacy, name)\n",
            True,
            id="api-absorbing-repeated-safe-join",
        ),
        pytest.param(
            'import legacy_app as legacy\nif first:\n    name = "get_api_key"\n'
            "if second:\n    pass\nvalue = getattr(legacy, name)\n",
            True,
            id="api-absorbing-missing-binding",
        ),
        pytest.param(
            'import legacy_app as legacy\nif first:\n    name = "_install_openapi_builder"\n'
            'else:\n    name = "other"\nvalue = getattr(legacy, name)\n',
            False,
            id="openapi-name-is-not-api-name",
        ),
    ],
)
def test_api_key_ownership_guard_preserves_family_string_join_policy(
    source: str, forbidden: bool
) -> None:
    """API markers remain absorbing; OpenAPI membership cannot leak into the API consumer."""
    expected = (
        ["app/routers/example.py: dynamic legacy API-key dependency lookup is forbidden: <dynamic>"]
        if forbidden
        else []
    )
    assert (
        _validate_api_key_dependency_ownership(
            _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
        )
        == expected
    )


@pytest.mark.parametrize("postponed", [False, True], ids=["active", "postponed"])
def test_api_key_ownership_guard_preserves_annotation_execution_context(postponed: bool) -> None:
    """Shared API annotation context stays independent from evaluated defaults."""
    prefix = "from __future__ import annotations\n" if postponed else ""
    source = prefix + (
        'import legacy_app as legacy\ndef lookup(value: getattr(legacy, "get_api_key")):\n'
        "    return value\n"
    )
    expected = (
        []
        if postponed
        else [
            "app/routers/example.py: dynamic legacy API-key dependency lookup is forbidden: get_api_key"
        ]
    )
    assert (
        _validate_api_key_dependency_ownership(
            _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
        )
        == expected
    )
    default = prefix + (
        'import legacy_app as legacy\ndef lookup(value=getattr(legacy, "get_api_key")):\n'
        "    return value\n"
    )
    assert _validate_api_key_dependency_ownership(
        _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": default}
    ) == [
        "app/routers/example.py: dynamic legacy API-key dependency lookup is forbidden: get_api_key"
    ]


def test_legacy_growth_guard_real_current_root_cli() -> None:
    """Invoke the actual script and filesystem owner with the current absolute interpreter."""

    def fingerprint_inputs() -> dict[str, object]:
        try:
            explicit_owners = {
                "scripts/ci/check_legacy_growth_guard.py",
                legacy_guard.LEGACY_APP,
                legacy_guard.LEGACY_SEAM_DOC,
                legacy_guard.FOOD_SEARCH_BOOTSTRAP,
                legacy_guard.CANONICAL_LIFESPAN,
                legacy_guard.CANONICAL_APPLICATION_METADATA,
                legacy_guard.CANONICAL_OPENAPI,
                legacy_guard.CANONICAL_MAIN,
                legacy_guard.APP_FACADE,
            }
            app_root = REPO_ROOT / "app"
            if not app_root.is_dir():
                return {"state": "unknown"}
            app_paths = {path.relative_to(REPO_ROOT).as_posix() for path in app_root.rglob("*.py")}
            input_paths = explicit_owners | app_paths
            aggregate = hashlib.sha256()
            owner_hashes: dict[str, str] = {}
            byte_count = 0
            for relative in sorted(input_paths):
                contents = (REPO_ROOT / relative).read_bytes()
                digest = hashlib.sha256(contents).hexdigest()
                aggregate.update(f"{relative}\0{digest}\0".encode("utf-8"))
                byte_count += len(contents)
                if relative in explicit_owners:
                    owner_hashes[relative] = digest
            return {
                "state": "known",
                "app_py_count": len(app_paths),
                "input_path_count": len(input_paths),
                "input_byte_count": byte_count,
                "raw_file_inputs_sha256": aggregate.hexdigest(),
                "explicit_owner_sha256": owner_hashes,
            }
        except Exception:
            return {"state": "unknown"}

    inputs_before = fingerprint_inputs()
    cpu_before: tuple[float, float] | None = None
    try:
        started: float | None = time.monotonic()
    except Exception:
        started = None
    try:
        usage_before = resource.getrusage(resource.RUSAGE_CHILDREN)
        cpu_before = (usage_before.ru_utime, usage_before.ru_stime)
    except Exception:
        pass
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-I",
                "-B",
                str(REPO_ROOT / "scripts/ci/check_legacy_growth_guard.py"),
                "--repo-root",
                str(REPO_ROOT),
            ],
            cwd=REPO_ROOT,
            env={"PYTHONDONTWRITEBYTECODE": "1"},
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        try:
            elapsed = time.monotonic() - started if started is not None else None
        except Exception:
            elapsed = None
        cpu_delta: dict[str, float] | None = None
        try:
            usage_after = resource.getrusage(resource.RUSAGE_CHILDREN)
            if cpu_before is not None:
                cpu_delta = {
                    "user_seconds": usage_after.ru_utime - cpu_before[0],
                    "system_seconds": usage_after.ru_stime - cpu_before[1],
                }
        except Exception:
            pass
        try:
            inputs_after = fingerprint_inputs()
            diagnostic = {
                "event": "legacy_guard_cli_timeout",
                "elapsed_seconds": elapsed,
                "reaped_children_accounting_window_cpu_delta": cpu_delta,
                "cpu_scope": "accounting_window_not_pid_exclusive",
                "host_cause": "unknown",
                "fingerprint_scope": "non_atomic_raw_file_read_set",
                "inputs_before": inputs_before,
                "inputs_after": inputs_after,
                "readback_equal": (
                    inputs_before == inputs_after
                    if inputs_before.get("state") == inputs_after.get("state") == "known"
                    else None
                ),
            }
            sys.stderr.write(json.dumps(diagnostic, sort_keys=True, allow_nan=False) + "\n")
        except Exception:
            try:
                sys.stderr.write('{"event":"legacy_guard_cli_timeout","diagnostic":"unknown"}\n')
            except Exception:
                pass
        raise
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "legacy compatibility seam guard passed"
    assert result.stderr == ""


@pytest.mark.parametrize(
    "binding",
    [
        pytest.param("route_map = routes", id="direct"),
        pytest.param("(route_map,) = (routes,)", id="tuple"),
        pytest.param("[route_map] = [routes]", id="list"),
        pytest.param("([route_map],) = ([routes],)", id="nested"),
    ],
)
def test_legacy_growth_guard_keeps_function_local_mapping_static(binding: str) -> None:
    """The corresponding actual function-local binding retains known-safe mapping precision."""
    body = (
        'routes = {"route": None}\n'
        + binding
        + '\nregister = {"route": app.get, **route_map}["route"]\n'
        + 'register("/api/v1/not-a-route")(handler)\n'
    )
    source = "def configure():\n" + textwrap.indent(body, "    ") + "configure()\n"
    assert legacy_guard.validate_legacy_growth(source) == []


@pytest.mark.parametrize(
    ("source", "forbidden"),
    [
        pytest.param(
            "def outer():\n    import legacy_app as legacy\n    def inner():\n"
            "        nonlocal legacy\n        value = legacy._install_openapi_builder\n"
            "        legacy = object()\n        return value\n    return inner\n",
            True,
            id="S23-N6-early-receiver-before-safe",
        ),
        pytest.param(
            'def outer():\n    installer_attr = "_install_openapi_builder"\n'
            "    def inner():\n        nonlocal installer_attr\n"
            "        value = getattr(legacy, installer_attr)\n"
            '        installer_attr = "other"\n        return value\n    return inner\n'
            "import legacy_app as legacy\n",
            True,
            id="S23-N6-early-name-before-safe",
        ),
        pytest.param(
            'def outer():\n    installer_attr = "_install_openapi_builder"\n'
            "    def middle():\n        def inner():\n            nonlocal installer_attr\n"
            "            return getattr(legacy, installer_attr)\n"
            "        return inner\n    return middle\nimport legacy_app as legacy\n",
            True,
            id="S23-N7-name-skips-middle",
        ),
        pytest.param(
            'def outer():\n    installer_attr = "other"\n'
            "    def middle():\n        def inner():\n            nonlocal installer_attr\n"
            "            return getattr(legacy, installer_attr)\n"
            "        return inner\n    return middle\nimport legacy_app as legacy\n"
            'installer_attr = "_install_openapi_builder"\n',
            False,
            id="S23-A9-safe-name-skips-middle",
        ),
    ],
)
def test_metadata_openapi_ownership_guard_distinguishes_nonlocal_receiver_and_name(
    source: str, forbidden: bool
) -> None:
    """Each nonlocal axis retains its own nearest-owner and early-use control."""
    expected = (
        ["app/main.py: OpenAPI symbol must not be accessed through legacy"] if forbidden else []
    )
    assert _consol_openapi_errors(source) == expected


@pytest.mark.parametrize(
    ("symbol", "lookup"),
    [
        pytest.param(symbol, lookup, id=f"{kind}-{symbol}")
        for symbol in _CONSOL_OPENAPI_SYMBOLS
        for kind, lookup in (
            ("attribute", "value = legacy.{symbol}\n"),
            ("getattr", 'value = getattr(legacy, "{symbol}")\n'),
        )
    ],
)
def test_metadata_openapi_ownership_guard_rejects_every_protected_name(
    symbol: str, lookup: str
) -> None:
    """Exact seven-name membership includes names without the OpenAPI substring."""
    source = "import legacy_app as legacy\n" + lookup.format(symbol=symbol)
    assert _consol_openapi_errors(source) == [
        "app/main.py: OpenAPI symbol must not be accessed through legacy"
    ]


@pytest.mark.parametrize("symbol", _CONSOL_API_KEY_SYMBOLS)
def test_api_key_ownership_guard_accepts_owner_binding_in_lambda_default(symbol: str) -> None:
    """An evaluated containing-scope lambda default supplies the missing module witness."""
    owner = _canonical_api_key_owner_without(symbol) + (
        f"\nchoose = lambda value=({symbol} := object()): value\n"
    )
    assert (
        legacy_guard.validate_api_key_dependency_ownership(
            _CONSOL_GETTER_IMPORTS, {legacy_guard.CANONICAL_API_KEY: owner}
        )
        == []
    )


@pytest.mark.parametrize("symbol", _CONSOL_API_KEY_SYMBOLS)
def test_api_key_ownership_guard_rejects_owner_binding_only_in_lambda_body(symbol: str) -> None:
    """The matching lambda body remains local during definite module-owner collection."""
    owner = _canonical_api_key_owner_without(symbol) + (
        f"\nchoose = lambda: ({symbol} := object())\n"
    )
    assert legacy_guard.validate_api_key_dependency_ownership(
        _CONSOL_GETTER_IMPORTS, {legacy_guard.CANONICAL_API_KEY: owner}
    ) == [f"app/routers/api_key.py: canonical API-key owner symbol is missing: {symbol}"]


@pytest.mark.parametrize("symbol", _CONSOL_API_KEY_SYMBOLS)
def test_api_key_ownership_guard_preserves_class_local_protected_names(symbol: str) -> None:
    """An unrelated class's local protected spelling does not restore a legacy module export."""
    source = _CONSOL_GETTER_IMPORTS + f"class Local:\n    {symbol} = object()\n"
    assert _validate_api_key_dependency_ownership(source, {}) == []


def test_api_key_ownership_guard_preserves_api_call_result_name_join() -> None:
    """The existing API summary/evaluator retains a possible API name through its own join."""
    source = (
        "import legacy_app as legacy\ndef member():\n    if enabled:\n"
        '        return "get_api_key"\n    return "other"\n'
        "value = getattr(legacy, member())\n"
    )
    assert _validate_api_key_dependency_ownership(
        _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
    ) == [
        "app/routers/example.py: dynamic legacy API-key dependency lookup is forbidden: <dynamic>"
    ]


def test_legacy_repo_validation_reports_unreadable_api_key_owner(tmp_path: Path) -> None:
    """Filesystem read failure remains visible instead of acquiring an augmented owner."""
    _write_consol_complete_guard_fixture(tmp_path)
    owner_path = tmp_path / legacy_guard.CANONICAL_API_KEY
    owner_path.unlink()
    owner_path.mkdir()
    errors = legacy_guard.validate_repo(tmp_path)
    assert "app/routers/api_key.py: unable to read: IsADirectoryError" in errors
    assert "app/routers/api_key.py: canonical API-key owner source is missing" in errors


@pytest.mark.parametrize("family", ["api", "openapi"])
def test_consol_ownership_join_retains_possible_name_after_missing(family: str) -> None:
    """A second branch deleting the name cannot erase the first possible protected witness."""
    protected = "get_api_key" if family == "api" else "_install_openapi_builder"
    source = (
        "import legacy_app as legacy\nif first:\n"
        f"    name = {protected!r}\nelse:\n    name = 'other'\n"
        "if second:\n    del name\nvalue = getattr(legacy, name)\n"
    )
    if family == "api":
        assert _validate_api_key_dependency_ownership(
            _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
        ) == [
            "app/routers/example.py: dynamic legacy API-key dependency lookup "
            "is forbidden: <dynamic>"
        ]
    else:
        assert _consol_openapi_errors(source) == [
            "app/main.py: OpenAPI symbol must not be accessed through legacy"
        ]


@pytest.mark.parametrize("consumer", ["api", "openapi"])
@pytest.mark.parametrize("marker_family", ["api", "openapi"])
def test_consol_ownership_consumers_keep_possible_marker_families_separate(
    consumer: str, marker_family: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Inject an actual family marker at the existing binding/snapshot seam."""
    marker_name = (
        "_POSSIBLE_API_KEY_SYMBOL" if marker_family == "api" else "_POSSIBLE_OPENAPI_SYMBOL"
    )
    marker = getattr(legacy_guard, marker_name, None)
    assert isinstance(marker, str), f"missing finite protected-string marker: {marker_name}"
    expected_forbidden = consumer == marker_family
    if consumer == "api":
        errors: list[str] = []
        visitor = legacy_guard._ApiKeyLookupVisitor(
            filename="app/routers/example.py", errors=errors
        )
        visitor.scope.bind("probe_name", reference=None, string=marker)
        visitor.visit(
            ast.parse("import legacy_app as legacy\nvalue = getattr(legacy, probe_name)\n")
        )
        expected = (
            [
                "app/routers/example.py: dynamic legacy API-key dependency lookup "
                "is forbidden: <dynamic>"
            ]
            if expected_forbidden
            else []
        )
        assert errors == expected
        return

    collect = legacy_guard._collect_lexical_binding_snapshots
    injected_nodes: list[int] = []

    def collect_with_marker(tree: ast.Module, **kwargs: Any) -> tuple[
        Mapping[int, Mapping[str, str]],
        Mapping[int, Mapping[str, str]],
        Mapping[int, legacy_guard._ResolvedBinding],
    ]:
        references, strings, results = collect(tree, **kwargs)
        injected = {
            key: {**environment, "probe_name": marker} for key, environment in strings.items()
        }
        injected_nodes.extend(injected)
        return references, injected, results

    monkeypatch.setattr(legacy_guard, "_collect_lexical_binding_snapshots", collect_with_marker)
    source = (
        "import legacy_app as legacy\nprobe_name = 'other'\n"
        "value = getattr(legacy, probe_name)\n"
    )
    expected = (
        ["app/main.py: OpenAPI symbol must not be accessed through legacy"]
        if expected_forbidden
        else []
    )
    errors = _consol_openapi_errors(source)
    assert injected_nodes, "the OpenAPI consumer must acquire its own injected marker snapshots"
    assert errors == expected


@pytest.mark.parametrize("legacy_receiver", [True, False], ids=["legacy", "safe-receiver"])
@pytest.mark.parametrize(
    "expression",
    [
        pytest.param('"_install_" + "openapi_builder"', id="concat"),
        pytest.param('f"_install_openapi_builder"', id="constant-joined-str"),
        pytest.param("f\"_install_{'openapi'}_builder\"", id="formatted-value"),
        pytest.param('"_".join(["", "install", "openapi", "builder"])', id="literal-join"),
        pytest.param('(member := "_install_openapi_builder")', id="named-expr"),
        pytest.param('"customOPENAPIHook"', id="casefold-nonenumerated"),
        pytest.param('"_collect_schema_refs"', id="exact-without-openapi-substring"),
    ],
)
def test_consol_openapi_name_expressions_have_paired_receiver_controls(
    expression: str, legacy_receiver: bool
) -> None:
    """The same protected expression is admissible with a positively nonlegacy receiver."""
    receiver = "legacy" if legacy_receiver else "other"
    source = (
        "import legacy_app as legacy\nother = object()\n"
        f"value = getattr({receiver}, {expression})\n"
    )
    expected = (
        ["app/main.py: OpenAPI symbol must not be accessed through legacy"]
        if legacy_receiver
        else []
    )
    assert _consol_openapi_errors(source) == expected


@pytest.mark.parametrize("family", ["api", "openapi"])
@pytest.mark.parametrize("safe_axis", ["none", "receiver", "name", "callee"])
def test_consol_getattr_alias_has_independent_safe_provenance(family: str, safe_axis: str) -> None:
    """A builtin alias is forbidden only with both protected-name and legacy-receiver provenance."""
    protected = "get_api_key" if family == "api" else "_install_openapi_builder"
    receiver = "other" if safe_axis == "receiver" else "legacy"
    member = "'other'" if safe_axis == "name" else repr(protected)
    callee = "object()" if safe_axis == "callee" else "getattr"
    source = (
        "import legacy_app as legacy\nother = object()\n"
        f"pick = {callee}\nvalue = pick({receiver}, {member})\n"
    )
    if family == "api":
        expected = (
            [
                "app/routers/example.py: dynamic legacy API-key dependency lookup "
                "is forbidden: get_api_key"
            ]
            if safe_axis == "none"
            else []
        )
        assert (
            _validate_api_key_dependency_ownership(
                _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
            )
            == expected
        )
    else:
        expected = (
            ["app/main.py: OpenAPI symbol must not be accessed through legacy"]
            if safe_axis == "none"
            else []
        )
        assert _consol_openapi_errors(source) == expected


@pytest.mark.parametrize("family", ["api", "openapi"])
@pytest.mark.parametrize("postponed", [False, True], ids=["active", "postponed"])
def test_consol_ownership_summary_and_argument_evaluator_preserve_annotation_context(
    family: str, postponed: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Observe actual shared summaries/evaluators and preserve their module annotation context."""
    created: list[legacy_guard._ApiKeyLookupVisitor] = []
    evaluated: list[str] = []
    initialize = legacy_guard._ApiKeyLookupVisitor.__init__
    resolve_arguments = legacy_guard._ApiKeyLookupVisitor._resolve_call_argument_bindings

    def initialize_and_record(self: legacy_guard._ApiKeyLookupVisitor, **kwargs: Any) -> None:
        initialize(self, **kwargs)
        created.append(self)

    def resolve_and_record(
        self: legacy_guard._ApiKeyLookupVisitor, *args: Any, **kwargs: Any
    ) -> dict[str, legacy_guard._ResolvedBinding] | None:
        evaluated.append(self.filename)
        return resolve_arguments(self, *args, **kwargs)

    monkeypatch.setattr(legacy_guard._ApiKeyLookupVisitor, "__init__", initialize_and_record)
    monkeypatch.setattr(
        legacy_guard._ApiKeyLookupVisitor, "_resolve_call_argument_bindings", resolve_and_record
    )
    protected = "get_api_key" if family == "api" else "_install_openapi_builder"
    source = (
        "import legacy_app as legacy\ndef member():\n"
        f"    def annotated(value: getattr(legacy, {protected!r})):\n        return value\n"
        "    return 'other'\ndef passthrough(value):\n    return value\n"
        "value = getattr(legacy, passthrough(member()))\n"
    )
    filename = "app/routers/example.py" if family == "api" else "app/main.py"
    if family == "api":
        prefix = "from __future__ import annotations\n" if postponed else ""
        expected = (
            []
            if postponed
            else [
                "app/routers/example.py: dynamic legacy API-key dependency lookup "
                "is forbidden: get_api_key"
            ]
        )
        errors = _validate_api_key_dependency_ownership(
            _CONSOL_GETTER_IMPORTS, {filename: prefix + source}
        )
    else:
        expected = (
            [] if postponed else ["app/main.py: OpenAPI symbol must not be accessed through legacy"]
        )
        errors = _consol_openapi_errors(source, postponed_annotations=postponed)
    assert errors == expected
    instances = [visitor for visitor in created if visitor.filename == filename]
    assert len(instances) >= 2, "the source must enter the actual shared summary/evaluator path"
    assert filename in evaluated, "the source must execute the existing argument evaluator"
    assert all(visitor._postponed_annotations == postponed for visitor in instances)


@pytest.mark.parametrize("analyze_bodies", [False, True], ids=["bodies-disabled", "bodies-enabled"])
@pytest.mark.parametrize("default_kind", ["positional", "keyword"])
def test_consol_lambda_defaults_are_visited_exactly_once_in_containing_scope(
    analyze_bodies: bool, default_kind: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Count the actual default AST visit before any deduplicated diagnostic can hide a repeat."""
    parameters = (
        "value=(probe_owner := 'bound')"
        if default_kind == "positional"
        else ("*, value=(probe_owner := 'bound')")
    )
    tree = ast.parse(f"choose = lambda {parameters}: value\n")
    assignment = tree.body[0]
    assert isinstance(assignment, ast.Assign)
    assert isinstance(assignment.value, ast.Lambda)
    defaults = [*assignment.value.args.defaults, *assignment.value.args.kw_defaults]
    default = next(item for item in defaults if item is not None)
    visits: list[legacy_guard._ApiKeyLookupVisitor] = []
    visit = legacy_guard._ApiKeyLookupVisitor.visit

    def visit_and_count(self: legacy_guard._ApiKeyLookupVisitor, node: ast.AST) -> object:
        if node is default:
            visits.append(self)
        return visit(self, node)

    monkeypatch.setattr(legacy_guard._ApiKeyLookupVisitor, "visit", visit_and_count)
    visitor = legacy_guard._ApiKeyLookupVisitor(
        filename="app/routers/example.py", errors=[], analyze_function_bodies=analyze_bodies
    )
    visitor.visit(tree)
    assert visits == [visitor]
    assert "probe_owner" in visitor.scope.bound_names
    assert visitor.scope.resolve_string("probe_owner") == "bound"


@pytest.mark.parametrize("symbol", _CONSOL_API_KEY_SYMBOLS)
def test_consol_exception_type_keyword_lambda_default_rebinds_protected_name(symbol: str) -> None:
    source = (
        _CONSOL_GETTER_IMPORTS
        + "class ReplacementError(Exception):\n    pass\ntry:\n    raise ReplacementError()\n"
        + f"except (lambda *, choice=({symbol} := ReplacementError): choice)():\n    pass\n"
    )
    assert _validate_api_key_dependency_ownership(source, {}) == [
        _CONSOL_API_KEY_REBINDING_ERRORS[symbol]
    ]


@pytest.mark.parametrize("symbol", _CONSOL_API_KEY_SYMBOLS)
@pytest.mark.parametrize("postponed", [False, True], ids=["active", "postponed"])
@pytest.mark.parametrize("header", ["async-annotation", "class-decorator"])
def test_consol_defining_headers_preserve_postponed_annotation_boundary(
    symbol: str, postponed: bool, header: str
) -> None:
    prefix = "from __future__ import annotations\n" if postponed else ""
    expression = f"({symbol} := ReplacementError)"
    definition = (
        f"async def child(value: {expression}):\n    pass\n"
        if header == "async-annotation"
        else f"@{expression}\nclass Child:\n    pass\n"
    )
    source = prefix + _CONSOL_GETTER_IMPORTS + "class ReplacementError(Exception):\n    pass\n"
    source += definition
    expected = (
        []
        if header == "async-annotation" and postponed
        else [_CONSOL_API_KEY_REBINDING_ERRORS[symbol]]
    )
    assert _validate_api_key_dependency_ownership(source, {}) == expected


@pytest.mark.parametrize(
    ("source", "forbidden"),
    [
        pytest.param(
            "async def lookup():\n    return getattr(legacy, member)\n"
            "import legacy_app as legacy\nmember = '_install_openapi_builder'\n",
            True,
            id="async-late-receiver-and-name",
        ),
        pytest.param(
            "async def lookup(legacy):\n    return legacy._install_openapi_builder\n"
            "import legacy_app as legacy\n",
            False,
            id="async-safe-receiver-parameter",
        ),
        pytest.param(
            "async def lookup(member):\n    return getattr(legacy, member)\n"
            "import legacy_app as legacy\nmember = '_install_openapi_builder'\n",
            False,
            id="async-safe-name-parameter",
        ),
        pytest.param(
            "import legacy_app as legacy\n"
            "async def lookup(legacy=getattr(legacy, '_install_openapi_builder')):\n"
            "    return legacy\n",
            True,
            id="async-defining-default",
        ),
        pytest.param(
            "class Holder:\n    async def lookup(self):\n"
            "        return getattr(legacy, member)\n"
            "import legacy_app as legacy\nmember = '_install_openapi_builder'\n",
            True,
            id="async-method-late-receiver-and-name",
        ),
        pytest.param(
            "class Holder:\n    async def lookup(self, legacy):\n"
            "        return legacy._install_openapi_builder\nimport legacy_app as legacy\n",
            False,
            id="async-method-safe-parameter",
        ),
    ],
)
def test_consol_openapi_async_scopes_preserve_independent_provenance(
    source: str, forbidden: bool
) -> None:
    expected = (
        ["app/main.py: OpenAPI symbol must not be accessed through legacy"] if forbidden else []
    )
    assert _consol_openapi_errors(source) == expected


@pytest.mark.parametrize("header", ["decorator", "class-base", "class-keyword", "keyword-default"])
def test_consol_openapi_defining_headers_are_not_shadowed_by_child_bindings(header: str) -> None:
    lookup = "getattr(legacy, '_install_openapi_builder')"
    definitions = {
        "decorator": f"@{lookup}\ndef child(legacy):\n    return legacy\n",
        "class-base": f"class Child({lookup}):\n    legacy = object()\n",
        "class-keyword": f"class Child(metaclass={lookup}):\n    legacy = object()\n",
        "keyword-default": f"choose = lambda *, legacy={lookup}: legacy\n",
    }
    assert _consol_openapi_errors("import legacy_app as legacy\n" + definitions[header]) == [
        "app/main.py: OpenAPI symbol must not be accessed through legacy"
    ]


@pytest.mark.parametrize("lookup_kind", ["getattr", "attribute"])
def test_consol_openapi_missing_own_snapshot_cannot_use_outer_final_context(
    lookup_kind: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    collect = legacy_guard._collect_lexical_binding_snapshots
    omitted_nodes: list[int] = []

    def collect_without_lookup(tree: ast.Module, **kwargs: Any) -> tuple[
        Mapping[int, Mapping[str, str]],
        Mapping[int, Mapping[str, str]],
        Mapping[int, legacy_guard._ResolvedBinding],
    ]:
        references, strings, results = collect(tree, **kwargs)
        omitted = {
            id(node)
            for node in ast.walk(tree)
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "getattr"
            )
            or (isinstance(node, ast.Attribute) and node.attr == "_install_openapi_builder")
        }
        omitted_nodes.extend(sorted(omitted))
        return (
            {key: value for key, value in references.items() if key not in omitted},
            {key: value for key, value in strings.items() if key not in omitted},
            {key: value for key, value in results.items() if key not in omitted},
        )

    monkeypatch.setattr(legacy_guard, "_collect_lexical_binding_snapshots", collect_without_lookup)
    lookup = (
        "getattr(legacy, '_install_openapi_builder')"
        if lookup_kind == "getattr"
        else "legacy._install_openapi_builder"
    )
    source = f"import legacy_app as legacy\nvalue = {lookup}\n"
    errors = _consol_openapi_errors(source)
    assert (
        omitted_nodes
    ), "the consumer must acquire snapshots before this test removes its own nodes"
    assert errors == []


@pytest.mark.parametrize("binding", ["direct", "tuple", "list"])
def test_consol_class_alias_publication_invalidates_shared_identity_once(binding: str) -> None:
    assignments = {
        "direct": "first = routes\nsecond = routes\n",
        "tuple": "first, second = routes, routes\n",
        "list": "[first, second] = [routes, routes]\n",
    }
    tree = ast.parse(
        'routes = {"route": None}\nclass Holder:\n' + textwrap.indent(assignments[binding], "    ")
    )
    visitor = legacy_guard._ApiKeyLookupVisitor(
        filename="legacy_app.py", errors=[], preserve_route_method_conflicts=True
    )
    visitor.visit(tree.body[0])
    mapping = visitor.scope.mappings["routes"]
    visitor.visit(tree.body[1])
    assert visitor._mapping_invalidation_counts.get(mapping, 0) == 1
    assert "routes" not in visitor.scope.mappings


@pytest.mark.parametrize("published", ["parent-alias", "independent-copy"])
def test_consol_class_publication_preserves_parent_identity_and_independent_copy(
    published: str,
) -> None:
    if published == "parent-alias":
        source = (
            'routes = {"route": None}\nalias = routes\nclass Holder:\n    member = alias\n'
            'register = {"route": app.get, **routes}["route"]\n'
            'register("/api/v1/class-parent-alias")(handler)\n'
        )
        expected = [
            "legacy_app.py: unexpected legacy route growth: "
            "registration:dynamic:/api/v1/class-parent-alias"
        ]
    else:
        source = (
            'routes = {"route": app.get}\ncopied = {**routes}\n'
            "class Holder:\n    first = routes\n    second = routes\n"
            'register = copied["route"]\nregister("/api/v1/class-independent-copy")(handler)\n'
        )
        expected = [
            "legacy_app.py: unexpected legacy route growth: "
            "registration:get:/api/v1/class-independent-copy"
        ]
    assert legacy_guard.validate_legacy_growth(source) == expected


@pytest.mark.parametrize("symbol", _CONSOL_API_KEY_SYMBOLS)
def test_consol_api_owner_accepts_definite_binding_in_both_branches(symbol: str) -> None:
    owner = _canonical_api_key_owner_without(symbol) + (
        f"\nif enabled:\n    {symbol} = object()\nelse:\n    {symbol} = object()\n"
    )
    assert (
        legacy_guard.validate_api_key_dependency_ownership(
            _CONSOL_GETTER_IMPORTS, {legacy_guard.CANONICAL_API_KEY: owner}
        )
        == []
    )


@pytest.mark.parametrize("iterations", [128, 129], ids=["owner-128", "owner-129"])
def test_consol_real_api_owner_keeps_existing_loop_budget(
    iterations: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Observe exact transfer counts without counting descriptor-normalization passes as loops."""
    owner = (
        _canonical_api_key_owner_source()
        + "\n"
        + "".join(f"for owner_item_{index} in values:\n    break\n" for index in range(iterations))
    )
    loops = [
        node
        for node in ast.walk(ast.parse(owner))
        if isinstance(node, (ast.For, ast.AsyncFor, ast.While))
    ]
    assert len(loops) == iterations
    assert all(
        isinstance(node, ast.For) and len(node.body) == 1 and isinstance(node.body[0], ast.Break)
        for node in loops
    )
    attempts: dict[legacy_guard._ApiKeyLookupVisitor, int] = {}
    consume_iteration = legacy_guard._ApiKeyLookupVisitor._consume_loop_iteration

    def consume_and_record(self: legacy_guard._ApiKeyLookupVisitor) -> None:
        if self.filename == legacy_guard.CANONICAL_API_KEY:
            attempts[self] = attempts.get(self, 0) + 1
        consume_iteration(self)

    monkeypatch.setattr(
        legacy_guard._ApiKeyLookupVisitor, "_consume_loop_iteration", consume_and_record
    )
    sources = {legacy_guard.CANONICAL_API_KEY: owner}
    if iterations == 129:
        with pytest.raises(
            legacy_guard.LegacyGrowthAnalysisError,
            match=r"app/routers/api_key\.py: loop binding analysis exceeded 128 total iterations",
        ):
            legacy_guard.validate_api_key_dependency_ownership(_CONSOL_GETTER_IMPORTS, sources)
    else:
        assert (
            legacy_guard.validate_api_key_dependency_ownership(_CONSOL_GETTER_IMPORTS, sources)
            == []
        )
    assert attempts, "the real owner must enter the existing loop transfer seam"
    assert set(attempts.values()) == {iterations}


def _write_consol_complete_guard_fixture(root: Path) -> None:
    """Copy the finite actual source prerequisites; never import or execute application runtime."""
    paths = (
        "legacy_app.py",
        "docs/architecture/LEGACY_COMPATIBILITY_SEAM.md",
        "app/bootstrap/food_search.py",
        "app/bootstrap/lifespan.py",
        "app/application_metadata.py",
        "app/bootstrap/openapi.py",
        "app/main.py",
        "app/__init__.py",
        "app/routers/api_key.py",
    )
    for relative_path in paths:
        destination = root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((REPO_ROOT / relative_path).read_bytes())


@pytest.mark.parametrize("failure", ["unreadable-owner", "owner-budget"])
def test_consol_cli_reports_only_intended_owner_failure_with_complete_prerequisites(
    failure: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Complete real source prerequisites isolate owner read/budget diagnostics and native exit1."""
    _write_consol_complete_guard_fixture(tmp_path)
    owner = tmp_path / "app/routers/api_key.py"
    if failure == "unreadable-owner":
        owner.unlink()
        owner.mkdir()
        expected = [
            "ERROR: app/routers/api_key.py: unable to read: IsADirectoryError",
            "ERROR: app/routers/api_key.py: canonical API-key owner source is missing",
        ]
    else:
        owner.write_text(
            owner.read_text(encoding="utf-8")
            + "\n"
            + "".join(f"for owner_item_{index} in values:\n    pass\n" for index in range(129)),
            encoding="utf-8",
        )
        expected = [
            "ERROR: app/routers/api_key.py: loop binding analysis exceeded 128 total iterations"
        ]
    assert legacy_guard.main(["--repo-root", str(tmp_path)]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert sorted(captured.err.splitlines()) == sorted(expected)
    assert "Traceback" not in captured.err
    assert str(tmp_path) not in captured.err


@pytest.mark.parametrize("inventory", ["api-five", "legacy-two", "openapi-seven"])
def test_consol_closed_protected_inventories_are_independently_exact(inventory: str) -> None:
    """Each independent finite inventory has its own case, including missing declarations."""
    if inventory == "api-five":
        assert legacy_guard.CANONICAL_API_KEY_SYMBOLS == frozenset(_CONSOL_API_KEY_SYMBOLS)
    elif inventory == "legacy-two":
        assert getattr(legacy_guard, "LEGACY_API_KEY_REEXPORTS", None) == frozenset(
            _CONSOL_LEGACY_GETTERS
        )
    else:
        assert legacy_guard.CANONICAL_OPENAPI_SYMBOLS == frozenset(_CONSOL_OPENAPI_SYMBOLS)


@pytest.mark.parametrize(
    "source",
    [
        pytest.param(
            "from types import SimpleNamespace\n"
            "other = SimpleNamespace(get_api_key=None)\n"
            "value = vars(other)['get_api_key']\n",
            id="vars-nonlegacy-owner",
        ),
        pytest.param(
            "vars = lambda owner: {'get_api_key': None}\n" "value = vars(legacy)['get_api_key']\n",
            id="shadowed-vars",
        ),
        pytest.param(
            "from types import SimpleNamespace\n"
            "other = SimpleNamespace(get_api_key=None)\n"
            "inspect = vars\nvalue = inspect(other)['get_api_key']\n",
            id="vars-alias-nonlegacy-owner",
        ),
        pytest.param(
            "class SafeLookup:\n"
            "    def get(self, owner, member):\n        return None\n"
            "dict = SafeLookup()\nvalue = dict.get(vars(legacy), 'get_api_key')\n",
            id="shadowed-dict-get",
        ),
        pytest.param(
            "mapping = {'get_api_key': None}\n" "value = dict.get(mapping, 'get_api_key')\n",
            id="dict-get-nonlegacy-mapping",
        ),
        pytest.param(
            "pick = vars(legacy).get\nvalue = pick('unrelated')\n",
            id="stored-namespace-get-safe-name",
        ),
        pytest.param(
            "owners = {'selected': vars(legacy)}\n" "value = owners['selected'].get('unrelated')\n",
            id="static-namespace-mapping-safe-name",
        ),
    ],
)
def test_consol_api_namespace_producers_preserve_safe_provenance(source: str) -> None:
    """New finite namespace producers keep builtin, receiver and member controls independent."""
    assert (
        _validate_api_key_dependency_ownership(
            _CONSOL_GETTER_IMPORTS,
            {"app/routers/example.py": "import legacy_app as legacy\n" + source},
        )
        == []
    )


def test_consol_ownership_symbol_family_rejects_unknown_selection() -> None:
    with pytest.raises(ValueError, match="unsupported ownership symbol family"):
        legacy_guard._ApiKeyLookupVisitor(
            filename="app/routers/example.py",
            errors=[],
            ownership_family=cast(Literal["api_key", "openapi"], "unknown"),
        )


@pytest.mark.parametrize(
    ("result", "expected_name"),
    [
        pytest.param("'other'", None, id="known-safe"),
        pytest.param("'get_api_key'", "get_api_key", id="known-protected"),
        pytest.param("external_member()", "<dynamic>", id="unknown"),
        pytest.param("'get_api_key' if enabled else 'other'", "<dynamic>", id="possible-protected"),
    ],
)
def test_consol_nested_api_member_call_uses_existing_result_binding(
    result: str, expected_name: str | None
) -> None:
    """Nested known-safe results stay precise while unknown/protected results still reject."""
    source = (
        "import legacy_app as legacy\ndef member():\n"
        f"    return {result}\n"
        "def passthrough(value):\n    return value\n"
        "value = getattr(legacy, passthrough(member()))\n"
    )
    expected = (
        []
        if expected_name is None
        else [
            "app/routers/example.py: dynamic legacy API-key dependency lookup "
            f"is forbidden: {expected_name}"
        ]
    )
    assert (
        _validate_api_key_dependency_ownership(
            _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
        )
        == expected
    )


@pytest.mark.parametrize(
    ("setup", "lookup"),
    [
        pytest.param("", "legacy.__dict__.get(passthrough(member()))", id="direct-namespace-get"),
        pytest.param("", "vars(legacy).get(passthrough(member()))", id="vars-namespace-get"),
        pytest.param("", "dict.get(vars(legacy), passthrough(member()))", id="unbound-dict-get"),
        pytest.param(
            "",
            "dict.__getitem__(vars(legacy), passthrough(member()))",
            id="unbound-dict-getitem",
        ),
        pytest.param(
            "pick = vars(legacy).get\n", "pick(passthrough(member()))", id="stored-namespace-get"
        ),
    ],
)
@pytest.mark.parametrize(
    ("result", "expected_name"),
    [
        pytest.param("'other'", None, id="known-safe"),
        pytest.param("'get_api_key'", "get_api_key", id="known-protected"),
        pytest.param("external_member()", "<dynamic>", id="unknown"),
        pytest.param("'get_api_key' if enabled else 'other'", "<dynamic>", id="possible-protected"),
    ],
)
def test_consol_nested_api_namespace_member_call_uses_existing_result_binding(
    setup: str, lookup: str, result: str, expected_name: str | None
) -> None:
    """All existing namespace calls preserve safe and protected nested result provenance."""
    source = (
        "import legacy_app as legacy\ndef member():\n"
        f"    return {result}\n"
        "def passthrough(value):\n    return value\n" + setup + f"value = {lookup}\n"
    )
    expected = (
        []
        if expected_name is None
        else [
            "app/routers/example.py: legacy API-key dependency namespace lookup "
            f"is forbidden: {expected_name}"
        ]
    )
    assert (
        _validate_api_key_dependency_ownership(
            _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
        )
        == expected
    )


@pytest.mark.parametrize(
    ("case_name", "assignment", "mutation", "observed_mapping", "scope", "expected_method"),
    [
        pytest.param(
            "direct-attribute",
            "Holder.route_map = routes",
            'Holder.route_map["route"] = app.get',
            "routes",
            "module",
            "dynamic",
            id="direct-attribute",
        ),
        pytest.param(
            "tuple-attribute",
            "Holder.route_map, ignored = routes, 0",
            'Holder.route_map["route"] = app.get',
            "routes",
            "module",
            "dynamic",
            id="tuple-attribute",
        ),
        pytest.param(
            "list-attribute",
            "[Holder.route_map, ignored] = [routes, 0]",
            'Holder.route_map["route"] = app.get',
            "routes",
            "module",
            "dynamic",
            id="list-attribute",
        ),
        pytest.param(
            "nested-tuple-list-attribute",
            "ignored, [Holder.route_map] = 0, [routes]",
            'Holder.route_map["route"] = app.get',
            "routes",
            "module",
            "dynamic",
            id="nested-tuple-list-attribute",
        ),
        pytest.param(
            "nested-list-tuple-attribute",
            "[(Holder.route_map,), ignored] = [(routes,), 0]",
            'Holder.route_map["route"] = app.get',
            "routes",
            "module",
            "dynamic",
            id="nested-list-tuple-attribute",
        ),
        pytest.param(
            "direct-subscript",
            'holder_values["map"] = routes',
            'holder_values["map"]["route"] = app.get',
            "routes",
            "module",
            "dynamic",
            id="direct-subscript",
        ),
        pytest.param(
            "tuple-subscript",
            'holder_values["map"], ignored = routes, 0',
            'holder_values["map"]["route"] = app.get',
            "routes",
            "module",
            "dynamic",
            id="tuple-subscript",
        ),
        pytest.param(
            "list-subscript",
            '[holder_values["map"], ignored] = [routes, 0]',
            'holder_values["map"]["route"] = app.get',
            "routes",
            "module",
            "dynamic",
            id="list-subscript",
        ),
        pytest.param(
            "nested-tuple-list-subscript",
            'ignored, [holder_values["map"]] = 0, [routes]',
            'holder_values["map"]["route"] = app.get',
            "routes",
            "module",
            "dynamic",
            id="nested-tuple-list-subscript",
        ),
        pytest.param(
            "nested-list-tuple-subscript",
            '[(holder_values["map"],), ignored] = [(routes,), 0]',
            'holder_values["map"]["route"] = app.get',
            "routes",
            "module",
            "dynamic",
            id="nested-list-tuple-subscript",
        ),
        pytest.param(
            "starred-attribute",
            "Holder.route_map, *ignored = routes, 0",
            'Holder.route_map["route"] = app.get',
            "routes",
            "module",
            "dynamic",
            id="starred-attribute",
        ),
        pytest.param(
            "starred-subscript",
            'holder_values["map"], *ignored = routes, 0',
            'holder_values["map"]["route"] = app.get',
            "routes",
            "module",
            "dynamic",
            id="starred-subscript",
        ),
        pytest.param(
            "chained-attribute",
            "Holder.route_map, ignored = alias, other = routes, 0",
            'Holder.route_map["route"] = app.get',
            "routes",
            "module",
            "dynamic",
            id="chained-attribute",
        ),
        pytest.param(
            "chained-subscript",
            'holder_values["map"], ignored = alias, other = routes, 0',
            'holder_values["map"]["route"] = app.get',
            "routes",
            "module",
            "dynamic",
            id="chained-subscript",
        ),
        pytest.param(
            "unmatched-rhs-attribute",
            "sequence = (routes, 0)\nHolder.route_map, ignored = sequence",
            'Holder.route_map["route"] = app.get',
            "routes",
            "module",
            "dynamic",
            id="unmatched-rhs-attribute",
        ),
        pytest.param(
            "unmatched-rhs-subscript",
            'sequence = (routes, 0)\nholder_values["map"], ignored = sequence',
            'holder_values["map"]["route"] = app.get',
            "routes",
            "module",
            "dynamic",
            id="unmatched-rhs-subscript",
        ),
        pytest.param(
            "local-tuple",
            "alias, ignored = routes, 0",
            'Holder.unrelated["route"] = app.get',
            "alias",
            "module",
            None,
            id="local-tuple",
        ),
        pytest.param(
            "local-list",
            "[alias, ignored] = [routes, 0]",
            'Holder.unrelated["route"] = app.get',
            "alias",
            "module",
            None,
            id="local-list",
        ),
        pytest.param(
            "local-nested",
            "ignored, [alias] = 0, [routes]",
            'Holder.unrelated["route"] = app.get',
            "alias",
            "module",
            None,
            id="local-nested",
        ),
        pytest.param(
            "copy-tuple",
            "Holder.route_map, ignored = copied, 0",
            'Holder.route_map["route"] = app.get',
            "routes",
            "module",
            None,
            id="copy-tuple",
        ),
        pytest.param(
            "copy-list",
            "[Holder.route_map, ignored] = [copied, 0]",
            'Holder.route_map["route"] = app.get',
            "routes",
            "module",
            None,
            id="copy-list",
        ),
        pytest.param(
            "copy-nested",
            "ignored, [Holder.route_map] = 0, [copied]",
            'Holder.route_map["route"] = app.get',
            "routes",
            "module",
            None,
            id="copy-nested",
        ),
        pytest.param(
            "nonlocal-outward",
            "alias = None\nclass Scope:\n    nonlocal alias\n    ([alias],) = ([routes],)",
            'Holder.unrelated["route"] = app.get',
            "alias",
            "function",
            None,
            id="nonlocal-outward",
        ),
    ],
)
def test_consol_paired_attribute_publication_preserves_mapping_escape(
    case_name: str,
    assignment: str,
    mutation: str,
    observed_mapping: str,
    scope: Literal["module", "function"],
    expected_method: Literal["dynamic"] | None,
) -> None:
    """Paired escape withdraws certainty only for the published mutable identity."""
    route = f"/api/v1/paired-publication-{case_name}"
    body = (
        'routes = {"route": None}\n'
        "copied = {**routes}\n"
        "holder_values = {}\n"
        "class Holder:\n    pass\n"
        'Holder.unrelated = {"route": None}\n'
        + assignment
        + "\n"
        + mutation
        + "\n"
        + f'register = {{"route": app.get, **{observed_mapping}}}["route"]\n'
        + f'register("{route}")(handler)\n'
    )
    source = (
        "def configure():\n" + textwrap.indent(body, "    ") + "configure()\n"
        if scope == "function"
        else body
    )
    expected = (
        [f"legacy_app.py: unexpected legacy route growth: registration:{expected_method}:{route}"]
        if expected_method is not None
        else []
    )
    assert legacy_guard.validate_legacy_growth(source) == expected


@pytest.mark.parametrize(
    ("case_name", "assignment", "observed_mappings", "expected_methods"),
    [
        pytest.param(
            "tuple-swap",
            "routes, safe = safe, routes",
            ("routes", "safe"),
            (None, "get"),
            id="tuple-swap",
        ),
        pytest.param(
            "list-swap",
            "[routes, safe] = [safe, routes]",
            ("routes", "safe"),
            (None, "get"),
            id="list-swap",
        ),
        pytest.param(
            "nested-swap",
            "([routes], safe) = ([safe], routes)",
            ("routes", "safe"),
            (None, "get"),
            id="nested-swap",
        ),
        pytest.param(
            "tuple-overlap",
            "safe, previous = routes, safe",
            ("safe", "previous"),
            ("get", None),
            id="tuple-overlap",
        ),
        pytest.param(
            "list-overlap",
            "[safe, previous] = [routes, safe]",
            ("safe", "previous"),
            ("get", None),
            id="list-overlap",
        ),
        pytest.param(
            "nested-overlap",
            "([safe], previous) = ([routes], safe)",
            ("safe", "previous"),
            ("get", None),
            id="nested-overlap",
        ),
        pytest.param(
            "tuple-self-safe",
            "safe, other = safe, safe",
            ("safe", "other"),
            (None, None),
            id="tuple-self-safe",
        ),
        pytest.param(
            "list-self-safe",
            "[safe, other] = [safe, safe]",
            ("safe", "other"),
            (None, None),
            id="list-self-safe",
        ),
        pytest.param(
            "nested-self-safe",
            "([safe], other) = ([safe], safe)",
            ("safe", "other"),
            (None, None),
            id="nested-self-safe",
        ),
        pytest.param(
            "tuple-nonoverlapping-safe",
            'first, second = safe, {"route": None}',
            ("first", "second"),
            (None, None),
            id="tuple-nonoverlapping-safe",
        ),
        pytest.param(
            "list-nonoverlapping-safe",
            '[first, second] = [safe, {"route": None}]',
            ("first", "second"),
            (None, None),
            id="list-nonoverlapping-safe",
        ),
        pytest.param(
            "nested-nonoverlapping-safe",
            '([first], second) = ([safe], {"route": None})',
            ("first", "second"),
            (None, None),
            id="nested-nonoverlapping-safe",
        ),
        pytest.param(
            "tuple-protected-before-safe-namedexpr",
            "first, second = routes, (routes := safe)",
            ("first", "second"),
            ("get", None),
            id="tuple-protected-before-safe-namedexpr",
        ),
        pytest.param(
            "list-protected-before-safe-namedexpr",
            "[first, second] = [routes, (routes := safe)]",
            ("first", "second"),
            ("get", None),
            id="list-protected-before-safe-namedexpr",
        ),
        pytest.param(
            "nested-protected-before-safe-namedexpr",
            "([first], second) = ([routes], (routes := safe))",
            ("first", "second"),
            ("get", None),
            id="nested-protected-before-safe-namedexpr",
        ),
        pytest.param(
            "tuple-safe-before-protected-namedexpr",
            "first, second = safe, (safe := routes)",
            ("first", "second"),
            (None, "get"),
            id="tuple-safe-before-protected-namedexpr",
        ),
        pytest.param(
            "list-safe-before-protected-namedexpr",
            "[first, second] = [safe, (safe := routes)]",
            ("first", "second"),
            (None, "get"),
            id="list-safe-before-protected-namedexpr",
        ),
        pytest.param(
            "nested-safe-before-protected-namedexpr",
            "([first], second) = ([safe], (safe := routes))",
            ("first", "second"),
            (None, "get"),
            id="nested-safe-before-protected-namedexpr",
        ),
    ],
)
def test_consol_simultaneous_local_mapping_assignment_preserves_rhs_identity(
    case_name: str,
    assignment: str,
    observed_mappings: tuple[str, str],
    expected_methods: tuple[Literal["get"] | None, Literal["get"] | None],
) -> None:
    """Each RHS retains its evaluated identity before later RHS effects or target writes."""
    source = 'routes = {"route": app.get}\nsafe = {"route": None}\n' + assignment + "\n"
    expected: list[str] = []
    for index, (mapping, method) in enumerate(
        zip(observed_mappings, expected_methods, strict=True)
    ):
        route = f"/api/v1/paired-identity-{case_name}-{index}"
        source += f'register_{index} = {mapping}["route"]\n'
        source += f'register_{index}("{route}")(handler)\n'
        if method is not None:
            expected.append(
                f"legacy_app.py: unexpected legacy route growth: registration:{method}:{route}"
            )
    assert legacy_guard.validate_legacy_growth(source) == expected


@pytest.mark.parametrize(
    ("case_name", "source", "expected_methods"),
    [
        pytest.param(
            "module-global-safe",
            'alias = {"route": app.get}\nclass Scope:\n    global alias\n    alias = {"route": None}\nregister_0 = {"route": app.get, **alias}["route"]\nregister_0("/api/v1/class-owner-__CASE__-0")(handler)\n',
            (None,),
            id="module-global-safe",
        ),
        pytest.param(
            "global-module-not-function",
            'alias = {"route": app.get}\ndef configure():\n    alias = {"route": app.get}\n    class Scope:\n        global alias\n        alias = {"route": None}\n    return alias\nlocal_result = configure()\nregister_0 = {"route": app.get, **alias}["route"]\nregister_0("/api/v1/class-owner-__CASE__-0")(handler)\nregister_1 = {"route": app.get, **local_result}["route"]\nregister_1("/api/v1/class-owner-__CASE__-1")(handler)\n',
            (None, "get"),
            id="global-module-not-function",
        ),
        pytest.param(
            "global-through-nested-classes",
            'alias = {"route": app.get}\ndef configure():\n    alias = {"route": app.get}\n    class Outer:\n        class Inner:\n            global alias\n            alias = {"route": None}\n    return alias\nlocal_result = configure()\nregister_0 = {"route": app.get, **alias}["route"]\nregister_0("/api/v1/class-owner-__CASE__-0")(handler)\nregister_1 = {"route": app.get, **local_result}["route"]\nregister_1("/api/v1/class-owner-__CASE__-1")(handler)\n',
            (None, "get"),
            id="global-through-nested-classes",
        ),
        pytest.param(
            "nearest-nonlocal-safe",
            'def configure():\n    alias = None\n    routes = {"route": None}\n    class Scope:\n        nonlocal alias\n        ([alias],) = ([routes],)\n    return alias\nresult = configure()\nregister_0 = {"route": app.get, **result}["route"]\nregister_0("/api/v1/class-owner-__CASE__-0")(handler)\n',
            (None,),
            id="nearest-nonlocal-safe",
        ),
        pytest.param(
            "nearest-nonlocal-protected",
            'def configure():\n    alias = {"route": None}\n    routes = {"route": app.get}\n    class Scope:\n        nonlocal alias\n        alias = routes\n    return alias\nresult = configure()\nregister_0 = {"route": app.get, **result}["route"]\nregister_0("/api/v1/class-owner-__CASE__-0")(handler)\n',
            ("get",),
            id="nearest-nonlocal-protected",
        ),
        pytest.param(
            "nested-class-member-is-not-safe-owner",
            'def configure():\n    alias = {"route": app.get}\n    routes = {"route": None}\n    class Outer:\n        alias = {"route": None}\n        class Inner:\n            nonlocal alias\n            alias = routes\n    return alias\nresult = configure()\nregister_0 = {"route": app.get, **result}["route"]\nregister_0("/api/v1/class-owner-__CASE__-0")(handler)\n',
            (None,),
            id="nested-class-member-is-not-safe-owner",
        ),
        pytest.param(
            "nested-class-member-is-not-protected-owner",
            'def configure():\n    alias = {"route": None}\n    routes = {"route": app.get}\n    class Outer:\n        alias = {"route": None}\n        class Inner:\n            nonlocal alias\n            alias = routes\n    return alias\nresult = configure()\nregister_0 = {"route": app.get, **result}["route"]\nregister_0("/api/v1/class-owner-__CASE__-0")(handler)\n',
            ("get",),
            id="nested-class-member-is-not-protected-owner",
        ),
        pytest.param(
            "skip-nonowning-intermediate-function",
            'def outer():\n    alias = {"route": None}\n    def middle():\n        observed_before = alias\n        class Scope:\n            nonlocal alias\n            alias = {"route": app.get}\n    middle()\n    return alias\nresult = outer()\nregister_0 = {"route": app.get, **result}["route"]\nregister_0("/api/v1/class-owner-__CASE__-0")(handler)\n',
            ("get",),
            id="skip-nonowning-intermediate-function",
        ),
        pytest.param(
            "intermediate-genuine-local-owner",
            'def outer():\n    alias = {"route": app.get}\n    def middle():\n        alias = {"route": app.get}\n        class Scope:\n            nonlocal alias\n            alias = {"route": None}\n        return alias\n    inner_result = middle()\n    register_0 = {"route": app.get, **inner_result}["route"]\n    register_0("/api/v1/class-owner-__CASE__-0")(handler)\n    return alias\nresult = outer()\nregister_1 = {"route": app.get, **result}["route"]\nregister_1("/api/v1/class-owner-__CASE__-1")(handler)\n',
            (None, "get"),
            id="intermediate-genuine-local-owner",
        ),
        pytest.param(
            "active-nonlocal-redirect",
            'def outer():\n    alias = {"route": None}\n    def middle():\n        nonlocal alias\n        class Scope:\n            nonlocal alias\n            alias = {"route": app.get}\n        register_0 = {"route": app.get, **alias}["route"]\n        register_0("/api/v1/class-owner-__CASE__-0")(handler)\n    middle()\n    return alias\nresult = outer()\nregister_1 = {"route": app.get, **result}["route"]\nregister_1("/api/v1/class-owner-__CASE__-1")(handler)\n',
            ("get", "get"),
            id="active-nonlocal-redirect",
        ),
        pytest.param(
            "active-global-redirect",
            'alias = {"route": app.get}\ndef outer():\n    alias = {"route": app.get}\n    def middle():\n        global alias\n        class Scope:\n            global alias\n            alias = {"route": None}\n        register_0 = {"route": app.get, **alias}["route"]\n        register_0("/api/v1/class-owner-__CASE__-0")(handler)\n    middle()\n    return alias\nlocal_result = outer()\nregister_1 = {"route": app.get, **alias}["route"]\nregister_1("/api/v1/class-owner-__CASE__-1")(handler)\nregister_2 = {"route": app.get, **local_result}["route"]\nregister_2("/api/v1/class-owner-__CASE__-2")(handler)\n',
            (None, None, "get"),
            id="active-global-redirect",
        ),
        pytest.param(
            "nonlocal-declaration-only-safe",
            'def configure():\n    alias = {"route": None}\n    class Scope:\n        nonlocal alias\n    return alias\nresult = configure()\nregister_0 = {"route": app.get, **result}["route"]\nregister_0("/api/v1/class-owner-__CASE__-0")(handler)\n',
            (None,),
            id="nonlocal-declaration-only-safe",
        ),
        pytest.param(
            "nonlocal-declaration-only-protected",
            'def configure():\n    alias = {"route": app.get}\n    class Scope:\n        nonlocal alias\n    return alias\nresult = configure()\nregister_0 = {"route": app.get, **result}["route"]\nregister_0("/api/v1/class-owner-__CASE__-0")(handler)\n',
            ("get",),
            id="nonlocal-declaration-only-protected",
        ),
        pytest.param(
            "global-declaration-only-protected",
            'alias = {"route": app.get}\nclass Scope:\n    global alias\nregister_0 = {"route": app.get, **alias}["route"]\nregister_0("/api/v1/class-owner-__CASE__-0")(handler)\n',
            ("get",),
            id="global-declaration-only-protected",
        ),
        pytest.param(
            "independent-copy",
            'alias = {"route": None}\ncopied = {**alias}\nclass Scope:\n    global alias\n    alias = {"route": app.get}\nregister_0 = {"route": app.get, **alias}["route"]\nregister_0("/api/v1/class-owner-__CASE__-0")(handler)\nregister_1 = {"route": app.get, **copied}["route"]\nregister_1("/api/v1/class-owner-__CASE__-1")(handler)\n',
            ("get", None),
            id="independent-copy",
        ),
        pytest.param(
            "later-mutation-shared-identity",
            'def configure():\n    alias = None\n    routes = {"route": None}\n    class Scope:\n        nonlocal alias\n        alias = routes\n    alias["route"] = app.get\n    return routes\nresult = configure()\nregister_0 = {"route": app.get, **result}["route"]\nregister_0("/api/v1/class-owner-__CASE__-0")(handler)\n',
            ("dynamic",),
            id="later-mutation-shared-identity",
        ),
        pytest.param(
            "nonlocal-conditional-assignment",
            'def configure():\n    alias = {"route": None}\n    class Scope:\n        nonlocal alias\n        if enabled:\n            alias = {"route": app.get}\n    return alias\nresult = configure()\nregister_0 = {"route": app.get, **result}["route"]\nregister_0("/api/v1/class-owner-__CASE__-0")(handler)\n',
            ("dynamic",),
            id="nonlocal-conditional-assignment",
        ),
        pytest.param(
            "nonlocal-unconditional-deletion",
            'def configure():\n    alias = {"route": app.get}\n    class Scope:\n        nonlocal alias\n        del alias\n    return alias\nresult = configure()\nregister_0 = {"route": app.get, **result}["route"]\nregister_0("/api/v1/class-owner-__CASE__-0")(handler)\n',
            ("dynamic",),
            id="nonlocal-unconditional-deletion",
        ),
        pytest.param(
            "nonlocal-conditional-deletion",
            'def configure():\n    alias = {"route": app.get}\n    class Scope:\n        nonlocal alias\n        if enabled:\n            del alias\n    return alias\nresult = configure()\nregister_0 = {"route": app.get, **result}["route"]\nregister_0("/api/v1/class-owner-__CASE__-0")(handler)\n',
            ("dynamic",),
            id="nonlocal-conditional-deletion",
        ),
        pytest.param(
            "nonlocal-unbound-annotation-owner",
            'def configure():\n    alias: dict\n    class Scope:\n        nonlocal alias\n    return alias\nresult = configure()\nregister_0 = {"route": app.get, **result}["route"]\nregister_0("/api/v1/class-owner-__CASE__-0")(handler)\n',
            ("dynamic",),
            id="nonlocal-unbound-annotation-owner",
        ),
        pytest.param(
            "global-missing-binding-declaration-only",
            'class Scope:\n    global alias\nregister_0 = {"route": app.get, **alias}["route"]\nregister_0("/api/v1/class-owner-__CASE__-0")(handler)\n',
            ("dynamic",),
            id="global-missing-binding-declaration-only",
        ),
        pytest.param(
            "global-unconditional-deletion",
            'alias = {"route": app.get}\nclass Scope:\n    global alias\n    del alias\nregister_0 = {"route": app.get, **alias}["route"]\nregister_0("/api/v1/class-owner-__CASE__-0")(handler)\n',
            ("dynamic",),
            id="global-unconditional-deletion",
        ),
        pytest.param(
            "global-conditional-deletion",
            'alias = {"route": None}\nclass Scope:\n    global alias\n    if enabled:\n        del alias\nregister_0 = {"route": app.get, **alias}["route"]\nregister_0("/api/v1/class-owner-__CASE__-0")(handler)\n',
            ("dynamic",),
            id="global-conditional-deletion",
        ),
        pytest.param(
            "global-conditional-assignment",
            'alias = {"route": None}\nclass Scope:\n    global alias\n    if enabled:\n        alias = {"route": app.get}\nregister_0 = {"route": app.get, **alias}["route"]\nregister_0("/api/v1/class-owner-__CASE__-0")(handler)\n',
            ("dynamic",),
            id="global-conditional-assignment",
        ),
    ],
)
def test_consol_class_outward_binding_uses_genuine_destination(
    case_name: str,
    source: str,
    expected_methods: tuple[Literal["get", "dynamic"] | None, ...],
) -> None:
    """Declarations select actual function/module owners, retaining precise or uncertain values."""
    source = source.replace("__CASE__", case_name)
    expected = [
        "legacy_app.py: unexpected legacy route growth: "
        f"registration:{method}:/api/v1/class-owner-{case_name}-{index}"
        for index, method in enumerate(expected_methods)
        if method is not None
    ]
    assert legacy_guard.validate_legacy_growth(source) == expected


@pytest.mark.parametrize(
    ("case_name", "setup", "body", "expected_bound", "expected_possible", "expected_method"),
    [
        pytest.param(
            "declaration-only-definite-safe",
            'alias = {"route": None}\n',
            "pass",
            True,
            True,
            None,
            id="declaration-only-definite-safe",
        ),
        pytest.param(
            "declaration-only-definite-protected",
            'alias = {"route": app.get}\n',
            "pass",
            True,
            True,
            "get",
            id="declaration-only-definite-protected",
        ),
        pytest.param(
            "declaration-only-possible",
            'if enabled:\n    alias = {"route": None}\n',
            "pass",
            False,
            True,
            "dynamic",
            id="declaration-only-possible",
        ),
        pytest.param(
            "declaration-only-unbound",
            "",
            "pass",
            False,
            False,
            "dynamic",
            id="declaration-only-unbound",
        ),
        pytest.param(
            "unconditional-safe-store",
            "",
            'alias = {"route": None}',
            True,
            True,
            None,
            id="unconditional-safe-store",
        ),
        pytest.param(
            "unconditional-protected-store",
            "",
            'alias = {"route": app.get}',
            True,
            True,
            "get",
            id="unconditional-protected-store",
        ),
        pytest.param(
            "conditional-safe-store",
            "",
            'if enabled:\n    alias = {"route": None}',
            False,
            True,
            "dynamic",
            id="conditional-safe-store",
        ),
        pytest.param(
            "conditional-protected-replacement",
            'alias = {"route": None}\n',
            'if enabled:\n    alias = {"route": app.get}',
            True,
            True,
            "dynamic",
            id="conditional-protected-replacement",
        ),
        pytest.param(
            "unconditional-delete",
            'alias = {"route": app.get}\n',
            "del alias",
            False,
            False,
            "dynamic",
            id="unconditional-delete",
        ),
        pytest.param(
            "conditional-delete",
            'alias = {"route": None}\n',
            "if enabled:\n    del alias",
            False,
            True,
            "dynamic",
            id="conditional-delete",
        ),
    ],
)
def test_consol_class_outward_binding_preserves_module_binding_state(
    case_name: str,
    setup: str,
    body: str,
    expected_bound: bool,
    expected_possible: bool,
    expected_method: Literal["get", "dynamic"] | None,
) -> None:
    """Class global declarations transfer existing fields and actual bound/possible/unbound state."""
    route = f"/api/v1/class-state-{case_name}"
    source = (
        setup
        + "class Scope:\n    global alias\n"
        + textwrap.indent(body, "    ")
        + '\nregister = {"route": app.get, **alias}["route"]\n'
        + f'register("{route}")(handler)\n'
    )
    visitor = legacy_guard._ApiKeyLookupVisitor(
        filename="legacy_app.py",
        errors=[],
        initial_references={"app": "pulseplate.app"},
        analyze_function_bodies=False,
        preserve_route_method_conflicts=True,
    )
    visitor.visit(ast.parse(source))
    assert ("alias" in visitor.scope.bound_names) is expected_bound
    assert ("alias" in visitor.scope.possibly_bound_names) is expected_possible
    assert not any(name == "alias" for _owner, name in visitor._class_direct_member_presence)
    assert visitor.errors == []
    expected = (
        [f"legacy_app.py: unexpected legacy route growth: registration:{expected_method}:{route}"]
        if expected_method is not None
        else []
    )
    assert legacy_guard.validate_legacy_growth(source) == expected


@pytest.mark.parametrize("symbol", (*_CONSOL_OPENAPI_SYMBOLS, "CustomOPENapiHook"))
@pytest.mark.parametrize(
    ("kind", "setup", "lookup"),
    [
        pytest.param("dict-subscript", "", "legacy.__dict__[member]", id="dict-subscript"),
        pytest.param("dict-get", "", "legacy.__dict__.get(member)", id="dict-get"),
        pytest.param("dict-getitem", "", "legacy.__dict__.__getitem__(member)", id="dict-getitem"),
        pytest.param("vars-subscript", "", "vars(legacy)[member]", id="vars-subscript"),
        pytest.param("vars-get", "", "vars(legacy).get(member)", id="vars-get"),
        pytest.param(
            "namespace-alias-subscript",
            "namespace = legacy.__dict__\n",
            "namespace[member]",
            id="namespace-alias-subscript",
        ),
        pytest.param(
            "namespace-alias-get",
            "namespace = vars(legacy)\n",
            "namespace.get(member)",
            id="namespace-alias-get",
        ),
        pytest.param("stored-get", "pick = vars(legacy).get\n", "pick(member)", id="stored-get"),
        pytest.param(
            "stored-getitem",
            "pick = legacy.__dict__.__getitem__\n",
            "pick(member)",
            id="stored-getitem",
        ),
        pytest.param(
            "unbound-dict-get", "", "dict.get(vars(legacy), member)", id="unbound-dict-get"
        ),
        pytest.param(
            "unbound-dict-getitem-vars",
            "",
            "dict.__getitem__(vars(legacy), member)",
            id="unbound-dict-getitem-vars",
        ),
        pytest.param(
            "unbound-dict-getitem-dict",
            "",
            "dict.__getitem__(legacy.__dict__, member)",
            id="unbound-dict-getitem-dict",
        ),
        pytest.param(
            "vars-alias-get", "inspect = vars\n", "inspect(legacy).get(member)", id="vars-alias-get"
        ),
        pytest.param("attribute", "", "legacy.{symbol}", id="attribute"),
        pytest.param("getattr", "", "getattr(legacy, member)", id="getattr"),
        pytest.param("import", "", "", id="import"),
    ],
)
def test_consol_openapi_namespace_lookup_covers_closed_protected_inventory(
    symbol: str, kind: str, setup: str, lookup: str
) -> None:
    """All seven independent names and casefold membership use existing namespace identities."""
    if kind == "import":
        source = f"from legacy_app import {symbol}\n"
        expected = [f"app/main.py: OpenAPI symbol must not be imported through legacy: {symbol}"]
    else:
        source = (
            "import legacy_app as legacy\n"
            + f"member = {symbol!r}\n"
            + setup
            + f"value = {lookup.format(symbol=symbol)}\n"
        )
        expected = ["app/main.py: OpenAPI symbol must not be accessed through legacy"]
    assert _consol_openapi_errors(source) == expected


@pytest.mark.parametrize(
    ("case_name", "source", "forbidden"),
    [
        pytest.param(
            "safe-dict-receiver",
            "import legacy_app as legacy\nclass Other:\n    pass\nother = Other()\nvalue = other.__dict__.get('_install_openapi_builder')\n",
            False,
            id="safe-dict-receiver",
        ),
        pytest.param(
            "shadowed-vars",
            "import legacy_app as legacy\nvars = lambda owner: {'_install_openapi_builder': None}\nvalue = vars(legacy).get('_install_openapi_builder')\n",
            False,
            id="shadowed-vars",
        ),
        pytest.param(
            "shadowed-dict",
            "import legacy_app as legacy\nclass Other:\n    def get(self, owner, member):\n        return None\ndict = Other()\nvalue = dict.get(vars(legacy), '_install_openapi_builder')\n",
            False,
            id="shadowed-dict",
        ),
        pytest.param(
            "safe-stored-callee",
            "import legacy_app as legacy\ndef pick(member):\n    return None\nvalue = pick('_install_openapi_builder')\n",
            False,
            id="safe-stored-callee",
        ),
        pytest.param(
            "safe-stored-method-spelling",
            "import legacy_app as legacy\nclass Other:\n    def get(self, member):\n        return None\nother = Other()\npick = other.get\nvalue = pick('_install_openapi_builder')\n",
            False,
            id="safe-stored-method-spelling",
        ),
        pytest.param(
            "safe-local-member",
            "import legacy_app as legacy\nmember = 'other'\nvalue = legacy.__dict__.get(member)\n",
            False,
            id="safe-local-member",
        ),
        pytest.param(
            "unknown-local-member",
            "import legacy_app as legacy\nmember = external_member()\nvalue = legacy.__dict__.get(member)\n",
            False,
            id="unknown-local-member",
        ),
        pytest.param(
            "api-family-only-member",
            "import legacy_app as legacy\nmember = 'get_api_key'\nvalue = vars(legacy).get(member)\n",
            False,
            id="api-family-only-member",
        ),
        pytest.param(
            "api-possible-family-only",
            "import legacy_app as legacy\nmember = 'get_api_key' if enabled else 'other'\nvalue = vars(legacy).get(member)\n",
            False,
            id="api-possible-family-only",
        ),
        pytest.param(
            "safe-possible-members",
            "import legacy_app as legacy\nmember = 'other' if enabled else 'different'\nvalue = vars(legacy).get(member)\n",
            False,
            id="safe-possible-members",
        ),
        pytest.param(
            "protected-possible-member",
            "import legacy_app as legacy\nmember = '_install_openapi_builder' if enabled else 'other'\nvalue = vars(legacy).get(member)\n",
            True,
            id="protected-possible-member",
        ),
        pytest.param(
            "protected-then-missing-join",
            "import legacy_app as legacy\nif enabled:\n    member = '_install_openapi_builder'\nif delete_member:\n    del member\nvalue = vars(legacy).get(member)\n",
            True,
            id="protected-then-missing-join",
        ),
        pytest.param(
            "possible-legacy-receiver",
            "import legacy_app as legacy\nclass Other:\n    pass\nother = Other()\nreceiver = legacy if enabled else other\nvalue = vars(receiver).get('_install_openapi_builder')\n",
            True,
            id="possible-legacy-receiver",
        ),
        pytest.param(
            "safe-receiver-unknown-member",
            "import legacy_app as legacy\nnamespace = {'_install_openapi_builder': None}\nvalue = namespace.get(external_member())\n",
            False,
            id="safe-receiver-unknown-member",
        ),
        pytest.param(
            "safe-unbound-dict-namespace",
            "import legacy_app as legacy\nnamespace = {'_install_openapi_builder': None}\nvalue = dict.get(namespace, '_install_openapi_builder')\n",
            False,
            id="safe-unbound-dict-namespace",
        ),
        pytest.param(
            "protected-namespace-store-is-blocked",
            "import legacy_app as legacy\nlegacy.__dict__['_install_openapi_builder'] = replacement\n",
            True,
            id="protected-namespace-store-is-blocked",
        ),
        pytest.param(
            "protected-namespace-delete-is-blocked",
            "import legacy_app as legacy\ndel legacy.__dict__['_install_openapi_builder']\n",
            True,
            id="protected-namespace-delete-is-blocked",
        ),
        pytest.param(
            "safe-shadowed-getattr",
            "import legacy_app as legacy\ndef getattr(owner, member):\n    return None\nvalue = getattr(legacy, '_install_openapi_builder')\n",
            False,
            id="safe-shadowed-getattr",
        ),
    ],
)
def test_consol_openapi_namespace_lookup_preserves_independent_controls(
    case_name: str, source: str, forbidden: bool
) -> None:
    """Receiver, callee, member family and Load context remain independent predicates."""
    expected = (
        ["app/main.py: OpenAPI symbol must not be accessed through legacy"] if forbidden else []
    )
    assert _consol_openapi_errors(source) == expected


@pytest.mark.parametrize(
    ("case_name", "source", "forbidden"),
    [
        pytest.param(
            "dict-subscript-safe",
            "import legacy_app as legacy\ndef member():\n    return 'other'\ndef passthrough(value):\n    return value\nvalue = legacy.__dict__[passthrough(member())]\n",
            False,
            id="dict-subscript-safe",
        ),
        pytest.param(
            "dict-subscript-protected",
            "import legacy_app as legacy\ndef member():\n    return '_install_openapi_builder'\ndef passthrough(value):\n    return value\nvalue = legacy.__dict__[passthrough(member())]\n",
            True,
            id="dict-subscript-protected",
        ),
        pytest.param(
            "dict-subscript-unknown",
            "import legacy_app as legacy\ndef member():\n    return external_member()\ndef passthrough(value):\n    return value\nvalue = legacy.__dict__[passthrough(member())]\n",
            False,
            id="dict-subscript-unknown",
        ),
        pytest.param(
            "dict-subscript-possible-protected",
            "import legacy_app as legacy\ndef member():\n    return '_install_openapi_builder' if enabled else 'other'\ndef passthrough(value):\n    return value\nvalue = legacy.__dict__[passthrough(member())]\n",
            True,
            id="dict-subscript-possible-protected",
        ),
        pytest.param(
            "dict-get-safe",
            "import legacy_app as legacy\ndef member():\n    return 'other'\ndef passthrough(value):\n    return value\nvalue = legacy.__dict__.get(passthrough(member()))\n",
            False,
            id="dict-get-safe",
        ),
        pytest.param(
            "dict-get-protected",
            "import legacy_app as legacy\ndef member():\n    return '_install_openapi_builder'\ndef passthrough(value):\n    return value\nvalue = legacy.__dict__.get(passthrough(member()))\n",
            True,
            id="dict-get-protected",
        ),
        pytest.param(
            "dict-get-unknown",
            "import legacy_app as legacy\ndef member():\n    return external_member()\ndef passthrough(value):\n    return value\nvalue = legacy.__dict__.get(passthrough(member()))\n",
            False,
            id="dict-get-unknown",
        ),
        pytest.param(
            "dict-get-possible-protected",
            "import legacy_app as legacy\ndef member():\n    return '_install_openapi_builder' if enabled else 'other'\ndef passthrough(value):\n    return value\nvalue = legacy.__dict__.get(passthrough(member()))\n",
            True,
            id="dict-get-possible-protected",
        ),
        pytest.param(
            "dict-getitem-safe",
            "import legacy_app as legacy\ndef member():\n    return 'other'\ndef passthrough(value):\n    return value\nvalue = legacy.__dict__.__getitem__(passthrough(member()))\n",
            False,
            id="dict-getitem-safe",
        ),
        pytest.param(
            "dict-getitem-protected",
            "import legacy_app as legacy\ndef member():\n    return '_install_openapi_builder'\ndef passthrough(value):\n    return value\nvalue = legacy.__dict__.__getitem__(passthrough(member()))\n",
            True,
            id="dict-getitem-protected",
        ),
        pytest.param(
            "dict-getitem-unknown",
            "import legacy_app as legacy\ndef member():\n    return external_member()\ndef passthrough(value):\n    return value\nvalue = legacy.__dict__.__getitem__(passthrough(member()))\n",
            False,
            id="dict-getitem-unknown",
        ),
        pytest.param(
            "dict-getitem-possible-protected",
            "import legacy_app as legacy\ndef member():\n    return '_install_openapi_builder' if enabled else 'other'\ndef passthrough(value):\n    return value\nvalue = legacy.__dict__.__getitem__(passthrough(member()))\n",
            True,
            id="dict-getitem-possible-protected",
        ),
        pytest.param(
            "vars-get-safe",
            "import legacy_app as legacy\ndef member():\n    return 'other'\ndef passthrough(value):\n    return value\nvalue = vars(legacy).get(passthrough(member()))\n",
            False,
            id="vars-get-safe",
        ),
        pytest.param(
            "vars-get-protected",
            "import legacy_app as legacy\ndef member():\n    return '_install_openapi_builder'\ndef passthrough(value):\n    return value\nvalue = vars(legacy).get(passthrough(member()))\n",
            True,
            id="vars-get-protected",
        ),
        pytest.param(
            "vars-get-unknown",
            "import legacy_app as legacy\ndef member():\n    return external_member()\ndef passthrough(value):\n    return value\nvalue = vars(legacy).get(passthrough(member()))\n",
            False,
            id="vars-get-unknown",
        ),
        pytest.param(
            "vars-get-possible-protected",
            "import legacy_app as legacy\ndef member():\n    return '_install_openapi_builder' if enabled else 'other'\ndef passthrough(value):\n    return value\nvalue = vars(legacy).get(passthrough(member()))\n",
            True,
            id="vars-get-possible-protected",
        ),
        pytest.param(
            "namespace-alias-get-safe",
            "import legacy_app as legacy\ndef member():\n    return 'other'\ndef passthrough(value):\n    return value\nnamespace = vars(legacy)\nvalue = namespace.get(passthrough(member()))\n",
            False,
            id="namespace-alias-get-safe",
        ),
        pytest.param(
            "namespace-alias-get-protected",
            "import legacy_app as legacy\ndef member():\n    return '_install_openapi_builder'\ndef passthrough(value):\n    return value\nnamespace = vars(legacy)\nvalue = namespace.get(passthrough(member()))\n",
            True,
            id="namespace-alias-get-protected",
        ),
        pytest.param(
            "namespace-alias-get-unknown",
            "import legacy_app as legacy\ndef member():\n    return external_member()\ndef passthrough(value):\n    return value\nnamespace = vars(legacy)\nvalue = namespace.get(passthrough(member()))\n",
            False,
            id="namespace-alias-get-unknown",
        ),
        pytest.param(
            "namespace-alias-get-possible-protected",
            "import legacy_app as legacy\ndef member():\n    return '_install_openapi_builder' if enabled else 'other'\ndef passthrough(value):\n    return value\nnamespace = vars(legacy)\nvalue = namespace.get(passthrough(member()))\n",
            True,
            id="namespace-alias-get-possible-protected",
        ),
        pytest.param(
            "stored-get-safe",
            "import legacy_app as legacy\ndef member():\n    return 'other'\ndef passthrough(value):\n    return value\npick = vars(legacy).get\nvalue = pick(passthrough(member()))\n",
            False,
            id="stored-get-safe",
        ),
        pytest.param(
            "stored-get-protected",
            "import legacy_app as legacy\ndef member():\n    return '_install_openapi_builder'\ndef passthrough(value):\n    return value\npick = vars(legacy).get\nvalue = pick(passthrough(member()))\n",
            True,
            id="stored-get-protected",
        ),
        pytest.param(
            "stored-get-unknown",
            "import legacy_app as legacy\ndef member():\n    return external_member()\ndef passthrough(value):\n    return value\npick = vars(legacy).get\nvalue = pick(passthrough(member()))\n",
            False,
            id="stored-get-unknown",
        ),
        pytest.param(
            "stored-get-possible-protected",
            "import legacy_app as legacy\ndef member():\n    return '_install_openapi_builder' if enabled else 'other'\ndef passthrough(value):\n    return value\npick = vars(legacy).get\nvalue = pick(passthrough(member()))\n",
            True,
            id="stored-get-possible-protected",
        ),
        pytest.param(
            "unbound-dict-get-safe",
            "import legacy_app as legacy\ndef member():\n    return 'other'\ndef passthrough(value):\n    return value\nvalue = dict.get(vars(legacy), passthrough(member()))\n",
            False,
            id="unbound-dict-get-safe",
        ),
        pytest.param(
            "unbound-dict-get-protected",
            "import legacy_app as legacy\ndef member():\n    return '_install_openapi_builder'\ndef passthrough(value):\n    return value\nvalue = dict.get(vars(legacy), passthrough(member()))\n",
            True,
            id="unbound-dict-get-protected",
        ),
        pytest.param(
            "unbound-dict-get-unknown",
            "import legacy_app as legacy\ndef member():\n    return external_member()\ndef passthrough(value):\n    return value\nvalue = dict.get(vars(legacy), passthrough(member()))\n",
            False,
            id="unbound-dict-get-unknown",
        ),
        pytest.param(
            "unbound-dict-get-possible-protected",
            "import legacy_app as legacy\ndef member():\n    return '_install_openapi_builder' if enabled else 'other'\ndef passthrough(value):\n    return value\nvalue = dict.get(vars(legacy), passthrough(member()))\n",
            True,
            id="unbound-dict-get-possible-protected",
        ),
        pytest.param(
            "vars-get-nested-receiver-legacy",
            "import legacy_app as legacy\nclass Other:\n    pass\nother = Other()\ndef owner():\n    return legacy\ndef passthrough(value):\n    return value\nvalue = vars(passthrough(owner())).get('_install_openapi_builder')\n",
            True,
            id="vars-get-nested-receiver-legacy",
        ),
        pytest.param(
            "vars-get-nested-receiver-other",
            "import legacy_app as legacy\nclass Other:\n    pass\nother = Other()\ndef owner():\n    return other\ndef passthrough(value):\n    return value\nvalue = vars(passthrough(owner())).get('_install_openapi_builder')\n",
            False,
            id="vars-get-nested-receiver-other",
        ),
        pytest.param(
            "namespace-alias-get-nested-receiver-legacy",
            "import legacy_app as legacy\nclass Other:\n    pass\nother = Other()\ndef owner():\n    return legacy\ndef passthrough(value):\n    return value\nnamespace = vars(passthrough(owner()))\nvalue = namespace.get('_install_openapi_builder')\n",
            True,
            id="namespace-alias-get-nested-receiver-legacy",
        ),
        pytest.param(
            "namespace-alias-get-nested-receiver-other",
            "import legacy_app as legacy\nclass Other:\n    pass\nother = Other()\ndef owner():\n    return other\ndef passthrough(value):\n    return value\nnamespace = vars(passthrough(owner()))\nvalue = namespace.get('_install_openapi_builder')\n",
            False,
            id="namespace-alias-get-nested-receiver-other",
        ),
        pytest.param(
            "stored-get-nested-receiver-legacy",
            "import legacy_app as legacy\nclass Other:\n    pass\nother = Other()\ndef owner():\n    return legacy\ndef passthrough(value):\n    return value\npick = vars(passthrough(owner())).get\nvalue = pick('_install_openapi_builder')\n",
            True,
            id="stored-get-nested-receiver-legacy",
        ),
        pytest.param(
            "stored-get-nested-receiver-other",
            "import legacy_app as legacy\nclass Other:\n    pass\nother = Other()\ndef owner():\n    return other\ndef passthrough(value):\n    return value\npick = vars(passthrough(owner())).get\nvalue = pick('_install_openapi_builder')\n",
            False,
            id="stored-get-nested-receiver-other",
        ),
        pytest.param(
            "unbound-dict-get-nested-receiver-legacy",
            "import legacy_app as legacy\nclass Other:\n    pass\nother = Other()\ndef owner():\n    return legacy\ndef passthrough(value):\n    return value\nvalue = dict.get(vars(passthrough(owner())), '_install_openapi_builder')\n",
            True,
            id="unbound-dict-get-nested-receiver-legacy",
        ),
        pytest.param(
            "unbound-dict-get-nested-receiver-other",
            "import legacy_app as legacy\nclass Other:\n    pass\nother = Other()\ndef owner():\n    return other\ndef passthrough(value):\n    return value\nvalue = dict.get(vars(passthrough(owner())), '_install_openapi_builder')\n",
            False,
            id="unbound-dict-get-nested-receiver-other",
        ),
    ],
)
def test_consol_openapi_namespace_lookup_preserves_nested_call_results(
    case_name: str, source: str, forbidden: bool
) -> None:
    """Known results refine through existing CallResults without turning unknowns into OpenAPI."""
    expected = (
        ["app/main.py: OpenAPI symbol must not be accessed through legacy"] if forbidden else []
    )
    assert _consol_openapi_errors(source) == expected


@pytest.mark.parametrize(
    ("case_name", "source", "forbidden", "postponed"),
    [
        pytest.param(
            "receiver-before-safe-default",
            "import legacy_app as legacy_module\nlegacy = legacy_module\nclass Other:\n    pass\nother = Other()\nvalue = legacy.__dict__.get('_install_openapi_builder', (legacy := other))\n",
            True,
            False,
            id="receiver-before-safe-default",
        ),
        pytest.param(
            "safe-receiver-before-legacy-default",
            "import legacy_app as legacy_module\nlegacy = legacy_module\nclass Other:\n    pass\nother = Other()\nlegacy = other\nvalue = legacy.__dict__.get('_install_openapi_builder', (legacy := legacy_module))\n",
            False,
            False,
            id="safe-receiver-before-legacy-default",
        ),
        pytest.param(
            "member-before-safe-default",
            "import legacy_app as legacy_module\nlegacy = legacy_module\nclass Other:\n    pass\nother = Other()\nmember = '_install_openapi_builder'\nvalue = legacy.__dict__.get(member, (member := 'other'))\n",
            True,
            False,
            id="member-before-safe-default",
        ),
        pytest.param(
            "safe-member-before-protected-default",
            "import legacy_app as legacy_module\nlegacy = legacy_module\nclass Other:\n    pass\nother = Other()\nmember = 'other'\nvalue = legacy.__dict__.get(member, (member := '_install_openapi_builder'))\n",
            False,
            False,
            id="safe-member-before-protected-default",
        ),
        pytest.param(
            "stored-callee-before-safe-default",
            "import legacy_app as legacy_module\nlegacy = legacy_module\nclass Other:\n    pass\nother = Other()\ndef safe(member, default):\n    return None\npick = legacy.__dict__.get\nvalue = pick('_install_openapi_builder', (pick := safe))\n",
            True,
            False,
            id="stored-callee-before-safe-default",
        ),
        pytest.param(
            "safe-stored-callee-before-legacy-default",
            "import legacy_app as legacy_module\nlegacy = legacy_module\nclass Other:\n    pass\nother = Other()\ndef safe(member, default):\n    return None\npick = safe\nvalue = pick('_install_openapi_builder', (pick := legacy.__dict__.get))\n",
            False,
            False,
            id="safe-stored-callee-before-legacy-default",
        ),
        pytest.param(
            "builtin-dict-before-shadow-default",
            "import legacy_app as legacy_module\nlegacy = legacy_module\nclass Other:\n    pass\nother = Other()\nclass SafeDict:\n    def get(self, namespace, member, default):\n        return None\nsafe_dict = SafeDict()\nvalue = dict.get(vars(legacy), '_install_openapi_builder', (dict := safe_dict))\n",
            True,
            False,
            id="builtin-dict-before-shadow-default",
        ),
        pytest.param(
            "shadowed-dict-before-builtin-default",
            "import legacy_app as legacy_module\nlegacy = legacy_module\nclass Other:\n    pass\nother = Other()\nbuiltin_dict = dict\nclass SafeDict:\n    def get(self, namespace, member, default):\n        return None\ndict = SafeDict()\nvalue = dict.get(vars(legacy), '_install_openapi_builder', (dict := builtin_dict))\n",
            False,
            False,
            id="shadowed-dict-before-builtin-default",
        ),
        pytest.param(
            "namespace-callee-before-member-rebind",
            "import legacy_app as legacy_module\nlegacy = legacy_module\nclass Other:\n    pass\nother = Other()\nnamespace = legacy.__dict__\nvalue = namespace.get('_install_openapi_builder' if (namespace := other.__dict__) else '_install_openapi_builder')\n",
            True,
            False,
            id="namespace-callee-before-member-rebind",
        ),
        pytest.param(
            "safe-namespace-callee-before-member-rebind",
            "import legacy_app as legacy_module\nlegacy = legacy_module\nclass Other:\n    pass\nother = Other()\nnamespace = other.__dict__\nvalue = namespace.get('_install_openapi_builder' if (namespace := legacy.__dict__) else '_install_openapi_builder')\n",
            False,
            False,
            id="safe-namespace-callee-before-member-rebind",
        ),
        pytest.param(
            "ordered-before-safe-dict-subscript",
            "import legacy_app as legacy\nvalue = legacy.__dict__['_install_openapi_builder']\nlegacy = object()\n",
            True,
            False,
            id="ordered-before-safe-dict-subscript",
        ),
        pytest.param(
            "ordered-before-safe-dict-get",
            "import legacy_app as legacy\nvalue = legacy.__dict__.get('_install_openapi_builder')\nlegacy = object()\n",
            True,
            False,
            id="ordered-before-safe-dict-get",
        ),
        pytest.param(
            "ordered-before-safe-vars-get",
            "import legacy_app as legacy\nvalue = vars(legacy).get('_install_openapi_builder')\nlegacy = object()\n",
            True,
            False,
            id="ordered-before-safe-vars-get",
        ),
        pytest.param(
            "ordered-before-safe-unbound-dict-get",
            "import legacy_app as legacy\nvalue = dict.get(vars(legacy), '_install_openapi_builder')\nlegacy = object()\n",
            True,
            False,
            id="ordered-before-safe-unbound-dict-get",
        ),
        pytest.param(
            "ordered-before-legacy-dict-subscript",
            "legacy = object()\nvalue = legacy.__dict__['_install_openapi_builder']\nimport legacy_app as legacy\n",
            False,
            False,
            id="ordered-before-legacy-dict-subscript",
        ),
        pytest.param(
            "ordered-before-legacy-dict-get",
            "legacy = object()\nvalue = legacy.__dict__.get('_install_openapi_builder')\nimport legacy_app as legacy\n",
            False,
            False,
            id="ordered-before-legacy-dict-get",
        ),
        pytest.param(
            "ordered-before-legacy-vars-get",
            "legacy = object()\nvalue = vars(legacy).get('_install_openapi_builder')\nimport legacy_app as legacy\n",
            False,
            False,
            id="ordered-before-legacy-vars-get",
        ),
        pytest.param(
            "ordered-before-legacy-unbound-dict-get",
            "legacy = object()\nvalue = dict.get(vars(legacy), '_install_openapi_builder')\nimport legacy_app as legacy\n",
            False,
            False,
            id="ordered-before-legacy-unbound-dict-get",
        ),
        pytest.param(
            "deferred-function-dict-subscript",
            "def lookup():\n    return legacy.__dict__['_install_openapi_builder']\nimport legacy_app as legacy\n",
            True,
            False,
            id="deferred-function-dict-subscript",
        ),
        pytest.param(
            "deferred-function-dict-get",
            "def lookup():\n    return legacy.__dict__.get('_install_openapi_builder')\nimport legacy_app as legacy\n",
            True,
            False,
            id="deferred-function-dict-get",
        ),
        pytest.param(
            "deferred-function-vars-get",
            "def lookup():\n    return vars(legacy).get('_install_openapi_builder')\nimport legacy_app as legacy\n",
            True,
            False,
            id="deferred-function-vars-get",
        ),
        pytest.param(
            "deferred-function-unbound-dict-get",
            "def lookup():\n    return dict.get(vars(legacy), '_install_openapi_builder')\nimport legacy_app as legacy\n",
            True,
            False,
            id="deferred-function-unbound-dict-get",
        ),
        pytest.param(
            "deferred-lambda-dict-subscript",
            "lookup = lambda: legacy.__dict__['_install_openapi_builder']\nimport legacy_app as legacy\n",
            True,
            False,
            id="deferred-lambda-dict-subscript",
        ),
        pytest.param(
            "deferred-lambda-dict-get",
            "lookup = lambda: legacy.__dict__.get('_install_openapi_builder')\nimport legacy_app as legacy\n",
            True,
            False,
            id="deferred-lambda-dict-get",
        ),
        pytest.param(
            "deferred-lambda-vars-get",
            "lookup = lambda: vars(legacy).get('_install_openapi_builder')\nimport legacy_app as legacy\n",
            True,
            False,
            id="deferred-lambda-vars-get",
        ),
        pytest.param(
            "deferred-lambda-unbound-dict-get",
            "lookup = lambda: dict.get(vars(legacy), '_install_openapi_builder')\nimport legacy_app as legacy\n",
            True,
            False,
            id="deferred-lambda-unbound-dict-get",
        ),
        pytest.param(
            "deferred-method-dict-subscript",
            "class Lookup:\n    def value(self):\n        return legacy.__dict__['_install_openapi_builder']\nimport legacy_app as legacy\n",
            True,
            False,
            id="deferred-method-dict-subscript",
        ),
        pytest.param(
            "deferred-method-dict-get",
            "class Lookup:\n    def value(self):\n        return legacy.__dict__.get('_install_openapi_builder')\nimport legacy_app as legacy\n",
            True,
            False,
            id="deferred-method-dict-get",
        ),
        pytest.param(
            "deferred-method-vars-get",
            "class Lookup:\n    def value(self):\n        return vars(legacy).get('_install_openapi_builder')\nimport legacy_app as legacy\n",
            True,
            False,
            id="deferred-method-vars-get",
        ),
        pytest.param(
            "deferred-method-unbound-dict-get",
            "class Lookup:\n    def value(self):\n        return dict.get(vars(legacy), '_install_openapi_builder')\nimport legacy_app as legacy\n",
            True,
            False,
            id="deferred-method-unbound-dict-get",
        ),
        pytest.param(
            "genuine-local-receiver-dict-subscript",
            "import legacy_app as legacy\nclass Other:\n    pass\ndef lookup():\n    legacy = Other()\n    return legacy.__dict__['_install_openapi_builder']\n",
            False,
            False,
            id="genuine-local-receiver-dict-subscript",
        ),
        pytest.param(
            "genuine-local-receiver-dict-get",
            "import legacy_app as legacy\nclass Other:\n    pass\ndef lookup():\n    legacy = Other()\n    return legacy.__dict__.get('_install_openapi_builder')\n",
            False,
            False,
            id="genuine-local-receiver-dict-get",
        ),
        pytest.param(
            "genuine-local-receiver-vars-get",
            "import legacy_app as legacy\nclass Other:\n    pass\ndef lookup():\n    legacy = Other()\n    return vars(legacy).get('_install_openapi_builder')\n",
            False,
            False,
            id="genuine-local-receiver-vars-get",
        ),
        pytest.param(
            "genuine-local-receiver-unbound-dict-get",
            "import legacy_app as legacy\nclass Other:\n    pass\ndef lookup():\n    legacy = Other()\n    return dict.get(vars(legacy), '_install_openapi_builder')\n",
            False,
            False,
            id="genuine-local-receiver-unbound-dict-get",
        ),
        pytest.param(
            "sibling-local-does-not-poison-dict-subscript",
            "import legacy_app as legacy\nclass Other:\n    pass\ndef safe():\n    legacy = Other()\n    return legacy.__dict__['_install_openapi_builder']\ndef protected():\n    return legacy.__dict__['_install_openapi_builder']\n",
            True,
            False,
            id="sibling-local-does-not-poison-dict-subscript",
        ),
        pytest.param(
            "sibling-local-does-not-poison-dict-get",
            "import legacy_app as legacy\nclass Other:\n    pass\ndef safe():\n    legacy = Other()\n    return legacy.__dict__.get('_install_openapi_builder')\ndef protected():\n    return legacy.__dict__.get('_install_openapi_builder')\n",
            True,
            False,
            id="sibling-local-does-not-poison-dict-get",
        ),
        pytest.param(
            "sibling-local-does-not-poison-vars-get",
            "import legacy_app as legacy\nclass Other:\n    pass\ndef safe():\n    legacy = Other()\n    return vars(legacy).get('_install_openapi_builder')\ndef protected():\n    return vars(legacy).get('_install_openapi_builder')\n",
            True,
            False,
            id="sibling-local-does-not-poison-vars-get",
        ),
        pytest.param(
            "sibling-local-does-not-poison-unbound-dict-get",
            "import legacy_app as legacy\nclass Other:\n    pass\ndef safe():\n    legacy = Other()\n    return dict.get(vars(legacy), '_install_openapi_builder')\ndef protected():\n    return dict.get(vars(legacy), '_install_openapi_builder')\n",
            True,
            False,
            id="sibling-local-does-not-poison-unbound-dict-get",
        ),
        pytest.param(
            "nonlocal-receiver-before-safe-dict-subscript",
            "def outer():\n    import legacy_app as legacy\n    def inner():\n        nonlocal legacy\n        value = legacy.__dict__['_install_openapi_builder']\n        legacy = object()\n        return value\n    return inner\n",
            True,
            False,
            id="nonlocal-receiver-before-safe-dict-subscript",
        ),
        pytest.param(
            "nonlocal-receiver-before-safe-dict-get",
            "def outer():\n    import legacy_app as legacy\n    def inner():\n        nonlocal legacy\n        value = legacy.__dict__.get('_install_openapi_builder')\n        legacy = object()\n        return value\n    return inner\n",
            True,
            False,
            id="nonlocal-receiver-before-safe-dict-get",
        ),
        pytest.param(
            "nonlocal-receiver-before-safe-vars-get",
            "def outer():\n    import legacy_app as legacy\n    def inner():\n        nonlocal legacy\n        value = vars(legacy).get('_install_openapi_builder')\n        legacy = object()\n        return value\n    return inner\n",
            True,
            False,
            id="nonlocal-receiver-before-safe-vars-get",
        ),
        pytest.param(
            "nonlocal-receiver-before-safe-unbound-dict-get",
            "def outer():\n    import legacy_app as legacy\n    def inner():\n        nonlocal legacy\n        value = dict.get(vars(legacy), '_install_openapi_builder')\n        legacy = object()\n        return value\n    return inner\n",
            True,
            False,
            id="nonlocal-receiver-before-safe-unbound-dict-get",
        ),
        pytest.param(
            "nonlocal-member-before-safe-dict-subscript",
            "import legacy_app as legacy\ndef outer():\n    member = '_install_openapi_builder'\n    def inner():\n        nonlocal member\n        value = legacy.__dict__[member]\n        member = 'other'\n        return value\n    return inner\n",
            True,
            False,
            id="nonlocal-member-before-safe-dict-subscript",
        ),
        pytest.param(
            "nonlocal-member-before-safe-dict-get",
            "import legacy_app as legacy\ndef outer():\n    member = '_install_openapi_builder'\n    def inner():\n        nonlocal member\n        value = legacy.__dict__.get(member)\n        member = 'other'\n        return value\n    return inner\n",
            True,
            False,
            id="nonlocal-member-before-safe-dict-get",
        ),
        pytest.param(
            "nonlocal-member-before-safe-vars-get",
            "import legacy_app as legacy\ndef outer():\n    member = '_install_openapi_builder'\n    def inner():\n        nonlocal member\n        value = vars(legacy).get(member)\n        member = 'other'\n        return value\n    return inner\n",
            True,
            False,
            id="nonlocal-member-before-safe-vars-get",
        ),
        pytest.param(
            "nonlocal-member-before-safe-unbound-dict-get",
            "import legacy_app as legacy\ndef outer():\n    member = '_install_openapi_builder'\n    def inner():\n        nonlocal member\n        value = dict.get(vars(legacy), member)\n        member = 'other'\n        return value\n    return inner\n",
            True,
            False,
            id="nonlocal-member-before-safe-unbound-dict-get",
        ),
        pytest.param(
            "defining-default-dict-subscript",
            "import legacy_app as legacy\ndef lookup(legacy, value=legacy.__dict__['_install_openapi_builder']):\n    return value\n",
            True,
            False,
            id="defining-default-dict-subscript",
        ),
        pytest.param(
            "defining-default-dict-get",
            "import legacy_app as legacy\ndef lookup(legacy, value=legacy.__dict__.get('_install_openapi_builder')):\n    return value\n",
            True,
            False,
            id="defining-default-dict-get",
        ),
        pytest.param(
            "defining-default-vars-get",
            "import legacy_app as legacy\ndef lookup(legacy, value=vars(legacy).get('_install_openapi_builder')):\n    return value\n",
            True,
            False,
            id="defining-default-vars-get",
        ),
        pytest.param(
            "defining-default-unbound-dict-get",
            "import legacy_app as legacy\ndef lookup(legacy, value=dict.get(vars(legacy), '_install_openapi_builder')):\n    return value\n",
            True,
            False,
            id="defining-default-unbound-dict-get",
        ),
        pytest.param(
            "lambda-defining-default-dict-subscript",
            "import legacy_app as legacy\nlookup = lambda legacy, value=legacy.__dict__['_install_openapi_builder']: value\n",
            True,
            False,
            id="lambda-defining-default-dict-subscript",
        ),
        pytest.param(
            "lambda-defining-default-dict-get",
            "import legacy_app as legacy\nlookup = lambda legacy, value=legacy.__dict__.get('_install_openapi_builder'): value\n",
            True,
            False,
            id="lambda-defining-default-dict-get",
        ),
        pytest.param(
            "lambda-defining-default-vars-get",
            "import legacy_app as legacy\nlookup = lambda legacy, value=vars(legacy).get('_install_openapi_builder'): value\n",
            True,
            False,
            id="lambda-defining-default-vars-get",
        ),
        pytest.param(
            "lambda-defining-default-unbound-dict-get",
            "import legacy_app as legacy\nlookup = lambda legacy, value=dict.get(vars(legacy), '_install_openapi_builder'): value\n",
            True,
            False,
            id="lambda-defining-default-unbound-dict-get",
        ),
        pytest.param(
            "parameter-annotation-active-dict-subscript",
            "import legacy_app as legacy\ndef lookup(value: legacy.__dict__['_install_openapi_builder']):\n    return value\n",
            True,
            False,
            id="parameter-annotation-active-dict-subscript",
        ),
        pytest.param(
            "parameter-annotation-active-dict-get",
            "import legacy_app as legacy\ndef lookup(value: legacy.__dict__.get('_install_openapi_builder')):\n    return value\n",
            True,
            False,
            id="parameter-annotation-active-dict-get",
        ),
        pytest.param(
            "parameter-annotation-active-vars-get",
            "import legacy_app as legacy\ndef lookup(value: vars(legacy).get('_install_openapi_builder')):\n    return value\n",
            True,
            False,
            id="parameter-annotation-active-vars-get",
        ),
        pytest.param(
            "parameter-annotation-active-unbound-dict-get",
            "import legacy_app as legacy\ndef lookup(value: dict.get(vars(legacy), '_install_openapi_builder')):\n    return value\n",
            True,
            False,
            id="parameter-annotation-active-unbound-dict-get",
        ),
        pytest.param(
            "parameter-annotation-postponed-dict-subscript",
            "import legacy_app as legacy\ndef lookup(value: legacy.__dict__['_install_openapi_builder']):\n    return value\n",
            False,
            True,
            id="parameter-annotation-postponed-dict-subscript",
        ),
        pytest.param(
            "parameter-annotation-postponed-dict-get",
            "import legacy_app as legacy\ndef lookup(value: legacy.__dict__.get('_install_openapi_builder')):\n    return value\n",
            False,
            True,
            id="parameter-annotation-postponed-dict-get",
        ),
        pytest.param(
            "parameter-annotation-postponed-vars-get",
            "import legacy_app as legacy\ndef lookup(value: vars(legacy).get('_install_openapi_builder')):\n    return value\n",
            False,
            True,
            id="parameter-annotation-postponed-vars-get",
        ),
        pytest.param(
            "parameter-annotation-postponed-unbound-dict-get",
            "import legacy_app as legacy\ndef lookup(value: dict.get(vars(legacy), '_install_openapi_builder')):\n    return value\n",
            False,
            True,
            id="parameter-annotation-postponed-unbound-dict-get",
        ),
        pytest.param(
            "return-annotation-active-dict-subscript",
            "import legacy_app as legacy\ndef lookup() -> legacy.__dict__['_install_openapi_builder']:\n    pass\n",
            True,
            False,
            id="return-annotation-active-dict-subscript",
        ),
        pytest.param(
            "return-annotation-active-dict-get",
            "import legacy_app as legacy\ndef lookup() -> legacy.__dict__.get('_install_openapi_builder'):\n    pass\n",
            True,
            False,
            id="return-annotation-active-dict-get",
        ),
        pytest.param(
            "return-annotation-active-vars-get",
            "import legacy_app as legacy\ndef lookup() -> vars(legacy).get('_install_openapi_builder'):\n    pass\n",
            True,
            False,
            id="return-annotation-active-vars-get",
        ),
        pytest.param(
            "return-annotation-active-unbound-dict-get",
            "import legacy_app as legacy\ndef lookup() -> dict.get(vars(legacy), '_install_openapi_builder'):\n    pass\n",
            True,
            False,
            id="return-annotation-active-unbound-dict-get",
        ),
        pytest.param(
            "return-annotation-postponed-dict-subscript",
            "import legacy_app as legacy\ndef lookup() -> legacy.__dict__['_install_openapi_builder']:\n    pass\n",
            False,
            True,
            id="return-annotation-postponed-dict-subscript",
        ),
        pytest.param(
            "return-annotation-postponed-dict-get",
            "import legacy_app as legacy\ndef lookup() -> legacy.__dict__.get('_install_openapi_builder'):\n    pass\n",
            False,
            True,
            id="return-annotation-postponed-dict-get",
        ),
        pytest.param(
            "return-annotation-postponed-vars-get",
            "import legacy_app as legacy\ndef lookup() -> vars(legacy).get('_install_openapi_builder'):\n    pass\n",
            False,
            True,
            id="return-annotation-postponed-vars-get",
        ),
        pytest.param(
            "return-annotation-postponed-unbound-dict-get",
            "import legacy_app as legacy\ndef lookup() -> dict.get(vars(legacy), '_install_openapi_builder'):\n    pass\n",
            False,
            True,
            id="return-annotation-postponed-unbound-dict-get",
        ),
    ],
)
def test_consol_openapi_namespace_lookup_preserves_temporal_and_deferred_context(
    case_name: str, source: str, forbidden: bool, postponed: bool
) -> None:
    """Each component retains its evaluation identity and original annotation/scope boundary."""
    expected = (
        ["app/main.py: OpenAPI symbol must not be accessed through legacy"] if forbidden else []
    )
    assert _consol_openapi_errors(source, postponed_annotations=postponed) == expected


@pytest.mark.parametrize("omitted", ["reference", "string"])
@pytest.mark.parametrize(
    "lookup",
    [
        pytest.param("legacy.__dict__['_install_openapi_builder']", id="dict-subscript"),
        pytest.param("legacy.__dict__.get('_install_openapi_builder')", id="dict-get"),
        pytest.param("legacy.__dict__.__getitem__('_install_openapi_builder')", id="dict-getitem"),
        pytest.param("dict.get(vars(legacy), '_install_openapi_builder')", id="unbound-dict-get"),
        pytest.param(
            "dict.__getitem__(vars(legacy), '_install_openapi_builder')",
            id="unbound-dict-getitem",
        ),
    ],
)
def test_consol_openapi_namespace_lookup_requires_own_reference_and_string_snapshots(
    omitted: str, lookup: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    collect = legacy_guard._collect_lexical_binding_snapshots
    removed_nodes: list[int] = []

    def collect_without_own_lookup(tree: ast.Module, **kwargs: Any) -> tuple[
        Mapping[int, Mapping[str, str]],
        Mapping[int, Mapping[str, str]],
        Mapping[int, legacy_guard._ResolvedBinding],
    ]:
        references, strings, results = collect(tree, **kwargs)
        selected = {
            id(statement.value)
            for statement in tree.body
            if isinstance(statement, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "value"
                for target in statement.targets
            )
        }
        removed_nodes.extend(selected)
        if omitted == "reference":
            references = {key: value for key, value in references.items() if key not in selected}
        else:
            strings = {key: value for key, value in strings.items() if key not in selected}
        return references, strings, results

    monkeypatch.setattr(
        legacy_guard, "_collect_lexical_binding_snapshots", collect_without_own_lookup
    )
    source = "import legacy_app as legacy\n" + f"value = {lookup}\n"
    assert _consol_openapi_errors(source) == []
    assert removed_nodes, "the existing collector must acquire the actual lookup before omission"


@pytest.mark.parametrize("marker_family", ["api", "openapi"])
@pytest.mark.parametrize(
    ("setup", "lookup"),
    [
        pytest.param("", "legacy.__dict__[probe_name]", id="dict-subscript"),
        pytest.param("", "legacy.__dict__.get(probe_name)", id="dict-get"),
        pytest.param("", "legacy.__dict__.__getitem__(probe_name)", id="dict-getitem"),
        pytest.param("", "vars(legacy).get(probe_name)", id="vars-get"),
        pytest.param("pick = vars(legacy).get\n", "pick(probe_name)", id="stored-get"),
        pytest.param("", "dict.get(vars(legacy), probe_name)", id="unbound-dict-get"),
        pytest.param("", "dict.__getitem__(vars(legacy), probe_name)", id="unbound-dict-getitem"),
    ],
)
def test_consol_openapi_namespace_lookup_keeps_possible_marker_families_separate(
    marker_family: str, setup: str, lookup: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    marker = (
        legacy_guard._POSSIBLE_API_KEY_SYMBOL
        if marker_family == "api"
        else legacy_guard._POSSIBLE_OPENAPI_SYMBOL
    )
    collect = legacy_guard._collect_lexical_binding_snapshots
    injected_nodes: list[int] = []

    def collect_with_marker(tree: ast.Module, **kwargs: Any) -> tuple[
        Mapping[int, Mapping[str, str]],
        Mapping[int, Mapping[str, str]],
        Mapping[int, legacy_guard._ResolvedBinding],
    ]:
        references, strings, results = collect(tree, **kwargs)
        injected_nodes.extend(strings)
        return (
            references,
            {key: {**values, "probe_name": marker} for key, values in strings.items()},
            results,
        )

    monkeypatch.setattr(legacy_guard, "_collect_lexical_binding_snapshots", collect_with_marker)
    source = "import legacy_app as legacy\nprobe_name = 'other'\n" + setup + f"value = {lookup}\n"
    expected = (
        ["app/main.py: OpenAPI symbol must not be accessed through legacy"]
        if marker_family == "openapi"
        else []
    )
    assert _consol_openapi_errors(source) == expected
    assert injected_nodes


@pytest.mark.parametrize("binding_kind", ["direct", "tuple", "list", "nested"])
@pytest.mark.parametrize(
    ("case_name", "initial", "mutation", "expected_method"),
    [
        pytest.param(
            "update-protected",
            '{"route": None}',
            'routes.update({"route": app.get})',
            "get",
            id="update-protected",
        ),
        pytest.param(
            "update-safe",
            '{"route": app.get}',
            'routes.update({"route": None})',
            None,
            id="update-safe",
        ),
        pytest.param(
            "update-safe-no-change",
            '{"route": None}',
            'routes.update({"route": None})',
            None,
            id="update-safe-no-change",
        ),
        pytest.param(
            "update-other-key",
            '{"route": None}',
            'routes.update({"other": app.get})',
            None,
            id="update-other-key",
        ),
        pytest.param(
            "clear-protected", '{"route": app.get}', "routes.clear()", None, id="clear-protected"
        ),
        pytest.param("clear-safe", '{"route": None}', "routes.clear()", None, id="clear-safe"),
        pytest.param(
            "pop-selected-protected",
            '{"route": app.get, "other": None}',
            'routes.pop("route")',
            None,
            id="pop-selected-protected",
        ),
        pytest.param(
            "pop-other-key",
            '{"route": app.get, "other": None}',
            'routes.pop("other")',
            "get",
            id="pop-other-key",
        ),
        pytest.param(
            "setdefault-existing-safe",
            '{"route": None}',
            'routes.setdefault("route", app.get)',
            None,
            id="setdefault-existing-safe",
        ),
        pytest.param(
            "setdefault-existing-protected",
            '{"route": app.get}',
            'routes.setdefault("route", None)',
            "get",
            id="setdefault-existing-protected",
        ),
        pytest.param(
            "setdefault-new-selected",
            '{"other": None}',
            'routes.setdefault("route", app.get)',
            "get",
            id="setdefault-new-selected",
        ),
        pytest.param(
            "setdefault-other-key",
            '{"route": None}',
            'routes.setdefault("other", app.get)',
            None,
            id="setdefault-other-key",
        ),
    ],
)
def test_consol_paired_pending_mapping_tracks_known_mutation(
    binding_kind: str,
    case_name: str,
    initial: str,
    mutation: str,
    expected_method: Literal["get", "dynamic"] | None,
) -> None:
    """Direct aliases stay precise; unsupported paired mutation sources reject conservatively."""
    assignments = {
        "direct": f"alias = routes\nignored = {mutation}\n",
        "tuple": f"alias, ignored = routes, {mutation}\n",
        "list": f"[alias, ignored] = [routes, {mutation}]\n",
        "nested": f"([alias], ignored) = ([routes], {mutation})\n",
    }
    route = f"/api/v1/paired-known-{binding_kind}-{case_name}"
    source = (
        f"routes = {initial}\n"
        + assignments[binding_kind]
        + 'register = {"route": None, **alias}["route"]\n'
        + f'register("{route}")(handler)\n'
    )
    if binding_kind in {"tuple", "list", "nested"}:
        expected_method = "dynamic"
    expected = (
        [f"legacy_app.py: unexpected legacy route growth: registration:{expected_method}:{route}"]
        if expected_method is not None
        else []
    )
    assert legacy_guard.validate_legacy_growth(source) == expected


@pytest.mark.parametrize("binding_kind", ["direct", "tuple", "list", "nested"])
@pytest.mark.parametrize(
    ("case_name", "initial", "setup", "captured_name", "effect", "expected_method"),
    [
        pytest.param(
            "independent-safe-copy",
            '{"route": None}',
            "copied = {**routes}\n",
            "copied",
            'routes.update({"route": app.get})',
            None,
            id="independent-safe-copy",
        ),
        pytest.param(
            "independent-protected-copy",
            '{"route": app.get}',
            "copied = {**routes}\n",
            "copied",
            'routes.update({"route": None})',
            "get",
            id="independent-protected-copy",
        ),
        pytest.param(
            "different-object-safe",
            '{"route": None}',
            'other = {"route": None}\n',
            "routes",
            'other.update({"route": app.get})',
            None,
            id="different-object-safe",
        ),
        pytest.param(
            "different-object-protected",
            '{"route": app.get}',
            'other = {"route": app.get}\n',
            "routes",
            "other.clear()",
            "get",
            id="different-object-protected",
        ),
        pytest.param(
            "rebind-preserves-protected-object",
            '{"route": app.get}',
            "",
            "routes",
            '(routes := {"route": None})',
            "get",
            id="rebind-preserves-protected-object",
        ),
        pytest.param(
            "rebind-preserves-safe-object",
            '{"route": None}',
            "",
            "routes",
            '(routes := {"route": app.get})',
            None,
            id="rebind-preserves-safe-object",
        ),
    ],
)
def test_consol_paired_pending_mapping_distinguishes_mutation_from_rebinding_and_copies(
    binding_kind: str,
    case_name: str,
    initial: str,
    setup: str,
    captured_name: str,
    effect: str,
    expected_method: Literal["get", "dynamic"] | None,
) -> None:
    """Keep transparent rebinding precise and reject unsupported paired effect sources."""
    assignments = {
        "direct": f"alias = {captured_name}\nignored = {effect}\n",
        "tuple": f"alias, ignored = {captured_name}, {effect}\n",
        "list": f"[alias, ignored] = [{captured_name}, {effect}]\n",
        "nested": f"([alias], ignored) = ([{captured_name}], {effect})\n",
    }
    route = f"/api/v1/paired-identity-effect-{binding_kind}-{case_name}"
    source = (
        f"routes = {initial}\n"
        + setup
        + assignments[binding_kind]
        + 'register = {"route": None, **alias}["route"]\n'
        + f'register("{route}")(handler)\n'
    )
    if binding_kind in {"tuple", "list", "nested"} and case_name in {
        "independent-safe-copy",
        "independent-protected-copy",
        "different-object-safe",
        "different-object-protected",
        "rebind-preserves-safe-object",
    }:
        expected_method = "dynamic"
    expected = (
        [f"legacy_app.py: unexpected legacy route growth: registration:{expected_method}:{route}"]
        if expected_method is not None
        else []
    )
    assert legacy_guard.validate_legacy_growth(source) == expected


@pytest.mark.parametrize(
    ("kind", "definition", "invocation", "expected_flag", "expected_deferred"),
    [
        pytest.param(
            "sync",
            "def mutate():\n    global flag\n    flag = 'after'\n    return 'result'\n",
            "result = mutate()\n",
            "after",
            False,
            id="explicit-sync",
        ),
        pytest.param(
            "async",
            "async def mutate():\n    global flag\n    flag = 'after'\n    return 'result'\n",
            "pending = mutate()\n",
            "before",
            True,
            id="dormant-async-creation",
        ),
        pytest.param(
            "generator",
            "def mutate():\n    global flag\n    flag = 'after'\n    yield 'result'\n",
            "pending = mutate()\n",
            "before",
            True,
            id="dormant-generator-creation",
        ),
        pytest.param(
            "async",
            "async def mutate():\n    global flag\n    flag = 'after'\n    return 'result'\n",
            "import asyncio\nresult = asyncio.run(mutate())\n",
            "after",
            False,
            id="explicit-async-execution",
        ),
        pytest.param(
            "generator",
            "def mutate():\n    global flag\n    flag = 'after'\n    yield 'result'\n",
            "result = next(mutate())\n",
            "after",
            False,
            id="explicit-generator-iteration",
        ),
    ],
)
def test_consol_body_disabled_analysis_preserves_explicit_and_deferred_call_semantics(
    kind: str,
    definition: str,
    invocation: str,
    expected_flag: str,
    expected_deferred: bool,
) -> None:
    """Skipping unused bodies must not erase explicit calls or execute dormant bodies."""
    visitor = legacy_guard._ApiKeyLookupVisitor(
        filename="legacy_app.py", errors=[], analyze_function_bodies=False
    )
    visitor.visit(ast.parse("flag = 'before'\n" + definition))
    assert visitor.scope.strings["flag"] == "before"
    invocation_tree = ast.parse(invocation)
    visitor.visit(invocation_tree)
    assert visitor.scope.strings["flag"] == expected_flag
    assert bool(visitor.scope.resolve_deferred_calls("pending")) is expected_deferred
    assert visitor.errors == []
    if kind == "sync":
        call = cast(ast.Call, cast(ast.Assign, invocation_tree.body[0]).value)
        assert visitor._call_result_bindings[id(call)].string == "result"


@pytest.mark.parametrize("owner_kind", ["global", "nonlocal"])
def test_consol_unused_definition_analysis_isolates_real_outward_owners(owner_kind: str) -> None:
    """A stored closure's real definition scope remains unchanged by detached unused analysis."""
    visitor = legacy_guard._ApiKeyLookupVisitor(filename="legacy_app.py", errors=[])
    if owner_kind == "global":
        source = "flag = 'before'\n" "def helper():\n    global flag\n    flag = 'after'\n"
    else:
        source = (
            "def make():\n    flag = 'before'\n"
            "    def helper():\n        nonlocal flag\n        flag = 'after'\n"
            "    return helper\nhelper = make()\n"
        )
    visitor.visit(ast.parse(source))
    if owner_kind == "global":
        owner = visitor.scope
    else:
        (helper_node,) = visitor.scope.resolve_callables("helper")
        owner = visitor._function_definition_scopes[helper_node]
    before = (
        dict(owner.references),
        dict(owner.strings),
        dict(owner.callables),
        dict(owner.deferred_calls),
        dict(owner.mappings),
        dict(owner.class_references),
        dict(owner.descriptors),
        dict(owner.iterable_elements),
        set(owner.bound_names),
        set(owner.possibly_bound_names),
    )
    assert owner.strings["flag"] == "before"
    visitor.visit(ast.parse("def unused():\n    helper()\n"))
    after = (
        dict(owner.references),
        dict(owner.strings),
        dict(owner.callables),
        dict(owner.deferred_calls),
        dict(owner.mappings),
        dict(owner.class_references),
        dict(owner.descriptors),
        dict(owner.iterable_elements),
        set(owner.bound_names),
        set(owner.possibly_bound_names),
    )
    if owner_kind == "global":
        registered = visitor.scope.resolve_callables("unused")
        assert len(registered) == 1
        assert next(iter(registered)).name == "unused"
        assert "unused" in owner.bound_names
        assert "unused" in owner.possibly_bound_names
        after = (
            {name: value for name, value in after[0].items() if name != "unused"},
            {name: value for name, value in after[1].items() if name != "unused"},
            {name: value for name, value in after[2].items() if name != "unused"},
            {name: value for name, value in after[3].items() if name != "unused"},
            {name: value for name, value in after[4].items() if name != "unused"},
            {name: value for name, value in after[5].items() if name != "unused"},
            {name: value for name, value in after[6].items() if name != "unused"},
            {name: value for name, value in after[7].items() if name != "unused"},
            after[8] - {"unused"},
            after[9] - {"unused"},
        )
    assert after == before
    visitor.visit(ast.parse("helper()\n"))
    assert owner.strings["flag"] == "after"
    assert visitor.errors == []


@pytest.mark.parametrize("invoked", [False, True], ids=["dormant", "invoked"])
@pytest.mark.parametrize(
    ("helper", "execution"),
    [
        pytest.param(
            "async def install(registrar):\n    registrar(handler)\n",
            'asyncio.run(install(app.middleware("http")))',
            id="async-call",
        ),
        pytest.param(
            "async def install(registrar):\n    registrar(handler)\n",
            'pending = install(app.middleware("http"))\nasyncio.run(pending)',
            id="async-alias",
        ),
        pytest.param(
            "def install(registrar):\n    registrar(handler)\n    yield None\n",
            'list(install(app.middleware("http")))',
            id="generator-call",
        ),
        pytest.param(
            "def install(registrar):\n    registrar(handler)\n    yield None\n",
            'pending = install(app.middleware("http"))\nlist(pending)',
            id="generator-alias",
        ),
    ],
)
def test_consol_unused_sync_wrapper_preserves_deferred_body_execution_boundary(
    helper: str, execution: str, invoked: bool
) -> None:
    """A nested sync helper must retain the dormant phase until an actual wrapper call."""
    source = (
        "import asyncio\n\n"
        + helper
        + "\ndef relay():\n"
        + textwrap.indent(execution + "\n", "    ")
        + "\ndef wrapper():\n    relay()\n"
        + ("\nwrapper()\n" if invoked else "")
    )
    expected = (
        ["legacy_app.py: unexpected legacy route growth: registration:middleware:http"]
        if invoked
        else []
    )
    assert legacy_guard.validate_legacy_growth(source) == expected


@pytest.mark.parametrize("family", ["api", "openapi"])
@pytest.mark.parametrize(
    ("setup", "lookup", "forbidden"),
    [
        pytest.param(
            "lookup_type = dict\n",
            "lookup_type.__getitem__(vars(legacy), member)",
            True,
            id="dict-alias",
        ),
        pytest.param(
            "import builtins as builtin_ns\n",
            "builtin_ns.dict.__getitem__(legacy.__dict__, member)",
            True,
            id="builtins-alias",
        ),
        pytest.param(
            "pick = dict.__getitem__\n",
            "pick(vars(legacy), member)",
            True,
            id="stored-unbound-method",
        ),
        pytest.param(
            "class Other:\n    def __getitem__(self, owner, name):\n        return None\n"
            "dict = Other()\n",
            "dict.__getitem__(vars(legacy), member)",
            False,
            id="shadowed-dict",
        ),
        pytest.param(
            "def __getitem__(owner, name):\n    return None\n",
            "__getitem__(vars(legacy), member)",
            False,
            id="shadowed-method-name",
        ),
        pytest.param(
            "other = {member: None}\n",
            "dict.__getitem__(other, member)",
            False,
            id="independent-mapping-receiver",
        ),
        pytest.param(
            "",
            "dict.__getitem__(vars(legacy), 'other')",
            False,
            id="safe-member",
        ),
    ],
)
def test_consol_unbound_dict_getitem_keeps_builtin_receiver_and_member_identity(
    family: Literal["api", "openapi"], setup: str, lookup: str, forbidden: bool
) -> None:
    """Builtin, receiver and member facts independently control the unbound lookup."""
    symbol = "get_api_key" if family == "api" else "_install_openapi_builder"
    source = (
        "import legacy_app as legacy\n" + f"member = {symbol!r}\n" + setup + f"value = {lookup}\n"
    )
    if family == "api":
        expected = (
            [
                "app/routers/example.py: legacy API-key dependency namespace lookup "
                f"is forbidden: {symbol}"
            ]
            if forbidden
            else []
        )
        assert (
            _validate_api_key_dependency_ownership(
                _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
            )
            == expected
        )
    else:
        expected = (
            ["app/main.py: OpenAPI symbol must not be accessed through legacy"] if forbidden else []
        )
        assert _consol_openapi_errors(source) == expected


@pytest.mark.parametrize("symbol", _CONSOL_API_KEY_SYMBOLS)
@pytest.mark.parametrize(
    "pattern",
    [
        pytest.param("{symbol}", id="capture"),
        pytest.param('{{"value": _}} as {symbol}', id="as"),
        pytest.param("[*{symbol}]", id="sequence-star"),
        pytest.param("{{**{symbol}}}", id="mapping-rest"),
    ],
)
def test_consol_api_key_match_captures_reject_full_protected_inventory(
    symbol: str, pattern: str
) -> None:
    source = (
        _CONSOL_GETTER_IMPORTS
        + "match value:\n"
        + f"    case {pattern.format(symbol=symbol)}:\n        pass\n"
    )
    assert _validate_api_key_dependency_ownership(source, {}) == [
        _CONSOL_API_KEY_REBINDING_ERRORS[symbol]
    ]


@pytest.mark.parametrize("symbol", _CONSOL_API_KEY_SYMBOLS)
@pytest.mark.parametrize("scope", ["function", "class"])
@pytest.mark.parametrize(
    "pattern",
    [
        pytest.param("{symbol}", id="capture"),
        pytest.param("[*{symbol}]", id="sequence-star"),
        pytest.param("{{**{symbol}}}", id="mapping-rest"),
    ],
)
def test_consol_api_key_match_captures_keep_nested_local_bindings_local(
    symbol: str, scope: str, pattern: str
) -> None:
    body = "match value:\n" + f"    case {pattern.format(symbol=symbol)}:\n        pass\n"
    declaration = "def local_scope():\n" if scope == "function" else "class LocalScope:\n"
    source = _CONSOL_GETTER_IMPORTS + declaration + textwrap.indent(body, "    ")
    assert _validate_api_key_dependency_ownership(source, {}) == []


@pytest.mark.parametrize(
    "pattern",
    [
        pytest.param("_", id="wildcard"),
        pytest.param("[*_]", id="star-wildcard"),
        pytest.param('{"value": _}', id="mapping-wildcard"),
        pytest.param("safe", id="safe-capture"),
        pytest.param("[*safe]", id="safe-star"),
        pytest.param("{**safe}", id="safe-rest"),
        pytest.param("canonical.get_api_key", id="canonical-value-pattern-load"),
    ],
)
def test_consol_api_key_match_captures_preserve_wildcards_safe_names_and_value_loads(
    pattern: str,
) -> None:
    source = (
        _CONSOL_GETTER_IMPORTS
        + "import app.routers.api_key as canonical\nmatch value:\n"
        + f"    case {pattern}:\n        pass\n"
    )
    assert _validate_api_key_dependency_ownership(source, {}) == []


@pytest.mark.parametrize("symbol", _CONSOL_API_KEY_SYMBOLS)
@pytest.mark.parametrize("location", ["subject", "guard"])
def test_consol_api_key_match_keeps_subject_and_guard_evaluation_visible(
    symbol: str, location: str
) -> None:
    lookup = f"getattr(legacy, {symbol!r})"
    statement = (
        f"match {lookup}:\n    case _:\n        pass\n"
        if location == "subject"
        else f"match value:\n    case _ if {lookup}:\n        pass\n"
    )
    source = "import legacy_app as legacy\n" + statement
    assert _validate_api_key_dependency_ownership(
        _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
    ) == [
        "app/routers/example.py: dynamic legacy API-key dependency lookup "
        f"is forbidden: {symbol}"
    ]


@pytest.mark.parametrize("symbol", _CONSOL_API_KEY_SYMBOLS)
@pytest.mark.parametrize("receiver", ["owner()", "passthrough(owner())"])
@pytest.mark.parametrize("getter", ["getattr", "pick"], ids=["builtin", "stored"])
def test_consol_api_getattr_resolves_nested_receivers_for_full_inventory(
    symbol: str, receiver: str, getter: str
) -> None:
    source = (
        "import legacy_app as legacy\n"
        "def owner():\n    return legacy\n"
        "def passthrough(value):\n    return value\n"
        "pick = getattr\n" + f"value = {getter}({receiver}, {symbol!r})\n"
    )
    assert _validate_api_key_dependency_ownership(
        _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
    ) == [
        "app/routers/example.py: dynamic legacy API-key dependency lookup "
        f"is forbidden: {symbol}"
    ]


@pytest.mark.parametrize(
    ("source", "expected_name"),
    [
        pytest.param(
            "def owner():\n    return object()\nvalue = getattr(owner(), 'get_api_key', None)\n",
            None,
            id="safe-receiver",
        ),
        pytest.param(
            "def owner():\n    return legacy\nvalue = getattr(owner(), 'other')\n",
            None,
            id="safe-member",
        ),
        pytest.param(
            "def owner():\n    return legacy\n"
            "def member():\n    return external_member()\n"
            "value = getattr(owner(), member())\n",
            "<dynamic>",
            id="unknown-member",
        ),
        pytest.param(
            "def owner():\n    return legacy\n"
            "def member():\n    return 'get_api_key' if enabled else 'other'\n"
            "value = getattr(owner(), member())\n",
            "<dynamic>",
            id="possible-member",
        ),
        pytest.param(
            "def owner():\n    return legacy if enabled else object()\n"
            "value = getattr(owner(), 'get_api_key')\n",
            "get_api_key",
            id="possible-receiver",
        ),
        pytest.param(
            "def owner():\n    return legacy\n"
            "getattr = lambda receiver, member: None\n"
            "value = getattr(owner(), 'get_api_key')\n",
            None,
            id="shadowed-getattr",
        ),
        pytest.param(
            "def owner():\n    return legacy\n"
            "def read(value=getattr(owner(), 'get_api_key')):\n    return value\n",
            "get_api_key",
            id="evaluated-function-default",
        ),
        pytest.param(
            "def owner():\n    return object()\n"
            "def read(value=getattr(owner(), 'get_api_key', None)):\n    return value\n",
            None,
            id="safe-function-default",
        ),
    ],
)
def test_consol_api_getattr_nested_receivers_preserve_safe_and_marker_controls(
    source: str, expected_name: str | None
) -> None:
    expected = (
        [
            "app/routers/example.py: dynamic legacy API-key dependency lookup "
            f"is forbidden: {expected_name}"
        ]
        if expected_name is not None
        else []
    )
    assert (
        _validate_api_key_dependency_ownership(
            _CONSOL_GETTER_IMPORTS,
            {"app/routers/example.py": "import legacy_app as legacy\n" + source},
        )
        == expected
    )


@pytest.mark.parametrize(
    ("source", "expected_name"),
    [
        pytest.param(
            "member = 'other'\n"
            "def owner():\n    global member\n    member = 'get_api_key'\n    return legacy\n"
            "value = getattr(owner(), member)\n",
            "get_api_key",
            id="receiver-promotes-later-member",
        ),
        pytest.param(
            "member = 'get_api_key'\n"
            "def owner():\n    global member\n    member = 'other'\n    return legacy\n"
            "value = getattr(owner(), member)\n",
            None,
            id="receiver-clears-later-member",
        ),
        pytest.param(
            "receiver = legacy\n"
            "def member():\n    global receiver\n    receiver = object()\n    return 'get_api_key'\n"
            "value = getattr(receiver, member())\n",
            "get_api_key",
            id="member-clears-earlier-receiver",
        ),
        pytest.param(
            "receiver = object()\n"
            "def member():\n    global receiver\n    receiver = legacy\n    return 'get_api_key'\n"
            "value = getattr(receiver, member())\n",
            None,
            id="member-promotes-earlier-safe-receiver",
        ),
        pytest.param(
            "receiver = legacy\nmember = 'get_api_key'\n"
            "def default():\n    global receiver, member\n"
            "    receiver = object()\n    member = 'other'\n    return None\n"
            "value = getattr(receiver, member, default())\n",
            "get_api_key",
            id="default-clears-earlier-facts",
        ),
        pytest.param(
            "receiver = object()\nmember = 'other'\n"
            "def default():\n    global receiver, member\n"
            "    receiver = legacy\n    member = 'get_api_key'\n    return None\n"
            "value = getattr(receiver, member, default())\n",
            None,
            id="default-promotes-earlier-safe-facts",
        ),
        pytest.param(
            "def owner():\n    return legacy\n"
            "def member():\n    global legacy\n    legacy = object()\n    return 'get_api_key'\n"
            "value = getattr(owner(), member())\n",
            "get_api_key",
            id="receiver-result-before-member-rebind",
        ),
        pytest.param(
            "def owner():\n    return legacy\n"
            "def default():\n    global legacy\n    legacy = object()\n    return None\n"
            "value = getattr(owner(), 'get_api_key', default())\n",
            "get_api_key",
            id="receiver-result-before-default-rebind",
        ),
        pytest.param(
            "pick = getattr\n"
            "def owner():\n    global pick\n"
            "    pick = lambda receiver, member: None\n    return legacy\n"
            "value = pick(owner(), 'get_api_key')\n",
            "get_api_key",
            id="callee-before-receiver-rebind",
        ),
        pytest.param(
            "def pick(receiver, member):\n    return None\n"
            "def owner():\n    global pick\n    pick = getattr\n    return legacy\n"
            "value = pick(owner(), 'get_api_key')\n",
            None,
            id="earlier-shadowed-callee-stays-safe",
        ),
    ],
)
def test_consol_api_getattr_preserves_argument_evaluation_time(
    source: str, expected_name: str | None
) -> None:
    expected = (
        [
            "app/routers/example.py: dynamic legacy API-key dependency lookup "
            f"is forbidden: {expected_name}"
        ]
        if expected_name is not None
        else []
    )
    assert (
        _validate_api_key_dependency_ownership(
            _CONSOL_GETTER_IMPORTS,
            {"app/routers/example.py": "import legacy_app as legacy\n" + source},
        )
        == expected
    )


@pytest.mark.parametrize(
    ("family", "symbol"),
    [
        *[pytest.param("api", symbol, id=f"api-{symbol}") for symbol in _CONSOL_API_KEY_SYMBOLS],
        *[
            pytest.param("openapi", symbol, id=f"openapi-{symbol}")
            for symbol in (*_CONSOL_OPENAPI_SYMBOLS, "CustomOPENapiHook")
        ],
    ],
)
@pytest.mark.parametrize(
    ("kind", "execution"),
    [
        pytest.param("async", "asyncio.run(access(legacy))", id="async-direct"),
        pytest.param("async", "pending = access(legacy)\nasyncio.run(pending)", id="async-pending"),
        pytest.param("generator", "list(access(legacy))", id="generator-direct"),
        pytest.param(
            "generator", "pending = access(legacy)\nlist(pending)", id="generator-pending"
        ),
        pytest.param("sync", "access(legacy)", id="sync-contrast"),
    ],
)
def test_consol_unused_sync_body_records_explicitly_consumed_ownership_helpers(
    family: Literal["api", "openapi"], symbol: str, kind: str, execution: str
) -> None:
    """Explicit source consumption retains argument-sensitive protected ownership evidence."""
    declaration = "async def access(owner):\n" if kind == "async" else "def access(owner):\n"
    operation = "yield" if kind == "generator" else "return"
    source = (
        "import asyncio\nimport legacy_app as legacy\n"
        + declaration
        + f"    {operation} owner.{symbol}\n"
        + "def unused():\n"
        + textwrap.indent(execution + "\n", "    ")
    )
    if family == "api":
        assert _validate_api_key_dependency_ownership(
            _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
        ) == [
            "app/routers/example.py: legacy API-key dependency attribute access "
            f"is forbidden: {symbol}"
        ]
    else:
        assert _consol_openapi_errors(source) == [
            "app/main.py: OpenAPI symbol must not be accessed through legacy"
        ]


@pytest.mark.parametrize("family", ["api", "openapi"])
@pytest.mark.parametrize("kind", ["async", "generator"])
@pytest.mark.parametrize(
    "control",
    ["bare-creation", "independent-receiver", "canonical-owner", "safe-member", "other-family"],
)
def test_consol_ownership_consumption_preserves_creation_receivers_and_symbol_families(
    family: Literal["api", "openapi"], kind: str, control: str
) -> None:
    symbol = "get_api_key" if family == "api" else "_install_openapi_builder"
    setup = ""
    receiver = "legacy"
    if control == "independent-receiver":
        setup = f"class Other:\n    {symbol} = None\nother = Other()\n"
        receiver = "other"
    elif control == "canonical-owner":
        module = "app.routers.api_key" if family == "api" else "app.bootstrap.openapi"
        setup = f"import {module} as canonical\n"
        receiver = "canonical"
    elif control == "safe-member":
        symbol = "__name__"
    elif control == "other-family":
        symbol = "_install_openapi_builder" if family == "api" else "get_api_key"
    declaration = "async def access(owner):\n" if kind == "async" else "def access(owner):\n"
    operation = "yield" if kind == "generator" else "return"
    creation = f"access({receiver})"
    execution = (
        creation
        if control == "bare-creation"
        else f"asyncio.run({creation})" if kind == "async" else f"list({creation})"
    )
    source = (
        "import asyncio\nimport legacy_app as legacy\n"
        + setup
        + declaration
        + f"    {operation} owner.{symbol}\n"
        + "def unused():\n"
        + textwrap.indent(execution + "\n", "    ")
    )
    if family == "api":
        assert (
            _validate_api_key_dependency_ownership(
                _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
            )
            == []
        )
    else:
        assert _consol_openapi_errors(source) == []


@pytest.mark.parametrize("family", ["api", "openapi"])
@pytest.mark.parametrize("protected", [True, False], ids=["protected", "safe"])
@pytest.mark.parametrize("form", ["no-argument-member", "global-receiver", "outer-receiver"])
def test_consol_consumed_ownership_helpers_preserve_strings_and_lexical_receivers(
    family: Literal["api", "openapi"], protected: bool, form: str
) -> None:
    symbol = "get_api_key" if family == "api" else "_install_openapi_builder"
    member = symbol if protected else "other"
    fixtures = {
        "no-argument-member": (
            "import asyncio\nimport legacy_app as legacy\n"
            + f"async def member():\n    return {member!r}\n"
            + "def unused():\n    getattr(legacy, asyncio.run(member()))\n"
        ),
        "global-receiver": (
            "import asyncio\nimport legacy_app as legacy\n"
            "async def access(member):\n    return getattr(legacy, member)\n"
            + f"def unused():\n    asyncio.run(access({member!r}))\n"
        ),
        "outer-receiver": (
            "import asyncio\ndef outer():\n    import legacy_app as legacy\n"
            "    async def access(member):\n        return getattr(legacy, member)\n"
            + f"    def unused():\n        asyncio.run(access({member!r}))\n"
        ),
    }
    source = fixtures[form]
    if family == "api":
        expected = (
            [
                "app/routers/example.py: dynamic legacy API-key dependency lookup "
                f"is forbidden: {symbol}"
            ]
            if protected
            else []
        )
        assert (
            _validate_api_key_dependency_ownership(
                _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
            )
            == expected
        )
    else:
        expected = (
            ["app/main.py: OpenAPI symbol must not be accessed through legacy"] if protected else []
        )
        assert _consol_openapi_errors(source) == expected


@pytest.mark.parametrize(
    ("parent_reference", "current_reference", "masked", "class_only", "member", "expected"),
    [
        pytest.param(None, None, False, False, "ordinary", None, id="missing"),
        pytest.param(
            "vendor.module",
            None,
            False,
            False,
            "ordinary",
            "vendor.module.ordinary",
            id="inherited",
        ),
        pytest.param(
            "legacy_app",
            "vendor.module",
            False,
            False,
            "ordinary",
            "vendor.module.ordinary",
            id="current-alias-overrides-parent",
        ),
        pytest.param("legacy_app", None, True, False, "ordinary", None, id="masked-parent"),
        pytest.param(None, None, True, True, "ordinary", None, id="class-only-raw-absence"),
        pytest.param(
            None,
            legacy_guard._KNOWN_NON_APP_REFERENCE,
            False,
            False,
            "ordinary",
            None,
            id="known-nonapp",
        ),
        pytest.param(
            None,
            legacy_guard._POSSIBLE_APP_REFERENCE,
            False,
            False,
            "get",
            legacy_guard._POSSIBLE_APP_CALL_REFERENCE,
            id="possible-app-route",
        ),
        pytest.param(
            None,
            legacy_guard._POSSIBLE_APP_REFERENCE,
            False,
            False,
            "router",
            legacy_guard._POSSIBLE_ROUTER_REFERENCE,
            id="possible-app-router",
        ),
        pytest.param(
            None,
            legacy_guard._POSSIBLE_APP_REFERENCE,
            False,
            False,
            "ordinary",
            None,
            id="possible-app-unrelated",
        ),
        pytest.param(
            None,
            legacy_guard._POSSIBLE_ROUTER_REFERENCE,
            False,
            False,
            "get",
            legacy_guard._POSSIBLE_APP_CALL_REFERENCE,
            id="possible-router-route",
        ),
        pytest.param(
            None,
            legacy_guard._POSSIBLE_ROUTER_REFERENCE,
            False,
            False,
            "ordinary",
            None,
            id="possible-router-unrelated",
        ),
        pytest.param(
            None,
            "legacy_app",
            False,
            False,
            "get_api_key",
            "legacy_app.get_api_key",
            id="legacy-protected-member",
        ),
        pytest.param(
            None,
            "legacy_app",
            False,
            False,
            "ordinary",
            "legacy_app.ordinary",
            id="legacy-ordinary-member",
        ),
        pytest.param(
            None,
            "pulseplate.app.get",
            False,
            False,
            "__call__",
            "pulseplate.app.get",
            id="registration-call",
        ),
        pytest.param(
            None,
            "vendor.module",
            False,
            False,
            "__call__",
            "vendor.module.__call__",
            id="ordinary-call-member",
        ),
        pytest.param(
            None,
            "pulseplate.app",
            False,
            False,
            "title",
            "pulseplate.app.title",
            id="known-app-ordinary-member",
        ),
    ],
)
def test_consol_simple_attribute_resolution_preserves_actual_scope_meaning(
    parent_reference: str | None,
    current_reference: str | None,
    masked: bool,
    class_only: bool,
    member: str,
    expected: str | None,
) -> None:
    visitor = legacy_guard._ApiKeyLookupVisitor(filename="fixture.py", errors=[])
    parent = visitor.scope
    if parent_reference is not None:
        parent.bind("owner", reference=parent_reference, string=None)
    visitor.scope = legacy_guard._LexicalBindings(
        parent=parent,
        local_names=frozenset({"owner"}) if masked else frozenset(),
        scope_kind="function",
    )
    if current_reference is not None:
        visitor.scope.bind("owner", reference=current_reference, string=None)
    if class_only:
        visitor.scope.bind(
            "owner",
            reference=None,
            string=None,
            class_references=frozenset({"<class:Only:1>"}),
        )
    query = ast.parse(f"owner.{member}", mode="eval").body
    assert visitor._resolve_reference(query) == expected


@pytest.mark.parametrize(
    ("source", "forbidden"),
    [
        pytest.param("import legacy_app as owner\nvalue = owner.get_api_key\n", True, id="legacy"),
        pytest.param(
            "import legacy_app as owner\ndef read():\n    return owner.get_api_key\n",
            True,
            id="inherited-defining-scope",
        ),
        pytest.param(
            "import legacy_app as owner\ndef read(owner):\n    return owner.get_api_key\n",
            False,
            id="masked-parameter",
        ),
        pytest.param(
            "import legacy_app as owner\ndef read():\n"
            "    import app.routers.api_key as owner\n    return owner.get_api_key\n",
            False,
            id="current-canonical-alias",
        ),
        pytest.param(
            "class Other:\n    get_api_key = None\nowner = Other()\n" "value = owner.get_api_key\n",
            False,
            id="independent-instance",
        ),
        pytest.param(
            "import legacy_app as owner\nvalue = owner.__name__\n",
            False,
            id="ordinary-legacy-member",
        ),
        pytest.param(
            "import legacy_app as legacy\nimport app.routers.api_key as canonical\n"
            "owner = legacy if enabled else canonical\nvalue = owner.get_api_key\n",
            True,
            id="possible-legacy-owner",
        ),
    ],
)
def test_consol_simple_attribute_resolution_preserves_ownership_diagnostics(
    source: str, forbidden: bool
) -> None:
    expected = (
        [
            "app/routers/example.py: legacy API-key dependency attribute access "
            "is forbidden: get_api_key"
        ]
        if forbidden
        else []
    )
    assert (
        _validate_api_key_dependency_ownership(
            _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
        )
        == expected
    )


@pytest.mark.parametrize(
    ("family", "symbol"),
    [
        *[pytest.param("api", symbol, id=f"api-{symbol}") for symbol in _CONSOL_API_KEY_SYMBOLS],
        *[
            pytest.param("openapi", symbol, id=f"openapi-{symbol}")
            for symbol in (*_CONSOL_OPENAPI_SYMBOLS, "CustomOPENapiHook")
        ],
    ],
)
@pytest.mark.parametrize("method", ["get", "__getitem__"])
@pytest.mark.parametrize("namespace", ["owner().__dict__", "vars(owner())"])
def test_consol_unbound_returned_namespace_covers_full_ownership_inventory(
    family: Literal["api", "openapi"], symbol: str, method: str, namespace: str
) -> None:
    source = (
        "import legacy_app as legacy\ndef owner():\n    return legacy\n"
        + f"value = dict.{method}({namespace}, {symbol!r})\n"
    )
    if family == "api":
        assert _validate_api_key_dependency_ownership(
            _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
        ) == [
            "app/routers/example.py: legacy API-key dependency namespace lookup "
            f"is forbidden: {symbol}"
        ]
    else:
        assert _consol_openapi_errors(source) == [
            "app/main.py: OpenAPI symbol must not be accessed through legacy"
        ]


@pytest.mark.parametrize("family", ["api", "openapi"])
@pytest.mark.parametrize(
    ("setup", "lookup", "expected_kind"),
    [
        pytest.param(
            "import builtins as bi\n",
            "bi.dict.get(owner().__dict__, member)",
            "protected",
            id="builtin-module-alias",
        ),
        pytest.param(
            "pick = dict.__getitem__\n",
            "pick(vars(owner()), member)",
            "protected",
            id="stored-unbound-method",
        ),
        pytest.param("", "owner().__dict__.get(member)", "protected", id="bound-get-contrast"),
        pytest.param(
            "", "vars(owner()).__getitem__(member)", "protected", id="bound-item-contrast"
        ),
        pytest.param(
            "def namespace():\n    return {{member: None}}\n",
            "dict.get(namespace(), member)",
            "safe",
            id="independent-returned-mapping",
        ),
        pytest.param(
            "import {canonical} as canonical\ndef owner():\n    return canonical\n",
            "dict.__getitem__(vars(owner()), member)",
            "safe",
            id="canonical-returned-owner",
        ),
        pytest.param(
            "class Other:\n    def get(self, namespace, name):\n        return None\ndict = Other()\n",
            "dict.get(owner().__dict__, member)",
            "safe",
            id="shadowed-dict",
        ),
        pytest.param(
            "def pick(namespace, name):\n    return None\n",
            "pick(owner().__dict__, member)",
            "safe",
            id="shadowed-callee",
        ),
        pytest.param("", "dict.__getitem__(vars(owner()), '__name__')", "safe", id="safe-member"),
        pytest.param(
            "member = {symbol!r} if enabled else 'other'\n",
            "dict.get(owner().__dict__, member)",
            "possible",
            id="possible-member",
        ),
        pytest.param(
            "member = {same_marker!r}\n",
            "dict.get(vars(owner()), member)",
            "possible",
            id="same-family-marker",
        ),
        pytest.param(
            "member = {other_marker!r}\n",
            "dict.__getitem__(owner().__dict__, member)",
            "safe",
            id="other-family-marker",
        ),
    ],
)
def test_consol_unbound_returned_namespace_keeps_alias_bound_and_independent_controls(
    family: Literal["api", "openapi"], setup: str, lookup: str, expected_kind: str
) -> None:
    symbol = "get_api_key" if family == "api" else "_install_openapi_builder"
    canonical = "app.routers.api_key" if family == "api" else "app.bootstrap.openapi"
    same_marker = (
        legacy_guard._POSSIBLE_API_KEY_SYMBOL
        if family == "api"
        else legacy_guard._POSSIBLE_OPENAPI_SYMBOL
    )
    other_marker = (
        legacy_guard._POSSIBLE_OPENAPI_SYMBOL
        if family == "api"
        else legacy_guard._POSSIBLE_API_KEY_SYMBOL
    )
    source = (
        "import legacy_app as legacy\ndef owner():\n    return legacy\n"
        + f"member = {symbol!r}\n"
        + setup.format(
            symbol=symbol, canonical=canonical, same_marker=same_marker, other_marker=other_marker
        )
        + f"value = {lookup}\n"
    )
    if family == "api":
        displayed = "<dynamic>" if expected_kind == "possible" else symbol
        expected = (
            [
                "app/routers/example.py: legacy API-key dependency namespace lookup "
                f"is forbidden: {displayed}"
            ]
            if expected_kind != "safe"
            else []
        )
        assert (
            _validate_api_key_dependency_ownership(
                _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
            )
            == expected
        )
    else:
        expected = (
            ["app/main.py: OpenAPI symbol must not be accessed through legacy"]
            if expected_kind != "safe"
            else []
        )
        assert _consol_openapi_errors(source) == expected


@pytest.mark.parametrize(
    ("setup", "lookup", "expected_name"),
    [
        pytest.param(
            "member = 'other'\ndef owner():\n    global member\n"
            "    member = 'get_api_key'\n    return legacy\n",
            "dict.get(owner().__dict__, member)",
            "get_api_key",
            id="receiver-promotes-member",
        ),
        pytest.param(
            "member = 'get_api_key'\ndef owner():\n    global member\n"
            "    member = '__name__'\n    return legacy\n",
            "dict.__getitem__(vars(owner()), member)",
            None,
            id="receiver-clears-member",
        ),
        pytest.param(
            "namespace = vars(legacy)\ndef member():\n    global namespace\n"
            "    namespace = {'get_api_key': None}\n    return 'get_api_key'\n",
            "dict.get(namespace, member())",
            "get_api_key",
            id="member-clears-earlier-namespace",
        ),
        pytest.param(
            "namespace = {'get_api_key': None}\ndef member():\n    global namespace\n"
            "    namespace = vars(legacy)\n    return 'get_api_key'\n",
            "dict.__getitem__(namespace, member())",
            None,
            id="member-promotes-earlier-safe-namespace",
        ),
        pytest.param(
            "namespace = vars(legacy)\nmember = 'get_api_key'\n"
            "def default():\n    global namespace, member\n"
            "    namespace = {'get_api_key': None}\n    member = '__name__'\n    return None\n",
            "dict.get(namespace, member, default())",
            "get_api_key",
            id="get-default-clears-earlier-facts",
        ),
        pytest.param(
            "namespace = {'get_api_key': None}\nmember = '__name__'\n"
            "def default():\n    global namespace, member\n"
            "    namespace = vars(legacy)\n    member = 'get_api_key'\n    return None\n",
            "dict.get(namespace, member, default())",
            None,
            id="get-default-promotes-earlier-safe-facts",
        ),
        pytest.param(
            "pick = dict.get\ndef owner():\n    global pick\n"
            "    pick = lambda namespace, member: None\n    return legacy\n",
            "pick(owner().__dict__, 'get_api_key')",
            "get_api_key",
            id="callee-before-receiver-rebind",
        ),
        pytest.param(
            "def pick(namespace, member):\n    return None\ndef owner():\n    global pick\n"
            "    pick = dict.__getitem__\n    return legacy\n",
            "pick(vars(owner()), 'get_api_key')",
            None,
            id="earlier-shadowed-callee-stays-safe",
        ),
        pytest.param(
            "def unused(namespace):\n    dict.get(namespace, 'get_api_key')\n",
            "None",
            None,
            id="masked-namespace-parameter",
        ),
        pytest.param("", "dict.get(missing_namespace, 'get_api_key')", None, id="missing-receiver"),
    ],
)
def test_consol_unbound_returned_namespace_preserves_evaluation_time(
    setup: str, lookup: str, expected_name: str | None
) -> None:
    source = "import legacy_app as legacy\n" + setup + f"value = {lookup}\n"
    expected = (
        [
            "app/routers/example.py: legacy API-key dependency namespace lookup "
            f"is forbidden: {expected_name}"
        ]
        if expected_name is not None
        else []
    )
    assert (
        _validate_api_key_dependency_ownership(
            _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
        )
        == expected
    )


def test_consol_unbound_returned_namespace_evaluates_effectful_children_once_in_order() -> None:
    source = (
        "import legacy_app as legacy\nsequence = ''\n"
        "def owner():\n    global sequence\n    sequence = sequence + 'r'\n    return legacy\n"
        "def member():\n    global sequence\n    sequence = sequence + 'm'\n    return 'get_api_key'\n"
        "def default():\n    global sequence\n    sequence = sequence + 'd'\n    return None\n"
        "value = dict.get(owner().__dict__, member(), default())\n"
    )
    visitor = legacy_guard._ApiKeyLookupVisitor(
        filename="app/routers/example.py",
        errors=[],
        analyze_function_bodies=False,
        purpose="ownership_audit",
    )
    visitor.visit(ast.parse(source))
    assert visitor.scope.resolve_string("sequence") == "rmd"
    assert visitor.errors == [
        "app/routers/example.py: legacy API-key dependency namespace lookup is forbidden: get_api_key"
    ]


@pytest.mark.parametrize("symbol", _CONSOL_API_KEY_SYMBOLS)
@pytest.mark.parametrize(
    "expression",
    [
        pytest.param("[item for {symbol} in seed]", id="list"),
        pytest.param("{{item for {symbol} in seed}}", id="set"),
        pytest.param("{{item: item for {symbol} in seed}}", id="dict"),
        pytest.param("(item for {symbol} in seed)", id="generator"),
    ],
)
def test_consol_module_comprehension_targets_remain_local(symbol: str, expression: str) -> None:
    """All five protected spellings remain local generator targets, not module rebindings."""
    source = _CONSOL_GETTER_IMPORTS + "seed = (None,)\nitem = None\n"
    source += f"value = {expression.format(symbol=symbol)}\n"
    compile(source, "<comprehension-target-fixture>", "exec")
    assert _validate_api_key_dependency_ownership(source, {}) == []


@pytest.mark.parametrize(
    "expression",
    [
        pytest.param("[[get_api_key for get_api_key in row] for row in rows]", id="nested"),
        pytest.param("[(get_api_key, item) for get_api_key, item in rows]", id="tuple-target"),
        pytest.param("[get_api_key for get_api_key, (item, tail) in rows]", id="nested-target"),
        pytest.param("[get_api_key for get_api_key, *tail in rows]", id="starred-target"),
        pytest.param("[get_api_key for row in rows for get_api_key in row]", id="later-generator"),
        pytest.param("[item for item in (get_api_key,)]", id="iterator-protected-load"),
    ],
)
def test_consol_module_comprehension_nested_targets_and_iterator_load_stay_local(
    expression: str,
) -> None:
    source = _CONSOL_GETTER_IMPORTS + f"rows = ()\nvalue = {expression}\n"
    compile(source, "<nested-comprehension-fixture>", "exec")
    assert _validate_api_key_dependency_ownership(source, {}) == []


@pytest.mark.parametrize("symbol", _CONSOL_API_KEY_SYMBOLS)
@pytest.mark.parametrize(
    "expression",
    [
        pytest.param("[item for item in seed if ({symbol} := None)]", id="condition-walrus"),
        pytest.param("[({symbol} := None) for item in seed]", id="result-walrus"),
    ],
)
def test_consol_module_comprehension_containing_scope_walrus_is_rebinding(
    symbol: str, expression: str
) -> None:
    source = _CONSOL_GETTER_IMPORTS + "seed = (None,)\n"
    source += f"value = {expression.format(symbol=symbol)}\n"
    compile(source, "<containing-scope-walrus-fixture>", "exec")
    assert _validate_api_key_dependency_ownership(source, {}) == [
        _CONSOL_API_KEY_REBINDING_ERRORS[symbol]
    ]


@pytest.mark.parametrize(
    "statement",
    [
        pytest.param("get_api_key = None\n", id="module-assignment"),
        pytest.param("del get_api_key\n", id="module-delete"),
        pytest.param("match None:\n    case get_api_key:\n        pass\n", id="module-match"),
        pytest.param("from unrelated import replacement as get_api_key\n", id="module-import"),
        pytest.param("value = (get_api_key := None)\n", id="outer-walrus"),
        pytest.param("value = {(get_api_key := None) for item in seed}\n", id="set-result"),
        pytest.param("value = {(get_api_key := None): item for item in seed}\n", id="dict-key"),
        pytest.param("value = ((get_api_key := None) for item in seed)\n", id="generator-result"),
    ],
)
def test_consol_module_comprehension_fix_preserves_genuine_module_rebinding(
    statement: str,
) -> None:
    source = _CONSOL_GETTER_IMPORTS + "seed = (None,)\n" + statement
    compile(source, "<genuine-module-rebinding-fixture>", "exec")
    assert _validate_api_key_dependency_ownership(source, {}) == [
        _CONSOL_API_KEY_REBINDING_ERRORS["get_api_key"]
    ]


@pytest.mark.parametrize("symbol", (*_CONSOL_OPENAPI_SYMBOLS, "CustomOPENapiHook"))
@pytest.mark.parametrize(
    "statement",
    [
        pytest.param("legacy.{symbol} = None\n", id="assignment"),
        pytest.param("legacy.{symbol}: object = None\n", id="valued-annotation"),
        pytest.param("legacy.{symbol} += replacement\n", id="augmented-assignment"),
        pytest.param("del legacy.{symbol}\n", id="delete"),
    ],
)
def test_consol_openapi_attribute_targets_cover_protected_inventory(
    symbol: str, statement: str
) -> None:
    """Writes and deletion retain the same finite legacy ownership restriction as reads."""
    source = "import legacy_app as legacy\n" + statement.format(symbol=symbol)
    compile(source, "<openapi-attribute-target-fixture>", "exec")
    assert _consol_openapi_errors(source) == [
        "app/main.py: OpenAPI symbol must not be accessed through legacy"
    ]


@pytest.mark.parametrize(
    "statement",
    [
        pytest.param("legacy.__dict__[member] = None\n", id="assignment"),
        pytest.param("legacy.__dict__[member]: object = None\n", id="valued-annotation"),
        pytest.param("legacy.__dict__[member] += replacement\n", id="augmented-assignment"),
        pytest.param("del legacy.__dict__[member]\n", id="delete"),
    ],
)
def test_consol_openapi_namespace_targets_use_actual_member_evidence(statement: str) -> None:
    source = "import legacy_app as legacy\nmember = '_install_openapi_builder'\n" + statement
    compile(source, "<openapi-namespace-target-fixture>", "exec")
    assert _consol_openapi_errors(source) == [
        "app/main.py: OpenAPI symbol must not be accessed through legacy"
    ]


@pytest.mark.parametrize(
    "source",
    [
        pytest.param("import legacy_app as legacy\nlegacy.other = None\n", id="safe-member"),
        pytest.param(
            "import app.bootstrap.openapi as canonical\ndel canonical._install_openapi_builder\n",
            id="canonical-owner",
        ),
        pytest.param(
            "import legacy_app as legacy\nlegacy = object()\n"
            "legacy._install_openapi_builder += replacement\n",
            id="shadowed-owner",
        ),
        pytest.param(
            "def local(legacy):\n    legacy._install_openapi_builder: object = None\n",
            id="local-parameter",
        ),
        pytest.param("unknown._install_openapi_builder = None\n", id="unknown-owner"),
        pytest.param(
            "import legacy_app as legacy\nlegacy.__dict__[unknown_member] = None\n",
            id="unknown-member",
        ),
    ],
)
def test_consol_openapi_target_controls_preserve_owner_and_member_boundaries(source: str) -> None:
    compile(source, "<openapi-target-control-fixture>", "exec")
    assert _consol_openapi_errors(source) == []


@pytest.mark.parametrize(
    ("source", "expected_count"),
    [
        pytest.param(
            "import legacy_app as legacy\nimport app.bootstrap.openapi as canonical\n"
            "def rhs():\n    global legacy\n    legacy = canonical\n    return None\n"
            "legacy._install_openapi_builder = rhs()\n",
            0,
            id="assignment-rhs-clears-owner-before-target",
        ),
        pytest.param(
            "import legacy_app as genuine\nimport app.bootstrap.openapi as legacy\n"
            "def rhs():\n    global legacy\n    legacy = genuine\n    return None\n"
            "legacy._install_openapi_builder: object = rhs()\n",
            1,
            id="valued-annotation-rhs-promotes-owner-before-target",
        ),
        pytest.param(
            "import legacy_app as legacy\nimport app.bootstrap.openapi as canonical\n"
            "def rhs():\n    global legacy\n    legacy = canonical\n    return None\n"
            "legacy._install_openapi_builder += rhs()\n",
            1,
            id="augmented-target-before-rhs-clears-owner",
        ),
        pytest.param(
            "import legacy_app as genuine\nimport app.bootstrap.openapi as legacy\n"
            "def rhs():\n    global legacy\n    legacy = genuine\n    return None\n"
            "legacy._install_openapi_builder += rhs()\n",
            0,
            id="augmented-safe-target-before-rhs-promotes-owner",
        ),
        pytest.param(
            "import legacy_app as legacy\n"
            "legacy._install_openapi_builder, legacy._build_canonical_openapi = None, None\n",
            2,
            id="tuple-target-leaves",
        ),
        pytest.param(
            "import legacy_app as legacy\n"
            "legacy._install_openapi_builder = legacy._build_canonical_openapi = None\n",
            2,
            id="chained-target-leaves",
        ),
        pytest.param(
            "import legacy_app as legacy\nimport app.bootstrap.openapi as canonical\n"
            "def receiver():\n    global legacy\n    result = legacy\n"
            "    legacy = canonical\n    return result\n"
            "del receiver()._install_openapi_builder, legacy._build_canonical_openapi\n",
            1,
            id="delete-targets-in-order-with-returned-receiver",
        ),
        pytest.param(
            "import legacy_app as legacy\nimport app.bootstrap.openapi as canonical\n"
            "def member():\n    global legacy\n    legacy = canonical\n"
            "    return '_install_openapi_builder'\n"
            "legacy.__dict__[member()] = None\n",
            1,
            id="subscript-receiver-before-member-effect",
        ),
    ],
)
def test_consol_openapi_target_snapshots_preserve_evaluation_order(
    source: str, expected_count: int
) -> None:
    compile(source, "<ordered-openapi-target-fixture>", "exec")
    diagnostic = "app/main.py: OpenAPI symbol must not be accessed through legacy"
    raw_errors: list[str] = []
    legacy_guard._record_main_legacy_openapi_lookups(ast.parse(source), raw_errors)
    assert raw_errors == [diagnostic] * expected_count
    assert _consol_openapi_errors(source) == ([diagnostic] if expected_count else [])


@pytest.mark.parametrize(
    ("target_kind", "omitted_component", "snapshot_kind"),
    [
        pytest.param("attribute", "target", "reference", id="attribute-target-reference"),
        pytest.param("attribute", "target", "string", id="attribute-target-string"),
        pytest.param("subscript", "target", "reference", id="subscript-target-reference"),
        pytest.param("subscript", "target", "string", id="subscript-target-string"),
        pytest.param("subscript", "receiver", "reference", id="subscript-receiver-reference"),
        pytest.param("subscript", "receiver", "string", id="subscript-receiver-string"),
        pytest.param("subscript", "member", "reference", id="subscript-member-reference"),
        pytest.param("subscript", "member", "string", id="subscript-member-string"),
    ],
)
def test_consol_openapi_targets_require_own_leaf_and_component_snapshots(
    target_kind: str,
    omitted_component: str,
    snapshot_kind: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    collect = legacy_guard._collect_lexical_binding_snapshots
    selected_nodes: list[int] = []

    def collect_without_selected_component(tree: ast.Module, **kwargs: Any) -> tuple[
        Mapping[int, Mapping[str, str]],
        Mapping[int, Mapping[str, str]],
        Mapping[int, legacy_guard._ResolvedBinding],
    ]:
        references, strings, results = collect(tree, **kwargs)
        targets = [
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.Attribute, ast.Subscript))
            and isinstance(node.ctx, ast.Store)
            and (
                isinstance(node, ast.Attribute)
                and node.attr == "_install_openapi_builder"
                or isinstance(node, ast.Subscript)
                and isinstance(node.slice, ast.Name)
                and node.slice.id == "target_member"
            )
        ]
        selected = {
            id(
                node
                if omitted_component == "target"
                else (
                    node.value
                    if omitted_component == "receiver"
                    else cast(ast.Subscript, node).slice
                )
            )
            for node in targets
        }
        selected_nodes.extend(selected)
        if snapshot_kind == "reference":
            references = {key: value for key, value in references.items() if key not in selected}
        else:
            strings = {key: value for key, value in strings.items() if key not in selected}
        return references, strings, results

    monkeypatch.setattr(
        legacy_guard, "_collect_lexical_binding_snapshots", collect_without_selected_component
    )
    target = (
        "legacy._install_openapi_builder"
        if target_kind == "attribute"
        else "legacy.__dict__[target_member]"
    )
    source = (
        "import legacy_app as legacy\ntarget_member = '_install_openapi_builder'\n"
        + f"{target} = None\n"
    )
    assert _consol_openapi_errors(source) == []
    assert selected_nodes, "the actual target/component node must be selected for omission"


@pytest.mark.parametrize(
    ("family", "symbol"),
    [
        pytest.param(
            family,
            symbol,
            id=f"{family}-{symbol}",
            marks=pytest.mark.skipif(
                sys.version_info < (3, 12),
                reason="PEP 695 generic declaration syntax requires Python 3.12 or newer",
            ),
        )
        for family, symbols in (
            ("api", _CONSOL_API_KEY_SYMBOLS),
            ("openapi", (*_CONSOL_OPENAPI_SYMBOLS, "CustomOPENapiHook")),
        )
        for symbol in symbols
    ],
)
def test_consol_generic_lazy_bound_covers_full_protected_inventory(
    family: Literal["api", "openapi"], symbol: str
) -> None:
    source = f"import legacy_app as legacy\ndef read[T: legacy.{symbol}]():\n    pass\n"
    compile(source, "<generic-bound-fixture>", "exec")
    if family == "api":
        assert _validate_api_key_dependency_ownership(
            _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
        ) == [
            "app/routers/example.py: legacy API-key dependency attribute access "
            f"is forbidden: {symbol}"
        ]
    else:
        assert _consol_openapi_errors(source) == [
            "app/main.py: OpenAPI symbol must not be accessed through legacy"
        ]


@pytest.mark.parametrize("family", ["api", "openapi"])
@pytest.mark.parametrize("forbidden", [True, False])
@pytest.mark.parametrize(
    "declaration",
    [
        pytest.param(
            declaration,
            id=case_name,
            marks=pytest.mark.skipif(
                sys.version_info < minimum,
                reason=(
                    "PEP 696 type-parameter default syntax requires Python 3.13 or newer"
                    if minimum == (3, 13)
                    else "PEP 695 generic declaration syntax requires Python 3.12 or newer"
                ),
            ),
        )
        for case_name, declaration, minimum in (
            ("function-bound", "def read[T: legacy.{member}]():\n    pass\n", (3, 12)),
            ("async-bound", "async def read[T: legacy.{member}]():\n    pass\n", (3, 12)),
            ("class-bound", "class Read[T: legacy.{member}]:\n    pass\n", (3, 12)),
            (
                "function-constraints",
                "def read[T: (legacy.__name__, legacy.{member})]():\n    pass\n",
                (3, 12),
            ),
            (
                "async-constraints",
                "async def read[T: (legacy.__name__, legacy.{member})]():\n    pass\n",
                (3, 12),
            ),
            (
                "class-constraints",
                "class Read[T: (legacy.__name__, legacy.{member})]:\n    pass\n",
                (3, 12),
            ),
            ("function-default", "def read[T = legacy.{member}]():\n    pass\n", (3, 13)),
            ("async-default", "async def read[T = legacy.{member}]():\n    pass\n", (3, 13)),
            ("class-default", "class Read[T = legacy.{member}]:\n    pass\n", (3, 13)),
            (
                "tuple-parameter-default",
                "def read[*Ts = *tuple[legacy.{member}]]():\n    pass\n",
                (3, 13),
            ),
            (
                "parameter-spec-default",
                "def read[**P = [legacy.{member}]]():\n    pass\n",
                (3, 13),
            ),
        )
    ],
)
def test_consol_generic_lazy_declaration_forms_distinguish_protected_and_safe(
    family: Literal["api", "openapi"], forbidden: bool, declaration: str
) -> None:
    symbol = "get_api_key" if family == "api" else "_install_openapi_builder"
    member = symbol if forbidden else "__name__"
    source = "import legacy_app as legacy\n" + declaration.format(member=member)
    compile(source, "<generic-declaration-fixture>", "exec")
    if family == "api":
        expected = (
            [
                "app/routers/example.py: legacy API-key dependency attribute access "
                f"is forbidden: {symbol}"
            ]
            if forbidden
            else []
        )
        assert (
            _validate_api_key_dependency_ownership(
                _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
            )
            == expected
        )
    else:
        expected = (
            ["app/main.py: OpenAPI symbol must not be accessed through legacy"] if forbidden else []
        )
        assert _consol_openapi_errors(source) == expected


@pytest.mark.parametrize("family", ["api", "openapi"])
@pytest.mark.parametrize(
    ("declaration", "forbidden"),
    [
        pytest.param(
            declaration,
            forbidden,
            id=case_name,
            marks=pytest.mark.skipif(
                sys.version_info < (3, 12),
                reason="PEP 695 generic declaration syntax requires Python 3.12 or newer",
            ),
        )
        for case_name, declaration, forbidden in (
            ("bound-receiver-mask", "def read[legacy: legacy.{symbol}]():\n    pass\n", False),
            (
                "all-declarations-mask-before-lazy-observation",
                "def read[T: legacy.{symbol}, legacy]():\n    pass\n",
                False,
            ),
            (
                "bound-member-mask",
                "member = {symbol!r}\ndef read[member, T: getattr(legacy, member)]():\n    pass\n",
                False,
            ),
            (
                "bound-callee-mask",
                "pick = getattr\ndef read[pick, T: pick(legacy, {symbol!r})]():\n    pass\n",
                False,
            ),
            (
                "annotation-and-return-inside-mask",
                "def read[legacy](value: legacy.{symbol}) -> legacy.{symbol}:\n    pass\n",
                False,
            ),
            (
                "class-base-and-keyword-inside-mask",
                "class Read[legacy](legacy.{symbol}, metaclass=legacy.{symbol}):\n    pass\n",
                False,
            ),
            (
                "function-default-outside-mask",
                "def read[legacy](value=legacy.{symbol}):\n    pass\n",
                True,
            ),
            (
                "function-decorator-outside-mask",
                "@legacy.{symbol}\ndef read[legacy]():\n    pass\n",
                True,
            ),
            (
                "class-decorator-outside-mask",
                "@legacy.{symbol}\nclass Read[legacy]:\n    pass\n",
                True,
            ),
            (
                "unmasked-annotation-still-protected",
                "def read[T](value: legacy.{symbol}):\n    pass\n",
                True,
            ),
        )
    ],
)
def test_consol_generic_parameter_masks_preserve_header_inside_outside_boundaries(
    family: Literal["api", "openapi"], declaration: str, forbidden: bool
) -> None:
    symbol = "get_api_key" if family == "api" else "_install_openapi_builder"
    source = "import legacy_app as legacy\n" + declaration.format(symbol=symbol)
    compile(source, "<generic-header-mask-fixture>", "exec")
    if family == "api":
        expected = (
            [
                "app/routers/example.py: legacy API-key dependency attribute access "
                f"is forbidden: {symbol}"
            ]
            if forbidden
            else []
        )
        assert (
            _validate_api_key_dependency_ownership(
                _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
            )
            == expected
        )
    else:
        expected = (
            ["app/main.py: OpenAPI symbol must not be accessed through legacy"] if forbidden else []
        )
        assert _consol_openapi_errors(source) == expected


@pytest.mark.parametrize("family", ["api", "openapi"])
@pytest.mark.parametrize(
    ("module_owner", "class_owner", "member", "forbidden"),
    [
        pytest.param(
            module_owner,
            class_owner,
            member,
            forbidden,
            id=case_name,
            marks=pytest.mark.skipif(
                sys.version_info < (3, 12),
                reason="PEP 695 generic declaration syntax requires Python 3.12 or newer",
            ),
        )
        for case_name, module_owner, class_owner, member, forbidden in (
            (
                "lazy-header-sees-safe-class-alias",
                "dangerous",
                "canonical",
                "def read[T: owner.{symbol}]():\n    pass\n",
                False,
            ),
            (
                "lazy-header-sees-protected-class-alias",
                "canonical",
                "dangerous",
                "def read[T: owner.{symbol}]():\n    pass\n",
                True,
            ),
            (
                "ordinary-method-excludes-safe-class-alias",
                "dangerous",
                "canonical",
                "def read[T]():\n    return owner.{symbol}\n",
                True,
            ),
            (
                "ordinary-method-excludes-protected-class-alias",
                "canonical",
                "dangerous",
                "def read[T]():\n    return owner.{symbol}\n",
                False,
            ),
        )
    ],
)
def test_consol_generic_class_header_visibility_does_not_leak_to_method_body(
    family: Literal["api", "openapi"],
    module_owner: str,
    class_owner: str,
    member: str,
    forbidden: bool,
) -> None:
    symbol = "get_api_key" if family == "api" else "_install_openapi_builder"
    canonical = "app.routers.api_key" if family == "api" else "app.bootstrap.openapi"
    source = (
        "import legacy_app as dangerous\n"
        + f"import {canonical} as canonical\nowner = {module_owner}\n"
        + f"class Container:\n    owner = {class_owner}\n"
        + textwrap.indent(member.format(symbol=symbol), "    ")
    )
    compile(source, "<generic-class-visibility-fixture>", "exec")
    if family == "api":
        expected = (
            [
                "app/routers/example.py: legacy API-key dependency attribute access "
                f"is forbidden: {symbol}"
            ]
            if forbidden
            else []
        )
        assert (
            _validate_api_key_dependency_ownership(
                _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
            )
            == expected
        )
    else:
        expected = (
            ["app/main.py: OpenAPI symbol must not be accessed through legacy"] if forbidden else []
        )
        assert _consol_openapi_errors(source) == expected


@pytest.mark.parametrize("family", ["api", "openapi"])
@pytest.mark.parametrize(
    "declaration",
    [
        pytest.param(
            declaration,
            id=case_name,
            marks=pytest.mark.skipif(
                sys.version_info < (3, 12),
                reason="PEP 695 generic declaration syntax requires Python 3.12 or newer",
            ),
        )
        for case_name, declaration in (
            ("generic-function-body", "def read[legacy]():\n    return legacy.{symbol}\n"),
            (
                "returned-generic-function-mask",
                "def configure[legacy]():\n    def read():\n        return legacy.{symbol}\n"
                "    return read\nread = configure()\nvalue = read()\n",
            ),
            (
                "generic-method-mask-through-replay",
                "class Container:\n    def read[legacy](self):\n        return legacy.{symbol}\n"
                "value = Container().read()\n",
            ),
            (
                "generic-class-parameter-through-method-replay",
                "class Container[legacy]:\n    def read(self):\n        return legacy.{symbol}\n"
                "value = Container().read()\n",
            ),
        )
    ],
)
def test_consol_generic_parameter_masks_survive_existing_definition_and_replay_capture(
    family: Literal["api", "openapi"], declaration: str
) -> None:
    symbol = "get_api_key" if family == "api" else "_install_openapi_builder"
    source = "import legacy_app as legacy\n" + declaration.format(symbol=symbol)
    compile(source, "<generic-capture-mask-fixture>", "exec")
    if family == "api":
        assert (
            _validate_api_key_dependency_ownership(
                _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
            )
            == []
        )
    else:
        assert _consol_openapi_errors(source) == []


@pytest.mark.parametrize("family", ["api", "openapi"])
@pytest.mark.parametrize(
    ("declaration", "postponed", "forbidden"),
    [
        pytest.param(
            declaration,
            postponed,
            forbidden,
            id=case_name,
            marks=pytest.mark.skipif(
                sys.version_info < (3, 12),
                reason="PEP 695 generic declaration syntax requires Python 3.12 or newer",
            ),
        )
        for case_name, declaration, postponed, forbidden in (
            ("active-annotation", "def read[T](value: legacy.{symbol}):\n    pass\n", False, True),
            (
                "postponed-annotation",
                "def read[T](value: legacy.{symbol}):\n    pass\n",
                True,
                False,
            ),
            ("active-lazy-bound", "def read[T: legacy.{symbol}]():\n    pass\n", False, True),
            ("postponed-lazy-bound", "def read[T: legacy.{symbol}]():\n    pass\n", True, True),
        )
    ],
)
def test_consol_generic_lazy_bounds_keep_postponed_annotation_policy_distinct(
    family: Literal["api", "openapi"], declaration: str, postponed: bool, forbidden: bool
) -> None:
    symbol = "get_api_key" if family == "api" else "_install_openapi_builder"
    source = "import legacy_app as legacy\n" + declaration.format(symbol=symbol)
    if postponed:
        source = "from __future__ import annotations\n" + source
    compile(source, "<generic-postponement-fixture>", "exec")
    if family == "api":
        expected = (
            [
                "app/routers/example.py: legacy API-key dependency attribute access "
                f"is forbidden: {symbol}"
            ]
            if forbidden
            else []
        )
        assert (
            _validate_api_key_dependency_ownership(
                _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
            )
            == expected
        )
    else:
        expected = (
            ["app/main.py: OpenAPI symbol must not be accessed through legacy"] if forbidden else []
        )
        assert _consol_openapi_errors(source) == expected


@pytest.mark.parametrize("family", ["api", "openapi"])
@pytest.mark.parametrize(
    ("marker_kind", "forbidden"),
    [
        pytest.param(
            marker_kind,
            forbidden,
            id=marker_kind,
            marks=pytest.mark.skipif(
                sys.version_info < (3, 13),
                reason="PEP 696 type-parameter default syntax requires Python 3.13 or newer",
            ),
        )
        for marker_kind, forbidden in (
            ("possible", True),
            ("same-family", True),
            ("other-family", False),
        )
    ],
)
def test_consol_generic_lazy_default_retains_closed_symbol_family_markers(
    family: Literal["api", "openapi"], marker_kind: str, forbidden: bool
) -> None:
    symbol = "get_api_key" if family == "api" else "_install_openapi_builder"
    same_marker = (
        legacy_guard._POSSIBLE_API_KEY_SYMBOL
        if family == "api"
        else legacy_guard._POSSIBLE_OPENAPI_SYMBOL
    )
    other_marker = (
        legacy_guard._POSSIBLE_OPENAPI_SYMBOL
        if family == "api"
        else legacy_guard._POSSIBLE_API_KEY_SYMBOL
    )
    member = (
        f"{symbol!r} if enabled else 'other'"
        if marker_kind == "possible"
        else repr(same_marker if marker_kind == "same-family" else other_marker)
    )
    source = (
        "import legacy_app as legacy\n"
        + f"member = {member}\ndef read[T = getattr(legacy, member)]():\n    pass\n"
    )
    compile(source, "<generic-marker-fixture>", "exec")
    if family == "api":
        expected = (
            [
                "app/routers/example.py: dynamic legacy API-key dependency lookup is forbidden: <dynamic>"
            ]
            if forbidden
            else []
        )
        assert (
            _validate_api_key_dependency_ownership(
                _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
            )
            == expected
        )
    else:
        expected = (
            ["app/main.py: OpenAPI symbol must not be accessed through legacy"] if forbidden else []
        )
        assert _consol_openapi_errors(source) == expected


@pytest.mark.parametrize(
    ("parameter", "explicit_call"),
    [
        pytest.param(
            parameter,
            explicit_call,
            id=f"{case_name}-{'explicit' if explicit_call else 'dormant'}",
            marks=pytest.mark.skipif(
                sys.version_info < minimum,
                reason=(
                    "PEP 696 type-parameter default syntax requires Python 3.13 or newer"
                    if minimum == (3, 13)
                    else "PEP 695 generic declaration syntax requires Python 3.12 or newer"
                ),
            ),
        )
        for case_name, parameter, minimum in (
            ("bound", "T: change()", (3, 12)),
            ("default", "T = change()", (3, 13)),
        )
        for explicit_call in (False, True)
    ],
)
def test_consol_generic_lazy_calls_are_dormant_in_ordinary_analysis(
    parameter: str, explicit_call: bool
) -> None:
    source = (
        "import legacy_app as legacy\nimport app.routers.api_key as canonical\n"
        "owner = canonical\nstate = 'unchanged'\n"
        "def change():\n    global owner, state\n    owner = legacy\n"
        "    state = 'changed'\n    return object\n"
        + f"def read[{parameter}]():\n    pass\n"
        + ("change()\n" if explicit_call else "")
    )
    compile(source, "<generic-ordinary-purpose-fixture>", "exec")
    visitor = legacy_guard._ApiKeyLookupVisitor(
        filename="app/routers/example.py", errors=[], analyze_function_bodies=False
    )
    visitor.visit(ast.parse(source))
    assert visitor.scope.resolve_reference("owner") == (
        "legacy_app" if explicit_call else "app.routers.api_key"
    )
    assert visitor.scope.resolve_string("state") == ("changed" if explicit_call else "unchanged")
    assert visitor.errors == []


@pytest.mark.parametrize(
    ("initial_owner", "changed_owner", "expected_reference", "forbidden"),
    [
        pytest.param(
            initial_owner,
            changed_owner,
            expected_reference,
            forbidden,
            id=case_name,
            marks=pytest.mark.skipif(
                sys.version_info < (3, 12),
                reason="PEP 695 generic declaration syntax requires Python 3.12 or newer",
            ),
        )
        for case_name, initial_owner, changed_owner, expected_reference, forbidden in (
            ("sibling-stays-canonical", "canonical", "legacy", "app.bootstrap.openapi", False),
            ("sibling-stays-legacy", "legacy", "canonical", "legacy_app", True),
        )
    ],
)
def test_consol_generic_independent_lazy_audits_do_not_transfer_outward_effects(
    initial_owner: str, changed_owner: str, expected_reference: str, forbidden: bool
) -> None:
    source = (
        "import legacy_app as legacy\nimport app.bootstrap.openapi as canonical\n"
        + f"owner = {initial_owner}\nstate = 'unchanged'\n"
        + "def change():\n    global owner, state\n"
        + f"    owner = {changed_owner}\n    state = 'changed'\n    return object\n"
        + "def read[T: change(), U: owner._install_openapi_builder]():\n    pass\n"
        + "value = owner._install_openapi_builder\n"
    )
    compile(source, "<generic-independent-lazy-fixture>", "exec")
    tree = ast.parse(source)
    references, strings, _results = legacy_guard._collect_lexical_binding_snapshots(
        tree,
        filename="app/main.py",
        initial_references={},
        ownership_family="openapi",
        purpose="ownership_audit",
    )
    receivers = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute) and node.attr == "_install_openapi_builder"
    ]
    assert len(receivers) == 2
    for receiver in receivers:
        assert id(receiver) in references
        assert id(receiver) in strings
        assert references[id(receiver)]["owner"] == expected_reference
        assert strings[id(receiver)]["state"] == "unchanged"
    raw_errors: list[str] = []
    legacy_guard._record_main_legacy_openapi_lookups(tree, raw_errors)
    diagnostic = "app/main.py: OpenAPI symbol must not be accessed through legacy"
    assert raw_errors == ([diagnostic, diagnostic] if forbidden else [])
    assert _consol_openapi_errors(source) == ([diagnostic] if forbidden else [])


@pytest.mark.parametrize(
    "source",
    [
        pytest.param(
            "import legacy_app as legacy\nimport app.bootstrap.openapi as canonical\n"
            "owner = canonical\nstate = 'unchanged'\n"
            "def change():\n    global owner, state\n    owner = legacy\n"
            "    state = 'changed'\n    return object\n"
            "def read[T: (change(), owner._install_openapi_builder)]():\n    pass\n"
            "value = owner._install_openapi_builder\n",
            id="constraint-keeps-internal-order-but-not-outward-effects",
            marks=pytest.mark.skipif(
                sys.version_info < (3, 12),
                reason="PEP 695 generic declaration syntax requires Python 3.12 or newer",
            ),
        )
    ],
)
def test_consol_generic_constraint_tuple_preserves_its_internal_evaluation_order(
    source: str,
) -> None:
    compile(source, "<generic-constraint-order-fixture>", "exec")
    tree = ast.parse(source)
    references, strings, _results = legacy_guard._collect_lexical_binding_snapshots(
        tree,
        filename="app/main.py",
        initial_references={},
        ownership_family="openapi",
        purpose="ownership_audit",
    )
    targets = sorted(
        (
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Attribute) and node.attr == "_install_openapi_builder"
        ),
        key=lambda node: node.lineno,
    )
    assert len(targets) == 2
    assert all(id(node.value) in references and id(node.value) in strings for node in targets)
    assert references[id(targets[0].value)]["owner"] == "legacy_app"
    assert strings[id(targets[0].value)]["state"] == "changed"
    assert references[id(targets[1].value)]["owner"] == "app.bootstrap.openapi"
    assert strings[id(targets[1].value)]["state"] == "unchanged"
    assert _consol_openapi_errors(source) == [
        "app/main.py: OpenAPI symbol must not be accessed through legacy"
    ]


@pytest.mark.parametrize(
    ("omitted_component", "snapshot_kind"),
    [
        pytest.param(
            omitted_component,
            snapshot_kind,
            id=f"{omitted_component}-{snapshot_kind}",
            marks=pytest.mark.skipif(
                sys.version_info < (3, 12),
                reason="PEP 695 generic declaration syntax requires Python 3.12 or newer",
            ),
        )
        for omitted_component in ("lookup", "receiver")
        for snapshot_kind in ("reference", "string")
    ],
)
def test_consol_generic_bound_lookup_requires_its_own_snapshot(
    omitted_component: str, snapshot_kind: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    collect = legacy_guard._collect_lexical_binding_snapshots
    selected_nodes: list[int] = []

    def collect_without_generic_lookup(tree: ast.Module, **kwargs: Any) -> tuple[
        Mapping[int, Mapping[str, str]],
        Mapping[int, Mapping[str, str]],
        Mapping[int, legacy_guard._ResolvedBinding],
    ]:
        references, strings, results = collect(tree, **kwargs)
        selected = {
            id(node if omitted_component == "lookup" else node.value)
            for node in ast.walk(tree)
            if isinstance(node, ast.Attribute) and node.attr == "_install_openapi_builder"
        }
        selected_nodes.extend(selected)
        if snapshot_kind == "reference":
            references = {key: value for key, value in references.items() if key not in selected}
        else:
            strings = {key: value for key, value in strings.items() if key not in selected}
        return references, strings, results

    monkeypatch.setattr(
        legacy_guard, "_collect_lexical_binding_snapshots", collect_without_generic_lookup
    )
    source = (
        "import legacy_app as legacy\ndef read[T: legacy._install_openapi_builder]():\n    pass\n"
    )
    compile(source, "<generic-own-snapshot-fixture>", "exec")
    assert _consol_openapi_errors(source) == []
    assert selected_nodes, "the actual generic lookup/component must be selected for omission"


@pytest.mark.parametrize(
    "family",
    [
        pytest.param(
            family,
            id=family,
            marks=pytest.mark.skipif(
                sys.version_info < (3, 13),
                reason="PEP 696 type-parameter default syntax requires Python 3.13 or newer",
            ),
        )
        for family in ("api", "openapi")
    ],
)
def test_consol_generic_lazy_default_uses_the_declared_receiver_mask(
    family: Literal["api", "openapi"],
) -> None:
    symbol = "get_api_key" if family == "api" else "_install_openapi_builder"
    source = (
        "import legacy_app as legacy\n" + f"def read[legacy, T = legacy.{symbol}]():\n    pass\n"
    )
    compile(source, "<generic-default-mask-fixture>", "exec")
    if family == "api":
        assert (
            _validate_api_key_dependency_ownership(
                _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
            )
            == []
        )
    else:
        assert _consol_openapi_errors(source) == []


@pytest.mark.parametrize(
    ("family", "symbol"),
    [
        *[pytest.param("api", symbol, id=f"api-{symbol}") for symbol in _CONSOL_API_KEY_SYMBOLS],
        *[
            pytest.param("openapi", symbol, id=f"openapi-{symbol}")
            for symbol in (*_CONSOL_OPENAPI_SYMBOLS, "CustomOPENapiHook")
        ],
    ],
)
@pytest.mark.parametrize("method", ["pop", "setdefault"])
def test_consol_namespace_pop_setdefault_reject_full_protected_inventory(
    family: Literal["api", "openapi"], symbol: str, method: str
) -> None:
    source = f"import legacy_app as legacy\nvalue = legacy.__dict__.{method}({symbol!r})\n"
    compile(source, "<namespace-mutating-lookup-fixture>", "exec")
    if family == "api":
        assert _validate_api_key_dependency_ownership(
            _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
        ) == [
            "app/routers/example.py: legacy API-key dependency namespace lookup "
            f"is forbidden: {symbol}"
        ]
    else:
        assert _consol_openapi_errors(source) == [
            "app/main.py: OpenAPI symbol must not be accessed through legacy"
        ]


@pytest.mark.parametrize("family", ["api", "openapi"])
@pytest.mark.parametrize("method", ["pop", "setdefault"])
@pytest.mark.parametrize(
    ("setup", "lookup"),
    [
        pytest.param(
            "namespace = vars(legacy)\npick = namespace.{method}\n",
            "pick({symbol!r}, None)",
            id="stored-bound-method",
        ),
        pytest.param(
            "pick = vars(legacy).{method}\n",
            "pick({symbol!r}, None)",
            id="stored-direct-vars-method",
        ),
        pytest.param(
            "def owner():\n    return legacy\n",
            "dict.{method}(owner().__dict__, {symbol!r}, None)",
            id="unbound-returned-receiver",
        ),
        pytest.param(
            "def owner():\n    return legacy\npick = dict.{method}\n",
            "pick(vars(owner()), {symbol!r}, None)",
            id="stored-unbound-method",
        ),
        pytest.param(
            "import builtins as bi\n",
            "bi.dict.{method}(vars(legacy), {symbol!r}, None)",
            id="builtin-module-alias",
        ),
    ],
)
def test_consol_namespace_pop_setdefault_preserve_supported_alias_and_returned_receivers(
    family: Literal["api", "openapi"], method: str, setup: str, lookup: str
) -> None:
    symbol = "get_api_key" if family == "api" else "_install_openapi_builder"
    source = (
        "import legacy_app as legacy\n"
        + setup.format(method=method)
        + f"value = {lookup.format(method=method, symbol=symbol)}\n"
    )
    compile(source, "<namespace-method-alias-fixture>", "exec")
    if family == "api":
        assert _validate_api_key_dependency_ownership(
            _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
        ) == [
            "app/routers/example.py: legacy API-key dependency namespace lookup "
            f"is forbidden: {symbol}"
        ]
    else:
        assert _consol_openapi_errors(source) == [
            "app/main.py: OpenAPI symbol must not be accessed through legacy"
        ]


@pytest.mark.parametrize("family", ["api", "openapi"])
@pytest.mark.parametrize("method", ["pop", "setdefault"])
@pytest.mark.parametrize(
    ("setup", "lookup"),
    [
        pytest.param("", "legacy.__dict__.{method}('__name__', None)", id="safe-member"),
        pytest.param(
            "namespace = {{{symbol!r}: None}}\n",
            "namespace.{method}({symbol!r}, None)",
            id="unrelated-mapping",
        ),
        pytest.param(
            "class Other:\n    def {method}(self, namespace, name, default):\n"
            "        return None\ndict = Other()\n",
            "dict.{method}(vars(legacy), {symbol!r}, None)",
            id="shadowed-builtin",
        ),
    ],
)
def test_consol_namespace_pop_setdefault_keep_independent_safe_controls(
    family: Literal["api", "openapi"], method: str, setup: str, lookup: str
) -> None:
    symbol = "get_api_key" if family == "api" else "_install_openapi_builder"
    source = (
        "import legacy_app as legacy\n"
        + setup.format(method=method, symbol=symbol)
        + f"value = {lookup.format(method=method, symbol=symbol)}\n"
    )
    compile(source, "<namespace-method-control-fixture>", "exec")
    if family == "api":
        assert (
            _validate_api_key_dependency_ownership(
                _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
            )
            == []
        )
    else:
        assert _consol_openapi_errors(source) == []


@pytest.mark.parametrize("family", ["api", "openapi"])
@pytest.mark.parametrize("method", ["pop", "setdefault"])
@pytest.mark.parametrize("initially_legacy", [True, False])
def test_consol_namespace_pop_setdefault_capture_bound_receiver_before_member_effects(
    family: Literal["api", "openapi"], method: str, initially_legacy: bool
) -> None:
    symbol = "get_api_key" if family == "api" else "_install_openapi_builder"
    initial = "vars(legacy)" if initially_legacy else "{}"
    replacement = "{}" if initially_legacy else "vars(legacy)"
    source = (
        "import legacy_app as legacy\n"
        + f"namespace = {initial}\ndef member():\n    global namespace\n"
        + f"    namespace = {replacement}\n    return {symbol!r}\n"
        + f"value = namespace.{method}(member(), None)\n"
    )
    compile(source, "<namespace-method-ordered-receiver-fixture>", "exec")
    if family == "api":
        expected = (
            [
                "app/routers/example.py: legacy API-key dependency namespace lookup "
                f"is forbidden: {symbol}"
            ]
            if initially_legacy
            else []
        )
        assert (
            _validate_api_key_dependency_ownership(
                _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
            )
            == expected
        )
    else:
        expected = (
            ["app/main.py: OpenAPI symbol must not be accessed through legacy"]
            if initially_legacy
            else []
        )
        assert _consol_openapi_errors(source) == expected


@pytest.mark.parametrize("symbol", _CONSOL_API_KEY_SYMBOLS)
@pytest.mark.parametrize("operation", ["replace", "delete"])
@pytest.mark.parametrize("scope", ["invoked-global", "dormant-global", "invoked-local"])
def test_consol_protected_module_bindings_follow_actual_helper_invocation(
    symbol: str, operation: str, scope: str
) -> None:
    declaration = f"    global {symbol}\n" if scope != "invoked-local" else ""
    mutation = (
        f"    {symbol} = None\n"
        if operation == "replace"
        else (
            (f"    {symbol} = None\n" if scope == "invoked-local" else "") + f"    del {symbol}\n"
        )
    )
    source = (
        _CONSOL_GETTER_IMPORTS
        + "def replace():\n"
        + declaration
        + mutation
        + ("replace()\n" if scope != "dormant-global" else "")
    )
    compile(source, "<protected-binding-helper-fixture>", "exec")
    expected = [_CONSOL_API_KEY_REBINDING_ERRORS[symbol]] if scope == "invoked-global" else []
    assert _validate_api_key_dependency_ownership(source, {}) == expected


@pytest.mark.parametrize(
    ("definition", "invocation", "forbidden"),
    [
        pytest.param(
            "def replace():\n    global require_app_api_key\n    require_app_api_key = None\n"
            "alias = replace\n",
            "alias()\n",
            True,
            id="direct-call-alias",
        ),
        pytest.param(
            "def replace():\n    global require_app_api_key\n    require_app_api_key = None\n"
            "alias = replace\n",
            "",
            False,
            id="dormant-call-alias",
        ),
        pytest.param(
            "def configure():\n    def replace():\n        global require_app_api_key\n"
            "        require_app_api_key = None\n    replace()\n",
            "configure()\n",
            True,
            id="nested-invoked-global",
        ),
        pytest.param(
            "def configure():\n    require_app_api_key = None\n    def replace():\n"
            "        nonlocal require_app_api_key\n        require_app_api_key = object\n"
            "    replace()\n",
            "configure()\n",
            False,
            id="genuine-nonlocal-owner",
        ),
        pytest.param(
            "class Configuration:\n    def replace(self):\n        global require_app_api_key\n"
            "        require_app_api_key = None\n",
            "Configuration().replace()\n",
            True,
            id="invoked-method-global",
        ),
        pytest.param(
            "class Configuration:\n    def replace(self):\n        global require_app_api_key\n"
            "        require_app_api_key = None\n",
            "",
            False,
            id="dormant-method-global",
        ),
        pytest.param(
            "class Configuration:\n    require_app_api_key = None\n",
            "",
            False,
            id="class-local-binding",
        ),
        pytest.param(
            "def replace():\n    global require_app_api_key\n    require_app_api_key = None\n",
            "class Configuration:\n    replace()\n",
            True,
            id="class-body-invoked-global",
        ),
    ],
)
def test_consol_protected_binding_replay_keeps_supported_outward_and_local_owners_distinct(
    definition: str, invocation: str, forbidden: bool
) -> None:
    source = _CONSOL_GETTER_IMPORTS + definition + invocation
    compile(source, "<protected-binding-supported-call-fixture>", "exec")
    expected = [_CONSOL_API_KEY_REBINDING_ERRORS["require_app_api_key"]] if forbidden else []
    assert _validate_api_key_dependency_ownership(source, {}) == expected


@pytest.mark.parametrize(
    ("family", "symbol"),
    [
        *[pytest.param("api", symbol, id=f"api-{symbol}") for symbol in _CONSOL_API_KEY_SYMBOLS],
        *[
            pytest.param("openapi", symbol, id=f"openapi-{symbol}")
            for symbol in (*_CONSOL_OPENAPI_SYMBOLS, "CustomOPENapiHook")
        ],
    ],
)
@pytest.mark.parametrize("method", ["pop", "setdefault"])
def test_consol_stored_direct_vars_methods_cover_full_protected_inventory(
    family: Literal["api", "openapi"], symbol: str, method: str
) -> None:
    source = (
        "import legacy_app as legacy\n"
        + f"pick = vars(legacy).{method}\nvalue = pick({symbol!r}, None)\n"
    )
    compile(source, "<stored-direct-vars-method-fixture>", "exec")
    if family == "api":
        assert _validate_api_key_dependency_ownership(
            _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
        ) == [
            "app/routers/example.py: legacy API-key dependency namespace lookup "
            f"is forbidden: {symbol}"
        ]
    else:
        assert _consol_openapi_errors(source) == [
            "app/main.py: OpenAPI symbol must not be accessed through legacy"
        ]


@pytest.mark.parametrize("family", ["api", "openapi"])
@pytest.mark.parametrize("method", ["pop", "setdefault"])
@pytest.mark.parametrize("control", ["safe-member", "unrelated-receiver", "shadowed-vars"])
def test_consol_stored_direct_vars_methods_keep_real_provenance_controls(
    family: Literal["api", "openapi"], method: str, control: str
) -> None:
    symbol = "get_api_key" if family == "api" else "_install_openapi_builder"
    canonical = "app.routers.api_key" if family == "api" else "app.bootstrap.openapi"
    setup = "import legacy_app as legacy\n"
    if control == "unrelated-receiver":
        setup += f"import {canonical} as legacy\n"
    elif control == "shadowed-vars":
        setup += f"def vars(receiver):\n    return {{{symbol!r}: None}}\n"
    member = "__name__" if control == "safe-member" else symbol
    source = setup + f"pick = vars(legacy).{method}\nvalue = pick({member!r}, None)\n"
    compile(source, "<stored-vars-independent-control-fixture>", "exec")
    if family == "api":
        assert (
            _validate_api_key_dependency_ownership(
                _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
            )
            == []
        )
    else:
        assert _consol_openapi_errors(source) == []


@pytest.mark.parametrize("family", ["api", "openapi"])
@pytest.mark.parametrize("method", ["get", "__getitem__"])
def test_consol_stored_direct_vars_getter_siblings_retain_provenance(
    family: Literal["api", "openapi"], method: str
) -> None:
    symbol = "get_api_key" if family == "api" else "_install_openapi_builder"
    source = (
        "import legacy_app as legacy\n"
        + f"pick = vars(legacy).{method}\nvalue = pick({symbol!r})\n"
    )
    compile(source, "<stored-vars-getter-sibling-fixture>", "exec")
    if family == "api":
        assert _validate_api_key_dependency_ownership(
            _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
        ) == [
            "app/routers/example.py: legacy API-key dependency namespace lookup "
            f"is forbidden: {symbol}"
        ]
    else:
        assert _consol_openapi_errors(source) == [
            "app/main.py: OpenAPI symbol must not be accessed through legacy"
        ]


@pytest.mark.parametrize("symbol", (*_CONSOL_OPENAPI_SYMBOLS, "CustomOPENapiHook"))
@pytest.mark.parametrize("method", ["setattr", "delattr"])
def test_consol_openapi_builtin_mutations_cover_full_protected_inventory(
    symbol: str, method: str
) -> None:
    arguments = f"legacy, {symbol!r}" + (", None" if method == "setattr" else "")
    source = "import legacy_app as legacy\n" + f"{method}({arguments})\n"
    compile(source, "<openapi-builtin-mutation-fixture>", "exec")
    assert _consol_openapi_errors(source) == [
        "app/main.py: OpenAPI symbol must not be accessed through legacy"
    ]


@pytest.mark.parametrize("method", ["setattr", "delattr"])
@pytest.mark.parametrize("form", ["qualified", "stored", "invoked-helper", "unused-helper"])
def test_consol_openapi_builtin_mutations_preserve_supported_callees_and_audit_context(
    method: str, form: str
) -> None:
    arguments = "legacy, '_install_openapi_builder'" + (", None" if method == "setattr" else "")
    source = "import legacy_app as legacy\n"
    if form == "qualified":
        source += f"import builtins as bi\nbi.{method}({arguments})\n"
    elif form == "stored":
        source += f"pick = {method}\npick({arguments})\n"
    else:
        source += f"def mutate():\n    {method}({arguments})\n"
        if form == "invoked-helper":
            source += "mutate()\n"
    compile(source, "<openapi-builtin-mutation-context-fixture>", "exec")
    assert _consol_openapi_errors(source) == [
        "app/main.py: OpenAPI symbol must not be accessed through legacy"
    ]


@pytest.mark.parametrize("method", ["setattr", "delattr"])
@pytest.mark.parametrize(
    "control",
    ["safe-member", "unrelated-receiver", "canonical-receiver", "shadowed-callee", "local"],
)
def test_consol_openapi_builtin_mutations_keep_independent_safe_controls(
    method: str, control: str
) -> None:
    member = "__name__" if control == "safe-member" else "_install_openapi_builder"
    arguments = f"legacy, {member!r}" + (", None" if method == "setattr" else "")
    source = "import legacy_app as legacy\n"
    if control == "unrelated-receiver":
        source += "class Other:\n    pass\nlegacy = Other()\n"
    elif control == "canonical-receiver":
        source += "import app.bootstrap.openapi as legacy\n"
    elif control == "shadowed-callee":
        source += f"def {method}(*arguments):\n    return None\n"
    elif control == "local":
        source += (
            "import app.bootstrap.openapi as canonical\ndef mutate():\n    legacy = canonical\n"
            + f"    {method}({arguments})\nmutate()\n"
        )
    if control != "local":
        source += f"{method}({arguments})\n"
    compile(source, "<openapi-builtin-mutation-control-fixture>", "exec")
    assert _consol_openapi_errors(source) == []


@pytest.mark.parametrize("method", ["setattr", "delattr"])
@pytest.mark.parametrize("component", ["callee", "receiver", "member"])
@pytest.mark.parametrize("snapshot_kind", ["reference", "string"])
def test_consol_openapi_builtin_mutations_require_own_component_snapshots(
    method: str, component: str, snapshot_kind: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    collect = legacy_guard._collect_lexical_binding_snapshots
    selected_nodes: list[int] = []

    def collect_without_component(tree: ast.Module, **kwargs: Any) -> tuple[
        Mapping[int, Mapping[str, str]],
        Mapping[int, Mapping[str, str]],
        Mapping[int, legacy_guard._ResolvedBinding],
    ]:
        references, strings, results = collect(tree, **kwargs)
        selected = {
            id(
                node.func
                if component == "callee"
                else node.args[0 if component == "receiver" else 1]
            )
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == method
        }
        selected_nodes.extend(selected)
        if snapshot_kind == "reference":
            references = {key: value for key, value in references.items() if key not in selected}
        else:
            strings = {key: value for key, value in strings.items() if key not in selected}
        return references, strings, results

    monkeypatch.setattr(
        legacy_guard, "_collect_lexical_binding_snapshots", collect_without_component
    )
    arguments = "legacy, '_install_openapi_builder'" + (", None" if method == "setattr" else "")
    source = "import legacy_app as legacy\n" + f"{method}({arguments})\n"
    compile(source, "<openapi-builtin-mutation-own-snapshot-fixture>", "exec")
    assert _consol_openapi_errors(source) == []
    assert selected_nodes, "the actual builtin call component must be selected for omission"


@pytest.mark.parametrize("target_kind", ["attribute", "subscript"])
@pytest.mark.parametrize(
    ("initial", "rhs_owner", "annotation_owner", "postponed", "target_owner"),
    [
        pytest.param(
            "genuine", None, "canonical", False, "legacy_app", id="legacy-before-annotation"
        ),
        pytest.param(
            "canonical",
            None,
            "genuine",
            False,
            "app.bootstrap.openapi",
            id="safe-before-annotation",
        ),
        pytest.param(
            "genuine",
            "canonical",
            "genuine",
            False,
            "app.bootstrap.openapi",
            id="rhs-safe-annotation-legacy",
        ),
        pytest.param(
            "canonical",
            "genuine",
            "canonical",
            False,
            "legacy_app",
            id="rhs-legacy-annotation-safe",
        ),
        pytest.param("genuine", None, "canonical", True, "legacy_app", id="postponed-legacy"),
        pytest.param(
            "canonical", None, "genuine", True, "app.bootstrap.openapi", id="postponed-safe"
        ),
        pytest.param(
            "genuine",
            "canonical",
            "genuine",
            True,
            "app.bootstrap.openapi",
            id="postponed-rhs-safe",
        ),
        pytest.param(
            "canonical", "genuine", "canonical", True, "legacy_app", id="postponed-rhs-legacy"
        ),
    ],
)
def test_consol_valued_annassign_captures_rhs_and_target_before_annotation_effects(
    target_kind: str,
    initial: str,
    rhs_owner: str | None,
    annotation_owner: str,
    postponed: bool,
    target_owner: str,
) -> None:
    source = (
        "import legacy_app as genuine\nimport app.bootstrap.openapi as canonical\n"
        + f"legacy = {initial}\nmember = '_install_openapi_builder'\n"
        + f"def annotation():\n    global legacy\n    legacy = {annotation_owner}\n    return object\n"
    )
    if rhs_owner is not None:
        source += f"def rhs():\n    global legacy\n    legacy = {rhs_owner}\n    return None\n"
    target = (
        "legacy._install_openapi_builder"
        if target_kind == "attribute"
        else "legacy.__dict__[member]"
    )
    source += f"{target}: annotation() = {'rhs()' if rhs_owner is not None else 'None'}\n"
    if postponed:
        source = "from __future__ import annotations\n" + source
    compile(source, "<valued-annassign-own-point-order-fixture>", "exec")
    tree = ast.parse(source)
    references, strings, _results = legacy_guard._collect_lexical_binding_snapshots(
        tree,
        filename="app/main.py",
        initial_references={},
        ownership_family="openapi",
        purpose="ownership_audit",
    )
    assignment = next(node for node in tree.body if isinstance(node, ast.AnnAssign))
    leaf = cast(ast.Attribute | ast.Subscript, assignment.target)
    assert id(leaf) in references and id(leaf) in strings
    assert id(leaf.value) in references and id(leaf.value) in strings
    assert references[id(leaf)]["legacy"] == target_owner
    assert references[id(leaf.value)]["legacy"] == target_owner
    final_references, _final_strings = legacy_guard._collect_module_final_bindings(
        tree, filename="app/main.py", initial_references={}, ownership_family="openapi"
    )
    final_owner = (
        target_owner
        if postponed
        else "legacy_app" if annotation_owner == "genuine" else "app.bootstrap.openapi"
    )
    assert final_references["legacy"] == final_owner
    diagnostic = "app/main.py: OpenAPI symbol must not be accessed through legacy"
    raw_errors: list[str] = []
    legacy_guard._record_main_legacy_openapi_lookups(tree, raw_errors)
    assert raw_errors == ([diagnostic] if target_owner == "legacy_app" else [])
    assert _consol_openapi_errors(source) == ([diagnostic] if target_owner == "legacy_app" else [])


@pytest.mark.parametrize("target_kind", ["attribute", "subscript"])
def test_consol_valued_annassign_keeps_real_local_receiver_boundary(target_kind: str) -> None:
    target = (
        "legacy._install_openapi_builder"
        if target_kind == "attribute"
        else "legacy.__dict__[member]"
    )
    source = (
        "import legacy_app as legacy\nimport app.bootstrap.openapi as canonical\n"
        "member = '_install_openapi_builder'\ndef annotation():\n    return object\n"
        + f"def update(legacy):\n    {target}: annotation() = None\nupdate(canonical)\n"
    )
    compile(source, "<valued-annassign-local-receiver-fixture>", "exec")
    assert _consol_openapi_errors(source) == []


@pytest.mark.parametrize("symbol", (*_CONSOL_OPENAPI_SYMBOLS, "CustomOPENapiHook"))
@pytest.mark.parametrize("method", ["setitem", "update-mapping", "update-keyword"])
@pytest.mark.parametrize("context", ["module", "invoked-helper"])
def test_consol_openapi_namespace_writes_cover_full_inventory_and_executed_helpers(
    symbol: str, method: str, context: str
) -> None:
    statement = (
        f"legacy.__dict__.__setitem__({symbol!r}, None)\n"
        if method == "setitem"
        else (
            f"legacy.__dict__.update({{{symbol!r}: None}})\n"
            if method == "update-mapping"
            else f"legacy.__dict__.update({symbol}=None)\n"
        )
    )
    source = "import legacy_app as legacy\n"
    source += (
        statement
        if context == "module"
        else "def mutate():\n" + textwrap.indent(statement, "    ") + "mutate()\n"
    )
    compile(source, "<openapi-namespace-write-inventory-fixture>", "exec")
    assert _consol_openapi_errors(source) == [
        "app/main.py: OpenAPI symbol must not be accessed through legacy"
    ]


@pytest.mark.parametrize(
    ("setup", "statement"),
    [
        pytest.param("", "vars(legacy).__setitem__(member, None)\n", id="computed-vars-setitem"),
        pytest.param("", "vars(legacy).update({member: None})\n", id="computed-vars-update"),
        pytest.param("", "dict.__setitem__(vars(legacy), member, None)\n", id="unbound-setitem"),
        pytest.param("", "dict.update(vars(legacy), {member: None})\n", id="unbound-update"),
        pytest.param(
            "pick = dict.__setitem__\n",
            "pick(vars(legacy), member, None)\n",
            id="stored-unbound-setitem",
        ),
        pytest.param(
            "pick = dict.update\n",
            "pick(vars(legacy), {member: None})\n",
            id="stored-unbound-update",
        ),
        pytest.param(
            "import builtins as bi\n",
            "bi.dict.update(vars(legacy), {member: None})\n",
            id="qualified-dict-update",
        ),
    ],
)
def test_consol_openapi_namespace_writes_preserve_supported_receiver_and_builtin_forms(
    setup: str, statement: str
) -> None:
    source = (
        "import legacy_app as legacy\nmember = '_install_openapi_builder'\n" + setup + statement
    )
    compile(source, "<openapi-namespace-write-provenance-fixture>", "exec")
    assert _consol_openapi_errors(source) == [
        "app/main.py: OpenAPI symbol must not be accessed through legacy"
    ]


@pytest.mark.parametrize(
    "source",
    [
        pytest.param(
            "import legacy_app as legacy\nlegacy.__dict__.update(other=None)\n", id="safe-keyword"
        ),
        pytest.param(
            "import legacy_app as legacy\nlegacy.__dict__.__setitem__('other', None)\n",
            id="safe-key",
        ),
        pytest.param(
            "namespace = {}\nnamespace.update({'_install_openapi_builder': None})\n",
            id="unrelated-mapping",
        ),
        pytest.param(
            "import app.bootstrap.openapi as canonical\nvars(canonical).update({'_install_openapi_builder': None})\n",
            id="canonical-namespace",
        ),
        pytest.param(
            "import legacy_app as legacy\nclass Other:\n    def update(self, namespace, changes):\n"
            "        pass\ndict = Other()\ndict.update(vars(legacy), {'_install_openapi_builder': None})\n",
            id="shadowed-dict-method",
        ),
        pytest.param(
            "import legacy_app as legacy\ndef vars(receiver):\n    return {}\n"
            "vars(legacy).__setitem__('_install_openapi_builder', None)\n",
            id="shadowed-vars",
        ),
        pytest.param(
            "import legacy_app as legacy\nimport app.bootstrap.openapi as canonical\n"
            "def mutate(legacy):\n    vars(legacy).update({'_install_openapi_builder': None})\n"
            "mutate(canonical)\n",
            id="real-local-receiver",
        ),
    ],
)
def test_consol_openapi_namespace_write_controls_require_actual_legacy_identity(
    source: str,
) -> None:
    compile(source, "<openapi-namespace-write-control-fixture>", "exec")
    assert _consol_openapi_errors(source) == []


@pytest.mark.parametrize("invoked", [False, True])
def test_consol_openapi_namespace_write_audit_keeps_ordinary_dormant_effects_separate(
    invoked: bool,
) -> None:
    source = (
        "import legacy_app as legacy\nstate = 'unchanged'\ndef mutate():\n"
        "    legacy.__dict__.update({'_install_openapi_builder': None})\n"
        "    global state\n    state = 'changed'\n" + ("mutate()\n" if invoked else "")
    )
    compile(source, "<openapi-namespace-write-purpose-fixture>", "exec")
    visitor = legacy_guard._ApiKeyLookupVisitor(
        filename="app/main.py", errors=[], analyze_function_bodies=False, ownership_family="openapi"
    )
    visitor.visit(ast.parse(source))
    assert visitor.scope.resolve_string("state") == ("changed" if invoked else "unchanged")
    assert _consol_openapi_errors(source) == [
        "app/main.py: OpenAPI symbol must not be accessed through legacy"
    ]


@pytest.mark.parametrize("initially_legacy", [True, False])
@pytest.mark.parametrize("method", ["setitem", "update"])
def test_consol_openapi_namespace_write_receiver_precedes_key_effects(
    initially_legacy: bool, method: str
) -> None:
    source = (
        "import legacy_app as genuine\nimport app.bootstrap.openapi as canonical\n"
        + f"legacy = {'genuine' if initially_legacy else 'canonical'}\n"
        + "def member():\n    global legacy\n"
        + f"    legacy = {'canonical' if initially_legacy else 'genuine'}\n"
        + "    return '_install_openapi_builder'\n"
        + (
            "legacy.__dict__.__setitem__(member(), None)\n"
            if method == "setitem"
            else "legacy.__dict__.update({member(): None})\n"
        )
    )
    compile(source, "<openapi-namespace-write-order-fixture>", "exec")
    diagnostic = "app/main.py: OpenAPI symbol must not be accessed through legacy"
    assert _consol_openapi_errors(source) == ([diagnostic] if initially_legacy else [])


@pytest.mark.parametrize("method", ["setitem", "update"])
@pytest.mark.parametrize("component", ["call", "callee", "receiver", "key"])
@pytest.mark.parametrize("snapshot_kind", ["reference", "string"])
def test_consol_openapi_namespace_writes_require_own_call_and_key_evidence(
    method: str, component: str, snapshot_kind: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    collect = legacy_guard._collect_lexical_binding_snapshots
    selected_nodes: list[int] = []
    method_name = "__setitem__" if method == "setitem" else "update"

    def collect_without_component(tree: ast.Module, **kwargs: Any) -> tuple[
        Mapping[int, Mapping[str, str]],
        Mapping[int, Mapping[str, str]],
        Mapping[int, legacy_guard._ResolvedBinding],
    ]:
        references, strings, results = collect(tree, **kwargs)
        selected: set[int] = set()
        for node in ast.walk(tree):
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == method_name
            ):
                continue
            if component == "call":
                selected.add(id(node))
            elif component == "callee":
                selected.add(id(node.func))
            elif component == "receiver":
                selected.add(id(node.func.value))
            else:
                key = node.args[0] if method == "setitem" else cast(ast.Dict, node.args[0]).keys[0]
                assert key is not None
                selected.add(id(key))
        selected_nodes.extend(selected)
        if snapshot_kind == "reference":
            references = {key: value for key, value in references.items() if key not in selected}
        else:
            strings = {key: value for key, value in strings.items() if key not in selected}
        return references, strings, results

    monkeypatch.setattr(
        legacy_guard, "_collect_lexical_binding_snapshots", collect_without_component
    )
    source = "import legacy_app as legacy\nmember = '_install_openapi_builder'\n" + (
        "legacy.__dict__.__setitem__(member, None)\n"
        if method == "setitem"
        else "legacy.__dict__.update({member: None})\n"
    )
    compile(source, "<openapi-namespace-write-own-evidence-fixture>", "exec")
    assert _consol_openapi_errors(source) == []
    assert selected_nodes, "the actual namespace call component must be selected for omission"


@pytest.mark.parametrize("symbol", _CONSOL_API_KEY_SYMBOLS)
@pytest.mark.parametrize("operation", ["assignment", "delete"])
def test_consol_class_global_api_rebinding_covers_full_protected_inventory(
    symbol: str, operation: str
) -> None:
    statement = f"{symbol} = None\n" if operation == "assignment" else f"del {symbol}\n"
    source = (
        _CONSOL_GETTER_IMPORTS
        + f"class Scope:\n    global {symbol}\n"
        + textwrap.indent(statement, "    ")
    )
    compile(source, "<class-global-protected-binding-fixture>", "exec")
    assert _validate_api_key_dependency_ownership(source, {}) == [
        _CONSOL_API_KEY_REBINDING_ERRORS[symbol]
    ]


@pytest.mark.parametrize(
    ("body", "invocation", "forbidden"),
    [
        pytest.param(
            "class Scope:\n    global require_app_api_key\n    if enabled:\n"
            "        require_app_api_key = None\n",
            "",
            True,
            id="conditional-class-global",
        ),
        pytest.param(
            "class Outer:\n    class Inner:\n        global require_app_api_key\n"
            "        require_app_api_key = None\n",
            "",
            True,
            id="nested-class-global",
        ),
        pytest.param(
            "def configure():\n    class Scope:\n        global require_app_api_key\n"
            "        require_app_api_key = None\n",
            "",
            False,
            id="uncalled-class-wrapper",
        ),
        pytest.param(
            "def configure():\n    class Scope:\n        global require_app_api_key\n"
            "        require_app_api_key = None\n",
            "configure()\n",
            True,
            id="called-class-wrapper",
        ),
        pytest.param(
            "class Scope:\n    global require_app_api_key\n",
            "",
            False,
            id="global-declaration-only",
        ),
        pytest.param(
            "class Scope:\n    global unrelated\n    unrelated = None\n",
            "",
            False,
            id="unrelated-global",
        ),
        pytest.param(
            "def configure():\n    require_app_api_key = None\n    class Scope:\n"
            "        nonlocal require_app_api_key\n        require_app_api_key = object\n",
            "configure()\n",
            False,
            id="genuine-enclosing-nonlocal",
        ),
    ],
)
def test_consol_class_outward_api_reporting_preserves_execution_and_real_owner_boundaries(
    body: str, invocation: str, forbidden: bool
) -> None:
    source = _CONSOL_GETTER_IMPORTS + body + invocation
    compile(source, "<class-outward-execution-boundary-fixture>", "exec")
    expected = [_CONSOL_API_KEY_REBINDING_ERRORS["require_app_api_key"]] if forbidden else []
    assert _validate_api_key_dependency_ownership(source, {}) == expected


@pytest.mark.parametrize("symbol", _CONSOL_API_KEY_SYMBOLS)
@pytest.mark.parametrize("operation", ["assignment", "valued-annotation", "delete"])
def test_consol_class_local_api_spellings_are_not_module_rebindings(
    symbol: str, operation: str
) -> None:
    statement = (
        f"{symbol}: object = None\n"
        if operation == "valued-annotation"
        else (
            f"{symbol} = None\n"
            if operation == "assignment"
            else f"{symbol} = None\ndel {symbol}\n"
        )
    )
    source = _CONSOL_GETTER_IMPORTS + "class Scope:\n" + textwrap.indent(statement, "    ")
    compile(source, "<class-local-protected-spelling-fixture>", "exec")
    assert _validate_api_key_dependency_ownership(source, {}) == []


@pytest.mark.parametrize("symbol", _CONSOL_API_KEY_SYMBOLS)
@pytest.mark.parametrize("target_kind", ["attribute", "subscript"])
@pytest.mark.parametrize("operation", ["assignment", "annotation", "augmented", "delete"])
def test_consol_api_protected_targets_cover_full_inventory(
    symbol: str, target_kind: str, operation: str
) -> None:
    target = f"legacy.{symbol}" if target_kind == "attribute" else f"legacy.__dict__[{symbol!r}]"
    statements = {
        "assignment": f"{target} = None\n",
        "annotation": f"{target}: object = None\n",
        "augmented": f"{target} += replacement\n",
        "delete": f"del {target}\n",
    }
    source = "import legacy_app as legacy\n" + statements[operation]
    compile(source, "<api-protected-target-fixture>", "exec")
    diagnostic = (
        "app/routers/example.py: legacy API-key dependency attribute access "
        if target_kind == "attribute"
        else "app/routers/example.py: legacy API-key dependency namespace lookup "
    ) + f"is forbidden: {symbol}"
    assert _validate_api_key_dependency_ownership(
        _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
    ) == [diagnostic]


@pytest.mark.parametrize("symbol", _CONSOL_API_KEY_SYMBOLS)
@pytest.mark.parametrize("carrier", ["setattr", "delattr", "setitem", "update"])
def test_consol_api_protected_mutating_calls_cover_full_inventory(
    symbol: str, carrier: str
) -> None:
    statements = {
        "setattr": f"setattr(legacy, {symbol!r}, None)\n",
        "delattr": f"delattr(legacy, {symbol!r})\n",
        "setitem": f"legacy.__dict__.__setitem__({symbol!r}, None)\n",
        "update": f"legacy.__dict__.update({{{symbol!r}: None}})\n",
    }
    source = "import legacy_app as legacy\n" + statements[carrier]
    compile(source, "<api-protected-mutation-fixture>", "exec")
    diagnostic = (
        "app/routers/example.py: dynamic legacy API-key dependency lookup "
        if carrier in {"setattr", "delattr"}
        else "app/routers/example.py: legacy API-key dependency namespace lookup "
    ) + f"is forbidden: {symbol}"
    assert _validate_api_key_dependency_ownership(
        _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
    ) == [diagnostic]


@pytest.mark.parametrize(
    "source",
    [
        "import legacy_app as legacy\nlegacy.other = None\n",
        "import app.routers.api_key as canonical\ncanonical.require_app_api_key = None\n",
        "class Other:\n    pass\nother = Other()\ndel other.require_app_api_key\n",
        "import legacy_app as legacy\nsetattr(legacy, 'other', None)\n",
        "import legacy_app as legacy\ndef setattr(*arguments):\n    pass\nsetattr(legacy, 'require_app_api_key', None)\n",
        "import legacy_app as legacy\ndef delattr(*arguments):\n    pass\ndelattr(legacy, 'require_app_api_key')\n",
        "import legacy_app as legacy\nlegacy.__dict__.update(other=None)\n",
        "import legacy_app as legacy\nimport app.routers.api_key as canonical\ndef mutate(legacy):\n    legacy.require_app_api_key = None\nmutate(canonical)\n",
    ],
)
def test_consol_api_protected_writes_keep_independent_safe_and_shadow_controls(source: str) -> None:
    compile(source, "<api-mutation-independent-control-fixture>", "exec")
    assert (
        _validate_api_key_dependency_ownership(
            _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
        )
        == []
    )


@pytest.mark.parametrize("invoked", [False, True])
def test_consol_api_target_audit_preserves_ordinary_dormant_outward_effects(invoked: bool) -> None:
    source = (
        "import legacy_app as legacy\nstate = 'unchanged'\ndef mutate():\n"
        "    legacy.require_app_api_key = None\n    global state\n    state = 'changed'\n"
        + ("mutate()\n" if invoked else "")
    )
    compile(source, "<api-target-purpose-fixture>", "exec")
    visitor = legacy_guard._ApiKeyLookupVisitor(
        filename="app/routers/example.py", errors=[], analyze_function_bodies=False
    )
    visitor.visit(ast.parse(source))
    assert visitor.scope.resolve_string("state") == ("changed" if invoked else "unchanged")
    assert _validate_api_key_dependency_ownership(
        _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
    ) == [
        "app/routers/example.py: legacy API-key dependency attribute access is forbidden: require_app_api_key"
    ]


@pytest.mark.parametrize(
    ("statement", "initial", "replacement", "forbidden"),
    [
        pytest.param(
            "legacy.require_app_api_key = rhs()\n",
            "genuine",
            "canonical",
            False,
            id="rhs-before-store",
        ),
        pytest.param(
            "legacy.require_app_api_key: object = rhs()\n",
            "canonical",
            "genuine",
            True,
            id="rhs-before-annotated-store",
        ),
        pytest.param(
            "legacy.require_app_api_key += rhs()\n",
            "genuine",
            "canonical",
            True,
            id="augmented-target-before-rhs",
        ),
        pytest.param(
            "legacy.__dict__[member()] = None\n",
            "genuine",
            "canonical",
            True,
            id="receiver-before-member",
        ),
    ],
)
def test_consol_api_target_reports_keep_actual_evaluation_order(
    statement: str, initial: str, replacement: str, forbidden: bool
) -> None:
    source = (
        "import legacy_app as genuine\nimport app.routers.api_key as canonical\n"
        + f"legacy = {initial}\ndef rhs():\n    global legacy\n    legacy = {replacement}\n    return None\n"
        + f"def member():\n    global legacy\n    legacy = {replacement}\n    return 'require_app_api_key'\n"
        + statement
    )
    compile(source, "<api-target-own-order-fixture>", "exec")
    kind = "namespace lookup" if "__dict__" in statement else "attribute access"
    diagnostic = f"app/routers/example.py: legacy API-key dependency {kind} is forbidden: require_app_api_key"
    assert _validate_api_key_dependency_ownership(
        _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
    ) == ([diagnostic] if forbidden else [])


@pytest.mark.parametrize(
    "statement",
    [
        pytest.param("legacy.__dict__.__setitem__(member, None)\n", id="setitem"),
        pytest.param("legacy.__dict__.__delitem__(member)\n", id="delitem"),
        pytest.param("legacy.__dict__.pop(member, None)\n", id="pop"),
        pytest.param("legacy.__dict__.setdefault(member, None)\n", id="setdefault"),
        pytest.param("legacy.__dict__.update({member: None})\n", id="update"),
        pytest.param("legacy.__dict__.__ior__({member: None})\n", id="ior"),
        pytest.param(
            "legacy.__dict__.__init__(_install_openapi_builder=None)\n", id="init-supplied-key"
        ),
        pytest.param("legacy.__dict__.clear()\n", id="clear"),
        pytest.param("legacy.__dict__.popitem()\n", id="popitem"),
    ],
)
def test_consol_openapi_current_nine_mutator_operations_keep_distinct_key_semantics(
    statement: str,
) -> None:
    source = "import legacy_app as legacy\nmember = '_install_openapi_builder'\n" + statement
    compile(source, "<current-nine-mutator-fixture>", "exec")
    assert _consol_openapi_errors(source) == [
        "app/main.py: OpenAPI symbol must not be accessed through legacy"
    ]


@pytest.mark.parametrize("method", ["clear", "popitem", "__delitem__"])
@pytest.mark.parametrize("form", ["computed-bound", "stored-unbound"])
def test_consol_openapi_destructive_methods_keep_proven_computed_and_builtin_aliases(
    method: str, form: str
) -> None:
    arguments = "'_install_openapi_builder'" if method == "__delitem__" else ""
    source = "import legacy_app as legacy\n" + (
        f"vars(legacy).{method}({arguments})\n"
        if form == "computed-bound"
        else f"pick = dict.{method}\npick(vars(legacy){', ' + arguments if arguments else ''})\n"
    )
    compile(source, "<destructive-method-provenance-fixture>", "exec")
    assert _consol_openapi_errors(source) == [
        "app/main.py: OpenAPI symbol must not be accessed through legacy"
    ]


@pytest.mark.parametrize(
    "source",
    [
        "import legacy_app as legacy\nlegacy.__dict__.__init__()\n",
        "import legacy_app as legacy\nlegacy.__dict__.update()\n",
        "import legacy_app as legacy\nlegacy.__dict__.__ior__({})\n",
        "import legacy_app as legacy\nlegacy.__dict__.__delitem__('other')\n",
        "import legacy_app as legacy\nlegacy.__dict__.__init__(other=None)\n",
        "namespace = {}\nnamespace.clear()\n",
        "import app.bootstrap.openapi as canonical\nvars(canonical).popitem()\n",
        "import legacy_app as legacy\ndef vars(receiver):\n    return {}\nvars(legacy).clear()\n",
    ],
)
def test_consol_mutator_empty_supplied_safe_and_unrelated_controls(source: str) -> None:
    compile(source, "<mutator-operation-control-fixture>", "exec")
    assert _consol_openapi_errors(source) == []


@pytest.mark.parametrize(
    ("statement", "forbidden"),
    [
        ("obj.__dict__.clear()", True),
        ("obj.__dict__.popitem()", True),
        ("obj.__dict__.__delitem__('owner')", True),
        ("obj.__dict__.__delitem__('other')", False),
        ("obj.__dict__.update(unknown)", True),
        ("obj.__dict__.update()", False),
        ("obj.__dict__.__init__()", False),
    ],
)
def test_consol_default_namespace_mutation_helper_keeps_conservative_unknown_and_empty_boundaries(
    statement: str, forbidden: bool
) -> None:
    tree = ast.parse(statement)
    call = cast(ast.Call, cast(ast.Expr, tree.body[0]).value)
    assert (
        legacy_guard._mutates_protected_namespace(
            call,
            protected_names={"owner"},
            references={},
            static_string_bindings={},
            static_mapping_bindings={},
        )
        is forbidden
    )


@pytest.mark.parametrize("family", ["api", "openapi"])
@pytest.mark.parametrize(
    ("lookup", "namespace"),
    [
        ("getattr(*(legacy, {member!r}))", False),
        ("getattr(*[legacy, {member!r}])", False),
        ("getattr(*[legacy, *({member!r},)])", False),
        ("getattr(legacy, *({member!r},))", False),
        ("dict.get(*(vars(legacy), {member!r}))", True),
        ("dict.__getitem__(*[vars(legacy), {member!r}])", True),
        ("dict.pop(*(vars(legacy), {member!r}, None))", True),
        ("dict.setdefault(*[vars(legacy), {member!r}, None])", True),
    ],
)
def test_consol_literal_starred_lookups_use_original_ordered_leaf_evidence(
    family: Literal["api", "openapi"], lookup: str, namespace: bool
) -> None:
    member = "get_api_key" if family == "api" else "_install_openapi_builder"
    source = "import legacy_app as legacy\nvalue = " + lookup.format(member=member) + "\n"
    compile(source, "<literal-starred-lookup-fixture>", "exec")
    if family == "api":
        kind = (
            "legacy API-key dependency namespace lookup"
            if namespace
            else "dynamic legacy API-key dependency lookup"
        )
        assert _validate_api_key_dependency_ownership(
            _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
        ) == [f"app/routers/example.py: {kind} is forbidden: {member}"]
    else:
        assert _consol_openapi_errors(source) == [
            "app/main.py: OpenAPI symbol must not be accessed through legacy"
        ]


@pytest.mark.parametrize("family", ["api", "openapi"])
@pytest.mark.parametrize(
    ("statement", "namespace"),
    [
        ("setattr(*(legacy, {member!r}, None))", False),
        ("delattr(*[legacy, {member!r}])", False),
        ("dict.__setitem__(*(vars(legacy), {member!r}, None))", True),
        ("dict.update(*[vars(legacy), {{{member!r}: None}}])", True),
    ],
)
def test_consol_literal_starred_mutations_share_existing_positional_normalization(
    family: Literal["api", "openapi"], statement: str, namespace: bool
) -> None:
    member = "get_api_key" if family == "api" else "_install_openapi_builder"
    source = "import legacy_app as legacy\n" + statement.format(member=member) + "\n"
    compile(source, "<literal-starred-mutation-fixture>", "exec")
    if family == "api":
        kind = (
            "legacy API-key dependency namespace lookup"
            if namespace
            else "dynamic legacy API-key dependency lookup"
        )
        assert _validate_api_key_dependency_ownership(
            _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
        ) == [f"app/routers/example.py: {kind} is forbidden: {member}"]
    else:
        assert _consol_openapi_errors(source) == [
            "app/main.py: OpenAPI symbol must not be accessed through legacy"
        ]


@pytest.mark.parametrize("family", ["api", "openapi"])
@pytest.mark.parametrize(
    "control",
    [
        "safe-receiver",
        "safe-member",
        "shadowed-getattr",
        "unknown-name",
        "unknown-call",
        "generator",
        "comprehension",
        "unknown-namespace",
        "depth-exhausted",
    ],
)
def test_consol_starred_controls_never_drop_unresolved_sources_and_reindex_known_nodes(
    family: Literal["api", "openapi"], control: str
) -> None:
    member = "get_api_key" if family == "api" else "_install_openapi_builder"
    canonical = "app.routers.api_key" if family == "api" else "app.bootstrap.openapi"
    source = "import legacy_app as legacy\n"
    if control == "safe-receiver":
        source += f"import {canonical} as canonical\ngetattr(*(canonical, {member!r}))\n"
    elif control == "safe-member":
        source += "getattr(*[legacy, 'other'])\n"
    elif control == "shadowed-getattr":
        source += f"def getattr(*arguments):\n    return None\ngetattr(*(legacy, {member!r}))\n"
    elif control == "unknown-namespace":
        source += f"dict.get(*unknown, vars(legacy), {member!r})\n"
    elif control == "depth-exhausted":
        value = f"(legacy, {member!r})"
        for _ in range(9):
            value = f"(*{value},)"
        source += f"getattr(*{value})\n"
    else:
        value = {
            "unknown-name": "unknown",
            "unknown-call": "values()",
            "generator": "(item for item in unknown)",
            "comprehension": "[item for item in unknown]",
        }[control]
        source += f"getattr(*{value}, legacy, {member!r})\n"
    compile(source, "<unresolved-starred-control-fixture>", "exec")
    if family == "api":
        assert (
            _validate_api_key_dependency_ownership(
                _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
            )
            == []
        )
    else:
        assert _consol_openapi_errors(source) == []


@pytest.mark.parametrize("component", ["callee", "receiver", "member"])
@pytest.mark.parametrize("snapshot_kind", ["reference", "string"])
def test_consol_starred_openapi_calls_require_each_original_leaf_snapshot(
    component: str, snapshot_kind: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    collect = legacy_guard._collect_lexical_binding_snapshots
    selected_nodes: list[int] = []

    def collect_without_leaf(tree: ast.Module, **kwargs: Any) -> tuple[
        Mapping[int, Mapping[str, str]],
        Mapping[int, Mapping[str, str]],
        Mapping[int, legacy_guard._ResolvedBinding],
    ]:
        references, strings, results = collect(tree, **kwargs)
        selected: set[int] = set()
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "getattr"
            ):
                leaves = cast(ast.Tuple, cast(ast.Starred, node.args[0]).value).elts
                selected.add(
                    id(
                        node.func
                        if component == "callee"
                        else leaves[0 if component == "receiver" else 1]
                    )
                )
        selected_nodes.extend(selected)
        if snapshot_kind == "reference":
            references = {key: value for key, value in references.items() if key not in selected}
        else:
            strings = {key: value for key, value in strings.items() if key not in selected}
        return references, strings, results

    monkeypatch.setattr(legacy_guard, "_collect_lexical_binding_snapshots", collect_without_leaf)
    source = "import legacy_app as legacy\ngetattr(*(legacy, '_install_openapi_builder'))\n"
    assert _consol_openapi_errors(source) == []
    assert selected_nodes, "the original expanded leaf must be selected for omission"


@pytest.mark.parametrize("family", ["api", "openapi"])
def test_consol_starred_lookup_children_execute_once_before_later_default_effects(
    family: Literal["api", "openapi"],
) -> None:
    member = "get_api_key" if family == "api" else "_install_openapi_builder"
    source = (
        "import legacy_app as legacy\ntrace = ''\ndef receiver():\n    global trace\n"
        "    trace = trace + 'r'\n    return legacy\ndef member():\n    global trace\n"
        + f"    trace = trace + 'k'\n    return {member!r}\n"
        + "def default():\n    global trace\n    trace = trace + 'd'\n    return None\n"
        + "getattr(*(receiver(), member()), default())\n"
    )
    compile(source, "<starred-once-only-child-order-fixture>", "exec")
    visitor = legacy_guard._ApiKeyLookupVisitor(
        filename="app/routers/example.py", errors=[], analyze_function_bodies=False
    )
    visitor.visit(ast.parse(source))
    assert visitor.scope.resolve_string("trace") == "rkd"
    if family == "api":
        assert _validate_api_key_dependency_ownership(
            _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
        ) == [
            f"app/routers/example.py: dynamic legacy API-key dependency lookup is forbidden: {member}"
        ]
    else:
        assert _consol_openapi_errors(source) == [
            "app/main.py: OpenAPI symbol must not be accessed through legacy"
        ]


@pytest.mark.parametrize("initially_protected", [True, False])
def test_consol_api_update_key_fact_precedes_later_value_rebinding(
    initially_protected: bool,
) -> None:
    initial = "require_app_api_key" if initially_protected else "other"
    replacement = "other" if initially_protected else "require_app_api_key"
    source = (
        "import legacy_app as legacy\n"
        + f"member = {initial!r}\ndef replace_member():\n    global member\n"
        + f"    member = {replacement!r}\n    return None\n"
        + "legacy.__dict__.update({member: replace_member()})\n"
    )
    compile(source, "<api-own-key-before-value-fixture>", "exec")
    diagnostic = "app/routers/example.py: legacy API-key dependency namespace lookup is forbidden: require_app_api_key"
    assert _validate_api_key_dependency_ownership(
        _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
    ) == ([diagnostic] if initially_protected else [])


def test_consol_api_update_uses_already_visited_returned_key_result() -> None:
    source = (
        "import legacy_app as legacy\nstate = 'unchanged'\ndef member():\n    global state\n"
        "    state = 'visited'\n    return 'require_app_api_key'\n"
        "def value():\n    global state\n    state = 'unchanged'\n    return None\n"
        "legacy.__dict__.update({member(): value()})\n"
    )
    compile(source, "<api-returned-own-key-fixture>", "exec")
    visitor = legacy_guard._ApiKeyLookupVisitor(
        filename="app/routers/example.py", errors=[], analyze_function_bodies=False
    )
    visitor.visit(ast.parse(source))
    assert visitor.scope.resolve_string("state") == "unchanged"
    assert _validate_api_key_dependency_ownership(
        _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
    ) == [
        "app/routers/example.py: legacy API-key dependency namespace lookup is forbidden: require_app_api_key"
    ]


@pytest.mark.parametrize("key_kind", ["name", "returned-call"])
@pytest.mark.parametrize("missing_snapshot", ["reference", "string"])
def test_consol_own_key_resolver_requires_both_actual_node_snapshots(
    key_kind: str, missing_snapshot: str
) -> None:
    source = (
        "member = 'require_app_api_key'\ndef read():\n    return member\n"
        "first = member\nsecond = read()\nmember = 'other'\n"
    )
    compile(source, "<own-key-missing-component-fixture>", "exec")
    tree = ast.parse(source)
    references: dict[int, dict[str, str]] = {}
    strings: dict[int, dict[str, str]] = {}
    visitor = legacy_guard._ApiKeyLookupVisitor(
        filename="app/routers/example.py",
        errors=[],
        analyze_function_bodies=False,
        reference_snapshots=references,
        string_snapshots=strings,
    )
    visitor.visit(tree)
    key = cast(ast.Assign, tree.body[2 if key_kind == "name" else 3]).value
    assert id(key) in references and id(key) in strings
    original_scope = visitor.scope
    (references if missing_snapshot == "reference" else strings).pop(id(key))
    assert visitor._resolve_string(key, own_environment=True) is None
    assert visitor.scope is original_scope
    assert visitor.scope.resolve_string("member") == "other"


@pytest.mark.parametrize("key_kind", ["name", "returned-call"])
def test_consol_own_key_resolver_restores_scope_and_never_replays_key_children(
    key_kind: str,
) -> None:
    source = (
        "member = 'require_app_api_key'\nstate = 'unchanged'\ndef read():\n    global state\n"
        "    state = 'visited'\n    return member\nfirst = member\nsecond = read()\n"
        "member = 'other'\nstate = 'unchanged'\n"
    )
    compile(source, "<own-key-restoration-fixture>", "exec")
    tree = ast.parse(source)
    references: dict[int, dict[str, str]] = {}
    strings: dict[int, dict[str, str]] = {}
    visitor = legacy_guard._ApiKeyLookupVisitor(
        filename="app/routers/example.py",
        errors=[],
        analyze_function_bodies=False,
        reference_snapshots=references,
        string_snapshots=strings,
    )
    visitor.visit(tree)
    key = cast(ast.Assign, tree.body[3 if key_kind == "name" else 4]).value
    original_scope = visitor.scope
    assert visitor._resolve_string(key, own_environment=True) == "require_app_api_key"
    assert visitor.scope is original_scope
    assert visitor.scope.resolve_string("member") == "other"
    assert visitor.scope.resolve_string("state") == "unchanged"


def test_consol_own_key_resolver_restores_scope_on_resolution_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = "first = 'require_' + 'app_api_key'\nmember = 'other'\n"
    tree = ast.parse(source)
    references: dict[int, dict[str, str]] = {}
    strings: dict[int, dict[str, str]] = {}
    visitor = legacy_guard._ApiKeyLookupVisitor(
        filename="app/routers/example.py",
        errors=[],
        analyze_function_bodies=False,
        reference_snapshots=references,
        string_snapshots=strings,
    )
    visitor.visit(tree)
    key = cast(ast.Assign, tree.body[0]).value
    original_scope = visitor.scope

    def reject_resolution(node: ast.AST, bindings: Mapping[str, str]) -> str | None:
        raise RuntimeError("synthetic key-resolution failure")

    monkeypatch.setattr(legacy_guard, "_resolve_static_string", reject_resolution)
    with pytest.raises(RuntimeError, match="synthetic key-resolution failure"):
        visitor._resolve_string(key, own_environment=True)
    assert visitor.scope is original_scope
    assert visitor.scope.resolve_string("member") == "other"


@pytest.mark.parametrize("ownership_family", ["api_key", "openapi"])
@pytest.mark.parametrize(
    "preservation_flags",
    [
        (False, False, False),
        (True, False, False),
        (False, True, False),
        (False, False, True),
        (True, True, False),
        (True, False, True),
        (False, True, True),
        (True, True, True),
    ],
)
def test_consol_repeated_snapshot_preserves_equal_markers_and_live_state(
    ownership_family: Literal["api_key", "openapi"],
    preservation_flags: tuple[bool, bool, bool],
) -> None:
    node = cast(ast.Expr, ast.parse("member\n").body[0]).value
    function = cast(ast.FunctionDef, ast.parse("def unused():\n    return 'changed'\n").body[0])
    references = {
        "legacy": "legacy_app",
        "possible_legacy": "<possible:legacy_app>",
        "builtin": "builtins.getattr",
        "possible_builtin": "<possible:builtins.getattr>",
        "builtin_namespace": "<namespace:builtins>",
        "possible_builtin_namespace": "<possible:namespace:builtins>",
        "module_namespace": "<namespace:module>",
        "possible_object_namespace": "<possible:namespace:object>",
        "fastapi": "fastapi.FastAPI",
        "possible_fastapi": "<possible:fastapi>",
        "conflicted_fastapi": "<conflicted:fastapi>",
        "importer": "builtins.__import__",
        "possible_importer": "<possible:import_callable>",
        "possible_mutator": "<possible:namespace-mutator>.update",
        "safe": "math",
    }
    strings = {
        "header": "api_key_header",
        "getter": "get_api_key",
        "dynamic_getter": "_get_api_key_dynamic",
        "validator": "validate_app_api_key",
        "required": "require_app_api_key",
        "openapi": "_install_openapi_builder",
        "casefold": "debugOPENAPIhook",
        "possible_api_key": "<possible:api_key_symbol>",
        "possible_openapi": "<possible:openapi_symbol>",
        "route": "get",
        "possible_route": "<possible:route_method>",
        "conflicted_route": "<conflicted:route_method>",
        "empty": "",
        "state": "unchanged",
    }
    reference_snapshots = {id(node): dict(references)}
    string_snapshots = {id(node): dict(strings)}
    saved_references = reference_snapshots[id(node)]
    saved_strings = string_snapshots[id(node)]
    errors = ["prior diagnostic"]
    visitor = legacy_guard._ApiKeyLookupVisitor(
        filename="app/routers/example.py",
        errors=errors,
        ownership_family=ownership_family,
        preserve_fastapi_conflicts=preservation_flags[0],
        preserve_lifecycle_conflicts=preservation_flags[1],
        preserve_route_method_conflicts=preservation_flags[2],
        reference_snapshots=reference_snapshots,
        string_snapshots=string_snapshots,
    )
    scope = legacy_guard._LexicalBindings(parent=None, local_names=frozenset({"masked"}))
    scope.references = dict(references)
    scope.strings = dict(strings)
    scope.callables = {"unused": frozenset({function})}
    scope.bound_names = {"member"}
    scope.possibly_bound_names = {"conditional"}
    visitor.scope = scope
    visitor._active_function_replays.add(function)
    visitor._remaining_loop_iterations = 17
    loop_controls = visitor._loop_controls

    visitor._record_snapshot(node)

    assert reference_snapshots[id(node)] == {
        "legacy": "legacy_app",
        "possible_legacy": "<possible:legacy_app>",
        "builtin": "builtins.getattr",
        "possible_builtin": "<possible:builtins.getattr>",
        "builtin_namespace": "<namespace:builtins>",
        "possible_builtin_namespace": "<possible:namespace:builtins>",
        "module_namespace": "<namespace:module>",
        "possible_object_namespace": "<possible:namespace:object>",
        "fastapi": "fastapi.FastAPI",
        "possible_fastapi": "<possible:fastapi>",
        "conflicted_fastapi": "<conflicted:fastapi>",
        "importer": "builtins.__import__",
        "possible_importer": "<possible:import_callable>",
        "possible_mutator": "<possible:namespace-mutator>.update",
        "safe": "math",
    }
    assert string_snapshots[id(node)] == {
        "header": "api_key_header",
        "getter": "get_api_key",
        "dynamic_getter": "_get_api_key_dynamic",
        "validator": "validate_app_api_key",
        "required": "require_app_api_key",
        "openapi": "_install_openapi_builder",
        "casefold": "debugOPENAPIhook",
        "possible_api_key": "<possible:api_key_symbol>",
        "possible_openapi": "<possible:openapi_symbol>",
        "route": "get",
        "possible_route": "<possible:route_method>",
        "conflicted_route": "<conflicted:route_method>",
        "empty": "",
        "state": "unchanged",
    }
    assert reference_snapshots[id(node)] is not saved_references
    assert string_snapshots[id(node)] is not saved_strings
    assert reference_snapshots[id(node)] is not scope.references
    assert string_snapshots[id(node)] is not scope.strings
    assert visitor.scope is scope
    assert visitor.errors is errors and errors == ["prior diagnostic"]
    assert scope.callables == {"unused": frozenset({function})}
    assert scope.local_names == frozenset({"masked"})
    assert scope.bound_names == {"member"}
    assert scope.possibly_bound_names == {"conditional"}
    assert visitor._active_function_replays == {function}
    assert visitor._remaining_loop_iterations == 17
    assert visitor._loop_controls is loop_controls and loop_controls == []


@pytest.mark.parametrize("ownership_family", ["api_key", "openapi"])
@pytest.mark.parametrize("snapshot_selection", ["references", "strings", "both"])
@pytest.mark.parametrize("populated", [False, True])
def test_consol_repeated_snapshot_preserves_equal_empty_and_selected_maps(
    ownership_family: Literal["api_key", "openapi"],
    snapshot_selection: str,
    populated: bool,
) -> None:
    node = cast(ast.Expr, ast.parse("member\n").body[0]).value
    reference_snapshots = (
        {id(node): {"receiver": "legacy_app"} if populated else {}}
        if snapshot_selection != "strings"
        else None
    )
    string_snapshots = (
        {id(node): {"member": "", "state": "unchanged"} if populated else {}}
        if snapshot_selection != "references"
        else None
    )
    visitor = legacy_guard._ApiKeyLookupVisitor(
        filename="app/routers/example.py",
        errors=[],
        ownership_family=ownership_family,
        reference_snapshots=reference_snapshots,
        string_snapshots=string_snapshots,
    )
    scope = legacy_guard._LexicalBindings(parent=None)
    scope.references = {"receiver": "legacy_app"} if populated else {}
    scope.strings = {"member": "", "state": "unchanged"} if populated else {}
    visitor.scope = scope

    visitor._record_snapshot(node)
    visitor._record_snapshot(node)

    if reference_snapshots is not None:
        assert reference_snapshots[id(node)] == ({"receiver": "legacy_app"} if populated else {})
    if string_snapshots is not None:
        assert string_snapshots[id(node)] == (
            {"member": "", "state": "unchanged"} if populated else {}
        )
    assert visitor.scope is scope
    assert visitor.errors == []


@pytest.mark.parametrize(
    "ownership_family,old_references,old_strings,new_references,new_strings,expected_references,expected_strings",
    [
        (
            "api_key",
            {"receiver": "legacy_app"},
            {"member": "get_api_key"},
            {"receiver": "legacy_app"},
            {"member": "other"},
            {"receiver": "legacy_app"},
            {"member": "<possible:api_key_symbol>"},
        ),
        (
            "api_key",
            {"receiver": "legacy_app"},
            {"member": "other"},
            {"receiver": "legacy_app"},
            {"member": "get_api_key"},
            {"receiver": "legacy_app"},
            {"member": "<possible:api_key_symbol>"},
        ),
        (
            "api_key",
            {"receiver": "legacy_app"},
            {"member": "get_api_key"},
            {"receiver": "math"},
            {"member": "get_api_key"},
            {"receiver": "<possible:legacy_app>"},
            {"member": "get_api_key"},
        ),
        (
            "api_key",
            {"receiver": "math"},
            {"member": "get_api_key"},
            {"receiver": "legacy_app"},
            {"member": "get_api_key"},
            {"receiver": "<possible:legacy_app>"},
            {"member": "get_api_key"},
        ),
        (
            "api_key",
            {"receiver": "legacy_app", "removed": "math"},
            {"member": "get_api_key", "removed": "other"},
            {"receiver": "legacy_app"},
            {"member": "get_api_key"},
            {"receiver": "legacy_app"},
            {"member": "get_api_key"},
        ),
        (
            "api_key",
            {},
            {},
            {"receiver": "legacy_app"},
            {"member": "get_api_key"},
            {"receiver": "<possible:legacy_app>"},
            {"member": "<possible:api_key_symbol>"},
        ),
        (
            "api_key",
            {"receiver": "legacy_app"},
            {"member": "get_api_key"},
            {},
            {},
            {"receiver": "<possible:legacy_app>"},
            {"member": "<possible:api_key_symbol>"},
        ),
        (
            "openapi",
            {"receiver": "legacy_app"},
            {"member": "debugOPENAPIhook"},
            {"receiver": "legacy_app"},
            {"member": "other"},
            {"receiver": "legacy_app"},
            {"member": "<possible:openapi_symbol>"},
        ),
        (
            "openapi",
            {"receiver": "legacy_app"},
            {"member": "other"},
            {"receiver": "legacy_app"},
            {"member": "debugOPENAPIhook"},
            {"receiver": "legacy_app"},
            {"member": "<possible:openapi_symbol>"},
        ),
        (
            "openapi",
            {"receiver": "legacy_app"},
            {"member": "_install_openapi_builder"},
            {"receiver": "math"},
            {"member": "_install_openapi_builder"},
            {"receiver": "<possible:legacy_app>"},
            {"member": "_install_openapi_builder"},
        ),
        (
            "openapi",
            {"receiver": "math"},
            {"member": "_install_openapi_builder"},
            {"receiver": "legacy_app"},
            {"member": "_install_openapi_builder"},
            {"receiver": "<possible:legacy_app>"},
            {"member": "_install_openapi_builder"},
        ),
        (
            "openapi",
            {"receiver": "legacy_app", "removed": "math"},
            {"member": "_install_openapi_builder", "removed": "other"},
            {"receiver": "legacy_app"},
            {"member": "_install_openapi_builder"},
            {"receiver": "legacy_app"},
            {"member": "_install_openapi_builder"},
        ),
        (
            "openapi",
            {},
            {},
            {"receiver": "legacy_app"},
            {"member": "_install_openapi_builder"},
            {"receiver": "<possible:legacy_app>"},
            {"member": "<possible:openapi_symbol>"},
        ),
        (
            "openapi",
            {"receiver": "legacy_app"},
            {"member": "_install_openapi_builder"},
            {},
            {},
            {"receiver": "<possible:legacy_app>"},
            {"member": "<possible:openapi_symbol>"},
        ),
    ],
)
def test_consol_repeated_snapshot_keeps_unequal_and_missing_key_conservative_results(
    ownership_family: Literal["api_key", "openapi"],
    old_references: dict[str, str],
    old_strings: dict[str, str],
    new_references: dict[str, str],
    new_strings: dict[str, str],
    expected_references: dict[str, str],
    expected_strings: dict[str, str],
) -> None:
    node = cast(ast.Expr, ast.parse("member\n").body[0]).value
    reference_snapshots = {id(node): dict(old_references)}
    string_snapshots = {id(node): dict(old_strings)}
    visitor = legacy_guard._ApiKeyLookupVisitor(
        filename="app/routers/example.py",
        errors=[],
        ownership_family=ownership_family,
        reference_snapshots=reference_snapshots,
        string_snapshots=string_snapshots,
    )
    scope = legacy_guard._LexicalBindings(parent=None)
    scope.references = dict(new_references)
    scope.strings = dict(new_strings)
    visitor.scope = scope

    visitor._record_snapshot(node)

    assert reference_snapshots[id(node)] == expected_references
    assert string_snapshots[id(node)] == expected_strings
    assert scope.references == new_references
    assert scope.strings == new_strings
    assert visitor.scope is scope
    assert visitor.errors == []


@pytest.mark.parametrize("ownership_family", ["api_key", "openapi"])
@pytest.mark.parametrize("snapshot_selection", ["references", "strings", "both", "neither"])
def test_consol_first_snapshot_keeps_missing_node_separate_from_empty_observation(
    ownership_family: Literal["api_key", "openapi"],
    snapshot_selection: str,
) -> None:
    tree = ast.parse("member\nother\n")
    node = cast(ast.Expr, tree.body[0]).value
    other = cast(ast.Expr, tree.body[1]).value
    reference_snapshots = {id(other): {}} if snapshot_selection in {"references", "both"} else None
    string_snapshots = {id(other): {}} if snapshot_selection in {"strings", "both"} else None
    visitor = legacy_guard._ApiKeyLookupVisitor(
        filename="app/routers/example.py",
        errors=[],
        ownership_family=ownership_family,
        reference_snapshots=reference_snapshots,
        string_snapshots=string_snapshots,
    )
    scope = legacy_guard._LexicalBindings(parent=None)
    scope.references = {"receiver": "legacy_app"}
    scope.strings = {"member": "get_api_key", "schema": "_install_openapi_builder"}
    visitor.scope = scope

    visitor._record_snapshot(node)

    if reference_snapshots is not None:
        assert reference_snapshots == {id(other): {}, id(node): {"receiver": "legacy_app"}}
    if string_snapshots is not None:
        assert string_snapshots == {
            id(other): {},
            id(node): {"member": "get_api_key", "schema": "_install_openapi_builder"},
        }
    assert visitor.scope is scope
    assert visitor.errors == []


@pytest.mark.parametrize("ownership_family", ["api_key", "openapi"])
@pytest.mark.parametrize("snapshot_selection", ["references", "strings", "both"])
def test_consol_repeated_snapshot_detaches_parent_and_local_masked_environments(
    ownership_family: Literal["api_key", "openapi"],
    snapshot_selection: str,
) -> None:
    node = cast(ast.Expr, ast.parse("member\n").body[0]).value
    parent = legacy_guard._LexicalBindings(parent=None)
    parent.references = {"inherited": "legacy_app", "masked": "legacy_app"}
    parent.strings = {"member": "get_api_key", "masked": "get_api_key"}
    scope = legacy_guard._LexicalBindings(
        parent=parent,
        local_names=frozenset({"masked"}),
        scope_kind="function",
    )
    scope.references = {"receiver": "legacy_app.__dict__"}
    scope.strings = {"local": "unchanged"}
    old_references = {"inherited": "legacy_app", "receiver": "legacy_app.__dict__"}
    old_strings = {"member": "get_api_key", "local": "unchanged"}
    reference_snapshots = {id(node): old_references} if snapshot_selection != "strings" else None
    string_snapshots = {id(node): old_strings} if snapshot_selection != "references" else None
    visitor = legacy_guard._ApiKeyLookupVisitor(
        filename="app/routers/example.py",
        errors=[],
        ownership_family=ownership_family,
        reference_snapshots=reference_snapshots,
        string_snapshots=string_snapshots,
    )
    visitor.scope = scope

    visitor._record_snapshot(node)
    parent.references["inherited"] = "math"
    parent.strings["member"] = "other"
    scope.references["receiver"] = "math.__dict__"
    scope.strings["local"] = "changed"

    if reference_snapshots is not None:
        assert reference_snapshots[id(node)] == {
            "inherited": "legacy_app",
            "receiver": "legacy_app.__dict__",
        }
        assert reference_snapshots[id(node)] is not old_references
    if string_snapshots is not None:
        assert string_snapshots[id(node)] == {"member": "get_api_key", "local": "unchanged"}
        assert string_snapshots[id(node)] is not old_strings
    assert old_references == {"inherited": "legacy_app", "receiver": "legacy_app.__dict__"}
    assert old_strings == {"member": "get_api_key", "local": "unchanged"}
    assert visitor.scope is scope and scope.parent is parent
    assert scope.local_names == frozenset({"masked"})
    assert scope.resolve_reference("masked") is None
    assert scope.resolve_string("masked") is None
    assert visitor.errors == []


@pytest.mark.parametrize("consumer", ["anext({operand})", "{operand}.__anext__()"])
@pytest.mark.parametrize("operand_kind", ["direct", "stored"])
@pytest.mark.parametrize(
    ("family", "member"),
    [
        (family, member)
        for family, members in (
            ("api", _CONSOL_API_KEY_SYMBOLS),
            ("openapi", (*_CONSOL_OPENAPI_SYMBOLS, "CustomOPENapiHook")),
        )
        for member in members
    ],
)
def test_consol_awaited_async_generator_consumers_cover_protected_inventory(
    family: str,
    member: str,
    consumer: str,
    operand_kind: str,
) -> None:
    operand = "access(legacy)" if operand_kind == "direct" else "stored"
    preparation = "" if operand_kind == "direct" else "    stored = access(legacy)\n"
    source = (
        "import asyncio\nimport legacy_app as legacy\n"
        f"async def access(owner):\n    yield owner.{member}\n"
        "async def driver():\n"
        + preparation
        + f"    await {consumer.format(operand=operand)}\nasyncio.run(driver())\n"
    )
    compile(source, "<immediate-async-generator-consumer>", "exec")
    if family == "api":
        assert _validate_api_key_dependency_ownership(
            _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
        ) == [
            "app/routers/example.py: legacy API-key dependency attribute access "
            f"is forbidden: {member}"
        ]
    else:
        assert _consol_openapi_errors(source) == [
            "app/main.py: OpenAPI symbol must not be accessed through legacy"
        ]


@pytest.mark.parametrize("family", ["api", "openapi"])
@pytest.mark.parametrize("operand_kind", ["direct", "stored"])
@pytest.mark.parametrize(
    ("prefix", "consumer"),
    [
        ("import builtins\n", "builtins.anext({operand})"),
        ("from builtins import anext as advance\n", "advance({operand})"),
        ("import builtins\nadvance = builtins.anext\n", "advance({operand})"),
    ],
)
def test_consol_async_generator_consumers_preserve_proven_alias_and_stored_receiver(
    family: str,
    operand_kind: str,
    prefix: str,
    consumer: str,
) -> None:
    member = "require_app_api_key" if family == "api" else "_install_openapi_builder"
    operand = "access(legacy)" if operand_kind == "direct" else "stored"
    preparation = "" if operand_kind == "direct" else "    stored = access(legacy)\n"
    source = (
        "import asyncio\nimport legacy_app as legacy\n"
        + prefix
        + f"async def access(owner):\n    yield owner.{member}\n"
        + "async def driver():\n"
        + preparation
        + f"    await {consumer.format(operand=operand)}\nasyncio.run(driver())\n"
    )
    compile(source, "<proven-anext-callee>", "exec")
    if family == "api":
        assert _validate_api_key_dependency_ownership(
            _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
        ) == [
            "app/routers/example.py: legacy API-key dependency attribute access "
            "is forbidden: require_app_api_key"
        ]
    else:
        assert _consol_openapi_errors(source) == [
            "app/main.py: OpenAPI symbol must not be accessed through legacy"
        ]


@pytest.mark.parametrize("family", ["api", "openapi"])
@pytest.mark.parametrize(
    ("prefix", "body", "invocation", "safe_body", "forbidden"),
    [
        ("", "    await anext(access(legacy))\n", "asyncio.run(driver())\n", True, False),
        ("", "    await access(legacy).__anext__()\n", "asyncio.run(driver())\n", True, False),
        ("", "    await anext(access(canonical))\n", "asyncio.run(driver())\n", False, False),
        ("", "    await access(canonical).__anext__()\n", "asyncio.run(driver())\n", False, False),
        ("", "    anext(access(legacy))\n", "asyncio.run(driver())\n", False, False),
        ("", "    access(legacy).__anext__()\n", "asyncio.run(driver())\n", False, False),
        ("", "    await anext(access(legacy))\n", "", False, False),
        ("", "    await access(legacy).__anext__()\n", "", False, False),
        (
            "async def anext(value):\n    return None\n",
            "    await anext(access(legacy))\n",
            "asyncio.run(driver())\n",
            False,
            False,
        ),
        (
            "",
            "    async def anext(value):\n        return None\n"
            "    await anext(access(legacy))\n",
            "asyncio.run(driver())\n",
            False,
            False,
        ),
        (
            "class Unrelated:\n    async def __anext__(self):\n        return None\n",
            "    await Unrelated().__anext__()\n",
            "asyncio.run(driver())\n",
            False,
            False,
        ),
        (
            "",
            "    async for item in access(legacy):\n        pass\n",
            "asyncio.run(driver())\n",
            False,
            True,
        ),
        (
            "async def read(owner):\n    return owner.{member}\n",
            "    await read(legacy)\n",
            "asyncio.run(driver())\n",
            False,
            True,
        ),
        (
            "async def anext(value):\n    return None\n",
            "    callback = anext\n    await callback(access(legacy))\n",
            "asyncio.run(driver())\n",
            False,
            False,
        ),
        (
            "async def shadow(value):\n    return None\n"
            "async def consume(anext):\n    await anext(access(legacy))\n",
            "    await consume(shadow)\n",
            "asyncio.run(driver())\n",
            False,
            False,
        ),
        (
            "import math as unrelated\n",
            "    await anext(access(unrelated))\n",
            "asyncio.run(driver())\n",
            False,
            False,
        ),
    ],
)
def test_consol_async_generator_consumers_keep_independent_safe_and_dormant_controls(
    family: str,
    prefix: str,
    body: str,
    invocation: str,
    safe_body: bool,
    forbidden: bool,
) -> None:
    member = "require_app_api_key" if family == "api" else "_install_openapi_builder"
    owner_module = "app.routers.api_key" if family == "api" else "app.bootstrap.openapi"
    yielded_member = "__name__" if safe_body else member
    source = (
        "import asyncio\nimport legacy_app as legacy\n"
        f"import {owner_module} as canonical\n"
        + prefix.format(member=member)
        + f"async def access(owner):\n    yield owner.{yielded_member}\n"
        + "async def driver():\n"
        + body
        + invocation
    )
    compile(source, "<async-consumer-independent-control>", "exec")
    if family == "api":
        expected = (
            [
                "app/routers/example.py: legacy API-key dependency attribute access "
                "is forbidden: require_app_api_key"
            ]
            if forbidden
            else []
        )
        assert (
            _validate_api_key_dependency_ownership(
                _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
            )
            == expected
        )
    else:
        expected = (
            ["app/main.py: OpenAPI symbol must not be accessed through legacy"] if forbidden else []
        )
        assert _consol_openapi_errors(source) == expected


@pytest.mark.parametrize("family", ["api", "openapi"])
@pytest.mark.parametrize("callee", ["anext", "advance"])
@pytest.mark.parametrize(
    ("lookup_kind", "initially_legacy", "aggregate_forbidden", "executed_forbidden"),
    [
        ("parameter", True, True, True),
        ("parameter", False, False, False),
        ("global", True, True, False),
        ("global", False, True, True),
    ],
)
def test_consol_async_generator_consumer_captures_receiver_before_default_effects(
    family: str,
    callee: str,
    lookup_kind: str,
    initially_legacy: bool,
    aggregate_forbidden: bool,
    executed_forbidden: bool,
) -> None:
    member = "require_app_api_key" if family == "api" else "_install_openapi_builder"
    owner_module = "app.routers.api_key" if family == "api" else "app.bootstrap.openapi"
    initial = "legacy" if initially_legacy else "canonical"
    replacement = "canonical" if initially_legacy else "legacy"
    receiver = "argument" if lookup_kind == "parameter" else "owner"
    source = (
        "import asyncio\nimport legacy_app as legacy\n"
        f"import {owner_module} as canonical\nowner = {initial}\nadvance = anext\n"
        "state = 'unchanged'\ncreation_state = 'unchanged'\n"
        "async def access(argument):\n    global state\n    state = state + 'B'\n"
        f"    yield {receiver}.{member}\n"
        "def operand():\n    global state\n    state = state + 'O'\n    return access(owner)\n"
        "def default():\n    global owner, state, advance\n    state = state + 'D'\n"
        "    advance = None\n"
        f"    owner = {replacement}\n    return None\n"
        "async def driver():\n    global creation_state\n    stored = operand()\n"
        f"    creation_state = state\n    await {callee}(stored, default())\nasyncio.run(driver())\n"
    )
    compile(source, "<async-generator-own-operand-default-order>", "exec")
    tree = ast.parse(source)
    reference_snapshots: dict[int, dict[str, str]] = {}
    string_snapshots: dict[int, dict[str, str]] = {}
    visitor = legacy_guard._ApiKeyLookupVisitor(
        filename="app/routers/example.py",
        errors=[],
        analyze_function_bodies=False,
        reference_snapshots=reference_snapshots,
        string_snapshots=string_snapshots,
    )
    original_scope = visitor.scope
    remaining_iterations = visitor._remaining_loop_iterations
    visitor.visit(tree)
    assert visitor.scope.resolve_string("creation_state") == "unchangedO"
    assert visitor.scope.resolve_string("state") == "unchangedODB"
    lookup = next(
        node for node in ast.walk(tree) if isinstance(node, ast.Attribute) and node.attr == member
    )
    assert isinstance(lookup.value, ast.Name)
    assert id(lookup.value) in reference_snapshots and id(lookup.value) in string_snapshots
    expected_receiver = "legacy_app" if executed_forbidden else owner_module
    assert reference_snapshots[id(lookup.value)][receiver] == expected_receiver
    assert string_snapshots[id(lookup.value)]["state"] == "unchangedODB"
    ordinary_errors = (
        [
            "app/routers/example.py: legacy API-key dependency attribute access "
            "is forbidden: require_app_api_key"
        ]
        if family == "api" and executed_forbidden
        else []
    )
    assert visitor.errors == ordinary_errors
    assert visitor.scope is original_scope
    assert visitor._remaining_loop_iterations == remaining_iterations
    assert visitor._active_function_replays == set()
    assert visitor._awaited_call_ids == set()
    assert visitor._iterated_call_ids == set()
    if family == "api":
        expected = (
            [
                "app/routers/example.py: legacy API-key dependency attribute access "
                "is forbidden: require_app_api_key"
            ]
            if aggregate_forbidden
            else []
        )
        assert (
            _validate_api_key_dependency_ownership(
                _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
            )
            == expected
        )
    else:
        expected = (
            ["app/main.py: OpenAPI symbol must not be accessed through legacy"]
            if aggregate_forbidden
            else []
        )
        assert _consol_openapi_errors(source) == expected


@pytest.mark.parametrize(
    ("family", "member"),
    [
        pytest.param(
            family,
            member,
            id=f"{family}-{member}",
            marks=pytest.mark.skipif(
                sys.version_info < (3, 12),
                reason="PEP 695 generic declaration syntax requires Python 3.12 or newer",
            ),
        )
        for family, members in (
            ("api", _CONSOL_API_KEY_SYMBOLS),
            ("openapi", (*_CONSOL_OPENAPI_SYMBOLS, "CustomOPENapiHook")),
        )
        for member in members
    ],
)
def test_consol_type_alias_declared_parameters_mask_outer_legacy_inventory(
    family: str,
    member: str,
) -> None:
    source = f"import legacy_app as legacy\ntype Alias[legacy] = legacy.{member}\n"
    compile(source, "<type-alias-receiver-mask>", "exec")
    if family == "api":
        assert (
            _validate_api_key_dependency_ownership(
                _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
            )
            == []
        )
    else:
        assert _consol_openapi_errors(source) == []


@pytest.mark.parametrize(
    "family",
    [
        pytest.param(
            family,
            marks=pytest.mark.skipif(
                sys.version_info < (3, 12),
                reason="PEP 695 generic declaration syntax requires Python 3.12 or newer",
            ),
        )
        for family in ("api", "openapi")
    ],
)
@pytest.mark.parametrize("projection", ["member", "member + ''"])
def test_consol_type_alias_member_parameter_keeps_closed_family_unknown_policy(
    family: str,
    projection: str,
) -> None:
    member = "get_api_key" if family == "api" else "_install_openapi_builder"
    source = (
        f"import legacy_app as legacy\nmember = '{member}'\n"
        f"type Alias[member] = getattr(legacy, {projection})\n"
    )
    compile(source, "<type-alias-member-mask>", "exec")
    tree = ast.parse(source)
    references, strings, _results = legacy_guard._collect_lexical_binding_snapshots(
        tree,
        filename="app/main.py",
        initial_references={},
        ownership_family="api_key" if family == "api" else "openapi",
        purpose="ownership_audit",
    )
    call = next(node for node in ast.walk(tree) if isinstance(node, ast.Call))
    member_node = (
        call.args[1] if isinstance(call.args[1], ast.Name) else cast(ast.BinOp, call.args[1]).left
    )
    assert id(member_node) in references and id(member_node) in strings
    assert "member" not in references[id(member_node)]
    assert "member" not in strings[id(member_node)]
    if family == "api":
        assert _validate_api_key_dependency_ownership(
            _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
        ) == (
            [
                "app/routers/example.py: dynamic legacy API-key dependency lookup is forbidden: <dynamic>"
            ]
            if projection != "member"
            else []
        )
    else:
        assert _consol_openapi_errors(source) == []


@pytest.mark.parametrize("family", ["api", "openapi"])
@pytest.mark.parametrize(
    ("declaration", "forbidden"),
    [
        pytest.param(
            declaration,
            forbidden,
            id=case_name,
            marks=pytest.mark.skipif(
                sys.version_info < minimum,
                reason=(
                    "PEP 696 type-parameter default syntax requires Python 3.13 or newer"
                    if minimum == (3, 13)
                    else "PEP 695 generic declaration syntax requires Python 3.12 or newer"
                ),
            ),
        )
        for case_name, declaration, forbidden, minimum in (
            ("plain-value", "type Alias = legacy.{member}\n", True, (3, 12)),
            ("generic-value", "type Alias[T] = legacy.{member}\n", True, (3, 12)),
            ("bound", "type Alias[T: legacy.{member}] = int\n", True, (3, 12)),
            ("constraints", "type Alias[T: (legacy.{member}, int)] = int\n", True, (3, 12)),
            ("default", "type Alias[T = legacy.{member}] = int\n", True, (3, 13)),
            ("masked-bound", "type Alias[legacy: legacy.{member}] = int\n", False, (3, 12)),
            ("masked-default", "type Alias[legacy = legacy.{member}] = int\n", False, (3, 13)),
            ("safe-value", "type Alias[T] = canonical.{member}\n", False, (3, 12)),
        )
    ],
)
def test_consol_type_alias_lazy_bounds_defaults_and_unmasked_values_remain_audited(
    family: str,
    declaration: str,
    forbidden: bool,
) -> None:
    member = "require_app_api_key" if family == "api" else "_install_openapi_builder"
    owner_module = "app.routers.api_key" if family == "api" else "app.bootstrap.openapi"
    source = (
        "import legacy_app as legacy\n"
        + f"import {owner_module} as canonical\n"
        + declaration.format(member=member)
    )
    compile(source, "<type-alias-lazy-header-and-value>", "exec")
    if family == "api":
        expected = (
            [
                "app/routers/example.py: legacy API-key dependency attribute access "
                "is forbidden: require_app_api_key"
            ]
            if forbidden
            else []
        )
        assert (
            _validate_api_key_dependency_ownership(
                _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
            )
            == expected
        )
    else:
        expected = (
            ["app/main.py: OpenAPI symbol must not be accessed through legacy"] if forbidden else []
        )
        assert _consol_openapi_errors(source) == expected


@pytest.mark.parametrize("family", ["api", "openapi"])
@pytest.mark.parametrize(
    ("declaration", "forbidden"),
    [
        pytest.param(
            declaration,
            forbidden,
            id=case_name,
            marks=pytest.mark.skipif(
                sys.version_info < (3, 12),
                reason="PEP 695 generic declaration syntax requires Python 3.12 or newer",
            ),
        )
        for case_name, declaration, forbidden in (
            (
                "function-parameter",
                "def wrap(legacy):\n    type Alias[T] = legacy.{member}\n",
                False,
            ),
            ("function-global", "def wrap():\n    type Alias[T] = legacy.{member}\n", True),
            (
                "class-legacy-member",
                "class Holder:\n    owner = legacy\n    type Alias[T] = owner.{member}\n",
                True,
            ),
            (
                "class-safe-member",
                "class Holder:\n    owner = canonical\n    type Alias[T] = owner.{member}\n",
                False,
            ),
            (
                "class-parameter-mask",
                "class Holder:\n    owner = legacy\n    type Alias[owner] = owner.{member}\n",
                False,
            ),
            (
                "module-alias-binder",
                "import legacy_app as Alias\ntype Alias[T] = int\nlater = Alias.{member}\n",
                False,
            ),
            (
                "function-alias-binder",
                "def wrap():\n    import legacy_app as Alias\n    type Alias[T] = int\n    later = Alias.{member}\n",
                False,
            ),
            (
                "function-generic-parent",
                "def wrap[legacy]():\n    type Alias[T] = legacy.{member}\n",
                False,
            ),
            (
                "class-generic-parent",
                "class Holder[legacy]:\n    type Alias[T] = legacy.{member}\n",
                False,
            ),
        )
    ],
)
def test_consol_type_alias_containing_binder_and_actual_parent_visibility(
    family: str,
    declaration: str,
    forbidden: bool,
) -> None:
    member = "require_app_api_key" if family == "api" else "_install_openapi_builder"
    owner_module = "app.routers.api_key" if family == "api" else "app.bootstrap.openapi"
    source = (
        "import legacy_app as legacy\n"
        + f"import {owner_module} as canonical\n"
        + declaration.format(member=member)
    )
    compile(source, "<type-alias-containing-parent>", "exec")
    if family == "api":
        expected = (
            [
                "app/routers/example.py: legacy API-key dependency attribute access "
                "is forbidden: require_app_api_key"
            ]
            if forbidden
            else []
        )
        assert (
            _validate_api_key_dependency_ownership(
                _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
            )
            == expected
        )
    else:
        expected = (
            ["app/main.py: OpenAPI symbol must not be accessed through legacy"] if forbidden else []
        )
        assert _consol_openapi_errors(source) == expected


@pytest.mark.parametrize("family", ["api", "openapi"])
@pytest.mark.parametrize(
    ("declaration", "forbidden"),
    [
        pytest.param(
            declaration,
            forbidden,
            id=case_name,
            marks=pytest.mark.skipif(
                sys.version_info < minimum,
                reason=(
                    "PEP 696 type-parameter default syntax requires Python 3.13 or newer"
                    if minimum == (3, 13)
                    else "PEP 695 generic declaration syntax requires Python 3.12 or newer"
                ),
            ),
        )
        for case_name, declaration, forbidden, minimum in (
            (
                "separate-bound-default-value",
                "type Alias[T: contaminate(), U = owner.{member}] = owner.{member}\n",
                False,
                (3, 13),
            ),
            ("value-call", "type Alias[T] = contaminate()\n", False, (3, 12)),
            ("value-order", "type Alias[T] = (contaminate(), owner.{member})\n", True, (3, 12)),
            (
                "constraint-order",
                "type Alias[T: (contaminate(), owner.{member})] = int\n",
                True,
                (3, 12),
            ),
        )
    ],
)
def test_consol_type_alias_independent_lazy_audits_do_not_execute_or_share_effects(
    family: str,
    declaration: str,
    forbidden: bool,
) -> None:
    member = "require_app_api_key" if family == "api" else "_install_openapi_builder"
    owner_module = "app.routers.api_key" if family == "api" else "app.bootstrap.openapi"
    source = (
        "import legacy_app as legacy\n" + f"import {owner_module} as canonical\n"
        "owner = canonical\nstate = 'unchanged'\n"
        "def contaminate():\n    global owner, state\n    owner = legacy\n"
        "    state = 'changed'\n    return int\n"
        + declaration.format(member=member)
        + f"type Sibling[V] = owner.{member}\n"
    )
    compile(source, "<type-alias-independent-lazy-effects>", "exec")
    visitor = legacy_guard._ApiKeyLookupVisitor(
        filename="app/routers/example.py",
        errors=[],
        analyze_function_bodies=False,
    )
    visitor.visit(ast.parse(source))
    assert visitor.scope.resolve_string("state") == "unchanged"
    assert visitor.scope.resolve_reference("owner") == owner_module
    if family == "api":
        expected = (
            [
                "app/routers/example.py: legacy API-key dependency attribute access "
                "is forbidden: require_app_api_key"
            ]
            if forbidden
            else []
        )
        assert (
            _validate_api_key_dependency_ownership(
                _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
            )
            == expected
        )
    else:
        expected = (
            ["app/main.py: OpenAPI symbol must not be accessed through legacy"] if forbidden else []
        )
        assert _consol_openapi_errors(source) == expected


def test_consol_canonical_join_equal_reference_preserves_other_field_normalization() -> None:
    functions = ast.parse("def first():\n    pass\ndef second():\n    pass\n").body
    first = cast(ast.FunctionDef, functions[0])
    second = cast(ast.FunctionDef, functions[1])
    site = cast(ast.Dict, ast.parse("{}", mode="eval").body)
    shared_mapping = legacy_guard._StaticMapping(site, ())
    left_mapping = legacy_guard._StaticMapping(site, ())
    right_mapping = legacy_guard._StaticMapping(site, ())
    assert left_mapping == right_mapping and left_mapping is not right_mapping
    first_pending = legacy_guard._DeferredFunctionCall(first, ())
    second_pending = legacy_guard._DeferredFunctionCall(second, ())
    left = legacy_guard._LexicalBindings(parent=None)
    right = legacy_guard._LexicalBindings(parent=None)
    left.references = {"stable": "legacy_app"}
    right.references = {"stable": "legacy_app"}
    left.strings = {"member": "require_app_api_key"}
    right.strings = {"member": "ordinary"}
    left.callables = {"callback": frozenset({first})}
    right.callables = {"callback": frozenset({second})}
    left.deferred_calls = {"pending": frozenset({first_pending})}
    right.deferred_calls = {"pending": frozenset({second_pending})}
    left.mappings = {"shared": shared_mapping, "distinct": left_mapping}
    right.mappings = {"shared": shared_mapping, "distinct": right_mapping}
    left.class_references = {"class": frozenset({"First"})}
    right.class_references = {"class": frozenset({"Second"})}
    left.descriptors = {"callback": frozenset({(first, "staticmethod")})}
    left.iterable_elements = {
        "element": legacy_guard._ResolvedBinding("legacy_app", "require_app_api_key")
    }
    right.iterable_elements = {"element": legacy_guard._ResolvedBinding("legacy_app", "ordinary")}
    left.bound_names = {"shared", "left"}
    right.bound_names = {"shared", "right"}
    left.possibly_bound_names = {"shared", "left"}
    right.possibly_bound_names = {"shared", "right"}
    errors = ["prior diagnostic"]
    visitor = legacy_guard._ApiKeyLookupVisitor(filename="app/routers/example.py", errors=errors)
    incoming = visitor.scope
    remaining_iterations = visitor._remaining_loop_iterations

    visitor._merge_outcomes(incoming, [left, right])

    assert visitor.scope is incoming
    assert incoming.references == {"stable": "legacy_app"}
    assert incoming.strings == {"member": "<possible:api_key_symbol>"}
    assert incoming.callables == {"callback": frozenset({first, second})}
    assert incoming.deferred_calls == {"pending": frozenset({first_pending, second_pending})}
    assert incoming.mappings == {"shared": shared_mapping}
    assert incoming.mappings["shared"] is shared_mapping
    assert incoming.class_references == {"class": frozenset({"First", "Second"})}
    assert incoming.descriptors == {
        "callback": frozenset({(first, "staticmethod"), (second, "plain")})
    }
    assert incoming.iterable_elements == {
        "element": legacy_guard._ResolvedBinding("legacy_app", "<possible:api_key_symbol>")
    }
    assert incoming.bound_names == {"shared"}
    assert incoming.possibly_bound_names == {"shared", "left", "right"}
    assert visitor._remaining_loop_iterations == remaining_iterations
    assert visitor.errors is errors and errors == ["prior diagnostic"]
    assert left.references == right.references == {"stable": "legacy_app"}
    assert left.mappings["distinct"] is left_mapping
    assert right.mappings["distinct"] is right_mapping


@pytest.mark.parametrize("ownership_family", ["api_key", "openapi"])
@pytest.mark.parametrize("outcome_count", [1, 3])
def test_consol_reference_component_preserves_explicit_none_filter(
    outcome_count: int, ownership_family: Literal["api_key", "openapi"]
) -> None:
    member = "require_app_api_key" if ownership_family == "api_key" else "_install_openapi_builder"
    outcomes = [legacy_guard._LexicalBindings(parent=None) for _ in range(outcome_count)]
    for outcome in outcomes:
        # Preserve the existing defensive join behavior for an explicit absent value.
        outcome.references = cast(dict[str, str], {"stable": "legacy_app", "absent": None})
        outcome.strings = cast(dict[str, str], {"member": member, "absent": None})
    visitor = legacy_guard._ApiKeyLookupVisitor(
        filename="app/routers/example.py", errors=[], ownership_family=ownership_family
    )
    incoming = visitor.scope
    remaining_iterations = visitor._remaining_loop_iterations

    visitor._merge_outcomes(incoming, outcomes)

    assert visitor.scope is incoming
    assert incoming.references == {"stable": "legacy_app"}
    assert incoming.strings == {"member": member}
    assert visitor._remaining_loop_iterations == remaining_iterations
    assert visitor.errors == []
    assert all(
        outcome.references == {"stable": "legacy_app", "absent": None}
        and outcome.strings == {"member": member, "absent": None}
        for outcome in outcomes
    )


@pytest.mark.parametrize("family", ["api", "openapi"])
@pytest.mark.parametrize(
    ("receiver", "method", "arguments", "dynamic"),
    [
        pytest.param("vars(legacy)", "clear", "", True, id="vars-clear"),
        pytest.param("legacy.__dict__", "clear", "", True, id="dict-clear"),
        pytest.param("vars(legacy)", "popitem", "", True, id="popitem"),
        pytest.param("legacy.__dict__", "__delitem__", "{member!r}", False, id="delitem"),
        pytest.param("vars(legacy)", "__setitem__", "{member!r}, None", False, id="setitem"),
        pytest.param("legacy.__dict__", "pop", "{member!r}, None", False, id="pop"),
        pytest.param("vars(legacy)", "setdefault", "{member!r}, None", False, id="setdefault"),
        pytest.param("legacy.__dict__", "update", "{{{member!r}: None}}", False, id="update"),
        pytest.param("vars(legacy)", "__ior__", "{{{member!r}: None}}", False, id="ior"),
        pytest.param("legacy.__dict__", "__init__", "{member}=None", False, id="init"),
    ],
)
def test_consol_stored_namespace_mutators_preserve_existing_nine_operation_semantics(
    family: Literal["api", "openapi"],
    receiver: str,
    method: str,
    arguments: str,
    dynamic: bool,
) -> None:
    member = "require_app_api_key" if family == "api" else "_install_openapi_builder"
    source = (
        "import legacy_app as legacy\n"
        f"operate = {receiver}.{method}\n"
        f"operate({arguments.format(member=member)})\n"
    )
    compile(source, "<stored-nine-mutator-fixture>", "exec")
    if family == "api":
        displayed = "<dynamic>" if dynamic else member
        assert _validate_api_key_dependency_ownership(
            _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
        ) == [
            "app/routers/example.py: legacy API-key dependency namespace lookup "
            f"is forbidden: {displayed}"
        ]
    else:
        assert _consol_openapi_errors(source) == [
            "app/main.py: OpenAPI symbol must not be accessed through legacy"
        ]


@pytest.mark.parametrize("family", ["api", "openapi"])
@pytest.mark.parametrize(
    "statement",
    [
        pytest.param("operate = vars(legacy).update\noperate()\n", id="empty-update"),
        pytest.param("operate = legacy.__dict__.__init__\noperate()\n", id="empty-init"),
        pytest.param("operate = vars(legacy).__ior__\noperate({})\n", id="empty-ior"),
        pytest.param("operate = legacy.__dict__.__delitem__\noperate('ordinary')\n", id="safe-key"),
        pytest.param("operate = vars(legacy).update\noperate(ordinary=None)\n", id="safe-update"),
        pytest.param("namespace = {}\noperate = namespace.clear\noperate()\n", id="unrelated"),
        pytest.param(
            "def vars(owner):\n    return {}\noperate = vars(legacy).clear\noperate()\n",
            id="shadowed-vars",
        ),
    ],
)
def test_consol_stored_namespace_mutators_keep_empty_safe_and_unrelated_controls(
    family: Literal["api", "openapi"], statement: str
) -> None:
    source = "import legacy_app as legacy\n" + statement
    compile(source, "<stored-mutator-control-fixture>", "exec")
    if family == "api":
        assert (
            _validate_api_key_dependency_ownership(
                _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
            )
            == []
        )
    else:
        assert _consol_openapi_errors(source) == []


@pytest.mark.parametrize("family", ["api", "openapi"])
@pytest.mark.parametrize("initially_legacy", [False, True])
def test_consol_stored_namespace_mutator_callee_and_receiver_precede_argument_rebinding(
    family: Literal["api", "openapi"], initially_legacy: bool
) -> None:
    member = "require_app_api_key" if family == "api" else "_install_openapi_builder"
    initial = "vars(legacy)" if initially_legacy else "{}"
    replacement = "{}" if initially_legacy else "vars(legacy)"
    source = (
        "import legacy_app as legacy\n"
        f"namespace = {initial}\noperate = namespace.__delitem__\n"
        "def member():\n    global namespace, operate\n"
        f"    namespace = {replacement}\n    operate = namespace.__delitem__\n"
        f"    return {member!r}\noperate(member())\n"
    )
    compile(source, "<stored-mutator-own-callee-fixture>", "exec")
    if family == "api":
        expected = (
            [
                "app/routers/example.py: legacy API-key dependency namespace lookup "
                f"is forbidden: {member}"
            ]
            if initially_legacy
            else []
        )
        assert (
            _validate_api_key_dependency_ownership(
                _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
            )
            == expected
        )
    else:
        expected = (
            ["app/main.py: OpenAPI symbol must not be accessed through legacy"]
            if initially_legacy
            else []
        )
        assert _consol_openapi_errors(source) == expected


@pytest.mark.parametrize("family", ["api", "openapi"])
@pytest.mark.parametrize("consumer", ["sorted", "min", "max"])
def test_consol_known_key_consumers_replay_existing_ownership_callback(
    family: Literal["api", "openapi"], consumer: str
) -> None:
    member = "require_app_api_key" if family == "api" else "_install_openapi_builder"
    source = (
        "import legacy_app as legacy\ndef access(owner):\n"
        f"    return owner.{member}\n{consumer}([legacy], key=access)\n"
    )
    compile(source, "<known-key-callback-fixture>", "exec")
    if family == "api":
        assert _validate_api_key_dependency_ownership(
            _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
        ) == [
            "app/routers/example.py: legacy API-key dependency attribute access "
            "is forbidden: require_app_api_key"
        ]
    else:
        assert _consol_openapi_errors(source) == [
            "app/main.py: OpenAPI symbol must not be accessed through legacy"
        ]


@pytest.mark.parametrize("family", ["api", "openapi"])
@pytest.mark.parametrize(
    ("setup", "invocation"),
    [
        pytest.param("", "sorted([], key=access)", id="proven-empty"),
        pytest.param("", "min([], key=access, default=None)", id="empty-default"),
        pytest.param("", "max([legacy], key=None)", id="none-key"),
        pytest.param("", "sorted([canonical], key=access)", id="unrelated-input"),
        pytest.param(
            "def sorted(iterable, key):\n    return iterable\n",
            "sorted([legacy], key=access)",
            id="shadowed-consumer",
        ),
        pytest.param(
            "def access(owner):\n    return owner.ordinary\n",
            "max([legacy], key=access)",
            id="safe-member",
        ),
    ],
)
def test_consol_known_key_consumers_keep_execution_and_safe_controls(
    family: Literal["api", "openapi"], setup: str, invocation: str
) -> None:
    member = "require_app_api_key" if family == "api" else "_install_openapi_builder"
    owner = "app.routers.api_key" if family == "api" else "app.bootstrap.openapi"
    source = (
        "import legacy_app as legacy\n"
        f"import {owner} as canonical\ndef access(owner):\n    return owner.{member}\n"
        + setup
        + invocation
        + "\n"
    )
    compile(source, "<known-key-control-fixture>", "exec")
    if family == "api":
        assert (
            _validate_api_key_dependency_ownership(
                _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
            )
            == []
        )
    else:
        assert _consol_openapi_errors(source) == []


@pytest.mark.parametrize("family", ["api", "openapi"])
@pytest.mark.parametrize(
    ("setup", "invocation", "forbidden"),
    [
        pytest.param(
            "owner = legacy\ndef select():\n    global owner\n"
            "    owner = canonical\n    return access\n",
            "sorted([owner], key=select())",
            True,
            id="input-before-key-effects",
        ),
        pytest.param(
            "def change():\n    global access\n    access = identity\n    return False\n",
            "sorted([legacy], key=access, reverse=change())",
            True,
            id="key-before-later-keyword",
        ),
        pytest.param(
            "pick = identity\ndef change():\n    global pick\n"
            "    pick = access\n    return False\n",
            "sorted([legacy], key=pick, reverse=change())",
            False,
            id="safe-key-before-later-keyword",
        ),
    ],
)
def test_consol_known_key_consumers_preserve_input_and_key_evaluation_points(
    family: Literal["api", "openapi"], setup: str, invocation: str, forbidden: bool
) -> None:
    member = "require_app_api_key" if family == "api" else "_install_openapi_builder"
    owner = "app.routers.api_key" if family == "api" else "app.bootstrap.openapi"
    source = (
        "import legacy_app as legacy\n"
        f"import {owner} as canonical\ndef access(owner):\n    return owner.{member}\n"
        "def identity(owner):\n    return owner\n" + setup + invocation + "\n"
    )
    compile(source, "<known-key-own-order-fixture>", "exec")
    if family == "api":
        expected = (
            [
                "app/routers/example.py: legacy API-key dependency attribute access "
                "is forbidden: require_app_api_key"
            ]
            if forbidden
            else []
        )
        assert (
            _validate_api_key_dependency_ownership(
                _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
            )
            == expected
        )
    else:
        expected = (
            ["app/main.py: OpenAPI symbol must not be accessed through legacy"] if forbidden else []
        )
        assert _consol_openapi_errors(source) == expected


@pytest.mark.parametrize("family", ["api", "openapi"])
@pytest.mark.parametrize("consumer", ["sorted", "min", "max"])
def test_consol_key_returns_do_not_replace_consumer_input_result_provenance(
    family: Literal["api", "openapi"], consumer: str
) -> None:
    member = "require_app_api_key" if family == "api" else "_install_openapi_builder"
    owner = "app.routers.api_key" if family == "api" else "app.bootstrap.openapi"
    for input_legacy in (False, True):
        input_name = "legacy" if input_legacy else "canonical"
        key_return = "canonical" if input_legacy else "legacy"
        observation = (
            f"for selected in result:\n    value = selected.{member}\n"
            if consumer == "sorted"
            else f"value = result.{member}\n"
        )
        source = (
            "import legacy_app as legacy\n"
            f"import {owner} as canonical\ndef key(owner):\n    return {key_return}\n"
            f"result = {consumer}([{input_name}], key=key)\n" + observation
        )
        compile(source, "<key-return-result-separation-fixture>", "exec")
        if family == "api":
            expected = (
                [
                    "app/routers/example.py: legacy API-key dependency attribute access "
                    "is forbidden: require_app_api_key"
                ]
                if input_legacy
                else []
            )
            assert (
                _validate_api_key_dependency_ownership(
                    _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
                )
                == expected
            )
        else:
            expected = (
                ["app/main.py: OpenAPI symbol must not be accessed through legacy"]
                if input_legacy
                else []
            )
            assert _consol_openapi_errors(source) == expected


@pytest.mark.parametrize("family", ["api", "openapi"])
@pytest.mark.parametrize("consumer", ["min", "max"])
@pytest.mark.parametrize("input_legacy", [False, True])
def test_consol_min_max_variadic_key_replay_uses_input_bindings(
    family: Literal["api", "openapi"], consumer: Literal["min", "max"], input_legacy: bool
) -> None:
    member = "require_app_api_key" if family == "api" else "_install_openapi_builder"
    owner = "app.routers.api_key" if family == "api" else "app.bootstrap.openapi"
    first_input = "legacy" if input_legacy else "canonical"
    source = (
        "import legacy_app as legacy\n"
        f"import {owner} as canonical\ndef access(owner):\n"
        f"    value = owner.{member}\n    return 0\n"
        f"{consumer}({first_input}, canonical, key=access)\n"
    )
    compile(source, "<variadic-min-max-key-fixture>", "exec")
    if family == "api":
        expected = (
            [
                "app/routers/example.py: legacy API-key dependency attribute access "
                "is forbidden: require_app_api_key"
            ]
            if input_legacy
            else []
        )
        assert (
            _validate_api_key_dependency_ownership(
                _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
            )
            == expected
        )
    else:
        expected = (
            ["app/main.py: OpenAPI symbol must not be accessed through legacy"]
            if input_legacy
            else []
        )
        assert _consol_openapi_errors(source) == expected


@pytest.mark.parametrize("family", ["api", "openapi"])
@pytest.mark.parametrize("consumer", ["sorted", "min", "max"])
def test_consol_key_callback_runs_after_stored_deferred_iteration(
    family: Literal["api", "openapi"], consumer: str
) -> None:
    member = "require_app_api_key" if family == "api" else "_install_openapi_builder"
    owner_module = "app.routers.api_key" if family == "api" else "app.bootstrap.openapi"
    source = (
        "import legacy_app as legacy\n"
        f"import {owner_module} as canonical\nowner = canonical\ntrace = ''\n"
        "def elements():\n    global owner, trace\n"
        "    trace = trace + 'I'\n    owner = legacy\n    yield 0\n"
        "def access(item):\n    global trace\n    trace = trace + 'K'\n"
        f"    value = owner.{member}\n    return 0\n"
        f"pending = elements()\ncreation_trace = trace\n{consumer}(pending, key=access)\n"
    )
    compile(source, "<stored-generator-key-order-fixture>", "exec")
    tree = ast.parse(source)
    refs: dict[int, dict[str, str]] = {}
    strings: dict[int, dict[str, str]] = {}
    errors: list[str] = []
    visitor = legacy_guard._ApiKeyLookupVisitor(
        filename="app/routers/example.py",
        errors=errors,
        analyze_function_bodies=False,
        ownership_family="api_key" if family == "api" else "openapi",
        reference_snapshots=refs,
        string_snapshots=strings,
    )
    visitor.visit(tree)
    assert visitor.scope.resolve_string("creation_trace") == ""
    assert visitor.scope.resolve_string("trace") == "IK"
    lookup = next(
        node for node in ast.walk(tree) if isinstance(node, ast.Attribute) and node.attr == member
    )
    assert isinstance(lookup.value, ast.Name)
    assert refs[id(lookup.value)]["owner"] == "legacy_app"
    assert strings[id(lookup.value)]["trace"] == "IK"
    assert errors == (
        [
            "app/routers/example.py: legacy API-key dependency attribute access "
            "is forbidden: require_app_api_key"
        ]
        if family == "api"
        else []
    )


@pytest.mark.parametrize("ownership_family", ["api_key", "openapi"])
@pytest.mark.parametrize("outcome_order", ["forward", "reverse", "duplicate"])
@pytest.mark.parametrize(
    ("values", "expected", "flags"),
    [
        ((), None, (False, False, False)),
        ((None, None), None, (False, False, False)),
        (("", ""), "", (False, False, False)),
        (("ordinary", "other"), None, (False, False, False)),
        (("<possible:legacy_app>",) * 2, "<possible:legacy_app>", (False, False, False)),
        (("<namespace:builtins>", None), "<namespace:builtins>", (False, False, False)),
        (
            ("<namespace:builtins>", "<possible:namespace:builtins>", "<namespace:module>"),
            "<possible:namespace:object>",
            (False, False, False),
        ),
        (
            ("<possible:namespace:object>", None),
            "<possible:namespace:object>",
            (False, False, False),
        ),
        (("<namespace:module>", "ordinary"), None, (False, False, False)),
        (("<namespace:module>", "builtins.dict.pop"), "builtins.dict.pop", (False, False, False)),
        (
            ("<namespace:builtins>.pop", "<namespace:module>.pop"),
            "<possible:namespace-mutator>.pop",
            (False, False, False),
        ),
        (
            ("builtins.dict.pop", "<possible:namespace-mutator>.clear"),
            "<possible:namespace-mutator>.*",
            (False, False, False),
        ),
        (
            ("builtins.dict.future_custom", "ordinary"),
            "builtins.dict.future_custom",
            (False, False, False),
        ),
        (
            ("<possible:namespace-mutator>.future_custom", "pulseplate.app.router.include_router"),
            "<possible:pulseplate.app.call>",
            (False, False, False),
        ),
        (
            ("builtins.dict.pop", "pulseplate.app.middleware.decorator:future_custom"),
            "<possible:pulseplate.app.call>",
            (False, False, False),
        ),
        (("builtins.dict.pop", "importlib.import_module"), "builtins.dict.pop", (True, True, True)),
        (
            ("builtins.__import__", "fastapi.FastAPI"),
            "<possible:import_callable>",
            (True, True, True),
        ),
        (
            ("importlib.import_module", "<possible:import_callable>"),
            "<possible:import_callable>",
            (True, False, False),
        ),
        (("builtins.__import__", "fastapi.FastAPI"), "<possible:fastapi>", (False, True, False)),
        (("builtins.__import__", "fastapi.FastAPI"), None, (False, False, False)),
        (
            ("fastapi.applications.FastAPI", "builtins.getattr"),
            "<possible:fastapi>",
            (False, True, False),
        ),
        (
            ("<possible:fastapi>", "<conflicted:fastapi>"),
            "<possible:fastapi>",
            (False, True, False),
        ),
        (
            ("fastapi.FastAPI", "builtins.getattr"),
            "<possible:builtins.getattr>",
            (False, False, False),
        ),
        (("builtins.getattr", "legacy_app"), "<possible:builtins.getattr>", (True, True, True)),
        (
            ("<possible:builtins.getattr>", "ordinary"),
            "<possible:builtins.getattr>",
            (False, False, False),
        ),
        (
            ("legacy_app.future_custom", "<iterable:possible-app>"),
            "<possible:legacy_app>",
            (False, False, False),
        ),
        (("legacy_application", "ordinary"), None, (False, False, False)),
        (
            (
                "<mapping:possible-app>",
                "<mapping:possible-app-call>",
                "<iterable:possible-app>",
                "<iterable:possible-app-call>",
            ),
            "<mapping:possible-app>",
            (False, False, False),
        ),
        (
            (
                "<mapping:possible-app-call>",
                "<iterable:possible-app>",
                "<iterable:possible-app-call>",
            ),
            "<mapping:possible-app-call>",
            (False, False, False),
        ),
        (
            ("<iterable:possible-app>", "<iterable:possible-app-call>"),
            "<iterable:possible-app>",
            (False, False, False),
        ),
        (
            ("<iterable:possible-app-call>", "ordinary"),
            "<iterable:possible-app-call>",
            (False, False, False),
        ),
        (
            ("<iterable:possible-app>", "pulseplate.app.get"),
            "<iterable:possible-app>",
            (False, False, True),
        ),
        (
            (
                "pulseplate.app.router.post",
                "pulseplate.app.middleware.decorator:http",
                "pulseplate.app",
            ),
            "<possible:pulseplate.app.call>",
            (False, False, True),
        ),
        (
            ("pulseplate.app.middleware.decorator:future_custom", "pulseplate.app"),
            "pulseplate.app.middleware.decorator:future_custom",
            (False, False, True),
        ),
        (
            (
                "pulseplate.app.middleware.decorator:http",
                "pulseplate.app.middleware.decorator:other",
            ),
            "<possible:pulseplate.app.middleware.decorator>",
            (False, False, True),
        ),
        (
            (
                "pulseplate.app.middleware.decorator:http",
                "<possible:pulseplate.app.middleware.decorator>",
            ),
            "<possible:pulseplate.app.middleware.decorator>",
            (False, False, True),
        ),
        (
            ("pulseplate.app.middleware.decorator:http", "pulseplate.app"),
            "<possible:pulseplate.app>",
            (False, False, False),
        ),
        (
            ("pulseplate.app", "pulseplate.app.router"),
            "<possible:pulseplate.app>",
            (False, False, True),
        ),
        (
            ("pulseplate.app.router", "ordinary"),
            "<possible:pulseplate.app.router>",
            (False, False, False),
        ),
        (
            ("<possible:pulseplate.app.router>", "ordinary"),
            "<possible:pulseplate.app.router>",
            (False, False, False),
        ),
        (("pulseplate.app.future_custom", "ordinary"), None, (False, False, True)),
    ],
)
def test_consol_finite_join_reference_markers_preserve_priority_and_inputs(
    ownership_family: Literal["api_key", "openapi"],
    outcome_order: str,
    values: tuple[str | None, ...],
    expected: str | None,
    flags: tuple[bool, bool, bool],
) -> None:
    outcomes = [legacy_guard._LexicalBindings(parent=None) for _ in values]
    for outcome, value in zip(outcomes, values):
        outcome.references = {} if value is None else {"binding": value}
    originals = [dict(outcome.references) for outcome in outcomes]
    ordered = list(reversed(outcomes)) if outcome_order == "reverse" else outcomes
    if outcome_order == "duplicate":
        ordered = ordered + ordered
    errors = ["prior diagnostic"]
    visitor = legacy_guard._ApiKeyLookupVisitor(
        filename="app/routers/example.py",
        errors=errors,
        ownership_family=ownership_family,
        preserve_lifecycle_conflicts=flags[0],
        preserve_fastapi_conflicts=flags[1],
        preserve_route_method_conflicts=flags[2],
    )
    incoming = visitor.scope
    original_incoming_references = dict(incoming.references)
    remaining_iterations = visitor._remaining_loop_iterations

    visitor._merge_outcomes(incoming, ordered)

    assert visitor.scope is incoming
    assert incoming.references == (
        original_incoming_references
        if not ordered
        else ({} if expected is None else {"binding": expected})
    )
    assert [outcome.references for outcome in outcomes] == originals
    assert visitor.errors is errors and errors == ["prior diagnostic"]
    assert visitor._remaining_loop_iterations == remaining_iterations


@pytest.mark.parametrize("ownership_family", ["api_key", "openapi"])
@pytest.mark.parametrize("outcome_order", ["forward", "reverse", "duplicate"])
@pytest.mark.parametrize(
    ("values", "routes", "api_expected", "openapi_expected"),
    [
        ((None, None), False, None, None),
        (("", ""), True, "", ""),
        (("ordinary", "other"), True, None, None),
        (("get_api_key",) * 2, True, "get_api_key", "get_api_key"),
        (("require_app_api_key", None), False, "<possible:api_key_symbol>", None),
        (("_install_openapi_builder", None), False, None, "<possible:openapi_symbol>"),
        (
            ("require_app_api_key", "_install_openapi_builder"),
            False,
            "<possible:api_key_symbol>",
            "<possible:openapi_symbol>",
        ),
        (("CUSTOM_OpEnApI_FUTURE", "ordinary"), False, None, "<possible:openapi_symbol>"),
        (("<possible:api_key_symbol>", "ordinary"), False, "<possible:api_key_symbol>", None),
        (("<possible:openapi_symbol>", "ordinary"), False, None, "<possible:openapi_symbol>"),
        (
            ("get", "require_app_api_key"),
            True,
            "<possible:route_method>",
            "<possible:route_method>",
        ),
        (
            ("include_router", "CUSTOM_OpEnApI_FUTURE"),
            True,
            "<possible:route_method>",
            "<possible:route_method>",
        ),
        (("get", "require_app_api_key"), False, "<possible:api_key_symbol>", None),
        (("post", "CUSTOM_OpEnApI_FUTURE"), False, None, "<possible:openapi_symbol>"),
        (
            ("<possible:route_method>", "<conflicted:route_method>"),
            True,
            "<possible:route_method>",
            "<possible:route_method>",
        ),
        (("<possible:route_method>", "<conflicted:route_method>"), False, None, None),
    ],
)
def test_consol_finite_join_string_markers_preserve_priority_and_inputs(
    ownership_family: Literal["api_key", "openapi"],
    outcome_order: str,
    values: tuple[str | None, ...],
    routes: bool,
    api_expected: str | None,
    openapi_expected: str | None,
) -> None:
    outcomes = [legacy_guard._LexicalBindings(parent=None) for _ in values]
    for outcome, value in zip(outcomes, values):
        outcome.strings = {} if value is None else {"binding": value}
    originals = [dict(outcome.strings) for outcome in outcomes]
    ordered = list(reversed(outcomes)) if outcome_order == "reverse" else outcomes
    if outcome_order == "duplicate":
        ordered = ordered + ordered
    visitor = legacy_guard._ApiKeyLookupVisitor(
        filename="app/routers/example.py",
        errors=[],
        ownership_family=ownership_family,
        preserve_route_method_conflicts=routes,
    )
    incoming = visitor.scope
    expected = api_expected if ownership_family == "api_key" else openapi_expected

    visitor._merge_outcomes(incoming, ordered)

    assert visitor.scope is incoming
    assert incoming.strings == ({} if expected is None else {"binding": expected})
    assert [outcome.strings for outcome in outcomes] == originals
    assert visitor.errors == []


@pytest.mark.parametrize("family", ["api", "openapi"])
@pytest.mark.parametrize(
    ("setup", "invocation", "forbidden"),
    [
        ("", "list(zip(map(access, [legacy])))", True),
        ("", "list(zip(filter(access, [legacy])))", True),
        ("import builtins as b\n", "list(b.zip(b.map(access, [legacy])))", True),
        ("", "list(zip(zip(map(access, [legacy]))))", True),
        ("", "zip(map(access, [legacy]))", False),
        ("", "list(zip(map(access, [])))", False),
        ("", "list(zip([], map(access, [legacy])))", False),
        ("", "list(zip(map(access, [legacy]), []))", True),
        ("", "list(zip(filter(access, [])))", False),
        ("", "list(zip(map(access, [canonical])))", False),
        (
            "def zip(*items):\n    return items\n",
            "list(zip(map(access, [legacy])))",
            False,
        ),
        (
            "def map(callback, items):\n    return items\n",
            "list(zip(map(access, [legacy])))",
            False,
        ),
        (
            "def filter(callback, items):\n    return items\n",
            "list(zip(filter(access, [legacy])))",
            False,
        ),
        (
            "def access(owner):\n    return owner.ordinary\n",
            "list(zip(map(access, [legacy])))",
            False,
        ),
        (
            "def access(owner):\n    yield owner.{member}\n",
            "list(zip(map(access, [legacy])))",
            False,
        ),
    ],
)
def test_consol_late3_zip_callbacks_preserve_consumption_and_controls(
    family: Literal["api", "openapi"], setup: str, invocation: str, forbidden: bool
) -> None:
    member = "require_app_api_key" if family == "api" else "_install_openapi_builder"
    owner = "app.routers.api_key" if family == "api" else "app.bootstrap.openapi"
    source = (
        "import legacy_app as legacy\n"
        f"import {owner} as canonical\ndef access(owner):\n    return owner.{member}\n"
        + setup.format(member=member)
        + invocation
        + "\n"
    )
    compile(source, "<late3-zip-control>", "exec")
    if family == "api":
        expected = (
            [
                "app/routers/example.py: legacy API-key dependency attribute access "
                "is forbidden: require_app_api_key"
            ]
            if forbidden
            else []
        )
        assert (
            _validate_api_key_dependency_ownership(
                _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
            )
            == expected
        )
    else:
        expected = (
            ["app/main.py: OpenAPI symbol must not be accessed through legacy"] if forbidden else []
        )
        assert _consol_openapi_errors(source) == expected


@pytest.mark.parametrize("family", ["api", "openapi"])
@pytest.mark.parametrize("mapper", ["map", "filter"])
@pytest.mark.parametrize("initially_legacy", [False, True])
def test_consol_late3_zip_captures_callback_and_input_before_later_creation_effects(
    family: Literal["api", "openapi"], mapper: str, initially_legacy: bool
) -> None:
    member = "require_app_api_key" if family == "api" else "_install_openapi_builder"
    owner = "app.routers.api_key" if family == "api" else "app.bootstrap.openapi"
    initial = "legacy" if initially_legacy else "canonical"
    replacement = "canonical" if initially_legacy else "legacy"
    source = (
        "import legacy_app as legacy\n"
        f"import {owner} as canonical\ntrace = ''\ninputs = [{initial}]\n"
        "def identity(item):\n    return item\n"
        "def access(item):\n    global trace\n    trace = trace + 'C'\n"
        f"    return item.{member}\npicked = access\n"
        "def later():\n    global trace, inputs, picked\n    trace = trace + 'L'\n"
        f"    inputs = [{replacement}]\n    picked = identity\n    return [0]\n"
        f"list(zip({mapper}(picked, inputs), later()))\n"
    )
    compile(source, "<late3-zip-creation-order>", "exec")
    visitor = legacy_guard._ApiKeyLookupVisitor(
        filename="app/routers/example.py",
        errors=[],
        analyze_function_bodies=False,
        ownership_family="api_key" if family == "api" else "openapi",
        purpose="ownership_audit",
    )
    visitor.visit(ast.parse(source))
    assert visitor.scope.resolve_string("trace") == "LC"
    if family == "api":
        expected = (
            [
                "app/routers/example.py: legacy API-key dependency attribute access "
                "is forbidden: require_app_api_key"
            ]
            if initially_legacy
            else []
        )
        assert (
            _validate_api_key_dependency_ownership(
                _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
            )
            == expected
        )
    else:
        expected = (
            ["app/main.py: OpenAPI symbol must not be accessed through legacy"]
            if initially_legacy
            else []
        )
        assert _consol_openapi_errors(source) == expected


@pytest.mark.parametrize("family", ["api", "openapi"])
@pytest.mark.parametrize("join_kind", ["expression", "statement"])
@pytest.mark.parametrize(
    ("method", "arguments", "dynamic"),
    [
        ("clear", "", True),
        ("popitem", "", True),
        ("__delitem__", "{member!r}", False),
        ("__setitem__", "{member!r}, None", False),
        ("pop", "{member!r}, None", False),
        ("setdefault", "{member!r}, None", False),
        ("update", "{{{member!r}: None}}", False),
        ("__ior__", "{{{member!r}: None}}", False),
        ("__init__", "{member}=None", False),
    ],
)
def test_consol_late3_joined_legacy_mutators_preserve_nine_method_semantics(
    family: Literal["api", "openapi"],
    join_kind: str,
    method: str,
    arguments: str,
    dynamic: bool,
) -> None:
    member = "require_app_api_key" if family == "api" else "_install_openapi_builder"
    selection = (
        f"    wipe = vars(legacy).{method} if flag else other\n"
        if join_kind == "expression"
        else f"    if flag:\n        wipe = vars(legacy).{method}\n    else:\n        wipe = other\n"
    )
    source = (
        "import legacy_app as legacy\ndef other(*args, **kwargs):\n    pass\n"
        "def mutate(flag):\n"
        + selection
        + f"    wipe({arguments.format(member=member)})\nmutate(True)\n"
    )
    compile(source, "<late3-joined-mutator>", "exec")
    visitor = legacy_guard._ApiKeyLookupVisitor(
        filename="app/routers/example.py", errors=[], analyze_function_bodies=False
    )
    visitor.visit(ast.parse(source))
    assert visitor.scope.resolve_reference("<state:builtins.object>") == "<safe:builtins.object>"
    if family == "api":
        displayed = "<dynamic>" if dynamic else member
        assert _validate_api_key_dependency_ownership(
            _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
        ) == [
            "app/routers/example.py: legacy API-key dependency namespace lookup "
            f"is forbidden: {displayed}"
        ]
    else:
        assert _consol_openapi_errors(source) == [
            "app/main.py: OpenAPI symbol must not be accessed through legacy"
        ]


@pytest.mark.parametrize("family", ["api", "openapi"])
@pytest.mark.parametrize(
    ("setup", "selection", "invocation", "forbidden"),
    [
        ("", "vars(legacy).clear if flag else vars(legacy).popitem", "wipe()", True),
        ("", "vars(legacy).update if flag else other", "wipe()", False),
        ("", "vars(legacy).__init__ if flag else other", "wipe()", False),
        ("", "vars(legacy).__ior__ if flag else other", "wipe({})", False),
        ("", "vars(legacy).__delitem__ if flag else other", "wipe('ordinary')", False),
        ("namespace = {}\n", "namespace.clear if flag else other", "wipe()", False),
        (
            "def vars(owner):\n    return {}\n",
            "vars(legacy).clear if flag else other",
            "wipe()",
            False,
        ),
        ("", "vars(legacy).clear if False else other", "wipe()", False),
    ],
)
def test_consol_late3_joined_mutators_keep_wildcard_and_independent_safe_controls(
    family: Literal["api", "openapi"],
    setup: str,
    selection: str,
    invocation: str,
    forbidden: bool,
) -> None:
    source = (
        "import legacy_app as legacy\ndef other(*args, **kwargs):\n    pass\n"
        + setup
        + f"def mutate(flag):\n    wipe = {selection}\n    {invocation}\nmutate(True)\n"
    )
    compile(source, "<late3-mutator-control>", "exec")
    if family == "api":
        expected = (
            [
                "app/routers/example.py: legacy API-key dependency namespace lookup "
                "is forbidden: <dynamic>"
            ]
            if forbidden
            else []
        )
        assert (
            _validate_api_key_dependency_ownership(
                _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
            )
            == expected
        )
    else:
        expected = (
            ["app/main.py: OpenAPI symbol must not be accessed through legacy"] if forbidden else []
        )
        assert _consol_openapi_errors(source) == expected


@pytest.mark.parametrize(
    ("addition", "expected"),
    [
        (
            "from app.routers.api_key import *\n",
            ["legacy_app.py: canonical API-key dependency star import is forbidden"],
        ),
        ("", []),
        ("from unrelated_module import *\n", []),
        ("note = 'from app.routers.api_key import *'\n", []),
    ],
)
def test_consol_late3_direct_api_owner_star_import_keeps_explicit_reexport_boundary(
    addition: str, expected: list[str]
) -> None:
    source = _CONSOL_GETTER_IMPORTS + addition
    compile(source, "<late3-canonical-star>", "exec")
    assert _validate_api_key_dependency_ownership(source, {}) == expected


@pytest.mark.parametrize("family", ["api", "openapi"])
@pytest.mark.parametrize("generator_first", [False, True])
def test_consol_late3_final2_zip_interleaves_generators_and_callbacks_in_argument_order(
    family: Literal["api", "openapi"], generator_first: bool
) -> None:
    member = "require_app_api_key" if family == "api" else "_install_openapi_builder"
    module = "app.routers.api_key" if family == "api" else "app.bootstrap.openapi"
    arguments = (
        "change_owner_generator(), map(access, [0])"
        if generator_first
        else "map(access, [0]), change_owner_generator()"
    )
    source = (
        "import legacy_app as legacy\n"
        f"import {module} as canonical\ntrace = ''\nowner = canonical\n"
        "def change_owner_generator():\n    global trace, owner\n"
        "    trace = trace + 'G'\n    owner = legacy\n    yield 0\n"
        "def access(item):\n    global trace\n    trace = trace + 'C'\n"
        f"    return owner.{member}\nlist(zip({arguments}))\n"
    )
    compile(source, "<final2-zip-generator-order>", "exec")
    visitor = legacy_guard._ApiKeyLookupVisitor(
        filename="app/routers/example.py",
        errors=[],
        analyze_function_bodies=False,
        ownership_family="api_key" if family == "api" else "openapi",
    )
    visitor.visit(ast.parse(source))
    assert visitor.scope.resolve_string("trace") == ("GC" if generator_first else "CG")
    # Full ownership admission also preserves required unused-definition evidence.
    if family == "api":
        assert _validate_api_key_dependency_ownership(
            _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
        ) == [
            "app/routers/example.py: legacy API-key dependency attribute access "
            "is forbidden: require_app_api_key"
        ]
    else:
        assert _consol_openapi_errors(source) == [
            "app/main.py: OpenAPI symbol must not be accessed through legacy"
        ]


@pytest.mark.parametrize("family", ["api", "openapi"])
@pytest.mark.parametrize("join_kind", ["expression", "statement"])
@pytest.mark.parametrize("legacy_candidate", [False, True])
def test_consol_late3_final2_mixed_unbound_mutator_preserves_legacy_and_safe_receiver(
    family: Literal["api", "openapi"], join_kind: str, legacy_candidate: bool
) -> None:
    first = "vars(legacy).clear" if legacy_candidate else "dict.clear"
    second = "dict.clear" if legacy_candidate else "other"
    selection = (
        f"    wipe = {first} if flag else {second}\n"
        if join_kind == "expression"
        else f"    if flag:\n        wipe = {first}\n    else:\n        wipe = {second}\n"
    )
    invocation = "wipe()" if legacy_candidate else "wipe({})"
    source = (
        "import legacy_app as legacy\ndef other(*args):\n    pass\ndef mutate(flag):\n"
        + selection
        + f"    {invocation}\nmutate(True)\n"
    )
    compile(source, "<final2-mixed-mutator>", "exec")
    visitor = legacy_guard._ApiKeyLookupVisitor(
        filename="app/routers/example.py", errors=[], analyze_function_bodies=False
    )
    visitor.visit(ast.parse(source))
    assert visitor.scope.resolve_reference("<state:builtins.object>") == "<safe:builtins.object>"
    if family == "api":
        expected = (
            [
                "app/routers/example.py: legacy API-key dependency namespace lookup "
                "is forbidden: <dynamic>"
            ]
            if legacy_candidate
            else []
        )
        assert (
            _validate_api_key_dependency_ownership(
                _CONSOL_GETTER_IMPORTS, {"app/routers/example.py": source}
            )
            == expected
        )
    else:
        expected = (
            ["app/main.py: OpenAPI symbol must not be accessed through legacy"]
            if legacy_candidate
            else []
        )
        assert _consol_openapi_errors(source) == expected


@pytest.mark.parametrize(
    ("values", "expected", "method"),
    [
        (
            ("legacy_app.__dict__.clear", "builtins.dict.clear"),
            "builtins.dict.<possible:legacy_app>.__dict__.clear",
            "clear",
        ),
        (
            ("legacy_app.__dict__.pop", "builtins.dict.clear"),
            "builtins.dict.<possible:legacy_app>.__dict__.*",
            "*",
        ),
        (
            ("legacy_app.__dict__.clear", "<namespace:builtins>.clear"),
            "<namespace:builtins>.<possible:legacy_app>.__dict__.clear",
            "clear",
        ),
        (
            ("legacy_app.__dict__.clear", "<namespace:module>.clear"),
            "<namespace:module>.<possible:legacy_app>.__dict__.clear",
            "clear",
        ),
        (
            ("legacy_app.__dict__.clear", "<namespace:builtins>.clear", "<namespace:module>.pop"),
            "<possible:namespace-mutator>.<possible:legacy_app>.__dict__.*",
            "*",
        ),
    ],
)
def test_consol_late3_final2_closed_qualified_join_keeps_both_method_provenances(
    values: tuple[str, ...], expected: str, method: str
) -> None:
    visitor = legacy_guard._ApiKeyLookupVisitor(filename="app/routers/example.py", errors=[])
    outcomes = [legacy_guard._LexicalBindings(parent=None) for _ in values]
    for outcome, value in zip(outcomes, values):
        outcome.references = {"wipe": value}
    incoming = visitor.scope
    visitor._merge_outcomes(incoming, outcomes)
    assert incoming.references == {"wipe": expected}
    assert [outcome.references for outcome in outcomes] == [{"wipe": value} for value in values]
    assert legacy_guard._namespace_mutator_method(expected) == method
    assert legacy_guard._namespace_mutator_method(expected, legacy_only=True) == method
    stable = legacy_guard._LexicalBindings(parent=None)
    stable.references = {"wipe": expected}
    visitor._merge_outcomes(incoming, [stable, legacy_guard._LexicalBindings(parent=None)])
    assert incoming.references == {"wipe": expected}
    assert (
        legacy_guard._namespace_mutator_method(
            "<possible:namespace-mutator>.clear", legacy_only=True
        )
        is None
    )
    assert legacy_guard._namespace_mutator_method("builtins.dict.clear", legacy_only=True) is None
    assert (
        legacy_guard._namespace_mutator_method("<namespace:builtins>.future_custom")
        == "future_custom"
    )
    assert (
        legacy_guard._namespace_mutator_method(
            "builtins.dict.<possible:legacy_app>.__dict__.future_custom"
        )
        is None
    )


@pytest.mark.parametrize(
    ("generic_method", "arguments", "builtin_state", "object_reference"),
    [
        (
            "vars(builtins).clear",
            "",
            "<poisoned:builtins.object>",
            "<captured-possible-app-factory>",
        ),
        (
            "globals().clear",
            "",
            "<safe:builtins.object>",
            "<captured-possible-app-factory>",
        ),
        (
            "dict.clear",
            "vars(builtins)",
            "<poisoned:builtins.object>",
            "<captured-possible-app-factory>",
        ),
        ("dict.clear", "", "<safe:builtins.object>", "builtins.object"),
    ],
)
def test_consol_late3_final2_mixed_namespace_effects_retain_generic_owner_semantics(
    generic_method: str, arguments: str, builtin_state: str, object_reference: str
) -> None:
    source = (
        "import builtins\nimport legacy_app as legacy\ndef mutate(flag):\n"
        f"    wipe = vars(legacy).clear if flag else {generic_method}\n"
        f"    wipe({arguments})\nmutate(True)\n"
    )
    compile(source, "<final2-mixed-namespace-effects>", "exec")
    visitor = legacy_guard._ApiKeyLookupVisitor(
        filename="app/routers/example.py", errors=[], analyze_function_bodies=False
    )
    visitor.visit(ast.parse(source))
    assert visitor.scope.resolve_reference("<state:builtins.object>") == builtin_state
    assert visitor.scope.resolve_reference("object") == object_reference
    assert visitor.errors == [
        "app/routers/example.py: legacy API-key dependency namespace lookup is forbidden: <dynamic>"
    ]
