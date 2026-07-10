#!/usr/bin/env python3
"""Fail-closed guard for legacy_app.py compatibility-seam growth."""

from __future__ import annotations

import argparse
import ast
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
import re
import sys
from typing import AbstractSet

REPO_ROOT = Path(__file__).resolve().parents[2]
LEGACY_APP = "legacy_app.py"
LEGACY_SEAM_DOC = "docs/architecture/LEGACY_COMPATIBILITY_SEAM.md"


@dataclass(frozen=True, order=True)
class LegacyFact:
    """One static fact that may not grow inside legacy_app.py."""

    kind: str
    action: str
    target: str
    owner: str

    def display(self) -> str:
        suffix = f" -> {self.owner}" if self.owner else ""
        return f"{self.kind}:{self.action}:{self.target}{suffix}"


APP_ROUTE_METHODS = frozenset(
    {
        "api_route",
        "delete",
        "get",
        "head",
        "middleware",
        "options",
        "patch",
        "post",
        "put",
        "route",
        "trace",
        "websocket",
        "websocket_route",
    }
)
APP_REGISTRATION_METHODS = frozenset(
    {"add_api_route", "add_middleware", "add_route", "add_websocket_route", "include_router"}
)
SENSITIVE_CALL_KEYWORDS: tuple[str, ...] = (
    "api_key",
    "auth",
    "billing",
    "entitlement",
    "llm",
    "provider",
    "quota",
    "receipt",
    "subscription",
)
SENSITIVE_CALL_LIMITS: Mapping[str, int] = {
    "api_key": 4,
    "auth": 0,
    "billing": 0,
    "entitlement": 0,
    "llm": 1,
    "provider": 1,
    "quota": 1,
    "receipt": 0,
    "subscription": 0,
}
SENSITIVE_APP_SURFACE_LIMITS: Mapping[str, int] = {
    "api_key": 0,
    "auth": 0,
    "billing": 0,
    "entitlement": 0,
    "llm": 0,
    "provider": 0,
    "quota": 0,
    "receipt": 0,
    "subscription": 0,
}
UNRESOLVED_APP_ROUTER_IMPORT = "<unresolved app.routers import>"
UNRESOLVED_DYNAMIC_ROUTER_IMPORT = "<unresolved dynamic router import>"

ALLOWED_LEGACY_ROUTE_FACTS: frozenset[LegacyFact] = frozenset()

FORBIDDEN_LEGACY_RUNTIME_REGISTRARS: Mapping[str, str] = {
    "app.bootstrap.http_stack.register_http_middleware_stack": ("register_http_middleware_stack"),
    "app.security.rate_limit.wire_rate_limiting": "wire_rate_limiting",
}

ALLOWED_ROUTER_IMPORT_FACTS = frozenset(
    {
        LegacyFact("router_import", "app.routers", "vip", "_vip_mod"),
        LegacyFact("router_import", "app.routers.api_key", "api_key_header", ""),
        LegacyFact("router_import", "app.routers.bmi", "bmi_calculate_handler", ""),
        LegacyFact("router_import", "dynamic", "app.routers.plan_export", "_plan_mod"),
        LegacyFact(
            "router_import", "app.routers.pro_nutrition_contracts", "pro_nutrition_plate", ""
        ),
        LegacyFact(
            "router_import", "app.routers.pro_nutrition_contracts", "pro_nutrition_targets", ""
        ),
        LegacyFact(
            "router_import",
            "app.routers.vip",
            "execute_legacy_premium_week_alias_payload",
            "",
        ),
    }
)

REQUIRED_DOC_MARKERS: Mapping[str, str] = {
    "LEGACY_SEAM_STATUS": "accepted_guardrail",
    "LEGACY_SEAM_RUNTIME_BEHAVIOR_CHANGED": "false",
    "LEGACY_SEAM_OPENAPI_CHANGED": "false",
    "LEGACY_SEAM_SEMANTIC_CACHE_SERVING": "false",
    "LEGACY_SEAM_FOODDB_CUTOVER": "false",
    "LEGACY_SEAM_BROAD_REFACTOR": "false",
}
REQUIRED_DOC_TOKENS = (
    "legacy_app.py",
    "app/main.py",
    "app/routers/",
    "app/bootstrap/",
    "new `@app.*` routes",
    "new OpenAPI-visible public surface",
    "semantic-cache serving",
    "FoodDB cutover",
)
MARKER_RE = re.compile(r"<!--\s*([A-Z0-9_]+):\s*(.*?)\s*-->")


def _safe_unparse(node: ast.AST) -> str:
    try:
        return ast.unparse(node).strip()
    except Exception:
        return "<unparseable>"


def _first_arg_label(call: ast.Call) -> str:
    if not call.args:
        return "<missing>"
    arg = call.args[0]
    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
        return arg.value
    if isinstance(arg, ast.Name):
        return arg.id
    return _safe_unparse(arg)


def _parse_source(source_text: str, *, filename: str) -> tuple[ast.Module | None, list[str]]:
    try:
        return ast.parse(source_text, filename=filename), []
    except SyntaxError as exc:
        line = exc.lineno or 0
        return None, [f"{filename}:{line}: syntax error: {exc.msg}"]


def _collect_app_aliases(tree: ast.Module) -> tuple[frozenset[str], frozenset[str]]:
    app_aliases: set[str] = {"app"}
    router_aliases: set[str] = set()
    changed = True
    while changed:
        changed = False
        for node in ast.walk(tree):
            value: ast.AST | None = None
            targets: list[ast.expr] = []
            if isinstance(node, ast.Assign):
                value = node.value
                targets = list(node.targets)
            elif isinstance(node, ast.AnnAssign) and node.value is not None:
                value = node.value
                targets = [node.target]
            if value is None:
                continue

            for target in targets:
                if not isinstance(target, ast.Name):
                    continue
                if (
                    isinstance(value, ast.Name)
                    and value.id in app_aliases
                    and target.id not in app_aliases
                ):
                    app_aliases.add(target.id)
                    changed = True
                elif (
                    isinstance(value, ast.Name)
                    and value.id in router_aliases
                    and target.id not in router_aliases
                ):
                    router_aliases.add(target.id)
                    changed = True
                elif (
                    isinstance(value, ast.Attribute)
                    and value.attr == "router"
                    and isinstance(value.value, ast.Name)
                    and value.value.id in app_aliases
                    and target.id not in router_aliases
                ):
                    router_aliases.add(target.id)
                    changed = True
    return frozenset(app_aliases), frozenset(router_aliases)


def _app_call_action(
    func: ast.AST,
    methods: frozenset[str],
    *,
    app_aliases: frozenset[str] = frozenset({"app"}),
    router_aliases: frozenset[str] = frozenset(),
    static_string_bindings: Mapping[str, str] | None = None,
) -> str | None:
    if isinstance(func, ast.Attribute) and func.attr in methods:
        if isinstance(func.value, ast.Name) and func.value.id in app_aliases:
            return func.attr
        if isinstance(func.value, ast.Name) and func.value.id in router_aliases:
            return f"router.{func.attr}"
        if (
            isinstance(func.value, ast.Attribute)
            and func.value.attr == "router"
            and isinstance(func.value.value, ast.Name)
            and func.value.value.id in app_aliases
        ):
            return f"router.{func.attr}"

    getattr_action = _getattr_app_call_action(
        func,
        methods,
        app_aliases=app_aliases,
        router_aliases=router_aliases,
        static_string_bindings=static_string_bindings,
    )
    if getattr_action is not None:
        return getattr_action
    return None


def _collect_bound_app_call_aliases(
    tree: ast.Module,
    *,
    app_aliases: AbstractSet[str],
    static_string_bindings: Mapping[str, str],
) -> dict[str, str]:
    aliases: dict[str, str] = {}
    changed = True
    while changed:
        changed = False
        for node in ast.walk(tree):
            value: ast.AST | None = None
            targets: list[ast.expr] = []
            if isinstance(node, ast.Assign):
                value = node.value
                targets = list(node.targets)
            elif isinstance(node, ast.AnnAssign) and node.value is not None:
                value = node.value
                targets = [node.target]
            if value is None:
                continue

            action: str | None = None
            if (
                isinstance(value, ast.Attribute)
                and isinstance(value.value, ast.Name)
                and value.value.id in app_aliases
                and value.attr in APP_ROUTE_METHODS | APP_REGISTRATION_METHODS
            ):
                action = value.attr
            elif (
                isinstance(value, ast.Call)
                and isinstance(value.func, ast.Name)
                and value.func.id == "getattr"
                and len(value.args) >= 2
                and isinstance(value.args[0], ast.Name)
                and value.args[0].id in app_aliases
            ):
                method_node = value.args[1]
                method_name: str | None
                if isinstance(method_node, ast.Constant) and isinstance(method_node.value, str):
                    method_name = method_node.value
                elif isinstance(method_node, ast.Name):
                    method_name = static_string_bindings.get(method_node.id)
                else:
                    method_name = None
                if method_name in APP_ROUTE_METHODS | APP_REGISTRATION_METHODS:
                    action = method_name
            elif isinstance(value, ast.Name):
                action = aliases.get(value.id)
            if action is None:
                continue
            for target in targets:
                if isinstance(target, ast.Name) and aliases.get(target.id) != action:
                    aliases[target.id] = action
                    changed = True
    return aliases


def _collect_middleware_decorator_aliases(
    tree: ast.Module,
    *,
    app_aliases: frozenset[str],
    router_aliases: frozenset[str],
    bound_call_aliases: Mapping[str, str],
    static_string_bindings: Mapping[str, str],
) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        value: ast.AST | None = None
        targets: list[ast.expr] = []
        if isinstance(node, ast.Assign):
            value = node.value
            targets = list(node.targets)
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            value = node.value
            targets = [node.target]
        if not isinstance(value, ast.Call):
            continue
        action = _app_call_action(
            value.func,
            APP_ROUTE_METHODS,
            app_aliases=app_aliases,
            router_aliases=router_aliases,
            static_string_bindings=static_string_bindings,
        )
        if action is None and isinstance(value.func, ast.Name):
            action = bound_call_aliases.get(value.func.id)
        if action != "middleware":
            continue
        for target in targets:
            if isinstance(target, ast.Name):
                aliases[target.id] = _first_arg_label(value)
    return aliases


def _getattr_app_call_action(
    func: ast.AST,
    methods: AbstractSet[str],
    *,
    app_aliases: frozenset[str],
    router_aliases: frozenset[str],
    static_string_bindings: Mapping[str, str] | None = None,
) -> str | None:
    method = _getattr_method_name(
        func,
        methods,
        static_string_bindings=static_string_bindings,
    )
    if method is None or not isinstance(func, ast.Call) or not func.args:
        return None
    target = func.args[0]
    if isinstance(target, ast.Name) and target.id in app_aliases:
        return method
    if isinstance(target, ast.Name) and target.id in router_aliases:
        return f"router.{method}"
    if (
        isinstance(target, ast.Attribute)
        and target.attr == "router"
        and isinstance(target.value, ast.Name)
        and target.value.id in app_aliases
    ):
        return f"router.{method}"
    return None


def collect_legacy_route_facts(source_text: str, *, filename: str = LEGACY_APP) -> set[LegacyFact]:
    """Return route and router-registration facts from legacy_app.py source."""

    tree, errors = _parse_source(source_text, filename=filename)
    if errors or tree is None:
        return set()

    facts: set[LegacyFact] = set()
    app_aliases, router_aliases = _collect_app_aliases(tree)
    static_string_bindings = _collect_static_string_bindings(tree)
    bound_call_aliases = _collect_bound_app_call_aliases(
        tree,
        app_aliases=app_aliases,
        static_string_bindings=static_string_bindings,
    )
    middleware_decorator_aliases = _collect_middleware_decorator_aliases(
        tree,
        app_aliases=app_aliases,
        router_aliases=router_aliases,
        bound_call_aliases=bound_call_aliases,
        static_string_bindings=static_string_bindings,
    )
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Name):
                    target = middleware_decorator_aliases.get(decorator.id)
                    if target is not None:
                        facts.add(
                            LegacyFact(
                                "decorator",
                                "middleware",
                                target,
                                node.name,
                            )
                        )
                    continue
                if not isinstance(decorator, ast.Call):
                    continue
                action = _app_call_action(
                    decorator.func,
                    APP_ROUTE_METHODS,
                    app_aliases=app_aliases,
                    router_aliases=router_aliases,
                    static_string_bindings=static_string_bindings,
                )
                if action is None and isinstance(decorator.func, ast.Name):
                    action = bound_call_aliases.get(decorator.func.id)
                if action is not None:
                    facts.add(
                        LegacyFact("decorator", action, _first_arg_label(decorator), node.name)
                    )
        elif isinstance(node, ast.Call):
            call = node
            if isinstance(call.func, ast.Call):
                action = _app_call_action(
                    call.func.func,
                    APP_ROUTE_METHODS,
                    app_aliases=app_aliases,
                    router_aliases=router_aliases,
                    static_string_bindings=static_string_bindings,
                )
                if action is None and isinstance(call.func.func, ast.Name):
                    action = bound_call_aliases.get(call.func.func.id)
                if action is not None:
                    facts.add(
                        LegacyFact(
                            "registration",
                            action,
                            _first_arg_label(call.func),
                            "",
                        )
                    )
            action = _app_call_action(
                call.func,
                APP_REGISTRATION_METHODS,
                app_aliases=app_aliases,
                router_aliases=router_aliases,
                static_string_bindings=static_string_bindings,
            )
            if action is None and isinstance(call.func, ast.Name):
                action = bound_call_aliases.get(call.func.id)
            if isinstance(call.func, ast.Name):
                middleware_target = middleware_decorator_aliases.get(call.func.id)
                if middleware_target is not None:
                    facts.add(
                        LegacyFact(
                            "registration",
                            "middleware",
                            middleware_target,
                            "",
                        )
                    )
            if action is not None:
                facts.add(LegacyFact("registration", action, _first_arg_label(call), ""))
    return facts


def _static_module_reference(
    node: ast.AST,
    *,
    module_aliases: Mapping[str, str],
    import_module_aliases: AbstractSet[str],
) -> str | None:
    if isinstance(node, ast.Name):
        return module_aliases.get(node.id)
    if isinstance(node, ast.Attribute):
        parent = _static_module_reference(
            node.value,
            module_aliases=module_aliases,
            import_module_aliases=import_module_aliases,
        )
        if parent is not None:
            return f"{parent}.{node.attr}"
        return None
    if not isinstance(node, ast.Call):
        return None

    is_import_module = (
        isinstance(node.func, ast.Name) and node.func.id in import_module_aliases
    ) or (
        isinstance(node.func, ast.Attribute)
        and node.func.attr == "import_module"
        and isinstance(node.func.value, ast.Name)
        and module_aliases.get(node.func.value.id) == "importlib"
    )
    if not is_import_module or not node.args:
        return None
    module_arg = node.args[0]
    if isinstance(module_arg, ast.Constant) and isinstance(module_arg.value, str):
        return module_arg.value
    return None


def _forbidden_registrar_label(
    node: ast.AST,
    *,
    callable_aliases: Mapping[str, str],
    module_aliases: Mapping[str, str],
    import_module_aliases: AbstractSet[str],
    static_string_bindings: Mapping[str, str],
) -> str | None:
    if isinstance(node, ast.Name):
        return callable_aliases.get(node.id)
    if isinstance(node, ast.Attribute):
        module_name = _static_module_reference(
            node.value,
            module_aliases=module_aliases,
            import_module_aliases=import_module_aliases,
        )
        if module_name is None:
            return None
        return FORBIDDEN_LEGACY_RUNTIME_REGISTRARS.get(f"{module_name}.{node.attr}")
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "getattr"
        and len(node.args) >= 2
    ):
        module_name = _static_module_reference(
            node.args[0],
            module_aliases=module_aliases,
            import_module_aliases=import_module_aliases,
        )
        if module_name is None:
            return None
        method_name = _resolve_static_string(node.args[1], static_string_bindings)
        if method_name is None:
            return None
        return FORBIDDEN_LEGACY_RUNTIME_REGISTRARS.get(f"{module_name}.{method_name}")
    return None


def collect_forbidden_runtime_registration_facts(
    source_text: str,
    *,
    filename: str = LEGACY_APP,
) -> set[LegacyFact]:
    """Return canonical runtime registrars invoked from the legacy seam."""

    tree, errors = _parse_source(source_text, filename=filename)
    if errors or tree is None:
        return set()

    module_aliases: dict[str, str] = {}
    import_module_aliases: set[str] = {"import_module"}
    callable_aliases: dict[str, str] = {}
    facts: set[LegacyFact] = set()
    static_string_bindings = _collect_static_string_bindings(tree)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in {
                    "app.bootstrap.http_stack",
                    "app.security.rate_limit",
                    "importlib",
                }:
                    local_name = alias.asname or alias.name.split(".")[0]
                    module_aliases[local_name] = alias.name if alias.asname else local_name
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            for alias in node.names:
                if alias.name == "*":
                    module_prefix = f"{node.module}."
                    for qualified, registrar_label in FORBIDDEN_LEGACY_RUNTIME_REGISTRARS.items():
                        if qualified.startswith(module_prefix):
                            facts.add(
                                LegacyFact(
                                    "runtime_registration",
                                    registrar_label,
                                    "star_import",
                                    "",
                                )
                            )
                    continue
                local_name = alias.asname or alias.name
                qualified = f"{node.module}.{alias.name}"
                label = FORBIDDEN_LEGACY_RUNTIME_REGISTRARS.get(qualified)
                if label is not None:
                    callable_aliases[local_name] = label
                elif qualified in {
                    "app.bootstrap.http_stack",
                    "app.security.rate_limit",
                }:
                    module_aliases[local_name] = qualified
                elif node.module == "importlib" and alias.name == "import_module":
                    import_module_aliases.add(local_name)

    changed = True
    while changed:
        changed = False
        for node in ast.walk(tree):
            value: ast.AST | None = None
            targets: list[ast.expr] = []
            if isinstance(node, ast.Assign):
                value = node.value
                targets = list(node.targets)
            elif isinstance(node, ast.AnnAssign) and node.value is not None:
                value = node.value
                targets = [node.target]
            elif isinstance(node, ast.NamedExpr):
                value = node.value
                targets = [node.target]
            if value is None:
                continue

            module_name = _static_module_reference(
                value,
                module_aliases=module_aliases,
                import_module_aliases=import_module_aliases,
            )
            label = _forbidden_registrar_label(
                value,
                callable_aliases=callable_aliases,
                module_aliases=module_aliases,
                import_module_aliases=import_module_aliases,
                static_string_bindings=static_string_bindings,
            )
            for target in targets:
                if not isinstance(target, ast.Name):
                    continue
                if module_name is not None and module_aliases.get(target.id) != module_name:
                    module_aliases[target.id] = module_name
                    changed = True
                if label is not None and callable_aliases.get(target.id) != label:
                    callable_aliases[target.id] = label
                    changed = True

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        label = _forbidden_registrar_label(
            node.func,
            callable_aliases=callable_aliases,
            module_aliases=module_aliases,
            import_module_aliases=import_module_aliases,
            static_string_bindings=static_string_bindings,
        )
        if label is not None:
            facts.add(
                LegacyFact(
                    "runtime_registration",
                    label,
                    _first_arg_label(node),
                    "",
                )
            )
    return facts


def collect_router_import_facts(source_text: str, *, filename: str = LEGACY_APP) -> set[LegacyFact]:
    """Return app.routers import facts from legacy_app.py source."""

    tree, errors = _parse_source(source_text, filename=filename)
    if errors or tree is None:
        return set()

    facts: set[LegacyFact] = set()
    dynamic_import_names = _collect_dynamic_import_function_names(tree)
    static_string_bindings = _collect_static_string_bindings(tree)
    static_app_router_hint_bindings = _collect_static_app_router_hint_bindings(
        tree,
        static_string_bindings,
    )
    dynamic_import_target_modules = _collect_unresolved_dynamic_import_target_modules(
        tree,
        import_func_names=dynamic_import_names,
        static_string_bindings=static_string_bindings,
    )
    registered_router_targets = _collect_registered_router_targets(
        tree,
        static_string_bindings=static_string_bindings,
    )
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            if node.module != "app.routers" and not node.module.startswith("app.routers."):
                continue
            for alias in node.names:
                facts.add(LegacyFact("router_import", node.module, alias.name, alias.asname or ""))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "app.routers" or alias.name.startswith("app.routers."):
                    facts.add(LegacyFact("router_import", "import", alias.name, alias.asname or ""))
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            value = node.value
            if value is None:
                continue
            targets = list(node.targets) if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                for module_name, target_name in _dynamic_app_router_import_assignments(
                    value,
                    target,
                    import_func_names=dynamic_import_names,
                    static_string_bindings=static_string_bindings,
                    static_app_router_hint_bindings=static_app_router_hint_bindings,
                    registered_router_targets=registered_router_targets,
                ):
                    facts.add(LegacyFact("router_import", "dynamic", module_name, target_name))
        elif isinstance(node, ast.NamedExpr):
            for module_name, target_name in _dynamic_app_router_import_assignments(
                node.value,
                node.target,
                import_func_names=dynamic_import_names,
                static_string_bindings=static_string_bindings,
                static_app_router_hint_bindings=static_app_router_hint_bindings,
                registered_router_targets=registered_router_targets,
            ):
                facts.add(LegacyFact("router_import", "dynamic", module_name, target_name))
        elif isinstance(node, ast.Call):
            if not _is_router_registration_call(
                node,
                static_string_bindings=static_string_bindings,
            ):
                continue
            for module_name in _dynamic_app_router_import_modules(
                node,
                import_func_names=dynamic_import_names,
                static_string_bindings=static_string_bindings,
                static_app_router_hint_bindings=static_app_router_hint_bindings,
                unresolved_router_registration=True,
            ):
                facts.add(
                    LegacyFact(
                        "router_import",
                        "dynamic",
                        module_name,
                        _safe_unparse(node.func),
                    )
                )
            for module_name in _tainted_dynamic_router_modules_in_registration_call(
                node,
                dynamic_import_target_modules,
                static_string_bindings=static_string_bindings,
            ):
                facts.add(
                    LegacyFact(
                        "router_import",
                        "dynamic",
                        module_name,
                        _safe_unparse(node.func),
                    )
                )
    return facts


def _collect_static_string_bindings(tree: ast.Module) -> Mapping[str, str]:
    """Return statically resolvable string assignments used by dynamic imports."""

    bindings: dict[str, str] = {}
    changed = True
    while changed:
        changed = False
        for node in ast.walk(tree):
            value: ast.AST | None = None
            targets: list[ast.expr] = []
            if isinstance(node, ast.Assign):
                value = node.value
                targets = list(node.targets)
            elif isinstance(node, ast.AnnAssign) and node.value is not None:
                value = node.value
                targets = [node.target]
            elif isinstance(node, ast.NamedExpr):
                value = node.value
                targets = [node.target]
            if value is None:
                continue
            resolved = _resolve_static_string(value, bindings)
            if resolved is None:
                continue
            for target in targets:
                for target_name in _assignment_target_names(target):
                    if target_name not in bindings:
                        bindings[target_name] = resolved
                        changed = True
    return bindings


def _resolve_static_string(node: ast.AST, bindings: Mapping[str, str]) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return bindings.get(node.id)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _resolve_static_string(node.left, bindings)
        right = _resolve_static_string(node.right, bindings)
        if left is not None and right is not None:
            return left + right
        return None
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
            elif isinstance(value, ast.FormattedValue):
                formatted_value = _resolve_static_string(value.value, bindings)
                if formatted_value is None:
                    return None
                parts.append(formatted_value)
            else:
                return None
        return "".join(parts)
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "join"
        and len(node.args) == 1
        and isinstance(node.args[0], (ast.List, ast.Tuple))
    ):
        separator = _resolve_static_string(node.func.value, bindings)
        if separator is None:
            return None
        items: list[str] = []
        for item in node.args[0].elts:
            item_value = _resolve_static_string(item, bindings)
            if item_value is None:
                return None
            items.append(item_value)
        return separator.join(items)
    return None


def _collect_static_app_router_hint_bindings(
    tree: ast.Module,
    static_string_bindings: Mapping[str, str],
) -> frozenset[str]:
    hints: set[str] = set()
    changed = True
    while changed:
        changed = False
        for node in ast.walk(tree):
            value: ast.AST | None = None
            targets: list[ast.expr] = []
            if isinstance(node, ast.Assign):
                value = node.value
                targets = list(node.targets)
            elif isinstance(node, ast.AnnAssign) and node.value is not None:
                value = node.value
                targets = [node.target]
            elif isinstance(node, ast.NamedExpr):
                value = node.value
                targets = [node.target]
            if value is None or not _static_app_router_hint(
                value,
                static_string_bindings,
                frozenset(hints),
            ):
                continue
            for target in targets:
                for target_name in _assignment_target_names(target):
                    if target_name not in hints:
                        hints.add(target_name)
                        changed = True
    return frozenset(hints)


def _static_app_router_hint(
    node: ast.AST,
    bindings: Mapping[str, str],
    hint_bindings: frozenset[str],
) -> bool:
    resolved = _resolve_static_string(node, bindings)
    if resolved is not None:
        return resolved == "app.routers" or resolved.startswith("app.routers.")
    if isinstance(node, ast.Name) and node.id in hint_bindings:
        return True
    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and isinstance(child.value, str):
            if "app.routers" in child.value:
                return True
        elif isinstance(child, ast.Name):
            if child.id in hint_bindings:
                return True
            bound = bindings.get(child.id)
            if bound is not None and (bound == "app.routers" or bound.startswith("app.routers.")):
                return True
    return False


def _collect_registered_router_targets(
    tree: ast.Module,
    *,
    static_string_bindings: Mapping[str, str] | None = None,
) -> frozenset[str]:
    targets: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not _is_router_registration_call(
            node,
            static_string_bindings=static_string_bindings,
        ):
            continue
        if not node.args:
            continue
        first_arg = node.args[0]
        if isinstance(first_arg, ast.Name):
            targets.add(first_arg.id)
    return frozenset(targets)


def _collect_dynamic_import_function_names(tree: ast.Module) -> frozenset[str]:
    """Return names that may call Python's dynamic import helpers."""

    names: set[str] = {"__import__", "import_module"}
    changed = True
    while changed:
        changed = False
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module in {"builtins", "importlib"}:
                for alias in node.names:
                    if (node.module, alias.name) not in {
                        ("builtins", "__import__"),
                        ("importlib", "import_module"),
                    }:
                        continue
                    imported_name = alias.asname or alias.name
                    if imported_name not in names:
                        names.add(imported_name)
                        changed = True
                continue

            value: ast.AST | None = None
            targets: list[ast.expr] = []
            if isinstance(node, ast.Assign):
                value = node.value
                targets = list(node.targets)
            elif isinstance(node, ast.AnnAssign) and node.value is not None:
                value = node.value
                targets = [node.target]
            elif isinstance(node, ast.NamedExpr):
                value = node.value
                targets = [node.target]
            if value is None or not _is_dynamic_import_function_reference(
                value,
                import_func_names=frozenset(names),
            ):
                continue

            for target in targets:
                for target_name in _assignment_target_names(target):
                    if target_name not in names:
                        names.add(target_name)
                        changed = True
    return frozenset(names)


def _collect_unresolved_dynamic_import_target_modules(
    tree: ast.Module,
    *,
    import_func_names: frozenset[str],
    static_string_bindings: Mapping[str, str],
) -> Mapping[str, frozenset[str]]:
    """Return unresolved dynamic-import targets for fail-closed router registration checks."""

    targets: dict[str, set[str]] = {}
    changed = True
    while changed:
        changed = False
        for node in ast.walk(tree):
            value: ast.AST | None = None
            assignment_targets: list[ast.expr] = []
            if isinstance(node, ast.Assign):
                value = node.value
                assignment_targets = list(node.targets)
            elif isinstance(node, ast.AnnAssign) and node.value is not None:
                value = node.value
                assignment_targets = [node.target]
            elif isinstance(node, ast.NamedExpr):
                value = node.value
                assignment_targets = [node.target]
            if value is None:
                continue

            module_names: set[str] = set()
            if _contains_unresolved_dynamic_import(
                value,
                import_func_names=import_func_names,
                static_string_bindings=static_string_bindings,
            ):
                module_names.add(UNRESOLVED_DYNAMIC_ROUTER_IMPORT)
            module_names.update(_tainted_dynamic_router_modules_in_node(value, targets))
            if not module_names:
                continue

            for target in assignment_targets:
                for target_name in _assignment_target_names(target):
                    target_modules = targets.setdefault(target_name, set())
                    before = len(target_modules)
                    target_modules.update(module_names)
                    changed = changed or len(target_modules) != before
    return {name: frozenset(module_names) for name, module_names in targets.items()}


def _is_dynamic_import_function_reference(
    node: ast.AST,
    *,
    import_func_names: frozenset[str],
) -> bool:
    if isinstance(node, ast.Name):
        return node.id in import_func_names
    return isinstance(node, ast.Attribute) and node.attr == "import_module"


def _is_router_registration_call(
    call: ast.Call,
    *,
    static_string_bindings: Mapping[str, str] | None = None,
) -> bool:
    return (
        isinstance(call.func, ast.Attribute)
        and call.func.attr in APP_REGISTRATION_METHODS
        or _getattr_method_name(
            call.func,
            APP_REGISTRATION_METHODS,
            static_string_bindings=static_string_bindings,
        )
        is not None
    )


def _getattr_method_name(
    func: ast.AST,
    methods: AbstractSet[str],
    *,
    static_string_bindings: Mapping[str, str] | None = None,
) -> str | None:
    if not isinstance(func, ast.Call):
        return None
    if not isinstance(func.func, ast.Name) or func.func.id != "getattr":
        return None
    if len(func.args) < 2:
        return None
    method = _resolve_static_string(func.args[1], static_string_bindings or {})
    if method in methods:
        return method
    return None


def _assignment_target_names(node: ast.AST) -> tuple[str, ...]:
    if isinstance(node, ast.Name):
        return (node.id,)
    if isinstance(node, (ast.Tuple, ast.List)):
        names: list[str] = []
        for element in node.elts:
            names.extend(_assignment_target_names(element))
        return tuple(names)
    return ()


def _dynamic_app_router_import_assignments(
    value: ast.AST,
    target: ast.AST,
    *,
    import_func_names: frozenset[str],
    static_string_bindings: Mapping[str, str],
    static_app_router_hint_bindings: frozenset[str],
    registered_router_targets: frozenset[str],
) -> tuple[tuple[str, str], ...]:
    """Return dynamic app.routers imports paired with the assigned target name."""

    if isinstance(target, (ast.Tuple, ast.List)) and isinstance(value, (ast.Tuple, ast.List)):
        destructured_pairs: list[tuple[str, str]] = []
        for value_item, target_item in zip(value.elts, target.elts, strict=False):
            destructured_pairs.extend(
                _dynamic_app_router_import_assignments(
                    value_item,
                    target_item,
                    import_func_names=import_func_names,
                    static_string_bindings=static_string_bindings,
                    static_app_router_hint_bindings=static_app_router_hint_bindings,
                    registered_router_targets=registered_router_targets,
                )
            )
        return tuple(destructured_pairs)

    target_names = _assignment_target_names(target)
    if not target_names:
        return ()

    pairs: list[tuple[str, str]] = []
    for module_name in _dynamic_app_router_import_modules(
        value,
        import_func_names=import_func_names,
        static_string_bindings=static_string_bindings,
        static_app_router_hint_bindings=static_app_router_hint_bindings,
        unresolved_router_registration=False,
    ):
        for target_name in target_names:
            pairs.append((module_name, target_name))
    for target_name in target_names:
        if target_name not in registered_router_targets:
            continue
        if pairs:
            continue
        if _contains_unresolved_dynamic_import(value, import_func_names=import_func_names):
            pairs.append((UNRESOLVED_DYNAMIC_ROUTER_IMPORT, target_name))
    return tuple(pairs)


def _tainted_dynamic_router_modules_in_registration_call(
    call: ast.Call,
    dynamic_import_target_modules: Mapping[str, AbstractSet[str]],
    *,
    static_string_bindings: Mapping[str, str] | None = None,
) -> frozenset[str]:
    """Return unresolved dynamic imports routed through wrapper-router registration args."""

    if not call.args:
        return frozenset()
    if isinstance(call.args[0], ast.Name) and _is_app_include_router_func(
        call.func,
        static_string_bindings=static_string_bindings,
    ):
        return frozenset()
    return _tainted_dynamic_router_modules_in_node(call.args[0], dynamic_import_target_modules)


def _is_app_include_router_func(
    func: ast.AST,
    *,
    static_string_bindings: Mapping[str, str] | None = None,
) -> bool:
    if (
        isinstance(func, ast.Attribute)
        and func.attr == "include_router"
        and isinstance(func.value, ast.Name)
        and func.value.id == "app"
    ):
        return True
    if (
        _getattr_method_name(
            func,
            frozenset({"include_router"}),
            static_string_bindings=static_string_bindings,
        )
        != "include_router"
    ):
        return False
    if not isinstance(func, ast.Call) or not func.args:
        return False
    target = func.args[0]
    return isinstance(target, ast.Name) and target.id == "app"


def _tainted_dynamic_router_modules_in_node(
    node: ast.AST,
    dynamic_import_target_modules: Mapping[str, AbstractSet[str]],
) -> frozenset[str]:
    """Return unresolved dynamic imports referenced by names or attributes in node."""

    modules: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            modules.update(dynamic_import_target_modules.get(child.id, ()))
        elif isinstance(child, ast.Attribute):
            root_name = _attribute_root_name(child)
            if root_name is not None:
                modules.update(dynamic_import_target_modules.get(root_name, ()))
    return frozenset(modules)


def _dynamic_app_router_import_modules(
    node: ast.AST,
    *,
    import_func_names: frozenset[str],
    static_string_bindings: Mapping[str, str],
    static_app_router_hint_bindings: frozenset[str],
    unresolved_router_registration: bool,
) -> frozenset[str]:
    """Return dynamic app.routers module imports embedded in an AST node."""

    modules: set[str] = set()
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        module_name = _dynamic_import_module_name(
            child,
            import_func_names=import_func_names,
            static_string_bindings=static_string_bindings,
            static_app_router_hint_bindings=static_app_router_hint_bindings,
            unresolved_router_registration=unresolved_router_registration,
        )
        if module_name is None:
            continue
        if (
            module_name == UNRESOLVED_APP_ROUTER_IMPORT
            or module_name == UNRESOLVED_DYNAMIC_ROUTER_IMPORT
            or module_name == "app.routers"
            or module_name.startswith("app.routers.")
        ):
            modules.add(module_name)
    return frozenset(modules)


def _attribute_root_name(node: ast.Attribute) -> str | None:
    value: ast.AST = node
    while isinstance(value, ast.Attribute):
        value = value.value
    if isinstance(value, ast.Name):
        return value.id
    return None


def _dynamic_import_module_name(
    call: ast.Call,
    *,
    import_func_names: frozenset[str],
    static_string_bindings: Mapping[str, str],
    static_app_router_hint_bindings: frozenset[str],
    unresolved_router_registration: bool,
) -> str | None:
    func = call.func
    if not (
        (isinstance(func, ast.Name) and func.id in import_func_names)
        or (isinstance(func, ast.Attribute) and func.attr == "import_module")
    ):
        return None

    module_arg = _dynamic_import_module_arg(call)
    if module_arg is None:
        return None

    resolved = _resolve_static_string(module_arg, static_string_bindings)
    if resolved is not None:
        return resolved
    if _static_app_router_hint(
        module_arg,
        static_string_bindings,
        static_app_router_hint_bindings,
    ):
        return UNRESOLVED_APP_ROUTER_IMPORT
    if unresolved_router_registration:
        return UNRESOLVED_DYNAMIC_ROUTER_IMPORT
    return None


def _dynamic_import_module_arg(call: ast.Call) -> ast.AST | None:
    if call.args:
        return call.args[0]
    for keyword in call.keywords:
        if keyword.arg == "name":
            return keyword.value
    return None


def _contains_unresolved_dynamic_import(
    node: ast.AST,
    *,
    import_func_names: frozenset[str],
    static_string_bindings: Mapping[str, str] | None = None,
) -> bool:
    static_string_bindings = static_string_bindings or {}
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        func = child.func
        if (isinstance(func, ast.Name) and func.id in import_func_names) or (
            isinstance(func, ast.Attribute) and func.attr == "import_module"
        ):
            module_arg = _dynamic_import_module_arg(child)
            if module_arg is None:
                continue
            resolved = _resolve_static_string(module_arg, static_string_bindings)
            if resolved is None:
                return True
    return False


def collect_sensitive_call_counts(
    source_text: str,
    *,
    filename: str = LEGACY_APP,
) -> Counter[str]:
    """Return counts for sensitive call families that must not grow in legacy_app.py."""

    counts: Counter[str] = Counter()
    tree, errors = _parse_source(source_text, filename=filename)
    if errors or tree is None:
        return counts

    sensitive_aliases = _collect_sensitive_aliases(tree)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func_name = _safe_unparse(node.func).casefold()
        call_keywords = {keyword for keyword in SENSITIVE_CALL_KEYWORDS if keyword in func_name}
        for alias_name in _function_alias_names(node.func):
            call_keywords.update(sensitive_aliases.get(alias_name, set()))
        for keyword in SENSITIVE_CALL_KEYWORDS:
            if keyword in call_keywords:
                counts[keyword] += 1
    return counts


def _collect_sensitive_import_aliases(tree: ast.Module) -> dict[str, set[str]]:
    sensitive_aliases: dict[str, set[str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            module_text = node.module.casefold()
            module_keywords = {
                keyword for keyword in SENSITIVE_CALL_KEYWORDS if keyword in module_text
            }
            for alias in node.names:
                alias_text = alias.name.casefold()
                alias_keywords = {
                    keyword for keyword in SENSITIVE_CALL_KEYWORDS if keyword in alias_text
                }
                keywords = module_keywords | alias_keywords
                if keywords:
                    sensitive_aliases.setdefault(alias.asname or alias.name, set()).update(keywords)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                import_text = alias.name.casefold()
                import_keywords = {
                    keyword for keyword in SENSITIVE_CALL_KEYWORDS if keyword in import_text
                }
                if not import_keywords:
                    continue
                sensitive_aliases.setdefault(
                    alias.asname or alias.name.split(".", maxsplit=1)[0],
                    set(),
                ).update(import_keywords)
    return sensitive_aliases


def _propagate_sensitive_aliases(
    tree: ast.Module,
    aliases: dict[str, set[str]],
) -> dict[str, set[str]]:
    sensitive_aliases = {name: set(keywords) for name, keywords in aliases.items()}
    changed = True
    while changed:
        changed = False
        for node in ast.walk(tree):
            value: ast.AST | None = None
            targets: list[ast.expr] = []
            if isinstance(node, ast.Assign):
                value = node.value
                targets = list(node.targets)
            elif isinstance(node, ast.AnnAssign) and node.value is not None:
                value = node.value
                targets = [node.target]
            if value is None:
                continue
            source_names = _function_alias_names(value)
            keywords: set[str] = set()
            for source_name in source_names:
                keywords.update(sensitive_aliases.get(source_name, set()))
            if not keywords:
                continue
            for target in targets:
                if not isinstance(target, ast.Name):
                    continue
                before = len(sensitive_aliases.get(target.id, set()))
                sensitive_aliases.setdefault(target.id, set()).update(keywords)
                if len(sensitive_aliases[target.id]) > before:
                    changed = True
    return sensitive_aliases


def _collect_sensitive_aliases(tree: ast.Module) -> dict[str, set[str]]:
    aliases = _collect_sensitive_import_aliases(tree)
    for name, keywords in _collect_sensitive_names(tree).items():
        aliases.setdefault(name, set()).update(keywords)
    return _propagate_sensitive_aliases(tree, aliases)


def _function_alias_names(func: ast.AST) -> set[str]:
    aliases: set[str] = set()
    current = func
    while isinstance(current, ast.Attribute):
        current = current.value
    if isinstance(current, ast.Name):
        aliases.add(current.id)
    if isinstance(func, ast.Name):
        aliases.add(func.id)
    return aliases


def _collect_sensitive_names(tree: ast.Module) -> dict[str, set[str]]:
    sensitive_names: dict[str, set[str]] = {}
    for node in ast.walk(tree):
        value: ast.AST | None = None
        targets: list[ast.expr] = []
        if isinstance(node, ast.Assign):
            value = node.value
            targets = list(node.targets)
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            value = node.value
            targets = [node.target]
        if value is None:
            continue

        value_text = _safe_unparse(value).casefold()
        keywords = {keyword for keyword in SENSITIVE_CALL_KEYWORDS if keyword in value_text}
        if not keywords:
            continue
        for target in targets:
            if isinstance(target, ast.Name):
                sensitive_names.setdefault(target.id, set()).update(keywords)
    return sensitive_names


def collect_sensitive_app_surface_counts(
    source_text: str,
    *,
    filename: str = LEGACY_APP,
) -> Counter[str]:
    """Return sensitive terms present on app route/router registration calls."""

    counts: Counter[str] = Counter()
    tree, errors = _parse_source(source_text, filename=filename)
    if errors or tree is None:
        return counts

    app_surface_methods = APP_ROUTE_METHODS | APP_REGISTRATION_METHODS
    sensitive_names = _collect_sensitive_names(tree)
    app_aliases, router_aliases = _collect_app_aliases(tree)
    static_string_bindings = _collect_static_string_bindings(tree)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if (
            _app_call_action(
                node.func,
                app_surface_methods,
                app_aliases=app_aliases,
                router_aliases=router_aliases,
                static_string_bindings=static_string_bindings,
            )
            is None
        ):
            continue
        call_text = _safe_unparse(node).casefold()
        call_keywords = {keyword for keyword in SENSITIVE_CALL_KEYWORDS if keyword in call_text}
        for child in ast.walk(node):
            if isinstance(child, ast.Name):
                call_keywords.update(sensitive_names.get(child.id, set()))
        for keyword in SENSITIVE_CALL_KEYWORDS:
            if keyword in call_keywords:
                counts[keyword] += 1
    return counts


def validate_legacy_growth(
    source_text: str,
    *,
    filename: str = LEGACY_APP,
    allowed_route_facts: set[LegacyFact] | frozenset[LegacyFact] = ALLOWED_LEGACY_ROUTE_FACTS,
    allowed_router_import_facts: set[LegacyFact] | frozenset[LegacyFact] = (
        ALLOWED_ROUTER_IMPORT_FACTS
    ),
    sensitive_call_limits: Mapping[str, int] = SENSITIVE_CALL_LIMITS,
    sensitive_app_surface_limits: Mapping[str, int] = SENSITIVE_APP_SURFACE_LIMITS,
) -> list[str]:
    """Return deterministic errors for legacy_app.py growth."""

    tree, parse_errors = _parse_source(source_text, filename=filename)
    if parse_errors or tree is None:
        return parse_errors

    errors: list[str] = []
    route_facts = collect_legacy_route_facts(source_text, filename=filename)
    runtime_registration_facts = collect_forbidden_runtime_registration_facts(
        source_text,
        filename=filename,
    )
    router_import_facts = collect_router_import_facts(source_text, filename=filename)
    sensitive_counts = collect_sensitive_call_counts(source_text, filename=filename)
    sensitive_app_surface_counts = collect_sensitive_app_surface_counts(
        source_text,
        filename=filename,
    )

    for fact in sorted(route_facts - set(allowed_route_facts)):
        errors.append(f"{filename}: unexpected legacy route growth: {fact.display()}")
    for fact in sorted(runtime_registration_facts):
        errors.append(f"{filename}: forbidden legacy runtime registration: {fact.display()}")
    for fact in sorted(router_import_facts - set(allowed_router_import_facts)):
        errors.append(f"{filename}: unexpected app.routers import growth: {fact.display()}")
    for keyword, limit in sorted(sensitive_call_limits.items()):
        actual = sensitive_counts[keyword]
        if actual > limit:
            errors.append(
                f"{filename}: sensitive call family grew for {keyword}: {actual} > {limit}"
            )
    for keyword, limit in sorted(sensitive_app_surface_limits.items()):
        actual = sensitive_app_surface_counts[keyword]
        if actual > limit:
            errors.append(
                f"{filename}: sensitive app surface grew for {keyword}: {actual} > {limit}"
            )
    return errors


def _markers(text: str) -> dict[str, str]:
    return {match.group(1): match.group(2).strip() for match in MARKER_RE.finditer(text)}


def validate_legacy_seam_doc(text: str, *, filename: str = LEGACY_SEAM_DOC) -> list[str]:
    """Return deterministic errors for the legacy seam architecture document."""

    errors: list[str] = []
    markers = _markers(text)
    for key, expected in REQUIRED_DOC_MARKERS.items():
        actual = markers.get(key)
        if actual is None:
            errors.append(f"{filename}: missing marker {key}")
        elif actual != expected:
            errors.append(f"{filename}: marker {key} must be {expected}, got {actual}")
    lowered = text.casefold()
    for token in REQUIRED_DOC_TOKENS:
        if token.casefold() not in lowered:
            errors.append(f"{filename}: missing required seam token: {token}")
    return errors


def _display(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return "<external-path>"


def _read(path: Path, repo_root: Path, errors: list[str]) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f"{_display(path, repo_root)}: unable to read: {type(exc).__name__}")
        return None


def validate_repo(repo_root: Path) -> list[str]:
    """Validate the repo's legacy compatibility seam."""

    errors: list[str] = []
    legacy_path = repo_root / LEGACY_APP
    doc_path = repo_root / LEGACY_SEAM_DOC
    legacy_source = _read(legacy_path, repo_root, errors)
    doc_text = _read(doc_path, repo_root, errors)
    if legacy_source is not None:
        errors.extend(
            validate_legacy_growth(legacy_source, filename=_display(legacy_path, repo_root))
        )
    if doc_text is not None:
        errors.extend(validate_legacy_seam_doc(doc_text, filename=_display(doc_path, repo_root)))
    return errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        default=str(REPO_ROOT),
        help="Repository root to validate. Defaults to this script's repo.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    errors = validate_repo(repo_root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("legacy compatibility seam guard passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
