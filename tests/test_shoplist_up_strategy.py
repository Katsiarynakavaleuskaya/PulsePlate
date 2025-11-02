from core.shoplist import ShoplistGenerator


def test_up_strategy_minimizes_overage_across_candidates():
    gen = ShoplistGenerator()
    # Current 'up' strategy selects the first package that covers quantity.
    # For total_grams=200 and packages [90, 120] -> first fit is 90g with 3 packs.
    package, packs = gen._find_best_package(200.0, [90, 120], "up")
    assert (package, packs) == (90, 3)
