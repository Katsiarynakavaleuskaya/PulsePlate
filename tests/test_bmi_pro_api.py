"""
Tests for BMI Pro API endpoint.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


class TestBMIProAPI:
    """Test BMI Pro API endpoint."""

    client: TestClient
    pro_headers: dict[str, str]

    @pytest.fixture(autouse=True)
    def _setup(
        self, client: TestClient, pro_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Set up test client and headers using fixtures (canonical pattern)."""
        monkeypatch.setenv("API_KEY", "test_key")
        self.client = client
        self.pro_headers = pro_headers

    def teardown_method(self) -> None:
        """Clean up test environment."""
        # Environment cleanup handled by monkeypatch fixture
        pass

    def test_bmi_pro_endpoint_success(self) -> None:
        """Test successful BMI Pro analysis."""
        data = {
            "weight_kg": 70.0,
            "height_cm": 175.0,
            "age": 30,
            "sex": "male",
            "waist_cm": 85.0,
            "hip_cm": 100.0,
            "bodyfat_percent": 20.0,
            "lang": "en",
        }

        response = self.client.post("/api/v1/pro/bmi", json=data, headers=self.pro_headers)
        assert response.status_code == 200

        result = response.json()
        assert "bmi" in result
        assert "whtr" in result
        assert "whr" in result
        assert "ffmi" in result
        assert "risk_level" in result
        assert "notes" in result
        assert result["bmi"] == pytest.approx(22.9, 0.1)
        assert result["whtr"] == pytest.approx(0.49, 0.01)

    def test_bmi_pro_endpoint_minimal_data(self) -> None:
        """Test BMI Pro analysis with minimal data (no hip or bodyfat)."""
        data = {
            "weight_kg": 70.0,
            "height_cm": 175.0,
            "age": 30,
            "sex": "female",
            "waist_cm": 80.0,
            "lang": "en",
        }

        response = self.client.post("/api/v1/pro/bmi", json=data, headers=self.pro_headers)
        assert response.status_code == 200

        result = response.json()
        assert "bmi" in result
        assert "whtr" in result
        # WHR and FFMI should be None when not provided
        assert result["whr"] is None
        assert result["ffmi"] is None

    def test_bmi_pro_endpoint_invalid_data(self) -> None:
        """Test BMI Pro analysis with invalid data."""
        data = {
            "weight_kg": -70.0,  # Invalid weight
            "height_cm": 175.0,
            "age": 30,
            "gender": "male",
            "pregnant": "no",
            "athlete": "no",
            "waist_cm": 85.0,
            "lang": "en",
        }

        response = self.client.post("/api/v1/pro/bmi", json=data, headers=self.pro_headers)
        assert response.status_code == 422  # Validation error

    def test_bmi_pro_endpoint_missing_api_key(self) -> None:
        """Test BMI Pro endpoint without API key (should require Pro tier)."""
        data = {
            "weight_kg": 70.0,
            "height_cm": 175.0,
            "age": 30,
            "sex": "male",
            "waist_cm": 85.0,
            "lang": "en",
        }

        response = self.client.post("/api/v1/pro/bmi", json=data)
        assert response.status_code in (401, 403)  # Pro tier guard requires API key

    def test_bmi_pro_legacy_alias_still_works(self) -> None:
        """Test that deprecated legacy alias /api/v1/bmi/pro still works (backward compatibility)."""
        data = {
            "weight_kg": 70.0,
            "height_cm": 175.0,
            "age": 30,
            "sex": "male",
            "waist_cm": 85.0,
            "hip_cm": 100.0,
            "bodyfat_percent": 20.0,
            "lang": "en",
        }

        # Legacy path should still work with Pro key
        response = self.client.post("/api/v1/bmi/pro", json=data, headers=self.pro_headers)
        assert response.status_code == 200

        result = response.json()
        assert "bmi" in result
        assert "whtr" in result
        assert result["bmi"] == pytest.approx(22.9, 0.1)

    def test_bmi_pro_legacy_alias_guard_called_once(self) -> None:
        """Test that require_pro_tier guard is NOT duplicated (static check).

        This prevents regression if guard gains side effects (logging, metrics, rate limits).
        We verify statically that guard is only in function parameter, not in decorator dependencies.

        Note: Runtime call counting is difficult with FastAPI's dependency injection system,
        so we use static analysis of the route definition and function signature.
        """
        import inspect

        from app.routers.bmi_pro_legacy_alias import bmi_pro_legacy_alias as handler_func

        # Check function signature: guard should be in parameter, not duplicated
        sig = inspect.signature(handler_func)
        param_guard_count = len(
            [p for p in sig.parameters.values() if "require_pro_tier" in str(p.default)]
        )

        assert param_guard_count == 1, (
            f"Legacy alias handler has {param_guard_count} require_pro_tier guards "
            "in function parameters. Expected exactly 1 (no duplication)."
        )

        # Check source code: decorator should NOT have dependencies=[Depends(require_pro_tier)]
        import re

        # Get source of the entire module to check decorator
        from app.routers import bmi_pro_legacy_alias

        module_source = inspect.getsource(bmi_pro_legacy_alias)
        # Remove comments to avoid false positives (comment mentions the pattern)
        lines = module_source.split("\n")
        code_lines = [line for line in lines if not line.strip().startswith("#")]
        code_source = "\n".join(code_lines)

        # Look for dependencies=[Depends(require_pro_tier)] in @router.post decorator context
        # Pattern: @router.post(... dependencies=[Depends(require_pro_tier)] ...)
        decorator_pattern = r"@router\.post\([^)]*dependencies\s*=\s*\[.*require_pro_tier.*\]"
        decorator_matches = re.findall(decorator_pattern, code_source, re.DOTALL)

        assert len(decorator_matches) == 0, (
            f"Legacy alias decorator has {len(decorator_matches)} require_pro_tier dependencies. "
            "Guard should only be in function parameter to avoid double invocation. "
            f"Found matches: {decorator_matches}"
        )

        # Functional test: verify endpoint still works correctly
        data = {
            "weight_kg": 70.0,
            "height_cm": 175.0,
            "age": 30,
            "sex": "male",
            "waist_cm": 85.0,
            "hip_cm": 100.0,
            "bodyfat_percent": 20.0,
            "lang": "en",
        }

        response = self.client.post("/api/v1/bmi/pro", json=data, headers=self.pro_headers)
        assert response.status_code == 200
