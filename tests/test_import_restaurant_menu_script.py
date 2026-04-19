from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import pytest

from app.services import restaurant_store
from scripts import import_restaurant_menu


def test_script_imports_sample_csv_into_local_store(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sample_csv = repo_root / "data" / "restaurant_menu_sample.csv"
    worker = os.getenv("PYTEST_XDIST_WORKER", "gw0")
    db_path = tmp_path / f"restaurant_menu_cli_{worker}.sqlite"
    original_db_path = restaurant_store.DB_PATH

    exit_code = import_restaurant_menu.main(
        [
            "--input",
            str(sample_csv),
            "--snapshot-date",
            "2026-02-25",
            "--db-path",
            str(db_path),
        ]
    )
    assert exit_code == 0
    assert restaurant_store.DB_PATH == original_db_path

    monkeypatch.setattr(restaurant_store, "DB_PATH", db_path)
    hits = restaurant_store.search_restaurants("pulse", limit=10, offset=0)
    assert len(hits) == 1
    assert hits[0]["id"] == "pulse-grill"

    menu = restaurant_store.get_restaurant_menu("pulse-grill", limit=10)
    assert len(menu) == 2
    assert menu[0]["provenance_source"] == "menustat"
    assert menu[0]["snapshot_date"] == "2026-02-25"


def test_load_menu_rows_maps_menustat_aliases(tmp_path: Path) -> None:
    csv_path = tmp_path / "menustat_like.csv"
    csv_path.write_text(
        (
            "restaurant,item_name,calories,total_fat,total_carbohydrate,protein,sodium\n"
            "Chain A,Item 1,500,20,55,25,800\n"
        ),
        encoding="utf-8",
    )
    rows = import_restaurant_menu.load_menu_rows(csv_path)
    assert isinstance(rows, list)
    assert len(rows) == 1
    assert rows[0]["chain_name"] == "Chain A"
    assert rows[0]["kcal"] == "500"
    assert rows[0]["fat_g"] == "20"
    assert rows[0]["carbs_g"] == "55"
    assert rows[0]["protein_g"] == "25"
    assert rows[0]["sodium_mg"] == "800"


def test_load_menu_rows_handles_whitespace_in_header_names(tmp_path: Path) -> None:
    csv_path = tmp_path / "menustat_spaced_headers.csv"
    csv_path.write_text(
        ("restaurant ,item_name ,calories\n" "Chain B,Item 2,400\n"),
        encoding="utf-8",
    )
    rows = import_restaurant_menu.load_menu_rows(csv_path)
    assert len(rows) == 1
    assert rows[0]["chain_name"] == "Chain B"
    assert rows[0]["item_name"] == "Item 2"
    assert rows[0]["kcal"] == "400"


def test_load_menu_rows_does_not_use_generic_id_as_source_id(tmp_path: Path) -> None:
    csv_path = tmp_path / "menu_with_generic_id.csv"
    csv_path.write_text(
        ("restaurant,item_name,id\n" "Chain C,Item 3,generic-123\n"),
        encoding="utf-8",
    )
    rows = import_restaurant_menu.load_menu_rows(csv_path)
    assert len(rows) == 1
    assert "source_id" not in rows[0]


def test_main_fails_when_no_valid_rows(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    csv_path = tmp_path / "empty_rows.csv"
    csv_path.write_text("restaurant,item_name\n,\n", encoding="utf-8")

    exit_code = import_restaurant_menu.main(["--input", str(csv_path)])
    assert exit_code == 2
    assert "Import failed:" in capsys.readouterr().err


def test_run_import_routes_to_postgres_bridge(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "menustat_like.csv"
    csv_path.write_text(
        (
            "restaurant,item_name,menu_item_id,calories\n"
            "Chain A,Item 1,item-1,500\n"
            "Chain A,Item 1,item-1,500\n"
        ),
        encoding="utf-8",
    )
    captured: dict[str, object] = {}

    def _fake_bridge(
        rows: list[dict[str, object]],
        *,
        snapshot_date: str | None,
        source_name: str,
        pg_url: str,
    ) -> dict[str, int]:
        captured["rows"] = rows
        captured["snapshot_date"] = snapshot_date
        captured["source_name"] = source_name
        captured["pg_url"] = pg_url
        return {"chains_upserted": 1, "menu_items_upserted": 1}

    monkeypatch.setattr(
        import_restaurant_menu.restaurant_postgres_bridge,
        "import_menustat_rows_to_postgres",
        _fake_bridge,
    )

    summary = import_restaurant_menu.run_import(
        input_path=csv_path,
        snapshot_date="2026-04-13",
        source_name="menustat",
        target_backend=import_restaurant_menu.TARGET_BACKEND_POSTGRES,
        db_path=None,
        pg_url="postgresql+psycopg://user:pass@db.example.com/pulseplate",  # pragma: allowlist secret
    )

    assert summary["target_backend"] == import_restaurant_menu.TARGET_BACKEND_POSTGRES
    assert summary["rows_loaded"] == 2
    assert summary["chains_upserted"] == 1
    assert summary["menu_items_upserted"] == 1
    assert captured["snapshot_date"] == "2026-04-13"
    assert captured["source_name"] == "menustat"
    expected_pg_url = (
        "postgresql+psycopg://user:pass@db.example.com/pulseplate"  # pragma: allowlist secret
    )
    assert captured["pg_url"] == expected_pg_url
    assert isinstance(captured["rows"], list)
    assert captured["rows"] == [
        {
            "chain_name": "Chain A",
            "item_name": "Item 1",
            "source_id": "item-1",
            "kcal": "500",
        },
        {
            "chain_name": "Chain A",
            "item_name": "Item 1",
            "source_id": "item-1",
            "kcal": "500",
        },
    ]


def test_run_import_uses_database_url_for_postgres_target(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "menustat_like.csv"
    csv_path.write_text("restaurant,item_name\nChain A,Item 1\n", encoding="utf-8")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://env-user:env-pass@db/pulseplate",  # pragma: allowlist secret
    )
    captured: dict[str, str] = {}

    def _fake_bridge(
        rows: list[dict[str, object]],
        *,
        snapshot_date: str | None,
        source_name: str,
        pg_url: str,
    ) -> dict[str, int]:
        captured["pg_url"] = pg_url
        return {"chains_upserted": len(rows), "menu_items_upserted": len(rows)}

    monkeypatch.setattr(
        import_restaurant_menu.restaurant_postgres_bridge,
        "import_menustat_rows_to_postgres",
        _fake_bridge,
    )

    summary = import_restaurant_menu.run_import(
        input_path=csv_path,
        snapshot_date=None,
        source_name="menustat",
        target_backend=import_restaurant_menu.TARGET_BACKEND_POSTGRES,
        db_path=None,
        pg_url=None,
    )

    assert summary["target_backend"] == import_restaurant_menu.TARGET_BACKEND_POSTGRES
    expected_env_pg_url = (
        "postgresql+psycopg://env-user:env-pass@db/pulseplate"  # pragma: allowlist secret
    )
    assert captured["pg_url"] == expected_env_pg_url


def test_main_fails_when_input_file_missing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    missing_path = tmp_path / "missing.csv"
    exit_code = import_restaurant_menu.main(["--input", str(missing_path)])
    assert exit_code == 2
    stderr = capsys.readouterr().err
    assert "Import failed:" in stderr
    assert "input file does not exist" in stderr


def test_main_fails_when_postgres_target_has_no_database_url(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    csv_path = tmp_path / "ok.csv"
    csv_path.write_text("restaurant,item_name\nChain A,Item 1\n", encoding="utf-8")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    exit_code = import_restaurant_menu.main(
        ["--input", str(csv_path), "--target-backend", "postgres"]
    )

    assert exit_code == 2
    stderr = capsys.readouterr().err
    assert "Import failed:" in stderr
    assert "postgres target requires --pg-url or DATABASE_URL" in stderr


def test_main_fails_when_postgres_target_uses_db_path(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    csv_path = tmp_path / "ok.csv"
    csv_path.write_text("restaurant,item_name\nChain A,Item 1\n", encoding="utf-8")

    exit_code = import_restaurant_menu.main(
        [
            "--input",
            str(csv_path),
            "--target-backend",
            "postgres",
            "--pg-url",
            "postgresql+psycopg://user:pass@db/pulseplate",  # pragma: allowlist secret
            "--db-path",
            str(tmp_path / "should-not-be-used.sqlite"),
        ]
    )

    assert exit_code == 2
    stderr = capsys.readouterr().err
    assert "Import failed:" in stderr
    assert "--db-path is only supported for sqlite target-backend" in stderr


def test_run_import_rejects_unknown_target_backend(tmp_path: Path) -> None:
    csv_path = tmp_path / "ok.csv"
    csv_path.write_text("restaurant,item_name\nChain A,Item 1\n", encoding="utf-8")

    with pytest.raises(ValueError, match="unsupported target-backend"):
        import_restaurant_menu.run_import(
            input_path=csv_path,
            snapshot_date=None,
            source_name="menustat",
            target_backend="bogus",
            db_path=None,
            pg_url=None,
        )


def test_main_fail_closed_on_postgres_bridge_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    csv_path = tmp_path / "ok.csv"
    csv_path.write_text("restaurant,item_name\nChain A,Item 1\n", encoding="utf-8")

    def _raise_bridge_error(**_: object) -> dict[str, object]:
        raise import_restaurant_menu.restaurant_postgres_bridge.RestaurantPostgresBridgeError(
            "bridge exploded"
        )

    monkeypatch.setattr(import_restaurant_menu, "run_import", _raise_bridge_error)

    exit_code = import_restaurant_menu.main(["--input", str(csv_path)])

    assert exit_code == 2
    stderr = capsys.readouterr().err
    assert "Import failed:" in stderr
    assert "bridge exploded" in stderr


def test_main_fails_when_input_path_is_directory(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = import_restaurant_menu.main(["--input", str(tmp_path)])
    assert exit_code == 2
    stderr = capsys.readouterr().err
    assert "Import failed:" in stderr
    assert "input path is not a file" in stderr


def test_main_fails_when_csv_has_no_header_row(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    csv_path = tmp_path / "headerless.csv"
    csv_path.write_text("", encoding="utf-8")

    exit_code = import_restaurant_menu.main(["--input", str(csv_path)])
    assert exit_code == 2
    stderr = capsys.readouterr().err
    assert "Import failed:" in stderr
    assert "input CSV has no header row" in stderr


def test_main_fails_when_csv_lacks_required_header_aliases(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    csv_path = tmp_path / "missing_aliases.csv"
    csv_path.write_text("foo,bar\nx,y\n", encoding="utf-8")

    exit_code = import_restaurant_menu.main(["--input", str(csv_path)])
    assert exit_code == 2
    stderr = capsys.readouterr().err
    assert "Import failed:" in stderr
    assert "input CSV missing required columns/aliases" in stderr


@pytest.mark.parametrize("bad_date", ["2026/02/25", "20260225"])
def test_main_rejects_invalid_snapshot_date(
    bad_date: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    csv_path = tmp_path / "ok.csv"
    csv_path.write_text("restaurant,item_name\nChain A,Item 1\n", encoding="utf-8")

    with pytest.raises(SystemExit) as exc_info:
        import_restaurant_menu.main(["--input", str(csv_path), "--snapshot-date", bad_date])
    assert exc_info.value.code == 2
    stderr = capsys.readouterr().err
    assert "snapshot-date must be YYYY-MM-DD" in stderr


@pytest.mark.parametrize(
    ("raised_exc", "message"),
    [
        (PermissionError("denied"), "denied"),
        (sqlite3.OperationalError("db locked"), "db locked"),
    ],
)
def test_main_fail_closed_on_os_and_sqlite_errors(
    raised_exc: Exception,
    message: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    csv_path = tmp_path / "ok.csv"
    csv_path.write_text("restaurant,item_name\nChain A,Item 1\n", encoding="utf-8")

    def _raise_error(**_: object) -> dict[str, object]:
        raise raised_exc

    monkeypatch.setattr(import_restaurant_menu, "run_import", _raise_error)
    exit_code = import_restaurant_menu.main(["--input", str(csv_path)])
    assert exit_code == 2
    stderr = capsys.readouterr().err
    assert "Import failed:" in stderr
    assert message in stderr
