import os

import pytest
from sqlalchemy import create_engine, text

pytestmark = pytest.mark.integration


def test_postgres_is_reachable() -> None:
    """Basic smoke test to ensure the Postgres service is reachable in CI.

    This test is intentionally minimal: it only verifies that we can connect
    using DATABASE_URL and execute a trivial SELECT 1.
    """
    url = os.environ.get("DATABASE_URL")
    assert url, "DATABASE_URL must be set for integration tests"

    engine = create_engine(url, pool_pre_ping=True, future=True)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT 1")).scalar_one() == 1
