from core.region_catalog import RegionCatalog


def test_region_catalog_unknown_region_and_category(tmp_path):
    # Create empty data dir (no regions)
    rc = RegionCatalog(data_dir=str(tmp_path / "regions"))
    # Unknown region returns empty constructs
    assert rc.search_products("milk", region="es").total_count == 0
    assert rc.get_products_by_category("unknown", region="es") == []
    assert rc.get_categories(region="es") == []


def test_disclaimers_fallback_language():
    from core.disclaimers import MEDICAL_DISCLAIMER

    # Use a non-existent language key to force fallback behavior
    msg = MEDICAL_DISCLAIMER.get("xx", MEDICAL_DISCLAIMER.get("en", ""))
    assert isinstance(msg, str) and msg != ""
