import ast
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
import textwrap

import pytest
from fastapi import APIRouter, Depends, FastAPI
from starlette.routing import Route
import app
import app.main as main
from app.bootstrap import application
from app.bootstrap.lifespan import application_lifespan
from app.effective_routes import route_endpoint_for_path_method
import legacy_app

_RETIRED_REGISTRATION_MIRRORS = (
    "VIP_MODULE_ENABLED",
    "vip_router",
    "pro_router",
    "premium_week_router",
    "FEATURE_BMI_PRO_ENABLED",
    "bmi_router",
    "bmi_pro_router",
    "bmi_pro_legacy_alias_router",
)
_IMPORT_SCENARIOS = """import app as package; import app.main as main; import legacy_app; from app.bootstrap import application as canonical
import app.main as main; import app as package; import legacy_app; from app.bootstrap import application as canonical
import legacy_app; import app.main as main; import app as package; from app.bootstrap import application as canonical""".splitlines()
_HTTP_CONTRACT_SPEC = "/:GET|/legacy/bmi-calculator:GET|/sitemap.xml:GET|/api/v1/feedback/rag:POST|/api/v1/pro/cbt/insight:POST|/api/v1/pro/fitchef/explain:POST|/api/v1/pro/fitchef/recommend:POST|/api/v1/internal/creative-research/pilot:POST|/api/v1/internal/paywall/events:POST"
_HTTP_CONTRACTS = tuple(x.rsplit(":", 1) for x in _HTTP_CONTRACT_SPEC.split("|"))
_HTTP_SOURCES = "_FEEDBACK_ROUTE_PATH:feedback_router _CBT_INSIGHT_ROUTE_PATH:cbt_insight_router _FITCHEF_STRUCTURED_ROUTE_PATH:fitchef_structured_router _CREATIVE_RESEARCH_PILOT_ROUTE_PATH:creative_research_internal_router _PAYWALL_EVENTS_ROUTE_PATH:paywall_analytics_router".split()
_OPTIONAL_ENV = "BUSINESS_MODULE_ENABLED ENABLE_TEST_ROUTES FEATURE_BMI_PRO_ENABLED FEATURE_PREMIUM_WEEK_ENABLED VIP_MODULE_ENABLED".split()
_WS_EXTRA_PATHS = {"w": "/unexpected-ws", "h": "/unexpected-http"}
_WS_STATES = "c. .c ff cf fc d. .d h. .h rr rc cr r. .r C. .C DC CD RC CR RR CCw CCh".split()
_FASTAPI_CALLEES = {"FastAPI", "fastapi.FastAPI", "fastapi.applications.FastAPI"}


def _assert_atomic_bootstrap_failure(target: FastAPI, match: str | None = None) -> None:
    before = (tuple(target.routes), tuple(target.user_middleware))
    with pytest.raises(RuntimeError, match=match):
        main.ensure_canonical_app_bootstrap(target)
    assert (tuple(target.routes), tuple(target.user_middleware)) == before


def test_one_direct_constructor_belongs_to_the_canonical_owner() -> None:
    sources = [Path("legacy_app.py"), *sorted(Path("app").rglob("*.py"))]
    trees = {path: ast.parse(path.read_bytes(), filename=str(path)) for path in sources}
    calls = [
        path
        for path, tree in trees.items()
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and ast.unparse(node.func) in _FASTAPI_CALLEES
    ]
    assert calls == [Path("app/bootstrap/application.py")]
    assert not any(
        isinstance(node, ast.ImportFrom)
        and node.module == "legacy_app"
        and any(alias.name == "app" for alias in node.names)
        for node in ast.walk(trees[Path("app/main.py")])
    )


def test_runtime_identity_lifespan_and_private_constructor_isolation() -> None:
    assert application.app is main.app is legacy_app.app is app.app
    assert application.app.router.lifespan_context is application_lifespan
    metadata = application.APPLICATION_METADATA
    first, second = (application._create_fastapi_application(metadata) for _ in range(2))
    assert first is not second
    assert first.router.lifespan_context is second.router.lifespan_context is application_lifespan
    first.contact["name"] = first.license_info["name"] = "mutated"
    first.openapi_tags[0]["description"] = "mutated"
    assert second.contact["name"] == metadata.contact_name
    assert second.license_info["name"] == metadata.license_name
    assert second.openapi_tags[0]["description"] == metadata.tags[0].description


def test_fresh_import_orders_have_relative_runtime_parity() -> None:
    def run(imports: str) -> list[object]:
        scenario = textwrap.dedent(f"""
            import hashlib, json; {imports}
            from app.bootstrap.http_stack import _owned_middleware_projection; from app.bootstrap.lifespan import application_lifespan; from app.effective_routes import iter_effective_route_candidates, route_endpoint, route_include_in_schema, route_methods, route_path
            def routes(target): return [[route_path(route), sorted(route_methods(route)) or ["WEBSOCKET"], f"{{route_endpoint(route).__module__}}.{{route_endpoint(route).__qualname__}}", route_include_in_schema(route)] for route in iter_effective_route_candidates(target.routes)]
            def snapshot(): schema = json.dumps(canonical.app.openapi(), sort_keys=True, separators=(",", ":")); return [routes(canonical.app), list(_owned_middleware_projection(canonical.app)), hashlib.sha256(schema.encode()).hexdigest()]
            before = snapshot(); assert canonical.app is main.app is legacy_app.app is package.app; assert "app_module" not in __import__("sys").modules; assert not hasattr(legacy_app, "start_background_updates"); assert not hasattr(legacy_app, "stop_background_updates"); assert canonical.app.router.lifespan_context is application_lifespan; assert all(not hasattr(module, name) for module in (package, main, legacy_app) for name in {_RETIRED_REGISTRATION_MIRRORS!r}); assert main.ensure_canonical_app_bootstrap(canonical.app) is canonical.app; assert snapshot() == before; print("OWNERSHIP_RESULT=" + json.dumps(before, sort_keys=True))
        """)
        env = os.environ | {"APP_ENV": "test", "ENVIRONMENT": "test", "TESTING": "true"}
        for name in _OPTIONAL_ENV:
            env.pop(name, None)
        options = {"capture_output": True, "text": True, "env": env}
        completed = subprocess.run([sys.executable, "-c", scenario], **options)
        assert completed.returncode == 0, completed.stdout + completed.stderr
        return json.loads(completed.stdout.rsplit("OWNERSHIP_RESULT=", 1)[-1])

    results = [run(imports) for imports in _IMPORT_SCENARIOS]
    assert results[1:] == results[:1] * (len(results) - 1)


def test_fresh_package_facade_and_canonical_main_do_not_load_legacy_app() -> None:
    scenario = textwrap.dedent("""
        import importlib
        import sys

        import app

        assert "legacy_app" not in sys.modules
        assert "app.main" not in sys.modules
        assert "app_module" not in sys.modules
        dir(app)
        try:
            app.not_a_supported_export
        except AttributeError:
            pass
        else:
            raise AssertionError("unknown facade export did not fail closed")
        assert "legacy_app" not in sys.modules
        assert "app.main" not in sys.modules
        assert "app_module" not in sys.modules

        for module_name in ("app_module", "app.scheduler_helpers"):
            try:
                importlib.import_module(module_name)
            except ModuleNotFoundError as exc:
                assert exc.name == module_name
            else:
                raise AssertionError(f"retired module still importable: {module_name}")

        canonical = app.app
        assert "app.main" in sys.modules
        assert "legacy_app" not in sys.modules
        import app.main as main
        assert "legacy_app" not in sys.modules
        import legacy_app

        assert canonical is main.app is legacy_app.app
        assert "app_module" not in sys.modules
        for name in (
            "start_background_updates",
            "stop_background_updates",
            "_scheduler_start_background_updates",
            "_scheduler_stop_background_updates",
        ):
            assert not hasattr(legacy_app, name), name

        retired = (
            "VIP_MODULE_ENABLED",
            "vip_router",
            "pro_router",
            "premium_week_router",
            "FEATURE_BMI_PRO_ENABLED",
            "bmi_router",
            "bmi_pro_router",
            "bmi_pro_legacy_alias_router",
        )
        assert all(
            not hasattr(module, name)
            for module in (app, main, legacy_app)
            for name in retired
        )
        """)
    env = os.environ | {"APP_ENV": "test", "ENVIRONMENT": "test", "TESTING": "true"}
    completed = subprocess.run(
        [sys.executable, "-c", scenario],
        capture_output=True,
        text=True,
        env=env,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_fresh_direct_main_import_does_not_load_legacy_app() -> None:
    scenario = textwrap.dedent("""
        import sys
        import app.main as main

        assert main.app is not None
        assert "legacy_app" not in sys.modules
        """)
    env = os.environ | {"APP_ENV": "test", "ENVIRONMENT": "test", "TESTING": "true"}
    completed = subprocess.run(
        [sys.executable, "-c", scenario],
        capture_output=True,
        text=True,
        env=env,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


@pytest.mark.parametrize(("path", "method"), _HTTP_CONTRACTS)
@pytest.mark.parametrize("owners", ("f", "cc", "ff", "cf", "fc", "r", "i"))
def test_bespoke_http_owner_states_fail_closed(path: str, method: str, owners: str) -> None:
    target, fn = FastAPI(), route_endpoint_for_path_method(main.app.routes, path, method)
    for owner in owners:
        if owner == "i":
            target.include_router(APIRouter(routes=[Route(path, fn, methods=[method])]))
        elif owner == "r":
            target.routes.append(Route(path, fn, methods=[method]))
        else:
            endpoint = fn if owner == "c" else (lambda: None)
            target.add_api_route(path, endpoint, methods=[method])
    expected_error = (
        "Invalid existing FitChef support handoff route"
        if path == main._FITCHEF_SUPPORT_HANDOFF_ROUTE_PATH
        else "Duplicate"
    )
    _assert_atomic_bootstrap_failure(target, expected_error)


@pytest.mark.parametrize(
    "override",
    (
        {"include_in_schema": True},
        {"status_code": 201},
        {"response_model": dict[str, object]},
        {"dependencies": [Depends(lambda: None)]},
    ),
)
def test_direct_root_metadata_drift_fails_before_mutation(override: dict[str, object]) -> None:
    target = FastAPI()
    metadata = {"include_in_schema": False, "response_model": main.DirectApiRootProbe, **override}
    target.add_api_route("/", main.serve_direct_api_root_probe, methods=["GET"], **metadata)
    _assert_atomic_bootstrap_failure(target, "metadata drift")


@pytest.mark.parametrize("source", _HTTP_SOURCES)
@pytest.mark.parametrize("state", ("extra", "raw"))
def test_source_guard(source: str, state: str, monkeypatch: pytest.MonkeyPatch) -> None:
    path_name, router_name = source.split(":")
    path, current = getattr(main, path_name), getattr(main, router_name)
    endpoint = route_endpoint_for_path_method(current.routes, path, "POST")
    selected = APIRouter(routes=[Route(path, endpoint, methods=["POST"])] if state == "raw" else [])
    if state == "extra":
        selected.add_api_route(path, endpoint, methods=["POST"])
        selected.add_api_route("/unexpected-source", lambda: None, methods=["GET"])
    monkeypatch.setattr(main, router_name, selected)
    _assert_atomic_bootstrap_failure(FastAPI(), "Invalid canonical HTTP source route")


@pytest.mark.parametrize(
    "state",
    (
        "zero",
        "extra",
        "wrong_path",
        "wrong_method",
        "wrong_visibility",
        "wrong_endpoint",
        "wrong_model",
        "missing_status",
        "extra_status",
        "wrong_primary_status",
        "altered_response_description",
        "altered_response_model",
        "wrong_response_model_include",
        "wrong_response_model_exclude",
        "wrong_by_alias",
        "wrong_exclude_unset",
        "wrong_exclude_defaults",
        "wrong_exclude_none",
        "wrong_summary",
        "wrong_description",
        "wrong_dependency",
        "extra_dependency",
        "combined_methods",
        "missing_openapi_extra",
        "wrong_openapi_extra",
        "extra_openapi_extra",
        "extra_nested_request_body",
    ),
)
def test_fitchef_support_handoff_source_fails_before_bootstrap_mutation(
    state: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Every malformed dedicated source is rejected before target mutation."""

    router = APIRouter()
    if state != "zero":
        path = (
            "/api/v1/pro/fitchef/not-recommend"
            if state == "wrong_path"
            else main._FITCHEF_SUPPORT_HANDOFF_ROUTE_PATH
        )
        methods = (
            ["POST", "DELETE"]
            if state == "combined_methods"
            else ["GET" if state == "wrong_method" else "POST"]
        )
        endpoint = (lambda: None) if state == "wrong_endpoint" else main.fitchef_support_handoff
        response_model = (
            dict[str, object] if state == "wrong_model" else main.FitChefSupportHandoffResponse
        )
        responses = deepcopy(main._FITCHEF_SUPPORT_HANDOFF_RESPONSES)
        if state == "missing_status":
            responses.pop(503)
        if state == "extra_status":
            responses[418] = {"description": "Unexpected response"}
        if state == "altered_response_description":
            responses[503]["description"] = "Altered feature-disabled response"
        if state == "altered_response_model":
            responses[503]["model"] = main.FitChefSupportHandoffResponse
        dependencies = [
            Depends((lambda: None) if state == "wrong_dependency" else main.require_pro_tier)
        ]
        if state == "extra_dependency":
            dependencies.append(Depends(lambda: None))
        openapi_extra = deepcopy(main._FITCHEF_SUPPORT_HANDOFF_OPENAPI_EXTRA)
        if state == "wrong_openapi_extra":
            openapi_extra["requestBody"] = {"required": False}
        if state == "extra_openapi_extra":
            openapi_extra["unexpected"] = True
        if state == "extra_nested_request_body":
            request_body = openapi_extra["requestBody"]
            assert isinstance(request_body, dict)
            request_body["unexpected"] = True
        router.add_api_route(
            path,
            endpoint,
            methods=methods,
            include_in_schema=state != "wrong_visibility",
            response_model=response_model,
            status_code=201 if state == "wrong_primary_status" else None,
            response_model_include=(
                {"support_need", "action"} if state == "wrong_response_model_include" else None
            ),
            response_model_exclude=(
                {"execution_authority"} if state == "wrong_response_model_exclude" else None
            ),
            response_model_by_alias=state != "wrong_by_alias",
            response_model_exclude_unset=state == "wrong_exclude_unset",
            response_model_exclude_defaults=state == "wrong_exclude_defaults",
            response_model_exclude_none=state == "wrong_exclude_none",
            summary=(
                "Substituted FitChef support summary"
                if state == "wrong_summary"
                else main._FITCHEF_SUPPORT_HANDOFF_SUMMARY
            ),
            description=(
                "Substituted FitChef support description"
                if state == "wrong_description"
                else main._FITCHEF_SUPPORT_HANDOFF_DESCRIPTION
            ),
            responses=responses,
            dependencies=dependencies,
            openapi_extra=None if state == "missing_openapi_extra" else openapi_extra,
        )
        if state == "extra":
            router.add_api_route("/unexpected-support-source", lambda: None, methods=["GET"])

    monkeypatch.setattr(main, "fitchef_support_handoff_router", router)
    _assert_atomic_bootstrap_failure(FastAPI(), "Invalid FitChef support handoff source route")


@pytest.mark.parametrize(
    "state",
    (
        "foreign",
        "duplicate",
        "wrong_method",
        "wrong_visibility",
        "wrong_model",
        "missing_status",
        "extra_status",
        "wrong_primary_status",
        "altered_response_description",
        "altered_response_model",
        "wrong_response_model_include",
        "wrong_response_model_exclude",
        "wrong_by_alias",
        "wrong_exclude_unset",
        "wrong_exclude_defaults",
        "wrong_exclude_none",
        "wrong_summary",
        "wrong_description",
        "wrong_dependency",
        "extra_dependency",
        "combined_methods",
        "missing_openapi_extra",
        "wrong_openapi_extra",
        "extra_openapi_extra",
        "extra_nested_request_body",
    ),
)
def test_fitchef_support_handoff_existing_target_fails_unchanged(
    state: str,
) -> None:
    """Foreign, duplicate, and metadata-drift live owners fail before mutation."""

    target = FastAPI()
    responses = deepcopy(main._FITCHEF_SUPPORT_HANDOFF_RESPONSES)
    if state == "missing_status":
        responses.pop(503)
    if state == "extra_status":
        responses[418] = {"description": "Unexpected response"}
    if state == "altered_response_description":
        responses[503]["description"] = "Altered feature-disabled response"
    if state == "altered_response_model":
        responses[503]["model"] = main.FitChefSupportHandoffResponse
    endpoint = (lambda: None) if state == "foreign" else main.fitchef_support_handoff
    methods = (
        ["POST", "DELETE"]
        if state == "combined_methods"
        else ["GET" if state == "wrong_method" else "POST"]
    )
    response_model = (
        dict[str, object] if state == "wrong_model" else main.FitChefSupportHandoffResponse
    )
    dependencies = [
        Depends((lambda: None) if state == "wrong_dependency" else main.require_pro_tier)
    ]
    if state == "extra_dependency":
        dependencies.append(Depends(lambda: None))
    openapi_extra = deepcopy(main._FITCHEF_SUPPORT_HANDOFF_OPENAPI_EXTRA)
    if state == "wrong_openapi_extra":
        openapi_extra["requestBody"] = {"required": False}
    if state == "extra_openapi_extra":
        openapi_extra["unexpected"] = True
    if state == "extra_nested_request_body":
        request_body = openapi_extra["requestBody"]
        assert isinstance(request_body, dict)
        request_body["unexpected"] = True
    target.add_api_route(
        main._FITCHEF_SUPPORT_HANDOFF_ROUTE_PATH,
        endpoint,
        methods=methods,
        include_in_schema=state != "wrong_visibility",
        response_model=response_model,
        status_code=201 if state == "wrong_primary_status" else None,
        response_model_include=(
            {"support_need", "action"} if state == "wrong_response_model_include" else None
        ),
        response_model_exclude=(
            {"execution_authority"} if state == "wrong_response_model_exclude" else None
        ),
        response_model_by_alias=state != "wrong_by_alias",
        response_model_exclude_unset=state == "wrong_exclude_unset",
        response_model_exclude_defaults=state == "wrong_exclude_defaults",
        response_model_exclude_none=state == "wrong_exclude_none",
        summary=(
            "Substituted FitChef support summary"
            if state == "wrong_summary"
            else main._FITCHEF_SUPPORT_HANDOFF_SUMMARY
        ),
        description=(
            "Substituted FitChef support description"
            if state == "wrong_description"
            else main._FITCHEF_SUPPORT_HANDOFF_DESCRIPTION
        ),
        responses=responses,
        dependencies=dependencies,
        openapi_extra=None if state == "missing_openapi_extra" else openapi_extra,
    )
    if state == "duplicate":
        target.include_router(main.fitchef_support_handoff_router)

    _assert_atomic_bootstrap_failure(target, "Invalid existing FitChef support handoff route")


def test_fitchef_support_handoff_private_registration_is_exact_and_idempotent() -> None:
    """Absent registration includes once; the exact live target is a no-op."""

    target = FastAPI()
    main._include_fitchef_support_handoff_router_if_needed(target)
    first_routes = tuple(target.routes)
    main._include_fitchef_support_handoff_router_if_needed(target)

    matching = [
        route
        for route in main._effective_app_routes(target)
        if main.route_path(route) == main._FITCHEF_SUPPORT_HANDOFF_ROUTE_PATH
    ]
    assert tuple(target.routes) == first_routes
    assert len(matching) == 1
    assert main._is_exact_fitchef_support_handoff_route(matching[0]) is True


@pytest.mark.parametrize("s", _WS_STATES)
def test_websocket_owner_states_fail_closed(s: str, monkeypatch: pytest.MonkeyPatch) -> None:
    target, canonical = FastAPI(), (main.realtime_ws.ws_pro, main.realtime_ws.ws_root)
    owner_app = APIRouter() if s != s.lower() else target
    for index, owner in enumerate(s.lower()):
        owners = "cc" if owner == "d" else owner.strip(".")
        for owner in owners:
            path = main._WS_ROUTE_PATHS[index] if index < 2 else _WS_EXTRA_PATHS[owner]
            if owner == "r":
                owner_app.routes.append(Route(path, canonical[index], methods=["GET"]))
            elif owner == "h":
                owner_app.add_api_route(path, lambda: None, methods=["GET"])
            else:
                endpoint = canonical[index] if owner == "c" else lambda _: None
                owner_app.add_api_websocket_route(path, endpoint)
    if owner_app is not target:
        monkeypatch.setattr(main.realtime_ws, "router", owner_app)
    _assert_atomic_bootstrap_failure(target)


def test_test_owned_app_does_not_rebind_canonical(monkeypatch: pytest.MonkeyPatch) -> None:
    test_owned = application._create_fastapi_application(application.APPLICATION_METADATA)
    monkeypatch.setattr(main.realtime_ws, "router", APIRouter())
    assert main.ensure_canonical_app_bootstrap(test_owned) is test_owned
    composed = (tuple(test_owned.routes), tuple(test_owned.user_middleware))
    assert main.ensure_canonical_app_bootstrap(test_owned) is test_owned
    assert (tuple(test_owned.routes), tuple(test_owned.user_middleware)) == composed
    monkeypatch.setattr(legacy_app, "app", test_owned)
    assert app.app is application.app is main.app
    assert legacy_app.app is test_owned
