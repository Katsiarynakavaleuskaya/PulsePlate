"""Ownership oracles for the canonical Insight compatibility seam."""

from __future__ import annotations

import ast
from pathlib import Path

from fastapi import FastAPI
import pytest

from app.schemas import insight as insight_schemas
from app.services import insight_application_service, insight_compat
from app.utils.feature_flags import is_insight_enabled
from tests.helpers.module_resolve import resolve_legacy_app
from tests.helpers.route_lookup import find_single_route

_CANONICAL_MODULES = (
    insight_schemas,
    insight_compat,
    insight_application_service,
)
_LEGACY_RUNTIME_NAMES = frozenset(
    {
        "_load_llm_get_provider",
        "_execute_insight_request",
        "_DirectInsightProviderStub",
    }
)
_UNSUPPORTED_LEGACY_ASSIGNMENT = "<unsupported-legacy-assignment>"
_LEGACY_COMPAT_ACCESS_ALLOWLIST = {
    (
        "tests/test_insight_ownership.py",
        "test_legacy_insight_exports_are_exact_canonical_aliases",
    ): _LEGACY_RUNTIME_NAMES,
    (
        "tests/test_philosophical_runtime.py",
        "test_direct_insight_provider_stub_raises_if_called",
    ): frozenset({"_DirectInsightProviderStub"}),
}


class _LegacyRuntimeAccessVisitor(ast.NodeVisitor):
    """Find the finite legacy Insight runtime carrier class in test code."""

    def __init__(self) -> None:
        self.aliases: set[str] = set()
        self.scope = "<module>"
        self.accesses: set[tuple[str, str, int]] = set()

    @staticmethod
    def _leaf_name(node: ast.expr) -> str | None:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return node.attr
        return None

    def _is_legacy_module(self, node: ast.expr) -> bool:
        if isinstance(node, ast.Name):
            return node.id in self.aliases
        if isinstance(node, ast.Call):
            function_name = self._leaf_name(node.func)
            if function_name == "resolve_legacy_app":
                return True
            if function_name in {"resolve_module", "import_module", "__import__"} and node.args:
                module_name = node.args[0]
                return isinstance(module_name, ast.Constant) and module_name.value == "legacy_app"
        return (
            isinstance(node, ast.Subscript)
            and isinstance(node.value, ast.Attribute)
            and isinstance(node.value.value, ast.Name)
            and node.value.value.id == "sys"
            and node.value.attr == "modules"
            and isinstance(node.slice, ast.Constant)
            and node.slice.value == "legacy_app"
        )

    def _record(self, node: ast.expr | ast.stmt, symbol: str) -> None:
        self.accesses.add((self.scope, symbol, node.lineno))

    @classmethod
    def _bound_names(cls, target: ast.expr) -> set[str]:
        if isinstance(target, ast.Name):
            return {target.id}
        if isinstance(target, (ast.Tuple, ast.List)):
            return set().union(*(cls._bound_names(item) for item in target.elts))
        if isinstance(target, ast.Starred):
            return cls._bound_names(target.value)
        return set()

    def _literal_contains_legacy_module(self, node: ast.expr) -> bool:
        if self._is_legacy_module(node):
            return True
        if isinstance(node, (ast.Tuple, ast.List)):
            return any(self._literal_contains_legacy_module(item) for item in node.elts)
        if isinstance(node, ast.Starred):
            return self._literal_contains_legacy_module(node.value)
        return False

    def _bind_simple_assignment(
        self,
        node: ast.Assign | ast.AnnAssign,
        targets: list[ast.expr],
        value: ast.expr | None,
        runtime_accesses: set[tuple[str, str, int]],
    ) -> None:
        if value is None:
            return

        target_names = set().union(*(self._bound_names(target) for target in targets))
        value_is_legacy = self._is_legacy_module(value)
        value_contains_legacy = self._literal_contains_legacy_module(value)
        unsupported = (
            len(targets) != 1
            or not isinstance(targets[0], ast.Name)
            or ((value_contains_legacy and not value_is_legacy) or bool(runtime_accesses))
        )
        if unsupported:
            self.accesses.difference_update(runtime_accesses)
            if value_contains_legacy or runtime_accesses or target_names.intersection(self.aliases):
                self._record(node, _UNSUPPORTED_LEGACY_ASSIGNMENT)
            return

        for target in targets:
            assert isinstance(target, ast.Name)
            self.aliases.discard(target.id)
            if value_is_legacy:
                self.aliases.add(target.id)

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        previous_scope, previous_aliases = self.scope, self.aliases
        self.scope, self.aliases = node.name, set(previous_aliases)
        self.generic_visit(node)
        self.scope, self.aliases = previous_scope, previous_aliases

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def visit_Import(self, node: ast.Import) -> None:
        self.aliases.update(
            alias.asname or "legacy_app" for alias in node.names if alias.name == "legacy_app"
        )

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module == "legacy_app":
            for alias in node.names:
                if alias.name in _LEGACY_RUNTIME_NAMES or alias.name == "*":
                    self._record(node, alias.name)

    def visit_Assign(self, node: ast.Assign) -> None:
        previous_accesses = set(self.accesses)
        self.generic_visit(node)
        self._bind_simple_assignment(
            node,
            node.targets,
            node.value,
            self.accesses - previous_accesses,
        )

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        previous_accesses = set(self.accesses)
        self.generic_visit(node)
        self._bind_simple_assignment(
            node,
            [node.target],
            node.value,
            self.accesses - previous_accesses,
        )

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr in _LEGACY_RUNTIME_NAMES and self._is_legacy_module(node.value):
            self._record(node, node.attr)
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        if (
            isinstance(node.slice, ast.Constant)
            and node.slice.value in _LEGACY_RUNTIME_NAMES
            and isinstance(node.value, ast.Attribute)
            and node.value.attr == "__dict__"
            and self._is_legacy_module(node.value.value)
        ):
            self._record(node, str(node.slice.value))
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        function_name = self._leaf_name(node.func)
        if (
            function_name in {"setattr", "getattr", "delattr", "object"}
            and len(node.args) >= 2
            and self._is_legacy_module(node.args[0])
            and isinstance(node.args[1], ast.Constant)
            and node.args[1].value in _LEGACY_RUNTIME_NAMES
        ):
            self._record(node, str(node.args[1].value))
        if function_name in {"setattr", "patch"} and node.args:
            target = node.args[0]
            if isinstance(target, ast.Constant) and isinstance(target.value, str):
                module_name, separator, symbol = target.value.partition(".")
                if module_name == "legacy_app" and separator and symbol in _LEGACY_RUNTIME_NAMES:
                    self._record(node, symbol)
        self.generic_visit(node)


def _legacy_runtime_accesses(source: str) -> set[tuple[str, str, int]]:
    visitor = _LegacyRuntimeAccessVisitor()
    visitor.visit(ast.parse(source))
    return visitor.accesses


def test_legacy_runtime_access_visitor_models_simple_name_bindings() -> None:
    assert _legacy_runtime_accesses(
        "legacy: object = resolve_legacy_app()\nlegacy._execute_insight_request\n"
    ) == {("<module>", "_execute_insight_request", 2)}
    assert _legacy_runtime_accesses(
        "legacy = resolve_legacy_app()\nalias = legacy\nalias._execute_insight_request\n"
    ) == {("<module>", "_execute_insight_request", 3)}
    for assignment in ("legacy = object()", "legacy: object = object()"):
        source = f"legacy = resolve_legacy_app()\n{assignment}\nlegacy._execute_insight_request\n"
        assert _legacy_runtime_accesses(source) == set()


def test_legacy_runtime_access_visitor_fails_closed_on_unpacking() -> None:
    cases = (
        ("legacy, other = resolve_legacy_app(), None\n", 1),
        ("[legacy, other] = [resolve_legacy_app(), None]\n", 1),
        ("legacy = alias = resolve_legacy_app()\n", 1),
        ("legacy = legacy = resolve_legacy_app()\n", 1),
        (
            "legacy = resolve_legacy_app()\nlegacy, legacy = legacy, None\n",
            2,
        ),
        ("*rest, legacy = None, None, resolve_legacy_app()\n", 1),
    )
    for source, expected_line in cases:
        finding = ("<module>", _UNSUPPORTED_LEGACY_ASSIGNMENT, expected_line)
        assert _legacy_runtime_accesses(source) == {finding}


@pytest.mark.parametrize(
    "source",
    [
        ("legacy = resolve_legacy_app()\n" "legacy = legacy._execute_insight_request\n"),
        (
            "legacy = resolve_legacy_app()\n"
            'legacy: object = getattr(legacy, "_execute_insight_request")\n'
        ),
    ],
)
def test_legacy_runtime_access_visitor_evaluates_rhs_before_rebinding(source: str) -> None:
    assert _legacy_runtime_accesses(source) == {("<module>", _UNSUPPORTED_LEGACY_ASSIGNMENT, 2)}


def test_canonical_insight_modules_do_not_depend_on_legacy_app() -> None:
    for module in _CANONICAL_MODULES:
        source_path = Path(str(module.__file__))
        assert "legacy_app" not in source_path.read_text(encoding="utf-8"), source_path


def test_legacy_insight_exports_are_exact_canonical_aliases() -> None:
    legacy_app = resolve_legacy_app()

    assert legacy_app.INSIGHT_TEXT_MAX_LENGTH == insight_schemas.INSIGHT_TEXT_MAX_LENGTH
    assert legacy_app.InsightRequest is insight_schemas.InsightRequest
    assert legacy_app.RAGSourceItem is insight_schemas.RAGSourceItem
    assert legacy_app.InsightResponse is insight_schemas.InsightResponse
    assert legacy_app.INSIGHT_TEMP_UNAVAILABLE_MESSAGE is (
        insight_compat.INSIGHT_TEMP_UNAVAILABLE_MESSAGE
    )
    assert legacy_app._DirectInsightProviderStub is insight_compat._DirectInsightProviderStub
    assert legacy_app._require_ai_generated_insight_notice is (
        insight_compat._require_ai_generated_insight_notice
    )
    assert legacy_app._enforce_vip_llm_monthly_quota is (
        insight_compat._enforce_vip_llm_monthly_quota
    )
    assert legacy_app._execute_insight_request is insight_compat._execute_insight_request
    assert legacy_app.insight_v1 is insight_compat.insight_v1
    assert legacy_app.insight is insight_compat.insight


def test_legacy_app_no_longer_defines_insight_models_or_dead_helpers() -> None:
    tree = ast.parse(Path("legacy_app.py").read_text(encoding="utf-8"))
    definitions = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    }

    assert definitions.isdisjoint(
        {
            "InsightRequest",
            "RAGSourceItem",
            "InsightResponse",
            "_ensure_insight_text_length",
            "_build_insight_prompt",
            "_build_rag_source_items",
        }
    )


def test_insight_router_response_models_are_canonical(app: FastAPI) -> None:
    for path in ("/api/v1/insight", "/insight"):
        route = find_single_route(app, path, "POST", family_label="legacy insight")
        assert getattr(route, "response_model", None) is insight_schemas.InsightResponse


def test_insight_runtime_tests_use_only_allowed_legacy_compat_accesses() -> None:
    violations: list[str] = []
    for path in Path("tests").rglob("test*.py"):
        if not path.exists():
            continue
        source = path.read_text(encoding="utf-8")
        for scope, symbol, line in _legacy_runtime_accesses(source):
            allowed = _LEGACY_COMPAT_ACCESS_ALLOWLIST.get((path.as_posix(), scope), frozenset())
            if symbol not in allowed:
                violations.append(f"{path}:{line}:{scope}:{symbol}")

    assert violations == []


def test_insight_feature_flag_is_read_at_call_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("FEATURE_INSIGHT", raising=False)
    assert is_insight_enabled() is False
    monkeypatch.setenv("FEATURE_INSIGHT", "true")
    assert is_insight_enabled() is True
    monkeypatch.setenv("FEATURE_INSIGHT", "false")
    assert is_insight_enabled() is False
