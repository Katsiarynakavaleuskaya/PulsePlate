"""
Simple tests for core/db.py to improve coverage.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from core.db import EngineCompat


class TestEngineCompat:
    """Test EngineCompat basic functionality."""

    def test_init(self):
        """Test initialization."""
        mock_engine = Mock()
        engine = EngineCompat(mock_engine)
        assert engine is not None
        assert engine._engine == mock_engine

    def test_execute_success(self):
        """Test successful execution."""
        mock_engine = Mock()
        engine = EngineCompat(mock_engine)

        mock_conn = Mock()
        mock_conn.execute.return_value = Mock()

        mock_connect = Mock()
        mock_connect.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_connect.return_value.__exit__ = Mock(return_value=False)
        mock_engine.connect = mock_connect

        result = engine.execute("SELECT 1")

        assert result is not None

    def test_execute_with_commit_error(self):
        """Test execution with commit error."""
        mock_engine = Mock()
        engine = EngineCompat(mock_engine)

        mock_conn = Mock()
        mock_conn.execute.return_value = Mock()
        mock_conn.commit.side_effect = Exception("Commit failed")

        mock_engine.connect.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = Mock(return_value=False)

        # Should not raise exception due to suppress
        with pytest.raises(Exception, match="Commit failed"):
            result = engine.execute("INSERT INTO test VALUES (1)")

    def test_execute_with_connection_error(self):
        """Test execution with connection error."""
        mock_engine = Mock()
        engine = EngineCompat(mock_engine)

        with patch.object(mock_engine, "connect") as mock_connect:
            mock_connect.side_effect = Exception("Connection failed")

            with pytest.raises(Exception, match="Connection failed"):
                engine.execute("SELECT 1")

    def test_execute_with_execution_error(self):
        """Test execution with execution error."""
        mock_engine = Mock()
        engine = EngineCompat(mock_engine)

        mock_conn = Mock()
        mock_conn.execute.side_effect = Exception("Execution failed")

        # Configure context manager for sync connect
        mock_engine.connect.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = Mock(return_value=False)

        with pytest.raises(Exception, match="Execution failed"):
            engine.execute("SELECT 1")

    def test_engine_compat_properties(self):
        """Test EngineCompat properties."""
        mock_engine = Mock()
        engine = EngineCompat(mock_engine)

        # Test that engine has expected attributes
        assert hasattr(engine, "execute")
        assert callable(engine.execute)
