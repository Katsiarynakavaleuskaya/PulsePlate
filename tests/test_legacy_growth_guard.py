from __future__ import annotations

import ast
import textwrap
from pathlib import Path

import pytest

import scripts.ci.check_legacy_growth_guard as legacy_guard

REPO_ROOT = Path(__file__).resolve().parents[1]

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
)

RETIRED_PRO_NUTRITION_BINDINGS = RETIRED_LEGACY_PYTHON_BINDINGS[10:20]
RETIRED_PLANNING_EXPORT_BINDINGS = RETIRED_LEGACY_PYTHON_BINDINGS[20:31]


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


@pytest.mark.parametrize("binding_name", RETIRED_PRO_NUTRITION_BINDINGS)
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

    assert legacy_guard.validate_retired_legacy_python_bindings(source) == [
        "legacy_app.py: star import is forbidden after legacy Python binding retirement"
    ]


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
            from app.bootstrap.openapi import (
                _OPENAPI_ALLOWED_EXACT,
                _OPENAPI_ALLOWED_PREFIXES,
                _build_canonical_openapi,
                _collect_schema_refs,
                _install_openapi_builder,
                _is_openapi_public_path,
                _prune_unreferenced_schema_components,
            )
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
            "missing_openapi_reexport",
            "canonical OpenAPI compatibility re-export must preserve identity",
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
    elif mutation_kind == "missing_openapi_reexport":
        sources[0] = sources[0].replace("    _install_openapi_builder,\n", "")
    else:
        sources[0] += "\nsetattr(app, 'openapi', replacement)\n"

    errors = legacy_guard.validate_application_metadata_openapi_ownership(*sources)

    assert any(expected_fragment in error for error in errors)


def test_metadata_openapi_ownership_guard_fails_closed_on_syntax_error() -> None:
    sources = list(_openapi_ownership_sources())
    sources[2] = "def broken(:\n"

    errors = legacy_guard.validate_application_metadata_openapi_ownership(*sources)

    assert errors == ["app/bootstrap/openapi.py:1: syntax error: invalid syntax"]


@pytest.mark.parametrize("symbol", ["get_api_key", "_get_api_key_dynamic"])
def test_api_key_ownership_guard_rejects_legacy_implementation(symbol: str) -> None:
    legacy_source = (
        "from app.routers.api_key import (\n"
        "    _get_api_key_dynamic as _get_api_key_dynamic,\n"
        "    get_api_key as get_api_key,\n"
        ")\n"
        f"def {symbol}():\n    return 'legacy'\n"
    )

    errors = legacy_guard.validate_api_key_dependency_ownership(legacy_source, {})

    assert errors == [f"legacy_app.py: API-key dependency must not be defined locally: {symbol}"]


@pytest.mark.parametrize("symbol", ["get_api_key", "_get_api_key_dynamic"])
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

    errors = legacy_guard.validate_api_key_dependency_ownership(legacy_source, {})

    assert errors == [
        f"legacy_app.py: canonical API-key compatibility re-export must not be rebound: {symbol}"
    ]


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

    assert legacy_guard.validate_api_key_dependency_ownership(legacy_source, {}) == [
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

    assert legacy_guard.validate_api_key_dependency_ownership(legacy_source, {}) == []


@pytest.mark.parametrize("keyword", ["def", "async def"])
@pytest.mark.parametrize("symbol", ["get_api_key", "_get_api_key_dynamic"])
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

    assert legacy_guard.validate_api_key_dependency_ownership(legacy_source, {}) == []


@pytest.mark.parametrize("keyword", ["def", "async def"])
@pytest.mark.parametrize("symbol", ["get_api_key", "_get_api_key_dynamic"])
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

    assert legacy_guard.validate_api_key_dependency_ownership(legacy_source, {}) == [
        f"legacy_app.py: API-key dependency must not be defined locally: {symbol}"
    ]


def test_legacy_growth_guard_rejects_api_key_header_reintroduction() -> None:
    errors = legacy_guard.validate_legacy_growth("from app.routers.api_key import api_key_header\n")

    assert errors == [
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:app.routers.api_key:api_key_header"
    ]


@pytest.mark.parametrize("symbol", ["get_api_key", "_get_api_key_dynamic"])
def test_api_key_ownership_guard_rejects_reverse_import(symbol: str) -> None:
    legacy_source = (
        "from app.routers.api_key import (\n"
        "    _get_api_key_dynamic as _get_api_key_dynamic,\n"
        "    get_api_key as get_api_key,\n"
        ")\n"
    )

    errors = legacy_guard.validate_api_key_dependency_ownership(
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

    errors = legacy_guard.validate_api_key_dependency_ownership(
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


@pytest.mark.parametrize("symbol", ["get_api_key", "_get_api_key_dynamic"])
def test_api_key_ownership_guard_rejects_legacy_module_attribute_access(symbol: str) -> None:
    legacy_source = (
        "from app.routers.api_key import (\n"
        "    _get_api_key_dynamic as _get_api_key_dynamic,\n"
        "    get_api_key as get_api_key,\n"
        ")\n"
    )

    errors = legacy_guard.validate_api_key_dependency_ownership(
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

    assert legacy_guard.validate_api_key_dependency_ownership(
        legacy_source,
        {"app/main.py": "from legacy_app import *\ndependency = get_api_key\n"},
    ) == ["app/main.py: canonical code must not use a legacy_app star import"]


def test_api_key_ownership_guard_rejects_legacy_namespace_lookup() -> None:
    legacy_source = "from app.routers.api_key import _get_api_key_dynamic, get_api_key\n"
    source = 'import legacy_app as legacy\ndependency = legacy.__dict__["get_api_key"]\n'

    assert legacy_guard.validate_api_key_dependency_ownership(
        legacy_source,
        {"app/main.py": source},
    ) == ["app/main.py: legacy API-key dependency namespace lookup is forbidden: get_api_key"]


def test_api_key_ownership_guard_allows_unrelated_star_import() -> None:
    legacy_source = (
        "from app.routers.api_key import (\n    _get_api_key_dynamic,\n    get_api_key,\n)\n"
    )

    assert (
        legacy_guard.validate_api_key_dependency_ownership(
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

    errors = legacy_guard.validate_api_key_dependency_ownership(
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

    assert legacy_guard.validate_api_key_dependency_ownership(
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
        legacy_guard.validate_api_key_dependency_ownership(legacy_source, {"app/main.py": source})
        == expected
    )
    assert (
        legacy_guard.validate_api_key_dependency_ownership(legacy_source, {"app/main.py": source})
        == expected
    )


def test_api_key_ownership_guard_rejects_maybe_legacy_conditional_alias() -> None:
    legacy_source = "from app.routers.api_key import _get_api_key_dynamic, get_api_key\n"
    source = "if enabled:\n" "    import legacy_app as legacy\n" "dependency = legacy.get_api_key\n"

    assert legacy_guard.validate_api_key_dependency_ownership(
        legacy_source, {"app/main.py": source}
    ) == ["app/main.py: legacy API-key dependency attribute access is forbidden: get_api_key"]


def test_api_key_ownership_guard_transfers_legacy_loop_target() -> None:
    legacy_source = "from app.routers.api_key import _get_api_key_dynamic, get_api_key\n"
    source = (
        "import importlib\n"
        'for legacy in [importlib.import_module("legacy_app")]:\n'
        "    dependency = legacy.get_api_key\n"
    )

    assert legacy_guard.validate_api_key_dependency_ownership(
        legacy_source, {"app/main.py": source}
    ) == ["app/main.py: legacy API-key dependency attribute access is forbidden: get_api_key"]


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

    assert legacy_guard.validate_api_key_dependency_ownership(
        legacy_source, {"app/main.py": source}
    ) == ["app/main.py: legacy API-key dependency attribute access is forbidden: get_api_key"]


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

    assert legacy_guard.validate_api_key_dependency_ownership(
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
        legacy_guard.validate_api_key_dependency_ownership(
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
        legacy_guard.validate_api_key_dependency_ownership(
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
        legacy_guard.validate_api_key_dependency_ownership(
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

    assert legacy_guard.validate_api_key_dependency_ownership(
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

    assert legacy_guard.validate_api_key_dependency_ownership(
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

    assert legacy_guard.validate_api_key_dependency_ownership(
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

    assert legacy_guard.validate_api_key_dependency_ownership(
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

    assert legacy_guard.validate_api_key_dependency_ownership(
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
        legacy_guard.validate_api_key_dependency_ownership(
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
        legacy_guard.validate_api_key_dependency_ownership(
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
        legacy_guard.validate_api_key_dependency_ownership(
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
        legacy_guard.validate_api_key_dependency_ownership(
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

    assert legacy_guard.validate_api_key_dependency_ownership(
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
        legacy_guard.validate_api_key_dependency_ownership(
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
    actual = legacy_guard.validate_api_key_dependency_ownership(
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

    assert legacy_guard.validate_api_key_dependency_ownership(
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

    assert legacy_guard.validate_api_key_dependency_ownership(
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

    assert legacy_guard.validate_api_key_dependency_ownership(
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

    assert legacy_guard.validate_api_key_dependency_ownership(
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

    assert legacy_guard.validate_api_key_dependency_ownership(
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

    assert legacy_guard.validate_api_key_dependency_ownership(
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

    assert legacy_guard.validate_api_key_dependency_ownership(
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

    assert legacy_guard.validate_api_key_dependency_ownership(
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

    assert legacy_guard.validate_api_key_dependency_ownership(
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

    assert legacy_guard.validate_api_key_dependency_ownership(
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

    assert legacy_guard.validate_api_key_dependency_ownership(
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
        legacy_guard.validate_api_key_dependency_ownership(
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

    assert legacy_guard.validate_api_key_dependency_ownership(
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

    assert legacy_guard.validate_api_key_dependency_ownership(
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
        legacy_guard.validate_api_key_dependency_ownership(
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
        legacy_guard.validate_api_key_dependency_ownership(
            legacy_source,
            {"app/main.py": source},
        )


def test_api_key_ownership_guard_enforces_global_loop_iteration_budget() -> None:
    legacy_source = "from app.routers.api_key import _get_api_key_dynamic, get_api_key\n"

    def source_with_loops(count: int) -> str:
        return "".join(f"for item_{index} in values:\n    pass\n" for index in range(count))

    assert (
        legacy_guard.validate_api_key_dependency_ownership(
            legacy_source,
            {"app/main.py": source_with_loops(128)},
        )
        == []
    )
    with pytest.raises(
        legacy_guard.LegacyGrowthAnalysisError,
        match=r"app/main.py: loop binding analysis exceeded 128 total iterations",
    ):
        legacy_guard.validate_api_key_dependency_ownership(
            legacy_source,
            {"app/main.py": source_with_loops(129)},
        )


def test_api_key_ownership_guard_preserves_budget_for_loop_body_bindings() -> None:
    legacy_source = "from app.routers.api_key import _get_api_key_dynamic, get_api_key\n"
    source = "".join(
        f"for item_{index} in values:\n    value_{index} = object()\n" for index in range(128)
    )

    assert (
        legacy_guard.validate_api_key_dependency_ownership(
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

    assert legacy_guard.validate_api_key_dependency_ownership(
        legacy_source, {"app/main.py": source}
    ) == ["app/main.py: legacy API-key dependency namespace lookup is forbidden: get_api_key"]


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

    assert legacy_guard.validate_api_key_dependency_ownership(
        legacy_source, {"app/main.py": source}
    ) == [f"app/main.py: {error_kind} is forbidden: <dynamic>"]


def test_api_key_ownership_guard_preserves_try_prefix_state_in_handler() -> None:
    legacy_source = "from app.routers.api_key import _get_api_key_dynamic, get_api_key\n"
    source = textwrap.dedent("""
        try:
            import legacy_app as legacy
            1 / 0
        except Exception:
            dependency = legacy.get_api_key
        """)

    assert legacy_guard.validate_api_key_dependency_ownership(
        legacy_source, {"app/main.py": source}
    ) == ["app/main.py: legacy API-key dependency attribute access is forbidden: get_api_key"]


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

    assert legacy_guard.validate_api_key_dependency_ownership(
        legacy_source, {"app/main.py": source}
    ) == ["app/main.py: legacy API-key dependency attribute access is forbidden: get_api_key"]


def test_api_key_ownership_guard_accepts_direct_identity_preserving_reexports() -> None:
    legacy_source = (
        "from app.routers.api_key import (\n    _get_api_key_dynamic,\n    get_api_key,\n)\n"
    )

    assert legacy_guard.validate_api_key_dependency_ownership(legacy_source, {}) == []


def test_api_key_ownership_guard_requires_module_level_reexports() -> None:
    legacy_source = textwrap.dedent("""
        def compatibility_imports():
            from app.routers.api_key import _get_api_key_dynamic, get_api_key
            return _get_api_key_dynamic, get_api_key
        """)

    assert legacy_guard.validate_api_key_dependency_ownership(legacy_source, {}) == [
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

    errors = legacy_guard.validate_api_key_dependency_ownership(
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
        legacy_guard.validate_api_key_dependency_ownership(
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

    assert legacy_guard.validate_api_key_dependency_ownership(
        legacy_source, {"app/main.py": source}
    ) == ["app/main.py: legacy API-key dependency attribute access is forbidden: get_api_key"]


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

    assert (
        legacy_guard.validate_api_key_dependency_ownership(legacy_source, {"app/main.py": source})
        == []
    )


def test_api_key_ownership_guard_rejects_single_alias_used_in_expression() -> None:
    legacy_source = (
        "from app.routers.api_key import (\n    _get_api_key_dynamic,\n    get_api_key,\n)\n"
    )
    source = "import legacy_app as legacy\ncompat = legacy\nregister(compat.get_api_key)\n"

    assert legacy_guard.validate_api_key_dependency_ownership(
        legacy_source, {"app/main.py": source}
    ) == ["app/main.py: legacy API-key dependency attribute access is forbidden: get_api_key"]


def test_api_key_ownership_guard_allows_safe_alias_used_in_expression() -> None:
    legacy_source = (
        "from app.routers.api_key import (\n    _get_api_key_dynamic,\n    get_api_key,\n)\n"
    )
    source = "import legacy_app as legacy\ncompat = object()\nregister(compat.get_api_key)\n"

    assert (
        legacy_guard.validate_api_key_dependency_ownership(legacy_source, {"app/main.py": source})
        == []
    )


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
    (tmp_path / "legacy_app.py").write_text("pass\n", encoding="utf-8")
    main_path = tmp_path / "app/main.py"
    main_path.parent.mkdir(parents=True)
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
