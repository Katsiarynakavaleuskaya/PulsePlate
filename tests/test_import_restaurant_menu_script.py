from __future__ import annotations

import os
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


def test_main_fails_when_no_valid_rows(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    csv_path = tmp_path / "empty_rows.csv"
    csv_path.write_text("restaurant,item_name\n,\n", encoding="utf-8")

    exit_code = import_restaurant_menu.main(["--input", str(csv_path)])
    assert exit_code == 2
    assert "Import failed:" in capsys.readouterr().err


def test_main_fails_when_input_file_missing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    missing_path = tmp_path / "missing.csv"
    exit_code = import_restaurant_menu.main(["--input", str(missing_path)])
    assert exit_code == 2
    stderr = capsys.readouterr().err
    assert "Import failed:" in stderr
    assert "input file does not exist" in stderr


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


def test_main_rejects_invalid_snapshot_date(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    csv_path = tmp_path / "ok.csv"
    csv_path.write_text("restaurant,item_name\nChain A,Item 1\n", encoding="utf-8")

    with pytest.raises(SystemExit) as exc_info:
        import_restaurant_menu.main(["--input", str(csv_path), "--snapshot-date", "2026/02/25"])
    assert exc_info.value.code == 2
    stderr = capsys.readouterr().err
    assert "snapshot-date must be YYYY-MM-DD" in stderr
