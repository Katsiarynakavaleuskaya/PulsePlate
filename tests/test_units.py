"""
Units Conversion Tests

RU: Тесты конверсии единиц.
EN: Units conversion tests.
"""

import pytest

from core.units import iu_vitd_from_ug, mg_from_g, mg_from_ug


def test_iu_vitd_from_ug():
    """Test vitamin D conversion from µg to IU."""
    # 1 µg = 40 IU
    assert iu_vitd_from_ug(1.0) == 40.0
    assert iu_vitd_from_ug(0.5) == 20.0
    assert iu_vitd_from_ug(2.5) == 100.0
    assert iu_vitd_from_ug(0.0) == 0.0


def test_mg_from_ug():
    """Test conversion from µg to mg."""
    # 1000 µg = 1 mg
    assert mg_from_ug(1000.0) == 1.0
    assert mg_from_ug(500.0) == 0.5
    assert mg_from_ug(2500.0) == 2.5
    assert mg_from_ug(0.0) == 0.0


def test_mg_from_g():
    """Test conversion from g to mg."""
    # 1 g = 1000 mg
    assert mg_from_g(1.0) == 1000.0
    assert mg_from_g(0.5) == 500.0
    assert mg_from_g(2.5) == 2500.0
    assert mg_from_g(0.0) == 0.0


if __name__ == "__main__":
    pytest.main([__file__])
