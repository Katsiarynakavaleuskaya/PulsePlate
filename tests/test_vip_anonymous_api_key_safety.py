"""Tests for VIP router anonymous API key safety in production environments."""

import pytest

from settings import is_production_like_env
from tests._client import open_test_client


@pytest.fixture(autouse=True)
def vip_anonymous_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reset auth-related env for each test via canonical monkeypatch fixtures.

    RU: Используем monkeypatch вместо прямой мутации os.environ.
    EN: Use monkeypatch instead of direct os.environ mutation.
    """

    monkeypatch.setenv("VIP_MODULE_ENABLED", "true")
    for name in (
        "API_KEY",
        "APP_ENV",
        "ENVIRONMENT",
        "ALLOW_ANONYMOUS_API_KEYS",
        "DEBUG",
        "VIP_API_KEYS",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("ALLOW_DEV_API_KEY", "false")


class TestVIPAnonymousAPIKeySafety:
    """Test VIP router anonymous API key safety functionality."""

    def test_production_mode_rejects_anonymous_access(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that production mode rejects anonymous access by default."""
        import app

        with open_test_client(app.app) as client:
            with monkeypatch.context() as request_env:
                request_env.setenv("APP_ENV", "production")
                request_env.setenv("DEBUG", "false")
                request_env.setenv("API_KEY", "secret-key")
                request_env.setenv("VIP_API_KEYS", "secret-key")  # pragma: allowlist secret

                # Test request without API key to VIP endpoint
                response = client.post(
                    "/api/v1/vip/weekly-plan",
                    json={
                        "sex": "female",
                        "age": 30,
                        "height_cm": 165.0,
                        "weight_kg": 60.0,
                        "activity": "moderate",
                        "goal": "maintain",
                    },
                )
                assert response.status_code == 403
                assert response.headers["content-type"].startswith("application/json")
                detail_lower = response.json()["detail"].lower()
                assert "api key" in detail_lower or "vip access" in detail_lower

                # Test request with invalid API key
                response = client.post(
                    "/api/v1/vip/weekly-plan",
                    json={
                        "sex": "female",
                        "age": 30,
                        "height_cm": 165.0,
                        "weight_kg": 60.0,
                        "activity": "moderate",
                        "goal": "maintain",
                    },
                    headers={"X-API-Key": "wrong-key"},
                )
                # Invalid key should be 403 (insufficient permissions), not 401 (missing auth)
                assert response.status_code == 403
                assert response.headers["content-type"].startswith("application/json")
                detail_lower = response.json()["detail"].lower()
                assert (
                    "vip" in detail_lower or "invalid" in detail_lower or "required" in detail_lower
                )

    def test_production_mode_with_explicit_anonymous_allowed_fails_fast(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that production mode fails fast when anonymous access is enabled."""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("DEBUG", "false")
        monkeypatch.setenv("ALLOW_ANONYMOUS_API_KEYS", "true")

        import app

        with pytest.raises(RuntimeError, match="ALLOW_ANONYMOUS_API_KEYS"):
            with open_test_client(app.app):
                pass

    def test_staging_mode_rejects_anonymous_access(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that staging mode rejects anonymous access by default."""
        import app

        with open_test_client(app.app) as client:
            with monkeypatch.context() as request_env:
                request_env.setenv("APP_ENV", "staging")
                request_env.setenv("DEBUG", "false")

                # Test request without API key to VIP endpoint
                response = client.post(
                    "/api/v1/vip/weekly-plan",
                    json={
                        "sex": "female",
                        "age": 30,
                        "height_cm": 165.0,
                        "weight_kg": 60.0,
                        "activity": "moderate",
                        "goal": "maintain",
                    },
                )
                assert response.status_code == 403
                assert response.headers["content-type"].startswith("application/json")
                detail_lower = response.json()["detail"].lower()
                assert "api key" in detail_lower or "vip access" in detail_lower

    def test_debug_false_rejects_anonymous_access(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that DEBUG=false rejects anonymous access even without explicit production env."""
        import app

        with open_test_client(app.app) as client:
            with monkeypatch.context() as request_env:
                request_env.setenv("APP_ENV", "preview")
                request_env.setenv("DEBUG", "true")
                assert is_production_like_env() is False

                request_env.setenv("DEBUG", "false")
                assert is_production_like_env() is True

                # Test request without API key to VIP endpoint
                response = client.post(
                    "/api/v1/vip/weekly-plan",
                    json={
                        "sex": "female",
                        "age": 30,
                        "height_cm": 165.0,
                        "weight_kg": 60.0,
                        "activity": "moderate",
                        "goal": "maintain",
                    },
                )
                assert response.status_code == 403
                assert response.headers["content-type"].startswith("application/json")
                detail_lower = response.json()["detail"].lower()
                assert "api key" in detail_lower or "vip access" in detail_lower

    def test_development_mode_allows_anonymous_access(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that development mode allows anonymous access by default."""
        import app

        with open_test_client(app.app) as client:
            with monkeypatch.context() as request_env:
                request_env.setenv("APP_ENV", "development")
                request_env.setenv("DEBUG", "true")
                request_env.setenv("ALLOW_DEV_API_KEY", "true")

                # Test request without API key to VIP endpoint
                response = client.post(
                    "/api/v1/vip/weekly-plan",
                    json={
                        "sex": "female",
                        "age": 30,
                        "height_cm": 165.0,
                        "weight_kg": 60.0,
                        "activity": "moderate",
                        "goal": "maintain",
                    },
                )
                assert response.status_code == 200

    def test_local_mode_allows_anonymous_access(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that local mode allows anonymous access by default."""
        import app

        with open_test_client(app.app) as client:
            with monkeypatch.context() as request_env:
                request_env.setenv("APP_ENV", "local")
                request_env.setenv("DEBUG", "true")
                request_env.setenv("ALLOW_DEV_API_KEY", "true")

                # Test request without API key to VIP endpoint
                response = client.post(
                    "/api/v1/vip/weekly-plan",
                    json={
                        "sex": "female",
                        "age": 30,
                        "height_cm": 165.0,
                        "weight_kg": 60.0,
                        "activity": "moderate",
                        "goal": "maintain",
                    },
                )
                assert response.status_code == 200

    def test_test_mode_allows_anonymous_access(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that test mode allows anonymous access by default."""
        import app

        with open_test_client(app.app) as client:
            with monkeypatch.context() as request_env:
                request_env.setenv("APP_ENV", "test")
                request_env.setenv("DEBUG", "true")
                request_env.setenv("ALLOW_DEV_API_KEY", "true")

                # Test request without API key to VIP endpoint
                response = client.post(
                    "/api/v1/vip/weekly-plan",
                    json={
                        "sex": "female",
                        "age": 30,
                        "height_cm": 165.0,
                        "weight_kg": 60.0,
                        "activity": "moderate",
                        "goal": "maintain",
                    },
                )
                assert response.status_code == 200

    def test_explicit_anonymous_disabled_in_development(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that explicit ALLOW_ANONYMOUS_API_KEYS=false disables anonymous access even in development."""
        import app

        with open_test_client(app.app) as client:
            with monkeypatch.context() as request_env:
                request_env.setenv("APP_ENV", "development")
                request_env.setenv("DEBUG", "true")
                request_env.setenv("ALLOW_DEV_API_KEY", "true")
                request_env.setenv("ALLOW_ANONYMOUS_API_KEYS", "false")

                # Test request without API key to VIP endpoint
                response = client.post(
                    "/api/v1/vip/weekly-plan",
                    json={
                        "sex": "female",
                        "age": 30,
                        "height_cm": 165.0,
                        "weight_kg": 60.0,
                        "activity": "moderate",
                        "goal": "maintain",
                    },
                )
                assert response.status_code == 403
                assert response.headers["content-type"].startswith("application/json")
                detail_lower = response.json()["detail"].lower()
                assert "api key" in detail_lower or "vip access" in detail_lower

    def test_production_mode_logs_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that production mode logs error when anonymous access is attempted."""
        import app

        with open_test_client(app.app) as client:
            with monkeypatch.context() as request_env:
                request_env.setenv("APP_ENV", "production")
                request_env.setenv("DEBUG", "false")

                # Test request without API key to VIP endpoint
                response = client.post(
                    "/api/v1/vip/weekly-plan",
                    json={
                        "sex": "female",
                        "age": 30,
                        "height_cm": 165.0,
                        "weight_kg": 60.0,
                        "activity": "moderate",
                        "goal": "maintain",
                    },
                )
                assert response.status_code == 403
                assert response.headers["content-type"].startswith("application/json")
                detail_lower = response.json()["detail"].lower()
                assert "api key" in detail_lower or "vip access" in detail_lower

    def test_anonymous_allowed_logs_warning_fails_fast(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that production no longer tolerates anonymous access warnings."""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("DEBUG", "false")
        monkeypatch.setenv("ALLOW_ANONYMOUS_API_KEYS", "true")

        import app

        with pytest.raises(RuntimeError, match="ALLOW_ANONYMOUS_API_KEYS"):
            with open_test_client(app.app):
                pass

    def test_development_mode_logs_info(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that development mode logs info when anonymous access is used."""
        import app

        with open_test_client(app.app) as client:
            with monkeypatch.context() as request_env:
                request_env.setenv("APP_ENV", "development")
                request_env.setenv("DEBUG", "true")
                request_env.setenv("ALLOW_DEV_API_KEY", "true")

                # Test request without API key to VIP endpoint
                response = client.post(
                    "/api/v1/vip/weekly-plan",
                    json={
                        "sex": "female",
                        "age": 30,
                        "height_cm": 165.0,
                        "weight_kg": 60.0,
                        "activity": "moderate",
                        "goal": "maintain",
                    },
                )
                assert response.status_code == 200

    def test_production_with_valid_api_key_works(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that production mode works correctly with valid API key."""
        import app

        with open_test_client(app.app) as client:
            with monkeypatch.context() as request_env:
                request_env.setenv("APP_ENV", "production")
                request_env.setenv("DEBUG", "false")
                request_env.setenv("API_KEY", "secret-key")
                request_env.setenv("VIP_API_KEYS", "secret-key")  # pragma: allowlist secret

                # Test request with valid API key
                response = client.post(
                    "/api/v1/vip/weekly-plan",
                    json={
                        "sex": "female",
                        "age": 30,
                        "height_cm": 165.0,
                        "weight_kg": 60.0,
                        "activity": "moderate",
                        "goal": "maintain",
                    },
                    headers={"X-API-Key": "secret-key"},
                )
                assert response.status_code == 200

    def test_production_with_invalid_api_key_rejects(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that production mode rejects invalid API key."""
        import app

        with open_test_client(app.app) as client:
            with monkeypatch.context() as request_env:
                request_env.setenv("APP_ENV", "production")
                request_env.setenv("DEBUG", "false")
                request_env.setenv("API_KEY", "secret-key")
                request_env.setenv("VIP_API_KEYS", "secret-key")  # pragma: allowlist secret

                # Test request with invalid API key
                response = client.post(
                    "/api/v1/vip/weekly-plan",
                    json={
                        "sex": "female",
                        "age": 30,
                        "height_cm": 165.0,
                        "weight_kg": 60.0,
                        "activity": "moderate",
                        "goal": "maintain",
                    },
                    headers={"X-API-Key": "wrong-key"},
                )
                assert response.status_code == 403
                assert response.headers["content-type"].startswith("application/json")
                detail_lower = response.json()["detail"].lower()
                assert "vip" in detail_lower or "invalid" in detail_lower

    def test_environment_variable_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that environment variables have correct defaults."""
        import app

        with open_test_client(app.app) as client:
            with monkeypatch.context() as request_env:
                request_env.delenv("APP_ENV", raising=False)
                request_env.delenv("DEBUG", raising=False)
                request_env.setenv("ALLOW_DEV_API_KEY", "false")

                # Missing API keys fail closed under the default environment values.
                response = client.post(
                    "/api/v1/vip/weekly-plan",
                    json={
                        "sex": "female",
                        "age": 30,
                        "height_cm": 165.0,
                        "weight_kg": 60.0,
                        "activity": "moderate",
                        "goal": "maintain",
                    },
                )
                assert response.status_code == 403

    def test_unknown_environment_rejects_anonymous_access(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Unknown env labels must not inherit dev-only anonymous fallbacks."""
        import app

        with open_test_client(app.app) as client:
            with monkeypatch.context() as request_env:
                request_env.setenv("APP_ENV", "preview")
                request_env.setenv("DEBUG", "true")
                request_env.setenv("ALLOW_DEV_API_KEY", "true")

                response = client.post(
                    "/api/v1/vip/weekly-plan",
                    json={
                        "sex": "female",
                        "age": 30,
                        "height_cm": 165.0,
                        "weight_kg": 60.0,
                        "activity": "moderate",
                        "goal": "maintain",
                    },
                )
                assert response.status_code == 403
