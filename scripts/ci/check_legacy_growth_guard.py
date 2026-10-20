#!/usr/bin/env python3
"""Fail-closed guard for legacy_app.py compatibility-seam growth."""

from __future__ import annotations

import argparse
import ast
import copy
from collections import Counter
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass, replace
from importlib.util import resolve_name
import operator
from pathlib import Path
import re
import sys
from typing import AbstractSet, Literal, cast

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
CANONICAL_API_KEY_SYMBOLS = frozenset(
    {
        "api_key_header",
        "get_api_key",
        "_get_api_key_dynamic",
        "validate_app_api_key",
        "require_app_api_key",
    }
)
LEGACY_API_KEY_REEXPORTS = frozenset({"get_api_key", "_get_api_key_dynamic"})
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
RETIRED_LEGACY_PYTHON_BINDINGS = frozenset(
    {
        "admin_status",
        "cleanup_expired_logs",
        "debug_env",
        "get_database_status",
        "force_database_update",
        "check_for_updates",
        "rollback_database",
        "bmi_endpoint",
        "plan_endpoint",
        "bmi_endpoint_v1",
        "_resolve_build_targets_callable",
        "PlateDependencies",
        "_compute_premium_plate",
        "api_premium_plate",
        "build_fallback_plate",
        "align_macros_with_targets",
        "aggregate_day_micros",
        "premium_targets_legacy",
        "api_who_targets",
        "api_nutrient_gaps",
        "analyze_nutrient_gaps",
        "make_daily_menu",
        "make_weekly_menu",
        "repair_week_plan",
        "make_plate",
        "build_nutrition_targets",
        "to_csv_day",
        "to_pdf_day",
        "to_csv_week",
        "to_pdf_week",
        "WeeklyPlanFlexibleRequest",
        "INSIGHT_TEXT_MAX_LENGTH",
        "InsightRequest",
        "RAGSourceItem",
        "InsightResponse",
        "INSIGHT_TEMP_UNAVAILABLE_MESSAGE",
        "_execute_insight_request",
        "insight_v1",
        "insight",
        "DB_TO_ALIAS_NUTRIENT_MAP",
        "PlateServiceDependencies",
        "_convert_db_nutrients_to_alias_format",
        "_aggregate_meal_micronutrients",
        "_get_recipe_ingredients_for_meal",
        "_aggregate_day_micronutrients",
        "_macros_to_kcal",
        "sanitize_plate_data",
        "_iter_exception_chain",
        "_is_missing_nh3_error",
        "_raise_missing_nh3_http_error",
        "calculate_heuristic_macros",
        "MANDATORY_MICRO_DEFAULTS",
        "MAX_DAILY_KCAL",
        "MICRO_ALIAS_MAP",
        "MIN_DAILY_KCAL",
        "_alias_micros",
        "_clamp_daily_kcal",
        "_ensure_priority_micros",
        "_generate_who_targets_response",
        "_fallback_targets_response",
        "analyze_nutrient_gaps_response",
        "_OPENAPI_ALLOWED_PREFIXES",
        "_OPENAPI_ALLOWED_EXACT",
        "_is_openapi_public_path",
        "_collect_schema_refs",
        "_prune_unreferenced_schema_components",
        "_build_canonical_openapi",
        "_install_openapi_builder",
        "BMRRequest",
        "BMRRequestLegacy",
        "BMRResponse",
        "NutrientGapsRequest",
        "NutrientGapsResponse",
        "PlateRequest",
        "PlateResponse",
        "VisualShape",
        "WHOTargetsRequest",
        "WHOTargetsResponse",
        "Activity",
        "DietFlag",
        "Goal",
        "Sex",
        "build_who_targets_ui_labels",
        "DataClass",
        "get_retention_manager",
        "LogRetentionManager",
        "_log_retention_manager",
        "TargetsIn",
        "CanonicalTargetsIn",
        "LegacyWeekPlanRequest",
        "WeeklyMenuResponse",
        "get_session",
        "Language",
        "normalize_lang",
        "t",
        "FIBER_MIN_G",
        "_short_git_sha",
        "_is_truthy",
        "_LEGACY_IMPORT_COMPAT_REEXPORTS",
        "BMIRequest",
        "BMIRequestV1",
        "MATPLOTLIB_AVAILABLE",
        "generate_bmi_visualization",
        "add_visualization_if_requested",
        "_BMI_COMPAT_REEXPORTS",
        "_BMI_SCHEMA_COMPAT_REEXPORTS",
        "build_application_metadata",
        "ENHANCED_PLATE_GENERATION_FAILED_DETAIL",
        "INVALID_PREMIUM_PLATE_INPUT_DETAIL",
        "APPLICATION_METADATA",
        "RUNTIME_ENV",
        "_app_env",
        "_application_metadata",
        "tags_metadata",
        "_api_description",
        "lifespan",
        "get_update_scheduler",
        "limiter",
        "limit_if_available",
        "RATE_LIMIT_EXPORTS",
        "RATE_LIMIT_INSIGHT",
        "RATE_LIMIT_429_RESPONSES",
        "_RATE_LIMIT_429_RESPONSES",
        "_TypeVar",
        "_F",
        "_LimitValue",
        "LimiterType",
        "_Limiter",
        "Limiter",
        "slowapi_available",
        "get_api_key",
        "_get_api_key_dynamic",
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
        LegacyFact("router_import", "app.routers.bmi", "bmi_calculate_handler", ""),
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

    class_nodes_by_reference = {
        f"{_CLASS_REFERENCE_PREFIX}{class_node.name}:{id(class_node)}>": class_node
        for class_node in ast.walk(tree)
        if isinstance(class_node, ast.ClassDef)
    }

    def static_reference(node: ast.AST) -> str | None:
        references = route_reference_snapshots.get(id(node), {})
        strings = route_string_snapshots.get(id(node), static_string_bindings)
        return _static_module_reference(
            node,
            module_aliases=references,
            import_module_aliases=frozenset(),
            static_string_bindings=strings,
        )

    def class_owner_reference(node: ast.AST) -> tuple[str, bool] | None:
        reference = static_reference(node)
        if reference is not None and reference.startswith(_CLASS_REFERENCE_PREFIX):
            return reference, False
        if reference is not None and reference.startswith(_INSTANCE_REFERENCE_PREFIX):
            return (
                reference.replace(
                    _INSTANCE_REFERENCE_PREFIX,
                    _CLASS_REFERENCE_PREFIX,
                    1,
                ),
                True,
            )
        if isinstance(node, ast.Call):
            constructor_reference = static_reference(node.func)
            if constructor_reference is not None and constructor_reference.startswith(
                _CLASS_REFERENCE_PREFIX
            ):
                return constructor_reference, True
        return None

    def class_member_binding(
        class_reference: str,
        member_name: str,
        *,
        instance: bool,
        before_line: int,
    ) -> str | None:
        class_node = class_nodes_by_reference.get(class_reference)
        if class_node is None:
            return None

        def merge_binding_flows(
            flows: Sequence[
                tuple[
                    set[str | None],
                    set[str | None],
                    set[str | None],
                    set[str | None],
                ]
            ],
        ) -> tuple[
            set[str | None],
            set[str | None],
            set[str | None],
            set[str | None],
        ]:
            live: set[str | None] = set()
            terminal: set[str | None] = set()
            breaks: set[str | None] = set()
            continues: set[str | None] = set()
            for flow_live, flow_terminal, flow_breaks, flow_continues in flows:
                live.update(flow_live)
                terminal.update(flow_terminal)
                breaks.update(flow_breaks)
                continues.update(flow_continues)
            return live, terminal, breaks, continues

        no_binding_update = object()

        def literal_bool(node: ast.AST) -> bool | None:
            if isinstance(node, ast.Constant) and isinstance(node.value, bool):
                return node.value
            return None

        def literal_iterable_nonempty(node: ast.AST) -> bool | None:
            if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
                if any(isinstance(element, ast.Starred) for element in node.elts):
                    return None
                return bool(node.elts)
            if isinstance(node, ast.Dict):
                return bool(node.keys)
            return None

        def assignment_reference(
            statement: ast.stmt,
            target_matches: Callable[[ast.expr], bool],
        ) -> object:
            value: ast.AST | None = None
            targets: tuple[ast.expr, ...] = ()
            if isinstance(statement, ast.Assign):
                value = statement.value
                targets = tuple(statement.targets)
            elif isinstance(statement, ast.AnnAssign) and statement.value is not None:
                value = statement.value
                targets = (statement.target,)
            if value is None or not any(target_matches(target) for target in targets):
                return no_binding_update
            return static_reference(value)

        def descriptor_return_reference(
            statement: ast.FunctionDef | ast.AsyncFunctionDef,
        ) -> str | None:
            decorator_references = {
                static_reference(decorator) for decorator in statement.decorator_list
            }
            if not decorator_references & {
                "builtins.property",
                "functools.cached_property",
            }:
                return None

            return_references: set[str | None] = set()

            class ReturnVisitor(ast.NodeVisitor):
                def visit_Return(self, child: ast.Return) -> None:
                    return_references.add(
                        static_reference(child.value) if child.value is not None else None
                    )

                def visit_FunctionDef(self, child: ast.FunctionDef) -> None:
                    return

                def visit_AsyncFunctionDef(self, child: ast.AsyncFunctionDef) -> None:
                    return

                def visit_Lambda(self, child: ast.Lambda) -> None:
                    return

                def visit_ClassDef(self, child: ast.ClassDef) -> None:
                    return

            visitor = ReturnVisitor()
            for child in statement.body:
                visitor.visit(child)
            if len(return_references) == 1:
                return next(iter(return_references))
            if any(
                _registration_action_for_reference(reference, APP_ROUTE_METHODS) is not None
                for reference in return_references
            ):
                return _CAPTURED_POSSIBLE_APP_FACTORY_REFERENCE
            return None

        def evaluate_binding_statements(
            statements: Sequence[ast.stmt],
            bindings: set[str | None],
            binding_update: Callable[[ast.stmt], object],
        ) -> tuple[
            set[str | None],
            set[str | None],
            set[str | None],
            set[str | None],
        ]:
            live = set(bindings)
            terminal: set[str | None] = set()
            breaks: set[str | None] = set()
            continues: set[str | None] = set()
            for block_statement in statements:
                if not live:
                    break
                (
                    live,
                    statement_terminal,
                    statement_breaks,
                    statement_continues,
                ) = evaluate_binding_statement(
                    block_statement,
                    live,
                    binding_update,
                )
                terminal.update(statement_terminal)
                breaks.update(statement_breaks)
                continues.update(statement_continues)
            return live, terminal, breaks, continues

        def evaluate_binding_statement(
            statement: ast.stmt,
            bindings: set[str | None],
            binding_update: Callable[[ast.stmt], object],
        ) -> tuple[
            set[str | None],
            set[str | None],
            set[str | None],
            set[str | None],
        ]:
            updated_reference = binding_update(statement)
            if updated_reference is not no_binding_update:
                return {cast(str | None, updated_reference)}, set(), set(), set()
            if isinstance(statement, (ast.Return, ast.Raise)):
                return set(), set(bindings), set(), set()
            if isinstance(statement, ast.Break):
                return set(), set(), set(bindings), set()
            if isinstance(statement, ast.Continue):
                return set(), set(), set(), set(bindings)
            if isinstance(statement, ast.If):
                condition = literal_bool(statement.test)
                if condition is not None:
                    branch = statement.body if condition else statement.orelse
                    return evaluate_binding_statements(branch, bindings, binding_update)
                return merge_binding_flows(
                    [
                        evaluate_binding_statements(statement.body, bindings, binding_update),
                        evaluate_binding_statements(statement.orelse, bindings, binding_update),
                    ],
                )
            if isinstance(statement, ast.While):
                condition = literal_bool(statement.test)
                if condition is False:
                    return evaluate_binding_statements(statement.orelse, bindings, binding_update)
                body_flow = evaluate_binding_statements(
                    statement.body,
                    bindings,
                    binding_update,
                )
                if condition is True:
                    return body_flow[2], body_flow[1], set(), set()
                normal_flow = evaluate_binding_statements(
                    statement.orelse,
                    body_flow[0] | body_flow[3] | bindings,
                    binding_update,
                )
                return (
                    normal_flow[0] | body_flow[2],
                    normal_flow[1] | body_flow[1],
                    set(),
                    set(),
                )
            if isinstance(statement, (ast.For, ast.AsyncFor)):
                nonempty = literal_iterable_nonempty(statement.iter)
                if nonempty is False:
                    return evaluate_binding_statements(statement.orelse, bindings, binding_update)
                body_flow = evaluate_binding_statements(
                    statement.body,
                    bindings,
                    binding_update,
                )
                if nonempty is True:
                    after_body = body_flow[0] | body_flow[2] | body_flow[3]
                    if not after_body:
                        return body_flow
                    orelse_flow = evaluate_binding_statements(
                        statement.orelse,
                        after_body,
                        binding_update,
                    )
                    return merge_binding_flows([body_flow, orelse_flow])
                zero_iteration_flow = evaluate_binding_statements(
                    statement.orelse,
                    bindings,
                    binding_update,
                )
                iterated_flow = evaluate_binding_statements(
                    statement.orelse,
                    body_flow[0] | body_flow[2] | body_flow[3],
                    binding_update,
                )
                return merge_binding_flows([body_flow, zero_iteration_flow, iterated_flow])
            return set(bindings), set(), set(), set()

        def class_body_update(statement: ast.stmt) -> object:
            if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
                return (
                    descriptor_return_reference(statement)
                    if statement.name == member_name
                    else no_binding_update
                )
            assignment = assignment_reference(
                statement,
                lambda target: isinstance(target, ast.Name) and target.id == member_name,
            )
            if assignment is no_binding_update:
                return no_binding_update
            value = statement.value if isinstance(statement, (ast.Assign, ast.AnnAssign)) else None
            if (
                isinstance(value, ast.Call)
                and len(value.args) == 1
                and not value.keywords
                and static_reference(value.func) == "builtins.staticmethod"
            ):
                return static_reference(value.args[0])
            return assignment

        def class_body_defines_member(statements: Sequence[ast.stmt]) -> bool:
            for statement in statements:
                if class_body_update(statement) is not no_binding_update:
                    return True
                if isinstance(statement, ast.If):
                    condition = literal_bool(statement.test)
                    if condition is not None:
                        if class_body_defines_member(
                            statement.body if condition else statement.orelse
                        ):
                            return True
                    elif class_body_defines_member(statement.body) and class_body_defines_member(
                        statement.orelse,
                    ):
                        return True
                    continue
                if isinstance(statement, (ast.For, ast.AsyncFor)):
                    nonempty = literal_iterable_nonempty(statement.iter)
                    if nonempty is True and class_body_defines_member(statement.body):
                        return True
                    if nonempty is False and class_body_defines_member(statement.orelse):
                        return True
                    if (
                        nonempty is None
                        and class_body_defines_member(statement.body)
                        and class_body_defines_member(statement.orelse)
                    ):
                        return True
            return False

        def module_update(statement: ast.stmt) -> object:
            assignment = assignment_reference(
                statement,
                lambda target: (
                    isinstance(target, ast.Attribute)
                    and target.attr == member_name
                    and class_owner_reference(target.value) == (class_reference, False)
                ),
            )
            if assignment is not no_binding_update:
                return assignment
            if not isinstance(statement, ast.Expr) or not isinstance(statement.value, ast.Call):
                return no_binding_update
            call = statement.value
            if static_reference(call.func) != "builtins.setattr" or len(call.args) < 3:
                return no_binding_update
            if _literal_value(call.args[1]) == member_name and class_owner_reference(
                call.args[0]
            ) == (class_reference, False):
                return static_reference(call.args[2])
            return no_binding_update

        class_flow = evaluate_binding_statements(
            class_node.body,
            {None},
            class_body_update,
        )
        class_bindings = set().union(*class_flow)
        class_defines_member = class_body_defines_member(class_node.body)
        if not class_defines_member:
            for base in class_node.bases:
                base_reference = static_reference(base)
                if base_reference is None or not base_reference.startswith(
                    _CLASS_REFERENCE_PREFIX,
                ):
                    continue
                if (
                    class_member_binding(
                        base_reference,
                        member_name,
                        instance=False,
                        before_line=before_line,
                    )
                    == _CAPTURED_POSSIBLE_APP_FACTORY_REFERENCE
                ):
                    class_bindings.add(_CAPTURED_POSSIBLE_APP_FACTORY_REFERENCE)
                    break
        module_statements = tuple(
            statement for statement in tree.body if getattr(statement, "lineno", 0) < before_line
        )
        module_flow = evaluate_binding_statements(
            module_statements,
            class_bindings,
            module_update,
        )
        possible_bindings = set().union(*module_flow)

        if instance:
            for statement in class_node.body:
                if not (
                    isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and statement.name == "__init__"
                ):
                    continue
                parameters = (*statement.args.posonlyargs, *statement.args.args)
                if not parameters:
                    break
                instance_name = parameters[0].arg

                def instance_update(init_statement: ast.stmt) -> object:
                    assignment = assignment_reference(
                        init_statement,
                        lambda target: (
                            isinstance(target, ast.Attribute)
                            and isinstance(target.value, ast.Name)
                            and target.value.id == instance_name
                            and target.attr == member_name
                        ),
                    )
                    if assignment is not no_binding_update:
                        return assignment
                    if not isinstance(init_statement, ast.Expr) or not isinstance(
                        init_statement.value,
                        ast.Call,
                    ):
                        return no_binding_update
                    call = init_statement.value
                    if static_reference(call.func) != "builtins.setattr" or len(call.args) < 3:
                        return no_binding_update
                    if (
                        isinstance(call.args[0], ast.Name)
                        and call.args[0].id == instance_name
                        and _literal_value(call.args[1]) == member_name
                    ):
                        return static_reference(call.args[2])
                    return no_binding_update

                instance_flow = evaluate_binding_statements(
                    statement.body,
                    possible_bindings,
                    instance_update,
                )
                possible_bindings = set().union(*instance_flow)
                break

        if _CAPTURED_POSSIBLE_APP_FACTORY_REFERENCE in possible_bindings:
            return _CAPTURED_POSSIBLE_APP_FACTORY_REFERENCE
        return next(iter(possible_bindings)) if len(possible_bindings) == 1 else None

    def captured_factory_reference(node: ast.AST, *, before_line: int) -> str | None:
        call_result = route_call_result_snapshots.get(id(node))
        if call_result is not None and (
            call_result.reference == _CAPTURED_POSSIBLE_APP_FACTORY_REFERENCE
        ):
            return call_result.reference
        reference = static_reference(node)
        if reference == _CAPTURED_POSSIBLE_APP_FACTORY_REFERENCE:
            return reference
        if isinstance(node, ast.Attribute):
            owner = class_owner_reference(node.value)
            if owner is None:
                return reference
            class_reference, instance = owner
            return class_member_binding(
                class_reference,
                node.attr,
                instance=instance,
                before_line=before_line,
            )
        if not (
            isinstance(node, ast.Call)
            and len(node.args) >= 2
            and static_reference(node.func) == "builtins.getattr"
        ):
            return reference
        member_name = _literal_value(node.args[1])
        if not isinstance(member_name, str):
            return reference
        owner = class_owner_reference(node.args[0])
        if owner is None:
            return reference
        class_reference, instance = owner
        return class_member_binding(
            class_reference,
            member_name,
            instance=instance,
            before_line=before_line,
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
            class_owner = class_owner_reference(func.value)
            if class_owner is not None:
                class_reference, instance = class_owner
                member_reference = class_member_binding(
                    class_reference,
                    func.attr,
                    instance=instance,
                    before_line=func.lineno,
                )
                action = _registration_action_for_reference(member_reference, methods)
                if action is not None:
                    return action
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
                if action is None:
                    reference = captured_factory_reference(
                        decorator.func,
                        before_line=decorator.lineno,
                    )
                    if reference == _CAPTURED_POSSIBLE_APP_FACTORY_REFERENCE:
                        action = "dynamic"
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
                captured_path = scoped_strings.get(call.func.id)
                captured_reference = route_reference_snapshots[id(call)].get(call.func.id)
                if (
                    captured_path is not None
                    and captured_reference is not None
                    and captured_reference.startswith(_ROUTE_DECORATOR_REFERENCE_PREFIX)
                ):
                    captured_route_action = _registration_action_for_reference(
                        captured_reference.removeprefix(_ROUTE_DECORATOR_REFERENCE_PREFIX),
                        APP_ROUTE_METHODS,
                    )
                else:
                    captured_route_action = None
                if captured_route_action is not None and captured_path is not None:
                    facts.add(
                        LegacyFact(
                            "registration",
                            captured_route_action,
                            (
                                "<dynamic>"
                                if captured_path == _DYNAMIC_STRING_BINDING
                                else captured_path
                            ),
                            "",
                        )
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
    if _CAPTURED_POSSIBLE_APP_FACTORY_REFERENCE in references:
        return (
            _MAPPING_CAPTURED_POSSIBLE_APP_FACTORY_REFERENCE
            if mapping
            else _ITERABLE_CAPTURED_POSSIBLE_APP_FACTORY_REFERENCE
        )
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
        indexed_shape = _indexed_tuple_shape(parent)
        if indexed_shape is not None:
            index = _literal_value(node.slice)
            sensitive_index, arity = indexed_shape
            if isinstance(index, int) and 0 <= index < arity and index != sensitive_index:
                return _KNOWN_NON_APP_REFERENCE
            return _POSSIBLE_APP_CALL_REFERENCE
        if parent in {
            _ITERABLE_CAPTURED_POSSIBLE_APP_FACTORY_REFERENCE,
            _MAPPING_CAPTURED_POSSIBLE_APP_FACTORY_REFERENCE,
        }:
            return _CAPTURED_POSSIBLE_APP_FACTORY_REFERENCE
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
        if wrapped_reference == _CAPTURED_POSSIBLE_APP_FACTORY_REFERENCE:
            return wrapped_reference
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


def _resolve_static_string(
    node: ast.AST,
    bindings: Mapping[str, str],
    *,
    ownership_family: Literal["api_key", "openapi"] | None = None,
) -> str | None:
    def fragments(value: ast.AST) -> list[str] | None:
        if isinstance(value, ast.NamedExpr):
            return fragments(value.value)
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            return [value.value]
        if isinstance(value, ast.Name):
            selected = bindings.get(value.id)
            return [selected] if selected is not None else None
        if isinstance(value, ast.BinOp) and isinstance(value.op, ast.Add):
            left = fragments(value.left)
            right = fragments(value.right)
            if left is None or right is None:
                return None
            left.extend(right)
            return left
        if isinstance(value, ast.JoinedStr):
            parts: list[str] = []
            for item in value.values:
                if isinstance(item, ast.Constant) and isinstance(item.value, str):
                    parts.append(item.value)
                elif isinstance(item, ast.FormattedValue):
                    selected_parts = fragments(item.value)
                    if selected_parts is None:
                        return None
                    parts.extend(selected_parts)
                else:
                    return None
            return parts
        if (
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Attribute)
            and value.func.attr == "join"
            and len(value.args) == 1
            and isinstance(value.args[0], (ast.List, ast.Tuple))
        ):
            separator = fragments(value.func.value)
            if separator is None:
                return None
            joined: list[str] = []
            for index, item in enumerate(value.args[0].elts):
                selected_parts = fragments(item)
                if selected_parts is None:
                    return None
                if index:
                    joined.extend(separator)
                joined.extend(selected_parts)
            return joined
        return None

    parts = fragments(node)
    if parts is None:
        return None
    rendered = "".join(parts)
    if ownership_family is None:
        # Other existing callers retain their exact renderer, including scoped
        # route facts. This mode is not an ownership uncertainty projection.
        return rendered
    contributing = [part for part in parts if part != ""]
    if not contributing:
        return ""
    if len(contributing) == 1:
        return contributing[0]
    if _POSSIBLE_OPENAPI_SYMBOL in contributing:
        # Preserve the nominal family fact, not the spelling of its token.
        return _POSSIBLE_OPENAPI_SYMBOL
    if ownership_family == "openapi":
        # Retain incumbent fragments across bindings (enapi + unknown, then op
        # + that value). This is compatible evidence, not a concrete value.
        return rendered
    abstract_facts = {
        _DYNAMIC_STRING_BINDING,
        _POSSIBLE_API_KEY_SYMBOL,
        _POSSIBLE_OPENAPI_SYMBOL,
        _POSSIBLE_ROUTE_METHOD,
        _CONFLICTED_ROUTE_METHOD,
    }
    if not any(part in abstract_facts for part in contributing):
        return rendered
    concrete_run: list[str] = []
    for part in contributing:
        if part in abstract_facts:
            if "openapi" in "".join(concrete_run).casefold():
                return _POSSIBLE_OPENAPI_SYMBOL
            concrete_run.clear()
        else:
            concrete_run.append(part)
    if "openapi" in "".join(concrete_run).casefold():
        return _POSSIBLE_OPENAPI_SYMBOL
    return _DYNAMIC_STRING_BINDING


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


def _expand_ordered_static_positional_arguments(
    arguments: Sequence[ast.expr],
    *,
    remaining_depth: int = _MAX_ITERABLE_ELEMENT_BINDING_DEPTH,
) -> tuple[tuple[ast.expr, bool], ...]:
    """Flatten bounded literal ``*args`` without discarding argument order."""

    ordered: list[tuple[ast.expr, bool]] = []
    for argument in arguments:
        if not isinstance(argument, ast.Starred):
            ordered.append((argument, False))
            continue
        value = argument.value
        if remaining_depth <= 0 or not isinstance(value, (ast.List, ast.Tuple)):
            ordered.append((value, True))
            continue
        ordered.extend(
            _expand_ordered_static_positional_arguments(
                value.elts,
                remaining_depth=remaining_depth - 1,
            )
        )
    return tuple(ordered)


def _expand_static_positional_arguments(
    arguments: Sequence[ast.expr],
    *,
    remaining_depth: int = _MAX_ITERABLE_ELEMENT_BINDING_DEPTH,
) -> tuple[tuple[ast.expr, ...], tuple[ast.expr, ...]]:
    """Flatten bounded literal ``*args`` while retaining unresolved sources."""

    ordered = _expand_ordered_static_positional_arguments(
        arguments,
        remaining_depth=remaining_depth,
    )
    return (
        tuple(argument for argument, unresolved in ordered if not unresolved),
        tuple(argument for argument, unresolved in ordered if unresolved),
    )


@dataclass(frozen=True)
class _DeferredFunctionCall:
    function: _FunctionNode | None
    arguments: tuple[tuple[str, _ResolvedBinding], ...]
    partial_template: bool = False
    partial_positional: tuple[_ResolvedBinding, ...] = ()
    partial_unresolved: bool = False
    builtin_reference: (
        Literal["builtins.getattr", "builtins.setattr", "builtins.delattr"] | None
    ) = None

    operation: Literal["real", "map", "filter", "starmap", "to_thread"] = "real"
    execution: Literal["iterate", "await"] | None = None
    value_key: _DeferredValueKey | None = None
    callee: _ResolvedBinding | None = None
    operands: tuple[_ResolvedBinding, ...] = ()
    keywords: tuple[tuple[str, _ResolvedBinding], ...] = ()
    unresolved_keywords: tuple[_ResolvedBinding, ...] = ()
    payload_known: bool = True


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
    ordered_items: tuple[_ResolvedBinding, ...] | None = None
    call_receivers: frozenset[tuple[_FunctionNode, str, _ResolvedBinding]] = frozenset()


_DeferredValueKey = tuple[
    Literal["precise", "transient", "summary"],
    ast.AST,
    tuple[tuple[ast.AST, int | None], ...],
    ast.AST | None,
]
_DeferredProgress = tuple[
    _DeferredValueKey,
    Literal["available", "active", "consumed", "unknown"],
    _ResolvedBinding | None,
]
_DeferredFlowSnapshot = tuple[
    tuple[tuple["_LexicalBindings", "_LexicalBindings"], ...],
    frozenset[_DeferredFunctionCall | _DeferredProgress],
    dict[int, _ResolvedBinding],
    dict[int, frozenset[_DeferredFunctionCall]],
    frozenset[int],
    ast.AST | None,
]


def _normalize_resolved_binding(
    binding: _ResolvedBinding,
    *,
    remaining_depth: int = _MAX_ITERABLE_ELEMENT_BINDING_DEPTH,
) -> _ResolvedBinding:
    """Bound every transported payload without losing deferred presence."""

    def summary(call: _DeferredFunctionCall) -> _DeferredFunctionCall:
        key = call.value_key
        if key is None:
            raise LegacyGrowthAnalysisError(
                "legacy deferred payload exceeds the existing depth bound"
            )
        return _DeferredFunctionCall(
            function=None,
            arguments=(),
            operation=call.operation,
            execution=call.execution
            or (
                "await"
                if isinstance(call.function, ast.AsyncFunctionDef)
                and not _function_is_generator(call.function)
                else "iterate"
            ),
            value_key=("summary", key[1], key[2], key[3]),
            payload_known=False,
        )

    if remaining_depth <= 0:
        if any(call.partial_template for call in binding.deferred_calls):
            raise LegacyGrowthAnalysisError("partial payload exceeds the existing depth bound")
        # Arbitrary scalar strings can carry identity; summary payloads keep no
        # captured function/receiver/class/default/scalar facts.
        return _ResolvedBinding(
            _POSSIBLE_APP_CALL_REFERENCE,
            _DYNAMIC_STRING_BINDING,
            deferred_calls=frozenset(
                summary(call) for call in binding.deferred_calls if not call.partial_template
            ),
        )

    def nested(value: _ResolvedBinding) -> _ResolvedBinding:
        return _normalize_resolved_binding(value, remaining_depth=remaining_depth - 1)

    deferred: set[_DeferredFunctionCall] = set()
    for call in binding.deferred_calls:
        normalized = replace(
            call,
            arguments=tuple((name, nested(value)) for name, value in call.arguments),
            callee=nested(call.callee) if call.callee is not None else None,
            operands=tuple(nested(value) for value in call.operands),
            keywords=tuple((name, nested(value)) for name, value in call.keywords),
            unresolved_keywords=tuple(nested(value) for value in call.unresolved_keywords),
            partial_positional=tuple(nested(value) for value in call.partial_positional),
        )
        if normalized != call:
            normalized = (
                replace(normalized, partial_unresolved=True)
                if call.partial_template
                else summary(call)
            )
        deferred.add(normalized)
    # Mapping is an existing identity-bearing owner, like a captured lexical
    # scope, not another nested RB copy. Its entry values are captured/normalized
    # at construction. Replacing it here would detach its invalidation identity.
    normalized_binding = replace(
        binding,
        deferred_calls=frozenset(deferred),
        iterable_element=(
            nested(binding.iterable_element) if binding.iterable_element is not None else None
        ),
        ordered_items=(
            tuple(nested(item) for item in binding.ordered_items)
            if binding.ordered_items is not None
            else None
        ),
        call_receivers=frozenset(
            (target, kind, nested(receiver)) for target, kind, receiver in binding.call_receivers
        ),
    )
    return binding if normalized_binding == binding else normalized_binding


@dataclass(frozen=True)
class _StaticMappingEntry:
    key: ast.AST | None
    binding: _ResolvedBinding


@dataclass(frozen=True)
class _StaticMapping:
    site: ast.Dict
    entries: tuple[_StaticMappingEntry, ...]


@dataclass(frozen=True)
class _MappingLookupReceiver:
    mapping: _StaticMapping | None
    possible_value: _ResolvedBinding | None
    invalidation_count: int
    last_clear_count: int


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


def _effective_static_mapping_entries(
    entries: Sequence[_StaticMappingEntry],
) -> tuple[_StaticMappingEntry, ...]:
    """Keep last-write-wins values for statically repeated mapping keys."""

    effective_reversed: list[_StaticMappingEntry] = []
    seen_keys: list[object] = []
    for entry in reversed(entries):
        if entry.key is None:
            effective_reversed.append(entry)
            continue
        candidate = _literal_value(entry.key)
        if candidate is _UNRESOLVED_LITERAL_VALUE:
            effective_reversed.append(entry)
            continue
        duplicate = False
        for seen in seen_keys:
            try:
                if candidate == seen:
                    duplicate = True
                    break
            except (TypeError, ValueError):
                continue
        if duplicate:
            continue
        seen_keys.append(candidate)
        effective_reversed.append(entry)
    return tuple(reversed(effective_reversed))


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
        self.ordered_items: dict[str, tuple[_ResolvedBinding, ...]] = {}
        self.call_receivers: dict[str, frozenset[tuple[_FunctionNode, str, _ResolvedBinding]]] = {}
        self._flow_owner: _ApiKeyLookupVisitor | None = None
        self._flow_snapshot: _DeferredFlowSnapshot | None = None
        self.bound_names: set[str] = set()
        self.possibly_bound_names: set[str] = set()

    def clone(self, *, capture_flow: bool = True) -> _LexicalBindings:
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
        clone.ordered_items = dict(self.ordered_items)
        clone.call_receivers = dict(self.call_receivers)
        clone.bound_names = set(self.bound_names)
        clone.possibly_bound_names = set(self.possibly_bound_names)
        if capture_flow and self._flow_owner is not None:
            if self._flow_owner.scope is self:
                self._flow_snapshot = self._flow_owner._capture_deferred_flow(self)
            clone._flow_snapshot = self._flow_snapshot
            clone._flow_owner = self._flow_owner
        return clone

    def detached_clone(
        self, memo: dict[_LexicalBindings, _LexicalBindings] | None = None
    ) -> _LexicalBindings:
        memo = {} if memo is None else memo
        existing = memo.get(self)
        if existing is not None:
            return existing
        clone = _LexicalBindings(
            parent=None,
            local_names=self.local_names,
            scope_kind=self.scope_kind,
        )
        memo[self] = clone
        clone.parent = self.parent.detached_clone(memo) if self.parent is not None else None
        clone.references = dict(self.references)
        clone.strings = dict(self.strings)
        clone.callables = dict(self.callables)
        clone.deferred_calls = dict(self.deferred_calls)
        clone.mappings = dict(self.mappings)
        clone.class_references = dict(self.class_references)
        clone.descriptors = dict(self.descriptors)
        clone.iterable_elements = dict(self.iterable_elements)
        clone.ordered_items = dict(self.ordered_items)
        clone.call_receivers = dict(self.call_receivers)
        clone.bound_names = set(self.bound_names)
        clone.possibly_bound_names = set(self.possibly_bound_names)
        return clone

    def function_parent(self) -> _LexicalBindings:
        """Keep parameter scopes while excluding class-only function visibility."""

        if self.parent is not None and self.scope_kind == "class":
            return self.parent.function_parent()
        if self.parent is not None and self.scope_kind == "type_parameters":
            parent = self.parent.function_parent()
            if parent is not self.parent:
                projected = self.clone()
                projected.parent = parent
                return projected
        return self

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

    def resolve_ordered_items(self, name: str) -> tuple[_ResolvedBinding, ...] | None:
        if name in self.ordered_items:
            return self.ordered_items[name]
        if name in self.local_names:
            return None
        return self.parent.resolve_ordered_items(name) if self.parent is not None else None

    def resolve_call_receivers(
        self, name: str
    ) -> frozenset[tuple[_FunctionNode, str, _ResolvedBinding]]:
        if name in self.call_receivers:
            return self.call_receivers[name]
        if name in self.local_names:
            return frozenset()
        return self.parent.resolve_call_receivers(name) if self.parent is not None else frozenset()

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
        ordered_items: tuple[_ResolvedBinding, ...] | None = None,
        call_receivers: frozenset[tuple[_FunctionNode, str, _ResolvedBinding]] = frozenset(),
        runtime_binding: bool = True,
    ) -> None:
        normalized = _normalize_resolved_binding(
            _ResolvedBinding(
                reference,
                string,
                callables,
                deferred_calls,
                mapping,
                class_references,
                descriptors,
                iterable_element,
                ordered_items,
                call_receivers,
            )
        )
        reference, string = normalized.reference, normalized.string
        callables, deferred_calls, mapping = (
            normalized.callables,
            normalized.deferred_calls,
            normalized.mapping,
        )
        class_references, descriptors = normalized.class_references, normalized.descriptors
        iterable_element, ordered_items = normalized.iterable_element, normalized.ordered_items
        call_receivers = normalized.call_receivers
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
        if ordered_items is None:
            self.ordered_items.pop(name, None)
        else:
            self.ordered_items[name] = ordered_items
        if call_receivers:
            self.call_receivers[name] = call_receivers
        else:
            self.call_receivers.pop(name, None)
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
        self.ordered_items.pop(name, None)
        self.call_receivers.pop(name, None)
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


def _has_postponed_annotations(tree: ast.Module) -> bool:
    return any(
        isinstance(statement, ast.ImportFrom)
        and statement.module == "__future__"
        and any(alias.name == "annotations" for alias in statement.names)
        for statement in tree.body
    )


def _function_local_binding_names(
    node: ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda,
    *,
    postponed_annotations: bool = False,
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

        def _visit_function_header(self, child: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
            for expression in (
                *child.decorator_list,
                *child.args.defaults,
                *child.args.kw_defaults,
            ):
                if expression is not None:
                    self.visit(expression)
            if not postponed_annotations:
                for argument in _iter_function_parameters(child.args):
                    if argument.annotation is not None:
                        self.visit(argument.annotation)
                if child.returns is not None:
                    self.visit(child.returns)

        def visit_FunctionDef(self, child: ast.FunctionDef) -> None:
            names.add(child.name)
            self._visit_function_header(child)

        def visit_AsyncFunctionDef(self, child: ast.AsyncFunctionDef) -> None:
            names.add(child.name)
            self._visit_function_header(child)

        def visit_ClassDef(self, child: ast.ClassDef) -> None:
            names.add(child.name)
            for expression in (*child.decorator_list, *child.bases):
                self.visit(expression)
            for keyword in child.keywords:
                self.visit(keyword.value)

        def visit_Lambda(self, child: ast.Lambda) -> None:
            for default in (*child.args.defaults, *child.args.kw_defaults):
                if default is not None:
                    self.visit(default)

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
            if child.type is not None:
                self.visit(child.type)
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


def _statement_binding_names(
    statements: Sequence[ast.stmt], *, postponed_annotations: bool = False
) -> frozenset[str]:
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
    return _function_local_binding_names(synthetic, postponed_annotations=postponed_annotations)


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
_ROUTE_DECORATOR_REFERENCE_PREFIX = "pulseplate.app.route.decorator:"
_POSSIBLE_MIDDLEWARE_DECORATOR_REFERENCE = "<possible:pulseplate.app.middleware.decorator>"
_POSSIBLE_GETATTR_REFERENCE = "<possible:builtins.getattr>"
_POSSIBLE_API_KEY_SYMBOL = "<possible:api_key_symbol>"
_POSSIBLE_OPENAPI_SYMBOL = "<possible:openapi_symbol>"
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
_ITERABLE_CAPTURED_POSSIBLE_APP_FACTORY_REFERENCE = "<iterable:captured-possible-app-factory>"
_MAPPING_CAPTURED_POSSIBLE_APP_FACTORY_REFERENCE = "<mapping:captured-possible-app-factory>"
_INDEXED_PAIR_ELEMENT_REFERENCE = "<iterable:indexed-pair>"
_REVERSED_INDEXED_PAIR_ELEMENT_REFERENCE = "<iterable:reversed-indexed-pair>"
_INDEXED_TUPLE_ELEMENT_REFERENCE_PREFIX = "<iterable:indexed-tuple:"
_KNOWN_NON_APP_REFERENCE = "<known:non-app>"
_CLASS_REFERENCE_PREFIX = "<class:"
_INSTANCE_REFERENCE_PREFIX = "<instance:"
_BUILTINS_OBJECT_STATE_NAME = "<state:builtins.object>"
_SAFE_BUILTINS_OBJECT_REFERENCE = "<safe:builtins.object>"
_POISONED_BUILTINS_OBJECT_REFERENCE = "<poisoned:builtins.object>"
_CAPTURED_SAFE_BUILTINS_OBJECT_REFERENCE = "<captured-safe:builtins.object>"
_CAPTURED_POSSIBLE_APP_FACTORY_REFERENCE = "<captured-possible-app-factory>"
_BUILTINS_NAMESPACE_REFERENCE = "<namespace:builtins>"
_POSSIBLE_BUILTINS_NAMESPACE_REFERENCE = "<possible:namespace:builtins>"
_MODULE_NAMESPACE_REFERENCE = "<namespace:module>"
_POSSIBLE_OBJECT_NAMESPACE_REFERENCE = "<possible:namespace:object>"
_POSSIBLE_NAMESPACE_MUTATOR_REFERENCE_PREFIX = "<possible:namespace-mutator>."
_MAX_LOOP_BINDING_ITERATIONS = 32
_MAX_TOTAL_LOOP_BINDING_ITERATIONS = 128
_DICT_NAMESPACE_LOOKUP_METHODS = frozenset({"get", "__getitem__", "pop", "setdefault"})
_UNBOUND_DICT_LOOKUP_REFERENCES = frozenset(
    f"builtins.dict.{method}" for method in _DICT_NAMESPACE_LOOKUP_METHODS
)
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
_ITERABLE_FILTERING_BUILTIN_REFERENCES = frozenset({"builtins.filter"})
_ITERABLE_CONCATENATING_REFERENCES = frozenset({"itertools.chain"})
_ITERABLE_FLATTENING_REFERENCES = frozenset({"itertools.chain.from_iterable"})
_ITERABLE_PRESERVING_WRAPPER_REFERENCES = _ITERABLE_PRESERVING_BUILTIN_REFERENCES | {
    "itertools.islice"
}


def _namespace_mutator_method(reference: str | None, *, legacy_only: bool = False) -> str | None:
    if reference is None:
        return None
    legacy_qualifier = f"{_POSSIBLE_LEGACY_REFERENCE}.__dict__."
    if legacy_only:
        for prefix in ("legacy_app.__dict__.", legacy_qualifier):
            if reference.startswith(prefix):
                method = reference.removeprefix(prefix)
                return method if method in _MAPPING_MUTATOR_METHODS | {"*"} else None
    for prefix in (
        f"{_BUILTINS_NAMESPACE_REFERENCE}.",
        f"{_MODULE_NAMESPACE_REFERENCE}.",
        _POSSIBLE_NAMESPACE_MUTATOR_REFERENCE_PREFIX,
        "builtins.dict.",
    ):
        if reference.startswith(prefix):
            method = reference.removeprefix(prefix)
            if method.startswith(legacy_qualifier):
                method = method.removeprefix(legacy_qualifier)
                return method if method in _MAPPING_MUTATOR_METHODS | {"*"} else None
            return None if legacy_only else method
    return None


_INDEXING_ITERABLE_BUILTIN_REFERENCES = frozenset({"builtins.enumerate"})
_ZIPPING_ITERABLE_BUILTIN_REFERENCES = frozenset({"builtins.zip"})


def _indexed_tuple_reference(sensitive_index: int, arity: int) -> str:
    return f"{_INDEXED_TUPLE_ELEMENT_REFERENCE_PREFIX}{sensitive_index}:{arity}>"


def _indexed_tuple_shape(reference: str | None) -> tuple[int, int] | None:
    if reference == _INDEXED_PAIR_ELEMENT_REFERENCE:
        return 1, 2
    if reference == _REVERSED_INDEXED_PAIR_ELEMENT_REFERENCE:
        return 0, 2
    if reference is None or not reference.startswith(_INDEXED_TUPLE_ELEMENT_REFERENCE_PREFIX):
        return None
    payload = reference.removeprefix(_INDEXED_TUPLE_ELEMENT_REFERENCE_PREFIX).removesuffix(">")
    try:
        sensitive_index_text, arity_text = payload.split(":", maxsplit=1)
        sensitive_index = int(sensitive_index_text)
        arity = int(arity_text)
    except ValueError:
        return None
    if arity < 1 or not 0 <= sensitive_index < arity:
        return None
    return sensitive_index, arity


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
        ownership_family: Literal["api_key", "openapi"] = "api_key",
        purpose: Literal["ordinary", "ownership_audit"] = "ordinary",
        expression_snapshots_only: bool = False,
    ) -> None:
        if ownership_family not in {"api_key", "openapi"}:
            raise ValueError("unsupported ownership symbol family")
        if purpose not in {"ordinary", "ownership_audit"}:
            raise ValueError("unsupported legacy analysis purpose")
        self.filename = filename
        self.ownership_family = ownership_family
        self._analysis_purpose = purpose
        self._expression_snapshots_only = expression_snapshots_only
        self.errors = errors
        self.reference_snapshots = reference_snapshots
        self.string_snapshots = string_snapshots
        self.call_result_snapshots = call_result_snapshots
        self._snapshot_collection = (reference_snapshots, string_snapshots, call_result_snapshots)
        self._snapshot_analysis_replaying: dict[int, bool] = {}
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
        self._consumed_deferred_calls: set[_DeferredFunctionCall | _DeferredProgress] = set()
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
        self._mapping_invalidation_counts: dict[_StaticMapping, int] = {}
        self._mapping_last_clear_counts: dict[_StaticMapping, int] = {}
        self._active_function_replays: set[_FunctionNode] = set()
        self._active_async_replay_depth = 0
        self._active_task_group_depth = 0
        self._outward_binding_targets: list[dict[str, _LexicalBindings]] = []
        self._awaited_call_ids: set[int] = set()
        self._iterated_call_ids: set[int] = set()
        self._deferred_mapping_mutator_attribute_ids: set[int] = set()
        self._previsited_call_receiver_attribute_ids: set[int] = set()
        self._call_result_bindings: dict[int, _ResolvedBinding] = {}
        self._deferred_call_bindings: dict[int, frozenset[_DeferredFunctionCall]] = {}
        self._return_binding_collectors: list[list[_ResolvedBinding]] = []
        self._replay_calls_enabled = True
        self._sync_only_body_analysis = False
        self._postponed_annotations = False
        self._remaining_loop_iterations = _MAX_TOTAL_LOOP_BINDING_ITERATIONS
        self.scope = _LexicalBindings(parent=None)
        self.scope._flow_owner = self
        self.scope.bind("__builtins__", reference="builtins", string=None)
        self.scope.bind("__import__", reference="builtins.__import__", string=None)
        self.scope.bind("getattr", reference="builtins.getattr", string=None)
        self.scope.bind("globals", reference="builtins.globals", string=None)
        self.scope.bind("dict", reference="builtins.dict", string=None)
        self.scope.bind("map", reference="builtins.map", string=None)
        self.scope.bind("object", reference="builtins.object", string=None)
        self.scope.bind("setattr", reference="builtins.setattr", string=None)
        self.scope.bind("delattr", reference="builtins.delattr", string=None)
        self.scope.bind("vars", reference="builtins.vars", string=None)
        self.scope.bind("locals", reference="builtins.locals", string=None)
        self.scope.bind("anext", reference="builtins.anext", string=None)
        for builtin_name in sorted(
            {
                reference.removeprefix("builtins.")
                for reference in (
                    _ITERABLE_PRESERVING_BUILTIN_REFERENCES
                    | _ITERABLE_ELEMENT_BUILTIN_REFERENCES
                    | _ITERABLE_FILTERING_BUILTIN_REFERENCES
                    | _INDEXING_ITERABLE_BUILTIN_REFERENCES
                    | _ZIPPING_ITERABLE_BUILTIN_REFERENCES
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
        self.scope.bind("property", reference="builtins.property", string=None)
        self.scope.bind("staticmethod", reference="builtins.staticmethod", string=None)
        for name, reference in (initial_references or {}).items():
            self.scope.bind(name, reference=reference, string=None)

    def visit_Module(self, node: ast.Module) -> None:
        self._postponed_annotations = _has_postponed_annotations(node)
        self._visit_statements(node.body)

    def visit(
        self,
        node: ast.AST,
        *,
        iterable_callback_inputs: (
            list[
                tuple[
                    ast.Call,
                    str,
                    _FunctionNode | _DeferredFunctionCall,
                    dict[str, _ResolvedBinding],
                ]
            ]
            | None
        ) = None,
        iteration_result_node: ast.expr | None = None,
    ) -> object:
        if self.reference_snapshots is not None or self.string_snapshots is not None:
            self._record_snapshot(node)
        records_exception_state = (
            bool(self._exception_scope_collectors)
            and isinstance(node, ast.expr)
            and not isinstance(node, (ast.Constant, ast.NamedExpr))
        )
        if records_exception_state:
            self._record_exception_scope()
        inherited_request = self._invocation_outcome_request()
        framed = isinstance(
            node,
            (ast.Module, ast.Call, ast.For, ast.AsyncFor, ast.While, ast.List, ast.Tuple, ast.Dict),
        ) or (
            inherited_request is not None
            and isinstance(node, ast.Await)
            and isinstance(node.value, ast.Call)
            and node in self._source_nodes()
            and node.value in self._source_nodes()
        )
        if framed:
            originals = (
                frozenset(ast.walk(node))
                if isinstance(node, ast.Module) or not self._active_replay_contexts
                else self._source_nodes()
            )
            self._active_replay_contexts.append(
                (
                    self._current_replay_context(),
                    node,
                    (),
                    (),
                    self._private_deferred_corridor(node),
                    (),
                    None,
                    originals,
                    (
                        _TerminalControlBindings(return_scopes=[], raise_scopes=[])
                        if inherited_request is not None
                        else None
                    ),
                )
            )
            frame = cast(tuple[object, ...], self._active_replay_contexts[-1])
            # Entry Flow is read only by this frame's transient install/GC.
            # An empty corridor cannot own a transient key, so keep its unused
            # entry slot empty while preserving the source/capture frame itself.
            if frame[4]:
                self._active_replay_contexts[-1] = (
                    *frame[:6],
                    self._capture_deferred_flow(self.scope),
                    *frame[7:],
                )
        collectors = self._deferred_abrupt_collectors()
        offsets = [(items, len(items)) for items in collectors]
        try:
            if isinstance(node, ast.Call) and (
                iterable_callback_inputs is not None or iteration_result_node is not None
            ):
                result: object = (
                    self.visit_Call(node, iterable_callback_inputs=iterable_callback_inputs)
                    if iteration_result_node is None
                    else self.visit_Call(
                        node,
                        iterable_callback_inputs=iterable_callback_inputs,
                        iteration_result_node=iteration_result_node,
                    )
                )
            else:
                result = super().visit(node)
            if iteration_result_node is not None and isinstance(node, ast.Call):
                own_request = self._invocation_outcome_request()
                if (
                    own_request is None
                    or inherited_request is None
                    or own_request is inherited_request
                ):
                    raise LegacyGrowthAnalysisError("direct iteration lost its Call frontier")
                if result is not False and not own_request.return_scopes:
                    value = self._capture_argument_binding(node)
                    if value.deferred_calls:
                        self._replay_deferred_calls(
                            value.deferred_calls,
                            execution="iterate",
                            iteration_result_node=iteration_result_node,
                        )
                    else:
                        projected = (
                            value
                            if value.ordered_items is not None or value.iterable_element is not None
                            else self._variadic_iterable_binding(
                                [self._conservative_argument_binding()]
                            )
                        )
                        self._call_result_bindings[id(iteration_result_node)] = projected
                        self._remember_captured_binding(projected, enclosing=True)
                        own_request.return_scopes.append(self.scope.clone())
                inherited_request.return_scopes.extend(own_request.return_scopes)
                inherited_request.raise_scopes.extend(own_request.raise_scopes)
                own_request.return_scopes.clear()
                own_request.raise_scopes.clear()
            if records_exception_state:
                self._record_exception_scope()
            if framed and isinstance(node, ast.Await) and result is not False:
                frame = cast(tuple[object, ...], self._active_replay_contexts[-1])
                if frame[5] and (published := self._call_result_bindings.get(id(node))) is not None:
                    self._remember_captured_binding(published, enclosing=True)
            return result
        finally:
            if framed:
                frame = cast(tuple[object, ...], self._active_replay_contexts[-1])
                primary_error = sys.exception()
                try:
                    if frame[5]:
                        self._close_private_deferred_frame(frame, offsets)
                    if isinstance(node, ast.Module):
                        self._freeze_deferred_scope(self.scope)
                except Exception as cleanup_error:
                    if primary_error is None:
                        raise
                    primary_error.add_note(f"private consumer cleanup also failed: {cleanup_error}")
                finally:
                    self._active_replay_contexts.pop()

    def _invocation_outcome_request(self) -> _TerminalControlBindings | None:
        for context in reversed(self._active_replay_contexts):
            if isinstance(context, tuple) and len(context) in {8, 9}:
                return (
                    cast(_TerminalControlBindings | None, context[8]) if len(context) == 9 else None
                )
        return None

    @contextmanager
    def _suspend_invocation_outcomes(self) -> Iterator[None]:
        if self._invocation_outcome_request() is None:
            yield
            return
        index = next(
            i
            for i in range(len(self._active_replay_contexts) - 1, -1, -1)
            if isinstance(self._active_replay_contexts[i], tuple)
            and len(cast(tuple[object, ...], self._active_replay_contexts[i])) in {8, 9}
        )
        frame = cast(tuple[object, ...], self._active_replay_contexts[index])
        self._active_replay_contexts[index] = (*frame[:8], None)
        try:
            yield
        finally:
            updated = (
                cast(tuple[object, ...], self._active_replay_contexts[index])
                if index < len(self._active_replay_contexts)
                else None
            )
            if (
                not isinstance(updated, tuple)
                or len(updated) not in {8, 9}
                or updated[0] is not frame[0]
                or updated[1] is not frame[1]
            ):
                if sys.exception() is None:
                    raise LegacyGrowthAnalysisError("invocation preparation lost its owning frame")
            else:
                self._active_replay_contexts[index] = (*updated[:8], *frame[8:])

    @contextmanager
    def _temporary_iteration_result(
        self, node: ast.AST, *, pin_consumer: bool = False, prior_live: bool | None = None
    ) -> Iterator[None]:
        """Own one transient current-result slot, including saved outcome views."""
        key = id(node)
        existed = key in self._call_result_bindings
        old = self._call_result_bindings.get(key)
        was_live = key in self._active_deferred_result_ids() if prior_live is None else prior_live
        index = len(self._active_replay_contexts) - 1
        frame = self._active_replay_contexts[index] if index >= 0 else None
        if not isinstance(frame, tuple) or len(frame) not in {8, 9}:
            raise LegacyGrowthAnalysisError("iteration result has no owning frame")
        if pin_consumer and (
            not isinstance(node, (ast.Tuple, ast.List, ast.YieldFrom))
            or node not in self._source_nodes()
        ):
            raise LegacyGrowthAnalysisError("iteration outlet is not an actual non-Call consumer")
        offsets = [(items, len(items)) for items in self._deferred_abrupt_collectors()]
        old_root_index = len(cast(tuple[_ResolvedBinding, ...], frame[2]))
        if old is not None:
            # Default function frames intentionally reject ordinary capture
            # handoff. This lexical slot owner must still root its old full value.
            self._active_replay_contexts[index] = (
                *frame[:2],
                (*cast(tuple[_ResolvedBinding, ...], frame[2]), old),
                *frame[3:],
            )
        current = cast(tuple[object, ...], self._active_replay_contexts[index])
        if pin_consumer:
            self._active_replay_contexts[index] = (
                *current[:4],
                (*cast(tuple[ast.AST, ...], current[4]), node),
                *current[5:],
            )
        self._call_result_bindings.pop(key, None)

        def restore(state: _DeferredFlowSnapshot) -> _DeferredFlowSnapshot:
            results = dict(state[2])
            if existed:
                if old is None:
                    raise AssertionError
                results[key] = old
            else:
                results.pop(key, None)
            live = state[4] | {key} if was_live else state[4] - {key}
            return (state[0], state[1], results, state[3], live, state[5])

        try:
            yield
        finally:
            primary = sys.exception()
            try:
                current = cast(tuple[object, ...], self._active_replay_contexts[index])
                if current[0] is not frame[0] or current[1] is not frame[1]:
                    raise LegacyGrowthAnalysisError("iteration result lost its owning frame")
                self._active_replay_contexts[index] = (*current[:4], frame[4], *current[5:])
                active = restore(self._capture_deferred_flow(self.scope))
                self._call_result_bindings = active[2]
                self.scope._flow_snapshot = active
                if old is not None:
                    roots = cast(tuple[_ResolvedBinding, ...], current[2])
                    if len(roots) <= old_root_index or roots[old_root_index] is not old:
                        raise LegacyGrowthAnalysisError(
                            "iteration result lost its saved operand root"
                        )
                    latest = cast(tuple[object, ...], self._active_replay_contexts[index])
                    self._active_replay_contexts[index] = (
                        *latest[:2],
                        (*roots[:old_root_index], *roots[old_root_index + 1 :]),
                        *latest[3:],
                    )
                for items, offset in offsets:
                    for saved in items[offset:]:
                        if saved._flow_snapshot is not None:
                            saved._flow_snapshot = restore(saved._flow_snapshot)
            except Exception as error:
                if primary is None:
                    raise
                primary.add_note(f"iteration result cleanup also failed: {error}")

    def _yield_result_owner(self) -> _FunctionNode | None:
        if self._invocation_outcome_request() is None:
            return None
        for frame in reversed(self._active_replay_contexts):
            if isinstance(frame, tuple) and len(frame) in {8, 9}:
                owner = frame[1]
                if isinstance(owner, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Every actual function replay clears an older slot first.
                    # Only explicit current iteration seeds this nearest sink.
                    return (
                        owner
                        if owner in self._active_function_replays
                        and _function_is_generator(owner)
                        and id(owner) in self._call_result_bindings
                        else None
                    )
        return None

    def _append_yield_result(self, owner: _FunctionNode, emitted: _ResolvedBinding) -> None:
        previous = self._call_result_bindings[id(owner)]
        if previous.ordered_items is not None and emitted.ordered_items is not None:
            rows = (*previous.ordered_items, *emitted.ordered_items)
            aggregate = self._variadic_iterable_binding(rows, ordered_items=rows)
        else:
            elements = [
                value
                for binding in (previous, emitted)
                if (value := binding.iterable_element) is not None
            ]
            if emitted.ordered_items is None and emitted.iterable_element is None:
                elements.append(self._conservative_argument_binding())
            aggregate = self._variadic_iterable_binding(elements)
        self._call_result_bindings[id(owner)] = aggregate
        self._remember_captured_binding(aggregate)

    def _discard_invocation_temporary(
        self, name: str, offsets: Sequence[tuple[list[_LexicalBindings], int]]
    ) -> None:
        # Preserve earlier saved views: only new outputs of this exact synthetic
        # application receive a fresh snapshot without its non-source name.
        self.scope.unbind(name)
        for outcomes, offset in offsets:
            for index in range(offset, len(outcomes)):
                outcome = outcomes[index]
                cleaned = outcome.clone(capture_flow=False)
                cleaned.unbind(name)
                if outcome._flow_snapshot is not None:
                    fields = []
                    for owner, saved in outcome._flow_snapshot[0]:
                        copied = saved.clone(capture_flow=False)
                        copied.unbind(name)
                        fields.append((owner, copied))
                    cleaned._flow_snapshot = (tuple(fields), *outcome._flow_snapshot[1:])
                cleaned._flow_owner = self
                outcomes[index] = cleaned
        self._freeze_deferred_scope(self.scope)

    def _unknown_invocation_outcomes(self, request: _TerminalControlBindings) -> None:
        request.return_scopes.append(self.scope.clone())
        request.raise_scopes.append(self.scope.clone())

    def _resume_invocation_outcomes(
        self,
        request: _TerminalControlBindings,
        offsets: tuple[int, int],
        *,
        abrupt_output: list[_LexicalBindings] | None = None,
    ) -> bool:
        normal = request.return_scopes[offsets[0] :]
        abrupt = request.raise_scopes[offsets[1] :]
        del request.return_scopes[offsets[0] :]
        del request.raise_scopes[offsets[1] :]
        (self._terminal_controls.raise_scopes if abrupt_output is None else abrupt_output).extend(
            abrupt
        )
        if not normal:
            return False
        self._merge_outcomes(self.scope, normal)
        return True

    def _project_invocation_scope(
        self,
        outcome: _LexicalBindings,
        caller: _LexicalBindings,
        entry: _DeferredFlowSnapshot,
        *,
        outward_targets: Mapping[str, _LexicalBindings] | None = None,
        caller_outward_views: Sequence[
            tuple[_LexicalBindings, Mapping[str, _LexicalBindings]]
        ] = (),
    ) -> _LexicalBindings:
        state = outcome._flow_snapshot
        if state is None:
            raise LegacyGrowthAnalysisError("requested invocation outcome has no saved Flow")
        self._restore_deferred_flow(entry)
        self._restore_deferred_flow(state)
        self.scope = outcome
        if outward_targets is not None:
            self._transfer_outward_bindings(
                outcome, outward_targets, caller, resolve_declared_source=True
            )
        # The actual caller can be dynamically suspended outside the callee's
        # lexical ancestry. Its declared outward views still mirror these real
        # targets, independently for this restored normal or abrupt outcome.
        for view, targets in caller_outward_views:
            for name, target in targets.items():
                self._transfer_outward_binding_state(name, target, view)
        projected = caller.clone(capture_flow=False)
        self.scope = projected
        projected._flow_owner = self
        projected._flow_snapshot = self._capture_deferred_flow(projected)
        return projected

    def generic_visit(self, node: ast.AST) -> None | Literal[False]:
        if self._invocation_outcome_request() is None:
            super().generic_visit(node)
            return None
        for _name, value in ast.iter_fields(node):
            if isinstance(value, list):
                for child in value:
                    if isinstance(child, ast.AST) and self.visit(child) is False:
                        return False
            elif isinstance(value, ast.AST) and self.visit(value) is False:
                return False
        return None

    def _deferred_abrupt_collectors(self) -> list[list[_LexicalBindings]]:
        collectors = [
            self._terminal_controls.return_scopes,
            self._terminal_controls.raise_scopes,
            *self._exception_scope_collectors,
            *(
                items
                for controls in self._loop_controls
                for items in (controls.break_scopes, controls.continue_scopes)
            ),
        ]
        seen = {id(items) for items in collectors}
        for context in self._active_replay_contexts:
            if isinstance(context, tuple) and len(context) == 9 and context[8] is not None:
                request = cast(_TerminalControlBindings, context[8])
                for items in (request.return_scopes, request.raise_scopes):
                    if id(items) not in seen:
                        seen.add(id(items))
                        collectors.append(items)
        return collectors

    def _private_deferred_corridor(self, node: ast.AST) -> tuple[ast.AST, ...]:
        """Private views of positively recognized, non-returning-input consumers."""
        operand: ast.AST | None = None
        if isinstance(node, ast.Await):
            # Candidacy alone grants nothing. The captured producer confirms
            # the actual operation and the live direct-Call phase independently.
            return (
                (node.value,)
                if self._invocation_outcome_request() is not None
                and isinstance(node.value, ast.Call)
                and node in self._source_nodes()
                and node.value in self._source_nodes()
                else ()
            )
        if isinstance(node, ast.Return):
            for frame in reversed(self._active_replay_contexts):
                if not isinstance(frame, tuple) or len(frame) not in {8, 9}:
                    continue
                candidates = self._private_deferred_corridor_operand(
                    node.value, return_source=True, owner_frame=frame
                )
                if candidates:
                    return candidates
            return ()
        if isinstance(node, (ast.For, ast.AsyncFor)):
            operand = node.iter
        elif (
            isinstance(node, ast.Call)
            and len(node.args) == 1
            and not node.keywords
            and not isinstance(node.args[0], ast.Starred)
        ):
            if self._resolve_reference(node.func) in {
                "builtins.list",
                "builtins.tuple",
                "builtins.set",
                "builtins.frozenset",
                "builtins.sorted",
                "builtins.next",
                "builtins.all",
                "builtins.any",
                "builtins.sum",
                "builtins.min",
                "builtins.max",
            }:
                operand = node.args[0]
        return self._private_deferred_corridor_operand(operand)

    def _private_deferred_corridor_operand(
        self,
        value: ast.AST | None,
        *,
        return_source: bool = False,
        owner_frame: tuple[object, ...] | None = None,
        child: ast.AST | None = None,
        owner_kind: bool = False,
        captured_operation: Literal["to_thread"] | None = None,
    ) -> tuple[ast.AST, ...]:
        if return_source:
            if owner_frame is None or len(owner_frame) not in {8, 9}:
                return ()
            owner_index = next(
                (i for i, frame in enumerate(self._active_replay_contexts) if frame is owner_frame),
                None,
            )
            if owner_index is None:
                return ()
            owner_node = owner_frame[1]
            if isinstance(owner_node, ast.Await):
                if not (
                    isinstance(owner_node.value, ast.Call)
                    and owner_frame[6] is not None
                    and owner_node in cast(frozenset[ast.AST], owner_frame[7])
                    and owner_node.value in cast(frozenset[ast.AST], owner_frame[7])
                ):
                    return ()
                if owner_kind:
                    # Recognition remains negative after phase/source/copy
                    # revocation: it must never fall through to generic pools.
                    return (owner_node,)
                descendants = self._active_replay_contexts[owner_index + 1 :]
                if not (
                    captured_operation == "to_thread"
                    and child is None
                    and len(owner_frame) == 9
                    and owner_frame[8] is not None
                    and value is owner_node.value
                    and value in cast(tuple[ast.AST, ...], owner_frame[4])
                    and owner_node in self._source_nodes()
                    and value in self._source_nodes()
                    and len(descendants) == 1
                    and isinstance(descendants[0], tuple)
                    and len(descendants[0]) in {8, 9}
                    and descendants[0][1] is value
                    and descendants[0][0] is owner_frame[0]
                    and descendants[0][7] is owner_frame[7]
                    and self._invocation_outcome_request() is not None
                ):
                    return ()
                return (cast(ast.AST, value),)
            if owner_index == 0:
                return ()
            preceding = self._active_replay_contexts[owner_index - 1]
            if not (
                isinstance(preceding, tuple)
                and len(preceding) in {8, 9}
                and isinstance(owner_frame[1], (ast.For, ast.AsyncFor))
                and owner_frame[1] is preceding[1]
                and owner_frame[0] is preceding[0]
                and owner_frame[7] is preceding[7]
                and owner_frame[6] is not None
                and owner_frame[1] in cast(frozenset[ast.AST], owner_frame[7])
            ):
                return ()
            if owner_kind:
                # This identifies the existing nested owner even after phase
                # eligibility ended. It grants no construction or source fact.
                return (cast(ast.AST, owner_frame[1]),)
            pool = cast(tuple[ast.AST, ...], owner_frame[4])
            anchors = tuple(item for item in pool if isinstance(item, _FunctionNode))
            if (
                not anchors
                or owner_frame[1] not in self._source_nodes()
                or value not in self._source_nodes()
            ):
                return ()
            if child is not None:
                # Only the actual synthetic constructor supplies child. Its
                # separately selected consumer preserves the original child tag.
                return (
                    (value,)
                    if isinstance(value, ast.Call)
                    and value in pool
                    and child in self._source_nodes()
                    and any(self._original_callable(target) is child for target in anchors)
                    else ()
                )
            functions = [
                (index, frame[1])
                for index, frame in enumerate(self._active_replay_contexts)
                if index > owner_index
                and isinstance(frame, tuple)
                and len(frame) in {8, 9}
                and isinstance(frame[1], _FunctionNode)
            ]
            if not functions or functions[0][1] not in anchors:
                return ()
            previous_index = owner_index
            for ordinal, (index, target) in enumerate(functions):
                calls = [
                    frame[1]
                    for frame in self._active_replay_contexts[previous_index + 1 : index]
                    if isinstance(frame, tuple)
                    and len(frame) in {8, 9}
                    and isinstance(frame[1], ast.Call)
                ]
                if calls and calls[-1] not in pool:
                    return ()
                if ordinal and (
                    not calls
                    or isinstance(target, ast.AsyncFunctionDef)
                    or _function_is_generator(target)
                ):
                    return ()
                previous_index = index
            if isinstance(value, ast.Call):
                return (value, *self._private_deferred_corridor_operand(value))
            if isinstance(value, ast.IfExp):
                return tuple(
                    item
                    for branch in (value.body, value.orelse)
                    for item in self._private_deferred_corridor_operand(
                        branch, return_source=True, owner_frame=owner_frame
                    )
                )
            if isinstance(value, ast.BoolOp):
                return tuple(
                    item
                    for branch in value.values
                    for item in self._private_deferred_corridor_operand(
                        branch, return_source=True, owner_frame=owner_frame
                    )
                )
            return ()
        if (
            not isinstance(value, ast.Call)
            or value.keywords
            or any(isinstance(item, ast.Starred) for item in value.args)
        ):
            return ()
        reference = self._resolve_reference(value.func)
        if reference in {"builtins.map", "builtins.filter", "itertools.starmap"}:
            return (value,)
        if (
            reference == "builtins.iter"
            and len(value.args) == 1
            or reference == "itertools.islice"
            and 2 <= len(value.args) <= 4
        ):
            nested = self._private_deferred_corridor_operand(value.args[0])
            return (value, *nested) if nested else ()
        if reference in _ITERABLE_CONCATENATING_REFERENCES | _ZIPPING_ITERABLE_BUILTIN_REFERENCES:
            nested = tuple(
                q
                for argument in value.args
                for q in self._private_deferred_corridor_operand(argument)
            )
            return (value, *nested) if nested else ()
        if (
            reference in _ITERABLE_FLATTENING_REFERENCES
            and len(value.args) == 1
            and isinstance(value.args[0], (ast.List, ast.Tuple))
            and not any(isinstance(item, ast.Starred) for item in value.args[0].elts)
        ):
            nested = tuple(
                q
                for argument in value.args[0].elts
                for q in self._private_deferred_corridor_operand(argument)
            )
            return (value, value.args[0], *nested) if nested else ()
        return ()

    def _deferred_key_reachable(
        self, value: object, keys: AbstractSet[_DeferredValueKey | None]
    ) -> bool:
        if isinstance(value, _DeferredFunctionCall):
            return value.value_key in keys or any(
                self._deferred_key_reachable(item, keys)
                for item in (
                    value.arguments,
                    value.callee,
                    value.operands,
                    value.keywords,
                    value.unresolved_keywords,
                    value.partial_positional,
                )
            )
        if isinstance(value, _ResolvedBinding):
            return any(
                self._deferred_key_reachable(getattr(value, name), keys)
                for name in value.__dataclass_fields__
            )
        if isinstance(value, _StaticMapping):
            return any(self._deferred_key_reachable(item.binding, keys) for item in value.entries)
        if isinstance(value, dict):
            return any(self._deferred_key_reachable(item, keys) for item in value.values())
        if isinstance(value, (tuple, list, set, frozenset)):
            return any(self._deferred_key_reachable(item, keys) for item in value)
        return False

    def _close_private_deferred_frame(
        self, frame: tuple[object, ...], offsets: Sequence[tuple[list[_LexicalBindings], int]]
    ) -> None:
        private = {
            id(node) for node in cast(tuple[ast.AST, ...], frame[4]) if isinstance(node, ast.expr)
        }
        calls = cast(tuple[_DeferredFunctionCall, ...], frame[5])
        keys = {call.value_key for call in calls}
        entry = cast(_DeferredFlowSnapshot, frame[6])

        def contains(value: object) -> bool:
            return self._deferred_key_reachable(value, keys)

        # Discard only this frame's private operand/owned views before the
        # post-GC reachability projection. Other frames and return collectors
        # remain strict escaping roots.
        current = cast(tuple[object, ...], self._active_replay_contexts[-1])
        self._active_replay_contexts[-1] = (
            *current[:2],
            (),
            current[3],
            (),
            (),
            *current[6:],
        )
        if any(
            contains(context[2])
            for context in self._active_replay_contexts[:-1]
            if isinstance(context, tuple) and len(context) in {8, 9}
        ) or any(contains(values) for values in self._return_binding_collectors):
            raise LegacyGrowthAnalysisError(
                "private deferred parent escaped in an active operand/return"
            )

        def clean(state: _DeferredFlowSnapshot) -> _DeferredFlowSnapshot:
            for _owner, fields in state[0]:
                if any(
                    contains(getattr(fields, name))
                    for name in (
                        "deferred_calls",
                        "iterable_elements",
                        "ordered_items",
                        "call_receivers",
                        "mappings",
                    )
                ):
                    raise LegacyGrowthAnalysisError("private deferred parent escaped its consumer")
            if any(
                contains(value)
                for key, value in state[2].items()
                if key in state[4] and key not in private
            ):
                raise LegacyGrowthAnalysisError("private deferred parent escaped in a result")
            current, deferred = dict(state[2]), dict(state[3])
            for key in private:
                if key in entry[2]:
                    current[key] = entry[2][key]
                else:
                    current.pop(key, None)
                if key in entry[3]:
                    deferred[key] = entry[3][key]
                else:
                    deferred.pop(key, None)
            progress = frozenset(
                record
                for record in state[1]
                if not isinstance(record, tuple) or record[0] not in keys
            )
            cleaned = (state[0], progress, current, deferred, state[4] - private, state[5])
            graph, _root = self._deferred_comparison_graph(cleaned)
            owners = tuple(
                (owner, fields) for owner, fields in state[0] if ("scope", owner) in graph
            )
            return (owners, progress, current, deferred, state[4] - private, state[5])

        active = clean(self._capture_deferred_flow(self.scope))
        self._consumed_deferred_calls = set(active[1])
        self._call_result_bindings, self._deferred_call_bindings = active[2], active[3]
        for items, offset in offsets:
            for saved in items[offset:]:
                if saved._flow_snapshot is not None:
                    saved._flow_snapshot = clean(saved._flow_snapshot)
        self.scope._flow_snapshot = active

    def _source_nodes(self) -> frozenset[ast.AST]:
        for context in reversed(self._active_replay_contexts):
            if isinstance(context, tuple) and len(context) in {8, 9}:
                return cast(frozenset[ast.AST], context[7])
        snapshot = self.scope._flow_snapshot
        if snapshot is not None and snapshot[5] is not None:
            return frozenset(ast.walk(snapshot[5]))
        return frozenset()

    def _current_replay_context(self) -> object | None:
        for context in reversed(self._active_replay_contexts):
            if isinstance(context, tuple) and len(context) in {8, 9}:
                opaque_context: object | None = context[0]
                return opaque_context
            return context
        return None

    def _remember_captured_binding(
        self, binding: _ResolvedBinding, *, enclosing: bool = False
    ) -> None:
        indices = (
            range(len(self._active_replay_contexts) - 2, -1, -1)
            if enclosing
            else range(
                len(self._active_replay_contexts) - 1, len(self._active_replay_contexts) - 2, -1
            )
        )
        for index in indices:
            if index < 0:
                continue
            context = self._active_replay_contexts[index]
            if (
                isinstance(context, tuple)
                and len(context) in {8, 9}
                and (
                    isinstance(context[1], (ast.Call, ast.List, ast.Tuple, ast.Dict))
                    or len(context) == 9
                    and context[8] is not None
                )
            ):
                self._active_replay_contexts[index] = (
                    *context[:2],
                    (*cast(tuple[_ResolvedBinding, ...], context[2]), binding),
                    *context[3:],
                )
                break

    def _live_deferred_scopes(
        self,
        root: _LexicalBindings,
        *,
        reject_keys: AbstractSet[_DeferredValueKey] | None = None,
        extra_flows: Sequence[_DeferredFlowSnapshot] = (),
    ) -> list[_LexicalBindings]:
        scopes: list[_LexicalBindings] = []
        seen_scopes: set[_LexicalBindings] = set()
        # Keep actual bindings and temporary deferred views alive for this
        # walk so an integer ID cannot be reused for another owner's facts.
        # This local memo is not value/progress identity.
        seen_bindings: dict[int, _ResolvedBinding] = {}
        seen_functions: set[_FunctionNode] = set()

        def facts(
            reference: str | None,
            callables: frozenset[_FunctionNode],
            deferred_calls: frozenset[_DeferredFunctionCall],
            mapping: _StaticMapping | None,
            class_references: frozenset[str],
            descriptors: frozenset[_DescriptorBinding],
            iterable_element: _ResolvedBinding | None,
            ordered_items: tuple[_ResolvedBinding, ...] | None,
            call_receivers: frozenset[tuple[_FunctionNode, str, _ResolvedBinding]],
        ) -> None:
            for reference in {*class_references, reference or ""}:
                if reference.startswith((_CLASS_REFERENCE_PREFIX, _INSTANCE_REFERENCE_PREFIX)):
                    for (owner, _member), functions in self._class_member_callables.items():
                        if owner == reference:
                            for target in functions:
                                function(target)
            for target in callables:
                function(target)
            for target, _kind in descriptors:
                function(target)
            for target, _kind, receiver in call_receivers:
                function(target)
                binding(receiver)
            if mapping is not None:
                for entry in mapping.entries:
                    binding(entry.binding)
            if iterable_element is not None:
                binding(iterable_element)
            for item in ordered_items or ():
                binding(item)
            for call in deferred_calls:
                if reject_keys is not None and call.value_key in reject_keys:
                    raise LegacyGrowthAnalysisError("transient identity collides with a live value")
                if call.function is not None:
                    function(call.function)
                for _name, item in (*call.arguments, *call.keywords):
                    binding(item)
                for item in (*call.operands, *call.partial_positional, *call.unresolved_keywords):
                    binding(item)
                if call.callee is not None:
                    binding(call.callee)

        def binding(value: _ResolvedBinding) -> None:
            if id(value) in seen_bindings:
                return
            seen_bindings[id(value)] = value
            facts(
                value.reference,
                value.callables,
                value.deferred_calls,
                value.mapping,
                value.class_references,
                value.descriptors,
                value.iterable_element,
                value.ordered_items,
                value.call_receivers,
            )

        def function(target: _FunctionNode) -> None:
            if target in seen_functions:
                return
            seen_functions.add(target)
            owner = self._function_definition_scopes.get(target)
            if owner is not None:
                effective = owner
                while (
                    effective.scope_kind in {"class", "type_parameters"}
                    and effective.parent is not None
                ):
                    effective = effective.parent
                if effective.scope_kind == "module":
                    scope(self._module_scope())
                    if owner.scope_kind == "type_parameters":
                        scope(owner)
                else:
                    scope(owner)
            for item in self._function_default_bindings.get(target, {}).values():
                binding(item)
            for targets in self._function_decorator_bindings.get(target, ()):
                for decorator in targets:
                    function(decorator)
            expression = self._deferred_generator_expression_for(target)
            if expression is not None:
                _expression, owner, outer = expression
                scope(owner)
                binding(outer)

        def scope(owner: _LexicalBindings) -> None:
            if owner in seen_scopes:
                return
            seen_scopes.add(owner)
            scopes.append(owner)
            scope_fields(owner)

        def scope_fields(data: _LexicalBindings) -> None:
            if data.parent is not None:
                scope(data.parent)
            names = set().union(
                data.references,
                data.strings,
                data.callables,
                data.deferred_calls,
                data.mappings,
                data.class_references,
                data.descriptors,
                data.iterable_elements,
                data.ordered_items,
                data.call_receivers,
            )
            edge_names = set().union(
                data.callables,
                data.deferred_calls,
                data.mappings,
                data.class_references,
                data.descriptors,
                data.iterable_elements,
                data.ordered_items,
                data.call_receivers,
            )
            edge_names.update(
                name
                for name, reference in data.references.items()
                if reference.startswith((_CLASS_REFERENCE_PREFIX, _INSTANCE_REFERENCE_PREFIX))
            )
            for name in names:
                # Other names have no outgoing owner edge in facts(). Keep
                # their scalar fields in the unchanged full lexical snapshot.
                if name not in edge_names:
                    continue
                # Walk the stored edges directly; the temporary RB added no
                # identity or string edge. Scalar facts remain in scope.clone.
                facts(
                    data.references.get(name),
                    data.callables.get(name, frozenset()),
                    data.deferred_calls.get(name, frozenset()),
                    data.mappings.get(name),
                    data.class_references.get(name, frozenset()),
                    data.descriptors.get(name, frozenset()),
                    data.iterable_elements.get(name),
                    data.ordered_items.get(name),
                    data.call_receivers.get(name, frozenset()),
                )

        def saved_flow(state: _DeferredFlowSnapshot) -> None:
            for owner, data in state[0]:
                scope(owner)
                scope_fields(data)
            for record in state[1]:
                if isinstance(record, tuple):
                    if reject_keys is not None and record[0] in reject_keys:
                        raise LegacyGrowthAnalysisError(
                            "transient identity collides with saved progress"
                        )
                    if record[2] is not None:
                        binding(record[2])
                else:
                    binding(_ResolvedBinding(None, None, deferred_calls=frozenset({record})))
            for key, result in state[2].items():
                if key in state[4]:
                    binding(result)
            for key, deferred in state[3].items():
                if key in state[4]:
                    for call in deferred:
                        binding(_ResolvedBinding(None, None, deferred_calls=frozenset({call})))

        # Snapshot comparison and JOIN use this designated root, so visit it
        # before result/default/return/callee reachability can discover a module
        # or captured owner. The same seen set retains every other owner once.
        scope(root)
        for node_id in self._active_deferred_result_ids():
            if node_id in self._call_result_bindings:
                binding(self._call_result_bindings[node_id])
            for call in self._deferred_call_bindings.get(node_id, ()):
                binding(_ResolvedBinding(None, None, deferred_calls=frozenset({call})))
        for record in self._consumed_deferred_calls:
            if isinstance(record, tuple):
                if reject_keys is not None and record[0] in reject_keys:
                    raise LegacyGrowthAnalysisError(
                        "transient identity collides with current progress"
                    )
                if record[2] is not None:
                    binding(record[2])
            else:
                binding(_ResolvedBinding(None, None, deferred_calls=frozenset({record})))
        for returns in self._return_binding_collectors:
            for value in returns:
                binding(value)
        for targets in self._outward_binding_targets:
            for owner in targets.values():
                scope(owner)
        for target in self._active_function_replays | self._definition_time_function_scans:
            function(target)
        for _references, _strings, functions in self._function_late_bindings:
            for late_targets in functions.values():
                for late_target in late_targets:
                    function(late_target)
        for context in self._active_replay_contexts:
            if isinstance(context, tuple) and len(context) in {8, 9}:
                for item in cast(tuple[_ResolvedBinding, ...], context[2]):
                    binding(item)
                for call in cast(tuple[_DeferredFunctionCall, ...], context[5]):
                    binding(_ResolvedBinding(None, None, deferred_calls=frozenset({call})))
                if len(context) == 9 and context[8] is not None:
                    request = cast(_TerminalControlBindings, context[8])
                    for saved in (*request.return_scopes, *request.raise_scopes):
                        scope(saved)
                        state = saved._flow_snapshot
                        if state is None:
                            continue
                        saved_flow(state)
        if reject_keys is not None:
            for state in extra_flows:
                saved_flow(state)
            for items in self._deferred_abrupt_collectors():
                for saved in items:
                    scope(saved)
                    if saved._flow_snapshot is not None:
                        saved_flow(saved._flow_snapshot)
        return scopes

    def _active_deferred_result_ids(self) -> frozenset[int]:
        live_ids: set[int] = set()
        for context in self._active_replay_contexts:
            if isinstance(context, tuple) and len(context) in {8, 9}:
                node = cast(ast.AST, context[1])
                live_ids.add(id(node))
                live_ids.update(
                    id(item)
                    for item in cast(tuple[ast.AST, ...], context[4])
                    if isinstance(item, ast.expr)
                )
                if isinstance(node, (ast.For, ast.AsyncFor)):
                    live_ids.update(id(item) for item in ast.walk(node.iter))
        return frozenset(live_ids)

    def _deferred_source_module(self) -> ast.Module | None:
        source_nodes = self._source_nodes()
        # A parsed source has one Module, retained by the existing source frame.
        # Membership rejects an outer frame while an independent Module is active.
        for context in reversed(self._active_replay_contexts):
            if isinstance(context, tuple) and len(context) in {8, 9}:
                node = context[1]
                if isinstance(node, ast.Module) and node in source_nodes:
                    return node
        # Standalone fragments and snapshots can have no active Module frame.
        return next((node for node in source_nodes if isinstance(node, ast.Module)), None)

    def _capture_deferred_flow(self, root: _LexicalBindings) -> _DeferredFlowSnapshot:
        live_ids = self._active_deferred_result_ids()
        original = self._deferred_source_module()
        return (
            tuple(
                (owner, owner.clone(capture_flow=False))
                for owner in self._live_deferred_scopes(root)
            ),
            frozenset(self._consumed_deferred_calls),
            dict(self._call_result_bindings),
            dict(self._deferred_call_bindings),
            frozenset(live_ids),
            original,
        )

    def _freeze_deferred_scope(self, scope: _LexicalBindings) -> None:
        if scope._flow_owner is self and self.scope is scope:
            scope._flow_snapshot = self._capture_deferred_flow(scope)

    def _restore_deferred_flow(self, state: _DeferredFlowSnapshot) -> None:
        for owner, snapshot in state[0]:
            self._restore_scope_state(owner, snapshot)
        self._consumed_deferred_calls = set(state[1])
        self._call_result_bindings = dict(state[2])
        self._deferred_call_bindings = dict(state[3])

    def _switch_deferred_scope(self, scope: _LexicalBindings, *, restore_flow: bool) -> None:
        self._freeze_deferred_scope(self.scope)
        if restore_flow and scope._flow_snapshot is not None:
            self._restore_deferred_flow(scope._flow_snapshot)
        self.scope = scope
        scope._flow_owner = self

    def _join_deferred_progress(
        self, outcomes: Sequence[_DeferredFlowSnapshot], incoming: _LexicalBindings
    ) -> None:
        keys = {record[0] for state in outcomes for record in state[1] if isinstance(record, tuple)}
        merged: set[_DeferredFunctionCall | _DeferredProgress] = set(outcomes[0][1])
        for state in outcomes[1:]:
            merged.intersection_update(state[1])
        for key in keys:
            values = [
                next(
                    (
                        record
                        for record in state[1]
                        if isinstance(record, tuple) and record[0] == key
                    ),
                    None,
                )
                for state in outcomes
            ]
            initial: _DeferredProgress = (key, "available", None)
            if all(value is None or value == initial for value in values):
                merged.add(initial)
                continue
            if any(value != values[0] for value in values[1:]) or values[0] is None:
                merged = {
                    record for record in merged if not isinstance(record, tuple) or record[0] != key
                }
                merged.add((key, "unknown", None))
        self._consumed_deferred_calls = merged
        for attribute, index in (("_call_result_bindings", 2), ("_deferred_call_bindings", 3)):
            maps = [cast(dict[int, object], state[index]) for state in outcomes]
            joined: dict[int, object] = {}
            for node_id in set().union(*(mapping.keys() for mapping in maps)):
                slot_values = [mapping.get(node_id) for mapping in maps]
                if all(value == slot_values[0] for value in slot_values):
                    if slot_values[0] is not None:
                        joined[node_id] = slot_values[0]
                elif attribute == "_call_result_bindings":
                    joined[node_id] = self._join_resolved_bindings(
                        [
                            (
                                cast(_ResolvedBinding, value)
                                if value is not None
                                else self._conservative_argument_binding()
                            )
                            for value in slot_values
                        ]
                    )
                else:
                    joined[node_id] = frozenset().union(
                        *(
                            cast(frozenset[_DeferredFunctionCall], value)
                            for value in slot_values
                            if value is not None
                        )
                    )
            setattr(self, attribute, joined)
        roots = {state[0][0][0] for state in outcomes if state[0]}
        owners = {owner for state in outcomes for owner, _snapshot in state[0]}
        for owner in owners - roots - {incoming}:
            snapshots = [
                next(
                    (snapshot for target, snapshot in state[0] if target is owner),
                    owner.clone(capture_flow=False),
                )
                for state in outcomes
            ]
            # Transfer physical fields without recapturing a finalized outcome
            # from another alternative's partially joined ambient owner graph.
            self._merge_binding_facts(owner, snapshots)
            owner._flow_owner = self
        self.scope = incoming

    def _deferred_flow_equal(
        self, left: _DeferredFlowSnapshot | None, right: _DeferredFlowSnapshot | None
    ) -> bool:
        if left is None or right is None:
            return left is right
        if left[5] is not right[5]:
            return False
        left_graph, left_root = self._deferred_comparison_graph(left)
        right_graph, right_root = self._deferred_comparison_graph(right)

        def compatible(a: object, b: object) -> bool:
            # Necessary labelled-leaf tests prune impossible permutations. Only
            # the complete verified traversal below establishes equivalence.
            if not isinstance(a, tuple) or not isinstance(b, tuple) or a[0] != b[0]:
                return False
            if a[0] == "source":
                return a[1] is b[1]
            if a[0] == "leaf":
                return a[1:] == b[1:]
            if a[0] == "node":
                kind_a = cast(tuple[str, object], a[1])[0]
                kind_b = cast(tuple[str, object], b[1])[0]
                return kind_a == kind_b
            if len(a[1]) != len(b[1]):
                return False
            if a[0] == "set":
                return True
            return all(compatible(x, y) for x, y in zip(a[1], b[1], strict=True))

        tasks: list[tuple[str, object, object]] = [("match", left_root, right_root)]
        alternatives: list[
            tuple[list[tuple[str, object, object]], dict[object, object], dict[object, object]]
        ] = [(tasks, {}, {})]
        while alternatives:
            pending, forward, reverse = alternatives.pop()
            while pending:
                operation, a, b = pending.pop()
                if operation == "unordered":
                    xs, ys = cast(tuple[object, ...], a), cast(tuple[object, ...], b)
                    if not xs:
                        continue
                    for index, item in enumerate(ys):
                        if compatible(xs[0], item):
                            alternatives.append(
                                (
                                    [
                                        *pending,
                                        ("unordered", xs[1:], ys[:index] + ys[index + 1 :]),
                                        ("match", xs[0], item),
                                    ],
                                    dict(forward),
                                    dict(reverse),
                                )
                            )
                    break
                if not compatible(a, b):
                    break
                a, b = cast(tuple[object, ...], a), cast(tuple[object, ...], b)
                if a[0] == "node":
                    key_a, key_b = a[1], b[1]
                    if key_a in forward:
                        if forward[key_a] != key_b or reverse.get(key_b) != key_a:
                            break
                    elif key_b in reverse:
                        break
                    else:
                        forward[key_a], reverse[key_b] = key_b, key_a
                        pending.append(("match", left_graph[key_a], right_graph[key_b]))
                elif a[0] not in {"source", "leaf"}:
                    xs, ys = cast(tuple[object, ...], a[1]), cast(tuple[object, ...], b[1])
                    if a[0] == "set":
                        pending.append(("unordered", xs, ys))
                    else:
                        pending.extend(
                            ("match", x, y) for x, y in reversed(list(zip(xs, ys, strict=True)))
                        )
            else:
                if len(forward) == len(left_graph) and len(reverse) == len(right_graph):
                    # This pairing is boolean proof only. It is never returned,
                    # cached or used to select RESTORE/JOIN physical owners.
                    return True
        return False

    def _deferred_comparison_graph(
        self, state: _DeferredFlowSnapshot
    ) -> tuple[dict[object, object], object]:
        overlay = dict(state[0])
        root_scope = state[0][0][0]
        source_nodes = self._source_nodes()
        graph: dict[object, object] = {}

        def source(node: ast.AST) -> object:
            return ("source", node)

        def fields(owner: _LexicalBindings) -> _LexicalBindings:
            return overlay.get(owner, owner)

        def module(owner: _LexicalBindings) -> _LexicalBindings:
            visited: set[_LexicalBindings] = set()
            while fields(owner).parent is not None:
                if owner in visited:
                    raise LegacyGrowthAnalysisError("cyclic active lexical parent")
                visited.add(owner)
                owner = cast(_LexicalBindings, fields(owner).parent)
            return owner

        def function_parent(owner: _LexicalBindings) -> object:
            data = fields(owner)
            if data.scope_kind == "class" and data.parent is not None:
                return function_parent(data.parent)
            if data.scope_kind == "module":
                return node("scope", module(root_scope))
            if data.scope_kind == "type_parameters" and data.parent is not None:
                return (
                    "sequence",
                    (
                        encode("type_parameters"),
                        encode(owner),
                        function_parent(data.parent),
                    ),
                )
            return node("scope", owner)

        def node(kind: str, owner: object) -> object:
            key = (kind, owner)
            if key in graph:
                return ("node", key)
            graph[key] = ("leaf", "pending", None)
            if kind == "scope":
                data = fields(cast(_LexicalBindings, owner))
                value: object = (
                    kind,
                    data.scope_kind,
                    data.local_names,
                    data.parent,
                    data.references,
                    data.strings,
                    data.callables,
                    data.deferred_calls,
                    data.mappings,
                    data.class_references,
                    data.descriptors,
                    data.iterable_elements,
                    data.ordered_items,
                    data.call_receivers,
                    data.bound_names,
                    data.possibly_bound_names,
                    tuple(
                        (
                            name,
                            _ResolvedBinding(
                                data.references.get(name),
                                data.strings.get(name),
                                data.callables.get(name, frozenset()),
                                data.deferred_calls.get(name, frozenset()),
                                data.mappings.get(name),
                                data.class_references.get(name, frozenset()),
                                data.descriptors.get(name, frozenset()),
                                data.iterable_elements.get(name),
                                data.ordered_items.get(name),
                                data.call_receivers.get(name, frozenset()),
                            ),
                        )
                        for name in sorted(
                            set().union(
                                data.references,
                                data.strings,
                                data.callables,
                                data.deferred_calls,
                                data.mappings,
                                data.class_references,
                                data.descriptors,
                                data.iterable_elements,
                                data.ordered_items,
                                data.call_receivers,
                            )
                        )
                    ),
                )
            elif kind == "function":
                target = cast(_FunctionNode, owner)
                origins: list[object] = []
                if target in source_nodes:
                    origins.append(("sequence", (encode("prototype"), source(target))))
                for (prototype, context), bound in self._function_binding_nodes.items():
                    if bound is not target:
                        continue
                    origins.append(
                        ("sequence", (encode("prototype"), source(prototype)))
                        if prototype is target
                        else ("sequence", (encode("binding"), encode(prototype), encode(context)))
                    )
                origins.extend(
                    ("sequence", (encode("lambda"), encode(original_id)))
                    for original_id, bound in self._lambda_function_bindings.items()
                    if bound is target
                )
                expression = self._deferred_generator_expression_for(target)
                if expression is not None:
                    origins.append(("sequence", (encode("generator"), source(expression[0]))))
                if not origins:
                    # Unknown origin cannot be alpha-renamed by similar text.
                    origins.append(("sequence", (encode("fixed"), source(target))))
                parent = self._function_definition_scopes.get(target, root_scope)
                graph[key] = (
                    "sequence",
                    (
                        encode(kind),
                        ("sequence", tuple(origins)),
                        encode(
                            tuple(
                                (name, getattr(target, name, None))
                                for name in (*target._fields, *target._attributes)
                            )
                        ),
                        function_parent(parent),
                        encode(self._function_default_bindings.get(target, {})),
                        encode(self._function_decorator_bindings.get(target, ())),
                        encode(expression),
                        encode(target in self._active_function_replays),
                        encode(target in self._definition_time_function_scans),
                    ),
                )
                return ("node", key)
            elif kind == "syntax":
                syntax = cast(ast.AST, owner)
                value = (
                    kind,
                    type(syntax).__name__,
                    tuple(
                        (name, getattr(syntax, name, None))
                        for name in (*syntax._fields, *syntax._attributes)
                    ),
                )
            elif kind == "mapping":
                mapping = cast(_StaticMapping, owner)
                value = (
                    kind,
                    mapping.site,
                    mapping.entries,
                    self._mapping_invalidation_counts.get(mapping, 0),
                    self._mapping_last_clear_counts.get(mapping, 0),
                )
            else:
                value = ("opaque_context",)
            graph[key] = encode(value)
            return ("node", key)

        def encode(value: object) -> object:
            if isinstance(value, _LexicalBindings):
                return node("scope", value)
            if isinstance(value, (ast.FunctionDef, ast.AsyncFunctionDef)):
                return node("function", value)
            if isinstance(value, ast.AST):
                return source(value) if value in source_nodes else node("syntax", value)
            if isinstance(value, _StaticMapping):
                return node("mapping", value)
            if isinstance(value, _ResolvedBinding):
                classes = {
                    reference
                    for reference in {*value.class_references, value.reference or ""}
                    if reference.startswith((_CLASS_REFERENCE_PREFIX, _INSTANCE_REFERENCE_PREFIX))
                }
                class_facts = tuple(
                    (
                        reference,
                        self._class_mros.get(reference),
                        self._class_mro_complete.get(reference),
                        tuple(
                            (
                                name,
                                {key: item for key, item in table.items() if key[0] == reference},
                            )
                            for name, table in (
                                ("members", self._class_member_callables),
                                ("descriptors", self._class_member_descriptors),
                                ("presence", self._class_member_presence),
                                ("direct", self._class_direct_member_callables),
                                ("direct_descriptors", self._class_direct_member_descriptors),
                                ("direct_presence", self._class_direct_member_presence),
                                ("direct_noncallable", self._class_direct_member_noncallable),
                            )
                        ),
                    )
                    for reference in sorted(classes)
                )
                return encode(
                    (
                        type(value).__name__,
                        tuple((name, getattr(value, name)) for name in value.__dataclass_fields__),
                        class_facts,
                    )
                )
            if isinstance(value, (_DeferredFunctionCall, _StaticMappingEntry)):
                return encode(
                    (
                        type(value).__name__,
                        tuple((name, getattr(value, name)) for name in value.__dataclass_fields__),
                    )
                )
            if isinstance(value, dict):
                return ("set", tuple(encode((key, item)) for key, item in value.items()))
            if isinstance(value, (set, frozenset)):
                return ("set", tuple(encode(item) for item in value))
            if isinstance(value, (list, tuple)):
                return ("sequence", tuple(encode(item) for item in value))
            if type(value) is object:
                return node("context", value)
            return ("leaf", type(value).__name__, value)

        contexts = tuple(self._current_replay_contexts_for_comparison())
        cache = tuple(
            (prototype, context, target)
            for (prototype, context), target in self._function_binding_nodes.items()
            if context is None or any(context is current for current in contexts)
        )
        roots: tuple[object, ...] = (
            root_scope,
            module(root_scope),
            self._active_function_replays,
            self._definition_time_function_scans,
            self._function_late_bindings,
            contexts,
            self._outward_binding_targets,
            tuple(frozenset(values) for values in self._return_binding_collectors),
            tuple(
                context[2]
                for context in self._active_replay_contexts
                if isinstance(context, tuple) and len(context) in {8, 9}
            ),
            state[1],
            {key: value for key, value in state[2].items() if key in state[4]},
            {key: value for key, value in state[3].items() if key in state[4]},
            cache,
            self.ownership_family,
            self._analysis_purpose,
            self._replay_calls_enabled,
            self._sync_only_body_analysis,
            self._active_async_replay_depth,
            self._active_task_group_depth,
        )
        pending = tuple(
            (
                label,
                tuple(
                    (
                        saved,
                        (
                            (
                                saved._flow_snapshot[0],
                                saved._flow_snapshot[1],
                                {
                                    key: value
                                    for key, value in saved._flow_snapshot[2].items()
                                    if key in saved._flow_snapshot[4]
                                },
                                {
                                    key: value
                                    for key, value in saved._flow_snapshot[3].items()
                                    if key in saved._flow_snapshot[4]
                                },
                                saved._flow_snapshot[4],
                                saved._flow_snapshot[5],
                            )
                            if saved._flow_snapshot is not None
                            else None
                        ),
                    )
                    for saved in items
                ),
            )
            for context in self._active_replay_contexts
            if isinstance(context, tuple) and len(context) == 9 and context[8] is not None
            for request in (cast(_TerminalControlBindings, context[8]),)
            for label, items in (
                ("invocation-normal", request.return_scopes),
                ("invocation-raise", request.raise_scopes),
            )
            if items
        )
        if pending:
            roots = (*roots, pending)
        root = encode(roots)
        return graph, root

    def _current_replay_contexts_for_comparison(self) -> Iterator[object]:
        for context in self._active_replay_contexts:
            opaque = (
                context[0] if isinstance(context, tuple) and len(context) in {8, 9} else context
            )
            if opaque is not None:
                yield opaque

    @staticmethod
    def _may_reference_legacy(reference: str | None) -> bool:
        return reference == _POSSIBLE_LEGACY_REFERENCE or (
            reference is not None
            and (
                reference == "legacy_app"
                or reference.startswith("legacy_app.")
                or reference.startswith(f"{_POSSIBLE_LEGACY_REFERENCE}.__dict__.")
                or (
                    _POSSIBLE_LEGACY_REFERENCE in reference
                    and _namespace_mutator_method(reference, legacy_only=True) is not None
                )
            )
        )

    @staticmethod
    def _is_legacy_module_reference(reference: str | None) -> bool:
        return reference in {"legacy_app", _POSSIBLE_LEGACY_REFERENCE}

    @staticmethod
    def _is_legacy_namespace_reference(reference: str | None) -> bool:
        return reference in {"legacy_app.__dict__", _POSSIBLE_LEGACY_REFERENCE}

    def _is_protected_ownership_symbol(self, name: str | None) -> bool:
        if self.ownership_family == "api_key":
            return name in CANONICAL_API_KEY_SYMBOLS or name in {
                _POSSIBLE_API_KEY_SYMBOL,
                _DYNAMIC_STRING_BINDING,
            }
        return name is not None and (
            name in CANONICAL_OPENAPI_SYMBOLS
            or name == _POSSIBLE_OPENAPI_SYMBOL
            or "openapi" in name.casefold()
        )

    def _record_snapshot(self, node: ast.AST) -> None:
        # The API ownership consumer reads only expression-owned environments.
        # Other collectors retain their full statement/import snapshot contract.
        if self._expression_snapshots_only and not isinstance(node, ast.expr):
            return
        node_id = id(node)
        current_references = self.scope.visible_references()
        current_strings = self.scope.visible_strings()
        existing_references = (
            self.reference_snapshots.get(node_id) if self.reference_snapshots is not None else None
        )
        existing_strings = (
            self.string_snapshots.get(node_id) if self.string_snapshots is not None else None
        )
        tracks_collection = all(
            current is owner
            for current, owner in zip(
                (self.reference_snapshots, self.string_snapshots, self.call_result_snapshots),
                self._snapshot_collection,
                strict=True,
            )
        ) and any(owner is not None for owner in self._snapshot_collection)
        prior_replaying = (
            self._snapshot_analysis_replaying.get(node_id) if tracks_collection else None
        )
        ordinary = self._analysis_purpose == "ordinary"
        # This annotation describes analysis, not runtime execution or callable effects.
        # Refine only a dormant possibility opposed by replay-enabled non-app identity;
        # competing replay-enabled observations and other reference classes still join.
        refined_references: dict[str, str] = {}
        if (
            ordinary
            and existing_references is not None
            and prior_replaying is not None
            and prior_replaying != self._replay_calls_enabled
        ):
            possibilities = {
                _POSSIBLE_APP_REFERENCE,
                _POSSIBLE_ROUTER_REFERENCE,
                _POSSIBLE_APP_CALL_REFERENCE,
                _POSSIBLE_MIDDLEWARE_DECORATOR_REFERENCE,
            }
            if prior_replaying is False and self._replay_calls_enabled:
                refined_references = {
                    name: reference
                    for name, reference in current_references.items()
                    if reference == _KNOWN_NON_APP_REFERENCE
                    and existing_references.get(name) in possibilities
                }
            elif prior_replaying is True and not self._replay_calls_enabled:
                refined_references = {
                    name: reference
                    for name, reference in existing_references.items()
                    if reference == _KNOWN_NON_APP_REFERENCE
                    and current_references.get(name) in possibilities
                }
        if (existing_references is not None or existing_strings is not None) and (
            existing_references != current_references or existing_strings != current_strings
        ):
            existing = _LexicalBindings(parent=None)
            existing.references = existing_references if existing_references is not None else {}
            existing.strings = existing_strings if existing_strings is not None else {}
            current = _LexicalBindings(parent=None)
            current.references = current_references
            current.strings = current_strings
            merged = _LexicalBindings(parent=None)
            self._merge_binding_facts(merged, [existing, current], snapshot_projection=True)
            self.scope._flow_owner = self
            current_references = merged.references
            current_strings = merged.strings
        current_references.update(refined_references)
        if self.reference_snapshots is not None:
            self.reference_snapshots[node_id] = current_references
        if self.string_snapshots is not None:
            self.string_snapshots[node_id] = current_strings
        if tracks_collection:
            if self._replay_calls_enabled:
                self._snapshot_analysis_replaying[node_id] = True
            elif ordinary and existing_references is None and existing_strings is None:
                self._snapshot_analysis_replaying[node_id] = False

    def _record_outward_api_key_rebinding(
        self, name: str, *, proven_module_namespace: bool = False
    ) -> None:
        if self.filename != LEGACY_APP or name not in CANONICAL_API_KEY_SYMBOLS:
            return
        execution_scope = self.scope
        while (
            execution_scope.scope_kind in {"class", "type_parameters", "comprehension"}
            and execution_scope.parent is not None
        ):
            execution_scope = execution_scope.parent
        if not self._active_function_replays and execution_scope.scope_kind != "module":
            return
        target = self._active_outward_targets_for_scope(self.scope).get(name)
        if not proven_module_namespace and (target is None or target.scope_kind != "module"):
            return
        description = (
            "canonical API-key compatibility re-export"
            if name in LEGACY_API_KEY_REEXPORTS
            else "canonical API-key dependency"
        )
        self.errors.append(f"{LEGACY_APP}: {description} must not be rebound: {name}")

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
        ordered_items: tuple[_ResolvedBinding, ...] | None = None,
        call_receivers: frozenset[tuple[_FunctionNode, str, _ResolvedBinding]] = frozenset(),
        runtime_binding: bool = True,
    ) -> None:
        if runtime_binding:
            self._record_outward_api_key_rebinding(name)
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
            ordered_items=ordered_items,
            call_receivers=call_receivers,
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
            ordered_items=binding.ordered_items,
            call_receivers=binding.call_receivers,
            runtime_binding=runtime_binding,
        )

    def _resolve_callables(self, node: ast.AST) -> frozenset[_FunctionNode]:
        # Calling a captured local instance selects its existing class member.
        implicit_callables: frozenset[_FunctionNode] = frozenset().union(
            *(
                self._class_member_callables.get((owner, "__call__"), frozenset())
                for owner in self._resolve_object_references(node)
                if owner.startswith(_INSTANCE_REFERENCE_PREFIX)
            )
        )
        if implicit_callables:
            return implicit_callables
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

    def _static_dict_comprehension_mapping(
        self,
        node: ast.DictComp,
    ) -> _StaticMapping | None:
        """Project a literal sequence of key/value pairs through a simple dict comprehension."""

        if len(node.generators) != 1:
            return None
        generator = node.generators[0]
        if generator.is_async:
            return None
        if any(
            isinstance(condition, ast.Constant) and not bool(condition.value)
            for condition in generator.ifs
        ):
            site = ast.copy_location(ast.Dict(keys=[], values=[]), node)
            candidate = _StaticMapping(site=site, entries=())
            return self._mapping_snapshot_intern.setdefault(candidate, candidate)
        if not (
            isinstance(generator.target, (ast.Tuple, ast.List))
            and len(generator.target.elts) == 2
            and isinstance(node.key, ast.Name)
            and isinstance(node.value, ast.Name)
            and isinstance(generator.iter, (ast.List, ast.Tuple, ast.Set))
            and not any(isinstance(item, ast.Starred) for item in generator.iter.elts)
        ):
            return None
        key_target, value_target = generator.target.elts
        if not (
            isinstance(key_target, ast.Name)
            and isinstance(value_target, ast.Name)
            and node.key.id == key_target.id
            and node.value.id == value_target.id
        ):
            return None

        entries: list[_StaticMappingEntry] = []
        for item in generator.iter.elts:
            if not (
                isinstance(item, (ast.Tuple, ast.List))
                and len(item.elts) == 2
                and not any(isinstance(element, ast.Starred) for element in item.elts)
            ):
                return None
            key, value = item.elts
            entries.append(
                _StaticMappingEntry(
                    key=key,
                    binding=self._capture_argument_binding(value),
                )
            )
        site = ast.copy_location(ast.Dict(keys=[], values=[]), node)
        candidate = _StaticMapping(site=site, entries=tuple(entries))
        return self._mapping_snapshot_intern.setdefault(candidate, candidate)

    def _resolve_mapping(self, node: ast.AST) -> _StaticMapping | None:
        if id(node) in self._call_result_bindings:
            return self._call_result_bindings[id(node)].mapping
        if isinstance(node, ast.Await):
            return self._resolve_mapping(node.value)
        if isinstance(node, ast.NamedExpr):
            return self._resolve_mapping(node.value)
        if isinstance(node, ast.Dict):
            return self._mapping_literal_snapshots.get(id(node))
        if isinstance(node, ast.DictComp):
            return self._mapping_literal_snapshots.get(id(node))
        if isinstance(node, ast.Name):
            return self.scope.resolve_mapping(node.id)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            existing = self._mapping_literal_snapshots.get(id(node))
            if existing is not None:
                return existing
            left = self._resolve_mapping(node.left)
            right = self._resolve_mapping(node.right)
            if left is None or right is None:
                return None
            site = ast.copy_location(ast.Dict(keys=[], values=[]), node)
            candidate = _StaticMapping(
                site=site,
                entries=_effective_static_mapping_entries((*left.entries, *right.entries)),
            )
            snapshot = self._mapping_snapshot_intern.setdefault(candidate, candidate)
            self._mapping_literal_snapshots[id(node)] = snapshot
            return snapshot
        if isinstance(node, ast.Subscript):
            binding, _unresolved = self._resolve_mapping_subscript_binding(node)
            return binding.mapping if binding is not None else None
        return None

    def _invalidate_mapping(
        self,
        mapping: _StaticMapping,
        *,
        known_empty: bool = False,
    ) -> None:
        next_count = self._mapping_invalidation_counts.get(mapping, 0) + 1
        self._mapping_invalidation_counts[mapping] = next_count
        if known_empty:
            self._mapping_last_clear_counts[mapping] = next_count
        scope: _LexicalBindings | None = self.scope
        while scope is not None:
            for name, candidate in tuple(scope.mappings.items()):
                if candidate is mapping:
                    scope.mappings.pop(name, None)
                    scope.iterable_elements.pop(name, None)
                    if name.startswith("<dict-argument:"):
                        continue
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
            if node.attr == "__dict__" and self._is_legacy_module_reference(owner_reference):
                return (
                    "legacy_app.__dict__"
                    if owner_reference == "legacy_app"
                    else _POSSIBLE_LEGACY_REFERENCE
                )
            if (
                self._is_legacy_namespace_reference(owner_reference)
                and node.attr in _DICT_NAMESPACE_LOOKUP_METHODS | _MAPPING_MUTATOR_METHODS
            ):
                return f"legacy_app.__dict__.{node.attr}"
            if owner_reference == _KNOWN_NON_APP_REFERENCE:
                return None
            if owner_reference == "builtins" and node.attr == "dict":
                return "builtins.dict"
            if owner_reference == "builtins.dict" and node.attr in _MAPPING_MUTATOR_METHODS:
                return f"builtins.dict.{node.attr}"
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
            if node.attr in _MAPPING_MUTATOR_METHODS:
                namespace_kind = self._object_namespace_mapping_kind(node.value)
                if namespace_kind == "builtins":
                    return f"{_BUILTINS_NAMESPACE_REFERENCE}.{node.attr}"
                if namespace_kind == "module":
                    return f"{_MODULE_NAMESPACE_REFERENCE}.{node.attr}"
        if isinstance(node, ast.Call):
            if self._resolve_reference(node.func) == _CAPTURED_POSSIBLE_APP_FACTORY_REFERENCE:
                return _POSSIBLE_APP_REFERENCE
            importer_reference = self._resolve_reference(node.func)
            if (
                importer_reference == "builtins.vars"
                and len(node.args) == 1
                and not node.keywords
                and self._is_legacy_module_reference(self._resolve_reference(node.args[0]))
            ):
                return "legacy_app.__dict__"
            module_strings: list[str | None] = []
            positional_arguments, unresolved_positional_sources = (
                _expand_static_positional_arguments(node.args)
            )
            module_argument_unresolved = bool(unresolved_positional_sources)
            if positional_arguments:
                module_strings.append(self._resolve_string(positional_arguments[0]))
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
            if importer_reference == "builtins.__import__" and (
                module_argument_unresolved
                or module_strings
                in [
                    [None],
                    [_DYNAMIC_STRING_BINDING],
                ]
            ):
                return _POSSIBLE_BUILTINS_NAMESPACE_REFERENCE
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
            if (
                self._resolve_reference(node.value) == "sys.modules"
                and self._resolve_string(node.slice) == "builtins"
            ):
                return "builtins"
            mapping_binding, _mapping_unresolved = self._resolve_mapping_subscript_binding(node)
            if mapping_binding is not None:
                return mapping_binding.reference
            if self._resolve_mapping(node.value) is None:
                selected, _unresolved = _literal_subscript_value(node)
                if selected is not None:
                    return self._resolve_reference(selected)
        if self._is_definitely_non_app_value(node):
            return _KNOWN_NON_APP_REFERENCE
        if isinstance(node, ast.Name):
            return None
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            attribute_parent_reference = self.scope.resolve_reference(node.value.id)
            return _static_module_reference(
                node,
                module_aliases=(
                    {node.value.id: attribute_parent_reference}
                    if attribute_parent_reference is not None
                    else {}
                ),
                import_module_aliases=frozenset(),
                static_string_bindings={},
            )
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
            indexed_shape = _indexed_tuple_shape(container_reference)
            if indexed_shape is not None:
                index = _literal_value(node.slice)
                sensitive_index, arity = indexed_shape
                if isinstance(index, int) and 0 <= index < arity and index != sensitive_index:
                    return _KNOWN_NON_APP_REFERENCE
                indexed_value = self._resolve_iterable_element_binding(node.value)
                if index == sensitive_index and indexed_value is not None:
                    return indexed_value.reference
                return _POSSIBLE_APP_CALL_REFERENCE
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

    def _resolve_string(self, node: ast.AST, *, own_environment: bool = False) -> str | None:
        if own_environment:
            node_id = id(node)
            if (
                self.reference_snapshots is None
                or self.string_snapshots is None
                or node_id not in self.reference_snapshots
                or node_id not in self.string_snapshots
            ):
                return None
            previous = self.scope
            self._switch_deferred_scope(_LexicalBindings(parent=None), restore_flow=False)
            self.scope.references = dict(self.reference_snapshots[node_id])
            self.scope.strings = dict(self.string_snapshots[node_id])
            try:
                return self._resolve_string(node)
            finally:
                self._switch_deferred_scope(previous, restore_flow=False)
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
        if isinstance(node, ast.Name):
            string = self.scope.resolve_string(node.id)
            if string is not None:
                return string
            # An imported or captured unknown value may be a protected string.
            # A missing lexical fact stays unbound; a known non-app scalar with
            # no string fact retains its existing non-string/unknown boundary.
            reference = self.scope.resolve_reference(node.id)
            if reference is not None and reference != _KNOWN_NON_APP_REFERENCE:
                return _DYNAMIC_STRING_BINDING
            return None
        if isinstance(node, ast.Constant):
            return node.value if isinstance(node.value, str) else None
        return _resolve_static_string(
            node, self.scope.visible_strings(), ownership_family=self.ownership_family
        )

    def _join_expression_bindings(
        self,
        nodes: Sequence[ast.AST],
    ) -> tuple[str | None, str | None]:
        marker = "<expression-result>"
        active_scope = self.scope
        outcomes: list[_LexicalBindings] = []
        for node in nodes:
            outcome = active_scope.clone()
            reference = self._resolve_reference(node)
            outcome.bind(
                marker,
                reference=self._namespace_mapping_binding_reference(
                    node,
                    reference,
                ),
                string=self._resolve_string(node),
            )
            outcomes.append(outcome)
        merged = active_scope.clone()
        self._merge_outcomes(merged, outcomes, flow_join=False)
        self._switch_deferred_scope(active_scope, restore_flow=False)
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
            self._switch_deferred_scope(incoming.clone(), restore_flow=True)
            if self._visit_statements(branch):
                outcomes.append(self.scope)
        if not outcomes:
            self._switch_deferred_scope(incoming, restore_flow=True)
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
            self._switch_deferred_scope(incoming, restore_flow=True)
            return False
        self._merge_outcomes(incoming, outcomes)
        return True

    def _bindings_equal(self, left: _LexicalBindings, right: _LexicalBindings) -> bool:
        if left._flow_snapshot is not None and right._flow_snapshot is not None:
            return self._deferred_flow_equal(left._flow_snapshot, right._flow_snapshot)
        return (
            left.references == right.references
            and left.strings == right.strings
            and left.callables == right.callables
            and left.deferred_calls == right.deferred_calls
            and left.mappings == right.mappings
            and left.class_references == right.class_references
            and left.descriptors == right.descriptors
            and left.iterable_elements == right.iterable_elements
            and left.ordered_items == right.ordered_items
            and left.call_receivers == right.call_receivers
            and self._deferred_flow_equal(left._flow_snapshot, right._flow_snapshot)
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

    def _merge_binding_facts(
        self,
        target: _LexicalBindings,
        outcomes: Sequence[_LexicalBindings],
        *,
        snapshot_projection: bool = False,
    ) -> None:
        """Merge nonempty lexical facts without capturing Flow graphs."""
        joined_references: dict[str, str] = {}
        if all(outcome.references == outcomes[0].references for outcome in outcomes):
            joined_references = {
                name: value for name, value in outcomes[0].references.items() if value is not None
            }
        else:
            reference_names = {
                name
                for outcome in outcomes[1:]
                for name, _value in outcomes[0].references.items() ^ outcome.references.items()
            }
            joined_references = {
                name: value
                for name, value in outcomes[0].references.items()
                if value is not None and name not in reference_names
            }
            for name in reference_names:
                values = {outcome.references.get(name) for outcome in outcomes}
                if len(values) == 1:
                    reference_value = next(iter(values))
                    if reference_value is not None:
                        joined_references[name] = reference_value
                    continue
                namespace_values = {
                    _BUILTINS_NAMESPACE_REFERENCE,
                    _POSSIBLE_BUILTINS_NAMESPACE_REFERENCE,
                    _MODULE_NAMESPACE_REFERENCE,
                    _POSSIBLE_OBJECT_NAMESPACE_REFERENCE,
                } & values
                if namespace_values and values <= namespace_values | {None}:
                    joined_references[name] = (
                        next(iter(namespace_values))
                        if len(namespace_values) == 1
                        else _POSSIBLE_OBJECT_NAMESPACE_REFERENCE
                    )
                elif namespace_mutator_values := {
                    value
                    for value in values
                    if value is not None and _namespace_mutator_method(value) is not None
                }:
                    legacy_methods = {
                        method
                        for value in values
                        if (method := _namespace_mutator_method(value, legacy_only=True))
                        is not None
                    }
                    if any(_is_registration_callable_reference(value) for value in values):
                        joined_references[name] = _POSSIBLE_APP_CALL_REFERENCE
                    elif legacy_methods:
                        methods = legacy_methods | {
                            method
                            for value in namespace_mutator_values
                            if (method := _namespace_mutator_method(value)) is not None
                        }
                        prefixes = {
                            prefix
                            for value in namespace_mutator_values
                            for prefix in (
                                f"{_BUILTINS_NAMESPACE_REFERENCE}.",
                                f"{_MODULE_NAMESPACE_REFERENCE}.",
                                _POSSIBLE_NAMESPACE_MUTATOR_REFERENCE_PREFIX,
                                "builtins.dict.",
                            )
                            if value.startswith(prefix)
                        }
                        prefix = (
                            next(iter(prefixes))
                            if len(prefixes) == 1
                            else _POSSIBLE_NAMESPACE_MUTATOR_REFERENCE_PREFIX
                        )
                        method = next(iter(methods)) if len(methods) == 1 else "*"
                        joined_references[name] = (
                            f"{prefix}{_POSSIBLE_LEGACY_REFERENCE}.__dict__.{method}"
                        )
                    elif len(namespace_mutator_values) == 1:
                        joined_references[name] = next(iter(namespace_mutator_values))
                    else:
                        methods = {
                            method
                            for value in namespace_mutator_values
                            if (method := _namespace_mutator_method(value)) is not None
                        }
                        method = next(iter(methods)) if len(methods) == 1 else "*"
                        joined_references[name] = (
                            f"{_POSSIBLE_NAMESPACE_MUTATOR_REFERENCE_PREFIX}{method}"
                        )
                elif self.preserve_lifecycle_conflicts and values & {
                    "builtins.__import__",
                    "importlib.import_module",
                    _POSSIBLE_IMPORT_CALLABLE_REFERENCE,
                }:
                    joined_references[name] = _POSSIBLE_IMPORT_CALLABLE_REFERENCE
                elif self.preserve_fastapi_conflicts and values & {
                    "fastapi.FastAPI",
                    "fastapi.applications.FastAPI",
                    _POSSIBLE_FASTAPI_REFERENCE,
                    _CONFLICTED_FASTAPI_REFERENCE,
                }:
                    joined_references[name] = _POSSIBLE_FASTAPI_REFERENCE
                elif values & {"builtins.getattr", _POSSIBLE_GETATTR_REFERENCE}:
                    joined_references[name] = _POSSIBLE_GETATTR_REFERENCE
                elif any(self._may_reference_legacy(value) for value in values):
                    legacy_mutator_methods = {
                        value.rpartition(".")[2]
                        for value in values
                        if value is not None
                        and value.rpartition(".")[0]
                        in {"legacy_app.__dict__", f"{_POSSIBLE_LEGACY_REFERENCE}.__dict__"}
                        and value.rpartition(".")[2] in _MAPPING_MUTATOR_METHODS | {"*"}
                    }
                    joined_references[name] = (
                        f"{_POSSIBLE_LEGACY_REFERENCE}.__dict__."
                        f"{next(iter(legacy_mutator_methods)) if len(legacy_mutator_methods) == 1 else '*'}"
                        if legacy_mutator_methods
                        else _POSSIBLE_LEGACY_REFERENCE
                    )
                elif values & {
                    _ITERABLE_APP_ELEMENT_REFERENCE,
                    _ITERABLE_SENSITIVE_ELEMENT_REFERENCE,
                    _MAPPING_APP_VALUE_REFERENCE,
                    _MAPPING_SENSITIVE_VALUE_REFERENCE,
                }:
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
                    or (
                        value is not None
                        and value.startswith(_MIDDLEWARE_DECORATOR_REFERENCE_PREFIX)
                    )
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
                elif values & {"pulseplate.app", _POSSIBLE_APP_REFERENCE}:
                    joined_references[name] = _POSSIBLE_APP_REFERENCE
                elif values & {"pulseplate.app.router", _POSSIBLE_ROUTER_REFERENCE}:
                    joined_references[name] = _POSSIBLE_ROUTER_REFERENCE
        target.references = joined_references

        joined_strings: dict[str, str] = {}
        if all(outcome.strings == outcomes[0].strings for outcome in outcomes):
            joined_strings = {
                name: value for name, value in outcomes[0].strings.items() if value is not None
            }
        else:
            string_names = {
                name
                for outcome in outcomes[1:]
                for name, _value in outcomes[0].strings.items() ^ outcome.strings.items()
            }
            joined_strings = {
                name: value
                for name, value in outcomes[0].strings.items()
                if value is not None and name not in string_names
            }
            for name in string_names:
                values = {outcome.strings.get(name) for outcome in outcomes}
                if len(values) == 1:
                    string_value = next(iter(values))
                    if string_value is not None:
                        joined_strings[name] = string_value
                elif self.preserve_route_method_conflicts and values & {
                    *APP_ROUTE_METHODS,
                    *APP_REGISTRATION_METHODS,
                    _POSSIBLE_ROUTE_METHOD,
                    _CONFLICTED_ROUTE_METHOD,
                }:
                    joined_strings[name] = _POSSIBLE_ROUTE_METHOD
                elif any(self._is_protected_ownership_symbol(value) for value in values):
                    joined_strings[name] = (
                        _POSSIBLE_API_KEY_SYMBOL
                        if self.ownership_family == "api_key"
                        else _POSSIBLE_OPENAPI_SYMBOL
                    )
        target.strings = joined_strings
        if snapshot_projection:
            return

        callable_names = set().union(*(set(outcome.callables) for outcome in outcomes))
        joined_callables: dict[str, frozenset[_FunctionNode]] = {}
        for name in callable_names:
            candidates = frozenset().union(
                *(outcome.callables.get(name, frozenset()) for outcome in outcomes)
            )
            if candidates:
                joined_callables[name] = candidates
        target.callables = joined_callables

        deferred_names = set().union(*(set(outcome.deferred_calls) for outcome in outcomes))
        joined_deferred_calls: dict[str, frozenset[_DeferredFunctionCall]] = {}
        for name in deferred_names:
            deferred_candidates: frozenset[_DeferredFunctionCall] = frozenset().union(
                *(outcome.deferred_calls.get(name, frozenset()) for outcome in outcomes)
            )
            if deferred_candidates:
                joined_deferred_calls[name] = deferred_candidates
        target.deferred_calls = joined_deferred_calls

        mapping_names = set().union(*(set(outcome.mappings) for outcome in outcomes))
        joined_mappings: dict[str, _StaticMapping] = {}
        for name in mapping_names:
            mapping_values = [outcome.mappings.get(name) for outcome in outcomes]
            first_mapping = mapping_values[0]
            if first_mapping is not None and all(
                value is first_mapping for value in mapping_values
            ):
                joined_mappings[name] = first_mapping
        target.mappings = joined_mappings
        class_reference_names = set().union(
            *(set(outcome.class_references) for outcome in outcomes)
        )
        target.class_references = {
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
        target.descriptors = joined_descriptors
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
        target.iterable_elements = joined_iterable_elements
        ordered_names = set().union(*(set(outcome.ordered_items) for outcome in outcomes))
        target.ordered_items = {}
        for name in ordered_names:
            rows = [outcome.ordered_items.get(name) for outcome in outcomes]
            if all(row is not None for row in rows):
                known = cast(list[tuple[_ResolvedBinding, ...]], rows)
                if len({len(row) for row in known}) == 1:
                    target.ordered_items[name] = tuple(
                        self._join_resolved_bindings([row[index] for row in known])
                        for index in range(len(known[0]))
                    )
        receiver_names = set().union(*(set(outcome.call_receivers) for outcome in outcomes))
        target.call_receivers = {
            name: frozenset().union(
                *(outcome.call_receivers.get(name, frozenset()) for outcome in outcomes)
            )
            for name in receiver_names
        }
        target.bound_names = set.intersection(*(set(outcome.bound_names) for outcome in outcomes))
        target.possibly_bound_names = set().union(
            *(set(outcome.possibly_bound_names) for outcome in outcomes)
        )

    def _merge_outcomes(
        self,
        incoming: _LexicalBindings,
        outcomes: Sequence[_LexicalBindings],
        *,
        snapshot_projection: bool = False,
        flow_join: bool = True,
    ) -> None:
        self._freeze_deferred_scope(self.scope)
        flow_outcomes = [outcome._flow_snapshot for outcome in outcomes]
        joins_flow = (
            flow_join
            and not snapshot_projection
            and bool(outcomes)
            and all(state is not None for state in flow_outcomes)
        )
        self.scope = incoming
        if not outcomes:
            return
        self._merge_binding_facts(incoming, outcomes, snapshot_projection=snapshot_projection)
        if snapshot_projection:
            return
        if joins_flow:
            self._join_deferred_progress(cast(list[_DeferredFlowSnapshot], flow_outcomes), incoming)
        incoming._flow_owner = self
        incoming._flow_snapshot = self._capture_deferred_flow(incoming)

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
        ordered_items: tuple[_ResolvedBinding, ...] | None = None,
        call_receivers: frozenset[tuple[_FunctionNode, str, _ResolvedBinding]] = frozenset(),
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
                    ordered_items=ordered_items,
                    call_receivers=call_receivers,
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
            ordered_items=binding.ordered_items,
            call_receivers=binding.call_receivers,
        )

    def _bind_indexed_pair_target(
        self,
        target: ast.expr,
        pair_binding: _ResolvedBinding,
        *,
        child_binder: Callable[[ast.expr, _ResolvedBinding], bool | None] | None = None,
    ) -> bool | None:
        indexed_shape = _indexed_tuple_shape(pair_binding.reference)
        if (
            indexed_shape is None
            or pair_binding.iterable_element is None
            or not isinstance(target, (ast.Tuple, ast.List))
        ):
            return False
        sensitive_index, arity = indexed_shape
        if len(target.elts) != arity:
            return False
        if child_binder is not None:
            for index, child_target in enumerate(target.elts):
                child = (
                    pair_binding.iterable_element
                    if index == sensitive_index
                    else _ResolvedBinding(_KNOWN_NON_APP_REFERENCE, None)
                )
                if isinstance(child_target, ast.Starred):
                    child = self._variadic_iterable_binding([child])
                if child_binder(child_target, child) is None:
                    return None
            return True
        for index, child_target in enumerate(target.elts):
            if index != sensitive_index:
                self._bind_targets(
                    [child_target],
                    reference=_KNOWN_NON_APP_REFERENCE,
                    string=None,
                )
        value_target = target.elts[sensitive_index]
        value_binding = (
            self._variadic_iterable_binding([pair_binding.iterable_element])
            if isinstance(value_target, ast.Starred)
            else pair_binding.iterable_element
        )
        self._bind_targets_from_resolved_binding([value_target], value_binding)
        return True

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

    @staticmethod
    def _is_builtin_namespace_reference(reference: str | None) -> bool:
        return reference in {
            "builtins",
            _BUILTINS_NAMESPACE_REFERENCE,
            _POSSIBLE_BUILTINS_NAMESPACE_REFERENCE,
            _POSSIBLE_OBJECT_NAMESPACE_REFERENCE,
        }

    def _builtins_object_is_safe(self) -> bool:
        return (
            self._module_scope().resolve_reference(_BUILTINS_OBJECT_STATE_NAME)
            == _SAFE_BUILTINS_OBJECT_REFERENCE
        )

    def _is_proven_builtin_object_callable(self, node: ast.AST) -> bool:
        reference = self._resolve_reference(node)
        if reference == _CAPTURED_SAFE_BUILTINS_OBJECT_REFERENCE:
            return True
        if reference != "builtins.object":
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

    def _capture_reference_provenance(
        self,
        node: ast.AST,
        reference: str | None,
    ) -> str | None:
        if reference != "builtins.object":
            return reference
        if self._is_proven_builtin_object_callable(node):
            return _CAPTURED_SAFE_BUILTINS_OBJECT_REFERENCE
        return _CAPTURED_POSSIBLE_APP_FACTORY_REFERENCE

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
        if self._is_builtin_namespace_reference(reference) or reference == "builtins.__dict__":
            return "builtins"
        if reference == _MODULE_NAMESPACE_REFERENCE:
            return "module"
        if isinstance(node, ast.Attribute) and node.attr == "__dict__":
            owner_reference = self._resolve_reference(node.value)
            if self._is_builtin_namespace_reference(owner_reference):
                return "builtins"
            if self._is_proven_current_module_object(node.value):
                return "module"
            return None
        if (
            isinstance(node, ast.Call)
            and self._resolve_reference(node.func) == "builtins.getattr"
            and len(node.args) == 2
            and not node.keywords
            and self._resolve_string(node.args[1]) == "__dict__"
        ):
            owner = node.args[0]
            if self._is_builtin_namespace_reference(self._resolve_reference(owner)):
                return "builtins"
            if self._is_proven_current_module_object(owner):
                return "module"
            return None
        if not isinstance(node, ast.Call) or node.keywords:
            return None
        function_reference = self._resolve_reference(node.func)
        if function_reference == "builtins.globals":
            return "module" if not node.args else None
        if function_reference == "builtins.locals":
            return "module" if not node.args and self.scope.scope_kind == "module" else None
        if function_reference != "builtins.vars":
            return None
        if not node.args:
            return "module" if self.scope.scope_kind == "module" else None
        if len(node.args) != 1:
            return None
        owner = node.args[0]
        if self._is_builtin_namespace_reference(self._resolve_reference(owner)):
            return "builtins"
        if self._is_proven_current_module_object(owner):
            return "module"
        return None

    def _namespace_mapping_binding_reference(
        self,
        node: ast.AST,
        reference: str | None,
    ) -> str | None:
        if reference in {
            _BUILTINS_NAMESPACE_REFERENCE,
            _MODULE_NAMESPACE_REFERENCE,
        }:
            return reference
        is_dunder_dict = isinstance(node, ast.Attribute) and node.attr == "__dict__"
        is_namespace_builtin_call = isinstance(node, ast.Call) and self._resolve_reference(
            node.func
        ) in {
            "builtins.globals",
            "builtins.vars",
            "builtins.locals",
        }
        if not is_dunder_dict and not is_namespace_builtin_call:
            return reference
        namespace_kind = self._object_namespace_mapping_kind(node)
        if namespace_kind == "builtins":
            return _BUILTINS_NAMESPACE_REFERENCE
        if namespace_kind == "module":
            return _MODULE_NAMESPACE_REFERENCE
        return reference

    def _object_namespace_target_kind(self, target: ast.AST) -> str | None:
        if isinstance(target, ast.Attribute) and target.attr == "object":
            if self._is_builtin_namespace_reference(self._resolve_reference(target.value)):
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

    def _visit_object_namespace_target_expressions(self, target: ast.AST) -> None | Literal[False]:
        """Evaluate assignment-target owners before classifying their namespace."""

        if isinstance(target, ast.Starred):
            if (
                self._visit_object_namespace_target_expressions(target.value) is False
                and self._invocation_outcome_request() is not None
            ):
                return False
            return None
        if isinstance(target, (ast.Tuple, ast.List)):
            for child in target.elts:
                if (
                    self._visit_object_namespace_target_expressions(child) is False
                    and self._invocation_outcome_request() is not None
                ):
                    return False
            return None
        if isinstance(target, (ast.Attribute, ast.Subscript)) and (
            self.reference_snapshots is not None or self.string_snapshots is not None
        ):
            self._record_snapshot(target)
        if isinstance(target, ast.Attribute):
            if self.visit(target.value) is False and self._invocation_outcome_request() is not None:
                return False
            if self.filename == LEGACY_APP and self._is_proven_current_module_object(target.value):
                self._record_outward_api_key_rebinding(target.attr, proven_module_namespace=True)
            if (
                self.ownership_family == "api_key"
                and target.attr in CANONICAL_API_KEY_SYMBOLS
                and self._is_legacy_module_reference(self._resolve_reference(target.value))
            ):
                self.errors.append(
                    f"{self.filename}: legacy API-key dependency attribute access is forbidden: "
                    f"{target.attr}"
                )
            return None
        if isinstance(target, ast.Subscript):
            if self.visit(target.value) is False and self._invocation_outcome_request() is not None:
                return False
            receiver_reference = self._resolve_reference(target.value)
            module_namespace = (
                self.filename == LEGACY_APP
                and self._object_namespace_mapping_kind(target.value) == "module"
            )
            if self.visit(target.slice) is False and self._invocation_outcome_request() is not None:
                return False
            if (
                self.filename == LEGACY_APP
                and module_namespace
                and not (
                    isinstance(target.slice, ast.Constant)
                    and not isinstance(target.slice.value, str)
                )
            ):
                member = self._capture_argument_binding(target.slice).string
                for name in (
                    CANONICAL_API_KEY_SYMBOLS
                    if member in {None, _DYNAMIC_STRING_BINDING}
                    else {member}
                ):
                    self._record_outward_api_key_rebinding(name, proven_module_namespace=True)
            if self.ownership_family == "api_key" and self._is_legacy_namespace_reference(
                receiver_reference
            ):
                symbol_name = self._resolve_string(target.slice)
                if symbol_name in CANONICAL_API_KEY_SYMBOLS or symbol_name in {
                    None,
                    _DYNAMIC_STRING_BINDING,
                    _POSSIBLE_API_KEY_SYMBOL,
                }:
                    self.errors.append(
                        f"{self.filename}: legacy API-key dependency namespace lookup is forbidden: "
                        f"{symbol_name if symbol_name in CANONICAL_API_KEY_SYMBOLS else '<dynamic>'}"
                    )
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
                module_scope.bind(
                    "object",
                    reference=_CAPTURED_POSSIBLE_APP_FACTORY_REFERENCE,
                    string=None,
                )
            return True
        module_scope.bind(
            "object",
            reference=(
                "builtins.object"
                if deletion and self._builtins_object_is_safe()
                else _CAPTURED_POSSIBLE_APP_FACTORY_REFERENCE
            ),
            string=None,
        )
        return True

    def _refine_object_namespace_assignment(
        self,
        target: ast.AST,
        value_reference: str | None,
    ) -> None:
        if self._object_namespace_target_kind(target) not in {"builtins", "module"}:
            return
        if value_reference not in {
            "pulseplate.app",
            "pulseplate.app.router",
            _POSSIBLE_APP_REFERENCE,
            _POSSIBLE_ROUTER_REFERENCE,
        }:
            return
        self._module_scope().bind(
            "object",
            reference=value_reference,
            string=None,
        )

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
                module_scope.bind(
                    "object",
                    reference=_CAPTURED_POSSIBLE_APP_FACTORY_REFERENCE,
                    string=None,
                )
            return
        if namespace_kind != "module":
            raise LegacyGrowthAnalysisError(
                f"{self.filename}: unsupported object namespace kind: {namespace_kind}"
            )
        module_scope.bind(
            "object",
            reference=(
                "builtins.object"
                if deletion and self._builtins_object_is_safe()
                else _CAPTURED_POSSIBLE_APP_FACTORY_REFERENCE
            ),
            string=None,
        )

    def _record_object_namespace_call_mutation(
        self,
        node: ast.Call,
        *,
        captured_function_reference: str | None = None,
        captured_receiver: _ResolvedBinding | None = None,
        captured_arguments: Sequence[_ResolvedBinding] = (),
    ) -> None:
        if (
            self.filename == LEGACY_APP
            and captured_receiver is not None
            and captured_receiver.reference == _MODULE_NAMESPACE_REFERENCE
        ):
            method = _namespace_mutator_method(captured_function_reference)
            api_arguments = captured_arguments
            if captured_function_reference is not None and captured_function_reference.startswith(
                "builtins.dict."
            ):
                api_arguments = api_arguments[1:]
            names: set[str | None] = set()
            if method in {"clear", "popitem"} and not api_arguments and not node.keywords:
                names.add(None)
            elif method in {"__delitem__", "__setitem__", "pop", "setdefault"}:
                valid_arity = (
                    len(api_arguments) == 2
                    if method == "__setitem__"
                    else (
                        len(api_arguments) == 1
                        if method == "__delitem__"
                        else 1 <= len(api_arguments) <= 2
                    )
                )
                if valid_arity and not node.keywords:
                    key_nodes, unresolved_key_arguments = _expand_static_positional_arguments(
                        node.args
                    )
                    key_index = (
                        1
                        if captured_function_reference is not None
                        and captured_function_reference.startswith("builtins.dict.")
                        else 0
                    )
                    key_node = key_nodes[key_index] if len(key_nodes) > key_index else None
                    if not (
                        not unresolved_key_arguments
                        and isinstance(key_node, ast.Constant)
                        and not isinstance(key_node.value, str)
                    ):
                        names.add(api_arguments[0].string)
            elif method in {"update", "__init__", "__ior__"}:
                valid_arity = (
                    len(api_arguments) == 1 if method == "__ior__" else len(api_arguments) <= 1
                )
                if valid_arity and (method != "__ior__" or not node.keywords):
                    names.update(keyword.arg for keyword in node.keywords)
                    for api_argument in api_arguments:
                        if api_argument.mapping is None:
                            names.add(None)
                            continue
                        for entry in api_argument.mapping.entries:
                            if isinstance(entry.key, ast.Constant):
                                if isinstance(entry.key.value, str):
                                    names.add(entry.key.value)
                            else:
                                # AST keys are not frozen string evidence after value effects.
                                names.add(None)
            selected = (
                CANONICAL_API_KEY_SYMBOLS
                if names & {None, _DYNAMIC_STRING_BINDING}
                else CANONICAL_API_KEY_SYMBOLS.intersection(names)
            )
            for name in sorted(selected):
                self._record_outward_api_key_rebinding(name, proven_module_namespace=True)
        function_reference = self._resolve_reference(node.func)
        descriptor_method = (
            node.func.attr
            if isinstance(node.func, ast.Attribute)
            and node.func.attr in {"__setattr__", "__delattr__"}
            and self._is_proven_builtin_object_callable(node.func.value)
            else None
        )
        if function_reference in {"builtins.setattr", "builtins.delattr"} or (
            descriptor_method is not None
        ):
            if len(node.args) < 2 or node.keywords:
                return
            owner = node.args[0]
            owner_reference = self._resolve_reference(owner)
            namespace_kind = (
                "builtins"
                if self._is_builtin_namespace_reference(owner_reference)
                else ("module" if self._is_proven_current_module_object(owner) else None)
            )
            if namespace_kind is None:
                return
            member_name = self._resolve_string(node.args[1])
            if member_name not in {"object", None, _DYNAMIC_STRING_BINDING}:
                return
            self._record_object_namespace_kind(
                namespace_kind,
                deletion=(
                    function_reference == "builtins.delattr" or descriptor_method == "__delattr__"
                ),
            )
            return

        mapping_namespace_kinds: tuple[str, ...] = ()
        arguments: Sequence[ast.expr] = node.args
        method = _namespace_mutator_method(function_reference)
        dict_method_prefix = "builtins.dict."
        if function_reference is not None and function_reference.startswith(dict_method_prefix):
            if method not in _MAPPING_MUTATOR_METHODS | {"*"} or not arguments:
                return
            direct_namespace_kind = self._object_namespace_mapping_kind(arguments[0])
            if direct_namespace_kind is None:
                return
            mapping_namespace_kinds = (direct_namespace_kind,)
            arguments = arguments[1:]
        elif method is not None:
            if function_reference is not None and function_reference.startswith(
                f"{_BUILTINS_NAMESPACE_REFERENCE}."
            ):
                mapping_namespace_kinds = ("builtins",)
            elif function_reference is not None and function_reference.startswith(
                f"{_MODULE_NAMESPACE_REFERENCE}."
            ):
                mapping_namespace_kinds = ("module",)
            else:
                mapping_namespace_kinds = ("builtins", "module")
        if not mapping_namespace_kinds:
            if not isinstance(node.func, ast.Attribute):
                return
            direct_namespace_kind = self._object_namespace_mapping_kind(node.func.value)
            if direct_namespace_kind is None:
                return
            mapping_namespace_kinds = (direct_namespace_kind,)
            method = node.func.attr
        if method == "*":
            for namespace_kind in mapping_namespace_kinds:
                self._record_object_namespace_kind(namespace_kind)
            return
        if method in {"clear", "popitem"}:
            for namespace_kind in mapping_namespace_kinds:
                self._record_object_namespace_kind(namespace_kind)
            return
        if method in {"__delitem__", "__setitem__", "pop", "setdefault"}:
            if not arguments:
                for namespace_kind in mapping_namespace_kinds:
                    self._record_object_namespace_kind(namespace_kind)
                return
            member_name = self._resolve_string(arguments[0])
            if member_name not in {"object", None, _DYNAMIC_STRING_BINDING}:
                return
            for namespace_kind in mapping_namespace_kinds:
                self._record_object_namespace_kind(
                    namespace_kind,
                    deletion=method in {"__delitem__", "pop"},
                )
            return
        if method not in {"__init__", "__ior__", "update"}:
            return
        keys: set[str | None] = {keyword.arg for keyword in node.keywords}
        for argument in arguments:
            if not isinstance(argument, ast.Dict):
                keys.add(None)
                continue
            keys.update(None if key is None else self._resolve_string(key) for key in argument.keys)
        if keys & {"object", None, _DYNAMIC_STRING_BINDING}:
            for namespace_kind in mapping_namespace_kinds:
                self._record_object_namespace_kind(namespace_kind)

    def _preserve_sensitive_reference(
        self,
        name: str,
        value: ast.AST,
        resolved_reference: str | None,
        *,
        definitely_non_app: bool | None = None,
    ) -> str | None:
        if resolved_reference is not None:
            return resolved_reference
        if (
            self._is_definitely_non_app_value(value)
            if definitely_non_app is None
            else definitely_non_app
        ):
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

    def _capture_assignment_source_binding(
        self, value: ast.AST, *, dynamic_unknown_string: bool
    ) -> _ResolvedBinding:
        resolved_string = self._resolve_string(value)
        resolved_reference = self._resolve_reference(value)
        resolved_reference = self._namespace_mapping_binding_reference(
            value,
            resolved_reference,
        )
        resolved_reference = self._capture_reference_provenance(
            value,
            resolved_reference,
        )
        callables = self._resolve_callables(value)
        deferred_calls = self._resolve_deferred_calls(value)
        mapping = self._resolve_mapping(value)
        if (
            isinstance(value, ast.Attribute)
            and value.attr in {"__getitem__", "get", "items", "pop", "setdefault", "values"}
            and (owner_mapping := self._resolve_mapping(value.value)) is not None
        ):
            resolved_reference = f"builtins.dict.{value.attr}"
            mapping = owner_mapping
        class_references = self._resolve_class_references(value)
        descriptors = self._resolve_descriptors(value)
        iterable_element = self._resolve_iterable_element_binding(value)
        ordered_items = self._resolve_ordered_items(value)
        call_receivers = self._resolve_captured_receivers(value)
        literal = _literal_value(value)
        known_nonstring = (
            (literal is not _UNRESOLVED_LITERAL_VALUE and not isinstance(literal, str))
            or (
                isinstance(value, ast.Call)
                and not value.args
                and not value.keywords
                and self._is_proven_builtin_object_callable(value.func)
            )
            or (
                isinstance(value, ast.Name)
                and resolved_reference == _KNOWN_NON_APP_REFERENCE
                and self.scope.resolve_string(value.id) is None
            )
        )
        string = (
            resolved_string
            if resolved_string is not None
            else (
                _DYNAMIC_STRING_BINDING if dynamic_unknown_string and not known_nonstring else None
            )
        )
        return _ResolvedBinding(
            reference=resolved_reference,
            string=string,
            callables=callables,
            deferred_calls=deferred_calls,
            mapping=mapping,
            class_references=class_references,
            descriptors=descriptors,
            iterable_element=iterable_element,
            ordered_items=ordered_items,
            call_receivers=call_receivers,
        )

    def _bind_target_value(
        self,
        target: ast.expr,
        value: ast.AST,
        *,
        dynamic_unknown_string: bool,
        value_consumed: bool = False,
        captured_binding: _ResolvedBinding | None = None,
        target_evaluator: (
            Callable[[ast.expr, _ResolvedBinding], _ResolvedBinding | None | Literal[False]] | None
        ) = None,
    ) -> None | Literal[False]:
        if isinstance(target, (ast.Tuple, ast.List)):

            def bind_captured(
                current_target: ast.expr,
                binding: _ResolvedBinding,
                *,
                consumed: bool = False,
                root: bool = False,
            ) -> bool | None:
                if not isinstance(current_target, (ast.Tuple, ast.List)):
                    if target_evaluator is not None:
                        projected = target_evaluator(current_target, binding)
                        if projected is False:
                            return None
                        if isinstance(projected, _ResolvedBinding):
                            binding = projected
                        elif projected is not None:
                            raise LegacyGrowthAnalysisError(
                                "invalid captured-target leaf projection"
                            )
                    self._bind_targets_from_resolved_binding([current_target], binding)
                    return True
                if not consumed:
                    request = self._invocation_outcome_request()
                    offsets = (
                        (len(request.return_scopes), len(request.raise_scopes))
                        if request is not None
                        else None
                    )
                    if request is not None and binding.deferred_calls:
                        if offsets is None:
                            raise AssertionError
                        with self._temporary_iteration_result(current_target, pin_consumer=True):
                            self._remember_captured_binding(binding)
                            self._replay_deferred_calls(
                                binding.deferred_calls,
                                execution="iterate",
                                iteration_result_node=current_target,
                            )
                            normal = request.return_scopes[offsets[0] :]
                            del request.return_scopes[offsets[0] :]
                            for saved in normal:
                                state = saved._flow_snapshot
                                if state is None or id(current_target) not in state[2]:
                                    raise LegacyGrowthAnalysisError(
                                        "unpack lost its current iteration result"
                                    )
                                self._restore_deferred_flow(state)
                                self.scope = saved
                                projected = state[2][id(current_target)]
                                self._remember_captured_binding(projected)
                                star_count = sum(
                                    isinstance(item, ast.Starred) for item in current_target.elts
                                )
                                rows = projected.ordered_items
                                if rows is not None and (
                                    (not star_count and len(rows) != len(current_target.elts))
                                    or star_count == 1
                                    and len(rows) < len(current_target.elts) - 1
                                    or star_count > 1
                                ):
                                    request.raise_scopes.append(self.scope.clone())
                                    continue
                                if rows is None and (
                                    not star_count or len(current_target.elts) > 1
                                ):
                                    request.raise_scopes.append(self.scope.clone())
                                if (
                                    bind_captured(
                                        current_target, projected, consumed=True, root=root
                                    )
                                    is not None
                                ):
                                    request.return_scopes.append(self.scope.clone())
                            return (
                                True if self._resume_invocation_outcomes(request, offsets) else None
                            )
                    self._replay_deferred_calls(binding.deferred_calls, execution="iterate")
                    if request is not None:
                        if offsets is None:
                            raise AssertionError
                        if not self._resume_invocation_outcomes(request, offsets):
                            return None
                ordered = binding.ordered_items
                if ordered is not None:
                    stars = [
                        index
                        for index, item in enumerate(current_target.elts)
                        if isinstance(item, ast.Starred)
                    ]
                    if not stars and len(current_target.elts) == len(ordered):
                        for child_target, child_binding in zip(
                            current_target.elts, ordered, strict=True
                        ):
                            if (bind_captured(child_target, child_binding)) is None:
                                return None
                        return True
                    if len(stars) == 1 and len(ordered) >= len(current_target.elts) - 1:
                        start = stars[0]
                        suffix = len(current_target.elts) - start - 1
                        for child_target, child_binding in zip(
                            current_target.elts[:start], ordered[:start], strict=True
                        ):
                            if (bind_captured(child_target, child_binding)) is None:
                                return None
                        middle = ordered[start : len(ordered) - suffix if suffix else None]
                        if (
                            bind_captured(
                                current_target.elts[start],
                                self._variadic_iterable_binding(middle, ordered_items=middle),
                            )
                        ) is None:
                            return None
                        if suffix:
                            for child_target, child_binding in zip(
                                current_target.elts[-suffix:], ordered[-suffix:], strict=True
                            ):
                                if (bind_captured(child_target, child_binding)) is None:
                                    return None
                        return True
                pair_bound = self._bind_indexed_pair_target(
                    current_target, binding, child_binder=bind_captured
                )
                if pair_bound is None:
                    return None
                if pair_bound:
                    return True
                element = self._deferred_result_element(binding)
                if element is not None:
                    for child_target in current_target.elts:
                        child_binding = (
                            self._variadic_iterable_binding([element])
                            if isinstance(child_target, ast.Starred)
                            else element
                        )
                        if (bind_captured(child_target, child_binding)) is None:
                            return None
                    return True
                if captured_binding is None and target_evaluator is None:
                    if root:
                        return False
                    self._bind_targets_from_resolved_binding([current_target], binding)
                    return True
                # Unknown shape retains the existing conservative publication;
                # target effects still follow the same leaf recursion.
                for child_target in current_target.elts:
                    if (
                        bind_captured(
                            child_target, self._conservative_argument_binding(), consumed=True
                        )
                        is None
                    ):
                        return None
                return True

            bound = bind_captured(
                target,
                (
                    captured_binding
                    if captured_binding is not None
                    else self._capture_argument_binding(value)
                ),
                consumed=value_consumed,
                root=True,
            )
            if bound is None:
                return False
            if bound:
                return None
        if captured_binding is not None:
            if target_evaluator is not None:
                projected = target_evaluator(target, captured_binding)
                if projected is False:
                    return False
                if isinstance(projected, _ResolvedBinding):
                    captured_binding = projected
                elif projected is not None:
                    raise LegacyGrowthAnalysisError("invalid captured-target leaf projection")
            self._bind_targets_from_resolved_binding([target], captured_binding)
            return None
        binding = self._capture_assignment_source_binding(
            value, dynamic_unknown_string=dynamic_unknown_string
        )
        for name in _assignment_target_names(target):
            self._bind_resolved_name(
                name,
                replace(
                    binding,
                    reference=self._preserve_sensitive_reference(name, value, binding.reference),
                ),
            )
        return None

    def _bind_iteration_target(self, target: ast.expr, iterable: ast.AST) -> None | Literal[False]:
        requested_structural = self._invocation_outcome_request() is not None and isinstance(
            target, (ast.Tuple, ast.List)
        )

        def evaluate_leaf(leaf: ast.expr, _binding: _ResolvedBinding) -> None | Literal[False]:
            if self._visit_object_namespace_target_expressions(leaf) is False:
                return False
            self._record_object_namespace_target(leaf)
            return None

        def bind_pair_child(leaf: ast.expr, binding: _ResolvedBinding) -> bool | None:
            result = self._bind_target_value(
                leaf,
                iterable,
                dynamic_unknown_string=False,
                captured_binding=binding,
                target_evaluator=evaluate_leaf if requested_structural else None,
            )
            return None if result is False else True

        if not requested_structural:
            if (
                self._visit_object_namespace_target_expressions(target) is False
                and self._invocation_outcome_request() is not None
            ):
                return False
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
                for child, binding in (
                    (
                        target.elts[0],
                        _ResolvedBinding(_KNOWN_NON_APP_REFERENCE, _DYNAMIC_STRING_BINDING),
                    ),
                    (target.elts[1], value_binding),
                ):
                    if bind_pair_child(child, binding) is None:
                        return False
                return None
        iterable_element = self._resolve_iterable_element_binding(iterable)
        if (
            iterable_element is not None
            and isinstance(target, (ast.Tuple, ast.List))
            and not isinstance(iterable, (ast.List, ast.Tuple, ast.Set))
        ):
            return self._bind_target_value(
                target,
                iterable,
                dynamic_unknown_string=False,
                captured_binding=iterable_element,
                target_evaluator=evaluate_leaf if requested_structural else None,
            )
        if iterable_element is not None:
            pair_bound = self._bind_indexed_pair_target(
                target, iterable_element, child_binder=bind_pair_child
            )
            if pair_bound is None:
                return False
            if pair_bound:
                return None
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
                ordered_items=iterable_element.ordered_items,
                call_receivers=iterable_element.call_receivers,
            )
            return None
        iterable_reference = self._resolve_reference(iterable)
        if iterable_reference in {
            _ITERABLE_APP_ELEMENT_REFERENCE,
            _ITERABLE_SENSITIVE_ELEMENT_REFERENCE,
            _POSSIBLE_APP_CALL_REFERENCE,
        }:
            if requested_structural:
                if self._visit_object_namespace_target_expressions(target) is False:
                    return False
                self._record_object_namespace_target(target)
            self._bind_targets(
                [target],
                reference=(
                    _POSSIBLE_APP_REFERENCE
                    if iterable_reference == _ITERABLE_APP_ELEMENT_REFERENCE
                    else _POSSIBLE_APP_CALL_REFERENCE
                ),
                string=(
                    _DYNAMIC_STRING_BINDING
                    if iterable_reference == _POSSIBLE_APP_CALL_REFERENCE
                    else None
                ),
            )
            return None
        literal_values = (
            iterable.elts if isinstance(iterable, (ast.List, ast.Tuple, ast.Set)) else None
        )
        if not literal_values:
            if requested_structural:
                if self._visit_object_namespace_target_expressions(target) is False:
                    return False
                self._record_object_namespace_target(target)
            for name in _assignment_target_names(target):
                self._bind_name(
                    name,
                    reference=self._possible_sensitive_reference(name),
                    string=None,
                )
            return None
        incoming = self.scope
        outcomes: list[_LexicalBindings] = []
        for value in literal_values:
            self._switch_deferred_scope(incoming.clone(), restore_flow=True)
            item_value = value.value if isinstance(value, ast.Starred) else value
            if isinstance(target, (ast.Tuple, ast.List)):
                bound = self._bind_target_value(
                    target,
                    item_value,
                    dynamic_unknown_string=False,
                    captured_binding=self._capture_argument_binding(item_value),
                    target_evaluator=evaluate_leaf if requested_structural else None,
                )
            else:
                bound = self._bind_target_value(target, item_value, dynamic_unknown_string=False)
            if bound is False and self._invocation_outcome_request() is not None:
                return False
            outcomes.append(self.scope)
        merged = incoming.clone()
        self._merge_outcomes(merged, outcomes)
        return None

    def _type_parameter_scope(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef | ast.TypeAlias,
    ) -> _LexicalBindings:
        type_parameters = getattr(node, "type_params", ())
        if not type_parameters:
            return self.scope
        parameter_scope = _LexicalBindings(
            parent=self.scope,
            local_names=frozenset(parameter.name for parameter in type_parameters),
            scope_kind="type_parameters",
        )
        if self._analysis_purpose == "ownership_audit":
            for parameter in type_parameters:
                for expression in (
                    getattr(parameter, "bound", None),
                    getattr(parameter, "default_value", None),
                ):
                    if expression is None:
                        continue
                    visitor = self._detached_analysis_visitor(
                        parameter_scope,
                        original_parent=parameter_scope,
                        analyze_function_bodies=self.analyze_function_bodies,
                    )
                    visitor.reference_snapshots = self.reference_snapshots
                    visitor.string_snapshots = self.string_snapshots
                    visitor.call_result_snapshots = self.call_result_snapshots
                    visitor._remaining_loop_iterations = self._remaining_loop_iterations
                    try:
                        visitor.visit(expression)
                        self.errors.extend(visitor.errors)
                    finally:
                        self._remaining_loop_iterations = visitor._remaining_loop_iterations
        return parameter_scope

    def visit_TypeAlias(self, node: ast.TypeAlias) -> None:
        self.visit(node.name)
        self._bind_name(node.name.id, reference=None, string=None)
        parameter_scope = self._type_parameter_scope(node)
        if self._analysis_purpose != "ownership_audit":
            return
        visitor = self._detached_analysis_visitor(
            parameter_scope,
            original_parent=parameter_scope,
            analyze_function_bodies=self.analyze_function_bodies,
        )
        visitor.reference_snapshots = self.reference_snapshots
        visitor.string_snapshots = self.string_snapshots
        visitor.call_result_snapshots = self.call_result_snapshots
        visitor._remaining_loop_iterations = self._remaining_loop_iterations
        try:
            visitor.visit(node.value)
            self.errors.extend(visitor.errors)
        finally:
            self._remaining_loop_iterations = visitor._remaining_loop_iterations

    def _visit_function_header(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> _LexicalBindings | Literal[False]:
        decorator_bindings: list[frozenset[_FunctionNode]] = []
        for decorator in node.decorator_list:
            if self.visit(decorator) is False and self._invocation_outcome_request() is not None:
                return False
            decorator_bindings.append(self._resolve_callables(decorator))
        self._function_decorator_bindings[node] = tuple(decorator_bindings)
        for default in (*node.args.defaults, *node.args.kw_defaults):
            if default is not None:
                if self.visit(default) is False and self._invocation_outcome_request() is not None:
                    return False
        previous = self.scope
        parameter_scope = self._type_parameter_scope(node)
        self._switch_deferred_scope(parameter_scope, restore_flow=False)
        try:
            for argument in _iter_function_parameters(node.args):
                if argument.annotation is not None and not self._postponed_annotations:
                    if (
                        self.visit(argument.annotation) is False
                        and self._invocation_outcome_request() is not None
                    ):
                        return False
            if node.returns is not None and not self._postponed_annotations:
                if (
                    self.visit(node.returns) is False
                    and self._invocation_outcome_request() is not None
                ):
                    return False
        finally:
            self._switch_deferred_scope(previous, restore_flow=False)
        return parameter_scope

    def _resolve_decorated_function_binding(
        self,
        node: _FunctionNode,
    ) -> _ResolvedBinding | Literal[False]:
        binding = _ResolvedBinding(None, None, frozenset({node}))
        if not self._replay_calls_enabled:
            return binding
        temporary_name = f"<decorated-function:{id(node)}>"
        captured_decorators = self._function_decorator_bindings.get(node, ())
        for decorator, targets in reversed(
            list(zip(node.decorator_list, captured_decorators, strict=True))
        ):
            if not targets:
                if self._invocation_outcome_request() is not None:
                    self._terminal_controls.raise_scopes.append(self.scope.clone())
                continue
            temporary_offsets = (
                [(items, len(items)) for items in self._deferred_abrupt_collectors()]
                if self._invocation_outcome_request() is not None
                else []
            )
            try:
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
                request = self._invocation_outcome_request()
                offsets = (
                    (len(request.return_scopes), len(request.raise_scopes))
                    if request is not None
                    else None
                )
                entry = self._capture_deferred_flow(self.scope) if request is not None else None
                active = self.scope
                for target in sorted(
                    targets,
                    key=lambda candidate: (
                        candidate.lineno,
                        candidate.col_offset,
                        candidate.name,
                    ),
                ):
                    if request is not None:
                        if entry is None:
                            raise AssertionError
                        self._restore_deferred_flow(entry)
                        self.scope = active
                        normal_offset = len(request.return_scopes)
                    with self._suspend_invocation_outcomes():
                        arguments = self._resolve_call_argument_bindings(target, synthetic_call)
                    if arguments is not None and not isinstance(target, ast.AsyncFunctionDef):
                        result = self._replay_function_call(target, arguments)
                        if request is None or len(request.return_scopes) > normal_offset:
                            results.append(result)
                    elif request is not None:
                        if arguments is None:
                            request.raise_scopes.append(self.scope.clone())
                        else:
                            # A decorator returning a coroutine is a dormant value.
                            results.append(
                                _ResolvedBinding(
                                    _KNOWN_NON_APP_REFERENCE,
                                    None,
                                    deferred_calls=frozenset(
                                        {
                                            _DeferredFunctionCall(
                                                function=target,
                                                arguments=tuple(sorted(arguments.items())),
                                                execution="await",
                                            )
                                        }
                                    ),
                                )
                            )
                            request.return_scopes.append(self.scope.clone())
                if request is not None:
                    if offsets is None:
                        raise AssertionError
                    if not self._resume_invocation_outcomes(request, offsets):
                        self.scope.unbind(temporary_name)
                        return False
                self.scope.bind(temporary_name, reference=None, string=None)
                binding = self._join_resolved_bindings(results)
            finally:
                if self._invocation_outcome_request() is not None:
                    self._discard_invocation_temporary(temporary_name, temporary_offsets)
        return binding

    def _detached_analysis_visitor(
        self,
        parent: _LexicalBindings,
        *,
        original_parent: _LexicalBindings,
        analyze_function_bodies: bool,
    ) -> _ApiKeyLookupVisitor:
        parameter_scopes: list[_LexicalBindings] = []
        while parent.scope_kind == "type_parameters" and parent.parent is not None:
            parameter_scopes.append(parent)
            parent = parent.parent
        if parent.scope_kind == "module" and (
            self.module_late_references or self.module_late_strings
        ):
            final_parent = parent.clone()
            final_parent.references = dict(self.module_late_references)
            final_parent.strings = dict(self.module_late_strings)
            late_parent = parent.clone()
            active_scope = self.scope
            self._merge_outcomes(late_parent, [parent.clone(), final_parent], flow_join=False)
            self._switch_deferred_scope(active_scope, restore_flow=False)
            parent = late_parent
        elif parent.scope_kind == "function" and self._function_late_bindings:
            late_references, late_strings, late_callables = self._function_late_bindings[-1]
            final_parent = parent.clone()
            final_parent.references = dict(late_references)
            final_parent.strings = dict(late_strings)
            final_parent.callables = dict(late_callables)
            late_parent = parent.clone()
            active_scope = self.scope
            self._merge_outcomes(late_parent, [parent.clone(), final_parent], flow_join=False)
            self._switch_deferred_scope(active_scope, restore_flow=False)
            parent = late_parent
        for parameter_scope in reversed(parameter_scopes):
            projected_scope = parameter_scope.clone()
            projected_scope.parent = parent
            parent = projected_scope
        visitor = _ApiKeyLookupVisitor(
            filename=self.filename,
            errors=[],
            preserve_fastapi_conflicts=self.preserve_fastapi_conflicts,
            preserve_lifecycle_conflicts=self.preserve_lifecycle_conflicts,
            preserve_route_method_conflicts=self.preserve_route_method_conflicts,
            analyze_function_bodies=analyze_function_bodies,
            ownership_family=self.ownership_family,
            purpose=self._analysis_purpose,
            expression_snapshots_only=self._expression_snapshots_only,
        )
        # A short-lived graph-copy memo preserves genuine owner relationships only.
        # It is not an evaluation/result cache and is discarded after detachment.
        memo: dict[_LexicalBindings, _LexicalBindings] = {}
        visitor.scope = parent.detached_clone(memo)
        memo[original_parent] = visitor.scope
        original_scope = original_parent
        detached_scope = visitor.scope
        while (
            original_scope.scope_kind == "type_parameters"
            and original_scope.parent is not None
            and detached_scope.parent is not None
        ):
            original_scope = original_scope.parent
            detached_scope = detached_scope.parent
            memo[original_scope] = detached_scope
        visitor._function_definition_scopes = {
            node: scope.detached_clone(memo)
            for node, scope in self._function_definition_scopes.items()
        }
        visitor._deferred_generator_scopes = {
            node: scope.detached_clone(memo)
            for node, scope in self._deferred_generator_scopes.items()
        }
        visitor._function_default_bindings = dict(self._function_default_bindings)
        visitor._function_decorator_bindings = dict(self._function_decorator_bindings)
        visitor._function_binding_nodes = dict(self._function_binding_nodes)
        visitor._deferred_generator_expressions = dict(self._deferred_generator_expressions)
        visitor._deferred_generator_outer_bindings = dict(self._deferred_generator_outer_bindings)
        visitor._lambda_function_bindings = dict(self._lambda_function_bindings)
        visitor._class_member_callables = dict(self._class_member_callables)
        visitor._class_member_descriptors = dict(self._class_member_descriptors)
        visitor._class_member_presence = dict(self._class_member_presence)
        visitor._class_direct_member_callables = dict(self._class_direct_member_callables)
        visitor._class_direct_member_descriptors = dict(self._class_direct_member_descriptors)
        visitor._class_direct_member_presence = dict(self._class_direct_member_presence)
        visitor._class_direct_member_noncallable = dict(self._class_direct_member_noncallable)
        visitor._class_mros = dict(self._class_mros)
        visitor._class_mro_complete = dict(self._class_mro_complete)
        visitor._mapping_invalidation_counts = dict(self._mapping_invalidation_counts)
        visitor._mapping_last_clear_counts = dict(self._mapping_last_clear_counts)
        visitor._outward_binding_targets = [
            {name: scope.detached_clone(memo) for name, scope in targets.items()}
            for targets in self._outward_binding_targets
        ]
        visitor._active_function_replays = set(self._active_function_replays)
        visitor._active_replay_contexts = [
            (
                (
                    *context[:4],
                    (
                        ()
                        if self._private_deferred_corridor_operand(
                            None, return_source=True, owner_frame=context, owner_kind=True
                        )
                        else context[4]
                    ),
                    *context[5:8],
                    None,
                )
                if isinstance(context, tuple) and len(context) in {8, 9}
                else context
            )
            for context in self._active_replay_contexts
        ]
        visitor._consumed_deferred_calls = set(self._consumed_deferred_calls)
        visitor._call_result_bindings = dict(self._call_result_bindings)
        visitor._deferred_call_bindings = dict(self._deferred_call_bindings)
        visitor.scope._flow_owner = visitor
        visitor._function_late_bindings = list(self._function_late_bindings)
        visitor._definition_time_function_scans = set(self._definition_time_function_scans)
        visitor._postponed_annotations = self._postponed_annotations
        visitor._replay_calls_enabled = self._replay_calls_enabled
        visitor._sync_only_body_analysis = self._sync_only_body_analysis
        visitor._snapshot_collection = self._snapshot_collection
        visitor._snapshot_analysis_replaying = self._snapshot_analysis_replaying
        return visitor

    def _enter_function_binding_scope(
        self,
        node: _FunctionNode,
        lexical_parent: _LexicalBindings,
        arguments: Mapping[str, _ResolvedBinding],
    ) -> dict[str, _LexicalBindings]:
        global_names, nonlocal_names = _function_outward_binding_names(node)
        targets = self._resolve_outward_binding_targets(
            global_names, nonlocal_names, lexical_parent
        )
        sources = {
            name: self._outward_binding_source(name, target) for name, target in targets.items()
        }
        self._switch_deferred_scope(
            _LexicalBindings(
                parent=lexical_parent,
                local_names=(
                    _function_local_binding_names(
                        node, postponed_annotations=self._postponed_annotations
                    )
                    | global_names
                    | nonlocal_names
                ),
                scope_kind="function",
            ),
            restore_flow=False,
        )
        for name, source in sources.items():
            self._transfer_outward_binding_state(name, source, self.scope)
        for name, binding in arguments.items():
            self._bind_resolved_name(name, binding)
        return targets

    def _visit_function(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> None | Literal[False]:
        header_scope = self._visit_function_header(node)
        if header_scope is False:
            return False
        definition_scope = header_scope.function_parent()
        binding_node: _FunctionNode = node
        if (
            self.scope.scope_kind != "module" or definition_scope is not self.scope
        ) and self._replay_calls_enabled:
            replay_context = self._current_replay_context()
            binding_key = (node, replay_context)
            binding_node = self._function_binding_nodes.get(binding_key, node)
            if binding_node is node:
                binding_node = copy.copy(node)
                self._function_binding_nodes[binding_key] = binding_node
            self._function_definition_scopes[binding_node] = definition_scope
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
            self._function_decorator_bindings[binding_node] = self._function_decorator_bindings[
                node
            ]
        decorated_binding = self._resolve_decorated_function_binding(binding_node)
        if decorated_binding is False:
            return False
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
            return None
        lexical_parent = definition_scope
        original_parent = lexical_parent
        definition_time_scan = node in self._definition_time_function_scans
        body_replay_enabled = self._replay_calls_enabled and (
            definition_time_scan
            or (
                self._analysis_purpose == "ownership_audit"
                and not isinstance(node, ast.AsyncFunctionDef)
                and not _function_is_generator(node)
            )
        )
        body_sync_only = self._sync_only_body_analysis or not definition_time_scan
        initial_arguments = default_bindings if definition_time_scan else {}
        if (
            not definition_time_scan
            and body_replay_enabled
            and self._analysis_purpose == "ownership_audit"
            and self.ownership_family == "api_key"
        ):
            # This existing detached synchronous API audit has no actual call
            # arguments. Parameters may select protected names; it does not
            # execute a dormant coroutine or generator.
            initial_arguments = {
                parameter.arg: _ResolvedBinding(None, _DYNAMIC_STRING_BINDING)
                for parameter in _iter_function_parameters(node.args)
            }
        summary_visitor = self._detached_analysis_visitor(
            lexical_parent,
            original_parent=original_parent,
            analyze_function_bodies=False,
        )
        summary_targets = summary_visitor._enter_function_binding_scope(
            node, summary_visitor.scope, initial_arguments
        )
        summary_visitor._outward_binding_targets.append(summary_targets)
        summary_phase = (
            summary_visitor._replay_calls_enabled,
            summary_visitor._sync_only_body_analysis,
        )
        summary_visitor._replay_calls_enabled = body_replay_enabled
        summary_visitor._sync_only_body_analysis = body_sync_only
        try:
            summary_visitor._visit_statements(node.body)
        finally:
            (
                summary_visitor._replay_calls_enabled,
                summary_visitor._sync_only_body_analysis,
            ) = summary_phase
            summary_visitor._outward_binding_targets.pop()
        function_late_bindings = (
            dict(summary_visitor.scope.references),
            dict(summary_visitor.scope.strings),
            dict(summary_visitor.scope.callables),
        )
        analysis_visitor = self._detached_analysis_visitor(
            lexical_parent,
            original_parent=original_parent,
            analyze_function_bodies=True,
        )
        analysis_visitor.reference_snapshots = self.reference_snapshots
        analysis_visitor.string_snapshots = self.string_snapshots
        analysis_visitor.call_result_snapshots = self.call_result_snapshots
        analysis_visitor._remaining_loop_iterations = self._remaining_loop_iterations
        analysis_targets = analysis_visitor._enter_function_binding_scope(
            node, analysis_visitor.scope, initial_arguments
        )
        analysis_visitor._outward_binding_targets.append(analysis_targets)
        analysis_visitor._function_late_bindings.append(function_late_bindings)
        analysis_phase = (
            analysis_visitor._replay_calls_enabled,
            analysis_visitor._sync_only_body_analysis,
        )
        analysis_visitor._replay_calls_enabled = body_replay_enabled
        analysis_visitor._sync_only_body_analysis = body_sync_only
        if definition_time_scan:
            analysis_visitor._iterated_call_ids.update(
                id(candidate)
                for candidate in ast.walk(node)
                if isinstance(candidate, ast.GeneratorExp)
            )
        try:
            analysis_visitor._visit_statements(node.body)
            self.errors.extend(analysis_visitor.errors)
        finally:
            (
                analysis_visitor._replay_calls_enabled,
                analysis_visitor._sync_only_body_analysis,
            ) = analysis_phase
            self._remaining_loop_iterations = analysis_visitor._remaining_loop_iterations
            analysis_visitor._function_late_bindings.pop()
            analysis_visitor._outward_binding_targets.pop()
        return None

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None | Literal[False]:
        if self._visit_function(node) is False and self._invocation_outcome_request() is not None:
            return False
        return None

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None | Literal[False]:
        if self._visit_function(node) is False and self._invocation_outcome_request() is not None:
            return False
        return None

    def visit_Lambda(self, node: ast.Lambda) -> None | Literal[False]:
        if not self.analyze_function_bodies:
            for default in (*node.args.defaults, *node.args.kw_defaults):
                if default is not None:
                    if (
                        self.visit(default) is False
                        and self._invocation_outcome_request() is not None
                    ):
                        return False
            return None
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
            if (
                self._visit_function(synthetic) is False
                and self._invocation_outcome_request() is not None
            ):
                return False
        finally:
            self._definition_time_function_scans.remove(synthetic)
        return None

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

    def _active_outward_targets_for_scope(
        self, scope: _LexicalBindings
    ) -> Mapping[str, _LexicalBindings]:
        active_scope: _LexicalBindings | None = self.scope
        for targets in reversed(self._outward_binding_targets):
            while active_scope is not None and active_scope.scope_kind not in {"function", "class"}:
                active_scope = active_scope.parent
            if active_scope is None:
                break
            if active_scope is scope:
                return targets
            active_scope = active_scope.parent
        return {}

    def _resolve_outward_binding_targets(
        self,
        global_names: AbstractSet[str],
        nonlocal_names: AbstractSet[str],
        lexical_parent: _LexicalBindings,
    ) -> dict[str, _LexicalBindings]:
        targets = {name: self._module_scope() for name in global_names}
        for name in nonlocal_names:
            owner: _LexicalBindings | None = lexical_parent
            while owner is not None:
                if owner.scope_kind == "function" and name in owner.local_names:
                    redirect = self._active_outward_targets_for_scope(owner).get(name)
                    if redirect is not None and redirect is not owner:
                        if redirect.scope_kind == "function":
                            targets[name] = redirect
                            break
                    else:
                        targets[name] = owner
                        break
                owner = owner.parent
            if name not in targets:
                raise LegacyGrowthAnalysisError(
                    f"{self.filename}: nonlocal binding owner is unavailable: {name}"
                )
        return targets

    @staticmethod
    def _transfer_outward_binding_state(
        name: str, source: _LexicalBindings, target: _LexicalBindings
    ) -> None:
        if name not in source.possibly_bound_names:
            target.unbind(name)
            return
        target.bind(
            name,
            reference=source.references.get(name),
            string=source.strings.get(name),
            callables=source.callables.get(name, frozenset()),
            deferred_calls=source.deferred_calls.get(name, frozenset()),
            mapping=source.mappings.get(name),
            class_references=source.class_references.get(name, frozenset()),
            descriptors=source.descriptors.get(name, frozenset()),
            iterable_element=source.iterable_elements.get(name),
            ordered_items=source.ordered_items.get(name),
            call_receivers=source.call_receivers.get(name, frozenset()),
            runtime_binding=False,
        )
        target.bound_names.discard(name)
        if name in source.bound_names:
            target.bound_names.add(name)
        target.possibly_bound_names.add(name)

    def _outward_binding_source(self, name: str, target: _LexicalBindings) -> _LexicalBindings:
        active_scope: _LexicalBindings | None = self.scope
        while active_scope is not None:
            if self._active_outward_targets_for_scope(active_scope).get(name) is target:
                return active_scope
            active_scope = active_scope.parent
        return target

    def _transfer_outward_bindings(
        self,
        source: _LexicalBindings,
        targets: Mapping[str, _LexicalBindings],
        parent_scope: _LexicalBindings,
        *,
        resolve_declared_source: bool = False,
    ) -> None:
        for name, target in targets.items():
            # A saved outcome may be rooted at a comprehension wrapper. Its
            # own missing/shadowing field is not the declaring owner's state.
            declaring_source = (
                self._outward_binding_source(name, target) if resolve_declared_source else source
            )
            self._transfer_outward_binding_state(name, declaring_source, target)
            active_scope: _LexicalBindings | None = parent_scope
            while active_scope is not None:
                if self._active_outward_targets_for_scope(active_scope).get(name) is target:
                    self._transfer_outward_binding_state(name, declaring_source, active_scope)
                active_scope = active_scope.parent

    def visit_ClassDef(self, node: ast.ClassDef) -> None | Literal[False]:
        decorator_targets: list[frozenset[_FunctionNode]] = []
        for decorator in node.decorator_list:
            if self.visit(decorator) is False and self._invocation_outcome_request() is not None:
                return False
            decorator_targets.append(self._resolve_callables(decorator))
        previous = self.scope
        try:
            self._switch_deferred_scope(self._type_parameter_scope(node), restore_flow=False)
            base_references: list[str] = []
            bases_complete = True
            for base in node.bases:
                if self.visit(base) is False and self._invocation_outcome_request() is not None:
                    return False
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
                if (
                    self.visit(keyword.value) is False
                    and self._invocation_outcome_request() is not None
                ):
                    return False
                if keyword.arg == "metaclass":
                    metaclass_targets = self._resolve_callables(keyword.value)
            lexical_parent = self.scope
            class_request = self._invocation_outcome_request()
            caller_outward_views: list[tuple[_LexicalBindings, Mapping[str, _LexicalBindings]]] = []
            if class_request is not None:
                view: _LexicalBindings | None = self.scope
                while view is not None:
                    declared_targets = self._active_outward_targets_for_scope(view)
                    if declared_targets:
                        caller_outward_views.append((view, dict(declared_targets)))
                    view = view.parent
                for _view, declared_targets in caller_outward_views:
                    for name, declared_owner in declared_targets.items():
                        self._transfer_outward_binding_state(
                            name, self._outward_binding_source(name, declared_owner), declared_owner
                        )
                for view, declared_targets in caller_outward_views:
                    for name, declared_owner in declared_targets.items():
                        self._transfer_outward_binding_state(name, declared_owner, view)
            caller_entry = (
                self._capture_deferred_flow(previous) if class_request is not None else None
            )
            global_names, nonlocal_names = _statement_outward_binding_names(node.body)
            outward_names = global_names | nonlocal_names
            outward_targets = self._resolve_outward_binding_targets(
                global_names, nonlocal_names, lexical_parent
            )
            class_scope = _LexicalBindings(
                parent=lexical_parent, local_names=outward_names, scope_kind="class"
            )
            for name, binding_owner in outward_targets.items():
                self._transfer_outward_binding_state(
                    name, self._outward_binding_source(name, binding_owner), class_scope
                )
            self._switch_deferred_scope(class_scope, restore_flow=False)
            self._outward_binding_targets.append(outward_targets)
            class_raise_offset = len(self._terminal_controls.raise_scopes)
            try:
                class_falls_through = self._visit_statements(node.body)
                class_scope = self.scope
                current_member_names = class_scope.possibly_bound_names - outward_names
                for member_name, mapping in tuple(class_scope.mappings.items()):
                    if (
                        member_name in current_member_names
                        and class_scope.mappings.get(member_name) is mapping
                    ):
                        self._invalidate_mapping(mapping)
                self._transfer_outward_bindings(class_scope, outward_targets, previous)
                if class_request is not None:
                    if caller_entry is None:
                        raise AssertionError
                    for view, declared_targets in caller_outward_views:
                        for name, declared_owner in declared_targets.items():
                            self._transfer_outward_binding_state(name, declared_owner, view)
                    completed_entry = self._capture_deferred_flow(self.scope)
                    projected_raises = [
                        self._project_invocation_scope(
                            outcome,
                            previous,
                            caller_entry,
                            outward_targets=outward_targets,
                            caller_outward_views=caller_outward_views,
                        )
                        for outcome in self._terminal_controls.raise_scopes[class_raise_offset:]
                    ]
                    self._terminal_controls.raise_scopes[class_raise_offset:] = projected_raises
                    self._restore_deferred_flow(completed_entry)
                    self.scope = class_scope
            finally:
                self._outward_binding_targets.pop()
                self._switch_deferred_scope(previous, restore_flow=False)
            if not class_falls_through and self._invocation_outcome_request() is not None:
                return False
            result_binding = _ResolvedBinding(None, None)
            if metaclass_targets:
                metaclass_call = ast.Call(
                    func=ast.Name(id="<metaclass>", ctx=ast.Load()),
                    args=[
                        ast.Constant(node.name),
                        ast.Tuple(elts=[]),
                        ast.Dict(keys=[], values=[]),
                    ],
                    keywords=[],
                )
                metaclass_results: list[_ResolvedBinding] = []
                request = self._invocation_outcome_request()
                offsets = (
                    (len(request.return_scopes), len(request.raise_scopes))
                    if request is not None
                    else None
                )
                entry = self._capture_deferred_flow(self.scope) if request is not None else None
                active = self.scope
                for target in metaclass_targets:
                    if request is not None:
                        if entry is None:
                            raise AssertionError
                        self._restore_deferred_flow(entry)
                        self.scope = active
                        normal_offset = len(request.return_scopes)
                    with self._suspend_invocation_outcomes():
                        arguments = self._resolve_call_argument_bindings(target, metaclass_call)
                    if arguments is not None:
                        result = self._replay_function_call(target, arguments)
                        if request is None or len(request.return_scopes) > normal_offset:
                            metaclass_results.append(result)
                    elif request is not None:
                        request.raise_scopes.append(self.scope.clone())
                if request is not None:
                    if offsets is None:
                        raise AssertionError
                    if not self._resume_invocation_outcomes(request, offsets):
                        return False
                result_binding = self._join_resolved_bindings(metaclass_results)
            for decorator, targets in reversed(
                list(zip(node.decorator_list, decorator_targets, strict=True))
            ):
                if not targets:
                    if self._invocation_outcome_request() is not None:
                        self._terminal_controls.raise_scopes.append(self.scope.clone())
                    continue
                temporary_name = f"<decorated-class:{id(node)}>"
                temporary_offsets = (
                    [(items, len(items)) for items in self._deferred_abrupt_collectors()]
                    if self._invocation_outcome_request() is not None
                    else []
                )
                try:
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
                    request = self._invocation_outcome_request()
                    offsets = (
                        (len(request.return_scopes), len(request.raise_scopes))
                        if request is not None
                        else None
                    )
                    entry = self._capture_deferred_flow(self.scope) if request is not None else None
                    active = self.scope
                    for target in targets:
                        if request is not None:
                            if entry is None:
                                raise AssertionError
                            self._restore_deferred_flow(entry)
                            self.scope = active
                            normal_offset = len(request.return_scopes)
                        with self._suspend_invocation_outcomes():
                            arguments = self._resolve_call_argument_bindings(target, decorator_call)
                        if arguments is not None:
                            result = self._replay_function_call(target, arguments)
                            if request is None or len(request.return_scopes) > normal_offset:
                                decorator_results.append(result)
                        elif request is not None:
                            request.raise_scopes.append(self.scope.clone())
                    if request is not None:
                        if offsets is None:
                            raise AssertionError
                        if not self._resume_invocation_outcomes(request, offsets):
                            return False
                    result_binding = self._join_resolved_bindings(decorator_results)
                    self.scope.bind(temporary_name, reference=None, string=None)
                finally:
                    if self._invocation_outcome_request() is not None:
                        self._discard_invocation_temporary(temporary_name, temporary_offsets)
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
                        prior_noncallable
                        and current_noncallable
                        and not callables
                        and current_present
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
        finally:
            self._switch_deferred_scope(previous, restore_flow=False)
        return None

    def visit_Assert(self, node: ast.Assert) -> None | Literal[False]:
        if self._invocation_outcome_request() is None:
            super().generic_visit(node)
            return None
        if self.visit(node.test) is False:
            return False
        truth = bool(node.test.value) if isinstance(node.test, ast.Constant) else None
        if truth is True:
            return None
        normal = self.scope.clone() if truth is None else None
        if node.msg is not None and self.visit(node.msg) is False:
            if normal is None:
                return False
            self._switch_deferred_scope(normal, restore_flow=True)
            return None
        self._terminal_controls.raise_scopes.append(self.scope.clone())
        if normal is None:
            return False
        self._switch_deferred_scope(normal, restore_flow=True)
        return None

    def visit_If(self, node: ast.If) -> bool:
        if self.visit(node.test) is False and self._invocation_outcome_request() is not None:
            return False
        if isinstance(node.test, ast.Constant):
            selected = node.body if bool(node.test.value) else node.orelse
            return self._visit_statements(selected)
        branches: list[Sequence[ast.stmt]] = [node.body]
        branches.append(node.orelse if node.orelse else ())
        return self._visit_branches(branches)

    def visit_IfExp(self, node: ast.IfExp) -> None | Literal[False]:
        if self.visit(node.test) is False and self._invocation_outcome_request() is not None:
            return False
        if isinstance(node.test, ast.Constant):
            if (
                self.visit(node.body if bool(node.test.value) else node.orelse) is False
                and self._invocation_outcome_request() is not None
            ):
                return False
            return None
        incoming = self.scope
        outcomes: list[_LexicalBindings] = []
        for branch in (node.body, node.orelse):
            self._switch_deferred_scope(incoming.clone(), restore_flow=True)
            if self.visit(branch) is False and self._invocation_outcome_request() is not None:
                continue
            outcomes.append(self.scope)
        if not outcomes:
            self._switch_deferred_scope(incoming, restore_flow=True)
            return False
        self._merge_outcomes(incoming, outcomes)
        return None

    def visit_BoolOp(self, node: ast.BoolOp) -> None | Literal[False]:
        incoming = self.scope
        outcomes: list[_LexicalBindings] = []
        for index, value in enumerate(node.values):
            if self.visit(value) is False and self._invocation_outcome_request() is not None:
                break
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
        if not outcomes:
            self._switch_deferred_scope(incoming, restore_flow=True)
            return False
        self._merge_outcomes(incoming, outcomes)
        return None

    def visit_Compare(self, node: ast.Compare) -> None | Literal[False]:
        incoming = self.scope
        outcomes: list[_LexicalBindings] = []
        left = node.left
        if self.visit(left) is False and self._invocation_outcome_request() is not None:
            return False
        for index, (comparison_operator, right) in enumerate(
            zip(node.ops, node.comparators, strict=True)
        ):
            if isinstance(comparison_operator, (ast.In, ast.NotIn)):
                result: object = self._visit_iterated_expression(right)
            else:
                result = self.visit(right)
            if result is False and self._invocation_outcome_request() is not None:
                break
            self.visit(comparison_operator)
            truth: bool | None = None
            if (
                isinstance(left, ast.Constant)
                and isinstance(right, ast.Constant)
                and type(left.value) in {int, float, complex, str, bytes, bool, type(None)}
                and type(right.value) in {int, float, complex, str, bytes, bool, type(None)}
            ):
                try:
                    if isinstance(comparison_operator, ast.Eq):
                        truth = left.value == right.value
                    elif isinstance(comparison_operator, ast.NotEq):
                        truth = left.value != right.value
                    else:
                        comparison = {
                            ast.Lt: operator.lt,
                            ast.LtE: operator.le,
                            ast.Gt: operator.gt,
                            ast.GtE: operator.ge,
                        }.get(type(comparison_operator))
                        if comparison is not None:
                            truth = cast(Callable[[object, object], bool], comparison)(
                                left.value, right.value
                            )
                except TypeError:
                    truth = None
            if truth is not True or index == len(node.ops) - 1:
                outcomes.append(self.scope.clone())
            if truth is False:
                break
            left = right
        if not outcomes:
            self._switch_deferred_scope(incoming, restore_flow=True)
            return False
        self._merge_outcomes(incoming, outcomes)
        return None

    def _visit_try(self, node: ast.Try | ast.TryStar) -> bool:
        requested_handlerless = self._invocation_outcome_request() is not None and not node.handlers
        loop_controls = self._loop_controls[-1] if self._loop_controls else None
        break_offset = len(loop_controls.break_scopes) if loop_controls is not None else 0
        continue_offset = len(loop_controls.continue_scopes) if loop_controls is not None else 0
        terminal_controls = self._terminal_controls
        return_offset = len(terminal_controls.return_scopes)
        raise_offset = len(terminal_controls.raise_scopes)
        incoming = self.scope
        try_scope = incoming.clone()
        self._switch_deferred_scope(try_scope, restore_flow=True)
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
            self._switch_deferred_scope(next_handler_entry.clone(), restore_flow=True)
            self._exception_scope_collectors.append(handler_exception_scopes)
            try:
                if handler.type is not None:
                    self._record_exception_scope()
                    if (
                        self.visit(handler.type) is False
                        and self._invocation_outcome_request() is not None
                    ):
                        continue
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
            self._switch_deferred_scope(try_scope, restore_flow=True)
            else_falls_through, else_exception_scopes = self._visit_with_exception_scopes(
                node.orelse
            )
            if else_falls_through:
                normal_outcomes.append(self.scope)
        if normal_outcomes:
            self._merge_outcomes(incoming, normal_outcomes)
        else:
            self._switch_deferred_scope(incoming, restore_flow=True)
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
        # Legacy diagnostic snapshots describe conservative handler entry;
        # they are not actual requested failures of a handlerless try/finally.
        if not requested_handlerless:
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
                self._switch_deferred_scope(abrupt_scope.clone(), restore_flow=True)
                if self._visit_statements(node.finalbody):
                    finalized_break_scopes.append(self.scope)
            finalized_continue_scopes: list[_LexicalBindings] = []
            for abrupt_scope in abrupt_continue_scopes:
                self._switch_deferred_scope(abrupt_scope.clone(), restore_flow=True)
                if self._visit_statements(node.finalbody):
                    finalized_continue_scopes.append(self.scope)
            loop_controls.break_scopes.extend(finalized_break_scopes)
            loop_controls.continue_scopes.extend(finalized_continue_scopes)
        finalized_return_scopes: list[_LexicalBindings] = []
        for abrupt_scope in abrupt_return_scopes:
            self._switch_deferred_scope(abrupt_scope.clone(), restore_flow=True)
            if self._visit_statements(node.finalbody):
                finalized_return_scopes.append(self.scope)
        finalized_raise_scopes: list[_LexicalBindings] = []
        for abrupt_scope in abrupt_raise_scopes:
            self._switch_deferred_scope(abrupt_scope.clone(), restore_flow=True)
            if self._visit_statements(node.finalbody):
                finalized_raise_scopes.append(self.scope)
        terminal_controls.return_scopes.extend(finalized_return_scopes)
        terminal_controls.raise_scopes.extend(finalized_raise_scopes)
        self._switch_deferred_scope(normal_final_scope, restore_flow=True)
        return normal_falls_through

    def visit_Try(self, node: ast.Try) -> bool:
        return self._visit_try(node)

    def visit_TryStar(self, node: ast.TryStar) -> bool:
        return self._visit_try(node)

    def _prepare_protocol_replay_inputs(
        self,
        binding: _ResolvedBinding,
        method: Literal[
            "__enter__", "__exit__", "__aenter__", "__aexit__", "__aiter__", "__anext__"
        ],
        positional: Sequence[_ResolvedBinding],
    ) -> list[tuple[_FunctionNode, dict[str, _ResolvedBinding]]] | None:
        if (
            method
            not in {"__enter__", "__exit__", "__aenter__", "__aexit__", "__aiter__", "__anext__"}
            or not self._replay_calls_enabled
            or (method not in {"__enter__", "__exit__"} and self._active_async_replay_depth == 0)
        ):
            return []
        instance_reference = binding.reference or ""
        if not instance_reference.startswith(_INSTANCE_REFERENCE_PREFIX):
            return []
        class_reference = instance_reference.replace(
            _INSTANCE_REFERENCE_PREFIX, _CLASS_REFERENCE_PREFIX, 1
        )
        known_callable = False
        if self._class_mro_complete.get(class_reference, False):
            for owner in self._class_mros[class_reference]:
                presence = self._class_direct_member_presence.get((owner, method))
                if presence is None:
                    continue
                if presence:
                    if self._class_direct_member_noncallable.get((owner, method), False):
                        return None
                    known_callable = bool(self._class_direct_member_callables.get((owner, method)))
                # A possible nearer override or an unresolved value stays unknown.
                break
            else:
                return None
        temporary_name = f"<async-protocol:{id(binding)}:{method}>"
        self.scope.bind(
            temporary_name,
            reference=binding.reference,
            string=binding.string,
            class_references=binding.class_references,
        )
        method_expr = ast.Attribute(
            value=ast.Name(id=temporary_name, ctx=ast.Load()), attr=method, ctx=ast.Load()
        )
        method_call = ast.Call(func=method_expr, args=[], keywords=[])
        replay_inputs: list[tuple[_FunctionNode, dict[str, _ResolvedBinding]]] = []
        try:
            owner_references = self._resolve_object_references(method_expr.value)
            for target in sorted(
                self._resolve_callables(method_expr),
                key=lambda candidate: (candidate.lineno, candidate.col_offset, candidate.name),
            ):
                if method not in {"__enter__", "__exit__"} and (
                    _function_is_generator(target)
                    or method == "__aiter__"
                    and isinstance(target, ast.AsyncFunctionDef)
                ):
                    continue
                original_kinds = {
                    kind
                    for owner in owner_references
                    for candidate, kind in self._class_member_descriptors.get((owner, method), ())
                    if candidate is target
                }
                receivers = []
                if "classmethod" in original_kinds:
                    class_references = {
                        owner.replace(_INSTANCE_REFERENCE_PREFIX, _CLASS_REFERENCE_PREFIX, 1)
                        for owner in owner_references
                        if owner.startswith((_INSTANCE_REFERENCE_PREFIX, _CLASS_REFERENCE_PREFIX))
                    }
                    receivers.append(
                        _ResolvedBinding(
                            next(iter(class_references)) if len(class_references) == 1 else None,
                            None,
                            class_references=frozenset(class_references),
                        )
                    )
                if original_kinds - {"classmethod"} or not original_kinds:
                    receivers.append(binding)
                with self._suspend_invocation_outcomes():
                    arguments = self._resolve_call_argument_bindings(
                        target,
                        method_call,
                        positional_override=positional,
                        receiver_override=self._join_resolved_bindings(receivers),
                    )
                if arguments is not None:
                    replay_inputs.append((target, arguments))
        finally:
            self.scope.unbind(temporary_name)
        return replay_inputs if replay_inputs or not known_callable else None

    def _visit_for(self, node: ast.For | ast.AsyncFor) -> bool:
        if self._visit_iterated_expression(node.iter) is False:
            return False
        async_item_binding: _ResolvedBinding | None = None
        next_inputs: list[tuple[_FunctionNode, dict[str, _ResolvedBinding]]] = []
        if (
            isinstance(node, ast.AsyncFor)
            and self._replay_calls_enabled
            and self._active_async_replay_depth > 0
        ):
            source_binding = self._capture_argument_binding(node.iter)
            iterator_inputs = self._prepare_protocol_replay_inputs(source_binding, "__aiter__", [])
            if iterator_inputs is None:
                self._terminal_controls.raise_scopes.append(self.scope.clone())
                return False
            factory_request = self._invocation_outcome_request()
            factory_offsets = (
                (len(factory_request.return_scopes), len(factory_request.raise_scopes))
                if factory_request is not None
                else None
            )
            factory_scope = self.scope
            factory_entry = (
                self._capture_deferred_flow(factory_scope) if factory_request is not None else None
            )
            iterator_results: list[_ResolvedBinding] = []
            for target, arguments in iterator_inputs:
                if factory_request is not None:
                    if factory_entry is None:
                        raise AssertionError
                    self._restore_deferred_flow(factory_entry)
                    self.scope = factory_scope
                    normal_offset = len(factory_request.return_scopes)
                iterator_result = self._replay_function_call(target, arguments)
                if factory_request is None or len(factory_request.return_scopes) > normal_offset:
                    iterator_results.append(iterator_result)
            if factory_request is not None and iterator_inputs:
                if factory_offsets is None:
                    raise AssertionError
                if not self._resume_invocation_outcomes(factory_request, factory_offsets):
                    return False
            if iterator_results:
                iterator_binding = self._join_resolved_bindings(iterator_results)
                prepared_next = self._prepare_protocol_replay_inputs(
                    iterator_binding, "__anext__", []
                )
                if prepared_next is None or iterator_binding.reference == _KNOWN_NON_APP_REFERENCE:
                    self._terminal_controls.raise_scopes.append(self.scope.clone())
                    return False
                next_inputs = prepared_next
        incoming = self.scope
        ordered_rows = self._resolve_ordered_items(node.iter) if isinstance(node, ast.For) else None
        known_container_rows = ordered_rows is not None and not self._resolve_deferred_calls(
            node.iter
        )
        if (
            isinstance(node, ast.For)
            and isinstance(node.iter, (ast.List, ast.Tuple))
            and not node.iter.elts
        ) or (known_container_rows and not ordered_rows):
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
        ) or (known_container_rows and bool(ordered_rows))
        loop_head = incoming.clone()
        for target_name in {
            *_assignment_target_names(node.target),
            *_statement_binding_names(node.body, postponed_annotations=self._postponed_annotations),
        }:
            loop_head.possibly_bound_names.add(target_name)
        self._switch_deferred_scope(loop_head, restore_flow=False)
        break_scopes: list[_LexicalBindings] = []
        next_exhaustion_scopes: list[_LexicalBindings] = []
        body_scope: _LexicalBindings | None = None
        controls = _LoopControlBindings(break_scopes=[], continue_scopes=[])
        for _iteration in range(_MAX_LOOP_BINDING_ITERATIONS):
            self._consume_loop_iteration()
            self._switch_deferred_scope(loop_head.clone(), restore_flow=True)
            outer_frame = cast(tuple[object, ...], self._active_replay_contexts[-1])
            initial_anchors = tuple(
                target
                for target, _arguments in next_inputs
                if not isinstance(target, ast.AsyncFunctionDef)
                or isinstance(node.target, (ast.Tuple, ast.List))
            )
            private_owner = bool(initial_anchors)
            owner_index = len(self._active_replay_contexts)
            if private_owner:
                entry = self._capture_deferred_flow(self.scope)
                self._active_replay_contexts.append(
                    (
                        outer_frame[0],
                        node,
                        (),
                        (),
                        (),
                        (),
                        entry,
                        outer_frame[7],
                        outer_frame[8],
                    )
                )
            iteration_frame = cast(tuple[object, ...], self._active_replay_contexts[-1])
            private_offsets = [(items, len(items)) for items in self._deferred_abrupt_collectors()]
            private_offsets.append((next_exhaustion_scopes, len(next_exhaustion_scopes)))
            phase_request: _TerminalControlBindings | None = None
            phase_normals: list[_LexicalBindings] = []
            try:
                requested_item = self._invocation_outcome_request() is not None
                if next_inputs:
                    # One request in the existing loop frame describes this actual
                    # next invocation; it is removed before entering the loop body.
                    frame = cast(tuple[object, ...], self._active_replay_contexts[-1])
                    request = _TerminalControlBindings(return_scopes=[], raise_scopes=[])
                    phase_request = request
                    self._active_replay_contexts[-1] = (*frame[:8], request)
                    next_entry_scope = self.scope
                    next_entry = self._capture_deferred_flow(next_entry_scope)
                    next_results: list[_ResolvedBinding] = []
                    completed_next = phase_normals
                    try:
                        for target, arguments in next_inputs:
                            self._restore_deferred_flow(next_entry)
                            self.scope = next_entry_scope
                            offsets = (len(request.return_scopes), len(request.raise_scopes))
                            if private_owner:
                                latest = cast(tuple[object, ...], self._active_replay_contexts[-1])
                                self._active_replay_contexts[-1] = (
                                    *latest[:4],
                                    (
                                        *tuple(
                                            item
                                            for item in cast(tuple[ast.AST, ...], latest[4])
                                            if not isinstance(item, _FunctionNode)
                                        ),
                                        *(
                                            (target,)
                                            if not isinstance(target, ast.AsyncFunctionDef)
                                            or isinstance(node.target, (ast.Tuple, ast.List))
                                            else ()
                                        ),
                                    ),
                                    *latest[5:],
                                )
                            try:
                                next_result = self._execute_deferred_call(
                                    _DeferredFunctionCall(
                                        function=target,
                                        arguments=tuple(sorted(arguments.items())),
                                    )
                                )
                            finally:
                                if private_owner:
                                    latest = cast(
                                        tuple[object, ...], self._active_replay_contexts[-1]
                                    )
                                    self._active_replay_contexts[-1] = (
                                        *latest[:4],
                                        tuple(
                                            item
                                            for item in cast(tuple[ast.AST, ...], latest[4])
                                            if not isinstance(item, _FunctionNode)
                                        ),
                                        *latest[5:],
                                    )
                            self._remember_captured_binding(next_result)
                            normals = request.return_scopes[offsets[0] :]
                            abrupt = request.raise_scopes[offsets[1] :]
                            del request.return_scopes[offsets[0] :]
                            del request.raise_scopes[offsets[1] :]
                            next_exhaustion_scopes.extend(abrupt)
                            self._terminal_controls.raise_scopes.extend(abrupt)
                            if not normals:
                                continue
                            self._merge_outcomes(self.scope, normals)
                            if not isinstance(target, ast.AsyncFunctionDef):
                                if private_owner and isinstance(node.target, (ast.Tuple, ast.List)):
                                    extra_anchors: set[_FunctionNode] = set()
                                    child_sources: set[ast.Call] = set()
                                    for parent in next_result.deferred_calls:
                                        if parent.function is not None:
                                            extra_anchors.add(parent.function)
                                        elif (
                                            parent.operation == "to_thread"
                                            and parent.callee is not None
                                        ):
                                            callee = self._captured_callback_callee(parent.callee)
                                            extra_anchors.update(callee.callables)
                                            extra_anchors.update(
                                                template.function
                                                for template in callee.deferred_calls
                                                if template.partial_template
                                                and template.function is not None
                                            )
                                            if parent.value_key is not None and isinstance(
                                                parent.value_key[1], ast.Call
                                            ):
                                                child_sources.add(parent.value_key[1])
                                    latest = cast(
                                        tuple[object, ...], self._active_replay_contexts[-1]
                                    )
                                    self._active_replay_contexts[-1] = (
                                        *latest[:4],
                                        tuple(
                                            dict.fromkeys(
                                                (
                                                    *cast(tuple[ast.AST, ...], latest[4]),
                                                    *extra_anchors,
                                                    *child_sources,
                                                )
                                            )
                                        ),
                                        *latest[5:],
                                    )
                                offsets = (len(request.return_scopes), len(request.raise_scopes))
                                awaited = self._replay_deferred_calls(
                                    next_result.deferred_calls, execution="await"
                                )
                                if not next_result.deferred_calls:
                                    # A concrete non-awaitable return is an actual
                                    # protocol error; an unknown value retains both.
                                    del request.return_scopes[offsets[0] :]
                                    del request.raise_scopes[offsets[1] :]
                                    if next_result.reference == _KNOWN_NON_APP_REFERENCE:
                                        request.raise_scopes.append(self.scope.clone())
                                    else:
                                        self._unknown_invocation_outcomes(request)
                                normals = request.return_scopes[offsets[0] :]
                                abrupt = request.raise_scopes[offsets[1] :]
                                del request.return_scopes[offsets[0] :]
                                del request.raise_scopes[offsets[1] :]
                                next_exhaustion_scopes.extend(abrupt)
                                self._terminal_controls.raise_scopes.extend(abrupt)
                                if not normals:
                                    continue
                                next_result = awaited or self._conservative_argument_binding()
                                self._remember_captured_binding(next_result)
                            completed_next.extend(normals)
                            next_results.append(next_result)
                        if completed_next:
                            self._merge_outcomes(next_entry_scope, completed_next)
                        else:
                            self._restore_deferred_flow(next_entry)
                            self.scope = next_entry_scope
                    finally:
                        updated_frame = cast(tuple[object, ...], self._active_replay_contexts[-1])
                        self._active_replay_contexts[-1] = (*updated_frame[:8], frame[8])
                    if not next_results:
                        updated_frame = cast(tuple[object, ...], self._active_replay_contexts[-1])
                        self._active_replay_contexts[-1] = (
                            *updated_frame[:2],
                            frame[2],
                            *updated_frame[3:],
                        )
                        break
                    async_item_binding = self._join_resolved_bindings(next_results)
                if private_owner:
                    # Await-result anchors end with that phase. The reached target
                    # consumes the already captured item; it does not own children
                    # merely produced by iteration or by target-owner expressions.
                    latest = cast(tuple[object, ...], self._active_replay_contexts[-1])
                    self._active_replay_contexts[-1] = (
                        *latest[:4],
                        tuple(
                            item
                            for item in cast(tuple[ast.AST, ...], latest[4])
                            if not isinstance(item, _FunctionNode)
                        ),
                        *latest[5:],
                    )
                if async_item_binding is None:
                    if (
                        self._bind_iteration_target(node.target, node.iter) is False
                        and self._invocation_outcome_request() is not None
                    ):
                        return False
                else:
                    item_frame = cast(tuple[object, ...], self._active_replay_contexts[-1])
                    if next_inputs:
                        self._active_replay_contexts[-1] = (*item_frame[:8], request)
                    try:

                        def evaluate_item_leaf(
                            leaf: ast.expr, _binding: _ResolvedBinding
                        ) -> None | Literal[False]:
                            if self._visit_object_namespace_target_expressions(leaf) is False:
                                return False
                            self._record_object_namespace_target(leaf)
                            return None

                        if (
                            self._bind_target_value(
                                node.target,
                                node.iter,
                                dynamic_unknown_string=False,
                                captured_binding=async_item_binding,
                                target_evaluator=evaluate_item_leaf,
                            )
                            is False
                        ):
                            return False
                    finally:
                        latest_frame = cast(tuple[object, ...], self._active_replay_contexts[-1])
                        self._active_replay_contexts[-1] = (
                            *latest_frame[:2],
                            frame[2] if next_inputs else latest_frame[2],
                            *latest_frame[3:8],
                            item_frame[8],
                        )
                if next_inputs or requested_item:
                    latest = cast(tuple[object, ...], self._active_replay_contexts[-1])
                    self._active_replay_contexts[-1] = (
                        *latest[:2],
                        iteration_frame[2],
                        *latest[3:],
                    )
            finally:
                if private_owner:
                    primary_error = sys.exception()
                    try:
                        if len(self._active_replay_contexts) != owner_index + 1:
                            raise LegacyGrowthAnalysisError("protocol private owner lost its frame")
                        latest = cast(tuple[object, ...], self._active_replay_contexts[-1])
                        if latest[1] is not node:
                            raise LegacyGrowthAnalysisError("protocol private owner changed source")
                        if latest[5]:
                            if phase_request is not None:
                                private_offsets.extend(
                                    (
                                        (phase_request.return_scopes, 0),
                                        (phase_request.raise_scopes, 0),
                                    )
                                )
                            private_offsets.append((phase_normals, 0))
                            self._close_private_deferred_frame(latest, private_offsets)
                    except Exception as cleanup_error:
                        if primary_error is None:
                            raise
                        primary_error.add_note(
                            f"protocol private cleanup also failed: {cleanup_error}"
                        )
                    finally:
                        if (
                            len(self._active_replay_contexts) == owner_index + 1
                            and cast(tuple[object, ...], self._active_replay_contexts[-1])[1]
                            is node
                        ):
                            self._active_replay_contexts.pop()
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
            *(
                next_exhaustion_scopes
                if next_inputs
                else [] if definitely_nonempty else [incoming.clone()]
            ),
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
        candidates = self._private_deferred_corridor(node)
        if candidates:
            for index in range(len(self._active_replay_contexts) - 1, -1, -1):
                frame = self._active_replay_contexts[index]
                if (
                    isinstance(frame, tuple)
                    and len(frame) in {8, 9}
                    and self._private_deferred_corridor_operand(
                        node.value, return_source=True, owner_frame=frame
                    )
                ):
                    self._active_replay_contexts[index] = (
                        *frame[:4],
                        tuple(dict.fromkeys((*cast(tuple[ast.AST, ...], frame[4]), *candidates))),
                        *frame[5:],
                    )
                    break
        if node.value is not None:
            if self.visit(node.value) is False and self._invocation_outcome_request() is not None:
                return False
        if self._return_binding_collectors:
            self._return_binding_collectors[-1].append(
                _ResolvedBinding(
                    (
                        _KNOWN_NON_APP_REFERENCE
                        if self._invocation_outcome_request() is not None
                        else None
                    ),
                    None,
                )
                if node.value is None
                else self._capture_argument_binding(node.value)
            )
        self._terminal_controls.return_scopes.append(self.scope.clone())
        return False

    def visit_Raise(self, node: ast.Raise) -> bool:
        if node.exc is not None:
            if self.visit(node.exc) is False and self._invocation_outcome_request() is not None:
                return False
        if node.cause is not None:
            if self.visit(node.cause) is False and self._invocation_outcome_request() is not None:
                return False
        self._terminal_controls.raise_scopes.append(self.scope.clone())
        return False

    def visit_While(self, node: ast.While) -> bool:
        if self.visit(node.test) is False and self._invocation_outcome_request() is not None:
            return False
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
            self._switch_deferred_scope(loop_head.clone(), restore_flow=True)
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
            if self.visit(node.test) is False and self._invocation_outcome_request() is not None:
                break
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
            ordered_items=binding.ordered_items,
            call_receivers=binding.call_receivers,
        )

    def _visit_with(self, node: ast.With | ast.AsyncWith) -> bool:
        asynchronous = isinstance(node, ast.AsyncWith)
        enter_method: Literal["__enter__", "__aenter__"] = (
            "__aenter__" if asynchronous else "__enter__"
        )
        exit_method: Literal["__exit__", "__aexit__"] = "__aexit__" if asynchronous else "__exit__"
        enters_task_group = asynchronous and any(
            isinstance(item.context_expr, ast.Call)
            and self._resolve_reference(item.context_expr.func) == "asyncio.TaskGroup"
            for item in node.items
        )
        captured_exit_inputs: list[
            list[tuple[_FunctionNode, dict[str, _ResolvedBinding]]] | None
        ] = []
        task_group_active = False
        invalid_exit = False
        falls_through = False
        terminal_controls = self._terminal_controls
        control_targets = [
            (terminal_controls.return_scopes, len(terminal_controls.return_scopes)),
            (terminal_controls.raise_scopes, len(terminal_controls.raise_scopes)),
        ]
        if self._loop_controls:
            loop_controls = self._loop_controls[-1]
            control_targets.extend(
                [
                    (loop_controls.break_scopes, len(loop_controls.break_scopes)),
                    (loop_controls.continue_scopes, len(loop_controls.continue_scopes)),
                ]
            )

        finalized_header_raises: list[_LexicalBindings] = []

        def replay_captured_exits() -> bool:
            request = self._invocation_outcome_request()
            if request is not None:
                active = self.scope
                normal = [active.clone()]
                raised: list[_LexicalBindings] = []
                for exit_inputs in reversed(captured_exit_inputs):
                    following_normal: list[_LexicalBindings] = []
                    following_raised: list[_LexicalBindings] = []
                    for prefix, already_raised in [
                        *((scope, False) for scope in normal),
                        *((scope, True) for scope in raised),
                    ]:
                        self._switch_deferred_scope(prefix.clone(), restore_flow=True)
                        entry_scope = self.scope
                        entry = self._capture_deferred_flow(entry_scope)
                        destination = following_raised if already_raised else following_normal
                        if exit_inputs is None:
                            following_raised.append(self.scope.clone())
                            continue
                        if not exit_inputs:
                            # An unresolved exit can return or raise; no suppression
                            # of the incoming abrupt prefix is inferred.
                            destination.append(self.scope.clone())
                            following_raised.append(self.scope.clone())
                            continue
                        for target, arguments in exit_inputs:
                            self._restore_deferred_flow(entry)
                            self.scope = entry_scope
                            offsets = (len(request.return_scopes), len(request.raise_scopes))
                            if not asynchronous and (
                                isinstance(target, ast.AsyncFunctionDef)
                                or _function_is_generator(target)
                            ):
                                destination.append(self.scope.clone())
                                continue
                            exited = self._execute_deferred_call(
                                _DeferredFunctionCall(
                                    function=target, arguments=tuple(sorted(arguments.items()))
                                )
                            )
                            completed = request.return_scopes[offsets[0] :]
                            abrupt = request.raise_scopes[offsets[1] :]
                            del request.return_scopes[offsets[0] :]
                            del request.raise_scopes[offsets[1] :]
                            following_raised.extend(abrupt)
                            if not completed:
                                continue
                            self._merge_outcomes(entry_scope, completed)
                            if asynchronous and not isinstance(target, ast.AsyncFunctionDef):
                                offsets = (len(request.return_scopes), len(request.raise_scopes))
                                self._replay_deferred_calls(
                                    exited.deferred_calls, execution="await"
                                )
                                if not exited.deferred_calls:
                                    del request.return_scopes[offsets[0] :]
                                    del request.raise_scopes[offsets[1] :]
                                    if exited.reference == _KNOWN_NON_APP_REFERENCE:
                                        request.raise_scopes.append(self.scope.clone())
                                    else:
                                        self._unknown_invocation_outcomes(request)
                                completed = request.return_scopes[offsets[0] :]
                                abrupt = request.raise_scopes[offsets[1] :]
                                del request.return_scopes[offsets[0] :]
                                del request.raise_scopes[offsets[1] :]
                                following_raised.extend(abrupt)
                            destination.extend(completed)
                    normal, raised = following_normal, following_raised
                terminal_controls.raise_scopes.extend(raised)
                if normal:
                    self._merge_outcomes(active, normal)
                elif raised:
                    self._merge_outcomes(active, raised)
                else:
                    self._switch_deferred_scope(active, restore_flow=True)
                return not normal
            failed_exit = False
            for exit_inputs in reversed(captured_exit_inputs):
                if exit_inputs is None:
                    failed_exit = True
                    continue
                possible_valid_exit = not exit_inputs
                for target, arguments in exit_inputs:
                    if not asynchronous and (
                        isinstance(target, ast.AsyncFunctionDef) or _function_is_generator(target)
                    ):
                        # The returned deferred object is discarded, never consumed.
                        possible_valid_exit = True
                        continue
                    exited = self._execute_deferred_call(
                        _DeferredFunctionCall(
                            function=target,
                            arguments=tuple(sorted(arguments.items())),
                        )
                    )
                    if asynchronous and not isinstance(target, ast.AsyncFunctionDef):
                        awaited = self._replay_deferred_calls(
                            exited.deferred_calls, execution="await"
                        )
                        if awaited is None and exited.reference == _KNOWN_NON_APP_REFERENCE:
                            terminal_controls.raise_scopes.append(self.scope.clone())
                            continue
                    possible_valid_exit = True
                failed_exit = failed_exit or not possible_valid_exit
            return failed_exit

        def finalize_header_raises(offset: int) -> None:
            # Finalize a header branch before entering a later context. Otherwise
            # a future exit would run for a context not entered on that branch.
            abrupt = terminal_controls.raise_scopes[offset:]
            del terminal_controls.raise_scopes[offset:]
            active = self.scope
            entry = self._capture_deferred_flow(active)
            for outcome in abrupt:
                self._switch_deferred_scope(outcome.clone(), restore_flow=True)
                produced = len(terminal_controls.raise_scopes)
                failed = replay_captured_exits()
                finalized_header_raises.extend(terminal_controls.raise_scopes[produced:])
                del terminal_controls.raise_scopes[produced:]
                if not failed:
                    finalized_header_raises.append(self.scope.clone())
            self._restore_deferred_flow(entry)
            self.scope = active

        try:
            for item in node.items:
                header_offset = len(terminal_controls.raise_scopes)
                if (
                    self.visit(item.context_expr) is False
                    and self._invocation_outcome_request() is not None
                ):
                    return False
                if self._invocation_outcome_request() is not None:
                    finalize_header_raises(header_offset)
                entered_binding: _ResolvedBinding | None = None
                context_binding = self._capture_argument_binding(item.context_expr)
                # Both protocol lookups precede entry and body effects.
                with self._suspend_invocation_outcomes():
                    enter_inputs = self._prepare_protocol_replay_inputs(
                        context_binding, enter_method, []
                    )
                    exit_inputs = self._prepare_protocol_replay_inputs(
                        context_binding, exit_method, [self._conservative_argument_binding()] * 3
                    )
                context_reference = context_binding.reference or ""
                missing_exit = (
                    context_reference.startswith(_INSTANCE_REFERENCE_PREFIX)
                    and self._class_mro_complete.get(
                        context_reference.replace(
                            _INSTANCE_REFERENCE_PREFIX, _CLASS_REFERENCE_PREFIX, 1
                        ),
                        False,
                    )
                    and (context_reference, exit_method) not in self._class_member_presence
                    and self._replay_calls_enabled
                    and (not asynchronous or self._active_async_replay_depth > 0)
                )
                if enter_inputs is None or missing_exit:
                    self._terminal_controls.raise_scopes.append(self.scope.clone())
                    return False
                header_offset = len(terminal_controls.raise_scopes)
                entered_results: list[_ResolvedBinding] = []
                request = self._invocation_outcome_request()
                enter_offsets = (
                    (len(request.return_scopes), len(request.raise_scopes))
                    if request is not None
                    else None
                )
                enter_scope = self.scope
                enter_entry = (
                    self._capture_deferred_flow(enter_scope) if request is not None else None
                )
                if request is not None and not enter_inputs:
                    terminal_controls.raise_scopes.append(self.scope.clone())
                for target, arguments in enter_inputs:
                    if request is not None:
                        if enter_entry is None:
                            raise AssertionError
                        self._restore_deferred_flow(enter_entry)
                        self.scope = enter_scope
                        normal_offset = len(request.return_scopes)
                    call = _DeferredFunctionCall(
                        function=target,
                        arguments=tuple(sorted(arguments.items())),
                    )
                    if not asynchronous and (
                        isinstance(target, ast.AsyncFunctionDef) or _function_is_generator(target)
                    ):
                        # A normal call creates a dormant coroutine/generator.
                        entered = _ResolvedBinding(
                            reference=_KNOWN_NON_APP_REFERENCE,
                            string=None,
                            deferred_calls=frozenset({call}),
                        )
                        if request is not None:
                            request.return_scopes.append(self.scope.clone())
                    else:
                        entered = self._execute_deferred_call(call)
                    if request is not None:
                        if len(request.return_scopes) == normal_offset:
                            continue
                        completed = request.return_scopes[normal_offset:]
                        del request.return_scopes[normal_offset:]
                        self._merge_outcomes(enter_scope, completed)
                        request.return_scopes.extend(completed)
                    if asynchronous and not isinstance(target, ast.AsyncFunctionDef):
                        if request is not None:
                            del request.return_scopes[normal_offset:]
                        awaited = self._replay_deferred_calls(
                            entered.deferred_calls, execution="await"
                        )
                        if request is not None:
                            if not entered.deferred_calls:
                                del request.return_scopes[normal_offset:]
                                if entered.reference == _KNOWN_NON_APP_REFERENCE:
                                    request.raise_scopes.append(self.scope.clone())
                                else:
                                    self._unknown_invocation_outcomes(request)
                            if len(request.return_scopes) == normal_offset:
                                continue
                        if awaited is None and entered.reference == _KNOWN_NON_APP_REFERENCE:
                            self._terminal_controls.raise_scopes.append(self.scope.clone())
                            continue
                        entered = awaited or self._conservative_argument_binding()
                    entered_results.append(entered)
                if request is not None and enter_inputs:
                    if enter_offsets is None:
                        raise AssertionError
                    if not self._resume_invocation_outcomes(request, enter_offsets):
                        return False
                if enter_inputs and not entered_results:
                    return False
                if entered_results:
                    entered_binding = self._join_resolved_bindings(entered_results)
                if request is not None:
                    finalize_header_raises(header_offset)
                # Unknown entry retains the existing possible body path and
                # its captured exit; it is not successful-entry evidence.
                captured_exit_inputs.append(exit_inputs)
                if item.optional_vars is not None:
                    header_offset = len(terminal_controls.raise_scopes)
                    binding = entered_binding or self._resolve_with_enter_binding(item.context_expr)
                    requested_target = self._invocation_outcome_request() is not None

                    def evaluate_with_leaf(
                        leaf: ast.expr, actual: _ResolvedBinding
                    ) -> _ResolvedBinding | None | Literal[False]:
                        if requested_target:
                            if self._visit_object_namespace_target_expressions(leaf) is False:
                                return False
                            self._record_object_namespace_target(leaf)
                        name = (
                            leaf.id
                            if isinstance(leaf, ast.Name)
                            else (
                                leaf.value.id
                                if isinstance(leaf, ast.Starred)
                                and isinstance(leaf.value, ast.Name)
                                else None
                            )
                        )
                        if actual.reference is None and name is not None:
                            return replace(
                                actual, reference=self._possible_sensitive_reference(name)
                            )
                        return None

                    if not requested_target:
                        self._visit_object_namespace_target_expressions(item.optional_vars)
                        self._record_object_namespace_target(item.optional_vars)
                    if (
                        self._bind_target_value(
                            item.optional_vars,
                            item.context_expr,
                            dynamic_unknown_string=False,
                            captured_binding=binding,
                            target_evaluator=evaluate_with_leaf,
                        )
                        is False
                    ):
                        return False
                    if requested_target:
                        finalize_header_raises(header_offset)
            if enters_task_group:
                self._active_task_group_depth += 1
                task_group_active = True
            falls_through = self._visit_statements(node.body)
        finally:
            # Finalize the existing abrupt outcomes just as Try.finalbody does.
            abrupt_groups = [
                (control_target, control_target[offset:])
                for control_target, offset in control_targets
            ]
            for control_target, offset in control_targets:
                del control_target[offset:]
            normal_scope = self.scope
            if falls_through or not any(scopes for _target, scopes in abrupt_groups):
                invalid_exit = replay_captured_exits()
                normal_scope = self.scope
                if invalid_exit and self._invocation_outcome_request() is None:
                    terminal_controls.raise_scopes.append(self.scope.clone())
            for control_target, abrupt_scopes in abrupt_groups:
                for abrupt_scope in abrupt_scopes:
                    self._switch_deferred_scope(abrupt_scope.clone(), restore_flow=True)
                    if replay_captured_exits():
                        if self._invocation_outcome_request() is None:
                            terminal_controls.raise_scopes.append(self.scope.clone())
                    else:
                        control_target.append(self.scope)
                    if not falls_through:
                        normal_scope = self.scope
            self._switch_deferred_scope(normal_scope, restore_flow=True)
            terminal_controls.raise_scopes.extend(finalized_header_raises)
            if task_group_active:
                self._active_task_group_depth -= 1
        return falls_through and not invalid_exit

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
        if self.visit(node.subject) is False and self._invocation_outcome_request() is not None:
            return False
        incoming = self.scope
        outcomes: list[_LexicalBindings] = []
        next_case_entry: _LexicalBindings | None = incoming.clone()
        for case in node.cases:
            if next_case_entry is None:
                break
            pattern_failure_scope = next_case_entry.clone()
            self._switch_deferred_scope(next_case_entry.clone(), restore_flow=True)
            if self.visit(case.pattern) is False and self._invocation_outcome_request() is not None:
                next_case_entry = None
                break
            self._bind_match_pattern(case.pattern, node.subject)
            guard_truth: bool | None = True
            if case.guard is not None:
                if (
                    self.visit(case.guard) is False
                    and self._invocation_outcome_request() is not None
                ):
                    next_case_entry = (
                        None
                        if self._is_irrefutable_pattern(case.pattern)
                        else pattern_failure_scope
                    )
                    continue
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
            self._switch_deferred_scope(incoming, restore_flow=True)
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
    ) -> None | Literal[False]:
        if not generators:
            for result_node in result_nodes:
                if (
                    self.visit(result_node)
                ) is False and self._invocation_outcome_request() is not None:
                    return False
            return None
        if (
            outer_binding is None
            and isinstance(generators[0].iter, (ast.List, ast.Tuple, ast.Set))
            and not (generators[0].iter.elts)
        ):
            if (
                self.visit(generators[0].iter)
            ) is False and self._invocation_outcome_request() is not None:
                return False
            return None
        if outer_binding is not None:
            request = self._invocation_outcome_request()
            offsets = (
                (len(request.return_scopes), len(request.raise_scopes))
                if request is not None
                else None
            )
            self._replay_deferred_calls(
                self._resolve_deferred_calls(generators[0].iter),
                execution="iterate",
            )
            if request is not None:
                if offsets is None:
                    raise AssertionError
                if not self._resume_invocation_outcomes(request, offsets):
                    return False
        elif deferred:
            if (
                self.visit(generators[0].iter)
            ) is False and self._invocation_outcome_request() is not None:
                return False
        else:
            if (
                self._visit_iterated_expression(generators[0].iter)
            ) is False and self._invocation_outcome_request() is not None:
                return False
        local_names = frozenset(
            name for generator in generators for name in _assignment_target_names(generator.target)
        )
        previous = self.scope
        previous_exception_scope_collectors = self._exception_scope_collectors
        previous_replay_calls_enabled = self._replay_calls_enabled
        self._switch_deferred_scope(
            _LexicalBindings(
                parent=previous,
                local_names=local_names,
                scope_kind="comprehension",
            ),
            restore_flow=False,
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
                        if (
                            self.visit(generator.iter)
                        ) is False and self._invocation_outcome_request() is not None:
                            return False
                        return None
                    if deferred:
                        if (
                            self.visit(generator.iter)
                        ) is False and self._invocation_outcome_request() is not None:
                            return False
                    else:
                        if (
                            self._visit_iterated_expression(generator.iter)
                        ) is False and self._invocation_outcome_request() is not None:
                            return False
                if index == 0 and outer_binding is not None:

                    def evaluate_comprehension_leaf(
                        leaf: ast.expr, _binding: _ResolvedBinding
                    ) -> None | Literal[False]:
                        if self._visit_object_namespace_target_expressions(leaf) is False:
                            return False
                        self._record_object_namespace_target(leaf)
                        return None

                    if (
                        self._bind_target_value(
                            generator.target,
                            generator.iter,
                            dynamic_unknown_string=False,
                            captured_binding=outer_binding,
                            target_evaluator=(
                                evaluate_comprehension_leaf
                                if self._invocation_outcome_request() is not None
                                else None
                            ),
                        )
                        is False
                    ):
                        return False
                else:
                    if (
                        self._bind_iteration_target(generator.target, generator.iter)
                    ) is False and self._invocation_outcome_request() is not None:
                        return False
                for condition in generator.ifs:
                    if (
                        self.visit(condition)
                    ) is False and self._invocation_outcome_request() is not None:
                        return False
                    if isinstance(condition, ast.Constant) and not bool(condition.value):
                        return None
            for result_node in result_nodes:
                if (
                    self.visit(result_node)
                ) is False and self._invocation_outcome_request() is not None:
                    return False
        finally:
            self._switch_deferred_scope(previous, restore_flow=False)
            self._exception_scope_collectors = previous_exception_scope_collectors
            self._replay_calls_enabled = previous_replay_calls_enabled
        return None

    def visit_ListComp(self, node: ast.ListComp) -> None | Literal[False]:
        return self._visit_comprehension(node.generators, [node.elt])

    def _visit_collection_elements(
        self, elements: Sequence[ast.expr]
    ) -> tuple[_ResolvedBinding, ...] | None | Literal[False]:
        captured: list[_ResolvedBinding] = []
        known = True
        for element in elements:
            value = element.value if isinstance(element, ast.Starred) else element
            if isinstance(element, ast.Starred):
                if (
                    self._visit_iterated_expression(value) is False
                    and self._invocation_outcome_request() is not None
                ):
                    return False
                rows = self._resolve_ordered_items(value)
                if rows is None:
                    known = False
                else:
                    captured.extend(rows)
            else:
                if self.visit(value) is False and self._invocation_outcome_request() is not None:
                    return False
                captured.append(self._capture_argument_binding(value))
                self._invalidate_mapping_aliases(value)
        return tuple(captured) if known else None

    def visit_Starred(self, node: ast.Starred) -> None | Literal[False]:
        if isinstance(node.ctx, ast.Load):
            if (
                self._visit_iterated_expression(node.value) is False
                and self._invocation_outcome_request() is not None
            ):
                return False
        else:
            if self.visit(node.value) is False and self._invocation_outcome_request() is not None:
                return False
        if self.visit(node.ctx) is False and self._invocation_outcome_request() is not None:
            return False
        return None

    def visit_List(self, node: ast.List) -> None | Literal[False]:
        rows = self._visit_collection_elements(node.elts)
        if rows is False:
            return False
        self._publish_captured_collection(node, rows)
        if self.visit(node.ctx) is False and self._invocation_outcome_request() is not None:
            return False
        return None

    def visit_Tuple(self, node: ast.Tuple) -> None | Literal[False]:
        rows = self._visit_collection_elements(node.elts)
        if rows is False:
            return False
        self._publish_captured_collection(node, rows)
        if self.visit(node.ctx) is False and self._invocation_outcome_request() is not None:
            return False
        return None

    def visit_Set(self, node: ast.Set) -> None | Literal[False]:
        if self._visit_collection_elements(node.elts) is False:
            return False
        return None

    def visit_Dict(self, node: ast.Dict) -> None | Literal[False]:
        entries: list[_StaticMappingEntry] = []
        escaped_mappings: list[_StaticMapping] = []
        for key, value in zip(node.keys, node.values, strict=True):
            if key is None:
                if self.visit(value) is False and self._invocation_outcome_request() is not None:
                    return False
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
            if self.visit(key) is False and self._invocation_outcome_request() is not None:
                return False
            if self.visit(value) is False and self._invocation_outcome_request() is not None:
                return False
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
                    ordered_items=binding.ordered_items,
                    call_receivers=binding.call_receivers,
                )
            entries.append(_StaticMappingEntry(key=key, binding=binding))
        candidate = _StaticMapping(site=node, entries=tuple(entries))
        snapshot = self._mapping_snapshot_intern.setdefault(candidate, candidate)
        self._mapping_literal_snapshots[id(node)] = snapshot
        for mapping in escaped_mappings:
            self._invalidate_mapping(mapping)
        return None

    def visit_SetComp(self, node: ast.SetComp) -> None | Literal[False]:
        return self._visit_comprehension(node.generators, [node.elt])

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> None | Literal[False]:
        if id(node) in self._iterated_call_ids:
            return self._visit_comprehension(node.generators, [node.elt])
        if node.generators:
            if (
                self.visit(node.generators[0].iter) is False
                and self._invocation_outcome_request() is not None
            ):
                return False
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
        return None

    def _visit_iterated_expression(
        self, node: ast.AST, *, iteration_result_node: ast.expr | None = None
    ) -> None | Literal[False]:
        node_id = id(node)
        was_iterated = node_id in self._iterated_call_ids
        self._iterated_call_ids.add(node_id)
        try:
            if iteration_result_node is not None:
                request = self._invocation_outcome_request()
                if request is None:
                    raise LegacyGrowthAnalysisError(
                        "iteration projection requires a current request"
                    )
                normal_offset = len(request.return_scopes)
                if self.visit(node, iteration_result_node=iteration_result_node) is False:
                    return False
                if len(request.return_scopes) > normal_offset:
                    # A direct Call has already performed this consumption.
                    return None
                binding = self._capture_argument_binding(node)
                if binding.deferred_calls:
                    self._replay_deferred_calls(
                        binding.deferred_calls,
                        execution="iterate",
                        iteration_result_node=iteration_result_node,
                    )
                else:
                    projected = (
                        binding
                        if binding.ordered_items is not None or binding.iterable_element is not None
                        else self._variadic_iterable_binding(
                            [self._conservative_argument_binding()]
                        )
                    )
                    self._call_result_bindings[id(iteration_result_node)] = projected
                    self._remember_captured_binding(projected)
                    request.return_scopes.append(self.scope.clone())
                return None
            if self.visit(node) is False and self._invocation_outcome_request() is not None:
                return False
            request = self._invocation_outcome_request()
            offsets = (
                (len(request.return_scopes), len(request.raise_scopes))
                if request is not None
                else None
            )
            self._replay_deferred_calls(self._resolve_deferred_calls(node), execution="iterate")
            if request is not None:
                if offsets is None:
                    raise AssertionError
                if not self._resume_invocation_outcomes(request, offsets):
                    return False
        finally:
            if not was_iterated:
                self._iterated_call_ids.remove(node_id)
        return None

    def visit_Yield(self, node: ast.Yield) -> None | Literal[False]:
        if node.value is not None and self.visit(node.value) is False:
            if self._invocation_outcome_request() is not None:
                return False
        owner = self._yield_result_owner()
        if owner is not None:
            value = (
                self._capture_argument_binding(node.value)
                if node.value is not None
                else _ResolvedBinding(_KNOWN_NON_APP_REFERENCE, None)
            )
            self._append_yield_result(
                owner, self._variadic_iterable_binding([value], ordered_items=(value,))
            )
        return None

    def visit_YieldFrom(self, node: ast.YieldFrom) -> None | Literal[False]:
        owner = self._yield_result_owner()
        if owner is None:
            return self._visit_iterated_expression(node.value)
        request = self._invocation_outcome_request()
        if request is None:
            raise AssertionError
        with self._temporary_iteration_result(node, pin_consumer=True):
            offsets = (len(request.return_scopes), len(request.raise_scopes))
            self._visit_iterated_expression(node.value, iteration_result_node=node)
            normal = request.return_scopes[offsets[0] :]
            del request.return_scopes[offsets[0] :]
            for saved in normal:
                state = saved._flow_snapshot
                if state is None or id(node) not in state[2]:
                    raise LegacyGrowthAnalysisError("delegation lost its current iteration result")
                self._restore_deferred_flow(state)
                self.scope = saved
                self._append_yield_result(owner, state[2][id(node)])
                request.return_scopes.append(self.scope.clone())
            if not self._resume_invocation_outcomes(request, offsets):
                return False
        return None

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
            entries = _effective_static_mapping_entries(mapping.entries)
            if not entries:
                return _ResolvedBinding(None, None)
            return self._join_resolved_bindings([entry.binding for entry in entries])
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

    @staticmethod
    def _mapping_lookup_attribute(node: ast.Call) -> ast.Attribute | None:
        positional_arguments, unresolved_sources = _expand_static_positional_arguments(node.args)
        if (
            not isinstance(node.func, ast.Attribute)
            or node.func.attr not in {"__getitem__", "get", "pop", "setdefault"}
            or not (positional_arguments or unresolved_sources)
        ):
            return None
        return node.func

    def _resolve_mapping_lookup_call_binding(
        self,
        node: ast.Call,
        *,
        receiver: _MappingLookupReceiver | None = None,
    ) -> _ResolvedBinding | None:
        attribute = self._mapping_lookup_attribute(node)
        if attribute is None:
            return None
        positional_arguments, unresolved_sources = _expand_static_positional_arguments(node.args)
        if unresolved_sources:
            return self._conservative_argument_binding()
        if not positional_arguments:
            return None
        return self._resolve_mapping_lookup_binding(
            owner=attribute.value,
            key=positional_arguments[0],
            default=(positional_arguments[1] if len(positional_arguments) >= 2 else None),
            receiver=receiver,
        )

    def _resolve_mapping_lookup_binding(
        self,
        *,
        owner: ast.AST,
        key: ast.AST,
        default: ast.AST | None,
        receiver: _MappingLookupReceiver | None,
    ) -> _ResolvedBinding | None:
        known_empty = False
        if receiver is not None:
            mapping = receiver.mapping
            possible_value = receiver.possible_value
            if mapping is not None:
                current_count = self._mapping_invalidation_counts.get(mapping, 0)
                if current_count != receiver.invalidation_count:
                    known_empty = (
                        self._mapping_last_clear_counts.get(mapping, 0) == current_count
                        and current_count > receiver.last_clear_count
                    )
                    if not known_empty:
                        return self._conservative_argument_binding()
        else:
            mapping = self._resolve_mapping(owner)
            possible_value = self._resolve_mapping_value_binding(owner)
        default_binding = self._capture_argument_binding(default) if default is not None else None
        if known_empty:
            return default_binding or _ResolvedBinding(
                reference=_KNOWN_NON_APP_REFERENCE,
                string=None,
            )
        literal_key = _literal_value(key)
        if mapping is not None and literal_key is not _UNRESOLVED_LITERAL_VALUE:
            selected, unresolved = _static_mapping_binding(mapping, literal_key)
            if selected is not None and not unresolved:
                return selected
            if not unresolved:
                return default_binding or _ResolvedBinding(
                    reference=_KNOWN_NON_APP_REFERENCE,
                    string=None,
                )
        if possible_value is None:
            return None
        candidates = [possible_value]
        if default_binding is not None:
            candidates.append(default_binding)
        return self._join_resolved_bindings(candidates)

    def _capture_mapping_receiver(self, owner: ast.AST) -> _MappingLookupReceiver:
        mapping = self._resolve_mapping(owner)
        return _MappingLookupReceiver(
            mapping=mapping,
            possible_value=self._resolve_mapping_value_binding(owner),
            invalidation_count=(
                self._mapping_invalidation_counts.get(mapping, 0) if mapping is not None else 0
            ),
            last_clear_count=(
                self._mapping_last_clear_counts.get(mapping, 0) if mapping is not None else 0
            ),
        )

    def _capture_mapping_lookup_receiver(
        self,
        node: ast.Call,
    ) -> _MappingLookupReceiver | None:
        attribute = self._mapping_lookup_attribute(node)
        if attribute is None:
            return None
        return self._capture_mapping_receiver(attribute.value)

    def _resolve_ordered_items(self, node: ast.AST) -> tuple[_ResolvedBinding, ...] | None:
        current = self._call_result_bindings.get(id(node))
        if current is not None:
            return current.ordered_items
        if isinstance(node, ast.Name):
            return self.scope.resolve_ordered_items(node.id)
        if isinstance(node, (ast.NamedExpr, ast.Await)):
            return self._resolve_ordered_items(node.value)
        if isinstance(node, ast.Subscript):
            binding, _unresolved = self._resolve_mapping_subscript_binding(node)
            return binding.ordered_items if binding is not None else None
        return None

    def _resolve_captured_receivers(
        self, node: ast.AST
    ) -> frozenset[tuple[_FunctionNode, str, _ResolvedBinding]]:
        current = self._call_result_bindings.get(id(node))
        if current is not None:
            return current.call_receivers
        if isinstance(node, ast.Name):
            return self.scope.resolve_call_receivers(node.id)
        if isinstance(node, (ast.NamedExpr, ast.Await)):
            return self._resolve_captured_receivers(node.value)
        if isinstance(node, ast.Subscript):
            binding, _unresolved = self._resolve_mapping_subscript_binding(node)
            return binding.call_receivers if binding is not None else frozenset()
        if not isinstance(node, ast.Attribute):
            return frozenset()
        receiver = self._capture_argument_binding(node.value)
        captured: set[tuple[_FunctionNode, str, _ResolvedBinding]] = set()
        for owner in self._resolve_object_references(node.value):
            for target, kind in self._class_member_descriptors.get((owner, node.attr), ()):
                if kind == "classmethod":
                    classes = frozenset(
                        {owner.replace(_INSTANCE_REFERENCE_PREFIX, _CLASS_REFERENCE_PREFIX, 1)}
                    )
                    value = _ResolvedBinding(next(iter(classes)), None, class_references=classes)
                    captured.add((target, "bound", value))
                elif (
                    kind == "bound"
                    or kind == "plain"
                    and owner.startswith(_INSTANCE_REFERENCE_PREFIX)
                ):
                    captured.add((target, "bound", receiver))
        return frozenset(captured)

    def _publish_captured_collection(
        self, node: ast.List | ast.Tuple, items: tuple[_ResolvedBinding, ...] | None
    ) -> None:
        if items is None:
            return
        result = self._variadic_iterable_binding(items, ordered_items=items)
        self._call_result_bindings[id(node)] = result

    def _deferred_result_element(self, binding: _ResolvedBinding) -> _ResolvedBinding | None:
        results = [
            record[2]
            for call in binding.deferred_calls
            if call.value_key is not None
            for record in self._consumed_deferred_calls
            if isinstance(record, tuple)
            and record[0] == call.value_key
            and record[1] == "consumed"
            and record[2] is not None
        ]
        return self._join_resolved_bindings(results) if results else binding.iterable_element

    def _resolve_iterable_element_binding(
        self,
        node: ast.AST,
    ) -> _ResolvedBinding | None:
        call_result = self._call_result_bindings.get(id(node))
        if call_result is not None:
            return self._deferred_result_element(call_result)
        if isinstance(node, ast.Await):
            return self._resolve_iterable_element_binding(node.value)
        if isinstance(node, ast.NamedExpr):
            return self._resolve_iterable_element_binding(node.value)
        if isinstance(node, ast.Name):
            return self._deferred_result_element(
                _ResolvedBinding(
                    None,
                    None,
                    deferred_calls=self.scope.resolve_deferred_calls(node.id),
                    iterable_element=self.scope.resolve_iterable_element(node.id),
                )
            )
        if isinstance(node, (ast.ListComp, ast.SetComp, ast.GeneratorExp)):
            if (
                len(node.generators) == 1
                and isinstance(node.elt, ast.Name)
                and isinstance(node.generators[0].target, ast.Name)
                and node.elt.id == node.generators[0].target.id
            ):
                return self._resolve_iterable_element_binding(node.generators[0].iter)
            return None
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in {"items", "values"}
            and not node.args
            and not node.keywords
        ):
            value_binding = self._resolve_mapping_value_binding(node.func.value)
            if value_binding is None or node.func.attr == "values":
                return value_binding
            return _ResolvedBinding(
                reference=_INDEXED_PAIR_ELEMENT_REFERENCE,
                string=None,
                iterable_element=value_binding,
            )
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
            ordered_items=self._resolve_ordered_items(node),
            call_receivers=self._resolve_captured_receivers(node),
        )

    def visit_DictComp(self, node: ast.DictComp) -> None | Literal[False]:
        if self._visit_comprehension(node.generators, [node.key, node.value]) is False:
            return False
        snapshot = self._static_dict_comprehension_mapping(node)
        if snapshot is not None:
            self._mapping_literal_snapshots[id(node)] = snapshot
        return None

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
            if reference == "builtins.object":
                reference = (
                    _CAPTURED_SAFE_BUILTINS_OBJECT_REFERENCE
                    if self._builtins_object_is_safe()
                    else _CAPTURED_POSSIBLE_APP_FACTORY_REFERENCE
                )
            self._bind_name(local_name, reference=reference, string=None)

    def visit_Assign(self, node: ast.Assign) -> None | Literal[False]:
        local_pairs: list[tuple[ast.Name, ast.AST]] = []

        def collect_local_pairs(target: ast.AST, value: ast.AST) -> bool:
            if isinstance(target, ast.Name) and not isinstance(
                value, (ast.Starred, ast.Tuple, ast.List)
            ):
                local_pairs.append((target, value))
                return True
            if (
                isinstance(target, (ast.Tuple, ast.List))
                and isinstance(value, (ast.Tuple, ast.List))
                and len(target.elts) == len(value.elts)
            ):
                return all(
                    collect_local_pairs(child_target, child_value)
                    for child_target, child_value in zip(target.elts, value.elts, strict=True)
                )
            return False

        def transparent_mapping_value(
            value: ast.AST,
            remaining_depth: int = _MAX_ITERABLE_ELEMENT_BINDING_DEPTH,
        ) -> bool:
            if remaining_depth < 0:
                return False
            if isinstance(value, ast.Constant) or (
                isinstance(value, ast.Name) and isinstance(value.ctx, ast.Load)
            ):
                return True
            if isinstance(value, ast.NamedExpr) and isinstance(value.target, ast.Name):
                return transparent_mapping_value(value.value, remaining_depth - 1)
            if isinstance(value, ast.Dict):
                return all(
                    isinstance(key, ast.Constant)
                    and transparent_mapping_value(child, remaining_depth - 1)
                    for key, child in zip(value.keys, value.values, strict=True)
                )
            return False

        if (
            len(node.targets) == 1
            and isinstance(node.targets[0], (ast.Tuple, ast.List))
            and not _assignment_target_escapes_value(node.targets[0])
            and collect_local_pairs(node.targets[0], node.value)
        ):
            preserve_mapping_precision = all(
                transparent_mapping_value(value) for _target, value in local_pairs
            )
            captured: list[tuple[ast.Name, _ResolvedBinding, int]] = []
            for target, value in local_pairs:
                if self.visit(value) is False and self._invocation_outcome_request() is not None:
                    return False
                binding = self._capture_argument_binding(value)
                # Preserve assignment fallback rather than argument-only unknown-call fallback.
                reference = self._resolve_reference(value)
                reference = self._namespace_mapping_binding_reference(value, reference)
                reference = self._capture_reference_provenance(value, reference)
                mapping = binding.mapping
                if (
                    isinstance(value, ast.Attribute)
                    and value.attr in {"__getitem__", "get", "items", "pop", "setdefault", "values"}
                    and (owner_mapping := self._resolve_mapping(value.value)) is not None
                ):
                    reference = f"builtins.dict.{value.attr}"
                    mapping = owner_mapping
                iterable_element = binding.iterable_element
                ordered_items = binding.ordered_items
                call_receivers = binding.call_receivers
                if mapping is not None and not preserve_mapping_precision:
                    # Match the original collection escape after this leaf's evaluation.
                    self._invalidate_mapping(mapping)
                    reference = (
                        reference
                        if reference == _MAPPING_APP_VALUE_REFERENCE
                        else _MAPPING_SENSITIVE_VALUE_REFERENCE
                    )
                    mapping = None
                    iterable_element = None
                binding = _ResolvedBinding(
                    reference=self._preserve_sensitive_reference(target.id, value, reference),
                    string=(
                        binding.string if binding.string is not None else _DYNAMIC_STRING_BINDING
                    ),
                    callables=binding.callables,
                    deferred_calls=binding.deferred_calls,
                    mapping=mapping,
                    class_references=binding.class_references,
                    descriptors=binding.descriptors,
                    iterable_element=iterable_element,
                    ordered_items=ordered_items,
                    call_receivers=call_receivers,
                )
                captured.append(
                    (
                        target,
                        binding,
                        (
                            self._mapping_invalidation_counts.get(mapping, 0)
                            if mapping is not None
                            else 0
                        ),
                    )
                )
            for target, binding, mapping_count in captured:
                if (
                    binding.mapping is not None
                    and self._mapping_invalidation_counts.get(binding.mapping, 0) != mapping_count
                ):
                    binding = _ResolvedBinding(
                        reference=(
                            binding.reference
                            if binding.reference == _MAPPING_APP_VALUE_REFERENCE
                            else _MAPPING_SENSITIVE_VALUE_REFERENCE
                        ),
                        string=binding.string,
                        callables=binding.callables,
                        deferred_calls=binding.deferred_calls,
                        class_references=binding.class_references,
                        descriptors=binding.descriptors,
                        ordered_items=binding.ordered_items,
                        call_receivers=binding.call_receivers,
                    )
                self._bind_targets_from_resolved_binding([target], binding)
            return None

        if self._invocation_outcome_request() is not None and any(
            isinstance(target, (ast.Tuple, ast.List)) for target in node.targets
        ):
            if self.visit(node.value) is False:
                return False
            captured_rhs = self._capture_argument_binding(node.value)
            frozen_value_reference = self._resolve_reference(node.value)
            scalar_rhs = (
                self._capture_assignment_source_binding(node.value, dynamic_unknown_string=True)
                if any(
                    isinstance(target, ast.Name)
                    or isinstance(target, ast.Starred)
                    and isinstance(target.value, ast.Name)
                    for target in node.targets
                )
                else None
            )
            frozen_non_app = (
                self._is_definitely_non_app_value(node.value) if scalar_rhs is not None else None
            )
            if scalar_rhs is not None:
                self._remember_captured_binding(scalar_rhs)

            def evaluate_leaf(
                target: ast.expr, binding: _ResolvedBinding
            ) -> _ResolvedBinding | None | Literal[False]:
                if self._visit_object_namespace_target_expressions(target) is False:
                    return False
                self._invalidate_mapping_target(target)
                self._record_object_namespace_target(target)
                self._refine_object_namespace_assignment(
                    target,
                    frozen_value_reference if target is assignment_target else binding.reference,
                )
                name = (
                    target.id
                    if isinstance(target, ast.Name)
                    else (
                        target.value.id
                        if isinstance(target, ast.Starred) and isinstance(target.value, ast.Name)
                        else None
                    )
                )
                if target is assignment_target and scalar_rhs is not None and name is not None:
                    if frozen_non_app is None:
                        raise AssertionError
                    return replace(
                        scalar_rhs,
                        reference=self._preserve_sensitive_reference(
                            name,
                            node.value,
                            scalar_rhs.reference,
                            definitely_non_app=frozen_non_app,
                        ),
                    )
                return None

            for assignment_target in node.targets:
                if (
                    self._bind_target_value(
                        assignment_target,
                        node.value,
                        dynamic_unknown_string=True,
                        captured_binding=captured_rhs,
                        target_evaluator=evaluate_leaf,
                    )
                    is False
                ):
                    return False
            if captured_rhs.mapping is not None and any(
                _assignment_target_escapes_value(target) for target in node.targets
            ):
                self._invalidate_mapping(captured_rhs.mapping)
            return None

        # Unsupported or escaping structures retain the original generic collection escape.
        if any(isinstance(target, (ast.Tuple, ast.List)) for target in node.targets):
            if (
                self._visit_iterated_expression(node.value) is False
                and self._invocation_outcome_request() is not None
            ):
                return False
        else:
            if self.visit(node.value) is False and self._invocation_outcome_request() is not None:
                return False
        value_mapping = self._resolve_mapping(node.value)
        value_reference = self._resolve_reference(node.value)
        for assignment_target in node.targets:
            if (
                self._visit_object_namespace_target_expressions(assignment_target) is False
                and self._invocation_outcome_request() is not None
            ):
                return False
            self._invalidate_mapping_target(assignment_target)
            self._record_object_namespace_target(assignment_target)
            self._refine_object_namespace_assignment(assignment_target, value_reference)
            if (
                self._bind_target_value(
                    assignment_target,
                    node.value,
                    dynamic_unknown_string=True,
                    value_consumed=isinstance(assignment_target, (ast.Tuple, ast.List)),
                )
                is False
                and self._invocation_outcome_request() is not None
            ):
                return False
        if value_mapping is not None and any(
            _assignment_target_escapes_value(target) for target in node.targets
        ):
            self._invalidate_mapping(value_mapping)
        return None

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None | Literal[False]:
        if node.value is None:
            if not self._postponed_annotations:
                if (
                    self.visit(node.annotation) is False
                    and self._invocation_outcome_request() is not None
                ):
                    return False
            if not isinstance(node.target, ast.Name):
                if (
                    self.visit(node.target) is False
                    and self._invocation_outcome_request() is not None
                ):
                    return False
            return None
        if self.visit(node.value) is False and self._invocation_outcome_request() is not None:
            return False
        value_mapping = self._resolve_mapping(node.value)
        value_reference = self._resolve_reference(node.value)
        if (
            self._visit_object_namespace_target_expressions(node.target) is False
            and self._invocation_outcome_request() is not None
        ):
            return False
        self._invalidate_mapping_target(node.target)
        self._record_object_namespace_target(node.target)
        self._refine_object_namespace_assignment(node.target, value_reference)
        if (
            self._bind_target_value(
                node.target,
                node.value,
                dynamic_unknown_string=True,
            )
            is False
            and self._invocation_outcome_request() is not None
        ):
            return False
        if value_mapping is not None and _assignment_target_escapes_value(node.target):
            self._invalidate_mapping(value_mapping)
        if not self._postponed_annotations:
            if (
                self.visit(node.annotation) is False
                and self._invocation_outcome_request() is not None
            ):
                return False
        return None

    def visit_AugAssign(self, node: ast.AugAssign) -> None | Literal[False]:
        if self.visit(node.target) is False and self._invocation_outcome_request() is not None:
            return False
        captured_api_namespace_kind = (
            self._object_namespace_mapping_kind(node.target)
            if self.filename == LEGACY_APP and isinstance(node.op, ast.BitOr)
            else None
        )
        captured_api_name_binding = (
            self._capture_argument_binding(node.target)
            if self.filename == LEGACY_APP
            and isinstance(node.op, ast.BitOr)
            and isinstance(node.target, ast.Name)
            else None
        )
        if self.visit(node.value) is False and self._invocation_outcome_request() is not None:
            return False
        target_reference = self._resolve_reference(node.target)
        namespace_kind = (
            self._object_namespace_mapping_kind(node.target)
            if isinstance(node.op, ast.BitOr)
            else None
        )
        if captured_api_namespace_kind == "module":
            mapping = self._capture_argument_binding(node.value).mapping
            names: set[str | None] = set()
            if mapping is None:
                names.add(None)
            else:
                for entry in mapping.entries:
                    if isinstance(entry.key, ast.Constant):
                        if isinstance(entry.key.value, str):
                            names.add(entry.key.value)
                    else:
                        names.add(None)
            selected = CANONICAL_API_KEY_SYMBOLS if None in names else names
            for name in selected:
                if name is not None:
                    self._record_outward_api_key_rebinding(name, proven_module_namespace=True)
        target_mapping = self._resolve_mapping(node.target)
        if target_mapping is not None:
            self._invalidate_mapping(target_mapping)
        self._invalidate_mapping_target(node.target)
        self._record_object_namespace_target(node.target)
        if namespace_kind is not None:
            keys = (
                {None if key is None else self._resolve_string(key) for key in node.value.keys}
                if isinstance(node.value, ast.Dict)
                else {None}
            )
            if keys & {"object", None, _DYNAMIC_STRING_BINDING}:
                self._record_object_namespace_kind(namespace_kind)
        if isinstance(node.target, ast.Name):
            preserved_reference = self._possible_sensitive_reference(node.target.id)
            if namespace_kind is not None and target_reference in {
                _BUILTINS_NAMESPACE_REFERENCE,
                _POSSIBLE_BUILTINS_NAMESPACE_REFERENCE,
                _MODULE_NAMESPACE_REFERENCE,
                _POSSIBLE_OBJECT_NAMESPACE_REFERENCE,
            }:
                preserved_reference = target_reference
            if captured_api_name_binding is not None:
                if captured_api_namespace_kind == "module":
                    preserved_reference = _MODULE_NAMESPACE_REFERENCE
                elif (
                    captured_api_name_binding.mapping is not None
                    and target_reference == _MODULE_NAMESPACE_REFERENCE
                ):
                    # Remove only a later RHS module alias; retain ordinary fail-closed joins.
                    preserved_reference = captured_api_name_binding.reference
            self._bind_name(
                node.target.id,
                reference=preserved_reference,
                string=None,
            )
        return None

    def visit_NamedExpr(self, node: ast.NamedExpr) -> None | Literal[False]:
        if self.visit(node.value) is False and self._invocation_outcome_request() is not None:
            return False
        active_scope = self.scope
        if active_scope.scope_kind == "comprehension":
            containing_scope = active_scope.parent
            while containing_scope is not None and containing_scope.scope_kind == "comprehension":
                containing_scope = containing_scope.parent
            if containing_scope is not None:
                self._switch_deferred_scope(containing_scope, restore_flow=False)
        try:
            if (
                self._bind_target_value(
                    node.target,
                    node.value,
                    dynamic_unknown_string=True,
                )
                is False
                and self._invocation_outcome_request() is not None
            ):
                return False
        finally:
            self._switch_deferred_scope(active_scope, restore_flow=False)
        return None

    def visit_Delete(self, node: ast.Delete) -> None | Literal[False]:
        for target in node.targets:
            if (
                self._visit_object_namespace_target_expressions(target) is False
                and self._invocation_outcome_request() is not None
            ):
                return False
            namespace_target_recorded = self._record_object_namespace_target(
                target,
                deletion=True,
            )
            if isinstance(target, ast.Subscript):
                mapping = self._resolve_mapping(target.value)
                if mapping is not None:
                    replacement = self._mapping_after_known_pop(
                        mapping,
                        target.slice,
                        target,
                        preserve_if_absent=False,
                    )
                    if replacement is not None:
                        self._replace_mapping_aliases(mapping, replacement)
                        self._invalidate_mapping(mapping)
                        continue
            names = _assignment_target_names(target)
            if not names:
                self._invalidate_mapping_target(target)
                continue
            for name in names:
                self._record_outward_api_key_rebinding(name)
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
        return None

    def visit_Attribute(self, node: ast.Attribute) -> None | Literal[False]:
        if node.attr in CANONICAL_API_KEY_SYMBOLS and self._is_legacy_module_reference(
            self._resolve_reference(node.value)
        ):
            self.errors.append(
                f"{self.filename}: legacy API-key dependency attribute access is forbidden: "
                f"{node.attr}"
            )
        if (
            node.attr in _MAPPING_MUTATOR_METHODS
            and id(node) not in self._deferred_mapping_mutator_attribute_ids
        ):
            self._invalidate_mapping_aliases(node.value)
        if id(node) not in self._previsited_call_receiver_attribute_ids:
            if self.generic_visit(node) is False and self._invocation_outcome_request() is not None:
                return False
        return None

    def visit_Subscript(self, node: ast.Subscript) -> None | Literal[False]:
        if self.filename == LEGACY_APP and isinstance(node.ctx, (ast.Store, ast.Del)):
            if (
                self._visit_object_namespace_target_expressions(node) is False
                and self._invocation_outcome_request() is not None
            ):
                return False
            if self.visit(node.ctx) is False and self._invocation_outcome_request() is not None:
                return False
            return None
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
        if self.generic_visit(node) is False and self._invocation_outcome_request() is not None:
            return False
        if (
            self._analysis_purpose == "ownership_audit"
            and isinstance(node.ctx, ast.Load)
            and isinstance(node.slice, ast.Constant)
        ):
            result = self._resolve_mapping_lookup_binding(
                owner=node.value, key=node.slice, default=None, receiver=None
            )
            if result is not None:
                existing = self._call_result_bindings.get(id(node))
                self._call_result_bindings[id(node)] = (
                    result if existing is None else self._join_resolved_bindings([existing, result])
                )
                if self.call_result_snapshots is not None:
                    existing_snapshot = self.call_result_snapshots.get(id(node))
                    self.call_result_snapshots[id(node)] = (
                        result
                        if existing_snapshot is None
                        else self._join_resolved_bindings([existing_snapshot, result])
                    )
        return None

    def _capture_argument_binding(
        self,
        value: ast.AST,
        *,
        conservative: bool = False,
    ) -> _ResolvedBinding:
        reference = self._resolve_reference(value)
        reference = self._namespace_mapping_binding_reference(value, reference)
        reference = self._capture_reference_provenance(value, reference)
        string = self._resolve_string(value)
        unresolved_dynamic = reference is None and isinstance(
            value,
            (ast.Call, ast.Attribute, ast.Subscript),
        )
        if reference is None and (conservative or unresolved_dynamic):
            reference = _POSSIBLE_APP_CALL_REFERENCE
        if string is None and conservative:
            string = _DYNAMIC_STRING_BINDING
        captured = _ResolvedBinding(
            reference=reference,
            string=string,
            callables=self._resolve_callables(value),
            deferred_calls=self._resolve_deferred_calls(value),
            mapping=self._resolve_mapping(value),
            class_references=self._resolve_class_references(value),
            descriptors=self._resolve_descriptors(value),
            iterable_element=self._resolve_iterable_element_binding(value),
            ordered_items=self._resolve_ordered_items(value),
            call_receivers=self._resolve_captured_receivers(value),
        )
        captured = _normalize_resolved_binding(captured)
        self._remember_captured_binding(captured)
        return captured

    @staticmethod
    def _conservative_argument_binding() -> _ResolvedBinding:
        return _ResolvedBinding(
            reference=_POSSIBLE_APP_CALL_REFERENCE,
            string=_DYNAMIC_STRING_BINDING,
        )

    def _variadic_iterable_binding(
        self,
        elements: Sequence[_ResolvedBinding],
        *,
        ordered_items: tuple[_ResolvedBinding, ...] | None = None,
    ) -> _ResolvedBinding:
        if not elements:
            return _ResolvedBinding(
                reference=_KNOWN_NON_APP_REFERENCE,
                string=None,
                ordered_items=(),
            )
        element = self._join_resolved_bindings(elements)
        collection_reference = _collection_reference(
            [binding.reference for binding in elements], mapping=False
        )
        factory_only = (
            collection_reference == _ITERABLE_CAPTURED_POSSIBLE_APP_FACTORY_REFERENCE
            and not any(
                self._argument_binding_may_register(
                    replace(binding, reference=None)
                    if binding.reference == _CAPTURED_POSSIBLE_APP_FACTORY_REFERENCE
                    else binding
                )
                for binding in elements
            )
        )
        return _ResolvedBinding(
            reference=(
                collection_reference
                if factory_only
                else (
                    _ITERABLE_SENSITIVE_ELEMENT_REFERENCE
                    if self._argument_binding_may_register(element)
                    else _KNOWN_NON_APP_REFERENCE
                )
            ),
            string=None,
            iterable_element=element,
            ordered_items=ordered_items,
        )

    def _variadic_mapping_binding(
        self,
        values: Sequence[_ResolvedBinding],
        *,
        mapping_entries: Sequence[_StaticMappingEntry] | None = None,
        mapping_site: ast.Dict | None = None,
    ) -> _ResolvedBinding:
        mapping: _StaticMapping | None = None
        if mapping_entries is not None:
            if mapping_site is None:
                raise LegacyGrowthAnalysisError(
                    f"{self.filename}: variadic mapping entries require a binding site"
                )
            candidate = _StaticMapping(
                site=mapping_site,
                entries=tuple(mapping_entries),
            )
            mapping = self._mapping_snapshot_intern.setdefault(candidate, candidate)
        if not values:
            return _ResolvedBinding(
                reference=_KNOWN_NON_APP_REFERENCE,
                string=None,
                mapping=mapping,
            )
        value = self._join_resolved_bindings(values)
        return _ResolvedBinding(
            reference=(
                _MAPPING_SENSITIVE_VALUE_REFERENCE
                if self._argument_binding_may_register(value)
                else _KNOWN_NON_APP_REFERENCE
            ),
            string=None,
            mapping=mapping,
            iterable_element=value,
        )

    def _copied_mapping_binding(
        self,
        mapping: _StaticMapping,
        site: ast.AST,
    ) -> _ResolvedBinding:
        synthetic_site = ast.copy_location(ast.Dict(keys=[], values=[]), site)
        return self._variadic_mapping_binding(
            [entry.binding for entry in mapping.entries],
            mapping_entries=mapping.entries,
            mapping_site=synthetic_site,
        )

    def _replace_mapping_aliases(
        self,
        mapping: _StaticMapping,
        replacement: _ResolvedBinding,
    ) -> None:
        if replacement.mapping is None:
            raise LegacyGrowthAnalysisError(
                f"{self.filename}: replacement mapping binding lost its mapping shape"
            )
        scope: _LexicalBindings | None = self.scope
        while scope is not None:
            for name, candidate in tuple(scope.mappings.items()):
                if candidate is not mapping:
                    continue
                scope.mappings[name] = replacement.mapping
                if name.startswith("<dict-argument:"):
                    continue
                if replacement.reference is None:
                    scope.references.pop(name, None)
                else:
                    scope.references[name] = replacement.reference
                if replacement.iterable_element is None:
                    scope.iterable_elements.pop(name, None)
                else:
                    scope.iterable_elements[name] = replacement.iterable_element
            scope = scope.parent

    def _mapping_after_known_pop(
        self,
        mapping: _StaticMapping,
        key_node: ast.AST,
        site: ast.AST,
        *,
        preserve_if_absent: bool,
    ) -> _ResolvedBinding | None:
        removed_key = _literal_value(key_node)
        if removed_key is _UNRESOLVED_LITERAL_VALUE:
            return None
        remaining: list[_StaticMappingEntry] = []
        removed = False
        for entry in mapping.entries:
            if entry.key is None:
                return None
            candidate = _literal_value(entry.key)
            if candidate is _UNRESOLVED_LITERAL_VALUE:
                return None
            if candidate == removed_key:
                removed = True
                continue
            remaining.append(entry)
        if not removed:
            return self._copied_mapping_binding(mapping, site) if preserve_if_absent else None
        synthetic_site = ast.copy_location(ast.Dict(keys=[], values=[]), site)
        return self._variadic_mapping_binding(
            [entry.binding for entry in remaining],
            mapping_entries=remaining,
            mapping_site=synthetic_site,
        )

    def _mapping_after_known_update(
        self,
        mapping: _StaticMapping,
        node: ast.Call,
        positional_arguments: Sequence[ast.expr],
        unresolved_positional_sources: Sequence[ast.expr],
    ) -> _ResolvedBinding | None:
        if unresolved_positional_sources or len(positional_arguments) > 1:
            return None
        entries = list(mapping.entries)
        if positional_arguments:
            source = self._resolve_mapping(positional_arguments[0])
            if source is None:
                return None
            entries.extend(source.entries)
        for keyword in node.keywords:
            if keyword.arg is None:
                source = self._resolve_mapping(keyword.value)
                if source is None:
                    return None
                entries.extend(source.entries)
                continue
            entries.append(
                _StaticMappingEntry(
                    key=ast.copy_location(ast.Constant(keyword.arg), keyword.value),
                    binding=self._capture_argument_binding(keyword.value),
                )
            )
        effective = _effective_static_mapping_entries(entries)
        synthetic_site = ast.copy_location(ast.Dict(keys=[], values=[]), node)
        return self._variadic_mapping_binding(
            [entry.binding for entry in effective],
            mapping_entries=effective,
            mapping_site=synthetic_site,
        )

    def _mapping_after_known_setdefault(
        self,
        mapping: _StaticMapping,
        key_node: ast.AST,
        default: ast.AST | None,
        site: ast.AST,
    ) -> _ResolvedBinding | None:
        key = _literal_value(key_node)
        if key is _UNRESOLVED_LITERAL_VALUE:
            return None
        selected, unresolved = _static_mapping_binding(mapping, key)
        if unresolved:
            return None
        if selected is not None:
            return self._copied_mapping_binding(mapping, site)
        default_binding = (
            self._capture_argument_binding(default)
            if default is not None
            else _ResolvedBinding(reference=_KNOWN_NON_APP_REFERENCE, string=None)
        )
        entries = [
            *mapping.entries,
            _StaticMappingEntry(key=key_node, binding=default_binding),
        ]
        effective = _effective_static_mapping_entries(entries)
        synthetic_site = ast.copy_location(ast.Dict(keys=[], values=[]), site)
        return self._variadic_mapping_binding(
            [entry.binding for entry in effective],
            mapping_entries=effective,
            mapping_site=synthetic_site,
        )

    def _dict_constructor_binding(
        self,
        node: ast.Call,
        positional_arguments: Sequence[ast.expr],
        unresolved_positional_sources: Sequence[ast.expr],
        *,
        captured_operand: _ResolvedBinding | None,
        captured_pair_entries: Sequence[_StaticMappingEntry] | None,
        captured_keyword_entries: Sequence[_StaticMappingEntry],
    ) -> _ResolvedBinding | None:
        if unresolved_positional_sources or len(positional_arguments) > 1:
            return None
        entries: list[_StaticMappingEntry] = []
        if positional_arguments:
            source_mapping = captured_operand.mapping if captured_operand is not None else None
            if source_mapping is None:
                if captured_pair_entries is None:
                    entries.append(
                        _StaticMappingEntry(
                            key=None,
                            binding=self._conservative_argument_binding(),
                        )
                    )
                else:
                    entries.extend(captured_pair_entries)
            else:
                entries.extend(source_mapping.entries)
        entries.extend(captured_keyword_entries)
        synthetic_site = ast.copy_location(ast.Dict(keys=[], values=[]), node)
        return self._variadic_mapping_binding(
            [entry.binding for entry in entries],
            mapping_entries=entries,
            mapping_site=synthetic_site,
        )

    def _static_pair_mapping_entries(
        self,
        source: ast.AST,
    ) -> list[_StaticMappingEntry] | None:
        if not isinstance(source, (ast.List, ast.Set, ast.Tuple)):
            return None
        entries: list[_StaticMappingEntry] = []
        for element in source.elts:
            if not isinstance(element, (ast.List, ast.Tuple)) or len(element.elts) != 2:
                return None
            key, value = element.elts
            if isinstance(key, ast.Starred) or isinstance(value, ast.Starred):
                return None
            entries.append(
                _StaticMappingEntry(
                    key=key,
                    binding=self._capture_argument_binding(value),
                )
            )
        return entries

    def _dict_fromkeys_binding(
        self,
        node: ast.Call,
        positional_arguments: Sequence[ast.expr],
        unresolved_positional_sources: Sequence[ast.expr],
    ) -> _ResolvedBinding | None:
        if (
            unresolved_positional_sources
            or not 1 <= len(positional_arguments) <= 2
            or node.keywords
        ):
            return None
        keys = positional_arguments[0]
        value_binding = (
            self._capture_argument_binding(positional_arguments[1])
            if len(positional_arguments) == 2
            else _ResolvedBinding(reference=_KNOWN_NON_APP_REFERENCE, string=None)
        )
        entries: list[_StaticMappingEntry] = []
        if isinstance(keys, (ast.List, ast.Tuple, ast.Set)) and all(
            not isinstance(element, ast.Starred) for element in keys.elts
        ):
            entries.extend(_StaticMappingEntry(key=key, binding=value_binding) for key in keys.elts)
        elif isinstance(keys, ast.Constant) and isinstance(keys.value, (bytes, str)):
            entries.extend(
                _StaticMappingEntry(
                    key=ast.copy_location(ast.Constant(value=key), keys),
                    binding=value_binding,
                )
                for key in keys.value
            )
        else:
            entries.append(_StaticMappingEntry(key=None, binding=value_binding))
        synthetic_site = ast.copy_location(ast.Dict(keys=[], values=[]), node)
        return self._variadic_mapping_binding(
            [entry.binding for entry in entries],
            mapping_entries=entries,
            mapping_site=synthetic_site,
        )

    def _is_proven_nonempty_iterable(self, node: ast.AST) -> bool:
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            return bool(node.elts) and all(
                not isinstance(element, ast.Starred) for element in node.elts
            )
        if not isinstance(node, ast.Call) or node.keywords:
            return False
        positional_arguments, unresolved_sources = _expand_static_positional_arguments(node.args)
        return (
            self._resolve_reference(node.func) == "builtins.iter"
            and not unresolved_sources
            and len(positional_arguments) == 1
            and self._is_proven_nonempty_iterable(positional_arguments[0])
        )

    def _resolve_first_static_iterable_binding(
        self,
        node: ast.AST,
    ) -> _ResolvedBinding | None:
        if isinstance(node, (ast.List, ast.Tuple)) and node.elts:
            first = node.elts[0]
            return None if isinstance(first, ast.Starred) else self._capture_argument_binding(first)
        if not isinstance(node, ast.Call) or node.keywords:
            return None
        positional_arguments, unresolved_sources = _expand_static_positional_arguments(node.args)
        if (
            self._resolve_reference(node.func) != "builtins.iter"
            or unresolved_sources
            or len(positional_arguments) != 1
        ):
            return None
        return self._resolve_first_static_iterable_binding(positional_arguments[0])

    def _is_proven_empty_iterable(self, node: ast.AST) -> bool:
        current = self._call_result_bindings.get(id(node))
        if current is not None and current.ordered_items == ():
            return True
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            return not node.elts
        if isinstance(node, ast.Dict):
            return not node.keys
        if not isinstance(node, ast.Call) or node.keywords:
            return False
        positional_arguments, unresolved_sources = _expand_static_positional_arguments(node.args)
        function_reference = self._resolve_reference(node.func)
        if not unresolved_sources:
            if function_reference == "builtins.map" and len(positional_arguments) >= 2:
                return any(
                    self._is_proven_empty_iterable(argument)
                    for argument in positional_arguments[1:]
                )
            if function_reference == "builtins.filter" and len(positional_arguments) == 2:
                return self._is_proven_empty_iterable(positional_arguments[1])
            if function_reference in _ZIPPING_ITERABLE_BUILTIN_REFERENCES:
                return not positional_arguments or any(
                    self._is_proven_empty_iterable(argument) for argument in positional_arguments
                )
        return (
            function_reference == "builtins.iter"
            and not unresolved_sources
            and len(positional_arguments) == 1
            and self._is_proven_empty_iterable(positional_arguments[0])
        )

    def _is_proven_empty_islice(
        self,
        arguments: Sequence[ast.expr],
        unresolved_sources: Sequence[ast.expr],
    ) -> bool:
        if unresolved_sources or not 2 <= len(arguments) <= 4:
            return False
        if self._is_proven_empty_iterable(arguments[0]):
            return True
        stop = _literal_value(arguments[1] if len(arguments) == 2 else arguments[2])
        if not isinstance(stop, int):
            return False
        if len(arguments) == 2:
            return stop <= 0
        start = _literal_value(arguments[1])
        return isinstance(start, int) and stop <= start

    def _zip_result_binding(
        self,
        arguments: Sequence[ast.expr],
        unresolved_sources: Sequence[ast.expr],
        *,
        keywords: Sequence[ast.keyword],
    ) -> _ResolvedBinding:
        if not unresolved_sources and any(
            self._is_proven_empty_iterable(argument) for argument in arguments
        ):
            if not keywords:
                return self._variadic_iterable_binding([])
            return self._variadic_iterable_binding(
                [_ResolvedBinding(reference=_KNOWN_NON_APP_REFERENCE, string=None)]
            )
        elements = [
            self._resolve_iterable_element_binding(argument)
            or self._conservative_argument_binding()
            for argument in arguments
        ]
        elements.extend(
            self._resolve_iterable_element_binding(source) or self._conservative_argument_binding()
            for source in unresolved_sources
        )
        sensitive_indices = [
            index
            for index, element in enumerate(elements)
            if self._argument_binding_may_register(element)
        ]
        if len(elements) >= 2 and len(sensitive_indices) == 1:
            sensitive_index = sensitive_indices[0]
            tuple_element = _ResolvedBinding(
                reference=(
                    _REVERSED_INDEXED_PAIR_ELEMENT_REFERENCE
                    if len(elements) == 2 and sensitive_index == 0
                    else (
                        _INDEXED_PAIR_ELEMENT_REFERENCE
                        if len(elements) == 2
                        else _indexed_tuple_reference(sensitive_index, len(elements))
                    )
                ),
                string=None,
                iterable_element=elements[sensitive_index],
                ordered_items=tuple(elements),
            )
            return self._variadic_iterable_binding([tuple_element])
        if len(elements) == 2 and not sensitive_indices:
            pair_element = _ResolvedBinding(
                reference=_INDEXED_PAIR_ELEMENT_REFERENCE,
                string=None,
                iterable_element=elements[1],
                ordered_items=tuple(elements),
            )
            return self._variadic_iterable_binding([pair_element])
        return self._variadic_iterable_binding(elements)

    def _identity_map_result_binding(
        self,
        arguments: Sequence[ast.expr],
        unresolved_sources: Sequence[ast.expr],
    ) -> _ResolvedBinding | None:
        if unresolved_sources or len(arguments) != 2:
            return None
        mapper, iterable = arguments
        if not isinstance(mapper, ast.Lambda):
            return None
        parameters = (*mapper.args.posonlyargs, *mapper.args.args)
        if (
            len(parameters) != 1
            or mapper.args.defaults
            or mapper.args.kwonlyargs
            or mapper.args.vararg is not None
            or mapper.args.kwarg is not None
            or not isinstance(mapper.body, ast.Name)
            or mapper.body.id != parameters[0].arg
        ):
            return None
        element = self._resolve_iterable_element_binding(iterable)
        return self._variadic_iterable_binding(
            [element if element is not None else self._conservative_argument_binding()]
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
                ordered_items=binding.ordered_items,
                call_receivers=binding.call_receivers,
            )
            outcomes.append(outcome)
        merged = _LexicalBindings(parent=None)
        self._merge_binding_facts(merged, outcomes)
        self.scope._flow_owner = self
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
            ordered_items=merged.ordered_items.get(marker),
            call_receivers=merged.call_receivers.get(marker, frozenset()),
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
                _CAPTURED_POSSIBLE_APP_FACTORY_REFERENCE,
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
        receiver_override: _ResolvedBinding | None = None,
        captured_callee: _ResolvedBinding | None = None,
        captured_positional: Sequence[tuple[_ResolvedBinding, bool]] | None = None,
        captured_keywords: Sequence[tuple[str, _ResolvedBinding]] | None = None,
        captured_unresolved_keywords: Sequence[_ResolvedBinding] | None = None,
    ) -> dict[str, _ResolvedBinding] | None:
        if captured_callee is not None:
            if (
                captured_positional is None
                or captured_keywords is None
                or captured_unresolved_keywords is None
            ):
                raise LegacyGrowthAnalysisError("incomplete captured canonical binder input")
            positional_segments = list(captured_positional)
            keyword_bindings = list(captured_keywords)
            unresolved_keyword_value_bindings = list(captured_unresolved_keywords)
            unresolved_keywords = bool(unresolved_keyword_value_bindings)
            receiver_options: set[bool] = set()
            captured_receivers = [
                receiver
                for target, kind, receiver in captured_callee.call_receivers
                if target is function and kind in {"bound", "classmethod"}
            ]
            if captured_receivers:
                receiver_override = self._join_resolved_bindings(captured_receivers)
                receiver_options.add(True)
            for target, kind in captured_callee.descriptors:
                if target is function:
                    receiver_options.add(kind in {"bound", "classmethod"})
            if not receiver_options:
                receiver_options.add(receiver_override is not None)
        else:
            callable_expr = callable_expr or call.func
            implicit_owners = {
                owner
                for owner in self._resolve_object_references(callable_expr)
                if owner.startswith(_INSTANCE_REFERENCE_PREFIX)
                and function in self._class_member_callables.get((owner, "__call__"), ())
            }
            if implicit_owners:
                captured_receiver = self._capture_argument_binding(callable_expr)
                descriptor_kinds = {
                    kind
                    for owner in implicit_owners
                    for target, kind in self._class_member_descriptors.get((owner, "__call__"), ())
                    if target is function
                }
                receivers = []
                if "classmethod" in descriptor_kinds:
                    classes = frozenset(
                        owner.replace(_INSTANCE_REFERENCE_PREFIX, _CLASS_REFERENCE_PREFIX, 1)
                        for owner in implicit_owners
                    )
                    receivers.append(
                        _ResolvedBinding(
                            next(iter(classes)) if len(classes) == 1 else None,
                            None,
                            class_references=classes,
                        )
                    )
                if descriptor_kinds - {"classmethod"} or not descriptor_kinds:
                    receivers.append(captured_receiver)
                if receivers:
                    receiver_override = self._join_resolved_bindings(receivers)
                callable_expr = ast.Attribute(value=callable_expr, attr="__call__", ctx=ast.Load())
            evaluator = _ApiKeyLookupVisitor(
                filename=self.filename,
                errors=[],
                preserve_fastapi_conflicts=self.preserve_fastapi_conflicts,
                preserve_lifecycle_conflicts=self.preserve_lifecycle_conflicts,
                preserve_route_method_conflicts=self.preserve_route_method_conflicts,
                analyze_function_bodies=False,
                ownership_family=self.ownership_family,
            )
            evaluator._postponed_annotations = self._postponed_annotations
            evaluator.scope = self.scope.detached_clone()
            evaluator._call_result_bindings = dict(self._call_result_bindings)
            # Carry active replays with the genuine parsed source frames.
            evaluator._active_function_replays = set(self._active_function_replays)
            evaluator._active_replay_contexts = [
                (
                    (
                        *context[:4],
                        (
                            ()
                            if self._private_deferred_corridor_operand(
                                None, return_source=True, owner_frame=context, owner_kind=True
                            )
                            else context[4]
                        ),
                        *context[5:8],
                        None,
                    )
                    if isinstance(context, tuple) and len(context) in {8, 9}
                    else context
                )
                for context in self._active_replay_contexts
            ]
            evaluator.visit(callable_expr)

            keyword_bindings = []
            positional_segments = []
            unresolved_keyword_value_bindings = []
            if positional_override is None:
                for call_argument, unresolved in _expand_ordered_static_positional_arguments(
                    call.args
                ):
                    evaluator.visit(call_argument)
                    positional_segments.append(
                        (
                            (
                                (
                                    evaluator._resolve_iterable_element_binding(call_argument)
                                    or evaluator._conservative_argument_binding()
                                )
                                if unresolved
                                else evaluator._capture_argument_binding(call_argument)
                            ),
                            unresolved,
                        )
                    )

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
                            static_dict_bindings[str(key.value)] = (
                                evaluator._capture_argument_binding(value)
                            )
                        keyword_bindings.extend(static_dict_bindings.items())
                    else:
                        evaluator.visit(keyword.value)
                        unresolved_keyword_value_bindings.append(
                            evaluator._resolve_mapping_value_binding(keyword.value)
                            or evaluator._conservative_argument_binding()
                        )
            else:
                positional_segments.extend((binding, False) for binding in positional_override)
            unresolved_keywords = bool(unresolved_keyword_value_bindings)

            receiver_options = set()
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

        positional_parameters = [*function.args.posonlyargs, *function.args.args]
        keyword_parameters = {parameter.arg for parameter in function.args.args}
        keyword_parameters.update(parameter.arg for parameter in function.args.kwonlyargs)
        default_bindings = self._function_default_bindings.get(function, {})
        positional_capacity = len(positional_parameters) + 1

        def append_positional_binding(
            state: tuple[_ResolvedBinding, ...],
            binding: _ResolvedBinding,
        ) -> tuple[_ResolvedBinding, ...]:
            if len(state) < positional_capacity:
                return (*state, binding)
            return (
                *state[:-1],
                self._join_resolved_bindings([state[-1], binding]),
            )

        def merge_positional_states(
            states: Sequence[tuple[_ResolvedBinding, ...]],
        ) -> list[tuple[_ResolvedBinding, ...]]:
            grouped: dict[int, list[tuple[_ResolvedBinding, ...]]] = {}
            for state in states:
                grouped.setdefault(len(state), []).append(state)
            return [
                tuple(
                    self._join_resolved_bindings([state[index] for state in candidates])
                    for index in range(length)
                )
                for length, candidates in sorted(grouped.items())
            ]

        positional_variants: list[tuple[_ResolvedBinding, ...]] = [
            (
                (receiver_override or _ResolvedBinding(None, None),)
                if inject_receiver and positional_capacity > 0
                else ()
            )
            for inject_receiver in sorted(receiver_options)
        ]
        for binding, unresolved in positional_segments:
            if not unresolved:
                positional_variants = merge_positional_states(
                    [append_positional_binding(variant, binding) for variant in positional_variants]
                )
                continue
            expanded_variants: list[tuple[_ResolvedBinding, ...]] = []
            for variant in positional_variants:
                expanded_variants.append(variant)
                candidate = variant
                while len(candidate) < positional_capacity:
                    candidate = append_positional_binding(candidate, binding)
                    expanded_variants.append(candidate)
                if len(candidate) == positional_capacity:
                    expanded_variants.append(append_positional_binding(candidate, binding))
            positional_variants = merge_positional_states(expanded_variants)

        unresolved_keyword_binding = (
            self._join_resolved_bindings(unresolved_keyword_value_bindings)
            if unresolved_keyword_value_bindings
            else None
        )
        variadic_mapping_site = ast.Dict(keys=[], values=[])
        ast.copy_location(variadic_mapping_site, call)

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
            unexpected_keyword_bindings: list[tuple[str, _ResolvedBinding]] = []
            for name, binding in keyword_bindings:
                if name in keyword_parameters:
                    assignments.setdefault(name, []).append(binding)
                else:
                    unexpected_keyword_bindings.append((name, binding))

            if overflow_positional_bindings and function.args.vararg is None:
                return None
            if unexpected_keyword_bindings and function.args.kwarg is None:
                return None
            if any(len(candidates) > 1 for candidates in assignments.values()):
                return None
            for parameter in positional_parameters:
                if assignments.get(parameter.arg) or parameter.arg in default_bindings:
                    continue
                may_be_supplied = parameter in function.args.args and unresolved_keywords
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
                elif parameter in function.args.args and unresolved_keyword_binding is not None:
                    resolved[parameter.arg] = (
                        self._join_resolved_bindings(
                            [
                                default_bindings[parameter.arg],
                                unresolved_keyword_binding,
                            ]
                        )
                        if parameter.arg in default_bindings
                        else unresolved_keyword_binding
                    )
                elif parameter.arg in default_bindings:
                    resolved[parameter.arg] = default_bindings[parameter.arg]
                else:
                    resolved[parameter.arg] = _ResolvedBinding(None, None)

            for parameter in function.args.kwonlyargs:
                candidates = assignments.get(parameter.arg, [])
                if len(candidates) == 1:
                    resolved[parameter.arg] = candidates[0]
                elif len(candidates) > 1:
                    resolved[parameter.arg] = self._conservative_argument_binding()
                elif unresolved_keyword_binding is not None:
                    resolved[parameter.arg] = (
                        self._join_resolved_bindings(
                            [
                                default_bindings[parameter.arg],
                                unresolved_keyword_binding,
                            ]
                        )
                        if parameter.arg in default_bindings
                        else unresolved_keyword_binding
                    )
                elif parameter.arg in default_bindings:
                    resolved[parameter.arg] = default_bindings[parameter.arg]
                else:
                    resolved[parameter.arg] = _ResolvedBinding(None, None)

            if function.args.vararg is not None:
                resolved[function.args.vararg.arg] = self._variadic_iterable_binding(
                    overflow_positional_bindings,
                    ordered_items=(
                        tuple(overflow_positional_bindings)
                        if (
                            not any(unresolved for _value, unresolved in positional_segments)
                            and len(receiver_options) == 1
                            and len(positional_segments) + int(True in receiver_options)
                            <= positional_capacity
                        )
                        else None
                    ),
                )
            if function.args.kwarg is not None:
                mapping_entries = [
                    _StaticMappingEntry(
                        key=ast.Constant(value=name),
                        binding=binding,
                    )
                    for name, binding in unexpected_keyword_bindings
                ]
                mapping_entries.extend(
                    _StaticMappingEntry(key=None, binding=binding)
                    for binding in unresolved_keyword_value_bindings
                )
                resolved[function.args.kwarg.arg] = self._variadic_mapping_binding(
                    [
                        *(binding for _name, binding in unexpected_keyword_bindings),
                        *unresolved_keyword_value_bindings,
                    ],
                    mapping_entries=mapping_entries,
                    mapping_site=variadic_mapping_site,
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
        *,
        positional_override: Sequence[_ResolvedBinding] | None = None,
        captured_callee: _ResolvedBinding | None = None,
        captured_positional: Sequence[tuple[_ResolvedBinding, bool]] | None = None,
        captured_keywords: Sequence[tuple[str, _ResolvedBinding]] | None = None,
        captured_unresolved_keywords: Sequence[_ResolvedBinding] | None = None,
    ) -> dict[str, _ResolvedBinding] | None:
        if captured_callee is not None and (
            captured_positional is None
            or captured_keywords is None
            or captured_unresolved_keywords is None
        ):
            raise LegacyGrowthAnalysisError("incomplete captured canonical binder input")
        if template.function is None:
            if template.builtin_reference is None or any(
                keyword.arg is not None for keyword in node.keywords
            ):
                return None
            if positional_override is None and any(
                isinstance(argument, ast.Starred) for argument in node.args
            ):
                return None
            positional = [
                *template.partial_positional,
                *(
                    positional_override
                    if positional_override is not None
                    else [self._capture_argument_binding(argument) for argument in node.args]
                ),
            ]
            names = (
                ("object", "name", "value")
                if template.builtin_reference == "builtins.setattr"
                else ("object", "name", "default")
            )
            minimum = 3 if template.builtin_reference == "builtins.setattr" else 2
            maximum = 2 if template.builtin_reference == "builtins.delattr" else 3
            if not minimum <= len(positional) <= maximum:
                return None
            return dict(zip(names, positional))
        if (
            template.partial_unresolved
            or node.keywords
            or positional_override is None
            and any(isinstance(argument, ast.Starred) for argument in node.args)
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
        if captured_callee is not None:
            if captured_positional is None:
                raise AssertionError
            return self._resolve_call_argument_bindings(
                template.function,
                node,
                captured_callee=template.callee or captured_callee,
                captured_positional=[
                    *((binding, False) for binding in template.partial_positional),
                    *captured_positional,
                ],
                captured_keywords=captured_keywords,
                captured_unresolved_keywords=captured_unresolved_keywords,
            )
        positional = [
            *template.partial_positional,
            *(
                positional_override
                if positional_override is not None
                else [self._capture_argument_binding(argument) for argument in node.args]
            ),
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
        captured_callee: _ResolvedBinding | None = None,
        captured_positional: Sequence[tuple[_ResolvedBinding, bool]] | None = None,
        captured_keywords: Sequence[tuple[str, _ResolvedBinding]] | None = None,
        captured_unresolved_keywords: Sequence[_ResolvedBinding] | None = None,
    ) -> list[tuple[_FunctionNode, dict[str, _ResolvedBinding]]]:
        if captured_callee is not None and (
            captured_positional is None
            or captured_keywords is None
            or captured_unresolved_keywords is None
        ):
            raise LegacyGrowthAnalysisError("incomplete captured canonical binder input")
        if not self._replay_calls_enabled:
            return []
        awaited = id(node) in self._awaited_call_ids
        iterated = id(node) in self._iterated_call_ids
        replay_inputs: list[tuple[_FunctionNode, dict[str, _ResolvedBinding]]] = []
        partial_templates = {
            call
            for call in (
                captured_callee.deferred_calls
                if captured_callee is not None
                else self._resolve_deferred_calls(node.func)
            )
            if call.partial_template and call.function is not None
        }
        partial_targets = {call.function for call in partial_templates}
        for target in sorted(
            (
                captured_callee.callables
                if captured_callee is not None
                else self._resolve_callables(node.func)
            )
            - excluded_targets
            - partial_targets,
            key=lambda candidate: (
                candidate.lineno,
                candidate.col_offset,
                candidate.name,
                isinstance(candidate, ast.AsyncFunctionDef),
            ),
        ):
            generator = _function_is_generator(target)
            if (
                self._sync_only_body_analysis
                and self._analysis_purpose != "ownership_audit"
                and (generator or isinstance(target, ast.AsyncFunctionDef))
            ):
                continue
            if generator and not iterated:
                continue
            if (
                isinstance(target, ast.AsyncFunctionDef)
                and not awaited
                and (not iterated or not generator)
            ):
                continue
            arguments = self._resolve_call_argument_bindings(
                target,
                node,
                captured_callee=captured_callee,
                captured_positional=captured_positional,
                captured_keywords=captured_keywords,
                captured_unresolved_keywords=captured_unresolved_keywords,
            )
            if arguments is not None:
                replay_inputs.append((target, arguments))
            elif captured_callee is not None:
                request = self._invocation_outcome_request()
                if request is not None:
                    request.raise_scopes.append(self.scope.clone())
        for template in sorted(partial_templates, key=self._deferred_call_sort_key):
            if template.function is None:
                continue
            target = template.function
            if target in excluded_targets:
                continue
            generator = _function_is_generator(target)
            if (
                self._sync_only_body_analysis
                and self._analysis_purpose != "ownership_audit"
                and (generator or isinstance(target, ast.AsyncFunctionDef))
            ):
                continue
            if generator and not iterated:
                continue
            if (
                isinstance(target, ast.AsyncFunctionDef)
                and not awaited
                and (not iterated or not generator)
            ):
                continue
            arguments = self._resolve_partial_invocation_bindings(
                template,
                node,
                captured_callee=captured_callee,
                captured_positional=captured_positional,
                captured_keywords=captured_keywords,
                captured_unresolved_keywords=captured_unresolved_keywords,
            )
            if arguments is not None:
                replay_inputs.append((target, arguments))
            elif captured_callee is not None:
                request = self._invocation_outcome_request()
                if request is not None:
                    request.raise_scopes.append(self.scope.clone())
        return replay_inputs

    def _capture_deferred_calls(
        self,
        node: ast.Call,
        *,
        captured_callee: _ResolvedBinding | None = None,
        captured_positional: Sequence[tuple[_ResolvedBinding, bool]] | None = None,
        captured_keywords: Sequence[tuple[str, _ResolvedBinding]] | None = None,
        captured_unresolved_keywords: Sequence[_ResolvedBinding] | None = None,
    ) -> frozenset[_DeferredFunctionCall]:
        if captured_callee is not None and (
            captured_positional is None
            or captured_keywords is None
            or captured_unresolved_keywords is None
        ):
            raise LegacyGrowthAnalysisError("incomplete captured canonical binder input")
        if not self._replay_calls_enabled or (
            (not self._sync_only_body_analysis or self._analysis_purpose == "ownership_audit")
            and (id(node) in self._awaited_call_ids or id(node) in self._iterated_call_ids)
        ):
            return frozenset()
        deferred: set[_DeferredFunctionCall] = set()
        partial_templates = {
            call
            for call in (
                captured_callee.deferred_calls
                if captured_callee is not None
                else self._resolve_deferred_calls(node.func)
            )
            if call.partial_template and call.function is not None
        }
        partial_targets = {call.function for call in partial_templates}
        for target in (
            captured_callee.callables
            if captured_callee is not None
            else self._resolve_callables(node.func)
        ) - partial_targets:
            is_generator = _function_is_generator(target)
            is_coroutine = isinstance(target, ast.AsyncFunctionDef) and not is_generator
            if not (is_generator or is_coroutine):
                continue
            arguments = self._resolve_call_argument_bindings(
                target,
                node,
                captured_callee=captured_callee,
                captured_positional=captured_positional,
                captured_keywords=captured_keywords,
                captured_unresolved_keywords=captured_unresolved_keywords,
            )
            if arguments is not None:
                deferred.add(
                    _DeferredFunctionCall(
                        function=target,
                        arguments=tuple(sorted(arguments.items())),
                        value_key=self._deferred_value_key(
                            node, actual_construction=captured_callee is not None
                        ),
                        execution="iterate" if is_generator else "await",
                    )
                )
            elif captured_callee is not None:
                request = self._invocation_outcome_request()
                if request is not None:
                    request.raise_scopes.append(self.scope.clone())
        self._register_private_deferred_creation(node, deferred)
        normalized: set[_DeferredFunctionCall] = set()
        for call in deferred:
            key = call.value_key
            if key is not None and key[0] == "summary":
                call = _DeferredFunctionCall(
                    None, (), execution=call.execution, value_key=key, payload_known=False
                )
            normalized.add(call)
            if key is not None and self._deferred_progress(key) is None:
                self._set_deferred_progress(key, "available")
        return frozenset(normalized)

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
        target.ordered_items = dict(snapshot.ordered_items)
        target.call_receivers = dict(snapshot.call_receivers)
        target.bound_names = set(snapshot.bound_names)
        target.possibly_bound_names = set(snapshot.possibly_bound_names)

    @staticmethod
    def _deferred_call_sort_key(call: _DeferredFunctionCall) -> tuple[object, ...]:
        source = call.value_key[1] if call.value_key is not None else call.function
        context = call.value_key[2] if call.value_key is not None else ()
        return (
            getattr(source, "lineno", -1),
            getattr(source, "col_offset", -1),
            call.operation,
            call.function.name if call.function is not None else call.builtin_reference or "",
            tuple(
                (
                    getattr(node, "lineno", -1),
                    getattr(node, "col_offset", -1),
                    -1 if index is None else index,
                )
                for node, index in context
            ),
            tuple(
                (name, binding.reference or "", binding.string or "")
                for name, binding in call.arguments
            ),
            call.partial_template,
            tuple(
                (binding.reference or "", binding.string or "")
                for binding in call.partial_positional
            ),
            call.partial_unresolved,
        )

    def _deferred_progress(self, key: _DeferredValueKey) -> _DeferredProgress | None:
        return next(
            (
                record
                for record in self._consumed_deferred_calls
                if isinstance(record, tuple) and record[0] == key
            ),
            None,
        )

    def _set_deferred_progress(
        self,
        key: _DeferredValueKey,
        phase: Literal["available", "active", "consumed", "unknown"],
        result: _ResolvedBinding | None = None,
    ) -> None:
        self._consumed_deferred_calls = {
            record
            for record in self._consumed_deferred_calls
            if not isinstance(record, tuple) or record[0] != key
        }
        self._consumed_deferred_calls.add((key, phase, result))

    def _original_callable(self, function: _FunctionNode) -> ast.AST:
        if function in self._source_nodes():
            return function
        expression = self._deferred_generator_expression_for(function)
        if expression is not None:
            return expression[0]
        for original_id, bound in self._lambda_function_bindings.items():
            if bound is function:
                original = next(
                    (
                        node
                        for node in self._source_nodes()
                        if isinstance(node, ast.Lambda) and id(node) == original_id
                    ),
                    None,
                )
                if original is not None:
                    return original
        for (prototype, _context), bound in self._function_binding_nodes.items():
            if bound is function and prototype is not function:
                return self._original_callable(prototype)
        raise LegacyGrowthAnalysisError("deferred callback has no original parsed callable origin")

    def _deferred_value_key(
        self,
        node: ast.AST,
        *,
        child: ast.AST | None = None,
        actual_construction: bool = False,
        captured_operation: Literal["to_thread"] | None = None,
    ) -> _DeferredValueKey:
        frames = [
            context
            for context in self._active_replay_contexts
            if isinstance(context, tuple) and len(context) in {8, 9}
        ]
        private = next(
            (
                context
                for context in reversed(frames)
                if node in context[4]
                and (
                    actual_construction
                    and node
                    in self._private_deferred_corridor_operand(
                        node,
                        return_source=True,
                        owner_frame=context,
                        child=child,
                        captured_operation=captured_operation,
                    )
                    if self._private_deferred_corridor_operand(
                        None, return_source=True, owner_frame=context, owner_kind=True
                    )
                    else child is None
                )
            ),
            None,
        )
        context_tokens: list[tuple[ast.AST, int | None]] = []
        for frame in frames:
            owner = frame[1]
            repeated_loop = isinstance(owner, ast.While) or (
                isinstance(owner, (ast.For, ast.AsyncFor))
                and id(owner.iter) not in self._iterated_call_ids
            )
            if private is None and repeated_loop:
                return ("summary", node, (*context_tokens, (cast(ast.AST, owner), None)), child)
            if isinstance(owner, ast.Call) and owner is not node and owner in self._source_nodes():
                context_tokens.append((owner, None))
            context_tokens.extend(cast(tuple[tuple[ast.AST, int | None], ...], frame[3]))
        if node not in self._source_nodes():
            raise LegacyGrowthAnalysisError(
                "deferred construction has no original parsed source origin"
            )
        return (
            "transient" if private is not None else "precise",
            node,
            tuple(context_tokens),
            child,
        )

    def _register_private_deferred_creation(
        self, node: ast.Call, descriptors: AbstractSet[_DeferredFunctionCall]
    ) -> None:
        groups: dict[_DeferredValueKey, set[_DeferredFunctionCall]] = {}
        for call in descriptors:
            if call.value_key is not None and call.value_key[0] == "transient":
                groups.setdefault(call.value_key, set()).add(call)
        if not groups:
            return
        owners: dict[int, set[_DeferredFunctionCall]] = {}
        entries: list[_DeferredFlowSnapshot] = []
        for key, calls in groups.items():
            if node not in self._source_nodes() or key[1] is not node:
                raise LegacyGrowthAnalysisError("private creation has no actual source origin")
            owner = next(
                (
                    index
                    for index in range(len(self._active_replay_contexts) - 1, -1, -1)
                    if isinstance((frame := self._active_replay_contexts[index]), tuple)
                    and len(frame) in {8, 9}
                    and node in frame[4]
                    and (
                        node
                        in self._private_deferred_corridor_operand(
                            node,
                            return_source=True,
                            owner_frame=frame,
                            child=key[3],
                            captured_operation=(
                                "to_thread"
                                if all(
                                    call.operation == "to_thread" and call.execution == "await"
                                    for call in calls
                                )
                                else None
                            ),
                        )
                        if self._private_deferred_corridor_operand(
                            None, return_source=True, owner_frame=frame, owner_kind=True
                        )
                        else key[3] is None
                    )
                ),
                None,
            )
            if owner is None:
                raise LegacyGrowthAnalysisError("transient creation lost its positive source owner")
            frame = cast(tuple[object, ...], self._active_replay_contexts[owner])
            if frame[6] is None:
                raise LegacyGrowthAnalysisError("private creation has no entry Flow")
            entries.append(cast(_DeferredFlowSnapshot, frame[6]))
            owners.setdefault(owner, set()).update(calls)
        self._live_deferred_scopes(self.scope, reject_keys=frozenset(groups), extra_flows=entries)
        for owner, calls in owners.items():
            frame = cast(tuple[object, ...], self._active_replay_contexts[owner])
            self._active_replay_contexts[owner] = (
                *frame[:5],
                (*cast(tuple[_DeferredFunctionCall, ...], frame[5]), *calls),
                *frame[6:],
            )
        for key in groups:
            self._set_deferred_progress(key, "available")

    def _install_deferred_value(self, node: ast.Call, call: _DeferredFunctionCall) -> None:
        key = call.value_key
        if key is None:
            raise LegacyGrowthAnalysisError("deferred value has no source identity")
        if key[0] == "summary":
            call = _DeferredFunctionCall(
                None,
                (),
                operation=call.operation,
                execution=call.execution,
                value_key=key,
                payload_known=False,
            )
        if key[0] == "transient":
            self._register_private_deferred_creation(node, frozenset({call}))
        else:
            present = self._deferred_progress(key)
            if present is not None and key[0] != "summary":
                raise LegacyGrowthAnalysisError(
                    "a distinct deferred creation reused an existing precise identity"
                )
            if present is None:
                self._set_deferred_progress(key, "available")
        binding = _ResolvedBinding(
            _POSSIBLE_APP_CALL_REFERENCE if not call.payload_known else _KNOWN_NON_APP_REFERENCE,
            _DYNAMIC_STRING_BINDING if not call.payload_known else None,
            deferred_calls=frozenset({call}),
            ordered_items=(
                ()
                if call.operation in {"map", "filter", "starmap"}
                and any(value.ordered_items == () for value in call.operands)
                else None
            ),
        )
        if isinstance(node, ast.Call) and node.args and len(call.operands) == 1:
            source = node.args[0]
            identity = False
            if call.operation == "filter":
                identity = isinstance(source, ast.Constant) and source.value is None
            elif call.operation == "map" and isinstance(source, ast.Lambda):
                parameters = (*source.args.posonlyargs, *source.args.args)
                identity = (
                    len(parameters) == 1
                    and not source.args.defaults
                    and not source.args.kwonlyargs
                    and source.args.vararg is None
                    and source.args.kwarg is None
                    and isinstance(source.body, ast.Name)
                    and source.body.id == parameters[0].arg
                )
            if identity:
                binding = replace(binding, iterable_element=call.operands[0].iterable_element)
        self._call_result_bindings[id(node)] = binding
        self._deferred_call_bindings[id(node)] = binding.deferred_calls

    def _captured_instance_references(self, binding: _ResolvedBinding) -> frozenset[str]:
        """Select existing instance owners, excluding their member references."""

        return frozenset(
            reference
            for reference in {*binding.class_references, binding.reference or ""}
            if reference.startswith(_INSTANCE_REFERENCE_PREFIX)
            and reference.replace(_INSTANCE_REFERENCE_PREFIX, _CLASS_REFERENCE_PREFIX, 1)
            in self._class_mros
        )

    def _visit_captured_deferred_constructor(
        self,
        node: ast.Call,
        iterable_callback_inputs: (
            list[
                tuple[
                    ast.Call,
                    str,
                    _FunctionNode | _DeferredFunctionCall,
                    dict[str, _ResolvedBinding],
                ]
            ]
            | None
        ),
        *,
        iteration_result_node: ast.expr | None = None,
    ) -> bool | None:
        references = {
            "builtins.map": "map",
            "builtins.filter": "filter",
            "itertools.starmap": "starmap",
            "asyncio.to_thread": "to_thread",
        }
        if self._resolve_reference(node.func) not in references:
            return False
        if self.visit(node.func) is False and self._invocation_outcome_request() is not None:
            return None
        wrapper = self._capture_argument_binding(node.func)
        positional: list[_ResolvedBinding] = []
        unresolved = False
        for argument in node.args:
            if isinstance(argument, ast.Starred):
                if (
                    self.visit(argument.value) is False
                    and self._invocation_outcome_request() is not None
                ):
                    return None
                values = self._resolve_ordered_items(argument.value)
                if values is None:
                    unresolved = True
                else:
                    positional.extend(values)
            else:
                if self.visit(argument) is False and self._invocation_outcome_request() is not None:
                    return None
                positional.append(self._capture_argument_binding(argument))
        keywords: list[tuple[str, _ResolvedBinding]] = []
        unknown_keywords: list[_ResolvedBinding] = []
        for keyword in node.keywords:
            if (
                self.visit(keyword.value) is False
                and self._invocation_outcome_request() is not None
            ):
                return None
            captured = self._capture_argument_binding(keyword.value)
            if keyword.arg is not None:
                keywords.append((keyword.arg, captured))
            elif captured.mapping is not None:
                for entry in _effective_static_mapping_entries(captured.mapping.entries):
                    literal = _literal_value(entry.key) if entry.key is not None else None
                    if isinstance(literal, str):
                        keywords.append((literal, entry.binding))
                    else:
                        unknown_keywords.append(entry.binding)
            else:
                unknown_keywords.append(
                    captured.iterable_element or self._conservative_argument_binding()
                )
        request = self._invocation_outcome_request()
        operation = references.get(wrapper.reference or "")
        if operation is None:
            # The wrapper expression changed while it was evaluated. Do not infer
            # a callable from the old pre-evaluation reference.
            self._call_result_bindings[id(node)] = self._conservative_argument_binding()
            if request is not None:
                self._terminal_controls.raise_scopes.append(self.scope.clone())
            return True
        if (
            not positional
            or operation != "to_thread"
            and (
                keywords
                or unknown_keywords
                or len(positional) < 2
                or operation in {"filter", "starmap"}
                and len(positional) != 2
            )
        ):
            self._call_result_bindings[id(node)] = _ResolvedBinding(_KNOWN_NON_APP_REFERENCE, None)
            if request is not None:
                self._terminal_controls.raise_scopes.append(self.scope.clone())
                if not unresolved:
                    return None
            return True
        callee = positional[0]
        # Capturing an object does not select its implicit __call__ descriptor.
        # A captured explicit member is already a function/receiver value.
        if self._captured_instance_references(callee):
            callee = replace(
                callee, callables=frozenset(), descriptors=frozenset(), call_receivers=frozenset()
            )
        call = _DeferredFunctionCall(
            None,
            (),
            operation=cast(Literal["map", "filter", "starmap", "to_thread"], operation),
            value_key=self._deferred_value_key(
                node,
                actual_construction=True,
                captured_operation="to_thread" if operation == "to_thread" else None,
            ),
            execution="await" if operation == "to_thread" else "iterate",
            callee=callee,
            operands=tuple(positional[1:]),
            keywords=tuple(keywords),
            unresolved_keywords=tuple(unknown_keywords),
            payload_known=not unresolved,
        )
        self._install_deferred_value(node, call)
        if iterable_callback_inputs is not None and operation != "to_thread":
            iterable_callback_inputs.extend(
                (node, "deferred-iterate", descriptor, dict(descriptor.arguments))
                for descriptor in self._resolve_deferred_calls(node)
            )
        if id(node) in self._awaited_call_ids and operation == "to_thread":
            request = self._invocation_outcome_request()
            call_offsets = (
                (len(request.return_scopes), len(request.raise_scopes))
                if request is not None
                else None
            )
            result = self._replay_deferred_calls(
                self._resolve_deferred_calls(node), execution="await"
            )
            if request is not None:
                if call_offsets is None:
                    raise AssertionError
                if not self._resume_invocation_outcomes(request, call_offsets):
                    return None
            if result is not None:
                self._call_result_bindings[id(node)] = result
        elif id(node) in self._iterated_call_ids and operation != "to_thread":
            request = self._invocation_outcome_request()
            call_offsets = (
                (len(request.return_scopes), len(request.raise_scopes))
                if request is not None
                else None
            )
            self._replay_deferred_calls(
                self._resolve_deferred_calls(node),
                execution="iterate",
                iteration_result_node=iteration_result_node,
            )
            if request is not None:
                if call_offsets is None:
                    raise AssertionError
                if iteration_result_node is not None:
                    if not request.return_scopes[call_offsets[0] :]:
                        return None
                elif not self._resume_invocation_outcomes(request, call_offsets):
                    return None
        return True

    def _captured_callback_callee(self, callee: _ResolvedBinding) -> _ResolvedBinding:
        owners = self._captured_instance_references(callee)
        if not owners:
            return callee
        targets = frozenset().union(
            *(
                self._class_member_callables.get((owner, "__call__"), frozenset())
                for owner in owners
            )
        )
        receivers: set[tuple[_FunctionNode, str, _ResolvedBinding]] = set()
        descriptors: set[_DescriptorBinding] = set()
        for owner in owners:
            for target in self._class_member_callables.get((owner, "__call__"), ()):
                kinds = {
                    kind
                    for function, kind in self._class_member_descriptors.get(
                        (owner, "__call__"), ()
                    )
                    if function is target
                }
                if "staticmethod" in kinds:
                    descriptors.add((target, "unbound"))
                elif "classmethod" in kinds:
                    reference = owner.replace(
                        _INSTANCE_REFERENCE_PREFIX, _CLASS_REFERENCE_PREFIX, 1
                    )
                    receivers.add(
                        (
                            target,
                            "bound",
                            _ResolvedBinding(
                                reference, None, class_references=frozenset({reference})
                            ),
                        )
                    )
                else:
                    receivers.add((target, "bound", callee))
        return replace(
            callee,
            callables=targets,
            descriptors=frozenset(descriptors),
            call_receivers=frozenset(receivers),
        )

    def _invoke_captured_callback(
        self,
        call: _DeferredFunctionCall,
        positional: Sequence[_ResolvedBinding],
        *,
        row: int | None = None,
        charge_row: bool = False,
    ) -> _ResolvedBinding | None:
        request = self._invocation_outcome_request()
        if call.callee is None or call.value_key is None:
            if request is not None:
                self._unknown_invocation_outcomes(request)
            return self._conservative_argument_binding()
        callee = self._captured_callback_callee(call.callee)
        inputs: list[tuple[_FunctionNode, dict[str, _ResolvedBinding]]] = []
        templates = {
            template
            for template in callee.deferred_calls
            if template.partial_template and template.function is not None
        }
        targets = callee.callables - {template.function for template in templates}
        creation = cast(ast.Call, call.value_key[1])
        for target in sorted(
            targets, key=lambda value: (value.lineno, value.col_offset, value.name)
        ):
            with self._suspend_invocation_outcomes():
                arguments = self._resolve_call_argument_bindings(
                    target,
                    creation,
                    captured_callee=callee,
                    captured_positional=[(binding, False) for binding in positional],
                    captured_keywords=call.keywords,
                    captured_unresolved_keywords=call.unresolved_keywords,
                )
            if arguments is not None:
                inputs.append((target, arguments))
            elif request is not None:
                request.raise_scopes.append(self.scope.clone())
        for template in sorted(templates, key=self._deferred_call_sort_key):
            if template.function is None:
                continue
            template_callee = self._captured_callback_callee(template.callee or callee)
            implicit_owner = bool(self._captured_instance_references(template_callee))
            template_targets = (
                template_callee.callables if implicit_owner else frozenset({template.function})
            )
            for target in sorted(
                template_targets, key=lambda value: (value.lineno, value.col_offset, value.name)
            ):
                with self._suspend_invocation_outcomes():
                    arguments = self._resolve_call_argument_bindings(
                        target,
                        creation,
                        captured_callee=template_callee,
                        captured_positional=[
                            (binding, False)
                            for binding in (*template.partial_positional, *positional)
                        ],
                        captured_keywords=call.keywords,
                        captured_unresolved_keywords=(
                            (*call.unresolved_keywords, self._conservative_argument_binding())
                            if template.partial_unresolved
                            else call.unresolved_keywords
                        ),
                    )
                if arguments is not None:
                    inputs.append((target, arguments))
                elif request is not None:
                    request.raise_scopes.append(self.scope.clone())
        if not inputs:
            if request is not None and not targets and not templates:
                self._unknown_invocation_outcomes(request)
            return None
        active = self.scope
        entry = self._capture_deferred_flow(active)
        outcomes: list[_LexicalBindings] = []
        results: list[_ResolvedBinding] = []
        context = cast(tuple[object, ...], self._active_replay_contexts[-1])
        self._active_replay_contexts[-1] = (
            *context[:3],
            (
                *cast(tuple[tuple[ast.AST, int | None], ...], context[3]),
                *call.value_key[2],
                (creation, row),
            ),
            *context[4:],
        )
        private_children_registered = False
        private_child_batch: dict[int, _DeferredFunctionCall] = {}
        try:
            for input_index, (target, arguments) in enumerate(inputs):
                self._restore_deferred_flow(entry)
                self.scope = active
                if charge_row:
                    self._consume_loop_iteration()
                normal_offset = len(request.return_scopes) if request is not None else 0
                if _function_is_generator(target) or isinstance(target, ast.AsyncFunctionDef):
                    key = self._deferred_value_key(
                        creation, child=self._original_callable(target), actual_construction=True
                    )
                    if key[0] == "transient" and not private_children_registered:
                        for candidate_index, (candidate, captured) in enumerate(inputs):
                            if not (
                                _function_is_generator(candidate)
                                or isinstance(candidate, ast.AsyncFunctionDef)
                            ):
                                continue
                            candidate_key = self._deferred_value_key(
                                creation,
                                child=self._original_callable(candidate),
                                actual_construction=True,
                            )
                            if candidate_key[0] == "transient":
                                private_child_batch[candidate_index] = _DeferredFunctionCall(
                                    candidate,
                                    tuple(sorted(captured.items())),
                                    value_key=candidate_key,
                                    execution=(
                                        "iterate" if _function_is_generator(candidate) else "await"
                                    ),
                                )
                        self._register_private_deferred_creation(
                            creation, frozenset(private_child_batch.values())
                        )
                        private_children_registered = True
                    child = _DeferredFunctionCall(
                        target,
                        tuple(sorted(arguments.items())),
                        value_key=key,
                        execution="iterate" if _function_is_generator(target) else "await",
                    )
                    if input_index in private_child_batch:
                        child = private_child_batch[input_index]
                    if key[0] == "summary":
                        child = _DeferredFunctionCall(
                            None, (), execution=child.execution, value_key=key, payload_known=False
                        )
                    if self._deferred_progress(key) is None:
                        self._set_deferred_progress(key, "available")
                    result = _ResolvedBinding(
                        _KNOWN_NON_APP_REFERENCE, None, deferred_calls=frozenset({child})
                    )
                    if request is not None:
                        request.return_scopes.append(self.scope.clone())
                else:
                    result = self._replay_function_call(target, arguments)
                if request is None:
                    results.append(result)
                    outcomes.append(self.scope.clone())
                else:
                    self._remember_captured_binding(result)
                    if len(request.return_scopes) > normal_offset:
                        results.append(result)
            if request is None:
                self._merge_outcomes(active, outcomes)
            else:
                self._restore_deferred_flow(entry)
            self.scope = active
        finally:
            latest = cast(tuple[object, ...], self._active_replay_contexts[-1])
            self._active_replay_contexts[-1] = (*latest[:3], context[3], *latest[4:])
        return self._join_resolved_bindings(results) if results else None

    def _execute_captured_deferred(self, call: _DeferredFunctionCall) -> _ResolvedBinding:
        request = self._invocation_outcome_request()
        if not call.payload_known or call.callee is None:
            raise LegacyGrowthAnalysisError(
                "deferred callback payload is unknown at the finite summary boundary"
            )
        if call.operation == "to_thread":
            return (
                self._invoke_captured_callback(call, call.operands)
                or self._conservative_argument_binding()
            )
        if not call.operands:
            if request is not None:
                request.return_scopes.append(self.scope.clone())
            return _ResolvedBinding(_KNOWN_NON_APP_REFERENCE, None)
        for operand in call.operands:
            offsets = (
                (len(request.return_scopes), len(request.raise_scopes))
                if request is not None
                else None
            )
            self._replay_deferred_calls(operand.deferred_calls, execution="iterate")
            if request is not None:
                if offsets is None:
                    raise AssertionError
                if not self._resume_invocation_outcomes(
                    request, offsets, abrupt_output=request.raise_scopes
                ):
                    return _ResolvedBinding(None, None)
            if operand.ordered_items == ():
                if request is not None:
                    request.return_scopes.append(self.scope.clone())
                return _ResolvedBinding(_KNOWN_NON_APP_REFERENCE, None)
        if call.operation == "starmap":
            rows = call.operands[0].ordered_items
            if rows is None:
                raise LegacyGrowthAnalysisError(
                    "starmap rows have no captured ordered source facts"
                )
            results: list[_ResolvedBinding] = []
            for index, row in enumerate(rows):
                if row.ordered_items is None:
                    if request is not None:
                        raise LegacyGrowthAnalysisError(
                            "requested starmap row has no captured ordered source facts"
                        )
                    break
                offsets = (
                    (len(request.return_scopes), len(request.raise_scopes))
                    if request is not None
                    else None
                )
                result = self._invoke_captured_callback(
                    call, row.ordered_items, row=index, charge_row=True
                )
                if request is not None:
                    if offsets is None:
                        raise AssertionError
                    if not self._resume_invocation_outcomes(
                        request, offsets, abrupt_output=request.raise_scopes
                    ):
                        return _ResolvedBinding(None, None)
                    result = result or self._conservative_argument_binding()
                if result is None:
                    break
                results.append(result)
            if request is not None:
                request.return_scopes.append(self.scope.clone())
            return (
                self._join_resolved_bindings(results)
                if results
                else _ResolvedBinding(_KNOWN_NON_APP_REFERENCE, None)
            )
        operands = [
            self._deferred_result_element(value) or self._conservative_argument_binding()
            for value in call.operands
        ]
        creation = call.value_key[1] if call.value_key is not None else None
        callback_source = (
            creation.args[0] if isinstance(creation, ast.Call) and creation.args else None
        )
        if (
            call.operation == "filter"
            and isinstance(callback_source, ast.Constant)
            and callback_source.value is None
        ):
            if request is not None:
                request.return_scopes.append(self.scope.clone())
            return operands[0]
        if call.operation == "map" and isinstance(callback_source, ast.Lambda):
            parameters = (*callback_source.args.posonlyargs, *callback_source.args.args)
            if (
                len(operands) == len(parameters) == 1
                and not callback_source.args.defaults
                and not callback_source.args.kwonlyargs
                and callback_source.args.vararg is None
                and callback_source.args.kwarg is None
                and isinstance(callback_source.body, ast.Name)
                and callback_source.body.id == parameters[0].arg
            ):
                if request is not None:
                    request.return_scopes.append(self.scope.clone())
                return operands[0]
        offsets = (
            (len(request.return_scopes), len(request.raise_scopes)) if request is not None else None
        )
        result = self._invoke_captured_callback(call, operands)
        if request is not None:
            if offsets is None:
                raise AssertionError
            if not self._resume_invocation_outcomes(
                request, offsets, abrupt_output=request.raise_scopes
            ):
                return _ResolvedBinding(None, None)
            request.return_scopes.append(self.scope.clone())
        return (
            operands[0]
            if call.operation == "filter"
            else result or self._conservative_argument_binding()
        )

    def _replay_deferred_calls(
        self,
        calls: AbstractSet[_DeferredFunctionCall],
        *,
        execution: str,
        iteration_result_node: ast.expr | None = None,
    ) -> _ResolvedBinding | None:
        request = self._invocation_outcome_request()
        if iteration_result_node is not None and (
            request is None
            or execution != "iterate"
            or not isinstance(iteration_result_node, (ast.Tuple, ast.List, ast.YieldFrom))
        ):
            raise LegacyGrowthAnalysisError("invalid current iteration projection")
        results: list[_ResolvedBinding] = []
        if iteration_result_node is not None:
            # An unresolved/disabled producer is never a proof of zero rows.
            self._call_result_bindings[id(iteration_result_node)] = self._variadic_iterable_binding(
                [self._conservative_argument_binding()]
            )
        if not self._replay_calls_enabled or (
            self._sync_only_body_analysis and self._analysis_purpose != "ownership_audit"
        ):
            if request is not None:
                if calls:
                    self._unknown_invocation_outcomes(request)
                else:
                    request.return_scopes.append(self.scope.clone())
            return (
                self._call_result_bindings[id(iteration_result_node)]
                if iteration_result_node is not None
                else None
            )
        eligible: list[_DeferredFunctionCall] = []
        rejected = False
        exhausted = False
        unresolved = False
        for call in calls:
            if call.partial_template:
                if request is not None:
                    rejected = True
                continue
            if call.execution is not None:
                supported = execution == call.execution
            elif call.operation != "real":
                supported = execution == ("await" if call.operation == "to_thread" else "iterate")
            elif call.function is not None:
                supported = (
                    execution == "iterate"
                    and (
                        self._deferred_generator_expression_for(call.function) is not None
                        or _function_is_generator(call.function)
                    )
                    or execution == "await"
                    and isinstance(call.function, ast.AsyncFunctionDef)
                    and not _function_is_generator(call.function)
                )
            else:
                supported = not call.payload_known
            if not supported:
                if request is not None:
                    rejected = rejected or call.payload_known
                    unresolved = unresolved or not call.payload_known
                continue
            if call.value_key is None:
                if call not in self._consumed_deferred_calls:
                    eligible.append(call)
                elif request is not None:
                    rejected = rejected or execution == "await"
                    if iteration_result_node is None:
                        exhausted = exhausted or execution == "iterate"
                    elif call.payload_known and (
                        call.operation in {"map", "filter", "starmap"}
                        or call.operation == "real"
                        and call.function is not None
                        and (
                            _function_is_generator(call.function)
                            or self._deferred_generator_expression_for(call.function) is not None
                        )
                    ):
                        exhausted = True
                    else:
                        unresolved = True
            else:
                progress = self._deferred_progress(call.value_key)
                if progress is None or progress[1] in {"available", "unknown"}:
                    eligible.append(call)
                elif request is not None:
                    if progress[1] == "active":
                        raise LegacyGrowthAnalysisError(
                            "requested deferred consumption reenters an active value"
                        )
                    rejected = rejected or execution == "await"
                    if iteration_result_node is None:
                        exhausted = exhausted or execution == "iterate"
                    elif call.payload_known and (
                        call.operation in {"map", "filter", "starmap"}
                        or call.operation == "real"
                        and call.function is not None
                        and (
                            _function_is_generator(call.function)
                            or self._deferred_generator_expression_for(call.function) is not None
                        )
                    ):
                        exhausted = True
                    else:
                        unresolved = True
        if request is not None:
            if rejected:
                request.raise_scopes.append(self.scope.clone())
            if exhausted:
                if iteration_result_node is not None:
                    empty = self._variadic_iterable_binding([])
                    self._call_result_bindings[id(iteration_result_node)] = empty
                    results.append(empty)
                request.return_scopes.append(self.scope.clone())
                if iteration_result_node is not None:
                    self._call_result_bindings[id(iteration_result_node)] = (
                        self._variadic_iterable_binding([self._conservative_argument_binding()])
                    )
            if unresolved:
                self._unknown_invocation_outcomes(request)
                if iteration_result_node is not None:
                    results.append(self._call_result_bindings[id(iteration_result_node)])
        if not eligible:
            if request is not None and not calls:
                request.return_scopes.append(self.scope.clone())
                if iteration_result_node is not None:
                    results.append(self._call_result_bindings[id(iteration_result_node)])
            return self._join_resolved_bindings(results) if results else None
        active = self.scope
        entry = self._capture_deferred_flow(active)
        outcomes: list[_LexicalBindings] = []
        for call in sorted(eligible, key=self._deferred_call_sort_key):
            self._restore_deferred_flow(entry)
            self.scope = active
            if call.value_key is not None:
                progress = self._deferred_progress(call.value_key)
                if progress is not None and progress[1] == "unknown":
                    raise LegacyGrowthAnalysisError(
                        "deferred consumption disagrees across incoming flows"
                    )
                self._set_deferred_progress(call.value_key, "active")
            offsets = (
                (len(request.return_scopes), len(request.raise_scopes))
                if request is not None
                else None
            )
            result = (
                self._execute_captured_deferred(call)
                if call.operation != "real"
                else (
                    self._execute_deferred_call(call)
                    if iteration_result_node is None
                    else self._execute_deferred_call(
                        call, iteration_result_node=iteration_result_node
                    )
                )
            )
            if request is not None:
                if offsets is None:
                    raise AssertionError
                has_normal = len(request.return_scopes) > offsets[0]
                self._remember_captured_binding(result)
                for items, offset, normal in (
                    (request.return_scopes, offsets[0], True),
                    (request.raise_scopes, offsets[1], False),
                ):
                    completed: list[_LexicalBindings] = []
                    for saved in items[offset:]:
                        state = saved._flow_snapshot
                        if state is None:
                            raise LegacyGrowthAnalysisError(
                                "requested deferred outcome has no saved Flow"
                            )
                        self._restore_deferred_flow(state)
                        resumed = saved.clone(capture_flow=False)
                        self.scope = resumed
                        resumed._flow_owner = self
                        if call.value_key is None:
                            self._consumed_deferred_calls.add(call)
                        else:
                            self._set_deferred_progress(
                                call.value_key, "consumed", result if normal else None
                            )
                        if normal and iteration_result_node is not None:
                            if (
                                call.operation == "real"
                                and call.function is not None
                                and _function_is_generator(call.function)
                                and self._deferred_generator_expression_for(call.function) is None
                            ):
                                projected = self._call_result_bindings.get(
                                    id(iteration_result_node)
                                )
                                if projected is None:
                                    raise LegacyGrowthAnalysisError(
                                        "fresh generator has no current iteration projection"
                                    )
                            elif call.operation in {"map", "filter", "starmap"}:
                                projected = (
                                    self._variadic_iterable_binding([])
                                    if call.operands
                                    and any(value.ordered_items == () for value in call.operands)
                                    else self._variadic_iterable_binding([result])
                                )
                            else:
                                projected = self._variadic_iterable_binding(
                                    [self._conservative_argument_binding()]
                                )
                            self._call_result_bindings[id(iteration_result_node)] = projected
                            self._remember_captured_binding(projected)
                            results.append(projected)
                        resumed._flow_snapshot = self._capture_deferred_flow(resumed)
                        completed.append(resumed)
                    items[offset:] = completed
                if has_normal and iteration_result_node is None:
                    results.append(result)
            else:
                if call.value_key is None:
                    self._consumed_deferred_calls.add(call)
                else:
                    self._set_deferred_progress(call.value_key, "consumed", result)
                results.append(result)
                outcomes.append(self.scope.clone())
        if request is None:
            self._merge_outcomes(active, outcomes)
        else:
            self._restore_deferred_flow(entry)
        self.scope = active
        return self._join_resolved_bindings(results) if results else None

    def _execute_deferred_call(
        self, call: _DeferredFunctionCall, *, iteration_result_node: ast.expr | None = None
    ) -> _ResolvedBinding:
        request = self._invocation_outcome_request()
        if not call.payload_known:
            raise LegacyGrowthAnalysisError(
                "deferred function payload is unknown at the finite summary boundary"
            )
        if call.function is None:
            if request is not None:
                self._unknown_invocation_outcomes(request)
            return _ResolvedBinding(None, None)
        previous_sync_only = self._sync_only_body_analysis
        if (
            previous_sync_only
            and self._replay_calls_enabled
            and self._analysis_purpose == "ownership_audit"
        ):
            self._sync_only_body_analysis = False
        try:
            deferred_expression = self._deferred_generator_expression_for(call.function)
            if deferred_expression is None:
                if iteration_result_node is not None and _function_is_generator(call.function):
                    return self._replay_function_call(
                        call.function,
                        dict(call.arguments),
                        iteration_result_node=iteration_result_node,
                    )
                return self._replay_function_call(call.function, dict(call.arguments))
            expression, expression_scope, outer_binding = deferred_expression
            previous = self.scope
            entry = self._capture_deferred_flow(previous) if request is not None else None
            previous_terminal = self._terminal_controls
            if request is not None:
                self._terminal_controls = _TerminalControlBindings(
                    return_scopes=[], raise_scopes=[]
                )
            self._switch_deferred_scope(expression_scope, restore_flow=False)
            try:
                continuation = self._visit_comprehension(
                    expression.generators,
                    [expression.elt],
                    outer_binding=outer_binding,
                )
                if request is not None:
                    if entry is None:
                        raise AssertionError
                    normal = [self.scope.clone()] if continuation is not False else []
                    for outcomes, destination in (
                        (normal, request.return_scopes),
                        (self._terminal_controls.raise_scopes, request.raise_scopes),
                    ):
                        for outcome in outcomes:
                            destination.append(
                                self._project_invocation_scope(outcome, previous, entry)
                            )
                    self._restore_deferred_flow(entry)
                    self.scope = previous
            finally:
                self._switch_deferred_scope(previous, restore_flow=False)
                self._terminal_controls = previous_terminal
            return _ResolvedBinding(None, None)
        finally:
            self._sync_only_body_analysis = previous_sync_only

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
        callable_binding: _ResolvedBinding | None = None,
        positional_override: Sequence[_ResolvedBinding] | None = None,
    ) -> frozenset[_DeferredFunctionCall]:
        if wrapper_reference != "functools.partial" or not node.args:
            return frozenset()
        callable_expr = node.args[0]
        nested_templates = {
            call
            for call in (
                callable_binding.deferred_calls
                if callable_binding is not None
                else self._resolve_deferred_calls(callable_expr)
            )
            if call.partial_template
        }
        unresolved = (
            bool(node.keywords)
            or positional_override is None
            and any(isinstance(argument, ast.Starred) for argument in node.args[1:])
        )
        positional = (
            tuple(positional_override)
            if positional_override is not None
            else (
                ()
                if unresolved
                else tuple(self._capture_argument_binding(argument) for argument in node.args[1:])
            )
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
                        builtin_reference=nested.builtin_reference,
                        callee=nested.callee,
                    )
                    for nested in nested_templates
                    if not (
                        nested.builtin_reference is not None
                        and any(keyword.arg is not None for keyword in node.keywords)
                    )
                }
            )

        builtin = (
            callable_binding.reference
            if callable_binding is not None
            else self._resolve_reference(callable_expr)
        )
        if builtin in {"builtins.getattr", "builtins.setattr", "builtins.delattr"}:
            if any(keyword.arg is not None for keyword in node.keywords):
                return frozenset()
            return frozenset(
                {
                    _DeferredFunctionCall(
                        function=None,
                        arguments=(),
                        partial_template=True,
                        partial_positional=positional,
                        partial_unresolved=unresolved,
                        builtin_reference=cast(
                            Literal["builtins.getattr", "builtins.setattr", "builtins.delattr"],
                            builtin,
                        ),
                    )
                }
            )
        return frozenset(
            _DeferredFunctionCall(
                function=target,
                arguments=(),
                partial_template=True,
                partial_positional=positional,
                partial_unresolved=unresolved,
                callee=callable_binding or self._capture_argument_binding(callable_expr),
            )
            for target in (
                callable_binding.callables
                if callable_binding is not None
                else self._resolve_callables(callable_expr)
            )
        )

    def _legacy_namespace_call_name(
        self,
        node: ast.Call,
        *,
        function_reference: str | None,
        receiver_reference: str | None,
    ) -> ast.AST | None:
        expanded_arguments, unresolved = _expand_static_positional_arguments(node.args)
        arguments: Sequence[ast.expr] = node.args if unresolved else expanded_arguments
        if (
            function_reference in _UNBOUND_DICT_LOOKUP_REFERENCES
            and len(arguments) >= 2
            and self._is_legacy_namespace_reference(receiver_reference)
        ):
            return arguments[1]
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr in _DICT_NAMESPACE_LOOKUP_METHODS
            and arguments
            and self._is_legacy_namespace_reference(receiver_reference)
        ):
            return arguments[0]
        if function_reference is not None and arguments:
            namespace, _separator, method = function_reference.rpartition(".")
            if namespace == "legacy_app.__dict__" and method in _DICT_NAMESPACE_LOOKUP_METHODS:
                return arguments[0]
        return None

    def visit_Call(
        self,
        node: ast.Call,
        *,
        iterable_callback_inputs: (
            list[
                tuple[
                    ast.Call,
                    str,
                    _FunctionNode | _DeferredFunctionCall,
                    dict[str, _ResolvedBinding],
                ]
            ]
            | None
        ) = None,
        iteration_result_node: ast.expr | None = None,
    ) -> None | Literal[False]:
        self._call_result_bindings.pop(id(node), None)
        self._deferred_call_bindings.pop(id(node), None)
        captured_constructor = (
            self._visit_captured_deferred_constructor(node, iterable_callback_inputs)
            if iteration_result_node is None
            else self._visit_captured_deferred_constructor(
                node, iterable_callback_inputs, iteration_result_node=iteration_result_node
            )
        )
        if captured_constructor is None:
            return False
        if captured_constructor:
            return None
        positional_arguments, unresolved_positional_sources = _expand_static_positional_arguments(
            node.args
        )
        lookup_arguments = node.args if unresolved_positional_sources else positional_arguments
        mapping_lookup_attribute = self._mapping_lookup_attribute(node)
        if mapping_lookup_attribute is not None:
            if (
                self.visit(mapping_lookup_attribute.value) is False
                and self._invocation_outcome_request() is not None
            ):
                return False
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
        mutated_mapping = (
            self._resolve_mapping(node.func.value)
            if (isinstance(node.func, ast.Attribute) and node.func.attr in _MAPPING_MUTATOR_METHODS)
            else None
        )
        if mutated_mapping is not None:
            escaped_mappings.append(mutated_mapping)
        known_empty_mappings: set[_StaticMapping] = set()
        if (
            mutated_mapping is not None
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "clear"
        ):
            known_empty_mappings.add(mutated_mapping)
        defer_mapping_mutation = (
            isinstance(node.func, ast.Attribute) and mutated_mapping is not None
        )
        mapping_lookup_receiver = self._capture_mapping_lookup_receiver(node)
        namespace_function_reference = self._resolve_reference(node.func)
        unbound_mutator_candidate = (
            namespace_function_reference is not None
            and namespace_function_reference.startswith("builtins.dict.")
            and namespace_function_reference.rpartition(".")[2] in _MAPPING_MUTATOR_METHODS
        )
        stored_legacy_mutator = (
            _namespace_mutator_method(namespace_function_reference, legacy_only=True) is not None
        )
        stored_module_mutator = (
            namespace_function_reference is not None
            and namespace_function_reference.startswith(f"{_MODULE_NAMESPACE_REFERENCE}.")
            and _namespace_mutator_method(namespace_function_reference) is not None
        )
        bound_mutator_candidate = (
            (isinstance(node.func, ast.Attribute) and node.func.attr in _MAPPING_MUTATOR_METHODS)
            or stored_legacy_mutator
            or stored_module_mutator
        )
        mutation_receiver_binding: _ResolvedBinding | None = (
            _ResolvedBinding("legacy_app.__dict__", None)
            if stored_legacy_mutator
            else (
                _ResolvedBinding(_MODULE_NAMESPACE_REFERENCE, None)
                if stored_module_mutator
                else None
            )
        )
        mutation_argument_bindings: list[_ResolvedBinding] = []
        mutation_function_references: dict[str, str] = {}
        namespace_receiver = (
            lookup_arguments[0]
            if namespace_function_reference in _UNBOUND_DICT_LOOKUP_REFERENCES and lookup_arguments
            else node.func.value if isinstance(node.func, ast.Attribute) else None
        )
        unbound_namespace_candidate = (
            namespace_function_reference in _UNBOUND_DICT_LOOKUP_REFERENCES
            and len(lookup_arguments) >= 2
        )
        namespace_name = (
            lookup_arguments[1]
            if unbound_namespace_candidate
            else self._legacy_namespace_call_name(
                node,
                function_reference=namespace_function_reference,
                receiver_reference=(
                    self._resolve_reference(namespace_receiver)
                    if namespace_receiver is not None
                    else None
                ),
            )
        )
        namespace_symbol_name = (
            self._resolve_string(namespace_name) if namespace_name is not None else None
        )
        getattr_candidate = (
            namespace_function_reference
            in {
                "builtins.getattr",
                _POSSIBLE_GETATTR_REFERENCE,
                "builtins.setattr",
                "builtins.delattr",
            }
            and len(lookup_arguments) >= 2
        )
        getattr_name = lookup_arguments[1] if getattr_candidate else None
        getattr_function_reference = namespace_function_reference
        getattr_receiver_binding: _ResolvedBinding | None = None
        getattr_member_binding: _ResolvedBinding | None = None
        implicit_instance_call = any(
            owner.startswith(_INSTANCE_REFERENCE_PREFIX)
            for owner in self._resolve_object_references(node.func)
        )
        wrapper_reference = self._resolve_reference(node.func)
        partial_constructor_candidate = wrapper_reference == "functools.partial" and bool(node.args)
        builtin_partial_invocation = any(
            call.builtin_reference is not None for call in self._resolve_deferred_calls(node.func)
        ) or (
            isinstance(node.func, ast.Call)
            and self._resolve_reference(node.func.func) == "functools.partial"
        )
        captured_partial_callable: _ResolvedBinding | None = None
        captured_partial_positional: list[_ResolvedBinding] = []
        captured_builtin_templates: frozenset[_DeferredFunctionCall] = frozenset()
        captured_builtin_arguments: list[_ResolvedBinding] = []
        dict_constructor_candidate = (
            wrapper_reference == "builtins.dict"
            and len(positional_arguments) <= 1
            and not unresolved_positional_sources
        )
        if dict_constructor_candidate:
            # A dict copy reads its positional container; named values can still escape.
            escaped_mappings = [
                mapping
                for keyword in node.keywords
                if keyword.arg is not None
                if (mapping := self._resolve_mapping(keyword.value)) is not None
            ]
        consumes_dict_iterable = dict_constructor_candidate and len(positional_arguments) == 1
        chain_candidate = (
            wrapper_reference in _ITERABLE_CONCATENATING_REFERENCES
            and not node.keywords
            and not unresolved_positional_sources
        )
        preserving_callback_wrapper = (
            not node.keywords
            and not unresolved_positional_sources
            and (
                wrapper_reference == "builtins.iter"
                and len(positional_arguments) == 1
                or wrapper_reference == "itertools.islice"
                and 2 <= len(positional_arguments) <= 4
            )
        )
        wrapper_consumption_empty = False
        if preserving_callback_wrapper and wrapper_reference == "itertools.islice":
            bounds = [_literal_value(argument) for argument in positional_arguments[1:]]
            invalid_bounds = (
                any(
                    value is not _UNRESOLVED_LITERAL_VALUE
                    and value is not None
                    and (not isinstance(value, int) or value < 0)
                    for value in bounds
                )
                or len(bounds) == 3
                and isinstance(bounds[2], int)
                and bounds[2] <= 0
            )
            preserving_callback_wrapper = not invalid_bounds
            start = 0 if len(bounds) == 1 else bounds[0]
            stop = bounds[0] if len(bounds) == 1 else bounds[1]
            wrapper_consumption_empty = stop == 0 and (start is None or start == 0)
        flattening_callback_wrapper = (
            wrapper_reference in _ITERABLE_FLATTENING_REFERENCES
            and not node.keywords
            and not unresolved_positional_sources
            and len(positional_arguments) == 1
            and isinstance(positional_arguments[0], (ast.List, ast.Tuple))
            and not any(isinstance(value, ast.Starred) for value in positional_arguments[0].elts)
        )
        collects_zip_callbacks = (
            (
                (
                    wrapper_reference in _ZIPPING_ITERABLE_BUILTIN_REFERENCES
                    or chain_candidate
                    or preserving_callback_wrapper
                    or flattening_callback_wrapper
                )
                and (id(node) in self._iterated_call_ids or iterable_callback_inputs is not None)
                or consumes_dict_iterable
            )
            and not unresolved_positional_sources
            and (
                consumes_dict_iterable
                or chain_candidate
                or preserving_callback_wrapper
                or flattening_callback_wrapper
                or not any(isinstance(argument, ast.Starred) for argument in node.args)
            )
        )
        zip_callback_inputs = (
            iterable_callback_inputs if iterable_callback_inputs is not None else []
        )
        owns_zip_callback_inputs = collects_zip_callbacks and iterable_callback_inputs is None
        zip_callback_end_indices: list[int] = []
        chain_operand_bindings: list[_ResolvedBinding] = []
        starmap_candidate = (
            wrapper_reference == "itertools.starmap"
            and len(lookup_arguments) == 2
            and not unresolved_positional_sources
            and not node.keywords
        )
        captures_lazy_callback = (
            (
                (iterable_callback_inputs is not None or id(node) in self._iterated_call_ids)
                and wrapper_reference in {"builtins.map", "builtins.filter"}
                and not unresolved_positional_sources
                and not node.keywords
                and not any(isinstance(argument, ast.Starred) for argument in node.args)
            )
            or starmap_candidate
            and (id(node) in self._iterated_call_ids or iterable_callback_inputs is not None)
        )
        captured_callback_targets: frozenset[_FunctionNode] = frozenset()
        captured_callback_templates: frozenset[_DeferredFunctionCall] = frozenset()
        captured_callback_scope: _LexicalBindings | None = None
        captured_callback_arguments: list[_ResolvedBinding] = []
        captured_starmap_rows: list[list[_ResolvedBinding] | None] = []
        captured_callback_empty = False
        reduce_candidate = (
            wrapper_reference == "functools.reduce"
            and len(positional_arguments) in {2, 3}
            and not unresolved_positional_sources
            and not node.keywords
            and isinstance(positional_arguments[1], (ast.List, ast.Tuple))
            and not any(isinstance(value, ast.Starred) for value in positional_arguments[1].elts)
        )
        captured_reduce_items: list[_ResolvedBinding] = []
        captured_reduce_initializer: _ResolvedBinding | None = None
        captured_dict_operand: _ResolvedBinding | None = None
        captured_dict_pair_entries: list[_StaticMappingEntry] | None = None
        captured_dict_keyword_entries: list[_StaticMappingEntry] = []
        dict_argument_alias: tuple[_LexicalBindings, str] | None = None
        wait_for_candidate = wrapper_reference == "asyncio.wait_for"
        wait_for_keywords = (
            {keyword.arg: keyword.value for keyword in node.keywords} if wait_for_candidate else {}
        )
        wait_for_operand = (
            positional_arguments[0] if positional_arguments else wait_for_keywords.get("fut")
        )
        wait_for_timeout = (
            positional_arguments[1]
            if len(positional_arguments) >= 2
            else wait_for_keywords.get("timeout")
        )
        wait_for_shape_valid = (
            wait_for_candidate
            and not unresolved_positional_sources
            and len(positional_arguments) <= 2
            and len(wait_for_keywords) == len(node.keywords)
            and all(name in {"fut", "timeout"} for name in wait_for_keywords)
            and not (positional_arguments and "fut" in wait_for_keywords)
            and not (len(positional_arguments) == 2 and "timeout" in wait_for_keywords)
            and wait_for_operand is not None
            and wait_for_timeout is not None
        )
        captured_wait_for_operand: _ResolvedBinding | None = None
        keys_callback = (
            wrapper_reference in {"builtins.sorted", "builtins.min", "builtins.max"}
            and bool(positional_arguments)
            and not unresolved_positional_sources
            and (wrapper_reference != "builtins.sorted" or len(positional_arguments) == 1)
            and any(keyword.arg == "key" for keyword in node.keywords)
        )
        key_input_binding: _ResolvedBinding | None = None
        key_replay_inputs: list[tuple[_FunctionNode, dict[str, _ResolvedBinding]]] = []
        if (
            not node.args
            and not node.keywords
            and self._is_proven_builtin_object_callable(node.func)
        ):
            self._call_result_bindings[id(node)] = _ResolvedBinding(
                reference=_KNOWN_NON_APP_REFERENCE,
                string=None,
            )
        unbound_mapping_receiver = (
            self._capture_mapping_receiver(positional_arguments[0])
            if (
                wrapper_reference
                in {
                    "builtins.dict.__getitem__",
                    "builtins.dict.get",
                    "builtins.dict.pop",
                    "builtins.dict.setdefault",
                }
                and len(positional_arguments) >= 2
                and not unresolved_positional_sources
            )
            else None
        )
        bound_mapping_alias_receiver = (
            self._capture_mapping_receiver(node.func)
            if (
                wrapper_reference
                in {
                    "builtins.dict.__getitem__",
                    "builtins.dict.get",
                    "builtins.dict.pop",
                    "builtins.dict.setdefault",
                }
                and self._resolve_mapping(node.func) is not None
                and positional_arguments
                and not unresolved_positional_sources
            )
            else None
        )
        known_pop_mapping = (
            mutated_mapping
            if isinstance(node.func, ast.Attribute) and node.func.attr == "pop"
            else None
        )
        known_pop_receiver = mapping_lookup_receiver if known_pop_mapping is not None else None
        known_pop_key = (
            positional_arguments[0]
            if known_pop_mapping is not None and positional_arguments
            else None
        )
        known_pop_has_default = known_pop_mapping is not None and len(positional_arguments) >= 2
        if wrapper_reference == "builtins.dict.pop" and unbound_mapping_receiver is not None:
            known_pop_mapping = unbound_mapping_receiver.mapping
            known_pop_receiver = unbound_mapping_receiver
            known_pop_key = positional_arguments[1]
            known_pop_has_default = len(positional_arguments) >= 3
        known_update_mapping = (
            mutated_mapping
            if isinstance(node.func, ast.Attribute) and node.func.attr == "update"
            else None
        )
        known_update_invalidation_count = (
            self._mapping_invalidation_counts.get(known_update_mapping, 0)
            if known_update_mapping is not None
            else None
        )
        known_setdefault_mapping = (
            mutated_mapping
            if isinstance(node.func, ast.Attribute) and node.func.attr == "setdefault"
            else None
        )
        known_setdefault_receiver = (
            mapping_lookup_receiver if known_setdefault_mapping is not None else None
        )
        known_setdefault_key = positional_arguments[0] if positional_arguments else None
        known_setdefault_default = (
            positional_arguments[1] if len(positional_arguments) >= 2 else None
        )
        if (
            wrapper_reference == "builtins.dict.setdefault"
            and unbound_mapping_receiver is not None
            and unbound_mapping_receiver.mapping is not None
            and len(positional_arguments) >= 2
        ):
            known_setdefault_mapping = unbound_mapping_receiver.mapping
            known_setdefault_receiver = unbound_mapping_receiver
            known_setdefault_key = positional_arguments[1]
            known_setdefault_default = (
                positional_arguments[2] if len(positional_arguments) >= 3 else None
            )
        elif (
            wrapper_reference == "builtins.dict.setdefault"
            and bound_mapping_alias_receiver is not None
            and bound_mapping_alias_receiver.mapping is not None
        ):
            known_setdefault_mapping = bound_mapping_alias_receiver.mapping
            known_setdefault_receiver = bound_mapping_alias_receiver
            known_setdefault_key = positional_arguments[0] if positional_arguments else None
            known_setdefault_default = (
                positional_arguments[1] if len(positional_arguments) >= 2 else None
            )
        known_setdefault_invalidation_count = (
            self._mapping_invalidation_counts.get(known_setdefault_mapping, 0)
            if known_setdefault_mapping is not None
            else None
        )
        unbound_iterator_method = (
            wrapper_reference.removeprefix("builtins.dict.")
            if (
                wrapper_reference in {"builtins.dict.items", "builtins.dict.values"}
                and len(positional_arguments) == 1
                and not unresolved_positional_sources
                and not node.keywords
            )
            else None
        )
        unbound_iterator_receiver = (
            self._capture_mapping_receiver(positional_arguments[0])
            if unbound_iterator_method is not None
            else None
        )
        bound_iterator_method = (
            wrapper_reference.removeprefix("builtins.dict.")
            if (
                wrapper_reference in {"builtins.dict.items", "builtins.dict.values"}
                and not positional_arguments
                and not unresolved_positional_sources
                and not node.keywords
                and self._resolve_mapping(node.func) is not None
            )
            else None
        )
        bound_iterator_receiver = (
            self._capture_mapping_receiver(node.func) if bound_iterator_method is not None else None
        )
        bound_mapping_copy = (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "copy"
            and not positional_arguments
            and not unresolved_positional_sources
            and not node.keywords
        )
        mapping_copy = (
            self._resolve_mapping(node.func.value)
            if bound_mapping_copy and isinstance(node.func, ast.Attribute)
            else None
        )
        popitem_receiver = (
            self._capture_mapping_receiver(node.func.value)
            if (
                isinstance(node.func, ast.Attribute)
                and node.func.attr == "popitem"
                and not positional_arguments
                and not unresolved_positional_sources
                and not node.keywords
            )
            else None
        )
        if popitem_receiver is not None and popitem_receiver.mapping is not None:
            effective_entries = _effective_static_mapping_entries(popitem_receiver.mapping.entries)
            if (
                len(effective_entries) == 1
                and effective_entries[0].key is not None
                and _literal_value(effective_entries[0].key) is not _UNRESOLVED_LITERAL_VALUE
            ):
                known_empty_mappings.add(popitem_receiver.mapping)
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
                "builtins.enumerate",
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
                "enumerate",
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
        # One incumbent operand decision governs both preparation and visits.
        async_iteration_candidate = id(node) in self._awaited_call_ids and (
            (
                wrapper_reference == "builtins.anext"
                and len(positional_arguments) in {1, 2}
                and not unresolved_positional_sources
                and not node.keywords
            )
            or (
                isinstance(node.func, ast.Attribute)
                and node.func.attr == "__anext__"
                and not node.args
                and not node.keywords
            )
        )
        if (
            getattr_candidate
            or unbound_namespace_candidate
            or unbound_mutator_candidate
            or bound_mutator_candidate
            or async_iteration_candidate
        ):
            operand_arm = "guarded"
        elif wait_for_candidate:
            operand_arm = "wait_for"
        elif keys_callback:
            operand_arm = "keys"
        elif reduce_candidate:
            operand_arm = "reduce"
        elif partial_constructor_candidate or builtin_partial_invocation:
            operand_arm = "partial"
        elif collects_zip_callbacks or dict_constructor_candidate:
            operand_arm = "collection"
        elif captures_lazy_callback:
            operand_arm = "lazy_callback"
        else:
            operand_arm = "ordinary"
        preparation_frame = cast(tuple[object, ...], self._active_replay_contexts[-1])
        self._active_replay_contexts[-1] = (*preparation_frame[:8], None)
        try:
            deferred_calls = (
                frozenset()
                if operand_arm == "ordinary" or implicit_instance_call
                else self._capture_deferred_calls(node)
            )
            if deferred_calls:
                self._deferred_call_bindings[id(node)] = deferred_calls
            argument_scope = None if operand_arm == "ordinary" else self.scope.detached_clone()
            initial_replay_inputs = (
                []
                if operand_arm == "ordinary" or implicit_instance_call
                else self._prepare_function_replay_inputs(node)
            )
        finally:
            updated_frame = cast(tuple[object, ...], self._active_replay_contexts[-1])
            self._active_replay_contexts[-1] = (
                *updated_frame[:8],
                preparation_frame[8],
            )
        initial_arguments = {target: arguments for target, arguments in initial_replay_inputs}
        prepared_targets = set(initial_arguments)
        invocation_entry: _LexicalBindings | None = None
        request = self._invocation_outcome_request()
        invocation_offsets = (
            (len(request.return_scopes), len(request.raise_scopes)) if request is not None else None
        )
        captured_callee: _ResolvedBinding | None = None
        captured_positional: list[tuple[_ResolvedBinding, bool]] = []
        captured_keywords: list[tuple[str, _ResolvedBinding]] = []
        captured_unresolved_keywords: list[_ResolvedBinding] = []
        if wrapped_call is not None and executes_async:
            self._awaited_call_ids.add(id(wrapped_call))
        for gathered_call in newly_awaited_gather_calls:
            self._awaited_call_ids.add(id(gathered_call))
        iterated_argument = (
            positional_arguments[0]
            if positional_arguments and not unresolved_positional_sources and consumes_iterable
            else None
        )
        iterated_argument_was_marked = (
            iterated_argument is not None and id(iterated_argument) in self._iterated_call_ids
        )
        if iterated_argument is not None:
            self._iterated_call_ids.add(id(iterated_argument))
        async_iteration_callee: str | None = None
        async_iteration_operand: _ResolvedBinding | None = None
        if defer_mapping_mutation:
            self._deferred_mapping_mutator_attribute_ids.add(id(node.func))
        if mapping_lookup_attribute is not None:
            self._previsited_call_receiver_attribute_ids.add(id(mapping_lookup_attribute))
        try:
            if operand_arm == "guarded":
                if (
                    self.visit(node.func) is False
                    and self._invocation_outcome_request() is not None
                ):
                    return False
                getattr_function_reference = self._resolve_reference(node.func)
                mutation_function_references = dict(
                    (self.reference_snapshots or {}).get(id(node.func), {})
                )
                if isinstance(node.func, ast.Name) and getattr_function_reference is not None:
                    mutation_function_references[node.func.id] = getattr_function_reference
                if async_iteration_candidate:
                    async_iteration_callee = getattr_function_reference
                    if isinstance(node.func, ast.Attribute) and node.func.attr == "__anext__":
                        async_iteration_operand = self._capture_argument_binding(node.func.value)
                if bound_mutator_candidate and isinstance(node.func, ast.Attribute):
                    mutation_receiver_binding = self._capture_argument_binding(node.func.value)
                for getattr_argument_index, getattr_argument in enumerate(lookup_arguments):
                    if (
                        self.visit(getattr_argument) is False
                        and self._invocation_outcome_request() is not None
                    ):
                        return False
                    if getattr_argument_index == 0:
                        getattr_receiver_binding = self._capture_argument_binding(getattr_argument)
                        if async_iteration_candidate:
                            async_iteration_operand = getattr_receiver_binding
                        if unbound_mutator_candidate and not stored_legacy_mutator:
                            mutation_receiver_binding = getattr_receiver_binding
                    elif getattr_argument_index == 1:
                        getattr_member_binding = self._capture_argument_binding(getattr_argument)
                    if (
                        self.filename == LEGACY_APP
                        and mutation_receiver_binding is not None
                        and mutation_receiver_binding.reference == _MODULE_NAMESPACE_REFERENCE
                    ):
                        captured_argument = (
                            getattr_receiver_binding
                            if getattr_argument_index == 0
                            else (getattr_member_binding if getattr_argument_index == 1 else None)
                        )
                        mutation_argument_bindings.append(
                            captured_argument
                            if captured_argument is not None
                            else self._capture_argument_binding(getattr_argument)
                        )
                for getattr_keyword in node.keywords:
                    if (
                        self.visit(getattr_keyword) is False
                        and self._invocation_outcome_request() is not None
                    ):
                        return False
            elif operand_arm == "wait_for":
                if (
                    self.visit(node.func) is False
                    and self._invocation_outcome_request() is not None
                ):
                    return False
                for argument in lookup_arguments:
                    if (
                        self.visit(argument) is False
                        and self._invocation_outcome_request() is not None
                    ):
                        return False
                    if argument is wait_for_operand:
                        captured_wait_for_operand = self._capture_argument_binding(argument)
                for keyword in node.keywords:
                    if (
                        self.visit(keyword) is False
                        and self._invocation_outcome_request() is not None
                    ):
                        return False
                    if keyword.value is wait_for_operand:
                        captured_wait_for_operand = self._capture_argument_binding(keyword.value)
            elif operand_arm == "keys":
                if (
                    self.visit(node.func) is False
                    and self._invocation_outcome_request() is not None
                ):
                    return False
                key_input_bindings: list[_ResolvedBinding] = []
                key_input_empty = False
                for argument in lookup_arguments:
                    if (
                        self.visit(argument) is False
                        and self._invocation_outcome_request() is not None
                    ):
                        return False
                    key_input_bindings.append(self._capture_argument_binding(argument))
                    if len(lookup_arguments) == 1:
                        key_input_empty = self._is_proven_empty_iterable(argument)
                key_input_binding = (
                    key_input_bindings[0].iterable_element or self._conservative_argument_binding()
                    if len(key_input_bindings) == 1
                    else self._join_resolved_bindings(key_input_bindings)
                )
                for keyword in node.keywords:
                    if (
                        self.visit(keyword) is False
                        and self._invocation_outcome_request() is not None
                    ):
                        return False
                    if keyword.arg != "key" or key_input_empty or not self._replay_calls_enabled:
                        continue
                    with self._suspend_invocation_outcomes():
                        key_replay_inputs.extend(
                            (target, arguments)
                            for target in sorted(
                                self._resolve_callables(keyword.value),
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
                                    callable_expr=keyword.value,
                                    positional_override=[key_input_binding],
                                )
                            )
                            is not None
                        )
            elif operand_arm == "reduce":
                if (
                    self.visit(node.func) is False
                    and self._invocation_outcome_request() is not None
                ):
                    return False
                for argument_index, argument in enumerate(positional_arguments):
                    if argument_index == 1 and isinstance(argument, (ast.List, ast.Tuple)):
                        if (
                            self.reference_snapshots is not None
                            or self.string_snapshots is not None
                        ):
                            self._record_snapshot(argument)
                        outer_exception_state = bool(self._exception_scope_collectors)
                        if outer_exception_state:
                            self._record_exception_scope()
                        for item in argument.elts:
                            if (
                                self.visit(item) is False
                                and self._invocation_outcome_request() is not None
                            ):
                                return False
                            captured_reduce_items.append(self._capture_argument_binding(item))
                            self._invalidate_mapping_aliases(item)
                        if (
                            self.visit(argument.ctx) is False
                            and self._invocation_outcome_request() is not None
                        ):
                            return False
                        if outer_exception_state:
                            self._record_exception_scope()
                        continue
                    if (
                        self.visit(argument) is False
                        and self._invocation_outcome_request() is not None
                    ):
                        return False
                    if argument_index == 0:
                        captured_callback_templates = frozenset(
                            call
                            for call in self._resolve_deferred_calls(argument)
                            if call.partial_template and call.function is not None
                        )
                        captured_callback_targets = self._resolve_callables(argument) - {
                            template.function for template in captured_callback_templates
                        }
                        captured_callback_scope = self.scope.detached_clone()
                    else:
                        captured_reduce_initializer = self._capture_argument_binding(argument)
            elif operand_arm == "partial":
                if (
                    self.visit(node.func) is False
                    and self._invocation_outcome_request() is not None
                ):
                    return False
                if builtin_partial_invocation:
                    callee_binding = self._capture_argument_binding(node.func)
                    captured_builtin_templates = frozenset(
                        call
                        for call in callee_binding.deferred_calls
                        if call.builtin_reference is not None
                    )
                    if captured_builtin_templates:
                        if not isinstance(node.func, ast.Name):
                            prior = self._call_result_bindings.get(id(node.func))
                            self._call_result_bindings[id(node.func)] = (
                                callee_binding
                                if prior is None
                                else self._join_resolved_bindings([prior, callee_binding])
                            )
                        if self.call_result_snapshots is not None:
                            prior_snapshot = self.call_result_snapshots.get(id(node.func))
                            self.call_result_snapshots[id(node.func)] = (
                                callee_binding
                                if prior_snapshot is None
                                else self._join_resolved_bindings([prior_snapshot, callee_binding])
                            )
                for argument_index, argument in enumerate(lookup_arguments):
                    if (
                        self.visit(argument) is False
                        and self._invocation_outcome_request() is not None
                    ):
                        return False
                    captured_partial_argument = self._capture_argument_binding(argument)
                    if partial_constructor_candidate:
                        if argument_index == 0:
                            captured_partial_callable = captured_partial_argument
                        else:
                            captured_partial_positional.append(captured_partial_argument)
                    else:
                        captured_builtin_arguments.append(captured_partial_argument)
                for keyword in node.keywords:
                    if (
                        self.visit(keyword) is False
                        and self._invocation_outcome_request() is not None
                    ):
                        return False
            elif operand_arm == "collection":
                if (
                    self.visit(node.func) is False
                    and self._invocation_outcome_request() is not None
                ):
                    return False
                exhausted_prefix = False
                for argument in (
                    lookup_arguments
                    if dict_constructor_candidate
                    or chain_candidate
                    or preserving_callback_wrapper
                    or flattening_callback_wrapper
                    else node.args
                ):
                    if flattening_callback_wrapper and isinstance(argument, (ast.List, ast.Tuple)):
                        if (
                            self.reference_snapshots is not None
                            or self.string_snapshots is not None
                        ):
                            self._record_snapshot(argument)
                        outer_exception_state = bool(self._exception_scope_collectors)
                        if outer_exception_state:
                            self._record_exception_scope()
                        for inner in argument.elts:
                            if (
                                isinstance(inner, ast.Call)
                                and self._resolve_reference(inner.func)
                                in {
                                    "builtins.zip",
                                    "builtins.map",
                                    "builtins.filter",
                                    "itertools.starmap",
                                    "builtins.iter",
                                    "itertools.islice",
                                }
                                | _ITERABLE_CONCATENATING_REFERENCES
                                | _ITERABLE_FLATTENING_REFERENCES
                            ):
                                if (
                                    self.visit(
                                        inner,
                                        iterable_callback_inputs=zip_callback_inputs,
                                    )
                                    is False
                                    and self._invocation_outcome_request() is not None
                                ):
                                    return False
                            else:
                                if (
                                    self.visit(inner) is False
                                    and self._invocation_outcome_request() is not None
                                ):
                                    return False
                            chain_operand_bindings.append(self._capture_argument_binding(inner))
                            inner_deferred = chain_operand_bindings[-1].deferred_calls
                            if len(inner_deferred) == 1:
                                deferred_input = next(iter(inner_deferred))
                                if (
                                    deferred_input.function is not None
                                    and not deferred_input.partial_template
                                    and (
                                        _function_is_generator(deferred_input.function)
                                        or self._deferred_generator_expression_for(
                                            deferred_input.function
                                        )
                                        is not None
                                    )
                                ):
                                    zip_callback_inputs.append(
                                        (
                                            node,
                                            "deferred-iterate",
                                            deferred_input,
                                            dict(deferred_input.arguments),
                                        )
                                    )
                            self._invalidate_mapping_aliases(inner)
                            zip_callback_end_indices.append(len(zip_callback_inputs))
                        if (
                            self.visit(argument.ctx) is False
                            and self._invocation_outcome_request() is not None
                        ):
                            return False
                        if outer_exception_state:
                            self._record_exception_scope()
                        continue
                    if (
                        not exhausted_prefix
                        and not (
                            preserving_callback_wrapper
                            and (argument is not lookup_arguments[0] or wrapper_consumption_empty)
                        )
                        and isinstance(argument, ast.Call)
                        and self._resolve_reference(argument.func)
                        in {
                            "builtins.zip",
                            "builtins.map",
                            "builtins.filter",
                            "itertools.starmap",
                            "builtins.iter",
                            "itertools.islice",
                        }
                        | _ITERABLE_CONCATENATING_REFERENCES
                        | _ITERABLE_FLATTENING_REFERENCES
                    ):
                        if (
                            self.visit(argument, iterable_callback_inputs=zip_callback_inputs)
                            is False
                            and self._invocation_outcome_request() is not None
                        ):
                            return False
                    else:
                        if (
                            self.visit(argument) is False
                            and self._invocation_outcome_request() is not None
                        ):
                            return False
                    if chain_candidate or preserving_callback_wrapper:
                        chain_operand_bindings.append(self._capture_argument_binding(argument))
                        operand_deferred = chain_operand_bindings[-1].deferred_calls
                        if len(operand_deferred) == 1 and (
                            chain_candidate
                            or argument is lookup_arguments[0]
                            and not wrapper_consumption_empty
                        ):
                            deferred_input = next(iter(operand_deferred))
                            if (
                                deferred_input.function is not None
                                and not deferred_input.partial_template
                                and (
                                    _function_is_generator(deferred_input.function)
                                    or self._deferred_generator_expression_for(
                                        deferred_input.function
                                    )
                                    is not None
                                )
                            ):
                                zip_callback_inputs.append(
                                    (
                                        node,
                                        "deferred-iterate",
                                        deferred_input,
                                        dict(deferred_input.arguments),
                                    )
                                )
                    if dict_constructor_candidate:
                        captured_dict_operand = self._capture_argument_binding(argument)
                        captured_dict_pair_entries = self._static_pair_mapping_entries(argument)
                        if captured_dict_operand.mapping is not None:
                            # Track the object through mutation without rereading its source name.
                            alias_name = f"<dict-argument:{id(node)}:0>"
                            self.scope.mappings[alias_name] = captured_dict_operand.mapping
                            dict_argument_alias = (self.scope, alias_name)
                    zip_callback_end_indices.append(len(zip_callback_inputs))
                    if wrapper_reference in _ZIPPING_ITERABLE_BUILTIN_REFERENCES:
                        exhausted_prefix = exhausted_prefix or self._is_proven_empty_iterable(
                            argument
                        )
                for keyword in node.keywords:
                    if (
                        self.visit(keyword) is False
                        and self._invocation_outcome_request() is not None
                    ):
                        return False
                    if dict_constructor_candidate:
                        keyword_binding = self._capture_argument_binding(keyword.value)
                        if keyword.arg is None:
                            if keyword_binding.mapping is not None:
                                captured_dict_keyword_entries.extend(
                                    keyword_binding.mapping.entries
                                )
                            else:
                                captured_dict_keyword_entries.append(
                                    _StaticMappingEntry(
                                        key=None,
                                        binding=self._conservative_argument_binding(),
                                    )
                                )
                        else:
                            captured_dict_keyword_entries.append(
                                _StaticMappingEntry(
                                    key=ast.copy_location(ast.Constant(keyword.arg), keyword.value),
                                    binding=keyword_binding,
                                )
                            )
            elif operand_arm == "lazy_callback":
                if (
                    self.visit(node.func) is False
                    and self._invocation_outcome_request() is not None
                ):
                    return False
                for argument_index, argument in enumerate(
                    lookup_arguments if starmap_candidate else node.args
                ):
                    if (
                        starmap_candidate
                        and argument_index == 1
                        and isinstance(argument, (ast.List, ast.Tuple))
                    ):
                        if (
                            self.reference_snapshots is not None
                            or self.string_snapshots is not None
                        ):
                            self._record_snapshot(argument)
                        outer_exception_state = bool(self._exception_scope_collectors)
                        if outer_exception_state:
                            self._record_exception_scope()
                        for row in argument.elts:
                            if not isinstance(row, (ast.List, ast.Tuple)) or any(
                                isinstance(value, ast.Starred) for value in row.elts
                            ):
                                if (
                                    self.visit(row) is False
                                    and self._invocation_outcome_request() is not None
                                ):
                                    return False
                                captured_starmap_rows.append(None)
                                continue
                            if (
                                self.reference_snapshots is not None
                                or self.string_snapshots is not None
                            ):
                                self._record_snapshot(row)
                            row_exception_state = bool(self._exception_scope_collectors)
                            if row_exception_state:
                                self._record_exception_scope()
                            row_bindings: list[_ResolvedBinding] = []
                            for value in row.elts:
                                if (
                                    self.visit(value) is False
                                    and self._invocation_outcome_request() is not None
                                ):
                                    return False
                                row_bindings.append(self._capture_argument_binding(value))
                            if (
                                self.visit(row.ctx) is False
                                and self._invocation_outcome_request() is not None
                            ):
                                return False
                            if row_exception_state:
                                self._record_exception_scope()
                            captured_starmap_rows.append(row_bindings)
                        if (
                            self.visit(argument.ctx) is False
                            and self._invocation_outcome_request() is not None
                        ):
                            return False
                        if outer_exception_state:
                            self._record_exception_scope()
                        continue
                    if (
                        self.visit(argument) is False
                        and self._invocation_outcome_request() is not None
                    ):
                        return False
                    if argument_index == 0:
                        captured_callback_templates = frozenset(
                            call
                            for call in self._resolve_deferred_calls(argument)
                            if call.partial_template and call.function is not None
                        )
                        captured_callback_targets = self._resolve_callables(argument) - {
                            template.function for template in captured_callback_templates
                        }
                        captured_callback_scope = self.scope.detached_clone()
                    elif not starmap_candidate:
                        captured_callback_arguments.append(
                            self._resolve_iterable_element_binding(argument)
                            or self._conservative_argument_binding()
                        )
                        captured_callback_empty = (
                            captured_callback_empty or self._is_proven_empty_iterable(argument)
                        )
            else:
                if (
                    self.visit(node.func) is False
                    and self._invocation_outcome_request() is not None
                ):
                    return False
                captured_callee = self._capture_argument_binding(node.func)
                if (
                    isinstance(node.func, ast.Attribute)
                    and node.func.attr in {"items", "values"}
                    and not node.args
                    and not node.keywords
                ):
                    # The literal/returned receiver now has its actual snapshot;
                    # stored bound aliases use the existing earlier capture.
                    direct_iterator_receiver = self._capture_mapping_receiver(node.func.value)
                    if direct_iterator_receiver.mapping is not None:
                        bound_iterator_method = node.func.attr
                        bound_iterator_receiver = direct_iterator_receiver
                for argument in node.args:
                    if (
                        self.visit(argument) is False
                        and self._invocation_outcome_request() is not None
                    ):
                        return False
                    bound = self._capture_argument_binding(
                        argument.value if isinstance(argument, ast.Starred) else argument
                    )
                    if isinstance(argument, ast.Starred):
                        if bound.ordered_items is not None:
                            captured_positional.extend(
                                (item, False) for item in bound.ordered_items
                            )
                        else:
                            captured_positional.append(
                                (
                                    bound.iterable_element or self._conservative_argument_binding(),
                                    True,
                                )
                            )
                    else:
                        captured_positional.append((bound, False))
                for keyword in node.keywords:
                    if (
                        self.visit(keyword) is False
                        and self._invocation_outcome_request() is not None
                    ):
                        return False
                    bound = self._capture_argument_binding(keyword.value)
                    if keyword.arg is not None:
                        captured_keywords.append((keyword.arg, bound))
                    elif bound.mapping is not None:
                        for entry in _effective_static_mapping_entries(bound.mapping.entries):
                            key = _literal_value(entry.key) if entry.key is not None else None
                            if isinstance(key, str):
                                captured_keywords.append((key, entry.binding))
                            else:
                                captured_unresolved_keywords.append(entry.binding)
                    else:
                        captured_unresolved_keywords.append(
                            bound.iterable_element or self._conservative_argument_binding()
                        )
                if (
                    captured_callee.reference in {"builtins.dict.items", "builtins.dict.values"}
                    and len(captured_positional) == 1
                    and not captured_positional[0][1]
                    and not node.keywords
                    and (iterator_mapping := captured_positional[0][0].mapping) is not None
                ):
                    # An unbound receiver can be constructed by this operand.
                    # Use its actual captured object, never a second name lookup.
                    unbound_iterator_method = captured_callee.reference.removeprefix(
                        "builtins.dict."
                    )
                    iterator_entries = _effective_static_mapping_entries(iterator_mapping.entries)
                    unbound_iterator_receiver = _MappingLookupReceiver(
                        mapping=iterator_mapping,
                        possible_value=(
                            self._join_resolved_bindings(
                                [entry.binding for entry in iterator_entries]
                            )
                            if iterator_entries
                            else _ResolvedBinding(None, None)
                        ),
                        invalidation_count=self._mapping_invalidation_counts.get(
                            iterator_mapping, 0
                        ),
                        last_clear_count=self._mapping_last_clear_counts.get(iterator_mapping, 0),
                    )
                invocation_entry = (
                    self.scope.clone() if self._invocation_outcome_request() is not None else None
                )
                # Ordinary functions/members retain their evaluated identity;
                # implicit instance dispatch selects its descriptor after operands.
                captured_callee = self._captured_callback_callee(captured_callee)
                deferred_calls = self._capture_deferred_calls(
                    node,
                    captured_callee=captured_callee,
                    captured_positional=captured_positional,
                    captured_keywords=captured_keywords,
                    captured_unresolved_keywords=captured_unresolved_keywords,
                )
                if deferred_calls:
                    self._deferred_call_bindings[id(node)] = deferred_calls
        finally:
            if dict_argument_alias is not None:
                alias_scope, alias_name = dict_argument_alias
                alias_mapping = self.scope.resolve_mapping(alias_name)
                captured_dict_operand = (
                    _ResolvedBinding(
                        reference=captured_dict_operand.reference,
                        string=captured_dict_operand.string,
                        callables=captured_dict_operand.callables,
                        deferred_calls=captured_dict_operand.deferred_calls,
                        mapping=alias_mapping,
                        class_references=captured_dict_operand.class_references,
                        descriptors=captured_dict_operand.descriptors,
                        iterable_element=captured_dict_operand.iterable_element,
                        ordered_items=captured_dict_operand.ordered_items,
                        call_receivers=captured_dict_operand.call_receivers,
                    )
                    if alias_mapping is not None and captured_dict_operand is not None
                    else self._conservative_argument_binding()
                )
                alias_scope.unbind(alias_name)
                current_alias_scope: _LexicalBindings | None = self.scope
                while current_alias_scope is not None:
                    current_alias_scope.unbind(alias_name)
                    current_alias_scope = current_alias_scope.parent
            if mapping_lookup_attribute is not None:
                self._previsited_call_receiver_attribute_ids.remove(id(mapping_lookup_attribute))
            if defer_mapping_mutation:
                self._deferred_mapping_mutator_attribute_ids.remove(id(node.func))
            if wrapped_call is not None and executes_async:
                self._awaited_call_ids.remove(id(wrapped_call))
            for gathered_call in newly_awaited_gather_calls:
                self._awaited_call_ids.remove(id(gathered_call))
            if iterated_argument is not None and not iterated_argument_was_marked:
                self._iterated_call_ids.remove(id(iterated_argument))
        request = self._invocation_outcome_request()
        if request is not None and operand_arm != "ordinary":
            invocation_entry = self.scope.clone()
        for template in captured_builtin_templates:
            with self._suspend_invocation_outcomes():
                arguments = self._resolve_partial_invocation_bindings(
                    template, node, positional_override=captured_builtin_arguments
                )
            if (
                arguments is not None
                and self._is_legacy_module_reference(arguments["object"].reference)
                and arguments["name"].string
                in CANONICAL_API_KEY_SYMBOLS | {_POSSIBLE_API_KEY_SYMBOL, _DYNAMIC_STRING_BINDING}
            ):
                partial_symbol = arguments["name"].string
                displayed_partial_symbol = (
                    partial_symbol if partial_symbol in CANONICAL_API_KEY_SYMBOLS else "<dynamic>"
                )
                self.errors.append(
                    f"{self.filename}: legacy API-key dependency attribute access is forbidden: {displayed_partial_symbol}"
                )
        if unbound_namespace_candidate:
            namespace_name = (
                lookup_arguments[1]
                if (
                    getattr_function_reference in _UNBOUND_DICT_LOOKUP_REFERENCES
                    and getattr_receiver_binding is not None
                    and getattr_member_binding is not None
                    and self._is_legacy_namespace_reference(getattr_receiver_binding.reference)
                )
                else None
            )
            namespace_symbol_name = (
                getattr_member_binding.string if getattr_member_binding is not None else None
            )
        if namespace_name is not None:
            if (
                not unbound_namespace_candidate
                and isinstance(namespace_name, ast.Call)
                and id(namespace_name) in self._call_result_bindings
            ):
                namespace_symbol_name = self._call_result_bindings[id(namespace_name)].string
            if (
                namespace_symbol_name in CANONICAL_API_KEY_SYMBOLS
                or namespace_symbol_name in {_POSSIBLE_API_KEY_SYMBOL, _DYNAMIC_STRING_BINDING}
                or (namespace_symbol_name is None and not isinstance(namespace_name, ast.Name))
            ):
                displayed_name = (
                    namespace_symbol_name
                    if namespace_symbol_name in CANONICAL_API_KEY_SYMBOLS
                    else "<dynamic>"
                )
                self.errors.append(
                    f"{self.filename}: legacy API-key dependency namespace lookup is forbidden: "
                    f"{displayed_name}"
                )
        if (
            getattr_name is not None
            and getattr_function_reference
            in {
                "builtins.getattr",
                _POSSIBLE_GETATTR_REFERENCE,
                "builtins.setattr",
                "builtins.delattr",
            }
            and getattr_receiver_binding is not None
            and getattr_member_binding is not None
            and self._is_legacy_module_reference(getattr_receiver_binding.reference)
        ):
            getattr_symbol_name = getattr_member_binding.string
            if (
                getattr_symbol_name in CANONICAL_API_KEY_SYMBOLS
                or getattr_symbol_name in {_POSSIBLE_API_KEY_SYMBOL, _DYNAMIC_STRING_BINDING}
                or (
                    getattr_symbol_name is None
                    and not isinstance(getattr_name, ast.Name)
                    and _literal_value(getattr_name) is _UNRESOLVED_LITERAL_VALUE
                )
            ):
                displayed_name = (
                    getattr_symbol_name
                    if getattr_symbol_name in CANONICAL_API_KEY_SYMBOLS
                    else "<dynamic>"
                )
                self.errors.append(
                    f"{self.filename}: dynamic legacy API-key dependency lookup is forbidden: "
                    f"{displayed_name}"
                )
        if (
            self.ownership_family == "api_key"
            and namespace_name is None
            and not unresolved_positional_sources
            and mutation_receiver_binding is not None
            and self._is_legacy_namespace_reference(mutation_receiver_binding.reference)
        ):

            def record_protected_mutation_name(name: str | None) -> bool:
                if not self._is_protected_ownership_symbol(name):
                    return False
                self.errors.append(
                    f"{self.filename}: legacy API-key dependency namespace lookup is forbidden: "
                    f"{name if name in CANONICAL_API_KEY_SYMBOLS else '<dynamic>'}"
                )
                return True

            if _mutates_protected_namespace(
                node,
                protected_names=CANONICAL_API_KEY_SYMBOLS,
                references=mutation_function_references,
                static_string_bindings={},
                static_mapping_bindings={},
                name_resolver=lambda key: self._resolve_string(key, own_environment=True),
                name_predicate=record_protected_mutation_name,
            ):
                if (
                    isinstance(node.func, ast.Attribute)
                    and node.func.attr in {"clear", "popitem"}
                    or getattr_function_reference
                    in {
                        "builtins.dict.clear",
                        "builtins.dict.popitem",
                        "legacy_app.__dict__.clear",
                        "legacy_app.__dict__.popitem",
                        f"{_POSSIBLE_LEGACY_REFERENCE}.__dict__.clear",
                        f"{_POSSIBLE_LEGACY_REFERENCE}.__dict__.popitem",
                        f"{_POSSIBLE_LEGACY_REFERENCE}.__dict__.*",
                    }
                    or _namespace_mutator_method(getattr_function_reference, legacy_only=True)
                    in {"clear", "popitem", "*"}
                ):
                    self.errors.append(
                        f"{self.filename}: legacy API-key dependency namespace lookup is forbidden: <dynamic>"
                    )
        self._record_object_namespace_call_mutation(
            node,
            captured_function_reference=getattr_function_reference,
            captured_receiver=mutation_receiver_binding,
            captured_arguments=mutation_argument_bindings,
        )
        if mapping_copy is None and bound_mapping_copy and isinstance(node.func, ast.Attribute):
            mapping_copy = self._resolve_mapping(node.func.value)
        projected_result = self._resolve_mapping_lookup_call_binding(
            node,
            receiver=mapping_lookup_receiver,
        )
        if wait_for_candidate:
            wait_for_calls: frozenset[_DeferredFunctionCall] = frozenset()
            if (
                wait_for_shape_valid
                and captured_wait_for_operand is not None
                and wait_for_timeout is not None
            ):
                timeout_value = _literal_value(wait_for_timeout)
                if (
                    timeout_value is None
                    or timeout_value is _UNRESOLVED_LITERAL_VALUE
                    or isinstance(timeout_value, (int, float))
                    and timeout_value > 0
                ):
                    wait_for_calls = captured_wait_for_operand.deferred_calls
            projected_result = _ResolvedBinding(None, None, deferred_calls=wait_for_calls)
            if id(node) in self._awaited_call_ids and wait_for_calls:
                request = self._invocation_outcome_request()
                call_offsets = (
                    (len(request.return_scopes), len(request.raise_scopes))
                    if request is not None
                    else None
                )
                awaited_result = self._replay_deferred_calls(wait_for_calls, execution="await")
                if request is not None:
                    if call_offsets is None:
                        raise AssertionError
                    if not self._resume_invocation_outcomes(request, call_offsets):
                        return False
                if awaited_result is not None:
                    projected_result = awaited_result
        if projected_result is None and unbound_mapping_receiver is not None:
            projected_result = self._resolve_mapping_lookup_binding(
                owner=positional_arguments[0],
                key=positional_arguments[1],
                default=(positional_arguments[2] if len(positional_arguments) >= 3 else None),
                receiver=unbound_mapping_receiver,
            )
        if projected_result is None and bound_mapping_alias_receiver is not None:
            projected_result = self._resolve_mapping_lookup_binding(
                owner=node.func,
                key=positional_arguments[0],
                default=(positional_arguments[1] if len(positional_arguments) >= 2 else None),
                receiver=bound_mapping_alias_receiver,
            )
        for iterator_receiver, iterator_method in (
            (unbound_iterator_receiver, unbound_iterator_method),
            (bound_iterator_receiver, bound_iterator_method),
        ):
            if projected_result is not None:
                break
            if iterator_receiver is None:
                continue
            iterator_mapping = iterator_receiver.mapping
            exact_mapping_rows = (
                iterator_mapping is not None
                and self._mapping_literal_snapshots.get(id(iterator_mapping.site))
                is iterator_mapping
                and len(iterator_mapping.entries) == len(iterator_mapping.site.keys)
                and all(
                    entry.key is key and key is not None
                    for entry, key in zip(
                        iterator_mapping.entries, iterator_mapping.site.keys, strict=True
                    )
                )
                and self._mapping_invalidation_counts.get(iterator_mapping, 0)
                == iterator_receiver.invalidation_count
                and self._mapping_last_clear_counts.get(iterator_mapping, 0)
                == iterator_receiver.last_clear_count
            )
            if exact_mapping_rows:
                if iterator_mapping is None:
                    raise AssertionError
                iterator_keys: set[object] = set()
                for entry in iterator_mapping.entries:
                    key = (
                        _literal_value(entry.key)
                        if entry.key is not None
                        else _UNRESOLVED_LITERAL_VALUE
                    )
                    if key is _UNRESOLVED_LITERAL_VALUE:
                        exact_mapping_rows = False
                        break
                    try:
                        if key in iterator_keys:
                            exact_mapping_rows = False
                            break
                        iterator_keys.add(key)
                    except TypeError:
                        exact_mapping_rows = False
                        break
            if exact_mapping_rows:
                if iterator_mapping is None:
                    raise AssertionError
                # A reduced last-write tuple cannot prove Python's first-key
                # insertion order. Only the actual unreduced unique-key snapshot
                # reaches this ordered publication; every row keeps its full RB.
                mapping_rows = tuple(
                    (
                        _ResolvedBinding(
                            reference=_INDEXED_PAIR_ELEMENT_REFERENCE,
                            string=None,
                            iterable_element=entry.binding,
                        )
                        if iterator_method == "items"
                        else entry.binding
                    )
                    for entry in iterator_mapping.entries
                )
                projected_result = self._variadic_iterable_binding(
                    mapping_rows, ordered_items=mapping_rows
                )
            elif iterator_receiver.possible_value is not None:
                iterator_element = iterator_receiver.possible_value
                if iterator_method == "items":
                    iterator_element = _ResolvedBinding(
                        reference=_INDEXED_PAIR_ELEMENT_REFERENCE,
                        string=None,
                        iterable_element=iterator_element,
                    )
                projected_result = self._variadic_iterable_binding([iterator_element])
        if projected_result is None and mapping_copy is not None:
            projected_result = self._copied_mapping_binding(mapping_copy, node)
        if (
            projected_result is None
            and popitem_receiver is not None
            and popitem_receiver.possible_value is not None
        ):
            projected_result = _ResolvedBinding(
                reference=_INDEXED_PAIR_ELEMENT_REFERENCE,
                string=None,
                iterable_element=popitem_receiver.possible_value,
            )
        if projected_result is None and wrapper_reference == "builtins.dict":
            projected_result = self._dict_constructor_binding(
                node,
                positional_arguments,
                unresolved_positional_sources,
                captured_operand=captured_dict_operand,
                captured_pair_entries=captured_dict_pair_entries,
                captured_keyword_entries=captured_dict_keyword_entries,
            )
        if projected_result is None and wrapper_reference == "builtins.dict.fromkeys":
            projected_result = self._dict_fromkeys_binding(
                node,
                positional_arguments,
                unresolved_positional_sources,
            )
        if projected_result is None and wrapper_reference in _ZIPPING_ITERABLE_BUILTIN_REFERENCES:
            projected_result = self._zip_result_binding(
                positional_arguments,
                unresolved_positional_sources,
                keywords=node.keywords,
            )
        elif (
            projected_result is None and wrapper_reference in _ITERABLE_FILTERING_BUILTIN_REFERENCES
        ):
            if (
                not unresolved_positional_sources
                and len(positional_arguments) == 2
                and self._is_proven_empty_iterable(positional_arguments[1])
            ):
                projected_result = self._variadic_iterable_binding([])
            else:
                element = (
                    self._conservative_argument_binding()
                    if unresolved_positional_sources or len(positional_arguments) != 2
                    else self._resolve_iterable_element_binding(positional_arguments[1])
                )
                if element is not None:
                    projected_result = self._variadic_iterable_binding([element])
        elif projected_result is None and wrapper_reference in _ITERABLE_CONCATENATING_REFERENCES:
            elements = [
                self._resolve_iterable_element_binding(argument)
                or self._conservative_argument_binding()
                for argument in positional_arguments
            ]
            elements.extend(
                self._conservative_argument_binding() for _source in unresolved_positional_sources
            )
            if elements:
                projected_result = self._variadic_iterable_binding(elements)
        elif projected_result is None and wrapper_reference in _ITERABLE_FLATTENING_REFERENCES:
            outer_element = (
                self._conservative_argument_binding()
                if unresolved_positional_sources or not positional_arguments
                else self._resolve_iterable_element_binding(positional_arguments[0])
            )
            if outer_element is not None:
                projected_result = self._variadic_iterable_binding(
                    [outer_element.iterable_element or self._conservative_argument_binding()]
                )
        elif (
            projected_result is None
            and (positional_arguments or unresolved_positional_sources)
            and (
                wrapper_reference in _INDEXING_ITERABLE_BUILTIN_REFERENCES
                or captured_callee is not None
                and captured_callee.reference in _INDEXING_ITERABLE_BUILTIN_REFERENCES
            )
        ):
            exact_indexed_input = (
                captured_positional[0][0]
                if captured_callee is not None
                and captured_callee.reference in _INDEXING_ITERABLE_BUILTIN_REFERENCES
                and 1 <= len(captured_positional) <= 2
                and not any(unresolved for _binding, unresolved in captured_positional)
                and not captured_unresolved_keywords
                and (
                    not captured_keywords
                    or len(captured_positional) == 1
                    and len(captured_keywords) == 1
                    and captured_keywords[0][0] == "start"
                )
                else None
            )
            if (
                exact_indexed_input is not None
                and exact_indexed_input.ordered_items is not None
                and not exact_indexed_input.deferred_calls
            ):
                # Keep each captured row, including its independent child
                # cursor. Later arguments may already have rebound its name.
                indexed_rows = tuple(
                    _ResolvedBinding(
                        reference=_INDEXED_PAIR_ELEMENT_REFERENCE,
                        string=None,
                        iterable_element=row,
                    )
                    for row in exact_indexed_input.ordered_items
                )
                projected_result = self._variadic_iterable_binding(
                    indexed_rows, ordered_items=indexed_rows
                )
            else:
                element = (
                    self._conservative_argument_binding()
                    if unresolved_positional_sources
                    else self._resolve_iterable_element_binding(positional_arguments[0])
                )
                if element is not None:
                    indexed_element = _ResolvedBinding(
                        reference=_INDEXED_PAIR_ELEMENT_REFERENCE,
                        string=None,
                        iterable_element=element,
                    )
                    projected_result = self._variadic_iterable_binding([indexed_element])
        elif (
            projected_result is None
            and (positional_arguments or unresolved_positional_sources)
            and wrapper_reference in _ITERABLE_PRESERVING_WRAPPER_REFERENCES
        ):
            if wrapper_reference == "itertools.islice" and self._is_proven_empty_islice(
                positional_arguments,
                unresolved_positional_sources,
            ):
                projected_result = self._variadic_iterable_binding([])
            else:
                element = (
                    key_input_binding
                    if keys_callback
                    else (
                        self._conservative_argument_binding()
                        if unresolved_positional_sources
                        else self._resolve_iterable_element_binding(positional_arguments[0])
                    )
                )
                if element is not None:
                    projected_result = self._variadic_iterable_binding([element])
        elif (
            projected_result is None
            and (positional_arguments or unresolved_positional_sources)
            and wrapper_reference in _ITERABLE_ELEMENT_BUILTIN_REFERENCES
        ):
            if unresolved_positional_sources:
                projected_result = self._conservative_argument_binding()
            elif (
                wrapper_reference in {"builtins.max", "builtins.min"}
                and len(positional_arguments) != 1
            ):
                projected_result = (
                    key_input_binding
                    if keys_callback
                    else self._join_resolved_bindings(
                        [
                            self._capture_argument_binding(argument)
                            for argument in positional_arguments
                        ]
                    )
                )
            else:
                projected_result = (
                    self._resolve_first_static_iterable_binding(positional_arguments[0])
                    if (
                        wrapper_reference == "builtins.next"
                        and isinstance(positional_arguments[0], ast.Call)
                        and self._resolve_reference(positional_arguments[0].func) == "builtins.iter"
                    )
                    else None
                )
                if projected_result is None:
                    projected_result = (
                        key_input_binding
                        if keys_callback
                        else self._resolve_iterable_element_binding(positional_arguments[0])
                    )
                if (
                    wrapper_reference == "builtins.next"
                    and len(positional_arguments) >= 2
                    and not self._is_proven_nonempty_iterable(positional_arguments[0])
                ):
                    default_binding = self._capture_argument_binding(positional_arguments[1])
                    projected_result = (
                        default_binding
                        if projected_result is None
                        else self._join_resolved_bindings([projected_result, default_binding])
                    )
            if wrapper_reference in {"builtins.max", "builtins.min"}:
                default_bindings: list[_ResolvedBinding] = []
                if not (
                    len(positional_arguments) == 1
                    and self._is_proven_nonempty_iterable(positional_arguments[0])
                ):
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
        if captured_callee is not None:
            replay_inputs.extend(
                self._prepare_function_replay_inputs(
                    node,
                    captured_callee=captured_callee,
                    captured_positional=captured_positional,
                    captured_keywords=captured_keywords,
                    captured_unresolved_keywords=captured_unresolved_keywords,
                )
            )
        else:
            if argument_scope is None:
                raise AssertionError
            active_scope = self.scope
            self._switch_deferred_scope(argument_scope, restore_flow=False)
            refresh_frame = cast(tuple[object, ...], self._active_replay_contexts[-1])
            self._active_replay_contexts[-1] = (*refresh_frame[:8], None)
            try:
                prepared_arguments = {
                    target: arguments
                    for target, arguments in self._prepare_function_replay_inputs(node)
                    if implicit_instance_call or target in prepared_targets
                }
            finally:
                updated_frame = cast(tuple[object, ...], self._active_replay_contexts[-1])
                self._active_replay_contexts[-1] = (
                    *updated_frame[:8],
                    refresh_frame[8],
                )
                self._switch_deferred_scope(active_scope, restore_flow=False)
            for target in sorted(
                prepared_targets,
                key=lambda candidate: (
                    candidate.lineno,
                    candidate.col_offset,
                    candidate.name,
                ),
            ):
                replay_inputs.append(
                    (target, prepared_arguments.get(target, initial_arguments[target]))
                )
            if implicit_instance_call:
                replay_inputs.extend(prepared_arguments.items())
            else:
                replay_inputs.extend(
                    self._prepare_function_replay_inputs(
                        node,
                        excluded_targets=prepared_targets,
                    )
                )
        callback_active_scope = self.scope
        if captures_lazy_callback and captured_callback_scope is not None:
            self._switch_deferred_scope(captured_callback_scope, restore_flow=False)
        try:
            maps_callback = (
                (id(node) in self._iterated_call_ids or captures_lazy_callback)
                and wrapper_reference == "builtins.map"
                and not captured_callback_empty
            )
            if maps_callback and len(node.args) >= 2:
                iterable_bindings = (
                    captured_callback_arguments
                    if captures_lazy_callback
                    else [
                        (
                            self._resolve_iterable_element_binding(
                                argument.value if isinstance(argument, ast.Starred) else argument
                            )
                            or self._conservative_argument_binding()
                        )
                        for argument in node.args[1:]
                    ]
                )
                with self._suspend_invocation_outcomes():
                    replay_inputs.extend(
                        (target, arguments)
                        for target in sorted(
                            (
                                captured_callback_targets
                                if captures_lazy_callback
                                else self._resolve_callables(node.args[0])
                            ),
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
                with self._suspend_invocation_outcomes():
                    replay_inputs.extend(
                        (template.function, arguments)
                        for template in sorted(
                            captured_callback_templates,
                            key=self._deferred_call_sort_key,
                        )
                        if template.function is not None
                        if not isinstance(template.function, ast.AsyncFunctionDef)
                        if not _function_is_generator(template.function)
                        if (
                            arguments := self._resolve_partial_invocation_bindings(
                                template, node, positional_override=iterable_bindings
                            )
                        )
                        is not None
                    )
            if starmap_candidate and captures_lazy_callback:
                for star_row_bindings in captured_starmap_rows:
                    if star_row_bindings is None:
                        continue
                    rejected_single_target = False
                    for target in sorted(
                        captured_callback_targets,
                        key=lambda candidate: (
                            candidate.lineno,
                            candidate.col_offset,
                            candidate.name,
                        ),
                    ):
                        if isinstance(target, ast.AsyncFunctionDef) or _function_is_generator(
                            target
                        ):
                            continue
                        with self._suspend_invocation_outcomes():
                            arguments = self._resolve_call_argument_bindings(
                                target,
                                node,
                                callable_expr=lookup_arguments[0],
                                positional_override=star_row_bindings,
                            )
                        if arguments is not None:
                            replay_inputs.append((target, arguments))
                        elif len(captured_callback_targets) == 1:
                            rejected_single_target = True
                    for template in sorted(
                        captured_callback_templates, key=self._deferred_call_sort_key
                    ):
                        if (
                            template.function is None
                            or isinstance(template.function, ast.AsyncFunctionDef)
                            or _function_is_generator(template.function)
                        ):
                            continue
                        with self._suspend_invocation_outcomes():
                            arguments = self._resolve_partial_invocation_bindings(
                                template, node, positional_override=star_row_bindings
                            )
                        if arguments is not None:
                            replay_inputs.append((template.function, arguments))
                        elif len(captured_callback_templates) + len(captured_callback_targets) == 1:
                            rejected_single_target = True
                    if rejected_single_target:
                        break
            filters_callback = (
                (id(node) in self._iterated_call_ids or captures_lazy_callback)
                and wrapper_reference == "builtins.filter"
                and not captured_callback_empty
            )
            if (
                filters_callback
                and len(node.args) == 2
                and not isinstance(node.args[0], ast.Constant)
                and (captures_lazy_callback or not self._is_proven_empty_iterable(node.args[1]))
            ):
                iterable_binding = (
                    captured_callback_arguments[0]
                    if captures_lazy_callback
                    else (
                        self._resolve_iterable_element_binding(node.args[1])
                        or self._conservative_argument_binding()
                    )
                )
                with self._suspend_invocation_outcomes():
                    replay_inputs.extend(
                        (target, arguments)
                        for target in sorted(
                            (
                                captured_callback_targets
                                if captures_lazy_callback
                                else self._resolve_callables(node.args[0])
                            ),
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
                                positional_override=[iterable_binding],
                            )
                        )
                        is not None
                    )
                with self._suspend_invocation_outcomes():
                    replay_inputs.extend(
                        (template.function, arguments)
                        for template in sorted(
                            captured_callback_templates,
                            key=self._deferred_call_sort_key,
                        )
                        if template.function is not None
                        if not isinstance(template.function, ast.AsyncFunctionDef)
                        if not _function_is_generator(template.function)
                        if (
                            arguments := self._resolve_partial_invocation_bindings(
                                template, node, positional_override=[iterable_binding]
                            )
                        )
                        is not None
                    )
        finally:
            self._switch_deferred_scope(callback_active_scope, restore_flow=False)
        previous_sync_only = self._sync_only_body_analysis
        if (
            previous_sync_only
            and self._replay_calls_enabled
            and self._analysis_purpose == "ownership_audit"
            and (id(node) in self._awaited_call_ids or id(node) in self._iterated_call_ids)
        ):
            self._sync_only_body_analysis = False
        replay_results: list[_ResolvedBinding] = []
        try:
            if (
                captures_lazy_callback
                and iterable_callback_inputs is not None
                and wrapper_reference is not None
            ):
                iterable_callback_inputs.extend(
                    (node, wrapper_reference, target, arguments)
                    for target, arguments in replay_inputs
                )
            else:
                replay_entry = (
                    self._capture_deferred_flow(self.scope) if request is not None else None
                )
                replay_scope = self.scope
                for target, arguments in replay_inputs:
                    if starmap_candidate and self._replay_calls_enabled:
                        self._consume_loop_iteration()
                    if request is not None:
                        if replay_entry is None:
                            raise AssertionError
                        self._restore_deferred_flow(replay_entry)
                        self.scope = replay_scope
                        normal_offset = len(request.return_scopes)
                    replay_result = (
                        self._replay_function_call(
                            target, arguments, iteration_result_node=iteration_result_node
                        )
                        if iteration_result_node is not None and _function_is_generator(target)
                        else self._replay_function_call(target, arguments)
                    )
                    if (
                        iteration_result_node is not None
                        and request is not None
                        and not _function_is_generator(target)
                    ):
                        # Compose each actual ordinary Return with iteration before
                        # joining producer alternatives. Callback values use their
                        # separate captured producer and are never flattened here.
                        returned_normal = request.return_scopes[normal_offset:]
                        del request.return_scopes[normal_offset:]
                        for saved in returned_normal:
                            if saved._flow_snapshot is None:
                                raise LegacyGrowthAnalysisError(
                                    "returned iterable lost its normal Flow"
                                )
                            self._restore_deferred_flow(saved._flow_snapshot)
                            self.scope = saved
                            if replay_result.deferred_calls:
                                self._replay_deferred_calls(
                                    replay_result.deferred_calls,
                                    execution="iterate",
                                    iteration_result_node=iteration_result_node,
                                )
                            else:
                                projected = (
                                    replay_result
                                    if replay_result.ordered_items is not None
                                    or replay_result.iterable_element is not None
                                    else self._variadic_iterable_binding(
                                        [self._conservative_argument_binding()]
                                    )
                                )
                                self._call_result_bindings[id(iteration_result_node)] = projected
                                self._remember_captured_binding(projected)
                                request.return_scopes.append(self.scope.clone())
                    if (
                        request is not None
                        and id(node) in self._awaited_call_ids
                        and not isinstance(target, ast.AsyncFunctionDef)
                    ):
                        returned_normal = request.return_scopes[normal_offset:]
                        del request.return_scopes[normal_offset:]
                        if returned_normal:
                            self._merge_outcomes(replay_scope, returned_normal)
                            awaited_offsets = (
                                len(request.return_scopes),
                                len(request.raise_scopes),
                            )
                            awaited_result = self._replay_deferred_calls(
                                replay_result.deferred_calls, execution="await"
                            )
                            if not replay_result.deferred_calls:
                                del request.return_scopes[awaited_offsets[0] :]
                                del request.raise_scopes[awaited_offsets[1] :]
                                if replay_result.reference == _KNOWN_NON_APP_REFERENCE:
                                    request.raise_scopes.append(self.scope.clone())
                                else:
                                    self._unknown_invocation_outcomes(request)
                            replay_result = awaited_result or self._conservative_argument_binding()
                    if request is None or len(request.return_scopes) > normal_offset:
                        replay_results.append(replay_result)
                if request is not None and replay_inputs:
                    if invocation_offsets is None:
                        raise AssertionError
                    if iteration_result_node is not None:
                        if not request.return_scopes[invocation_offsets[0] :]:
                            return False
                    elif not self._resume_invocation_outcomes(request, invocation_offsets):
                        return False
                elif request is not None and captured_callee is not None:
                    if invocation_offsets is None:
                        raise AssertionError
                    rejected = request.raise_scopes[invocation_offsets[1] :]
                    del request.raise_scopes[invocation_offsets[1] :]
                    self._terminal_controls.raise_scopes.extend(rejected)
                    if rejected and not deferred_calls and captured_callee.callables:
                        return False
                elif request is not None:
                    # No producer claimed an exact invocation. Its abrupt continuation
                    # belongs to the actual post-eager operand phase.
                    if invocation_entry is None:
                        raise AssertionError
                    self._terminal_controls.raise_scopes.append(invocation_entry.clone())
        finally:
            self._sync_only_body_analysis = previous_sync_only
        if (
            request is not None
            and captured_callee is not None
            and not replay_inputs
            and not deferred_calls
            and not captured_callee.callables
        ):
            if invocation_entry is None:
                raise AssertionError
            self._terminal_controls.raise_scopes.append(invocation_entry.clone())
        if replay_results:
            result_binding = self._join_resolved_bindings(replay_results)
            if starmap_candidate:
                result_binding = self._variadic_iterable_binding([result_binding])
            self._call_result_bindings[id(node)] = result_binding
            if self.call_result_snapshots is not None:
                existing = self.call_result_snapshots.get(id(node))
                self.call_result_snapshots[id(node)] = (
                    result_binding
                    if existing is None
                    else self._join_resolved_bindings([existing, result_binding])
                )
        if reduce_candidate and self._replay_calls_enabled:
            reduce_accumulator = captured_reduce_initializer
            reduce_items = captured_reduce_items
            if reduce_accumulator is None and reduce_items:
                reduce_accumulator, reduce_items = reduce_items[0], reduce_items[1:]
            for reduce_item_binding in reduce_items:
                if reduce_accumulator is None:
                    break
                fold_inputs: list[tuple[_FunctionNode, dict[str, _ResolvedBinding]]] = []
                fold_scope = self.scope
                if captured_callback_scope is not None:
                    self._switch_deferred_scope(captured_callback_scope, restore_flow=False)
                rejected_single_target = False
                try:
                    for target in sorted(
                        captured_callback_targets,
                        key=lambda candidate: (
                            candidate.lineno,
                            candidate.col_offset,
                            candidate.name,
                        ),
                    ):
                        if isinstance(target, ast.AsyncFunctionDef) or _function_is_generator(
                            target
                        ):
                            continue
                        with self._suspend_invocation_outcomes():
                            arguments = self._resolve_call_argument_bindings(
                                target,
                                node,
                                callable_expr=positional_arguments[0],
                                positional_override=[
                                    reduce_accumulator,
                                    reduce_item_binding,
                                ],
                            )
                        if arguments is not None:
                            fold_inputs.append((target, arguments))
                        elif len(captured_callback_templates) + len(captured_callback_targets) == 1:
                            rejected_single_target = True
                    for template in sorted(
                        captured_callback_templates, key=self._deferred_call_sort_key
                    ):
                        if (
                            template.function is None
                            or isinstance(template.function, ast.AsyncFunctionDef)
                            or _function_is_generator(template.function)
                        ):
                            continue
                        with self._suspend_invocation_outcomes():
                            arguments = self._resolve_partial_invocation_bindings(
                                template,
                                node,
                                positional_override=[
                                    reduce_accumulator,
                                    reduce_item_binding,
                                ],
                            )
                        if arguments is not None:
                            fold_inputs.append((template.function, arguments))
                        elif len(captured_callback_templates) + len(captured_callback_targets) == 1:
                            rejected_single_target = True
                finally:
                    self._switch_deferred_scope(fold_scope, restore_flow=False)
                if rejected_single_target or not fold_inputs:
                    reduce_accumulator = None
                    break
                fold_results: list[_ResolvedBinding] = []
                fold_request = self._invocation_outcome_request()
                fold_offsets = (
                    (len(fold_request.return_scopes), len(fold_request.raise_scopes))
                    if fold_request is not None
                    else None
                )
                fold_entry = (
                    self._capture_deferred_flow(self.scope) if fold_request is not None else None
                )
                fold_active = self.scope
                for target, arguments in fold_inputs:
                    self._consume_loop_iteration()
                    if fold_request is not None:
                        if fold_entry is None:
                            raise AssertionError
                        self._restore_deferred_flow(fold_entry)
                        self.scope = fold_active
                        normal_offset = len(fold_request.return_scopes)
                    fold_result = self._replay_function_call(target, arguments)
                    if fold_request is None or len(fold_request.return_scopes) > normal_offset:
                        fold_results.append(fold_result)
                if fold_request is not None:
                    if fold_offsets is None:
                        raise AssertionError
                    if not self._resume_invocation_outcomes(fold_request, fold_offsets):
                        return False
                reduce_accumulator = self._join_resolved_bindings(fold_results)
            if reduce_accumulator is not None:
                self._call_result_bindings[id(node)] = reduce_accumulator
                if self.call_result_snapshots is not None:
                    existing_reduce = self.call_result_snapshots.get(id(node))
                    self.call_result_snapshots[id(node)] = (
                        reduce_accumulator
                        if existing_reduce is None
                        else self._join_resolved_bindings([existing_reduce, reduce_accumulator])
                    )
        if maps_callback:
            identity_map_result = self._identity_map_result_binding(
                positional_arguments,
                unresolved_positional_sources,
            )
            if identity_map_result is not None:
                self._call_result_bindings[id(node)] = identity_map_result
                if self.call_result_snapshots is not None:
                    self.call_result_snapshots[id(node)] = identity_map_result
        with self._suspend_invocation_outcomes():
            partial_templates = self._partial_function_templates(
                node,
                wrapper_reference=wrapper_reference,
                callable_binding=captured_partial_callable,
                positional_override=(
                    captured_partial_positional
                    if partial_constructor_candidate and not unresolved_positional_sources
                    else None
                ),
            )
        partial_wrapped_binding: _ResolvedBinding | None = None
        if wrapper_reference == "functools.partial" and node.args:
            wrapped = node.args[0]
            if isinstance(wrapped, ast.Call):
                registrar_reference = self._resolve_reference(wrapped.func)
                if _is_registration_callable_reference(registrar_reference):
                    partial_wrapped_binding = _ResolvedBinding(
                        reference=f"{_ROUTE_DECORATOR_REFERENCE_PREFIX}{registrar_reference}",
                        string=(self._resolve_string(wrapped.args[0]) if wrapped.args else None),
                    )
        if partial_templates or partial_wrapped_binding is not None:
            partial_binding = _ResolvedBinding(
                reference=(
                    partial_wrapped_binding.reference
                    if partial_wrapped_binding is not None
                    else self._resolve_reference(node) or _KNOWN_NON_APP_REFERENCE
                ),
                string=(
                    partial_wrapped_binding.string if partial_wrapped_binding is not None else None
                ),
                callables=frozenset(
                    template.function
                    for template in partial_templates
                    if template.function is not None
                ),
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
        if (
            self._analysis_purpose == "ownership_audit"
            and wrapper_reference == "asyncio.run"
            and wrapped_call is not None
        ):
            wrapped_result = self._call_result_bindings.get(id(wrapped_call))
            if wrapped_result is not None:
                self._call_result_bindings[id(node)] = wrapped_result
                if self.call_result_snapshots is not None:
                    existing_snapshot = self.call_result_snapshots.get(id(node))
                    self.call_result_snapshots[id(node)] = (
                        wrapped_result
                        if existing_snapshot is None
                        else self._join_resolved_bindings([existing_snapshot, wrapped_result])
                    )
        if executes_async and node.args and wrapped_call is None:
            request = self._invocation_outcome_request()
            call_offsets = (
                (len(request.return_scopes), len(request.raise_scopes))
                if request is not None
                else None
            )
            deferred_result = self._replay_deferred_calls(
                self._resolve_deferred_calls(node.args[0]),
                execution="await",
            )
            if request is not None:
                if call_offsets is None:
                    raise AssertionError
                if not self._resume_invocation_outcomes(request, call_offsets):
                    return False
            if deferred_result is not None:
                self._call_result_bindings[id(node)] = deferred_result
        if gathers_awaitables:
            for argument in node.args:
                if isinstance(argument, ast.Starred):
                    element = self._resolve_iterable_element_binding(argument.value)
                    deferred = element.deferred_calls if element is not None else frozenset()
                else:
                    deferred = self._resolve_deferred_calls(argument)
                request = self._invocation_outcome_request()
                call_offsets = (
                    (len(request.return_scopes), len(request.raise_scopes))
                    if request is not None
                    else None
                )
                self._replay_deferred_calls(deferred, execution="await")
                if request is not None:
                    if call_offsets is None:
                        raise AssertionError
                    if not self._resume_invocation_outcomes(request, call_offsets):
                        return False
        if consumes_iterable and positional_arguments:
            request = self._invocation_outcome_request()
            call_offsets = (
                (len(request.return_scopes), len(request.raise_scopes))
                if request is not None
                else None
            )
            self._replay_deferred_calls(
                self._resolve_deferred_calls(positional_arguments[0]),
                execution="iterate",
            )
            if request is not None:
                if call_offsets is None:
                    raise AssertionError
                if not self._resume_invocation_outcomes(request, call_offsets):
                    return False
        if consumes_iterable:
            for source in unresolved_positional_sources:
                request = self._invocation_outcome_request()
                call_offsets = (
                    (len(request.return_scopes), len(request.raise_scopes))
                    if request is not None
                    else None
                )
                self._replay_deferred_calls(
                    self._resolve_deferred_calls(source),
                    execution="iterate",
                )
                if request is not None:
                    if call_offsets is None:
                        raise AssertionError
                    if not self._resume_invocation_outcomes(request, call_offsets):
                        return False
        key_previous_sync_only = self._sync_only_body_analysis
        self._sync_only_body_analysis = previous_sync_only
        try:
            for target, arguments in key_replay_inputs:
                request = self._invocation_outcome_request()
                call_offsets = (
                    (len(request.return_scopes), len(request.raise_scopes))
                    if request is not None
                    else None
                )
                self._replay_function_call(target, arguments)
                if request is not None:
                    if call_offsets is None:
                        raise AssertionError
                    if not self._resume_invocation_outcomes(request, call_offsets):
                        return False
        finally:
            self._sync_only_body_analysis = key_previous_sync_only
        if async_iteration_operand is not None and (
            async_iteration_callee == "builtins.anext"
            or isinstance(node.func, ast.Attribute)
            and node.func.attr == "__anext__"
        ):
            request = self._invocation_outcome_request()
            call_offsets = (
                (len(request.return_scopes), len(request.raise_scopes))
                if request is not None
                else None
            )
            self._replay_deferred_calls(
                frozenset(
                    call
                    for call in async_iteration_operand.deferred_calls
                    if isinstance(call.function, ast.AsyncFunctionDef)
                    and _function_is_generator(call.function)
                ),
                execution="iterate",
            )
            if request is not None:
                if call_offsets is None:
                    raise AssertionError
                if not self._resume_invocation_outcomes(request, call_offsets):
                    return False
        if (
            (
                wrapper_reference in _ZIPPING_ITERABLE_BUILTIN_REFERENCES
                or chain_candidate
                or preserving_callback_wrapper
                and not wrapper_consumption_empty
                or flattening_callback_wrapper
            )
            and id(node) in self._iterated_call_ids
        ) or consumes_dict_iterable:
            zip_previous_sync_only = self._sync_only_body_analysis
            if owns_zip_callback_inputs and self._analysis_purpose == "ownership_audit":
                self._sync_only_body_analysis = False
            try:
                callback_results: dict[ast.Call, list[_ResolvedBinding]] = {}
                callback_start = 0
                callback_operands = (
                    list(cast(ast.List | ast.Tuple, positional_arguments[0]).elts)
                    if flattening_callback_wrapper
                    else (
                        list(positional_arguments[:1])
                        if preserving_callback_wrapper
                        else list(positional_arguments)
                    )
                )
                callback_exhausted_prefix = False
                for argument_index, argument in enumerate(callback_operands):
                    if (
                        wrapper_reference in _ZIPPING_ITERABLE_BUILTIN_REFERENCES
                        and callback_exhausted_prefix
                    ):
                        break
                    callback_exhausted_prefix = (
                        callback_exhausted_prefix or self._is_proven_empty_iterable(argument)
                    )
                    request = self._invocation_outcome_request()
                    call_offsets = (
                        (len(request.return_scopes), len(request.raise_scopes))
                        if request is not None
                        else None
                    )
                    self._replay_deferred_calls(
                        (
                            captured_dict_operand.deferred_calls
                            if consumes_dict_iterable and captured_dict_operand is not None
                            else (
                                chain_operand_bindings[argument_index].deferred_calls
                                if chain_candidate
                                or preserving_callback_wrapper
                                or flattening_callback_wrapper
                                else self._resolve_deferred_calls(argument)
                            )
                        ),
                        execution="iterate",
                    )
                    if request is not None:
                        if call_offsets is None:
                            raise AssertionError
                        if not self._resume_invocation_outcomes(request, call_offsets):
                            return False
                    if not owns_zip_callback_inputs:
                        continue
                    callback_end = zip_callback_end_indices[argument_index]
                    for (
                        original_call,
                        callback_reference,
                        queued_target,
                        arguments,
                    ) in zip_callback_inputs[callback_start:callback_end]:
                        if callback_reference == "deferred-iterate":
                            if not isinstance(queued_target, _DeferredFunctionCall):
                                raise LegacyGrowthAnalysisError(
                                    "deferred queue view lost its full descriptor"
                                )
                            request = self._invocation_outcome_request()
                            call_offsets = (
                                (len(request.return_scopes), len(request.raise_scopes))
                                if request is not None
                                else None
                            )
                            self._replay_deferred_calls(
                                frozenset({queued_target}), execution="iterate"
                            )
                            if request is not None:
                                if call_offsets is None:
                                    raise AssertionError
                                if not self._resume_invocation_outcomes(request, call_offsets):
                                    return False
                            continue
                        if isinstance(queued_target, _DeferredFunctionCall):
                            raise LegacyGrowthAnalysisError(
                                "real callback queue received a deferred view"
                            )
                        was_iterated = id(original_call) in self._iterated_call_ids
                        self._iterated_call_ids.add(id(original_call))
                        try:
                            if (
                                callback_reference == "itertools.starmap"
                                and self._replay_calls_enabled
                            ):
                                self._consume_loop_iteration()
                            request = self._invocation_outcome_request()
                            call_offsets = (
                                (len(request.return_scopes), len(request.raise_scopes))
                                if request is not None
                                else None
                            )
                            callback_result = self._replay_function_call(queued_target, arguments)
                            if request is not None:
                                if call_offsets is None:
                                    raise AssertionError
                                if not self._resume_invocation_outcomes(request, call_offsets):
                                    return False
                        finally:
                            if not was_iterated:
                                self._iterated_call_ids.remove(id(original_call))
                        if callback_reference in {"builtins.map", "itertools.starmap"}:
                            if callback_reference == "itertools.starmap":
                                callback_result = self._variadic_iterable_binding([callback_result])
                            callback_results.setdefault(original_call, []).append(callback_result)
                    callback_start = callback_end
                for original_call, results in callback_results.items():
                    if id(original_call) not in self._call_result_bindings:
                        callback_result = self._join_resolved_bindings(results)
                        self._call_result_bindings[id(original_call)] = callback_result
                        if self.call_result_snapshots is not None:
                            self.call_result_snapshots[id(original_call)] = callback_result
            finally:
                self._sync_only_body_analysis = zip_previous_sync_only
        if (
            wrapper_reference in _ZIPPING_ITERABLE_BUILTIN_REFERENCES
            and id(node) in self._iterated_call_ids
        ):
            final_zip = self._zip_result_binding(
                positional_arguments, unresolved_positional_sources, keywords=node.keywords
            )
            self._call_result_bindings[id(node)] = final_zip
            if self.call_result_snapshots is not None:
                previous_zip = self.call_result_snapshots.get(id(node))
                self.call_result_snapshots[id(node)] = (
                    final_zip
                    if previous_zip is None
                    else self._join_resolved_bindings([previous_zip, final_zip])
                )
        escaped_mappings.extend(
            mapping
            for argument in node.args
            if not dict_constructor_candidate
            if not isinstance(argument, ast.Starred)
            if (mapping := self._resolve_mapping(argument)) is not None
        )
        escaped_mappings.extend(
            mapping
            for keyword in node.keywords
            if keyword.arg is not None
            if (mapping := self._resolve_mapping(keyword.value)) is not None
        )
        rewritten_mappings: set[_StaticMapping] = set()
        if (
            known_pop_mapping is not None
            and known_pop_key is not None
            and not unresolved_positional_sources
            and known_pop_receiver is not None
            and known_pop_receiver.mapping is known_pop_mapping
            and self._mapping_invalidation_counts.get(known_pop_mapping, 0)
            == known_pop_receiver.invalidation_count
        ):
            replacement = self._mapping_after_known_pop(
                known_pop_mapping,
                known_pop_key,
                node,
                preserve_if_absent=known_pop_has_default,
            )
            if replacement is not None:
                self._replace_mapping_aliases(known_pop_mapping, replacement)
                rewritten_mappings.add(known_pop_mapping)
        if (
            known_update_mapping is not None
            and known_update_invalidation_count is not None
            and self._mapping_invalidation_counts.get(known_update_mapping, 0)
            == known_update_invalidation_count
        ):
            replacement = self._mapping_after_known_update(
                known_update_mapping,
                node,
                positional_arguments,
                unresolved_positional_sources,
            )
            if replacement is not None:
                self._replace_mapping_aliases(known_update_mapping, replacement)
                rewritten_mappings.add(known_update_mapping)
        if (
            known_setdefault_mapping is not None
            and known_setdefault_key is not None
            and known_setdefault_invalidation_count is not None
            and not unresolved_positional_sources
            and not node.keywords
            and known_setdefault_receiver is not None
            and known_setdefault_receiver.mapping is known_setdefault_mapping
            and self._mapping_invalidation_counts.get(known_setdefault_mapping, 0)
            == known_setdefault_invalidation_count
        ):
            replacement = self._mapping_after_known_setdefault(
                known_setdefault_mapping,
                known_setdefault_key,
                known_setdefault_default,
                node,
            )
            if replacement is not None:
                self._replace_mapping_aliases(known_setdefault_mapping, replacement)
                rewritten_mappings.add(known_setdefault_mapping)
        for mapping in set(escaped_mappings):
            if mapping in rewritten_mappings:
                continue
            if mapping in known_empty_mappings:
                empty_site = ast.copy_location(ast.Dict(keys=[], values=[]), node)
                replacement = self._variadic_mapping_binding(
                    [],
                    mapping_entries=(),
                    mapping_site=empty_site,
                )
                self._replace_mapping_aliases(mapping, replacement)
            self._invalidate_mapping(
                mapping,
                known_empty=mapping in known_empty_mappings,
            )
        return None

    def visit_Await(self, node: ast.Await) -> None | Literal[False]:
        if not isinstance(node.value, ast.Call):
            if self.generic_visit(node) is False and self._invocation_outcome_request() is not None:
                return False
            request = self._invocation_outcome_request()
            offsets = (
                (len(request.return_scopes), len(request.raise_scopes))
                if request is not None
                else None
            )
            deferred = self._resolve_deferred_calls(node.value)
            result_binding = self._replay_deferred_calls(deferred, execution="await")
            if request is not None:
                if offsets is None:
                    raise AssertionError
                if not deferred:
                    del request.return_scopes[offsets[0] :]
                    del request.raise_scopes[offsets[1] :]
                    if (
                        self._capture_argument_binding(node.value).reference
                        == _KNOWN_NON_APP_REFERENCE
                    ):
                        request.raise_scopes.append(self.scope.clone())
                    else:
                        self._unknown_invocation_outcomes(request)
                if not self._resume_invocation_outcomes(request, offsets):
                    return False
            if result_binding is not None:
                self._call_result_bindings[id(node)] = result_binding
            return None
        call_id = id(node.value)
        frame = self._active_replay_contexts[-1] if self._active_replay_contexts else None
        owns_direct = (
            isinstance(frame, tuple)
            and len(frame) == 9
            and frame[1] is node
            and frame[8] is not None
            and node.value in frame[4]
        )
        request = self._invocation_outcome_request()
        normal_offset = len(request.return_scopes) if request is not None else 0
        if owns_direct:
            # Frozen entry Flow retains older values. Current evaluation cannot
            # reuse either an old Await value or its constructor's old output.
            self._call_result_bindings.pop(id(node), None)
            self._call_result_bindings.pop(call_id, None)
        self._awaited_call_ids.add(call_id)
        try:
            if self.visit(node.value) is False and self._invocation_outcome_request() is not None:
                return False
            current = self._active_replay_contexts[-1] if owns_direct else None
            if isinstance(current, tuple) and current[1] is node and current[5]:
                result_binding = self._call_result_bindings.get(call_id)
                if result_binding is None:
                    raise LegacyGrowthAnalysisError(
                        "immediate await lost its completed normal result"
                    )
                self._call_result_bindings[id(node)] = result_binding
                if self.call_result_snapshots is not None:
                    existing = self.call_result_snapshots.get(id(node))
                    self.call_result_snapshots[id(node)] = (
                        result_binding
                        if existing is None
                        else self._join_resolved_bindings([existing, result_binding])
                    )
                if request is not None:
                    for saved in request.return_scopes[normal_offset:]:
                        state = saved._flow_snapshot
                        if state is None:
                            raise LegacyGrowthAnalysisError(
                                "immediate await normal has no saved Flow"
                            )
                        results = dict(state[2])
                        results[id(node)] = result_binding
                        saved._flow_snapshot = (
                            state[0],
                            state[1],
                            results,
                            state[3],
                            state[4] | {id(node)},
                            state[5],
                        )
        finally:
            self._awaited_call_ids.remove(call_id)
        return None

    def _replay_function_call(
        self,
        node: _FunctionNode,
        arguments: Mapping[str, _ResolvedBinding],
        *,
        iteration_result_node: ast.expr | None = None,
    ) -> _ResolvedBinding:
        request = self._invocation_outcome_request()
        if (
            not self._replay_calls_enabled
            or (
                self._sync_only_body_analysis
                and (isinstance(node, ast.AsyncFunctionDef) or _function_is_generator(node))
            )
            or node in self._active_function_replays
        ):
            if request is not None:
                self._unknown_invocation_outcomes(request)
            return _ResolvedBinding(None, None)
        caller_outward_views: list[tuple[_LexicalBindings, Mapping[str, _LexicalBindings]]] = []
        if request is not None:
            view: _LexicalBindings | None = self.scope
            while view is not None:
                targets = self._active_outward_targets_for_scope(view)
                if targets:
                    caller_outward_views.append((view, dict(targets)))
                view = view.parent
            # Establish entry coherence before the callee changes the outward
            # stack. A pending caller write must not be erased by a later read
            # of its older physical target; the nearest declared source wins.
            for _view, targets in caller_outward_views:
                for name, target in targets.items():
                    self._transfer_outward_binding_state(
                        name, self._outward_binding_source(name, target), target
                    )
            for view, targets in caller_outward_views:
                for name, target in targets.items():
                    self._transfer_outward_binding_state(name, target, view)
        caller_entry = self._capture_deferred_flow(self.scope) if request is not None else None
        previous_phase = (self._replay_calls_enabled, self._sync_only_body_analysis)
        previous = self.scope
        previous_loop_controls = self._loop_controls
        previous_terminal_controls = self._terminal_controls
        previous_exception_scope_collectors = self._exception_scope_collectors
        lexical_parent = self._function_definition_scopes.get(node, previous).function_parent()
        if lexical_parent.scope_kind == "module":
            # Module globals follow the active branch, not an older definition snapshot.
            lexical_parent = self._module_scope()
        outward_targets = self._enter_function_binding_scope(node, lexical_parent, arguments)
        self._loop_controls = []
        self._terminal_controls = _TerminalControlBindings(return_scopes=[], raise_scopes=[])
        self._exception_scope_collectors = []
        function_result_was_live = id(node) in self._active_deferred_result_ids()
        self._active_function_replays.add(node)
        self._active_replay_contexts.append(
            (
                object(),
                node,
                tuple(arguments.values()),
                (),
                (),
                (),
                None,
                self._source_nodes(),
                (
                    _TerminalControlBindings(return_scopes=[], raise_scopes=[])
                    if self._invocation_outcome_request() is not None
                    else None
                ),
            )
        )
        self._outward_binding_targets.append(outward_targets)
        return_bindings: list[_ResolvedBinding] = []
        self._return_binding_collectors.append(return_bindings)
        replays_async = isinstance(node, ast.AsyncFunctionDef)
        if replays_async:
            self._active_async_replay_depth += 1
        try:
            with (
                self._temporary_iteration_result(node, prior_live=function_result_was_live)
                if iteration_result_node is not None or id(node) in self._call_result_bindings
                else nullcontext()
            ):
                replay_entry = self.scope.clone()
                yields_result = (
                    iteration_result_node is not None
                    and request is not None
                    and _function_is_generator(node)
                )
                if yields_result:
                    self._call_result_bindings[id(node)] = self._variadic_iterable_binding([])
                falls_through = self._visit_statements(node.body)
                if request is None:
                    result_binding = self._join_resolved_bindings(
                        [
                            *return_bindings,
                            *([_ResolvedBinding(None, None)] if falls_through else []),
                        ]
                    )
                else:
                    result_binding = _ResolvedBinding(None, None)
                normal_outcomes: list[_LexicalBindings] = []
                if request is not None:
                    normal_outcomes = [
                        *self._terminal_controls.return_scopes,
                        *([self.scope.clone()] if falls_through else []),
                    ]
                    none_result = _ResolvedBinding(_KNOWN_NON_APP_REFERENCE, None)
                    candidates = [
                        *(return_bindings if self._terminal_controls.return_scopes else []),
                        *([none_result] if falls_through else []),
                    ]

                    def same_fact(left: object, right: object) -> bool:
                        if type(left) is not type(right):
                            return False
                        if isinstance(left, (_StaticMapping, ast.AST, _LexicalBindings)):
                            return left is right
                        if isinstance(
                            left, (_ResolvedBinding, _DeferredFunctionCall, _StaticMappingEntry)
                        ):
                            return all(
                                same_fact(getattr(left, name), getattr(right, name))
                                for name in left.__dataclass_fields__
                            )
                        if isinstance(left, (tuple, list)):
                            other = cast(Sequence[object], right)
                            return len(left) == len(other) and all(
                                same_fact(x, y) for x, y in zip(left, other, strict=True)
                            )
                        if isinstance(left, (set, frozenset)):
                            remaining = list(cast(AbstractSet[object], right))
                            if len(left) != len(remaining):
                                return False
                            for item in left:
                                index = next(
                                    (
                                        i
                                        for i, candidate in enumerate(remaining)
                                        if same_fact(item, candidate)
                                    ),
                                    None,
                                )
                                if index is None:
                                    return False
                                remaining.pop(index)
                            return True
                        if left is None or isinstance(left, (str, int, float, bool)):
                            return left == right
                        return left is right

                    # Return operands already passed through canonical capture.
                    # Rebuilding their mapping values would erase the identity proof.
                    normalized = candidates
                    if yields_result:
                        normalized = []
                        for outcome in normal_outcomes:
                            state = outcome._flow_snapshot
                            if state is None or id(node) not in state[2]:
                                raise LegacyGrowthAnalysisError(
                                    "generator lost its finalized yield aggregate"
                                )
                            normalized.append(state[2][id(node)])
                    if (
                        not yields_result
                        and normal_outcomes
                        and (
                            not normalized
                            or any(not same_fact(normalized[0], value) for value in normalized[1:])
                        )
                    ):
                        raise LegacyGrowthAnalysisError(
                            "requested invocation has uncorrelated finalized normal return values"
                        )
                    result_binding = (
                        self._join_resolved_bindings(normalized)
                        if yields_result
                        else normalized[0] if normalized else _ResolvedBinding(None, None)
                    )
                    self._remember_captured_binding(result_binding)
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
                        result_binding.ordered_items,
                        result_binding.call_receivers,
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
                        result_binding.ordered_items,
                        result_binding.call_receivers,
                    )
                if request is None:
                    outcomes = [
                        self.scope,
                        *self._terminal_controls.return_scopes,
                        *self._terminal_controls.raise_scopes,
                    ]
                    joined_scope = replay_entry.clone()
                    self._merge_outcomes(joined_scope, outcomes)
                    self._transfer_outward_bindings(joined_scope, outward_targets, previous)
                else:
                    if caller_entry is None:
                        raise AssertionError
                    for outcomes, destination in (
                        (normal_outcomes, request.return_scopes),
                        (self._terminal_controls.raise_scopes, request.raise_scopes),
                    ):
                        for outcome in outcomes:
                            projected = self._project_invocation_scope(
                                outcome,
                                previous,
                                caller_entry,
                                outward_targets=outward_targets,
                                caller_outward_views=caller_outward_views,
                            )
                            if yields_result and destination is request.return_scopes:
                                if not (
                                    iteration_result_node is not None
                                    and outcome._flow_snapshot is not None
                                ):
                                    raise AssertionError
                                yielded = outcome._flow_snapshot[2][id(node)]
                                self._call_result_bindings[id(iteration_result_node)] = yielded
                                self._remember_captured_binding(yielded, enclosing=True)
                                projected._flow_snapshot = self._capture_deferred_flow(projected)
                            destination.append(projected)
                    self._restore_deferred_flow(caller_entry)
                    self.scope = previous
        finally:
            if replays_async:
                self._active_async_replay_depth -= 1
            self._return_binding_collectors.pop()
            self._outward_binding_targets.pop()
            self._active_replay_contexts.pop()
            self._active_function_replays.remove(node)
            self._switch_deferred_scope(previous, restore_flow=False)
            self._loop_controls = previous_loop_controls
            self._terminal_controls = previous_terminal_controls
            self._exception_scope_collectors = previous_exception_scope_collectors
            self._replay_calls_enabled, self._sync_only_body_analysis = previous_phase
        return result_binding


def _collect_module_final_bindings(
    tree: ast.Module,
    *,
    filename: str = LEGACY_APP,
    initial_references: Mapping[str, str],
    preserve_fastapi_conflicts: bool = False,
    preserve_lifecycle_conflicts: bool = False,
    preserve_route_method_conflicts: bool = False,
    ownership_family: Literal["api_key", "openapi"] = "api_key",
    purpose: Literal["ordinary", "ownership_audit"] = "ordinary",
) -> tuple[Mapping[str, str], Mapping[str, str]]:
    visitor = _ApiKeyLookupVisitor(
        filename=filename,
        errors=[],
        initial_references=initial_references,
        preserve_fastapi_conflicts=preserve_fastapi_conflicts,
        preserve_lifecycle_conflicts=preserve_lifecycle_conflicts,
        preserve_route_method_conflicts=preserve_route_method_conflicts,
        analyze_function_bodies=False,
        ownership_family=ownership_family,
        purpose=purpose,
    )
    visitor.visit(tree)
    return visitor.scope.visible_references(), visitor.scope.visible_strings()


def _collect_lexical_binding_snapshots(
    tree: ast.Module,
    *,
    initial_references: Mapping[str, str],
    filename: str = LEGACY_APP,
    ownership_family: Literal["api_key", "openapi"] = "api_key",
    preserve_fastapi_conflicts: bool = False,
    preserve_lifecycle_conflicts: bool = False,
    preserve_route_method_conflicts: bool = False,
    purpose: Literal["ordinary", "ownership_audit"] = "ordinary",
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
        filename=filename,
        initial_references=initial_references,
        preserve_fastapi_conflicts=preserve_fastapi_conflicts,
        preserve_lifecycle_conflicts=preserve_lifecycle_conflicts,
        preserve_route_method_conflicts=preserve_route_method_conflicts,
        ownership_family=ownership_family,
        purpose=purpose,
    )
    _ApiKeyLookupVisitor(
        filename=filename,
        errors=[],
        initial_references=initial_references,
        reference_snapshots=reference_snapshots,
        string_snapshots=string_snapshots,
        call_result_snapshots=call_result_snapshots,
        preserve_fastapi_conflicts=preserve_fastapi_conflicts,
        preserve_lifecycle_conflicts=preserve_lifecycle_conflicts,
        preserve_route_method_conflicts=preserve_route_method_conflicts,
        ownership_family=ownership_family,
        module_late_references=module_late_references,
        module_late_strings=module_late_strings,
        purpose=purpose,
    ).visit(tree)
    return reference_snapshots, string_snapshots, call_result_snapshots


def validate_api_key_dependency_ownership(
    legacy_source: str,
    app_sources: Mapping[str, str],
) -> list[str]:
    """Require full canonical ownership; aggregate retirement rejects Legacy exports."""

    errors: list[str] = []
    app_trees: dict[str, ast.Module] = {}
    for filename, source_text in sorted(app_sources.items()):
        tree, source_errors = _parse_source(source_text, filename=filename)
        errors.extend(source_errors)
        if tree is not None:
            app_trees[filename] = tree
    if CANONICAL_API_KEY not in app_sources:
        errors.append(f"{CANONICAL_API_KEY}: canonical API-key owner source is missing")
    elif (owner_tree := app_trees.get(CANONICAL_API_KEY)) is not None:
        owner_visitor = _ApiKeyLookupVisitor(
            filename=CANONICAL_API_KEY, errors=[], analyze_function_bodies=False
        )
        owner_visitor.visit(owner_tree)
        for name in sorted(CANONICAL_API_KEY_SYMBOLS - owner_visitor.scope.bound_names):
            errors.append(f"{CANONICAL_API_KEY}: canonical API-key owner symbol is missing: {name}")

    legacy_tree, parse_errors = _parse_source(legacy_source, filename=LEGACY_APP)
    errors.extend(parse_errors)
    if legacy_tree is not None:
        locally_defined: set[str] = set()
        postponed_annotations = _has_postponed_annotations(legacy_tree)

        class _ModuleApiKeyDefinitionVisitor(ast.NodeVisitor):
            def _visit_function_header(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
                for expression in (
                    *node.decorator_list,
                    *node.args.defaults,
                    *node.args.kw_defaults,
                ):
                    if expression is not None:
                        self.visit(expression)
                if not postponed_annotations:
                    for argument in _iter_function_parameters(node.args):
                        if argument.annotation is not None:
                            self.visit(argument.annotation)
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
                for expression in (*node.decorator_list, *node.bases):
                    self.visit(expression)
                for keyword in node.keywords:
                    self.visit(keyword.value)

            def visit_Lambda(self, node: ast.Lambda) -> None:
                for default in (*node.args.defaults, *node.args.kw_defaults):
                    if default is not None:
                        self.visit(default)

        definition_visitor = _ModuleApiKeyDefinitionVisitor()
        for statement in legacy_tree.body:
            definition_visitor.visit(statement)
        for name in sorted(locally_defined):
            errors.append(f"{LEGACY_APP}: API-key dependency must not be defined locally: {name}")

        rebound_names: set[str] = set()

        class _TopLevelBindingVisitor(_ModuleApiKeyDefinitionVisitor):
            def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
                self._visit_function_header(node)

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
                self._visit_function_header(node)

            def visit_ClassDef(self, node: ast.ClassDef) -> None:
                rebound_names.add(node.name)
                super().visit_ClassDef(node)

            def visit_Name(self, node: ast.Name) -> None:
                if isinstance(node.ctx, (ast.Store, ast.Del)):
                    rebound_names.add(node.id)

            def visit_comprehension(self, node: ast.comprehension) -> None:
                self.visit(node.iter)
                for condition in node.ifs:
                    self.visit(condition)

            def visit_MatchAs(self, node: ast.MatchAs) -> None:
                if node.name is not None:
                    rebound_names.add(node.name)
                if node.pattern is not None:
                    self.visit(node.pattern)

            def visit_MatchStar(self, node: ast.MatchStar) -> None:
                if node.name is not None:
                    rebound_names.add(node.name)

            def visit_MatchMapping(self, node: ast.MatchMapping) -> None:
                if node.rest is not None:
                    rebound_names.add(node.rest)
                self.generic_visit(node)

            def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
                if not postponed_annotations:
                    self.visit(node.annotation)
                if node.value is not None:
                    self.visit(node.value)
                    self.visit(node.target)

            def visit_Import(self, node: ast.Import) -> None:
                for alias in node.names:
                    rebound_names.add(alias.asname or alias.name.split(".", maxsplit=1)[0])

            def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
                for alias in node.names:
                    bound_name = alias.asname or alias.name
                    if alias.name == "*":
                        errors.append(
                            f"{LEGACY_APP}: canonical API-key dependency star import is forbidden"
                            if node.level == 0 and node.module == "app.routers.api_key"
                            else f"{LEGACY_APP}: unresolved API-key dependency star import is forbidden"
                        )
                        continue
                    if (
                        node.level == 0
                        and node.module == "app.routers.api_key"
                        and alias.name in LEGACY_API_KEY_REEXPORTS
                        and bound_name == alias.name
                    ):
                        continue
                    if alias.name != "*":
                        rebound_names.add(bound_name)

            def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
                if node.type is not None:
                    self.visit(node.type)
                if node.name is not None:
                    rebound_names.add(node.name)
                for statement in node.body:
                    self.visit(statement)

        binding_visitor = _TopLevelBindingVisitor()
        for statement in legacy_tree.body:
            binding_visitor.visit(statement)
        execution_visitor = _ApiKeyLookupVisitor(
            filename=LEGACY_APP, errors=[], analyze_function_bodies=False
        )
        execution_visitor.visit(legacy_tree)
        for name in sorted(CANONICAL_API_KEY_SYMBOLS):
            description = (
                "canonical API-key compatibility re-export"
                if name in LEGACY_API_KEY_REEXPORTS
                else "canonical API-key dependency"
            )
            diagnostic = f"{LEGACY_APP}: {description} must not be rebound: {name}"
            if name in rebound_names or diagnostic in execution_visitor.errors:
                errors.append(diagnostic)

    for filename, tree in sorted(app_trees.items()):
        module_late_references, module_late_strings = _collect_module_final_bindings(
            tree, filename=filename, initial_references={}, purpose="ownership_audit"
        )
        _ApiKeyLookupVisitor(
            filename=filename,
            errors=errors,
            reference_snapshots={},
            string_snapshots={},
            module_late_references=module_late_references,
            module_late_strings=module_late_strings,
            purpose="ownership_audit",
            expression_snapshots_only=True,
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
    name_resolver: Callable[[ast.AST], str | None] | None = None,
    name_predicate: Callable[[str | None], bool] | None = None,
) -> bool:
    positional_arguments, unresolved = _expand_static_positional_arguments(node.args)
    arguments = list(positional_arguments)
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
        legacy_method = _namespace_mutator_method(function_reference, legacy_only=True)
        dict_method_prefix = "builtins.dict."
        if legacy_method is not None:
            method_name = legacy_method
        else:
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
            if unresolved:
                return False
            arguments = arguments[1:]
    if unresolved:
        return name_resolver is None
    if method_name in {"__ior__", "update", "__init__"}:
        if any(
            (
                name_predicate(keyword.arg)
                if name_predicate is not None
                else keyword.arg in protected_names
            )
            for keyword in node.keywords
            if keyword.arg is not None
        ):
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
                name_resolver=name_resolver,
                name_predicate=name_predicate,
            ):
                return True
        return False
    if method_name in {"clear", "popitem", "*"}:
        return True
    if method_name in {"__delitem__", "__setitem__", "pop", "setdefault"}:
        if not arguments:
            return name_resolver is None
        key_name = (
            name_resolver(arguments[0])
            if name_resolver is not None
            else _resolve_static_string(arguments[0], static_string_bindings)
        )
        if name_predicate is not None:
            return name_predicate(key_name)
        return key_name is None or key_name in protected_names
    return False


def _mapping_may_mutate_protected_namespace(
    node: ast.AST,
    *,
    protected_names: AbstractSet[str],
    static_string_bindings: Mapping[str, str],
    static_mapping_bindings: Mapping[str, ast.Dict],
    name_resolver: Callable[[ast.AST], str | None] | None = None,
    name_predicate: Callable[[str | None], bool] | None = None,
) -> bool:
    mapping = _resolve_static_mapping(node, static_mapping_bindings)
    if mapping is None:
        return name_resolver is None
    for key, _value in mapping:
        if key is None:
            if name_resolver is None:
                return True
            continue
        resolved_key = (
            name_resolver(key)
            if name_resolver is not None
            else _resolve_static_string(key, static_string_bindings)
        )
        if (
            name_predicate(resolved_key)
            if name_predicate is not None
            else resolved_key is None or resolved_key in protected_names
        ):
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
            for default in (*node.args.defaults, *node.args.kw_defaults):
                if default is not None:
                    self.visit(default)

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
                    and alias.name not in RETIRED_LEGACY_PYTHON_BINDINGS
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


def _namespace_rebindings(
    tree: ast.Module,
    protected_names: set[str],
) -> set[str]:
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


def validate_retired_legacy_python_bindings(
    source_text: str,
    *,
    filename: str = LEGACY_APP,
) -> list[str]:
    """Reject exact retired ordinary module bindings in legacy_app.py only."""

    if filename != LEGACY_APP:
        return []

    tree, parse_errors = _parse_source(source_text, filename=filename)
    if parse_errors or tree is None:
        return parse_errors

    protected_names = set(RETIRED_LEGACY_PYTHON_BINDINGS)
    assigned_names = _assigned_names(tree)
    explicit_globals = {
        name for node in ast.walk(tree) if isinstance(node, ast.Global) for name in node.names
    }
    rebound = (assigned_names | explicit_globals) & protected_names

    errors = [
        f"{filename}: retired Python compatibility binding is forbidden: {name}"
        for name in sorted(rebound)
    ]
    if any(
        isinstance(node, ast.ImportFrom) and any(alias.name == "*" for alias in node.names)
        for node in ast.walk(tree)
    ):
        errors.append(
            f"{filename}: star import is forbidden after legacy Python binding retirement"
        )
    if "__getattr__" in assigned_names | explicit_globals:
        errors.append(
            f"{filename}: module-level __getattr__ is forbidden after legacy Python "
            "binding retirement"
        )
    return errors


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
            and node.func.attr in _DICT_NAMESPACE_LOOKUP_METHODS
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


def _record_main_legacy_openapi_lookups(tree: ast.Module, errors: list[str]) -> None:
    """Report only each visited node's existing lexical and resolved-call evidence."""

    references, strings, results = _collect_lexical_binding_snapshots(
        tree,
        filename=CANONICAL_MAIN,
        initial_references={},
        ownership_family="openapi",
        purpose="ownership_audit",
    )
    evaluator = _ApiKeyLookupVisitor(
        filename=CANONICAL_MAIN,
        errors=[],
        analyze_function_bodies=False,
        ownership_family="openapi",
    )
    evaluator._postponed_annotations = _has_postponed_annotations(tree)
    evaluator._call_result_bindings = dict(results)

    def select_own_environment(node: ast.AST) -> bool:
        node_id = id(node)
        if node_id not in references or node_id not in strings:
            return False
        evaluator.scope = _LexicalBindings(parent=None)
        evaluator.scope.references = dict(references[node_id])
        evaluator.scope.strings = dict(strings[node_id])
        return True

    def own_reference(node: ast.AST) -> str | None:
        return evaluator._resolve_reference(node) if select_own_environment(node) else None

    def own_string(node: ast.AST) -> str | None:
        return evaluator._resolve_string(node) if select_own_environment(node) else None

    for node in ast.walk(tree):
        if not select_own_environment(node):
            continue
        if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module == "legacy_app":
            for alias in node.names:
                if evaluator._is_protected_ownership_symbol(alias.name):
                    errors.append(
                        f"{CANONICAL_MAIN}: OpenAPI symbol must not be imported through legacy: "
                        f"{alias.name}"
                    )
        elif (
            isinstance(node, ast.Attribute)
            and evaluator._is_protected_ownership_symbol(node.attr)
            and evaluator._is_legacy_module_reference(own_reference(node.value))
        ):
            errors.append(f"{CANONICAL_MAIN}: OpenAPI symbol must not be accessed through legacy")
        elif (
            isinstance(node, ast.Subscript)
            and evaluator._is_legacy_namespace_reference(own_reference(node.value))
            and evaluator._is_protected_ownership_symbol(own_string(node.slice))
        ):
            errors.append(f"{CANONICAL_MAIN}: OpenAPI symbol must not be accessed through legacy")
        elif isinstance(node, ast.Call):
            arguments, unresolved = _expand_static_positional_arguments(node.args)
            if unresolved:
                continue
            function_reference = own_reference(node.func)
            callee_binding = results.get(id(node.func))
            if callee_binding is not None and select_own_environment(node.func):
                actual_bindings = [
                    _ResolvedBinding(own_reference(argument), own_string(argument))
                    for argument in arguments
                    if id(argument) in references and id(argument) in strings
                ]
                if len(actual_bindings) == len(arguments):
                    for template in callee_binding.deferred_calls:
                        if template.builtin_reference is None:
                            continue
                        bound = evaluator._resolve_partial_invocation_bindings(
                            template, node, positional_override=actual_bindings
                        )
                        if (
                            bound is not None
                            and evaluator._is_legacy_module_reference(bound["object"].reference)
                            and evaluator._is_protected_ownership_symbol(bound["name"].string)
                        ):
                            errors.append(
                                f"{CANONICAL_MAIN}: OpenAPI symbol must not be accessed through legacy"
                            )
            unbound_mutator = (
                function_reference is not None
                and function_reference.startswith("builtins.dict.")
                and function_reference.rpartition(".")[2] in _MAPPING_MUTATOR_METHODS
            )
            stored_legacy_mutator = (
                isinstance(node.func, ast.Name)
                and _namespace_mutator_method(function_reference, legacy_only=True) is not None
            )
            mutation_receiver = (
                arguments[0]
                if unbound_mutator and arguments
                else (
                    node.func.value
                    if isinstance(node.func, ast.Attribute)
                    and node.func.attr in _MAPPING_MUTATOR_METHODS
                    else None
                )
            )
            if (
                select_own_environment(node.func)
                and (
                    stored_legacy_mutator
                    or mutation_receiver is not None
                    and evaluator._is_legacy_namespace_reference(own_reference(mutation_receiver))
                )
                and all(select_own_environment(keyword.value) for keyword in node.keywords)
                and _mutates_protected_namespace(
                    node,
                    protected_names=CANONICAL_OPENAPI_SYMBOLS,
                    references=references[id(node.func)],
                    static_string_bindings=strings[id(node.func)],
                    static_mapping_bindings={},
                    name_resolver=own_string,
                    name_predicate=evaluator._is_protected_ownership_symbol,
                )
            ):
                errors.append(
                    f"{CANONICAL_MAIN}: OpenAPI symbol must not be accessed through legacy"
                )
                continue
            if (
                function_reference
                in {
                    "builtins.getattr",
                    _POSSIBLE_GETATTR_REFERENCE,
                    "builtins.setattr",
                    "builtins.delattr",
                }
                and len(arguments) >= 2
                and evaluator._is_legacy_module_reference(own_reference(arguments[0]))
                and evaluator._is_protected_ownership_symbol(own_string(arguments[1]))
            ):
                errors.append(
                    f"{CANONICAL_MAIN}: OpenAPI symbol must not be accessed through legacy"
                )
                continue
            receiver = (
                arguments[0]
                if function_reference in _UNBOUND_DICT_LOOKUP_REFERENCES and arguments
                else node.func.value if isinstance(node.func, ast.Attribute) else None
            )
            namespace_name = evaluator._legacy_namespace_call_name(
                node,
                function_reference=function_reference,
                receiver_reference=own_reference(receiver) if receiver is not None else None,
            )
            if namespace_name is not None and evaluator._is_protected_ownership_symbol(
                own_string(namespace_name)
            ):
                errors.append(
                    f"{CANONICAL_MAIN}: OpenAPI symbol must not be accessed through legacy"
                )


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

    foreign_import_rebindings: set[str] = set()
    for statement in legacy_tree.body:
        if isinstance(statement, ast.ImportFrom) and statement.module == CANONICAL_OPENAPI.replace(
            "/", "."
        ).removesuffix(".py"):
            continue
        if isinstance(statement, ast.ImportFrom):
            for alias in statement.names:
                bound_name = alias.asname or alias.name
                if bound_name in CANONICAL_OPENAPI_SYMBOLS:
                    foreign_import_rebindings.add(bound_name)
        elif isinstance(statement, ast.Import):
            for alias in statement.names:
                bound_name = alias.asname or alias.name.split(".", 1)[0]
                if bound_name in CANONICAL_OPENAPI_SYMBOLS:
                    foreign_import_rebindings.add(bound_name)
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
    _record_main_legacy_openapi_lookups(main_tree, errors)

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
                filename=LEGACY_APP,
            )
        )
        errors.extend(
            validate_retired_legacy_python_bindings(
                legacy_source,
                filename=LEGACY_APP,
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
