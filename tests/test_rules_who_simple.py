from core import rules_who_simple as rules


def test_who_activity_and_micro_rda_present():
    assert "adult" in rules.WHO_ACTIVITY
    assert rules.WHO_ACTIVITY["adult"]["moderate_min_week"] == 150
    assert ("female", "19-50") in rules.WHO_MICRO_RDA
    assert rules.WHO_MICRO_RDA[("male", "19-50")]["Fe_mg"] == 8
