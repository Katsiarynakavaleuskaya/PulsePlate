import ast
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
import textwrap
from typing import cast

import pytest
from fastapi import APIRouter, Depends, FastAPI
from fastapi.responses import PlainTextResponse
from fastapi.routing import APIRoute
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


REPO_ROOT = Path(__file__).resolve().parents[1]
_OWNERSHIP_SCENARIO_LABELS = ("package-first", "main-first", "legacy-first")
_OWNERSHIP_RECORD_MAX_BYTES = 1024 * 1024
_OWNERSHIP_MAX_ROUTES = 4096
_OWNERSHIP_MAX_MIDDLEWARE = 64
_OWNERSHIP_MAX_STRING = 4096
_OWNERSHIP_MAX_METHODS = 32
_OWNERSHIP_NETWORK_DENIAL = textwrap.dedent("""
    import socket

    def _deny_network(*_args, **_kwargs):
        raise AssertionError("ownership probe network denied")

    class _DeniedSocket(socket.socket):
        def connect(self, *_args, **_kwargs):
            _deny_network()

        def connect_ex(self, *_args, **_kwargs):
            _deny_network()

    socket.create_connection = _deny_network
    socket.socket = _DeniedSocket
    try:
        socket.create_connection(("127.0.0.1", 9), timeout=1)
    except AssertionError:
        pass
    else:
        raise AssertionError("ownership probe connection denial missing")
    with socket.socket() as transport:
        for connect in (transport.connect, transport.connect_ex):
            try:
                connect(("127.0.0.1", 9))
            except AssertionError:
                pass
            else:
                raise AssertionError("ownership probe socket denial missing")
    """)


def _run_ownership_parity_probe(index: int) -> list[object]:
    """Observe one existing fixed import program without ambient payload diagnostics."""
    imports = _IMPORT_SCENARIOS[index]
    label = _OWNERSHIP_SCENARIO_LABELS[index]
    scenario = textwrap.dedent(f"""
        import hashlib, json; {imports}
        from app.bootstrap.http_stack import _owned_middleware_projection; from app.bootstrap.lifespan import application_lifespan; from app.effective_routes import iter_effective_route_candidates, route_endpoint, route_include_in_schema, route_methods, route_path
        def routes(target): return [[route_path(route), sorted(route_methods(route)) or ["WEBSOCKET"], f"{{route_endpoint(route).__module__}}.{{route_endpoint(route).__qualname__}}", route_include_in_schema(route)] for route in iter_effective_route_candidates(target.routes)]
        def snapshot(): schema = json.dumps(canonical.app.openapi(), sort_keys=True, separators=(",", ":")); return [routes(canonical.app), list(_owned_middleware_projection(canonical.app)), hashlib.sha256(schema.encode()).hexdigest()]
        before = snapshot(); assert canonical.app is main.app is legacy_app.app is package.app; assert "app_module" not in __import__("sys").modules; assert not hasattr(legacy_app, "start_background_updates"); assert not hasattr(legacy_app, "stop_background_updates"); assert canonical.app.router.lifespan_context is application_lifespan; assert all(not hasattr(module, name) for module in (package, main, legacy_app) for name in {_RETIRED_REGISTRATION_MIRRORS!r}); assert main.ensure_canonical_app_bootstrap(canonical.app) is canonical.app; assert snapshot() == before; print("OWNERSHIP_RESULT=" + json.dumps(before, sort_keys=True))
    """)
    passthrough = ("LANG", "LC_ALL", "PATH", "PYTHONIOENCODING", "PYTHONUTF8", "TMPDIR")
    env = {name: value for name in passthrough if (value := os.environ.get(name)) is not None}
    env.update(
        {
            "APP_ENV": "test",
            "ENVIRONMENT": "test",
            "TESTING": "true",
            "PYTEST_CURRENT_TEST": "ownership-parity-probe",
            "PRIVATE_EXPORTS_ENABLED": "false",
        }
    )
    try:
        completed = subprocess.run(
            [sys.executable, "-c", _OWNERSHIP_NETWORK_DENIAL + scenario],
            capture_output=True,
            text=True,
            env=env,
            cwd=REPO_ROOT,
            timeout=30,
            shell=False,
            check=False,
        )
    except subprocess.TimeoutExpired:
        raise AssertionError(f"ownership probe {label}: timeout") from None
    except OSError:
        raise AssertionError(f"ownership probe {label}: process unavailable") from None
    except UnicodeError:
        raise AssertionError(f"ownership probe {label}: output decoding failed") from None
    if type(completed.returncode) is not int or type(completed.stdout) is not str:
        raise AssertionError(f"ownership probe {label}: process result invalid")
    if completed.returncode != 0:
        raise AssertionError(f"ownership probe {label}: exit={completed.returncode}")
    result_lines = [
        line for line in completed.stdout.splitlines() if line.startswith("OWNERSHIP_RESULT=")
    ]
    if len(result_lines) != 1:
        raise AssertionError(f"ownership probe {label}: result marker invalid")
    try:
        record_bytes = result_lines[0].encode("utf-8")
    except UnicodeError:
        raise AssertionError(f"ownership probe {label}: result encoding invalid") from None
    if len(record_bytes) > _OWNERSHIP_RECORD_MAX_BYTES:
        raise AssertionError(f"ownership probe {label}: result exceeds budget")
    try:
        decoded: object = json.loads(result_lines[0].removeprefix("OWNERSHIP_RESULT="))
    except (ValueError, RecursionError):
        raise AssertionError(f"ownership probe {label}: result JSON invalid") from None
    if type(decoded) is not list or len(decoded) != 3:
        raise AssertionError(f"ownership probe {label}: result shape invalid")
    rows, middleware, digest = decoded
    if (
        type(rows) is not list
        or len(rows) > _OWNERSHIP_MAX_ROUTES
        or type(middleware) is not list
        or len(middleware) > _OWNERSHIP_MAX_MIDDLEWARE
        or type(digest) is not str
        or len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
    ):
        raise AssertionError(f"ownership probe {label}: result shape invalid")
    for row in rows:
        if type(row) is not list or len(row) != 4:
            raise AssertionError(f"ownership probe {label}: route shape invalid")
        path, methods, endpoint, included = row
        if (
            type(path) is not str
            or len(path) > _OWNERSHIP_MAX_STRING
            or type(endpoint) is not str
            or len(endpoint) > _OWNERSHIP_MAX_STRING
            or type(methods) is not list
            or len(methods) > _OWNERSHIP_MAX_METHODS
            or any(
                type(method) is not str or len(method) > _OWNERSHIP_MAX_STRING for method in methods
            )
            or type(included) is not bool
        ):
            raise AssertionError(f"ownership probe {label}: route shape invalid")
    if any(type(label) is not str or len(label) > _OWNERSHIP_MAX_STRING for label in middleware):
        raise AssertionError(f"ownership probe {label}: middleware shape invalid")
    return cast(list[object], decoded)


def _assert_ownership_parity(records: list[list[object]]) -> None:
    """Preserve complete relative equality without rendering admitted child strings."""
    if len(records) != len(_IMPORT_SCENARIOS):
        raise AssertionError("ownership probe: scenario observations incomplete")
    if any(record != records[0] for record in records[1:]):
        raise AssertionError("ownership probe: relative parity mismatch")


def test_fresh_import_orders_have_relative_runtime_parity() -> None:
    results = [_run_ownership_parity_probe(index) for index in range(len(_IMPORT_SCENARIOS))]
    _assert_ownership_parity(results)


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
        "wrong_response_class",
        "wrong_name",
        "wrong_operation_id",
        "wrong_generate_unique_id_function",
        "wrong_unique_id",
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

    def wrong_generate_unique_id(_: APIRoute) -> str:
        return main._FITCHEF_SUPPORT_HANDOFF_UNIQUE_ID

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
            response_class=(
                PlainTextResponse if state == "wrong_response_class" else main.JSONResponse
            ),
            name=(
                "wrong_fitchef_support_handoff"
                if state == "wrong_name"
                else main._FITCHEF_SUPPORT_HANDOFF_ROUTE_NAME
            ),
            operation_id=(
                "wrong_fitchef_support_handoff_operation" if state == "wrong_operation_id" else None
            ),
            generate_unique_id_function=(
                wrong_generate_unique_id
                if state == "wrong_generate_unique_id_function"
                else main.generate_unique_id
            ),
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
        if state in {"wrong_name", "wrong_operation_id"}:
            source_route = router.routes[-1]
            assert isinstance(source_route, APIRoute)
            source_route.unique_id = main._FITCHEF_SUPPORT_HANDOFF_UNIQUE_ID
        if state == "wrong_unique_id":
            source_route = router.routes[-1]
            assert isinstance(source_route, APIRoute)
            source_route.unique_id = "wrong_fitchef_support_handoff_stored_id"
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
        "wrong_response_class",
        "wrong_name",
        "wrong_operation_id",
        "wrong_generate_unique_id_function",
        "wrong_unique_id",
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

    def wrong_generate_unique_id(_: APIRoute) -> str:
        return main._FITCHEF_SUPPORT_HANDOFF_UNIQUE_ID

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
        response_class=(
            PlainTextResponse if state == "wrong_response_class" else main.JSONResponse
        ),
        name=(
            "wrong_fitchef_support_handoff"
            if state == "wrong_name"
            else main._FITCHEF_SUPPORT_HANDOFF_ROUTE_NAME
        ),
        operation_id=(
            "wrong_fitchef_support_handoff_operation" if state == "wrong_operation_id" else None
        ),
        generate_unique_id_function=(
            wrong_generate_unique_id
            if state == "wrong_generate_unique_id_function"
            else main.generate_unique_id
        ),
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
    if state in {"wrong_name", "wrong_operation_id"}:
        live_route = target.routes[-1]
        assert isinstance(live_route, APIRoute)
        live_route.unique_id = main._FITCHEF_SUPPORT_HANDOFF_UNIQUE_ID
    if state == "wrong_unique_id":
        live_route = target.routes[-1]
        assert isinstance(live_route, APIRoute)
        live_route.unique_id = "wrong_fitchef_support_handoff_stored_id"
    if state == "duplicate":
        target.include_router(main.fitchef_support_handoff_router)

    _assert_atomic_bootstrap_failure(target, "Invalid existing FitChef support handoff route")


def test_fitchef_support_handoff_effective_include_dependency_fails_unchanged() -> None:
    """An include-level dependency is effective drift and blocks registration."""

    def extra_guard() -> None:
        return None

    target = FastAPI()
    target.include_router(
        main.fitchef_support_handoff_router,
        dependencies=[Depends(extra_guard)],
    )
    matching = [
        route
        for route in main._effective_app_routes(target)
        if main.route_path(route) == main._FITCHEF_SUPPORT_HANDOFF_ROUTE_PATH
    ]
    assert len(matching) == 1
    route = cast(APIRoute, matching[0])
    assert [dependency.call for dependency in route.dependant.dependencies] == [
        extra_guard,
        main.require_pro_tier,
    ]

    _assert_atomic_bootstrap_failure(target, "Invalid existing FitChef support handoff route")


def test_fitchef_support_handoff_private_registration_is_exact_and_idempotent() -> None:
    """The canonical source/effective publication identity is exact and idempotent."""

    source_matching = [
        route
        for route in main.iter_effective_route_candidates(
            main.fitchef_support_handoff_router.routes
        )
        if main.route_path(route) == main._FITCHEF_SUPPORT_HANDOFF_ROUTE_PATH
    ]
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
    assert len(source_matching) == 1
    assert len(matching) == 1
    for candidate in (*source_matching, *matching):
        route = cast(APIRoute, candidate)
        response_class = route.response_class
        if isinstance(response_class, main.DefaultPlaceholder):
            response_class = response_class.value
        unique_id_generator = route.generate_unique_id_function
        if isinstance(unique_id_generator, main.DefaultPlaceholder):
            unique_id_generator = unique_id_generator.value
        assert response_class is main.JSONResponse
        assert route.name == main._FITCHEF_SUPPORT_HANDOFF_ROUTE_NAME
        assert route.operation_id is None
        assert unique_id_generator is main.generate_unique_id
        assert route.unique_id == main._FITCHEF_SUPPORT_HANDOFF_UNIQUE_ID
        assert [dependency.call for dependency in route.dependant.dependencies] == [
            main.require_pro_tier
        ]
        assert main._is_exact_fitchef_support_handoff_route(route) is True


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


def _ownership_observation_fixture() -> list[object]:
    """A shape-only fixture deliberately includes permitted empty observations."""
    return [[["", [], "", True]], [""], "0" * 64]


def test_ownership_probe_uses_fixed_process_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    record = _ownership_observation_fixture()
    seen: list[str] = []

    def run(
        argv: list[str],
        *,
        capture_output: bool,
        text: bool,
        env: dict[str, str],
        cwd: Path,
        timeout: int,
        shell: bool,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        assert argv[:2] == [sys.executable, "-c"]
        assert argv[2].startswith(_OWNERSHIP_NETWORK_DENIAL)
        seen.append(next(imports for imports in _IMPORT_SCENARIOS if imports in argv[2]))
        assert cwd == REPO_ROOT and timeout == 30
        assert capture_output is True and text is True and shell is False and check is False
        assert set(env) <= {
            "LANG",
            "LC_ALL",
            "PATH",
            "PYTHONIOENCODING",
            "PYTHONUTF8",
            "TMPDIR",
            "APP_ENV",
            "ENVIRONMENT",
            "TESTING",
            "PYTEST_CURRENT_TEST",
            "PRIVATE_EXPORTS_ENABLED",
        }
        assert {
            key: env[key]
            for key in (
                "APP_ENV",
                "ENVIRONMENT",
                "TESTING",
                "PYTEST_CURRENT_TEST",
                "PRIVATE_EXPORTS_ENABLED",
            )
        } == {
            "APP_ENV": "test",
            "ENVIRONMENT": "test",
            "TESTING": "true",
            "PYTEST_CURRENT_TEST": "ownership-parity-probe",
            "PRIVATE_EXPORTS_ENABLED": "false",
        }
        return subprocess.CompletedProcess(
            argv, 0, "noise\nOWNERSHIP_RESULT=" + json.dumps(record), ""
        )

    monkeypatch.setenv("PYTEST_CURRENT_TEST", "synthetic-ambient-marker")
    monkeypatch.setattr(subprocess, "run", run)
    results = [_run_ownership_parity_probe(index) for index in range(len(_IMPORT_SCENARIOS))]
    assert seen == _IMPORT_SCENARIOS
    assert results == [record] * len(_IMPORT_SCENARIOS)
    _assert_ownership_parity(results)


def test_ownership_probe_excludes_ambient_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    names = (
        "GH_TOKEN",
        "GITHUB_TOKEN",
        "OPENAI_API_KEY",
        "API_KEY",
        "PULSEPLATE_PYTHON_INDEX_URL",
        "FIGMA_ACCESS_TOKEN",
        "DATABASE_URL",
        "HOME",
        "PYTHONPATH",
        "PYTHONSTARTUP",
    )
    for name in names:
        monkeypatch.setenv(name, "synthetic-input-must-not-enter-child")
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "synthetic-ambient-marker")
    original_run = subprocess.run

    def run(
        argv: list[str],
        *,
        capture_output: bool,
        text: bool,
        env: dict[str, str],
        cwd: Path,
        timeout: int,
        shell: bool,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        assert argv[2].startswith(_OWNERSHIP_NETWORK_DENIAL)
        child_check = (
            "\nimport os\n"
            f"assert all(name not in os.environ for name in {names!r})\n"
            "assert os.environ['PYTEST_CURRENT_TEST'] == 'ownership-parity-probe'\n"
        )
        argv = [*argv]
        argv[2] = (
            _OWNERSHIP_NETWORK_DENIAL + child_check + argv[2][len(_OWNERSHIP_NETWORK_DENIAL) :]
        )
        return original_run(
            argv,
            capture_output=capture_output,
            text=text,
            env=env,
            cwd=cwd,
            timeout=timeout,
            shell=shell,
            check=check,
        )

    monkeypatch.setattr(subprocess, "run", run)
    _run_ownership_parity_probe(0)


@pytest.mark.parametrize(
    "failure",
    (
        "exit",
        "process",
        "timeout",
        "decode",
        "missing",
        "duplicate",
        "oversize",
        "json",
        "depth",
        "recursion",
        "encoding",
        "root",
        "arity",
        "rows",
        "middleware",
        "digest",
        "row_arity",
        "path",
        "methods",
        "method",
        "endpoint",
        "include",
        "label",
        "row_limit",
        "middleware_limit",
        "path_limit",
        "method_limit",
        "methods_limit",
        "endpoint_limit",
        "label_limit",
    ),
)
def test_ownership_probe_rejects_invalid_observation_without_payload(
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    sentinel = "synthetic-sensitive-observation"
    record = _ownership_observation_fixture()
    row = cast(list[list[object]], record[0])[0]
    payload: object = record
    if failure == "root":
        payload = {sentinel: sentinel}
    elif failure == "arity":
        record.append(sentinel)
    elif failure == "rows":
        record[0] = sentinel
    elif failure == "middleware":
        record[1] = sentinel
    elif failure == "digest":
        record[2] = sentinel
    elif failure == "row_arity":
        row.append(sentinel)
    elif failure == "path":
        row[0] = 1
    elif failure == "methods":
        row[1] = sentinel
    elif failure == "method":
        row[1] = [1]
    elif failure == "endpoint":
        row[2] = 1
    elif failure == "include":
        row[3] = 1
    elif failure == "label":
        record[1] = [1]
    elif failure == "row_limit":
        record[0] = [row] * (_OWNERSHIP_MAX_ROUTES + 1)
    elif failure == "middleware_limit":
        record[1] = [""] * (_OWNERSHIP_MAX_MIDDLEWARE + 1)
    elif failure == "path_limit":
        row[0] = sentinel * (_OWNERSHIP_MAX_STRING // len(sentinel) + 1)
    elif failure == "method_limit":
        row[1] = [sentinel * (_OWNERSHIP_MAX_STRING // len(sentinel) + 1)]
    elif failure == "methods_limit":
        row[1] = [""] * (_OWNERSHIP_MAX_METHODS + 1)
    elif failure == "endpoint_limit":
        row[2] = sentinel * (_OWNERSHIP_MAX_STRING // len(sentinel) + 1)
    elif failure == "label_limit":
        record[1] = [sentinel * (_OWNERSHIP_MAX_STRING // len(sentinel) + 1)]
    stdout = "OWNERSHIP_RESULT=" + json.dumps(payload)
    if failure == "missing":
        stdout = sentinel
    elif failure == "duplicate":
        stdout += "\n" + stdout
    elif failure == "oversize":
        stdout = "OWNERSHIP_RESULT=" + sentinel * (_OWNERSHIP_RECORD_MAX_BYTES // len(sentinel) + 1)
    elif failure == "json":
        stdout = "OWNERSHIP_RESULT=" + sentinel
    elif failure == "depth":
        depth = sys.getrecursionlimit() + 100
        stdout = "OWNERSHIP_RESULT=" + "[" * depth + "0" + "]" * depth
    elif failure == "encoding":
        stdout = "OWNERSHIP_RESULT=\ud800"

    def run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if failure == "process":
            raise OSError(sentinel)
        if failure == "timeout":
            raise subprocess.TimeoutExpired(sentinel, 30, output=sentinel, stderr=sentinel)
        if failure == "decode":
            raise UnicodeDecodeError("utf-8", sentinel.encode(), 0, 1, sentinel)
        return subprocess.CompletedProcess(
            sentinel, 1 if failure == "exit" else 0, stdout, sentinel
        )

    monkeypatch.setattr(subprocess, "run", run)
    if failure == "recursion":

        def decode(_payload: str) -> object:
            raise RecursionError(sentinel)

        monkeypatch.setattr(json, "loads", decode)
    with pytest.raises(AssertionError) as caught:
        _run_ownership_parity_probe(0)
    assert sentinel not in str(caught.value)
    assert str(caught.value).startswith("ownership probe package-first: ")
    if failure in {"process", "timeout", "decode", "json", "recursion", "encoding"}:
        assert caught.value.__suppress_context__ is True
    if failure == "depth":
        assert str(caught.value) in {
            "ownership probe package-first: result shape invalid",
            "ownership probe package-first: result JSON invalid",
        }


@pytest.mark.parametrize("boundary", ("empty", "rows", "middleware", "scalar", "methods", "record"))
def test_ownership_probe_admits_empty_and_bounded_full_records(
    monkeypatch: pytest.MonkeyPatch,
    boundary: str,
) -> None:
    record = _ownership_observation_fixture()
    row = cast(list[list[object]], record[0])[0]
    if boundary == "rows":
        record[0] = [row] * _OWNERSHIP_MAX_ROUTES
    elif boundary == "middleware":
        record[1] = [""] * _OWNERSHIP_MAX_MIDDLEWARE
    elif boundary == "scalar":
        row[0] = row[2] = "x" * _OWNERSHIP_MAX_STRING
        record[1] = ["x" * _OWNERSHIP_MAX_STRING]
    elif boundary == "methods":
        row[1] = [""] * _OWNERSHIP_MAX_METHODS
    stdout = "OWNERSHIP_RESULT=" + json.dumps(record)
    if boundary == "record":
        stdout += " " * (_OWNERSHIP_RECORD_MAX_BYTES - len(stdout.encode("utf-8")))
    completed = subprocess.CompletedProcess("synthetic", 0, stdout, "")

    def run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return completed

    monkeypatch.setattr(subprocess, "run", run)
    assert _run_ownership_parity_probe(0) == record


def test_ownership_parity_mismatch_diagnostics_are_constant() -> None:
    original = _ownership_observation_fixture()
    changed = deepcopy(original)
    cast(list[list[object]], changed[0])[0][0] = "synthetic-sensitive-valid-path"
    with pytest.raises(
        AssertionError, match="^ownership probe: relative parity mismatch$"
    ) as caught:
        _assert_ownership_parity([original, changed, original])
    assert "synthetic-sensitive-valid-path" not in str(caught.value)
    _assert_ownership_parity([original, deepcopy(original), deepcopy(original)])
    with pytest.raises(AssertionError, match="^ownership probe: scenario observations incomplete$"):
        _assert_ownership_parity([])
