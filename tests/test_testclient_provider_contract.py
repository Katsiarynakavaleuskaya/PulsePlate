"""Bounded guards for the four shared TestClient provider files.

This intentionally proves only direct syntax in a fixed provider surface. It
does not resolve imports, reflection, aliases, or whole-tree callers; TC2 owns
that migration after the compatibility patch is removed.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CLIENT_HELPERS = Path("tests/_client.py")
TEST_FIXTURES = Path("tests/conftest.py")
APP_COMPATIBILITY = Path("tests/conftest_app.py")
ROOT_FIXTURES = Path("conftest.py")
PROVIDER_PATHS = (
    ROOT_FIXTURES,
    CLIENT_HELPERS,
    TEST_FIXTURES,
    APP_COMPATIBILITY,
)
SHARED_CLIENT_FIXTURES = {
    "client",
    "test_client",
    "app_client",
    "isolated_test_client",
    "client_with_vip_access",
}
ROOT_FORBIDDEN_FIXTURES = SHARED_CLIENT_FIXTURES | {"dynamic_app", "dynamic_client"}
RAW_CLIENT_NAMES = {"TestClient", "MetricsAwareTestClient"}


def _source(path: Path) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def _tree(path: Path) -> ast.Module:
    return ast.parse(_source(path), filename=path.as_posix())


def _function_nodes(path: Path) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    return {
        node.name: node
        for node in _tree(path).body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _is_fixture(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    for decorator in node.decorator_list:
        target = decorator.func if isinstance(decorator, ast.Call) else decorator
        if isinstance(target, ast.Name) and target.id == "fixture":
            return True
        if isinstance(target, ast.Attribute) and target.attr == "fixture":
            return True
    return False


def _direct_call_name(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return None


def _raw_constructor_lines(path: Path) -> list[int]:
    return [
        node.lineno
        for node in ast.walk(_tree(path))
        if isinstance(node, ast.Call) and _direct_call_name(node) in RAW_CLIENT_NAMES
    ]


def _direct_factory_call_lines(path: Path) -> list[tuple[str, int]]:
    forbidden = {"make_test_client", "get_client"}
    return [
        (name, node.lineno)
        for node in ast.walk(_tree(path))
        if isinstance(node, ast.Call) and (name := _direct_call_name(node)) in forbidden
    ]


def _managed_context_yield_counts(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[int]:
    counts: list[int] = []
    for candidate in ast.walk(node):
        if not isinstance(candidate, (ast.With, ast.AsyncWith)):
            continue
        for item in candidate.items:
            expression = item.context_expr
            if (
                isinstance(expression, ast.Call)
                and _direct_call_name(expression) == "open_test_client"
            ):
                counts.append(
                    sum(
                        isinstance(descendant, (ast.Yield, ast.YieldFrom))
                        for statement in candidate.body
                        for descendant in ast.walk(statement)
                    )
                )
                break
    return counts


def test_provider_surface_is_fixed_and_exists() -> None:
    assert all((REPO_ROOT / path).is_file() for path in PROVIDER_PATHS)
    assert len(PROVIDER_PATHS) == 4


def test_root_retains_exactly_one_metrics_compatibility_patch() -> None:
    assignment = "fastapi_testclient.TestClient = MetricsAwareTestClient"
    owners = [path for path in PROVIDER_PATHS if assignment in _source(path)]

    assert owners == [ROOT_FIXTURES]
    assert _source(ROOT_FIXTURES).count(assignment) == 1


def test_raw_client_construction_has_one_bounded_provider_owner() -> None:
    violations = {
        path.as_posix(): _raw_constructor_lines(path)
        for path in PROVIDER_PATHS
        if path != CLIENT_HELPERS and _raw_constructor_lines(path)
    }

    helper_nodes = _function_nodes(CLIENT_HELPERS)
    factory_lines = [
        node.lineno
        for node in ast.walk(helper_nodes["make_test_client"])
        if isinstance(node, ast.Call) and _direct_call_name(node) in RAW_CLIENT_NAMES
    ]

    assert violations == {}
    assert len(factory_lines) == 1
    assert _raw_constructor_lines(CLIENT_HELPERS) == factory_lines


def test_deprecated_factories_gain_no_provider_callers() -> None:
    violations = {
        path.as_posix(): _direct_factory_call_lines(path)
        for path in PROVIDER_PATHS
        if path != CLIENT_HELPERS and _direct_factory_call_lines(path)
    }

    assert violations == {}


def test_shared_fixture_ownership_is_managed_and_root_is_clean() -> None:
    root_fixtures = {
        name for name, node in _function_nodes(ROOT_FIXTURES).items() if _is_fixture(node)
    }
    test_fixture_nodes = _function_nodes(TEST_FIXTURES)

    assert root_fixtures.isdisjoint(ROOT_FORBIDDEN_FIXTURES)
    for fixture_name in SHARED_CLIENT_FIXTURES:
        node = test_fixture_nodes[fixture_name]
        assert _is_fixture(node)
        assert _managed_context_yield_counts(node) == [1]


def test_app_compatibility_provider_contains_no_fixtures_or_clients() -> None:
    fixture_names = {
        name for name, node in _function_nodes(APP_COMPATIBILITY).items() if _is_fixture(node)
    }

    assert fixture_names == set()
    assert _raw_constructor_lines(APP_COMPATIBILITY) == []
