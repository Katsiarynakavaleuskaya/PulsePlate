# -*- coding: utf-8 -*-
"""Targeted coverage tests for lightweight core helpers.

The original version of this file tried to import dozens of optional modules,
duplicated assignments, and defined invalid tests that pytest could not run
(`self` arguments outside of classes, repeated blocks, etc.).  The result was a
mixture of `AttributeError`, `TypeError`, and silent skips, which is why the
user observed "много проблем с импортами".  This rewrite keeps the intent of
smoke-testing a few frequently used helpers while ensuring every test executes
predictably and degrades gracefully when an optional module is missing.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# core.aliases
# ---------------------------------------------------------------------------


def test_aliases_round_trip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Alias helpers should read the CSV table and sanitise fallbacks."""

    aliases = pytest.importorskip("core.aliases")

    csv_path = tmp_path / "aliases.csv"
    aliases.add_alias("яблоко", "apple", path=str(csv_path))

    original_loader = aliases._load_aliases

    def _load_override(path: str | None = None) -> dict[str, str]:
        return original_loader(str(csv_path))

    monkeypatch.setattr(aliases, "_load_aliases", _load_override)

    assert aliases.map_to_canonical("  ЯБЛОКО  ") == "apple"
    assert aliases.map_to_canonical("Fresh bread!") == "fresh_bread"


# ---------------------------------------------------------------------------
# core.i18n
# ---------------------------------------------------------------------------


def test_i18n_translation_and_normalization() -> None:
    i18n = pytest.importorskip("core.i18n")

    russian_label = i18n.t("ru", "bmi_normal")
    assert "Норма" in russian_label

    # Normalisation uses business rules with locale specific fallbacks
    assert i18n.normalize_lang("es-MX") == "es"
    assert i18n.normalize_lang("fr_FR") == "en"

    assert i18n.validate_translation_key("bmi_normal") is True


# ---------------------------------------------------------------------------
# core.time_utils
# ---------------------------------------------------------------------------


def test_time_utils_timezone_functions(monkeypatch: pytest.MonkeyPatch) -> None:
    time_utils = pytest.importorskip("core.time_utils")

    fixed_now = datetime(2024, 1, 1, 12, tzinfo=timezone.utc)
    monkeypatch.setattr(time_utils, "now_utc", lambda: fixed_now)

    iso_value = time_utils.isoformat_utc()
    parsed = time_utils.parse_iso8601(iso_value)
    assert parsed.tzinfo == timezone.utc

    if getattr(time_utils, "ZoneInfo", None) is None:
        pytest.skip("zoneinfo not available in this runtime")

    berlin_time = time_utils.to_timezone(fixed_now, "Europe/Berlin")
    assert berlin_time.tzinfo is not None

    today = time_utils.local_date_today("UTC")
    assert today == "2024-01-01"


# ---------------------------------------------------------------------------
# core.units
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "func,value,expected",
    [
        ("iu_vitd_from_ug", 10, 400.0),
        ("mg_from_ug", 2500, 2.5),
        ("mg_from_g", 1.2, 1200.0),
    ],
)
def test_units_conversions(func: str, value: float, expected: float) -> None:
    units = pytest.importorskip("core.units")

    result = getattr(units, func)(value)
    assert result == pytest.approx(expected)


# ---------------------------------------------------------------------------
# core.utils
# ---------------------------------------------------------------------------


def test_get_activity_factor_and_defaults() -> None:
    utils = pytest.importorskip("core.utils")
    assert utils.get_activity_factor("active") == pytest.approx(1.725)
    assert utils.get_activity_factor("unknown") == pytest.approx(1.55)


def test_resolve_attr_prefers_candidates(monkeypatch: pytest.MonkeyPatch) -> None:
    utils = pytest.importorskip("core.utils")
    sentinel = object()

    import types

    candidate_module = types.ModuleType("candidate_module")
    setattr(candidate_module, "target_value", "from_namespace")
    resolved = utils.resolve_attr("target_value", sentinel, [candidate_module])
    assert resolved == "from_namespace"

    fake_module_name = "tests.fake_module_for_utils"
    fake_module = types.ModuleType(fake_module_name)
    setattr(fake_module, "target_value", "from_sys_modules")
    sys.modules[fake_module_name] = fake_module
    try:
        resolved = utils.resolve_attr("target_value", sentinel, [fake_module_name])
        assert resolved == "from_sys_modules"
    finally:
        sys.modules.pop(fake_module_name, None)

    assert utils.resolve_attr("missing", sentinel, []) is sentinel


# ---------------------------------------------------------------------------
# core.plate (import smoke)
# ---------------------------------------------------------------------------


def test_plate_module_import_smoke() -> None:
    plate = pytest.importorskip("core.plate")
    assert hasattr(plate, "make_plate")
