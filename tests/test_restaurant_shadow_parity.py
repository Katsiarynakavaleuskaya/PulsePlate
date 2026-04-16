from __future__ import annotations

from decimal import Decimal

from app.services import restaurant_shadow_parity


def test_normalize_numeric_handles_none_invalid_and_fractional_values() -> None:
    assert restaurant_shadow_parity._normalize_numeric(None) is None
    assert restaurant_shadow_parity._normalize_numeric("not-a-number") is None
    assert restaurant_shadow_parity._normalize_numeric(Decimal("12.500")) == "12.5"


def test_normalize_bool_like_handles_supported_inputs() -> None:
    assert restaurant_shadow_parity._normalize_bool_like(None) is None
    assert restaurant_shadow_parity._normalize_bool_like(True) is True
    assert restaurant_shadow_parity._normalize_bool_like(0) is False
    assert restaurant_shadow_parity._normalize_bool_like("YES") is True
    assert restaurant_shadow_parity._normalize_bool_like("n") is False
    assert restaurant_shadow_parity._normalize_bool_like("maybe") is None


def test_compare_restaurant_hits_match() -> None:
    sqlite_rows = [{"id": "c1", "name": "Alpha", "country": "US", "source": "menustat"}]
    postgres_rows = [{"id": "c1", "name": "Alpha", "country": "US", "source": "menustat"}]
    result = restaurant_shadow_parity.compare_restaurant_hits(sqlite_rows, postgres_rows)
    assert result.match is True
    assert result.mismatch_reasons == ()


def test_compare_restaurant_menu_ignores_provenance_fields_in_v1() -> None:
    sqlite_rows = [
        {
            "id": "m1",
            "chain_id": "c1",
            "item_name": "Protein Bowl",
            "category": "Bowls",
            "serving_size_g": 240.0,
            "kcal": 510.0,
            "protein_g": 28.0,
            "fat_g": 16.0,
            "carbs_g": 55.0,
            "sodium_mg": 760.0,
            "source": "menustat",
            "source_id": "menu-1",
            "is_active": 1,
            "snapshot_date": "2026-02-24",
            "provenance_source": "menustat",
            "provenance_record_id": "menu-1",
        }
    ]
    postgres_rows = [
        {
            "id": "m1",
            "chain_id": "c1",
            "item_name": "Protein Bowl",
            "category": "Bowls",
            "serving_size_g": "240.00",
            "kcal": "510.00",
            "protein_g": "28.00",
            "fat_g": "16.00",
            "carbs_g": "55.00",
            "sodium_mg": "760.00",
            "source": "menustat",
            "source_id": "menu-1",
            "is_active": True,
            "snapshot_date": None,
            "provenance_source": None,
            "provenance_record_id": None,
        }
    ]
    result = restaurant_shadow_parity.compare_restaurant_menu(sqlite_rows, postgres_rows)
    assert result.match is True
    assert result.mismatch_reasons == ()


def test_compare_restaurant_menu_detects_value_drift() -> None:
    sqlite_rows = [
        {
            "id": "m1",
            "chain_id": "c1",
            "item_name": "Protein Bowl",
            "category": "Bowls",
            "serving_size_g": 240,
            "kcal": 510,
            "protein_g": 28,
            "fat_g": 16,
            "carbs_g": 55,
            "sodium_mg": 760,
            "source": "menustat",
            "source_id": "menu-1",
            "is_active": True,
        }
    ]
    postgres_rows = [
        {
            "id": "m1",
            "chain_id": "c1",
            "item_name": "Protein Bowl",
            "category": "Bowls",
            "serving_size_g": 240,
            "kcal": 499,
            "protein_g": 28,
            "fat_g": 16,
            "carbs_g": 55,
            "sodium_mg": 760,
            "source": "menustat",
            "source_id": "menu-1",
            "is_active": True,
        }
    ]
    result = restaurant_shadow_parity.compare_restaurant_menu(sqlite_rows, postgres_rows)
    assert result.match is False
    assert result.mismatched_indexes == (0,)
    assert "field kcal mismatch" in result.mismatch_reasons[0]


def test_compare_restaurant_menu_detects_ordering_drift() -> None:
    sqlite_rows = [
        {
            "id": "m1",
            "chain_id": "c1",
            "item_name": "Alpha Bowl",
            "category": "Bowls",
            "serving_size_g": 240,
            "kcal": 510,
            "protein_g": 28,
            "fat_g": 16,
            "carbs_g": 55,
            "sodium_mg": 760,
            "source": "menustat",
            "source_id": "menu-1",
            "is_active": True,
        },
        {
            "id": "m2",
            "chain_id": "c1",
            "item_name": "Beta Bowl",
            "category": "Bowls",
            "serving_size_g": 230,
            "kcal": 470,
            "protein_g": 24,
            "fat_g": 14,
            "carbs_g": 52,
            "sodium_mg": 710,
            "source": "menustat",
            "source_id": "menu-2",
            "is_active": True,
        },
    ]
    postgres_rows = [sqlite_rows[1], sqlite_rows[0]]
    result = restaurant_shadow_parity.compare_restaurant_menu(sqlite_rows, postgres_rows)
    assert result.match is False
    assert result.mismatched_indexes[0] == 0


def test_compare_restaurant_menu_detects_unequal_row_lengths() -> None:
    sqlite_rows = [
        {
            "id": "m1",
            "chain_id": "c1",
            "item_name": "Alpha Bowl",
            "category": "Bowls",
            "serving_size_g": 240,
            "kcal": 510,
            "protein_g": 28,
            "fat_g": 16,
            "carbs_g": 55,
            "sodium_mg": 760,
            "source": "menustat",
            "source_id": "menu-1",
            "is_active": True,
        },
        {
            "id": "m2",
            "chain_id": "c1",
            "item_name": "Beta Bowl",
            "category": "Bowls",
            "serving_size_g": 230,
            "kcal": 470,
            "protein_g": 24,
            "fat_g": 14,
            "carbs_g": 52,
            "sodium_mg": 710,
            "source": "menustat",
            "source_id": "menu-2",
            "is_active": True,
        },
    ]
    postgres_rows = [sqlite_rows[0]]

    result = restaurant_shadow_parity.compare_restaurant_menu(sqlite_rows, postgres_rows)

    assert result.match is False
    assert result.sqlite_count == 2
    assert result.postgres_count == 1
    assert result.mismatched_indexes == (1,)
    assert result.mismatch_reasons[0] == "row-count mismatch sqlite=2 postgres=1"
    assert result.mismatch_reasons[1] == "missing postgres row at index 1"


def test_compare_restaurant_menu_detects_missing_sqlite_row() -> None:
    sqlite_rows = [
        {
            "id": "m1",
            "chain_id": "c1",
            "item_name": "Alpha Bowl",
            "category": "Bowls",
            "serving_size_g": 240,
            "kcal": 510,
            "protein_g": 28,
            "fat_g": 16,
            "carbs_g": 55,
            "sodium_mg": 760,
            "source": "menustat",
            "source_id": "menu-1",
            "is_active": True,
        }
    ]
    postgres_rows = [
        sqlite_rows[0],
        {
            "id": "m2",
            "chain_id": "c1",
            "item_name": "Beta Bowl",
            "category": "Bowls",
            "serving_size_g": 230,
            "kcal": 470,
            "protein_g": 24,
            "fat_g": 14,
            "carbs_g": 52,
            "sodium_mg": 710,
            "source": "menustat",
            "source_id": "menu-2",
            "is_active": True,
        },
    ]

    result = restaurant_shadow_parity.compare_restaurant_menu(sqlite_rows, postgres_rows)

    assert result.match is False
    assert result.sqlite_count == 1
    assert result.postgres_count == 2
    assert result.mismatched_indexes == (1,)
    assert result.mismatch_reasons[0] == "row-count mismatch sqlite=1 postgres=2"
    assert result.mismatch_reasons[1] == "missing sqlite row at index 1"
