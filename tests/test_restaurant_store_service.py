from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.services import restaurant_store


def _set_test_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    worker = os.getenv("PYTEST_XDIST_WORKER", "gw0")
    db_path = tmp_path / f"restaurants_test_{worker}.sqlite"
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


def test_as_float_conversion_branches() -> None:
    assert restaurant_store._as_float(12) == 12.0
    assert restaurant_store._as_float(True) is None
    assert restaurant_store._as_float(False) is None
    assert restaurant_store._as_float("") is None
    assert restaurant_store._as_float("abc") is None
    assert restaurant_store._as_float(object()) is None


def test_import_menustat_rows_skips_invalid_entries(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _set_test_db(monkeypatch, tmp_path)
    stats = restaurant_store.import_menustat_rows(
        [
            {"chain_name": "", "item_name": "A"},
            {"chain_name": "Chain", "item_name": ""},
        ]
    )
    assert stats == {"chains_upserted": 0, "menu_items_upserted": 0}


def test_get_submission_handles_invalid_payload_json(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _set_test_db(monkeypatch, tmp_path)
    with restaurant_store._connect() as con:
        con.execute(
            """
            INSERT INTO user_submissions (
                id, entity_type, canonical_name, barcode, off_url, payload_json,
                status, reviewer_notes, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?, ?)
            """,
            (
                "s-bad-json",
                "restaurant_menu",
                "Bad payload",
                None,
                None,
                "{bad",
                "pending",
                "a",
                "b",
            ),
        )
        con.commit()

    row = restaurant_store.get_submission("s-bad-json")
    assert row is not None
    assert row["payload"] == {}


def test_create_submission_requires_name(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _set_test_db(monkeypatch, tmp_path)
    with pytest.raises(ValueError, match="canonical_name is required"):
        restaurant_store.create_submission(canonical_name="  ")


def test_create_submission_runtime_error_when_lookup_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _set_test_db(monkeypatch, tmp_path)
    original_get_submission = restaurant_store.get_submission
    monkeypatch.setattr(restaurant_store, "get_submission", lambda _: None)
    with pytest.raises(RuntimeError, match="failed to persist submission"):
        restaurant_store.create_submission(canonical_name="X")
    monkeypatch.setattr(restaurant_store, "get_submission", original_get_submission)


def test_get_submission_missing_returns_none(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _set_test_db(monkeypatch, tmp_path)
    assert restaurant_store.get_submission("no-such-submission") is None


def test_import_menustat_rows_non_ascii_ids_do_not_collapse(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _set_test_db(monkeypatch, tmp_path)
    stats = restaurant_store.import_menustat_rows(
        [
            {"chain_name": "Пицца Дом", "item_name": "Маргарита"},
            {"chain_name": "Роллы Плюс", "item_name": "Филадельфия"},
        ]
    )
    assert stats == {"chains_upserted": 2, "menu_items_upserted": 2}

    with restaurant_store._connect() as con:
        chain_rows = con.execute("SELECT id, name FROM restaurant_chains ORDER BY name").fetchall()
    assert len(chain_rows) == 2
    chain_ids = [row["id"] for row in chain_rows]
    assert chain_ids[0] != chain_ids[1]
    assert all(chain_id.startswith("id-") for chain_id in chain_ids)


def test_connect_enables_foreign_keys(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _set_test_db(monkeypatch, tmp_path)
    with restaurant_store._connect() as con:
        row = con.execute("PRAGMA foreign_keys").fetchone()
    assert row is not None
    assert row[0] == 1


def test_search_restaurants_rejects_invalid_pagination(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _set_test_db(monkeypatch, tmp_path)
    with pytest.raises(ValueError, match="offset must be >= 0"):
        restaurant_store.search_restaurants("x", limit=10, offset=-1)
    with pytest.raises(ValueError, match="limit must be <= 100"):
        restaurant_store.search_restaurants("x", limit=101, offset=0)


def test_get_restaurant_menu_rejects_invalid_limit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _set_test_db(monkeypatch, tmp_path)
    with pytest.raises(ValueError, match="limit must be <= 500"):
        restaurant_store.get_restaurant_menu("any", limit=501)
