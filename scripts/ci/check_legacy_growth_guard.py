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
    "api_key": 5,
    "auth": 0,
    "billing": 0,
    "entitlement": 0,
    "llm": 2,
    "provider": 1,
    "quota": 1,
    "receipt": 0,
    "subscription": 0,
}
SENSITIVE_APP_SURFACE_LIMITS: Mapping[str, int] = {
    "api_key": 6,
    "auth": 0,
    "billing": 0,
    "entitlement": 0,
    "llm": 0,
    "provider": 0,
    "quota": 0,
    "receipt": 0,
    "subscription": 0,
}

ALLOWED_LEGACY_ROUTE_FACTS = frozenset(
    {
        LegacyFact("decorator", "middleware", "http", "csp_nonce_middleware"),
        LegacyFact("decorator", "middleware", "http", "log_requests"),
        LegacyFact("decorator", "post", "/api/v1/insight", "insight_v1_route"),
        LegacyFact("decorator", "post", "/insight", "insight_route"),
        LegacyFact("decorator", "post", "/api/v1/premium/plate", "api_premium_plate"),
        LegacyFact("decorator", "post", "/api/v1/premium/bmr", "api_premium_bmr"),
        LegacyFact("decorator", "post", "/premium_bmr", "premium_bmr_legacy"),
        LegacyFact("decorator", "post", "/premium_targets", "premium_targets_legacy"),
        LegacyFact("decorator", "post", "/api/v1/premium/targets", "api_who_targets"),
        LegacyFact("decorator", "post", "/api/v1/premium/plan/week", "api_weekly_menu"),
        LegacyFact("decorator", "post", "/api/v1/premium/gaps", "api_nutrient_gaps"),
        LegacyFact("registration", "include_router", "foods_router", ""),
        LegacyFact("registration", "include_router", "nutrition_recommendations_router", ""),
        LegacyFact("registration", "include_router", "restaurants_router", ""),
        LegacyFact("registration", "include_router", "recipes_router", ""),
        LegacyFact("registration", "include_router", "users_router", ""),
        LegacyFact("registration", "include_router", "catalog_router", ""),
        LegacyFact("registration", "include_router", "shopping_list_pro_router", ""),
        LegacyFact("registration", "include_router", "shoplist_day_router", ""),
        LegacyFact("registration", "include_router", "bmi_router", ""),
        LegacyFact("registration", "include_router", "bayes_adherence.router", ""),
        LegacyFact("registration", "include_router", "nutrition_log.router", ""),
        LegacyFact("registration", "include_router", "legacy_nutrition_alias_router", ""),
        LegacyFact("registration", "include_router", "get_bodyfat_router()", ""),
        LegacyFact("registration", "include_router", "bmi_pro_router", ""),
        LegacyFact("registration", "include_router", "business_router", ""),
        LegacyFact("registration", "include_router", "test_router.router", ""),
        LegacyFact("registration", "include_router", "bmi_pro_legacy_alias_router", ""),
    }
)

ALLOWED_ROUTER_IMPORT_FACTS = frozenset(
    {
        LegacyFact("router_import", "app.routers", "bayes_adherence", ""),
        LegacyFact("router_import", "app.routers", "nutrition_log", ""),
        LegacyFact("router_import", "app.routers", "test", "test_router"),
        LegacyFact("router_import", "app.routers", "vip", "_vip_mod"),
        LegacyFact("router_import", "app.routers.api_key", "api_key_header", ""),
        LegacyFact("router_import", "app.routers.bmi", "bmi_calculate_handler", ""),
        LegacyFact("router_import", "app.routers.bmi", "router", "bmi_router"),
        LegacyFact("router_import", "app.routers.bmi_pro", "router", "bmi_pro_router"),
        LegacyFact(
            "router_import",
            "app.routers.bmi_pro_legacy_alias",
            "router",
            "bmi_pro_legacy_alias_router",
        ),
        LegacyFact("router_import", "app.routers.bodyfat", "get_router", "get_bodyfat_router"),
        LegacyFact("router_import", "app.routers.business", "router", "business_router"),
        LegacyFact("router_import", "app.routers.catalog", "router", "catalog_router"),
        LegacyFact("router_import", "app.routers.foods", "router", "foods_router"),
        LegacyFact(
            "router_import",
            "app.routers.legacy_nutrition_alias",
            "router",
            "legacy_nutrition_alias_router",
        ),
        LegacyFact(
            "router_import",
            "app.routers.nutrition_recommendations",
            "router",
            "nutrition_recommendations_router",
        ),
        LegacyFact(
            "router_import", "app.routers.pro_nutrition_contracts", "pro_nutrition_plate", ""
        ),
        LegacyFact(
            "router_import", "app.routers.pro_nutrition_contracts", "pro_nutrition_targets", ""
        ),
        LegacyFact(
            "router_import",
            "app.routers.pro_registration",
            "register_pro_routes",
            "_register_pro_routes",
        ),
        LegacyFact("router_import", "app.routers.recipes", "router", "recipes_router"),
        LegacyFact("router_import", "app.routers.restaurants", "router", "restaurants_router"),
        LegacyFact("router_import", "app.routers.shoplist_day", "router", "shoplist_day_router"),
        LegacyFact(
            "router_import",
            "app.routers.shopping_list_pro",
            "router",
            "shopping_list_pro_router",
        ),
        LegacyFact("router_import", "app.routers.users", "router", "users_router"),
        LegacyFact(
            "router_import",
            "app.routers.vip",
            "execute_legacy_premium_week_alias_payload",
            "",
        ),
        LegacyFact("router_import", "app.routers.vip_registration", "register_vip_routes", ""),
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
) -> str | None:
    if not isinstance(func, ast.Attribute) or func.attr not in methods:
        return None
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
    return None


def collect_legacy_route_facts(source_text: str, *, filename: str = LEGACY_APP) -> set[LegacyFact]:
    """Return route and router-registration facts from legacy_app.py source."""

    tree, errors = _parse_source(source_text, filename=filename)
    if errors or tree is None:
        return set()

    facts: set[LegacyFact] = set()
    app_aliases, router_aliases = _collect_app_aliases(tree)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for decorator in node.decorator_list:
                if not isinstance(decorator, ast.Call):
                    continue
                action = _app_call_action(
                    decorator.func,
                    APP_ROUTE_METHODS,
                    app_aliases=app_aliases,
                    router_aliases=router_aliases,
                )
                if action is not None:
                    facts.add(
                        LegacyFact("decorator", action, _first_arg_label(decorator), node.name)
                    )
        elif isinstance(node, ast.Call):
            call = node
            action = _app_call_action(
                call.func,
                APP_REGISTRATION_METHODS,
                app_aliases=app_aliases,
                router_aliases=router_aliases,
            )
            if action is not None:
                facts.add(LegacyFact("registration", action, _first_arg_label(call), ""))
    return facts


def collect_router_import_facts(source_text: str, *, filename: str = LEGACY_APP) -> set[LegacyFact]:
    """Return app.routers import facts from legacy_app.py source."""

    tree, errors = _parse_source(source_text, filename=filename)
    if errors or tree is None:
        return set()

    facts: set[LegacyFact] = set()
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
    return facts


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
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if (
            _app_call_action(
                node.func,
                app_surface_methods,
                app_aliases=app_aliases,
                router_aliases=router_aliases,
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
    router_import_facts = collect_router_import_facts(source_text, filename=filename)
    sensitive_counts = collect_sensitive_call_counts(source_text, filename=filename)
    sensitive_app_surface_counts = collect_sensitive_app_surface_counts(
        source_text,
        filename=filename,
    )

    for fact in sorted(route_facts - set(allowed_route_facts)):
        errors.append(f"{filename}: unexpected legacy route growth: {fact.display()}")
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
