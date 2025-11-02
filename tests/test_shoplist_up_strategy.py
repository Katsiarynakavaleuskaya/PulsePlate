from core.shoplist import ShoplistGenerator, PackagingRule


def test_up_strategy_minimizes_overage_across_candidates():
    """Test that 'up' packaging strategy minimizes overage across all candidates."""
    gen = ShoplistGenerator()
    # 'up' strategy should minimize overage, not just pick first fit.
    # For total_grams=200 and packages [90, 120]:
    # - 90g: ceil(200/90) = 3 packs = 270g (overage: 70g)
    # - 120g: ceil(200/120) = 2 packs = 240g (overage: 40g)
    # Should pick 120g with 2 packs (minimal overage).

    # Test through public API: round_to_packages with custom rules
    aggregated = {"test_product": 200.0}
    custom_rules = {"default": PackagingRule("default", "g", [90, 120], "up")}

    shopping_list = gen.round_to_packages(aggregated, rules=custom_rules)

    assert len(shopping_list) == 1
    item = shopping_list[0]
    # Should pick 120g with 2 packs (minimal overage: 40g vs 70g for 90g)
    assert item.package_size == 120
    assert item.packages_needed == 2
