#!/usr/bin/env python3
"""Fail-closed guard for legacy_app.py compatibility-seam growth."""

from __future__ import annotations

import argparse
import ast
import copy
from collections import Counter
from collections.abc import Callable, Iterator, Mapping, Sequence
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
    methods: AbstractSet[str],
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


def _getattr_app_call_action(
    func: ast.AST,
    methods: AbstractSet[str],
    *,
    app_aliases: frozenset[str],
    router_aliases: frozenset[str],
    static_string_bindings: Mapping[str, str] | None = None,
) -> str | None:
    if not isinstance(func, ast.Call) or not func.args:
        return None
    target = func.args[0]
    target_prefix: str | None = None
    if isinstance(target, ast.Name) and target.id in app_aliases:
        target_prefix = ""
    elif isinstance(target, ast.Name) and target.id in router_aliases:
        target_prefix = "router."
    elif (
        isinstance(target, ast.Attribute)
        and target.attr == "router"
        and isinstance(target.value, ast.Name)
        and target.value.id in app_aliases
    ):
        target_prefix = "router."
    if target_prefix is None:
        return None

    method = _getattr_method_name(
        func,
        methods,
        static_string_bindings=static_string_bindings,
    )
    if method is not None:
        return f"{target_prefix}{method}"
    if _is_unresolved_getattr_method(func, static_string_bindings=static_string_bindings):
        return f"{target_prefix}dynamic"
    return None


def collect_legacy_route_facts(source_text: str, *, filename: str = LEGACY_APP) -> set[LegacyFact]:
    """Return route and router-registration facts from legacy_app.py source."""

    tree, errors = _parse_source(source_text, filename=filename)
    if errors or tree is None:
        return set()

    facts: set[LegacyFact] = set()
    static_string_bindings = _collect_static_string_bindings(tree)
    (
        route_reference_snapshots,
        route_string_snapshots,
        route_call_result_snapshots,
    ) = _collect_lexical_binding_snapshots(
        tree,
        initial_references={
            "app": "pulseplate.app",
            "FastAPI": "fastapi.FastAPI",
            "getattr": "builtins.getattr",
        },
        preserve_route_method_conflicts=True,
    )

    def scoped_route_bindings(
        node: ast.AST,
    ) -> tuple[frozenset[str], frozenset[str], Mapping[str, str]]:
        references = route_reference_snapshots.get(id(node), {})
        scoped_app_aliases = frozenset(
            name
            for name, reference in references.items()
            if reference in {"pulseplate.app", _POSSIBLE_APP_REFERENCE}
        )
        scoped_router_aliases = frozenset(
            name
            for name, reference in references.items()
            if reference in {"pulseplate.app.router", _POSSIBLE_ROUTER_REFERENCE}
        )
        return (
            scoped_app_aliases,
            scoped_router_aliases,
            route_string_snapshots.get(id(node), static_string_bindings),
        )

    def scoped_call_action(
        node: ast.AST,
        func: ast.AST,
        methods: AbstractSet[str],
    ) -> str | None:
        call_result = route_call_result_snapshots.get(id(func))
        if call_result is not None:
            action = _registration_action_for_reference(call_result.reference, methods)
            if action is not None:
                return action
        if isinstance(func, ast.Attribute):
            owner_result = route_call_result_snapshots.get(id(func.value))
            if owner_result is not None and func.attr in methods:
                if owner_result.reference == "pulseplate.app":
                    return func.attr
                if owner_result.reference == "pulseplate.app.router":
                    return f"router.{func.attr}"
                if owner_result.reference in {
                    _POSSIBLE_APP_REFERENCE,
                    _POSSIBLE_ROUTER_REFERENCE,
                }:
                    return "dynamic"
        node_id = id(node)
        if node_id not in route_reference_snapshots:
            return None
        references = route_reference_snapshots[node_id]
        strings = route_string_snapshots[node_id]
        scoped_app_aliases, scoped_router_aliases, _scoped_strings = scoped_route_bindings(node)
        if not isinstance(func, (ast.Name, ast.Call)):
            direct_action = _app_call_action(
                func,
                methods,
                app_aliases=scoped_app_aliases,
                router_aliases=scoped_router_aliases,
                static_string_bindings=strings,
            )
            if direct_action is not None:
                return direct_action
            if (
                isinstance(func, ast.Attribute)
                and func.attr in APP_ROUTE_METHODS | APP_REGISTRATION_METHODS
            ):
                return None
        reference = _static_module_reference(
            func,
            module_aliases=references,
            import_module_aliases=frozenset(),
            static_string_bindings=strings,
        )
        action = _registration_action_for_reference(reference, methods)
        if action is not None:
            return action
        if not isinstance(func, (ast.Name, ast.Call)):
            return None
        if isinstance(func, ast.Name):
            return None
        lookup_reference = _static_module_reference(
            func.func,
            module_aliases=references,
            import_module_aliases=frozenset(),
            static_string_bindings=strings,
        )
        if lookup_reference not in {"builtins.getattr", _POSSIBLE_GETATTR_REFERENCE}:
            return None
        if len(func.args) < 2:
            return None
        target_reference = _static_module_reference(
            func.args[0],
            module_aliases=references,
            import_module_aliases=frozenset(),
            static_string_bindings=strings,
        )
        if target_reference in {"pulseplate.app", _POSSIBLE_APP_REFERENCE}:
            action_prefix = ""
        elif target_reference in {
            "pulseplate.app.router",
            _POSSIBLE_ROUTER_REFERENCE,
        }:
            action_prefix = "router."
        else:
            return None
        resolved_method = _resolve_static_string(func.args[1], strings)
        if resolved_method in methods:
            return f"{action_prefix}{resolved_method}"
        if resolved_method in {
            None,
            _DYNAMIC_STRING_BINDING,
            _POSSIBLE_ROUTE_METHOD,
            _CONFLICTED_ROUTE_METHOD,
        }:
            return f"{action_prefix}dynamic"
        return None

    def scoped_middleware_target(node: ast.AST, name: str) -> str | None:
        references = route_reference_snapshots.get(id(node))
        if references is None:
            return None
        reference = references.get(name)
        if reference == _POSSIBLE_MIDDLEWARE_DECORATOR_REFERENCE:
            return "<dynamic>"
        if reference is not None and reference.startswith(_MIDDLEWARE_DECORATOR_REFERENCE_PREFIX):
            return reference.removeprefix(_MIDDLEWARE_DECORATOR_REFERENCE_PREFIX)
        return None

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for decorator in node.decorator_list:
                if id(decorator) not in route_reference_snapshots:
                    continue
                scoped_app_aliases, scoped_router_aliases, scoped_strings = scoped_route_bindings(
                    decorator
                )
                if isinstance(decorator, ast.Name):
                    target = scoped_middleware_target(decorator, decorator.id)
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
                action = scoped_call_action(
                    decorator,
                    decorator.func,
                    APP_ROUTE_METHODS,
                )
                if action is not None:
                    facts.add(
                        LegacyFact("decorator", action, _first_arg_label(decorator), node.name)
                    )
        elif isinstance(node, ast.Call):
            call = node
            if id(call) not in route_reference_snapshots:
                continue
            scoped_app_aliases, scoped_router_aliases, scoped_strings = scoped_route_bindings(call)
            if isinstance(call.func, ast.Call):
                returned_action = scoped_call_action(
                    call,
                    call.func,
                    APP_ROUTE_METHODS,
                )
                if returned_action is not None:
                    facts.add(
                        LegacyFact(
                            "registration",
                            returned_action,
                            _first_arg_label(call),
                            "",
                        )
                    )
                action = scoped_call_action(
                    call,
                    call.func.func,
                    APP_ROUTE_METHODS,
                )
                if action is not None:
                    facts.add(
                        LegacyFact(
                            "registration",
                            action,
                            _first_arg_label(call.func),
                            "",
                        )
                    )
                returned_binding = route_call_result_snapshots.get(id(call.func))
                if returned_binding is not None:
                    middleware_reference = returned_binding.reference
                    if middleware_reference == _POSSIBLE_MIDDLEWARE_DECORATOR_REFERENCE:
                        middleware_target = "<dynamic>"
                    elif middleware_reference is not None and middleware_reference.startswith(
                        _MIDDLEWARE_DECORATOR_REFERENCE_PREFIX
                    ):
                        middleware_target = middleware_reference.removeprefix(
                            _MIDDLEWARE_DECORATOR_REFERENCE_PREFIX
                        )
                    else:
                        middleware_target = None
                    if middleware_target is not None:
                        facts.add(
                            LegacyFact(
                                "registration",
                                "middleware",
                                middleware_target,
                                "",
                            )
                        )
            action = scoped_call_action(
                call,
                call.func,
                APP_REGISTRATION_METHODS,
            )
            if isinstance(call.func, ast.Name):
                middleware_target = scoped_middleware_target(call, call.func.id)
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


def _is_registration_callable_reference(reference: str | None) -> bool:
    if reference in {
        _POSSIBLE_APP_CALL_REFERENCE,
        _POSSIBLE_MIDDLEWARE_DECORATOR_REFERENCE,
    }:
        return True
    if reference is None:
        return False
    if reference.startswith(_MIDDLEWARE_DECORATOR_REFERENCE_PREFIX):
        return True
    return reference.startswith("pulseplate.app.") and (
        reference.rsplit(".", maxsplit=1)[-1] in APP_ROUTE_METHODS | APP_REGISTRATION_METHODS
    )


def _registration_action_for_reference(
    reference: str | None,
    methods: AbstractSet[str],
) -> str | None:
    if reference == _POSSIBLE_APP_CALL_REFERENCE:
        return "dynamic"
    for prefix, action_prefix in (
        ("pulseplate.app.router.", "router."),
        ("pulseplate.app.", ""),
    ):
        if reference is not None and reference.startswith(prefix):
            method = reference.removeprefix(prefix)
            if method in methods:
                return f"{action_prefix}{method}"
    return None


_UNRESOLVED_LITERAL_VALUE = object()


def _literal_value(node: ast.AST) -> object:
    try:
        return ast.literal_eval(node)
    except (TypeError, ValueError):
        return _UNRESOLVED_LITERAL_VALUE


def _literal_subscript_value(
    node: ast.Subscript,
) -> tuple[ast.AST | None, bool]:
    key = _literal_value(node.slice)
    if key is _UNRESOLVED_LITERAL_VALUE:
        return None, False
    if isinstance(node.value, (ast.List, ast.Tuple)):
        if not isinstance(key, int) or isinstance(key, bool):
            return None, False
        try:
            selected = node.value.elts[key]
        except IndexError:
            return None, False
        return (
            selected.value if isinstance(selected, ast.Starred) else selected,
            False,
        )
    if isinstance(node.value, ast.Dict):
        later_entry_may_override = False
        items = list(zip(node.value.keys, node.value.values, strict=True))
        for candidate_key, candidate_value in reversed(items):
            if candidate_key is None:
                later_entry_may_override = True
                continue
            candidate = _literal_value(candidate_key)
            if candidate is _UNRESOLVED_LITERAL_VALUE:
                later_entry_may_override = True
                continue
            if candidate == key:
                return (None, True) if later_entry_may_override else (candidate_value, False)
        if later_entry_may_override:
            return None, True
    return None, False


def _collection_reference(
    references: Sequence[str | None],
    *,
    mapping: bool,
) -> str | None:
    if any(
        reference
        in {
            "pulseplate.app",
            "pulseplate.app.router",
            _POSSIBLE_APP_REFERENCE,
            _POSSIBLE_ROUTER_REFERENCE,
        }
        for reference in references
    ):
        return _MAPPING_APP_VALUE_REFERENCE if mapping else _ITERABLE_APP_ELEMENT_REFERENCE
    if any(_is_registration_callable_reference(reference) for reference in references):
        return (
            _MAPPING_SENSITIVE_VALUE_REFERENCE if mapping else _ITERABLE_SENSITIVE_ELEMENT_REFERENCE
        )
    if references and all(reference == _KNOWN_NON_APP_REFERENCE for reference in references):
        return _KNOWN_NON_APP_REFERENCE
    return None


def _unpacked_mapping_reference(
    key: ast.expr | None,
    reference: str | None,
) -> str | None:
    if key is not None:
        return reference
    if reference == _MAPPING_APP_VALUE_REFERENCE:
        return _POSSIBLE_APP_REFERENCE
    if reference == _MAPPING_SENSITIVE_VALUE_REFERENCE:
        return _POSSIBLE_APP_CALL_REFERENCE
    return reference


def _collection_element_reference(
    node: ast.AST,
    *,
    module_aliases: Mapping[str, str],
    import_module_aliases: AbstractSet[str],
    static_string_bindings: Mapping[str, str],
) -> str | None:
    reference = _static_module_reference(
        node,
        module_aliases=module_aliases,
        import_module_aliases=import_module_aliases,
        static_string_bindings=static_string_bindings,
    )
    if reference is None and isinstance(node, (ast.Constant, ast.JoinedStr)):
        return _KNOWN_NON_APP_REFERENCE
    return reference


def _static_module_reference(
    node: ast.AST,
    *,
    module_aliases: Mapping[str, str],
    import_module_aliases: AbstractSet[str],
    static_string_bindings: Mapping[str, str],
) -> str | None:
    if isinstance(node, ast.NamedExpr):
        return _static_module_reference(
            node.value,
            module_aliases=module_aliases,
            import_module_aliases=import_module_aliases,
            static_string_bindings=static_string_bindings,
        )
    if isinstance(node, ast.Name):
        return module_aliases.get(node.id)
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return _collection_reference(
            [
                _collection_element_reference(
                    element.value if isinstance(element, ast.Starred) else element,
                    module_aliases=module_aliases,
                    import_module_aliases=import_module_aliases,
                    static_string_bindings=static_string_bindings,
                )
                for element in node.elts
            ],
            mapping=False,
        )
    if isinstance(node, ast.Dict):
        return _collection_reference(
            [
                _unpacked_mapping_reference(
                    key,
                    _collection_element_reference(
                        value,
                        module_aliases=module_aliases,
                        import_module_aliases=import_module_aliases,
                        static_string_bindings=static_string_bindings,
                    ),
                )
                for key, value in zip(node.keys, node.values, strict=True)
            ],
            mapping=True,
        )
    if isinstance(node, ast.Attribute):
        parent = _static_module_reference(
            node.value,
            module_aliases=module_aliases,
            import_module_aliases=import_module_aliases,
            static_string_bindings=static_string_bindings,
        )
        if parent == _KNOWN_NON_APP_REFERENCE:
            return None
        if node.attr == "__call__" and _is_registration_callable_reference(parent):
            return parent
        if parent == _POSSIBLE_APP_REFERENCE:
            if node.attr == "router":
                return _POSSIBLE_ROUTER_REFERENCE
            if node.attr in APP_ROUTE_METHODS | APP_REGISTRATION_METHODS:
                return _POSSIBLE_APP_CALL_REFERENCE
            return None
        if parent == _POSSIBLE_ROUTER_REFERENCE:
            if node.attr in APP_ROUTE_METHODS | APP_REGISTRATION_METHODS:
                return _POSSIBLE_APP_CALL_REFERENCE
            return None
        if parent is not None:
            return f"{parent}.{node.attr}"
        return None
    if isinstance(node, ast.Subscript):
        selected, unresolved = _literal_subscript_value(node)
        if selected is not None:
            return _static_module_reference(
                selected,
                module_aliases=module_aliases,
                import_module_aliases=import_module_aliases,
                static_string_bindings=static_string_bindings,
            )
        parent = _static_module_reference(
            node.value,
            module_aliases=module_aliases,
            import_module_aliases=import_module_aliases,
            static_string_bindings=static_string_bindings,
        )
        if parent in {
            _POSSIBLE_APP_CALL_REFERENCE,
            _POSSIBLE_MIDDLEWARE_DECORATOR_REFERENCE,
            _ITERABLE_SENSITIVE_ELEMENT_REFERENCE,
            _MAPPING_SENSITIVE_VALUE_REFERENCE,
        }:
            return _POSSIBLE_APP_CALL_REFERENCE
        if parent in {
            _ITERABLE_APP_ELEMENT_REFERENCE,
            _MAPPING_APP_VALUE_REFERENCE,
        }:
            return _POSSIBLE_APP_REFERENCE
        if parent == _KNOWN_NON_APP_REFERENCE:
            return _KNOWN_NON_APP_REFERENCE
        if unresolved:
            return _POSSIBLE_APP_CALL_REFERENCE
        return None
    if not isinstance(node, ast.Call):
        return None

    callable_reference = _static_module_reference(
        node.func,
        module_aliases=module_aliases,
        import_module_aliases=import_module_aliases,
        static_string_bindings=static_string_bindings,
    )
    if callable_reference == "functools.partial" and node.args:
        wrapped_reference = _static_module_reference(
            node.args[0],
            module_aliases=module_aliases,
            import_module_aliases=import_module_aliases,
            static_string_bindings=static_string_bindings,
        )
        if _is_registration_callable_reference(wrapped_reference):
            return wrapped_reference

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
    """Count module bindings without leaking nested lexical stores."""

    counts: Counter[str] = Counter()

    class _ModuleBindingVisitor(ast.NodeVisitor):
        def visit_Name(self, node: ast.Name) -> None:
            if isinstance(node.ctx, (ast.Store, ast.Del)):
                counts[node.id] += 1

        def _visit_function_header(
            self,
            node: ast.FunctionDef | ast.AsyncFunctionDef,
        ) -> None:
            counts[node.name] += 1
            for decorator in node.decorator_list:
                self.visit(decorator)
            for default in (*node.args.defaults, *node.args.kw_defaults):
                if default is not None:
                    self.visit(default)
            if node.returns is not None:
                self.visit(node.returns)

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self._visit_function_header(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            self._visit_function_header(node)

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            counts[node.name] += 1
            for decorator in node.decorator_list:
                self.visit(decorator)
            for base in node.bases:
                self.visit(base)
            for keyword in node.keywords:
                self.visit(keyword.value)

        def visit_Lambda(self, node: ast.Lambda) -> None:
            return

        def visit_Import(self, node: ast.Import) -> None:
            for alias in node.names:
                counts[alias.asname or alias.name.split(".", maxsplit=1)[0]] += 1

        def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
            for alias in node.names:
                counts[alias.asname or alias.name] += 1

        def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
            if node.name is not None:
                counts[node.name] += 1
            for statement in node.body:
                self.visit(statement)

    for statement in tree.body:
        _ModuleBindingVisitor().visit(statement)
    return counts


def _resolve_static_string(node: ast.AST, bindings: Mapping[str, str]) -> str | None:
    if isinstance(node, ast.NamedExpr):
        return _resolve_static_string(node.value, bindings)
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


def _is_unresolved_getattr_method(
    func: ast.Call,
    *,
    static_string_bindings: Mapping[str, str] | None = None,
) -> bool:
    if not isinstance(func.func, ast.Name) or func.func.id != "getattr":
        return False
    if len(func.args) < 2:
        return False
    return _resolve_static_string(func.args[1], static_string_bindings or {}) in {
        None,
        _POSSIBLE_ROUTE_METHOD,
        _CONFLICTED_ROUTE_METHOD,
        _DYNAMIC_STRING_BINDING,
    }


def _assignment_target_names(node: ast.AST) -> tuple[str, ...]:
    if isinstance(node, ast.Name):
        return (node.id,)
    if isinstance(node, ast.Starred):
        return _assignment_target_names(node.value)
    if isinstance(node, (ast.Tuple, ast.List)):
        names: list[str] = []
        for element in node.elts:
            names.extend(_assignment_target_names(element))
        return tuple(names)
    return ()


def _assignment_target_escapes_value(node: ast.AST) -> bool:
    if isinstance(node, (ast.Attribute, ast.Subscript)):
        return True
    if isinstance(node, ast.Starred):
        return _assignment_target_escapes_value(node.value)
    if isinstance(node, (ast.Tuple, ast.List)):
        return any(_assignment_target_escapes_value(element) for element in node.elts)
    return False


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


_MAX_ITERABLE_ELEMENT_BINDING_DEPTH = 8

_FunctionNode = ast.FunctionDef | ast.AsyncFunctionDef
_DescriptorBinding = tuple[_FunctionNode, str]


@dataclass(frozen=True)
class _DeferredFunctionCall:
    function: _FunctionNode
    arguments: tuple[tuple[str, _ResolvedBinding], ...]
    partial_template: bool = False
    partial_positional: tuple[_ResolvedBinding, ...] = ()
    partial_unresolved: bool = False


@dataclass(frozen=True)
class _ResolvedBinding:
    reference: str | None
    string: str | None
    callables: frozenset[_FunctionNode] = frozenset()
    deferred_calls: frozenset[_DeferredFunctionCall] = frozenset()
    mapping: _StaticMapping | None = None
    class_references: frozenset[str] = frozenset()
    descriptors: frozenset[_DescriptorBinding] = frozenset()
    iterable_element: _ResolvedBinding | None = None


def _normalize_resolved_binding(
    binding: _ResolvedBinding,
    *,
    remaining_depth: int = _MAX_ITERABLE_ELEMENT_BINDING_DEPTH,
) -> _ResolvedBinding:
    """Bound recursive provenance without turning overflow into a false-safe value."""

    nested = binding.iterable_element
    if nested is None:
        return binding
    normalized_nested = (
        _ResolvedBinding(
            reference=_POSSIBLE_APP_CALL_REFERENCE,
            string=_DYNAMIC_STRING_BINDING,
        )
        if remaining_depth <= 0
        else _normalize_resolved_binding(
            nested,
            remaining_depth=remaining_depth - 1,
        )
    )
    if normalized_nested == nested:
        return binding
    return _ResolvedBinding(
        reference=binding.reference,
        string=binding.string,
        callables=binding.callables,
        deferred_calls=binding.deferred_calls,
        mapping=binding.mapping,
        class_references=binding.class_references,
        descriptors=binding.descriptors,
        iterable_element=normalized_nested,
    )


@dataclass(frozen=True)
class _StaticMappingEntry:
    key: ast.AST | None
    binding: _ResolvedBinding


@dataclass(frozen=True)
class _StaticMapping:
    site: ast.Dict
    entries: tuple[_StaticMappingEntry, ...]


def _static_mapping_binding(
    mapping: _StaticMapping,
    key: object,
) -> tuple[_ResolvedBinding | None, bool]:
    later_entry_may_override = False
    for entry in reversed(mapping.entries):
        if entry.key is None:
            later_entry_may_override = True
            continue
        candidate = _literal_value(entry.key)
        if candidate is _UNRESOLVED_LITERAL_VALUE:
            later_entry_may_override = True
            continue
        try:
            matches = candidate == key
        except (TypeError, ValueError):
            later_entry_may_override = True
            continue
        if matches is True:
            return (None, True) if later_entry_may_override else (entry.binding, False)
    return (None, True) if later_entry_may_override else (None, False)


class _LexicalBindings:
    """Statement-ordered bindings for one Python lexical scope."""

    def __init__(
        self,
        *,
        parent: _LexicalBindings | None,
        local_names: frozenset[str] = frozenset(),
        scope_kind: str = "module",
    ) -> None:
        self.parent = parent
        self.local_names = local_names
        self.scope_kind = scope_kind
        self.references: dict[str, str] = {}
        self.strings: dict[str, str] = {}
        self.callables: dict[str, frozenset[_FunctionNode]] = {}
        self.deferred_calls: dict[str, frozenset[_DeferredFunctionCall]] = {}
        self.mappings: dict[str, _StaticMapping] = {}
        self.class_references: dict[str, frozenset[str]] = {}
        self.descriptors: dict[str, frozenset[_DescriptorBinding]] = {}
        self.iterable_elements: dict[str, _ResolvedBinding] = {}
        self.bound_names: set[str] = set()
        self.possibly_bound_names: set[str] = set()

    def clone(self) -> _LexicalBindings:
        clone = _LexicalBindings(
            parent=self.parent,
            local_names=self.local_names,
            scope_kind=self.scope_kind,
        )
        clone.references = dict(self.references)
        clone.strings = dict(self.strings)
        clone.callables = dict(self.callables)
        clone.deferred_calls = dict(self.deferred_calls)
        clone.mappings = dict(self.mappings)
        clone.class_references = dict(self.class_references)
        clone.descriptors = dict(self.descriptors)
        clone.iterable_elements = dict(self.iterable_elements)
        clone.bound_names = set(self.bound_names)
        clone.possibly_bound_names = set(self.possibly_bound_names)
        return clone

    def detached_clone(self) -> _LexicalBindings:
        clone = _LexicalBindings(
            parent=self.parent.detached_clone() if self.parent is not None else None,
            local_names=self.local_names,
            scope_kind=self.scope_kind,
        )
        clone.references = dict(self.references)
        clone.strings = dict(self.strings)
        clone.callables = dict(self.callables)
        clone.deferred_calls = dict(self.deferred_calls)
        clone.mappings = dict(self.mappings)
        clone.class_references = dict(self.class_references)
        clone.descriptors = dict(self.descriptors)
        clone.iterable_elements = dict(self.iterable_elements)
        clone.bound_names = set(self.bound_names)
        clone.possibly_bound_names = set(self.possibly_bound_names)
        return clone

    def resolve_reference(self, name: str) -> str | None:
        if name in self.references:
            return self.references[name]
        if name in self.local_names:
            return None
        if self.parent is not None:
            return self.parent.resolve_reference(name)
        return None

    def resolve_string(self, name: str) -> str | None:
        if name in self.strings:
            return self.strings[name]
        if name in self.local_names:
            return None
        if self.parent is not None:
            return self.parent.resolve_string(name)
        return None

    def resolve_callables(self, name: str) -> frozenset[_FunctionNode]:
        if name in self.callables:
            return self.callables[name]
        if name in self.local_names:
            return frozenset()
        if self.parent is not None:
            return self.parent.resolve_callables(name)
        return frozenset()

    def resolve_deferred_calls(self, name: str) -> frozenset[_DeferredFunctionCall]:
        if name in self.deferred_calls:
            return self.deferred_calls[name]
        if name in self.local_names:
            return frozenset()
        if self.parent is not None:
            return self.parent.resolve_deferred_calls(name)
        return frozenset()

    def resolve_mapping(self, name: str) -> _StaticMapping | None:
        if name in self.mappings:
            return self.mappings[name]
        if name in self.local_names:
            return None
        if self.parent is not None:
            return self.parent.resolve_mapping(name)
        return None

    def resolve_class_references(self, name: str) -> frozenset[str]:
        if name in self.class_references:
            return self.class_references[name]
        if name in self.local_names:
            return frozenset()
        if self.parent is not None:
            return self.parent.resolve_class_references(name)
        return frozenset()

    def resolve_descriptors(self, name: str) -> frozenset[_DescriptorBinding]:
        if name in self.descriptors:
            return self.descriptors[name]
        if name in self.local_names:
            return frozenset()
        if self.parent is not None:
            return self.parent.resolve_descriptors(name)
        return frozenset()

    def resolve_iterable_element(self, name: str) -> _ResolvedBinding | None:
        if name in self.iterable_elements:
            return self.iterable_elements[name]
        if name in self.local_names:
            return None
        if self.parent is not None:
            return self.parent.resolve_iterable_element(name)
        return None

    def visible_references(self) -> dict[str, str]:
        visible = self.parent.visible_references() if self.parent is not None else {}
        for name in self.local_names:
            visible.pop(name, None)
        visible.update(self.references)
        return visible

    def visible_strings(self) -> dict[str, str]:
        visible = self.parent.visible_strings() if self.parent is not None else {}
        for name in self.local_names:
            visible.pop(name, None)
        visible.update(self.strings)
        return visible

    def visible_callables(self) -> dict[str, frozenset[_FunctionNode]]:
        visible = self.parent.visible_callables() if self.parent is not None else {}
        for name in self.local_names:
            visible.pop(name, None)
        visible.update(self.callables)
        return visible

    def bind(
        self,
        name: str,
        *,
        reference: str | None,
        string: str | None,
        callables: frozenset[_FunctionNode] = frozenset(),
        deferred_calls: frozenset[_DeferredFunctionCall] = frozenset(),
        mapping: _StaticMapping | None = None,
        class_references: frozenset[str] = frozenset(),
        descriptors: frozenset[_DescriptorBinding] = frozenset(),
        iterable_element: _ResolvedBinding | None = None,
        runtime_binding: bool = True,
    ) -> None:
        if reference is None:
            self.references.pop(name, None)
        else:
            self.references[name] = reference
        if string is None:
            self.strings.pop(name, None)
        else:
            self.strings[name] = string
        if callables:
            self.callables[name] = callables
        else:
            self.callables.pop(name, None)
        if deferred_calls:
            self.deferred_calls[name] = deferred_calls
        else:
            self.deferred_calls.pop(name, None)
        if mapping is None:
            self.mappings.pop(name, None)
        else:
            self.mappings[name] = mapping
        if class_references:
            self.class_references[name] = class_references
        else:
            self.class_references.pop(name, None)
        if descriptors:
            self.descriptors[name] = descriptors
        else:
            self.descriptors.pop(name, None)
        if iterable_element is None:
            self.iterable_elements.pop(name, None)
        else:
            self.iterable_elements[name] = _normalize_resolved_binding(iterable_element)
        if runtime_binding:
            self.bound_names.add(name)
            self.possibly_bound_names.add(name)

    def unbind(self, name: str) -> None:
        self.references.pop(name, None)
        self.strings.pop(name, None)
        self.callables.pop(name, None)
        self.deferred_calls.pop(name, None)
        self.mappings.pop(name, None)
        self.class_references.pop(name, None)
        self.descriptors.pop(name, None)
        self.iterable_elements.pop(name, None)
        self.bound_names.discard(name)
        self.possibly_bound_names.discard(name)


@dataclass
class _LoopControlBindings:
    """Binding snapshots captured when the current loop changes control flow."""

    break_scopes: list[_LexicalBindings]
    continue_scopes: list[_LexicalBindings]


@dataclass
class _TerminalControlBindings:
    """Binding snapshots captured when the current function exits abruptly."""

    return_scopes: list[_LexicalBindings]
    raise_scopes: list[_LexicalBindings]


def _iter_function_parameters(arguments: ast.arguments) -> tuple[ast.arg, ...]:
    """Return every Python parameter exactly once in declaration order."""

    return (
        *arguments.posonlyargs,
        *arguments.args,
        *([arguments.vararg] if arguments.vararg is not None else []),
        *arguments.kwonlyargs,
        *([arguments.kwarg] if arguments.kwarg is not None else []),
    )


def _function_local_binding_names(
    node: ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda,
) -> frozenset[str]:
    """Return Python-local binders without descending into nested scopes."""

    names = {argument.arg for argument in _iter_function_parameters(node.args)}
    global_names: set[str] = set()
    nonlocal_names: set[str] = set()

    class _LocalBindingVisitor(ast.NodeVisitor):
        def visit_Name(self, child: ast.Name) -> None:
            if isinstance(child.ctx, (ast.Store, ast.Del)):
                names.add(child.id)

        def visit_Import(self, child: ast.Import) -> None:
            for alias in child.names:
                names.add(alias.asname or alias.name.split(".", maxsplit=1)[0])

        def visit_ImportFrom(self, child: ast.ImportFrom) -> None:
            for alias in child.names:
                if alias.name != "*":
                    names.add(alias.asname or alias.name)

        def visit_FunctionDef(self, child: ast.FunctionDef) -> None:
            names.add(child.name)

        def visit_AsyncFunctionDef(self, child: ast.AsyncFunctionDef) -> None:
            names.add(child.name)

        def visit_ClassDef(self, child: ast.ClassDef) -> None:
            names.add(child.name)

        def visit_Lambda(self, child: ast.Lambda) -> None:
            return

        def _visit_comprehension_parts(
            self,
            generators: Sequence[ast.comprehension],
            results: Sequence[ast.AST],
        ) -> None:
            for generator in generators:
                self.visit(generator.iter)
                for condition in generator.ifs:
                    self.visit(condition)
            for result in results:
                self.visit(result)

        def visit_ListComp(self, child: ast.ListComp) -> None:
            self._visit_comprehension_parts(child.generators, [child.elt])

        def visit_SetComp(self, child: ast.SetComp) -> None:
            self._visit_comprehension_parts(child.generators, [child.elt])

        def visit_DictComp(self, child: ast.DictComp) -> None:
            self._visit_comprehension_parts(child.generators, [child.key, child.value])

        def visit_GeneratorExp(self, child: ast.GeneratorExp) -> None:
            self._visit_comprehension_parts(child.generators, [child.elt])

        def visit_MatchAs(self, child: ast.MatchAs) -> None:
            if child.name is not None:
                names.add(child.name)
            if child.pattern is not None:
                self.visit(child.pattern)

        def visit_MatchStar(self, child: ast.MatchStar) -> None:
            if child.name is not None:
                names.add(child.name)

        def visit_MatchMapping(self, child: ast.MatchMapping) -> None:
            if child.rest is not None:
                names.add(child.rest)
            self.generic_visit(child)

        def visit_Global(self, child: ast.Global) -> None:
            global_names.update(child.names)

        def visit_Nonlocal(self, child: ast.Nonlocal) -> None:
            nonlocal_names.update(child.names)

        def visit_ExceptHandler(self, child: ast.ExceptHandler) -> None:
            if child.name is not None:
                names.add(child.name)
            for statement in child.body:
                self.visit(statement)

    visitor = _LocalBindingVisitor()
    if isinstance(node, ast.Lambda):
        visitor.visit(node.body)
    else:
        for statement in node.body:
            visitor.visit(statement)
    return frozenset(names - global_names - nonlocal_names)


def _function_outward_binding_names(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> tuple[frozenset[str], frozenset[str]]:
    global_names: set[str] = set()
    nonlocal_names: set[str] = set()

    class _OutwardBindingVisitor(ast.NodeVisitor):
        def visit_Global(self, child: ast.Global) -> None:
            global_names.update(child.names)

        def visit_Nonlocal(self, child: ast.Nonlocal) -> None:
            nonlocal_names.update(child.names)

        def visit_FunctionDef(self, child: ast.FunctionDef) -> None:
            return

        def visit_AsyncFunctionDef(self, child: ast.AsyncFunctionDef) -> None:
            return

        def visit_ClassDef(self, child: ast.ClassDef) -> None:
            return

        def visit_Lambda(self, child: ast.Lambda) -> None:
            return

    visitor = _OutwardBindingVisitor()
    for statement in node.body:
        visitor.visit(statement)
    return frozenset(global_names), frozenset(nonlocal_names)


def _statement_binding_names(statements: Sequence[ast.stmt]) -> frozenset[str]:
    synthetic = ast.FunctionDef(
        name="<statement-bindings>",
        args=ast.arguments(
            posonlyargs=[],
            args=[],
            kwonlyargs=[],
            kw_defaults=[],
            defaults=[],
        ),
        body=list(statements),
        decorator_list=[],
    )
    return _function_local_binding_names(synthetic)


def _statement_outward_binding_names(
    statements: Sequence[ast.stmt],
) -> tuple[frozenset[str], frozenset[str]]:
    synthetic = ast.FunctionDef(
        name="<statement-outward-bindings>",
        args=ast.arguments(
            posonlyargs=[],
            args=[],
            kwonlyargs=[],
            kw_defaults=[],
            defaults=[],
        ),
        body=list(statements),
        decorator_list=[],
    )
    return _function_outward_binding_names(synthetic)


def _function_is_generator(node: _FunctionNode) -> bool:
    found = False

    class _GeneratorVisitor(ast.NodeVisitor):
        def visit_Yield(self, child: ast.Yield) -> None:
            nonlocal found
            found = True

        def visit_YieldFrom(self, child: ast.YieldFrom) -> None:
            nonlocal found
            found = True

        def visit_FunctionDef(self, child: ast.FunctionDef) -> None:
            return

        def visit_AsyncFunctionDef(self, child: ast.AsyncFunctionDef) -> None:
            return

        def visit_Lambda(self, child: ast.Lambda) -> None:
            return

        def visit_ClassDef(self, child: ast.ClassDef) -> None:
            return

    visitor = _GeneratorVisitor()
    for statement in node.body:
        visitor.visit(statement)
    return found


_POSSIBLE_LEGACY_REFERENCE = "<possible:legacy_app>"
_POSSIBLE_APP_REFERENCE = "<possible:pulseplate.app>"
_POSSIBLE_ROUTER_REFERENCE = "<possible:pulseplate.app.router>"
_POSSIBLE_APP_CALL_REFERENCE = "<possible:pulseplate.app.call>"
_MIDDLEWARE_DECORATOR_REFERENCE_PREFIX = "pulseplate.app.middleware.decorator:"
_POSSIBLE_MIDDLEWARE_DECORATOR_REFERENCE = "<possible:pulseplate.app.middleware.decorator>"
_POSSIBLE_GETATTR_REFERENCE = "<possible:builtins.getattr>"
_POSSIBLE_API_KEY_SYMBOL = "<possible:api_key_symbol>"
_POSSIBLE_ROUTE_METHOD = "<possible:route_method>"
_CONFLICTED_ROUTE_METHOD = "<conflicted:route_method>"
_DYNAMIC_STRING_BINDING = "<dynamic:string>"
_DYNAMIC_LIFECYCLE_REFERENCE = "<dynamic>"
_POSSIBLE_FASTAPI_REFERENCE = "<possible:fastapi>"
_CONFLICTED_FASTAPI_REFERENCE = "<conflicted:fastapi>"
_POSSIBLE_IMPORT_CALLABLE_REFERENCE = "<possible:import_callable>"
_ITERABLE_SENSITIVE_ELEMENT_REFERENCE = "<iterable:possible-app-call>"
_ITERABLE_APP_ELEMENT_REFERENCE = "<iterable:possible-app>"
_MAPPING_SENSITIVE_VALUE_REFERENCE = "<mapping:possible-app-call>"
_MAPPING_APP_VALUE_REFERENCE = "<mapping:possible-app>"
_KNOWN_NON_APP_REFERENCE = "<known:non-app>"
_CLASS_REFERENCE_PREFIX = "<class:"
_INSTANCE_REFERENCE_PREFIX = "<instance:"
_BUILTINS_OBJECT_STATE_NAME = "<state:builtins.object>"
_SAFE_BUILTINS_OBJECT_REFERENCE = "<safe:builtins.object>"
_POISONED_BUILTINS_OBJECT_REFERENCE = "<poisoned:builtins.object>"
_BUILTINS_NAMESPACE_REFERENCE = "<namespace:builtins>"
_MODULE_NAMESPACE_REFERENCE = "<namespace:module>"
_MAX_LOOP_BINDING_ITERATIONS = 32
_MAX_TOTAL_LOOP_BINDING_ITERATIONS = 128
_MAPPING_MUTATOR_METHODS = frozenset(
    {
        "__delitem__",
        "__init__",
        "__ior__",
        "__setitem__",
        "clear",
        "pop",
        "popitem",
        "setdefault",
        "update",
    }
)
_ITERABLE_PRESERVING_BUILTIN_REFERENCES = frozenset(
    {
        "builtins.frozenset",
        "builtins.iter",
        "builtins.list",
        "builtins.reversed",
        "builtins.set",
        "builtins.sorted",
        "builtins.tuple",
    }
)
_ITERABLE_ELEMENT_BUILTIN_REFERENCES = frozenset(
    {
        "builtins.max",
        "builtins.min",
        "builtins.next",
    }
)


class LegacyGrowthAnalysisError(RuntimeError):
    """Fail-closed diagnostic for bounded lexical analysis exhaustion."""


class _ApiKeyLookupVisitor(ast.NodeVisitor):
    """Detect legacy API-key lookups using lexical, statement-ordered bindings."""

    def __init__(
        self,
        *,
        filename: str,
        errors: list[str],
        initial_references: Mapping[str, str] | None = None,
        reference_snapshots: dict[int, dict[str, str]] | None = None,
        string_snapshots: dict[int, dict[str, str]] | None = None,
        call_result_snapshots: dict[int, _ResolvedBinding] | None = None,
        preserve_fastapi_conflicts: bool = False,
        preserve_lifecycle_conflicts: bool = False,
        preserve_route_method_conflicts: bool = False,
        module_late_references: Mapping[str, str] | None = None,
        module_late_strings: Mapping[str, str] | None = None,
        analyze_function_bodies: bool = True,
    ) -> None:
        self.filename = filename
        self.errors = errors
        self.reference_snapshots = reference_snapshots
        self.string_snapshots = string_snapshots
        self.call_result_snapshots = call_result_snapshots
        self.preserve_fastapi_conflicts = preserve_fastapi_conflicts
        self.preserve_lifecycle_conflicts = preserve_lifecycle_conflicts
        self.preserve_route_method_conflicts = preserve_route_method_conflicts
        self.module_late_references = dict(module_late_references or {})
        self.module_late_strings = dict(module_late_strings or {})
        self.analyze_function_bodies = analyze_function_bodies
        self._loop_controls: list[_LoopControlBindings] = []
        self._terminal_controls = _TerminalControlBindings(return_scopes=[], raise_scopes=[])
        self._exception_scope_collectors: list[list[_LexicalBindings]] = []
        self._function_late_bindings: list[
            tuple[
                dict[str, str],
                dict[str, str],
                dict[str, frozenset[_FunctionNode]],
            ]
        ] = []
        self._function_default_bindings: dict[_FunctionNode, dict[str, _ResolvedBinding]] = {}
        self._function_binding_nodes: dict[tuple[_FunctionNode, object | None], _FunctionNode] = {}
        self._active_replay_contexts: list[object] = []
        self._function_decorator_bindings: dict[
            _FunctionNode, tuple[frozenset[_FunctionNode], ...]
        ] = {}
        self._function_definition_scopes: dict[_FunctionNode, _LexicalBindings] = {}
        self._deferred_generator_expressions: dict[_FunctionNode, ast.GeneratorExp] = {}
        self._deferred_generator_scopes: dict[_FunctionNode, _LexicalBindings] = {}
        self._deferred_generator_outer_bindings: dict[_FunctionNode, _ResolvedBinding] = {}
        self._consumed_deferred_calls: set[_DeferredFunctionCall] = set()
        self._lambda_function_bindings: dict[int, _FunctionNode] = {}
        self._definition_time_function_scans: set[_FunctionNode] = set()
        self._class_member_callables: dict[tuple[str, str], frozenset[_FunctionNode]] = {}
        self._class_member_descriptors: dict[tuple[str, str], frozenset[_DescriptorBinding]] = {}
        self._class_member_presence: dict[tuple[str, str], bool] = {}
        self._class_direct_member_callables: dict[tuple[str, str], frozenset[_FunctionNode]] = {}
        self._class_direct_member_descriptors: dict[
            tuple[str, str], frozenset[_DescriptorBinding]
        ] = {}
        self._class_direct_member_presence: dict[tuple[str, str], bool] = {}
        self._class_direct_member_noncallable: dict[tuple[str, str], bool] = {}
        self._class_mros: dict[str, tuple[str, ...]] = {}
        self._class_mro_complete: dict[str, bool] = {}
        self._mapping_literal_snapshots: dict[int, _StaticMapping] = {}
        self._mapping_snapshot_intern: dict[_StaticMapping, _StaticMapping] = {}
        self._active_function_replays: set[_FunctionNode] = set()
        self._active_async_replay_depth = 0
        self._active_task_group_depth = 0
        self._outward_binding_targets: list[dict[str, _LexicalBindings]] = []
        self._awaited_call_ids: set[int] = set()
        self._iterated_call_ids: set[int] = set()
        self._call_result_bindings: dict[int, _ResolvedBinding] = {}
        self._deferred_call_bindings: dict[int, frozenset[_DeferredFunctionCall]] = {}
        self._return_binding_collectors: list[list[_ResolvedBinding]] = []
        self._replay_calls_enabled = True
        self._postponed_annotations = False
        self._remaining_loop_iterations = _MAX_TOTAL_LOOP_BINDING_ITERATIONS
        self.scope = _LexicalBindings(parent=None)
        self.scope.bind("__builtins__", reference="builtins", string=None)
        self.scope.bind("__import__", reference="builtins.__import__", string=None)
        self.scope.bind("getattr", reference="builtins.getattr", string=None)
        self.scope.bind("globals", reference="builtins.globals", string=None)
        self.scope.bind("object", reference="builtins.object", string=None)
        self.scope.bind("setattr", reference="builtins.setattr", string=None)
        self.scope.bind("delattr", reference="builtins.delattr", string=None)
        self.scope.bind("vars", reference="builtins.vars", string=None)
        for builtin_name in sorted(
            {
                reference.removeprefix("builtins.")
                for reference in (
                    _ITERABLE_PRESERVING_BUILTIN_REFERENCES | _ITERABLE_ELEMENT_BUILTIN_REFERENCES
                )
            }
        ):
            self.scope.bind(
                builtin_name,
                reference=f"builtins.{builtin_name}",
                string=None,
            )
        self.scope.bind(
            _BUILTINS_OBJECT_STATE_NAME,
            reference=_SAFE_BUILTINS_OBJECT_REFERENCE,
            string=None,
            runtime_binding=False,
        )
        self.scope.bind("classmethod", reference="builtins.classmethod", string=None)
        self.scope.bind("staticmethod", reference="builtins.staticmethod", string=None)
        for name, reference in (initial_references or {}).items():
            self.scope.bind(name, reference=reference, string=None)

    def visit_Module(self, node: ast.Module) -> None:
        previous = self._postponed_annotations
        self._postponed_annotations = any(
            isinstance(statement, ast.ImportFrom)
            and statement.module == "__future__"
            and any(alias.name == "annotations" for alias in statement.names)
            for statement in node.body
        )
        try:
            self._visit_statements(node.body)
        finally:
            self._postponed_annotations = previous

    def visit(self, node: ast.AST) -> object:
        if self.reference_snapshots is not None or self.string_snapshots is not None:
            self._record_snapshot(node)
        records_exception_state = (
            bool(self._exception_scope_collectors)
            and isinstance(node, ast.expr)
            and not isinstance(node, (ast.Constant, ast.NamedExpr))
        )
        if records_exception_state:
            self._record_exception_scope()
        result = super().visit(node)
        if records_exception_state:
            self._record_exception_scope()
        return result

    @staticmethod
    def _may_reference_legacy(reference: str | None) -> bool:
        return reference == _POSSIBLE_LEGACY_REFERENCE or (
            reference is not None
            and (reference == "legacy_app" or reference.startswith("legacy_app."))
        )

    @staticmethod
    def _is_legacy_module_reference(reference: str | None) -> bool:
        return reference in {"legacy_app", _POSSIBLE_LEGACY_REFERENCE}

    @staticmethod
    def _is_legacy_namespace_reference(reference: str | None) -> bool:
        return reference in {"legacy_app.__dict__", _POSSIBLE_LEGACY_REFERENCE}

    def _record_snapshot(self, node: ast.AST) -> None:
        node_id = id(node)
        current_references = self.scope.visible_references()
        current_strings = self.scope.visible_strings()
        existing_references = (
            self.reference_snapshots.get(node_id) if self.reference_snapshots is not None else None
        )
        existing_strings = (
            self.string_snapshots.get(node_id) if self.string_snapshots is not None else None
        )
        if existing_references is not None or existing_strings is not None:
            existing = _LexicalBindings(parent=None)
            existing.references = dict(existing_references or {})
            existing.strings = dict(existing_strings or {})
            current = _LexicalBindings(parent=None)
            current.references = current_references
            current.strings = current_strings
            merged = _LexicalBindings(parent=None)
            active_scope = self.scope
            self._merge_outcomes(merged, [existing, current])
            self.scope = active_scope
            current_references = merged.references
            current_strings = merged.strings
        if self.reference_snapshots is not None:
            self.reference_snapshots[node_id] = current_references
        if self.string_snapshots is not None:
            self.string_snapshots[node_id] = current_strings

    def _bind_name(
        self,
        name: str,
        *,
        reference: str | None,
        string: str | None,
        callables: frozenset[_FunctionNode] = frozenset(),
        deferred_calls: frozenset[_DeferredFunctionCall] = frozenset(),
        overwrite_conflicts: bool = False,
        mapping: _StaticMapping | None = None,
        class_references: frozenset[str] = frozenset(),
        descriptors: frozenset[_DescriptorBinding] = frozenset(),
        iterable_element: _ResolvedBinding | None = None,
        runtime_binding: bool = True,
    ) -> None:
        if self.preserve_fastapi_conflicts and not overwrite_conflicts:
            current = self.scope.references.get(name)
            fastapi_references = {
                "fastapi.FastAPI",
                "fastapi.applications.FastAPI",
            }
            if current == _CONFLICTED_FASTAPI_REFERENCE:
                reference = _CONFLICTED_FASTAPI_REFERENCE
            elif current != _POSSIBLE_FASTAPI_REFERENCE and (
                current is not None
                and current != reference
                and (current in fastapi_references or reference in fastapi_references)
            ):
                reference = _CONFLICTED_FASTAPI_REFERENCE
        if self.preserve_route_method_conflicts and not overwrite_conflicts:
            current_string = self.scope.strings.get(name)
            route_methods = APP_ROUTE_METHODS | APP_REGISTRATION_METHODS
            if current_string == _CONFLICTED_ROUTE_METHOD:
                string = _CONFLICTED_ROUTE_METHOD
            elif current_string != _POSSIBLE_ROUTE_METHOD and (
                current_string is not None
                and current_string != string
                and (current_string in route_methods or string in route_methods)
            ):
                string = _CONFLICTED_ROUTE_METHOD
        self.scope.bind(
            name,
            reference=reference,
            string=string,
            callables=callables,
            deferred_calls=deferred_calls,
            mapping=mapping,
            class_references=class_references,
            descriptors=descriptors,
            iterable_element=iterable_element,
            runtime_binding=runtime_binding,
        )

    def _bind_resolved_name(
        self,
        name: str,
        binding: _ResolvedBinding,
        *,
        overwrite_conflicts: bool = False,
        runtime_binding: bool = True,
    ) -> None:
        self._bind_name(
            name,
            reference=binding.reference,
            string=binding.string,
            callables=binding.callables,
            deferred_calls=binding.deferred_calls,
            overwrite_conflicts=overwrite_conflicts,
            mapping=binding.mapping,
            class_references=binding.class_references,
            descriptors=binding.descriptors,
            iterable_element=binding.iterable_element,
            runtime_binding=runtime_binding,
        )

    def _resolve_callables(self, node: ast.AST) -> frozenset[_FunctionNode]:
        if id(node) in self._call_result_bindings:
            return self._call_result_bindings[id(node)].callables
        if isinstance(node, ast.Await):
            return self._resolve_callables(node.value)
        if isinstance(node, ast.Lambda):
            synthetic = self._lambda_function_bindings.get(id(node))
            return frozenset({synthetic}) if synthetic is not None else frozenset()
        if isinstance(node, ast.Attribute):
            return frozenset().union(
                *(
                    self._class_member_callables.get(
                        (owner_reference, node.attr),
                        frozenset(),
                    )
                    for owner_reference in self._resolve_object_references(node.value)
                )
            )
        if isinstance(node, ast.Subscript):
            mapping_binding, _unresolved = self._resolve_mapping_subscript_binding(node)
            if mapping_binding is not None:
                return mapping_binding.callables
        if isinstance(node, ast.Call):
            constructor_reference = self._resolve_reference(node.func)
            if (
                constructor_reference in {"builtins.classmethod", "builtins.staticmethod"}
                and len(node.args) == 1
                and not node.keywords
            ):
                return self._resolve_callables(node.args[0])
        if isinstance(node, ast.NamedExpr):
            return self._resolve_callables(node.value)
        if isinstance(node, ast.Name):
            return self.scope.resolve_callables(node.id)
        if isinstance(node, ast.BoolOp):
            return frozenset().union(*(self._resolve_callables(value) for value in node.values))
        if isinstance(node, ast.IfExp):
            selected_nodes = (
                [node.body if bool(node.test.value) else node.orelse]
                if isinstance(node.test, ast.Constant)
                else [node.body, node.orelse]
            )
            return frozenset().union(*(self._resolve_callables(value) for value in selected_nodes))
        return frozenset()

    def _resolve_descriptors(self, node: ast.AST) -> frozenset[_DescriptorBinding]:
        if id(node) in self._call_result_bindings:
            return self._call_result_bindings[id(node)].descriptors
        if isinstance(node, ast.Await):
            return self._resolve_descriptors(node.value)
        if isinstance(node, ast.NamedExpr):
            return self._resolve_descriptors(node.value)
        if isinstance(node, ast.Attribute):
            resolved: set[_DescriptorBinding] = set()
            for owner_reference in self._resolve_object_references(node.value):
                for function, descriptor_kind in self._class_member_descriptors.get(
                    (owner_reference, node.attr),
                    frozenset(),
                ):
                    if descriptor_kind in {"bound", "classmethod"}:
                        resolved.add((function, "bound"))
                    elif descriptor_kind == "staticmethod":
                        resolved.add((function, "unbound"))
                    elif descriptor_kind == "plain":
                        resolved.add(
                            (
                                function,
                                (
                                    "bound"
                                    if owner_reference.startswith(_INSTANCE_REFERENCE_PREFIX)
                                    else "unbound"
                                ),
                            )
                        )
                    else:
                        resolved.add((function, descriptor_kind))
            return frozenset(resolved)
        if isinstance(node, ast.Name):
            return self.scope.resolve_descriptors(node.id)
        if isinstance(node, ast.Subscript):
            mapping_binding, _unresolved = self._resolve_mapping_subscript_binding(node)
            if mapping_binding is not None:
                return mapping_binding.descriptors
        if isinstance(node, ast.BoolOp):
            return frozenset().union(*(self._resolve_descriptors(value) for value in node.values))
        if isinstance(node, ast.IfExp):
            selected_nodes = (
                [node.body if bool(node.test.value) else node.orelse]
                if isinstance(node.test, ast.Constant)
                else [node.body, node.orelse]
            )
            return frozenset().union(
                *(self._resolve_descriptors(value) for value in selected_nodes)
            )
        if isinstance(node, ast.Call):
            constructor_reference = self._resolve_reference(node.func)
            if (
                constructor_reference in {"builtins.classmethod", "builtins.staticmethod"}
                and len(node.args) == 1
                and not node.keywords
            ):
                kind = constructor_reference.rsplit(".", maxsplit=1)[-1]
                return frozenset(
                    (function, kind) for function in self._resolve_callables(node.args[0])
                )
        return frozenset()

    def _resolve_deferred_calls(self, node: ast.AST) -> frozenset[_DeferredFunctionCall]:
        if id(node) in self._call_result_bindings:
            return self._call_result_bindings[id(node)].deferred_calls
        if id(node) in self._deferred_call_bindings:
            return self._deferred_call_bindings[id(node)]
        if isinstance(node, ast.Call):
            return frozenset()
        if isinstance(node, ast.Await):
            return self._resolve_deferred_calls(node.value)
        if isinstance(node, ast.NamedExpr):
            return self._resolve_deferred_calls(node.value)
        if isinstance(node, ast.Name):
            return self.scope.resolve_deferred_calls(node.id)
        if isinstance(node, ast.Subscript):
            mapping_binding, _unresolved = self._resolve_mapping_subscript_binding(node)
            if mapping_binding is not None:
                return mapping_binding.deferred_calls
        if isinstance(node, ast.BoolOp):
            return frozenset().union(
                *(self._resolve_deferred_calls(value) for value in node.values)
            )
        if isinstance(node, ast.IfExp):
            selected_nodes = (
                [node.body if bool(node.test.value) else node.orelse]
                if isinstance(node.test, ast.Constant)
                else [node.body, node.orelse]
            )
            return frozenset().union(
                *(self._resolve_deferred_calls(value) for value in selected_nodes)
            )
        return frozenset()

    def _resolve_mapping_subscript_binding(
        self,
        node: ast.Subscript,
    ) -> tuple[_ResolvedBinding | None, bool]:
        mapping = self._resolve_mapping(node.value)
        key = _literal_value(node.slice)
        if mapping is None or key is _UNRESOLVED_LITERAL_VALUE:
            return None, False
        return _static_mapping_binding(mapping, key)

    def _resolve_class_references(self, node: ast.AST) -> frozenset[str]:
        if id(node) in self._call_result_bindings:
            return self._call_result_bindings[id(node)].class_references
        if isinstance(node, ast.Await):
            return self._resolve_class_references(node.value)
        if isinstance(node, ast.NamedExpr):
            return self._resolve_class_references(node.value)
        if isinstance(node, ast.Name):
            return self.scope.resolve_class_references(node.id)
        if isinstance(node, ast.BoolOp):
            return frozenset().union(
                *(self._resolve_class_references(value) for value in node.values)
            )
        if isinstance(node, ast.IfExp):
            selected_nodes = (
                [node.body if bool(node.test.value) else node.orelse]
                if isinstance(node.test, ast.Constant)
                else [node.body, node.orelse]
            )
            return frozenset().union(
                *(self._resolve_class_references(value) for value in selected_nodes)
            )
        reference = self._resolve_reference(node)
        if reference is not None and reference.startswith(_CLASS_REFERENCE_PREFIX):
            return frozenset({reference})
        return frozenset()

    def _resolve_object_references(self, node: ast.AST) -> frozenset[str]:
        references: set[str] = set()
        reference = self._resolve_reference(node)
        if reference is not None:
            references.add(reference)
        references.update(self._resolve_class_references(node))
        if isinstance(node, ast.Call):
            references.update(
                class_reference.replace(
                    _CLASS_REFERENCE_PREFIX,
                    _INSTANCE_REFERENCE_PREFIX,
                    1,
                )
                for class_reference in self._resolve_class_references(node.func)
            )
        return frozenset(references)

    def _resolve_mapping(self, node: ast.AST) -> _StaticMapping | None:
        if id(node) in self._call_result_bindings:
            return self._call_result_bindings[id(node)].mapping
        if isinstance(node, ast.Await):
            return self._resolve_mapping(node.value)
        if isinstance(node, ast.NamedExpr):
            return self._resolve_mapping(node.value)
        if isinstance(node, ast.Dict):
            return self._mapping_literal_snapshots.get(id(node))
        if isinstance(node, ast.Name):
            return self.scope.resolve_mapping(node.id)
        if isinstance(node, ast.Subscript):
            binding, _unresolved = self._resolve_mapping_subscript_binding(node)
            return binding.mapping if binding is not None else None
        return None

    def _invalidate_mapping(self, mapping: _StaticMapping) -> None:
        scope: _LexicalBindings | None = self.scope
        while scope is not None:
            for name, candidate in tuple(scope.mappings.items()):
                if candidate is mapping:
                    scope.mappings.pop(name, None)
                    if scope.references.get(name) != _MAPPING_APP_VALUE_REFERENCE:
                        scope.references[name] = _MAPPING_SENSITIVE_VALUE_REFERENCE
            scope = scope.parent

    def _invalidate_mapping_aliases(self, node: ast.AST) -> None:
        mapping = self._resolve_mapping(node)
        if mapping is not None:
            self._invalidate_mapping(mapping)

    def _invalidate_mapping_target(self, target: ast.AST) -> None:
        if isinstance(target, (ast.Attribute, ast.Subscript)):
            self._invalidate_mapping_aliases(target.value)

    def _resolve_unpacked_keyword_binding(
        self,
        node: ast.AST,
        keyword_name: str,
    ) -> tuple[_ResolvedBinding | None, bool]:
        mapping = self._resolve_mapping(node)
        if mapping is not None:
            return _static_mapping_binding(mapping, keyword_name)
        if not isinstance(node, ast.Dict):
            return None, True
        later_entry_may_override = False
        for key, value in reversed(tuple(zip(node.keys, node.values, strict=True))):
            if key is None:
                later_entry_may_override = True
                continue
            resolved_key = self._resolve_string(key)
            if resolved_key in {None, _DYNAMIC_STRING_BINDING}:
                later_entry_may_override = True
                continue
            if resolved_key == keyword_name:
                if later_entry_may_override:
                    return None, True
                return self._capture_argument_binding(value), False
        return (None, True) if later_entry_may_override else (None, False)

    def _resolve_reference(self, node: ast.AST) -> str | None:
        if id(node) in self._call_result_bindings:
            return self._call_result_bindings[id(node)].reference
        if isinstance(node, ast.Await):
            return self._resolve_reference(node.value)
        if isinstance(node, ast.NamedExpr):
            return self._resolve_reference(node.value)
        if isinstance(node, ast.Name):
            reference = self.scope.resolve_reference(node.id)
            if reference is not None:
                return reference
            class_references = self.scope.resolve_class_references(node.id)
            if len(class_references) == 1:
                return next(iter(class_references))
        if isinstance(node, ast.BoolOp):
            return self._join_expression_bindings(node.values)[0]
        if isinstance(node, ast.IfExp):
            selected_nodes = (
                [node.body if bool(node.test.value) else node.orelse]
                if isinstance(node.test, ast.Constant)
                else [node.body, node.orelse]
            )
            return self._join_expression_bindings(selected_nodes)[0]
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            element_references = [
                self._resolve_reference(
                    element.value if isinstance(element, ast.Starred) else element
                )
                for element in node.elts
            ]
            collection_reference = _collection_reference(
                element_references,
                mapping=False,
            )
            if collection_reference is not None:
                return collection_reference
        if isinstance(node, ast.Dict):
            mapping = self._resolve_mapping(node)
            collection_reference = _collection_reference(
                (
                    [entry.binding.reference for entry in mapping.entries]
                    if mapping is not None
                    else [
                        _unpacked_mapping_reference(
                            key,
                            self._resolve_reference(value),
                        )
                        for key, value in zip(node.keys, node.values, strict=True)
                    ]
                ),
                mapping=True,
            )
            if collection_reference is not None:
                return collection_reference
        if isinstance(node, ast.Attribute):
            owner_reference = self._resolve_reference(node.value)
            if owner_reference == _KNOWN_NON_APP_REFERENCE:
                return None
            if node.attr == "__call__" and _is_registration_callable_reference(owner_reference):
                return owner_reference
            if owner_reference in {"pulseplate.app", _POSSIBLE_APP_REFERENCE}:
                if node.attr == "router":
                    return _POSSIBLE_ROUTER_REFERENCE
                if node.attr in APP_ROUTE_METHODS | APP_REGISTRATION_METHODS:
                    return (
                        f"pulseplate.app.{node.attr}"
                        if owner_reference == "pulseplate.app"
                        else _POSSIBLE_APP_CALL_REFERENCE
                    )
            if owner_reference in {"pulseplate.app.router", _POSSIBLE_ROUTER_REFERENCE} and (
                node.attr in APP_ROUTE_METHODS | APP_REGISTRATION_METHODS
            ):
                return (
                    f"pulseplate.app.router.{node.attr}"
                    if owner_reference == "pulseplate.app.router"
                    else _POSSIBLE_APP_CALL_REFERENCE
                )
        if isinstance(node, ast.Call):
            importer_reference = self._resolve_reference(node.func)
            module_strings: list[str | None] = []
            module_argument_unresolved = False
            if node.args:
                first_argument = node.args[0]
                if isinstance(first_argument, ast.Starred):
                    unpacked = first_argument.value
                    if (
                        isinstance(unpacked, (ast.List, ast.Tuple))
                        and len(unpacked.elts) == 1
                        and not isinstance(unpacked.elts[0], ast.Starred)
                    ):
                        module_strings.append(self._resolve_string(unpacked.elts[0]))
                    else:
                        module_argument_unresolved = True
                else:
                    module_strings.append(self._resolve_string(first_argument))
            for keyword in node.keywords:
                if keyword.arg == "name":
                    module_strings.append(self._resolve_string(keyword.value))
                elif keyword.arg is None:
                    binding, unresolved = self._resolve_unpacked_keyword_binding(
                        keyword.value,
                        "name",
                    )
                    if binding is not None:
                        module_strings.append(binding.string)
                    module_argument_unresolved = module_argument_unresolved or unresolved
            if (
                importer_reference == "builtins.__import__"
                and not module_argument_unresolved
                and module_strings == ["builtins"]
            ):
                return "builtins"
            class_references = self._resolve_class_references(node.func)
            if len(class_references) == 1:
                return next(iter(class_references)).replace(
                    _CLASS_REFERENCE_PREFIX,
                    _INSTANCE_REFERENCE_PREFIX,
                    1,
                )
            constructor_reference = self._resolve_reference(node.func)
            if constructor_reference is not None and constructor_reference.startswith(
                _CLASS_REFERENCE_PREFIX
            ):
                return constructor_reference.replace(
                    _CLASS_REFERENCE_PREFIX,
                    _INSTANCE_REFERENCE_PREFIX,
                    1,
                )
        if isinstance(node, ast.Subscript):
            mapping_binding, _mapping_unresolved = self._resolve_mapping_subscript_binding(node)
            if mapping_binding is not None:
                return mapping_binding.reference
            if self._resolve_mapping(node.value) is None:
                selected, _unresolved = _literal_subscript_value(node)
                if selected is not None:
                    return self._resolve_reference(selected)
        if self._is_definitely_non_app_value(node):
            return _KNOWN_NON_APP_REFERENCE
        references = self.scope.visible_references()
        strings = self.scope.visible_strings()
        reference = _static_module_reference(
            node,
            module_aliases=references,
            import_module_aliases={
                name
                for name, candidate in references.items()
                if candidate == "importlib.import_module"
            },
            static_string_bindings=strings,
        )
        if reference is not None:
            return reference
        if isinstance(node, ast.Subscript):
            container_reference = self._resolve_reference(node.value)
            if container_reference in {
                _POSSIBLE_APP_CALL_REFERENCE,
                _POSSIBLE_MIDDLEWARE_DECORATOR_REFERENCE,
                _ITERABLE_SENSITIVE_ELEMENT_REFERENCE,
                _MAPPING_SENSITIVE_VALUE_REFERENCE,
            }:
                return _POSSIBLE_APP_CALL_REFERENCE
            if container_reference in {
                _ITERABLE_APP_ELEMENT_REFERENCE,
                _MAPPING_APP_VALUE_REFERENCE,
            }:
                return _POSSIBLE_APP_REFERENCE
            if container_reference == _KNOWN_NON_APP_REFERENCE:
                return _KNOWN_NON_APP_REFERENCE
        if isinstance(node, ast.Call):
            if (
                self.preserve_route_method_conflicts
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "middleware"
                and self._resolve_reference(node.func.value)
                in {"pulseplate.app", _POSSIBLE_APP_REFERENCE}
            ):
                return f"{_MIDDLEWARE_DECORATOR_REFERENCE_PREFIX}{_first_arg_label(node)}"
            if self.preserve_route_method_conflicts and len(node.args) >= 2:
                lookup_reference = _static_module_reference(
                    node.func,
                    module_aliases=references,
                    import_module_aliases=frozenset(),
                    static_string_bindings=strings,
                )
                if lookup_reference in {
                    "builtins.getattr",
                    _POSSIBLE_GETATTR_REFERENCE,
                }:
                    target_reference = _static_module_reference(
                        node.args[0],
                        module_aliases=references,
                        import_module_aliases=frozenset(),
                        static_string_bindings=strings,
                    )
                    target_prefix: str | None = None
                    if target_reference in {
                        "pulseplate.app",
                        _POSSIBLE_APP_REFERENCE,
                    }:
                        target_prefix = "pulseplate.app."
                    elif target_reference in {
                        "pulseplate.app.router",
                        _POSSIBLE_ROUTER_REFERENCE,
                    }:
                        target_prefix = "pulseplate.app.router."
                    if target_prefix is not None:
                        method = self._resolve_string(node.args[1])
                        if method in APP_ROUTE_METHODS | APP_REGISTRATION_METHODS:
                            return f"{target_prefix}{method}"
                        if method in {
                            None,
                            _DYNAMIC_STRING_BINDING,
                            _POSSIBLE_ROUTE_METHOD,
                            _CONFLICTED_ROUTE_METHOD,
                        }:
                            return _POSSIBLE_APP_CALL_REFERENCE
            constructor = _static_module_reference(
                node.func,
                module_aliases=references,
                import_module_aliases=frozenset(),
                static_string_bindings=strings,
            )
            if self.preserve_route_method_conflicts and constructor == "pulseplate.app.middleware":
                return f"{_MIDDLEWARE_DECORATOR_REFERENCE_PREFIX}{_first_arg_label(node)}"
            if constructor in {"fastapi.FastAPI", "fastapi.applications.FastAPI"}:
                return "pulseplate.app"
        return None

    def _resolve_string(self, node: ast.AST) -> str | None:
        if id(node) in self._call_result_bindings:
            return self._call_result_bindings[id(node)].string
        if isinstance(node, ast.Await):
            return self._resolve_string(node.value)
        if isinstance(node, ast.NamedExpr):
            return self._resolve_string(node.value)
        if isinstance(node, ast.BoolOp):
            return self._join_expression_bindings(node.values)[1]
        if isinstance(node, ast.IfExp):
            selected_nodes = (
                [node.body if bool(node.test.value) else node.orelse]
                if isinstance(node.test, ast.Constant)
                else [node.body, node.orelse]
            )
            return self._join_expression_bindings(selected_nodes)[1]
        if isinstance(node, ast.Subscript):
            mapping_binding, _unresolved = self._resolve_mapping_subscript_binding(node)
            if mapping_binding is not None:
                return mapping_binding.string
        return _resolve_static_string(node, self.scope.visible_strings())

    def _join_expression_bindings(
        self,
        nodes: Sequence[ast.AST],
    ) -> tuple[str | None, str | None]:
        marker = "<expression-result>"
        active_scope = self.scope
        outcomes: list[_LexicalBindings] = []
        for node in nodes:
            outcome = active_scope.clone()
            outcome.bind(
                marker,
                reference=self._resolve_reference(node),
                string=self._resolve_string(node),
            )
            outcomes.append(outcome)
        merged = active_scope.clone()
        self._merge_outcomes(merged, outcomes)
        self.scope = active_scope
        return merged.references.get(marker), merged.strings.get(marker)

    def _visit_statements(self, statements: Sequence[ast.stmt]) -> bool:
        for statement in statements:
            falls_through = self.visit(statement) is not False
            if not falls_through:
                return False
        return True

    def _record_exception_scope(self) -> None:
        for collector in self._exception_scope_collectors:
            collector.append(self.scope.clone())

    def _visit_branches(self, branches: Sequence[Sequence[ast.stmt]]) -> bool:
        incoming = self.scope
        outcomes: list[_LexicalBindings] = []
        for branch in branches:
            self.scope = incoming.clone()
            if self._visit_statements(branch):
                outcomes.append(self.scope)
        if not outcomes:
            self.scope = incoming
            return False
        self._merge_outcomes(incoming, outcomes)
        return True

    def _visit_with_exception_scopes(
        self,
        statements: Sequence[ast.stmt],
    ) -> tuple[bool, list[_LexicalBindings]]:
        exception_scopes: list[_LexicalBindings] = []
        self._exception_scope_collectors.append(exception_scopes)
        try:
            falls_through = self._visit_statements(statements)
        finally:
            self._exception_scope_collectors.pop()
        return falls_through, exception_scopes

    def _visit_loop_body(
        self,
        statements: Sequence[ast.stmt],
    ) -> tuple[_LexicalBindings | None, _LoopControlBindings]:
        controls = _LoopControlBindings(break_scopes=[], continue_scopes=[])
        self._loop_controls.append(controls)
        try:
            falls_through = self._visit_statements(statements)
        finally:
            self._loop_controls.pop()
        return (self.scope if falls_through else None), controls

    def _finish_loop(
        self,
        *,
        incoming: _LexicalBindings,
        normal_entries: Sequence[_LexicalBindings],
        break_scopes: Sequence[_LexicalBindings],
        orelse: Sequence[ast.stmt],
    ) -> bool:
        outcomes: list[_LexicalBindings] = list(break_scopes)
        if normal_entries:
            else_entry = incoming.clone()
            self._merge_outcomes(else_entry, normal_entries)
            if self._visit_statements(orelse):
                outcomes.append(self.scope)
        if not outcomes:
            self.scope = incoming
            return False
        self._merge_outcomes(incoming, outcomes)
        return True

    @staticmethod
    def _bindings_equal(left: _LexicalBindings, right: _LexicalBindings) -> bool:
        return (
            left.references == right.references
            and left.strings == right.strings
            and left.callables == right.callables
            and left.deferred_calls == right.deferred_calls
            and left.mappings == right.mappings
            and left.class_references == right.class_references
            and left.descriptors == right.descriptors
            and left.iterable_elements == right.iterable_elements
            and left.bound_names == right.bound_names
            and left.possibly_bound_names == right.possibly_bound_names
        )

    def _consume_loop_iteration(self) -> None:
        if self._remaining_loop_iterations <= 0:
            raise LegacyGrowthAnalysisError(
                f"{self.filename}: loop binding analysis exceeded "
                f"{_MAX_TOTAL_LOOP_BINDING_ITERATIONS} total iterations"
            )
        self._remaining_loop_iterations -= 1

    def _merge_outcomes(
        self,
        incoming: _LexicalBindings,
        outcomes: Sequence[_LexicalBindings],
    ) -> None:
        self.scope = incoming
        if not outcomes:
            return
        reference_names = set().union(*(set(outcome.references) for outcome in outcomes))
        joined_references: dict[str, str] = {}
        for name in reference_names:
            values = [outcome.references.get(name) for outcome in outcomes]
            if all(value == values[0] for value in values) and values[0] is not None:
                joined_references[name] = values[0]
            elif self.preserve_lifecycle_conflicts and any(
                value
                in {
                    "builtins.__import__",
                    "importlib.import_module",
                    _POSSIBLE_IMPORT_CALLABLE_REFERENCE,
                }
                for value in values
            ):
                joined_references[name] = _POSSIBLE_IMPORT_CALLABLE_REFERENCE
            elif self.preserve_fastapi_conflicts and any(
                value
                in {
                    "fastapi.FastAPI",
                    "fastapi.applications.FastAPI",
                    _POSSIBLE_FASTAPI_REFERENCE,
                    _CONFLICTED_FASTAPI_REFERENCE,
                }
                for value in values
            ):
                joined_references[name] = _POSSIBLE_FASTAPI_REFERENCE
            elif any(
                value in {"builtins.getattr", _POSSIBLE_GETATTR_REFERENCE} for value in values
            ):
                joined_references[name] = _POSSIBLE_GETATTR_REFERENCE
            elif any(self._may_reference_legacy(value) for value in values):
                joined_references[name] = _POSSIBLE_LEGACY_REFERENCE
            elif any(
                value
                in {
                    _ITERABLE_APP_ELEMENT_REFERENCE,
                    _ITERABLE_SENSITIVE_ELEMENT_REFERENCE,
                    _MAPPING_APP_VALUE_REFERENCE,
                    _MAPPING_SENSITIVE_VALUE_REFERENCE,
                }
                for value in values
            ):
                if _MAPPING_APP_VALUE_REFERENCE in values:
                    joined_references[name] = _MAPPING_APP_VALUE_REFERENCE
                elif _MAPPING_SENSITIVE_VALUE_REFERENCE in values:
                    joined_references[name] = _MAPPING_SENSITIVE_VALUE_REFERENCE
                elif _ITERABLE_APP_ELEMENT_REFERENCE in values:
                    joined_references[name] = _ITERABLE_APP_ELEMENT_REFERENCE
                else:
                    joined_references[name] = _ITERABLE_SENSITIVE_ELEMENT_REFERENCE
            elif any(
                value == _POSSIBLE_APP_CALL_REFERENCE
                or (
                    value is not None
                    and value.startswith("pulseplate.app.")
                    and value.rsplit(".", maxsplit=1)[-1]
                    in APP_ROUTE_METHODS | APP_REGISTRATION_METHODS
                )
                for value in values
            ):
                joined_references[name] = _POSSIBLE_APP_CALL_REFERENCE
            elif self.preserve_route_method_conflicts and any(
                value == _POSSIBLE_MIDDLEWARE_DECORATOR_REFERENCE
                or (value is not None and value.startswith(_MIDDLEWARE_DECORATOR_REFERENCE_PREFIX))
                for value in values
            ):
                middleware_values = {
                    value
                    for value in values
                    if value is not None
                    and value.startswith(_MIDDLEWARE_DECORATOR_REFERENCE_PREFIX)
                }
                joined_references[name] = (
                    next(iter(middleware_values))
                    if len(middleware_values) == 1
                    and _POSSIBLE_MIDDLEWARE_DECORATOR_REFERENCE not in values
                    else _POSSIBLE_MIDDLEWARE_DECORATOR_REFERENCE
                )
            elif any(value in {"pulseplate.app", _POSSIBLE_APP_REFERENCE} for value in values):
                joined_references[name] = _POSSIBLE_APP_REFERENCE
            elif any(
                value in {"pulseplate.app.router", _POSSIBLE_ROUTER_REFERENCE} for value in values
            ):
                joined_references[name] = _POSSIBLE_ROUTER_REFERENCE
        self.scope.references = joined_references

        string_names = set().union(*(set(outcome.strings) for outcome in outcomes))
        joined_strings: dict[str, str] = {}
        for name in string_names:
            values = [outcome.strings.get(name) for outcome in outcomes]
            if all(value == values[0] for value in values) and values[0] is not None:
                joined_strings[name] = values[0]
            elif self.preserve_route_method_conflicts and any(
                value
                in {
                    *APP_ROUTE_METHODS,
                    *APP_REGISTRATION_METHODS,
                    _POSSIBLE_ROUTE_METHOD,
                    _CONFLICTED_ROUTE_METHOD,
                }
                for value in values
            ):
                joined_strings[name] = _POSSIBLE_ROUTE_METHOD
            elif any(value in CANONICAL_API_KEY_SYMBOLS for value in values):
                joined_strings[name] = _POSSIBLE_API_KEY_SYMBOL
        self.scope.strings = joined_strings

        callable_names = set().union(*(set(outcome.callables) for outcome in outcomes))
        joined_callables: dict[str, frozenset[_FunctionNode]] = {}
        for name in callable_names:
            candidates = frozenset().union(
                *(outcome.callables.get(name, frozenset()) for outcome in outcomes)
            )
            if candidates:
                joined_callables[name] = candidates
        self.scope.callables = joined_callables

        deferred_names = set().union(*(set(outcome.deferred_calls) for outcome in outcomes))
        joined_deferred_calls: dict[str, frozenset[_DeferredFunctionCall]] = {}
        for name in deferred_names:
            deferred_candidates: frozenset[_DeferredFunctionCall] = frozenset().union(
                *(outcome.deferred_calls.get(name, frozenset()) for outcome in outcomes)
            )
            if deferred_candidates:
                joined_deferred_calls[name] = deferred_candidates
        self.scope.deferred_calls = joined_deferred_calls

        mapping_names = set().union(*(set(outcome.mappings) for outcome in outcomes))
        joined_mappings: dict[str, _StaticMapping] = {}
        for name in mapping_names:
            mapping_values = [outcome.mappings.get(name) for outcome in outcomes]
            first_mapping = mapping_values[0]
            if first_mapping is not None and all(
                value is first_mapping for value in mapping_values
            ):
                joined_mappings[name] = first_mapping
        self.scope.mappings = joined_mappings
        class_reference_names = set().union(
            *(set(outcome.class_references) for outcome in outcomes)
        )
        self.scope.class_references = {
            name: frozenset().union(
                *(outcome.class_references.get(name, frozenset()) for outcome in outcomes)
            )
            for name in class_reference_names
        }
        descriptor_names = set().union(
            *(set(outcome.descriptors) | set(outcome.callables) for outcome in outcomes)
        )
        joined_descriptors: dict[str, frozenset[_DescriptorBinding]] = {}
        for name in descriptor_names:
            descriptor_candidates: set[_DescriptorBinding] = set()
            for outcome in outcomes:
                outcome_descriptors = outcome.descriptors.get(name, frozenset())
                descriptor_candidates.update(outcome_descriptors)
                described_callables = {function for function, _kind in outcome_descriptors}
                descriptor_candidates.update(
                    (function, "plain")
                    for function in outcome.callables.get(name, frozenset())
                    if function not in described_callables
                )
            if descriptor_candidates:
                joined_descriptors[name] = frozenset(descriptor_candidates)
        self.scope.descriptors = joined_descriptors
        iterable_names = set().union(*(set(outcome.iterable_elements) for outcome in outcomes))
        joined_iterable_elements: dict[str, _ResolvedBinding] = {}
        for name in iterable_names:
            iterable_values: list[_ResolvedBinding | None] = [
                outcome.iterable_elements.get(name) for outcome in outcomes
            ]
            join_candidates: list[_ResolvedBinding] = []
            for value in iterable_values:
                join_candidates.append(
                    value if value is not None else self._conservative_argument_binding()
                )
            joined_iterable_elements[name] = self._join_resolved_bindings(join_candidates)
        self.scope.iterable_elements = joined_iterable_elements
        self.scope.bound_names = set.intersection(
            *(set(outcome.bound_names) for outcome in outcomes)
        )
        self.scope.possibly_bound_names = set().union(
            *(set(outcome.possibly_bound_names) for outcome in outcomes)
        )

    def _bind_targets(
        self,
        targets: Sequence[ast.expr],
        *,
        reference: str | None,
        string: str | None,
        callables: frozenset[_FunctionNode] = frozenset(),
        deferred_calls: frozenset[_DeferredFunctionCall] = frozenset(),
        mapping: _StaticMapping | None = None,
        class_references: frozenset[str] = frozenset(),
        descriptors: frozenset[_DescriptorBinding] = frozenset(),
        iterable_element: _ResolvedBinding | None = None,
        runtime_binding: bool = True,
    ) -> None:
        for target in targets:
            for name in _assignment_target_names(target):
                self._bind_name(
                    name,
                    reference=reference,
                    string=string,
                    callables=callables,
                    deferred_calls=deferred_calls,
                    mapping=mapping,
                    class_references=class_references,
                    descriptors=descriptors,
                    iterable_element=iterable_element,
                    runtime_binding=runtime_binding,
                )

    def _bind_targets_from_resolved_binding(
        self,
        targets: Sequence[ast.expr],
        binding: _ResolvedBinding,
    ) -> None:
        self._bind_targets(
            targets,
            reference=binding.reference,
            string=binding.string,
            callables=binding.callables,
            deferred_calls=binding.deferred_calls,
            mapping=binding.mapping,
            class_references=binding.class_references,
            descriptors=binding.descriptors,
            iterable_element=binding.iterable_element,
        )

    def _is_definitely_non_app_value(self, node: ast.AST) -> bool:
        if isinstance(node, (ast.Constant, ast.JoinedStr, ast.Lambda)):
            return True
        if (
            isinstance(node, ast.Call)
            and not node.args
            and not node.keywords
            and self._is_proven_builtin_object_callable(node.func)
        ):
            return True
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            return all(
                not isinstance(element, ast.Starred) and self._is_definitely_non_app_value(element)
                for element in node.elts
            )
        if isinstance(node, ast.Dict):
            return all(
                key is not None
                and self._is_definitely_non_app_value(key)
                and self._is_definitely_non_app_value(value)
                for key, value in zip(node.keys, node.values, strict=True)
            )
        return False

    def _module_scope(self) -> _LexicalBindings:
        scope = self.scope
        while scope.parent is not None:
            scope = scope.parent
        return scope

    def _builtins_object_is_safe(self) -> bool:
        return (
            self._module_scope().resolve_reference(_BUILTINS_OBJECT_STATE_NAME)
            == _SAFE_BUILTINS_OBJECT_REFERENCE
        )

    def _is_proven_builtin_object_callable(self, node: ast.AST) -> bool:
        if self._resolve_reference(node) != "builtins.object":
            return False
        if isinstance(node, ast.Name):
            if node.id == "object":
                return (
                    self._module_scope().resolve_reference("object") == "builtins.object"
                    and self._builtins_object_is_safe()
                )
            return self.scope.resolve_reference(node.id) == "builtins.object"
        if isinstance(node, ast.Attribute) and node.attr == "object":
            return (
                self._resolve_reference(node.value) == "builtins"
                and self._builtins_object_is_safe()
            )
        return False

    def _is_proven_current_module_object(self, node: ast.AST) -> bool:
        if (
            not _is_current_module_object_shape(node)
            or not isinstance(node, ast.Subscript)
            or not isinstance(node.value, ast.Attribute)
        ):
            return False
        return self._resolve_reference(node.value.value) == "sys"

    def _object_namespace_mapping_kind(self, node: ast.AST) -> str | None:
        reference = self._resolve_reference(node)
        if reference in {"builtins", _BUILTINS_NAMESPACE_REFERENCE}:
            return "builtins"
        if reference == _MODULE_NAMESPACE_REFERENCE:
            return "module"
        if isinstance(node, ast.Attribute) and node.attr == "__dict__":
            owner_reference = self._resolve_reference(node.value)
            if owner_reference == "builtins":
                return "builtins"
            if self._is_proven_current_module_object(node.value):
                return "module"
            return None
        if not isinstance(node, ast.Call) or node.keywords:
            return None
        function_reference = self._resolve_reference(node.func)
        if function_reference == "builtins.globals":
            return "module" if not node.args else None
        if function_reference != "builtins.vars":
            return None
        if not node.args:
            return "module" if self.scope.scope_kind == "module" else None
        if len(node.args) != 1:
            return None
        owner = node.args[0]
        if self._resolve_reference(owner) == "builtins":
            return "builtins"
        if self._is_proven_current_module_object(owner):
            return "module"
        return None

    def _object_namespace_target_kind(self, target: ast.AST) -> str | None:
        if isinstance(target, ast.Attribute) and target.attr == "object":
            if self._resolve_reference(target.value) == "builtins":
                return "builtins"
            if self._is_proven_current_module_object(target.value):
                return "module"
            return None
        if not isinstance(target, ast.Subscript):
            return None
        namespace_kind = self._object_namespace_mapping_kind(target.value)
        if namespace_kind is None:
            return None
        member_name = self._resolve_string(target.slice)
        if member_name in {
            "object",
            None,
            _DYNAMIC_STRING_BINDING,
        }:
            return namespace_kind
        return None

    def _record_object_namespace_target(
        self,
        target: ast.AST,
        *,
        deletion: bool = False,
    ) -> bool:
        if isinstance(target, ast.Starred):
            return self._record_object_namespace_target(target.value, deletion=deletion)
        if isinstance(target, (ast.Tuple, ast.List)):
            recorded = False
            for child in target.elts:
                recorded = (
                    self._record_object_namespace_target(child, deletion=deletion) or recorded
                )
            return recorded
        namespace_kind = self._object_namespace_target_kind(target)
        if namespace_kind is None:
            return False
        module_scope = self._module_scope()
        if namespace_kind == "builtins":
            module_scope.bind(
                _BUILTINS_OBJECT_STATE_NAME,
                reference=_POISONED_BUILTINS_OBJECT_REFERENCE,
                string=None,
                runtime_binding=False,
            )
            if module_scope.resolve_reference("object") == "builtins.object":
                module_scope.bind("object", reference=None, string=None)
            return True
        module_scope.bind(
            "object",
            reference=("builtins.object" if deletion and self._builtins_object_is_safe() else None),
            string=None,
        )
        return True

    def _record_object_namespace_kind(
        self,
        namespace_kind: str,
        *,
        deletion: bool = False,
    ) -> None:
        module_scope = self._module_scope()
        if namespace_kind == "builtins":
            module_scope.bind(
                _BUILTINS_OBJECT_STATE_NAME,
                reference=_POISONED_BUILTINS_OBJECT_REFERENCE,
                string=None,
                runtime_binding=False,
            )
            if module_scope.resolve_reference("object") == "builtins.object":
                module_scope.bind("object", reference=None, string=None)
            return
        if namespace_kind != "module":
            raise LegacyGrowthAnalysisError(
                f"{self.filename}: unsupported object namespace kind: {namespace_kind}"
            )
        module_scope.bind(
            "object",
            reference=("builtins.object" if deletion and self._builtins_object_is_safe() else None),
            string=None,
        )

    def _record_object_namespace_call_mutation(self, node: ast.Call) -> None:
        function_reference = self._resolve_reference(node.func)
        if function_reference in {"builtins.setattr", "builtins.delattr"}:
            if len(node.args) < 2 or node.keywords:
                return
            owner = node.args[0]
            owner_reference = self._resolve_reference(owner)
            namespace_kind = (
                "builtins"
                if owner_reference == "builtins"
                else ("module" if self._is_proven_current_module_object(owner) else None)
            )
            if namespace_kind is None:
                return
            member_name = self._resolve_string(node.args[1])
            if member_name not in {"object", None, _DYNAMIC_STRING_BINDING}:
                return
            self._record_object_namespace_kind(
                namespace_kind,
                deletion=function_reference == "builtins.delattr",
            )
            return

        if not isinstance(node.func, ast.Attribute):
            return
        namespace_kind = self._object_namespace_mapping_kind(node.func.value)
        if namespace_kind is None:
            return
        method = node.func.attr
        if method in {"clear", "popitem"}:
            self._record_object_namespace_kind(namespace_kind)
            return
        if method in {"__delitem__", "__setitem__", "pop", "setdefault"}:
            if not node.args:
                self._record_object_namespace_kind(namespace_kind)
                return
            member_name = self._resolve_string(node.args[0])
            if member_name not in {"object", None, _DYNAMIC_STRING_BINDING}:
                return
            self._record_object_namespace_kind(
                namespace_kind,
                deletion=method in {"__delitem__", "pop"},
            )
            return
        if method != "update":
            return
        keys: set[str | None] = {keyword.arg for keyword in node.keywords}
        for argument in node.args:
            if not isinstance(argument, ast.Dict):
                keys.add(None)
                continue
            keys.update(None if key is None else self._resolve_string(key) for key in argument.keys)
        if keys & {"object", None, _DYNAMIC_STRING_BINDING}:
            self._record_object_namespace_kind(namespace_kind)

    def _preserve_sensitive_reference(
        self,
        name: str,
        value: ast.AST,
        resolved_reference: str | None,
    ) -> str | None:
        if resolved_reference is not None:
            return resolved_reference
        if self._is_definitely_non_app_value(value):
            return _KNOWN_NON_APP_REFERENCE
        current = self.scope.resolve_reference(name)
        if current in {"pulseplate.app", _POSSIBLE_APP_REFERENCE}:
            return _POSSIBLE_APP_REFERENCE
        if current in {"pulseplate.app.router", _POSSIBLE_ROUTER_REFERENCE}:
            return _POSSIBLE_ROUTER_REFERENCE
        if current == _POSSIBLE_APP_CALL_REFERENCE or (
            current is not None
            and current.startswith("pulseplate.app.")
            and current.rsplit(".", maxsplit=1)[-1] in APP_ROUTE_METHODS | APP_REGISTRATION_METHODS
        ):
            return _POSSIBLE_APP_CALL_REFERENCE
        if current == _POSSIBLE_MIDDLEWARE_DECORATOR_REFERENCE or (
            current is not None and current.startswith(_MIDDLEWARE_DECORATOR_REFERENCE_PREFIX)
        ):
            return _POSSIBLE_MIDDLEWARE_DECORATOR_REFERENCE
        if current in {
            _ITERABLE_APP_ELEMENT_REFERENCE,
            _MAPPING_APP_VALUE_REFERENCE,
        }:
            return current
        if current in {
            _ITERABLE_SENSITIVE_ELEMENT_REFERENCE,
            _MAPPING_SENSITIVE_VALUE_REFERENCE,
        }:
            return current
        return None

    def _possible_sensitive_reference(self, name: str) -> str | None:
        current = self.scope.resolve_reference(name)
        if current in {"pulseplate.app", _POSSIBLE_APP_REFERENCE}:
            return _POSSIBLE_APP_REFERENCE
        if current in {"pulseplate.app.router", _POSSIBLE_ROUTER_REFERENCE}:
            return _POSSIBLE_ROUTER_REFERENCE
        if current == _POSSIBLE_APP_CALL_REFERENCE or (
            current is not None
            and current.startswith("pulseplate.app.")
            and current.rsplit(".", maxsplit=1)[-1] in APP_ROUTE_METHODS | APP_REGISTRATION_METHODS
        ):
            return _POSSIBLE_APP_CALL_REFERENCE
        if current == _POSSIBLE_MIDDLEWARE_DECORATOR_REFERENCE or (
            current is not None and current.startswith(_MIDDLEWARE_DECORATOR_REFERENCE_PREFIX)
        ):
            return _POSSIBLE_MIDDLEWARE_DECORATOR_REFERENCE
        if current in {
            _ITERABLE_APP_ELEMENT_REFERENCE,
            _ITERABLE_SENSITIVE_ELEMENT_REFERENCE,
            _MAPPING_APP_VALUE_REFERENCE,
            _MAPPING_SENSITIVE_VALUE_REFERENCE,
        }:
            return current
        return None

    def _bind_target_value(
        self,
        target: ast.expr,
        value: ast.AST,
        *,
        dynamic_unknown_string: bool,
    ) -> None:
        if (
            isinstance(target, (ast.Tuple, ast.List))
            and isinstance(value, (ast.Tuple, ast.List))
            and len(target.elts) == len(value.elts)
            and not any(isinstance(element, ast.Starred) for element in target.elts)
        ):
            for child_target, child_value in zip(target.elts, value.elts, strict=True):
                self._bind_target_value(
                    child_target,
                    child_value,
                    dynamic_unknown_string=dynamic_unknown_string,
                )
            return
        if isinstance(target, (ast.Tuple, ast.List)):
            iterable_element = self._resolve_iterable_element_binding(value)
            if iterable_element is not None:
                for child_target in target.elts:
                    child_binding = (
                        self._variadic_iterable_binding([iterable_element])
                        if isinstance(child_target, ast.Starred)
                        else iterable_element
                    )
                    self._bind_targets_from_resolved_binding(
                        [child_target],
                        child_binding,
                    )
                return
        resolved_string = self._resolve_string(value)
        resolved_reference = self._resolve_reference(value)
        callables = self._resolve_callables(value)
        deferred_calls = self._resolve_deferred_calls(value)
        mapping = self._resolve_mapping(value)
        class_references = self._resolve_class_references(value)
        descriptors = self._resolve_descriptors(value)
        iterable_element = self._resolve_iterable_element_binding(value)
        string = (
            resolved_string
            if resolved_string is not None
            else (_DYNAMIC_STRING_BINDING if dynamic_unknown_string else None)
        )
        for name in _assignment_target_names(target):
            self._bind_name(
                name,
                reference=self._preserve_sensitive_reference(
                    name,
                    value,
                    resolved_reference,
                ),
                string=string,
                callables=callables,
                deferred_calls=deferred_calls,
                mapping=mapping,
                class_references=class_references,
                descriptors=descriptors,
                iterable_element=iterable_element,
            )

    def _bind_iteration_target(self, target: ast.expr, iterable: ast.AST) -> None:
        self._record_object_namespace_target(target)
        if (
            isinstance(iterable, ast.Call)
            and isinstance(iterable.func, ast.Attribute)
            and iterable.func.attr == "items"
            and not iterable.args
            and not iterable.keywords
            and isinstance(target, (ast.Tuple, ast.List))
            and len(target.elts) == 2
        ):
            value_binding = self._resolve_mapping_value_binding(iterable.func.value)
            if value_binding is not None:
                self._bind_targets(
                    [target.elts[0]],
                    reference=_KNOWN_NON_APP_REFERENCE,
                    string=_DYNAMIC_STRING_BINDING,
                )
                self._bind_targets(
                    [target.elts[1]],
                    reference=value_binding.reference,
                    string=value_binding.string,
                    callables=value_binding.callables,
                    deferred_calls=value_binding.deferred_calls,
                    mapping=value_binding.mapping,
                    class_references=value_binding.class_references,
                    descriptors=value_binding.descriptors,
                    iterable_element=value_binding.iterable_element,
                )
                return
        iterable_element = self._resolve_iterable_element_binding(iterable)
        if iterable_element is not None and not isinstance(
            iterable,
            (ast.List, ast.Tuple, ast.Set),
        ):
            self._bind_targets(
                [target],
                reference=iterable_element.reference,
                string=iterable_element.string,
                callables=iterable_element.callables,
                deferred_calls=iterable_element.deferred_calls,
                mapping=iterable_element.mapping,
                class_references=iterable_element.class_references,
                descriptors=iterable_element.descriptors,
                iterable_element=iterable_element.iterable_element,
            )
            return
        iterable_reference = self._resolve_reference(iterable)
        if iterable_reference in {
            _ITERABLE_APP_ELEMENT_REFERENCE,
            _ITERABLE_SENSITIVE_ELEMENT_REFERENCE,
        }:
            self._bind_targets(
                [target],
                reference=(
                    _POSSIBLE_APP_REFERENCE
                    if iterable_reference == _ITERABLE_APP_ELEMENT_REFERENCE
                    else _POSSIBLE_APP_CALL_REFERENCE
                ),
                string=None,
            )
            return
        literal_values = (
            iterable.elts if isinstance(iterable, (ast.List, ast.Tuple, ast.Set)) else None
        )
        if not literal_values:
            for name in _assignment_target_names(target):
                self._bind_name(
                    name,
                    reference=self._possible_sensitive_reference(name),
                    string=None,
                )
            return
        incoming = self.scope
        outcomes: list[_LexicalBindings] = []
        for value in literal_values:
            self.scope = incoming.clone()
            item_value = value.value if isinstance(value, ast.Starred) else value
            self._bind_target_value(
                target,
                item_value,
                dynamic_unknown_string=False,
            )
            outcomes.append(self.scope)
        merged = incoming.clone()
        self._merge_outcomes(merged, outcomes)

    def _visit_function_header(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> None:
        decorator_bindings: list[frozenset[_FunctionNode]] = []
        for decorator in node.decorator_list:
            self.visit(decorator)
            decorator_bindings.append(self._resolve_callables(decorator))
        self._function_decorator_bindings[node] = tuple(decorator_bindings)
        for default in (*node.args.defaults, *node.args.kw_defaults):
            if default is not None:
                self.visit(default)
        for argument in _iter_function_parameters(node.args):
            if argument.annotation is not None and not self._postponed_annotations:
                self.visit(argument.annotation)
        if node.returns is not None and not self._postponed_annotations:
            self.visit(node.returns)

    def _resolve_decorated_function_binding(
        self,
        node: _FunctionNode,
    ) -> _ResolvedBinding:
        binding = _ResolvedBinding(None, None, frozenset({node}))
        if not self._replay_calls_enabled:
            return binding
        temporary_name = f"<decorated-function:{id(node)}>"
        captured_decorators = self._function_decorator_bindings.get(node, ())
        for decorator, targets in reversed(
            list(zip(node.decorator_list, captured_decorators, strict=True))
        ):
            if not targets:
                continue
            self.scope.bind(
                temporary_name,
                reference=binding.reference,
                string=binding.string,
                callables=binding.callables,
                descriptors=binding.descriptors,
            )
            synthetic_call = ast.Call(
                func=decorator,
                args=[ast.Name(id=temporary_name, ctx=ast.Load())],
                keywords=[],
            )
            results: list[_ResolvedBinding] = []
            for target in sorted(
                targets,
                key=lambda candidate: (
                    candidate.lineno,
                    candidate.col_offset,
                    candidate.name,
                ),
            ):
                arguments = self._resolve_call_argument_bindings(target, synthetic_call)
                if arguments is not None and not isinstance(target, ast.AsyncFunctionDef):
                    results.append(self._replay_function_call(target, arguments))
            self.scope.bind(temporary_name, reference=None, string=None)
            binding = self._join_resolved_bindings(results)
        return binding

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        self._visit_function_header(node)
        binding_node: _FunctionNode = node
        if self.scope.scope_kind != "module" and self._replay_calls_enabled:
            replay_context = (
                self._active_replay_contexts[-1] if self._active_replay_contexts else None
            )
            binding_key = (node, replay_context)
            binding_node = self._function_binding_nodes.get(binding_key, node)
            if binding_node is node:
                binding_node = copy.copy(node)
                self._function_binding_nodes[binding_key] = binding_node
            self._function_definition_scopes[binding_node] = self.scope
        positional_parameters = [*node.args.posonlyargs, *node.args.args]
        positional_default_parameters = (
            positional_parameters[-len(node.args.defaults) :] if node.args.defaults else []
        )
        default_bindings = {
            parameter.arg: self._capture_argument_binding(default)
            for parameter, default in zip(
                positional_default_parameters,
                node.args.defaults,
                strict=True,
            )
        }
        default_bindings.update(
            {
                parameter.arg: self._capture_argument_binding(default)
                for parameter, default in zip(
                    node.args.kwonlyargs,
                    node.args.kw_defaults,
                    strict=True,
                )
                if default is not None
            }
        )
        self._function_default_bindings[node] = default_bindings
        if binding_node is not node:
            self._function_default_bindings[binding_node] = default_bindings
        decorated_binding = self._resolve_decorated_function_binding(node)
        decorated_callables = frozenset(
            binding_node if candidate is node else candidate
            for candidate in decorated_binding.callables
        )
        decorated_reference = decorated_binding.reference
        if not node.decorator_list and decorated_reference is None:
            decorated_reference = _KNOWN_NON_APP_REFERENCE
        descriptor_kinds = {
            decorator_reference.rsplit(".", maxsplit=1)[-1]
            for decorator in node.decorator_list
            if (decorator_reference := self._resolve_reference(decorator))
            in {"builtins.classmethod", "builtins.staticmethod"}
        }
        descriptors = frozenset(
            (candidate, kind) for candidate in decorated_callables for kind in descriptor_kinds
        )
        self._bind_name(
            node.name,
            reference=decorated_reference,
            string=decorated_binding.string,
            callables=decorated_callables,
            descriptors=descriptors,
            overwrite_conflicts=True,
        )
        if not self.analyze_function_bodies:
            return
        lexical_parent = self.scope
        if lexical_parent.scope_kind == "class" and lexical_parent.parent is not None:
            lexical_parent = lexical_parent.parent
        if lexical_parent.scope_kind == "module" and (
            self.module_late_references or self.module_late_strings
        ):
            final_parent = lexical_parent.clone()
            final_parent.references = dict(self.module_late_references)
            final_parent.strings = dict(self.module_late_strings)
            late_parent = lexical_parent.clone()
            active_scope = self.scope
            self._merge_outcomes(
                late_parent,
                [lexical_parent.clone(), final_parent],
            )
            self.scope = active_scope
            lexical_parent = late_parent
        elif lexical_parent.scope_kind == "function" and self._function_late_bindings:
            late_references, late_strings, late_callables = self._function_late_bindings[-1]
            final_parent = lexical_parent.clone()
            final_parent.references = dict(late_references)
            final_parent.strings = dict(late_strings)
            final_parent.callables = dict(late_callables)
            late_parent = lexical_parent.clone()
            active_scope = self.scope
            self._merge_outcomes(
                late_parent,
                [lexical_parent.clone(), final_parent],
            )
            self.scope = active_scope
            lexical_parent = late_parent
        lexical_parent = lexical_parent.detached_clone()
        summary_visitor = _ApiKeyLookupVisitor(
            filename=self.filename,
            errors=[],
            preserve_fastapi_conflicts=self.preserve_fastapi_conflicts,
            preserve_lifecycle_conflicts=self.preserve_lifecycle_conflicts,
            preserve_route_method_conflicts=self.preserve_route_method_conflicts,
            analyze_function_bodies=False,
        )
        summary_visitor.scope = _LexicalBindings(
            parent=lexical_parent,
            local_names=_function_local_binding_names(node),
            scope_kind="function",
        )
        summary_visitor._visit_statements(node.body)
        function_late_bindings = (
            dict(summary_visitor.scope.references),
            dict(summary_visitor.scope.strings),
            dict(summary_visitor.scope.callables),
        )
        previous = self.scope
        previous_loop_controls = self._loop_controls
        previous_terminal_controls = self._terminal_controls
        previous_exception_scope_collectors = self._exception_scope_collectors
        previous_replay_calls_enabled = self._replay_calls_enabled
        previous_return_binding_collectors = self._return_binding_collectors
        self.scope = _LexicalBindings(
            parent=lexical_parent,
            local_names=_function_local_binding_names(node),
            scope_kind="function",
        )
        self._loop_controls = []
        self._terminal_controls = _TerminalControlBindings(return_scopes=[], raise_scopes=[])
        self._exception_scope_collectors = []
        self._return_binding_collectors = []
        self._function_late_bindings.append(function_late_bindings)
        definition_time_scan = node in self._definition_time_function_scans
        if definition_time_scan:
            for name, binding in default_bindings.items():
                self._bind_resolved_name(name, binding)
        newly_iterated_generator_ids = {
            id(candidate)
            for candidate in ast.walk(node)
            if definition_time_scan
            and isinstance(candidate, ast.GeneratorExp)
            and id(candidate) not in self._iterated_call_ids
        }
        self._iterated_call_ids.update(newly_iterated_generator_ids)
        self._replay_calls_enabled = (
            previous_replay_calls_enabled if definition_time_scan else False
        )
        try:
            self._visit_statements(node.body)
        finally:
            self._iterated_call_ids.difference_update(newly_iterated_generator_ids)
            self._function_late_bindings.pop()
            self.scope = previous
            self._loop_controls = previous_loop_controls
            self._terminal_controls = previous_terminal_controls
            self._exception_scope_collectors = previous_exception_scope_collectors
            self._replay_calls_enabled = previous_replay_calls_enabled
            self._return_binding_collectors = previous_return_binding_collectors

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        if not self.analyze_function_bodies:
            return
        synthetic = self._lambda_function_bindings.get(id(node))
        if synthetic is None:
            synthetic = ast.FunctionDef(
                name="<lambda>",
                args=node.args,
                body=[ast.Return(value=node.body)],
                decorator_list=[],
            )
            ast.copy_location(synthetic, node)
            self._lambda_function_bindings[id(node)] = synthetic
        if self.scope.scope_kind != "module":
            self._function_definition_scopes[synthetic] = self.scope
        self._definition_time_function_scans.add(synthetic)
        try:
            self._visit_function(synthetic)
        finally:
            self._definition_time_function_scans.remove(synthetic)

    def _build_class_mro(
        self,
        class_reference: str,
        base_references: Sequence[str],
    ) -> tuple[tuple[str, ...], bool]:
        sequences: list[list[str]] = []
        complete = True
        canonical_bases: list[str] = []
        for base_reference in base_references:
            if base_reference == "builtins.object":
                continue
            if not base_reference.startswith(_CLASS_REFERENCE_PREFIX):
                complete = False
                continue
            canonical_bases.append(base_reference)
            base_mro = self._class_mros.get(base_reference)
            if base_mro is None:
                complete = False
                base_mro = (base_reference,)
            elif not self._class_mro_complete.get(base_reference, False):
                complete = False
            sequences.append(list(base_mro))
        sequences.append(list(canonical_bases))
        merged: list[str] = []
        while any(sequences):
            sequences = [sequence for sequence in sequences if sequence]
            candidate = next(
                (
                    sequence[0]
                    for sequence in sequences
                    if all(sequence[0] not in other[1:] for other in sequences)
                ),
                None,
            )
            if candidate is None:
                complete = False
                for sequence in sequences:
                    for reference in sequence:
                        if reference not in merged:
                            merged.append(reference)
                break
            merged.append(candidate)
            for sequence in sequences:
                if sequence and sequence[0] == candidate:
                    sequence.pop(0)
        return (class_reference, *merged), complete

    def _publish_class_member_summaries(
        self,
        class_reference: str,
        instance_reference: str,
    ) -> None:
        mro = self._class_mros[class_reference]
        complete = self._class_mro_complete[class_reference]
        member_names = {
            member_name
            for owner_reference, member_name in self._class_direct_member_presence
            if owner_reference in mro
        }
        for member_name in member_names:
            candidates: frozenset[_FunctionNode] = frozenset()
            descriptors: frozenset[_DescriptorBinding] = frozenset()
            definitely_present = False
            possibly_present = False
            for owner_reference in mro:
                presence = self._class_direct_member_presence.get((owner_reference, member_name))
                if presence is None:
                    continue
                possibly_present = True
                direct_callables = self._class_direct_member_callables.get(
                    (owner_reference, member_name),
                    frozenset(),
                )
                candidates |= direct_callables
                descriptors |= self._class_direct_member_descriptors.get(
                    (owner_reference, member_name),
                    frozenset(),
                )
                proven_noncallable = self._class_direct_member_noncallable.get(
                    (owner_reference, member_name),
                    False,
                )
                if not presence:
                    continue
                definitely_present = True
                resolved_owner = bool(direct_callables) or proven_noncallable
                if resolved_owner and (complete or owner_reference == class_reference):
                    break
            if not possibly_present:
                continue
            self._class_member_presence[(class_reference, member_name)] = definitely_present
            self._class_member_presence[(instance_reference, member_name)] = definitely_present
            if candidates:
                self._class_member_callables[(class_reference, member_name)] = candidates
                self._class_member_callables[(instance_reference, member_name)] = candidates
            else:
                self._class_member_callables.pop((class_reference, member_name), None)
                self._class_member_callables.pop((instance_reference, member_name), None)
            if descriptors:
                self._class_member_descriptors[(class_reference, member_name)] = descriptors
                self._class_member_descriptors[(instance_reference, member_name)] = descriptors
            else:
                self._class_member_descriptors.pop((class_reference, member_name), None)
                self._class_member_descriptors.pop((instance_reference, member_name), None)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        decorator_targets: list[frozenset[_FunctionNode]] = []
        for decorator in node.decorator_list:
            self.visit(decorator)
            decorator_targets.append(self._resolve_callables(decorator))
        base_references: list[str] = []
        bases_complete = True
        for base in node.bases:
            self.visit(base)
            class_candidates = self._resolve_class_references(base)
            if class_candidates:
                if len(class_candidates) != 1:
                    bases_complete = False
                base_references.extend(sorted(class_candidates))
                continue
            base_reference = self._resolve_reference(base)
            if base_reference is not None:
                base_references.append(base_reference)
            else:
                bases_complete = False
        metaclass_targets: frozenset[_FunctionNode] = frozenset()
        for keyword in node.keywords:
            self.visit(keyword.value)
            if keyword.arg == "metaclass":
                metaclass_targets = self._resolve_callables(keyword.value)
        previous = self.scope
        self.scope = _LexicalBindings(parent=previous, scope_kind="class")
        self._visit_statements(node.body)
        class_scope = self.scope
        self.scope = previous
        result_binding = _ResolvedBinding(None, None)
        if metaclass_targets:
            metaclass_call = ast.Call(
                func=ast.Name(id="<metaclass>", ctx=ast.Load()),
                args=[ast.Constant(node.name), ast.Tuple(elts=[]), ast.Dict(keys=[], values=[])],
                keywords=[],
            )
            metaclass_results: list[_ResolvedBinding] = []
            for target in metaclass_targets:
                arguments = self._resolve_call_argument_bindings(target, metaclass_call)
                if arguments is not None:
                    metaclass_results.append(self._replay_function_call(target, arguments))
            result_binding = self._join_resolved_bindings(metaclass_results)
        for decorator, targets in reversed(
            list(zip(node.decorator_list, decorator_targets, strict=True))
        ):
            if not targets:
                continue
            temporary_name = f"<decorated-class:{id(node)}>"
            self.scope.bind(
                temporary_name,
                reference=result_binding.reference,
                string=result_binding.string,
                callables=result_binding.callables,
                descriptors=result_binding.descriptors,
            )
            decorator_call = ast.Call(
                func=decorator,
                args=[ast.Name(id=temporary_name, ctx=ast.Load())],
                keywords=[],
            )
            decorator_results: list[_ResolvedBinding] = []
            for target in targets:
                arguments = self._resolve_call_argument_bindings(target, decorator_call)
                if arguments is not None:
                    decorator_results.append(self._replay_function_call(target, arguments))
            result_binding = self._join_resolved_bindings(decorator_results)
            self.scope.bind(temporary_name, reference=None, string=None)
        class_reference = f"{_CLASS_REFERENCE_PREFIX}{node.name}:{id(node)}>"
        instance_reference = class_reference.replace(
            _CLASS_REFERENCE_PREFIX,
            _INSTANCE_REFERENCE_PREFIX,
            1,
        )
        new_mro, mro_complete = self._build_class_mro(class_reference, base_references)
        mro_complete = mro_complete and bases_complete
        seen_class_site = class_reference in self._class_mros
        if seen_class_site and self._class_mros[class_reference] != new_mro:
            new_mro = (
                class_reference,
                *dict.fromkeys(
                    [
                        *self._class_mros[class_reference][1:],
                        *new_mro[1:],
                    ]
                ),
            )
            mro_complete = False
        self._class_mros[class_reference] = new_mro
        self._class_mro_complete[class_reference] = mro_complete and (
            not seen_class_site or self._class_mro_complete[class_reference]
        )
        global_names, nonlocal_names = _statement_outward_binding_names(node.body)
        outward_names = global_names | nonlocal_names
        current_member_names = class_scope.possibly_bound_names - outward_names
        prior_member_names = {
            member_name
            for owner_reference, member_name in self._class_direct_member_presence
            if owner_reference == class_reference
        }
        for member_name in current_member_names | prior_member_names:
            current_present = member_name in current_member_names
            current_definite = current_present and member_name in class_scope.bound_names
            current_callables = (
                class_scope.callables.get(member_name, frozenset())
                if current_present
                else frozenset()
            )
            current_descriptors = (
                class_scope.descriptors.get(member_name, frozenset())
                if current_present
                else frozenset()
            )
            current_descriptors = frozenset(
                (
                    function,
                    "plain" if descriptor_kind == "unbound" else descriptor_kind,
                )
                for function, descriptor_kind in current_descriptors
            )
            described_callables = {function for function, _kind in current_descriptors}
            current_descriptors |= frozenset(
                (function, "plain")
                for function in current_callables
                if function not in described_callables
            )
            current_noncallable = (
                current_present
                and not current_callables
                and class_scope.references.get(member_name) == _KNOWN_NON_APP_REFERENCE
            )
            key = (class_reference, member_name)
            if seen_class_site:
                prior_definite = self._class_direct_member_presence.get(key, False)
                prior_callables = self._class_direct_member_callables.get(key, frozenset())
                prior_descriptors = self._class_direct_member_descriptors.get(
                    key,
                    frozenset(),
                )
                prior_noncallable = self._class_direct_member_noncallable.get(key, False)
                definitely_present = (
                    prior_definite and current_definite if current_present else False
                )
                callables = prior_callables | current_callables
                descriptors = prior_descriptors | current_descriptors
                proven_noncallable = (
                    prior_noncallable and current_noncallable and not callables and current_present
                )
            else:
                definitely_present = current_definite
                callables = current_callables
                descriptors = current_descriptors
                proven_noncallable = current_noncallable
            self._class_direct_member_presence[key] = definitely_present
            if callables:
                self._class_direct_member_callables[key] = callables
            else:
                self._class_direct_member_callables.pop(key, None)
            if descriptors:
                self._class_direct_member_descriptors[key] = descriptors
            else:
                self._class_direct_member_descriptors.pop(key, None)
            self._class_direct_member_noncallable[key] = proven_noncallable
        self._publish_class_member_summaries(class_reference, instance_reference)
        self._bind_name(
            node.name,
            reference=result_binding.reference or class_reference,
            string=result_binding.string,
            callables=result_binding.callables,
            class_references=(result_binding.class_references or frozenset({class_reference})),
            descriptors=result_binding.descriptors,
            overwrite_conflicts=True,
        )

    def visit_If(self, node: ast.If) -> bool:
        self.visit(node.test)
        if isinstance(node.test, ast.Constant):
            selected = node.body if bool(node.test.value) else node.orelse
            return self._visit_statements(selected)
        branches: list[Sequence[ast.stmt]] = [node.body]
        branches.append(node.orelse if node.orelse else ())
        return self._visit_branches(branches)

    def visit_IfExp(self, node: ast.IfExp) -> None:
        self.visit(node.test)
        if isinstance(node.test, ast.Constant):
            self.visit(node.body if bool(node.test.value) else node.orelse)
            return
        incoming = self.scope
        outcomes: list[_LexicalBindings] = []
        for branch in (node.body, node.orelse):
            self.scope = incoming.clone()
            self.visit(branch)
            outcomes.append(self.scope)
        self._merge_outcomes(incoming, outcomes)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        incoming = self.scope
        outcomes: list[_LexicalBindings] = []
        for index, value in enumerate(node.values):
            self.visit(value)
            current = self.scope.clone()
            if index == len(node.values) - 1:
                outcomes.append(current)
                break
            truth = bool(value.value) if isinstance(value, ast.Constant) else None
            short_circuits = (isinstance(node.op, ast.And) and truth is not True) or (
                isinstance(node.op, ast.Or) and truth is not False
            )
            if short_circuits:
                outcomes.append(current)
            always_short_circuits = (isinstance(node.op, ast.And) and truth is False) or (
                isinstance(node.op, ast.Or) and truth is True
            )
            if always_short_circuits:
                break
        self._merge_outcomes(incoming, outcomes)

    def _visit_try(self, node: ast.Try | ast.TryStar) -> bool:
        loop_controls = self._loop_controls[-1] if self._loop_controls else None
        break_offset = len(loop_controls.break_scopes) if loop_controls is not None else 0
        continue_offset = len(loop_controls.continue_scopes) if loop_controls is not None else 0
        terminal_controls = self._terminal_controls
        return_offset = len(terminal_controls.return_scopes)
        raise_offset = len(terminal_controls.raise_scopes)
        incoming = self.scope
        try_scope = incoming.clone()
        self.scope = try_scope
        try_falls_through, exception_entry_scopes = self._visit_with_exception_scopes(node.body)

        body_raise_scopes = terminal_controls.raise_scopes[raise_offset:]
        del terminal_controls.raise_scopes[raise_offset:]

        handler_entry = incoming.clone()
        self._merge_outcomes(
            handler_entry,
            [
                incoming.clone(),
                try_scope,
                *exception_entry_scopes,
                *body_raise_scopes,
            ],
        )
        handler_outcomes: list[_LexicalBindings] = []
        handler_exception_scopes: list[_LexicalBindings] = []
        next_handler_entry = handler_entry
        trystar_handler_scopes: list[_LexicalBindings] = []
        for handler in node.handlers:
            self.scope = next_handler_entry.clone()
            self._exception_scope_collectors.append(handler_exception_scopes)
            try:
                if handler.type is not None:
                    self._record_exception_scope()
                    self.visit(handler.type)
                    self._record_exception_scope()
                after_type_scope = self.scope.clone()
                if isinstance(node, ast.TryStar) and trystar_handler_scopes:
                    handler_body_entry = after_type_scope.clone()
                    self._merge_outcomes(
                        handler_body_entry,
                        [after_type_scope, *trystar_handler_scopes],
                    )
                if handler.name is not None:
                    self._bind_name(handler.name, reference=None, string=None)
                handler_falls_through = self._visit_statements(handler.body)
                if handler.name is not None:
                    self.scope.unbind(handler.name)
            finally:
                self._exception_scope_collectors.pop()
            if handler_falls_through:
                handler_outcomes.append(self.scope)
            if isinstance(node, ast.TryStar):
                trystar_handler_scopes.append(self.scope)
                next_handler_entry = after_type_scope.clone()
                self._merge_outcomes(
                    next_handler_entry,
                    [after_type_scope, *trystar_handler_scopes],
                )
            else:
                next_handler_entry = after_type_scope

        normal_outcomes = handler_outcomes
        else_exception_scopes: list[_LexicalBindings] = []
        if try_falls_through:
            self.scope = try_scope
            else_falls_through, else_exception_scopes = self._visit_with_exception_scopes(
                node.orelse
            )
            if else_falls_through:
                normal_outcomes.append(self.scope)
        if normal_outcomes:
            self._merge_outcomes(incoming, normal_outcomes)
        else:
            self.scope = incoming
        abrupt_break_scopes: list[_LexicalBindings] = []
        abrupt_continue_scopes: list[_LexicalBindings] = []
        if loop_controls is not None:
            abrupt_break_scopes = loop_controls.break_scopes[break_offset:]
            abrupt_continue_scopes = loop_controls.continue_scopes[continue_offset:]
            del loop_controls.break_scopes[break_offset:]
            del loop_controls.continue_scopes[continue_offset:]
        abrupt_return_scopes = terminal_controls.return_scopes[return_offset:]
        catches_all_body_exceptions = any(handler.type is None for handler in node.handlers)
        abrupt_raise_scopes = [] if catches_all_body_exceptions else list(body_raise_scopes)
        if not catches_all_body_exceptions:
            abrupt_raise_scopes.extend(exception_entry_scopes)
        abrupt_raise_scopes.extend(handler_exception_scopes)
        abrupt_raise_scopes.extend(else_exception_scopes)
        abrupt_raise_scopes.extend(terminal_controls.raise_scopes[raise_offset:])
        del terminal_controls.return_scopes[return_offset:]
        del terminal_controls.raise_scopes[raise_offset:]
        normal_falls_through = False
        normal_final_scope = incoming
        if normal_outcomes:
            normal_falls_through = self._visit_statements(node.finalbody)
            if normal_falls_through:
                normal_final_scope = self.scope
        if loop_controls is not None:
            finalized_break_scopes: list[_LexicalBindings] = []
            for abrupt_scope in abrupt_break_scopes:
                self.scope = abrupt_scope.clone()
                if self._visit_statements(node.finalbody):
                    finalized_break_scopes.append(self.scope)
            finalized_continue_scopes: list[_LexicalBindings] = []
            for abrupt_scope in abrupt_continue_scopes:
                self.scope = abrupt_scope.clone()
                if self._visit_statements(node.finalbody):
                    finalized_continue_scopes.append(self.scope)
            loop_controls.break_scopes.extend(finalized_break_scopes)
            loop_controls.continue_scopes.extend(finalized_continue_scopes)
        finalized_return_scopes: list[_LexicalBindings] = []
        for abrupt_scope in abrupt_return_scopes:
            self.scope = abrupt_scope.clone()
            if self._visit_statements(node.finalbody):
                finalized_return_scopes.append(self.scope)
        finalized_raise_scopes: list[_LexicalBindings] = []
        for abrupt_scope in abrupt_raise_scopes:
            self.scope = abrupt_scope.clone()
            if self._visit_statements(node.finalbody):
                finalized_raise_scopes.append(self.scope)
        terminal_controls.return_scopes.extend(finalized_return_scopes)
        terminal_controls.raise_scopes.extend(finalized_raise_scopes)
        self.scope = normal_final_scope
        return normal_falls_through

    def visit_Try(self, node: ast.Try) -> bool:
        return self._visit_try(node)

    def visit_TryStar(self, node: ast.TryStar) -> bool:
        return self._visit_try(node)

    def _visit_for(self, node: ast.For | ast.AsyncFor) -> bool:
        self._visit_iterated_expression(node.iter)
        incoming = self.scope
        if (
            isinstance(node, ast.For)
            and isinstance(node.iter, (ast.List, ast.Tuple))
            and not node.iter.elts
        ):
            return self._finish_loop(
                incoming=incoming,
                normal_entries=[incoming.clone()],
                break_scopes=[],
                orelse=node.orelse,
            )
        definitely_nonempty = (
            isinstance(node, ast.For)
            and isinstance(node.iter, (ast.List, ast.Tuple, ast.Set))
            and bool(node.iter.elts)
            and all(not isinstance(element, ast.Starred) for element in node.iter.elts)
        )
        loop_head = incoming.clone()
        for target_name in {
            *_assignment_target_names(node.target),
            *_statement_binding_names(node.body),
        }:
            loop_head.possibly_bound_names.add(target_name)
        break_scopes: list[_LexicalBindings] = []
        body_scope: _LexicalBindings | None = None
        controls = _LoopControlBindings(break_scopes=[], continue_scopes=[])
        for _iteration in range(_MAX_LOOP_BINDING_ITERATIONS):
            self._consume_loop_iteration()
            self.scope = loop_head.clone()
            self._bind_iteration_target(node.target, node.iter)
            body_scope, controls = self._visit_loop_body(node.body)
            break_scopes.extend(controls.break_scopes)
            carried_scopes = [
                *([body_scope] if body_scope is not None else []),
                *controls.continue_scopes,
            ]
            if not carried_scopes:
                break
            next_head = loop_head.clone()
            self._merge_outcomes(
                next_head,
                [loop_head, *carried_scopes],
            )
            if self._bindings_equal(loop_head, next_head):
                break
            loop_head = next_head
        else:
            raise LegacyGrowthAnalysisError(
                f"{self.filename}: loop binding analysis did not converge within "
                f"{_MAX_LOOP_BINDING_ITERATIONS} iterations"
            )
        normal_entries = [
            *([] if definitely_nonempty else [incoming.clone()]),
            *([body_scope] if body_scope is not None else []),
            *controls.continue_scopes,
        ]
        return self._finish_loop(
            incoming=incoming,
            normal_entries=normal_entries,
            break_scopes=break_scopes,
            orelse=node.orelse,
        )

    def visit_For(self, node: ast.For) -> bool:
        return self._visit_for(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> bool:
        return self._visit_for(node)

    def visit_Break(self, node: ast.Break) -> bool:
        if self._loop_controls:
            self._loop_controls[-1].break_scopes.append(self.scope.clone())
        return False

    def visit_Continue(self, node: ast.Continue) -> bool:
        if self._loop_controls:
            self._loop_controls[-1].continue_scopes.append(self.scope.clone())
        return False

    def visit_Return(self, node: ast.Return) -> bool:
        if node.value is not None:
            self.visit(node.value)
        if self._return_binding_collectors:
            self._return_binding_collectors[-1].append(
                _ResolvedBinding(None, None)
                if node.value is None
                else self._capture_argument_binding(node.value)
            )
        self._terminal_controls.return_scopes.append(self.scope.clone())
        return False

    def visit_Raise(self, node: ast.Raise) -> bool:
        if node.exc is not None:
            self.visit(node.exc)
        if node.cause is not None:
            self.visit(node.cause)
        self._terminal_controls.raise_scopes.append(self.scope.clone())
        return False

    def visit_While(self, node: ast.While) -> bool:
        self.visit(node.test)
        incoming = self.scope
        constant_truth = bool(node.test.value) if isinstance(node.test, ast.Constant) else None
        if constant_truth is False:
            return self._finish_loop(
                incoming=incoming,
                normal_entries=[incoming.clone()],
                break_scopes=[],
                orelse=node.orelse,
            )
        definitely_true = constant_truth is True
        loop_head = incoming.clone()
        break_scopes: list[_LexicalBindings] = []
        exhaustion_scope: _LexicalBindings | None = None
        controls = _LoopControlBindings(break_scopes=[], continue_scopes=[])
        for _iteration in range(_MAX_LOOP_BINDING_ITERATIONS):
            self._consume_loop_iteration()
            self.scope = loop_head.clone()
            body_scope, controls = self._visit_loop_body(node.body)
            break_scopes.extend(controls.break_scopes)
            carried_scopes = [
                *([body_scope] if body_scope is not None else []),
                *controls.continue_scopes,
            ]
            if not carried_scopes:
                break
            carried = loop_head.clone()
            self._merge_outcomes(
                carried,
                [loop_head, *carried_scopes],
            )
            self.visit(node.test)
            conditioned_scope = self.scope
            if not definitely_true:
                exhaustion_scope = conditioned_scope
            next_head = loop_head.clone()
            self._merge_outcomes(next_head, [loop_head, conditioned_scope])
            if self._bindings_equal(loop_head, next_head):
                break
            loop_head = next_head
        else:
            raise LegacyGrowthAnalysisError(
                f"{self.filename}: loop binding analysis did not converge within "
                f"{_MAX_LOOP_BINDING_ITERATIONS} iterations"
            )
        normal_entries = [
            *([] if definitely_true else [incoming.clone()]),
            *([exhaustion_scope] if exhaustion_scope is not None else []),
        ]
        return self._finish_loop(
            incoming=incoming,
            normal_entries=normal_entries,
            break_scopes=break_scopes,
            orelse=node.orelse,
        )

    def _resolve_with_enter_binding(self, context_expr: ast.AST) -> _ResolvedBinding:
        if (
            isinstance(context_expr, ast.Call)
            and self._resolve_reference(context_expr.func) == "asyncio.TaskGroup"
        ):
            return _ResolvedBinding("asyncio.TaskGroup.instance", None)
        if (
            isinstance(context_expr, ast.Call)
            and self._resolve_reference(context_expr.func) == "contextlib.nullcontext"
        ):
            positional = [
                argument for argument in context_expr.args if not isinstance(argument, ast.Starred)
            ]
            keyword = [item.value for item in context_expr.keywords if item.arg == "enter_result"]
            unresolved = any(isinstance(argument, ast.Starred) for argument in context_expr.args)
            unresolved = unresolved or any(item.arg is None for item in context_expr.keywords)
            candidates = [*positional, *keyword]
            if len(candidates) == 1 and not unresolved:
                return self._capture_argument_binding(candidates[0])
            if not candidates and not unresolved:
                return _ResolvedBinding(_KNOWN_NON_APP_REFERENCE, None)
            return self._conservative_argument_binding()

        binding = self._capture_argument_binding(context_expr)
        reference = self._resolve_reference(context_expr)
        if reference is None and isinstance(context_expr, ast.Call) and context_expr.args:
            argument_reference = self._resolve_reference(context_expr.args[0])
            if argument_reference in {
                "pulseplate.app",
                "pulseplate.app.router",
                _POSSIBLE_APP_REFERENCE,
                _POSSIBLE_ROUTER_REFERENCE,
                _POSSIBLE_APP_CALL_REFERENCE,
            }:
                reference = (
                    _POSSIBLE_APP_REFERENCE
                    if argument_reference in {"pulseplate.app", _POSSIBLE_APP_REFERENCE}
                    else (
                        _POSSIBLE_ROUTER_REFERENCE
                        if argument_reference
                        in {"pulseplate.app.router", _POSSIBLE_ROUTER_REFERENCE}
                        else _POSSIBLE_APP_CALL_REFERENCE
                    )
                )
        if reference is None:
            reference = binding.reference
        return _ResolvedBinding(
            reference=reference,
            string=self._resolve_string(context_expr),
            callables=binding.callables,
            deferred_calls=binding.deferred_calls,
            mapping=binding.mapping,
            class_references=binding.class_references,
            descriptors=binding.descriptors,
            iterable_element=binding.iterable_element,
        )

    def _visit_with(self, node: ast.With | ast.AsyncWith) -> bool:
        enters_task_group = isinstance(node, ast.AsyncWith) and any(
            isinstance(item.context_expr, ast.Call)
            and self._resolve_reference(item.context_expr.func) == "asyncio.TaskGroup"
            for item in node.items
        )
        for item in node.items:
            self.visit(item.context_expr)
            if item.optional_vars is not None:
                self._record_object_namespace_target(item.optional_vars)
                binding = self._resolve_with_enter_binding(item.context_expr)
                for name in _assignment_target_names(item.optional_vars):
                    reference = (
                        binding.reference
                        if binding.reference is not None
                        else self._possible_sensitive_reference(name)
                    )
                    self._bind_resolved_name(
                        name,
                        _ResolvedBinding(
                            reference=reference,
                            string=binding.string,
                            callables=binding.callables,
                            deferred_calls=binding.deferred_calls,
                            mapping=binding.mapping,
                            class_references=binding.class_references,
                            descriptors=binding.descriptors,
                            iterable_element=binding.iterable_element,
                        ),
                    )
        if enters_task_group:
            self._active_task_group_depth += 1
        try:
            return self._visit_statements(node.body)
        finally:
            if enters_task_group:
                self._active_task_group_depth -= 1

    def visit_With(self, node: ast.With) -> bool:
        return self._visit_with(node)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> bool:
        return self._visit_with(node)

    @staticmethod
    def _is_irrefutable_pattern(pattern: ast.pattern) -> bool:
        if isinstance(pattern, ast.MatchAs):
            return pattern.pattern is None or _ApiKeyLookupVisitor._is_irrefutable_pattern(
                pattern.pattern
            )
        if isinstance(pattern, ast.MatchOr):
            return any(
                _ApiKeyLookupVisitor._is_irrefutable_pattern(candidate)
                for candidate in pattern.patterns
            )
        return False

    def _bind_match_capture(self, name: str, value: ast.AST | None) -> None:
        binding = (
            self._capture_argument_binding(value)
            if value is not None
            else _ResolvedBinding(None, None)
        )
        self._bind_resolved_name(
            name,
            binding,
            overwrite_conflicts=True,
        )

    def _bind_match_pattern(self, pattern: ast.pattern, subject: ast.AST) -> None:
        if isinstance(pattern, ast.MatchAs):
            if pattern.name is not None:
                self._bind_match_capture(pattern.name, subject)
            if pattern.pattern is not None:
                self._bind_match_pattern(pattern.pattern, subject)
            return
        if isinstance(pattern, ast.MatchStar):
            if pattern.name is not None:
                self._bind_match_capture(pattern.name, None)
            return
        if isinstance(pattern, ast.MatchSequence) and isinstance(subject, (ast.List, ast.Tuple)):
            star_indexes = [
                index
                for index, child_pattern in enumerate(pattern.patterns)
                if isinstance(child_pattern, ast.MatchStar)
            ]
            if not star_indexes and len(pattern.patterns) == len(subject.elts):
                for child_pattern, child_subject in zip(
                    pattern.patterns,
                    subject.elts,
                    strict=True,
                ):
                    self._bind_match_pattern(child_pattern, child_subject)
                return
            if len(star_indexes) == 1:
                star_index = star_indexes[0]
                suffix_count = len(pattern.patterns) - star_index - 1
                if len(subject.elts) >= star_index + suffix_count:
                    for child_pattern, child_subject in zip(
                        pattern.patterns[:star_index],
                        subject.elts[:star_index],
                        strict=True,
                    ):
                        self._bind_match_pattern(child_pattern, child_subject)
                    self._bind_match_pattern(pattern.patterns[star_index], subject)
                    if suffix_count:
                        for child_pattern, child_subject in zip(
                            pattern.patterns[-suffix_count:],
                            subject.elts[-suffix_count:],
                            strict=True,
                        ):
                            self._bind_match_pattern(child_pattern, child_subject)
                    return
        if isinstance(pattern, ast.MatchMapping):
            subject_values = (
                {
                    self._resolve_string(key): value
                    for key, value in zip(subject.keys, subject.values, strict=True)
                    if key is not None and self._resolve_string(key) is not None
                }
                if isinstance(subject, ast.Dict)
                else {}
            )
            for key, child_pattern in zip(pattern.keys, pattern.patterns, strict=True):
                self._bind_match_pattern(
                    child_pattern,
                    subject_values.get(self._resolve_string(key), subject),
                )
            if pattern.rest is not None:
                self._bind_match_capture(pattern.rest, None)
            return
        captured_names = {
            child.name
            for child in ast.walk(pattern)
            if isinstance(child, (ast.MatchAs, ast.MatchStar)) and child.name is not None
        }
        if isinstance(pattern, ast.MatchMapping) and pattern.rest is not None:
            captured_names.add(pattern.rest)
        for name in captured_names:
            self._bind_match_capture(name, subject)

    def visit_Match(self, node: ast.Match) -> bool:
        self.visit(node.subject)
        incoming = self.scope
        outcomes: list[_LexicalBindings] = []
        next_case_entry: _LexicalBindings | None = incoming.clone()
        for case in node.cases:
            if next_case_entry is None:
                break
            pattern_failure_scope = next_case_entry.clone()
            self.scope = next_case_entry.clone()
            self.visit(case.pattern)
            self._bind_match_pattern(case.pattern, node.subject)
            guard_truth: bool | None = True
            if case.guard is not None:
                self.visit(case.guard)
                guard_truth = (
                    bool(case.guard.value) if isinstance(case.guard, ast.Constant) else None
                )
            guard_false_scope = self.scope.clone()
            if guard_truth is not False and self._visit_statements(case.body):
                outcomes.append(self.scope)
            irrefutable = self._is_irrefutable_pattern(case.pattern)
            remaining_entries: list[_LexicalBindings] = []
            if not irrefutable:
                remaining_entries.append(pattern_failure_scope)
            if guard_truth is not True:
                remaining_entries.append(guard_false_scope)
            if not remaining_entries:
                next_case_entry = None
                continue
            next_case_entry = pattern_failure_scope.clone()
            self._merge_outcomes(next_case_entry, remaining_entries)
        if next_case_entry is not None:
            outcomes.append(next_case_entry)
        if not outcomes:
            self.scope = incoming
            return False
        self._merge_outcomes(incoming, outcomes)
        return True

    def _visit_comprehension(
        self,
        generators: Sequence[ast.comprehension],
        result_nodes: Sequence[ast.AST],
        *,
        deferred: bool = False,
        outer_binding: _ResolvedBinding | None = None,
    ) -> None:
        if not generators:
            for result_node in result_nodes:
                self.visit(result_node)
            return
        if (
            outer_binding is None
            and isinstance(generators[0].iter, (ast.List, ast.Tuple, ast.Set))
            and not (generators[0].iter.elts)
        ):
            self.visit(generators[0].iter)
            return
        if outer_binding is not None:
            self._replay_deferred_calls(
                self._resolve_deferred_calls(generators[0].iter),
                execution="iterate",
            )
        elif deferred:
            self.visit(generators[0].iter)
        else:
            self._visit_iterated_expression(generators[0].iter)
        local_names = frozenset(
            name for generator in generators for name in _assignment_target_names(generator.target)
        )
        previous = self.scope
        previous_exception_scope_collectors = self._exception_scope_collectors
        previous_replay_calls_enabled = self._replay_calls_enabled
        self.scope = _LexicalBindings(
            parent=previous,
            local_names=local_names,
            scope_kind="comprehension",
        )
        if deferred:
            self._exception_scope_collectors = []
            self._replay_calls_enabled = False
        try:
            for index, generator in enumerate(generators):
                if index:
                    if isinstance(generator.iter, (ast.List, ast.Tuple, ast.Set)) and not (
                        generator.iter.elts
                    ):
                        self.visit(generator.iter)
                        return
                    if deferred:
                        self.visit(generator.iter)
                    else:
                        self._visit_iterated_expression(generator.iter)
                if index == 0 and outer_binding is not None:
                    self._bind_targets(
                        [generator.target],
                        reference=outer_binding.reference,
                        string=outer_binding.string,
                        callables=outer_binding.callables,
                        deferred_calls=outer_binding.deferred_calls,
                    )
                else:
                    self._bind_iteration_target(generator.target, generator.iter)
                for condition in generator.ifs:
                    self.visit(condition)
                    if isinstance(condition, ast.Constant) and not bool(condition.value):
                        return
            for result_node in result_nodes:
                self.visit(result_node)
        finally:
            self.scope = previous
            self._exception_scope_collectors = previous_exception_scope_collectors
            self._replay_calls_enabled = previous_replay_calls_enabled

    def visit_ListComp(self, node: ast.ListComp) -> None:
        self._visit_comprehension(node.generators, [node.elt])

    def _visit_collection_elements(self, elements: Sequence[ast.expr]) -> None:
        for element in elements:
            value = element.value if isinstance(element, ast.Starred) else element
            self.visit(value)
            if not isinstance(element, ast.Starred):
                self._invalidate_mapping_aliases(value)

    def visit_List(self, node: ast.List) -> None:
        self._visit_collection_elements(node.elts)

    def visit_Tuple(self, node: ast.Tuple) -> None:
        self._visit_collection_elements(node.elts)

    def visit_Set(self, node: ast.Set) -> None:
        self._visit_collection_elements(node.elts)

    def visit_Dict(self, node: ast.Dict) -> None:
        entries: list[_StaticMappingEntry] = []
        escaped_mappings: list[_StaticMapping] = []
        for key, value in zip(node.keys, node.values, strict=True):
            if key is None:
                self.visit(value)
                unpacked = self._resolve_mapping(value)
                if unpacked is None:
                    entries.append(
                        _StaticMappingEntry(
                            key=None,
                            binding=self._conservative_argument_binding(),
                        )
                    )
                else:
                    entries.extend(unpacked.entries)
                continue
            self.visit(key)
            self.visit(value)
            binding = self._capture_argument_binding(value)
            if binding.mapping is not None:
                escaped_mappings.append(binding.mapping)
                binding = _ResolvedBinding(
                    reference=_MAPPING_SENSITIVE_VALUE_REFERENCE,
                    string=binding.string,
                    callables=binding.callables,
                    deferred_calls=binding.deferred_calls,
                    class_references=binding.class_references,
                    descriptors=binding.descriptors,
                    iterable_element=binding.iterable_element,
                )
            entries.append(_StaticMappingEntry(key=key, binding=binding))
        candidate = _StaticMapping(site=node, entries=tuple(entries))
        snapshot = self._mapping_snapshot_intern.setdefault(candidate, candidate)
        self._mapping_literal_snapshots[id(node)] = snapshot
        for mapping in escaped_mappings:
            self._invalidate_mapping(mapping)

    def visit_SetComp(self, node: ast.SetComp) -> None:
        self._visit_comprehension(node.generators, [node.elt])

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> None:
        if id(node) in self._iterated_call_ids:
            self._visit_comprehension(node.generators, [node.elt])
            return
        if node.generators:
            self.visit(node.generators[0].iter)
        synthetic = ast.FunctionDef(
            name="<generator-expression>",
            args=ast.arguments(
                posonlyargs=[],
                args=[],
                kwonlyargs=[],
                kw_defaults=[],
                defaults=[],
            ),
            body=[],
            decorator_list=[],
        )
        ast.copy_location(synthetic, node)
        self._deferred_generator_expressions[synthetic] = node
        self._deferred_generator_scopes[synthetic] = self.scope
        self._deferred_generator_outer_bindings[synthetic] = (
            self._capture_iterable_element_binding(node.generators[0].iter)
            if node.generators
            else _ResolvedBinding(None, None)
        )
        self._deferred_call_bindings[id(node)] = frozenset(
            {_DeferredFunctionCall(function=synthetic, arguments=())}
        )

    def _visit_iterated_expression(self, node: ast.AST) -> None:
        node_id = id(node)
        was_iterated = node_id in self._iterated_call_ids
        self._iterated_call_ids.add(node_id)
        try:
            self.visit(node)
            self._replay_deferred_calls(
                self._resolve_deferred_calls(node),
                execution="iterate",
            )
        finally:
            if not was_iterated:
                self._iterated_call_ids.remove(node_id)

    def visit_YieldFrom(self, node: ast.YieldFrom) -> None:
        self._visit_iterated_expression(node.value)

    def _resolve_mapping_value_binding(
        self,
        node: ast.AST,
    ) -> _ResolvedBinding | None:
        stored = (
            self.scope.resolve_iterable_element(node.id) if isinstance(node, ast.Name) else None
        )
        if stored is not None:
            return stored
        mapping = self._resolve_mapping(node)
        if mapping is not None:
            if not mapping.entries:
                return _ResolvedBinding(None, None)
            return self._join_resolved_bindings([entry.binding for entry in mapping.entries])
        reference = self._resolve_reference(node)
        if reference in {
            _MAPPING_APP_VALUE_REFERENCE,
            _MAPPING_SENSITIVE_VALUE_REFERENCE,
        }:
            return _ResolvedBinding(
                reference=(
                    _POSSIBLE_APP_REFERENCE
                    if reference == _MAPPING_APP_VALUE_REFERENCE
                    else _POSSIBLE_APP_CALL_REFERENCE
                ),
                string=_DYNAMIC_STRING_BINDING,
            )
        return None

    def _resolve_iterable_element_binding(
        self,
        node: ast.AST,
    ) -> _ResolvedBinding | None:
        call_result = self._call_result_bindings.get(id(node))
        if call_result is not None:
            return call_result.iterable_element
        if isinstance(node, ast.Await):
            return self._resolve_iterable_element_binding(node.value)
        if isinstance(node, ast.NamedExpr):
            return self._resolve_iterable_element_binding(node.value)
        if isinstance(node, ast.Name):
            return self.scope.resolve_iterable_element(node.id)
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in {"items", "values"}
            and not node.args
            and not node.keywords
        ):
            return self._resolve_mapping_value_binding(node.func.value)
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)) and node.elts:
            element_bindings: list[_ResolvedBinding] = []
            for element in node.elts:
                if not isinstance(element, ast.Starred):
                    element_bindings.append(self._capture_argument_binding(element))
                    continue
                nested = self._resolve_iterable_element_binding(element.value)
                element_bindings.append(
                    nested if nested is not None else self._conservative_argument_binding()
                )
            return self._join_resolved_bindings(element_bindings)
        return None

    def _capture_iterable_element_binding(self, node: ast.AST) -> _ResolvedBinding:
        iterable_element = self._resolve_iterable_element_binding(node)
        if iterable_element is not None:
            return iterable_element
        reference = self._resolve_reference(node)
        if reference in {
            _ITERABLE_APP_ELEMENT_REFERENCE,
            _ITERABLE_SENSITIVE_ELEMENT_REFERENCE,
        }:
            reference = (
                _POSSIBLE_APP_REFERENCE
                if reference == _ITERABLE_APP_ELEMENT_REFERENCE
                else _POSSIBLE_APP_CALL_REFERENCE
            )
        return _ResolvedBinding(
            reference=reference,
            string=self._resolve_string(node),
            callables=self._resolve_callables(node),
            deferred_calls=self._resolve_deferred_calls(node),
            mapping=self._resolve_mapping(node),
            class_references=self._resolve_class_references(node),
            descriptors=self._resolve_descriptors(node),
        )

    def visit_DictComp(self, node: ast.DictComp) -> None:
        self._visit_comprehension(node.generators, [node.key, node.value])

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            local_name = alias.asname or alias.name.split(".", maxsplit=1)[0]
            reference = alias.name if alias.asname is not None else alias.name.partition(".")[0]
            self._bind_name(local_name, reference=reference, string=None)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module == "legacy_app":
            for alias in node.names:
                if alias.name == "*":
                    self.errors.append(
                        f"{self.filename}: canonical code must not use a legacy_app star import"
                    )
                elif alias.name in CANONICAL_API_KEY_SYMBOLS:
                    self.errors.append(
                        f"{self.filename}: canonical code must import API-key dependency "
                        f"from {CANONICAL_API_KEY}, not legacy_app: {alias.name}"
                    )
        for alias in node.names:
            if alias.name == "*":
                continue
            local_name = alias.asname or alias.name
            reference = f"{node.module}.{alias.name}" if node.module is not None else None
            self._bind_name(local_name, reference=reference, string=None)

    def visit_Assign(self, node: ast.Assign) -> None:
        self.visit(node.value)
        value_mapping = self._resolve_mapping(node.value)
        for target in node.targets:
            self._invalidate_mapping_target(target)
            self._record_object_namespace_target(target)
            self._bind_target_value(
                target,
                node.value,
                dynamic_unknown_string=True,
            )
        if value_mapping is not None and any(
            _assignment_target_escapes_value(target) for target in node.targets
        ):
            self._invalidate_mapping(value_mapping)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if not self._postponed_annotations:
            self.visit(node.annotation)
        if node.value is None:
            if not isinstance(node.target, ast.Name):
                self.visit(node.target)
            return
        self.visit(node.value)
        value_mapping = self._resolve_mapping(node.value)
        self._invalidate_mapping_target(node.target)
        self._record_object_namespace_target(node.target)
        self._bind_target_value(
            node.target,
            node.value,
            dynamic_unknown_string=True,
        )
        if value_mapping is not None and _assignment_target_escapes_value(node.target):
            self._invalidate_mapping(value_mapping)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        self.visit(node.target)
        self.visit(node.value)
        target_mapping = self._resolve_mapping(node.target)
        if target_mapping is not None:
            self._invalidate_mapping(target_mapping)
        self._invalidate_mapping_target(node.target)
        self._record_object_namespace_target(node.target)
        if isinstance(node.target, ast.Name):
            self._bind_name(
                node.target.id,
                reference=self._possible_sensitive_reference(node.target.id),
                string=None,
            )

    def visit_NamedExpr(self, node: ast.NamedExpr) -> None:
        self.visit(node.value)
        active_scope = self.scope
        if active_scope.scope_kind == "comprehension":
            containing_scope = active_scope.parent
            while containing_scope is not None and containing_scope.scope_kind == "comprehension":
                containing_scope = containing_scope.parent
            if containing_scope is not None:
                self.scope = containing_scope
        try:
            self._bind_target_value(
                node.target,
                node.value,
                dynamic_unknown_string=True,
            )
        finally:
            self.scope = active_scope

    def visit_Delete(self, node: ast.Delete) -> None:
        for target in node.targets:
            namespace_target_recorded = self._record_object_namespace_target(
                target,
                deletion=True,
            )
            names = _assignment_target_names(target)
            if not names:
                self.visit(target)
                self._invalidate_mapping_target(target)
                continue
            for name in names:
                self.scope.unbind(name)
                outward_target = (
                    self._outward_binding_targets[-1].get(name)
                    if self._outward_binding_targets
                    else None
                )
                restores_module_builtin = self.scope.scope_kind == "module" or (
                    outward_target is not None and outward_target.scope_kind == "module"
                )
                if (
                    restores_module_builtin
                    and name == "object"
                    and not namespace_target_recorded
                    and self._builtins_object_is_safe()
                ):
                    self.scope.bind(
                        name,
                        reference="builtins.object",
                        string=None,
                    )

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr in CANONICAL_API_KEY_SYMBOLS and self._is_legacy_module_reference(
            self._resolve_reference(node.value)
        ):
            self.errors.append(
                f"{self.filename}: legacy API-key dependency attribute access is forbidden: "
                f"{node.attr}"
            )
        if node.attr in _MAPPING_MUTATOR_METHODS:
            self._invalidate_mapping_aliases(node.value)
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        if self._is_legacy_namespace_reference(self._resolve_reference(node.value)):
            symbol_name = self._resolve_string(node.slice)
            if symbol_name in CANONICAL_API_KEY_SYMBOLS or symbol_name in {
                None,
                _DYNAMIC_STRING_BINDING,
                _POSSIBLE_API_KEY_SYMBOL,
            }:
                self.errors.append(
                    f"{self.filename}: legacy API-key dependency namespace lookup is forbidden: "
                    f"{symbol_name if symbol_name in CANONICAL_API_KEY_SYMBOLS else '<dynamic>'}"
                )
        self.generic_visit(node)

    def _capture_argument_binding(
        self,
        value: ast.AST,
        *,
        conservative: bool = False,
    ) -> _ResolvedBinding:
        reference = self._resolve_reference(value)
        string = self._resolve_string(value)
        unresolved_dynamic = reference is None and isinstance(
            value,
            (ast.Call, ast.Attribute, ast.Subscript),
        )
        if reference is None and (conservative or unresolved_dynamic):
            reference = _POSSIBLE_APP_CALL_REFERENCE
        if string is None and conservative:
            string = _DYNAMIC_STRING_BINDING
        return _ResolvedBinding(
            reference=reference,
            string=string,
            callables=self._resolve_callables(value),
            deferred_calls=self._resolve_deferred_calls(value),
            mapping=self._resolve_mapping(value),
            class_references=self._resolve_class_references(value),
            descriptors=self._resolve_descriptors(value),
            iterable_element=self._resolve_iterable_element_binding(value),
        )

    @staticmethod
    def _conservative_argument_binding() -> _ResolvedBinding:
        return _ResolvedBinding(
            reference=_POSSIBLE_APP_CALL_REFERENCE,
            string=_DYNAMIC_STRING_BINDING,
        )

    def _variadic_iterable_binding(
        self,
        elements: Sequence[_ResolvedBinding],
    ) -> _ResolvedBinding:
        if not elements:
            return _ResolvedBinding(
                reference=_KNOWN_NON_APP_REFERENCE,
                string=None,
            )
        element = self._join_resolved_bindings(elements)
        return _ResolvedBinding(
            reference=(
                _ITERABLE_SENSITIVE_ELEMENT_REFERENCE
                if self._argument_binding_may_register(element)
                else _KNOWN_NON_APP_REFERENCE
            ),
            string=None,
            iterable_element=element,
        )

    def _variadic_mapping_binding(
        self,
        values: Sequence[_ResolvedBinding],
    ) -> _ResolvedBinding:
        if not values:
            return _ResolvedBinding(
                reference=_KNOWN_NON_APP_REFERENCE,
                string=None,
            )
        value = self._join_resolved_bindings(values)
        return _ResolvedBinding(
            reference=(
                _MAPPING_SENSITIVE_VALUE_REFERENCE
                if self._argument_binding_may_register(value)
                else _KNOWN_NON_APP_REFERENCE
            ),
            string=None,
            iterable_element=value,
        )

    def _join_resolved_bindings(
        self,
        bindings: Sequence[_ResolvedBinding],
    ) -> _ResolvedBinding:
        if not bindings:
            return _ResolvedBinding(None, None)
        marker = f"<call-result:{id(bindings)}>"
        outcomes: list[_LexicalBindings] = []
        for binding in bindings:
            outcome = _LexicalBindings(parent=None)
            outcome.bind(
                marker,
                reference=binding.reference,
                string=binding.string,
                callables=binding.callables,
                deferred_calls=binding.deferred_calls,
                mapping=binding.mapping,
                class_references=binding.class_references,
                descriptors=binding.descriptors,
                iterable_element=binding.iterable_element,
            )
            outcomes.append(outcome)
        merged = _LexicalBindings(parent=None)
        active_scope = self.scope
        self._merge_outcomes(merged, outcomes)
        self.scope = active_scope
        return _ResolvedBinding(
            reference=merged.references.get(marker),
            string=merged.strings.get(marker),
            callables=merged.callables.get(marker, frozenset()),
            deferred_calls=merged.deferred_calls.get(marker, frozenset()),
            mapping=(
                bindings[0].mapping
                if bindings[0].mapping is not None
                and all(binding.mapping is bindings[0].mapping for binding in bindings)
                else None
            ),
            class_references=frozenset().union(*(binding.class_references for binding in bindings)),
            descriptors=frozenset().union(*(binding.descriptors for binding in bindings)),
            iterable_element=merged.iterable_elements.get(marker),
        )

    @staticmethod
    def _argument_binding_may_register(binding: _ResolvedBinding) -> bool:
        reference = binding.reference
        return (
            bool(binding.callables)
            or (
                binding.iterable_element is not None
                and _ApiKeyLookupVisitor._argument_binding_may_register(binding.iterable_element)
            )
            or reference
            in {
                "pulseplate.app",
                "pulseplate.app.router",
                _POSSIBLE_APP_REFERENCE,
                _POSSIBLE_ROUTER_REFERENCE,
                _POSSIBLE_APP_CALL_REFERENCE,
                _POSSIBLE_MIDDLEWARE_DECORATOR_REFERENCE,
            }
            or (
                reference is not None
                and (
                    reference.startswith("pulseplate.app.")
                    or reference.startswith(_MIDDLEWARE_DECORATOR_REFERENCE_PREFIX)
                )
            )
        )

    def _resolve_call_argument_bindings(
        self,
        function: _FunctionNode,
        call: ast.Call,
        *,
        callable_expr: ast.expr | None = None,
        positional_override: Sequence[_ResolvedBinding] | None = None,
    ) -> dict[str, _ResolvedBinding] | None:
        callable_expr = callable_expr or call.func
        evaluator = _ApiKeyLookupVisitor(
            filename=self.filename,
            errors=[],
            preserve_fastapi_conflicts=self.preserve_fastapi_conflicts,
            preserve_lifecycle_conflicts=self.preserve_lifecycle_conflicts,
            preserve_route_method_conflicts=self.preserve_route_method_conflicts,
            analyze_function_bodies=False,
        )
        evaluator.scope = self.scope.detached_clone()
        evaluator.visit(callable_expr)

        keyword_bindings: list[tuple[str, _ResolvedBinding]] = []
        if positional_override is None:
            positional_bindings: list[_ResolvedBinding] = []
            unresolved_positional_bindings: list[_ResolvedBinding] = []
            for call_argument in call.args:
                if not isinstance(call_argument, ast.Starred):
                    evaluator.visit(call_argument)
                    positional_bindings.append(evaluator._capture_argument_binding(call_argument))
                    continue
                if isinstance(call_argument.value, (ast.List, ast.Tuple)) and not any(
                    isinstance(element, ast.Starred) for element in call_argument.value.elts
                ):
                    for element in call_argument.value.elts:
                        evaluator.visit(element)
                        positional_bindings.append(evaluator._capture_argument_binding(element))
                else:
                    evaluator.visit(call_argument.value)
                    unresolved_positional_bindings.append(
                        evaluator._resolve_iterable_element_binding(call_argument.value)
                        or evaluator._conservative_argument_binding()
                    )

            unresolved_keyword_value_bindings: list[_ResolvedBinding] = []
            for keyword in call.keywords:
                if keyword.arg is not None:
                    evaluator.visit(keyword.value)
                    keyword_bindings.append(
                        (
                            keyword.arg,
                            evaluator._capture_argument_binding(keyword.value),
                        )
                    )
                    continue
                if (
                    isinstance(keyword.value, ast.Dict)
                    and all(
                        isinstance(key, ast.Constant) and isinstance(key.value, str)
                        for key in keyword.value.keys
                        if key is not None
                    )
                    and all(key is not None for key in keyword.value.keys)
                ):
                    static_dict_bindings: dict[str, _ResolvedBinding] = {}
                    for key, value in zip(
                        keyword.value.keys,
                        keyword.value.values,
                        strict=True,
                    ):
                        if not isinstance(key, ast.Constant):
                            continue
                        evaluator.visit(key)
                        evaluator.visit(value)
                        static_dict_bindings[str(key.value)] = evaluator._capture_argument_binding(
                            value
                        )
                    keyword_bindings.extend(static_dict_bindings.items())
                else:
                    evaluator.visit(keyword.value)
                    unresolved_keyword_value_bindings.append(
                        evaluator._resolve_mapping_value_binding(keyword.value)
                        or evaluator._conservative_argument_binding()
                    )
        else:
            positional_bindings = list(positional_override)
            unresolved_positional_bindings = []
            unresolved_keyword_value_bindings = []
        unresolved_positional = bool(unresolved_positional_bindings)
        unresolved_keywords = bool(unresolved_keyword_value_bindings)

        receiver_options: set[bool] = set()
        call_descriptor_kinds = {
            descriptor_kind
            for candidate, descriptor_kind in self._resolve_descriptors(callable_expr)
            if candidate is function
        }
        for descriptor_kind in call_descriptor_kinds:
            if descriptor_kind in {"bound", "classmethod"}:
                receiver_options.add(True)
            elif descriptor_kind in {"unbound", "plain", "staticmethod"}:
                receiver_options.add(False)
        if not receiver_options and isinstance(callable_expr, ast.Attribute):
            owner_references = self._resolve_object_references(callable_expr.value)
            instance_access = any(
                owner_reference.startswith(_INSTANCE_REFERENCE_PREFIX)
                for owner_reference in owner_references
            )
            receiver_options.add(instance_access)
        if not receiver_options:
            receiver_options.add(False)

        positional_variants = [
            [
                *([_ResolvedBinding(None, None)] if inject_receiver else []),
                *positional_bindings,
            ]
            for inject_receiver in sorted(receiver_options)
        ]

        positional_parameters = [*function.args.posonlyargs, *function.args.args]
        keyword_parameters = {parameter.arg for parameter in function.args.args}
        keyword_parameters.update(parameter.arg for parameter in function.args.kwonlyargs)
        default_bindings = self._function_default_bindings.get(function, {})

        def resolve_variant(
            variant: Sequence[_ResolvedBinding],
        ) -> dict[str, _ResolvedBinding] | None:
            assignments: dict[str, list[_ResolvedBinding]] = {}
            overflow_positional_bindings: list[_ResolvedBinding] = []
            for index, binding in enumerate(variant):
                if index < len(positional_parameters):
                    name = positional_parameters[index].arg
                    assignments.setdefault(name, []).append(binding)
                else:
                    overflow_positional_bindings.append(binding)
            unexpected_keyword_bindings: list[_ResolvedBinding] = []
            for name, binding in keyword_bindings:
                if name in keyword_parameters:
                    assignments.setdefault(name, []).append(binding)
                else:
                    unexpected_keyword_bindings.append(binding)

            if overflow_positional_bindings and function.args.vararg is None:
                return None
            if unexpected_keyword_bindings and function.args.kwarg is None:
                return None
            if any(len(candidates) > 1 for candidates in assignments.values()):
                return None
            for parameter in positional_parameters:
                if assignments.get(parameter.arg) or parameter.arg in default_bindings:
                    continue
                may_be_supplied = unresolved_positional or (
                    parameter in function.args.args and unresolved_keywords
                )
                if not may_be_supplied:
                    return None
            for parameter in function.args.kwonlyargs:
                if assignments.get(parameter.arg) or parameter.arg in default_bindings:
                    continue
                if not unresolved_keywords:
                    return None

            resolved: dict[str, _ResolvedBinding] = {}
            for parameter in positional_parameters:
                candidates = assignments.get(parameter.arg, [])
                if len(candidates) == 1:
                    resolved[parameter.arg] = candidates[0]
                elif len(candidates) > 1:
                    resolved[parameter.arg] = self._conservative_argument_binding()
                elif parameter.arg in default_bindings:
                    resolved[parameter.arg] = default_bindings[parameter.arg]
                elif unresolved_positional or (
                    parameter in function.args.args and unresolved_keywords
                ):
                    resolved[parameter.arg] = self._conservative_argument_binding()
                else:
                    resolved[parameter.arg] = _ResolvedBinding(None, None)

            for parameter in function.args.kwonlyargs:
                candidates = assignments.get(parameter.arg, [])
                if len(candidates) == 1:
                    resolved[parameter.arg] = candidates[0]
                elif len(candidates) > 1:
                    resolved[parameter.arg] = self._conservative_argument_binding()
                elif parameter.arg in default_bindings:
                    resolved[parameter.arg] = default_bindings[parameter.arg]
                elif unresolved_keywords:
                    resolved[parameter.arg] = self._conservative_argument_binding()
                else:
                    resolved[parameter.arg] = _ResolvedBinding(None, None)

            if function.args.vararg is not None:
                resolved[function.args.vararg.arg] = self._variadic_iterable_binding(
                    [
                        *overflow_positional_bindings,
                        *unresolved_positional_bindings,
                    ]
                )
            if function.args.kwarg is not None:
                resolved[function.args.kwarg.arg] = self._variadic_mapping_binding(
                    [
                        *unexpected_keyword_bindings,
                        *unresolved_keyword_value_bindings,
                    ]
                )
            return resolved

        resolved_variants = [
            resolved
            for variant in positional_variants
            if (resolved := resolve_variant(variant)) is not None
        ]
        if not resolved_variants:
            return None
        if len(resolved_variants) == 1:
            return resolved_variants[0]
        return {
            name: self._join_resolved_bindings([resolved[name] for resolved in resolved_variants])
            for name in resolved_variants[0]
        }

    def _resolve_partial_invocation_bindings(
        self,
        template: _DeferredFunctionCall,
        node: ast.Call,
    ) -> dict[str, _ResolvedBinding] | None:
        if (
            template.partial_unresolved
            or node.keywords
            or any(isinstance(argument, ast.Starred) for argument in node.args)
        ):
            conservative = self._conservative_argument_binding()
            resolved: dict[str, _ResolvedBinding] = {}
            for parameter in _iter_function_parameters(template.function.args):
                if parameter is template.function.args.vararg:
                    resolved[parameter.arg] = self._variadic_iterable_binding([conservative])
                elif parameter is template.function.args.kwarg:
                    resolved[parameter.arg] = self._variadic_mapping_binding([conservative])
                else:
                    resolved[parameter.arg] = conservative
            return resolved
        positional = [
            *template.partial_positional,
            *(self._capture_argument_binding(argument) for argument in node.args),
        ]
        return self._resolve_call_argument_bindings(
            template.function,
            node,
            positional_override=positional,
        )

    def _prepare_function_replay_inputs(
        self,
        node: ast.Call,
        *,
        excluded_targets: AbstractSet[_FunctionNode] = frozenset(),
    ) -> list[tuple[_FunctionNode, dict[str, _ResolvedBinding]]]:
        if not self.analyze_function_bodies or not self._replay_calls_enabled:
            return []
        awaited = id(node) in self._awaited_call_ids
        iterated = id(node) in self._iterated_call_ids
        replay_inputs: list[tuple[_FunctionNode, dict[str, _ResolvedBinding]]] = []
        partial_templates = {
            call for call in self._resolve_deferred_calls(node.func) if call.partial_template
        }
        partial_targets = {call.function for call in partial_templates}
        for target in sorted(
            self._resolve_callables(node.func) - excluded_targets - partial_targets,
            key=lambda candidate: (
                candidate.lineno,
                candidate.col_offset,
                candidate.name,
                isinstance(candidate, ast.AsyncFunctionDef),
            ),
        ):
            generator = _function_is_generator(target)
            if generator and not iterated:
                continue
            if isinstance(target, ast.AsyncFunctionDef) and not awaited and not iterated:
                continue
            arguments = self._resolve_call_argument_bindings(target, node)
            if arguments is not None:
                replay_inputs.append((target, arguments))
        for template in sorted(partial_templates, key=self._deferred_call_sort_key):
            target = template.function
            if target in excluded_targets:
                continue
            generator = _function_is_generator(target)
            if generator and not iterated:
                continue
            if isinstance(target, ast.AsyncFunctionDef) and not awaited and not iterated:
                continue
            arguments = self._resolve_partial_invocation_bindings(template, node)
            if arguments is not None:
                replay_inputs.append((target, arguments))
        return replay_inputs

    def _capture_deferred_calls(
        self,
        node: ast.Call,
    ) -> frozenset[_DeferredFunctionCall]:
        if (
            not self.analyze_function_bodies
            or not self._replay_calls_enabled
            or id(node) in self._awaited_call_ids
            or id(node) in self._iterated_call_ids
        ):
            return frozenset()
        deferred: set[_DeferredFunctionCall] = set()
        partial_templates = {
            call for call in self._resolve_deferred_calls(node.func) if call.partial_template
        }
        partial_targets = {call.function for call in partial_templates}
        for target in self._resolve_callables(node.func) - partial_targets:
            is_generator = _function_is_generator(target)
            is_coroutine = isinstance(target, ast.AsyncFunctionDef) and not is_generator
            if not (is_generator or is_coroutine):
                continue
            arguments = self._resolve_call_argument_bindings(target, node)
            if arguments is not None:
                deferred.add(
                    _DeferredFunctionCall(
                        function=target,
                        arguments=tuple(sorted(arguments.items())),
                    )
                )
        return frozenset(deferred)

    @staticmethod
    def _restore_scope_state(target: _LexicalBindings, snapshot: _LexicalBindings) -> None:
        target.references = dict(snapshot.references)
        target.strings = dict(snapshot.strings)
        target.callables = dict(snapshot.callables)
        target.deferred_calls = dict(snapshot.deferred_calls)
        target.mappings = dict(snapshot.mappings)
        target.class_references = dict(snapshot.class_references)
        target.descriptors = dict(snapshot.descriptors)
        target.iterable_elements = dict(snapshot.iterable_elements)
        target.bound_names = set(snapshot.bound_names)
        target.possibly_bound_names = set(snapshot.possibly_bound_names)

    @staticmethod
    def _deferred_call_sort_key(
        call: _DeferredFunctionCall,
    ) -> tuple[
        int,
        int,
        str,
        tuple[tuple[str, str | None, str | None], ...],
        bool,
        tuple[tuple[str | None, str | None], ...],
        bool,
    ]:
        return (
            call.function.lineno,
            call.function.col_offset,
            call.function.name,
            tuple((name, binding.reference, binding.string) for name, binding in call.arguments),
            call.partial_template,
            tuple((binding.reference, binding.string) for binding in call.partial_positional),
            call.partial_unresolved,
        )

    def _replay_deferred_calls(
        self,
        calls: AbstractSet[_DeferredFunctionCall],
        *,
        execution: str,
    ) -> _ResolvedBinding | None:
        eligible_calls = {
            call
            for call in calls
            if call not in self._consumed_deferred_calls
            if not call.partial_template
            if (
                execution == "iterate"
                and (
                    self._deferred_generator_expression_for(call.function) is not None
                    or _function_is_generator(call.function)
                )
            )
            or (
                execution == "await"
                and isinstance(call.function, ast.AsyncFunctionDef)
                and not _function_is_generator(call.function)
            )
        }
        ordered_calls = sorted(eligible_calls, key=self._deferred_call_sort_key)
        if not ordered_calls:
            return None
        if len(ordered_calls) == 1:
            call = ordered_calls[0]
            result = self._execute_deferred_call(call)
            self._consumed_deferred_calls.add(call)
            return result

        active_scope = self.scope
        scope_chain: list[_LexicalBindings] = []
        candidate_scope: _LexicalBindings | None = active_scope
        while candidate_scope is not None:
            scope_chain.append(candidate_scope)
            candidate_scope = candidate_scope.parent
        initial_states = [scope.clone() for scope in scope_chain]
        outcome_states: list[list[_LexicalBindings]] = [[] for _scope in scope_chain]
        result_bindings: list[_ResolvedBinding] = []
        for call in ordered_calls:
            for scope, initial in zip(scope_chain, initial_states, strict=True):
                self._restore_scope_state(scope, initial)
            self.scope = active_scope
            result_bindings.append(self._execute_deferred_call(call))
            self._consumed_deferred_calls.add(call)
            for index, scope in enumerate(scope_chain):
                outcome_states[index].append(scope.clone())
        for scope, outcomes in reversed(list(zip(scope_chain, outcome_states, strict=True))):
            self._merge_outcomes(scope, outcomes)
        self.scope = active_scope
        return self._join_resolved_bindings(result_bindings)

    def _execute_deferred_call(self, call: _DeferredFunctionCall) -> _ResolvedBinding:
        deferred_expression = self._deferred_generator_expression_for(call.function)
        if deferred_expression is None:
            return self._replay_function_call(call.function, dict(call.arguments))
        expression, expression_scope, outer_binding = deferred_expression
        previous = self.scope
        self.scope = expression_scope
        try:
            self._visit_comprehension(
                expression.generators,
                [expression.elt],
                outer_binding=outer_binding,
            )
        finally:
            self.scope = previous
        return _ResolvedBinding(None, None)

    def _deferred_generator_expression_for(
        self,
        function: _FunctionNode,
    ) -> tuple[ast.GeneratorExp, _LexicalBindings, _ResolvedBinding] | None:
        expression = self._deferred_generator_expressions.get(function)
        if expression is not None:
            return (
                expression,
                self._deferred_generator_scopes[function],
                self._deferred_generator_outer_bindings[function],
            )
        for candidate, candidate_expression in self._deferred_generator_expressions.items():
            if (
                function.name == candidate.name == "<generator-expression>"
                and function.lineno == candidate.lineno
                and function.col_offset == candidate.col_offset
            ):
                return (
                    candidate_expression,
                    self._deferred_generator_scopes[candidate],
                    self._deferred_generator_outer_bindings[candidate],
                )
        return None

    def _partial_function_templates(
        self,
        node: ast.Call,
        *,
        wrapper_reference: str | None,
    ) -> frozenset[_DeferredFunctionCall]:
        if wrapper_reference != "functools.partial" or not node.args:
            return frozenset()
        callable_expr = node.args[0]
        nested_templates = {
            call for call in self._resolve_deferred_calls(callable_expr) if call.partial_template
        }
        unresolved = bool(node.keywords) or any(
            isinstance(argument, ast.Starred) for argument in node.args[1:]
        )
        positional = (
            ()
            if unresolved
            else tuple(self._capture_argument_binding(argument) for argument in node.args[1:])
        )
        if nested_templates:
            return frozenset(
                {
                    _DeferredFunctionCall(
                        function=nested.function,
                        arguments=(),
                        partial_template=True,
                        partial_positional=(*nested.partial_positional, *positional),
                        partial_unresolved=nested.partial_unresolved or unresolved,
                    )
                    for nested in nested_templates
                }
            )

        return frozenset(
            _DeferredFunctionCall(
                function=target,
                arguments=(),
                partial_template=True,
                partial_positional=positional,
                partial_unresolved=unresolved,
            )
            for target in self._resolve_callables(callable_expr)
        )

    def visit_Call(self, node: ast.Call) -> None:
        self._record_object_namespace_call_mutation(node)
        escaped_mappings = [
            mapping
            for argument in node.args
            if not isinstance(argument, ast.Starred)
            if (mapping := self._resolve_mapping(argument)) is not None
        ]
        escaped_mappings.extend(
            mapping
            for keyword in node.keywords
            if keyword.arg is not None
            if (mapping := self._resolve_mapping(keyword.value)) is not None
        )
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr in _MAPPING_MUTATOR_METHODS
            and (mutated_mapping := self._resolve_mapping(node.func.value)) is not None
        ):
            escaped_mappings.append(mutated_mapping)
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr in {"get", "__getitem__"}
            and node.args
            and self._is_legacy_namespace_reference(self._resolve_reference(node.func.value))
        ):
            symbol_name = self._resolve_string(node.args[0])
            if (
                symbol_name in CANONICAL_API_KEY_SYMBOLS
                or symbol_name in {_POSSIBLE_API_KEY_SYMBOL, _DYNAMIC_STRING_BINDING}
                or (symbol_name is None and not isinstance(node.args[0], ast.Name))
            ):
                self.errors.append(
                    f"{self.filename}: legacy API-key dependency namespace lookup is forbidden: "
                    f"{symbol_name if symbol_name in CANONICAL_API_KEY_SYMBOLS else '<dynamic>'}"
                )
        if (
            self.filename != CANONICAL_API_KEY
            and self._resolve_reference(node.func)
            in {"builtins.getattr", _POSSIBLE_GETATTR_REFERENCE}
            and len(node.args) >= 2
            and self._is_legacy_module_reference(self._resolve_reference(node.args[0]))
        ):
            symbol_name = self._resolve_string(node.args[1])
            if (
                symbol_name in CANONICAL_API_KEY_SYMBOLS
                or symbol_name in {_POSSIBLE_API_KEY_SYMBOL, _DYNAMIC_STRING_BINDING}
                or (symbol_name is None and not isinstance(node.args[1], ast.Name))
            ):
                self.errors.append(
                    f"{self.filename}: dynamic legacy API-key dependency lookup is forbidden: "
                    f"{symbol_name if symbol_name in CANONICAL_API_KEY_SYMBOLS else '<dynamic>'}"
                )
        deferred_calls = self._capture_deferred_calls(node)
        if deferred_calls:
            self._deferred_call_bindings[id(node)] = deferred_calls
        initial_replay_inputs = self._prepare_function_replay_inputs(node)
        initial_arguments = {target: arguments for target, arguments in initial_replay_inputs}
        prepared_targets = set(initial_arguments)

        wrapper_reference = self._resolve_reference(node.func)
        namespace_kind = self._object_namespace_mapping_kind(node)
        if namespace_kind is not None:
            self._call_result_bindings[id(node)] = _ResolvedBinding(
                reference=(
                    _BUILTINS_NAMESPACE_REFERENCE
                    if namespace_kind == "builtins"
                    else _MODULE_NAMESPACE_REFERENCE
                ),
                string=None,
            )
        wrapped_call = node.args[0] if node.args and isinstance(node.args[0], ast.Call) else None
        executes_async = wrapper_reference in {
            "asyncio.run",
            "asyncio.create_task",
            "asyncio.ensure_future",
            "asyncio.shield",
        } or (
            wrapper_reference == "asyncio.TaskGroup.instance.create_task"
            and self._active_async_replay_depth > 0
            and self._active_task_group_depth > 0
        )
        gathers_awaitables = wrapper_reference == "asyncio.gather" and (
            id(node) in self._awaited_call_ids or self._active_async_replay_depth > 0
        )
        gathered_calls = [
            argument
            for argument in node.args
            if not isinstance(argument, ast.Starred) and isinstance(argument, ast.Call)
        ]
        newly_awaited_gather_calls = [
            argument
            for argument in gathered_calls
            if gathers_awaitables and id(argument) not in self._awaited_call_ids
        ]
        consumes_iterable = (
            wrapper_reference
            in {
                "builtins.all",
                "builtins.any",
                "builtins.list",
                "builtins.frozenset",
                "builtins.max",
                "builtins.min",
                "builtins.next",
                "builtins.set",
                "builtins.sorted",
                "builtins.sum",
                "builtins.tuple",
            }
            or isinstance(node.func, ast.Name)
            and node.func.id
            in {
                "all",
                "any",
                "frozenset",
                "list",
                "max",
                "min",
                "next",
                "set",
                "sorted",
                "sum",
                "tuple",
            }
        )
        if wrapped_call is not None and executes_async:
            self._awaited_call_ids.add(id(wrapped_call))
        for gathered_call in newly_awaited_gather_calls:
            self._awaited_call_ids.add(id(gathered_call))
        iterated_argument = node.args[0] if node.args and consumes_iterable else None
        iterated_argument_was_marked = (
            iterated_argument is not None and id(iterated_argument) in self._iterated_call_ids
        )
        if iterated_argument is not None:
            self._iterated_call_ids.add(id(iterated_argument))
        try:
            self.generic_visit(node)
        finally:
            if wrapped_call is not None and executes_async:
                self._awaited_call_ids.remove(id(wrapped_call))
            for gathered_call in newly_awaited_gather_calls:
                self._awaited_call_ids.remove(id(gathered_call))
            if iterated_argument is not None and not iterated_argument_was_marked:
                self._iterated_call_ids.remove(id(iterated_argument))
        projected_result: _ResolvedBinding | None = None
        if node.args and wrapper_reference in _ITERABLE_PRESERVING_BUILTIN_REFERENCES:
            element = self._resolve_iterable_element_binding(node.args[0])
            if element is not None:
                projected_result = self._variadic_iterable_binding([element])
        elif node.args and wrapper_reference in _ITERABLE_ELEMENT_BUILTIN_REFERENCES:
            if wrapper_reference in {"builtins.max", "builtins.min"} and len(node.args) != 1:
                projected_result = self._join_resolved_bindings(
                    [self._capture_argument_binding(argument) for argument in node.args]
                )
            else:
                projected_result = self._resolve_iterable_element_binding(node.args[0])
                if wrapper_reference == "builtins.next" and len(node.args) >= 2:
                    default_binding = self._capture_argument_binding(node.args[1])
                    projected_result = (
                        default_binding
                        if projected_result is None
                        else self._join_resolved_bindings([projected_result, default_binding])
                    )
            if wrapper_reference in {"builtins.max", "builtins.min"}:
                default_bindings: list[_ResolvedBinding] = []
                for keyword in node.keywords:
                    if keyword.arg == "default":
                        default_bindings.append(self._capture_argument_binding(keyword.value))
                    elif keyword.arg is None:
                        binding, unresolved = self._resolve_unpacked_keyword_binding(
                            keyword.value,
                            "default",
                        )
                        if binding is not None:
                            default_bindings.append(binding)
                        if unresolved:
                            default_bindings.append(self._conservative_argument_binding())
                if default_bindings:
                    default_binding = self._join_resolved_bindings(default_bindings)
                    projected_result = (
                        default_binding
                        if projected_result is None
                        else self._join_resolved_bindings([projected_result, default_binding])
                    )
        if projected_result is not None:
            existing_result = self._call_result_bindings.get(id(node))
            self._call_result_bindings[id(node)] = (
                projected_result
                if existing_result is None
                else self._join_resolved_bindings([existing_result, projected_result])
            )
            if self.call_result_snapshots is not None:
                existing_snapshot = self.call_result_snapshots.get(id(node))
                self.call_result_snapshots[id(node)] = (
                    projected_result
                    if existing_snapshot is None
                    else self._join_resolved_bindings([existing_snapshot, projected_result])
                )
        replay_inputs: list[tuple[_FunctionNode, dict[str, _ResolvedBinding]]] = []
        for target in sorted(
            prepared_targets,
            key=lambda candidate: (
                candidate.lineno,
                candidate.col_offset,
                candidate.name,
            ),
        ):
            arguments = self._resolve_call_argument_bindings(target, node)
            if arguments is None:
                replay_inputs.append((target, initial_arguments[target]))
                continue
            replay_inputs.append(
                (
                    target,
                    {
                        name: (
                            initial_arguments[target][name]
                            if (
                                initial_arguments[target][name].reference is not None
                                or initial_arguments[target][name].string is not None
                                or initial_arguments[target][name].callables
                                or initial_arguments[target][name].deferred_calls
                            )
                            else binding
                        )
                        for name, binding in arguments.items()
                    },
                )
            )
        replay_inputs.extend(
            self._prepare_function_replay_inputs(
                node,
                excluded_targets=prepared_targets,
            )
        )
        maps_callback = id(node) in self._iterated_call_ids and (
            wrapper_reference == "builtins.map"
            or isinstance(node.func, ast.Name)
            and node.func.id == "map"
        )
        if maps_callback and len(node.args) >= 2:
            iterable_bindings = [
                (
                    self._resolve_iterable_element_binding(
                        argument.value if isinstance(argument, ast.Starred) else argument
                    )
                    or self._conservative_argument_binding()
                )
                for argument in node.args[1:]
            ]
            replay_inputs.extend(
                (target, arguments)
                for target in sorted(
                    self._resolve_callables(node.args[0]),
                    key=lambda candidate: (
                        candidate.lineno,
                        candidate.col_offset,
                        candidate.name,
                    ),
                )
                if not isinstance(target, ast.AsyncFunctionDef)
                if not _function_is_generator(target)
                if (
                    arguments := self._resolve_call_argument_bindings(
                        target,
                        node,
                        callable_expr=node.args[0],
                        positional_override=iterable_bindings,
                    )
                )
                is not None
            )
        replay_results = [
            self._replay_function_call(target, arguments) for target, arguments in replay_inputs
        ]
        if replay_results:
            result_binding = self._join_resolved_bindings(replay_results)
            self._call_result_bindings[id(node)] = result_binding
            if self.call_result_snapshots is not None:
                existing = self.call_result_snapshots.get(id(node))
                self.call_result_snapshots[id(node)] = (
                    result_binding
                    if existing is None
                    else self._join_resolved_bindings([existing, result_binding])
                )
        partial_templates = self._partial_function_templates(
            node,
            wrapper_reference=wrapper_reference,
        )
        if partial_templates:
            partial_binding = _ResolvedBinding(
                reference=self._resolve_reference(node) or _KNOWN_NON_APP_REFERENCE,
                string=None,
                callables=frozenset(template.function for template in partial_templates),
                deferred_calls=partial_templates,
            )
            existing = self._call_result_bindings.get(id(node))
            self._call_result_bindings[id(node)] = (
                partial_binding
                if existing is None
                else self._join_resolved_bindings([existing, partial_binding])
            )
            if self.call_result_snapshots is not None:
                existing_snapshot = self.call_result_snapshots.get(id(node))
                self.call_result_snapshots[id(node)] = (
                    partial_binding
                    if existing_snapshot is None
                    else self._join_resolved_bindings([existing_snapshot, partial_binding])
                )
        if executes_async and node.args and wrapped_call is None:
            deferred_result = self._replay_deferred_calls(
                self._resolve_deferred_calls(node.args[0]),
                execution="await",
            )
            if deferred_result is not None:
                self._call_result_bindings[id(node)] = deferred_result
        if gathers_awaitables:
            for argument in node.args:
                if isinstance(argument, ast.Starred):
                    element = self._resolve_iterable_element_binding(argument.value)
                    deferred = element.deferred_calls if element is not None else frozenset()
                else:
                    deferred = self._resolve_deferred_calls(argument)
                self._replay_deferred_calls(deferred, execution="await")
        if consumes_iterable and node.args:
            self._replay_deferred_calls(
                self._resolve_deferred_calls(node.args[0]),
                execution="iterate",
            )
        escaped_mappings.extend(
            mapping
            for argument in node.args
            if not isinstance(argument, ast.Starred)
            if (mapping := self._resolve_mapping(argument)) is not None
        )
        escaped_mappings.extend(
            mapping
            for keyword in node.keywords
            if keyword.arg is not None
            if (mapping := self._resolve_mapping(keyword.value)) is not None
        )
        for mapping in set(escaped_mappings):
            self._invalidate_mapping(mapping)

    def visit_Await(self, node: ast.Await) -> None:
        if not isinstance(node.value, ast.Call):
            self.generic_visit(node)
            result_binding = self._replay_deferred_calls(
                self._resolve_deferred_calls(node.value),
                execution="await",
            )
            if result_binding is not None:
                self._call_result_bindings[id(node)] = result_binding
            return
        call_id = id(node.value)
        self._awaited_call_ids.add(call_id)
        try:
            self.visit(node.value)
        finally:
            self._awaited_call_ids.remove(call_id)

    def _replay_function_call(
        self,
        node: _FunctionNode,
        arguments: Mapping[str, _ResolvedBinding],
    ) -> _ResolvedBinding:
        if node in self._active_function_replays:
            return _ResolvedBinding(None, None)
        previous = self.scope
        previous_loop_controls = self._loop_controls
        previous_terminal_controls = self._terminal_controls
        previous_exception_scope_collectors = self._exception_scope_collectors
        lexical_parent = self._function_definition_scopes.get(node, previous)
        global_names, nonlocal_names = _function_outward_binding_names(node)
        outward_targets: dict[str, _LexicalBindings] = {}
        module_scope: _LexicalBindings | None = previous
        while module_scope is not None and module_scope.scope_kind != "module":
            module_scope = module_scope.parent
        if module_scope is not None:
            outward_targets.update({name: module_scope for name in global_names})
        for name in nonlocal_names:
            nonlocal_scope: _LexicalBindings | None = lexical_parent
            while nonlocal_scope is not None:
                owns_name = nonlocal_scope.scope_kind == "function" and (
                    name in nonlocal_scope.local_names
                    or name in nonlocal_scope.references
                    or name in nonlocal_scope.strings
                    or name in nonlocal_scope.callables
                    or name in nonlocal_scope.mappings
                    or name in nonlocal_scope.class_references
                    or name in nonlocal_scope.descriptors
                    or name in nonlocal_scope.iterable_elements
                )
                if owns_name:
                    outward_targets[name] = nonlocal_scope
                    break
                nonlocal_scope = nonlocal_scope.parent
        self.scope = _LexicalBindings(
            parent=lexical_parent,
            local_names=(_function_local_binding_names(node) | global_names | nonlocal_names),
            scope_kind="function",
        )
        for name, target in outward_targets.items():
            self.scope.bind(
                name,
                reference=target.resolve_reference(name),
                string=target.resolve_string(name),
                callables=target.resolve_callables(name),
                deferred_calls=target.resolve_deferred_calls(name),
                mapping=target.resolve_mapping(name),
                class_references=target.resolve_class_references(name),
                descriptors=target.resolve_descriptors(name),
                iterable_element=target.resolve_iterable_element(name),
            )
        for name, binding in arguments.items():
            self.scope.bind(
                name,
                reference=binding.reference,
                string=binding.string,
                callables=binding.callables,
                deferred_calls=binding.deferred_calls,
                mapping=binding.mapping,
                class_references=binding.class_references,
                descriptors=binding.descriptors,
                iterable_element=binding.iterable_element,
            )
        self._loop_controls = []
        self._terminal_controls = _TerminalControlBindings(return_scopes=[], raise_scopes=[])
        self._exception_scope_collectors = []
        self._active_function_replays.add(node)
        self._active_replay_contexts.append(object())
        self._outward_binding_targets.append(outward_targets)
        return_bindings: list[_ResolvedBinding] = []
        self._return_binding_collectors.append(return_bindings)
        replay_entry = self.scope.clone()
        replays_async = isinstance(node, ast.AsyncFunctionDef)
        if replays_async:
            self._active_async_replay_depth += 1
        try:
            falls_through = self._visit_statements(node.body)
            result_binding = self._join_resolved_bindings(
                [
                    *return_bindings,
                    *([_ResolvedBinding(None, None)] if falls_through else []),
                ]
            )
            if result_binding.reference == "pulseplate.app":
                result_binding = _ResolvedBinding(
                    _POSSIBLE_APP_REFERENCE,
                    result_binding.string,
                    result_binding.callables,
                    result_binding.deferred_calls,
                    result_binding.mapping,
                    result_binding.class_references,
                    result_binding.descriptors,
                    result_binding.iterable_element,
                )
            elif result_binding.reference == "pulseplate.app.router":
                result_binding = _ResolvedBinding(
                    _POSSIBLE_ROUTER_REFERENCE,
                    result_binding.string,
                    result_binding.callables,
                    result_binding.deferred_calls,
                    result_binding.mapping,
                    result_binding.class_references,
                    result_binding.descriptors,
                    result_binding.iterable_element,
                )
            outcomes = [
                self.scope,
                *self._terminal_controls.return_scopes,
                *self._terminal_controls.raise_scopes,
            ]
            joined_scope = replay_entry.clone()
            self._merge_outcomes(joined_scope, outcomes)
            for name, target in outward_targets.items():
                mapping = joined_scope.mappings.get(name)
                class_references = joined_scope.class_references.get(name, frozenset())
                descriptors = joined_scope.descriptors.get(name, frozenset())
                iterable_element = joined_scope.iterable_elements.get(name)
                binding = _ResolvedBinding(
                    reference=joined_scope.references.get(name),
                    string=joined_scope.strings.get(name),
                    callables=joined_scope.callables.get(name, frozenset()),
                    deferred_calls=joined_scope.deferred_calls.get(name, frozenset()),
                    mapping=mapping,
                    class_references=class_references,
                    descriptors=descriptors,
                    iterable_element=iterable_element,
                )
                target.bind(
                    name,
                    reference=binding.reference,
                    string=binding.string,
                    callables=binding.callables,
                    deferred_calls=binding.deferred_calls,
                    mapping=mapping,
                    class_references=class_references,
                    descriptors=descriptors,
                    iterable_element=iterable_element,
                )
                parent_scope: _LexicalBindings | None = previous
                for active_targets in reversed(self._outward_binding_targets[:-1]):
                    while parent_scope is not None and parent_scope.scope_kind != "function":
                        parent_scope = parent_scope.parent
                    if parent_scope is None:
                        break
                    if active_targets.get(name) is target:
                        parent_scope.bind(
                            name,
                            reference=binding.reference,
                            string=binding.string,
                            callables=binding.callables,
                            deferred_calls=binding.deferred_calls,
                            mapping=mapping,
                            class_references=class_references,
                            descriptors=descriptors,
                            iterable_element=iterable_element,
                        )
                    parent_scope = parent_scope.parent
        finally:
            if replays_async:
                self._active_async_replay_depth -= 1
            self._return_binding_collectors.pop()
            self._outward_binding_targets.pop()
            self._active_replay_contexts.pop()
            self._active_function_replays.remove(node)
            self.scope = previous
            self._loop_controls = previous_loop_controls
            self._terminal_controls = previous_terminal_controls
            self._exception_scope_collectors = previous_exception_scope_collectors
        return result_binding


def _collect_module_final_bindings(
    tree: ast.Module,
    *,
    filename: str = LEGACY_APP,
    initial_references: Mapping[str, str],
    preserve_fastapi_conflicts: bool = False,
    preserve_lifecycle_conflicts: bool = False,
    preserve_route_method_conflicts: bool = False,
) -> tuple[Mapping[str, str], Mapping[str, str]]:
    visitor = _ApiKeyLookupVisitor(
        filename=filename,
        errors=[],
        initial_references=initial_references,
        preserve_fastapi_conflicts=preserve_fastapi_conflicts,
        preserve_lifecycle_conflicts=preserve_lifecycle_conflicts,
        preserve_route_method_conflicts=preserve_route_method_conflicts,
        analyze_function_bodies=False,
    )
    visitor.visit(tree)
    return visitor.scope.visible_references(), visitor.scope.visible_strings()


def _collect_lexical_binding_snapshots(
    tree: ast.Module,
    *,
    initial_references: Mapping[str, str],
    preserve_fastapi_conflicts: bool = False,
    preserve_lifecycle_conflicts: bool = False,
    preserve_route_method_conflicts: bool = False,
) -> tuple[
    Mapping[int, Mapping[str, str]],
    Mapping[int, Mapping[str, str]],
    Mapping[int, _ResolvedBinding],
]:
    """Collect statement-ordered reference/string environments at call sites."""

    reference_snapshots: dict[int, dict[str, str]] = {}
    string_snapshots: dict[int, dict[str, str]] = {}
    call_result_snapshots: dict[int, _ResolvedBinding] = {}
    module_late_references, module_late_strings = _collect_module_final_bindings(
        tree,
        filename=LEGACY_APP,
        initial_references=initial_references,
        preserve_fastapi_conflicts=preserve_fastapi_conflicts,
        preserve_lifecycle_conflicts=preserve_lifecycle_conflicts,
        preserve_route_method_conflicts=preserve_route_method_conflicts,
    )
    _ApiKeyLookupVisitor(
        filename=LEGACY_APP,
        errors=[],
        initial_references=initial_references,
        reference_snapshots=reference_snapshots,
        string_snapshots=string_snapshots,
        call_result_snapshots=call_result_snapshots,
        preserve_fastapi_conflicts=preserve_fastapi_conflicts,
        preserve_lifecycle_conflicts=preserve_lifecycle_conflicts,
        preserve_route_method_conflicts=preserve_route_method_conflicts,
        module_late_references=module_late_references,
        module_late_strings=module_late_strings,
    ).visit(tree)
    return reference_snapshots, string_snapshots, call_result_snapshots


def validate_api_key_dependency_ownership(
    legacy_source: str,
    app_sources: Mapping[str, str],
) -> list[str]:
    """Keep client API-key dependency ownership canonical and identity-preserving."""

    errors: list[str] = []
    legacy_tree, parse_errors = _parse_source(legacy_source, filename=LEGACY_APP)
    errors.extend(parse_errors)
    if legacy_tree is not None:
        locally_defined: set[str] = set()

        class _ModuleApiKeyDefinitionVisitor(ast.NodeVisitor):
            def _visit_function_header(
                self,
                node: ast.FunctionDef | ast.AsyncFunctionDef,
            ) -> None:
                for decorator in node.decorator_list:
                    self.visit(decorator)
                for default in (*node.args.defaults, *node.args.kw_defaults):
                    if default is not None:
                        self.visit(default)
                if node.returns is not None:
                    self.visit(node.returns)

            def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
                if node.name in CANONICAL_API_KEY_SYMBOLS:
                    locally_defined.add(node.name)
                self._visit_function_header(node)

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
                if node.name in CANONICAL_API_KEY_SYMBOLS:
                    locally_defined.add(node.name)
                self._visit_function_header(node)

            def visit_ClassDef(self, node: ast.ClassDef) -> None:
                for decorator in node.decorator_list:
                    self.visit(decorator)
                for base in node.bases:
                    self.visit(base)
                for keyword in node.keywords:
                    self.visit(keyword.value)

            def visit_Lambda(self, node: ast.Lambda) -> None:
                return

        definition_visitor = _ModuleApiKeyDefinitionVisitor()
        for statement in legacy_tree.body:
            definition_visitor.visit(statement)
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
        if tree is not None:
            module_late_references, module_late_strings = _collect_module_final_bindings(
                tree,
                filename=filename,
                initial_references={},
            )
            _ApiKeyLookupVisitor(
                filename=filename,
                errors=errors,
                module_late_references=module_late_references,
                module_late_strings=module_late_strings,
            ).visit(tree)
    return sorted(set(errors))


def _collect_lifecycle_references(
    tree: ast.Module,
) -> tuple[dict[str, str], frozenset[str]]:
    """Resolve lifecycle aliases with a finite, monotonic conflict lattice."""

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

    def join_reference(name: str, reference: str) -> bool:
        current = references.get(name)
        if current in {
            _DYNAMIC_LIFECYCLE_REFERENCE,
            _POSSIBLE_FASTAPI_REFERENCE,
            _CONFLICTED_FASTAPI_REFERENCE,
        }:
            return False
        if current == reference:
            return False
        if current is None:
            joined = reference
        elif any(
            candidate in {"fastapi.FastAPI", "fastapi.applications.FastAPI"}
            for candidate in (current, reference)
        ):
            joined = _POSSIBLE_FASTAPI_REFERENCE
        else:
            joined = _DYNAMIC_LIFECYCLE_REFERENCE
        references[name] = joined
        return True

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
                        join_reference(alias.asname, alias.name)
                    else:
                        root_module = alias.name.partition(".")[0]
                        join_reference(root_module, root_module)
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
                    join_reference(local_name, qualified)
                if qualified == "app.bootstrap.lifespan.application_lifespan":
                    canonical_lifespan_aliases.add(local_name)

    static_string_bindings = _collect_static_string_bindings(tree)
    assignments: list[tuple[str, ast.AST]] = []
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
        for target in targets:
            assignments.extend((name, value) for name in _assignment_target_names(target))

    changed = True
    while changed:
        changed = False
        for target_name, value in assignments:
            reference = _resolve_lifecycle_reference(
                value,
                references=references,
                static_string_bindings=static_string_bindings,
            )
            if reference is None:
                continue
            changed = join_reference(target_name, reference) or changed

    # Unknown RHS values and unresolved cycles are dynamic. Propagate that top
    # state once more so downstream aliases cannot recover a stale static fact.
    for target_name, value in assignments:
        if (
            _resolve_lifecycle_reference(
                value,
                references=references,
                static_string_bindings=static_string_bindings,
            )
            is None
        ):
            join_reference(target_name, _DYNAMIC_LIFECYCLE_REFERENCE)
    changed = True
    while changed:
        changed = False
        for target_name, value in assignments:
            reference = _resolve_lifecycle_reference(
                value,
                references=references,
                static_string_bindings=static_string_bindings,
            )
            if reference is not None:
                changed = join_reference(target_name, reference) or changed
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
    if isinstance(node, ast.NamedExpr):
        return _resolve_lifecycle_reference(
            node.value,
            references=references,
            static_string_bindings=static_string_bindings,
        )
    if isinstance(node, ast.Name):
        return references.get(node.id)
    if isinstance(node, ast.Subscript):
        parent = _resolve_lifecycle_reference(
            node.value,
            references=references,
            static_string_bindings=static_string_bindings,
        )
        member_name = _resolve_static_string(node.slice, static_string_bindings)
        if parent in {
            _DYNAMIC_LIFECYCLE_REFERENCE,
            _POSSIBLE_FASTAPI_REFERENCE,
            _CONFLICTED_FASTAPI_REFERENCE,
        }:
            return parent
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
        if parent in {
            _DYNAMIC_LIFECYCLE_REFERENCE,
            _POSSIBLE_FASTAPI_REFERENCE,
            _CONFLICTED_FASTAPI_REFERENCE,
        }:
            return parent
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
    if function_reference in {
        _DYNAMIC_LIFECYCLE_REFERENCE,
        _POSSIBLE_FASTAPI_REFERENCE,
        _CONFLICTED_FASTAPI_REFERENCE,
    }:
        return function_reference
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
    _references, canonical_lifespan_aliases = _collect_lifecycle_references(tree)
    static_string_bindings = _collect_static_string_bindings(tree)
    static_mapping_bindings = _collect_static_mapping_bindings(tree)
    reference_snapshots, string_snapshots, _call_results = _collect_lexical_binding_snapshots(
        tree,
        initial_references={
            "FastAPI": "fastapi.FastAPI",
            "__import__": "builtins.__import__",
            "dict": "builtins.dict",
            "getattr": "builtins.getattr",
            "setattr": "builtins.setattr",
            "vars": "builtins.vars",
        },
        preserve_fastapi_conflicts=True,
    )
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        node_id = id(node)
        if node_id not in reference_snapshots:
            continue
        scoped_references = reference_snapshots[node_id]
        scoped_strings = string_snapshots[node_id]
        resolved_constructor = _resolve_lifecycle_reference(
            node.func,
            references=scoped_references,
            static_string_bindings=scoped_strings,
        )
        if resolved_constructor == _DYNAMIC_LIFECYCLE_REFERENCE:
            if any(keyword.arg in {None, "lifespan"} for keyword in node.keywords):
                return True
            continue
        if resolved_constructor not in {
            "fastapi.FastAPI",
            "fastapi.applications.FastAPI",
            _POSSIBLE_FASTAPI_REFERENCE,
            _CONFLICTED_FASTAPI_REFERENCE,
        }:
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
                            references=scoped_references,
                            static_string_bindings=scoped_strings,
                        ):
                            return True
                        has_canonical_lifespan = True
                continue
            if keyword.arg != "lifespan":
                continue
            if not _is_canonical_lifespan_value(
                keyword.value,
                canonical_lifespan_aliases,
                references=scoped_references,
                static_string_bindings=scoped_strings,
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
    *,
    references: Mapping[str, str] | None = None,
    static_string_bindings: Mapping[str, str] | None = None,
) -> bool:
    if references is not None:
        return (
            _resolve_lifecycle_reference(
                node,
                references=references,
                static_string_bindings=static_string_bindings or {},
            )
            == "app.bootstrap.lifespan.application_lifespan"
        )
    return isinstance(node, ast.Name) and node.id in canonical_lifespan_aliases


def _is_facade_module_name(module_name: str) -> bool:
    return module_name in {"app", "legacy_app"} or module_name.startswith(("app.", "legacy_app."))


def _uses_dynamic_facade_lookup(tree: ast.Module) -> bool:
    _references, _canonical_lifespan_aliases = _collect_lifecycle_references(tree)
    static_string_bindings = _collect_static_string_bindings(tree)
    reference_snapshots, string_snapshots, _call_results = _collect_lexical_binding_snapshots(
        tree,
        initial_references={
            "__builtins__": "builtins",
            "__import__": "builtins.__import__",
            "dict": "builtins.dict",
            "getattr": "builtins.getattr",
            "vars": "builtins.vars",
        },
        preserve_lifecycle_conflicts=True,
    )
    for node in ast.walk(tree):
        node_id = id(node)
        if node_id not in reference_snapshots:
            continue
        scoped_references = reference_snapshots[node_id]
        scoped_strings = string_snapshots[node_id]
        reference = _resolve_lifecycle_reference(
            node,
            references=scoped_references,
            static_string_bindings=scoped_strings,
        )
        if reference == "sys.modules":
            return True
        if not isinstance(node, ast.Call):
            continue
        function_reference = _resolve_lifecycle_reference(
            node.func,
            references=scoped_references,
            static_string_bindings=scoped_strings,
        )
        if function_reference not in {
            "builtins.__import__",
            "importlib.import_module",
            _POSSIBLE_IMPORT_CALLABLE_REFERENCE,
            _DYNAMIC_LIFECYCLE_REFERENCE,
        }:
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
        module_name = _resolve_static_string(module_node, scoped_strings)
        if module_name is not None and module_name.startswith("."):
            if package_node is None:
                return True
            package_name = _resolve_static_string(package_node, scoped_strings)
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

    def extend_analysis(operation: Callable[[], Sequence[str]]) -> None:
        try:
            errors.extend(operation())
        except LegacyGrowthAnalysisError as exc:
            errors.append(str(exc))

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
        extend_analysis(
            lambda: validate_legacy_growth(
                legacy_source,
                filename=_display(legacy_path, repo_root),
            )
        )
    if doc_text is not None:
        errors.extend(validate_legacy_seam_doc(doc_text, filename=_display(doc_path, repo_root)))
    if legacy_source is not None and food_search_source is not None and lifespan_source is not None:
        extend_analysis(
            lambda: validate_lifecycle_ownership(
                legacy_source,
                food_search_source,
                lifespan_source,
            )
        )
    if legacy_source is not None:
        extend_analysis(lambda: validate_api_key_dependency_ownership(legacy_source, app_sources))
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
        extend_analysis(
            lambda: validate_application_metadata_openapi_ownership(
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
