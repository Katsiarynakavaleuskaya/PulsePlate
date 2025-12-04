"""
Targeted tests for app.py DB fallback logic (lines 299-425) to reach 97% coverage.

Covers _attempt_db_fallback function branches:
- Production in-memory fallback rejection
- Production persistent fallback with/without ALLOW_DB_PERSISTENT_FALLBACK
- Non-production fallback paths
"""

import os
from unittest.mock import MagicMock, patch

import pytest


class TestAppDBFallback97:
    """Tests for app.py DB fallback logic to achieve 97% coverage."""

    TRUTHY = {"1", "true", "yes", "on"}

    def test_attempt_db_fallback_production_inmemory_rejected(self) -> None:
        """Production environment rejects in-memory DB fallback."""
        import app

        # Simulate production environment with in-memory fallback
        with patch.dict(os.environ, {"DB_FALLBACK_URL": "sqlite:///:memory:"}):
            mock_err = Exception("Primary DB failed")

            with pytest.raises(Exception, match="Primary DB failed"):
                app._attempt_db_fallback(
                    env_name="production",
                    is_production=True,
                    db_err=mock_err,
                    truthy=self.TRUTHY,
                )

    def test_attempt_db_fallback_production_no_override(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Production rejects fallback when ALLOW_DB_PERSISTENT_FALLBACK not set."""
        import app

        monkeypatch.setenv("DB_FALLBACK_URL", "sqlite:///./fallback.db")
        # Ensure ALLOW_DB_PERSISTENT_FALLBACK is NOT set
        monkeypatch.delenv("ALLOW_DB_PERSISTENT_FALLBACK", raising=False)

        mock_err = Exception("Primary DB failed")

        with pytest.raises(Exception, match="Primary DB failed"):
            app._attempt_db_fallback(
                env_name="production",
                is_production=True,
                db_err=mock_err,
                truthy=self.TRUTHY,
            )

    def test_attempt_db_fallback_production_persistent_allowed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Production allows persistent fallback when explicitly enabled."""
        import app

        monkeypatch.setenv("DB_FALLBACK_URL", "sqlite:///./prod_fallback.db")
        monkeypatch.setenv("ALLOW_DB_PERSISTENT_FALLBACK", "1")

        mock_err = Exception("Primary DB failed")

        # Mock SQLAlchemy engine creation to avoid actual DB operations
        with (
            patch("sqlalchemy.create_engine") as mock_create_engine,
            patch("core.models.Base") as mock_base,
            patch("core.db.SessionLocal") as mock_session,
        ):
            mock_engine = MagicMock()
            mock_create_engine.return_value = mock_engine
            mock_base.metadata.create_all = MagicMock()
            mock_session.configure = MagicMock()

            # Should not raise
            app._attempt_db_fallback(
                env_name="production",
                is_production=True,
                db_err=mock_err,
                truthy=self.TRUTHY,
            )

            # Verify fallback was attempted
            mock_create_engine.assert_called_once()
            assert "sqlite:///./prod_fallback.db" in str(mock_create_engine.call_args)

    def test_attempt_db_fallback_nonproduction_inmemory_allowed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Non-production environment allows in-memory fallback."""
        import app

        monkeypatch.setenv("DB_FALLBACK_URL", "sqlite:///:memory:")
        monkeypatch.delenv("ALLOW_DB_INMEMORY_FALLBACK", raising=False)

        mock_err = OSError("Primary DB failed")

        with (
            patch("sqlalchemy.create_engine") as mock_create_engine,
            patch("core.models.Base"),
            patch("core.db.SessionLocal"),
        ):
            mock_engine = MagicMock()
            mock_create_engine.return_value = mock_engine

            # Should not raise
            app._attempt_db_fallback(
                env_name="local",
                is_production=False,
                db_err=mock_err,
                truthy=self.TRUTHY,
            )

            mock_create_engine.assert_called_once()

    def test_attempt_db_fallback_nonproduction_explicit_override(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Non-production with explicit ALLOW_DB_INMEMORY_FALLBACK=1."""
        import app

        monkeypatch.setenv("DB_FALLBACK_URL", "sqlite:///:memory:")
        monkeypatch.setenv("ALLOW_DB_INMEMORY_FALLBACK", "true")

        mock_err = Exception("Generic DB error")

        with (
            patch("sqlalchemy.create_engine") as mock_create_engine,
            patch("core.models.Base"),
            patch("core.db.SessionLocal"),
        ):
            mock_engine = MagicMock()
            mock_create_engine.return_value = mock_engine

            app._attempt_db_fallback(
                env_name="dev",
                is_production=False,
                db_err=mock_err,
                truthy=self.TRUTHY,
            )

            mock_create_engine.assert_called_once()

    def test_attempt_db_fallback_fallback_init_fails(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Fallback DB initialization failure re-raises original error."""
        import app

        monkeypatch.setenv("DB_FALLBACK_URL", "sqlite:///:memory:")
        mock_err = OSError("Primary DB failed")

        with patch("sqlalchemy.create_engine", side_effect=Exception("Fallback failed")):
            # Should raise original error when fallback fails
            with pytest.raises(OSError, match="Primary DB failed"):
                app._attempt_db_fallback(
                    env_name="local",
                    is_production=False,
                    db_err=mock_err,
                    truthy=self.TRUTHY,
                )
