#!/usr/bin/env python3
"""Fail-closed guard for legacy_app.py compatibility-seam growth."""

from __future__ import annotations

import argparse
import ast
from collections import Counter
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from importlib.util import resolve_name
from pathlib import Path
import re
import sys
from typing import AbstractSet, cast

REPO_ROOT = Path(__file__).resolve().parents[2]
LEGACY_APP = "legacy_app.py"
LEGACY_SEAM_DOC = "docs/architecture/LEGACY_COMPATIBILITY_SEAM.md"
FOOD_SEARCH_BOOTSTRAP = "app/bootstrap/food_search.py"
CANONICAL_LIFESPAN = "app/bootstrap/lifespan.py"
CANONICAL_API_KEY = "app/routers/api_key.py"  # pragma: allowlist secret
CANONICAL_APPLICATION_METADATA = "app/application_metadata.py"
CANONICAL_OPENAPI = "app/bootstrap/openapi.py"
CANONICAL_MAIN = "app/main.py"
APP_FACADE = "app/__init__.py"
CANONICAL_API_KEY_SYMBOLS = frozenset({"get_api_key", "_get_api_key_dynamic"})
CANONICAL_OPENAPI_SYMBOLS = frozenset(
    {
        "_OPENAPI_ALLOWED_PREFIXES",
        "_OPENAPI_ALLOWED_EXACT",
        "_is_openapi_public_path",
        "_collect_schema_refs",
        "_prune_unreferenced_schema_components",
        "_build_canonical_openapi",
        "_install_openapi_builder",
    }
)
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
    if not is_import_module:
        return None
    module_node = node.args[0] if node.args else None
    package_node = node.args[1] if len(node.args) >= 2 else None
    for keyword in node.keywords:
        if keyword.arg == "name":
            module_node = keyword.value
        elif keyword.arg == "package":
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


def validate_api_key_dependency_ownership(
    legacy_source: str,
    app_sources: Mapping[str, str],
) -> list[str]:
    """Keep client API-key dependency ownership canonical and identity-preserving."""

    errors: list[str] = []
    legacy_tree, parse_errors = _parse_source(legacy_source, filename=LEGACY_APP)
    errors.extend(parse_errors)
    if legacy_tree is not None:
        locally_defined = {
            node.name
            for node in legacy_tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name in CANONICAL_API_KEY_SYMBOLS
        }
        for name in sorted(locally_defined):
            errors.append(f"{LEGACY_APP}: API-key dependency must not be defined locally: {name}")

        exact_aliases: set[str] = set()
        for statement in legacy_tree.body:
            if (
                not isinstance(statement, ast.ImportFrom)
                or statement.module != "app.routers.api_key"
            ):
                continue
            for alias in statement.names:
                if alias.name in CANONICAL_API_KEY_SYMBOLS and alias.asname in {
                    None,
                    alias.name,
                }:
                    exact_aliases.add(alias.name)
        for name in sorted(CANONICAL_API_KEY_SYMBOLS - exact_aliases):
            errors.append(
                f"{LEGACY_APP}: canonical API-key compatibility re-export must preserve "
                f"identity: {name}"
            )

        rebound_names: set[str] = set()

        class _TopLevelBindingVisitor(ast.NodeVisitor):
            def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
                return

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
                return

            def visit_ClassDef(self, node: ast.ClassDef) -> None:
                rebound_names.add(node.name)

            def visit_Lambda(self, node: ast.Lambda) -> None:
                return

            def visit_Name(self, node: ast.Name) -> None:
                if isinstance(node.ctx, ast.Store):
                    rebound_names.add(node.id)

            def visit_Import(self, node: ast.Import) -> None:
                for alias in node.names:
                    rebound_names.add(alias.asname or alias.name.split(".", maxsplit=1)[0])

            def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
                for alias in node.names:
                    bound_name = alias.asname or alias.name
                    if (
                        node.module == "app.routers.api_key"
                        and alias.name in CANONICAL_API_KEY_SYMBOLS
                        and bound_name == alias.name
                    ):
                        continue
                    if alias.name != "*":
                        rebound_names.add(bound_name)

            def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
                if node.name is not None:
                    rebound_names.add(node.name)
                for statement in node.body:
                    self.visit(statement)

        binding_visitor = _TopLevelBindingVisitor()
        for statement in legacy_tree.body:
            binding_visitor.visit(statement)
        for name in sorted(rebound_names & CANONICAL_API_KEY_SYMBOLS):
            errors.append(
                f"{LEGACY_APP}: canonical API-key compatibility re-export must not be "
                f"rebound: {name}"
            )

    for filename, source_text in sorted(app_sources.items()):
        tree, source_errors = _parse_source(source_text, filename=filename)
        errors.extend(source_errors)
        if tree is None:
            continue
        module_aliases: dict[str, str] = {}
        import_module_aliases: set[str] = set()
        static_string_bindings: dict[str, str] = {}
        top_level_assignment_counts: Counter[str] = Counter()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in {"importlib", "legacy_app"}:
                        module_aliases.setdefault(alias.asname or alias.name, alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module == "importlib":
                for alias in node.names:
                    if alias.name == "import_module":
                        import_module_aliases.add(alias.asname or alias.name)

        def record_bounded_lookups(expression: ast.AST) -> None:
            def expression_is_legacy_module(node: ast.AST) -> bool:
                return (
                    _static_module_reference(
                        node,
                        module_aliases=module_aliases,
                        import_module_aliases=import_module_aliases,
                        static_string_bindings=static_string_bindings,
                    )
                    == "legacy_app"
                )

            for lookup_node in ast.walk(expression):
                if (
                    isinstance(lookup_node, ast.Attribute)
                    and lookup_node.attr in CANONICAL_API_KEY_SYMBOLS
                    and expression_is_legacy_module(lookup_node.value)
                ):
                    errors.append(
                        f"{filename}: legacy API-key dependency attribute access is "
                        f"forbidden: {lookup_node.attr}"
                    )
                elif (
                    filename != CANONICAL_API_KEY
                    and isinstance(lookup_node, ast.Call)
                    and isinstance(lookup_node.func, ast.Name)
                    and lookup_node.func.id == "getattr"
                    and len(lookup_node.args) >= 2
                    and expression_is_legacy_module(lookup_node.args[0])
                    and (
                        symbol_name := _resolve_static_string(
                            lookup_node.args[1], static_string_bindings
                        )
                    )
                    in CANONICAL_API_KEY_SYMBOLS
                ):
                    errors.append(
                        f"{filename}: dynamic legacy API-key dependency lookup is forbidden: "
                        f"{symbol_name}"
                    )

        for statement in tree.body:
            if isinstance(statement, ast.Import):
                for alias in statement.names:
                    if alias.name in {"importlib", "legacy_app"}:
                        module_aliases[alias.asname or alias.name] = alias.name
                continue
            if isinstance(statement, ast.ImportFrom) and statement.module == "importlib":
                for alias in statement.names:
                    if alias.name == "import_module":
                        import_module_aliases.add(alias.asname or alias.name)
                continue

            value: ast.AST | None = None
            targets: tuple[ast.expr, ...] = ()
            if isinstance(statement, ast.Assign):
                value = statement.value
                targets = tuple(statement.targets)
            elif isinstance(statement, ast.AnnAssign) and statement.value is not None:
                value = statement.value
                targets = (statement.target,)
            elif isinstance(statement, ast.Expr):
                value = statement.value
            if value is None:
                continue
            record_bounded_lookups(value)
            reference = _static_module_reference(
                value,
                module_aliases=module_aliases,
                import_module_aliases=import_module_aliases,
                static_string_bindings=static_string_bindings,
            )
            static_string = _resolve_static_string(value, static_string_bindings)
            for target in targets:
                for target_name in _assignment_target_names(target):
                    top_level_assignment_counts[target_name] += 1
                    if reference == "legacy_app":
                        module_aliases[target_name] = reference
                    else:
                        module_aliases.pop(target_name, None)
                    if static_string is None:
                        static_string_bindings.pop(target_name, None)
                    else:
                        static_string_bindings[target_name] = static_string

        for target_name, assignment_count in top_level_assignment_counts.items():
            if assignment_count > 1:
                module_aliases.pop(target_name, None)
                static_string_bindings.pop(target_name, None)

        def legacy_module_reference(node: ast.AST) -> bool:
            return (
                _static_module_reference(
                    node,
                    module_aliases=module_aliases,
                    import_module_aliases=import_module_aliases,
                    static_string_bindings=static_string_bindings,
                )
                == "legacy_app"
            )

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "legacy_app":
                for alias in node.names:
                    if alias.name == "*":
                        errors.append(
                            f"{filename}: canonical code must not use a legacy_app star import"
                        )
                    elif alias.name in CANONICAL_API_KEY_SYMBOLS:
                        errors.append(
                            f"{filename}: canonical code must import API-key dependency "
                            f"from {CANONICAL_API_KEY}, not legacy_app: {alias.name}"
                        )
            elif (
                isinstance(node, ast.Attribute)
                and node.attr in CANONICAL_API_KEY_SYMBOLS
                and legacy_module_reference(node.value)
            ):
                errors.append(
                    f"{filename}: legacy API-key dependency attribute access is forbidden: "
                    f"{node.attr}"
                )
            elif (
                filename != CANONICAL_API_KEY
                and isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "getattr"
                and len(node.args) >= 2
                and legacy_module_reference(node.args[0])
                and (symbol_name := _resolve_static_string(node.args[1], static_string_bindings))
                in CANONICAL_API_KEY_SYMBOLS
            ):
                errors.append(
                    f"{filename}: dynamic legacy API-key dependency lookup is forbidden: "
                    f"{symbol_name}"
                )
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


def _assigned_names(tree: ast.Module) -> set[str]:
    names: set[str] = set()

    class _ModuleBindingVisitor(ast.NodeVisitor):
        def _visit_function_header(
            self,
            node: ast.FunctionDef | ast.AsyncFunctionDef,
        ) -> None:
            names.add(node.name)
            for decorator in node.decorator_list:
                self.visit(decorator)
            for default in (*node.args.defaults, *node.args.kw_defaults):
                if default is not None:
                    self.visit(default)
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
            if node.returns is not None:
                self.visit(node.returns)
            for type_param in getattr(node, "type_params", ()):
                self.visit(type_param)

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self._visit_function_header(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            self._visit_function_header(node)

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            names.add(node.name)
            for decorator in node.decorator_list:
                self.visit(decorator)
            for base in node.bases:
                self.visit(base)
            for keyword in node.keywords:
                self.visit(keyword.value)
            for type_param in getattr(node, "type_params", ()):
                self.visit(type_param)

        def visit_Lambda(self, node: ast.Lambda) -> None:
            return

        def visit_ListComp(self, node: ast.ListComp) -> None:
            self._visit_comprehension(node.generators)
            self.visit(node.elt)

        def visit_SetComp(self, node: ast.SetComp) -> None:
            self._visit_comprehension(node.generators)
            self.visit(node.elt)

        def visit_DictComp(self, node: ast.DictComp) -> None:
            self._visit_comprehension(node.generators)
            self.visit(node.key)
            self.visit(node.value)

        def visit_GeneratorExp(self, node: ast.GeneratorExp) -> None:
            self._visit_comprehension(node.generators)
            self.visit(node.elt)

        def _visit_comprehension(self, generators: Sequence[ast.comprehension]) -> None:
            for generator in generators:
                self.visit(generator.iter)
                for condition in generator.ifs:
                    self.visit(condition)

        def visit_Name(self, node: ast.Name) -> None:
            if isinstance(node.ctx, (ast.Store, ast.Del)):
                names.add(node.id)

        def visit_Import(self, node: ast.Import) -> None:
            for alias in node.names:
                names.add(alias.asname or alias.name.split(".", maxsplit=1)[0])

        def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
            for alias in node.names:
                if alias.name == "*":
                    names.update(CANONICAL_OPENAPI_SYMBOLS)
                    continue
                bound_name = alias.asname or alias.name
                if (
                    node.module == "app.bootstrap.openapi"
                    and alias.name in CANONICAL_OPENAPI_SYMBOLS
                    and bound_name == alias.name
                ):
                    continue
                names.add(bound_name)

        def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
            if node.name is not None:
                names.add(node.name)
            for statement in node.body:
                self.visit(statement)

        def visit_MatchAs(self, node: ast.MatchAs) -> None:
            if node.name is not None:
                names.add(node.name)
            if node.pattern is not None:
                self.visit(node.pattern)

        def visit_MatchStar(self, node: ast.MatchStar) -> None:
            if node.name is not None:
                names.add(node.name)

        def visit_MatchMapping(self, node: ast.MatchMapping) -> None:
            if node.rest is not None:
                names.add(node.rest)
            for pattern in node.patterns:
                self.visit(pattern)

    visitor = _ModuleBindingVisitor()
    for statement in tree.body:
        visitor.visit(statement)
    return names


def _static_string(node: ast.AST, bindings: dict[str, str] | None = None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name) and bindings is not None:
        return bindings.get(node.id)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _static_string(node.left, bindings)
        right = _static_string(node.right, bindings)
        if left is not None and right is not None:
            return left + right
    if isinstance(node, ast.JoinedStr):
        joined_parts: list[str] = []
        for value in node.values:
            if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
                return None
            joined_parts.append(value.value)
        return "".join(joined_parts)
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "join"
        and len(node.args) == 1
    ):
        separator = _static_string(node.func.value, bindings)
        values = node.args[0]
        if separator is not None and isinstance(values, (ast.List, ast.Tuple)):
            parts = [_static_string(item, bindings) for item in values.elts]
            if all(part is not None for part in parts):
                return separator.join(cast(str, part) for part in parts)
    return None


def _module_static_string_bindings(tree: ast.Module) -> dict[str, str]:
    bindings: dict[str, str] = {}
    for statement in tree.body:
        if not isinstance(statement, (ast.Assign, ast.AnnAssign)):
            continue
        value = statement.value
        if value is None:
            continue
        resolved = _static_string(value, bindings)
        if resolved is None:
            continue
        targets = statement.targets if isinstance(statement, ast.Assign) else (statement.target,)
        for target in targets:
            if isinstance(target, ast.Name):
                bindings[target.id] = resolved
    return bindings


def _is_namespace_mapping(node: ast.AST) -> bool:
    if isinstance(node, ast.Attribute) and node.attr == "__dict__":
        return True
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in {"globals", "vars"}
    )


def _is_current_module_object_shape(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Subscript)
        and isinstance(node.value, ast.Attribute)
        and node.value.attr == "modules"
        and isinstance(node.slice, ast.Name)
        and node.slice.id == "__name__"
    )


def _binds_namespace_alias(tree: ast.Module) -> bool:
    """Reject namespace-object aliases instead of implementing general data flow."""

    for node in ast.walk(tree):
        value: ast.AST | None = None
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.NamedExpr)):
            value = node.value
        if value is None:
            continue
        if (
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Name)
            and value.func.id in {"globals", "vars"}
        ):
            return True
    return False


def _references_protected_openapi_compat_symbol(tree: ast.Module) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in CANONICAL_OPENAPI_SYMBOLS:
            return True
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and node.value in CANONICAL_OPENAPI_SYMBOLS
        ):
            return True
    return False


_NAMESPACE_KEY_MUTATORS = {
    "__delitem__",
    "__setitem__",
    "pop",
    "setdefault",
}
_NAMESPACE_UNKNOWN_KEY_MUTATORS = {"clear", "popitem"}


def _namespace_mapping_mutation_names(
    node: ast.Call,
    bindings: dict[str, str],
) -> set[str] | None:
    """Return mutated names, or ``None`` when a namespace mutation is unbounded."""

    if not isinstance(node.func, ast.Attribute) or not _is_namespace_mapping(node.func.value):
        return set()
    method = node.func.attr
    if method in _NAMESPACE_UNKNOWN_KEY_MUTATORS:
        return None
    if method in _NAMESPACE_KEY_MUTATORS:
        if not node.args:
            return None
        name = _static_string(node.args[0], bindings)
        return None if name is None else {name}
    if method != "update":
        return set()

    names: set[str] = set()
    for keyword in node.keywords:
        if keyword.arg is None:
            return None
        names.add(keyword.arg)
    for argument in node.args:
        if not isinstance(argument, ast.Dict):
            return None
        for key in argument.keys:
            if key is None:
                return None
            name = _static_string(key, bindings)
            if name is None:
                return None
            names.add(name)
    return names


def _namespace_rebindings(tree: ast.Module, protected_names: set[str]) -> set[str]:
    bindings = _module_static_string_bindings(tree)
    rebound: set[str] = set()
    current_module_aliases: set[str] = set()
    attribute_mutator_aliases: set[str] = {"delattr", "setattr"}

    def same_module_scope_nodes(node: ast.AST) -> Iterator[ast.AST]:
        """Walk a module statement without borrowing names from nested scopes."""

        yield node
        if isinstance(node, (ast.AsyncFunctionDef, ast.ClassDef, ast.FunctionDef, ast.Lambda)):
            return
        for child in ast.iter_child_nodes(node):
            yield from same_module_scope_nodes(child)

    def record_target(target: ast.AST) -> None:
        if (
            isinstance(target, ast.Attribute)
            and _is_current_module_object_shape(target.value)
            and target.attr in protected_names
        ):
            rebound.add(target.attr)
            return
        if not isinstance(target, ast.Subscript) or not _is_namespace_mapping(target.value):
            return
        name = _static_string(target.slice, bindings)
        if name is None:
            rebound.update(protected_names)
        elif name in protected_names:
            rebound.add(name)

    for statement in tree.body:
        for node in same_module_scope_nodes(statement):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
                continue
            if node.func.id not in attribute_mutator_aliases or len(node.args) < 2:
                continue
            if not (
                isinstance(node.args[0], ast.Name) and node.args[0].id in current_module_aliases
            ):
                continue
            attribute_name = _static_string(node.args[1], bindings)
            if attribute_name is None:
                rebound.update(protected_names)
            elif attribute_name in protected_names:
                rebound.add(attribute_name)

        value: ast.AST | None = None
        targets: Sequence[ast.expr] = ()
        if isinstance(statement, ast.Assign):
            value = statement.value
            targets = statement.targets
        elif isinstance(statement, ast.AnnAssign):
            value = statement.value
            targets = (statement.target,)
        if value is not None:
            binds_current_module = _is_current_module_object_shape(value) or (
                isinstance(value, ast.Name) and value.id in current_module_aliases
            )
            binds_attribute_mutator = (
                isinstance(value, ast.Name) and value.id in attribute_mutator_aliases
            )
            for target in targets:
                if not isinstance(target, ast.Name):
                    continue
                if binds_current_module:
                    current_module_aliases.add(target.id)
                else:
                    current_module_aliases.discard(target.id)
                if binds_attribute_mutator:
                    attribute_mutator_aliases.add(target.id)
                else:
                    attribute_mutator_aliases.discard(target.id)

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                record_target(target)
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
            record_target(node.target)
        elif isinstance(node, ast.Delete):
            for target in node.targets:
                record_target(target)
        elif isinstance(node, ast.Call):
            if (
                isinstance(node.func, ast.Name)
                and node.func.id in {"delattr", "setattr"}
                and len(node.args) >= 2
                and _is_current_module_object_shape(node.args[0])
            ):
                attribute_name = _static_string(node.args[1], bindings)
                if attribute_name is None:
                    rebound.update(protected_names)
                elif attribute_name in protected_names:
                    rebound.add(attribute_name)
            mutation_names = _namespace_mapping_mutation_names(node, bindings)
            if mutation_names is None:
                rebound.update(protected_names)
            else:
                rebound.update(mutation_names & protected_names)
    return rebound


def _subscript_attribute_name(
    target: ast.AST,
    bindings: dict[str, str],
) -> str | None:
    if not isinstance(target, ast.Subscript) or not _is_namespace_mapping(target.value):
        return None
    return _static_string(target.slice, bindings)


def _mutates_openapi_callable_or_cache(tree: ast.Module) -> bool:
    bindings = _module_static_string_bindings(tree)
    for node in ast.walk(tree):
        targets: Sequence[ast.expr] = ()
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
            targets = (node.target,)
        elif isinstance(node, ast.Delete):
            targets = node.targets
        for target in targets:
            if isinstance(target, ast.Attribute) and target.attr in {
                "openapi",
                "openapi_schema",
            }:
                return True
            subscript_name = _subscript_attribute_name(target, bindings)
            if subscript_name is None and isinstance(target, ast.Subscript):
                if _is_namespace_mapping(target.value):
                    return True
            if subscript_name in {"openapi", "openapi_schema"}:
                return True
        if not isinstance(node, ast.Call):
            continue
        if (
            (isinstance(node.func, ast.Name) and node.func.id == "setattr")
            or (isinstance(node.func, ast.Attribute) and node.func.attr == "__setattr__")
        ) and len(node.args) >= 2:
            attribute_name = _static_string(node.args[1], bindings)
            if attribute_name in {"openapi", "openapi_schema"}:
                return True
        mutation_names = _namespace_mapping_mutation_names(node, bindings)
        if mutation_names is None or mutation_names & {"openapi", "openapi_schema"}:
            return True
    return False


def _imports_forbidden_openapi_owner(
    tree: ast.Module,
    *,
    current_module: str,
) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import) and any(alias.name == "importlib" for alias in node.names):
            return True
        if isinstance(node, ast.ImportFrom) and node.module == "importlib":
            return True
        if (
            isinstance(node, ast.ImportFrom)
            and node.module == "builtins"
            and any(alias.name == "__import__" for alias in node.names)
        ):
            return True
        if (
            isinstance(node, ast.Name)
            and isinstance(node.ctx, ast.Load)
            and node.id == "__import__"
        ):
            return True
        if isinstance(node, ast.Attribute) and node.attr == "__import__":
            return True
        if _static_string(node) == "__import__":
            return True

    importlib_aliases = {"importlib"}
    import_module_aliases: set[str] = set()
    bindings = _module_static_string_bindings(tree)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "importlib":
                    importlib_aliases.add(alias.asname or alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module == "importlib":
            for alias in node.names:
                if alias.name == "import_module":
                    import_module_aliases.add(alias.asname or alias.name)
    for statement in tree.body:
        if not isinstance(statement, ast.Assign):
            continue
        is_import_module = (
            isinstance(statement.value, ast.Name) and statement.value.id in import_module_aliases
        ) or (
            isinstance(statement.value, ast.Attribute)
            and isinstance(statement.value.value, ast.Name)
            and statement.value.value.id in importlib_aliases
            and statement.value.attr == "import_module"
        )
        if not is_import_module:
            continue
        import_module_aliases.update(
            target.id for target in statement.targets if isinstance(target, ast.Name)
        )

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(alias.name in {"legacy_app", "app.main"} for alias in node.names):
                return True
        elif isinstance(node, ast.ImportFrom):
            if node.module in {"legacy_app", "app.main"} or (
                node.module == "app" and any(alias.name == "main" for alias in node.names)
            ):
                return True
            if node.level:
                package = current_module.rpartition(".")[0]
                relative_module = "." * node.level + (node.module or "")
                try:
                    resolved_module = resolve_name(relative_module, package)
                except (ImportError, ValueError):
                    return True
                if resolved_module == "app.main":
                    return True
                if node.module is None and any(
                    f"{resolved_module}.{alias.name}" == "app.main" for alias in node.names
                ):
                    return True
        elif isinstance(node, ast.Call):
            is_dunder_import = isinstance(node.func, ast.Name) and node.func.id == "__import__"
            is_dynamic_import = (
                is_dunder_import
                or (isinstance(node.func, ast.Name) and node.func.id in import_module_aliases)
                or (
                    isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id in importlib_aliases
                    and node.func.attr == "import_module"
                )
            )
            if not is_dynamic_import:
                continue
            if not node.args:
                return True
            module_name = _static_string(node.args[0], bindings)
            if module_name is None:
                return True
            package_name = _static_string(node.args[1], bindings) if len(node.args) > 1 else None
            if package_name is None:
                package_name = next(
                    (
                        _static_string(keyword.value, bindings)
                        for keyword in node.keywords
                        if keyword.arg == "package"
                    ),
                    None,
                )
            if module_name in {"legacy_app", "app.main"}:
                return True
            if is_dunder_import:
                fromlist_node: ast.expr | None = None
                if len(node.args) > 3:
                    fromlist_node = node.args[3]
                else:
                    for keyword in node.keywords:
                        if keyword.arg == "fromlist":
                            fromlist_node = keyword.value
                            break
                if fromlist_node is not None:
                    if not isinstance(fromlist_node, (ast.List, ast.Tuple, ast.Set)):
                        if module_name == "app":
                            return True
                    else:
                        fromlist_names = [
                            _static_string(item, bindings) for item in fromlist_node.elts
                        ]
                        if any(name is None for name in fromlist_names):
                            if module_name == "app":
                                return True
                        elif any(f"{module_name}.{name}" == "app.main" for name in fromlist_names):
                            return True
            if module_name.startswith("."):
                if package_name is None:
                    return True
                try:
                    resolved_module = resolve_name(module_name, package_name)
                except (ImportError, ValueError):
                    return True
                if resolved_module == "app.main":
                    return True
    return False


def _references_legacy_openapi_installer(tree: ast.Module) -> bool:
    installer_name = "_install_openapi_builder"
    bindings = _module_static_string_bindings(tree)
    for node in ast.walk(tree):
        if _static_string(node) == installer_name:
            return True
        if isinstance(node, ast.Name) and node.id == installer_name:
            return True
        if isinstance(node, ast.Attribute) and node.attr == installer_name:
            return True
        if isinstance(node, ast.ImportFrom) and any(
            alias.name == installer_name for alias in node.names
        ):
            return True
        if isinstance(node, ast.Subscript) and _is_namespace_mapping(node.value):
            name = _static_string(node.slice, bindings)
            if name is None or name == installer_name:
                return True
        if not isinstance(node, ast.Call):
            continue
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr in {"get", "__getitem__"}
            and _is_namespace_mapping(node.func.value)
        ):
            if not node.args:
                return True
            name = _static_string(node.args[0], bindings)
            if name is None or name == installer_name:
                return True
            continue
        if not isinstance(node.func, ast.Name) or node.func.id != "getattr":
            continue
        if len(node.args) >= 2:
            name = _static_string(node.args[1], bindings)
            if name == installer_name:
                return True
    return False


def _function_references_legacy_openapi_symbol(tree: ast.Module) -> bool:
    for function in ast.walk(tree):
        if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for node in ast.walk(function):
            if _static_string(node) in CANONICAL_OPENAPI_SYMBOLS:
                return True
            if isinstance(node, ast.Name) and node.id in CANONICAL_OPENAPI_SYMBOLS:
                return True
            if isinstance(node, ast.Attribute) and node.attr in CANONICAL_OPENAPI_SYMBOLS:
                return True
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and node.value in CANONICAL_OPENAPI_SYMBOLS
            ):
                return True
    return False


def _parses_environment_directly(tree: ast.Module) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import) and any(alias.name == "os" for alias in node.names):
            return True
        if isinstance(node, ast.ImportFrom) and node.module == "os":
            return True
        if isinstance(node, ast.Attribute) and node.attr in {"getenv", "environ"}:
            return True
    return False


def validate_application_metadata_openapi_ownership(
    legacy_source: str,
    metadata_source: str,
    openapi_source: str,
    main_source: str,
    facade_source: str,
) -> list[str]:
    """Keep metadata and OpenAPI implementation in their canonical modules."""

    sources = {
        LEGACY_APP: legacy_source,
        CANONICAL_APPLICATION_METADATA: metadata_source,
        CANONICAL_OPENAPI: openapi_source,
        CANONICAL_MAIN: main_source,
        APP_FACADE: facade_source,
    }
    trees: dict[str, ast.Module] = {}
    errors: list[str] = []
    for filename, source in sources.items():
        tree, parse_errors = _parse_source(source, filename=filename)
        errors.extend(parse_errors)
        if tree is not None:
            trees[filename] = tree
    if errors:
        return sorted(set(errors))

    legacy_tree = trees[LEGACY_APP]
    local_openapi_defs = {
        node.name
        for node in legacy_tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name in CANONICAL_OPENAPI_SYMBOLS
    }
    for name in sorted(local_openapi_defs):
        errors.append(f"{LEGACY_APP}: OpenAPI implementation must be canonical: {name}")

    exact_aliases: set[str] = set()
    foreign_import_rebindings: set[str] = set()
    metadata_factory_imported = False
    for statement in legacy_tree.body:
        if isinstance(statement, ast.ImportFrom) and statement.module == CANONICAL_OPENAPI.replace(
            "/", "."
        ).removesuffix(".py"):
            for alias in statement.names:
                if alias.name in CANONICAL_OPENAPI_SYMBOLS and alias.asname in {
                    None,
                    alias.name,
                }:
                    exact_aliases.add(alias.name)
        elif isinstance(statement, ast.ImportFrom):
            for alias in statement.names:
                bound_name = alias.asname or alias.name
                if bound_name in CANONICAL_OPENAPI_SYMBOLS:
                    foreign_import_rebindings.add(bound_name)
        elif isinstance(statement, ast.Import):
            for alias in statement.names:
                bound_name = alias.asname or alias.name.split(".", 1)[0]
                if bound_name in CANONICAL_OPENAPI_SYMBOLS:
                    foreign_import_rebindings.add(bound_name)
        if (
            isinstance(statement, ast.ImportFrom)
            and statement.module == "app.application_metadata"
            and any(
                alias.name == "build_application_metadata"
                and alias.asname in {None, "build_application_metadata"}
                for alias in statement.names
            )
        ):
            metadata_factory_imported = True
    for name in sorted(CANONICAL_OPENAPI_SYMBOLS - exact_aliases):
        errors.append(
            f"{LEGACY_APP}: canonical OpenAPI compatibility re-export must preserve identity: {name}"
        )
    explicit_globals = {
        name
        for node in ast.walk(legacy_tree)
        if isinstance(node, ast.Global)
        for name in node.names
    }
    rebound = (
        ((_assigned_names(legacy_tree) | explicit_globals) & CANONICAL_OPENAPI_SYMBOLS)
        | foreign_import_rebindings
        | _namespace_rebindings(
            legacy_tree,
            set(CANONICAL_OPENAPI_SYMBOLS),
        )
    )
    if _binds_namespace_alias(legacy_tree) or _references_protected_openapi_compat_symbol(
        legacy_tree
    ):
        rebound.update(CANONICAL_OPENAPI_SYMBOLS)
    for name in sorted(rebound):
        errors.append(f"{LEGACY_APP}: canonical OpenAPI re-export must not be rebound: {name}")
    if not metadata_factory_imported:
        errors.append(f"{LEGACY_APP}: canonical application metadata factory import is required")
    if _mutates_openapi_callable_or_cache(legacy_tree):
        errors.append(f"{LEGACY_APP}: OpenAPI callable/cache mutation is forbidden")

    metadata_tree = trees[CANONICAL_APPLICATION_METADATA]
    openapi_tree = trees[CANONICAL_OPENAPI]
    for filename, tree in (
        (CANONICAL_APPLICATION_METADATA, metadata_tree),
        (CANONICAL_OPENAPI, openapi_tree),
    ):
        current_module = filename.replace("/", ".").removesuffix(".py")
        if _imports_forbidden_openapi_owner(tree, current_module=current_module):
            errors.append(f"{filename}: reverse legacy/main import is forbidden")
    if _parses_environment_directly(metadata_tree):
        errors.append(f"{CANONICAL_APPLICATION_METADATA}: direct environment parsing is forbidden")

    main_tree = trees[CANONICAL_MAIN]
    main_imports = {
        alias.name
        for node in main_tree.body
        if isinstance(node, ast.ImportFrom) and node.module == "app.bootstrap.openapi"
        for alias in node.names
    }
    required_main_imports = {
        "validate_openapi_builder_state",
        "apply_public_openapi_input_policy",
        "install_canonical_openapi_builder",
    }
    for name in sorted(required_main_imports - main_imports):
        errors.append(f"{CANONICAL_MAIN}: canonical OpenAPI import is required: {name}")
    for node in main_tree.body:
        if not isinstance(node, ast.ImportFrom) or node.module != "legacy_app":
            continue
        for alias in node.names:
            if "openapi" in alias.name.casefold():
                errors.append(
                    f"{CANONICAL_MAIN}: OpenAPI symbol must not be imported through legacy: "
                    f"{alias.name}"
                )
    main_module_aliases: dict[str, str] = {}
    main_import_module_aliases: set[str] = set()
    main_string_bindings: dict[str, str] = {}

    def record_main_legacy_openapi_lookups(expression: ast.AST) -> None:
        def is_legacy_module(node: ast.AST) -> bool:
            return (
                _static_module_reference(
                    node,
                    module_aliases=main_module_aliases,
                    import_module_aliases=main_import_module_aliases,
                    static_string_bindings=main_string_bindings,
                )
                == "legacy_app"
            )

        for walk_node in ast.walk(expression):
            if (
                isinstance(walk_node, ast.Attribute)
                and is_legacy_module(walk_node.value)
                and "openapi" in walk_node.attr.casefold()
            ):
                errors.append(
                    f"{CANONICAL_MAIN}: OpenAPI symbol must not be accessed through legacy: "
                    f"{walk_node.attr}"
                )
            elif (
                isinstance(walk_node, ast.Call)
                and isinstance(walk_node.func, ast.Name)
                and walk_node.func.id == "getattr"
                and len(walk_node.args) >= 2
                and is_legacy_module(walk_node.args[0])
            ):
                attribute_name = _static_string(walk_node.args[1], main_string_bindings)
                if attribute_name is not None and "openapi" in attribute_name.casefold():
                    errors.append(
                        f"{CANONICAL_MAIN}: OpenAPI symbol must not be accessed through legacy"
                    )

    for statement in main_tree.body:
        record_main_legacy_openapi_lookups(statement)
        if isinstance(statement, ast.Import):
            for alias in statement.names:
                bound_name = alias.asname or alias.name.split(".", maxsplit=1)[0]
                if alias.name in {"importlib", "legacy_app"}:
                    main_module_aliases[bound_name] = alias.name
                else:
                    main_module_aliases.pop(bound_name, None)
            continue
        if isinstance(statement, ast.ImportFrom):
            for alias in statement.names:
                bound_name = alias.asname or alias.name
                main_module_aliases.pop(bound_name, None)
                if statement.module == "importlib" and alias.name == "import_module":
                    main_import_module_aliases.add(bound_name)
            continue

        value: ast.AST | None = None
        targets: Sequence[ast.expr] = ()
        if isinstance(statement, ast.Assign):
            value = statement.value
            targets = statement.targets
        elif isinstance(statement, ast.AnnAssign):
            value = statement.value
            targets = (statement.target,)
        if value is None:
            continue
        reference = _static_module_reference(
            value,
            module_aliases=main_module_aliases,
            import_module_aliases=main_import_module_aliases,
            static_string_bindings=main_string_bindings,
        )
        static_string = _static_string(value, main_string_bindings)
        for target in targets:
            for target_name in _assignment_target_names(target):
                if reference == "legacy_app":
                    main_module_aliases[target_name] = reference
                else:
                    main_module_aliases.pop(target_name, None)
                if static_string is None:
                    main_string_bindings.pop(target_name, None)
                else:
                    main_string_bindings[target_name] = static_string

    if _function_references_legacy_openapi_symbol(main_tree):
        errors.append(f"{CANONICAL_MAIN}: OpenAPI symbol must not be accessed through legacy")

    facade_tree = trees[APP_FACADE]
    facade_binds_namespace_alias = _binds_namespace_alias(facade_tree)
    if _mutates_openapi_callable_or_cache(facade_tree) or facade_binds_namespace_alias:
        errors.append(f"{APP_FACADE}: OpenAPI callable/cache mutation is forbidden")
    if _references_legacy_openapi_installer(facade_tree) or facade_binds_namespace_alias:
        errors.append(f"{APP_FACADE}: legacy OpenAPI installer lookup is forbidden")

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


def validate_repo(repo_root: Path) -> list[str]:
    """Validate the repo's legacy compatibility seam."""

    errors: list[str] = []
    legacy_path = repo_root / LEGACY_APP
    doc_path = repo_root / LEGACY_SEAM_DOC
    food_search_path = repo_root / FOOD_SEARCH_BOOTSTRAP
    lifespan_path = repo_root / CANONICAL_LIFESPAN
    metadata_path = repo_root / CANONICAL_APPLICATION_METADATA
    openapi_path = repo_root / CANONICAL_OPENAPI
    main_path = repo_root / CANONICAL_MAIN
    facade_path = repo_root / APP_FACADE
    legacy_source = _read(legacy_path, repo_root, errors)
    doc_text = _read(doc_path, repo_root, errors)
    food_search_source = _read(food_search_path, repo_root, errors)
    lifespan_source = _read(lifespan_path, repo_root, errors)
    metadata_source = _read(metadata_path, repo_root, errors)
    openapi_source = _read(openapi_path, repo_root, errors)
    main_source = _read(main_path, repo_root, errors)
    facade_source = _read(facade_path, repo_root, errors)
    app_sources: dict[str, str] = {}
    app_root = repo_root / "app"
    if not app_root.is_dir():
        errors.append("app: canonical source scan root is missing")
    else:
        for app_path in sorted(app_root.rglob("*.py")):
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
    if all(
        source is not None
        for source in (
            legacy_source,
            metadata_source,
            openapi_source,
            main_source,
            facade_source,
        )
    ):
        errors.extend(
            validate_application_metadata_openapi_ownership(
                cast(str, legacy_source),
                cast(str, metadata_source),
                cast(str, openapi_source),
                cast(str, main_source),
                cast(str, facade_source),
            )
        )
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
