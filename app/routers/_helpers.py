"""
Shared helper functions for routers.

RU: Общие вспомогательные функции для роутеров.
EN: Shared helper functions for routers.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from app.schemas.bmi import SoftPaywallHook

# Keep fallback defaults aligned with core.bmi.engine defaults.
_DEFAULT_YES_VALUES: set[str] = {"yes", "y", "true", "1", "да", "д", "истина", "si", "sí"}


def _env_bool(name: str, default: bool) -> bool:
    """
    Parse boolean env var.

    RU/EN note: Accepts common truthy/falsey strings.
    """
    raw = os.getenv(name)
    if raw is None:
        return default
    value = raw.strip().lower()
    if value in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if value in {"0", "false", "f", "no", "n", "off"}:
        return False
    return default


def _get_engine_normalize_bool_flag() -> Callable[[str | bool, set[str] | None], bool] | None:
    """
    Internal helper to isolate engine import.

    Test can monkeypatch this to force fallback without mocking builtins import.
    """
    try:
        from core.bmi.engine import (
            _normalize_bool_flag as _engine_normalize_bool_flag,
        )  # noqa: WPS433

        return _engine_normalize_bool_flag
    except ImportError:
        return None


def _normalize_bool_flag(value: str | bool, yes_values: set[str] | None = None) -> bool:
    """
    Normalize boolean flag from string or bool.

    RU: Нормализует флаг yes/no (pregnant/athlete и т.п.) в bool.
    EN: Normalize yes/no-ish flag to bool.

    Uses canonical implementation from core.bmi.engine with fallback.
    This ensures consistent normalization across FREE and PRO routers.

    Args:
        value: String or bool value to normalize
        yes_values: Optional custom set of truthy strings (defaults to engine's _DEFAULT_YES_VALUES)

    Returns:
        bool: Normalized boolean value

    Note:
        Falls back to local implementation if engine is not available (development/testing).
    """
    engine_fn = _get_engine_normalize_bool_flag()
    if engine_fn is not None:
        return engine_fn(value, yes_values)

    # Fallback path (dev/partial checkouts): keep behavior aligned with engine defaults.
    if isinstance(value, bool):
        return value
    if not isinstance(value, str):
        return False
    s = value.strip().lower()
    if not s:
        return False

    # Preserve explicit empty set semantics (set() stays empty).
    allowed = (
        {v.strip().lower() for v in yes_values} if yes_values is not None else _DEFAULT_YES_VALUES
    )
    return s in allowed


def _build_soft_paywall_hook(lang: str, *, default_enabled: bool) -> SoftPaywallHook | None:
    """
    Build text-only soft paywall hook (no BMI logic).

    IMPORTANT:
    - No BMI-dependent logic.
    - Must not depend on BMI calculation modules.

    Args:
        lang: Language code for i18n
        default_enabled: Default value if SOFT_PAYWALL_ENABLED env var is not set
                         (FREE tier: True, PRO tier: False)

    Returns:
        SoftPaywallHook if enabled, None otherwise

    Note:
        Uses lazy imports to avoid circular dependencies.
    """
    # Lazy imports to avoid circular dependencies
    from app.schemas.bmi import (
        SoftPaywallAvailability,
        SoftPaywallHook,
        SoftPaywallMessage,
    )
    from core.i18n import normalize_lang, t

    enabled = _env_bool("SOFT_PAYWALL_ENABLED", default=default_enabled)
    if not enabled:
        return None

    safe_lang = normalize_lang(lang)

    message = SoftPaywallMessage(
        lang=safe_lang,
        title_key="soft_paywall.title",
        body_key="soft_paywall.body",
        cta_key="soft_paywall.cta",
        default_title=t(safe_lang, "soft_paywall.title"),
        default_body=t(safe_lang, "soft_paywall.body"),
        default_cta=t(safe_lang, "soft_paywall.cta"),
    )

    availability = SoftPaywallAvailability(pro_available=True, reason_key=None)

    return SoftPaywallHook(
        id="bmi.pro_interpretation_v1",
        message=message,
        availability=availability,
        target="pro_paywall",
    )
