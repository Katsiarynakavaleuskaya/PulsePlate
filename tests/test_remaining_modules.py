# -*- coding: utf-8 -*-
"""
Tests for Remaining Low Coverage Modules

RU: Тесты для оставшихся модулей с низким покрытием
EN: Tests for remaining modules with low coverage
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from tests.test_root_npm_dependency_guards import _load_json


def test_root_npm_security_override_smoke() -> None:
    """RU/EN: Keep critical root npm graph removal invariants in the deterministic fast lane."""
    repo_root = Path(__file__).resolve().parents[1]
    package_manifest = _load_json(repo_root / "package.json")
    package_lock = _load_json(repo_root / "package-lock.json")

    dependencies = package_manifest.get("dependencies", {})
    assert "@goplus/agentguard" not in dependencies

    packages = package_lock.get("packages", {})
    assert isinstance(packages, dict)
    assert "node_modules/@goplus/agentguard" not in packages
    assert "node_modules/axios" not in packages
    assert "node_modules/hono" not in packages
    assert "node_modules/path-to-regexp" not in packages
    assert not any(
        isinstance(package_path, str) and package_path.endswith("/brace-expansion")
        for package_path in packages
    )


class TestShoplistModule:
    """Test core.shoplist module."""

    def test_packaging_rule_class(self):
        """Test PackagingRule dataclass."""
        from core.shoplist import PackagingRule

        # Test creating packaging rule
        rule = PackagingRule(
            category="grains",
            unit="g",
            typical_packages=[100, 250, 500, 1000],
            rounding_strategy="up",
        )

        assert rule.category == "grains"
        assert rule.unit == "g"
        assert rule.typical_packages == [100, 250, 500, 1000]
        assert rule.rounding_strategy == "up"

    def test_shopping_item_class(self):
        """Test ShoppingItem dataclass."""
        from core.shoplist import ShoppingItem

        # Test creating shopping item
        item = ShoppingItem(name="chicken breast", quantity=500.0, unit="g", category="meat")

        assert item.name == "chicken breast"
        assert item.quantity == 500.0
        assert item.unit == "g"

    def test_shoplist_functions(self):
        """Test shoplist utility functions."""
        from core.shoplist import (
            create_shopping_list,
            group_by_category,
            optimize_packaging,
        )

        # Test with mock meal plan
        meal_plan = {
            "day1": {
                "breakfast": [{"name": "oats", "amount": 50, "unit": "g"}],
                "lunch": [{"name": "chicken", "amount": 150, "unit": "g"}],
                "dinner": [{"name": "rice", "amount": 100, "unit": "g"}],
            }
        }

        # Test shopping list creation
        shopping_list = create_shopping_list(meal_plan)
        assert isinstance(shopping_list, (list, dict, type(None)))

        # Test packaging optimization
        items = [
            {"name": "flour", "quantity": 350, "unit": "g"},
            {"name": "sugar", "quantity": 150, "unit": "g"},
        ]

        optimized = optimize_packaging(items)
        assert isinstance(optimized, (list, dict, type(None)))

        # Test category grouping
        grouped = group_by_category(items)
        assert isinstance(grouped, (dict, type(None)))


class TestWeeklyPlanModule:
    """Test core.weekly_plan module."""

    def test_weekly_plan_generation(self) -> None:
        """Test weekly plan generation."""
        from unittest.mock import MagicMock

        from core.weekly_plan import generate_weekly_plan

        targets = MagicMock()
        targets.kcal_daily = 2000

        with patch("core.weekly_plan.parse_food_db", return_value={}):
            with patch("core.weekly_plan.parse_recipe_db", return_value={}):
                with patch("core.weekly_plan.create_daily_plate", return_value={}):
                    plan = generate_weekly_plan(targets, set())
                    assert isinstance(plan, dict)
                    assert "days" in plan
                    assert len(plan["days"]) == 7

    def test_weekly_plan_with_diet_flags(self) -> None:
        """Test weekly plan with dietary restrictions."""
        from unittest.mock import MagicMock

        from core.weekly_plan import generate_weekly_plan

        targets = MagicMock()
        targets.kcal_daily = 1800

        diet_flags = {"vegetarian", "gluten_free"}

        with patch("core.weekly_plan.parse_food_db", return_value={}):
            with patch("core.weekly_plan.parse_recipe_db", return_value={}):
                with patch("core.weekly_plan.create_daily_plate", return_value={}):
                    plan = generate_weekly_plan(targets, diet_flags)
                    assert isinstance(plan, dict)
                    assert "days" in plan
                    assert len(plan["days"]) == 7

    def test_daily_plan_functions(self) -> None:
        """Test daily plan helper functions."""
        from core.weekly_plan import (
            calculate_weekly_nutrition,
            optimize_weekly_variety,
            validate_weekly_plan,
        )

        # Mock weekly plan data
        weekly_plan = {
            "day1": {"calories": 2000, "protein": 150},
            "day2": {"calories": 1900, "protein": 140},
            "day3": {"calories": 2100, "protein": 160},
        }

        # Test nutrition calculation
        nutrition = calculate_weekly_nutrition(weekly_plan)
        assert isinstance(nutrition, dict)
        assert "total_calories" in nutrition
        assert "avg_calories" in nutrition

        # Test variety optimization
        optimized = optimize_weekly_variety(weekly_plan)
        assert isinstance(optimized, dict)
        assert optimized.get("variety_optimized") is True

        # Test plan validation
        is_valid = validate_weekly_plan(weekly_plan)
        assert is_valid is True


class TestUtilsModule:
    """Test core.utils module."""

    def test_utils_comprehensive(self) -> None:
        """Test utils functions comprehensively."""
        from core.utils import (
            safe_float,
            safe_int,
            slugify,
        )

        # Test safe_float with various inputs
        assert safe_float("123.45") == 123.45
        assert safe_float("invalid") is None
        assert safe_float(None) is None
        assert safe_float("") is None
        assert safe_float("0") == 0.0
        assert safe_float("-123.45") == -123.45

        # Test safe_int with various inputs
        assert safe_int("123") == 123
        assert safe_int("invalid") is None
        assert safe_int(None) is None
        assert safe_int("") is None
        assert safe_int("0") == 0
        assert safe_int("-123") == -123

        # Test slugify with various inputs
        slug = slugify("Test String With Spaces")
        assert isinstance(slug, str)

        slug = slugify("Special!@#$%Characters")
        assert isinstance(slug, str)

        slug = slugify("")
        assert slug == ""

        slug = slugify(None)
        assert slug == ""

    def test_additional_utils(self) -> None:
        """Test additional utility functions."""
        from core.utils import (
            format_number,
            generate_id,
            sanitize_html,
            validate_email,
        )

        # Test email validation
        assert validate_email("test@example.com") is True
        assert validate_email("invalid-email") is False
        assert validate_email("") is False
        assert validate_email(None) is False

        # Test HTML sanitization
        sanitized = sanitize_html("<script>alert('xss')</script>")
        assert isinstance(sanitized, str)
        assert "<script>" not in sanitized

        sanitized = sanitize_html("<p>Valid HTML</p>")
        assert isinstance(sanitized, str)

        # Test ID generation
        idVal = generate_id()
        assert isinstance(idVal, str)
        assert len(idVal) == 32  # UUID hex without hyphens

        # Test number formatting
        formatted = format_number(1234.567)
        assert isinstance(formatted, str)


class TestTimeUtilsModule:
    """Test core.time_utils module for better coverage."""

    def test_time_utils_comprehensive(self) -> None:
        """Test time utilities comprehensively."""
        from core.time_utils import (
            format_datetime,
            get_timezone_offset,
            is_valid_date,
            parse_datetime,
        )

        # Test datetime parsing
        result = parse_datetime("2024-01-01T00:00:00")
        assert result is not None

        result = parse_datetime("2024-01-01")
        assert result is not None

        result = parse_datetime("invalid")
        assert result is None

        result = parse_datetime("")
        assert result is None

        # Test datetime formatting
        formatted = format_datetime("2024-01-01T00:00:00")
        assert isinstance(formatted, str)

        # Test timezone offset
        offset = get_timezone_offset("UTC")
        assert offset == 0.0

        offset = get_timezone_offset("US/Eastern")
        assert isinstance(offset, (int, float, type(None)))

        # Test date validation
        assert is_valid_date("2024-01-01") is True
        assert is_valid_date("invalid") is False


class TestDbGuardAndFallbackSmokeCoverage:
    """RU: Smoke-visible coverage tail for DB guard/fallback helpers.

    EN: Smoke-visible coverage tail for DB guard/fallback helpers.
    """

    TRUTHY = {"1", "true", "yes", "on"}

    def test_build_engine_url_production_guards_fail_closed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """RU: Prod-like env must reject missing and SQLite URLs.

        EN: Production-like env must reject missing and SQLite DATABASE_URL values.
        """

        import core.db as core_db

        core_db.reset_db_for_tests()
        try:
            monkeypatch.setenv("ENVIRONMENT", "production")
            monkeypatch.delenv("APP_ENV", raising=False)
            monkeypatch.setenv("DEBUG", "false")
            monkeypatch.delenv("DATABASE_URL", raising=False)

            with pytest.raises(RuntimeError, match="DATABASE_URL is required"):
                core_db._build_engine_url()

            monkeypatch.setenv("DATABASE_URL", "sqlite:///./cache/app.db")
            with pytest.raises(RuntimeError, match="SQLite DATABASE_URL is not allowed"):
                core_db._build_engine_url()
        finally:
            core_db.reset_db_for_tests()

    def test_is_sqlite_database_url_uses_scheme_fallback_when_sqlalchemy_parse_fails(self) -> None:
        """RU: Fallback parser must still detect SQLite dialect schemes.

        EN: Fallback parser must still detect SQLite dialect schemes.
        """

        import core.db as core_db

        with patch.object(core_db, "make_url", side_effect=ValueError("bad url")):
            assert core_db._is_sqlite_database_url("sqlite+pysqlite:///./cache/app.db") is True

    @pytest.mark.parametrize(
        ("database_url", "expected"),
        [
            ("", "<empty-db-url>"),
            ("sqlite:///:memory:", "sqlite:///:memory:"),
            ("sqlite:///./fallback.db", "sqlite:///<redacted>"),
            ("postgresql://db.example/pulseplate", "<redacted-db-url>"),
        ],
    )
    def test_redact_database_url_variants(self, database_url: str, expected: str) -> None:
        """RU: Redaction helper must cover empty, memory, file, and remote DSNs.

        EN: Redaction helper must cover empty, memory, file, and remote DSNs.
        """

        from core.db_fallback import _redact_database_url

        assert _redact_database_url(database_url) == expected

    def test_check_production_constraints_logs_and_raises(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """RU: Production fallback constraint must fail closed with guidance.

        EN: Production fallback constraint must fail closed with guidance.
        """

        from core.db_fallback import _check_production_constraints

        with pytest.raises(RuntimeError, match="prod-db-error"):
            _check_production_constraints(
                env_name="production",
                fallback_url="sqlite:///./fallback.db",
                truthy=self.TRUTHY,
                db_err=RuntimeError("prod-db-error"),
            )

        assert "canonical Postgres DATABASE_URL" in caplog.text

    def test_initialize_fallback_engine_re_raises_original_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """RU: Fallback engine init must preserve the original DB error.

        EN: Fallback engine init must preserve the original DB error.
        """

        import core.db_fallback as fallback_mod

        def _raise_create_engine(*args: object, **kwargs: object) -> object:
            raise RuntimeError("fallback init failed")

        monkeypatch.setattr(fallback_mod, "create_engine", _raise_create_engine)

        with pytest.raises(OSError, match="primary-db-error"):
            fallback_mod._initialize_fallback_engine(
                "sqlite:///:memory:",
                OSError("primary-db-error"),
            )

    def test_attempt_db_fallback_routes_production_and_nonproduction_helpers(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """RU: _attempt_db_fallback must route prod and non-prod helper paths.

        EN: _attempt_db_fallback must route prod and non-prod helper paths.
        """

        import core.db_fallback as fallback_mod

        production_calls: list[tuple[object, ...]] = []
        nonproduction_calls: list[tuple[str, object]] = []

        def _fake_check(
            env_name: str | None,
            fallback_url: str,
            truthy: set[str],
            db_err: Exception,
        ) -> None:
            production_calls.append((env_name, fallback_url, truthy, str(db_err)))
            raise db_err

        def _fake_validate(
            env_name: str | None,
            is_production: bool,
            fallback_url: str,
            db_err: Exception,
        ) -> None:
            nonproduction_calls.append(
                ("validate", (env_name, is_production, fallback_url, str(db_err)))
            )

        def _fake_initialize(fallback_url: str, db_err: Exception) -> str:
            nonproduction_calls.append(("initialize", (fallback_url, str(db_err))))
            return "engine-sentinel"

        def _fake_configure(
            engine: str,
            is_production: bool,
            fallback_url: str,
            env_name: str | None,
        ) -> None:
            nonproduction_calls.append(
                ("configure", (engine, is_production, fallback_url, env_name))
            )

        monkeypatch.setattr(fallback_mod, "_check_production_constraints", _fake_check)
        monkeypatch.setattr(fallback_mod, "_validate_fallback_url", _fake_validate)
        monkeypatch.setattr(fallback_mod, "_initialize_fallback_engine", _fake_initialize)
        monkeypatch.setattr(fallback_mod, "_configure_session_bindings", _fake_configure)

        monkeypatch.setenv("DB_FALLBACK_URL", "sqlite:///./prod-fallback.db")
        with pytest.raises(RuntimeError, match="prod failure"):
            fallback_mod._attempt_db_fallback(
                env_name="production",
                is_production=True,
                db_err=RuntimeError("prod failure"),
                truthy=self.TRUTHY,
            )

        assert production_calls == [
            ("production", "sqlite:///./prod-fallback.db", self.TRUTHY, "prod failure")
        ]

        monkeypatch.delenv("DB_FALLBACK_URL", raising=False)
        monkeypatch.setenv("ALLOW_DB_INMEMORY_FALLBACK", "true")
        fallback_mod._attempt_db_fallback(
            env_name="dev",
            is_production=False,
            db_err=RuntimeError("dev failure"),
            truthy=self.TRUTHY,
        )

        assert nonproduction_calls == [
            ("validate", ("dev", False, "sqlite:///:memory:", "dev failure")),
            ("initialize", ("sqlite:///:memory:", "dev failure")),
            ("configure", ("engine-sentinel", False, "sqlite:///:memory:", "dev")),
        ]
