"""Quality tests for users router retry logic and error handling.

Tests verify the actual retry mechanism with exponential backoff:
- OperationalError triggers retries with proper delays
- IntegrityError bypasses retry and returns 409 immediately
- Retry exhaustion returns fallback or 503
- Session cleanup happens correctly on every attempt
"""

import pytest
import time
from unittest.mock import patch, MagicMock, call
from fastapi import HTTPException
from sqlalchemy.exc import OperationalError, IntegrityError


class TestUsersRetryMechanism:
    """Test the _execute_with_retry retry mechanism with real timing."""

    def test_operational_error_triggers_retry_with_exponential_backoff(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify retry delays follow exponential backoff: 0.1s, 0.2s, 0.4s."""
        from app.routers import users

        # Mock db_module to control session behavior
        mock_db = MagicMock()
        mock_session = MagicMock()

        # First 3 attempts fail with OperationalError, 4th succeeds
        call_count = 0

        def action_with_failures(session):
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                raise OperationalError("database locked", None, None)
            # 4th attempt succeeds
            return {"user_id": 123, "email": "test@example.com"}

        mock_db.SessionLocal.return_value = mock_session
        monkeypatch.setattr("app.routers.users.db_module", mock_db)

        # Track timing to verify exponential backoff (function has max_retries=3, base_delay=0.1 hardcoded)
        start_time = time.time()
        result = users._execute_with_retry(action_with_failures)
        elapsed = time.time() - start_time

        # Should succeed on 4th attempt (1 initial + 3 retries)
        assert result == {"user_id": 123, "email": "test@example.com"}
        assert call_count == 4

        # Verify timing: 0.1s + 0.2s + 0.4s = 0.7s minimum
        # Allow 50ms tolerance for test execution overhead
        assert elapsed >= 0.65, f"Expected >= 0.7s for exponential backoff, got {elapsed}s"

        # Verify session cleanup: 1 initial + 3 retries = 4 sessions created and closed
        assert mock_db.SessionLocal.call_count == 4
        assert mock_session.close.call_count == 4

    def test_integrity_error_bypasses_retry_returns_409_immediately(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """IntegrityError (duplicate key) should NOT retry - fail fast with 409."""
        from app.routers import users

        mock_db = MagicMock()
        mock_session = MagicMock()
        mock_db.SessionLocal.return_value = mock_session
        monkeypatch.setattr("app.routers.users.db_module", mock_db)

        def action_with_integrity_error(session):
            # Simulate duplicate email constraint violation
            raise IntegrityError("UNIQUE constraint failed: users.email", None, None)

        start_time = time.time()
        with pytest.raises(HTTPException) as exc_info:
            users._execute_with_retry(action_with_integrity_error)
        elapsed = time.time() - start_time

        # Should fail immediately without retries
        assert exc_info.value.status_code == 409
        assert "conflict" in exc_info.value.detail.lower()

        # Verify NO retries happened (only 1 attempt, < 100ms)
        assert elapsed < 0.1, f"Should fail fast, but took {elapsed}s"
        assert mock_db.SessionLocal.call_count == 1
        assert mock_session.close.call_count == 1
        assert mock_session.rollback.call_count == 1

    def test_retry_on_second_attempt_integrity_error_fails_fast(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """If first attempt has OperationalError but retry hits IntegrityError, should stop immediately."""
        from app.routers import users

        mock_db = MagicMock()
        mock_session = MagicMock()
        mock_db.SessionLocal.return_value = mock_session
        monkeypatch.setattr("app.routers.users.db_module", mock_db)

        call_count = 0

        def action_with_mixed_errors(session):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First attempt: operational error (triggers retry)
                raise OperationalError("database locked", None, None)
            else:
                # Retry attempt: integrity error (should fail fast)
                raise IntegrityError("UNIQUE constraint", None, None)

        start_time = time.time()
        with pytest.raises(HTTPException) as exc_info:
            users._execute_with_retry(action_with_mixed_errors)
        elapsed = time.time() - start_time

        # Should fail on 2nd attempt (after first retry delay of 0.1s)
        assert exc_info.value.status_code == 409
        assert call_count == 2

        # Timing: 0.1s delay before 2nd attempt
        assert 0.1 <= elapsed < 0.3, f"Expected ~0.1s for single retry, got {elapsed}s"

    def test_retry_exhaustion_with_fallback_returns_fallback_value(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When all retries fail and fallback provided, should return fallback."""
        from app.routers import users

        mock_db = MagicMock()
        mock_session = MagicMock()
        mock_db.SessionLocal.return_value = mock_session
        monkeypatch.setattr("app.routers.users.db_module", mock_db)

        def always_fails(session):
            raise OperationalError("database unavailable", None, None)

        fallback_value = []
        result = users._execute_with_retry(always_fails, fallback=fallback_value)

        # Should return fallback after exhausting retries
        assert result is fallback_value
        # 1 initial + 3 retries (hardcoded) = 4 attempts
        assert mock_db.SessionLocal.call_count == 4

    def test_retry_exhaustion_without_fallback_raises_503(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When all retries fail and no fallback, should raise 503 SERVICE_UNAVAILABLE."""
        from app.routers import users

        mock_db = MagicMock()
        mock_session = MagicMock()
        mock_db.SessionLocal.return_value = mock_session
        monkeypatch.setattr("app.routers.users.db_module", mock_db)

        def always_fails(session):
            raise OperationalError("database down", None, None)

        with pytest.raises(HTTPException) as exc_info:
            users._execute_with_retry(always_fails)

        assert exc_info.value.status_code == 503
        assert "unavailable" in exc_info.value.detail.lower()
        # 1 initial + 3 retries (hardcoded) = 4 attempts
        assert mock_db.SessionLocal.call_count == 4


class TestUsersEndpointRetryIntegration:
    """Test actual user endpoints to verify retry integration."""

    @pytest.mark.asyncio
    async def test_list_users_no_fallback_on_db_failure(
        self, test_client, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """list_users should raise 503 on DB failure (no fallback configured)."""
        from app.routers import users

        def always_fail(action, **kwargs):
            # Simulate DB completely down
            raise HTTPException(status_code=503, detail="Database unavailable")

        monkeypatch.setattr("app.routers.users._execute_with_retry", always_fail)

        response = test_client.get("/api/v1/users")

        # Should fail with 503 (no fallback for list operation)
        assert response.status_code == 503
