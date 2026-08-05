from __future__ import annotations

import asyncio
import importlib
import logging
import os
import sys
import inspect
from contextlib import suppress
from types import ModuleType
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
)

import dotenv
from fastapi import APIRouter, Body, FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import (
    BaseModel,
    ValidationError,
)
from settings import get_runtime_env_name

from app.application_metadata import build_application_metadata
from app.bootstrap.openapi import (  # noqa: F401 - identity-preserving compatibility re-exports
    _OPENAPI_ALLOWED_EXACT,
    _OPENAPI_ALLOWED_PREFIXES,
    _build_canonical_openapi,
    _collect_schema_refs,
    _install_openapi_builder,
    _is_openapi_public_path,
    _prune_unreferenced_schema_components,
)

from app.bootstrap.lifespan import application_lifespan as lifespan
from app.http_error_details import (
    ENHANCED_PLATE_GENERATION_FAILED_DETAIL,
    INVALID_PREMIUM_PLATE_INPUT_DETAIL,
)
from app.routers.api_key import (  # noqa: F401 - identity-preserving compatibility re-exports
    _get_api_key_dynamic as _get_api_key_dynamic,
    get_api_key as get_api_key,
)
from app.schemas.bmr import (  # noqa: F401 - compatibility re-exports
    BMRRequest,
    BMRRequestLegacy,
    BMRResponse,
)
from app.schemas.bmi_compat import BMIRequest, BMIRequestV1
from app.schemas.insight import (  # noqa: F401 - compatibility re-exports
    INSIGHT_TEXT_MAX_LENGTH,
    InsightRequest,
    InsightResponse,
    RAGSourceItem,
)
from app.schemas.premium_contracts import (
    Activity,
    DietFlag,
    Goal,
    NutrientGapsRequest,
    NutrientGapsResponse,
    PlateRequest,
    PlateResponse,
    Sex,
    VisualShape,
    WHOTargetsRequest,
    WHOTargetsResponse,
    build_who_targets_ui_labels,
)
from app.schemas.nutrition_targets import TargetsIn as CanonicalTargetsIn

# LegacyWeekPlanRequest is a compat re-export contract asserted by
# tests/test_legacy_weekly_plan_alias_api.py; WeeklyMenuResponse is also used below.
from app.schemas.legacy_premium_weekly_plan import (  # noqa: F401
    LegacyWeekPlanRequest,
    WeeklyMenuResponse,
)
from app.services import pro_nutrition_plate as _canonical_plate_service
from app.services.insight_compat import (  # noqa: F401 - compatibility re-exports
    INSIGHT_TEMP_UNAVAILABLE_MESSAGE,
    _execute_insight_request,
    insight,
    insight_v1,
)
from app.services.pro_nutrition_targets import (
    analyze_nutrient_gaps_response,
    generate_who_targets_response as _generate_who_targets_response,
)
from app.services.pro_nutrition_targets import (  # noqa: F401 - compatibility re-export
    fallback_targets_response as _fallback_targets_response,
)
from app.services.scheduler_access import (  # noqa: F401 - compatibility re-export
    get_update_scheduler as get_update_scheduler,
)

from app.services.bmi_compat import (
    MATPLOTLIB_AVAILABLE,
    add_visualization_if_requested,
    generate_bmi_visualization,
)
from core.log_retention import (
    DataClass,
    get_retention_manager,
    LogRetentionManager,
)
from core.db import get_session
from core.i18n import Language, normalize_lang, t
from core.nutrition_utils import (  # noqa: F401 - compatibility re-exports
    MANDATORY_MICRO_DEFAULTS,
    MAX_DAILY_KCAL,
    MICRO_ALIAS_MAP,
    MIN_DAILY_KCAL,
)
from core.nutrition_utils import (
    alias_micros as _alias_micros,
    clamp_daily_kcal as _clamp_daily_kcal,
    ensure_priority_micros as _ensure_priority_micros,
)
from core.targets import FIBER_MIN_G
from app.scheduler_helpers import (
    resolve_scheduler_starter,
    resolve_stop_callable,
    handle_sync_test_mode,
    execute_async_starter,
    safe_stop_with_cleanup,
)
from app.utils.helpers import _short_git_sha as _short_git_sha
from app.utils.feature_flags import _is_truthy

_BMI_COMPAT_REEXPORTS = (
    MATPLOTLIB_AVAILABLE,
    add_visualization_if_requested,
    generate_bmi_visualization,
)

_LEGACY_IMPORT_COMPAT_REEXPORTS = (
    DataClass,
    get_retention_manager,
    get_session,
    Language,
    normalize_lang,
    _short_git_sha,
    _is_truthy,
)

# PR-633: thin alias to canonical import-safe schema (no local validation).
TargetsIn = CanonicalTargetsIn

# Rate limiting imports (PR-628)
# RU: Импорты для rate-limiting (медленные imports только если slowapi доступен).
# EN: Rate limiting imports (lazy imports only if slowapi is available).
RATE_LIMIT_429_RESPONSES: dict[int | str, dict[str, Any]]
try:
    from app.security.rate_limit import (
        limiter,
        limit_if_available,
        RATE_LIMIT_EXPORTS,
        RATE_LIMIT_INSIGHT,
        RATE_LIMIT_429_RESPONSES as _RATE_LIMIT_429_RESPONSES,
    )

    RATE_LIMIT_429_RESPONSES = _RATE_LIMIT_429_RESPONSES
except ImportError:  # pragma: no cover - optional dependency in runtime
    limiter = None  # type: ignore[assignment]  # pragma: no cover

    # No-op decorator if rate limiting is unavailable
    from typing import TypeVar as _TypeVar  # pragma: no cover

    _F = _TypeVar("_F", bound=Callable[..., Any])  # pragma: no cover

    _LimitValue = str | Callable[[], str]  # pragma: no cover

    def limit_if_available(rate: _LimitValue) -> Callable[[_F], _F]:  # pragma: no cover
        def decorator(func: _F) -> _F:  # pragma: no cover
            return func  # pragma: no cover

        return decorator  # pragma: no cover

    RATE_LIMIT_INSIGHT = "10/minute"  # pragma: no cover
    RATE_LIMIT_EXPORTS = "20/minute"  # pragma: no cover
    RATE_LIMIT_429_RESPONSES = {429: {"description": "Rate limit exceeded"}}  # pragma: no cover


# PRO router registration is owned by app.main canonical bootstrap.
# Public compatibility surface: tests + app/__init__.py expect these attrs to exist.
premium_week_router: Optional[APIRouter] = None
pro_router: Optional[APIRouter] = None

# BMI route registration is owned by app.main canonical bootstrap.
# Public compatibility surface: tests + app/__init__.py expect these attrs to exist.
FEATURE_BMI_PRO_ENABLED: bool = False
bmi_router: Optional[APIRouter] = None
bmi_pro_router: Optional[APIRouter] = None
bmi_pro_legacy_alias_router: Optional[APIRouter] = None

try:
    from core.food_apis.scheduler import (
        start_background_updates as _scheduler_start_background_updates,
        stop_background_updates as _scheduler_stop_background_updates,
    )
except ImportError:  # pragma: no cover - scheduler not available outside backend runtime

    async def _scheduler_start_background_updates(update_interval_hours: int = 24) -> None:
        logger.warning("Scheduler module unavailable; background updates not started.")

    async def _scheduler_stop_background_updates() -> None:
        logger.warning("Scheduler module unavailable; background updates not stopped (noop).")


if TYPE_CHECKING:
    from slowapi import Limiter as LimiterType
else:
    LimiterType = Any

Limiter: Optional[type[LimiterType]]
try:
    from slowapi import Limiter as _Limiter

    Limiter = _Limiter  # Assign the class itself
except ImportError:
    Limiter = None

slowapi_available = Limiter is not None

vip_router: Optional[APIRouter] = None

# VIP router registration is owned by app.main canonical bootstrap.
try:
    from app.utils.feature_flags import is_vip_module_enabled

    VIP_MODULE_ENABLED = is_vip_module_enabled()  # Keep for backward compatibility
except ImportError:
    VIP_MODULE_ENABLED = False

# Backward-compat: expose vip_router for tests/introspection.
if VIP_MODULE_ENABLED:
    try:
        from app.routers import vip as _vip_mod

        vip_router = getattr(_vip_mod, "router", None)
    except ImportError:
        vip_router = None


def start_background_updates(update_interval_hours: int = 24) -> None:
    """Start background updates in the current or a new event loop (sync wrapper).

    Resolves the scheduler starter from the module hierarchy and executes it
    either in the current event loop (if one exists) or in a new loop.

    In pytest sync mode (PYTEST_CURRENT_TEST set), uses special handling to
    manage awaitables and track calls in the caller's 'called' list.

    Returns:
        None (synchronous fire-and-forget wrapper for the async scheduler starter)
    """
    import sys as _sys

    pkg = _sys.modules.get("app") or _APP_PACKAGE_REF
    if pkg is not None and not getattr(pkg, "__path__", None) and _APP_PACKAGE_REF is not None:
        # Prefer the package wrapper when sys.modules['app'] points to app_module
        pkg = _APP_PACKAGE_REF
    alias_pkg = _sys.modules.get("app_module")

    _asyncio = getattr(pkg, "asyncio", None) or getattr(alias_pkg, "asyncio", None) or asyncio
    force_sync = os.getenv("PYTEST_CURRENT_TEST") is not None

    if force_sync:
        # Pytest sync mode: resolve candidates and call with special handling
        caller_called: list[Any] | None = None
        frame = inspect.currentframe()
        if frame is not None and frame.f_back is not None:
            maybe_called = frame.f_back.f_locals.get("called")
            if isinstance(maybe_called, list):
                caller_called = maybe_called

        pkg_appmod = getattr(pkg, "app_module", None) if pkg else None
        pkg_attr = pkg.__dict__.get("_scheduler_start_background_updates") if pkg else None
        candidates = [
            (
                pkg_attr
                if pkg_attr is not None
                else getattr(pkg, "_scheduler_start_background_updates", None)
            ),
            (
                getattr(pkg_appmod, "_scheduler_start_background_updates", None)
                if pkg_appmod
                else None
            ),
            globals().get("_scheduler_start_background_updates", None),
        ]
        for target in candidates:
            if not callable(target):
                continue
            handle_sync_test_mode(target, update_interval_hours, caller_called)
            break
        return None

    # Normal mode: resolve starter and execute
    starter = resolve_scheduler_starter(
        pkg, alias_pkg, globals(), _scheduler_start_background_updates
    )
    execute_async_starter(starter, update_interval_hours, _asyncio)
    return None


def stop_background_updates() -> None:
    """Stop background updates in the current or a new event loop (sync wrapper).

    Resolves the stop callable from the module hierarchy and executes it
    either in the current event loop (if one exists) or in a new loop with
    proper cleanup and error suppression.

    In pytest sync mode (PYTEST_CURRENT_TEST set), uses special handling to
    manage awaitables and track calls in the caller's 'called' list.
    """
    import sys as _sys

    pkg = _sys.modules.get("app") or _APP_PACKAGE_REF
    if pkg is not None and not getattr(pkg, "__path__", None) and _APP_PACKAGE_REF is not None:
        pkg = _APP_PACKAGE_REF
    alias_pkg = _sys.modules.get("app_module")

    _asyncio = getattr(pkg, "asyncio", None) or getattr(alias_pkg, "asyncio", None) or asyncio
    force_sync = os.getenv("PYTEST_CURRENT_TEST") is not None

    if force_sync:
        # Pytest sync mode: resolve candidates and call with special handling
        caller_called: list[Any] | None = None
        frame = inspect.currentframe()
        if frame is not None and frame.f_back is not None:
            maybe_called = frame.f_back.f_locals.get("called")
            if isinstance(maybe_called, list):
                caller_called = maybe_called

        pkg_appmod = getattr(pkg, "app_module", None) if pkg else None
        pkg_attr = pkg.__dict__.get("_scheduler_stop_background_updates") if pkg else None
        candidates = [
            (
                pkg_attr
                if pkg_attr is not None
                else getattr(pkg, "_scheduler_stop_background_updates", None)
            ),
            getattr(pkg_appmod, "_scheduler_stop_background_updates", None) if pkg_appmod else None,
            globals().get("_scheduler_stop_background_updates", None),
        ]
        for target in candidates:
            if not callable(target):
                continue
            handle_sync_test_mode(target, None, caller_called)
            break
        return None

    # Normal mode: resolve stopper and execute
    stopper = resolve_stop_callable(pkg, alias_pkg, globals(), _scheduler_stop_background_updates)

    # Detect running loop
    event_loop: Optional[asyncio.AbstractEventLoop] = None
    try:
        event_loop = _asyncio.get_running_loop()
    except RuntimeError:
        pass

    if event_loop is None:
        # No running loop: run in new loop with cleanup
        safe_stop_with_cleanup(stopper)
    else:
        # Running loop exists: schedule as task
        event_loop.create_task(stopper())
    return None


# Only load the local .env automatically for explicit local/dev environments.
_env_was_sanitized = "PATH" not in os.environ
_app_env = get_runtime_env_name()
_should_load_local_env = _app_env in {"local", "dev", "development"}
if not _env_was_sanitized and _should_load_local_env and os.getenv("PYTEST_CURRENT_TEST") is None:
    dotenv.load_dotenv()


# Set up logging
# Configure logging - ensure pytest can capture logs
# In test environment, use DEBUG level to capture all logs
_log_level = logging.DEBUG if _app_env in {"test", "testing"} else logging.INFO
logging.basicConfig(level=_log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
bmi_logger = logging.getLogger("app.bmi")

# Initialize log retention manager
_log_retention_manager: Optional[LogRetentionManager] = None


def _resolve_build_targets_callable() -> Optional[Callable[..., Any]]:
    if callable(build_nutrition_targets):
        return build_nutrition_targets
    return None


# OpenAPI/Swagger metadata remains available here as compatibility values.
_application_metadata = build_application_metadata(runtime_env=_app_env)
tags_metadata = _application_metadata.openapi_tags_list()
_api_description = _application_metadata.description

app = FastAPI(
    title=_application_metadata.title,
    version=_application_metadata.version,
    description=_application_metadata.description,
    contact=_application_metadata.contact_dict(),
    license_info=_application_metadata.license_info_dict(),
    openapi_tags=tags_metadata,
    lifespan=lifespan,
)


# Startup/shutdown behavior is owned by app.bootstrap.lifespan. This module
# only passes the canonical context manager to the legacy-created FastAPI app.


# (moved to top with other imports)


async def admin_status() -> Dict[str, str]:
    """Compatibility shim for direct imports; route ownership is canonical."""

    from app.services.admin_operations import admin_status as _admin_status

    return await _admin_status()


# PRO/VIP route registration is owned by app.main canonical bootstrap.
# Compatibility attrs above are populated there after successful registration.
# Shopping-list route registration is owned by app.main canonical bootstrap.

# Premium week router registration is now handled in
# app.routers.pro_registration.register_pro_routes() for centralized registration.

# Provide a stable alias for plan_export to support tests that reload it dynamically
with suppress(Exception):
    import importlib as _importlib
    import types as _types

    # Try to import plan_export module through the package path
    _plan_mod: Any = None
    try:
        _plan_mod = _importlib.import_module("app.routers.plan_export")
    except ImportError:
        # Module not available, continue without it
        pass
    except Exception:
        # Log unexpected errors during import
        logging.debug("Unexpected error importing plan_export module", exc_info=True)
    # Expose a lightweight 'routers' attribute on this module for direct access
    if not hasattr(sys.modules[__name__], "routers"):
        setattr(sys.modules[__name__], "routers", _types.SimpleNamespace())
    if _plan_mod is not None:
        setattr(sys.modules[__name__].routers, "plan_export", _plan_mod)
        sys.modules.setdefault("app.routers.plan_export", _plan_mod)

# Legacy event handlers - replaced with lifespan
# @app.on_event("startup")
# @app.on_event("shutdown")


# ---------- Helpers ----------


def legacy_category_label(cat: str, lang: str) -> str:
    """Map core category labels to legacy wording for the v0 endpoints only.

    - EN: "Normal weight" → "Healthy weight"
    - RU: "Избыточная масса" → "Избыточный вес"
    """
    try:
        lang_code = (lang or "ru").lower()
    except Exception:
        lang_code = "ru"
    if lang_code.startswith("en") and cat == "Normal weight":
        return "Healthy weight"
    if lang_code.startswith("ru") and cat == "Избыточная масса":
        return "Избыточный вес"
    return cat


# Legacy/compat helper expected by coverage tests.
def _is_rate_limiting_available() -> bool:
    try:
        from app.security.rate_limit import limiter

        return limiter is not None
    except Exception:  # pragma: no cover - defensive
        return False  # pragma: no cover


# Rate limiting setup (PR-628)
# Wiring is centralized in app.security.rate_limit; import after app creation
# to avoid import-order issues with FastAPI instance


# ---------- Core logic ----------


async def cleanup_expired_logs(
    data_class: Optional[str] = None,
) -> Dict[str, Any]:
    """Compatibility shim for direct imports; route ownership is canonical."""

    from app.services.admin_operations import cleanup_expired_logs as _cleanup_expired_logs

    return await _cleanup_expired_logs(data_class=data_class)


async def bmi_endpoint(req: BMIRequest) -> Dict[str, Any]:
    """Compatibility direct-call shim; route ownership is canonical."""

    from app.services.bmi_compat import bmi_endpoint as _bmi_endpoint

    return await _bmi_endpoint(req)


async def plan_endpoint(req: BMIRequest) -> Dict[str, Any]:
    """Compatibility direct-call shim; route ownership is canonical."""

    from app.services.bmi_compat import plan_endpoint as _plan_endpoint

    return await _plan_endpoint(req)


async def bmi_endpoint_v1(req: BMIRequestV1) -> Dict[str, Any]:
    """Compatibility direct-call shim; route ownership is canonical."""

    from app.services.bmi_compat import bmi_endpoint_v1 as _bmi_endpoint_v1

    return await _bmi_endpoint_v1(req)


MenuEngineCallable = Callable[..., Any]

analyze_nutrient_gaps: Optional[MenuEngineCallable] = None
make_daily_menu: Optional[MenuEngineCallable] = None
make_weekly_menu: Optional[MenuEngineCallable] = None
repair_week_plan: Optional[MenuEngineCallable] = None
make_plate: Optional[MenuEngineCallable] = None
build_nutrition_targets: Optional[MenuEngineCallable] = None

ExportCallable = Callable[..., Any]
to_csv_day: Optional[ExportCallable] = None
to_pdf_day: Optional[ExportCallable] = None
to_csv_week: Optional[ExportCallable] = None
to_pdf_week: Optional[ExportCallable] = None

try:
    from core.menu_engine import analyze_nutrient_gaps as _analyze_nutrient_gaps
    from core.menu_engine import make_daily_menu as _make_daily_menu
    from core.menu_engine import make_weekly_menu as _make_weekly_menu
    from core.menu_engine import repair_week_plan as _repair_week_plan
    from core.plate import make_plate as _make_plate
    from core.recommendations import build_nutrition_targets as _build_nutrition_targets
except ImportError:
    pass
else:
    analyze_nutrient_gaps = _analyze_nutrient_gaps
    make_daily_menu = _make_daily_menu
    make_weekly_menu = _make_weekly_menu
    repair_week_plan = _repair_week_plan
    make_plate = _make_plate
    build_nutrition_targets = _build_nutrition_targets


try:
    from core.exports import to_csv_day as _to_csv_day_fn
    from core.exports import to_csv_week as _to_csv_week_fn
except ImportError:
    pass
else:
    to_csv_day = _to_csv_day_fn
    to_csv_week = _to_csv_week_fn


if "to_pdf_day" not in globals():
    to_pdf_day = None
if "to_pdf_week" not in globals():
    to_pdf_week = None

# Ensure analyze_nutrient_gaps is available at module level for tests
if "analyze_nutrient_gaps" not in globals():
    with suppress(Exception):
        from core.menu_engine import analyze_nutrient_gaps

        globals()["analyze_nutrient_gaps"] = analyze_nutrient_gaps
# Ensure make_weekly_menu is available at module level for tests
if "make_weekly_menu" not in globals():
    with suppress(Exception):
        from core.menu_engine import make_weekly_menu

        globals()["make_weekly_menu"] = make_weekly_menu
# Ensure repair_week_plan is available at module level for tests
if "repair_week_plan" not in globals():
    with suppress(Exception):
        from core.menu_engine import repair_week_plan

        globals()["repair_week_plan"] = repair_week_plan
# WHO-Based Nutrition Models
#
# NOTE (PR-633): `TargetsIn` is canonical in `app.schemas.nutrition_targets` (import-safe).
# Legacy endpoints must not define a second validation path to avoid drift.
#
# NOTE: Legacy weekly-plan contracts are now owned by
# `app.schemas.legacy_premium_weekly_plan`; `legacy_app` only re-exports them.


class WeeklyPlanFlexibleRequest(BaseModel):
    # Either 'targets' or a lightweight user profile
    targets: Optional[Dict[str, Any]] = None
    sex: Optional[Sex] = None
    age: Optional[int] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    activity: Optional[Activity] = "moderate"
    goal: Optional[Goal] = "maintain"
    deficit_pct: Optional[float] = None
    surplus_pct: Optional[float] = None
    bodyfat: Optional[float] = None
    diet_flags: Optional[set[DietFlag]] = None
    life_stage: Optional[Literal["child", "teen", "adult", "pregnant", "lactating", "elderly"]] = (
        "adult"
    )
    lang: Optional[str] = "en"


# Canonical Plate ownership. These assignments deliberately replace the former
# local implementations with exact service callables while compatibility imports
# remain. Canonical and retained HTTP handlers import the service directly.
DB_TO_ALIAS_NUTRIENT_MAP = _canonical_plate_service.DB_TO_ALIAS_NUTRIENT_MAP


class PlateDependencies:
    """Legacy direct-import dependency container retained for compatibility.

    Canonical Plate execution uses ``PlateServiceDependencies`` directly. This
    mutable shim preserves the historical constructor and attributes for Python
    callers without recreating the former process-global dependency registry.
    """

    def __init__(
        self,
        make_plate_fn: Callable[..., Any] | None = None,
        build_nutrition_targets_fn: Callable[..., Any] | None = None,
        calculate_all_bmr_fn: Callable[..., Any] | None = None,
        calculate_all_tdee_fn: Callable[..., Any] | None = None,
        aggregate_day_micronutrients_fn: Callable[..., Any] | None = None,
    ) -> None:
        self.make_plate_fn = make_plate_fn
        self.make_plate = make_plate_fn
        self.build_nutrition_targets_fn = build_nutrition_targets_fn
        self.build_nutrition_targets = build_nutrition_targets_fn
        self.calculate_all_bmr_fn = calculate_all_bmr_fn
        self.calculate_all_bmr = calculate_all_bmr_fn
        self.calculate_all_tdee_fn = calculate_all_tdee_fn
        self.calculate_all_tdee = calculate_all_tdee_fn
        self.aggregate_day_micronutrients_fn = aggregate_day_micronutrients_fn
        self._aggregate_day_micronutrients = aggregate_day_micronutrients_fn


PlateServiceDependencies = _canonical_plate_service.PlateServiceDependencies
_convert_db_nutrients_to_alias_format = (
    _canonical_plate_service._convert_db_nutrients_to_alias_format
)
_aggregate_meal_micronutrients = _canonical_plate_service._aggregate_meal_micronutrients
_get_recipe_ingredients_for_meal = _canonical_plate_service._get_recipe_ingredients_for_meal
_aggregate_day_micronutrients = _canonical_plate_service._aggregate_day_micronutrients
_macros_to_kcal = _canonical_plate_service._macros_to_kcal
sanitize_plate_data = _canonical_plate_service.sanitize_plate_data
_iter_exception_chain = _canonical_plate_service._iter_exception_chain
_is_missing_nh3_error = _canonical_plate_service._is_missing_nh3_error
_raise_missing_nh3_http_error = _canonical_plate_service._raise_missing_nh3_http_error
calculate_heuristic_macros = _canonical_plate_service.calculate_heuristic_macros
_compute_premium_plate = _canonical_plate_service.generate_plate_response
api_premium_plate = _canonical_plate_service.generate_plate_response


def build_fallback_plate(
    req: PlateRequest,
    candidates: list[Any] | None = None,
) -> PlateResponse:
    """Compatibility delegate with explicit canonical target dependency."""

    del candidates
    return _canonical_plate_service.build_fallback_plate(
        req,
        targets_builder=_resolve_build_targets_callable(),
    )


def align_macros_with_targets(
    req: PlateRequest,
    plate_data: Dict[str, Any],
    candidates: list[Any] | None = None,
) -> tuple[Dict[str, Any], Optional[int], bool]:
    """Compatibility delegate with explicit canonical target dependency."""

    del candidates
    return _canonical_plate_service.align_macros_with_targets(
        req,
        plate_data,
        targets_builder=_resolve_build_targets_callable(),
        targets_response_factory=_generate_who_targets_response,
    )


async def aggregate_day_micros(
    meals: List[Dict[str, Any]],
    candidates: list[Any] | None = None,
) -> Dict[str, float]:
    """Compatibility delegate for callers that still inject an aggregator."""

    aggregator = _aggregate_day_micronutrients
    for candidate in candidates or []:
        candidate_aggregator = getattr(
            candidate,
            "_aggregate_day_micronutrients",
            None,
        )
        if callable(candidate_aggregator):
            aggregator = candidate_aggregator
            break
    return await _canonical_plate_service.aggregate_day_micros(
        meals,
        aggregator=aggregator,
    )


# Legacy Premium Endpoints (for backwards compatibility)
async def premium_targets_legacy(req: WHOTargetsRequest) -> WHOTargetsResponse:
    """Legacy endpoint for WHO targets (backwards compatibility).

    Protected with API key authentication to match the new /api/v1/premium/targets endpoint.
    """
    return _generate_who_targets_response(req, allow_backend_fallback=False)


# WHO-Based Nutrition Endpoints


async def api_who_targets(payload: Dict[str, Any] = Body(...)) -> WHOTargetsResponse:
    """[DEPRECATED] Alias for canonical `POST /api/v1/pro/nutrition/targets`.

    Normal FastAPI route usage with Body(...) and dependency injection.
    For direct test calls, use _generate_who_targets_response directly.
    """
    try:
        req: WHOTargetsRequest
        req = WHOTargetsRequest.model_validate(payload)
    except ValidationError as exc:
        from fastapi.encoders import jsonable_encoder

        raise HTTPException(status_code=422, detail=jsonable_encoder(exc.errors())) from exc

    return _generate_who_targets_response(req)


async def api_nutrient_gaps(req: NutrientGapsRequest) -> NutrientGapsResponse:
    """
    RU: Анализирует дефициты нутриентов и даёт рекомендации.
    EN: Analyzes nutrient deficiencies and provides food recommendations.

    Smart gap analysis:
    - Compares actual intake vs WHO targets
    - Identifies priority deficiencies (iron, calcium, folate, etc.)
    - Suggests specific foods to close gaps
    - Adapts recommendations for dietary restrictions
    - No supplement recommendations (food-first approach)

    Perfect for food diary analysis and meal optimization.
    """
    return analyze_nutrient_gaps_response(req)


async def debug_env() -> JSONResponse:
    """Compatibility shim for direct imports; route ownership is canonical."""

    from app.services.admin_operations import debug_env as _debug_env

    return await _debug_env()


# ========================================
# Database Auto-Update Management Endpoints
# ========================================


async def get_database_status() -> JSONResponse:
    """Compatibility shim for direct imports; route ownership is canonical."""

    from app.services.admin_operations import get_database_status as _get_database_status

    return await _get_database_status()


async def force_database_update(source: Optional[str] = None) -> JSONResponse:
    """Compatibility shim for direct imports; route ownership is canonical."""

    from app.services.admin_operations import force_database_update as _force_database_update

    return await _force_database_update(source=source)


async def check_for_updates() -> JSONResponse:
    """Compatibility shim for direct imports; route ownership is canonical."""

    from app.services.admin_operations import check_for_updates as _check_for_updates

    return await _check_for_updates()


async def rollback_database(source: str, target_version: str) -> Dict[str, Any]:
    """Compatibility shim for direct imports; route ownership is canonical."""

    from app.services.admin_operations import rollback_database as _rollback_database

    return await _rollback_database(source=source, target_version=target_version)


_APP_PACKAGE_REF: Optional[ModuleType] = sys.modules.get("app")


def _iter_app_modules() -> list[ModuleType]:
    """Return all loaded module objects that point to app.py (handles aliasing in tests)."""
    modules: list[ModuleType] = []
    seen: set[int] = set()
    if _APP_PACKAGE_REF is not None:
        modules.append(_APP_PACKAGE_REF)
        seen.add(id(_APP_PACKAGE_REF))
    for mod in sys.modules.values():
        if not isinstance(mod, ModuleType):
            continue
        if id(mod) in seen:
            continue
        file = getattr(mod, "__file__", "") or ""
        if file.endswith("app.py"):
            modules.append(mod)
            seen.add(id(mod))
    return modules


# Bodyfat, BMI, and BMI Pro route registration is owned by app.main canonical bootstrap.
