from pathlib import Path
from typing import Any

import pytest


def test_bmi_extras_functions_and_errors():
    from core import bmi_extras as extras

    # WHtR normal
    assert extras.wht_ratio(80, 200) == 0.4
    # WHtR errors
    with pytest.raises(ValueError):
        extras.wht_ratio(0, 200)
    with pytest.raises(ValueError):
        extras.wht_ratio(80, 0)

    # WHR normal
    assert extras.whr_ratio(90, 100, "male") == 0.9
    # WHR errors
    with pytest.raises(ValueError):
        extras.whr_ratio(0, 100, "male")
    with pytest.raises(ValueError):
        extras.whr_ratio(90, 0, "female")

    # FFMI with bodyfat
    out = extras.ffmi(80, 180, 20)
    assert out["ffmi"] > 0 and out["ffm_kg"] == 64.0
    # FFMI no bodyfat (estimate path)
    out2 = extras.ffmi(80, 180)
    assert out2["ffm_kg"] == 68.0
    # FFMI errors
    with pytest.raises(ValueError):
        extras.ffmi(0, 180)
    with pytest.raises(ValueError):
        extras.ffmi(80, 0)
    with pytest.raises(ValueError):
        extras.ffmi(80, 180, -1)

    # Interpretations
    assert extras.interpret_wht_ratio(0.35)["category"] == "underweight"
    assert extras.interpret_wht_ratio(0.45)["category"] == "healthy"
    assert extras.interpret_wht_ratio(0.55)["category"] == "overweight"
    assert extras.interpret_wht_ratio(0.65)["category"] == "obese"

    male_risk = extras.interpret_whr_ratio(0.96, "male", "en")
    assert male_risk["risk"] in {"low", "high"}
    female_risk = extras.interpret_whr_ratio(0.81, "female", "en")
    assert female_risk["risk"] in {"low", "high"}

    # Staging
    stage = extras.stage_obesity(bmi=31, wht=0.52, whr=0.97, sex="male", lang="en")
    assert stage["stage"] in {"high_risk", "moderate_risk", "low_risk"}


def test_bmi_extras_low_risk_and_moderate_stage():
    from core import bmi_extras as extras

    # Low risk branches for WHR
    assert extras.interpret_whr_ratio(0.94, "male", "en")["risk"] == "low"
    assert extras.interpret_whr_ratio(0.79, "female", "en")["risk"] == "low"

    # Moderate risk stage: only WHtR high
    mod = extras.stage_obesity(bmi=24.0, wht=0.52, whr=0.7, sex="female", lang="en")
    assert mod["stage"] == "moderate_risk"


def test_product_finder_mkdir_exception_and_loop_exception(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from core.product_finder import ProductFinder

    pf = ProductFinder()

    # Force directory creation to raise
    def boom_mkdir(self: Any, *args: Any, **kwargs: Any):  # noqa: D401
        raise OSError("mkdir fail")

    monkeypatch.setattr(Path, "mkdir", boom_mkdir, raising=False)

    # Also force search_product to raise to hit inner except per item
    def boom_search(name: str):  # noqa: D401
        raise RuntimeError("search fail")

    monkeypatch.setattr(pf, "search_product", boom_search)

    non_existing_dir = tmp_path / "sub" / "data.csv"

    # Redirect file open to an in-memory dummy to avoid FileNotFoundError
    class DummyFile:
        def __init__(self):
            self.closed = False

        def write(self, *_: Any, **__: Any) -> int:
            return 0

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            self.closed = True
            return False

    def fake_open(*args: Any, **kwargs: Any):  # noqa: D401
        return DummyFile()

    monkeypatch.setattr("builtins.open", fake_open)

    results = pf.expand_database(["x"], str(non_existing_dir))
    assert results == {"x": False}


def test_exports_importerror_branch_and_pdf_functions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    import core.exports as exports

    # Deterministic: force the ImportError branch without module reload.
    monkeypatch.setattr(exports, "REPORTLAB_AVAILABLE", False, raising=False)
    with pytest.raises(ImportError):
        exports._import_reportlab_modules()
