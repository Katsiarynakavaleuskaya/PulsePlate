import builtins
from typing import Any

from core.product_varieties import ProductVarietiesManager, ProductVariety


def test_product_varieties_load_error_branch(tmp_path, monkeypatch):
    # Create an empty file to satisfy Path.exists()
    csv_path = tmp_path / "varieties.csv"
    csv_path.write_text("name,variety,brand\n", encoding="utf-8")

    # Force open() to raise to hit error logging in _load_varieties except
    real_open = builtins.open

    def fake_open(*args: Any, **kwargs: Any):  # noqa: D401
        if str(args[0]) == str(csv_path):
            raise RuntimeError("open fail")
        return real_open(*args, **kwargs)

    monkeypatch.setattr(builtins, "open", fake_open)

    mgr = ProductVarietiesManager(csv_path=str(csv_path))
    # After error, varieties should stay empty
    assert mgr.get_all_products() == []


def test_product_varieties_recommendation_fallback_first_item():
    mgr = ProductVarietiesManager(csv_path="/nonexistent.csv")
    # Manually inject varieties for a product
    v1 = ProductVariety(
        name="Yogurt",
        variety="plain",
        brand="A",
        protein_g=8.0,
        fat_g=2.0,
        carbs_g=10.0,
        fiber_g=0.0,
        sugar_g=9.0,
        Fe_mg=0.0,
        Ca_mg=100.0,
        VitD_IU=0.0,
        B12_ug=0.0,
        Folate_ug=0.0,
        Iodine_ug=0.0,
        K_mg=0.0,
        Mg_mg=0.0,
        flags=set(),
        notes="",
    )
    v2 = ProductVariety(
        name="Yogurt",
        variety="sweet",
        brand="B",
        protein_g=6.0,
        fat_g=3.0,
        carbs_g=14.0,
        fiber_g=0.0,
        sugar_g=12.0,
        Fe_mg=0.0,
        Ca_mg=100.0,
        VitD_IU=0.0,
        B12_ug=0.0,
        Folate_ug=0.0,
        Iodine_ug=0.0,
        K_mg=0.0,
        Mg_mg=0.0,
        flags=set(),
        notes="",
    )
    mgr.varieties["Yogurt"] = [v1, v2]

    # Preferences that filter out all items (require VEG/GF not present) → fallback to first
    rec = mgr.recommend_variety("Yogurt", {"vegetarian": True, "gluten_free": True})
    assert rec is v1
