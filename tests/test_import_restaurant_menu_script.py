from __future__ import annotations

import runpy
from pathlib import Path

import pytest

from app.services import restaurant_store


def _load_script_namespace() -> dict[str, object]:
    repo_root = Path(__file__).resolve().parents[1]
    script_path = repo_root / "scripts" / "import_restaurant_menu.py"
    return runpy.run_path(str(script_path))


def test_script_imports_sample_csv_into_local_store(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    namespace = _load_script_namespace()
    main = namespace["main"]
    assert callable(main)

    repo_root = Path(__file__).resolve().parents[1]
    sample_csv = repo_root / "data" / "restaurant_menu_sample.csv"
    db_path = tmp_path / "restaurant_menu_cli.sqlite"

    exit_code = main(
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

    monkeypatch.setattr(restaurant_store, "DB_PATH", db_path)
    hits = restaurant_store.search_restaurants("pulse", limit=10, offset=0)
    assert len(hits) == 1
    assert hits[0]["id"] == "pulse-grill"

    menu = restaurant_store.get_restaurant_menu("pulse-grill", limit=10)
    assert len(menu) == 2
    assert menu[0]["provenance_source"] == "menustat"
    assert menu[0]["snapshot_date"] == "2026-02-25"


def test_load_menu_rows_maps_menustat_aliases(tmp_path: Path) -> None:
    namespace = _load_script_namespace()
    load_menu_rows = namespace["load_menu_rows"]
    assert callable(load_menu_rows)

    csv_path = tmp_path / "menustat_like.csv"
    csv_path.write_text(
        (
            "restaurant,item_name,calories,total_fat,total_carbohydrate,protein,sodium\n"
            "Chain A,Item 1,500,20,55,25,800\n"
        ),
        encoding="utf-8",
    )
    rows = load_menu_rows(csv_path)
    assert isinstance(rows, list)
    assert len(rows) == 1
    assert rows[0]["chain_name"] == "Chain A"
    assert rows[0]["kcal"] == "500"
    assert rows[0]["fat_g"] == "20"
    assert rows[0]["carbs_g"] == "55"
    assert rows[0]["protein_g"] == "25"
    assert rows[0]["sodium_mg"] == "800"


def test_main_fails_when_no_valid_rows(tmp_path: Path) -> None:
    namespace = _load_script_namespace()
    main = namespace["main"]
    assert callable(main)

    csv_path = tmp_path / "empty_rows.csv"
    csv_path.write_text("restaurant,item_name\n,\n", encoding="utf-8")

    exit_code = main(["--input", str(csv_path)])
    assert exit_code == 2
