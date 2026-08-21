"""Repository policy guards - enforce import hygiene and architectural constraints.

These tests prevent regression of patterns that cause Dual Base, namespace conflicts,
and xdist failures.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Iterable, Iterator, Optional

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def _digest_literal(grouped: str) -> str:
    """Render a public SHA-256 test digest from low-entropy grouped text."""

    return grouped.replace("-", "")


_REGISTRATION_AUTHORITY_MANIFEST = {
    "schema_version": "registration_authority_manifest.v1",
    "source_path": "app/main.py",
    "bootstrap_owner": "ensure_canonical_app_bootstrap",
    "wrappers": [
        {
            "owner": "_register_paid_tier_routes",
            "parameter": "target_app",
            "bootstrap_argument": "app",
            "registrars": [
                {
                    "import_module": "app.routers.vip_registration",
                    "name": "register_vip_routes",
                },
                {
                    "import_module": "app.routers.pro_registration",
                    "name": "register_pro_routes",
                },
            ],
        },
        {
            "owner": "_register_bmi_routes",
            "parameter": "target_app",
            "bootstrap_argument": "app",
            "registrars": [
                {
                    "import_module": "app.routers.bmi_registration",
                    "name": "register_bmi_routes",
                },
            ],
        },
    ],
    "feature_flags": [
        "FEATURE_BMI_PRO_ENABLED",
        "FEATURE_PREMIUM_WEEK_ENABLED",
        "VIP_MODULE_ENABLED",
    ],
    "base_router_sources": [
        ["app.routers.pro", "router"],
        ["app.routers.pro_session", "router"],
        ["app.routers.pro_nutrition_insights", "router"],
        ["app.routers.pro_food_attribution", "router"],
        ["app.routers.pro_payments", "router"],
        ["app.routers.pro_restaurant_partner", "router"],
        ["app.routers.bmi", "router"],
    ],
    "conditional_router_sources": {
        "FEATURE_BMI_PRO_ENABLED": [
            ["app.routers.bmi_pro", "router"],
            ["app.routers.bmi_pro_legacy_alias", "router"],
        ],
        "FEATURE_PREMIUM_WEEK_EFFECTIVE": [
            ["app.routers.premium_week", "router"],
        ],
        "VIP_MODULE_ENABLED": [
            ["app.routers.fitchef_structured", "vip_router"],
            ["app.routers.fitchef_insight", "router"],
            ["app.routers.vip", "router"],
        ],
    },
    "feature_states": {
        "000": {
            "source_count": 22,
            "live_count": 22,
            "source_digest": _digest_literal(
                "948b-761f-9e6b-f8f5-c658-e9f4-981d-8945-2849-f9b2-ffe9-8e2a-4a89-8103-002e-6e3c"
            ),
            "live_digest": _digest_literal(
                "948b-761f-9e6b-f8f5-c658-e9f4-981d-8945-2849-f9b2-ffe9-8e2a-4a89-8103-002e-6e3c"
            ),
        },
        "001": {
            "source_count": 48,
            "live_count": 48,
            "source_digest": _digest_literal(
                "4a0a-a0fa-8579-4967-f0e8-81d7-7e70-636b-ea91-8e01-965a-fded-7656-ab0f-b502-3501"
            ),
            "live_digest": _digest_literal(
                "66ee-6f6a-3071-cf99-4b86-6a4c-2bac-aac5-17cc-eef4-e17e-e997-e6bb-235e-5a05-2dc9"
            ),
        },
        "010": {
            "source_count": 23,
            "live_count": 23,
            "source_digest": _digest_literal(
                "f035-9bb0-9359-bd97-56d9-855c-97fb-3963-9b0c-6fb3-85d4-3909-68e3-c3fe-5b31-1a28"
            ),
            "live_digest": _digest_literal(
                "f035-9bb0-9359-bd97-56d9-855c-97fb-3963-9b0c-6fb3-85d4-3909-68e3-c3fe-5b31-1a28"
            ),
        },
        "011": {
            "source_count": 48,
            "live_count": 48,
            "source_digest": _digest_literal(
                "4a0a-a0fa-8579-4967-f0e8-81d7-7e70-636b-ea91-8e01-965a-fded-7656-ab0f-b502-3501"
            ),
            "live_digest": _digest_literal(
                "66ee-6f6a-3071-cf99-4b86-6a4c-2bac-aac5-17cc-eef4-e17e-e997-e6bb-235e-5a05-2dc9"
            ),
        },
        "100": {
            "source_count": 25,
            "live_count": 25,
            "source_digest": _digest_literal(
                "aca7-1782-6794-a202-6607-d940-0fa9-5d81-d647-9bb0-dbe7-4f9e-b031-201d-feab-291b"
            ),
            "live_digest": _digest_literal(
                "aca7-1782-6794-a202-6607-d940-0fa9-5d81-d647-9bb0-dbe7-4f9e-b031-201d-feab-291b"
            ),
        },
        "101": {
            "source_count": 51,
            "live_count": 51,
            "source_digest": _digest_literal(
                "41c4-c769-beed-27c3-a48b-68b8-8058-e7bf-b74c-737e-e9c6-41d8-adad-e5fa-1a6c-fc53"
            ),
            "live_digest": _digest_literal(
                "bbb0-fbb4-2df9-b85d-e1a8-774a-de42-1b50-12c3-67da-458e-3c3b-a0d3-3d2b-3f56-1c44"
            ),
        },
        "110": {
            "source_count": 26,
            "live_count": 26,
            "source_digest": _digest_literal(
                "ec4b-22f3-3b2a-8fed-a6fe-c5c5-6a16-7791-bc06-9b0a-51d7-7dcd-9ca2-59b2-a2eb-8756"
            ),
            "live_digest": _digest_literal(
                "ec4b-22f3-3b2a-8fed-a6fe-c5c5-6a16-7791-bc06-9b0a-51d7-7dcd-9ca2-59b2-a2eb-8756"
            ),
        },
        "111": {
            "source_count": 51,
            "live_count": 51,
            "source_digest": _digest_literal(
                "41c4-c769-beed-27c3-a48b-68b8-8058-e7bf-b74c-737e-e9c6-41d8-adad-e5fa-1a6c-fc53"
            ),
            "live_digest": _digest_literal(
                "bbb0-fbb4-2df9-b85d-e1a8-774a-de42-1b50-12c3-67da-458e-3c3b-a0d3-3d2b-3f56-1c44"
            ),
        },
    },
}
_REGISTRATION_AUTHORITY_MANIFEST_SHA256 = _digest_literal(
    "9a1e-a098-a6c7-e248-23b2-d9b2-74b4-6842-e167-9670-704a-fc42-2aac-188a-5e55-71fd"
)

_REGISTRATION_AUTHORITY_MINIMAL_SOURCE = """
from app.routers.bmi_registration import register_bmi_routes
from app.routers.pro_registration import register_pro_routes
from app.routers.vip_registration import register_vip_routes

def _register_paid_tier_routes(target_app):
    register_vip_routes(target_app)
    register_pro_routes(target_app)

def _register_bmi_routes(target_app):
    register_bmi_routes(target_app)

def ensure_canonical_app_bootstrap(target_app):
    app = target_app
    _register_paid_tier_routes(app)
    _register_bmi_routes(app)
"""

_REGISTRATION_LIVE_MANIFEST_SCRIPT = r"""
import hashlib
import importlib
import json
import sys

from app.effective_routes import (
    iter_effective_route_candidates,
    route_endpoint,
    route_include_in_schema,
    route_methods,
    route_path,
)
import app.main as main

manifest = json.loads(sys.argv[1])
state = sys.argv[2]
mutation = sys.argv[3] if len(sys.argv) > 3 else "none"


def identity(value):
    if value is None:
        return None
    module = getattr(value, "__module__", type(value).__module__)
    qualname = getattr(
        value,
        "__qualname__",
        getattr(value, "__name__", type(value).__qualname__),
    )
    return f"{module}.{qualname}"


def dependency_ids(route):
    result = set()
    stack = list(getattr(getattr(route, "dependant", None), "dependencies", ()) or ())
    while stack:
        dependency = stack.pop()
        call = getattr(dependency, "call", None)
        if call is not None:
            result.add(identity(call))
        stack.extend(getattr(dependency, "dependencies", ()) or ())
    return sorted(result)


def route_row(route):
    return {
        "path": route_path(route),
        "methods": sorted(route_methods(route) - {"HEAD", "OPTIONS"}) or ["WEBSOCKET"],
        "endpoint": identity(route_endpoint(route)),
        "dependencies": dependency_ids(route),
        "include_in_schema": route_include_in_schema(route),
        "deprecated": bool(getattr(route, "deprecated", False)),
        "status_code": getattr(route, "status_code", None),
        "response_model": identity(getattr(route, "response_model", None)),
        "response_class": identity(getattr(route, "response_class", None)),
        "openapi_extra": getattr(route, "openapi_extra", None),
        "tags": list(getattr(route, "tags", None) or []),
    }


def rows_digest(rows):
    payload = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


source_specs = list(manifest["base_router_sources"])
conditional = manifest["conditional_router_sources"]
if state[0] == "1":
    source_specs.extend(conditional["FEATURE_BMI_PRO_ENABLED"])
if state[1] == "1" or state[2] == "1":
    source_specs.extend(conditional["FEATURE_PREMIUM_WEEK_EFFECTIVE"])
if state[2] == "1":
    source_specs.extend(conditional["VIP_MODULE_ENABLED"])

source_routes = []
for module_name, attribute in source_specs:
    router = getattr(importlib.import_module(module_name), attribute)
    source_routes.extend(iter_effective_route_candidates(router.routes))

source_rows = sorted(
    (route_row(route) for route in source_routes),
    key=lambda row: (row["path"], row["methods"], row["endpoint"]),
)
source_keys = {
    (method, row["path"])
    for row in source_rows
    for method in row["methods"]
}
live_candidates = list(iter_effective_route_candidates(main.app.routes))
if mutation == "foreign_duplicate":
    main.app.add_api_route(
        "/api/v1/bmi/calculate",
        lambda: None,
        methods=["POST"],
    )
    live_candidates = list(iter_effective_route_candidates(main.app.routes))
else:
    bmi_route = next(
        route
        for route in live_candidates
        if route_path(route) == "/api/v1/bmi/calculate"
        and "POST" in route_methods(route)
    )
    if mutation == "foreign_owner":
        bmi_route.endpoint = lambda: None
    elif mutation == "visibility":
        bmi_route.include_in_schema = not bmi_route.include_in_schema
    elif mutation == "response_status_metadata":
        bmi_route.status_code = 201
        bmi_route.response_model = dict[str, object]
    elif mutation == "dependency":
        guarded_route = next(
            route
            for route in live_candidates
            if any(
                (method, route_path(route)) in source_keys
                for method in route_methods(route)
            )
            and getattr(getattr(route, "dependant", None), "dependencies", None)
        )
        guarded_route.dependant.dependencies.clear()
    elif mutation != "none":
        raise AssertionError(f"unknown mutation: {mutation}")
live_rows = sorted(
    (
        route_row(route)
        for route in live_candidates
        if any((method, route_path(route)) in source_keys for method in route_methods(route))
    ),
    key=lambda row: (row["path"], row["methods"], row["endpoint"]),
)
result = {
    "source_count": len(source_rows),
    "live_count": len(live_rows),
    "source_digest": rows_digest(source_rows),
    "live_digest": rows_digest(live_rows),
    "source_rows": source_rows,
    "live_rows": live_rows,
}
print(json.dumps(result, sort_keys=True, separators=(",", ":")))
"""

_REGISTRATION_MANIFEST_SUMMARY_FIELDS = (
    "source_count",
    "live_count",
    "source_digest",
    "live_digest",
)

# --- Hard rules (policy) ---
FORBIDDEN_DYNAMIC_IMPORT_TOKENS = (
    "importlib.util.spec_from_file_location",
    "importlib.util.module_from_spec",
    "spec_from_file_location(",
    "module_from_spec(",
    "exec_module(",
)

FORBIDDEN_SYS_MODULES_TOKENS = (
    "sys.modules[",  # assignment/deletion (check context manually if needed)
)

FORBIDDEN_SYS_PATH_INSERT = "sys.path.insert"

# Allowed exceptions for dynamic imports / sys.path insert in tests
ALLOWED_TEST_FILES_FOR_DYNAMIC_IMPORT = {
    "tests/test_test_pro_access_coverage.py",
    "tests/test_ensure_database_versions.py",
    "tests/conftest.py",
    "tests/test_repo_policy_guards.py",  # this file (checks for these patterns)
    "tests/test_import_hygiene_guard.py",  # guard test
    "tests/test_app_public_surface.py",  # checks for spec_from_file_location string
}

ALLOWED_TEST_FILES_FOR_SYS_PATH_INSERT = {
    "tests/test_test_pro_access_coverage.py",
    "tests/conftest.py",
    "tests/test_repo_policy_guards.py",  # this file (checks for the pattern)
    "tests/test_import_hygiene_guard.py",  # guard test
}

# sys.modules checking in tests is allowed only for verification/guards
ALLOWED_SYS_MODULES_CHECK_FILES = {
    "tests/test_repo_policy_guards.py",  # this file
    "tests/conftest.py",  # sys.modules binding for app
}

ALLOWED_NUTRIMENTS_ACCESS_FILES = {
    "core/food_apis/openfoodfacts_client.py",
}

# If you intentionally allow a specific file later, add it to an allowlist above.


def _iter_py_files(relative_glob: str) -> Iterable[Path]:
    yield from REPO_ROOT.glob(relative_glob)


def _rel(p: Path) -> str:
    return p.relative_to(REPO_ROOT).as_posix()


_TRANSIENT_POLICY_SCAN_PATHS = (re.compile(r"^app/test_guard_.*_temp\.py$"),)


def _read(p: Path) -> Optional[str]:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        rel = _rel(p)
        if any(pattern.match(rel) for pattern in _TRANSIENT_POLICY_SCAN_PATHS):
            # xdist TOCTOU: transient helper files can disappear between glob and read.
            return None
        raise


def test_no_dynamic_imports_in_app_core() -> None:
    """Prevent re-introducing dynamic module exec in app/core code."""
    offenders: list[str] = []

    for path in list(_iter_py_files("app/**/*.py")) + list(_iter_py_files("core/**/*.py")):
        rel = _rel(path)
        content = _read(path)
        if content is None:
            continue
        if any(tok in content for tok in FORBIDDEN_DYNAMIC_IMPORT_TOKENS):
            offenders.append(rel)

    assert not offenders, f"Dynamic import tokens found in: {offenders}"


def test_no_sys_modules_mutation_in_repo() -> None:
    """sys.modules mutation is a common source of Dual Base / namespace bugs.

    This runtime guard checks only app/core/providers modules.
    Legacy test-scope cleanup is enforced incrementally in
    tests/test_repo_policy_sys_modules.py.
    """
    offenders: list[str] = []

    # Check for assignment: sys.modules[...] =
    assignment_pattern = r"sys\.modules\[[^]]+\]\s*="
    # Check for deletion: del sys.modules[...]
    deletion_pattern = r"del\s+sys\.modules\["

    for path in (
        list(_iter_py_files("app/**/*.py"))
        + list(_iter_py_files("core/**/*.py"))
        + list(_iter_py_files("providers/**/*.py"))
    ):
        rel = _rel(path)
        content = _read(path)
        if content is None:
            continue

        # Allow specific guard/verification files
        if rel in ALLOWED_SYS_MODULES_CHECK_FILES:
            continue

        if re.search(assignment_pattern, content) or re.search(deletion_pattern, content):
            offenders.append(rel)

    assert not offenders, f"sys.modules mutation found in: {offenders}"


def test_tests_have_no_dynamic_imports_except_whitelist() -> None:
    """Dynamic imports in tests cause module identity issues under xdist."""
    offenders: list[str] = []

    for path in _iter_py_files("tests/**/*.py"):
        rel = _rel(path)
        content = _read(path)
        if content is None:
            continue

        if any(tok in content for tok in FORBIDDEN_DYNAMIC_IMPORT_TOKENS):
            if rel not in ALLOWED_TEST_FILES_FOR_DYNAMIC_IMPORT:
                offenders.append(rel)

    assert (
        not offenders
    ), f"Dynamic imports are forbidden in tests except whitelist. Offenders: {offenders}"


def test_tests_have_no_sys_path_insert_except_whitelist() -> None:
    """sys.path.insert masks import errors and breaks xdist isolation."""
    offenders: list[str] = []

    for path in _iter_py_files("tests/**/*.py"):
        rel = _rel(path)
        content = _read(path)
        if content is None:
            continue

        if FORBIDDEN_SYS_PATH_INSERT in content:
            if rel not in ALLOWED_TEST_FILES_FOR_SYS_PATH_INSERT:
                offenders.append(rel)

    assert (
        not offenders
    ), f"sys.path.insert is forbidden in tests except whitelist. Offenders: {offenders}"


def test_app_init_is_import_shim_not_dynamic_loader() -> None:
    """app/__init__.py must not reintroduce the old dynamic loader."""
    init_path = REPO_ROOT / "app" / "__init__.py"
    assert init_path.exists(), "app/__init__.py missing"

    content = _read(init_path)
    assert content is not None, "app/__init__.py unexpectedly missing during read"
    banned = [tok for tok in FORBIDDEN_DYNAMIC_IMPORT_TOKENS if tok in content]
    assert not banned, f"app/__init__.py contains forbidden tokens: {banned}"


def test_app_facade_does_not_restore_arbitrary_legacy_fallthrough() -> None:
    """The package facade must remain finite and fail closed for unknown names."""
    content = _read(REPO_ROOT / "app" / "__init__.py")
    assert content is not None, "app/__init__.py unexpectedly missing during read"

    forbidden = ("getattr(_legacy(), name)", "dir(_legacy())")
    offenders = [token for token in forbidden if token in content]
    assert not offenders, f"Arbitrary legacy facade fallthrough restored: {offenders}"


def _canonical_json_digest(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def _direct_named_call(statement: ast.stmt) -> ast.Call | None:
    if not isinstance(statement, ast.Expr) or not isinstance(statement.value, ast.Call):
        return None
    if not isinstance(statement.value.func, ast.Name):
        return None
    return statement.value


def _is_exact_named_call(call: ast.Call, name: str, argument: str) -> bool:
    return (
        isinstance(call.func, ast.Name)
        and call.func.id == name
        and len(call.args) == 1
        and isinstance(call.args[0], ast.Name)
        and call.args[0].id == argument
        and not call.keywords
    )


def _registration_authority_violations(source: str) -> list[str]:
    """Return closed-grammar violations for canonical registrar authority."""

    tree = ast.parse(source, filename="app/main.py")
    violations: list[str] = []
    manifest = _REGISTRATION_AUTHORITY_MANIFEST
    wrappers = manifest["wrappers"]
    bootstrap_name = manifest["bootstrap_owner"]

    all_functions = [
        node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    top_level_functions = [
        node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]

    bootstrap_matches = [node for node in top_level_functions if node.name == bootstrap_name]
    if len(bootstrap_matches) != 1:
        violations.append(f"bootstrap_owner:{bootstrap_name}:{len(bootstrap_matches)}")
        bootstrap = None
    else:
        bootstrap = bootstrap_matches[0]
    if sum(node.name == bootstrap_name for node in all_functions) != 1:
        violations.append(f"bootstrap_scope:{bootstrap_name}")

    wrapper_calls: list[ast.Call] = []
    for wrapper in wrappers:
        owner = wrapper["owner"]
        parameter = wrapper["parameter"]
        registrars = wrapper["registrars"]
        owner_matches = [node for node in top_level_functions if node.name == owner]
        if len(owner_matches) != 1:
            violations.append(f"wrapper_owner:{owner}:{len(owner_matches)}")
            continue
        owner_node = owner_matches[0]
        if sum(node.name == owner for node in all_functions) != 1:
            violations.append(f"wrapper_scope:{owner}")

        arguments = owner_node.args
        if (
            [argument.arg for argument in arguments.args] != [parameter]
            or arguments.posonlyargs
            or arguments.kwonlyargs
            or arguments.vararg is not None
            or arguments.kwarg is not None
            or arguments.defaults
            or arguments.kw_defaults
        ):
            violations.append(f"wrapper_signature:{owner}")

        direct_calls = [_direct_named_call(statement) for statement in owner_node.body]
        expected_names = [registrar["name"] for registrar in registrars]
        if len(direct_calls) != len(expected_names) or any(
            call is None or not _is_exact_named_call(call, expected_name, parameter)
            for call, expected_name in zip(direct_calls, expected_names, strict=False)
        ):
            violations.append(f"wrapper_body:{owner}")

        for registrar in registrars:
            registrar_name = registrar["name"]
            import_module = registrar["import_module"]
            import_aliases = [
                (node, alias)
                for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom)
                for alias in node.names
                if alias.name == registrar_name
            ]
            if (
                len(import_aliases) != 1
                or import_aliases[0][0] not in tree.body
                or import_aliases[0][0].module != import_module
                or import_aliases[0][0].level != 0
                or import_aliases[0][1].asname is not None
            ):
                violations.append(f"registrar_import:{registrar_name}")

            all_calls = [
                node
                for node in ast.walk(tree)
                if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == registrar_name
            ]
            owner_calls = [
                call
                for call in direct_calls
                if call is not None
                and isinstance(call.func, ast.Name)
                and call.func.id == registrar_name
            ]
            if len(all_calls) != 1 or len(owner_calls) != 1 or all_calls[0] is not owner_calls[0]:
                violations.append(f"registrar_cardinality_scope:{registrar_name}")

            name_uses = [
                node
                for node in ast.walk(tree)
                if isinstance(node, ast.Name)
                and isinstance(node.ctx, ast.Load)
                and node.id == registrar_name
            ]
            if len(name_uses) != 1 or not isinstance(getattr(name_uses[0], "ctx", None), ast.Load):
                violations.append(f"registrar_indirect_use:{registrar_name}")
            if any(
                isinstance(node, ast.Attribute) and node.attr == registrar_name
                for node in ast.walk(tree)
            ) or any(
                isinstance(node, ast.Constant) and node.value == registrar_name
                for node in ast.walk(tree)
            ):
                violations.append(f"registrar_dynamic_use:{registrar_name}")

        owner_all_calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == owner
        ]
        bootstrap_calls = (
            [_direct_named_call(statement) for statement in bootstrap.body]
            if bootstrap is not None
            else []
        )
        owner_bootstrap_calls = [
            call
            for call in bootstrap_calls
            if call is not None and isinstance(call.func, ast.Name) and call.func.id == owner
        ]
        if (
            len(owner_all_calls) != 1
            or len(owner_bootstrap_calls) != 1
            or owner_all_calls[0] is not owner_bootstrap_calls[0]
            or not _is_exact_named_call(
                owner_bootstrap_calls[0],
                owner,
                wrapper["bootstrap_argument"],
            )
        ):
            violations.append(f"wrapper_bootstrap_cardinality_scope:{owner}")
        else:
            wrapper_calls.append(owner_bootstrap_calls[0])

        owner_name_uses = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id == owner
        ]
        if len(owner_name_uses) != 1:
            violations.append(f"wrapper_indirect_use:{owner}")
        if any(
            isinstance(node, ast.Attribute) and node.attr == owner for node in ast.walk(tree)
        ) or any(isinstance(node, ast.Constant) and node.value == owner for node in ast.walk(tree)):
            violations.append(f"wrapper_dynamic_use:{owner}")

    if bootstrap is not None and len(wrapper_calls) == len(wrappers):
        bootstrap_call_order = [
            call
            for statement in bootstrap.body
            if (call := _direct_named_call(statement)) is not None
        ]
        positions = [bootstrap_call_order.index(call) for call in wrapper_calls]
        if positions != sorted(positions) or len(set(positions)) != len(positions):
            violations.append("bootstrap_wrapper_order")

    return sorted(set(violations))


def test_paid_bmi_registration_mirrors_remain_retired() -> None:
    """Canonical bootstrap and legacy facade must not restore retired mirror bindings."""
    assert (
        _canonical_json_digest(_REGISTRATION_AUTHORITY_MANIFEST)
        == _REGISTRATION_AUTHORITY_MANIFEST_SHA256
    )
    retired = {
        "VIP_MODULE_ENABLED",
        "vip_router",
        "pro_router",
        "premium_week_router",
        "FEATURE_BMI_PRO_ENABLED",
        "bmi_router",
        "bmi_pro_router",
        "bmi_pro_legacy_alias_router",
    }

    for relative_path in ("app/main.py", "legacy_app.py"):
        content = _read(REPO_ROOT / relative_path)
        assert content is not None, f"{relative_path} unexpectedly missing during read"
        tree = ast.parse(content, filename=relative_path)
        bindings = {
            target.id
            for node in tree.body
            for target in (
                [node.target]
                if isinstance(node, ast.AnnAssign)
                else node.targets if isinstance(node, ast.Assign) else []
            )
            if isinstance(target, ast.Name)
        }
        assert retired.isdisjoint(bindings), (
            f"Retired registration mirrors restored in {relative_path}: "
            f"{sorted(retired & bindings)}"
        )

    main_content = _read(REPO_ROOT / "app" / "main.py")
    assert main_content is not None, "app/main.py unexpectedly missing during read"
    main_tree = ast.parse(main_content, filename="app/main.py")
    assert not any(
        isinstance(node, ast.Import)
        and any(alias.name == "legacy_app" for alias in node.names)
        or isinstance(node, ast.ImportFrom)
        and node.module == "legacy_app"
        for node in ast.walk(main_tree)
    )
    assert "_legacy_module" not in main_content
    assert "_mirror_paid_tier_registration_attrs" not in main_content
    assert "_mirror_bmi_registration_attrs" not in main_content
    assert not _registration_authority_violations(main_content)


def test_registration_authority_recognizer_ignores_lexical_decoys() -> None:
    source = _REGISTRATION_AUTHORITY_MINIMAL_SOURCE + """
# register_vip_routes(target_app)
LEXICAL_DECOY = "register_pro_routes(target_app)"
"""
    assert not _registration_authority_violations(source)


@pytest.mark.parametrize(
    "source",
    (
        _REGISTRATION_AUTHORITY_MINIMAL_SOURCE.replace(
            "    register_vip_routes(target_app)\n",
            "    register_vip_routes(target_app)\n    register_vip_routes(other_app)\n",
            1,
        ),
        _REGISTRATION_AUTHORITY_MINIMAL_SOURCE.replace(
            "    register_pro_routes(target_app)\n",
            "    register_pro_routes(target_app, enabled=True)\n",
            1,
        ),
        _REGISTRATION_AUTHORITY_MINIMAL_SOURCE
        + "\ndef unused():\n    register_bmi_routes(target_app)\n",
        _REGISTRATION_AUTHORITY_MINIMAL_SOURCE.replace(
            "from app.routers.vip_registration import register_vip_routes",
            "from app.routers.vip_registration import register_vip_routes as vip_register",
            1,
        ),
        _REGISTRATION_AUTHORITY_MINIMAL_SOURCE.replace(
            "    register_vip_routes(target_app)\n",
            "    alias = register_vip_routes\n    alias(target_app)\n",
            1,
        ),
        _REGISTRATION_AUTHORITY_MINIMAL_SOURCE
        + "\nif False:\n    register_pro_routes(target_app)\n",
        _REGISTRATION_AUTHORITY_MINIMAL_SOURCE
        + '\ngetattr(object(), "register_bmi_routes")(target_app)\n',
        _REGISTRATION_AUTHORITY_MINIMAL_SOURCE.replace(
            "    _register_bmi_routes(app)\n",
            "    if target_app:\n        _register_bmi_routes(app)\n",
            1,
        ),
    ),
)
def test_registration_authority_recognizer_rejects_unknown_carriers(source: str) -> None:
    assert _registration_authority_violations(source)


def _registration_live_manifest(state: str, mutation: str = "none") -> dict[str, object]:
    """Return exact route rows plus their summary for one fresh feature state.

    To inspect or intentionally regenerate a changed snapshot, run this test
    with ``pytest -vv -k registration_authority_live_manifest``. The failing
    assertion prints deterministic ``source_rows`` and ``live_rows``; review
    that row-level diff before updating the manifest counts, digests, and its
    content fingerprint together.
    """

    manifest_json = json.dumps(
        _REGISTRATION_AUTHORITY_MANIFEST,
        sort_keys=True,
        separators=(",", ":"),
    )
    base_env = os.environ | {
        "APP_ENV": "test",
        "ENVIRONMENT": "test",
        "TESTING": "true",
    }
    for flag in (
        "BUSINESS_MODULE_ENABLED",
        "ENABLE_TEST_ROUTES",
        *_REGISTRATION_AUTHORITY_MANIFEST["feature_flags"],
    ):
        base_env.pop(flag, None)
    env = dict(base_env)
    for index, flag in enumerate(_REGISTRATION_AUTHORITY_MANIFEST["feature_flags"]):
        if state[index] == "1":
            env[flag] = "true"
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            _REGISTRATION_LIVE_MANIFEST_SCRIPT,
            manifest_json,
            state,
            mutation,
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    return json.loads(completed.stdout)


def _registration_manifest_summary(actual: dict[str, object]) -> dict[str, object]:
    return {field: actual[field] for field in _REGISTRATION_MANIFEST_SUMMARY_FIELDS}


@pytest.mark.parametrize(
    ("state", "expected"),
    sorted(_REGISTRATION_AUTHORITY_MANIFEST["feature_states"].items()),
)
def test_registration_authority_live_manifest_matches_feature_state(
    state: str,
    expected: dict[str, object],
) -> None:
    actual = _registration_live_manifest(state)
    actual_summary = _registration_manifest_summary(actual)
    assert actual_summary == expected, (
        f"Registration route manifest drift for state {state}: "
        f"expected {expected}, got {actual_summary}; "
        f"source_rows={actual['source_rows']}; live_rows={actual['live_rows']}"
    )


@pytest.mark.parametrize(
    "mutation",
    (
        "foreign_duplicate",
        "foreign_owner",
        "visibility",
        "response_status_metadata",
        "dependency",
    ),
)
def test_registration_authority_live_manifest_rejects_drift(mutation: str) -> None:
    state = "100"
    expected = _REGISTRATION_AUTHORITY_MANIFEST["feature_states"][state]
    actual = _registration_live_manifest(state, mutation)
    assert _registration_manifest_summary(actual) != expected


def test_app_surface_has_required_legacy_symbols() -> None:
    """If tests depend on `from app import X`, enforce that it exists."""
    import app

    required = {
        "app",  # FastAPI instance
        "__getattr__",  # PEP 562 forwarding
    }

    missing = [name for name in required if not hasattr(app, name)]
    assert not missing, f"Missing required symbols in app package: {missing}"


@pytest.mark.parametrize(
    "path_glob,forbidden_tokens",
    [
        ("providers/**/*.py", ("spec_from_file_location(", "exec_module(")),
    ],
)
def test_providers_no_dynamic_imports(path_glob: str, forbidden_tokens: tuple[str, ...]) -> None:
    """Providers must not use dynamic imports to avoid namespace corruption."""
    offenders: list[str] = []

    for path in _iter_py_files(path_glob):
        content = _read(path)
        if content is None:
            continue
        if any(tok in content for tok in forbidden_tokens):
            offenders.append(_rel(path))

    assert not offenders, f"Providers contain dynamic import tokens: {offenders}"


def test_no_sys_modules_get_recipe_store_in_tests() -> None:
    """Tests must not use sys.modules.get('recipe_store') - use standard imports instead.

    Anti-pattern: sys.modules.get("recipe_store") returns wrong module instance.
    Correct pattern: import app.services.recipe_store as rs
    """
    offenders: list[str] = []

    for path in _iter_py_files("tests/**/*.py"):
        rel = _rel(path)
        # Skip this guard file itself
        if rel == "tests/test_repo_policy_guards.py":
            continue

        content = _read(path)
        if content is None:
            continue
        if (
            'sys.modules.get("recipe_store")' in content
            or "sys.modules.get('recipe_store')" in content
        ):
            offenders.append(rel)

    assert not offenders, (
        "Tests must not use sys.modules.get('recipe_store'). "
        f"Use 'import app.services.recipe_store as rs' instead. Offenders: {offenders}"
    )


def test_no_sys_modules_none_poisoning() -> None:
    """Prohibit setting sys.modules[...] = None which creates 'halted import' state.

    ❌ sys.modules["core.menu_engine"] = None  # Creates ModuleNotFoundError: import halted
    ❌ patch.dict("sys.modules", {"core.menu_engine": None})  # Same effect
    ✅ del sys.modules["core.menu_engine"]  # Safe removal
    ✅ monkeypatch.delitem(sys.modules, "core.menu_engine", raising=False)  # Safe mocking

    Note: This test allows legitimate import error testing in specific test files.
    """
    import re

    offenders: list[str] = []
    # Pattern: sys.modules[...]=None or patch.dict(..., {...: None})
    # Exclude this guard file itself from the check
    patterns = [
        r"sys\.modules\[[^]]+\]\s*=\s*None",
        r"patch\.dict\([^)]*\{[^}]*:[^}]*None[^}]*\}",  # patch.dict with None values
    ]

    for path in (
        list(_iter_py_files("app/**/*.py"))
        + list(_iter_py_files("core/**/*.py"))
        + list(_iter_py_files("tests/**/*.py"))
    ):
        rel = _rel(path)
        # Skip this guard file itself to avoid false positive on the pattern strings
        if rel == "tests/test_repo_policy_guards.py":
            continue
        # Skip specific test files that legitimately test import error handling
        if rel in [
            "tests/test_bmi_visualization.py",  # Tests matplotlib import error handling
        ]:
            continue

        content = _read(path)
        if content is None:
            continue

        for pattern in patterns:
            if re.search(pattern, content):
                offenders.append(f"{rel} (pattern: {pattern})")
                break  # Don't report same file multiple times

    assert not offenders, (
        "sys.modules None poisoning found. Use 'del sys.modules[key]' instead of 'sys.modules[key] = None'. "
        f"Offenders: {offenders}"
    )


def test_nutriments_access_is_limited_to_off_ingestion() -> None:
    """Raw nutriments access must stay inside the OFF ingestion boundary."""

    offenders: list[str] = []
    for path in (
        list(_iter_py_files("app/**/*.py"))
        + list(_iter_py_files("core/**/*.py"))
        + list(_iter_py_files("scripts/**/*.py"))
    ):
        rel = _rel(path)
        content = _read(path)
        if content is None:
            continue
        if "nutriments" in content and rel not in ALLOWED_NUTRIMENTS_ACCESS_FILES:
            offenders.append(rel)

    assert not offenders, (
        "Direct nutriments access is forbidden outside OFF ingestion/resolver files. "
        f"Offenders: {offenders}"
    )


def test_engineering_lessons_are_linked_from_repo_entrypoints() -> None:
    """Ensure ENGINEERING_LESSONS stays discoverable and doesn't get accidentally unlinked."""
    lessons_path = REPO_ROOT / "docs" / "ENGINEERING_LESSONS.md"
    assert lessons_path.exists(), "docs/ENGINEERING_LESSONS.md missing"

    agents_path = REPO_ROOT / "AGENTS.md"
    assert agents_path.exists(), "AGENTS.md missing"
    agents_content = _read(agents_path)
    assert agents_content is not None, "AGENTS.md unexpectedly missing during read"
    assert (
        "docs/ENGINEERING_LESSONS.md" in agents_content
    ), "AGENTS.md must reference docs/ENGINEERING_LESSONS.md so agents have a stable entrypoint."

    pr_template_path = REPO_ROOT / ".github" / "pull_request_template.md"
    assert pr_template_path.exists(), ".github/pull_request_template.md missing"
    pr_template_content = _read(pr_template_path)
    assert pr_template_content is not None, "PR template unexpectedly missing during read"
    assert (
        "docs/ENGINEERING_LESSONS.md" in pr_template_content
    ), "PR template must reference docs/ENGINEERING_LESSONS.md to keep humans/agents aligned."


def test_active_command_surfaces_use_docker_compose_v2() -> None:
    """Active operator command surfaces must use Docker Compose v2 syntax.

    File names such as ``docker-compose.production.yaml`` are allowed. This
    guard blocks executable legacy command tokens only.
    """

    command_surface_paths = (
        "Makefile",
        "AGENTS.md",
        "docs/runbooks/ENGINEER_QUICKPATH.md",
        "docs/architecture/ADR_COMPOSE_V2_COMMAND_SURFACE_SEAM_2026-03-09.md",
        "scripts/QUICK_DIAGNOSTIC.md",
        "scripts/QUICK_FIX_PRODUCTION.sh",
        "scripts/diagnose_production.sh",
        "scripts/fix_production_env.sh",
        "scripts/redeploy_caddy.sh",
    )
    legacy_command_pattern = re.compile(r"(?<![\w./-])docker-compose(?![\w./-])")
    offenders: list[str] = []

    assert legacy_command_pattern.search("docker-compose up -d")
    assert legacy_command_pattern.search("`docker-compose`")
    assert legacy_command_pattern.search("docker-compose:")
    assert not legacy_command_pattern.search("docker-compose.production.yaml")

    for rel in command_surface_paths:
        path = REPO_ROOT / rel
        if not path.exists():
            continue
        content = _read(path)
        if content is None:
            continue
        for line_no, line in enumerate(content.splitlines(), start=1):
            if legacy_command_pattern.search(line):
                offenders.append(f"{rel}:{line_no}: {line.strip()}")

    assert not offenders, (
        "Active command surfaces must use 'docker compose' v2 syntax; "
        "compose file names remain allowed. Offenders: " + repr(offenders)
    )


def test_no_direct_model_submodule_imports() -> None:
    """Prohibit importing models from submodules - causes duplicate registration.

    ❌ from app.models.plans import WeeklyPlan
    ❌ from app.models.events import NutritionEvent
    ✅ from app.models import WeeklyPlan, NutritionEvent

    Reason: Direct submodule imports cause 'Table already defined' errors
    when modules are imported through different paths.
    See PR #403 commit 447e39c8 for context.
    """
    import re

    offenders: list[str] = []
    # Pattern: from app.models.(plans|events) import (exclude nutrition which is a data class module)
    pattern = re.compile(r"from\s+app\.models\.(plans|events)\s+import")

    # Check all Python files except app/models/__init__.py (which does the exports)
    for path in (
        list(_iter_py_files("app/**/*.py"))
        + list(_iter_py_files("core/**/*.py"))
        + list(_iter_py_files("tests/**/*.py"))
    ):
        rel = _rel(path)
        # Allow files within app/models/ (they form a cohesive layer and may
        # cross-reference TypeDecorators and shared utilities like JSONEncodedDict)
        # and this guard file
        if rel.startswith("app/models/") or rel == "tests/test_repo_policy_guards.py":
            continue

        content = _read(path)
        if content is None:
            continue
        if pattern.search(content):
            offenders.append(rel)

    assert not offenders, (
        "Direct model submodule imports forbidden. "
        "Use 'from app.models import X' instead. "
        f"Offenders: {offenders}"
    )


# --- AST-first guardrails (harder to bypass than grep) ---

FORBIDDEN_EXACT_RELOAD_TARGETS: set[str] = {
    # Absolute forbid:
    "core.db",
}

FORBIDDEN_RELOAD_PREFIXES: set[str] = {
    # Optional broader forbid:
    "core.",
}

# Keep minimal; prefer empty.
ALLOWLIST_PATH_SUBSTRINGS: set[str] = set()

SKIP_DIRS_FOR_AST_SCAN = {
    ".git",
    ".cursor",
    ".agents",
    ".venv",
    ".venv-ci",
    "venv",
    "__pycache__",
    "site-packages",
    "build",
    "dist",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "node_modules",
    "artifacts",
    "worktrees",
    # Client apps (not part of backend policy)
    "docs",
    "frontend",
    "ios",
    # Test exclusions (aligned with pytest --ignore)
    "disabled_hypothesis",
    # Deployment/infra (may contain scripts but not core logic)
    "deploy",
    "scripts",
    # Migrations (Alembic scripts, not core logic)
    "alembic",
}


@dataclass(frozen=True)
class _AstViolation:
    relpath: str
    lineno: int
    col: int
    rule: str
    detail: str

    def format(self) -> str:
        return f"{self.relpath}:{self.lineno}:{self.col} [{self.rule}] {self.detail}"


def _root_relative_parts_for_ast_scan(path: Path, root: Path) -> tuple[str, ...]:
    if path.is_absolute():
        try:
            return path.relative_to(root).parts
        except ValueError:
            return ()
    return path.parts


def _path_has_ast_scan_skip_part(path: Path, root: Path) -> bool:
    parts = _root_relative_parts_for_ast_scan(path, root)
    return any(part in SKIP_DIRS_FOR_AST_SCAN for part in parts)


def _iter_repo_py_files_for_ast_scan(root: Path) -> Iterable[Path]:
    paths: list[Path] = []

    def _handle_walk_error(error: OSError) -> None:
        if error.filename is None:
            raise error
        error_path = Path(os.fsdecode(error.filename))
        if not _path_has_ast_scan_skip_part(error_path, root):
            raise error

    for dirpath, dirnames, filenames in os.walk(
        root,
        topdown=True,
        onerror=_handle_walk_error,
        followlinks=False,
    ):
        dirnames[:] = [name for name in dirnames if name not in SKIP_DIRS_FOR_AST_SCAN]
        for filename in filenames:
            if not filename.endswith(".py"):
                continue
            p = Path(dirpath) / filename
            if _path_has_ast_scan_skip_part(p, root):
                continue
            if not p.exists():
                # CI TOCTOU safety: transient files can disappear between discovery and scan.
                continue
            paths.append(p)

    yield from sorted(paths, key=lambda x: x.as_posix())


def test_iter_repo_py_files_for_ast_scan_prunes_skipped_dirs(tmp_path: Path) -> None:
    """Generated dependency trees must be pruned before AST scanning."""
    repo_root = tmp_path / "frontend" / "repo"
    source_file = repo_root / "app" / "real_source.py"
    source_file.parent.mkdir(parents=True)
    source_file.write_text("VALUE = 1\n", encoding="utf-8")

    dependency_file = repo_root / "frontend" / "node_modules" / "@open-draft" / "generated.py"
    dependency_file.parent.mkdir(parents=True)
    dependency_file.write_text("importlib.reload(core.db)\n", encoding="utf-8")

    yielded = {
        path.relative_to(repo_root).as_posix()
        for path in _iter_repo_py_files_for_ast_scan(repo_root)
    }

    assert yielded == {"app/real_source.py"}


def test_iter_repo_py_files_for_ast_scan_ignores_skipped_walk_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Transient generated dependency paths must not crash traversal."""
    source_file = tmp_path / "app" / "real_source.py"
    source_file.parent.mkdir()
    source_file.write_text("VALUE = 1\n", encoding="utf-8")
    generated_path = tmp_path / "frontend" / "node_modules" / "@open-draft"

    def fake_walk(
        top: Path,
        topdown: bool = True,
        onerror: object | None = None,
        followlinks: bool = False,
    ) -> Iterator[tuple[str, list[str], list[str]]]:
        assert top == tmp_path
        assert topdown is True
        assert followlinks is False
        if callable(onerror):
            onerror(FileNotFoundError(2, "No such file", str(generated_path)))
        yield str(source_file.parent), [], [source_file.name]

    monkeypatch.setattr(os, "walk", fake_walk)

    yielded = {
        path.relative_to(tmp_path).as_posix() for path in _iter_repo_py_files_for_ast_scan(tmp_path)
    }

    assert yielded == {"app/real_source.py"}


def test_iter_repo_py_files_for_ast_scan_reraises_source_walk_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Traversal failures outside skipped generated trees must fail closed."""

    def fake_walk(
        top: Path,
        topdown: bool = True,
        onerror: object | None = None,
        followlinks: bool = False,
    ) -> Iterator[tuple[str, list[str], list[str]]]:
        assert top == tmp_path
        assert topdown is True
        assert followlinks is False
        if callable(onerror):
            onerror(FileNotFoundError(2, "source tree disappeared", str(tmp_path / "app")))
        yield str(tmp_path), [], []

    monkeypatch.setattr(os, "walk", fake_walk)

    with pytest.raises(FileNotFoundError, match="source tree disappeared"):
        list(_iter_repo_py_files_for_ast_scan(tmp_path))


def _is_allowlisted_for_ast_scan(path: Path) -> bool:
    rel = path.relative_to(REPO_ROOT).as_posix()
    return any(token in rel for token in ALLOWLIST_PATH_SUBSTRINGS)


def _dotted_name(node: ast.AST) -> Optional[str]:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted_name(node.value)
        if base is None:
            return None
        return f"{base}.{node.attr}"
    return None


class _RepoPolicyAstVisitor(ast.NodeVisitor):
    def __init__(self, path: Path) -> None:
        self.path = path
        self.relpath = path.relative_to(REPO_ROOT).as_posix()
        self.violations: list[_AstViolation] = []
        # local alias -> fully-qualified dotted name (e.g., "r" -> "importlib.reload")
        self.aliases: dict[str, str] = {}

    def _resolve(self, dotted: Optional[str]) -> Optional[str]:
        if dotted is None:
            return None
        if dotted in self.aliases:
            return self.aliases[dotted]
        base, sep, rest = dotted.partition(".")
        if base in self.aliases:
            return f"{self.aliases[base]}{sep}{rest}" if sep else self.aliases[base]
        return dotted

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            asname = alias.asname or alias.name

            if alias.name == "importlib":
                self.aliases[asname] = "importlib"
            elif alias.name == "sys":
                self.aliases[asname] = "sys"
            # Help resolve reload(db) where db came from "import core.db as db"
            elif alias.name == "core" or alias.name.startswith("core."):
                self.aliases[asname] = alias.name

        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module == "importlib":
            for alias in node.names:
                if alias.name == "reload":
                    self.aliases[alias.asname or "reload"] = "importlib.reload"

        if node.module == "sys":
            for alias in node.names:
                if alias.name == "modules":
                    self.aliases[alias.asname or "modules"] = "sys.modules"

        # from core import db as db_mod  => db_mod == core.db
        if node.module == "core":
            for alias in node.names:
                if alias.name:
                    self.aliases[alias.asname or alias.name] = f"core.{alias.name}"

        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        # Track simple alias assignments like: r = importlib.reload; mods = sys.modules
        value_name = self._resolve(_dotted_name(node.value))
        if value_name in ("importlib.reload", "sys.modules"):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.aliases[target.id] = value_name

        # Forbid sys.modules = ...
        for target in node.targets:
            target_name = self._resolve(_dotted_name(target))
            if target_name == "sys.modules":
                self.violations.append(
                    _AstViolation(
                        relpath=self.relpath,
                        lineno=node.lineno,
                        col=node.col_offset,
                        rule="FORBID_SYS_MODULES_REASSIGN",
                        detail="Reassigning sys.modules is forbidden (breaks import invariants).",
                    )
                )

        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        # Forbid sys.modules |= ... (or other augmented rebinds)
        target_name = self._resolve(_dotted_name(node.target))
        if target_name == "sys.modules":
            self.violations.append(
                _AstViolation(
                    relpath=self.relpath,
                    lineno=node.lineno,
                    col=node.col_offset,
                    rule="FORBID_SYS_MODULES_REASSIGN",
                    detail="Augmented assignment to sys.modules is forbidden (breaks import invariants).",
                )
            )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        fn_name = self._resolve(_dotted_name(node.func))

        # 1) Forbid importlib.reload(core.*)
        if fn_name == "importlib.reload":
            self._check_importlib_reload(node)

        # 2) Forbid sys.modules.clear()
        if fn_name == "sys.modules.clear":
            self.violations.append(
                _AstViolation(
                    relpath=self.relpath,
                    lineno=node.lineno,
                    col=node.col_offset,
                    rule="FORBID_SYS_MODULES_CLEAR",
                    detail="sys.modules.clear() is forbidden (causes reload-style flakiness / dual-namespace issues).",
                )
            )

        self.generic_visit(node)

    def _reload_target(self, node: ast.AST) -> Optional[str]:
        # Case 1: dotted name (optionally resolved via aliases)
        dotted = self._resolve(_dotted_name(node))
        if dotted:
            return dotted

        # Case 2: sys.modules["core.db"]
        if isinstance(node, ast.Subscript):
            base = self._resolve(_dotted_name(node.value))
            if base == "sys.modules":
                sl = node.slice
                if isinstance(sl, ast.Constant) and isinstance(sl.value, str):
                    return sl.value

        # Case 3: importlib.import_module("core.db")
        if isinstance(node, ast.Call):
            fn_name = self._resolve(_dotted_name(node.func))
            if fn_name == "importlib.import_module" and node.args:
                arg0 = node.args[0]
                if isinstance(arg0, ast.Constant) and isinstance(arg0.value, str):
                    return arg0.value

        return None

    def _check_importlib_reload(self, node: ast.Call) -> None:
        if not node.args:
            # reload() without args is invalid anyway; still forbid.
            self.violations.append(
                _AstViolation(
                    relpath=self.relpath,
                    lineno=node.lineno,
                    col=node.col_offset,
                    rule="FORBID_IMPORTLIB_RELOAD",
                    detail="importlib.reload() is forbidden in this repo (use explicit init patterns).",
                )
            )
            return

        target = self._reload_target(node.args[0])

        # If target cannot be resolved, we cannot determine if it's core.*, so we forbid it
        # to be safe (prevents obfuscated reload patterns).
        if not target:
            self.violations.append(
                _AstViolation(
                    relpath=self.relpath,
                    lineno=node.lineno,
                    col=node.col_offset,
                    rule="FORBID_IMPORTLIB_RELOAD",
                    detail="importlib.reload(...) with unresolvable target is forbidden (prevents obfuscated reload patterns).",
                )
            )
            return

        # Absolute forbid: core.db
        if target in FORBIDDEN_EXACT_RELOAD_TARGETS:
            self.violations.append(
                _AstViolation(
                    relpath=self.relpath,
                    lineno=node.lineno,
                    col=node.col_offset,
                    rule="FORBID_RELOAD_CORE_DB",
                    detail="importlib.reload(core.db) is forbidden. Use explicit init patterns (init_db()).",
                )
            )
            return

        # Forbid: core.* (any core module)
        if any(target.startswith(prefix) for prefix in FORBIDDEN_RELOAD_PREFIXES):
            self.violations.append(
                _AstViolation(
                    relpath=self.relpath,
                    lineno=node.lineno,
                    col=node.col_offset,
                    rule="FORBID_RELOAD_CORE_PREFIX",
                    detail=f"importlib.reload({target}) is forbidden (core.* reload breaks single-Base invariants).",
                )
            )
            return

        # Allow reload of non-core modules (legacy_app, app, llm, test_router, etc.)
        # These are test-only patterns and don't affect core.db Base identity.
        # Policy: Reload is allowed for non-core modules only; core.* reload breaks
        # single-Base + DB init invariants (see PR #410).


def _scan_file_ast(path: Path) -> list[_AstViolation]:
    if _is_allowlisted_for_ast_scan(path):
        return []
    try:
        src = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        rel = _rel(path)
        if any(pattern.match(rel) for pattern in _TRANSIENT_POLICY_SCAN_PATHS):
            return []
        raise
    except UnicodeDecodeError:
        return []
    try:
        tree = ast.parse(src, filename=str(path))
    except SyntaxError:
        return []

    v = _RepoPolicyAstVisitor(path)
    v.visit(tree)
    return v.violations


def test_repo_policy_guards_ast_reload_and_sys_modules_clear() -> None:
    """Repository policy guardrails: forbid reload(core.db) and risky module resets.

    IMPORTANT: This test must remain deterministic and NOT import runtime modules:
    - do NOT import app/core/providers here (would break isolation)
    - only scan source via AST (no execution, no env/DB dependencies)
    - ensures single-Base invariant and prevents dual-namespace issues

    This test protects PR #410 invariants:
    - deterministic DB init (init_db() only, no reload)
    - single-Base identity (no module reloads that create new Base)
    - no reload/purge-induced flakiness in CI

    Note: This test does NOT import core.db or any runtime modules.
    It only parses source code via AST, making it deterministic and fast (~2-3s).
    """
    violations: list[_AstViolation] = []
    for p in _iter_repo_py_files_for_ast_scan(REPO_ROOT):
        violations.extend(_scan_file_ast(p))

    if violations:
        msg = "\n".join(v.format() for v in violations)
        raise AssertionError(
            "Repository policy violated.\n"
            "The following guardrails must hold (CI stability & single-Base invariants):\n"
            "- FORBID: importlib.reload(core.db) (absolute) → use init_db() + SessionLocal contract\n"
            "- FORBID: importlib.reload(core.*) → breaks single-Base invariant\n"
            "- FORBID: importlib.reload(...) with unresolvable target → prevents obfuscation\n"
            "- FORBID: sys.modules.clear() / sys.modules reassignment → causes dual-namespace issues\n\n"
            f"Violations:\n{msg}\n\n"
            "To fix: remove reload/purge patterns and use explicit init flows (init_db, fixtures)."
        )
