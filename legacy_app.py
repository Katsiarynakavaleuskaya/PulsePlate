from __future__ import annotations

import logging
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Optional,
    cast,
)

from app.application_metadata import build_application_metadata
from app.bootstrap.application import APPLICATION_METADATA, RUNTIME_ENV, app as _canonical_app
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
    NutrientGapsRequest,
    NutrientGapsResponse,
    PlateRequest,
    PlateResponse,
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
from app.utils.helpers import _short_git_sha as _short_git_sha
from app.utils.feature_flags import _is_truthy

# Preserve the declared lexical legacy surface while re-exporting the exact canonical object.
app = cast(Any, _canonical_app)

_BMI_COMPAT_REEXPORTS = (
    MATPLOTLIB_AVAILABLE,
    add_visualization_if_requested,
    generate_bmi_visualization,
)

_BMI_SCHEMA_COMPAT_REEXPORTS = (
    BMIRequest,
    BMIRequestV1,
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

# Canonical application bootstrap owns environment resolution, dotenv loading,
# root logging configuration, metadata construction, and the FastAPI instance.
_app_env = RUNTIME_ENV
logger = logging.getLogger(__name__)
bmi_logger = logging.getLogger("app.bmi")

# Initialize log retention manager
_log_retention_manager: Optional[LogRetentionManager] = None


# OpenAPI/Swagger metadata remains available here as exact compatibility values.
_application_metadata = APPLICATION_METADATA
tags_metadata = _application_metadata.openapi_tags_list()
_api_description = _application_metadata.description


# (moved to top with other imports)


# PRO/VIP route registration is owned by app.main canonical bootstrap.
# Shopping-list route registration is owned by app.main canonical bootstrap.

# Premium week router registration is now handled in
# app.routers.pro_registration.register_pro_routes() for centralized registration.

# Legacy event handlers - replaced with lifespan
# @app.on_event("startup")
# @app.on_event("shutdown")


# Rate limiting setup (PR-628)
# Wiring is centralized in app.security.rate_limit; import after app creation
# to avoid import-order issues with FastAPI instance


# ---------- Core logic ----------


# WHO-Based Nutrition Models
#
# NOTE (PR-633): `TargetsIn` is canonical in `app.schemas.nutrition_targets` (import-safe).
# Legacy endpoints must not define a second validation path to avoid drift.
#
# NOTE: Legacy weekly-plan contracts are now owned by
# `app.schemas.legacy_premium_weekly_plan`; `legacy_app` only re-exports them.


# Canonical Plate ownership. Retained schema and helper compatibility exports
# remain exact service aliases. Canonical and retained HTTP handlers import the
# service directly.
DB_TO_ALIAS_NUTRIENT_MAP = _canonical_plate_service.DB_TO_ALIAS_NUTRIENT_MAP


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


# Bodyfat, BMI, and BMI Pro route registration is owned by app.main canonical bootstrap.
