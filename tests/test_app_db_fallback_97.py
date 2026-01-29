"""
Targeted tests for core.db_fallback DB fallback logic to reach 97% coverage.

Covers _attempt_db_fallback function branches:
- Production in-memory fallback rejection
- Production persistent fallback with/without ALLOW_DB_PERSISTENT_FALLBACK
- Non-production fallback paths
"""

import os
from unittest.mock import MagicMock, patch

import pytest


class TestAppDBFallback97:
    """Tests for core.db_fallback DB fallback logic to achieve 97% coverage."""

    TRUTHY: set[str] = {"1", "true", "yes", "on"}

    @pytest.fixture(autouse=True)
    def _reset_fallback_flag(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Reset fallback state and ENV before each test to avoid cross-test leakage."""
        import core.db_fallback as fallback_mod

        monkeypatch.setattr(fallback_mod, "_db_fallback_active", False)
        for key in ("DB_HEALTH_DEGRADED", "DB_FALLBACK_URL", "DATABASE_URL"):
            monkeypatch.delenv(key, raising=False)

    def test_attempt_db_fallback_production_inmemory_rejected(self) -> None:
        """Production environment rejects in-memory DB fallback."""
        from core.db_fallback import _attempt_db_fallback

        # Simulate production environment with in-memory fallback
        with patch.dict(os.environ, {"DB_FALLBACK_URL": "sqlite:///:memory:"}):
            mock_err = Exception("Primary DB failed")

            with pytest.raises(Exception, match="Primary DB failed"):
                _attempt_db_fallback(
                    env_name="production",
                    is_production=True,
                    db_err=mock_err,
                    truthy=self.TRUTHY,
                )

    def test_attempt_db_fallback_production_inmemory_rejected_logs(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Cover db_fallback lines 81/87: production in-memory branch logs and raises."""
        from core.db_fallback import _attempt_db_fallback

        with patch.dict(os.environ, {"DB_FALLBACK_URL": "sqlite:///:memory:"}):
            mock_err = Exception("Primary DB failed")
            with pytest.raises(Exception, match="Primary DB failed"):
                _attempt_db_fallback(
                    env_name="production",
                    is_production=True,
                    db_err=mock_err,
                    truthy=self.TRUTHY,
                )
        assert "in-memory" in caplog.text or "CRITICAL" in caplog.text

    def test_attempt_db_fallback_production_no_override(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Production rejects fallback when ALLOW_DB_PERSISTENT_FALLBACK not set."""
        from core.db_fallback import _attempt_db_fallback

        monkeypatch.setenv("DB_FALLBACK_URL", "sqlite:///./fallback.db")
        # Ensure ALLOW_DB_PERSISTENT_FALLBACK is NOT set
        monkeypatch.delenv("ALLOW_DB_PERSISTENT_FALLBACK", raising=False)

        mock_err = Exception("Primary DB failed")

        with pytest.raises(Exception, match="Primary DB failed"):
            _attempt_db_fallback(
                env_name="production",
                is_production=True,
                db_err=mock_err,
                truthy=self.TRUTHY,
            )

    def test_attempt_db_fallback_production_persistent_allowed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Production allows persistent fallback when explicitly enabled."""
        from core.db_fallback import _attempt_db_fallback

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
            _attempt_db_fallback(
                env_name="production",
                is_production=True,
                db_err=mock_err,
                truthy=self.TRUTHY,
            )

            # Verify fallback was attempted
            mock_create_engine.assert_called_once()
            assert "sqlite:///./prod_fallback.db" in str(mock_create_engine.call_args)

    def test_attempt_db_fallback_production_persistent_logs(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Cover db_fallback line 87: production persistent path logger.warning."""
        from core.db_fallback import _attempt_db_fallback

        monkeypatch.setenv("DB_FALLBACK_URL", "sqlite:///./prod_fallback.db")
        monkeypatch.setenv("ALLOW_DB_PERSISTENT_FALLBACK", "1")
        mock_err = Exception("Primary DB failed")
        with (
            patch("sqlalchemy.create_engine") as mock_create_engine,
            patch("core.models.Base"),
            patch("core.db.SessionLocal"),
        ):
            mock_create_engine.return_value = MagicMock()
            _attempt_db_fallback(
                env_name="production",
                is_production=True,
                db_err=mock_err,
                truthy=self.TRUTHY,
            )
        assert "attempting persistent fallback" in caplog.text

    def test_attempt_db_fallback_nonproduction_inmemory_allowed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Non-production environment allows in-memory fallback."""
        from core.db_fallback import _attempt_db_fallback

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
            _attempt_db_fallback(
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
        from core.db_fallback import _attempt_db_fallback

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

            _attempt_db_fallback(
                env_name="dev",
                is_production=False,
                db_err=mock_err,
                truthy=self.TRUTHY,
            )

            mock_create_engine.assert_called_once()

    def test_attempt_db_fallback_fallback_init_fails(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Fallback DB initialization failure re-raises original error."""
        from core.db_fallback import _attempt_db_fallback

        monkeypatch.setenv("DB_FALLBACK_URL", "sqlite:///:memory:")
        mock_err = OSError("Primary DB failed")

        with patch("sqlalchemy.create_engine", side_effect=Exception("Fallback failed")):
            # Should raise original error when fallback fails
            with pytest.raises(OSError, match="Primary DB failed"):
                _attempt_db_fallback(
                    env_name="local",
                    is_production=False,
                    db_err=mock_err,
                    truthy=self.TRUTHY,
                )

    def test_check_production_constraints_inmemory_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Cover _check_production_constraints in-memory branch (lines 76-83)."""
        from core.db_fallback import _check_production_constraints

        monkeypatch.setenv("ALLOW_DB_PERSISTENT_FALLBACK", "1")
        db_err = ValueError("test")
        with pytest.raises(ValueError, match="test"):
            _check_production_constraints(
                env_name="prod",
                fallback_url="sqlite:///:memory:",
                truthy={"1", "yes"},
                db_err=db_err,
            )

    def test_check_production_constraints_persistent_logs(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Cover _check_production_constraints persistent URL path (line 87)."""
        from core.db_fallback import _check_production_constraints

        monkeypatch.setenv("ALLOW_DB_PERSISTENT_FALLBACK", "1")
        _check_production_constraints(
            env_name="production",
            fallback_url="sqlite:///./fallback.db",
            truthy=self.TRUTHY,
            db_err=Exception("x"),
        )
        assert "attempting persistent fallback" in caplog.text

    def test_configure_session_bindings_sessionlocal_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Cover _configure_session_bindings else branch (SessionLocal None, line 147)."""
        from core import db as core_db
        from core.db_fallback import _configure_session_bindings
        from sqlalchemy import create_engine

        engine = create_engine("sqlite:///:memory:")
        orig = getattr(core_db, "SessionLocal", None)
        try:
            monkeypatch.setattr(core_db, "SessionLocal", None)
            _configure_session_bindings(
                engine=engine,
                is_production=False,
                fallback_url="sqlite:///:memory:",
                env_name="test",
            )
            assert core_db.SessionLocal is not None
        finally:
            monkeypatch.setattr(core_db, "SessionLocal", orig, raising=False)

    def test_configure_session_bindings_configure_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Cover _configure_session_bindings except branch (lines 147, 150-151)."""
        from core import db as core_db
        from core.db_fallback import _configure_session_bindings
        from sqlalchemy import create_engine

        engine = create_engine("sqlite:///:memory:")
        mock_sl = MagicMock()
        mock_sl.configure.side_effect = RuntimeError("configure failed")
        orig = getattr(core_db, "SessionLocal", None)
        try:
            monkeypatch.setattr(core_db, "SessionLocal", mock_sl)
            _configure_session_bindings(
                engine=engine,
                is_production=False,
                fallback_url="sqlite:///:memory:",
                env_name="test",
            )
            assert core_db.SessionLocal is not None
        finally:
            monkeypatch.setattr(core_db, "SessionLocal", orig, raising=False)

    def test_attempt_db_fallback_via_configure_session_bindings_except(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Cover db_fallback lines 147, 150-151 via _attempt_db_fallback (SessionLocal.configure raises)."""
        from core import db as core_db
        from core.db_fallback import _attempt_db_fallback

        monkeypatch.setenv("DB_FALLBACK_URL", "sqlite:///:memory:")
        mock_sl = MagicMock()
        mock_sl.configure.side_effect = RuntimeError("configure failed")
        orig_sl = getattr(core_db, "SessionLocal", None)
        try:
            monkeypatch.setattr(core_db, "SessionLocal", mock_sl)
            with (
                patch("sqlalchemy.create_engine") as mock_create_engine,
                patch("core.models.Base"),
            ):
                mock_engine = MagicMock()
                mock_create_engine.return_value = mock_engine
                _attempt_db_fallback(
                    env_name="local",
                    is_production=False,
                    db_err=OSError("Primary DB failed"),
                    truthy=self.TRUTHY,
                )
            assert core_db.SessionLocal is not None
        finally:
            monkeypatch.setattr(core_db, "SessionLocal", orig_sl, raising=False)

    def test_attempt_db_fallback_nonproduction_logs(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Cover non-production logger.warning (line 230) via explicit override."""
        from core.db_fallback import _attempt_db_fallback

        monkeypatch.setenv("DB_FALLBACK_URL", "sqlite:///:memory:")
        monkeypatch.setenv("ALLOW_DB_INMEMORY_FALLBACK", "1")
        with (
            patch("sqlalchemy.create_engine") as mock_create_engine,
            patch("core.models.Base"),
            patch("core.db.SessionLocal"),
        ):
            mock_create_engine.return_value = MagicMock()
            _attempt_db_fallback(
                env_name="dev",
                is_production=False,
                db_err=Exception("Generic"),
                truthy=self.TRUTHY,
            )
        assert "attempting fallback SQLite" in caplog.text

    def test_attempt_db_fallback_nonproduction_oserror_logs(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Cover db_fallback line 230: non-production OSError path (fallback_exception) logs."""
        from core.db_fallback import _attempt_db_fallback

        monkeypatch.setenv("DB_FALLBACK_URL", "sqlite:///:memory:")
        monkeypatch.delenv("ALLOW_DB_INMEMORY_FALLBACK", raising=False)
        with (
            patch("sqlalchemy.create_engine") as mock_create_engine,
            patch("core.models.Base"),
            patch("core.db.SessionLocal"),
        ):
            mock_create_engine.return_value = MagicMock()
            _attempt_db_fallback(
                env_name="local",
                is_production=False,
                db_err=OSError("Primary DB failed"),
                truthy=self.TRUTHY,
            )
        assert "attempting fallback SQLite" in caplog.text
        assert "OSError" in caplog.text
