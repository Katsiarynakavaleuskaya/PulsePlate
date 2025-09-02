import pathlib
import sys

# Корень репозитория = родитель папки tests
ROOT = pathlib.Path(__file__).resolve().parent.parent
p = str(ROOT)
if p not in sys.path:
    sys.path.insert(0, p)


import os
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True, scope="session")
def _neutral_llm_env():
    for k in ("LLM_PROVIDER","GROK_ENDPOINT","GROK_MODEL","OPENAI_API_KEY","XAI_API_KEY"):
        os.environ.pop(k, None)


@pytest.fixture(autouse=True, scope="function")
def _set_api_key():
    original_api_key = os.environ.get("API_KEY")
    os.environ["API_KEY"] = "test_key"
    yield
    if original_api_key is not None:
        os.environ["API_KEY"] = original_api_key
    else:
        os.environ.pop("API_KEY", None)


@pytest.fixture(autouse=True, scope="function")
def _reset_scheduler():
    """Reset the global scheduler instance between tests."""
    import core.food_apis.scheduler
    core.food_apis.scheduler._scheduler_instance = None
    yield


@pytest.fixture
def client():
    """Create a test client for each test."""
    from fastapi.testclient import TestClient

    from app import app
    return TestClient(app)
