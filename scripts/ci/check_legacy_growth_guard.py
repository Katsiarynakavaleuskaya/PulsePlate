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
    {"api_route", "delete", "get", "head", "options", "patch", "post", "put", "trace", "websocket"}
)
APP_REGISTRATION_METHODS = frozenset({"add_api_route", "include_router"})
SENSITIVE_CALL_KEYWORDS: tuple[str, ...] = (
    "billing",
    "entitlement",
    "llm",
    "provider",
    "quota",
    "receipt",
    "subscription",
)
SENSITIVE_CALL_LIMITS: Mapping[str, int] = {
    "billing": 0,
    "entitlement": 0,
    "llm": 1,
    "provider": 1,
    "quota": 1,
    "receipt": 0,
    "subscription": 0,
}

ALLOWED_LEGACY_ROUTE_FACTS = frozenset(
    {
        LegacyFact("decorator", "get", "/api/v1/admin/status", "admin_status"),
        LegacyFact("decorator", "get", "/health/db", "database_health"),
        LegacyFact("decorator", "get", "/ready", "ready"),
        LegacyFact("decorator", "get", "/favicon.ico", "favicon"),
        LegacyFact("decorator", "get", "/health", "health"),
        LegacyFact("decorator", "get", "/api/v1/health", "health_v1"),
        LegacyFact("decorator", "get", "/privacy", "privacy"),
        LegacyFact("decorator", "get", "/terms", "terms"),
        LegacyFact("decorator", "post", "/admin/logs/cleanup", "cleanup_expired_logs"),
        LegacyFact("decorator", "post", "/bmi", "bmi_endpoint"),
        LegacyFact("decorator", "post", "/plan", "plan_endpoint"),
        LegacyFact("decorator", "post", "/api/v1/bmi", "bmi_endpoint_v1"),
        LegacyFact("decorator", "post", "/api/v1/insight", "insight_v1_route"),
        LegacyFact("decorator", "post", "/insight", "insight_route"),
        LegacyFact("decorator", "post", "/api/v1/premium/plate", "api_premium_plate"),
        LegacyFact("decorator", "post", "/api/v1/premium/bmr", "api_premium_bmr"),
        LegacyFact("decorator", "post", "/premium_bmr", "premium_bmr_legacy"),
        LegacyFact("decorator", "post", "/premium_targets", "premium_targets_legacy"),
        LegacyFact("decorator", "post", "/api/v1/premium/targets", "api_who_targets"),
        LegacyFact("decorator", "post", "/api/v1/premium/plan/week", "api_weekly_menu"),
        LegacyFact("decorator", "post", "/api/v1/premium/gaps", "api_nutrient_gaps"),
        LegacyFact("decorator", "get", "/debug_env", "debug_env"),
        LegacyFact("decorator", "get", "/api/v1/admin/db-status", "get_database_status"),
        LegacyFact("decorator", "post", "/api/v1/admin/force-update", "force_database_update"),
        LegacyFact("decorator", "get", "/api/v1/admin/check-updates", "check_for_updates"),
        LegacyFact("decorator", "post", "/api/v1/admin/rollback", "rollback_database"),
        LegacyFact(
            "decorator",
            "get",
            "/api/v1/premium/exports/day/{plan_id}.csv",
            "export_daily_plan_csv_route",
        ),
        LegacyFact("decorator", "post", "/api/v1/export/pdf", "export_pdf_generic_route"),
        LegacyFact(
            "decorator",
            "get",
            "/api/v1/premium/exports/week/{plan_id}.csv",
            "export_weekly_plan_csv_route",
        ),
        LegacyFact(
            "decorator",
            "get",
            "/api/v1/premium/exports/day/{plan_id}.pdf",
            "export_daily_plan_pdf_route",
        ),
        LegacyFact(
            "decorator",
            "get",
            "/api/v1/premium/exports/week/{plan_id}.pdf",
            "export_weekly_plan_pdf_route",
        ),
        LegacyFact("registration", "include_router", "foods_router", ""),
        LegacyFact("registration", "include_router", "nutrition_recommendations_router", ""),
        LegacyFact("registration", "include_router", "restaurants_router", ""),
        LegacyFact("registration", "include_router", "recipes_router", ""),
        LegacyFact("registration", "include_router", "users_router", ""),
        LegacyFact("registration", "include_router", "catalog_router", ""),
        LegacyFact("registration", "include_router", "restaurant_moderation_router", ""),
        LegacyFact("registration", "include_router", "export_router", ""),
        LegacyFact("registration", "include_router", "plan_router", ""),
        LegacyFact("registration", "include_router", "shoplist_router", ""),
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
        LegacyFact("router_import", "app.routers.legal", "build_terms_endpoint_payload", ""),
        LegacyFact(
            "router_import",
            "app.routers.nutrition_recommendations",
            "router",
            "nutrition_recommendations_router",
        ),
        LegacyFact("router_import", "app.routers.plan_export", "export_router", ""),
        LegacyFact("router_import", "app.routers.plan_export", "plan_router", ""),
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
        LegacyFact(
            "router_import",
            "app.routers.restaurants",
            "moderation_router",
            "restaurant_moderation_router",
        ),
        LegacyFact("router_import", "app.routers.restaurants", "router", "restaurants_router"),
        LegacyFact("router_import", "app.routers.shoplist_day", "router", "shoplist_day_router"),
        LegacyFact("router_import", "app.routers.shoplist_export", "router", "shoplist_router"),
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


def collect_legacy_route_facts(source_text: str, *, filename: str = LEGACY_APP) -> set[LegacyFact]:
    """Return route and router-registration facts from legacy_app.py source."""

    tree, errors = _parse_source(source_text, filename=filename)
    if errors or tree is None:
        return set()

    facts: set[LegacyFact] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for decorator in node.decorator_list:
                if not isinstance(decorator, ast.Call):
                    continue
                func = decorator.func
                if (
                    isinstance(func, ast.Attribute)
                    and isinstance(func.value, ast.Name)
                    and func.value.id == "app"
                    and func.attr in APP_ROUTE_METHODS
                ):
                    facts.add(
                        LegacyFact("decorator", func.attr, _first_arg_label(decorator), node.name)
                    )
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            call = node.value
            func = call.func
            if (
                isinstance(func, ast.Attribute)
                and isinstance(func.value, ast.Name)
                and func.value.id == "app"
                and func.attr in APP_REGISTRATION_METHODS
            ):
                facts.add(LegacyFact("registration", func.attr, _first_arg_label(call), ""))
    return facts


def collect_router_import_facts(source_text: str, *, filename: str = LEGACY_APP) -> set[LegacyFact]:
    """Return app.routers import facts from legacy_app.py source."""

    tree, errors = _parse_source(source_text, filename=filename)
    if errors or tree is None:
        return set()

    facts: set[LegacyFact] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or node.module is None:
            continue
        if node.module != "app.routers" and not node.module.startswith("app.routers."):
            continue
        for alias in node.names:
            facts.add(LegacyFact("router_import", node.module, alias.name, alias.asname or ""))
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

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func_name = _safe_unparse(node.func).casefold()
        for keyword in SENSITIVE_CALL_KEYWORDS:
            if keyword in func_name:
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
) -> list[str]:
    """Return deterministic errors for legacy_app.py growth."""

    tree, parse_errors = _parse_source(source_text, filename=filename)
    if parse_errors or tree is None:
        return parse_errors

    errors: list[str] = []
    route_facts = collect_legacy_route_facts(source_text, filename=filename)
    router_import_facts = collect_router_import_facts(source_text, filename=filename)
    sensitive_counts = collect_sensitive_call_counts(source_text, filename=filename)

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


def _read(path: Path, repo_root: Path, errors: list[str]) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f"{_display(path, repo_root)}: unable to read: {type(exc).__name__}")
        return ""


def validate_repo(repo_root: Path) -> list[str]:
    """Validate the repo's legacy compatibility seam."""

    errors: list[str] = []
    legacy_path = repo_root / LEGACY_APP
    doc_path = repo_root / LEGACY_SEAM_DOC
    legacy_source = _read(legacy_path, repo_root, errors)
    doc_text = _read(doc_path, repo_root, errors)
    if legacy_source:
        errors.extend(
            validate_legacy_growth(legacy_source, filename=_display(legacy_path, repo_root))
        )
    if doc_text:
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
