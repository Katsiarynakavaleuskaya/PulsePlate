"""Real functionality tests to reach 97% coverage.

These tests exercise actual code paths in core modules rather than just imports.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import patch
import tempfile
import os


class TestTimeUtils:
    """Test core.time_utils module functionality."""

    def test_now_utc(self):
        """Test now_utc returns timezone-aware UTC datetime."""
        from core.time_utils import now_utc

        result = now_utc()
        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc

    def test_ensure_utc_with_naive_datetime(self):
        """Test ensure_utc with naive datetime."""
        from core.time_utils import ensure_utc

        naive_dt = datetime(2024, 1, 1, 12, 0, 0)
        result = ensure_utc(naive_dt)

        assert result.tzinfo == timezone.utc
        assert result.replace(tzinfo=None) == naive_dt

    def test_ensure_utc_with_aware_datetime(self):
        """Test ensure_utc with timezone-aware datetime."""
        from core.time_utils import ensure_utc

        aware_dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        result = ensure_utc(aware_dt)

        assert result.tzinfo == timezone.utc
        assert result == aware_dt

    def test_isoformat_utc_with_datetime(self):
        """Test isoformat_utc with provided datetime."""
        from core.time_utils import isoformat_utc

        dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        result = isoformat_utc(dt)

        assert result == "2024-01-01T12:00:00+00:00"

    def test_isoformat_utc_without_datetime(self):
        """Test isoformat_utc without provided datetime."""
        from core.time_utils import isoformat_utc

        result = isoformat_utc()
        assert isinstance(result, str)
        assert "T" in result
        assert "+00:00" in result

    def test_parse_iso8601_with_timezone(self):
        """Test parse_iso8601 with timezone info."""
        from core.time_utils import parse_iso8601

        result = parse_iso8601("2024-01-01T12:00:00+00:00")
        assert result.tzinfo == timezone.utc
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 1

    def test_parse_iso8601_without_timezone(self):
        """Test parse_iso8601 without timezone info."""
        from core.time_utils import parse_iso8601

        result = parse_iso8601("2024-01-01T12:00:00")
        assert result.tzinfo == timezone.utc

    def test_to_timezone_with_zoneinfo(self):
        """Test to_timezone conversion."""
        from core.time_utils import to_timezone

        dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        result = to_timezone(dt, "America/New_York")

        assert result.tzinfo is not None
        assert result.year == 2024

    def test_to_timezone_without_zoneinfo(self):
        """Test to_timezone without zoneinfo module."""
        from core.time_utils import to_timezone

        with patch("core.time_utils.ZoneInfo", None):
            dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            with pytest.raises(RuntimeError, match="zoneinfo module is required"):
                to_timezone(dt, "America/New_York")

    def test_local_now(self):
        """Test local_now function."""
        from core.time_utils import local_now

        result = local_now("America/New_York")
        assert isinstance(result, datetime)
        assert result.tzinfo is not None

    def test_local_date_today(self):
        """Test local_date_today function."""
        from core.time_utils import local_date_today

        result = local_date_today("America/New_York")
        assert isinstance(result, str)
        assert len(result) == 10  # YYYY-MM-DD format
        assert result.count("-") == 2


class TestUnits:
    """Test core.units module functionality."""

    def test_iu_vitd_from_ug(self):
        """Test vitamin D conversion from µg to IU."""
        from core.units import iu_vitd_from_ug

        # Test normal conversion
        result = iu_vitd_from_ug(10.0)
        assert result == 400.0  # 10 µg * 40 IU/µg

        # Test with integer input
        result = iu_vitd_from_ug(5)
        assert result == 200.0

        # Test with zero
        result = iu_vitd_from_ug(0)
        assert result == 0.0

    def test_mg_from_ug(self):
        """Test conversion from µg to mg."""
        from core.units import mg_from_ug

        # Test normal conversion
        result = mg_from_ug(1000.0)
        assert result == 1.0

        # Test with integer input
        result = mg_from_ug(500)
        assert result == 0.5

        # Test with zero
        result = mg_from_ug(0)
        assert result == 0.0

    def test_mg_from_g(self):
        """Test conversion from g to mg."""
        from core.units import mg_from_g

        # Test normal conversion
        result = mg_from_g(1.0)
        assert result == 1000.0

        # Test with integer input
        result = mg_from_g(2)
        assert result == 2000.0

        # Test with zero
        result = mg_from_g(0)
        assert result == 0.0


class TestAliases:
    """Test core.aliases module functionality."""

    def test_map_to_canonical_with_empty_string(self):
        """Test map_to_canonical with empty string."""
        from core.aliases import map_to_canonical

        result = map_to_canonical("")
        assert result == "unknown"

    def test_map_to_canonical_with_whitespace(self):
        """Test map_to_canonical with whitespace-only string."""
        from core.aliases import map_to_canonical

        result = map_to_canonical("   ")
        assert result == "unknown"

    def test_map_to_canonical_fallback_conversion(self):
        """Test map_to_canonical fallback to snake_case conversion."""
        from core.aliases import map_to_canonical

        # Test with special characters
        result = map_to_canonical("apple-pie!")
        assert result == "apple_pie"

        # Test with multiple spaces
        result = map_to_canonical("chocolate  cake")
        assert result == "chocolate_cake"

        # Test with leading/trailing underscores
        result = map_to_canonical("_special_food_")
        assert result == "special_food"

    def test_map_to_canonical_with_locale(self):
        """Test map_to_canonical with different locales."""
        from core.aliases import map_to_canonical

        result = map_to_canonical("test food", "en")
        assert result == "test_food"

        result = map_to_canonical("test food", "ru")
        assert result == "test_food"

    def test_add_alias_new_file(self):
        """Test add_alias creating new file."""
        from core.aliases import add_alias

        # Create a temporary file path that doesn't exist yet
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as f:
            temp_path = f.name
        # Remove the file so it doesn't exist
        os.unlink(temp_path)

        try:
            add_alias("test_alias", "test_canonical", temp_path)

            # Verify file was created with correct content
            with open(temp_path, "r", encoding="utf-8") as f:
                content = f.read()
                assert "alias,canonical" in content
                assert "test_alias,test_canonical" in content
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_add_alias_existing_file(self):
        """Test add_alias appending to existing file."""
        from core.aliases import add_alias

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as f:
            f.write("alias,canonical\n")
            f.write("existing,existing_canonical\n")
            temp_path = f.name

        try:
            add_alias("new_alias", "new_canonical", temp_path)

            # Verify content was appended
            with open(temp_path, "r", encoding="utf-8") as f:
                content = f.read()
                assert "existing,existing_canonical" in content
                assert "new_alias,new_canonical" in content
        finally:
            os.unlink(temp_path)


class TestUtils:
    """Test core.utils module functionality."""

    def test_get_activity_factor_valid_activities(self):
        """Test get_activity_factor with valid activity levels."""
        from core.utils import get_activity_factor

        assert get_activity_factor("sedentary") == 1.2
        assert get_activity_factor("light") == 1.375
        assert get_activity_factor("moderate") == 1.55
        assert get_activity_factor("active") == 1.725
        assert get_activity_factor("very_active") == 1.9

    def test_get_activity_factor_invalid_activity(self):
        """Test get_activity_factor with invalid activity level."""
        from core.utils import get_activity_factor

        # Test with unknown activity
        result = get_activity_factor("unknown_activity")
        assert result == 1.55  # Default moderate

        # Test with empty string
        result = get_activity_factor("")
        assert result == 1.55

    def test_resolve_attr_with_local_default(self):
        """Test resolve_attr with local default."""
        from core.utils import resolve_attr

        result = resolve_attr("nonexistent_attr", "default_value")
        assert result == "default_value"

    def test_resolve_attr_with_candidates(self):
        """Test resolve_attr with candidate modules."""
        from core.utils import resolve_attr

        # Test with empty candidates
        result = resolve_attr("test_attr", "default", [])
        assert result == "default"

        # Test with None candidates
        result = resolve_attr("test_attr", "default", [None])
        assert result == "default"


class TestDisclaimers:
    """Test core.disclaimers module functionality."""

    def test_get_disclaimer_text_medical(self):
        """Test get_disclaimer_text for medical disclaimers."""
        from core.disclaimers import get_disclaimer_text

        # Test English medical disclaimer
        result = get_disclaimer_text("medical", language="en")
        assert "IMPORTANT MEDICAL DISCLAIMER" in result
        assert "NOT intended for medical diagnosis" in result

        # Test Russian medical disclaimer
        result = get_disclaimer_text("medical", language="ru")
        assert "ВАЖНЫЙ МЕДИЦИНСКИЙ ОТКАЗ" in result

    def test_get_disclaimer_text_legal(self):
        """Test get_disclaimer_text for legal disclaimers."""
        from core.disclaimers import get_disclaimer_text

        result = get_disclaimer_text("legal", language="en")
        assert "LEGAL DISCLAIMER" in result
        assert "provided 'as is'" in result

    def test_get_disclaimer_text_privacy(self):
        """Test get_disclaimer_text for privacy disclaimers."""
        from core.disclaimers import get_disclaimer_text

        result = get_disclaimer_text("privacy", language="en")
        assert "PRIVACY NOTICE" in result
        assert "privacy-compliant" in result

    def test_get_disclaimer_text_with_special_population(self):
        """Test get_disclaimer_text with special population."""
        from core.disclaimers import get_disclaimer_text

        result = get_disclaimer_text("medical", special_population="pregnancy", language="en")
        assert "IMPORTANT MEDICAL DISCLAIMER" in result
        assert "PREGNANCY NUTRITION DISCLAIMER" in result

    def test_get_disclaimer_text_invalid_population(self):
        """Test get_disclaimer_text with invalid special population."""
        from core.disclaimers import get_disclaimer_text

        result = get_disclaimer_text("medical", special_population="invalid", language="en")
        assert "IMPORTANT MEDICAL DISCLAIMER" in result
        assert "PREGNANCY NUTRITION DISCLAIMER" not in result

    def test_get_comprehensive_disclaimer(self):
        """Test get_comprehensive_disclaimer function."""
        from core.disclaimers import get_comprehensive_disclaimer

        result = get_comprehensive_disclaimer(language="en")
        assert "IMPORTANT MEDICAL DISCLAIMER" in result
        assert "LEGAL DISCLAIMER" in result
        assert "PRIVACY NOTICE" in result
        assert "=" * 50 in result

    def test_get_comprehensive_disclaimer_with_populations(self):
        """Test get_comprehensive_disclaimer with special populations."""
        from core.disclaimers import get_comprehensive_disclaimer

        result = get_comprehensive_disclaimer(
            special_populations=["pregnancy", "children"], language="en"
        )
        assert "PREGNANCY NUTRITION DISCLAIMER" in result
        assert "PEDIATRIC NUTRITION DISCLAIMER" in result

    def test_get_professional_referral(self):
        """Test get_professional_referral function."""
        from core.disclaimers import get_professional_referral

        # Test valid categories
        result = get_professional_referral("general", "en")
        assert "Registered Dietitian" in result

        result = get_professional_referral("sports", "en")
        assert "Sports Nutritionist" in result

        # Test invalid category (should return general)
        result = get_professional_referral("invalid", "en")
        assert "Registered Dietitian" in result

        # Test Russian
        result = get_professional_referral("general", "ru")
        assert "Диетолог" in result
