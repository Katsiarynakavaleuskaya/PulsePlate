# -*- coding: utf-8 -*-
import pytest

import nutrition_plate as np


def test_macro_distribution_field_validator_bounds_direct_call():
    """Directly exercise the field validator logic for out-of-range values.

    Pydantic constraints typically intercept invalid values before the
    validator runs, so we call the validator directly to cover the branch.
    """
    with pytest.raises(ValueError):
        # Exceeds 0..100 window to trigger the check
        np.MacroDistribution.validate_percentages(150)
