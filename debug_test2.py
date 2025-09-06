import os
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import app


def test_database_status_endpoint_exception():
    """Test database status endpoint exception handling."""
    client = TestClient(app)
    os.environ["API_KEY"] = "test_key"

    # Mock the scheduler to raise an exception
    with patch("app.get_update_scheduler") as mock_get_scheduler:
        mock_get_scheduler.side_effect = Exception("Test error")

        response = client.get(
            "/api/v1/admin/db-status", headers={"X-API-Key": "test_key"}
        )
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code


if __name__ == "__main__":
    status_code = test_database_status_endpoint_exception()
    print(f"Test result: {status_code}")
