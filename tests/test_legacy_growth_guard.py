from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

import scripts.ci.check_legacy_growth_guard as legacy_guard

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_current_legacy_app_passes_growth_guard() -> None:
    source = (REPO_ROOT / "legacy_app.py").read_text(encoding="utf-8")

    assert legacy_guard.validate_legacy_growth(source) == []
    assert legacy_guard.ALLOWED_LEGACY_ROUTE_FACTS == frozenset()


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


def test_legacy_growth_guard_cli_passes(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = legacy_guard.main(["--repo-root", str(REPO_ROOT)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "legacy compatibility seam guard passed" in captured.out
