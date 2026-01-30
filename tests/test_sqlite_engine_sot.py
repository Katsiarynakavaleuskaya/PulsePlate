"""Guard test: SQLite engine/URL consistency (fixture vs app).

Ensures that test fixture and app code use the same SQLite engine/URL.
Prevents "no such table" errors from dual-engine topology.
"""

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def test_sqlite_engine_url_is_single_source_of_truth(client: TestClient) -> None:
    """Verify app uses the same SQLite URL configured by test fixture.

    Root cause: If app creates a separate engine, schema exists in fixture's DB
    but app queries a different (empty) DB → "no such table" errors.

    This guard ensures single engine topology in tests.
    """
    import core.db

    # Get database URL from environment (set by configure_sqlite_database fixture)
    expected_url = os.environ.get("DATABASE_URL", "")

    # Verify it's SQLite file-based (xdist requirement)
    assert expected_url.startswith(
        "sqlite:///"
    ), f"Test DATABASE_URL must be file-based SQLite, got: {expected_url}"
    assert (
        ":memory:" not in expected_url
    ), "In-memory SQLite not supported with xdist (per-worker isolation required)"

    # Get actual engine URL from app/core.db layer
    engine = getattr(core.db, "_RAW_ENGINE", None) or getattr(core.db, "engine", None)
    assert engine is not None, "core.db engine not initialized"

    actual_url = str(engine.url)

    # Extract paths for comparison (ignore query params like ?mode=rwc)
    def extract_path(url: str) -> str:
        """Extract file path from SQLite URL (before query string)."""
        if "?" in url:
            url = url.split("?")[0]
        return url.replace("sqlite:///", "")

    expected_path = Path(extract_path(expected_url)).resolve()
    actual_path = Path(extract_path(actual_url)).resolve()

    assert actual_path == expected_path, (
        f"Engine URL mismatch (dual-engine topology detected):\n"
        f"  Fixture DB:  {expected_path}\n"
        f"  App engine:  {actual_path}\n"
        f"This causes 'no such table' errors because schema exists in fixture DB "
        f"but app queries different DB. Fix: ensure app uses fixture's engine."
    )


def test_sqlite_db_file_per_worker_under_xdist() -> None:
    """Verify each xdist worker has unique SQLite DB file.

    Prevents race conditions and schema conflicts when multiple workers
    run tests concurrently.
    """
    db_url = os.environ.get("DATABASE_URL", "")
    worker_id = os.environ.get("PYTEST_XDIST_WORKER", "gw0")

    if worker_id == "gw0" and "PYTEST_XDIST_WORKER" not in os.environ:
        # Serial run (no xdist) - skip check
        pytest.skip("Not running under xdist, per-worker check not applicable")

    # DB path must contain worker ID to ensure isolation
    assert worker_id in db_url, (
        f"SQLite DB path must include worker ID for xdist isolation.\n"
        f"  Worker: {worker_id}\n"
        f"  DB URL: {db_url}\n"
        f"Fix: configure_sqlite_database fixture must use PYTEST_XDIST_WORKER in path."
    )
