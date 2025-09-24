def test_region_catalog_helpers_and_conversion(monkeypatch, tmp_path):
    import csv
    from core import region_catalog as rc

    # Prepare temporary region data
    data_dir = tmp_path / "regions"
    data_dir.mkdir()
    es_csv = data_dir / "es_products.csv"
    with es_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "product_id",
                "name_es",
                "name_en",
                "category",
                "unit",
                "typical_package_size",
                "price_eur",
                "price_usd",
                "store_chain",
                "region",
            ]
        )
        writer.writerow(["p1", "Tomate", "Tomato", "veg", "g", 100, 1.5, 1.7, "ChainA", "ES"])

    # New catalog instance bound to temp data
    cat = rc.RegionCatalog(str(data_dir))
    monkeypatch.setattr(rc, "_region_catalog", cat)

    # Helpers cover get_available_regions and search
    regions = rc.get_available_regions()
    assert "es" in regions

    sr = rc.search_products("tom", "es")
    assert sr.total_count >= 1

    # Test price comparison helper
    cmp_res = rc.get_price_comparison("tomato", ["es", "us"])  # us missing gracefully
    assert "es" in cmp_res and "us" in cmp_res

    # Currency conversion branch
    assert rc.RegionCatalog().convert_currency(10, "EUR", "USD") >= 10
    assert rc.RegionCatalog().convert_currency(10, "USD", "EUR") <= 10
