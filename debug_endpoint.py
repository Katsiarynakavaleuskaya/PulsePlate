import os
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

# Set API key
os.environ["API_KEY"] = "test_key"

# Import and check scheduler state
from core.food_apis.scheduler import _scheduler_instance

print(f"Initial scheduler instance: {_scheduler_instance}")

from app import app

client = TestClient(app)


def test_database_status_exception():
    """Test database status endpoint exception handling."""
    # Check scheduler state before patching
    from core.food_apis.scheduler import _scheduler_instance

    print(f"Scheduler instance before test: {_scheduler_instance}")

    with patch(
        "app.get_update_scheduler", new_callable=AsyncMock
    ) as mock_get_scheduler:
        mock_get_scheduler.side_effect = Exception("Test error")

        response = client.get(
            "/api/v1/admin/db-status", headers={"X-API-Key": "test_key"}
        )
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code


if __name__ == "__main__":
    status_code = test_database_status_exception()
    print(f"Got status code: {status_code}")
