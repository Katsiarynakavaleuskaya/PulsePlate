"""Quality tests for users router retry logic and error handling.

Tests verify the actual retry mechanism with exponential backoff:
- OperationalError triggers retries with proper delays
- IntegrityError bypasses retry and returns 409 immediately
- Retry exhaustion returns fallback or 503
- Session cleanup happens correctly on every attempt
"""

import pytest
from typing import Any
from unittest.mock import patch, MagicMock, call
from fastapi import HTTPException
from sqlalchemy.exc import OperationalError, IntegrityError

from tests._helpers.api_headers import API_KEY_HEADERS


def _wire_session_factory(mock_db: MagicMock, mock_session: MagicMock) -> MagicMock:
    """Make db_module.get_session_factory() return a callable factory.

    The factory() returns mock_session directly (not a context manager),
    matching the actual code pattern where session_factory() returns a Session
    and code explicitly calls session.close() and session.rollback().
    """
    session_factory = MagicMock(name="session_factory")
    session_factory.return_value = mock_session

    mock_db.get_session_factory.return_value = session_factory
    return session_factory


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

        session_factory = _wire_session_factory(mock_db, mock_session)
        monkeypatch.setattr("app.routers.users.db_module", mock_db)

        # Mock time.sleep to verify exponential backoff delays without actually sleeping
        with patch("app.routers.users.time.sleep") as mock_sleep:
            result = users._execute_with_retry(action_with_failures)

        # Should succeed on 4th attempt (1 initial + 3 retries)
        assert result == {"user_id": 123, "email": "test@example.com"}
        assert call_count == 4

        # Verify exponential backoff delays: 0.1s, 0.2s, 0.4s (base_delay=0.1, multiplied by 2 each retry)
        assert mock_sleep.call_count == 3, "Expected 3 sleep calls for 3 retries"
        expected_delays = [call(0.1), call(0.2), call(0.4)]
        mock_sleep.assert_has_calls(expected_delays, any_order=False)

        # Verify session cleanup: 1 initial + 3 retries = 4 sessions created and closed
        assert session_factory.call_count == 4
        assert mock_session.close.call_count == 4

    def test_integrity_error_bypasses_retry_returns_409_immediately(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """IntegrityError (duplicate key) should NOT retry - fail fast with 409."""
        from app.routers import users

        mock_db = MagicMock()
        mock_session = MagicMock()
        session_factory = _wire_session_factory(mock_db, mock_session)
        monkeypatch.setattr("app.routers.users.db_module", mock_db)

        def action_with_integrity_error(session):
            # Simulate duplicate email constraint violation
            raise IntegrityError("UNIQUE constraint failed: users.email", None, None)

        # Ensure any potential retry delay is a no-op
        monkeypatch.setattr("app.routers.users.time.sleep", lambda _seconds: None)
        with pytest.raises(HTTPException) as exc_info:
            users._execute_with_retry(action_with_integrity_error)

        # Should fail immediately without retries
        assert exc_info.value.status_code == 409
        assert "conflict" in exc_info.value.detail.lower()

        # Verify NO retries happened (only 1 attempt)
        assert session_factory.call_count == 1
        assert mock_session.close.call_count == 1
        assert mock_session.rollback.call_count == 1

    def test_retry_on_second_attempt_integrity_error_fails_fast(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """If first attempt has OperationalError but retry hits IntegrityError, should stop immediately."""
        from app.routers import users

        mock_db = MagicMock()
        mock_session = MagicMock()
        session_factory = _wire_session_factory(mock_db, mock_session)
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

        # Ensure retry delay is a no-op to avoid timing-based flakiness
        monkeypatch.setattr("app.routers.users.time.sleep", lambda _seconds: None)
        with pytest.raises(HTTPException) as exc_info:
            users._execute_with_retry(action_with_mixed_errors)

        # Should fail on 2nd attempt (after first retry delay of 0.1s)
        assert exc_info.value.status_code == 409
        assert call_count == 2
        # Verify exactly one retry happened
        assert session_factory.call_count == 2
        assert mock_session.close.call_count == 2

    def test_retry_http_exception_propagates(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """HTTPException in a retry attempt should rollback and propagate immediately."""
        from app.routers import users

        mock_db = MagicMock()
        mock_session = MagicMock()
        session_factory = _wire_session_factory(mock_db, mock_session)
        monkeypatch.setattr("app.routers.users.db_module", mock_db)

        call_count = 0

        def action_with_http_after_retry(session):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise OperationalError("database locked", None, None)
            raise HTTPException(status_code=418, detail="Retry failed")

        monkeypatch.setattr("app.routers.users.time.sleep", lambda _seconds: None)
        with pytest.raises(HTTPException) as exc_info:
            users._execute_with_retry(action_with_http_after_retry)

        assert exc_info.value.status_code == 418
        assert call_count == 2
        assert session_factory.call_count == 2
        assert mock_session.rollback.call_count == 1
        assert mock_session.close.call_count == 2

    def test_retry_exhaustion_with_fallback_returns_fallback_value(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When all retries fail and fallback provided, should return fallback."""
        from app.routers import users

        mock_db = MagicMock()
        mock_session = MagicMock()
        session_factory = _wire_session_factory(mock_db, mock_session)
        monkeypatch.setattr("app.routers.users.db_module", mock_db)

        def always_fails(session):
            raise OperationalError("database unavailable", None, None)

        fallback_value: list[Any] = []
        result = users._execute_with_retry(always_fails, fallback=fallback_value)

        # Should return fallback after exhausting retries
        assert result is fallback_value
        # 1 initial + 3 retries (hardcoded) = 4 attempts
        assert session_factory.call_count == 4

    def test_retry_exhaustion_without_fallback_raises_503(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When all retries fail and no fallback, should raise 503 SERVICE_UNAVAILABLE."""
        from app.routers import users

        mock_db = MagicMock()
        mock_session = MagicMock()
        session_factory = _wire_session_factory(mock_db, mock_session)
        monkeypatch.setattr("app.routers.users.db_module", mock_db)

        def always_fails(session):
            raise OperationalError("database down", None, None)

        with pytest.raises(HTTPException) as exc_info:
            users._execute_with_retry(always_fails)

        assert exc_info.value.status_code == 503
        assert "unavailable" in exc_info.value.detail.lower()
        # 1 initial + 3 retries (hardcoded) = 4 attempts
        assert session_factory.call_count == 4

    def test_http_exception_propagates_without_retry(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """HTTPException raised by action should rollback and propagate without retries."""
        from app.routers import users

        mock_db = MagicMock()
        mock_session = MagicMock()
        session_factory = _wire_session_factory(mock_db, mock_session)
        monkeypatch.setattr("app.routers.users.db_module", mock_db)

        def action_raises_http(session):
            raise HTTPException(status_code=400, detail="Bad input")

        with pytest.raises(HTTPException) as exc_info:
            users._execute_with_retry(action_raises_http)

        assert exc_info.value.status_code == 400
        session_factory.assert_called_once()
        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()


class TestUsersEndpointRetryIntegration:
    """Test actual user endpoints to verify retry integration."""

    def test_list_users_no_fallback_on_db_failure(
        self, test_client, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """list_users should raise 503 on DB failure (no fallback configured)."""
        from app.routers import users

        def always_fail(action, **kwargs):
            # Simulate DB completely down
            raise HTTPException(status_code=503, detail="Database unavailable")

        monkeypatch.setattr("app.routers.users._execute_with_retry", always_fail)

        response = test_client.get("/api/v1/users", headers=API_KEY_HEADERS)

        # Should fail with 503 (no fallback for list operation)
        assert response.status_code == 503
