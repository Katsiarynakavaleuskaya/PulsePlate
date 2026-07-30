"""Finite AST guard for the four TC1 TestClient provider modules."""

from __future__ import annotations

import ast
import symtable
from dataclasses import dataclass
from pathlib import Path

PROVIDER_PATHS = (
    Path("conftest.py"),
    Path("tests/_client.py"),
    Path("tests/conftest.py"),
    Path("tests/conftest_app.py"),
)
SHARED_CLIENT_FIXTURES = {
    "client",
    "test_client",
    "app_client",
    "isolated_test_client",
    "client_with_vip_access",
}
ROOT_FORBIDDEN_FIXTURES = SHARED_CLIENT_FIXTURES | {"dynamic_app", "dynamic_client"}
FASTAPI_TESTCLIENT_MODULE = "fastapi.testclient"
CLIENT_HELPERS_MODULE = "tests._client"
TESTCLIENT_SYMBOL = f"{FASTAPI_TESTCLIENT_MODULE}.TestClient"
METRICS_CLIENT_SYMBOL = f"{CLIENT_HELPERS_MODULE}.MetricsAwareTestClient"
OPEN_CLIENT_SYMBOL = f"{CLIENT_HELPERS_MODULE}.open_test_client"
MAKE_CLIENT_SYMBOL = f"{CLIENT_HELPERS_MODULE}.make_test_client"
GET_CLIENT_SYMBOL = f"{CLIENT_HELPERS_MODULE}.get_client"
TRACKED_SYMBOLS = {
    TESTCLIENT_SYMBOL,
    METRICS_CLIENT_SYMBOL,
    OPEN_CLIENT_SYMBOL,
    MAKE_CLIENT_SYMBOL,
    GET_CLIENT_SYMBOL,
}
TRACKED_MODULES = {
    "fastapi",
    FASTAPI_TESTCLIENT_MODULE,
    "tests",
    CLIENT_HELPERS_MODULE,
}
LOCAL_CLIENT_HELPERS = {
    "MetricsAwareTestClient": METRICS_CLIENT_SYMBOL,
    "open_test_client": OPEN_CLIENT_SYMBOL,
    "make_test_client": MAKE_CLIENT_SYMBOL,
    "get_client": GET_CLIENT_SYMBOL,
}


def _trees() -> dict[Path, ast.Module]:
    return {
        path: ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for path in PROVIDER_PATHS
    }


@dataclass(frozen=True)
class _Binding:
    target: str
    alias_depth: int


class _BoundedModuleResolver:
    """Resolve only TC1 provider imports and safe one-hop name aliases."""

    def __init__(self, path: Path, tree: ast.Module) -> None:
        self.path = path
        self.tree = tree
        self.bindings: dict[str, _Binding] = {}
        self._unsupported_carriers: list[tuple[int, str]] = []
        self._collect_bindings()

    def _set_binding(self, name: str, binding: _Binding, *, line: int) -> None:
        existing = self.bindings.get(name)
        if existing is not None and existing.target != binding.target:
            self._record_unsupported_carrier(line, "tracked_binding_rebound")
        self.bindings[name] = binding

    def _unbind_name(self, name: str, *, line: int) -> None:
        if name in self.bindings:
            self._record_unsupported_carrier(line, "tracked_binding_rebound")
            self.bindings.pop(name)

    @staticmethod
    def _is_tracked_import(target: str) -> bool:
        return target in TRACKED_MODULES or any(
            module.startswith(f"{target}.") for module in TRACKED_MODULES
        )

    @staticmethod
    def _is_safe_alias_target(target: str) -> bool:
        return target in TRACKED_MODULES or target in TRACKED_SYMBOLS

    def _bind_import(self, node: ast.Import) -> None:
        for alias in node.names:
            if not self._is_tracked_import(alias.name):
                continue
            if alias.asname is not None:
                self._set_binding(
                    alias.asname,
                    _Binding(alias.name, 0),
                    line=node.lineno,
                )
                continue
            root_name = alias.name.split(".", maxsplit=1)[0]
            self._set_binding(
                root_name,
                _Binding(root_name, 0),
                line=node.lineno,
            )

    def _bind_import_from(self, node: ast.ImportFrom) -> None:
        if node.level != 0 or node.module is None:
            return
        for alias in node.names:
            target = f"{node.module}.{alias.name}"
            if not (self._is_tracked_import(target) or target in TRACKED_SYMBOLS):
                continue
            bound_name = alias.asname or alias.name
            self._set_binding(
                bound_name,
                _Binding(target, 0),
                line=node.lineno,
            )

    def _bind_local_definition(
        self,
        node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> None:
        target = (
            LOCAL_CLIENT_HELPERS.get(node.name) if self.path == Path("tests/_client.py") else None
        )
        if target is None:
            self._unbind_name(node.name, line=node.lineno)
        else:
            self._set_binding(
                node.name,
                _Binding(target, 0),
                line=node.lineno,
            )

    @staticmethod
    def _name_targets(node: ast.AST) -> list[str]:
        if isinstance(node, ast.Name):
            return [node.id]
        if isinstance(node, ast.Starred):
            return _BoundedModuleResolver._name_targets(node.value)
        if isinstance(node, (ast.Tuple, ast.List)):
            names: list[str] = []
            for element in node.elts:
                names.extend(_BoundedModuleResolver._name_targets(element))
            return names
        return []

    def _record_unsupported_carrier(self, line: int, reason: str) -> None:
        carrier = (line, reason)
        if carrier not in self._unsupported_carriers:
            self._unsupported_carriers.append(carrier)

    def _bind_assignment(
        self,
        targets: list[ast.AST],
        value: ast.AST,
        *,
        line: int,
    ) -> None:
        source = self.resolve(value)
        names = [name for target in targets for name in self._name_targets(target)]
        if source is not None and self._is_safe_alias_target(source.target):
            alias_depth = source.alias_depth + 1
            for name in names:
                self._set_binding(
                    name,
                    _Binding(source.target, alias_depth),
                    line=line,
                )
            if alias_depth > 1 and names:
                self._record_unsupported_carrier(line, "tracked_alias_depth")
            return
        for name in names:
            self._unbind_name(name, line=line)

    def _collect_bindings(self) -> None:
        # Provider imports may intentionally live inside pytest hooks. Treat a
        # canonical import anywhere in one of the four closed provider modules
        # as a fail-closed module binding; this guard makes no whole-tree claim.
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                self._bind_import(node)
            elif isinstance(node, ast.ImportFrom):
                self._bind_import_from(node)

        for node in self.tree.body:
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                self._bind_local_definition(node)

        for node in ast.walk(self.tree):
            if isinstance(node, ast.Assign):
                self._bind_assignment(node.targets, node.value, line=node.lineno)
            elif isinstance(node, ast.AnnAssign) and node.value is not None:
                self._bind_assignment([node.target], node.value, line=node.lineno)

    def resolve(self, node: ast.AST) -> _Binding | None:
        if isinstance(node, ast.Name):
            return self.bindings.get(node.id)
        if isinstance(node, ast.Attribute):
            owner = self.resolve(node.value)
            if owner is not None:
                return _Binding(f"{owner.target}.{node.attr}", owner.alias_depth)
        return None

    def call_target(self, call: ast.Call) -> str | None:
        binding = self.resolve(call.func)
        if binding is None or binding.alias_depth > 1:
            return None
        return binding.target

    def unsupported_carriers(self) -> list[tuple[int, str]]:
        """Return explicit fail-closed records outside the supported AST grammar."""

        self.compatibility_patches()
        return sorted(self._unsupported_carriers)

    def compatibility_patches(self) -> list[int]:
        assignments: list[int] = []
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Call):
                if not (
                    isinstance(node.func, ast.Name)
                    and node.func.id == "setattr"
                    and len(node.args) >= 3
                ):
                    continue
                owner = self.resolve(node.args[0])
                value = self.resolve(node.args[2])
                if (
                    owner is None
                    or owner.target != FASTAPI_TESTCLIENT_MODULE
                    or value is None
                    or value.target != METRICS_CLIENT_SYMBOL
                ):
                    continue
                attribute = node.args[1]
                if not isinstance(attribute, ast.Constant) or not isinstance(
                    attribute.value,
                    str,
                ):
                    self._record_unsupported_carrier(node.lineno, "dynamic_patch_attribute")
                    continue
                if attribute.value != "TestClient":
                    continue
                if owner.alias_depth > 1 or value.alias_depth > 1:
                    self._record_unsupported_carrier(node.lineno, "tracked_patch_operand_alias")
                    continue
                assignments.append(node.lineno)
                continue

            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            value = self.resolve(node.value) if node.value is not None else None
            if value is None or value.target != METRICS_CLIENT_SYMBOL:
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            patch_targets = [
                resolved
                for target in targets
                if (resolved := self.resolve(target)) is not None
                and resolved.target == TESTCLIENT_SYMBOL
            ]
            if not patch_targets:
                continue
            if value.alias_depth > 1 or any(target.alias_depth > 1 for target in patch_targets):
                self._record_unsupported_carrier(node.lineno, "tracked_patch_operand_alias")
            else:
                assignments.append(node.lineno)
        return assignments


def _is_sys_modules_target(node: ast.AST) -> bool:
    if isinstance(node, (ast.Tuple, ast.List)):
        return any(_is_sys_modules_target(element) for element in node.elts)
    return (
        isinstance(node, ast.Subscript)
        and isinstance(node.value, ast.Attribute)
        and isinstance(node.value.value, ast.Name)
        and node.value.value.id == "sys"
        and node.value.attr == "modules"
    )


def _function_map(tree: ast.Module) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    return {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _top_level_import_targets(tree: ast.Module, bound_name: str) -> list[str]:
    targets: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                runtime_name = alias.asname or alias.name.split(".", maxsplit=1)[0]
                if runtime_name == bound_name:
                    targets.append(alias.name if alias.asname else runtime_name)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            for alias in node.names:
                if (alias.asname or alias.name) == bound_name:
                    targets.append(f"{node.module}.{alias.name}")
    return targets


def _tracked_root_name(node: ast.AST) -> str | None:
    while isinstance(node, (ast.Attribute, ast.Subscript)):
        node = node.value
    return node.id if isinstance(node, ast.Name) else None


def _direct_fixture_with_targets(
    source: str,
    *,
    path: Path,
    function_name: str,
    owner_name: str,
    owner_target: str,
    attribute_name: str | None,
    call_target: str,
) -> list[str]:
    """Credit only one compiler-stable direct provider call shape.

    Arbitrary alias/import/reflection semantics are intentionally outside this
    finite TC1 guard. PR-TC2 owns the whole-tree migration and final guard.
    """

    tree = ast.parse(source, filename=str(path))
    functions = _function_map(tree)
    function = functions[function_name]
    module_table = symtable.symtable(source, str(path), "exec")

    try:
        module_symbol = module_table.lookup(owner_name)
    except KeyError:
        return []

    if owner_target == CLIENT_HELPERS_MODULE:
        if _top_level_import_targets(tree, owner_name) != [owner_target]:
            return []
        if not module_symbol.is_imported() or module_symbol.is_assigned():
            return []
    elif (
        path != Path("tests/_client.py")
        or LOCAL_CLIENT_HELPERS.get(owner_name) != owner_target
        or not module_symbol.is_namespace()
    ):
        return []

    function_tables = [
        table
        for table in module_table.get_children()
        if table.get_type() == "function"
        and table.get_name() == function_name
        and table.get_lineno() == function.lineno
    ]
    if len(function_tables) != 1:
        return []

    try:
        owner_symbol = function_tables[0].lookup(owner_name)
    except KeyError:
        return []
    if (
        not owner_symbol.is_global()
        or not owner_symbol.is_referenced()
        or owner_symbol.is_assigned()
        or owner_symbol.is_declared_global()
        or owner_symbol.is_imported()
        or owner_symbol.is_nonlocal()
        or owner_symbol.is_parameter()
    ):
        return []

    class Visitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.targets: list[str] = []
            self.tracked_root_mutated = False

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            return

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            return

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            return

        def _visit_with(self, node: ast.With | ast.AsyncWith) -> None:
            for item in node.items:
                context = item.context_expr
                if not isinstance(context, ast.Call):
                    continue
                if attribute_name is None:
                    direct_call = (
                        isinstance(context.func, ast.Name) and context.func.id == owner_name
                    )
                else:
                    direct_call = (
                        isinstance(context.func, ast.Attribute)
                        and context.func.attr == attribute_name
                        and isinstance(context.func.value, ast.Name)
                        and context.func.value.id == owner_name
                    )
                if direct_call:
                    self.targets.append(call_target)
            self.generic_visit(node)

        def visit_With(self, node: ast.With) -> None:
            self._visit_with(node)

        def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
            self._visit_with(node)

        def visit_Attribute(self, node: ast.Attribute) -> None:
            if isinstance(node.ctx, (ast.Store, ast.Del)) and (
                _tracked_root_name(node) == owner_name
            ):
                self.tracked_root_mutated = True
            self.generic_visit(node)

        def visit_Subscript(self, node: ast.Subscript) -> None:
            if isinstance(node.ctx, (ast.Store, ast.Del)) and (
                _tracked_root_name(node) == owner_name
            ):
                self.tracked_root_mutated = True
            self.generic_visit(node)

    visitor = Visitor()
    for statement in function.body:
        visitor.visit(statement)
    return [] if visitor.tracked_root_mutated else visitor.targets


def _resolved_call_targets(
    source: str,
    *,
    path: Path = Path("conftest.py"),
) -> set[str]:
    tree = ast.parse(source)
    resolver = _BoundedModuleResolver(path, tree)
    return {
        target
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        if (target := resolver.call_target(node)) is not None
    }


def _resolved_patch_lines(
    source: str,
    *,
    path: Path = Path("conftest.py"),
) -> list[int]:
    tree = ast.parse(source)
    return _BoundedModuleResolver(path, tree).compatibility_patches()


def _resolved_unsupported_carriers(
    source: str,
    *,
    path: Path = Path("conftest.py"),
) -> list[tuple[int, str]]:
    tree = ast.parse(source)
    return _BoundedModuleResolver(path, tree).unsupported_carriers()


def test_provider_surface_is_closed_and_exists() -> None:
    assert all(path.is_file() for path in PROVIDER_PATHS)
    assert len(PROVIDER_PATHS) == 4


def test_root_retains_exactly_one_metrics_compatibility_patch() -> None:
    assignments: list[tuple[Path, int]] = []
    for path, tree in _trees().items():
        resolver = _BoundedModuleResolver(path, tree)
        assignments.extend((path, line) for line in resolver.compatibility_patches())

    assert len(assignments) == 1
    assert assignments[0][0] == Path("conftest.py")


def test_provider_surface_has_no_unsupported_client_carriers() -> None:
    violations: list[str] = []
    for path, tree in _trees().items():
        resolver = _BoundedModuleResolver(path, tree)
        violations.extend(
            f"{path}:{line}:{reason}" for line, reason in resolver.unsupported_carriers()
        )

    assert violations == []


def test_provider_surface_has_no_sys_modules_mutation() -> None:
    violations: list[str] = []
    for path, tree in _trees().items():
        for node in ast.walk(tree):
            targets: list[ast.AST] = []
            if isinstance(node, ast.Assign):
                targets.extend(node.targets)
            elif isinstance(node, ast.AnnAssign):
                targets.append(node.target)
            elif isinstance(node, ast.AugAssign):
                targets.append(node.target)
            elif isinstance(node, ast.Delete):
                targets.extend(node.targets)
            if any(_is_sys_modules_target(target) for target in targets):
                violations.append(f"{path}:{node.lineno}")

    assert violations == []


def test_raw_client_construction_has_one_provider_owner() -> None:
    violations: list[str] = []
    allowed: list[str] = []

    class Visitor(ast.NodeVisitor):
        def __init__(
            self,
            path: Path,
            resolver: _BoundedModuleResolver,
        ) -> None:
            self.path = path
            self.resolver = resolver
            self.functions: list[str] = []

        def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
            self.functions.append(node.name)
            self.generic_visit(node)
            self.functions.pop()

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self._visit_function(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            self._visit_function(node)

        def visit_Call(self, node: ast.Call) -> None:
            call_target = self.resolver.call_target(node)
            if call_target in {TESTCLIENT_SYMBOL, METRICS_CLIENT_SYMBOL}:
                location = f"{self.path}:{node.lineno}"
                if (
                    self.path == Path("tests/_client.py")
                    and self.functions == ["make_test_client"]
                    and call_target == METRICS_CLIENT_SYMBOL
                ):
                    allowed.append(location)
                else:
                    violations.append(location)
            self.generic_visit(node)

    for path, tree in _trees().items():
        Visitor(path, _BoundedModuleResolver(path, tree)).visit(tree)

    assert len(allowed) == 1
    assert violations == []


def test_deprecated_client_factories_have_only_compatibility_owners() -> None:
    violations: list[str] = []
    allowed: list[str] = []

    class Visitor(ast.NodeVisitor):
        def __init__(
            self,
            path: Path,
            resolver: _BoundedModuleResolver,
        ) -> None:
            self.path = path
            self.resolver = resolver
            self.functions: list[str] = []

        def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
            self.functions.append(node.name)
            self.generic_visit(node)
            self.functions.pop()

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self._visit_function(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            self._visit_function(node)

        def visit_Call(self, node: ast.Call) -> None:
            call_target = self.resolver.call_target(node)
            if call_target == GET_CLIENT_SYMBOL:
                violations.append(f"{self.path}:{node.lineno}")
            elif call_target == MAKE_CLIENT_SYMBOL:
                location = f"{self.path}:{node.lineno}"
                if self.path == Path("tests/_client.py") and self.functions in (
                    ["open_test_client"],
                    ["get_client"],
                ):
                    allowed.append(location)
                else:
                    violations.append(location)
            self.generic_visit(node)

    for path, tree in _trees().items():
        Visitor(path, _BoundedModuleResolver(path, tree)).visit(tree)

    assert len(allowed) == 2
    assert violations == []


def test_managed_client_contract_and_fixture_ownership() -> None:
    trees = _trees()
    root_functions = _function_map(trees[Path("conftest.py")])
    shared_functions = _function_map(trees[Path("tests/conftest.py")])
    client_functions = _function_map(trees[Path("tests/_client.py")])
    shared_source = Path("tests/conftest.py").read_text(encoding="utf-8")
    client_source = Path("tests/_client.py").read_text(encoding="utf-8")

    assert ROOT_FORBIDDEN_FIXTURES.isdisjoint(root_functions)
    assert SHARED_CLIENT_FIXTURES <= set(shared_functions)
    assert "open_test_client" in client_functions
    assert _direct_fixture_with_targets(
        client_source,
        path=Path("tests/_client.py"),
        function_name="open_test_client",
        owner_name="make_test_client",
        owner_target=MAKE_CLIENT_SYMBOL,
        attribute_name=None,
        call_target=MAKE_CLIENT_SYMBOL,
    ) == [MAKE_CLIENT_SYMBOL]

    unmanaged: list[str] = []
    for fixture_name in sorted(SHARED_CLIENT_FIXTURES):
        targets = _direct_fixture_with_targets(
            shared_source,
            path=Path("tests/conftest.py"),
            function_name=fixture_name,
            owner_name="test_client_helpers",
            owner_target=CLIENT_HELPERS_MODULE,
            attribute_name="open_test_client",
            call_target=OPEN_CLIENT_SYMBOL,
        )
        if targets != [OPEN_CLIENT_SYMBOL]:
            unmanaged.append(fixture_name)
    assert unmanaged == []


def test_bounded_resolver_recognizes_supported_client_reference_shapes() -> None:
    sources = (
        """
from fastapi.testclient import TestClient
from tests._client import (
    get_client,
    MetricsAwareTestClient,
    make_test_client,
    open_test_client,
)
TestClient(app)
MetricsAwareTestClient(app)
with get_client():
    pass
with open_test_client(app):
    pass
with make_test_client(app):
    pass
""",
        """
from fastapi.testclient import TestClient as ImportedTestClient
from tests._client import MetricsAwareTestClient as ImportedMetricsClient
from tests._client import get_client as imported_getter
from tests._client import make_test_client as imported_factory
from tests._client import open_test_client as imported_manager
ImportedTestClient(app)
ImportedMetricsClient(app)
with imported_getter():
    pass
with imported_manager(app):
    pass
with imported_factory(app):
    pass
""",
        """
import fastapi.testclient as fastapi_clients
import tests._client as client_helpers
fastapi_clients.TestClient(app)
client_helpers.MetricsAwareTestClient(app)
with client_helpers.get_client():
    pass
with client_helpers.open_test_client(app):
    pass
with client_helpers.make_test_client(app):
    pass
""",
        """
from fastapi.testclient import TestClient as ImportedTestClient
from tests._client import MetricsAwareTestClient as ImportedMetricsClient
from tests._client import get_client as imported_getter
from tests._client import make_test_client as imported_factory
from tests._client import open_test_client as imported_manager
raw_alias = ImportedTestClient
metrics_alias = ImportedMetricsClient
getter_alias = imported_getter
factory_alias = imported_factory
managed_alias = imported_manager
raw_alias(app)
metrics_alias(app)
with getter_alias():
    pass
with managed_alias(app):
    pass
with factory_alias(app):
    pass
""",
    )

    for source in sources:
        assert _resolved_call_targets(source) == TRACKED_SYMBOLS
        assert _resolved_unsupported_carriers(source) == []


def test_bounded_resolver_fails_closed_when_tracked_bindings_are_rebound() -> None:
    sources = (
        """
from fastapi.testclient import TestClient
TestClient(app)
TestClient = unrelated_client
""",
        """
from fastapi.testclient import TestClient
from tests._client import open_test_client
TestClient(app)
TestClient = open_test_client
""",
        """
from fastapi.testclient import TestClient
TestClient(app)
def TestClient():
    pass
""",
        """
from fastapi.testclient import TestClient
TestClient(app)
from tests._client import open_test_client as TestClient
""",
    )

    for source in sources:
        unsupported = _resolved_unsupported_carriers(source)
        assert len(unsupported) == 1
        assert unsupported[0][1] == "tracked_binding_rebound"


def test_direct_fixture_guard_uses_compiler_scope_for_one_exact_call_shape() -> None:
    def targets(source: str) -> list[str]:
        return _direct_fixture_with_targets(
            source,
            path=Path("tests/conftest.py"),
            function_name="client",
            owner_name="test_client_helpers",
            owner_target=CLIENT_HELPERS_MODULE,
            attribute_name="open_test_client",
            call_target=OPEN_CLIENT_SYMBOL,
        )

    direct_source = """
from tests import _client as test_client_helpers
def client(app):
    with test_client_helpers.open_test_client(app) as managed_client:
        yield managed_client
"""
    nested_scope_source = """
from tests import _client as test_client_helpers
def client(app, managers):
    def nested(test_client_helpers):
        return test_client_helpers
    local_values = [test_client_helpers for test_client_helpers in managers]
    with test_client_helpers.open_test_client(app) as managed_client:
        yield managed_client, nested, local_values
"""

    invalid_sources = (
        """
from tests import _client as test_client_helpers
def client(app, test_client_helpers):
    with test_client_helpers.open_test_client(app):
        yield
""",
        """
from tests import _client as test_client_helpers
def client(app):
    with test_client_helpers.open_test_client(app):
        yield
    test_client_helpers = object()
""",
        """
from tests import _client as test_client_helpers
def client(app, manager):
    with manager as test_client_helpers:
        pass
    with test_client_helpers.open_test_client(app):
        yield
""",
        """
from tests import _client as test_client_helpers
def client(app, managers):
    for test_client_helpers in managers:
        with test_client_helpers.open_test_client(app):
            yield
""",
        """
from tests import _client as test_client_helpers
def client(app, manager):
    if (test_client_helpers := manager):
        pass
    with test_client_helpers.open_test_client(app):
        yield
""",
        """
from tests import _client as test_client_helpers
def client(app):
    try:
        pass
    except Exception as test_client_helpers:
        pass
    with test_client_helpers.open_test_client(app):
        yield
""",
        """
from tests import _client as test_client_helpers
def client(app):
    def test_client_helpers():
        pass
    with test_client_helpers.open_test_client(app):
        yield
""",
        """
from tests import _client as test_client_helpers
def client(app):
    from tests import _client as test_client_helpers
    with test_client_helpers.open_test_client(app):
        yield
""",
        """
from tests import _client as test_client_helpers
def client(app):
    global test_client_helpers
    with test_client_helpers.open_test_client(app):
        yield
""",
        """
from tests import _client as test_client_helpers
def client(app):
    with test_client_helpers.open_test_client(app):
        yield
    del test_client_helpers
""",
        """
from tests import _client as test_client_helpers
def client(app, value):
    match value:
        case test_client_helpers:
            pass
    with test_client_helpers.open_test_client(app):
        yield
""",
        """
from tests import _client as test_client_helpers
def client(app, manager):
    test_client_helpers.open_test_client = manager
    with test_client_helpers.open_test_client(app):
        yield
""",
        """
from tests import _client as test_client_helpers
def client(app, manager):
    test_client_helpers["open_test_client"] = manager
    with test_client_helpers.open_test_client(app):
        yield
""",
        """
from tests import _client as test_client_helpers
def client(app):
    manager = test_client_helpers.open_test_client
    with manager(app):
        yield
""",
    )

    assert targets(direct_source) == [OPEN_CLIENT_SYMBOL]
    assert targets(nested_scope_source) == [OPEN_CLIENT_SYMBOL]
    assert all(targets(source) == [] for source in invalid_sources)


def test_bounded_resolver_ignores_unrelated_names_and_flags_two_hop_aliases() -> None:
    unrelated_source = """
import unrelated_clients as clients
from unrelated_clients import MetricsAwareTestClient
from unrelated_clients import TestClient
from unrelated_clients import get_client
from unrelated_clients import make_test_client
from unrelated_clients import open_test_client
clients.TestClient(app)
clients.MetricsAwareTestClient(app)
TestClient(app)
MetricsAwareTestClient(app)
with get_client():
    pass
with open_test_client(app):
    pass
with make_test_client(app):
    pass
"""
    unrelated_two_hop_source = """
from unrelated_clients import TestClient as ImportedTestClient
first_alias = ImportedTestClient
second_alias = first_alias
second_alias(app)
"""
    two_hop_source = """
from fastapi.testclient import TestClient as ImportedTestClient
from tests._client import open_test_client as imported_manager
first_raw_alias = ImportedTestClient
second_raw_alias = first_raw_alias
first_managed_alias = imported_manager
second_managed_alias = first_managed_alias
second_raw_alias(app)
with second_managed_alias(app):
    pass
"""

    assert _resolved_call_targets(unrelated_source) == set()
    assert _resolved_unsupported_carriers(unrelated_source) == []
    assert _resolved_call_targets(unrelated_two_hop_source) == set()
    assert _resolved_unsupported_carriers(unrelated_two_hop_source) == []
    assert _resolved_call_targets(two_hop_source) == set()
    unsupported = _resolved_unsupported_carriers(two_hop_source)
    assert len(unsupported) == 2
    assert {reason for _line, reason in unsupported} == {"tracked_alias_depth"}


def test_bounded_resolver_recognizes_assignment_and_setattr_patches() -> None:
    one_patch_source = """
import fastapi.testclient as imported_fastapi_clients
from tests._client import MetricsAwareTestClient as ImportedMetricsClient
module_alias = imported_fastapi_clients
metrics_alias = ImportedMetricsClient
module_alias.TestClient = metrics_alias
"""
    duplicate_patch_source = """
import fastapi.testclient as fastapi_clients
from tests._client import MetricsAwareTestClient as MetricsClient
fastapi_clients.TestClient = MetricsClient
fastapi_clients.TestClient = MetricsClient
"""
    setattr_patch_source = """
import fastapi.testclient as fastapi_clients
from tests._client import MetricsAwareTestClient as MetricsClient
setattr(fastapi_clients, "TestClient", MetricsClient)
"""
    duplicate_setattr_source = """
import fastapi.testclient as fastapi_clients
from tests._client import MetricsAwareTestClient as MetricsClient
setattr(fastapi_clients, "TestClient", MetricsClient)
setattr(fastapi_clients, "TestClient", MetricsClient)
"""
    assignment_and_setattr_source = """
import fastapi.testclient as fastapi_clients
from tests._client import MetricsAwareTestClient as MetricsClient
fastapi_clients.TestClient = MetricsClient
setattr(fastapi_clients, "TestClient", MetricsClient)
"""
    unrelated_patch_source = """
import unrelated_clients as fastapi_clients
from unrelated_clients import MetricsAwareTestClient
fastapi_clients.TestClient = MetricsAwareTestClient
setattr(fastapi_clients, "TestClient", MetricsAwareTestClient)
"""
    unrelated_value_source = """
import fastapi.testclient as fastapi_clients
from unrelated_clients import MetricsAwareTestClient
setattr(fastapi_clients, "TestClient", MetricsAwareTestClient)
"""
    other_literal_source = """
import fastapi.testclient as fastapi_clients
from tests._client import MetricsAwareTestClient
setattr(fastapi_clients, "OtherClient", MetricsAwareTestClient)
"""

    assert len(_resolved_patch_lines(one_patch_source)) == 1
    assert len(_resolved_patch_lines(duplicate_patch_source)) == 2
    assert len(_resolved_patch_lines(setattr_patch_source)) == 1
    assert len(_resolved_patch_lines(duplicate_setattr_source)) == 2
    assert len(_resolved_patch_lines(assignment_and_setattr_source)) == 2
    assert _resolved_patch_lines(unrelated_patch_source) == []
    assert _resolved_patch_lines(unrelated_value_source) == []
    assert _resolved_patch_lines(other_literal_source) == []
    assert _resolved_unsupported_carriers(one_patch_source) == []
    assert _resolved_unsupported_carriers(setattr_patch_source) == []
    assert _resolved_unsupported_carriers(unrelated_patch_source) == []
    assert _resolved_unsupported_carriers(unrelated_value_source) == []
    assert _resolved_unsupported_carriers(other_literal_source) == []


def test_bounded_resolver_fails_closed_for_dynamic_and_two_hop_patch_operands() -> None:
    dynamic_attribute_source = """
import fastapi.testclient as fastapi_clients
from tests._client import MetricsAwareTestClient
patch_name = "TestClient"
setattr(fastapi_clients, patch_name, MetricsAwareTestClient)
"""
    two_hop_operand_source = """
import fastapi.testclient as fastapi_clients
from tests._client import MetricsAwareTestClient as MetricsClient
first_module_alias = fastapi_clients
second_module_alias = first_module_alias
first_value_alias = MetricsClient
second_value_alias = first_value_alias
setattr(second_module_alias, "TestClient", second_value_alias)
"""

    assert _resolved_patch_lines(dynamic_attribute_source) == []
    assert _resolved_unsupported_carriers(dynamic_attribute_source) == [
        (5, "dynamic_patch_attribute")
    ]
    assert _resolved_patch_lines(two_hop_operand_source) == []
    unsupported = _resolved_unsupported_carriers(two_hop_operand_source)
    assert {reason for _line, reason in unsupported} == {
        "tracked_alias_depth",
        "tracked_patch_operand_alias",
    }
    assert unsupported[-1] == (8, "tracked_patch_operand_alias")


def test_compatibility_app_provider_retains_only_assertion_helper() -> None:
    functions = _function_map(_trees()[Path("tests/conftest_app.py")])
    assert set(functions) == {"assert_vip_response"}
