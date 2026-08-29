from __future__ import annotations

import ast
from pathlib import Path

CONTRACT_PATH = Path(__file__).with_name("_api_authz_contracts.py")
CONTRACT_TREE = ast.parse(CONTRACT_PATH.read_text(encoding="utf-8"))
MATRIX_PATH = Path(__file__).with_name("test_api_bola_cross_principal_matrix.py")
MATRIX_TREE = ast.parse(MATRIX_PATH.read_text(encoding="utf-8"))


def _dotted_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _dotted_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return None


def _string_literal(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _has_import(module: str, imported_name: str) -> bool:
    for node in CONTRACT_TREE.body:
        if isinstance(node, ast.ImportFrom) and node.module == module:
            return any(alias.name == imported_name for alias in node.names)
    return False


def _enum_member_value(class_name: str, member_name: str) -> str | None:
    for node in CONTRACT_TREE.body:
        if not isinstance(node, ast.ClassDef) or node.name != class_name:
            continue
        for statement in node.body:
            if not isinstance(statement, ast.Assign):
                continue
            if not any(
                isinstance(target, ast.Name) and target.id == member_name
                for target in statement.targets
            ):
                continue
            return _string_literal(statement.value)
    return None


def _assigned_value(name: str, *, tree: ast.Module = CONTRACT_TREE) -> ast.AST | None:
    for node in tree.body:
        if isinstance(node, ast.AnnAssign):
            target = node.target
            if isinstance(target, ast.Name) and target.id == name:
                return node.value
            continue
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name for target in node.targets
        ):
            return node.value
    return None


def _contract_calls() -> list[ast.Call]:
    value = _assigned_value("API_AUTHZ_CONTRACTS")
    if not isinstance(value, ast.Tuple):
        return []
    return [
        element
        for element in value.elts
        if isinstance(element, ast.Call) and _dotted_name(element.func) == "_contract"
    ]


def _keyword_value(call: ast.Call, name: str) -> ast.AST | None:
    for keyword in call.keywords:
        if keyword.arg == name:
            return keyword.value
    return None


def _bola_contract_bindings() -> list[tuple[str | None, str | None, str | None]]:
    bindings: list[tuple[str | None, str | None, str | None]] = []
    for call in _contract_calls():
        oracle_node = _keyword_value(call, "bola_oracle_id")
        if oracle_node is None:
            continue
        method = _string_literal(call.args[0]) if len(call.args) > 0 else None
        path = _string_literal(call.args[1]) if len(call.args) > 1 else None
        bindings.append((_string_literal(oracle_node), method, path))
    return bindings


def _bola_scenario_bindings() -> list[tuple[str | None, str | None, str | None]]:
    value = _assigned_value("BOLA_SCENARIOS", tree=MATRIX_TREE)
    if not isinstance(value, ast.Tuple):
        return []

    bindings: list[tuple[str | None, str | None, str | None]] = []
    for element in value.elts:
        if not isinstance(element, ast.Call) or _dotted_name(element.func) != "BolaScenario":
            bindings.append((None, None, None))
            continue
        oracle_node = _keyword_value(element, "oracle_id")
        route_node = _keyword_value(element, "route_key")
        if not isinstance(route_node, ast.Tuple) or len(route_node.elts) != 2:
            bindings.append((_string_literal(oracle_node) if oracle_node else None, None, None))
            continue
        bindings.append(
            (
                _string_literal(oracle_node) if oracle_node else None,
                _string_literal(route_node.elts[0]),
                _string_literal(route_node.elts[1]),
            )
        )
    return bindings


def _contract_signature(path: str) -> tuple[str | None, ...] | None:
    for call in _contract_calls():
        if len(call.args) < 7 or _string_literal(call.args[1]) != path:
            continue
        return tuple(
            _string_literal(argument) or _dotted_name(argument) for argument in call.args[:7]
        )
    return None


def _dependency_for_auth_class(auth_class_name: str) -> str | None:
    value = _assigned_value("EXPECTED_DEPENDENCY_BY_AUTH_CLASS")
    if not isinstance(value, ast.Dict):
        return None
    for key, dependency in zip(value.keys, value.values, strict=True):
        if key is not None and _dotted_name(key) == auth_class_name:
            return _dotted_name(dependency)
    return None


def test_non_production_test_guard_classifies_hidden_mutating_test_routes() -> None:
    expected_signature: tuple[str | None, ...] = (
        "POST",
        None,
        "AuthClass.NON_PRODUCTION_TEST_GUARD",
        "MinimumTier.NONE",
        "PrincipalSource.INTERNAL_OPTIONAL",
        "OwnershipPolicy.INTERNAL_OPTIONAL",
        "ApiExposure.HIDDEN_RUNTIME",
    )

    assert _has_import("app.routers.test", "_ensure_non_production")
    assert (
        _enum_member_value("AuthClass", "NON_PRODUCTION_TEST_GUARD") == "non_production_test_guard"
    )
    for path in ("/api/v1/test/rate-limit", "/api/v1/test/echo"):
        signature = _contract_signature(path)
        assert signature is not None
        assert signature[:1] + signature[2:] == expected_signature[:1] + expected_signature[2:]
    assert _contract_signature("/api/v1/test/health") is None


def test_non_production_test_guard_maps_to_route_dependency() -> None:
    assert (
        _dependency_for_auth_class("AuthClass.NON_PRODUCTION_TEST_GUARD")
        == "_ensure_non_production"
    )


def test_bola_oracle_bindings_are_literal_unique_and_bijective() -> None:
    contract_bindings = _bola_contract_bindings()
    scenario_bindings = _bola_scenario_bindings()

    assert contract_bindings, "BOLA contracts must use literal oracle bindings"
    assert scenario_bindings, "BOLA_SCENARIOS must be one literal non-empty tuple"
    assert all(all(value is not None for value in binding) for binding in contract_bindings)
    assert all(all(value is not None for value in binding) for binding in scenario_bindings)
    assert len(set(contract_bindings)) == len(contract_bindings)
    assert len(set(scenario_bindings)) == len(scenario_bindings)
    assert len({binding[0] for binding in contract_bindings}) == len(contract_bindings)
    assert len({binding[1:] for binding in contract_bindings}) == len(contract_bindings)
    assert len({binding[0] for binding in scenario_bindings}) == len(scenario_bindings)
    assert len({binding[1:] for binding in scenario_bindings}) == len(scenario_bindings)
    assert set(contract_bindings) == set(scenario_bindings)
