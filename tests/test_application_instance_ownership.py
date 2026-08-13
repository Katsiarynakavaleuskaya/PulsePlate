"""Regression contract for canonical FastAPI construction and identity ownership."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import textwrap
from typing import Any

from fastapi.testclient import TestClient
import pytest

EXPECTED_OPENAPI_DIGEST = (
    "478873f1cc82292211c1191013f6d96250dc3d46a617bac8151fee65fdff3f1a"  # pragma: allowlist secret
)
EXPECTED_ROUTE_PROJECTION_COUNT = 133
EXPECTED_ROUTE_PROJECTION_DIGEST = (
    "e22e521ffec1e455c15a4cff4759b258b704b0b6af77c4a2f52e3558124ce493"  # pragma: allowlist secret
)
EXPECTED_MIDDLEWARE_ORDER = [
    "BaseHTTPMiddleware",
    "BaseHTTPMiddleware",
    "BaseHTTPMiddleware",
    "CSPNonceMiddleware",
    "SlowAPIMiddleware",
]

SUPPORTED_IMPORT_MATRIX = (
    (
        "canonical-first",
        "from app.bootstrap import application as canonical; import app.main as main; "
        "import legacy_app; import app as package",
    ),
    (
        "main-first",
        "import app.main as main; from app.bootstrap import application as canonical; "
        "import legacy_app; import app as package",
    ),
    (
        "legacy-first",
        "import legacy_app; from app.bootstrap import application as canonical; "
        "import app.main as main; import app as package",
    ),
    (
        "package-facade-first",
        "import app as package; package_app = package.app; "
        "from app.bootstrap import application as canonical; import app.main as main; "
        "import legacy_app",
    ),
)


def _run_import_scenario(imports: str) -> dict[str, Any]:
    scenario = textwrap.dedent(f"""
        import hashlib
        import json
        import sys
        from fastapi import FastAPI
        from app.effective_routes import (
            iter_effective_route_candidates,
            route_endpoint,
            route_include_in_schema,
            route_methods,
            route_path,
        )

        {imports}
        package_app = package.app
        assert canonical.app is main.app is package_app is legacy_app.app
        assert sys.modules["app_module"] is legacy_app

        def route_projection(target_app):
            projection = []
            for route in iter_effective_route_candidates(target_app.routes):
                original_route = getattr(route, "original_route", route)
                endpoint = route_endpoint(route)
                endpoint_module = getattr(endpoint, "__module__", None)
                endpoint_qualname = getattr(endpoint, "__qualname__", None)
                endpoint_identity = (
                    f"{{endpoint_module}}.{{endpoint_qualname}}"
                    if endpoint_module is not None and endpoint_qualname is not None
                    else None
                )
                projection.append(
                    {{
                        "kind": f"{{type(route).__module__}}.{{type(route).__qualname__}}",
                        "path": route_path(route),
                        "path_format": getattr(
                            route,
                            "path_format",
                            getattr(original_route, "path_format", None),
                        ),
                        "methods_or_websocket": sorted(route_methods(route))
                        or ["WEBSOCKET"],
                        "endpoint": endpoint_identity,
                        "name": getattr(route, "name", None),
                        "include_in_schema": route_include_in_schema(route),
                    }}
                )
            return projection

        projection_before_repeat = route_projection(canonical.app)
        assert main.ensure_canonical_app_bootstrap(canonical.app) is canonical.app
        assert canonical.app is main.app is package.app
        projection = route_projection(canonical.app)
        assert projection == projection_before_repeat
        projection_payload = json.dumps(
            projection, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        openapi_payload = json.dumps(
            canonical.app.openapi(), sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        middleware = [item.cls.__name__ for item in canonical.app.user_middleware]

        replacement = FastAPI()
        legacy_app.app = replacement
        assert canonical.app is main.app is package.app
        assert canonical.app is not replacement

        print("OWNERSHIP_RESULT=" + json.dumps({{
            "projection": projection,
            "projection_digest": hashlib.sha256(projection_payload).hexdigest(),
            "openapi_digest": hashlib.sha256(openapi_payload).hexdigest(),
            "middleware": middleware,
        }}, sort_keys=True))
        """)
    env = os.environ.copy()
    env.update(
        {
            "APP_ENV": "test",
            "ENV": "test",
            "ENVIRONMENT": "test",
            "RATE_LIMITING_IN_TESTS": "true",
            "TESTING": "true",
        }
    )
    for inherited_name in (
        "BUSINESS_MODULE_ENABLED",
        "ENABLE_TEST_ROUTES",
        "FEATURE_BMI_PRO_ENABLED",
        "VIP_MODULE_ENABLED",
    ):
        env.pop(inherited_name, None)
    result = subprocess.run(
        [sys.executable, "-c", scenario],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    result_line = next(
        line for line in result.stdout.splitlines() if line.startswith("OWNERSHIP_RESULT=")
    )
    payload: dict[str, Any] = json.loads(result_line.removeprefix("OWNERSHIP_RESULT="))
    return payload


def test_fastapi_constructor_has_one_bounded_production_owner() -> None:
    sources = {
        path: Path(path).read_text(encoding="utf-8")
        for path in (
            "app/bootstrap/application.py",
            "app/main.py",
            "legacy_app.py",
        )
    }

    assert sources["app/bootstrap/application.py"].count("FastAPI(") == 1
    assert sources["app/main.py"].count("FastAPI(") == 0
    assert sources["legacy_app.py"].count("FastAPI(") == 0


def test_private_constructor_returns_independent_apps_and_mutable_metadata() -> None:
    from app.bootstrap.application import APPLICATION_METADATA, _create_fastapi_application

    first_kwargs = APPLICATION_METADATA.to_fastapi_kwargs()
    second_kwargs = APPLICATION_METADATA.to_fastapi_kwargs()
    first_app = _create_fastapi_application(APPLICATION_METADATA)
    second_app = _create_fastapi_application(APPLICATION_METADATA)

    assert first_app is not second_app
    assert first_kwargs["contact"] is not second_kwargs["contact"]
    assert first_kwargs["license_info"] is not second_kwargs["license_info"]
    assert first_kwargs["openapi_tags"] is not second_kwargs["openapi_tags"]
    assert first_kwargs["openapi_tags"][0] is not second_kwargs["openapi_tags"][0]

    first_app.contact["name"] = "mutated"
    first_app.openapi_tags[0]["description"] = "mutated"
    assert second_app.contact["name"] == APPLICATION_METADATA.contact_name
    assert second_app.openapi_tags[0]["description"] == APPLICATION_METADATA.tags[0].description


def test_factory_uses_canonical_lifespan_observably(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.bootstrap.lifespan as lifespan_module
    import legacy_app
    from app.bootstrap.application import APPLICATION_METADATA, _create_fastapi_application
    from app.bootstrap.food_search import FoodSearchLifecycleLease
    from app.bootstrap.lifespan import LifespanHooks, application_lifespan
    from core.food_apis.scheduler_runtime import SchedulerMode

    events: list[str] = []

    async def _noop_start(update_interval_hours: int = 24) -> None:
        del update_interval_hours

    async def _noop_stop() -> None:
        return None

    hooks = LifespanHooks(
        run_startup_guards=lambda _app: events.append("guard"),
        initialize_database=lambda: events.append("database"),
        clear_database_fallback=lambda: events.append("database-clear"),
        attempt_database_fallback=lambda _env, _prod, _error: events.append("fallback"),
        validate_templates=lambda: events.append("templates"),
        configure_food_search=lambda _app: (
            events.append("food-acquire") or FoodSearchLifecycleLease()
        ),
        dispose_food_search=lambda _app, _lease: events.append("food-release"),
        start_background_updates=_noop_start,
        stop_background_updates=_noop_stop,
    )
    monkeypatch.setattr(lifespan_module, "build_default_lifespan_hooks", lambda: hooks)
    monkeypatch.setattr(
        lifespan_module,
        "resolve_scheduler_mode",
        lambda: SchedulerMode.DISABLED,
    )

    test_app = _create_fastapi_application(APPLICATION_METADATA)
    with TestClient(test_app):
        events.append("serving")

    assert legacy_app.lifespan is application_lifespan
    assert events == [
        "guard",
        "database",
        "database-clear",
        "templates",
        "food-acquire",
        "serving",
        "food-release",
    ]


def test_supported_fresh_process_import_matrix_preserves_runtime_truth() -> None:
    results = {label: _run_import_scenario(imports) for label, imports in SUPPORTED_IMPORT_MATRIX}

    assert list(results) == [
        "canonical-first",
        "main-first",
        "legacy-first",
        "package-facade-first",
    ]
    canonical_result = results["canonical-first"]
    assert len(canonical_result["projection"]) == EXPECTED_ROUTE_PROJECTION_COUNT
    assert canonical_result["projection_digest"] == EXPECTED_ROUTE_PROJECTION_DIGEST
    assert canonical_result["openapi_digest"] == EXPECTED_OPENAPI_DIGEST
    assert canonical_result["middleware"] == EXPECTED_MIDDLEWARE_ORDER
    for result in results.values():
        assert len(result["projection"]) == EXPECTED_ROUTE_PROJECTION_COUNT
        assert result["projection"] == canonical_result["projection"]
        assert result["projection_digest"] == EXPECTED_ROUTE_PROJECTION_DIGEST
        assert result["openapi_digest"] == EXPECTED_OPENAPI_DIGEST
        assert result["middleware"] == EXPECTED_MIDDLEWARE_ORDER
