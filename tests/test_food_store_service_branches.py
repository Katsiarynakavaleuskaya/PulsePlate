import csv
import io
import os
import sys
import importlib.util
from pathlib import Path
from typing import Any, Mapping, Sequence

import pytest

# Load food_store module - first check sys.modules, otherwise load from file
if "food_store" in sys.modules:
    fs = sys.modules["food_store"]
else:
    spec = importlib.util.spec_from_file_location(
        "food_store",
        os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "app", "services", "food_store.py"
        ),
    )
    if spec is None or spec.loader is None:
        raise ImportError("Cannot load food_store module")
    fs_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fs_module)
    fs = fs_module


def resolve_attr(name: str) -> Any:
    """Helper to resolve attributes from the food_store module for test patching."""
    return getattr(fs, name)


def test_safe_float_invalid_returns_zero() -> None:
    assert fs._safe_float(None) == 0.0
    assert fs._safe_float("not-a-number") == 0.0


def test_validate_csv_quotes_strict_typeerror_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Prepare a simple valid CSV
    csv_path = tmp_path / "valid.csv"
    csv_path.write_text("a,b\n1,2\n", encoding="utf-8")

    original_reader = csv.reader

    def reader_with_typeerror(f: Any, *args: Any, **kwargs: Any):
        # Simulate Python<3.12 behavior when strict is passed
        if "strict" in kwargs:
            raise TypeError("strict not supported")
        return original_reader(f)

    monkeypatch.setattr(csv, "reader", reader_with_typeerror)

    assert fs._validate_csv_quotes(csv_path, is_production=False) is True


def test_validate_csv_quotes_csv_error_in_production_returns_false(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Create a file and force csv.Error during iteration
    csv_path = tmp_path / "malformed.csv"
    csv_path.write_text('bad,data\n"unclosed quote\n', encoding="utf-8")

    class FailingReader:
        def __iter__(self):
            raise csv.Error("malformed")

    def reader(_: Any, *args: Any, **kwargs: Any):
        return FailingReader()

    monkeypatch.setattr(csv, "reader", reader)

    assert fs._validate_csv_quotes(csv_path, is_production=True) is False


@pytest.mark.parametrize(
    "ing, expected",
    [
        ("not-a-mapping", None),  # not a mapping
        ({}, None),  # missing food_id
        ({"food_id": " ", "grams": 10}, None),  # blank food_id
        ({"food_id": "f1", "grams": object()}, None),  # unsupported grams type
        ({"food_id": "f1", "grams": "abc"}, None),  # non-numeric grams triggers ValueError
        ({"food_id": "f1", "grams": -5}, None),  # negative grams
        ({"food_id": "f1", "grams": 0}, ("f1", 0.0)),  # valid edge
    ],
)
def test_validate_ingredient_mapping_various(ing: Mapping[str, Any] | str, expected: Any) -> None:
    assert fs._validate_ingredient_mapping(ing) == expected  # type: ignore[arg-type]


def test_safe_per_g_invalid_and_zero() -> None:
    assert fs._safe_per_g("oops", "f1") == fs.DEFAULT_PER_G
    assert fs._safe_per_g(0, "f1") == fs.DEFAULT_PER_G


def test_nutrients_for_empty_and_valid_sequence() -> None:
    # Empty sequence returns zeros for known keys
    result_empty = fs.nutrients_for([])
    assert isinstance(result_empty, dict)
    assert all(v == 0.0 for v in result_empty.values())

    # Minimal valid ingredient; get_food is used by aggregator in app layer, here we just validate stability
    aggregated = fs.nutrients_for([{"food_id": "x", "grams": 0}])
    assert isinstance(aggregated, dict)


@pytest.mark.parametrize(
    "limit, offset, ok",
    [(1, 0, True), ("5", "2", True), (0, 0, False), ("bad", 0, False), (1, "bad", False)],
)
def test_validate_pagination_params(limit: int | str, offset: int | str, ok: bool) -> None:
    if ok:
        norm_limit, norm_offset = fs._validate_pagination_params(limit, offset)
        assert isinstance(norm_limit, int) and isinstance(norm_offset, int)
        assert norm_limit >= 1 and norm_offset >= 0
    else:
        with pytest.raises(ValueError):
            fs._validate_pagination_params(limit, offset)
