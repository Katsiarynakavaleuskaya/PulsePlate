from __future__ import annotations

from app.services import restaurant_shadow_parity


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
