"""Bounded contract for canonical FastAPI construction and composition."""

from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import subprocess
import sys
import textwrap
from typing import Any

import pytest

_CANONICAL_OWNER = Path("app/bootstrap/application.py")
_MIRRORS = (
    "VIP_MODULE_ENABLED",
    "vip_router",
    "pro_router",
    "premium_week_router",
    "FEATURE_BMI_PRO_ENABLED",
    "bmi_router",
    "bmi_pro_router",
    "bmi_pro_legacy_alias_router",
)
_IMPORT_SCENARIOS = (
    "from app.bootstrap import application as canonical; import app.main as main; "
    "import legacy_app; import app as package",
    "import legacy_app; from app.bootstrap import application as canonical; "
    "import app.main as main; import app as package",
    "import app as package; package.app; "
    "from app.bootstrap import application as canonical; import app.main as main; "
    "import legacy_app",
)
_HTTP_CONTRACTS = (
    ("/", "GET"),
    ("/legacy/bmi-calculator", "GET"),
    ("/sitemap.xml", "GET"),
    ("/api/v1/feedback/rag", "POST"),
    ("/api/v1/pro/cbt/insight", "POST"),
    ("/api/v1/pro/fitchef/explain", "POST"),
    ("/api/v1/internal/creative-research/pilot", "POST"),
    ("/api/v1/internal/paywall/events", "POST"),
)


def _is_direct_fastapi_call(call: ast.Call) -> bool:
    return ast.unparse(call.func) in {"FastAPI", "fastapi.FastAPI", "fastapi.applications.FastAPI"}


def test_one_direct_constructor_belongs_to_the_canonical_owner() -> None:
    sources = [Path("legacy_app.py"), *sorted(Path("app").rglob("*.py"))]
    trees = {
        path: ast.parse(path.read_text(encoding="utf-8"), filename=str(path)) for path in sources
    }
    calls = [
        path
        for path, tree in trees.items()
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and _is_direct_fastapi_call(node)
    ]

    assert calls == [_CANONICAL_OWNER]
    assert not any(
        isinstance(node, ast.ImportFrom)
        and node.module == "legacy_app"
        and any(alias.name == "app" for alias in node.names)
        for node in ast.walk(trees[Path("app/main.py")])
    )


def test_runtime_identity_lifespan_and_private_constructor_isolation() -> None:
    import app
    import app.main as main
    import legacy_app
    from app.bootstrap import application
    from app.bootstrap.lifespan import application_lifespan

    assert application.app is main.app is legacy_app.app is app.app
    assert application.app.router.lifespan_context is application_lifespan
    first = application._create_fastapi_application(application.APPLICATION_METADATA)
    second = application._create_fastapi_application(application.APPLICATION_METADATA)
    assert first is not second
    assert first.router.lifespan_context is second.router.lifespan_context is application_lifespan
    assert first.contact is not second.contact
    assert first.license_info is not second.license_info
    assert first.openapi_tags is not second.openapi_tags
    assert first.openapi_tags[0] is not second.openapi_tags[0]
    first.contact["name"] = "mutated"
    first.license_info["name"] = "mutated"
    first.openapi_tags[0]["description"] = "mutated"
    assert second.contact["name"] == application.APPLICATION_METADATA.contact_name
    assert second.license_info["name"] == application.APPLICATION_METADATA.license_name
    assert (
        second.openapi_tags[0]["description"]
        == application.APPLICATION_METADATA.tags[0].description
    )


def _run_import_scenario(imports: str) -> list[Any]:
    scenario = textwrap.dedent(f"""
        import hashlib, json
        {imports}
        from app.bootstrap.http_stack import _owned_middleware_projection
        from app.bootstrap.lifespan import application_lifespan
        from app.effective_routes import iter_effective_route_candidates, route_endpoint, route_include_in_schema, route_methods, route_path

        def routes(target): return [[route_path(route), sorted(route_methods(route)) or ["WEBSOCKET"], f"{{route_endpoint(route).__module__}}.{{route_endpoint(route).__qualname__}}", route_include_in_schema(route)] for route in iter_effective_route_candidates(target.routes)]
        def mirror(value): return value if value is None or isinstance(value, (bool, int, str)) else routes(value)

        assert canonical.app is main.app is legacy_app.app is package.app
        assert canonical.app.router.lifespan_context is application_lifespan
        def snapshot():
            schema = json.dumps(canonical.app.openapi(), sort_keys=True, separators=(",", ":"))
            return [routes(canonical.app), list(_owned_middleware_projection(canonical.app)), hashlib.sha256(schema.encode()).hexdigest(), {{name: mirror(getattr(main, name)) for name in {list(_MIRRORS)!r}}}]

        before = snapshot()
        assert all(getattr(main, name) is getattr(legacy_app, name) for name in {list(_MIRRORS)!r})
        assert main.ensure_canonical_app_bootstrap(canonical.app) is canonical.app
        assert snapshot() == before
        print("OWNERSHIP_RESULT=" + json.dumps(before, sort_keys=True))
    """)
    env = os.environ.copy()
    env.update({"APP_ENV": "test", "ENVIRONMENT": "test", "TESTING": "true"})
    for (
        name
    ) in "BUSINESS_MODULE_ENABLED ENABLE_TEST_ROUTES FEATURE_BMI_PRO_ENABLED FEATURE_PREMIUM_WEEK_ENABLED VIP_MODULE_ENABLED".split():
        env.pop(name, None)
    completed = subprocess.run(
        [sys.executable, "-c", scenario],
        capture_output=True,
        text=True,
        env=env,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    result_line = next(
        line for line in completed.stdout.splitlines() if "OWNERSHIP_RESULT=" in line
    )
    return json.loads(result_line.removeprefix("OWNERSHIP_RESULT="))


def test_fresh_import_orders_have_relative_runtime_parity() -> None:
    results = [_run_import_scenario(imports) for imports in _IMPORT_SCENARIOS]
    assert results[1:] == results[:1] * (len(results) - 1)


@pytest.mark.parametrize(("path", "method"), _HTTP_CONTRACTS)
@pytest.mark.parametrize("owners", ("f", "cc", "ff", "cf", "fc"))
def test_bespoke_http_owner_states_fail_closed(path: str, method: str, owners: str) -> None:
    import app.main as main
    from fastapi import FastAPI

    target = FastAPI()
    canonical = main.route_endpoint_for_path_method(main.app.routes, path, method)
    for owner in owners:
        endpoint = canonical if owner == "c" else (lambda: None)
        target.add_api_route(path, endpoint, methods=[method])
    before = (tuple(target.routes), tuple(target.user_middleware))
    with pytest.raises(RuntimeError, match="Duplicate"):
        main.ensure_canonical_app_bootstrap(target)
    assert (tuple(target.routes), tuple(target.user_middleware)) == before


@pytest.mark.parametrize("state", ("c|", "f|f", "c|f", "cc|", "h|"))
def test_websocket_owner_states_fail_closed(state: str) -> None:
    import app.main as main
    from fastapi import FastAPI

    target = FastAPI()
    canonical = (main.realtime_ws.ws_pro, main.realtime_ws.ws_root)
    for index, owners in enumerate(state.split("|")):
        for owner in owners:
            path = main._WS_ROUTE_PATHS[index]
            if owner == "h":
                target.add_api_route(path, lambda: None, methods=["GET"])
            else:
                target.add_api_websocket_route(
                    path, canonical[index] if owner == "c" else lambda _: None
                )
    before = tuple(target.routes)
    with pytest.raises(RuntimeError):
        main.ensure_canonical_app_bootstrap(target)
    assert tuple(target.routes) == before


def test_test_owned_composition_and_legacy_alias_do_not_rebind_canonical(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app
    import app.main as main
    import legacy_app
    from app.bootstrap import application

    test_owned = application._create_fastapi_application(application.APPLICATION_METADATA)
    assert main.ensure_canonical_app_bootstrap(test_owned) is test_owned
    assert main.ensure_canonical_app_bootstrap(test_owned) is test_owned
    assert application.app is main.app
    monkeypatch.setattr(legacy_app, "app", test_owned)
    assert app.app is test_owned
    assert application.app is main.app
