"""Contract tests for scripts/promote_foods_snapshot_to_postgres.py.

RU: Детерминированный harness для offline promotion foods snapshot -> PostgreSQL.
EN: Deterministic harness for offline foods snapshot -> PostgreSQL promotion.
"""

from __future__ import annotations

from dataclasses import dataclass
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import sys
import uuid

import pytest
from sqlalchemy import Column, Integer, MetaData, Numeric, Table, Text, create_engine, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import URL, make_url

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "promote_foods_snapshot_to_postgres.py"

SQLITE_FOODS_DDL = """
CREATE TABLE foods (
    id TEXT PRIMARY KEY,
    canonical_name TEXT NOT NULL,
    group_name TEXT,
    per_g REAL,
    kcal REAL,
    protein_g REAL,
    fat_g REAL,
    carbs_g REAL,
    fiber_g REAL,
    Fe_mg REAL,
    Ca_mg REAL,
    K_mg REAL,
    Mg_mg REAL,
    VitD_IU REAL,
    B12_ug REAL,
    Folate_ug REAL,
    Iodine_ug REAL,
    flags TEXT,
    brand TEXT,
    gtin TEXT,
    fdc_id TEXT,
    source TEXT,
    source_priority INTEGER,
    version_date TEXT,
    price_per_100g REAL,
    nutrition_inputs_json TEXT,
    nutrition_provenance_json TEXT,
    nutrition_confidence REAL,
    nutrition_nutrient_confidence_json TEXT
)
"""

SQLITE_FOODS_DDL_LEGACY = """
CREATE TABLE foods (
    id TEXT PRIMARY KEY,
    canonical_name TEXT NOT NULL,
    group_name TEXT,
    per_g REAL,
    kcal REAL,
    protein_g REAL,
    fat_g REAL,
    carbs_g REAL,
    fiber_g REAL,
    Fe_mg REAL,
    Ca_mg REAL,
    K_mg REAL,
    Mg_mg REAL,
    VitD_IU REAL,
    B12_ug REAL,
    Folate_ug REAL,
    Iodine_ug REAL,
    flags TEXT,
    brand TEXT,
    gtin TEXT,
    fdc_id TEXT,
    source TEXT,
    source_priority INTEGER,
    version_date TEXT,
    price_per_100g REAL
)
"""

JSON_TEXT_COLUMNS = {
    "flags",
    "nutrition_inputs_json",
    "nutrition_provenance_json",
    "nutrition_nutrient_confidence_json",
}

INSERT_COLUMNS = [
    "id",
    "canonical_name",
    "group_name",
    "per_g",
    "kcal",
    "protein_g",
    "fat_g",
    "carbs_g",
    "fiber_g",
    "Fe_mg",
    "Ca_mg",
    "K_mg",
    "Mg_mg",
    "VitD_IU",
    "B12_ug",
    "Folate_ug",
    "Iodine_ug",
    "flags",
    "brand",
    "gtin",
    "fdc_id",
    "source",
    "source_priority",
    "version_date",
    "price_per_100g",
    "nutrition_inputs_json",
    "nutrition_provenance_json",
    "nutrition_confidence",
    "nutrition_nutrient_confidence_json",
]

LEGACY_INSERT_COLUMNS = [
    "id",
    "canonical_name",
    "group_name",
    "per_g",
    "kcal",
    "protein_g",
    "fat_g",
    "carbs_g",
    "fiber_g",
    "Fe_mg",
    "Ca_mg",
    "K_mg",
    "Mg_mg",
    "VitD_IU",
    "B12_ug",
    "Folate_ug",
    "Iodine_ug",
    "flags",
    "brand",
    "gtin",
    "fdc_id",
    "source",
    "source_priority",
    "version_date",
    "price_per_100g",
]

REPORT_PATH_RELATIVE = Path("artifacts/food_lane/foods_postgres_promotion_report.json")


@dataclass(frozen=True)
class RawJsonText:
    """Preserve raw JSON text for malformed-payload fixtures."""

    value: str


def _load_script_module():
    """Load the non-package promotion script lazily per test."""

    assert SCRIPT_PATH.exists(), (
        "Expected script scripts/promote_foods_snapshot_to_postgres.py to exist. "
        "Implement the script before running this harness."
    )
    spec = importlib.util.spec_from_file_location(
        "promote_foods_snapshot_to_postgres",
        SCRIPT_PATH,
    )
    if spec is None or spec.loader is None:
        raise ImportError("Could not load promote_foods_snapshot_to_postgres module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    sys.modules["scripts.promote_foods_snapshot_to_postgres"] = module
    return module


def _sample_source_rows() -> list[dict[str, object]]:
    return [
        {
            "id": "food.apple.raw",
            "canonical_name": "Apple, raw",
            "group_name": "fruit",
            "per_g": 100.0,
            "kcal": 52.0,
            "protein_g": 0.3,
            "fat_g": 0.2,
            "carbs_g": 14.0,
            "fiber_g": 2.4,
            "Fe_mg": 0.12,
            "Ca_mg": 6.0,
            "K_mg": 107.0,
            "Mg_mg": 5.0,
            "VitD_IU": 0.0,
            "B12_ug": 0.0,
            "Folate_ug": 3.0,
            "Iodine_ug": 0.0,
            "flags": ["fruit", "fresh"],
            "brand": None,
            "gtin": "000111222333",
            "fdc_id": "171688",
            "source": "usda",
            "source_priority": 10,
            "version_date": "2026-04-12T12:00:00+00:00",
            "price_per_100g": 0.49,
            "nutrition_inputs_json": {"serving_basis": "100g", "source": "usda"},
            "nutrition_provenance_json": {"provider": "usda", "pipeline": "build_food_db"},
            "nutrition_confidence": 0.981,
            "nutrition_nutrient_confidence_json": {"kcal": 0.99, "fiber_g": 0.97},
        },
        {
            "id": "food.yogurt.greek.plain",
            "canonical_name": "Greek yogurt, plain",
            "group_name": "dairy",
            "per_g": 100.0,
            "kcal": 97.0,
            "protein_g": 9.0,
            "fat_g": 5.0,
            "carbs_g": 3.9,
            "fiber_g": 0.0,
            "Fe_mg": 0.05,
            "Ca_mg": 100.0,
            "K_mg": 141.0,
            "Mg_mg": 11.0,
            "VitD_IU": 44.0,
            "B12_ug": 0.75,
            "Folate_ug": 7.0,
            "Iodine_ug": 0.0,
            "flags": ["protein", "breakfast"],
            "brand": "PulsePlate Test",
            "gtin": "999888777666",
            "fdc_id": "123456",
            "source": "off",
            "source_priority": 5,
            "version_date": "2026-04-12T12:00:00+00:00",
            "price_per_100g": 1.09,
            "nutrition_inputs_json": {
                "serving_basis": "100g",
                "package_size_g": 450,
            },
            "nutrition_provenance_json": {
                "provider": "off",
                "pipeline": "build_food_db",
            },
            "nutrition_confidence": 0.874,
            "nutrition_nutrient_confidence_json": {"protein_g": 0.95, "Ca_mg": 0.9},
        },
    ]


def _legacy_source_rows() -> list[dict[str, object]]:
    return [
        {
            "id": "food.legacy.apple",
            "canonical_name": "Apple legacy",
            "group_name": "fruit",
            "per_g": 100.0,
            "kcal": 51.0,
            "protein_g": 0.2,
            "fat_g": 0.1,
            "carbs_g": 13.9,
            "fiber_g": 2.2,
            "Fe_mg": 0.11,
            "Ca_mg": 5.0,
            "K_mg": 106.0,
            "Mg_mg": 4.0,
            "VitD_IU": 0.0,
            "B12_ug": 0.0,
            "Folate_ug": 2.0,
            "Iodine_ug": 0.0,
            "flags": ["legacy", "fruit"],
            "brand": None,
            "gtin": "111222333444",
            "fdc_id": "171689",
            "source": "sqlite-snapshot",
            "source_priority": 3,
            "version_date": "2026-04-12T12:00:00+00:00",
            "price_per_100g": 0.39,
        },
    ]


def _serialize_source_cell(value: object) -> object:
    if isinstance(value, RawJsonText):
        return value.value
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False)


def _create_source_sqlite(
    sqlite_path: Path,
    rows: list[dict[str, object]],
    *,
    include_foods_table: bool,
    legacy_shape: bool = False,
) -> Path:
    ddl = SQLITE_FOODS_DDL_LEGACY if legacy_shape else SQLITE_FOODS_DDL
    insert_columns = LEGACY_INSERT_COLUMNS if legacy_shape else INSERT_COLUMNS

    with sqlite3.connect(sqlite_path) as connection:
        cursor = connection.cursor()
        if include_foods_table:
            cursor.execute(ddl)
            placeholders = ",".join("?" for _ in insert_columns)
            insert_sql = (
                f"INSERT INTO foods ({','.join(insert_columns)}) " f"VALUES ({placeholders})"
            )
            for row in rows:
                values = []
                for column_name in insert_columns:
                    value = row[column_name]
                    if column_name in JSON_TEXT_COLUMNS:
                        values.append(_serialize_source_cell(value))
                    else:
                        values.append(value)
                cursor.execute(insert_sql, values)
        connection.commit()
    return sqlite_path


def _postgres_url_or_skip() -> str:
    env_url = os.environ.get("DATABASE_URL")
    if not env_url:
        pytest.skip("DATABASE_URL must be set for PostgreSQL promotion integration tests")
    backend_name = make_url(env_url).get_backend_name()
    if backend_name != "postgresql":
        pytest.skip("Promotion integration tests require a PostgreSQL DATABASE_URL")
    return env_url


def _schema_search_path_url(base_url: str, schema_name: str) -> str:
    url = make_url(base_url)
    query: dict[str, str] = {key: value for key, value in url.query.items()}
    existing_options = query.get("options", "").strip()
    search_path_option = f"-csearch_path={schema_name}"
    query["options"] = (
        f"{existing_options} {search_path_option}".strip()
        if existing_options
        else search_path_option
    )
    updated_url: URL = url.set(query=query)
    return updated_url.render_as_string(hide_password=False)


def _foods_table_metadata(schema_name: str) -> MetaData:
    metadata = MetaData()
    Table(
        "foods",
        metadata,
        # RU: Тестовая таблица повторяет колонковый контракт Alembic revision.
        # EN: Test table mirrors the Alembic revision column contract.
        Column("id", Text, primary_key=True, nullable=False),
        Column("canonical_name", Text, nullable=False),
        Column("group_name", Text, nullable=False),
        Column("per_g", Numeric(8, 2), nullable=False),
        Column("kcal", Numeric(8, 2), nullable=False),
        Column("protein_g", Numeric(8, 2), nullable=False),
        Column("fat_g", Numeric(8, 2), nullable=False),
        Column("carbs_g", Numeric(8, 2), nullable=False),
        Column("fiber_g", Numeric(8, 2), nullable=False),
        Column("Fe_mg", Numeric(10, 3), nullable=False),
        Column("Ca_mg", Numeric(10, 3), nullable=False),
        Column("K_mg", Numeric(10, 3), nullable=False),
        Column("Mg_mg", Numeric(10, 3), nullable=False),
        Column("VitD_IU", Numeric(10, 3), nullable=False),
        Column("B12_ug", Numeric(10, 3), nullable=False),
        Column("Folate_ug", Numeric(10, 3), nullable=False),
        Column("Iodine_ug", Numeric(10, 3), nullable=False),
        Column("flags", JSONB, nullable=False),
        Column("brand", Text, nullable=True),
        Column("gtin", Text, nullable=True),
        Column("fdc_id", Text, nullable=True),
        Column("source", Text, nullable=False),
        Column("source_priority", Integer, nullable=False),
        Column("version_date", Text, nullable=False),
        Column("price_per_100g", Numeric(10, 2), nullable=True),
        Column("nutrition_inputs_json", JSONB, nullable=True),
        Column("nutrition_provenance_json", JSONB, nullable=True),
        Column("nutrition_confidence", Numeric(4, 3), nullable=True),
        Column("nutrition_nutrient_confidence_json", JSONB, nullable=True),
        schema=schema_name,
    )
    return metadata


def _create_target_schema(
    base_url: str,
    schema_name: str,
    *,
    create_foods_table: bool,
) -> tuple[str, str]:
    schema_url = _schema_search_path_url(base_url, schema_name)
    admin_engine = create_engine(base_url, pool_pre_ping=True, future=True)
    metadata = _foods_table_metadata(schema_name)
    try:
        with admin_engine.begin() as connection:
            connection.execute(text(f"CREATE SCHEMA {schema_name}"))
            if create_foods_table:
                metadata.create_all(connection)
    finally:
        admin_engine.dispose()
    return schema_name, schema_url


def _drop_target_schema(base_url: str, schema_name: str) -> None:
    admin_engine = create_engine(base_url, pool_pre_ping=True, future=True)
    try:
        with admin_engine.begin() as connection:
            connection.execute(text(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE"))
    finally:
        admin_engine.dispose()


def _query_target_rows(base_url: str, schema_name: str) -> list[dict[str, object]]:
    engine = create_engine(base_url, pool_pre_ping=True, future=True)
    try:
        with engine.connect() as connection:
            rows = connection.execute(
                text(
                    "SELECT id, flags, nutrition_inputs_json, "
                    "nutrition_provenance_json, nutrition_nutrient_confidence_json "
                    f"FROM {schema_name}.foods ORDER BY id"
                ),
            ).mappings()
            return [dict(row) for row in rows]
    finally:
        engine.dispose()


def _query_target_count(base_url: str, schema_name: str) -> int:
    engine = create_engine(base_url, pool_pre_ping=True, future=True)
    try:
        with engine.connect() as connection:
            return int(
                connection.execute(
                    text(f"SELECT COUNT(*) FROM {schema_name}.foods"),
                ).scalar_one(),
            )
    finally:
        engine.dispose()


def _run_promotion(
    module,
    *,
    sqlite_path: Path,
    pg_url: str,
    batch_size: int,
    report_path: Path,
) -> dict[str, object]:
    promote = getattr(module, "promote_foods_snapshot_to_postgres")
    result = promote(
        sqlite_path=sqlite_path,
        pg_url=pg_url,
        batch_size=batch_size,
        report_path=report_path,
    )
    assert report_path.exists(), "Promotion script must write a JSON report"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if isinstance(result, dict):
        assert result == report
    return report


def _assert_report_shape(report: dict[str, object]) -> None:
    assert isinstance(report["source_count"], int)
    assert isinstance(report["batch_count"], int)
    assert report["batch_count"] >= 1
    checksum = report["checksum"]
    assert isinstance(checksum, str)
    assert checksum


def test_script_exports_expected_entrypoints() -> None:
    module = _load_script_module()

    assert callable(getattr(module, "promote_foods_snapshot_to_postgres", None))
    assert callable(getattr(module, "main", None))


def test_main_forwards_cli_arguments_to_promotion_function(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_script_module()
    captured: dict[str, object] = {}
    test_pg_url = "postgresql://" + "user" + ":" + "pass" + "@localhost/db"

    def fake_promote_foods_snapshot_to_postgres(**kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        report_path = Path(str(kwargs["report_path"]))
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(
                {
                    "source_count": 0,
                    "inserted_count": 0,
                    "updated_count": 0,
                    "batch_count": 0,
                    "checksum": "stub",
                },
            ),
            encoding="utf-8",
        )
        return {
            "source_count": 0,
            "inserted_count": 0,
            "updated_count": 0,
            "batch_count": 0,
            "checksum": "stub",
        }

    monkeypatch.setattr(
        module,
        "promote_foods_snapshot_to_postgres",
        fake_promote_foods_snapshot_to_postgres,
    )
    sqlite_path = tmp_path / "source.sqlite"
    report_path = tmp_path / REPORT_PATH_RELATIVE
    result = module.main(
        [
            "--sqlite-path",
            str(sqlite_path),
            "--pg-url",
            test_pg_url,
            "--batch-size",
            "7",
            "--report-path",
            str(report_path),
        ],
    )

    assert result in (0, None)
    assert str(captured["sqlite_path"]) == str(sqlite_path)
    assert str(captured["pg_url"]) == test_pg_url
    assert captured["batch_size"] == 7
    assert str(captured["report_path"]) == str(report_path)


@pytest.mark.integration
def test_promotion_happy_path_preserves_json_fields(tmp_path: Path) -> None:
    module = _load_script_module()
    base_url = _postgres_url_or_skip()
    sqlite_path = _create_source_sqlite(
        tmp_path / "foods-source.sqlite",
        _sample_source_rows(),
        include_foods_table=True,
    )
    schema_name = f"test_promote_foods_{uuid.uuid4().hex[:12]}"
    _, schema_url = _create_target_schema(base_url, schema_name, create_foods_table=True)
    report_path = tmp_path / REPORT_PATH_RELATIVE

    try:
        report = _run_promotion(
            module,
            sqlite_path=sqlite_path,
            pg_url=schema_url,
            batch_size=1,
            report_path=report_path,
        )
        _assert_report_shape(report)
        assert report["source_count"] == 2
        assert report["inserted_count"] == 2
        assert report["updated_count"] == 0
        assert report["batch_count"] == 2

        rows = _query_target_rows(base_url, schema_name)
        assert len(rows) == 2
        row_by_id = {str(row["id"]): row for row in rows}
        expected_by_id = {row["id"]: row for row in _sample_source_rows()}
        for food_id, expected in expected_by_id.items():
            stored = row_by_id[food_id]
            assert stored["flags"] == expected["flags"]
            assert stored["nutrition_inputs_json"] == expected["nutrition_inputs_json"]
            assert stored["nutrition_provenance_json"] == expected["nutrition_provenance_json"]
            assert (
                stored["nutrition_nutrient_confidence_json"]
                == expected["nutrition_nutrient_confidence_json"]
            )
    finally:
        _drop_target_schema(base_url, schema_name)


@pytest.mark.integration
def test_promotion_is_idempotent_for_same_snapshot(tmp_path: Path) -> None:
    module = _load_script_module()
    base_url = _postgres_url_or_skip()
    sqlite_path = _create_source_sqlite(
        tmp_path / "foods-source.sqlite",
        _sample_source_rows(),
        include_foods_table=True,
    )
    schema_name = f"test_promote_foods_{uuid.uuid4().hex[:12]}"
    _, schema_url = _create_target_schema(base_url, schema_name, create_foods_table=True)

    try:
        first_report = _run_promotion(
            module,
            sqlite_path=sqlite_path,
            pg_url=schema_url,
            batch_size=2,
            report_path=tmp_path / "artifacts/food_lane/first_report.json",
        )
        second_report = _run_promotion(
            module,
            sqlite_path=sqlite_path,
            pg_url=schema_url,
            batch_size=2,
            report_path=tmp_path / "artifacts/food_lane/second_report.json",
        )

        assert first_report["inserted_count"] == 2
        assert first_report["updated_count"] == 0
        assert second_report["inserted_count"] == 0
        assert second_report["updated_count"] == 2
        assert first_report["checksum"] == second_report["checksum"]
        assert _query_target_count(base_url, schema_name) == 2
    finally:
        _drop_target_schema(base_url, schema_name)


@pytest.mark.integration
def test_promotion_supports_legacy_snapshot_without_optional_json_columns(
    tmp_path: Path,
) -> None:
    module = _load_script_module()
    base_url = _postgres_url_or_skip()
    sqlite_path = _create_source_sqlite(
        tmp_path / "foods-source-legacy.sqlite",
        _legacy_source_rows(),
        include_foods_table=True,
        legacy_shape=True,
    )
    schema_name = f"test_promote_foods_{uuid.uuid4().hex[:12]}"
    _, schema_url = _create_target_schema(base_url, schema_name, create_foods_table=True)

    try:
        report = _run_promotion(
            module,
            sqlite_path=sqlite_path,
            pg_url=schema_url,
            batch_size=100,
            report_path=tmp_path / "artifacts/food_lane/legacy_report.json",
        )
        _assert_report_shape(report)
        assert report["source_count"] == 1
        assert report["inserted_count"] == 1
        rows = _query_target_rows(base_url, schema_name)
        assert rows[0]["flags"] == ["legacy", "fruit"]
        assert rows[0]["nutrition_inputs_json"] == []
        assert rows[0]["nutrition_provenance_json"] == {}
        assert rows[0]["nutrition_nutrient_confidence_json"] == {}
    finally:
        _drop_target_schema(base_url, schema_name)


@pytest.mark.integration
def test_promotion_fails_when_source_foods_table_is_missing(tmp_path: Path) -> None:
    module = _load_script_module()
    base_url = _postgres_url_or_skip()
    sqlite_path = _create_source_sqlite(
        tmp_path / "foods-source-missing.sqlite",
        [],
        include_foods_table=False,
    )
    schema_name = f"test_promote_foods_{uuid.uuid4().hex[:12]}"
    _, schema_url = _create_target_schema(base_url, schema_name, create_foods_table=True)

    try:
        with pytest.raises(Exception, match="foods"):
            _run_promotion(
                module,
                sqlite_path=sqlite_path,
                pg_url=schema_url,
                batch_size=100,
                report_path=tmp_path / "artifacts/food_lane/missing_source_report.json",
            )
        assert _query_target_count(base_url, schema_name) == 0
    finally:
        _drop_target_schema(base_url, schema_name)


@pytest.mark.integration
def test_promotion_fails_when_target_foods_table_is_missing(tmp_path: Path) -> None:
    module = _load_script_module()
    base_url = _postgres_url_or_skip()
    sqlite_path = _create_source_sqlite(
        tmp_path / "foods-source.sqlite",
        _sample_source_rows(),
        include_foods_table=True,
    )
    schema_name = f"test_promote_foods_{uuid.uuid4().hex[:12]}"
    _, schema_url = _create_target_schema(base_url, schema_name, create_foods_table=False)

    try:
        with pytest.raises(Exception, match="foods"):
            _run_promotion(
                module,
                sqlite_path=sqlite_path,
                pg_url=schema_url,
                batch_size=100,
                report_path=tmp_path / "artifacts/food_lane/missing_target_report.json",
            )
    finally:
        _drop_target_schema(base_url, schema_name)


@pytest.mark.integration
def test_promotion_fails_deterministically_on_malformed_json(tmp_path: Path) -> None:
    module = _load_script_module()
    base_url = _postgres_url_or_skip()
    malformed_rows = _sample_source_rows()
    malformed_rows[0] = {
        **malformed_rows[0],
        "nutrition_inputs_json": RawJsonText('{"bad_json": '),
    }
    sqlite_path = _create_source_sqlite(
        tmp_path / "foods-source-malformed.sqlite",
        malformed_rows,
        include_foods_table=True,
    )
    schema_name = f"test_promote_foods_{uuid.uuid4().hex[:12]}"
    _, schema_url = _create_target_schema(base_url, schema_name, create_foods_table=True)

    try:
        with pytest.raises(Exception, match="JSON|json|nutrition_inputs_json"):
            _run_promotion(
                module,
                sqlite_path=sqlite_path,
                pg_url=schema_url,
                batch_size=100,
                report_path=tmp_path / "artifacts/food_lane/malformed_report.json",
            )
        assert _query_target_count(base_url, schema_name) == 0
    finally:
        _drop_target_schema(base_url, schema_name)
