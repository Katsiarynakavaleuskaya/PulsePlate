"""Shared pytest fixtures for the PulsePlate test suite."""

import base64
import importlib.util
import os
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import secure_config
from secure_config import InvalidToken


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment variables before any tests run.

    This fixture runs automatically for the entire session to ensure
    API_KEY is configured before the app module is loaded.
    """
    # Set API key for the entire test session
    os.environ["API_KEY"] = "test_key"
    yield
    # Clean up after all tests
    if "API_KEY" in os.environ:
        del os.environ["API_KEY"]


@pytest.fixture(scope="session")
def app_module() -> ModuleType:
    """Dynamically load app.py and return the module.

    This fixture depends on setup_test_environment to ensure
    API_KEY is set before loading the app.
    """
    repo_root = Path(__file__).parent.parent
    sys.path.insert(0, str(repo_root))

    app_path = repo_root / "app.py"
    spec = importlib.util.spec_from_file_location("app_module", str(app_path))
    if spec is None or spec.loader is None:
        pytest.skip("Cannot load app.py", allow_module_level=True)

    app_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(app_module)
    return app_module


@pytest.fixture
def app(app_module: ModuleType) -> FastAPI:
    """Return the FastAPI app instance with API key mock."""

    # Apply lenient API key mode
    def mock_get_api_key(api_key: str = ""):
        if not api_key or len(api_key.strip()) < 3:
            from fastapi import HTTPException

            raise HTTPException(status_code=403, detail="Invalid API Key")
        return api_key

    if hasattr(app_module.app, "dependency_overrides") and hasattr(app_module, "get_api_key"):
        app_module.app.dependency_overrides[app_module.get_api_key] = mock_get_api_key

    return cast(FastAPI, app_module.app)


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Return a TestClient for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def api_key():
    """Return the test API key value.

    The actual environment setup is done by setup_test_environment fixture.
    This fixture just provides the key value for tests to use in headers.
    """
    return "test_key"


@pytest.fixture
def export_client(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Client configured for export endpoints with API key env."""
    monkeypatch.setenv("API_KEY", "test_key")
    monkeypatch.setenv("API_KEY_REQUIRED", "true")
    return client


@pytest.fixture
def fake_crypto(monkeypatch: pytest.MonkeyPatch):
    """Provide a deterministic Fernet substitute when cryptography is absent."""

    class FakeFernet:
        _RAW_KEY = b"01234567890123456789012345678901"
        _KEY = base64.urlsafe_b64encode(_RAW_KEY)
        _INVALID_KEY_MSG = "invalid key"

        def __init__(self, key: bytes):
            if key != self._KEY:
                raise InvalidToken(self._INVALID_KEY_MSG)
            self._key = key

        @staticmethod
        def generate_key() -> bytes:
            return FakeFernet._KEY

        def encrypt(self, data: bytes) -> bytes:
            cipher = data[::-1]
            return base64.urlsafe_b64encode(cipher)

        def decrypt(self, token: bytes) -> bytes:
            try:
                decoded = base64.urlsafe_b64decode(token)
            except Exception as exc:  # pragma: no cover - defensive
                raise InvalidToken(str(exc)) from exc
            return decoded[::-1]

    monkeypatch.setattr(secure_config, "ENCRYPTION_AVAILABLE", True)
    monkeypatch.setattr(secure_config, "Fernet", FakeFernet, raising=False)

    try:  # Some tests import update_api_key lazily
        import update_api_key as update_api_key_module  # type: ignore
    except ImportError:  # pragma: no cover - optional dependency
        update_api_key_module = None

    if update_api_key_module is not None:
        monkeypatch.setattr(update_api_key_module, "ENCRYPTION_AVAILABLE", True, raising=False)
        monkeypatch.setattr(update_api_key_module, "Fernet", FakeFernet, raising=False)
        monkeypatch.setattr(
            update_api_key_module,
            "encrypt_value",
            secure_config.encrypt_value,
            raising=False,
        )
        monkeypatch.setattr(update_api_key_module, "Path", Path, raising=False)

    return FakeFernet
