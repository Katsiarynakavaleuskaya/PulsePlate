"""
Hypothesis-based integration tests for Plate → Targets micros coverage.
Focus on Fe/Ca/Mg/K micronutrient coverage and day_micros collection.
"""

import os

from fastapi.testclient import TestClient
from hypothesis import given, settings
from hypothesis import strategies as st

import app as app_mod


class TestPlateTargetsMicrosHypothesis:
    """Hypothesis-based tests for Plate → Targets micros integration."""

    def setup_method(self):
        """Set up test environment."""
        os.environ["API_KEY"] = "test_key"
        self.client = TestClient(app_mod.app)

    @given(
        sex=st.sampled_from(["male", "female"]),
        age=st.integers(min_value=18, max_value=65),
        height_cm=st.floats(min_value=150.0, max_value=200.0),
        weight_kg=st.floats(min_value=45.0, max_value=120.0),
        activity=st.sampled_from(
            ["sedentary", "light", "moderate", "active", "very_active"]
        ),
        goal=st.sampled_from(["loss", "maintain", "gain"]),
    )
    @settings(deadline=None)
    def test_plate_targets_micros_integration_hypothesis(
        self,
        sex: str,
        age: int,
        height_cm: float,
        weight_kg: float,
        activity: str,
        goal: str,
    ):
        """Test Plate → Targets micros integration with Hypothesis."""
        base_payload = {
            "sex": sex,
            "age": age,
            "height_cm": height_cm,
            "weight_kg": weight_kg,
            "activity": activity,
            "goal": goal,
        }

        # Step 1: Generate plate
        plate_resp = self.client.post(
            "/api/v1/premium/plate",
            json=base_payload,
            headers={"X-API-Key": "test_key"},
        )
        assert plate_resp.status_code == 200
        plate_data = plate_resp.json()

        # Step 2: Generate targets
        targets_payload = {
            **base_payload,
            "life_stage": "adult",
            "lang": "en",
        }
        targets_resp = self.client.post(
            "/api/v1/premium/targets",
            json=targets_payload,
            headers={"X-API-Key": "test_key"},
        )
        assert targets_resp.status_code == 200
        targets_data = targets_resp.json()

        # Step 3: Verify both have micros data
        assert "day_micros" in plate_data
        assert "priority_micros" in targets_data

        plate_micros = plate_data["day_micros"]
        target_micros = targets_data["priority_micros"]

        # Both should have micronutrient data
        assert len(plate_micros) > 0
        assert len(target_micros) > 0

        # Check for common micronutrients
        common_micros = set(plate_micros.keys()) & set(target_micros.keys())
        assert (
            len(common_micros) > 0
        ), "No common micronutrients between plate and targets"

    @given(
        sex=st.sampled_from(["male", "female"]),
        age=st.integers(min_value=18, max_value=65),
        height_cm=st.floats(min_value=150.0, max_value=200.0),
        weight_kg=st.floats(min_value=45.0, max_value=120.0),
        activity=st.sampled_from(
            ["sedentary", "light", "moderate", "active", "very_active"]
        ),
        goal=st.sampled_from(["loss", "maintain", "gain"]),
    )
    def test_fe_ca_mg_k_coverage_hypothesis(
        self,
        sex: str,
        age: int,
        height_cm: float,
        weight_kg: float,
        activity: str,
        goal: str,
    ):
        """Test Fe/Ca/Mg/K coverage between plate and targets with Hypothesis."""
        base_payload = {
            "sex": sex,
            "age": age,
            "height_cm": height_cm,
            "weight_kg": weight_kg,
            "activity": activity,
            "goal": goal,
        }

        # Generate plate
        plate_resp = self.client.post(
            "/api/v1/premium/plate",
            json=base_payload,
            headers={"X-API-Key": "test_key"},
        )
        assert plate_resp.status_code == 200
        plate_data = plate_resp.json()

        # Generate targets
        targets_payload = {
            **base_payload,
            "life_stage": "adult",
            "lang": "en",
        }
        targets_resp = self.client.post(
            "/api/v1/premium/targets",
            json=targets_payload,
            headers={"X-API-Key": "test_key"},
        )
        assert targets_resp.status_code == 200
        targets_data = targets_resp.json()

        # Check Fe/Ca/Mg/K coverage
        plate_micros = plate_data["day_micros"]
        target_micros = targets_data["priority_micros"]

        # Key micronutrients to check
        key_micros = ["iron", "calcium", "magnesium", "potassium"]
        micro_aliases = {
            "iron": ["iron", "fe", "fe_mg"],
            "calcium": ["calcium", "ca", "ca_mg"],
            "magnesium": ["magnesium", "mg", "mg_mg"],
            "potassium": ["potassium", "k", "k_mg"],
        }

        for micro in key_micros:
            # Find the micro in both datasets (check aliases)
            plate_value = None
            target_value = None

            for alias in micro_aliases[micro]:
                if alias in plate_micros:
                    plate_value = plate_micros[alias]
                if alias in target_micros:
                    target_value = target_micros[alias]

            # At least one should have the micronutrient
            if plate_value is not None or target_value is not None:
                # If both have it, values should be reasonable
                if plate_value is not None and target_value is not None:
                    # Values should be positive
                    assert (
                        plate_value > 0
                    ), f"{micro} plate value should be positive: {plate_value}"
                    assert (
                        target_value > 0
                    ), f"{micro} target value should be positive: {target_value}"

    @given(
        sex=st.sampled_from(["male", "female"]),
        age=st.integers(min_value=18, max_value=65),
        height_cm=st.floats(min_value=150.0, max_value=200.0),
        weight_kg=st.floats(min_value=45.0, max_value=120.0),
        activity=st.sampled_from(
            ["sedentary", "light", "moderate", "active", "very_active"]
        ),
        goal=st.sampled_from(["loss", "maintain", "gain"]),
    )
    def test_day_micros_structure_hypothesis(
        self,
        sex: str,
        age: int,
        height_cm: float,
        weight_kg: float,
        activity: str,
        goal: str,
    ):
        """Test day_micros structure and completeness with Hypothesis."""
        payload = {
            "sex": sex,
            "age": age,
            "height_cm": height_cm,
            "weight_kg": weight_kg,
            "activity": activity,
            "goal": goal,
        }

        # Generate plate
        plate_resp = self.client.post(
            "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
        )
        assert plate_resp.status_code == 200
        plate_data = plate_resp.json()

        # Check day_micros structure
        assert "day_micros" in plate_data
        day_micros = plate_data["day_micros"]

        # Should be a dictionary
        assert isinstance(day_micros, dict)
        assert len(day_micros) > 0

        # Check that values are numeric and positive
        for micro_name, micro_value in day_micros.items():
            assert isinstance(micro_name, str)
            assert len(micro_name) > 0
            assert isinstance(micro_value, (int, float))
            assert micro_value >= 0  # Some micros might be 0

        # Should have at least some common micronutrients
        common_micros = [
            "iron",
            "calcium",
            "magnesium",
            "potassium",
            "vitamin_c",
            "vitamin_d",
        ]
        found_micros = [
            micro
            for micro in common_micros
            if any(micro in key.lower() for key in day_micros.keys())
        ]
        assert (
            len(found_micros) > 0
        ), f"Should have at least some common micronutrients, found: {list(day_micros.keys())}"

    @given(
        sex=st.sampled_from(["male", "female"]),
        age=st.integers(min_value=18, max_value=65),
        height_cm=st.floats(min_value=150.0, max_value=200.0),
        weight_kg=st.floats(min_value=45.0, max_value=120.0),
        activity=st.sampled_from(
            ["sedentary", "light", "moderate", "active", "very_active"]
        ),
        goal=st.sampled_from(["loss", "maintain", "gain"]),
    )
    def test_plate_targets_calorie_alignment_hypothesis(
        self,
        sex: str,
        age: int,
        height_cm: float,
        weight_kg: float,
        activity: str,
        goal: str,
    ):
        """Test calorie alignment between plate and targets with Hypothesis."""
        base_payload = {
            "sex": sex,
            "age": age,
            "height_cm": height_cm,
            "weight_kg": weight_kg,
            "activity": activity,
            "goal": goal,
        }

        # Generate plate
        plate_resp = self.client.post(
            "/api/v1/premium/plate",
            json=base_payload,
            headers={"X-API-Key": "test_key"},
        )
        assert plate_resp.status_code == 200
        plate_data = plate_resp.json()

        # Generate targets
        targets_payload = {
            **base_payload,
            "life_stage": "adult",
            "lang": "en",
        }
        targets_resp = self.client.post(
            "/api/v1/premium/targets",
            json=targets_payload,
            headers={"X-API-Key": "test_key"},
        )
        assert targets_resp.status_code == 200
        targets_data = targets_resp.json()

        # Check calorie alignment
        plate_kcal = plate_data["kcal"]
        target_kcal = targets_data["kcal_daily"]

        # Both should be positive
        assert plate_kcal > 0
        assert target_kcal > 0

        # Should be within reasonable range (1000-5000 kcal)
        assert 1000 <= plate_kcal <= 5000
        assert 1000 <= target_kcal <= 5000

        # Should be reasonably aligned (within 20% for different goals)
        deviation = abs(plate_kcal - target_kcal) / target_kcal
        assert deviation <= 0.2, (
            f"Calorie deviation too high: {deviation:.2%} "
            f"(plate: {plate_kcal}, target: {target_kcal})"
        )

    @given(
        sex=st.sampled_from(["male", "female"]),
        age=st.integers(min_value=18, max_value=65),
        height_cm=st.floats(min_value=150.0, max_value=200.0),
        weight_kg=st.floats(min_value=45.0, max_value=120.0),
        activity=st.sampled_from(
            ["sedentary", "light", "moderate", "active", "very_active"]
        ),
        goal=st.sampled_from(["loss", "maintain", "gain"]),
    )
    def test_plate_targets_macro_alignment_hypothesis(
        self,
        sex: str,
        age: int,
        height_cm: float,
        weight_kg: float,
        activity: str,
        goal: str,
    ):
        """Test macro alignment between plate and targets with Hypothesis."""
        base_payload = {
            "sex": sex,
            "age": age,
            "height_cm": height_cm,
            "weight_kg": weight_kg,
            "activity": activity,
            "goal": goal,
        }

        # Generate plate
        plate_resp = self.client.post(
            "/api/v1/premium/plate",
            json=base_payload,
            headers={"X-API-Key": "test_key"},
        )
        assert plate_resp.status_code == 200
        plate_data = plate_resp.json()

        # Generate targets
        targets_payload = {
            **base_payload,
            "life_stage": "adult",
            "lang": "en",
        }
        targets_resp = self.client.post(
            "/api/v1/premium/targets",
            json=targets_payload,
            headers={"X-API-Key": "test_key"},
        )
        assert targets_resp.status_code == 200
        targets_data = targets_resp.json()

        # Check macro alignment
        plate_macros = plate_data["macros"]
        target_macros = targets_data["macros"]

        # Check common macros
        common_macros = ["protein_g", "fat_g", "carbs_g", "fiber_g"]
        for macro in common_macros:
            if macro in plate_macros and macro in target_macros:
                plate_val = plate_macros[macro]
                target_val = target_macros[macro]

                # Both should be positive
                assert (
                    plate_val > 0
                ), f"{macro} plate value should be positive: {plate_val}"
                assert (
                    target_val > 0
                ), f"{macro} target value should be positive: {target_val}"

                # Should be reasonably aligned (within 50% for macros, especially fiber)
                deviation = abs(plate_val - target_val) / target_val
                max_deviation = (
                    0.8 if macro == "fiber_g" else 0.4
                )  # Allow more deviation for fiber
                assert deviation <= max_deviation, (
                    f"{macro} deviation too high: {deviation:.2%} "
                    f"(plate: {plate_val}, target: {target_val})"
                )

    def test_plate_targets_micros_comprehensive_coverage(self):
        """Test comprehensive micros coverage between plate and targets."""
        # Test with different profiles to ensure comprehensive coverage
        test_profiles = [
            {
                "sex": "female",
                "age": 25,
                "height_cm": 165.0,
                "weight_kg": 55.0,
                "activity": "moderate",
                "goal": "maintain",
            },
            {
                "sex": "male",
                "age": 35,
                "height_cm": 180.0,
                "weight_kg": 80.0,
                "activity": "active",
                "goal": "loss",
            },
            {
                "sex": "female",
                "age": 45,
                "height_cm": 170.0,
                "weight_kg": 65.0,
                "activity": "light",
                "goal": "gain",
            },
        ]

        for profile in test_profiles:
            # Generate plate
            plate_resp = self.client.post(
                "/api/v1/premium/plate", json=profile, headers={"X-API-Key": "test_key"}
            )
            assert plate_resp.status_code == 200
            plate_data = plate_resp.json()

            # Generate targets
            targets_payload = {
                **profile,
                "life_stage": "adult",
                "lang": "en",
            }
            targets_resp = self.client.post(
                "/api/v1/premium/targets",
                json=targets_payload,
                headers={"X-API-Key": "test_key"},
            )
            assert targets_resp.status_code == 200
            targets_data = targets_resp.json()

            # Check comprehensive micros coverage
            plate_micros = plate_data["day_micros"]
            target_micros = targets_data["priority_micros"]

            # Should have substantial micros data
            assert (
                len(plate_micros) >= 5
            ), f"Plate should have at least 5 micronutrients, got {len(plate_micros)}"
            assert (
                len(target_micros) >= 5
            ), f"Targets should have at least 5 micronutrients, got {len(target_micros)}"

            # Check for key micronutrients
            key_micros = [
                "iron",
                "calcium",
                "magnesium",
                "potassium",
                "vitamin_c",
                "vitamin_d",
                "vitamin_b12",
                "folate",
            ]
            found_in_plate = 0
            found_in_targets = 0

            for micro in key_micros:
                if any(micro in key.lower() for key in plate_micros.keys()):
                    found_in_plate += 1
                if any(micro in key.lower() for key in target_micros.keys()):
                    found_in_targets += 1

            # Should find most key micronutrients
            assert (
                found_in_plate >= 4
            ), f"Should find at least 4 key micronutrients in plate, found {found_in_plate}"
            assert (
                found_in_targets >= 4
            ), f"Should find at least 4 key micronutrients in targets, found {found_in_targets}"
