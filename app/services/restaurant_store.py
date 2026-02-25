# -*- coding: utf-8 -*-
"""
Restaurant menu store and controlled submission workflow.

RU: Хранилище ресторанных меню и модерируемых пользовательских добавлений.
EN: Restaurant menu storage and moderated submission workflow.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
from typing import Any, Dict, Iterable, Iterator, Optional
from uuid import uuid4

# Keep food and restaurant data in the same SQLite file for local-first lookups.
_env_db_path = os.getenv("FOOD_DB_PATH")
DB_PATH: Path = Path(_env_db_path) if _env_db_path else Path("data/food.sqlite")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

STATUS_PENDING = "pending"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"
_ALLOWED_REVIEW_STATUSES = {STATUS_APPROVED, STATUS_REJECTED}
MAX_RESTAURANT_SEARCH_LIMIT = 100
MAX_RESTAURANT_MENU_LIMIT = 500


def _utc_now_iso() -> str:
    """Return UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def _slugify(value: str) -> str:
    """Build deterministic IDs from external strings.

    RU: Для строк без ASCII-символов используем hash fallback вместо `unknown`,
    чтобы избежать коллизий при upsert.
    EN: For non-ASCII-only strings, use hash fallback instead of `unknown`
    to prevent upsert collisions.
    """
    normalized = value.strip().casefold()
    slug = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")
    if slug:
        return slug
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]
    return f"id-{digest}"


def _as_float(value: Any) -> float | None:
    """Best-effort numeric conversion for optional nutrient fields."""
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        try:
            return float(raw)
        except ValueError:
            return None
    return None


def _validate_pagination(limit: int, offset: int, *, max_limit: int) -> tuple[int, int]:
    """Validate pagination bounds for service-layer callers."""
    if limit < 1:
        raise ValueError("limit must be >= 1")
    if limit > max_limit:
        raise ValueError(f"limit must be <= {max_limit}")
    if offset < 0:
        raise ValueError("offset must be >= 0")
    return limit, offset


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA foreign_keys = ON")
    con.row_factory = sqlite3.Row
    try:
        _ensure_schema(con)
        yield con
    finally:
        con.close()


def _ensure_schema(con: sqlite3.Connection) -> None:
    """Create W3 tables if absent.

    RU: Создаёт минимальную схему W3 (идемпотентно).
    EN: Ensures minimal W3 schema exists (idempotent).
    """
    con.executescript("""
        CREATE TABLE IF NOT EXISTS restaurant_chains (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            country TEXT,
            source TEXT NOT NULL,
            source_id TEXT,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS restaurant_menu_items (
            id TEXT PRIMARY KEY,
            chain_id TEXT NOT NULL,
            item_name TEXT NOT NULL,
            category TEXT,
            serving_size_g REAL,
            kcal REAL,
            protein_g REAL,
            fat_g REAL,
            carbs_g REAL,
            sodium_mg REAL,
            source TEXT NOT NULL,
            source_id TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (chain_id) REFERENCES restaurant_chains(id)
        );

        CREATE TABLE IF NOT EXISTS source_catalog (
            id TEXT PRIMARY KEY,
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            source_name TEXT NOT NULL,
            source_record_id TEXT,
            snapshot_date TEXT,
            raw_data_json TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS user_submissions (
            id TEXT PRIMARY KEY,
            entity_type TEXT NOT NULL,
            canonical_name TEXT NOT NULL,
            barcode TEXT,
            off_url TEXT,
            payload_json TEXT NOT NULL,
            status TEXT NOT NULL,
            reviewer_notes TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS submission_audit (
            id TEXT PRIMARY KEY,
            submission_id TEXT NOT NULL,
            from_status TEXT,
            to_status TEXT NOT NULL,
            reviewer_notes TEXT,
            changed_at TEXT NOT NULL,
            FOREIGN KEY (submission_id) REFERENCES user_submissions(id)
        );

        CREATE INDEX IF NOT EXISTS idx_restaurant_chains_name
            ON restaurant_chains(name);
        CREATE INDEX IF NOT EXISTS idx_restaurant_menu_items_chain
            ON restaurant_menu_items(chain_id);
        CREATE INDEX IF NOT EXISTS idx_user_submissions_status
            ON user_submissions(status);
        CREATE INDEX IF NOT EXISTS idx_submission_audit_submission
            ON submission_audit(submission_id);
        CREATE INDEX IF NOT EXISTS idx_source_catalog_entity
            ON source_catalog(entity_type, entity_id, created_at, id);
        """)
    con.commit()


def import_menustat_rows(
    rows: Iterable[Dict[str, Any]],
    *,
    snapshot_date: str | None = None,
    source_name: str = "menustat",
) -> Dict[str, int]:
    """
    Import normalized MenuStat-like rows.

    Expected keys:
    - chain_name, item_name (required)
    - category, serving_size_g, kcal, protein_g, fat_g, carbs_g, sodium_mg, source_id
    """
    snapshot = snapshot_date or datetime.now(timezone.utc).date().isoformat()
    chains_upserted = 0
    items_upserted = 0
    with _connect() as con:
        for row in rows:
            chain_name = str(row.get("chain_name", "")).strip()
            item_name = str(row.get("item_name", "")).strip()
            if not chain_name or not item_name:
                continue
            chain_id = _slugify(chain_name)
            now_iso = _utc_now_iso()
            country = str(row.get("country", "US")).strip() or "US"
            source_id = str(row.get("source_id", "")).strip() or None

            con.execute(
                """
                INSERT INTO restaurant_chains (id, name, country, source, source_id, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    country = excluded.country,
                    source = excluded.source,
                    source_id = excluded.source_id,
                    updated_at = excluded.updated_at
                """,
                (chain_id, chain_name, country, source_name, source_id, now_iso),
            )
            chains_upserted += 1

            menu_source_part = source_id or _slugify(item_name)
            menu_id = f"{chain_id}:{menu_source_part}"
            con.execute(
                """
                INSERT INTO restaurant_menu_items (
                    id, chain_id, item_name, category, serving_size_g, kcal, protein_g,
                    fat_g, carbs_g, sodium_mg, source, source_id, is_active, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                ON CONFLICT(id) DO UPDATE SET
                    chain_id = excluded.chain_id,
                    item_name = excluded.item_name,
                    category = excluded.category,
                    serving_size_g = excluded.serving_size_g,
                    kcal = excluded.kcal,
                    protein_g = excluded.protein_g,
                    fat_g = excluded.fat_g,
                    carbs_g = excluded.carbs_g,
                    sodium_mg = excluded.sodium_mg,
                    source = excluded.source,
                    source_id = excluded.source_id,
                    is_active = excluded.is_active,
                    updated_at = excluded.updated_at
                """,
                (
                    menu_id,
                    chain_id,
                    item_name,
                    str(row.get("category", "")).strip() or None,
                    _as_float(row.get("serving_size_g")),
                    _as_float(row.get("kcal")),
                    _as_float(row.get("protein_g")),
                    _as_float(row.get("fat_g")),
                    _as_float(row.get("carbs_g")),
                    _as_float(row.get("sodium_mg")),
                    source_name,
                    source_id,
                    now_iso,
                ),
            )
            items_upserted += 1
            con.execute(
                """
                INSERT INTO source_catalog (
                    id, entity_type, entity_id, source_name, source_record_id,
                    snapshot_date, raw_data_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid4()),
                    "restaurant_menu_item",
                    menu_id,
                    source_name,
                    source_id,
                    snapshot,
                    json.dumps(row, ensure_ascii=True),
                    now_iso,
                ),
            )
        con.commit()
    return {"chains_upserted": chains_upserted, "menu_items_upserted": items_upserted}


def search_restaurants(query: str, limit: int = 20, offset: int = 0) -> list[Dict[str, Any]]:
    """Search restaurant chains from local canonical DB."""
    limit, offset = _validate_pagination(
        limit=limit,
        offset=offset,
        max_limit=MAX_RESTAURANT_SEARCH_LIMIT,
    )
    pattern = f"%{(query or '').strip().lower()}%"
    with _connect() as con:
        rows = con.execute(
            """
            SELECT id, name, country, source
            FROM restaurant_chains
            WHERE lower(name) LIKE ?
            ORDER BY name ASC
            LIMIT ? OFFSET ?
            """,
            (pattern, limit, offset),
        ).fetchall()
    return [dict(row) for row in rows]


def get_restaurant_menu(chain_id: str, limit: int = 200) -> list[Dict[str, Any]]:
    """Return active menu rows for a restaurant chain."""
    limit, _ = _validate_pagination(
        limit=limit,
        offset=0,
        max_limit=MAX_RESTAURANT_MENU_LIMIT,
    )
    with _connect() as con:
        rows = con.execute(
            """
            SELECT
                m.id,
                m.chain_id,
                m.item_name,
                m.category,
                m.serving_size_g,
                m.kcal,
                m.protein_g,
                m.fat_g,
                m.carbs_g,
                m.sodium_mg,
                m.source,
                m.source_id,
                m.is_active,
                sc.snapshot_date AS snapshot_date,
                sc.source_name AS provenance_source,
                sc.source_record_id AS provenance_record_id
            FROM restaurant_menu_items AS m
            LEFT JOIN source_catalog AS sc
                ON sc.id = (
                    SELECT latest.id
                    FROM source_catalog AS latest
                    WHERE latest.entity_type = 'restaurant_menu_item'
                      AND latest.entity_id = m.id
                    ORDER BY latest.created_at DESC, latest.id DESC
                    LIMIT 1
                )
            WHERE m.chain_id = ? AND m.is_active = 1
            ORDER BY m.item_name ASC
            LIMIT ?
            """,
            (chain_id, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def _normalize_submission_record(row: sqlite3.Row, audit_rows: list[sqlite3.Row]) -> Dict[str, Any]:
    payload: dict[str, Any]
    try:
        payload = json.loads(row["payload_json"]) if row["payload_json"] else {}
    except json.JSONDecodeError:
        payload = {}
    record = dict(row)
    record["payload"] = payload
    record.pop("payload_json", None)
    record["audit"] = [dict(audit_row) for audit_row in audit_rows]
    return record


def create_submission(
    *,
    canonical_name: str,
    payload: dict[str, Any] | None = None,
    barcode: str | None = None,
    off_url: str | None = None,
    entity_type: str = "restaurant_menu",
) -> Dict[str, Any]:
    """Create a controlled submission in pending state."""
    clean_name = canonical_name.strip()
    if not clean_name:
        raise ValueError("canonical_name is required")
    payload_value = payload or {}
    now_iso = _utc_now_iso()
    submission_id = str(uuid4())
    with _connect() as con:
        con.execute(
            """
            INSERT INTO user_submissions (
                id, entity_type, canonical_name, barcode, off_url, payload_json,
                status, reviewer_notes, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?, ?)
            """,
            (
                submission_id,
                entity_type,
                clean_name,
                barcode,
                off_url,
                json.dumps(payload_value, ensure_ascii=True),
                STATUS_PENDING,
                now_iso,
                now_iso,
            ),
        )
        con.commit()
    record = get_submission(submission_id)
    if record is None:
        raise RuntimeError("failed to persist submission")
    return record


def get_submission(submission_id: str) -> Optional[Dict[str, Any]]:
    with _connect() as con:
        row = con.execute(
            """
            SELECT id, entity_type, canonical_name, barcode, off_url, payload_json,
                   status, reviewer_notes, created_at, updated_at
            FROM user_submissions
            WHERE id = ?
            """,
            (submission_id,),
        ).fetchone()
        if row is None:
            return None
        audit_rows = con.execute(
            """
            SELECT id, from_status, to_status, reviewer_notes, changed_at
            FROM submission_audit
            WHERE submission_id = ?
            ORDER BY changed_at ASC
            """,
            (submission_id,),
        ).fetchall()
    return _normalize_submission_record(row, list(audit_rows))


def review_submission(
    submission_id: str, *, status: str, reviewer_notes: str | None = None
) -> Optional[Dict[str, Any]]:
    """Move submission to approved/rejected and append audit transition."""
    if status not in _ALLOWED_REVIEW_STATUSES:
        raise ValueError("status must be one of: approved, rejected")

    now_iso = _utc_now_iso()
    with _connect() as con:
        current = con.execute(
            "SELECT id, status FROM user_submissions WHERE id = ?",
            (submission_id,),
        ).fetchone()
        if current is None:
            return None

        from_status = str(current["status"])
        con.execute(
            """
            UPDATE user_submissions
            SET status = ?, reviewer_notes = ?, updated_at = ?
            WHERE id = ?
            """,
            (status, reviewer_notes, now_iso, submission_id),
        )
        audit_id = str(uuid4())
        con.execute(
            """
            INSERT INTO submission_audit (
                id, submission_id, from_status, to_status, reviewer_notes, changed_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (audit_id, submission_id, from_status, status, reviewer_notes, now_iso),
        )
        con.execute(
            """
            INSERT INTO source_catalog (
                id, entity_type, entity_id, source_name, source_record_id,
                snapshot_date, raw_data_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                "user_submission",
                submission_id,
                "moderation",
                audit_id,
                now_iso.split("T", maxsplit=1)[0],
                json.dumps(
                    {
                        "from_status": from_status,
                        "to_status": status,
                        "reviewer_notes": reviewer_notes,
                    },
                    ensure_ascii=True,
                ),
                now_iso,
            ),
        )
        con.commit()
    return get_submission(submission_id)
