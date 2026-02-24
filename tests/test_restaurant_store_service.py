from __future__ import annotations

from pathlib import Path

import pytest

from app.services import restaurant_store


def _set_test_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    db_path = tmp_path / "restaurants_test.sqlite"
    monkeypatch.setattr(restaurant_store, "DB_PATH", db_path)
    return db_path


def test_import_menustat_rows_and_query(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _set_test_db(monkeypatch, tmp_path)
    stats = restaurant_store.import_menustat_rows(
        [
            {
                "chain_name": "Test Chain",
                "country": "US",
                "item_name": "Protein Burger",
                "category": "Burgers",
                "kcal": "540",
                "protein_g": "30",
                "fat_g": "24",
                "carbs_g": "50",
                "sodium_mg": "910",
                "source_id": "menu-001",
            }
        ],
        snapshot_date="2026-02-24",
    )
    assert stats == {"chains_upserted": 1, "menu_items_upserted": 1}

    chains = restaurant_store.search_restaurants("test", limit=10, offset=0)
    assert len(chains) == 1
    assert chains[0]["id"] == "test-chain"
    assert chains[0]["source"] == "menustat"

    menu = restaurant_store.get_restaurant_menu("test-chain", limit=10)
    assert len(menu) == 1
    assert menu[0]["item_name"] == "Protein Burger"
    assert menu[0]["chain_id"] == "test-chain"
    assert menu[0]["kcal"] == 540.0


def test_submission_lifecycle_with_audit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _set_test_db(monkeypatch, tmp_path)

    created = restaurant_store.create_submission(
        canonical_name="Protein Burger",
        payload={"kcal": 540, "source_hint": "menustat"},
        barcode="0123456789012",
        off_url=None,
    )
    assert created["status"] == "pending"
    assert created["audit"] == []

    reviewed = restaurant_store.review_submission(
        created["id"], status="approved", reviewer_notes="verified"
    )
    assert reviewed is not None
    assert reviewed["status"] == "approved"
    assert len(reviewed["audit"]) == 1
    assert reviewed["audit"][0]["from_status"] == "pending"
    assert reviewed["audit"][0]["to_status"] == "approved"


def test_review_submission_invalid_status(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _set_test_db(monkeypatch, tmp_path)

    created = restaurant_store.create_submission(
        canonical_name="Salad",
        payload={"kcal": 120},
    )
    with pytest.raises(ValueError, match="status must be one of: approved, rejected"):
        restaurant_store.review_submission(created["id"], status="pending")


def test_review_submission_missing_returns_none(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _set_test_db(monkeypatch, tmp_path)
    assert restaurant_store.review_submission("missing-id", status="approved") is None
