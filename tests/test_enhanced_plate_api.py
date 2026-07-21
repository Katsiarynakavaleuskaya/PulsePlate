"""
Tests for Enhanced My Plate API endpoint

Tests cover:
- Visual plate layout generation
- Hand/cup portion calculations
- Deficit/surplus percentage control
- Diet flags functionality
- Macro distribution validation
- Visual shape specification
- Goal-specific recommendations
- Error handling and edge cases
"""

import os

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.middleware.api_tiers import TEST_KEY_PRO
from app.services import pro_nutrition_plate
from app.services.pro_nutrition_targets import WHO_TARGETS_SAFETY_VALIDATION_FAILED_DETAIL

# Import the FastAPI app from the app package
from app import app
from app.http_error_details import (
    ENHANCED_PLATE_GENERATION_FAILED_DETAIL,
    INVALID_PREMIUM_PLATE_INPUT_DETAIL,
)

client = TestClient(app)


class TestEnhancedPlateAPI:
    """Test Enhanced My Plate API endpoint."""

    def setup_method(self) -> None:
        """Set up test environment."""
        os.environ["API_KEY"] = "test_key"
        os.environ["FEATURE_PREMIUM_NUTRITION"] = "true"

    def test_plate_contract_basic(self) -> None:
        """Test basic plate API contract with all required fields."""
        payload = {
            "sex": "female",
            "age": 30,
            "height_cm": 170,
            "weight_kg": 65,
            "activity": "moderate",
            "goal": "loss",
            "deficit_pct": 15,
            "diet_flags": ["LOW_COST", "DAIRY_FREE"],
        }

        response = client.post(
            "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
        )

        assert response.status_code == 200
        data = response.json()

        # Check required response structure
        assert set(data.keys()) == {
            "kcal",
            "macros",
            "portions",
            "layout",
            "meals",
            "day_micros",
            "meals_per_day",
        }
        assert data["kcal"] > 1000
        assert all(k in data["macros"] for k in ("protein_g", "fat_g", "carbs_g", "fiber_g"))
        assert isinstance(data["layout"], list) and len(data["layout"]) >= 4
        assert data["layout"][0]["kind"] in ("plate_sector", "bowl", "marker")

    def test_plate_visual_layout_structure(self) -> None:
        """Test visual layout contains proper plate sectors and bowls."""
        payload = {
            "sex": "male",
            "age": 25,
            "height_cm": 180,
            "weight_kg": 75,
            "activity": "active",
            "goal": "maintain",
        }

        response = client.post(
            "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
        )

        assert response.status_code == 200
        data = response.json()

        layout = data["layout"]
        # Should have 4 sectors + 2 bowls = 6 items
        assert len(layout) == 6

        # Check sector types
        sectors = [item for item in layout if item["kind"] == "plate_sector"]
        bowls = [item for item in layout if item["kind"] == "bowl"]

        assert len(sectors) == 4  # Vegetables, Protein, Carbs, Fat
        assert len(bowls) == 2  # Grain cup, Vegetable cup

        # Check all have required fields
        for item in layout:
            assert "kind" in item
            assert "fraction" in item
            assert "label" in item
            assert "tooltip" in item
            assert isinstance(item["fraction"], (int, float))
            assert 0 <= item["fraction"] <= 1.5  # Allow cups > 1

    def test_plate_portions_hand_cup_method(self) -> None:
        """Test portions are converted to hand/cup measurements."""
        payload = {
            "sex": "female",
            "age": 35,
            "height_cm": 165,
            "weight_kg": 60,
            "activity": "light",
            "goal": "gain",
            "surplus_pct": 10,
        }

        response = client.post(
            "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
        )

        assert response.status_code == 200
        data = response.json()

        portions = data["portions"]
        # Check hand/cup portion fields (meals_per_day is now metadata, not in portions)
        required_portion_keys = {
            "protein_palm",
            "fat_thumbs",
            "carb_cups",
            "veg_cups",
        }
        assert required_portion_keys.issubset(set(portions.keys()))

        # Check reasonable portion values
        assert 0.5 <= portions["protein_palm"] <= 4.0  # Palms per meal
        assert 0.3 <= portions["fat_thumbs"] <= 3.0  # Thumbs per meal
        assert 0.5 <= portions["carb_cups"] <= 3.0  # Cups per meal
        assert 0.5 <= portions["veg_cups"] <= 4.0  # Vegetable cups per meal
        # meals_per_day is now a top-level field in the response
        assert data["meals_per_day"] == 3

    def test_plate_deficit_surplus_control(self) -> None:
        """Test precise deficit and surplus percentage control."""
        base_payload = {
            "sex": "male",
            "age": 30,
            "height_cm": 175,
            "weight_kg": 70,
            "activity": "moderate",
        }

        # Test different deficit percentages for loss
        for deficit in [10, 15, 20]:
            payload = {**base_payload, "goal": "loss", "deficit_pct": deficit}
            response = client.post(
                "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
            )
            assert response.status_code == 200
            data = response.json()
            # Higher deficit should mean fewer calories
            assert data["kcal"] >= 1200  # Minimum safety threshold

        # Test different surplus percentages for gain
        for surplus in [8, 12, 15]:
            payload = {**base_payload, "goal": "gain", "surplus_pct": surplus}
            response = client.post(
                "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["kcal"] > 2000  # Should be above maintenance

    def test_plate_diet_flags_functionality(self) -> None:
        """Test diet flags affect meal suggestions."""
        base_payload = {
            "sex": "female",
            "age": 28,
            "height_cm": 168,
            "weight_kg": 62,
            "activity": "moderate",
            "goal": "maintain",
        }

        # Test VEG flag
        payload = {**base_payload, "diet_flags": ["VEG"]}
        response = client.post(
            "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
        )
        assert response.status_code == 200
        data = response.json()

        meals_text = " ".join([meal["title"] for meal in data["meals"]])
        assert "тофу" in meals_text or "нут" in meals_text  # Should suggest plant proteins

        # Test GF flag
        payload = {**base_payload, "diet_flags": ["GF"]}
        response = client.post(
            "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
        )
        assert response.status_code == 200
        data = response.json()

        meals_text = " ".join([meal["title"] for meal in data["meals"]])
        # Should prefer gluten-free grains like buckwheat
        assert "Гречка" in meals_text or "гречка" in meals_text

        # Test LOW_COST flag
        payload = {**base_payload, "diet_flags": ["LOW_COST"]}
        response = client.post(
            "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
        )
        assert response.status_code == 200
        data = response.json()

        meals_text = " ".join([meal["title"] for meal in data["meals"]])
        assert "(бюджет)" in meals_text  # Should mark budget options

    def test_plate_macro_consistency(self) -> None:
        """Test macro distribution consistency and calculations."""
        payload = {
            "sex": "male",
            "age": 35,
            "height_cm": 185,
            "weight_kg": 80,
            "activity": "active",
            "goal": "maintain",
        }

        response = client.post(
            "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
        )

        assert response.status_code == 200
        data = response.json()

        macros = data["macros"]
        kcal = data["kcal"]

        # Check macro ranges are reasonable
        assert 50 <= macros["protein_g"] <= 200
        assert 40 <= macros["fat_g"] <= 150
        assert 100 <= macros["carbs_g"] <= 600  # Allow higher carbs for very active individuals
        # fiber_g can vary based on targets or calculations; accept reasonable range
        assert (
            25 <= macros["fiber_g"] <= 50
        ), f"Expected fiber_g between 25-50, got {macros['fiber_g']}"

        # Verify calorie calculation consistency (4/4/9 rule)
        calculated_kcal = (
            (macros["protein_g"] * 4) + (macros["carbs_g"] * 4) + (macros["fat_g"] * 9)
        )
        # Allow 5% variance for rounding
        assert abs(calculated_kcal - kcal) / kcal <= 0.05

    def test_plate_macro_coercion_fallback_keeps_response_valid(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Cover macro coercion fallback when float conversion fails for a custom macro value."""

        class FloatFailIntOk:
            def __float__(self) -> float:
                raise TypeError("float conversion disabled for coverage path")

            def __int__(self) -> int:
                return 7

        def _mock_align(*_args: object, **_kwargs: object) -> tuple[dict[str, object], int, bool]:
            return (
                {
                    "protein_g": 120,
                    "fat_g": 60,
                    "carbs_g": 200,
                    "fiber_g": 30,
                    "custom_bad": FloatFailIntOk(),
                },
                2300,
                True,
            )

        monkeypatch.setattr(
            pro_nutrition_plate,
            "align_macros_with_targets",
            _mock_align,
        )

        payload = {
            "sex": "female",
            "age": 30,
            "height_cm": 170,
            "weight_kg": 65,
            "activity": "moderate",
            "goal": "maintain",
        }
        response = client.post(
            "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
        )

        assert response.status_code == 400
        assert response.headers.get("content-type", "").startswith("application/json")
        assert response.json()["detail"] == ENHANCED_PLATE_GENERATION_FAILED_DETAIL
        assert "custom_bad" not in response.text

    def test_plate_error_hygiene_does_not_leak_raw_value_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _raise_sensitive_value_error(*_args: object, **_kwargs: object) -> dict[str, object]:
            raise ValueError("secret provider trace at /srv/pulseplate/plate.py")

        monkeypatch.setattr(
            pro_nutrition_plate.nutrition_plate,
            "make_plate",
            _raise_sensitive_value_error,
        )

        payload = {
            "sex": "female",
            "age": 30,
            "height_cm": 170,
            "weight_kg": 65,
            "activity": "moderate",
            "goal": "maintain",
        }
        response = client.post(
            "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
        )

        assert response.status_code == 400
        assert response.headers.get("content-type", "").startswith("application/json")
        assert response.json()["detail"] == INVALID_PREMIUM_PLATE_INPUT_DETAIL
        assert "/srv/pulseplate/plate.py" not in response.text

    @pytest.mark.parametrize(
        "invalid_micro",
        [
            pytest.param("NaN", id="nan"),
            pytest.param("Infinity", id="infinity"),
            pytest.param("-Infinity", id="negative-infinity"),
            pytest.param("1e309", id="exponent-overflow"),
            pytest.param(-0.01, id="negative-finite"),
            pytest.param(100000.01, id="above-canonical-maximum"),
        ],
    )
    @pytest.mark.parametrize(
        ("route", "headers"),
        [
            pytest.param(
                "/api/v1/pro/nutrition/plate",
                {"X-API-Key": TEST_KEY_PRO},
                id="canonical",
            ),
            pytest.param(
                "/api/v1/premium/plate",
                {"X-API-Key": "test_key"},
                id="legacy",
            ),
        ],
    )
    def test_plate_non_finite_day_micros_is_safe_500_at_http_boundary(
        self,
        monkeypatch: pytest.MonkeyPatch,
        invalid_micro: object,
        route: str,
        headers: dict[str, str],
    ) -> None:
        """Invalid enriched day micros never become a null-bearing false 200."""

        def _non_finite_day_micros(
            _meals: list[dict[str, object]],
        ) -> dict[str, object]:
            return {"private_dependency_nutrient": invalid_micro}

        monkeypatch.setattr(
            pro_nutrition_plate,
            "_aggregate_day_micronutrients",
            _non_finite_day_micros,
        )
        payload = {
            "sex": "female",
            "age": 30,
            "height_cm": 170,
            "weight_kg": 65,
            "activity": "moderate",
            "goal": "maintain",
        }

        response = client.post(
            route,
            json=payload,
            headers=headers,
        )

        assert response.status_code == 500
        assert response.json() == {"detail": ENHANCED_PLATE_GENERATION_FAILED_DETAIL}
        response_text = response.text.casefold()
        assert "private_dependency_nutrient" not in response_text
        assert str(invalid_micro).casefold() not in response_text
        assert "null" not in response_text

    @pytest.mark.parametrize(
        ("route", "headers"),
        [
            pytest.param(
                "/api/v1/pro/nutrition/plate",
                {"X-API-Key": TEST_KEY_PRO},
                id="canonical",
            ),
            pytest.param(
                "/api/v1/premium/plate",
                {"X-API-Key": "test_key"},
                id="legacy",
            ),
        ],
    )
    def test_plate_routes_propagate_canonical_target_safety_failure(
        self,
        monkeypatch: pytest.MonkeyPatch,
        route: str,
        headers: dict[str, str],
    ) -> None:
        """Both route families preserve canonical target safety failures."""

        def _reject_unsafe_targets(*_args: object, **_kwargs: object) -> object:
            raise HTTPException(
                status_code=500,
                detail=WHO_TARGETS_SAFETY_VALIDATION_FAILED_DETAIL,
            )

        def _empty_day_micros(
            _meals: list[dict[str, object]],
        ) -> dict[str, float]:
            return {}

        monkeypatch.setattr(
            pro_nutrition_plate,
            "generate_who_targets_response",
            _reject_unsafe_targets,
        )
        monkeypatch.setattr(
            pro_nutrition_plate,
            "_aggregate_day_micronutrients",
            _empty_day_micros,
        )
        payload = {
            "sex": "female",
            "age": 30,
            "height_cm": 170,
            "weight_kg": 65,
            "activity": "moderate",
            "goal": "maintain",
        }

        response = client.post(route, json=payload, headers=headers)

        assert response.status_code == 500
        assert response.json() == {"detail": WHO_TARGETS_SAFETY_VALIDATION_FAILED_DETAIL}

    @pytest.mark.parametrize(
        ("route", "headers"),
        [
            pytest.param(
                "/api/v1/pro/nutrition/plate",
                {"X-API-Key": TEST_KEY_PRO},
                id="canonical",
            ),
            pytest.param(
                "/api/v1/premium/plate",
                {"X-API-Key": "test_key"},
                id="legacy",
            ),
        ],
    )
    def test_plate_fallback_rejects_real_zero_kcal_extreme_profile(
        self,
        monkeypatch: pytest.MonkeyPatch,
        route: str,
        headers: dict[str, str],
    ) -> None:
        """Schema-accepted extremes cannot bypass canonical target safety."""

        fallback_dependencies = pro_nutrition_plate.PlateServiceDependencies(
            make_plate=None,
            calculate_all_bmr=None,
            calculate_all_tdee=None,
            build_nutrition_targets=(
                pro_nutrition_plate.nutrition_recommendations.build_nutrition_targets
            ),
            aggregate_day_micronutrients=lambda _meals: {},
        )
        monkeypatch.setattr(
            pro_nutrition_plate,
            "_default_dependencies",
            lambda: fallback_dependencies,
        )
        payload = {
            "sex": "female",
            "age": 10,
            "height_cm": 32.2,
            "weight_kg": 1,
            "activity": "sedentary",
            "goal": "maintain",
        }

        response = client.post(route, json=payload, headers=headers)

        assert response.status_code == 500
        assert response.json() == {"detail": WHO_TARGETS_SAFETY_VALIDATION_FAILED_DETAIL}
        assert '"kcal":0' not in response.text

    @pytest.mark.parametrize(
        ("response_field", "non_finite_value"),
        [
            pytest.param("portions", float("nan"), id="portions-nan"),
            pytest.param("portions", float("inf"), id="portions-infinity"),
            pytest.param("layout", float("nan"), id="layout-nan"),
            pytest.param("layout", float("inf"), id="layout-infinity"),
        ],
    )
    def test_plate_non_finite_response_bound_values_are_safe_500_at_http_boundary(
        self,
        monkeypatch: pytest.MonkeyPatch,
        response_field: str,
        non_finite_value: float,
    ) -> None:
        """Portions and layout values cannot reach JSON serialization as NaN/Infinity."""

        def _non_finite_plate(**_kwargs: object) -> dict[str, object]:
            portions: dict[str, object] = {
                "protein_palm": 2.0,
                "fat_thumbs": 2.0,
                "carb_cups": 2.0,
                "veg_cups": 3.0,
            }
            layout: list[dict[str, object]] = [
                {
                    "kind": "plate_sector",
                    "fraction": 1.0,
                    "label": "Plate",
                    "tooltip": "Plate",
                }
            ]
            if response_field == "portions":
                portions["protein_palm"] = non_finite_value
            else:
                layout[0]["fraction"] = non_finite_value
            return {
                "kcal": 2000,
                "macros": {
                    "protein_g": 110,
                    "fat_g": 60,
                    "carbs_g": 240,
                    "fiber_g": 25,
                },
                "portions": portions,
                "layout": layout,
                "meals": [],
                "meals_per_day": 3,
            }

        monkeypatch.setattr(
            pro_nutrition_plate.nutrition_plate,
            "make_plate",
            _non_finite_plate,
        )
        payload = {
            "sex": "female",
            "age": 30,
            "height_cm": 170,
            "weight_kg": 65,
            "activity": "moderate",
            "goal": "maintain",
        }

        response = client.post(
            "/api/v1/premium/plate",
            json=payload,
            headers={"X-API-Key": "test_key"},
        )

        assert response.status_code == 500
        assert response.json() == {"detail": ENHANCED_PLATE_GENERATION_FAILED_DETAIL}
        assert response_field not in response.text
        assert "nan" not in response.text.lower()
        assert "infinity" not in response.text.lower()

    @pytest.mark.parametrize("response_field", ["portions", "layout"])
    @pytest.mark.parametrize(
        "non_finite_token",
        [
            pytest.param("NaN", id="nan"),
            pytest.param("Infinity", id="infinity"),
            pytest.param("-Infinity", id="negative-infinity"),
            pytest.param("+nAn", id="case-and-sign-nan"),
            pytest.param(" -InFiNiTy ", id="whitespace-case-and-sign-infinity"),
            pytest.param("1e309", id="exponent-overflow"),
        ],
    )
    def test_plate_non_finite_string_response_bound_values_are_safe_500_at_http_boundary(
        self,
        monkeypatch: pytest.MonkeyPatch,
        response_field: str,
        non_finite_token: str,
    ) -> None:
        """Non-finite numeric strings cannot reach JSON serialization."""

        def _non_finite_plate(**_kwargs: object) -> dict[str, object]:
            portions: dict[str, object] = {
                "protein_palm": 2.0,
                "fat_thumbs": 2.0,
                "carb_cups": 2.0,
                "veg_cups": 3.0,
            }
            layout: list[dict[str, object]] = [
                {
                    "kind": "plate_sector",
                    "fraction": 1.0,
                    "label": "Plate",
                    "tooltip": "Plate",
                }
            ]
            if response_field == "portions":
                portions["protein_palm"] = non_finite_token
            else:
                layout[0]["fraction"] = non_finite_token
            return {
                "kcal": 2000,
                "macros": {
                    "protein_g": 110,
                    "fat_g": 60,
                    "carbs_g": 240,
                    "fiber_g": 25,
                },
                "portions": portions,
                "layout": layout,
                "meals": [],
                "meals_per_day": 3,
            }

        monkeypatch.setattr(
            pro_nutrition_plate.nutrition_plate,
            "make_plate",
            _non_finite_plate,
        )
        payload = {
            "sex": "female",
            "age": 30,
            "height_cm": 170,
            "weight_kg": 65,
            "activity": "moderate",
            "goal": "maintain",
        }

        response = client.post(
            "/api/v1/premium/plate",
            json=payload,
            headers={"X-API-Key": "test_key"},
        )

        assert response.status_code == 500
        assert response.json() == {"detail": ENHANCED_PLATE_GENERATION_FAILED_DETAIL}
        response_text = response.text.casefold()
        assert "nan" not in response_text
        assert "infinity" not in response_text
        assert non_finite_token.strip().casefold() not in response_text

    def test_plate_exact_numeric_tokens_are_allowed_in_text_fields(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Labels, tooltips, and titles preserve exact token-like text."""

        def _text_token_plate(**_kwargs: object) -> dict[str, object]:
            return {
                "kcal": 2000,
                "macros": {
                    "protein_g": 110,
                    "fat_g": 60,
                    "carbs_g": 240,
                    "fiber_g": 25,
                },
                "portions": {
                    "protein_palm": 2.0,
                    "fat_thumbs": 2.0,
                    "carb_cups": 2.0,
                    "veg_cups": 3.0,
                },
                "layout": [
                    {
                        "kind": "plate_sector",
                        "fraction": 1.0,
                        "label": "Infinity",
                        "tooltip": "NaN",
                    }
                ],
                "meals": [
                    {
                        "title": "Inf",
                        "kcal": 500,
                        "protein_g": 30,
                        "fat_g": 15,
                        "carbs_g": 60,
                        "fiber_g": 8,
                        "micros": {"iron_mg": 1.0},
                    }
                ],
                "meals_per_day": 3,
            }

        monkeypatch.setattr(
            pro_nutrition_plate.nutrition_plate,
            "make_plate",
            _text_token_plate,
        )
        payload = {
            "sex": "female",
            "age": 30,
            "height_cm": 170,
            "weight_kg": 65,
            "activity": "moderate",
            "goal": "maintain",
        }

        response = client.post(
            "/api/v1/premium/plate",
            json=payload,
            headers={"X-API-Key": "test_key"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["layout"][0]["label"] == "Infinity"
        assert data["layout"][0]["tooltip"] == "NaN"
        assert data["meals"][0]["title"] == "Inf"

    def test_plate_goal_specific_differences(self) -> None:
        """Test different goals produce appropriate macro distributions."""
        base_payload = {
            "sex": "female",
            "age": 30,
            "height_cm": 170,
            "weight_kg": 65,
            "activity": "moderate",
        }

        results = {}
        goals = ["loss", "maintain", "gain"]

        for goal in goals:
            extra_params = {}
            if goal == "loss":
                extra_params["deficit_pct"] = 15
            elif goal == "gain":
                extra_params["surplus_pct"] = 12

            payload = {**base_payload, "goal": goal, **extra_params}
            response = client.post(
                "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
            )
            assert response.status_code == 200
            results[goal] = response.json()

        # Loss should have fewer calories than maintenance
        assert results["loss"]["kcal"] < results["maintain"]["kcal"]
        # Gain should have more calories than maintenance
        assert results["gain"]["kcal"] > results["maintain"]["kcal"]

        # Loss should emphasize protein relatively more
        loss_protein_ratio = results["loss"]["macros"]["protein_g"] / results["loss"]["kcal"]
        maintain_protein_ratio = (
            results["maintain"]["macros"]["protein_g"] / results["maintain"]["kcal"]
        )
        assert loss_protein_ratio >= maintain_protein_ratio

    def test_plate_validation_errors(self) -> None:
        """Test input validation errors."""
        base_payload = {
            "sex": "male",
            "age": 30,
            "height_cm": 175,
            "weight_kg": 70,
            "activity": "moderate",
            "goal": "maintain",
        }

        # Test invalid age
        payload = {**base_payload, "age": 5}
        response = client.post(
            "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
        )
        assert response.status_code == 422

        # Test invalid deficit percentage
        payload = {**base_payload, "goal": "loss", "deficit_pct": 30}
        response = client.post(
            "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
        )
        assert response.status_code == 422

        # Test invalid surplus percentage
        payload = {**base_payload, "goal": "gain", "surplus_pct": 25}
        response = client.post(
            "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
        )
        assert response.status_code == 422

        # Test invalid body fat
        payload = {**base_payload, "bodyfat": 65}
        response = client.post(
            "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
        )
        assert response.status_code == 422

    def test_plate_missing_api_key(self) -> None:
        """Test plate API requires authentication."""
        payload = {
            "sex": "male",
            "age": 30,
            "height_cm": 175,
            "weight_kg": 70,
            "activity": "moderate",
            "goal": "maintain",
        }

        response = client.post("/api/v1/premium/plate", json=payload)
        assert response.status_code == 403

    def test_plate_meal_suggestions_structure(self) -> None:
        """Test meal suggestions have proper structure."""
        payload = {
            "sex": "female",
            "age": 25,
            "height_cm": 160,
            "weight_kg": 55,
            "activity": "light",
            "goal": "maintain",
        }

        response = client.post(
            "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
        )

        assert response.status_code == 200
        data = response.json()

        meals = data["meals"]
        assert len(meals) == 3  # Breakfast, lunch, dinner

        for meal in meals:
            assert "title" in meal
            assert "kcal" in meal
            assert "protein_g" in meal
            assert "fat_g" in meal
            assert "carbs_g" in meal

            # Check reasonable portion sizes
            assert 200 <= meal["kcal"] <= 1000
            assert meal["protein_g"] >= 0
            assert meal["fat_g"] >= 0
            assert meal["carbs_g"] >= 0

    def test_plate_edge_cases(self) -> None:
        """Test edge cases and boundary values."""
        # Test minimum valid values - but realistic ones
        payload = {
            "sex": "female",
            "age": 18,  # Adult minimum
            "height_cm": 150,  # Realistic short
            "weight_kg": 45,  # Realistic light
            "activity": "sedentary",
            "goal": "maintain",
        }

        response = client.post(
            "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["kcal"] >= 1000  # Should be reasonable for small adult

        # Test maximum valid values
        payload = {
            "sex": "male",
            "age": 100,  # Maximum age
            "height_cm": 220,  # Very tall
            "weight_kg": 150,  # Very heavy
            "activity": "very_active",
            "goal": "gain",
            "surplus_pct": 20,  # Maximum surplus
        }

        response = client.post(
            "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["kcal"] > 3000  # Should be very high calories


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
