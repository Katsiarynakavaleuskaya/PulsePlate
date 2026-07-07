from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

import scripts.ci.check_legacy_growth_guard as legacy_guard

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_current_legacy_app_passes_growth_guard() -> None:
    source = (REPO_ROOT / "legacy_app.py").read_text(encoding="utf-8")

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_seam_doc_passes_contract() -> None:
    text = (REPO_ROOT / "docs/architecture/LEGACY_COMPATIBILITY_SEAM.md").read_text(
        encoding="utf-8"
    )

    assert legacy_guard.validate_legacy_seam_doc(text) == []


def test_legacy_growth_guard_allows_shrinkage() -> None:
    source = "from fastapi import FastAPI\napp = FastAPI()\n"

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_rejects_new_route() -> None:
    source = textwrap.dedent("""
        from fastapi import FastAPI

        app = FastAPI()

        @app.post("/api/v1/new-runtime")
        async def new_runtime_route():
            return {"ok": True}
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "decorator:post:/api/v1/new-runtime -> new_runtime_route"
    ]


@pytest.mark.parametrize(
    ("path", "owner"),
    [
        ("/api/v1/premium/plate", "api_premium_plate"),
        ("/api/v1/premium/bmr", "api_premium_bmr"),
        ("/premium_bmr", "premium_bmr_legacy"),
        ("/api/v1/premium/targets", "api_who_targets"),
        ("/premium_targets", "premium_targets_legacy"),
        ("/api/v1/premium/gaps", "api_nutrient_gaps"),
        ("/api/v1/premium/plan/week", "api_weekly_menu"),
    ],
)
def test_legacy_growth_guard_rejects_reintroduced_premium_routes(
    path: str,
    owner: str,
) -> None:
    source = textwrap.dedent(f"""
        @app.post("{path}")
        async def {owner}():
            return {{"ok": True}}
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        f"legacy_app.py: unexpected legacy route growth: decorator:post:{path} -> {owner}"
    ]


def test_legacy_growth_guard_rejects_reintroduced_legal_routes() -> None:
    source = textwrap.dedent("""
        @app.get("/privacy")
        async def privacy():
            return {"privacy_policy": "legacy"}

        @app.get("/terms", include_in_schema=False)
        async def terms():
            return {"terms_of_use": "legacy"}
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: decorator:get:/privacy -> privacy",
        "legacy_app.py: unexpected legacy route growth: decorator:get:/terms -> terms",
    ]


def test_legacy_growth_guard_rejects_reintroduced_health_routes() -> None:
    source = textwrap.dedent("""
        @app.get("/health")
        async def health():
            return {"status": "legacy"}

        @app.get("/api/v1/health", include_in_schema=False)
        async def health_v1():
            return await health()

        @app.get("/health/db", include_in_schema=False)
        async def database_health():
            return {"status": "ok"}

        @app.get("/ready", include_in_schema=False)
        async def ready():
            return {"status": "ok"}
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "decorator:get:/api/v1/health -> health_v1",
        "legacy_app.py: unexpected legacy route growth: decorator:get:/health -> health",
        "legacy_app.py: unexpected legacy route growth: "
        "decorator:get:/health/db -> database_health",
        "legacy_app.py: unexpected legacy route growth: decorator:get:/ready -> ready",
    ]


def test_legacy_growth_guard_rejects_reintroduced_favicon_route() -> None:
    source = textwrap.dedent("""
        @app.get("/favicon.ico")
        async def favicon():
            return Response(status_code=204)
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: decorator:get:/favicon.ico -> favicon"
    ]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            textwrap.dedent("""
                @app.post("/bmi")
                async def bmi_endpoint():
                    return {"ok": True}
                """),
            "legacy_app.py: unexpected legacy route growth: decorator:post:/bmi -> bmi_endpoint",
        ),
        (
            textwrap.dedent("""
                @app.post("/plan")
                async def plan_endpoint():
                    return {"ok": True}
                """),
            "legacy_app.py: unexpected legacy route growth: decorator:post:/plan -> plan_endpoint",
        ),
        (
            textwrap.dedent("""
                @app.post("/api/v1/bmi")
                async def bmi_endpoint_v1():
                    return {"ok": True}
                """),
            (
                "legacy_app.py: unexpected legacy route growth: "
                "decorator:post:/api/v1/bmi -> bmi_endpoint_v1"
            ),
        ),
    ],
)
def test_legacy_growth_guard_rejects_reintroduced_bmi_plan_routes(
    source: str,
    expected: str,
) -> None:
    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [expected]


def test_legacy_growth_guard_rejects_reintroduced_bmi_router_registration() -> None:
    source = textwrap.dedent("""
        from app.routers.bmi import router as bmi_router
        from app.routers.bmi_pro import router as bmi_pro_router
        from app.routers.bmi_pro_legacy_alias import router as bmi_pro_legacy_alias_router

        app.include_router(bmi_router)
        app.include_router(bmi_pro_router)
        app.include_router(bmi_pro_legacy_alias_router)
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:include_router:bmi_pro_legacy_alias_router",
        "legacy_app.py: unexpected legacy route growth: "
        "registration:include_router:bmi_pro_router",
        "legacy_app.py: unexpected legacy route growth: registration:include_router:bmi_router",
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:app.routers.bmi:router -> bmi_router",
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:app.routers.bmi_pro:router -> bmi_pro_router",
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:app.routers.bmi_pro_legacy_alias:router -> "
        "bmi_pro_legacy_alias_router",
    ]


def test_legacy_growth_guard_rejects_reintroduced_export_alias_routes() -> None:
    source = textwrap.dedent("""
        @app.get("/api/v1/premium/exports/day/{plan_id}.csv")
        async def export_daily_plan_csv_route():
            return Response()

        @app.post("/api/v1/export/pdf")
        async def export_pdf_generic_route():
            return Response()

        @app.get("/api/v1/premium/exports/week/{plan_id}.csv")
        async def export_weekly_plan_csv_route():
            return Response()

        @app.get("/api/v1/premium/exports/day/{plan_id}.pdf")
        async def export_daily_plan_pdf_route():
            return Response()

        @app.get("/api/v1/premium/exports/week/{plan_id}.pdf")
        async def export_weekly_plan_pdf_route():
            return Response()
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "decorator:get:/api/v1/premium/exports/day/{plan_id}.csv -> "
        "export_daily_plan_csv_route",
        "legacy_app.py: unexpected legacy route growth: "
        "decorator:get:/api/v1/premium/exports/day/{plan_id}.pdf -> "
        "export_daily_plan_pdf_route",
        "legacy_app.py: unexpected legacy route growth: "
        "decorator:get:/api/v1/premium/exports/week/{plan_id}.csv -> "
        "export_weekly_plan_csv_route",
        "legacy_app.py: unexpected legacy route growth: "
        "decorator:get:/api/v1/premium/exports/week/{plan_id}.pdf -> "
        "export_weekly_plan_pdf_route",
        "legacy_app.py: unexpected legacy route growth: "
        "decorator:post:/api/v1/export/pdf -> export_pdf_generic_route",
    ]


def test_legacy_growth_guard_rejects_reintroduced_admin_debug_routes() -> None:
    source = textwrap.dedent("""
        @app.get("/debug_env")
        async def debug_env():
            return {"ok": True}

        @app.get("/api/v1/admin/status")
        async def admin_status():
            return {"ok": True}

        @app.post("/admin/logs/cleanup")
        async def cleanup_expired_logs():
            return {"ok": True}

        @app.get("/api/v1/admin/db-status")
        async def get_database_status():
            return {"ok": True}

        @app.post("/api/v1/admin/force-update")
        async def force_database_update():
            return {"ok": True}

        @app.get("/api/v1/admin/check-updates")
        async def check_for_updates():
            return {"ok": True}

        @app.post("/api/v1/admin/rollback")
        async def rollback_database():
            return {"ok": True}
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "decorator:get:/api/v1/admin/check-updates -> check_for_updates",
        "legacy_app.py: unexpected legacy route growth: "
        "decorator:get:/api/v1/admin/db-status -> get_database_status",
        "legacy_app.py: unexpected legacy route growth: "
        "decorator:get:/api/v1/admin/status -> admin_status",
        "legacy_app.py: unexpected legacy route growth: decorator:get:/debug_env -> debug_env",
        "legacy_app.py: unexpected legacy route growth: "
        "decorator:post:/admin/logs/cleanup -> cleanup_expired_logs",
        "legacy_app.py: unexpected legacy route growth: "
        "decorator:post:/api/v1/admin/force-update -> force_database_update",
        "legacy_app.py: unexpected legacy route growth: "
        "decorator:post:/api/v1/admin/rollback -> rollback_database",
    ]


def test_legacy_growth_guard_rejects_new_router_registration() -> None:
    source = "app.include_router(new_router)\n"

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: registration:include_router:new_router"
    ]


def test_legacy_growth_guard_rejects_add_api_route_registration() -> None:
    source = 'app.add_api_route("/api/v1/new-runtime", new_runtime_route)\n'

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:add_api_route:/api/v1/new-runtime"
    ]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            'app.add_route("/api/v1/new-runtime", new_runtime_route)\n',
            "legacy_app.py: unexpected legacy route growth: "
            "registration:add_route:/api/v1/new-runtime",
        ),
        (
            'app.router.add_api_route("/api/v1/new-runtime", new_runtime_route)\n',
            "legacy_app.py: unexpected legacy route growth: "
            "registration:router.add_api_route:/api/v1/new-runtime",
        ),
        (
            'app.add_websocket_route("/ws/new-runtime", new_runtime_ws)\n',
            "legacy_app.py: unexpected legacy route growth: "
            "registration:add_websocket_route:/ws/new-runtime",
        ),
    ],
)
def test_legacy_growth_guard_rejects_router_api_registration_aliases(
    source: str,
    expected: str,
) -> None:
    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [expected]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            textwrap.dedent("""
                legacy = app
                legacy.add_api_route("/api/v1/new-runtime", new_runtime_route)
                """),
            "legacy_app.py: unexpected legacy route growth: "
            "registration:add_api_route:/api/v1/new-runtime",
        ),
        (
            textwrap.dedent("""
                legacy = app

                @legacy.post("/api/v1/new-runtime")
                async def new_runtime_route():
                    return {"ok": True}
                """),
            "legacy_app.py: unexpected legacy route growth: "
            "decorator:post:/api/v1/new-runtime -> new_runtime_route",
        ),
        (
            textwrap.dedent("""
                legacy = app
                legacy_router = legacy.router
                legacy_router.add_api_route("/api/v1/new-runtime", new_runtime_route)
                """),
            "legacy_app.py: unexpected legacy route growth: "
            "registration:router.add_api_route:/api/v1/new-runtime",
        ),
    ],
)
def test_legacy_growth_guard_rejects_app_alias_registrations(
    source: str,
    expected: str,
) -> None:
    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [expected]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            textwrap.dedent("""
                @app.route("/api/v1/new-runtime")
                async def new_runtime_route():
                    return {"ok": True}
                """),
            "legacy_app.py: unexpected legacy route growth: "
            "decorator:route:/api/v1/new-runtime -> new_runtime_route",
        ),
        (
            textwrap.dedent("""
                @app.websocket_route("/ws/new-runtime")
                async def new_runtime_ws(websocket):
                    pass
                """),
            "legacy_app.py: unexpected legacy route growth: "
            "decorator:websocket_route:/ws/new-runtime -> new_runtime_ws",
        ),
    ],
)
def test_legacy_growth_guard_rejects_route_decorator_aliases(
    source: str,
    expected: str,
) -> None:
    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [expected]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            'registered = app.add_api_route("/api/v1/new-runtime", new_runtime_route)\n',
            "legacy_app.py: unexpected legacy route growth: "
            "registration:add_api_route:/api/v1/new-runtime",
        ),
        (
            "registered = app.add_middleware(NewRuntimeMiddleware)\n",
            "legacy_app.py: unexpected legacy route growth: "
            "registration:add_middleware:NewRuntimeMiddleware",
        ),
        (
            "registered = app.include_router(new_router)\n",
            "legacy_app.py: unexpected legacy route growth: "
            "registration:include_router:new_router",
        ),
    ],
)
def test_legacy_growth_guard_rejects_non_expression_app_registrations(
    source: str,
    expected: str,
) -> None:
    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [expected]


def test_legacy_growth_guard_rejects_add_middleware() -> None:
    source = "app.add_middleware(NewRuntimeMiddleware)\n"

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:add_middleware:NewRuntimeMiddleware"
    ]


def test_legacy_growth_guard_rejects_middleware_decorator() -> None:
    source = textwrap.dedent("""
        @app.middleware("http")
        async def new_legacy_middleware(request, call_next):
            return await call_next(request)
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "decorator:middleware:http -> new_legacy_middleware"
    ]


def test_legacy_growth_guard_rejects_new_router_import() -> None:
    source = "from app.routers.new_surface import router as new_router\n"

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:app.routers.new_surface:router -> new_router"
    ]


def test_legacy_growth_guard_rejects_legal_router_import() -> None:
    source = "from app.routers.legal import build_terms_endpoint_payload\n"

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:app.routers.legal:build_terms_endpoint_payload"
    ]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            textwrap.dedent("""
                from app.routers.pro_registration import register_pro_routes as _register_pro_routes

                pro_router, premium_week_router = _register_pro_routes(app)
                """),
            "legacy_app.py: unexpected app.routers import growth: "
            "router_import:app.routers.pro_registration:register_pro_routes -> "
            "_register_pro_routes",
        ),
        (
            textwrap.dedent("""
                from app.routers.vip_registration import register_vip_routes

                register_vip_routes(app)
                """),
            "legacy_app.py: unexpected app.routers import growth: "
            "router_import:app.routers.vip_registration:register_vip_routes",
        ),
    ],
)
def test_legacy_growth_guard_rejects_reintroduced_paid_tier_registration_imports(
    source: str,
    expected: str,
) -> None:
    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [expected]


def test_legacy_growth_guard_rejects_reintroduced_plan_export_router_registration() -> None:
    source = textwrap.dedent("""
        from app.routers.plan_export import export_router, plan_router

        app.include_router(export_router, dependencies=[protected_dependency])
        app.include_router(plan_router, dependencies=[protected_dependency])
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:include_router:export_router",
        "legacy_app.py: unexpected legacy route growth: " "registration:include_router:plan_router",
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:app.routers.plan_export:export_router",
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:app.routers.plan_export:plan_router",
    ]


def test_legacy_growth_guard_rejects_reintroduced_aliased_plan_export_registration() -> None:
    source = textwrap.dedent("""
        from app.routers.plan_export import export_router as canonical_export_router
        from app.routers.plan_export import plan_router as canonical_plan_router

        app.include_router(canonical_export_router, dependencies=[protected_dependency])
        app.include_router(canonical_plan_router, dependencies=[protected_dependency])
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:include_router:canonical_export_router",
        "legacy_app.py: unexpected legacy route growth: "
        "registration:include_router:canonical_plan_router",
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:app.routers.plan_export:export_router -> canonical_export_router",
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:app.routers.plan_export:plan_router -> canonical_plan_router",
    ]


def test_legacy_growth_guard_rejects_reintroduced_shoplist_export_registration() -> None:
    source = textwrap.dedent("""
        from app.routers.shoplist_export import router as shoplist_router

        app.include_router(shoplist_router, dependencies=[protected_dependency])
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:include_router:shoplist_router",
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:app.routers.shoplist_export:router -> shoplist_router",
    ]


def test_legacy_growth_guard_rejects_reintroduced_aliased_shoplist_export_registration() -> None:
    source = textwrap.dedent("""
        from app.routers.shoplist_export import router as canonical_shoplist_router

        app.include_router(canonical_shoplist_router, dependencies=[protected_dependency])
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:include_router:canonical_shoplist_router",
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:app.routers.shoplist_export:router -> canonical_shoplist_router",
    ]


def test_legacy_growth_guard_rejects_reintroduced_bodyfat_factory_registration() -> None:
    source = textwrap.dedent("""
        from app.routers.bodyfat import get_router as get_bodyfat_router

        app.include_router(get_bodyfat_router(), prefix="/api/v1")
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:include_router:get_bodyfat_router()",
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:app.routers.bodyfat:get_router -> get_bodyfat_router",
    ]


def test_legacy_growth_guard_rejects_direct_bodyfat_router_registration() -> None:
    source = textwrap.dedent("""
        from app.routers.bodyfat import router

        app.include_router(router)
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: registration:include_router:router",
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:app.routers.bodyfat:router",
    ]


def test_legacy_growth_guard_rejects_aliased_bodyfat_router_registration() -> None:
    source = textwrap.dedent("""
        from app.routers.bodyfat import router as canonical_bodyfat_router

        app.include_router(canonical_bodyfat_router)
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:include_router:canonical_bodyfat_router",
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:app.routers.bodyfat:router -> canonical_bodyfat_router",
    ]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            textwrap.dedent("""
                from app.routers.business import router as business_router

                app.include_router(business_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:business_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:app.routers.business:router -> business_router",
            ],
        ),
        (
            textwrap.dedent("""
                from app.routers.business import router as canonical_business_router

                app.include_router(canonical_business_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:canonical_business_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:app.routers.business:router -> canonical_business_router",
            ],
        ),
        (
            textwrap.dedent("""
                import app.routers.business as business_routes

                app.include_router(business_routes.router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:business_routes.router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:import:app.routers.business -> business_routes",
            ],
        ),
        (
            textwrap.dedent("""
                import importlib

                business_router = importlib.import_module("app.routers.business").router
                app.include_router(business_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:business_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.business -> business_router",
            ],
        ),
        (
            textwrap.dedent("""
                import importlib

                if (business_router := importlib.import_module("app.routers.business").router):
                    app.include_router(business_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:business_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.business -> business_router",
            ],
        ),
    ],
)
def test_legacy_growth_guard_rejects_business_router_reintroduction(
    source: str,
    expected: list[str],
) -> None:
    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            textwrap.dedent("""
                from app.routers import bayes_adherence

                app.include_router(bayes_adherence.router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:bayes_adherence.router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:app.routers:bayes_adherence",
            ],
        ),
        (
            textwrap.dedent("""
                from app.routers import nutrition_log as nutrition_routes

                app.include_router(nutrition_routes.router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:nutrition_routes.router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:app.routers:nutrition_log -> nutrition_routes",
            ],
        ),
        (
            textwrap.dedent("""
                from app.routers.legacy_nutrition_alias import (
                    router as legacy_nutrition_alias_router,
                )

                app.include_router(legacy_nutrition_alias_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:legacy_nutrition_alias_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:app.routers.legacy_nutrition_alias:router -> "
                "legacy_nutrition_alias_router",
            ],
        ),
        (
            textwrap.dedent("""
                import app.routers.nutrition_log as nutrition_log_module

                app.include_router(nutrition_log_module.router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:nutrition_log_module.router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:import:app.routers.nutrition_log -> nutrition_log_module",
            ],
        ),
        (
            textwrap.dedent("""
                import importlib

                bayes_router = importlib.import_module("app.routers.bayes_adherence").router
                app.include_router(bayes_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:bayes_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.bayes_adherence -> bayes_router",
            ],
        ),
        (
            textwrap.dedent("""
                import importlib

                nutrition_router, _ = (
                    importlib.import_module("app.routers.nutrition_log").router,
                    None,
                )
                app.include_router(nutrition_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:nutrition_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.nutrition_log -> nutrition_router",
            ],
        ),
        (
            textwrap.dedent("""
                from importlib import import_module

                if (alias_router := import_module("app.routers.legacy_nutrition_alias").router):
                    app.include_router(alias_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:alias_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.legacy_nutrition_alias -> alias_router",
            ],
        ),
    ],
)
def test_legacy_growth_guard_rejects_nutrition_state_router_reintroduction(
    source: str,
    expected: list[str],
) -> None:
    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            textwrap.dedent("""
                from app.routers.shopping_list_pro import router as shopping_list_pro_router

                app.include_router(shopping_list_pro_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:shopping_list_pro_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:app.routers.shopping_list_pro:router -> "
                "shopping_list_pro_router",
            ],
        ),
        (
            textwrap.dedent("""
                from app.routers.shoplist_day import router as shoplist_day_router

                app.include_router(shoplist_day_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:shoplist_day_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:app.routers.shoplist_day:router -> shoplist_day_router",
            ],
        ),
        (
            textwrap.dedent("""
                from app.routers.shopping_list_pro import router as canonical_shopping_router

                app.include_router(canonical_shopping_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:canonical_shopping_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:app.routers.shopping_list_pro:router -> "
                "canonical_shopping_router",
            ],
        ),
        (
            textwrap.dedent("""
                import app.routers.shoplist_day as shoplist_day_module

                app.include_router(shoplist_day_module.router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:shoplist_day_module.router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:import:app.routers.shoplist_day -> shoplist_day_module",
            ],
        ),
        (
            textwrap.dedent("""
                import importlib

                shopping_router = importlib.import_module("app.routers.shopping_list_pro").router
                app.include_router(shopping_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:shopping_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.shopping_list_pro -> shopping_router",
            ],
        ),
        (
            textwrap.dedent("""
                import importlib

                shopping_router, _ = (
                    importlib.import_module("app.routers.shoplist_day").router,
                    None,
                )
                app.include_router(shopping_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:shopping_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.shoplist_day -> shopping_router",
            ],
        ),
        (
            textwrap.dedent("""
                from importlib import import_module

                if (shopping_router := import_module("app.routers.shoplist_day").router):
                    app.include_router(shopping_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:shopping_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.shoplist_day -> shopping_router",
            ],
        ),
    ],
)
def test_legacy_growth_guard_rejects_shopping_list_router_reintroduction(
    source: str,
    expected: list[str],
) -> None:
    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            textwrap.dedent("""
                from app.routers.foods import router as foods_router

                app.include_router(foods_router, include_in_schema=False)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:foods_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:app.routers.foods:router -> foods_router",
            ],
        ),
        (
            textwrap.dedent("""
                from app.routers.catalog import router as catalog_router

                app.include_router(catalog_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:catalog_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:app.routers.catalog:router -> catalog_router",
            ],
        ),
        (
            textwrap.dedent("""
                from app.routers.foods import router as canonical_foods_router

                app.include_router(canonical_foods_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:canonical_foods_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:app.routers.foods:router -> canonical_foods_router",
            ],
        ),
        (
            textwrap.dedent("""
                import app.routers.catalog as catalog_routes

                app.include_router(catalog_routes.router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:catalog_routes.router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:import:app.routers.catalog -> catalog_routes",
            ],
        ),
        (
            textwrap.dedent("""
                import importlib

                food_router = importlib.import_module("app.routers.foods").router
                app.include_router(food_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:food_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.foods -> food_router",
            ],
        ),
        (
            textwrap.dedent("""
                import importlib

                catalog_router, _ = (
                    importlib.import_module("app.routers.catalog").router,
                    None,
                )
                app.include_router(catalog_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:catalog_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.catalog -> catalog_router",
            ],
        ),
        (
            textwrap.dedent("""
                from importlib import import_module

                if (food_router := import_module("app.routers.foods").router):
                    app.include_router(food_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:food_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.foods -> food_router",
            ],
        ),
        (
            textwrap.dedent("""
                import importlib

                wrapper_router = APIRouter()
                wrapper_router.include_router(
                    importlib.import_module("app.routers.catalog").router
                )
                app.include_router(wrapper_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:wrapper_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.catalog -> wrapper_router.include_router",
            ],
        ),
    ],
)
def test_legacy_growth_guard_rejects_food_catalog_router_reintroduction(
    source: str,
    expected: list[str],
) -> None:
    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            textwrap.dedent("""
                from app.routers.users import router

                app.include_router(router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:app.routers.users:router",
            ],
        ),
        (
            textwrap.dedent("""
                from app.routers.users import router as users_router

                app.include_router(users_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:users_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:app.routers.users:router -> users_router",
            ],
        ),
        (
            textwrap.dedent("""
                import app.routers.users as users_routes

                app.include_router(users_routes.router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:users_routes.router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:import:app.routers.users -> users_routes",
            ],
        ),
        (
            textwrap.dedent("""
                import importlib

                module_name = "app.routers." + "users"
                users_router = importlib.import_module(module_name).router
                app.include_router(users_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:users_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.users -> users_router",
            ],
        ),
        (
            textwrap.dedent("""
                from importlib import import_module

                if (users_router := import_module("app.routers.users").router):
                    app.include_router(users_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:users_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.users -> users_router",
            ],
        ),
        (
            textwrap.dedent("""
                import importlib

                wrapper_router = APIRouter()
                wrapper_router.include_router(
                    importlib.import_module("app.routers.users").router
                )
                app.include_router(wrapper_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:wrapper_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.users -> wrapper_router.include_router",
            ],
        ),
    ],
)
def test_legacy_growth_guard_rejects_users_router_reintroduction(
    source: str,
    expected: list[str],
) -> None:
    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            textwrap.dedent("""
                from app.routers.restaurants import router

                app.include_router(router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:app.routers.restaurants:router",
            ],
        ),
        (
            textwrap.dedent("""
                from app.routers.restaurants import router as restaurants_router

                app.include_router(restaurants_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:restaurants_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:app.routers.restaurants:router -> restaurants_router",
            ],
        ),
        (
            textwrap.dedent("""
                import app.routers.restaurants as restaurant_routes

                app.include_router(restaurant_routes.router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:restaurant_routes.router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:import:app.routers.restaurants -> restaurant_routes",
            ],
        ),
        (
            textwrap.dedent("""
                import importlib

                restaurants_router = importlib.import_module("app.routers.restaurants").router
                app.include_router(restaurants_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:restaurants_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.restaurants -> restaurants_router",
            ],
        ),
        (
            textwrap.dedent("""
                import importlib

                module_name = "app.routers." + "restaurants"
                restaurants_router = importlib.import_module(module_name).router
                app.include_router(restaurants_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:restaurants_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.restaurants -> restaurants_router",
            ],
        ),
        (
            textwrap.dedent("""
                import importlib

                restaurants_router, _ = (
                    importlib.import_module("app.routers.restaurants").router,
                    None,
                )
                app.include_router(restaurants_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:restaurants_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.restaurants -> restaurants_router",
            ],
        ),
        (
            textwrap.dedent("""
                from importlib import import_module

                if (restaurants_router := import_module("app.routers.restaurants").router):
                    app.include_router(restaurants_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:restaurants_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.restaurants -> restaurants_router",
            ],
        ),
        (
            textwrap.dedent("""
                import importlib

                wrapper_router = APIRouter()
                wrapper_router.include_router(
                    importlib.import_module("app.routers.restaurants").router
                )
                app.include_router(wrapper_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:wrapper_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.restaurants -> wrapper_router.include_router",
            ],
        ),
    ],
    ids=[
        "direct_import",
        "aliased_import",
        "module_qualified_import",
        "dynamic_literal_import",
        "dynamic_computed_import",
        "destructured_dynamic_import",
        "walrus_dynamic_import",
        "nested_wrapper_dynamic_import",
    ],
)
def test_legacy_growth_guard_rejects_restaurants_router_reintroduction(
    source: str,
    expected: list[str],
) -> None:
    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            textwrap.dedent("""
                from app.routers.recipes import router as recipes_router

                app.include_router(recipes_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:recipes_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:app.routers.recipes:router -> recipes_router",
            ],
        ),
        (
            textwrap.dedent("""
                from app.routers.nutrition_recommendations import (
                    router as nutrition_recommendations_router,
                )

                app.include_router(nutrition_recommendations_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:nutrition_recommendations_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:app.routers.nutrition_recommendations:router -> "
                "nutrition_recommendations_router",
            ],
        ),
        (
            textwrap.dedent("""
                from app.routers.recipes import router as canonical_recipes_router

                app.include_router(canonical_recipes_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:canonical_recipes_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:app.routers.recipes:router -> canonical_recipes_router",
            ],
        ),
        (
            textwrap.dedent("""
                import app.routers.recipes as recipe_routes

                app.include_router(recipe_routes.router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:recipe_routes.router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:import:app.routers.recipes -> recipe_routes",
            ],
        ),
        (
            textwrap.dedent("""
                import importlib

                module_name = "app.routers." + "recipes"
                recipe_router = importlib.import_module(module_name).router
                app.include_router(recipe_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:recipe_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.recipes -> recipe_router",
            ],
        ),
        (
            textwrap.dedent("""
                import importlib

                family = "nutrition_recommendations"
                module_name = f"app.routers.{family}"
                nutrition_router = importlib.import_module(module_name).router
                app.include_router(nutrition_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:nutrition_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.nutrition_recommendations -> "
                "nutrition_router",
            ],
        ),
        (
            textwrap.dedent("""
                import importlib

                nutrition_recommendations_router, _ = (
                    importlib.import_module("app.routers.nutrition_recommendations").router,
                    None,
                )
                app.include_router(nutrition_recommendations_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:nutrition_recommendations_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.nutrition_recommendations -> "
                "nutrition_recommendations_router",
            ],
        ),
        (
            textwrap.dedent("""
                from importlib import import_module

                if (recipes_router := import_module("app.routers.recipes").router):
                    app.include_router(recipes_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:recipes_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.recipes -> recipes_router",
            ],
        ),
        (
            textwrap.dedent("""
                from importlib import import_module

                getattr(app, "include_router")(
                    import_module("app.routers.recipes").router
                )
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:import_module('app.routers.recipes').router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.recipes -> "
                "getattr(app, 'include_router')",
            ],
        ),
        (
            textwrap.dedent("""
                from importlib import import_module

                method = "include_" + "router"
                getattr(app, method)(
                    import_module("app.routers.recipes").router
                )
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:import_module('app.routers.recipes').router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.recipes -> getattr(app, method)",
            ],
        ),
        (
            textwrap.dedent("""
                import importlib

                wrapper_router = APIRouter()
                wrapper_router.include_router(
                    importlib.import_module("app.routers.nutrition_recommendations").router
                )
                app.include_router(wrapper_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:wrapper_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.nutrition_recommendations -> "
                "wrapper_router.include_router",
            ],
        ),
    ],
)
def test_legacy_growth_guard_rejects_recipe_nutrition_reference_router_reintroduction(
    source: str,
    expected: list[str],
) -> None:
    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            textwrap.dedent("""
                import importlib

                module_name = "app.routers." + "foods"
                recipes_router = importlib.import_module(module_name).router
                app.include_router(recipes_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:recipes_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.foods -> recipes_router",
            ],
        ),
        (
            textwrap.dedent("""
                import importlib

                module_name = ".".join(["app", "routers", "catalog"])
                users_router = importlib.import_module(module_name).router
                app.include_router(users_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:users_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.catalog -> users_router",
            ],
        ),
        (
            textwrap.dedent("""
                import importlib

                family = "catalog"
                module_name = f"app.routers.{family}"
                restaurants_router = importlib.import_module(module_name).router
                app.include_router(restaurants_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:restaurants_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.catalog -> restaurants_router",
            ],
        ),
        (
            textwrap.dedent("""
                import importlib
                import os

                family = os.getenv("ROUTER_FAMILY", "foods")
                module_name = f"app.routers.{family}"
                nutrition_recommendations_router = importlib.import_module(module_name).router
                app.include_router(nutrition_recommendations_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:nutrition_recommendations_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:<unresolved app.routers import> -> "
                "nutrition_recommendations_router",
            ],
        ),
        (
            textwrap.dedent("""
                import importlib
                import os

                module_name = os.getenv("LEGACY_ROUTER_MODULE")
                recipes_router = importlib.import_module(module_name).router
                app.include_router(recipes_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:recipes_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:<unresolved dynamic router import> -> recipes_router",
            ],
        ),
        (
            textwrap.dedent("""
                import os
                from importlib import import_module

                module = import_module(os.getenv("LEGACY_ROUTER_MODULE"))
                recipes_router.include_router(module.router)
                app.include_router(recipes_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:recipes_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:<unresolved dynamic router import> -> "
                "recipes_router.include_router",
            ],
        ),
        (
            textwrap.dedent("""
                import os
                from importlib import import_module

                module = import_module(os.getenv("LEGACY_ROUTER_MODULE"))
                router = module.router
                recipes_router.include_router(router)
                app.include_router(recipes_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:recipes_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:<unresolved dynamic router import> -> "
                "recipes_router.include_router",
            ],
        ),
        (
            textwrap.dedent("""
                import importlib

                recipes_router = importlib.import_module(name="app.routers.foods").router
                app.include_router(recipes_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:recipes_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.foods -> recipes_router",
            ],
        ),
    ],
)
def test_legacy_growth_guard_rejects_computed_food_catalog_dynamic_import_alias_bypass(
    source: str,
    expected: list[str],
) -> None:
    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == expected


def test_legacy_growth_guard_allows_unregistered_dynamic_import_without_router_use() -> None:
    source = textwrap.dedent("""
        import os
        from importlib import import_module

        module = import_module(os.getenv("LEGACY_HELPER_MODULE"))
        value = module.VALUE
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_rejects_module_qualified_bodyfat_router_registration() -> None:
    source = textwrap.dedent("""
        import app.routers.bodyfat as bodyfat_routes

        app.include_router(bodyfat_routes.router)
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:include_router:bodyfat_routes.router",
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:import:app.routers.bodyfat -> bodyfat_routes",
    ]


def test_legacy_growth_guard_rejects_dynamic_bodyfat_router_hidden_as_allowed_name() -> None:
    source = textwrap.dedent("""
        import importlib

        business_router = importlib.import_module("app.routers.bodyfat").router
        app.include_router(business_router)
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:include_router:business_router",
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:dynamic:app.routers.bodyfat -> business_router",
    ]


def test_legacy_growth_guard_rejects_dunder_import_bodyfat_router_hidden_as_allowed_name() -> None:
    source = textwrap.dedent("""
        business_router = __import__("app.routers.bodyfat", fromlist=["router"]).router
        app.include_router(business_router)
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:include_router:business_router",
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:dynamic:app.routers.bodyfat -> business_router",
    ]


def test_legacy_growth_guard_rejects_aliased_import_module_bodyfat_router() -> None:
    source = textwrap.dedent("""
        from importlib import import_module as load_router_module

        business_router = load_router_module("app.routers.bodyfat").router
        app.include_router(business_router)
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:include_router:business_router",
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:dynamic:app.routers.bodyfat -> business_router",
    ]


def test_legacy_growth_guard_rejects_aliased_builtin_import_bodyfat_router() -> None:
    source = textwrap.dedent("""
        from builtins import __import__ as load_router_module

        business_router = load_router_module("app.routers.bodyfat", fromlist=["router"]).router
        app.include_router(business_router)
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:include_router:business_router",
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:dynamic:app.routers.bodyfat -> business_router",
    ]


def test_legacy_growth_guard_rejects_simple_import_module_alias_bodyfat_router() -> None:
    source = textwrap.dedent("""
        import importlib

        load_router_module = importlib.import_module
        business_router = load_router_module("app.routers.bodyfat").router
        app.include_router(business_router)
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:include_router:business_router",
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:dynamic:app.routers.bodyfat -> business_router",
    ]


def test_legacy_growth_guard_rejects_simple_dunder_import_alias_bodyfat_router() -> None:
    source = textwrap.dedent("""
        load_router_module = __import__
        business_router = load_router_module("app.routers.bodyfat", fromlist=["router"]).router
        app.include_router(business_router)
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:include_router:business_router",
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:dynamic:app.routers.bodyfat -> business_router",
    ]


def test_legacy_growth_guard_rejects_destructured_dynamic_bodyfat_router() -> None:
    source = textwrap.dedent("""
        import importlib

        business_router, _ = (importlib.import_module("app.routers.bodyfat").router, None)
        app.include_router(business_router)
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:include_router:business_router",
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:dynamic:app.routers.bodyfat -> business_router",
    ]


def test_legacy_growth_guard_rejects_walrus_dynamic_bodyfat_router() -> None:
    source = textwrap.dedent("""
        import importlib

        if (business_router := importlib.import_module("app.routers.bodyfat").router):
            app.include_router(business_router)
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:include_router:business_router",
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:dynamic:app.routers.bodyfat -> business_router",
    ]


def test_legacy_growth_guard_rejects_walrus_import_function_alias_bodyfat_router() -> None:
    source = textwrap.dedent("""
        import importlib

        if (load_router_module := importlib.import_module):
            business_router = load_router_module("app.routers.bodyfat").router
            app.include_router(business_router)
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:include_router:business_router",
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:dynamic:app.routers.bodyfat -> business_router",
    ]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            textwrap.dedent("""
                from app.routers import test as test_router

                app.include_router(test_router.router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:test_router.router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:app.routers:test -> test_router",
            ],
        ),
        (
            textwrap.dedent("""
                from app.routers.test import router as canonical_test_router

                app.include_router(canonical_test_router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:canonical_test_router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:app.routers.test:router -> canonical_test_router",
            ],
        ),
        (
            textwrap.dedent("""
                import app.routers.test as test_router

                app.include_router(test_router.router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:test_router.router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:import:app.routers.test -> test_router",
            ],
        ),
        (
            textwrap.dedent("""
                import importlib

                test_router = importlib.import_module("app.routers.test")
                app.include_router(test_router.router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:test_router.router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.test -> test_router",
            ],
        ),
        (
            textwrap.dedent("""
                from importlib import import_module

                if (test_router := import_module("app.routers.test")):
                    app.include_router(test_router.router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:test_router.router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.test -> test_router",
            ],
        ),
    ],
)
def test_legacy_growth_guard_rejects_reintroduced_test_router_registration(
    source: str,
    expected: list[str],
) -> None:
    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == expected


def test_legacy_growth_guard_rejects_nested_dynamic_bodyfat_router_registration() -> None:
    source = textwrap.dedent("""
        import importlib

        app.include_router(importlib.import_module("app.routers.bodyfat").router)
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:include_router:importlib.import_module('app.routers.bodyfat').router",
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:dynamic:app.routers.bodyfat -> app.include_router",
    ]


def test_legacy_growth_guard_rejects_nested_dynamic_bodyfat_router_composition() -> None:
    source = textwrap.dedent("""
        from fastapi import APIRouter
        import importlib

        business_router = APIRouter()
        business_router.include_router(importlib.import_module("app.routers.bodyfat").router)
        app.include_router(business_router)
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:include_router:business_router",
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:dynamic:app.routers.bodyfat -> business_router.include_router",
    ]


def test_legacy_growth_guard_rejects_reintroduced_restaurant_moderation_registration() -> None:
    source = textwrap.dedent("""
        from app.routers.restaurants import moderation_router as restaurant_moderation_router

        app.include_router(
            restaurant_moderation_router,
            dependencies=[Depends(_get_api_key_dynamic)],
            include_in_schema=False,
        )
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:include_router:restaurant_moderation_router",
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:app.routers.restaurants:moderation_router -> "
        "restaurant_moderation_router",
        "legacy_app.py: sensitive app surface grew for api_key: 1 > 0",
    ]


def test_legacy_growth_guard_rejects_direct_restaurant_moderation_import() -> None:
    source = textwrap.dedent("""
        from app.routers.restaurants import moderation_router

        app.include_router(moderation_router, dependencies=[Depends(_get_api_key_dynamic)])
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:include_router:moderation_router",
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:app.routers.restaurants:moderation_router",
        "legacy_app.py: sensitive app surface grew for api_key: 1 > 0",
    ]


def test_legacy_growth_guard_rejects_normal_router_import() -> None:
    source = "import app.routers.new_surface as new_surface\n"

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected app.routers import growth: "
        "router_import:import:app.routers.new_surface -> new_surface"
    ]


def test_legacy_growth_guard_rejects_sensitive_call_growth() -> None:
    source = "def call(provider):\n    return provider.generate('unsafe')\n"

    errors = legacy_guard.validate_legacy_growth(
        source,
        sensitive_call_limits={key: 0 for key in legacy_guard.SENSITIVE_CALL_KEYWORDS},
    )

    assert errors == ["legacy_app.py: sensitive call family grew for provider: 1 > 0"]


@pytest.mark.parametrize(
    ("keyword", "source"),
    [
        (
            "api_key",
            "\n".join(
                "api_key_guard()" for _ in range(legacy_guard.SENSITIVE_CALL_LIMITS["api_key"] + 1)
            ),
        ),
        ("auth", "auth_guard()\n"),
        ("entitlement", "entitlement.check()\n"),
        (
            "llm",
            "\n".join(
                "llm.generate()" for _ in range(legacy_guard.SENSITIVE_CALL_LIMITS["llm"] + 1)
            ),
        ),
        ("provider", "provider.generate()\nprovider.generate()\n"),
        ("quota", "quota.consume()\nquota.consume()\n"),
    ],
)
def test_legacy_growth_guard_rejects_current_baseline_sensitive_growth(
    keyword: str,
    source: str,
) -> None:
    errors = legacy_guard.validate_legacy_growth(source)

    limit = legacy_guard.SENSITIVE_CALL_LIMITS[keyword]
    assert errors == [
        f"legacy_app.py: sensitive call family grew for {keyword}: {limit + 1} > {limit}"
    ]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            "from providers.openai import client\nclient.generate('unsafe')\n",
            "legacy_app.py: sensitive call family grew for provider: 1 > 0",
        ),
        (
            "from core.llm import model as m\nm.generate('unsafe')\n",
            "legacy_app.py: sensitive call family grew for llm: 1 > 0",
        ),
        (
            "from core import llm as l\nl.model.generate('unsafe')\n",
            "legacy_app.py: sensitive call family grew for llm: 1 > 0",
        ),
    ],
)
def test_legacy_growth_guard_rejects_sensitive_import_alias_calls(
    source: str,
    expected: str,
) -> None:
    errors = legacy_guard.validate_legacy_growth(
        source,
        sensitive_call_limits={key: 0 for key in legacy_guard.SENSITIVE_CALL_KEYWORDS},
    )

    assert errors == [expected]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            textwrap.dedent("""
                auth_alias = auth_guard
                guard = auth_alias
                guard()
                """),
            "legacy_app.py: sensitive call family grew for auth: 1 > 0",
        ),
        (
            textwrap.dedent("""
                from app.auth import auth_guard as imported_guard

                guard = imported_guard
                guard()
                """),
            "legacy_app.py: sensitive call family grew for auth: 1 > 0",
        ),
    ],
)
def test_legacy_growth_guard_rejects_sensitive_local_assignment_alias_calls(
    source: str,
    expected: str,
) -> None:
    errors = legacy_guard.validate_legacy_growth(
        source,
        sensitive_call_limits={key: 0 for key in legacy_guard.SENSITIVE_CALL_KEYWORDS},
    )

    assert errors == [expected]


def test_legacy_growth_guard_rejects_auth_dependency_on_reintroduced_route() -> None:
    source = textwrap.dedent("""
        @app.post("/api/v1/insight", dependencies=[Depends(auth_guard)])
        def insight_v1_route():
            return {"ok": True}
        """)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "decorator:post:/api/v1/insight -> insight_v1_route",
        "legacy_app.py: sensitive app surface grew for auth: 1 > 0",
    ]


def test_legacy_growth_guard_rejects_auth_dependency_on_allowed_router() -> None:
    source = "app.include_router(_vip_mod.router, dependencies=[Depends(auth_guard)])\n"

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "registration:include_router:_vip_mod.router",
        "legacy_app.py: sensitive app surface grew for auth: 1 > 0",
    ]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            textwrap.dedent("""
                deps = [Depends(auth_guard)]

                @app.post("/api/v1/insight", dependencies=deps)
                def insight_v1_route():
                    return {"ok": True}
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "decorator:post:/api/v1/insight -> insight_v1_route",
                "legacy_app.py: sensitive app surface grew for auth: 1 > 0",
            ],
        ),
        (
            textwrap.dedent("""
                deps = [Depends(auth_guard)]
                app.include_router(_vip_mod.router, dependencies=deps)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:_vip_mod.router",
                "legacy_app.py: sensitive app surface grew for auth: 1 > 0",
            ],
        ),
    ],
    ids=[
        "decorator_dependency_alias",
        "include_router_dependency_alias",
    ],
)
def test_legacy_growth_guard_rejects_sensitive_dependency_aliases(
    source: str,
    expected: list[str],
) -> None:
    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == expected


def test_legacy_growth_guard_rejects_api_key_surface_growth_on_current_baseline() -> None:
    source = (REPO_ROOT / "legacy_app.py").read_text(encoding="utf-8")
    limit = legacy_guard.SENSITIVE_APP_SURFACE_LIMITS["api_key"]
    source += textwrap.dedent("""

        @app.post("/api/v1/insight", dependencies=[Depends(api_key_guard)])
        def insight_v1_route():
            return {"ok": True}
        """) * (limit + 1)

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == [
        "legacy_app.py: unexpected legacy route growth: "
        "decorator:post:/api/v1/insight -> insight_v1_route",
        f"legacy_app.py: sensitive app surface grew for api_key: {limit + 1} > {limit}",
    ]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            textwrap.dedent("""
                @app.post("/api/v1/insight")
                async def insight_v1_route():
                    return {"ok": True}
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "decorator:post:/api/v1/insight -> insight_v1_route",
            ],
        ),
        (
            textwrap.dedent("""
                @app.post("/insight")
                async def insight_route():
                    return {"ok": True}
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "decorator:post:/insight -> insight_route",
            ],
        ),
        (
            'app.router.add_api_route("/api/v1/insight", handler, methods=["POST"])\n',
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:router.add_api_route:/api/v1/insight",
            ],
        ),
        (
            'app.add_api_route("/insight", handler, methods=["POST"])\n',
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:add_api_route:/insight",
            ],
        ),
        (
            textwrap.dedent("""
                legacy = app

                @legacy.post("/insight")
                async def wrapped_insight_route():
                    return {"ok": True}
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "decorator:post:/insight -> wrapped_insight_route",
            ],
        ),
        (
            "app.include_router(insight_router)\n",
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:insight_router",
            ],
        ),
        (
            textwrap.dedent("""
                import importlib

                _mod = importlib.import_module("app.routers.legacy_insight")
                app.include_router(_mod.router)
                """),
            [
                "legacy_app.py: unexpected legacy route growth: "
                "registration:include_router:_mod.router",
                "legacy_app.py: unexpected app.routers import growth: "
                "router_import:dynamic:app.routers.legacy_insight -> _mod",
            ],
        ),
    ],
    ids=[
        "direct_decorator_v1",
        "direct_decorator_legacy",
        "router_add_api_route",
        "app_add_api_route",
        "aliased_app_wrapper",
        "include_router",
        "dynamic_imported_router",
    ],
)
def test_legacy_growth_guard_blocks_insight_route_reintroduction(
    source: str,
    expected: list[str],
) -> None:
    """Extracted insight routes must never regrow inside legacy_app.py."""

    errors = legacy_guard.validate_legacy_growth(source)

    assert errors == expected


def test_legacy_growth_guard_ignores_comments_and_strings() -> None:
    source = textwrap.dedent("""
        "# @app.post('/not-real')"
        # app.include_router(fake_router)
        def route_text():
            return "app.include_router(fake_router)"
        """)

    assert legacy_guard.validate_legacy_growth(source) == []


def test_legacy_growth_guard_fails_closed_on_syntax_error() -> None:
    errors = legacy_guard.validate_legacy_growth("def broken(:\n")

    assert errors == ["legacy_app.py:1: syntax error: invalid syntax"]


def test_legacy_seam_doc_rejects_missing_marker() -> None:
    text = (REPO_ROOT / "docs/architecture/LEGACY_COMPATIBILITY_SEAM.md").read_text(
        encoding="utf-8"
    )
    text = text.replace("<!-- LEGACY_SEAM_OPENAPI_CHANGED: false -->\n", "")

    errors = legacy_guard.validate_legacy_seam_doc(text)

    assert (
        "docs/architecture/LEGACY_COMPATIBILITY_SEAM.md: missing marker LEGACY_SEAM_OPENAPI_CHANGED"
        in errors
    )


def test_legacy_repo_validation_rejects_empty_doc(tmp_path: Path) -> None:
    (tmp_path / "legacy_app.py").write_text("", encoding="utf-8")
    doc_path = tmp_path / "docs/architecture/LEGACY_COMPATIBILITY_SEAM.md"
    doc_path.parent.mkdir(parents=True)
    doc_path.write_text("", encoding="utf-8")

    errors = legacy_guard.validate_repo(tmp_path)

    assert (
        "docs/architecture/LEGACY_COMPATIBILITY_SEAM.md: missing marker LEGACY_SEAM_STATUS"
        in errors
    )


def test_legacy_growth_guard_cli_passes(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = legacy_guard.main(["--repo-root", str(REPO_ROOT)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "legacy compatibility seam guard passed" in captured.out
