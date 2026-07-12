#!/usr/bin/env python3
"""Fail-closed guard for legacy_app.py compatibility-seam growth."""

from __future__ import annotations

import argparse
import ast
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from importlib.util import resolve_name
from pathlib import Path
import re
import sys
from typing import AbstractSet

REPO_ROOT = Path(__file__).resolve().parents[2]
LEGACY_APP = "legacy_app.py"
LEGACY_SEAM_DOC = "docs/architecture/LEGACY_COMPATIBILITY_SEAM.md"
FOOD_SEARCH_BOOTSTRAP = "app/bootstrap/food_search.py"
CANONICAL_LIFESPAN = "app/bootstrap/lifespan.py"
CANONICAL_API_KEY = "app/routers/api_key.py"  # pragma: allowlist secret
CANONICAL_API_KEY_SYMBOLS = frozenset(
    {
        "api_key_header",
        "get_api_key",
        "_get_api_key_dynamic",
        "validate_app_api_key",
        "require_app_api_key",
    }
)
LEGACY_API_KEY_REEXPORT_SYMBOLS = frozenset({"get_api_key", "_get_api_key_dynamic"})
ALLOWED_CANONICAL_LIFESPAN_APP_IMPORTS = frozenset(
    {
        "app.bootstrap.food_search",
        "app.bootstrap.startup_guards",
        "app.dependencies",
    }
)


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
    "api_key": 0,
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
        LegacyFact(
            "router_import",
            "app.routers.api_key",
            "_get_api_key_dynamic",
            "_get_api_key_dynamic",
        ),
        LegacyFact("router_import", "app.routers.api_key", "get_api_key", "get_api_key"),
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
    static_string_bindings: Mapping[str, str],
) -> str | None:
    if isinstance(node, ast.Name):
        return module_aliases.get(node.id)
    if isinstance(node, ast.Attribute):
        parent = _static_module_reference(
            node.value,
            module_aliases=module_aliases,
            import_module_aliases=import_module_aliases,
            static_string_bindings=static_string_bindings,
        )
        if parent is not None:
            return f"{parent}.{node.attr}"
        return None
    if isinstance(node, ast.Subscript):
        container = _static_module_reference(
            node.value,
            module_aliases=module_aliases,
            import_module_aliases=import_module_aliases,
            static_string_bindings=static_string_bindings,
        )
        if container == "sys.modules":
            return _resolve_static_string(node.slice, static_string_bindings)
        return None
    if not isinstance(node, ast.Call):
        return None

    function_reference = _static_module_reference(
        node.func,
        module_aliases=module_aliases,
        import_module_aliases=import_module_aliases,
        static_string_bindings=static_string_bindings,
    )
    if (
        function_reference == "sys.modules.get"
        and node.args
        and not any(keyword.arg == "name" for keyword in node.keywords)
    ):
        return _resolve_static_string(node.args[0], static_string_bindings)
    is_module_loader = (
        function_reference in {"builtins.__import__", "importlib.import_module"}
        or isinstance(node.func, ast.Name)
        and node.func.id in import_module_aliases
    )
    if not is_module_loader:
        return None
    module_node = node.args[0] if node.args else None
    supports_relative_package = function_reference != "builtins.__import__"
    package_node = node.args[1] if supports_relative_package and len(node.args) >= 2 else None
    for keyword in node.keywords:
        if keyword.arg == "name":
            module_node = keyword.value
        elif keyword.arg == "package" and supports_relative_package:
            package_node = keyword.value
    if module_node is None:
        return None

    module_name = _resolve_static_string(module_node, static_string_bindings)
    if module_name is None or not module_name.startswith("."):
        return module_name
    if package_node is None:
        return None
    package_name = _resolve_static_string(package_node, static_string_bindings)
    if not package_name:
        return None
    try:
        return resolve_name(module_name, package_name)
    except ImportError:
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
            static_string_bindings=static_string_bindings,
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
            static_string_bindings=static_string_bindings,
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
                static_string_bindings=static_string_bindings,
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
    binding_counts = _collect_binding_counts(tree)
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
                    if binding_counts[target_name] == 1 and target_name not in bindings:
                        bindings[target_name] = resolved
                        changed = True
    return bindings


def _collect_binding_counts(tree: ast.Module) -> Counter[str]:
    """Count bindings so static security facts never survive reassignment."""

    counts: Counter[str] = Counter()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(
            node.ctx,
            (ast.Store, ast.Del),
        ):
            counts[node.id] += 1
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            counts[node.name] += 1
        elif isinstance(node, ast.arg):
            counts[node.arg] += 1
        elif isinstance(node, ast.Import):
            for alias in node.names:
                counts[alias.asname or alias.name.split(".", maxsplit=1)[0]] += 1
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                counts[alias.asname or alias.name] += 1
        elif isinstance(node, ast.ExceptHandler) and node.name is not None:
            counts[node.name] += 1
    return counts


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


class _ModuleScopeBindingCollector(ast.NodeVisitor):
    """Collect module-scope bindings without entering nested Python scopes."""

    def __init__(
        self,
        ignored_import_names: Mapping[int, frozenset[str]] | None = None,
    ) -> None:
        self.bindings: set[str] = set()
        self.function_definitions: set[str] = set()
        self.global_declarations: set[str] = set()
        self.nonlocal_declarations: set[str] = set()
        self._ignored_import_names = ignored_import_names or {}

    def _add_target(self, target: ast.AST) -> None:
        self.bindings.update(_assignment_target_names(target))

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.bindings.add(node.name)
        self.function_definitions.add(node.name)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.bindings.add(node.name)
        self.function_definitions.add(node.name)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.bindings.add(node.name)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        return

    def visit_comprehension(self, node: ast.comprehension) -> None:
        return

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.bindings.add(alias.asname or alias.name.split(".", maxsplit=1)[0])

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            local_name = alias.asname or alias.name
            if local_name in self._ignored_import_names.get(id(node), frozenset()):
                continue
            self.bindings.add(local_name)

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            self._add_target(target)
        self.visit(node.value)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self._add_target(node.target)
        if node.value is not None:
            self.visit(node.value)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        self._add_target(node.target)
        self.visit(node.value)

    def visit_NamedExpr(self, node: ast.NamedExpr) -> None:
        self._add_target(node.target)
        self.visit(node.value)

    def visit_Delete(self, node: ast.Delete) -> None:
        for target in node.targets:
            self._add_target(target)

    def visit_For(self, node: ast.For) -> None:
        self._add_target(node.target)
        self.generic_visit(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self._add_target(node.target)
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        for item in node.items:
            if item.optional_vars is not None:
                self._add_target(item.optional_vars)
        self.generic_visit(node)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        for item in node.items:
            if item.optional_vars is not None:
                self._add_target(item.optional_vars)
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.name is not None:
            self.bindings.add(node.name)
        self.generic_visit(node)

    def visit_Global(self, node: ast.Global) -> None:
        self.global_declarations.update(node.names)

    def visit_Nonlocal(self, node: ast.Nonlocal) -> None:
        self.nonlocal_declarations.update(node.names)


def _canonical_api_key_source_errors(app_sources: Mapping[str, str]) -> list[str]:
    source_text = app_sources.get(CANONICAL_API_KEY)
    if source_text is None:
        return [f"{CANONICAL_API_KEY}: canonical API-key owner source is missing"]
    tree, errors = _parse_source(source_text, filename=CANONICAL_API_KEY)
    if tree is None:
        return errors
    collector = _ModuleScopeBindingCollector()
    collector.visit(tree)
    for name in sorted(CANONICAL_API_KEY_SYMBOLS - collector.bindings):
        errors.append(f"{CANONICAL_API_KEY}: canonical API-key symbol is missing: {name}")
    return errors


def _legacy_api_key_export_errors(legacy_tree: ast.Module) -> list[str]:
    errors: list[str] = []
    exact_reexports: set[str] = set()
    exact_import_names: dict[int, set[str]] = {}
    for statement in legacy_tree.body:
        if not isinstance(statement, ast.ImportFrom) or statement.module != "app.routers.api_key":
            continue
        for alias in statement.names:
            local_name = alias.asname or alias.name
            if alias.name in LEGACY_API_KEY_REEXPORT_SYMBOLS and local_name == alias.name:
                exact_reexports.add(alias.name)
                exact_import_names.setdefault(id(statement), set()).add(alias.name)

    for name in sorted(LEGACY_API_KEY_REEXPORT_SYMBOLS - exact_reexports):
        errors.append(
            f"{LEGACY_APP}: canonical API-key compatibility re-export must preserve "
            f"identity: {name}"
        )

    collector = _ModuleScopeBindingCollector(
        {node_id: frozenset(names) for node_id, names in exact_import_names.items()}
    )
    collector.visit(legacy_tree)
    local_definitions = collector.function_definitions & CANONICAL_API_KEY_SYMBOLS
    for name in sorted(local_definitions):
        errors.append(f"{LEGACY_APP}: API-key dependency must not be defined locally: {name}")
    rebound_names = (collector.bindings & CANONICAL_API_KEY_SYMBOLS) - local_definitions
    for name in sorted(rebound_names):
        errors.append(
            f"{LEGACY_APP}: canonical API-key compatibility re-export must not be rebound: {name}"
        )
    return errors


class _LexicalScopeNodeCollector(ast.NodeVisitor):
    """Collect nodes for one lexical scope and retain nested scopes separately."""

    def __init__(self) -> None:
        self.nodes: list[ast.AST] = []
        self.nested_scopes: list[
            ast.FunctionDef
            | ast.AsyncFunctionDef
            | ast.ClassDef
            | ast.Lambda
            | ast.ListComp
            | ast.SetComp
            | ast.DictComp
            | ast.GeneratorExp
        ] = []

    def generic_visit(self, node: ast.AST) -> None:
        self.nodes.append(node)
        super().generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.nodes.append(node)
        self.nested_scopes.append(node)
        self._visit_function_signature(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.nodes.append(node)
        self.nested_scopes.append(node)
        self._visit_function_signature(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.nodes.append(node)
        self.nested_scopes.append(node)
        for decorator in node.decorator_list:
            self.visit(decorator)
        for base in node.bases:
            self.visit(base)
        for keyword in node.keywords:
            self.visit(keyword.value)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        self.nodes.append(node)
        self.nested_scopes.append(node)
        for positional_default in node.args.defaults:
            self.visit(positional_default)
        for keyword_default in node.args.kw_defaults:
            if keyword_default is not None:
                self.visit(keyword_default)

    def visit_ListComp(self, node: ast.ListComp) -> None:
        self._visit_comprehension(node)

    def visit_SetComp(self, node: ast.SetComp) -> None:
        self._visit_comprehension(node)

    def visit_DictComp(self, node: ast.DictComp) -> None:
        self._visit_comprehension(node)

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> None:
        self._visit_comprehension(node)

    def _visit_comprehension(
        self,
        node: ast.ListComp | ast.SetComp | ast.DictComp | ast.GeneratorExp,
    ) -> None:
        self.nodes.append(node)
        self.nested_scopes.append(node)
        if node.generators:
            self.visit(node.generators[0].iter)

    def _visit_function_signature(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> None:
        for decorator in node.decorator_list:
            self.visit(decorator)
        for argument in (
            *node.args.posonlyargs,
            *node.args.args,
            *node.args.kwonlyargs,
        ):
            if argument.annotation is not None:
                self.visit(argument.annotation)
        if node.args.vararg is not None and node.args.vararg.annotation is not None:
            self.visit(node.args.vararg.annotation)
        if node.args.kwarg is not None and node.args.kwarg.annotation is not None:
            self.visit(node.args.kwarg.annotation)
        for positional_default in node.args.defaults:
            self.visit(positional_default)
        for keyword_default in node.args.kw_defaults:
            if keyword_default is not None:
                self.visit(keyword_default)
        if node.returns is not None:
            self.visit(node.returns)


def _ordered_lexical_scope_nodes(
    statements: Sequence[ast.stmt],
) -> tuple[
    list[ast.AST],
    list[
        ast.FunctionDef
        | ast.AsyncFunctionDef
        | ast.ClassDef
        | ast.Lambda
        | ast.ListComp
        | ast.SetComp
        | ast.DictComp
        | ast.GeneratorExp
    ],
]:
    collector = _LexicalScopeNodeCollector()
    for statement in statements:
        collector.visit(statement)
    return (
        sorted(
            collector.nodes,
            key=lambda node: (
                getattr(node, "lineno", -1),
                getattr(node, "col_offset", -1),
                type(node).__name__,
            ),
        ),
        collector.nested_scopes,
    )


def _function_local_bindings(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> set[str]:
    collector = _ModuleScopeBindingCollector()
    for statement in node.body:
        collector.visit(statement)
    bindings = set(collector.bindings) - (
        collector.global_declarations | collector.nonlocal_declarations
    )
    arguments = [
        *node.args.posonlyargs,
        *node.args.args,
        *node.args.kwonlyargs,
    ]
    if node.args.vararg is not None:
        arguments.append(node.args.vararg)
    if node.args.kwarg is not None:
        arguments.append(node.args.kwarg)
    bindings.update(argument.arg for argument in arguments)
    return bindings


def _lambda_local_bindings(node: ast.Lambda) -> set[str]:
    arguments = [
        *node.args.posonlyargs,
        *node.args.args,
        *node.args.kwonlyargs,
    ]
    if node.args.vararg is not None:
        arguments.append(node.args.vararg)
    if node.args.kwarg is not None:
        arguments.append(node.args.kwarg)
    return {argument.arg for argument in arguments}


def _match_pattern_bindings(pattern: ast.pattern) -> set[str]:
    """Return names captured by one structural pattern."""

    bindings: set[str] = set()
    for node in ast.walk(pattern):
        if isinstance(node, (ast.MatchAs, ast.MatchStar)) and node.name is not None:
            bindings.add(node.name)
        elif isinstance(node, ast.MatchMapping) and node.rest is not None:
            bindings.add(node.rest)
    return bindings


def _is_unguarded_irrefutable_case(case: ast.match_case) -> bool:
    """Return whether a match case guarantees that some case body executes."""

    return (
        case.guard is None
        and isinstance(case.pattern, ast.MatchAs)
        and (case.pattern.pattern is None)
    )


def _scan_api_key_alias_expressions(
    expressions: Sequence[ast.expr],
    *,
    filename: str,
    inherited_module_aliases: Mapping[str, str],
    inherited_import_module_aliases: AbstractSet[str],
    inherited_static_string_bindings: Mapping[str, str] | None = None,
    local_bindings: AbstractSet[str],
) -> list[str]:
    return _scan_api_key_alias_scope(
        [ast.Expr(value=expression) for expression in expressions],
        filename=filename,
        inherited_module_aliases=inherited_module_aliases,
        inherited_import_module_aliases=inherited_import_module_aliases,
        inherited_static_string_bindings=inherited_static_string_bindings,
        local_bindings=local_bindings,
    )


def _join_api_key_alias_states(
    *states: tuple[Mapping[str, str], AbstractSet[str]],
) -> tuple[dict[str, str], set[str]]:
    joined_modules: dict[str, str] = {}
    all_names = {name for modules, _imports in states for name in modules}
    for name in all_names:
        possible = {modules.get(name) for modules, _imports in states}
        resolved = _preferred_api_key_module_reference(possible)
        if resolved is not None:
            joined_modules[name] = resolved
    joined_imports = set().union(*(imports for _modules, imports in states))
    return joined_modules, joined_imports


def _preferred_api_key_module_reference(references: AbstractSet[str | None]) -> str | None:
    for reference in (
        "legacy_app",
        "sys.modules",
        "builtins.__import__",
        "importlib.import_module",
        "sys",
        "builtins",
        "importlib",
    ):
        if reference in references:
            return reference
    return None


ApiKeyAliasState = tuple[dict[str, str], set[str]]


@dataclass(frozen=True)
class _ApiKeyLoopFlow:
    normal: ApiKeyAliasState | None
    breaks: ApiKeyAliasState | None = None
    continues: ApiKeyAliasState | None = None


def _join_optional_api_key_alias_states(
    *states: ApiKeyAliasState | None,
) -> ApiKeyAliasState | None:
    present = tuple(state for state in states if state is not None)
    return _join_api_key_alias_states(*present) if present else None


def _apply_api_key_loop_statement_flow(
    statement: ast.stmt,
    *,
    entry_state: ApiKeyAliasState,
    static_string_bindings: Mapping[str, str],
) -> _ApiKeyLoopFlow:
    """Apply one outer-loop statement without flattening abrupt transfers."""

    if isinstance(statement, ast.Break):
        return _ApiKeyLoopFlow(normal=None, breaks=entry_state)
    if isinstance(statement, ast.Continue):
        return _ApiKeyLoopFlow(normal=None, continues=entry_state)
    if isinstance(statement, (ast.Return, ast.Raise)):
        return _ApiKeyLoopFlow(normal=None)

    if isinstance(statement, ast.If):
        condition_state = _apply_api_key_alias_expression(
            statement.test,
            module_aliases=entry_state[0],
            import_module_aliases=entry_state[1],
            static_string_bindings=static_string_bindings,
        )
        body_flow = _apply_api_key_loop_block_flow(
            statement.body,
            entry_state=condition_state,
            static_string_bindings=static_string_bindings,
        )
        else_flow = _apply_api_key_loop_block_flow(
            statement.orelse,
            entry_state=condition_state,
            static_string_bindings=static_string_bindings,
        )
        return _ApiKeyLoopFlow(
            normal=_join_optional_api_key_alias_states(body_flow.normal, else_flow.normal),
            breaks=_join_optional_api_key_alias_states(body_flow.breaks, else_flow.breaks),
            continues=_join_optional_api_key_alias_states(
                body_flow.continues,
                else_flow.continues,
            ),
        )

    if isinstance(statement, (ast.With, ast.AsyncWith)):
        body_modules = dict(entry_state[0])
        body_imports = set(entry_state[1])
        for item in statement.items:
            body_modules, body_imports = _apply_api_key_alias_expression(
                item.context_expr,
                module_aliases=body_modules,
                import_module_aliases=body_imports,
                static_string_bindings=static_string_bindings,
            )
            if item.optional_vars is not None:
                for target_name in _assignment_target_names(item.optional_vars):
                    body_modules.pop(target_name, None)
                    body_imports.discard(target_name)
        body_entry = (body_modules, body_imports)
        body_flow = _apply_api_key_loop_block_flow(
            statement.body,
            entry_state=body_entry,
            static_string_bindings=static_string_bindings,
        )
        return _ApiKeyLoopFlow(
            # A context manager may suppress an exception before the next body statement.
            normal=_join_optional_api_key_alias_states(body_entry, body_flow.normal),
            breaks=body_flow.breaks,
            continues=body_flow.continues,
        )

    if isinstance(statement, ast.Match):
        subject_state = _apply_api_key_alias_expression(
            statement.subject,
            module_aliases=entry_state[0],
            import_module_aliases=entry_state[1],
            static_string_bindings=static_string_bindings,
        )
        case_flows: list[_ApiKeyLoopFlow] = []
        has_irrefutable_case = False
        for case in statement.cases:
            bindings = _match_pattern_bindings(case.pattern)
            case_modules = {
                name: module for name, module in subject_state[0].items() if name not in bindings
            }
            case_imports = set(subject_state[1]) - bindings
            if case.guard is not None:
                case_modules, case_imports = _apply_api_key_alias_expression(
                    case.guard,
                    module_aliases=case_modules,
                    import_module_aliases=case_imports,
                    static_string_bindings=static_string_bindings,
                )
            case_flows.append(
                _apply_api_key_loop_block_flow(
                    case.body,
                    entry_state=(case_modules, case_imports),
                    static_string_bindings=static_string_bindings,
                )
            )
            has_irrefutable_case = has_irrefutable_case or _is_unguarded_irrefutable_case(case)
        unmatched_state = None if has_irrefutable_case else subject_state
        return _ApiKeyLoopFlow(
            normal=_join_optional_api_key_alias_states(
                unmatched_state,
                *(flow.normal for flow in case_flows),
            ),
            breaks=_join_optional_api_key_alias_states(*(flow.breaks for flow in case_flows)),
            continues=_join_optional_api_key_alias_states(*(flow.continues for flow in case_flows)),
        )

    if isinstance(statement, (ast.Try, ast.TryStar)):
        body_flow = _apply_api_key_loop_block_flow(
            statement.body,
            entry_state=entry_state,
            static_string_bindings=static_string_bindings,
        )
        else_flow = (
            _apply_api_key_loop_block_flow(
                statement.orelse,
                entry_state=body_flow.normal,
                static_string_bindings=static_string_bindings,
            )
            if body_flow.normal is not None
            else _ApiKeyLoopFlow(normal=None)
        )

        handler_entry = _api_key_exception_prefix_state(
            statement.body,
            entry_state=entry_state,
            static_string_bindings=static_string_bindings,
        )
        handler_flows: list[_ApiKeyLoopFlow] = []
        for handler in statement.handlers:
            handler_modules = dict(handler_entry[0])
            handler_imports = set(handler_entry[1])
            if handler.name is not None:
                handler_modules.pop(handler.name, None)
                handler_imports.discard(handler.name)
            handler_flows.append(
                _apply_api_key_loop_block_flow(
                    handler.body,
                    entry_state=(handler_modules, handler_imports),
                    static_string_bindings=static_string_bindings,
                )
            )

        combined = _ApiKeyLoopFlow(
            normal=_join_optional_api_key_alias_states(
                else_flow.normal,
                *(flow.normal for flow in handler_flows),
            ),
            breaks=_join_optional_api_key_alias_states(
                body_flow.breaks,
                else_flow.breaks,
                *(flow.breaks for flow in handler_flows),
            ),
            continues=_join_optional_api_key_alias_states(
                body_flow.continues,
                else_flow.continues,
                *(flow.continues for flow in handler_flows),
            ),
        )
        if not statement.finalbody:
            return combined

        final_normal: ApiKeyAliasState | None = None
        final_breaks: ApiKeyAliasState | None = None
        final_continues: ApiKeyAliasState | None = None
        for exit_kind, exit_state in (
            ("normal", combined.normal),
            ("break", combined.breaks),
            ("continue", combined.continues),
            ("exception", handler_entry),
        ):
            if exit_state is None:
                continue
            final_flow = _apply_api_key_loop_block_flow(
                statement.finalbody,
                entry_state=exit_state,
                static_string_bindings=static_string_bindings,
            )
            if final_flow.normal is not None:
                if exit_kind == "normal":
                    final_normal = _join_optional_api_key_alias_states(
                        final_normal,
                        final_flow.normal,
                    )
                elif exit_kind == "break":
                    final_breaks = _join_optional_api_key_alias_states(
                        final_breaks,
                        final_flow.normal,
                    )
                elif exit_kind == "continue":
                    final_continues = _join_optional_api_key_alias_states(
                        final_continues,
                        final_flow.normal,
                    )
            final_breaks = _join_optional_api_key_alias_states(
                final_breaks,
                final_flow.breaks,
            )
            final_continues = _join_optional_api_key_alias_states(
                final_continues,
                final_flow.continues,
            )
        return _ApiKeyLoopFlow(
            normal=final_normal,
            breaks=final_breaks,
            continues=final_continues,
        )

    # A nested loop owns its own break/continue statements and is one normal outer statement.
    normal_state = _apply_api_key_alias_statements(
        [statement],
        module_aliases=entry_state[0],
        import_module_aliases=entry_state[1],
        static_string_bindings=static_string_bindings,
    )
    return _ApiKeyLoopFlow(normal=normal_state)


def _apply_api_key_loop_block_flow(
    statements: Sequence[ast.stmt],
    *,
    entry_state: ApiKeyAliasState,
    static_string_bindings: Mapping[str, str],
) -> _ApiKeyLoopFlow:
    """Apply one loop block and keep normal, break, and continue exits separate."""

    normal: ApiKeyAliasState | None = entry_state
    breaks: ApiKeyAliasState | None = None
    continues: ApiKeyAliasState | None = None
    for statement in statements:
        if normal is None:
            break
        statement_flow = _apply_api_key_loop_statement_flow(
            statement,
            entry_state=normal,
            static_string_bindings=static_string_bindings,
        )
        normal = statement_flow.normal
        breaks = _join_optional_api_key_alias_states(breaks, statement_flow.breaks)
        continues = _join_optional_api_key_alias_states(continues, statement_flow.continues)
    return _ApiKeyLoopFlow(normal=normal, breaks=breaks, continues=continues)


def _loop_api_key_alias_fixed_point(
    statement: ast.For | ast.AsyncFor | ast.While,
    *,
    initial_modules: Mapping[str, str],
    initial_imports: AbstractSet[str],
    static_string_bindings: Mapping[str, str],
) -> tuple[
    tuple[dict[str, str], set[str]],
    tuple[dict[str, str], set[str]],
    tuple[dict[str, str], set[str]],
    tuple[dict[str, str], set[str]] | None,
]:
    """Return iteration, body, no-break, and break states for repeated iterations."""

    initial_state = (dict(initial_modules), set(initial_imports))
    iteration_entry = initial_state
    while True:
        tested_state = (
            _apply_api_key_alias_expression(
                statement.test,
                module_aliases=iteration_entry[0],
                import_module_aliases=iteration_entry[1],
                static_string_bindings=static_string_bindings,
            )
            if isinstance(statement, ast.While)
            else iteration_entry
        )
        body_modules = dict(tested_state[0])
        body_imports = set(tested_state[1])
        if isinstance(statement, (ast.For, ast.AsyncFor)):
            for target_name in _assignment_target_names(statement.target):
                body_modules.pop(target_name, None)
                body_imports.discard(target_name)
        body_flow = _apply_api_key_loop_block_flow(
            statement.body,
            entry_state=(body_modules, body_imports),
            static_string_bindings=static_string_bindings,
        )
        backedge_state = _join_optional_api_key_alias_states(
            body_flow.normal,
            body_flow.continues,
        )
        next_iteration_entry = _join_optional_api_key_alias_states(
            initial_state,
            backedge_state,
        )
        if next_iteration_entry is None:
            raise RuntimeError("API-key alias loop analysis lost its initial state")
        if next_iteration_entry == iteration_entry:
            return (
                iteration_entry,
                (body_modules, body_imports),
                tested_state,
                body_flow.breaks,
            )
        iteration_entry = next_iteration_entry


def _api_key_exception_prefix_state(
    statements: Sequence[ast.stmt],
    *,
    entry_state: ApiKeyAliasState,
    static_string_bindings: Mapping[str, str],
) -> ApiKeyAliasState:
    """Join every state from which a nested statement may raise."""

    possible_states: list[ApiKeyAliasState] = [entry_state]
    current_state = entry_state
    for statement in statements:
        if isinstance(statement, ast.If):
            condition_state = _apply_api_key_alias_expression(
                statement.test,
                module_aliases=current_state[0],
                import_module_aliases=current_state[1],
                static_string_bindings=static_string_bindings,
            )
            possible_states.extend(
                [
                    _api_key_exception_prefix_state(
                        branch,
                        entry_state=condition_state,
                        static_string_bindings=static_string_bindings,
                    )
                    for branch in (statement.body, statement.orelse)
                ]
            )
        elif isinstance(statement, (ast.For, ast.AsyncFor, ast.While)):
            if isinstance(statement, ast.While):
                loop_modules, loop_imports = current_state
            else:
                loop_modules, loop_imports = _apply_api_key_alias_expression(
                    statement.iter,
                    module_aliases=current_state[0],
                    import_module_aliases=current_state[1],
                    static_string_bindings=static_string_bindings,
                )
            _iteration_entry, body_entry, normal_exit, _break_exit = (
                _loop_api_key_alias_fixed_point(
                    statement,
                    initial_modules=loop_modules,
                    initial_imports=loop_imports,
                    static_string_bindings=static_string_bindings,
                )
            )
            possible_states.append(
                _api_key_exception_prefix_state(
                    statement.body,
                    entry_state=body_entry,
                    static_string_bindings=static_string_bindings,
                )
            )
            possible_states.append(
                _api_key_exception_prefix_state(
                    statement.orelse,
                    entry_state=normal_exit,
                    static_string_bindings=static_string_bindings,
                )
            )
        elif isinstance(statement, (ast.With, ast.AsyncWith)):
            body_modules = dict(current_state[0])
            body_imports = set(current_state[1])
            for item in statement.items:
                body_modules, body_imports = _apply_api_key_alias_expression(
                    item.context_expr,
                    module_aliases=body_modules,
                    import_module_aliases=body_imports,
                    static_string_bindings=static_string_bindings,
                )
                if item.optional_vars is not None:
                    for target_name in _assignment_target_names(item.optional_vars):
                        body_modules.pop(target_name, None)
                        body_imports.discard(target_name)
            possible_states.append(
                _api_key_exception_prefix_state(
                    statement.body,
                    entry_state=(body_modules, body_imports),
                    static_string_bindings=static_string_bindings,
                )
            )
        elif isinstance(statement, ast.Match):
            subject_state = _apply_api_key_alias_expression(
                statement.subject,
                module_aliases=current_state[0],
                import_module_aliases=current_state[1],
                static_string_bindings=static_string_bindings,
            )
            for case in statement.cases:
                bindings = _match_pattern_bindings(case.pattern)
                case_modules = {
                    name: module
                    for name, module in subject_state[0].items()
                    if name not in bindings
                }
                case_imports = set(subject_state[1]) - bindings
                if case.guard is not None:
                    case_modules, case_imports = _apply_api_key_alias_expression(
                        case.guard,
                        module_aliases=case_modules,
                        import_module_aliases=case_imports,
                        static_string_bindings=static_string_bindings,
                    )
                possible_states.append(
                    _api_key_exception_prefix_state(
                        case.body,
                        entry_state=(case_modules, case_imports),
                        static_string_bindings=static_string_bindings,
                    )
                )
        elif isinstance(statement, (ast.Try, ast.TryStar)):
            nested_handler_entry = _api_key_exception_prefix_state(
                statement.body,
                entry_state=current_state,
                static_string_bindings=static_string_bindings,
            )
            escaping_exception_states = [nested_handler_entry]
            for handler in statement.handlers:
                escaping_exception_states.append(
                    _api_key_exception_prefix_state(
                        handler.body,
                        entry_state=nested_handler_entry,
                        static_string_bindings=static_string_bindings,
                    )
                )
            escaping_exception_states.append(
                _api_key_exception_prefix_state(
                    statement.orelse,
                    entry_state=current_state,
                    static_string_bindings=static_string_bindings,
                )
            )
            escaping_exception_state = _join_api_key_alias_states(*escaping_exception_states)
            if statement.finalbody:
                escaping_exception_state = _apply_api_key_alias_statements(
                    statement.finalbody,
                    module_aliases=escaping_exception_state[0],
                    import_module_aliases=escaping_exception_state[1],
                    static_string_bindings=static_string_bindings,
                )
            possible_states.append(escaping_exception_state)

        current_state = _apply_api_key_alias_statements(
            [statement],
            module_aliases=current_state[0],
            import_module_aliases=current_state[1],
            static_string_bindings=static_string_bindings,
        )
        possible_states.append(current_state)
    return _join_api_key_alias_states(*possible_states)


def _evaluate_api_key_alias_expression(
    expression: ast.expr,
    *,
    module_aliases: Mapping[str, str],
    import_module_aliases: AbstractSet[str],
    static_string_bindings: Mapping[str, str],
) -> tuple[dict[str, str], set[str], set[str | None]]:
    """Evaluate alias side effects and possible module references conservatively."""

    if isinstance(expression, ast.IfExp):
        test_modules, test_imports, _test_refs = _evaluate_api_key_alias_expression(
            expression.test,
            module_aliases=module_aliases,
            import_module_aliases=import_module_aliases,
            static_string_bindings=static_string_bindings,
        )
        body_modules, body_imports, body_refs = _evaluate_api_key_alias_expression(
            expression.body,
            module_aliases=test_modules,
            import_module_aliases=test_imports,
            static_string_bindings=static_string_bindings,
        )
        else_modules, else_imports, else_refs = _evaluate_api_key_alias_expression(
            expression.orelse,
            module_aliases=test_modules,
            import_module_aliases=test_imports,
            static_string_bindings=static_string_bindings,
        )
        joined_modules, joined_imports = _join_api_key_alias_states(
            (body_modules, body_imports),
            (else_modules, else_imports),
        )
        return joined_modules, joined_imports, body_refs | else_refs

    if isinstance(expression, ast.BoolOp):
        current_modules = dict(module_aliases)
        current_imports = set(import_module_aliases)
        exit_states: list[tuple[dict[str, str], set[str]]] = []
        possible_refs: set[str | None] = set()
        for operand in expression.values:
            (
                current_modules,
                current_imports,
                operand_refs,
            ) = _evaluate_api_key_alias_expression(
                operand,
                module_aliases=current_modules,
                import_module_aliases=current_imports,
                static_string_bindings=static_string_bindings,
            )
            exit_states.append((dict(current_modules), set(current_imports)))
            possible_refs.update(operand_refs)
        joined_modules, joined_imports = _join_api_key_alias_states(*exit_states)
        return joined_modules, joined_imports, possible_refs

    if isinstance(expression, ast.NamedExpr):
        next_modules, next_imports, value_refs = _evaluate_api_key_alias_expression(
            expression.value,
            module_aliases=module_aliases,
            import_module_aliases=import_module_aliases,
            static_string_bindings=static_string_bindings,
        )
        resolved_module = _preferred_api_key_module_reference(value_refs)
        for target_name in _assignment_target_names(expression.target):
            if value_refs & {"builtins.__import__", "importlib.import_module"}:
                next_imports.add(target_name)
            else:
                next_imports.discard(target_name)
            if resolved_module is not None:
                next_modules[target_name] = resolved_module
            else:
                next_modules.pop(target_name, None)
        return next_modules, next_imports, value_refs

    if isinstance(expression, ast.Lambda):
        next_modules = dict(module_aliases)
        next_imports = set(import_module_aliases)
        for default in [*expression.args.defaults, *expression.args.kw_defaults]:
            if default is not None:
                next_modules, next_imports, _refs = _evaluate_api_key_alias_expression(
                    default,
                    module_aliases=next_modules,
                    import_module_aliases=next_imports,
                    static_string_bindings=static_string_bindings,
                )
        return next_modules, next_imports, {None}

    if isinstance(expression, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
        base_modules = dict(module_aliases)
        base_imports = set(import_module_aliases)
        if expression.generators:
            base_modules, base_imports, _refs = _evaluate_api_key_alias_expression(
                expression.generators[0].iter,
                module_aliases=base_modules,
                import_module_aliases=base_imports,
                static_string_bindings=static_string_bindings,
            )
        iter_modules = dict(base_modules)
        iter_imports = set(base_imports)
        for index, generator in enumerate(expression.generators):
            if index > 0:
                iter_modules, iter_imports, _refs = _evaluate_api_key_alias_expression(
                    generator.iter,
                    module_aliases=iter_modules,
                    import_module_aliases=iter_imports,
                    static_string_bindings=static_string_bindings,
                )
            for target_name in _assignment_target_names(generator.target):
                iter_modules.pop(target_name, None)
                iter_imports.discard(target_name)
            for condition in generator.ifs:
                iter_modules, iter_imports, _refs = _evaluate_api_key_alias_expression(
                    condition,
                    module_aliases=iter_modules,
                    import_module_aliases=iter_imports,
                    static_string_bindings=static_string_bindings,
                )
        result_expressions = (
            [expression.key, expression.value]
            if isinstance(expression, ast.DictComp)
            else [expression.elt]
        )
        for result_expression in result_expressions:
            iter_modules, iter_imports, _refs = _evaluate_api_key_alias_expression(
                result_expression,
                module_aliases=iter_modules,
                import_module_aliases=iter_imports,
                static_string_bindings=static_string_bindings,
            )
        joined_modules, joined_imports = _join_api_key_alias_states(
            (base_modules, base_imports),
            (iter_modules, iter_imports),
        )
        return joined_modules, joined_imports, {None}

    next_modules = dict(module_aliases)
    next_imports = set(import_module_aliases)
    for child in ast.iter_child_nodes(expression):
        if not isinstance(child, ast.expr):
            continue
        next_modules, next_imports, _child_refs = _evaluate_api_key_alias_expression(
            child,
            module_aliases=next_modules,
            import_module_aliases=next_imports,
            static_string_bindings=static_string_bindings,
        )
    resolved = _static_module_reference(
        expression,
        module_aliases=next_modules,
        import_module_aliases=next_imports,
        static_string_bindings=static_string_bindings,
    )
    return next_modules, next_imports, {resolved}


def _apply_api_key_alias_expression(
    expression: ast.expr,
    *,
    module_aliases: Mapping[str, str],
    import_module_aliases: AbstractSet[str],
    static_string_bindings: Mapping[str, str],
) -> tuple[dict[str, str], set[str]]:
    next_modules, next_imports, _references = _evaluate_api_key_alias_expression(
        expression,
        module_aliases=module_aliases,
        import_module_aliases=import_module_aliases,
        static_string_bindings=static_string_bindings,
    )
    return next_modules, next_imports


def _function_header_expressions(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[ast.expr]:
    expressions: list[ast.expr] = list(node.decorator_list)
    for argument in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs):
        if argument.annotation is not None:
            expressions.append(argument.annotation)
    if node.args.vararg is not None and node.args.vararg.annotation is not None:
        expressions.append(node.args.vararg.annotation)
    if node.args.kwarg is not None and node.args.kwarg.annotation is not None:
        expressions.append(node.args.kwarg.annotation)
    expressions.extend(node.args.defaults)
    expressions.extend(default for default in node.args.kw_defaults if default is not None)
    if node.returns is not None:
        expressions.append(node.returns)
    return sorted(
        expressions,
        key=lambda expression: (
            getattr(expression, "lineno", -1),
            getattr(expression, "col_offset", -1),
        ),
    )


def _legacy_api_key_dynamic_lookup_name(
    node: ast.AST,
    *,
    module_reference: Callable[[ast.AST], str | None],
    static_string_bindings: Mapping[str, str],
) -> str | None:
    def is_legacy_namespace(candidate: ast.AST) -> bool:
        if (
            isinstance(candidate, ast.Attribute)
            and candidate.attr == "__dict__"
            and module_reference(candidate.value) == "legacy_app"
        ):
            return True
        return bool(
            isinstance(candidate, ast.Call)
            and isinstance(candidate.func, ast.Name)
            and candidate.func.id == "vars"
            and len(candidate.args) == 1
            and not candidate.keywords
            and module_reference(candidate.args[0]) == "legacy_app"
        )

    if isinstance(node, ast.Subscript) and is_legacy_namespace(node.value):
        return _resolve_static_string(node.slice, static_string_bindings)
    if not isinstance(node, ast.Call):
        return None
    if (
        isinstance(node.func, ast.Name)
        and node.func.id == "getattr"
        and len(node.args) >= 2
        and module_reference(node.args[0]) == "legacy_app"
    ):
        return _resolve_static_string(node.args[1], static_string_bindings)
    if (
        isinstance(node.func, ast.Attribute)
        and node.func.attr == "__getattribute__"
        and module_reference(node.func.value) == "legacy_app"
        and node.args
    ):
        return _resolve_static_string(node.args[0], static_string_bindings)
    if (
        isinstance(node.func, ast.Attribute)
        and node.func.attr in {"get", "__getitem__", "pop", "setdefault"}
        and is_legacy_namespace(node.func.value)
        and node.args
    ):
        return _resolve_static_string(node.args[0], static_string_bindings)
    return None


def _scan_api_key_comprehension_scope(
    node: ast.ListComp | ast.SetComp | ast.DictComp | ast.GeneratorExp,
    *,
    filename: str,
    inherited_module_aliases: Mapping[str, str],
    inherited_import_module_aliases: AbstractSet[str],
    inherited_static_string_bindings: Mapping[str, str] | None = None,
) -> list[str]:
    errors: list[str] = []
    bound_names: set[str] = set()
    for index, generator in enumerate(node.generators):
        if index > 0:
            errors.extend(
                _scan_api_key_alias_expressions(
                    [generator.iter],
                    filename=filename,
                    inherited_module_aliases=inherited_module_aliases,
                    inherited_import_module_aliases=inherited_import_module_aliases,
                    inherited_static_string_bindings=inherited_static_string_bindings,
                    local_bindings=bound_names,
                )
            )
        bound_names.update(_assignment_target_names(generator.target))
        errors.extend(
            _scan_api_key_alias_expressions(
                generator.ifs,
                filename=filename,
                inherited_module_aliases=inherited_module_aliases,
                inherited_import_module_aliases=inherited_import_module_aliases,
                inherited_static_string_bindings=inherited_static_string_bindings,
                local_bindings=bound_names,
            )
        )

    result_expressions: list[ast.expr]
    if isinstance(node, ast.DictComp):
        result_expressions = [node.key, node.value]
    else:
        result_expressions = [node.elt]
    errors.extend(
        _scan_api_key_alias_expressions(
            result_expressions,
            filename=filename,
            inherited_module_aliases=inherited_module_aliases,
            inherited_import_module_aliases=inherited_import_module_aliases,
            inherited_static_string_bindings=inherited_static_string_bindings,
            local_bindings=bound_names,
        )
    )
    return errors


def _apply_api_key_alias_statements(
    statements: Sequence[ast.stmt],
    *,
    module_aliases: Mapping[str, str],
    import_module_aliases: AbstractSet[str],
    static_string_bindings: Mapping[str, str],
) -> tuple[dict[str, str], set[str]]:
    """Return the alias state after one deterministic statement block."""

    next_modules = dict(module_aliases)
    next_imports = set(import_module_aliases)

    for statement in statements:
        if isinstance(statement, ast.If):
            condition_modules, condition_imports = _apply_api_key_alias_expression(
                statement.test,
                module_aliases=next_modules,
                import_module_aliases=next_imports,
                static_string_bindings=static_string_bindings,
            )
            body_state = _apply_api_key_alias_statements(
                statement.body,
                module_aliases=condition_modules,
                import_module_aliases=condition_imports,
                static_string_bindings=static_string_bindings,
            )
            else_state = _apply_api_key_alias_statements(
                statement.orelse,
                module_aliases=condition_modules,
                import_module_aliases=condition_imports,
                static_string_bindings=static_string_bindings,
            )
            next_modules, next_imports = _join_api_key_alias_states(body_state, else_state)
            continue

        if isinstance(statement, (ast.For, ast.AsyncFor, ast.While)):
            expression = (
                statement.iter if isinstance(statement, (ast.For, ast.AsyncFor)) else statement.test
            )
            if isinstance(statement, ast.While):
                loop_modules, loop_imports = dict(next_modules), set(next_imports)
            else:
                loop_modules, loop_imports = _apply_api_key_alias_expression(
                    expression,
                    module_aliases=next_modules,
                    import_module_aliases=next_imports,
                    static_string_bindings=static_string_bindings,
                )
            (
                _iteration_entry,
                _body_entry,
                normal_loop_exit,
                break_exit,
            ) = _loop_api_key_alias_fixed_point(
                statement,
                initial_modules=loop_modules,
                initial_imports=loop_imports,
                static_string_bindings=static_string_bindings,
            )
            else_state = _apply_api_key_alias_statements(
                statement.orelse,
                module_aliases=normal_loop_exit[0],
                import_module_aliases=normal_loop_exit[1],
                static_string_bindings=static_string_bindings,
            )
            next_modules, next_imports = _join_api_key_alias_states(
                else_state,
                *((break_exit,) if break_exit is not None else ()),
            )
            continue

        if isinstance(statement, (ast.Try, ast.TryStar)):
            entry_state = (dict(next_modules), set(next_imports))
            handler_entry = _api_key_exception_prefix_state(
                statement.body,
                entry_state=entry_state,
                static_string_bindings=static_string_bindings,
            )
            body_state = _apply_api_key_alias_statements(
                statement.body,
                module_aliases=entry_state[0],
                import_module_aliases=entry_state[1],
                static_string_bindings=static_string_bindings,
            )
            normal_state = _apply_api_key_alias_statements(
                statement.orelse,
                module_aliases=body_state[0],
                import_module_aliases=body_state[1],
                static_string_bindings=static_string_bindings,
            )
            continuing_states = [normal_state]
            if statement.handlers:
                for handler in statement.handlers:
                    handler_modules = dict(handler_entry[0])
                    handler_imports = set(handler_entry[1])
                    if handler.name is not None:
                        handler_modules.pop(handler.name, None)
                        handler_imports.discard(handler.name)
                    continuing_states.append(
                        _apply_api_key_alias_statements(
                            handler.body,
                            module_aliases=handler_modules,
                            import_module_aliases=handler_imports,
                            static_string_bindings=static_string_bindings,
                        )
                    )
            joined_state = _join_api_key_alias_states(*continuing_states)
            if statement.finalbody:
                joined_state = _apply_api_key_alias_statements(
                    statement.finalbody,
                    module_aliases=joined_state[0],
                    import_module_aliases=joined_state[1],
                    static_string_bindings=static_string_bindings,
                )
            next_modules, next_imports = joined_state
            continue

        if isinstance(statement, (ast.With, ast.AsyncWith)):
            body_modules = dict(next_modules)
            body_imports = set(next_imports)
            for item in statement.items:
                body_modules, body_imports = _apply_api_key_alias_expression(
                    item.context_expr,
                    module_aliases=body_modules,
                    import_module_aliases=body_imports,
                    static_string_bindings=static_string_bindings,
                )
                if item.optional_vars is not None:
                    for target_name in _assignment_target_names(item.optional_vars):
                        body_modules.pop(target_name, None)
                        body_imports.discard(target_name)
            with_prefix_states: list[tuple[dict[str, str], set[str]]] = [
                (dict(body_modules), set(body_imports))
            ]
            body_state = with_prefix_states[0]
            for body_statement in statement.body:
                body_state = _apply_api_key_alias_statements(
                    [body_statement],
                    module_aliases=body_state[0],
                    import_module_aliases=body_state[1],
                    static_string_bindings=static_string_bindings,
                )
                with_prefix_states.append(body_state)
            next_modules, next_imports = _join_api_key_alias_states(*with_prefix_states)
            continue

        if isinstance(statement, ast.Match):
            subject_modules, subject_imports = _apply_api_key_alias_expression(
                statement.subject,
                module_aliases=next_modules,
                import_module_aliases=next_imports,
                static_string_bindings=static_string_bindings,
            )
            case_states: list[tuple[dict[str, str], set[str]]] = []
            has_irrefutable_case = False
            for case in statement.cases:
                bindings = _match_pattern_bindings(case.pattern)
                case_modules = {
                    name: module for name, module in subject_modules.items() if name not in bindings
                }
                case_imports = set(subject_imports) - bindings
                if case.guard is not None:
                    case_modules, case_imports = _apply_api_key_alias_expression(
                        case.guard,
                        module_aliases=case_modules,
                        import_module_aliases=case_imports,
                        static_string_bindings=static_string_bindings,
                    )
                case_states.append(
                    _apply_api_key_alias_statements(
                        case.body,
                        module_aliases=case_modules,
                        import_module_aliases=case_imports,
                        static_string_bindings=static_string_bindings,
                    )
                )
                has_irrefutable_case = has_irrefutable_case or _is_unguarded_irrefutable_case(case)
            if not has_irrefutable_case:
                case_states.append((subject_modules, subject_imports))
            next_modules, next_imports = _join_api_key_alias_states(*case_states)
            continue

        if isinstance(statement, ast.Import):
            for alias in statement.names:
                local_name = alias.asname or alias.name.split(".", maxsplit=1)[0]
                if alias.name in {"builtins", "importlib", "legacy_app", "sys"}:
                    next_modules[local_name] = alias.name
                else:
                    next_modules.pop(local_name, None)
            continue

        if isinstance(statement, ast.ImportFrom):
            for alias in statement.names:
                local_name = alias.asname or alias.name
                qualified = f"{statement.module}.{alias.name}"
                if qualified in {
                    "builtins.__import__",
                    "importlib.import_module",
                    "sys.modules",
                }:
                    next_modules[local_name] = qualified
                else:
                    next_modules.pop(local_name, None)
                if qualified in {"builtins.__import__", "importlib.import_module"}:
                    next_imports.add(local_name)
                else:
                    next_imports.discard(local_name)
            continue

        if isinstance(statement, (ast.Assign, ast.AnnAssign)):
            targets = statement.targets if isinstance(statement, ast.Assign) else [statement.target]
            value = statement.value
            value_references: set[str | None] = {None}
            if value is not None:
                (
                    next_modules,
                    next_imports,
                    value_references,
                ) = _evaluate_api_key_alias_expression(
                    value,
                    module_aliases=next_modules,
                    import_module_aliases=next_imports,
                    static_string_bindings=static_string_bindings,
                )
            resolved_module = _preferred_api_key_module_reference(value_references)
            for target in targets:
                for target_name in _assignment_target_names(target):
                    if value_references & {
                        "builtins.__import__",
                        "importlib.import_module",
                    }:
                        next_imports.add(target_name)
                    else:
                        next_imports.discard(target_name)
                    if resolved_module is not None:
                        next_modules[target_name] = resolved_module
                    else:
                        next_modules.pop(target_name, None)
            continue

        if isinstance(statement, ast.Expr):
            next_modules, next_imports = _apply_api_key_alias_expression(
                statement.value,
                module_aliases=next_modules,
                import_module_aliases=next_imports,
                static_string_bindings=static_string_bindings,
            )
            continue

        if isinstance(statement, (ast.AugAssign, ast.Delete)):
            targets = (
                [statement.target] if isinstance(statement, ast.AugAssign) else statement.targets
            )
            for target in targets:
                for target_name in _assignment_target_names(target):
                    next_modules.pop(target_name, None)
            continue

        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for expression in _function_header_expressions(statement):
                    next_modules, next_imports = _apply_api_key_alias_expression(
                        expression,
                        module_aliases=next_modules,
                        import_module_aliases=next_imports,
                        static_string_bindings=static_string_bindings,
                    )
            next_modules.pop(statement.name, None)
            next_imports.discard(statement.name)

    return next_modules, next_imports


_API_KEY_STRUCTURED_STATEMENT_TYPES = (
    ast.If,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.Try,
    ast.TryStar,
    ast.With,
    ast.AsyncWith,
    ast.Match,
)


def _scan_api_key_structured_statement(
    statement: (
        ast.If
        | ast.For
        | ast.AsyncFor
        | ast.While
        | ast.Try
        | ast.TryStar
        | ast.With
        | ast.AsyncWith
        | ast.Match
    ),
    *,
    filename: str,
    module_aliases: Mapping[str, str],
    import_module_aliases: AbstractSet[str],
    static_string_bindings: Mapping[str, str],
) -> list[str]:
    """Scan one compound statement with path-sensitive alias state."""

    errors: list[str] = []
    if isinstance(statement, ast.If):
        errors.extend(
            _scan_api_key_alias_expressions(
                [statement.test],
                filename=filename,
                inherited_module_aliases=module_aliases,
                inherited_import_module_aliases=import_module_aliases,
                inherited_static_string_bindings=static_string_bindings,
                local_bindings=frozenset(),
            )
        )
        condition_modules, condition_imports = _apply_api_key_alias_expression(
            statement.test,
            module_aliases=module_aliases,
            import_module_aliases=import_module_aliases,
            static_string_bindings=static_string_bindings,
        )
        for branch in (statement.body, statement.orelse):
            errors.extend(
                _scan_api_key_alias_scope(
                    branch,
                    filename=filename,
                    inherited_module_aliases=condition_modules,
                    inherited_import_module_aliases=condition_imports,
                    inherited_static_string_bindings=static_string_bindings,
                )
            )
        return errors

    if isinstance(statement, (ast.For, ast.AsyncFor, ast.While)):
        expression = (
            statement.iter if isinstance(statement, (ast.For, ast.AsyncFor)) else statement.test
        )
        errors.extend(
            _scan_api_key_alias_expressions(
                [expression],
                filename=filename,
                inherited_module_aliases=module_aliases,
                inherited_import_module_aliases=import_module_aliases,
                inherited_static_string_bindings=static_string_bindings,
                local_bindings=frozenset(),
            )
        )
        if isinstance(statement, ast.While):
            loop_modules, loop_imports = dict(module_aliases), set(import_module_aliases)
        else:
            loop_modules, loop_imports = _apply_api_key_alias_expression(
                expression,
                module_aliases=module_aliases,
                import_module_aliases=import_module_aliases,
                static_string_bindings=static_string_bindings,
            )
        (
            iteration_entry,
            body_entry,
            normal_loop_exit,
            _break_exit,
        ) = _loop_api_key_alias_fixed_point(
            statement,
            initial_modules=loop_modules,
            initial_imports=loop_imports,
            static_string_bindings=static_string_bindings,
        )
        if isinstance(statement, ast.While):
            errors.extend(
                _scan_api_key_alias_expressions(
                    [statement.test],
                    filename=filename,
                    inherited_module_aliases=iteration_entry[0],
                    inherited_import_module_aliases=iteration_entry[1],
                    inherited_static_string_bindings=static_string_bindings,
                    local_bindings=frozenset(),
                )
            )
        errors.extend(
            _scan_api_key_alias_scope(
                statement.body,
                filename=filename,
                inherited_module_aliases=body_entry[0],
                inherited_import_module_aliases=body_entry[1],
                inherited_static_string_bindings=static_string_bindings,
                local_bindings=(
                    set(_assignment_target_names(statement.target))
                    if isinstance(statement, (ast.For, ast.AsyncFor))
                    else frozenset()
                ),
            )
        )
        errors.extend(
            _scan_api_key_alias_scope(
                statement.orelse,
                filename=filename,
                inherited_module_aliases=normal_loop_exit[0],
                inherited_import_module_aliases=normal_loop_exit[1],
                inherited_static_string_bindings=static_string_bindings,
            )
        )
        return errors

    if isinstance(statement, (ast.With, ast.AsyncWith)):
        body_modules = dict(module_aliases)
        body_imports = set(import_module_aliases)
        with_bindings: set[str] = set()
        for item in statement.items:
            errors.extend(
                _scan_api_key_alias_expressions(
                    [item.context_expr],
                    filename=filename,
                    inherited_module_aliases=body_modules,
                    inherited_import_module_aliases=body_imports,
                    inherited_static_string_bindings=static_string_bindings,
                    local_bindings=frozenset(),
                )
            )
            body_modules, body_imports = _apply_api_key_alias_expression(
                item.context_expr,
                module_aliases=body_modules,
                import_module_aliases=body_imports,
                static_string_bindings=static_string_bindings,
            )
            if item.optional_vars is not None:
                with_bindings.update(_assignment_target_names(item.optional_vars))
        errors.extend(
            _scan_api_key_alias_scope(
                statement.body,
                filename=filename,
                inherited_module_aliases=body_modules,
                inherited_import_module_aliases=body_imports,
                inherited_static_string_bindings=static_string_bindings,
                local_bindings=with_bindings,
            )
        )
        return errors

    if isinstance(statement, ast.Match):
        errors.extend(
            _scan_api_key_alias_expressions(
                [statement.subject],
                filename=filename,
                inherited_module_aliases=module_aliases,
                inherited_import_module_aliases=import_module_aliases,
                inherited_static_string_bindings=static_string_bindings,
                local_bindings=frozenset(),
            )
        )
        subject_modules, subject_imports = _apply_api_key_alias_expression(
            statement.subject,
            module_aliases=module_aliases,
            import_module_aliases=import_module_aliases,
            static_string_bindings=static_string_bindings,
        )
        for case in statement.cases:
            bindings = _match_pattern_bindings(case.pattern)
            case_modules = {
                name: module for name, module in subject_modules.items() if name not in bindings
            }
            case_imports = set(subject_imports) - bindings
            if case.guard is not None:
                errors.extend(
                    _scan_api_key_alias_expressions(
                        [case.guard],
                        filename=filename,
                        inherited_module_aliases=case_modules,
                        inherited_import_module_aliases=case_imports,
                        inherited_static_string_bindings=static_string_bindings,
                        local_bindings=frozenset(),
                    )
                )
                case_modules, case_imports = _apply_api_key_alias_expression(
                    case.guard,
                    module_aliases=case_modules,
                    import_module_aliases=case_imports,
                    static_string_bindings=static_string_bindings,
                )
            errors.extend(
                _scan_api_key_alias_scope(
                    case.body,
                    filename=filename,
                    inherited_module_aliases=case_modules,
                    inherited_import_module_aliases=case_imports,
                    inherited_static_string_bindings=static_string_bindings,
                    local_bindings=bindings,
                )
            )
        return errors

    entry_state = (dict(module_aliases), set(import_module_aliases))
    errors.extend(
        _scan_api_key_alias_scope(
            statement.body,
            filename=filename,
            inherited_module_aliases=entry_state[0],
            inherited_import_module_aliases=entry_state[1],
            inherited_static_string_bindings=static_string_bindings,
        )
    )
    handler_entry = _api_key_exception_prefix_state(
        statement.body,
        entry_state=entry_state,
        static_string_bindings=static_string_bindings,
    )
    body_state = _apply_api_key_alias_statements(
        statement.body,
        module_aliases=entry_state[0],
        import_module_aliases=entry_state[1],
        static_string_bindings=static_string_bindings,
    )
    errors.extend(
        _scan_api_key_alias_scope(
            statement.orelse,
            filename=filename,
            inherited_module_aliases=body_state[0],
            inherited_import_module_aliases=body_state[1],
            inherited_static_string_bindings=static_string_bindings,
        )
    )
    normal_state = _apply_api_key_alias_statements(
        statement.orelse,
        module_aliases=body_state[0],
        import_module_aliases=body_state[1],
        static_string_bindings=static_string_bindings,
    )
    continuing_states = [normal_state]
    if statement.handlers:
        for handler in statement.handlers:
            if handler.type is not None:
                errors.extend(
                    _scan_api_key_alias_expressions(
                        [handler.type],
                        filename=filename,
                        inherited_module_aliases=handler_entry[0],
                        inherited_import_module_aliases=handler_entry[1],
                        inherited_static_string_bindings=static_string_bindings,
                        local_bindings=frozenset(),
                    )
                )
            handler_bindings = {handler.name} if handler.name is not None else set()
            errors.extend(
                _scan_api_key_alias_scope(
                    handler.body,
                    filename=filename,
                    inherited_module_aliases=handler_entry[0],
                    inherited_import_module_aliases=handler_entry[1],
                    inherited_static_string_bindings=static_string_bindings,
                    local_bindings=handler_bindings,
                )
            )
            handler_modules = {
                name: module
                for name, module in handler_entry[0].items()
                if name not in handler_bindings
            }
            handler_imports = set(handler_entry[1]) - handler_bindings
            continuing_states.append(
                _apply_api_key_alias_statements(
                    handler.body,
                    module_aliases=handler_modules,
                    import_module_aliases=handler_imports,
                    static_string_bindings=static_string_bindings,
                )
            )
    joined_state = _join_api_key_alias_states(*continuing_states)
    errors.extend(
        _scan_api_key_alias_scope(
            statement.finalbody,
            filename=filename,
            inherited_module_aliases=joined_state[0],
            inherited_import_module_aliases=joined_state[1],
            inherited_static_string_bindings=static_string_bindings,
        )
    )
    return errors


def _scan_api_key_alias_scope(
    statements: Sequence[ast.stmt],
    *,
    filename: str,
    inherited_module_aliases: Mapping[str, str],
    inherited_import_module_aliases: AbstractSet[str],
    inherited_closure_module_aliases: Mapping[str, str] | None = None,
    inherited_closure_import_module_aliases: AbstractSet[str] | None = None,
    inherited_static_string_bindings: Mapping[str, str] | None = None,
    local_bindings: AbstractSet[str] = frozenset(),
) -> list[str]:
    errors: list[str] = []
    module_aliases = {
        name: module
        for name, module in inherited_module_aliases.items()
        if name not in local_bindings
    }
    import_module_aliases = set(inherited_import_module_aliases) - set(local_bindings)
    if inherited_closure_module_aliases is None:
        closure_module_aliases = module_aliases
    else:
        closure_module_aliases = dict(inherited_closure_module_aliases)
    if inherited_closure_import_module_aliases is None:
        closure_import_module_aliases = import_module_aliases
    else:
        closure_import_module_aliases = set(inherited_closure_import_module_aliases)
    scope_tree = ast.Module(body=list(statements), type_ignores=[])
    local_static_string_bindings = _collect_static_string_bindings(scope_tree)
    static_string_bindings = {
        name: value
        for name, value in (inherited_static_string_bindings or {}).items()
        if name not in local_bindings
    }
    static_string_bindings.update(local_static_string_bindings)
    scope_nodes, nested_scopes = _ordered_lexical_scope_nodes(statements)
    structured_nodes = [
        node for node in scope_nodes if isinstance(node, _API_KEY_STRUCTURED_STATEMENT_TYPES)
    ]
    nested_structured_ids = {
        id(child)
        for node in structured_nodes
        for child in ast.walk(node)
        if child is not node and isinstance(child, _API_KEY_STRUCTURED_STATEMENT_TYPES)
    }
    root_structured_nodes = {
        id(node): node for node in structured_nodes if id(node) not in nested_structured_ids
    }
    structured_descendant_node_ids = {
        id(child)
        for node in root_structured_nodes.values()
        for child in ast.walk(node)
        if child is not node
    }
    structured_expression_binding_ids = {
        id(child)
        for node in scope_nodes
        if isinstance(node, (ast.IfExp, ast.BoolOp))
        for child in ast.walk(node)
        if isinstance(child, ast.NamedExpr)
    }
    lexical_scope_alias_snapshots: dict[
        int,
        tuple[dict[str, str], set[str]],
    ] = {}

    def module_reference(node: ast.AST) -> str | None:
        return _static_module_reference(
            node,
            module_aliases=module_aliases,
            import_module_aliases=import_module_aliases,
            static_string_bindings=static_string_bindings,
        )

    for node in scope_nodes:
        if id(node) in root_structured_nodes:
            structured_statement = root_structured_nodes[id(node)]
            errors.extend(
                _scan_api_key_structured_statement(
                    structured_statement,
                    filename=filename,
                    module_aliases=module_aliases,
                    import_module_aliases=import_module_aliases,
                    static_string_bindings=static_string_bindings,
                )
            )
            module_aliases, import_module_aliases = _apply_api_key_alias_statements(
                [structured_statement],
                module_aliases=module_aliases,
                import_module_aliases=import_module_aliases,
                static_string_bindings=static_string_bindings,
            )
        elif id(node) in structured_descendant_node_ids:
            continue
        elif id(node) in structured_expression_binding_ids:
            pass
        elif isinstance(node, ast.Import):
            for alias in node.names:
                local_name = alias.asname or alias.name.split(".", maxsplit=1)[0]
                if alias.name in {"builtins", "importlib", "legacy_app", "sys"}:
                    module_aliases[local_name] = alias.name
                else:
                    module_aliases.pop(local_name, None)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                local_name = alias.asname or alias.name
                if node.module == "legacy_app" and alias.name == "*":
                    errors.append(f"{filename}: canonical code must not star import legacy_app")
                qualified = f"{node.module}.{alias.name}"
                if qualified in {
                    "builtins.__import__",
                    "importlib.import_module",
                    "sys.modules",
                }:
                    module_aliases[local_name] = qualified
                else:
                    module_aliases.pop(local_name, None)
                if qualified in {"builtins.__import__", "importlib.import_module"}:
                    import_module_aliases.add(local_name)
                else:
                    import_module_aliases.discard(local_name)
                if node.module == "legacy_app" and alias.name in CANONICAL_API_KEY_SYMBOLS:
                    errors.append(
                        f"{filename}: canonical code must import API-key dependency "
                        f"from {CANONICAL_API_KEY}, not legacy_app: {alias.name}"
                    )
        elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.NamedExpr)):
            targets: list[ast.expr]
            value: ast.expr | None
            if isinstance(node, ast.Assign):
                targets = node.targets
                value = node.value
            else:
                targets = [node.target]
                value = node.value
            value_references: set[str | None] = {None}
            if value is not None:
                (
                    module_aliases,
                    import_module_aliases,
                    value_references,
                ) = _evaluate_api_key_alias_expression(
                    value,
                    module_aliases=module_aliases,
                    import_module_aliases=import_module_aliases,
                    static_string_bindings=static_string_bindings,
                )
            resolved_module = _preferred_api_key_module_reference(value_references)
            for target in targets:
                for target_name in _assignment_target_names(target):
                    if value_references & {
                        "builtins.__import__",
                        "importlib.import_module",
                    }:
                        import_module_aliases.add(target_name)
                    else:
                        import_module_aliases.discard(target_name)
                    if resolved_module is not None:
                        module_aliases[target_name] = resolved_module
                    else:
                        module_aliases.pop(target_name, None)
        elif isinstance(node, ast.Expr):
            module_aliases, import_module_aliases = _apply_api_key_alias_expression(
                node.value,
                module_aliases=module_aliases,
                import_module_aliases=import_module_aliases,
                static_string_bindings=static_string_bindings,
            )
        elif isinstance(node, (ast.AugAssign, ast.Delete)):
            targets = [node.target] if isinstance(node, ast.AugAssign) else node.targets
            for target in targets:
                for target_name in _assignment_target_names(target):
                    module_aliases.pop(target_name, None)

        if (
            isinstance(node, ast.Attribute)
            and node.attr in CANONICAL_API_KEY_SYMBOLS
            and module_reference(node.value) == "legacy_app"
        ):
            errors.append(
                f"{filename}: legacy API-key dependency attribute access is forbidden: {node.attr}"
            )
        else:
            symbol_name = _legacy_api_key_dynamic_lookup_name(
                node,
                module_reference=module_reference,
                static_string_bindings=static_string_bindings,
            )
            if symbol_name in CANONICAL_API_KEY_SYMBOLS:
                errors.append(
                    f"{filename}: dynamic legacy API-key dependency lookup is forbidden: "
                    f"{symbol_name}"
                )

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for expression in _function_header_expressions(node):
                module_aliases, import_module_aliases = _apply_api_key_alias_expression(
                    expression,
                    module_aliases=module_aliases,
                    import_module_aliases=import_module_aliases,
                    static_string_bindings=static_string_bindings,
                )
            snapshot_modules = (
                closure_module_aliases
                if inherited_closure_module_aliases is not None
                else module_aliases
            )
            snapshot_imports = (
                closure_import_module_aliases
                if inherited_closure_import_module_aliases is not None
                else import_module_aliases
            )
            lexical_scope_alias_snapshots[id(node)] = (
                dict(snapshot_modules),
                set(snapshot_imports),
            )
        elif isinstance(node, ast.ClassDef):
            lexical_scope_alias_snapshots[id(node)] = (
                dict(module_aliases),
                set(import_module_aliases),
            )
        elif isinstance(
            node,
            (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp),
        ):
            comprehension_module_aliases = (
                closure_module_aliases
                if inherited_closure_module_aliases is not None
                else module_aliases
            )
            comprehension_import_module_aliases = (
                closure_import_module_aliases
                if inherited_closure_import_module_aliases is not None
                else import_module_aliases
            )
            lexical_scope_alias_snapshots[id(node)] = (
                dict(comprehension_module_aliases),
                set(comprehension_import_module_aliases),
            )
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            module_aliases.pop(node.name, None)
            import_module_aliases.discard(node.name)

    final_closure_module_aliases = (
        closure_module_aliases if inherited_closure_module_aliases is not None else module_aliases
    )
    final_closure_import_module_aliases = (
        closure_import_module_aliases
        if inherited_closure_import_module_aliases is not None
        else import_module_aliases
    )

    for nested_scope in nested_scopes:
        if id(nested_scope) in structured_descendant_node_ids:
            continue
        if isinstance(nested_scope, (ast.FunctionDef, ast.AsyncFunctionDef)):
            function_states = [
                (
                    dict(final_closure_module_aliases),
                    set(final_closure_import_module_aliases),
                ),
                lexical_scope_alias_snapshots[id(nested_scope)],
            ]
            for function_modules, function_imports in function_states:
                errors.extend(
                    _scan_api_key_alias_scope(
                        nested_scope.body,
                        filename=filename,
                        inherited_module_aliases=function_modules,
                        inherited_import_module_aliases=function_imports,
                        inherited_static_string_bindings=static_string_bindings,
                        local_bindings=_function_local_bindings(nested_scope),
                    )
                )
            continue

        if isinstance(nested_scope, ast.Lambda):
            errors.extend(
                _scan_api_key_alias_scope(
                    [ast.Expr(value=nested_scope.body)],
                    filename=filename,
                    inherited_module_aliases=final_closure_module_aliases,
                    inherited_import_module_aliases=final_closure_import_module_aliases,
                    inherited_static_string_bindings=static_string_bindings,
                    local_bindings=_lambda_local_bindings(nested_scope),
                )
            )
            continue

        (
            nested_module_aliases,
            nested_import_module_aliases,
        ) = lexical_scope_alias_snapshots[id(nested_scope)]
        if isinstance(nested_scope, ast.ClassDef):
            nested_statements = nested_scope.body
            nested_local_bindings: AbstractSet[str] = frozenset()
        else:
            errors.extend(
                _scan_api_key_comprehension_scope(
                    nested_scope,
                    filename=filename,
                    inherited_module_aliases=nested_module_aliases,
                    inherited_import_module_aliases=nested_import_module_aliases,
                    inherited_static_string_bindings=static_string_bindings,
                )
            )
            continue
        errors.extend(
            _scan_api_key_alias_scope(
                nested_statements,
                filename=filename,
                inherited_module_aliases=nested_module_aliases,
                inherited_import_module_aliases=nested_import_module_aliases,
                inherited_closure_module_aliases=final_closure_module_aliases,
                inherited_closure_import_module_aliases=final_closure_import_module_aliases,
                inherited_static_string_bindings=static_string_bindings,
                local_bindings=nested_local_bindings,
            )
        )
    return list(dict.fromkeys(errors))


def _app_api_key_reverse_dependency_errors(
    tree: ast.Module,
    *,
    filename: str,
) -> list[str]:
    return _scan_api_key_alias_scope(
        tree.body,
        filename=filename,
        inherited_module_aliases={"__import__": "builtins.__import__"},
        inherited_import_module_aliases=frozenset({"__import__"}),
    )


def validate_api_key_dependency_ownership(
    legacy_source: str,
    app_sources: Mapping[str, str],
) -> list[str]:
    """Keep client API-key dependency ownership canonical and identity-preserving."""

    errors = _canonical_api_key_source_errors(app_sources)
    legacy_tree, parse_errors = _parse_source(legacy_source, filename=LEGACY_APP)
    errors.extend(parse_errors)
    if legacy_tree is not None:
        errors.extend(_legacy_api_key_export_errors(legacy_tree))

    for filename, source_text in sorted(app_sources.items()):
        tree, source_errors = _parse_source(source_text, filename=filename)
        errors.extend(source_errors)
        if tree is not None:
            errors.extend(_app_api_key_reverse_dependency_errors(tree, filename=filename))
    return sorted(set(errors))


def _collect_lifecycle_references(
    tree: ast.Module,
) -> tuple[dict[str, str], frozenset[str]]:
    """Resolve the small static alias set relevant to lifecycle ownership."""

    references: dict[str, str] = {
        "FastAPI": "fastapi.FastAPI",
        "__builtins__": "builtins",
        "__import__": "builtins.__import__",
        "dict": "builtins.dict",
        "getattr": "builtins.getattr",
        "setattr": "builtins.setattr",
        "vars": "builtins.vars",
    }
    canonical_lifespan_aliases: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in {
                    "builtins",
                    "fastapi",
                    "fastapi.applications",
                    "importlib",
                    "sys",
                }:
                    if alias.asname is not None:
                        references[alias.asname] = alias.name
                    else:
                        root_module = alias.name.partition(".")[0]
                        references[root_module] = root_module
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            for alias in node.names:
                local_name = alias.asname or alias.name
                qualified = f"{node.module}.{alias.name}"
                if qualified in {
                    "builtins.__import__",
                    "builtins.dict",
                    "builtins.getattr",
                    "builtins.setattr",
                    "builtins.vars",
                    "fastapi.FastAPI",
                    "fastapi.applications",
                    "fastapi.applications.FastAPI",
                    "importlib.import_module",
                    "sys.modules",
                }:
                    references[local_name] = qualified
                if qualified == "app.bootstrap.lifespan.application_lifespan":
                    canonical_lifespan_aliases.add(local_name)

    static_string_bindings = _collect_static_string_bindings(tree)
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
            reference = _resolve_lifecycle_reference(
                value,
                references=references,
                static_string_bindings=static_string_bindings,
            )
            if reference is None:
                continue
            for target in targets:
                for target_name in _assignment_target_names(target):
                    if references.get(target_name) != reference:
                        references[target_name] = reference
                        changed = True
    binding_counts = _collect_binding_counts(tree)
    stable_canonical_aliases = {
        name for name in canonical_lifespan_aliases if binding_counts[name] == 1
    }
    return references, frozenset(stable_canonical_aliases)


def _resolve_lifecycle_reference(
    node: ast.AST,
    *,
    references: Mapping[str, str],
    static_string_bindings: Mapping[str, str],
) -> str | None:
    if isinstance(node, ast.Name):
        return references.get(node.id)
    if isinstance(node, ast.Subscript):
        parent = _resolve_lifecycle_reference(
            node.value,
            references=references,
            static_string_bindings=static_string_bindings,
        )
        member_name = _resolve_static_string(node.slice, static_string_bindings)
        if parent is not None and parent.endswith(".__dict__"):
            parent = parent.removesuffix(".__dict__")
        if parent is not None and member_name is not None:
            return f"{parent}.{member_name}"
        return None
    if isinstance(node, ast.Attribute):
        parent = _resolve_lifecycle_reference(
            node.value,
            references=references,
            static_string_bindings=static_string_bindings,
        )
        if parent is not None:
            return f"{parent}.{node.attr}"
        if node.attr in {"add_event_handler", "on_event", "on_shutdown", "on_startup"}:
            return f"*.{node.attr}"
        if node.attr == "__getattribute__":
            return "object.__getattribute__"
        if node.attr == "__setattr__":
            return "object.__setattr__"
        return None
    if not isinstance(node, ast.Call):
        return None
    if (
        isinstance(node.func, ast.Attribute)
        and node.func.attr in {"__getitem__", "get"}
        and node.args
        and _is_object_namespace_mapping(
            node.func.value,
            references=references,
            static_string_bindings=static_string_bindings,
        )
    ):
        namespace_owner = _resolve_lifecycle_reference(
            node.func.value,
            references=references,
            static_string_bindings=static_string_bindings,
        )
        if namespace_owner is not None and namespace_owner.endswith(".__dict__"):
            namespace_owner = namespace_owner.removesuffix(".__dict__")
        member_name = _resolve_static_string(node.args[0], static_string_bindings)
        if namespace_owner is not None and member_name is not None:
            return f"{namespace_owner}.{member_name}"
        return None
    function_reference = _resolve_lifecycle_reference(
        node.func,
        references=references,
        static_string_bindings=static_string_bindings,
    )
    if function_reference == "builtins.vars" and len(node.args) == 1 and not node.keywords:
        return _resolve_lifecycle_reference(
            node.args[0],
            references=references,
            static_string_bindings=static_string_bindings,
        )
    if (
        function_reference is not None
        and function_reference.endswith(".__getattribute__")
        and node.args
    ):
        parent_node: ast.AST | None
        if len(node.args) >= 2:
            parent_node = node.args[0]
            attribute_node = node.args[1]
        else:
            parent_node = node.func.value if isinstance(node.func, ast.Attribute) else None
            attribute_node = node.args[0]
        attribute_name = _resolve_static_string(attribute_node, static_string_bindings)
        parent = (
            _resolve_lifecycle_reference(
                parent_node,
                references=references,
                static_string_bindings=static_string_bindings,
            )
            if parent_node is not None
            else None
        )
        if parent is None and function_reference != "object.__getattribute__":
            parent = function_reference.removesuffix(".__getattribute__")
        if parent is not None and attribute_name is not None:
            return f"{parent}.{attribute_name}"
        if attribute_name in {"add_event_handler", "on_event", "on_shutdown", "on_startup"}:
            return f"*.{attribute_name}"
        if attribute_name == "__dict__":
            return "*.__dict__"
        return None
    if function_reference != "builtins.getattr" or len(node.args) < 2:
        return None
    attribute_name = _resolve_static_string(node.args[1], static_string_bindings)
    if attribute_name is None:
        return None
    parent = _resolve_lifecycle_reference(
        node.args[0],
        references=references,
        static_string_bindings=static_string_bindings,
    )
    if parent is not None:
        return f"{parent}.{attribute_name}"
    if attribute_name in {"add_event_handler", "on_event", "on_shutdown", "on_startup"}:
        return f"*.{attribute_name}"
    if attribute_name == "__dict__":
        return "*.__dict__"
    return None


def _assigns_lifespan_context(tree: ast.Module) -> bool:
    references, _canonical_lifespan_aliases = _collect_lifecycle_references(tree)
    static_string_bindings = _collect_static_string_bindings(tree)
    static_mapping_bindings = _collect_static_mapping_bindings(tree)
    for node in ast.walk(tree):
        targets: list[ast.AST] = []
        assigned_value: ast.AST | None = None
        if isinstance(node, ast.Assign):
            targets.extend(node.targets)
            assigned_value = node.value
        elif isinstance(node, ast.AnnAssign):
            targets.append(node.target)
            assigned_value = node.value
        elif isinstance(node, ast.AugAssign):
            targets.append(node.target)
        elif isinstance(node, ast.Delete):
            targets.extend(node.targets)
        for target in targets:
            if isinstance(target, ast.Attribute) and target.attr == "lifespan_context":
                return True
            if (
                isinstance(target, ast.Subscript)
                and _resolve_static_string(target.slice, static_string_bindings)
                == "lifespan_context"
            ):
                return True
            if (
                assigned_value is not None
                and _is_object_namespace_mapping(
                    target,
                    references=references,
                    static_string_bindings=static_string_bindings,
                )
                and _mapping_may_mutate_protected_namespace(
                    assigned_value,
                    protected_names={"lifespan_context"},
                    static_string_bindings=static_string_bindings,
                    static_mapping_bindings=static_mapping_bindings,
                )
            ):
                return True
        if (
            isinstance(node, ast.AugAssign)
            and isinstance(node.op, ast.BitOr)
            and _is_object_namespace_mapping(
                node.target,
                references=references,
                static_string_bindings=static_string_bindings,
            )
            and _mapping_may_mutate_protected_namespace(
                node.value,
                protected_names={"lifespan_context"},
                static_string_bindings=static_string_bindings,
                static_mapping_bindings=static_mapping_bindings,
            )
        ):
            return True
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "__setattr__"
            and len(node.args) >= 1
            and _resolve_static_string(node.args[0], static_string_bindings) == "lifespan_context"
        ):
            return True
        if (
            isinstance(node, ast.Call)
            and len(node.args) >= 2
            and _resolve_lifecycle_reference(
                node.func,
                references=references,
                static_string_bindings=static_string_bindings,
            )
            in {"builtins.setattr", "object.__setattr__"}
            and _resolve_static_string(node.args[1], static_string_bindings) == "lifespan_context"
        ):
            return True
        if isinstance(node, ast.Call) and _mutates_protected_namespace(
            node,
            protected_names={"lifespan_context"},
            references=references,
            static_string_bindings=static_string_bindings,
            static_mapping_bindings=static_mapping_bindings,
        ):
            return True
    return False


def _is_object_namespace_mapping(
    node: ast.AST,
    *,
    references: Mapping[str, str],
    static_string_bindings: Mapping[str, str],
) -> bool:
    if (isinstance(node, ast.Attribute) and node.attr == "__dict__") or (
        isinstance(node, ast.Call)
        and _resolve_lifecycle_reference(
            node.func,
            references=references,
            static_string_bindings=static_string_bindings,
        )
        == "builtins.vars"
    ):
        return True
    resolved = _resolve_lifecycle_reference(
        node,
        references=references,
        static_string_bindings=static_string_bindings,
    )
    return resolved is not None and resolved.endswith(".__dict__")


def _mutates_protected_namespace(
    node: ast.Call,
    *,
    protected_names: AbstractSet[str],
    references: Mapping[str, str],
    static_string_bindings: Mapping[str, str],
    static_mapping_bindings: Mapping[str, ast.Dict],
) -> bool:
    arguments = list(node.args)
    if isinstance(node.func, ast.Attribute) and _is_object_namespace_mapping(
        node.func.value,
        references=references,
        static_string_bindings=static_string_bindings,
    ):
        method_name = node.func.attr
    else:
        function_reference = _resolve_lifecycle_reference(
            node.func,
            references=references,
            static_string_bindings=static_string_bindings,
        )
        dict_method_prefix = "builtins.dict."
        if (
            function_reference is None
            or not function_reference.startswith(dict_method_prefix)
            or not arguments
            or not _is_object_namespace_mapping(
                arguments[0],
                references=references,
                static_string_bindings=static_string_bindings,
            )
        ):
            return False
        method_name = function_reference.removeprefix(dict_method_prefix)
        arguments = arguments[1:]
    if method_name in {"__ior__", "update"}:
        if any(keyword.arg in protected_names for keyword in node.keywords):
            return True
        mapping_arguments = [
            *arguments,
            *(keyword.value for keyword in node.keywords if keyword.arg is None),
        ]
        for argument in mapping_arguments:
            if _mapping_may_mutate_protected_namespace(
                argument,
                protected_names=protected_names,
                static_string_bindings=static_string_bindings,
                static_mapping_bindings=static_mapping_bindings,
            ):
                return True
        return False
    if method_name == "clear":
        return True
    if method_name in {"__delitem__", "__setitem__", "pop", "setdefault"}:
        if not arguments:
            return True
        key_name = _resolve_static_string(arguments[0], static_string_bindings)
        return key_name is None or key_name in protected_names
    return False


def _mapping_may_mutate_protected_namespace(
    node: ast.AST,
    *,
    protected_names: AbstractSet[str],
    static_string_bindings: Mapping[str, str],
    static_mapping_bindings: Mapping[str, ast.Dict],
) -> bool:
    mapping = _resolve_static_mapping(node, static_mapping_bindings)
    if mapping is None:
        return True
    for key, _value in mapping:
        if key is None:
            return True
        resolved_key = _resolve_static_string(key, static_string_bindings)
        if resolved_key is None or resolved_key in protected_names:
            return True
    return False


def _accesses_lifecycle_event_namespace(
    tree: ast.Module,
    *,
    references: Mapping[str, str],
    static_string_bindings: Mapping[str, str],
) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Subscript) or not _is_object_namespace_mapping(
            node.value,
            references=references,
            static_string_bindings=static_string_bindings,
        ):
            continue
        event_name = _resolve_static_string(node.slice, static_string_bindings)
        if event_name in {"on_shutdown", "on_startup"}:
            return True
    return False


def _registers_lifecycle_event(tree: ast.Module) -> bool:
    references, _canonical_lifespan_aliases = _collect_lifecycle_references(tree)
    static_string_bindings = _collect_static_string_bindings(tree)
    static_mapping_bindings = _collect_static_mapping_bindings(tree)
    if _accesses_lifecycle_event_namespace(
        tree,
        references=references,
        static_string_bindings=static_string_bindings,
    ):
        return True
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            raw_targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(
                isinstance(target, ast.Attribute) and target.attr in {"on_shutdown", "on_startup"}
                for target in raw_targets
            ):
                return True
            assigned_value = node.value if isinstance(node, (ast.Assign, ast.AnnAssign)) else None
            if assigned_value is not None and any(
                _is_object_namespace_mapping(
                    target,
                    references=references,
                    static_string_bindings=static_string_bindings,
                )
                and _mapping_may_mutate_protected_namespace(
                    assigned_value,
                    protected_names={"on_shutdown", "on_startup"},
                    static_string_bindings=static_string_bindings,
                    static_mapping_bindings=static_mapping_bindings,
                )
                for target in raw_targets
            ):
                return True
            if (
                isinstance(node, ast.AugAssign)
                and isinstance(node.op, ast.BitOr)
                and _is_object_namespace_mapping(
                    node.target,
                    references=references,
                    static_string_bindings=static_string_bindings,
                )
                and _mapping_may_mutate_protected_namespace(
                    node.value,
                    protected_names={"on_shutdown", "on_startup"},
                    static_string_bindings=static_string_bindings,
                    static_mapping_bindings=static_mapping_bindings,
                )
            ):
                return True
        if not isinstance(node, ast.Call):
            continue
        if _mutates_protected_namespace(
            node,
            protected_names={"on_shutdown", "on_startup"},
            references=references,
            static_string_bindings=static_string_bindings,
            static_mapping_bindings=static_mapping_bindings,
        ):
            return True
        reference = _resolve_lifecycle_reference(
            node.func,
            references=references,
            static_string_bindings=static_string_bindings,
        )
        if reference in {"*.add_event_handler", "*.on_event"}:
            return True
        if reference is not None and reference.startswith(("*.on_shutdown.", "*.on_startup.")):
            return True
    return False


def _uses_noncanonical_fastapi_lifespan(tree: ast.Module) -> bool:
    references, canonical_lifespan_aliases = _collect_lifecycle_references(tree)
    static_string_bindings = _collect_static_string_bindings(tree)
    static_mapping_bindings = _collect_static_mapping_bindings(tree)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        resolved_constructor = _resolve_lifecycle_reference(
            node.func,
            references=references,
            static_string_bindings=static_string_bindings,
        )
        if resolved_constructor not in {"fastapi.FastAPI", "fastapi.applications.FastAPI"}:
            continue
        has_canonical_lifespan = False
        for keyword in node.keywords:
            if keyword.arg is None:
                expanded_mapping = _resolve_static_mapping(
                    keyword.value,
                    static_mapping_bindings,
                )
                if expanded_mapping is None:
                    return True
                for key, value in expanded_mapping:
                    if key is None:
                        return True
                    resolved_key = _resolve_static_string(key, static_string_bindings)
                    if resolved_key is None:
                        return True
                    if resolved_key == "lifespan":
                        if not _is_canonical_lifespan_value(
                            value,
                            canonical_lifespan_aliases,
                        ):
                            return True
                        has_canonical_lifespan = True
                continue
            if keyword.arg != "lifespan":
                continue
            if not _is_canonical_lifespan_value(
                keyword.value,
                canonical_lifespan_aliases,
            ):
                return True
            has_canonical_lifespan = True
        if not has_canonical_lifespan:
            return True
    return False


def _collect_static_mapping_bindings(tree: ast.Module) -> Mapping[str, ast.Dict]:
    """Return simple literal mappings that are safe to inspect for ``**kwargs``."""

    candidates: dict[str, ast.Dict] = {}
    assignment_counts: Counter[str] = Counter()
    mutated_names: set[str] = set()
    expansion_name_nodes = {
        id(keyword.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        for keyword in node.keywords
        if keyword.arg is None and isinstance(keyword.value, ast.Name)
    }
    for node in ast.walk(tree):
        value: ast.AST | None = None
        targets: list[ast.expr] = []
        if isinstance(node, ast.Assign):
            value = node.value
            targets = list(node.targets)
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            value = node.value
            targets = [node.target]
        elif isinstance(node, ast.AugAssign):
            for target_name in _assignment_target_names(node.target):
                mutated_names.add(target_name)
            continue
        for target in targets:
            target_names = tuple(_assignment_target_names(target))
            for target_name in target_names:
                assignment_counts[target_name] += 1
            if isinstance(value, ast.Dict):
                for target_name in target_names:
                    candidates[target_name] = value
        if isinstance(node, ast.Subscript) and isinstance(node.ctx, (ast.Store, ast.Del)):
            if isinstance(node.value, ast.Name):
                mutated_names.add(node.value.id)
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
        ):
            mutated_names.add(node.func.value.id)
        if (
            isinstance(node, ast.Name)
            and isinstance(node.ctx, ast.Load)
            and node.id in candidates
            and id(node) not in expansion_name_nodes
        ):
            mutated_names.add(node.id)
    return {
        name: value
        for name, value in candidates.items()
        if assignment_counts[name] == 1 and name not in mutated_names
    }


def _resolve_static_mapping(
    node: ast.AST,
    bindings: Mapping[str, ast.Dict],
) -> tuple[tuple[ast.AST | None, ast.AST], ...] | None:
    if isinstance(node, ast.Name):
        resolved = bindings.get(node.id)
        if resolved is None:
            return None
        node = resolved
    if not isinstance(node, ast.Dict):
        return None
    return tuple(zip(node.keys, node.values, strict=True))


def _is_canonical_lifespan_value(
    node: ast.AST,
    canonical_lifespan_aliases: AbstractSet[str],
) -> bool:
    return isinstance(node, ast.Name) and node.id in canonical_lifespan_aliases


def _is_facade_module_name(module_name: str) -> bool:
    return module_name in {"app", "legacy_app"} or module_name.startswith(("app.", "legacy_app."))


def _uses_dynamic_facade_lookup(tree: ast.Module) -> bool:
    references, _canonical_lifespan_aliases = _collect_lifecycle_references(tree)
    static_string_bindings = _collect_static_string_bindings(tree)
    for node in ast.walk(tree):
        reference = _resolve_lifecycle_reference(
            node,
            references=references,
            static_string_bindings=static_string_bindings,
        )
        if reference == "sys.modules":
            return True
        if not isinstance(node, ast.Call):
            continue
        function_reference = _resolve_lifecycle_reference(
            node.func,
            references=references,
            static_string_bindings=static_string_bindings,
        )
        if function_reference not in {"builtins.__import__", "importlib.import_module"}:
            continue
        module_node = node.args[0] if node.args else None
        package_node = (
            node.args[1]
            if function_reference == "importlib.import_module" and len(node.args) >= 2
            else None
        )
        for keyword in node.keywords:
            if keyword.arg in {"name", "module"}:
                module_node = keyword.value
            elif keyword.arg == "package" and function_reference == "importlib.import_module":
                package_node = keyword.value
        if module_node is None:
            continue
        module_name = _resolve_static_string(module_node, static_string_bindings)
        if module_name is not None and module_name.startswith("."):
            if package_node is None:
                return True
            package_name = _resolve_static_string(package_node, static_string_bindings)
            if package_name is None:
                return True
            try:
                module_name = resolve_name(module_name, package_name)
            except ImportError:
                return True
        if module_name is None or _is_facade_module_name(module_name):
            return True
    return False


def validate_lifecycle_ownership(
    legacy_source: str,
    food_search_source: str,
    lifespan_source: str,
) -> list[str]:
    """Return errors when lifecycle ownership leaks outside the canonical module."""

    errors: list[str] = []
    legacy_tree, legacy_parse_errors = _parse_source(legacy_source, filename=LEGACY_APP)
    food_tree, food_parse_errors = _parse_source(
        food_search_source,
        filename=FOOD_SEARCH_BOOTSTRAP,
    )
    lifespan_tree, lifespan_parse_errors = _parse_source(
        lifespan_source,
        filename=CANONICAL_LIFESPAN,
    )
    errors.extend(legacy_parse_errors)
    errors.extend(food_parse_errors)
    errors.extend(lifespan_parse_errors)
    if legacy_tree is not None:
        if any(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "lifespan"
            for node in ast.walk(legacy_tree)
        ):
            errors.append(f"{LEGACY_APP}: lifecycle implementation must be canonical")
        if _registers_lifecycle_event(legacy_tree):
            errors.append(f"{LEGACY_APP}: startup/shutdown event registration is forbidden")
        if _assigns_lifespan_context(legacy_tree):
            errors.append(f"{LEGACY_APP}: lifespan_context mutation is forbidden")
        if _uses_noncanonical_fastapi_lifespan(legacy_tree):
            errors.append(f"{LEGACY_APP}: FastAPI lifespan must use the canonical re-export")
    if food_tree is not None:
        if _registers_lifecycle_event(food_tree):
            errors.append(
                f"{FOOD_SEARCH_BOOTSTRAP}: startup/shutdown event registration is forbidden"
            )
        if _assigns_lifespan_context(food_tree):
            errors.append(f"{FOOD_SEARCH_BOOTSTRAP}: lifespan_context mutation is forbidden")
    if lifespan_tree is not None:
        forbidden_names = {"app_module", "legacy_app", "_resolve_app_callable"}
        used_names = {node.id for node in ast.walk(lifespan_tree) if isinstance(node, ast.Name)}
        forbidden_used = sorted(forbidden_names & used_names)
        for name in forbidden_used:
            errors.append(f"{CANONICAL_LIFESPAN}: forbidden legacy dependency lookup: {name}")
        for node in ast.walk(lifespan_tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if _is_facade_module_name(alias.name) and (
                        alias.name not in ALLOWED_CANONICAL_LIFESPAN_APP_IMPORTS
                    ):
                        errors.append(
                            f"{CANONICAL_LIFESPAN}: forbidden facade import: {alias.name}"
                        )
            elif (
                isinstance(node, ast.ImportFrom)
                and node.module is not None
                and _is_facade_module_name(node.module)
                and node.module not in ALLOWED_CANONICAL_LIFESPAN_APP_IMPORTS
            ):
                errors.append(f"{CANONICAL_LIFESPAN}: forbidden facade import: {node.module}")
        if _uses_dynamic_facade_lookup(lifespan_tree):
            errors.append(f"{CANONICAL_LIFESPAN}: dynamic facade lookup is forbidden")
    return sorted(set(errors))


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


def _tracked_app_python_paths(repo_root: Path, errors: list[str]) -> list[Path]:
    app_root = repo_root / "app"
    if not app_root.is_dir():
        errors.append("app: required canonical source root is missing")
        return []

    try:
        paths = sorted(path for path in app_root.rglob("*.py") if path.is_file())
    except OSError as exc:
        errors.append(f"app: unable to enumerate canonical sources: {type(exc).__name__}")
        return []
    return paths


def validate_repo(repo_root: Path) -> list[str]:
    """Validate the repo's legacy compatibility seam."""

    errors: list[str] = []
    legacy_path = repo_root / LEGACY_APP
    doc_path = repo_root / LEGACY_SEAM_DOC
    food_search_path = repo_root / FOOD_SEARCH_BOOTSTRAP
    lifespan_path = repo_root / CANONICAL_LIFESPAN
    legacy_source = _read(legacy_path, repo_root, errors)
    doc_text = _read(doc_path, repo_root, errors)
    food_search_source = _read(food_search_path, repo_root, errors)
    lifespan_source = _read(lifespan_path, repo_root, errors)
    app_sources: dict[str, str] = {}
    for app_path in _tracked_app_python_paths(repo_root, errors):
        source = _read(app_path, repo_root, errors)
        if source is not None:
            app_sources[_display(app_path, repo_root)] = source
    if legacy_source is not None:
        errors.extend(
            validate_legacy_growth(legacy_source, filename=_display(legacy_path, repo_root))
        )
    if doc_text is not None:
        errors.extend(validate_legacy_seam_doc(doc_text, filename=_display(doc_path, repo_root)))
    if legacy_source is not None and food_search_source is not None and lifespan_source is not None:
        errors.extend(
            validate_lifecycle_ownership(
                legacy_source,
                food_search_source,
                lifespan_source,
            )
        )
    if legacy_source is not None:
        errors.extend(validate_api_key_dependency_ownership(legacy_source, app_sources))
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
