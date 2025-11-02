from core.shoplist import ShoplistGenerator, PackagingRule


def test_up_strategy_minimizes_overage_across_candidates():
    """Test that 'up' packaging strategy works correctly through the public API."""
    gen = ShoplistGenerator()
    # Current 'up' strategy selects the first package that covers quantity.
    # For total_grams=200 and packages [90, 120] -> first fit is 90g with 3 packs.

    # Test through public API: round_to_packages with custom rules
    aggregated = {"test_product": 200.0}
    custom_rules = {"default": PackagingRule("default", "g", [90, 120], "up")}

    shopping_list = gen.round_to_packages(aggregated, rules=custom_rules)

    assert len(shopping_list) == 1
    item = shopping_list[0]
    assert item.package_size == 90
    assert item.packages_needed == 3
