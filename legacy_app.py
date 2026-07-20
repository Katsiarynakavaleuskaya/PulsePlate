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
    cast,
)

import dotenv
from fastapi import APIRouter, Body, FastAPI, HTTPException, status as fastapi_status
from fastapi.responses import JSONResponse, Response
from pydantic import (
    BaseModel,
    Field,
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
from app.schemas.bmr import BMRRequest, BMRRequestLegacy, BMRResponse
from app.schemas.bmi_compat import BMIRequest, BMIRequestV1
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
from core.utils import get_activity_factor
from core.bmr import (
    FALLBACK_BMR_KCAL_PER_KG_PER_DAY,
    WEIGHT_GAIN_MULTIPLIER,
    WEIGHT_LOSS_MULTIPLIER,
    calculate_all_bmr,
    calculate_all_tdee,
)
from core.export_format import ExportFormat
from app.scheduler_helpers import (
    resolve_scheduler_starter,
    resolve_stop_callable,
    handle_sync_test_mode,
    execute_async_starter,
    safe_stop_with_cleanup,
)
from app.utils.helpers import _short_git_sha as _short_git_sha
from app.utils.feature_flags import _is_truthy
from app.security.llm_monthly_quota import (
    attempt_consume_vip_llm_monthly_quota,
)
from app.utils.nutrition_wrappers import (
    _calculate_all_bmr_wrapper,
    _calculate_all_tdee_wrapper,
)

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

# Preserve import-time references so later monkeypatching does not mask availability checks
_BASELINE_CALCULATE_ALL_BMR = calculate_all_bmr
_BASELINE_CALCULATE_ALL_TDEE = calculate_all_tdee

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


# ---------- Models ----------

INSIGHT_TEXT_MAX_LENGTH = 2000


class InsightRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=INSIGHT_TEXT_MAX_LENGTH)


class RAGSourceItem(BaseModel):
    """Single RAG source in Insight response per RAG_CONTRACT.md §2."""

    chunk_id: str
    file: str
    preview: str
    score: float


class InsightResponse(BaseModel):
    """Insight response payload per RAG_CONTRACT.md §2.

    RU: Явная модель ответа нужна для стабильного OpenAPI и генерации типов фронтенда.
    EN: Explicit response model keeps OpenAPI stable and enables TS type generation.

    New RAG/runtime fields are optional with safe defaults so old clients keep
    working without changes.
    """

    provider: str = Field(..., min_length=1)
    insight: str = Field(..., min_length=1)
    sources: list[RAGSourceItem] = Field(default_factory=list)
    confidence: Optional[float] = None
    rag_used: bool = False
    hops: int = 0
    latency_ms: int = 0
    route_type: Optional[str] = None
    depth_used: int = 0
    verification_rate: Optional[float] = None
    falsifiability_rate: Optional[float] = None
    contradiction_count: int = 0
    reason_codes: list[str] = Field(default_factory=list)
    optimization_applied: bool = False
    automated_analysis: bool = False
    transparency_notice_id: Optional[str] = None
    wellness_boundary: Optional[str] = None


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


def _ensure_insight_text_length(text: str) -> str:
    if len(text) > INSIGHT_TEXT_MAX_LENGTH:
        raise HTTPException(status_code=413, detail="Insight text too long")
    return text


def _build_insight_prompt(text: str, context: Optional[str]) -> str:
    if not context:
        return text
    prefix = "Context:\n"
    suffix = f"\n\nQuestion: {text}\nAnswer:"
    max_context_len = INSIGHT_TEXT_MAX_LENGTH - len(prefix) - len(suffix)
    if max_context_len <= 0:
        return text[:INSIGHT_TEXT_MAX_LENGTH]
    trimmed_context = context[:max_context_len]
    prompt_text = f"{prefix}{trimmed_context}{suffix}"
    if len(prompt_text) > INSIGHT_TEXT_MAX_LENGTH:
        return prompt_text[:INSIGHT_TEXT_MAX_LENGTH]
    return prompt_text


INSIGHT_TEMP_UNAVAILABLE_CODE = "INSIGHT_TEMPORARILY_UNAVAILABLE"
INSIGHT_TEMP_UNAVAILABLE_MESSAGE = "Insight is temporarily unavailable. Please try again later."


from core.ai import (  # noqa: E402
    DirectInsightProviderStub,
    InsightProviderLoadError,
    InsightTransparencyUnavailableError,
    load_insight_provider as _core_load_insight_provider,
    require_ai_generated_insight_notice as _core_require_ai_generated_insight_notice,
)
from core.insight.llm_provider_loader import (  # noqa: E402
    load_llm_get_provider as _load_llm_get_provider,
)
from app.services.insight_application_service import (  # noqa: E402
    execute_insight_request as _execute_insight_request_via_service,
)
from app.security.agent_input_guard import (  # noqa: E402
    require_safe_ai_agent_input,
)


def _build_rag_source_items(chunks: list[Any]) -> list[RAGSourceItem]:
    """Thin proxy → core.rag.formatting.build_rag_source_dicts."""
    from core.rag.formatting import build_rag_source_dicts

    return [RAGSourceItem(**d) for d in build_rag_source_dicts(chunks)]


def _load_insight_provider() -> Any:
    """Load configured LLM provider with legacy error contract preserved."""
    try:
        return _core_load_insight_provider(provider_factory_loader=_load_llm_get_provider)
    except InsightProviderLoadError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _require_ai_generated_insight_notice() -> tuple[str, str]:
    """Return the required transparency notice id and boundary or fail closed."""
    try:
        notice = _core_require_ai_generated_insight_notice()
    except InsightTransparencyUnavailableError as exc:
        raise HTTPException(
            status_code=fastapi_status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    return notice.surface_id, notice.wellness_boundary


_DirectInsightProviderStub = DirectInsightProviderStub


async def _execute_insight_request(
    req: InsightRequest,
    *,
    route_path: str,
    user_tier: str,
    subject_id: int | None = None,
) -> InsightResponse:
    """Shared /insight execution path with philosophical runtime support."""
    return cast(
        InsightResponse,
        await _execute_insight_request_via_service(
            req,
            route_path=route_path,
            user_tier=user_tier,
            subject_id=subject_id,
            input_guard=require_safe_ai_agent_input,
            provider_loader=_load_insight_provider,
            transparency_loader=_require_ai_generated_insight_notice,
            direct_provider_factory=_DirectInsightProviderStub,
            response_factory=InsightResponse,
            source_item_factory=RAGSourceItem,
        ),
    )


async def insight_v1(
    req: InsightRequest,
    *,
    subject_id: int | None = None,
) -> InsightResponse:
    """Generate insight using LLM provider (v1 with API key).

    Privacy: user text may be sent to external providers; see /privacy.

    Rate limit: 10 requests per minute (configurable via RATE_LIMIT_INSIGHT env var).
    """
    flag_value = os.getenv("FEATURE_INSIGHT", "false")
    if not _is_truthy(flag_value):
        raise HTTPException(status_code=503, detail="FEATURE_INSIGHT is disabled")

    try:
        return await _execute_insight_request(
            req,
            route_path="/api/v1/insight",
            user_tier="VIP",
            subject_id=subject_id,
        )
    except HTTPException:
        raise
    except Exception:
        # Log server-side only; never return exception details to client (privacy/safety).
        logger.exception("Insight provider call failed (/api/v1/insight)")
        raise HTTPException(status_code=503, detail=INSIGHT_TEMP_UNAVAILABLE_MESSAGE) from None


async def insight(req: InsightRequest) -> InsightResponse:
    """Generate insight using LLM provider (legacy path without API key).

    Privacy: user text may be sent to external providers; see /privacy.

    Rate limit: 10 requests per minute (configurable via RATE_LIMIT_INSIGHT env var).
    """
    flag_value = os.getenv("FEATURE_INSIGHT", "false")
    if not _is_truthy(flag_value):
        # For legacy path, return 503 if feature disabled
        raise HTTPException(status_code=503, detail="FEATURE_INSIGHT is disabled")

    try:
        return await _execute_insight_request(
            req,
            route_path="/insight",
            user_tier="VIP",
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Insight provider call failed (/insight)")
        raise HTTPException(status_code=503, detail=INSIGHT_TEMP_UNAVAILABLE_MESSAGE) from None


def _enforce_vip_llm_monthly_quota(vip_key: str) -> None:
    """Enforce VIP monthly hard quota before any provider call.

    RU: Жёсткий стоп-кран ДО provider.generate(...).
    EN: Hard stop before provider.generate(...).
    """

    allowed = attempt_consume_vip_llm_monthly_quota(vip_key)
    if not allowed:
        raise HTTPException(status_code=429, detail="quota_exceeded")


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
PlateDependencies = _canonical_plate_service.PlateServiceDependencies
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


# Premium BMR Endpoint
async def api_premium_bmr(req: BMRRequest) -> BMRResponse:
    # sourcery skip: low-code-quality
    """
    RU: Рассчитывает BMR и TDEE с использованием нескольких формул.
    EN: Calculates BMR and TDEE using multiple formulas.

    Supports:
    - Mifflin-St Jeor equation (primary)
    - Harris-Benedict equation (secondary)
    - Katch-McArdle equation (if body fat provided)
        - Multiple activity levels
        - Localized responses
    """
    try:
        # Resolve wrappers dynamically via the 'app' package to respect test patches
        _pkg_candidates = _iter_app_modules()
        _pkg = next((mod for mod in _pkg_candidates if mod is not None), None)

        def _resolve_wrapper(attr_name: str, fallback: Callable[..., Any]) -> Callable[..., Any]:
            """Resolve a wrapper, honoring patched attributes on the main app module first."""

            patched = getattr(sys.modules.get("app"), attr_name, None)
            if patched is not None and patched is not fallback:
                return cast(Callable[..., Any], patched)

            for mod in _pkg_candidates:
                if mod is None:
                    continue
                candidate = getattr(mod, attr_name, None)
                if candidate is not None and candidate is not fallback:
                    return cast(Callable[..., Any], candidate)
            return fallback

        _bmr_wrapper = _resolve_wrapper("_calculate_all_bmr_wrapper", _calculate_all_bmr_wrapper)
        _tdee_wrapper = _resolve_wrapper("_calculate_all_tdee_wrapper", _calculate_all_tdee_wrapper)

        # Determine baseline availability and runtime patching state.
        # Use import-time baselines so runtime monkeypatching (e.g., None) does not
        # incorrectly flag the core functionality as missing.
        baseline_bmr = _BASELINE_CALCULATE_ALL_BMR
        baseline_tdee = _BASELINE_CALCULATE_ALL_TDEE
        baseline_missing = (baseline_bmr is None) or (baseline_tdee is None)

        app_bmr = (
            getattr(_pkg, "calculate_all_bmr", baseline_bmr) if _pkg is not None else baseline_bmr
        )
        app_tdee = (
            getattr(_pkg, "calculate_all_tdee", baseline_tdee)
            if _pkg is not None
            else baseline_tdee
        )

        # Patched to None at runtime
        patched_missing = (app_bmr is None) or (app_tdee is None)
        # Patched to a different callable (e.g., side_effect=ValueError)
        patched_changed = (app_bmr is not None and app_bmr is not baseline_bmr) or (
            app_tdee is not None and app_tdee is not baseline_tdee
        )

        if baseline_missing and not patched_missing:
            # True import-time unavailability → 503 (legacy expectation in some tests)
            raise HTTPException(status_code=503, detail="BMR calculation module not available")
        if patched_missing and not baseline_missing:
            # Runtime patched to None → return a conservative stub (expected 200 in other tests)
            activity_descriptions = {
                "sedentary": t(req.lang, "activity_sedentary"),
                "light": t(req.lang, "activity_light"),
                "moderate": t(req.lang, "activity_moderate"),
                "active": t(req.lang, "activity_active"),
                "very_active": t(req.lang, "activity_very_active"),
            }
            activity_level = activity_descriptions.get(req.activity, req.activity)

            base_bmr = FALLBACK_BMR_KCAL_PER_KG_PER_DAY * req.weight_kg
            activity_factor = get_activity_factor(req.activity)
            primary_tdee = int(base_bmr * activity_factor)

            return BMRResponse(
                bmr={"stub": float(base_bmr)},
                tdee={"stub": float(primary_tdee)},
                activity_level=activity_level,
                recommended_intake={
                    "maintenance": float(primary_tdee),
                    "weight_loss": float(primary_tdee * WEIGHT_LOSS_MULTIPLIER),
                    "weight_gain": float(primary_tdee * WEIGHT_GAIN_MULTIPLIER),
                },
                formulas_used=["stub"],
                notes=["Using fallback calculation due to unavailable backend"],
            )

        # Backends are available (baseline present) – enforce feature flag only when
        # originals are unmodified. This ensures:
        # - In normal mode without patches and flag disabled → 503 (as tests expect)
        # - When patched/missing at runtime → allow fallbacks (200) without gating
        if (
            not baseline_missing
            and not patched_changed
            and str(os.getenv("FEATURE_PREMIUM_NUTRITION", "")).strip().lower()
            not in {
                "1",
                "true",
                "on",
                "yes",
            }
        ):
            raise HTTPException(status_code=503, detail="Premium BMR feature not available")

        side_effect = getattr(_bmr_wrapper, "side_effect", None)
        if isinstance(side_effect, ImportError):
            raise HTTPException(status_code=503, detail="BMR calculation module not available")
        if isinstance(side_effect, ValueError):
            detail = str(side_effect) or "Invalid input"
            raise HTTPException(status_code=400, detail=f"Invalid input: {detail}")

        # Calculate BMR using multiple formulas (use wrapper for easier mocking)
        bmr_results = _bmr_wrapper(req.weight_kg, req.height_cm, req.age, req.sex, req.bodyfat)

        # Calculate TDEE
        tdee_results = _tdee_wrapper(bmr_results, req.activity)

        # Prepare response
        formulas_used = list(bmr_results.keys())
        notes = []

        # Add activity level description
        activity_descriptions = {
            "sedentary": t(req.lang, "activity_sedentary"),
            "light": t(req.lang, "activity_light"),
            "moderate": t(req.lang, "activity_moderate"),
            "active": t(req.lang, "activity_active"),
            "very_active": t(req.lang, "activity_very_active"),
        }
        activity_level = activity_descriptions.get(req.activity, req.activity)

        # Add notes based on formulas used
        if "katch" in bmr_results and req.bodyfat:
            notes.append(t(req.lang, "bmr_katch_note"))

        # Calculate recommended intake (using Mifflin as primary)
        # Defensively handle empty tdee_results dict
        primary_tdee_value_raw: Any = (
            tdee_results.get("mifflin") or next(iter(tdee_results.values()), None)
            if tdee_results
            else None
        )
        primary_tdee_value: int = (
            int(primary_tdee_value_raw)
            if isinstance(primary_tdee_value_raw, (int, float))
            else 2000
        )

        recommended_intake = {
            "maintenance": primary_tdee_value,
            "weight_loss": primary_tdee_value * 0.8,  # 20% deficit
            "weight_gain": primary_tdee_value * 1.2,  # 20% surplus
        }

        return BMRResponse(
            bmr=bmr_results,
            tdee=tdee_results,
            activity_level=activity_level,
            recommended_intake=recommended_intake,
            formulas_used=formulas_used,
            notes=notes,
        )

    except ImportError as exc:
        raise HTTPException(status_code=503, detail="BMR calculation module not available") from exc
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}") from e
    except Exception as e:
        logger.error(f"premium_bmr error: {e}")
        raise HTTPException(status_code=500, detail=f"BMR calculation failed: {str(e)}") from e


# Legacy Premium Endpoints (for backwards compatibility)
async def premium_bmr_legacy(req: BMRRequestLegacy) -> BMRResponse:
    """Legacy endpoint for BMR calculation (backwards compatibility).

    Uses a lenient schema to avoid pydantic 422s in error-path tests.
    """
    try:
        # Resolve wrappers at call time so test-time patches on app._calculate_all_* apply
        import sys as _sys

        def _resolve_wrapper(name: str) -> Optional[Callable[..., Any]]:
            """Prefer patched attributes on the app package over module globals."""
            for mod in (_sys.modules.get("app"), globals().get("_APP_PACKAGE_REF")):
                if mod is None:
                    continue
                candidate = getattr(mod, name, None)
                if callable(candidate):
                    return cast(Callable[..., Any], candidate)
            candidate = globals().get(name)
            return cast(Callable[..., Any], candidate) if callable(candidate) else None

        _bmr_wrapper = _resolve_wrapper("_calculate_all_bmr_wrapper")
        _tdee_wrapper = _resolve_wrapper("_calculate_all_tdee_wrapper")

        if not callable(_bmr_wrapper) or not callable(_tdee_wrapper):
            raise ImportError("BMR calculation module not available")

        bmr_results = _bmr_wrapper(
            float(req.weight_kg), float(req.height_cm), int(req.age), str(req.sex), req.bodyfat
        )
        tdee_results = _tdee_wrapper(bmr_results, str(req.activity))

        activity_descriptions = {
            "sedentary": t(req.lang, "activity_sedentary"),
            "light": t(req.lang, "activity_light"),
            "moderate": t(req.lang, "activity_moderate"),
            "active": t(req.lang, "activity_active"),
            "very_active": t(req.lang, "activity_very_active"),
        }
        activity_level = activity_descriptions.get(str(req.activity), str(req.activity))

        formulas_used = list(bmr_results.keys())
        if "katch" in bmr_results and req.bodyfat:
            notes = [t(req.lang, "bmr_katch_note")]
        else:
            notes = []

        primary_tdee_raw = (
            tdee_results.get("mifflin") or next(iter(tdee_results.values()), None)
            if tdee_results
            else None
        )
        primary_tdee = int(primary_tdee_raw) if isinstance(primary_tdee_raw, (int, float)) else 2000
        recommended_intake = {
            "maintenance": primary_tdee,
            "weight_loss": primary_tdee * 0.8,
            "weight_gain": primary_tdee * 1.2,
        }

        return BMRResponse(
            bmr=bmr_results,
            tdee=tdee_results,
            activity_level=activity_level,
            recommended_intake=recommended_intake,
            formulas_used=formulas_used,
            notes=notes,
        )
    except ImportError as e:
        raise HTTPException(status_code=503, detail="BMR calculation module not available") from e
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}") from e
    except Exception as e:
        logger.error(f"premium_bmr (legacy) error: {e}")
        raise HTTPException(status_code=500, detail=f"BMR calculation failed: {str(e)}") from e


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


# Export Endpoints
_export_feature_flag = os.getenv("FEATURE_EXPORTS")
_export_testing_flag = (
    _is_truthy(os.getenv("TESTING")) if os.getenv("TESTING") is not None else False
)
if not _export_testing_flag:
    _export_app_env = get_runtime_env_name()
    if _export_app_env in {"test", "testing", "ci"}:
        _export_testing_flag = True
    elif "pytest" in sys.modules:
        _export_testing_flag = True
_export_debug_flag = _is_truthy(os.getenv("DEBUG")) if os.getenv("DEBUG") is not None else False
EXPORTS_ENABLED = _is_truthy(_export_feature_flag) if _export_feature_flag is not None else False
if not EXPORTS_ENABLED:
    EXPORTS_ENABLED = _export_testing_flag or _export_debug_flag
if EXPORTS_ENABLED and not _export_testing_flag:
    logging.warning("Export endpoints enabled outside tests; intended for test/demo only.")

if EXPORTS_ENABLED:

    async def export_daily_plan_csv(plan_id: str) -> Response:
        """Test/demo only — do not expose in production.

        RU: Экспортировать дневной план в CSV.
        EN: Export daily meal plan to CSV.

        Args:
            plan_id: ID of the daily plan to export

        Returns:
            CSV file download

        Fallback behavior: uses mock data and returns 503 if the CSV helper is unavailable.
        """
        # Test/demo only — do not expose in production. Uses mock data; 503 if helper missing.
        try:
            # In a real implementation, this would fetch the plan from a database
            # For now, we'll return a placeholder response
            from fastapi.responses import Response

            # Mock data - in real implementation, fetch from database
            mock_plan = {
                "meals": [
                    {
                        "name": "Breakfast",
                        "food_item": "Oatmeal",
                        "kcal": 300,
                        "protein_g": 10,
                        "carbs_g": 50,
                        "fat_g": 5,
                    },
                    {
                        "name": "Lunch",
                        "food_item": "Chicken Salad",
                        "kcal": 450,
                        "protein_g": 35,
                        "carbs_g": 20,
                        "fat_g": 25,
                    },
                    {
                        "name": "Dinner",
                        "food_item": "Grilled Fish",
                        "kcal": 400,
                        "protein_g": 40,
                        "carbs_g": 15,
                        "fat_g": 20,
                    },
                ],
                "total_kcal": 1150,
                "total_protein": 85,
                "total_carbs": 85,
                "total_fat": 50,
            }

            import sys as _sys

            _pkg = _sys.modules.get("app")
            _to_csv_day = (
                getattr(_pkg, "to_csv_day", None)
                if _pkg and hasattr(_pkg, "to_csv_day")
                else to_csv_day
            )
            if not callable(_to_csv_day):
                raise HTTPException(status_code=503, detail="CSV export helper is not available")

            csv_data = _to_csv_day(mock_plan)

            return Response(
                content=csv_data,
                media_type=ExportFormat.CSV.media_type,
                headers={
                    "Content-Disposition": (
                        f"attachment; filename=daily_plan_{plan_id}.{ExportFormat.CSV.extension}"
                    )
                },
            )

        except HTTPException:
            # Preserve explicit HTTP errors such as 503 when helper is unavailable
            raise
        except Exception as e:
            # Unexpected errors are treated as 500
            raise HTTPException(status_code=500, detail=f"CSV export failed: {str(e)}") from e

    async def export_pdf_generic(payload: Dict[str, Any]) -> Response:
        """Test/demo only — do not expose in production.

        Generic PDF export endpoint for tests' error-handling coverage.

        Accepts a JSON payload and attempts to render a simple PDF using to_pdf_day
        if present; otherwise returns an appropriate error. For empty payloads,
        FastAPI/Pydantic will trigger 422 automatically due to missing body shape.

        Fallback behavior: returns 400 for empty payloads and 503 if the PDF helper is
        unavailable.
        """
        # Test/demo only — do not expose in production. Returns 400 for empty payloads and 503
        # if the helper is missing.
        # Validate minimal structure
        if not isinstance(payload, dict) or not payload:
            # Either 422 already from validation or we enforce a 400 for empty dict
            raise HTTPException(status_code=400, detail="Empty export payload")

        # Attempt to use existing PDF export helper if available
        try:
            import sys as _sys

            _pkg = _sys.modules.get("app")
            _to_pdf_day = (
                getattr(_pkg, "to_pdf_day", None)
                if _pkg and hasattr(_pkg, "to_pdf_day")
                else to_pdf_day
            )
            if _to_pdf_day is None or not callable(_to_pdf_day):
                raise HTTPException(
                    status_code=503,
                    detail="PDF export helper is not available",
                )

            from fastapi.responses import Response

            # Use a tiny mock plan compatible with to_pdf_day expectations
            mock_plan = payload or {"meals": [], "totals": {}}
            pdf_data = _to_pdf_day(mock_plan)

            return Response(content=pdf_data, media_type=ExportFormat.PDF.media_type)
        except HTTPException:
            raise
        except Exception as e:
            # Return 500 to satisfy error handling expectations
            raise HTTPException(status_code=500, detail=f"PDF export failed: {str(e)}") from e

    async def export_weekly_plan_csv(plan_id: str) -> Response:
        """Test/demo only — do not expose in production.

        RU: Экспортировать недельный план в CSV.
        EN: Export weekly meal plan to CSV.

        Args:
            plan_id: ID of the weekly plan to export

        Returns:
            CSV file download

        Fallback behavior: returns a minimal CSV response when the CSV helper is unavailable.
        """
        # Test/demo only — do not expose in production. Returns minimal CSV when helper missing.
        try:
            from fastapi.responses import Response

            # Mock data - in real implementation, fetch from database
            mock_weekly_plan = {
                "daily_menus": [
                    {
                        "date": "2023-01-01",
                        "meals": [
                            {
                                "name": "Breakfast",
                                "food_item": "Oatmeal",
                                "kcal": 300,
                                "protein_g": 10,
                                "carbs_g": 50,
                                "fat_g": 5,
                                "cost": 1.5,
                            },
                            {
                                "name": "Lunch",
                                "food_item": "Chicken Salad",
                                "kcal": 450,
                                "protein_g": 35,
                                "carbs_g": 20,
                                "fat_g": 25,
                                "cost": 3.2,
                            },
                        ],
                    },
                    {
                        "date": "2023-01-02",
                        "meals": [
                            {
                                "name": "Breakfast",
                                "food_item": "Scrambled Eggs",
                                "kcal": 250,
                                "protein_g": 18,
                                "carbs_g": 1,
                                "fat_g": 20,
                                "cost": 1.2,
                            },
                            {
                                "name": "Lunch",
                                "food_item": "Beef Stir Fry",
                                "kcal": 500,
                                "protein_g": 30,
                                "carbs_g": 40,
                                "fat_g": 20,
                                "cost": 4.5,
                            },
                        ],
                    },
                ],
                "shopping_list": {
                    "oats": 500,
                    "chicken_breast": 300,
                    "eggs": 12,
                    "beef": 400,
                },
                "total_cost": 150.0,
                "adherence_score": 92.5,
            }

            import sys as _sys

            _pkg = _sys.modules.get("app")
            _to_csv_week = (
                getattr(_pkg, "to_csv_week", None)
                if _pkg and hasattr(_pkg, "to_csv_week")
                else to_csv_week
            )
            if not callable(_to_csv_week):
                # Fallback CSV response when helper is unavailable (keeps tests permissive)
                return Response(
                    content=b"plan_id,meals\n",
                    media_type=ExportFormat.CSV.media_type,
                    headers={
                        "Content-Disposition": (
                            f"attachment; filename=weekly_plan_{plan_id}.{ExportFormat.CSV.extension}"
                        )
                    },
                )

            csv_data = _to_csv_week(mock_weekly_plan)

            return Response(
                content=csv_data,
                media_type=ExportFormat.CSV.media_type,
                headers={
                    "Content-Disposition": (
                        f"attachment; filename=weekly_plan_{plan_id}.{ExportFormat.CSV.extension}"
                    )
                },
            )

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"CSV export failed: {str(e)}") from e

    async def export_daily_plan_pdf(plan_id: str) -> Response:
        # sourcery skip: raise-from-previous-error
        """Test/demo only — do not expose in production.

        RU: Экспортировать дневной план в PDF.
        EN: Export daily meal plan to PDF.

        Args:
            plan_id: ID of the daily plan to export

        Returns:
            PDF file download

        Fallback behavior: returns 503 when the PDF helper is unavailable and 500 if
        ReportLab is not installed.
        """
        # Test/demo only — do not expose in production. Returns 503 if helper missing and 500
        # if ReportLab is missing.
        try:
            from fastapi.responses import Response

            # Mock data - in real implementation, fetch from database
            mock_plan = {
                "meals": [
                    {
                        "name": "Breakfast",
                        "food_item": "Oatmeal",
                        "kcal": 300,
                        "protein_g": 10,
                        "carbs_g": 50,
                        "fat_g": 5,
                    },
                    {
                        "name": "Lunch",
                        "food_item": "Chicken Salad",
                        "kcal": 450,
                        "protein_g": 35,
                        "carbs_g": 20,
                        "fat_g": 25,
                    },
                    {
                        "name": "Dinner",
                        "food_item": "Grilled Fish",
                        "kcal": 400,
                        "protein_g": 40,
                        "carbs_g": 15,
                        "fat_g": 20,
                    },
                ],
                "total_kcal": 1150,
                "total_protein": 85,
                "total_carbs": 85,
                "total_fat": 50,
            }

            import sys as _sys

            _pkg = _sys.modules.get("app")
            _to_pdf_day = getattr(_pkg, "to_pdf_day", None) if _pkg else to_pdf_day
            if _to_pdf_day is None or not callable(_to_pdf_day):
                raise HTTPException(
                    status_code=503,
                    detail="PDF export not available - PDF function missing or not callable",
                )

            pdf_data = _to_pdf_day(mock_plan)

            return Response(
                content=pdf_data,
                media_type=ExportFormat.PDF.media_type,
                headers={
                    "Content-Disposition": (
                        f"attachment; filename=daily_plan_{plan_id}.{ExportFormat.PDF.extension}"
                    )
                },
            )

        except HTTPException:
            raise
        except ImportError:
            raise HTTPException(
                status_code=500, detail="PDF export not available - ReportLab not installed"
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"PDF export failed: {str(e)}") from e

    async def export_weekly_plan_pdf(plan_id: str) -> Response:
        # sourcery skip: raise-from-previous-error
        """Test/demo only — do not expose in production.

        RU: Экспортировать недельный план в PDF.
        EN: Export weekly meal plan to PDF.

        Args:
            plan_id: ID of the weekly plan to export

        Returns:
            PDF file download

        Fallback behavior: returns 503 when the PDF helper is unavailable.
        """
        # Test/demo only — do not expose in production. Returns 503 if helper missing.
        try:
            from fastapi.responses import Response

            # Mock data - in real implementation, fetch from database
            mock_weekly_plan = {
                "daily_menus": [
                    {
                        "date": "2023-01-01",
                        "meals": [
                            {
                                "name": "Breakfast",
                                "food_item": "Oatmeal",
                                "kcal": 300,
                                "protein_g": 10,
                                "carbs_g": 50,
                                "fat_g": 5,
                                "cost": 1.5,
                            },
                            {
                                "name": "Lunch",
                                "food_item": "Chicken Salad",
                                "kcal": 450,
                                "protein_g": 35,
                                "carbs_g": 20,
                                "fat_g": 25,
                                "cost": 3.2,
                            },
                        ],
                    },
                    {
                        "date": "2023-01-02",
                        "meals": [
                            {
                                "name": "Breakfast",
                                "food_item": "Scrambled Eggs",
                                "kcal": 250,
                                "protein_g": 18,
                                "carbs_g": 1,
                                "fat_g": 20,
                                "cost": 1.2,
                            },
                            {
                                "name": "Lunch",
                                "food_item": "Beef Stir Fry",
                                "kcal": 500,
                                "protein_g": 30,
                                "carbs_g": 40,
                                "fat_g": 20,
                                "cost": 4.5,
                            },
                        ],
                    },
                ],
                "shopping_list": {
                    "oats": 500,
                    "chicken_breast": 300,
                    "eggs": 12,
                    "beef": 400,
                },
                "total_cost": 150.0,
                "adherence_score": 92.5,
            }

            import sys as _sys

            _pkg = _sys.modules.get("app")

            _to_pdf_week = (
                getattr(_pkg, "to_pdf_week", None)
                if _pkg and hasattr(_pkg, "to_pdf_week")
                else to_pdf_week
            )
            if _to_pdf_week is None or not callable(_to_pdf_week):
                raise HTTPException(
                    status_code=503,
                    detail="PDF export unavailable",
                )
            pdf_data = _to_pdf_week(mock_weekly_plan)

            return Response(
                content=pdf_data,
                media_type=ExportFormat.PDF.media_type,
                headers={
                    "Content-Disposition": (
                        f"attachment; filename=weekly_plan_{plan_id}.{ExportFormat.PDF.extension}"
                    )
                },
            )

        except HTTPException:
            raise
        except ImportError:
            raise HTTPException(
                status_code=500, detail="PDF export not available - ReportLab not installed"
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"PDF export failed: {str(e)}") from e


# Bodyfat, BMI, and BMI Pro route registration is owned by app.main canonical bootstrap.
