from __future__ import annotations

import json
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
    assert menu[0]["snapshot_date"] == "2026-02-24"
    assert menu[0]["provenance_source"] == "menustat"
    assert menu[0]["provenance_record_id"] == "menu-001"


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

    with restaurant_store._connect() as con:
        source_row = con.execute(
            """
            SELECT entity_type, source_name, source_record_id, snapshot_date, raw_data_json
            FROM source_catalog
            WHERE entity_type = 'user_submission' AND entity_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (created["id"],),
        ).fetchone()
    assert source_row is not None
    assert source_row["entity_type"] == "user_submission"
    assert source_row["source_name"] == "moderation"
    assert source_row["snapshot_date"]
    source_payload = json.loads(source_row["raw_data_json"])
    assert source_payload["from_status"] == "pending"
    assert source_payload["to_status"] == "approved"
    assert source_payload["reviewer_notes"] == "verified"


def test_approved_submission_promotes_menu_item(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _set_test_db(monkeypatch, tmp_path)
    created = restaurant_store.create_submission(
        canonical_name="Power Wrap",
        payload={
            "chain_name": "Fit Hub",
            "category": "Wraps",
            "kcal": 420,
            "protein_g": 28,
            "fat_g": 12,
            "carbs_g": 44,
            "sodium_mg": 640,
        },
    )

    reviewed = restaurant_store.review_submission(created["id"], status="approved")
    assert reviewed is not None
    assert reviewed["status"] == "approved"

    chains = restaurant_store.search_restaurants("fit hub", limit=10, offset=0)
    assert len(chains) == 1
    assert chains[0]["id"] == "fit-hub"
    assert chains[0]["source"] == restaurant_store.SUBMISSION_MENU_SOURCE

    menu = restaurant_store.get_restaurant_menu("fit-hub", limit=10)
    assert len(menu) == 1
    assert menu[0]["item_name"] == "Power Wrap"
    assert menu[0]["category"] == "Wraps"
    assert menu[0]["kcal"] == 420.0
    assert menu[0]["provenance_source"] == restaurant_store.SUBMISSION_MENU_SOURCE
    assert menu[0]["provenance_record_id"] == f"submission-{created['id']}"

    with restaurant_store._connect() as con:
        promoted = con.execute(
            """
            SELECT source_name, source_record_id
            FROM source_catalog
            WHERE entity_type = 'restaurant_menu_item' AND entity_id = ?
            """,
            (menu[0]["id"],),
        ).fetchall()
    assert len(promoted) == 1
    assert promoted[0]["source_name"] == restaurant_store.SUBMISSION_MENU_SOURCE


def test_approved_submission_promotion_is_idempotent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _set_test_db(monkeypatch, tmp_path)
    created = restaurant_store.create_submission(
        canonical_name="Idempotent Bowl",
        payload={"chain_name": "Fit Hub", "kcal": 390},
    )

    first = restaurant_store.review_submission(created["id"], status="approved")
    second = restaurant_store.review_submission(created["id"], status="approved")
    assert first is not None
    assert second is not None
    assert second["status"] == "approved"

    with restaurant_store._connect() as con:
        menu_rows = con.execute(
            """
            SELECT id
            FROM restaurant_menu_items
            WHERE source = ? AND source_id = ?
            """,
            (restaurant_store.SUBMISSION_MENU_SOURCE, f"submission-{created['id']}"),
        ).fetchall()
        promoted_sources = con.execute(
            """
            SELECT raw_data_json
            FROM source_catalog
            WHERE entity_type = 'user_submission' AND entity_id = ?
            ORDER BY created_at ASC, id ASC
            """,
            (created["id"],),
        ).fetchall()
    assert len(menu_rows) == 1
    assert len(promoted_sources) == 2
    first_payload = json.loads(promoted_sources[0]["raw_data_json"])
    second_payload = json.loads(promoted_sources[1]["raw_data_json"])
    assert first_payload["promoted_to_menu"] is True
    assert second_payload["promoted_to_menu"] is False


def test_rejected_submission_does_not_promote_menu_item(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _set_test_db(monkeypatch, tmp_path)
    created = restaurant_store.create_submission(
        canonical_name="Rejected Salad",
        payload={"chain_name": "Fit Hub", "kcal": 120},
    )

    reviewed = restaurant_store.review_submission(created["id"], status="rejected")
    assert reviewed is not None
    assert reviewed["status"] == "rejected"

    with restaurant_store._connect() as con:
        menu_count = con.execute("SELECT COUNT(*) FROM restaurant_menu_items").fetchone()[0]
        promoted_count = con.execute("""
            SELECT COUNT(*)
            FROM source_catalog
            WHERE entity_type = 'restaurant_menu_item'
            """).fetchone()[0]
        moderation_row = con.execute(
            """
            SELECT raw_data_json
            FROM source_catalog
            WHERE entity_type = 'user_submission' AND entity_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (created["id"],),
        ).fetchone()
    assert menu_count == 0
    assert promoted_count == 0
    assert moderation_row is not None
    moderation_payload = json.loads(moderation_row["raw_data_json"])
    assert moderation_payload["promoted_to_menu"] is False


def test_review_submission_rolls_back_on_promotion_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _set_test_db(monkeypatch, tmp_path)
    created = restaurant_store.create_submission(
        canonical_name="Rollback Burger",
        payload={"chain_name": "Fit Hub", "kcal": 500},
    )

    def _boom(*args: object, **kwargs: object) -> bool:
        raise RuntimeError("promotion failed")

    monkeypatch.setattr(restaurant_store, "_upsert_menu_row", _boom)
    with pytest.raises(RuntimeError, match="promotion failed"):
        restaurant_store.review_submission(created["id"], status="approved")

    current = restaurant_store.get_submission(created["id"])
    assert current is not None
    assert current["status"] == "pending"
    assert current["audit"] == []
    with restaurant_store._connect() as con:
        menu_count = con.execute("SELECT COUNT(*) FROM restaurant_menu_items").fetchone()[0]
        moderation_count = con.execute(
            """
            SELECT COUNT(*)
            FROM source_catalog
            WHERE entity_type = 'user_submission' AND entity_id = ?
            """,
            (created["id"],),
        ).fetchone()[0]
    assert menu_count == 0
    assert moderation_count == 0


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


def test_get_restaurant_menu_uses_latest_provenance(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _set_test_db(monkeypatch, tmp_path)
    timestamps = iter(
        [
            "2026-02-24T00:00:00+00:00",
            "2026-02-25T00:00:00+00:00",
        ]
    )
    monkeypatch.setattr(restaurant_store, "_utc_now_iso", lambda: next(timestamps))

    restaurant_store.import_menustat_rows(
        [
            {
                "chain_name": "Test Chain",
                "item_name": "Protein Burger",
                "kcal": 500,
                "source_id": "menu-001",
            }
        ],
        snapshot_date="2026-02-24",
    )
    restaurant_store.import_menustat_rows(
        [
            {
                "chain_name": "Test Chain",
                "item_name": "Protein Burger",
                "kcal": 550,
                "source_id": "menu-001",
            }
        ],
        snapshot_date="2026-02-25",
    )

    menu = restaurant_store.get_restaurant_menu("test-chain", limit=10)
    assert len(menu) == 1
    assert menu[0]["kcal"] == 550.0
    assert menu[0]["snapshot_date"] == "2026-02-25"
    assert menu[0]["provenance_source"] == "menustat"
    assert menu[0]["provenance_record_id"] == "menu-001"


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
