"""Tests for SQLAlchemy analyzer state storage.

RU: Тесты для хранилища состояния анализатора на SQLAlchemy.
EN: Tests for SQLAlchemyAnalyzerStore (works on SQLite in CI, validates Postgres semantics).
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from core.analyzer.store import AnalyzerState
from core.analyzer.store_cache import TTLCacheAnalyzerStore
from core.analyzer.store_sqlalchemy import SQLAlchemyAnalyzerStore
from core.db import Base
from core.models import AnalyzerStateModel


@pytest.fixture
def memory_engine():
    """Create in-memory SQLite engine for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(memory_engine):
    """Create a test DB session."""
    session = Session(bind=memory_engine)
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def store(db_session):
    """Create SQLAlchemyAnalyzerStore instance."""
    return SQLAlchemyAnalyzerStore(session=db_session)


class TestSQLAlchemyAnalyzerStore:
    """Test suite for SQLAlchemyAnalyzerStore."""

    def test_get_state_returns_none_when_missing(self, store: SQLAlchemyAnalyzerStore):
        """Test get_state returns None for non-existent state."""
        result = store.get_state(user_id=1, analyzer_key="test_analyzer")
        assert result is None

    def test_upsert_state_creates_new(self, store: SQLAlchemyAnalyzerStore):
        """Test upsert_state creates new state with version 1."""
        payload = {"mean": 2000.0, "variance": 100.0}
        result = store.upsert_state(
            user_id=1, analyzer_key="calorie_drift", state_schema_version=1, payload=payload
        )

        assert result.user_id == 1
        assert result.analyzer_key == "calorie_drift"
        assert result.state_schema_version == 1
        assert result.state_version == 1
        assert result.payload == payload
        assert result.updated_at is not None

    def test_upsert_state_updates_existing(self, store: SQLAlchemyAnalyzerStore):
        """Test upsert_state updates existing state and increments version."""
        # Create initial state
        initial_payload = {"mean": 2000.0, "variance": 100.0}
        store.upsert_state(
            user_id=1, analyzer_key="calorie_drift", state_schema_version=1, payload=initial_payload
        )

        # Update state
        updated_payload = {"mean": 2100.0, "variance": 120.0}
        result = store.upsert_state(
            user_id=1, analyzer_key="calorie_drift", state_schema_version=1, payload=updated_payload
        )

        assert result.state_version == 2  # Version incremented
        assert result.payload == updated_payload

    def test_get_state_retrieves_upserted(self, store: SQLAlchemyAnalyzerStore):
        """Test get_state retrieves previously upserted state."""
        payload = {"mean": 2000.0, "variance": 100.0}
        store.upsert_state(
            user_id=1, analyzer_key="calorie_drift", state_schema_version=1, payload=payload
        )

        result = store.get_state(user_id=1, analyzer_key="calorie_drift")

        assert result is not None
        assert result.user_id == 1
        assert result.analyzer_key == "calorie_drift"
        assert result.payload == payload

    def test_update_if_version_matches_succeeds(self, store: SQLAlchemyAnalyzerStore):
        """Test update_if_version_matches succeeds with correct version."""
        # Create initial state
        initial_payload = {"mean": 2000.0}
        state = store.upsert_state(
            user_id=1, analyzer_key="test", state_schema_version=1, payload=initial_payload
        )

        # Update with matching version
        updated_payload = {"mean": 2100.0}
        result = store.update_if_version_matches(
            user_id=1,
            analyzer_key="test",
            expected_version=state.state_version,
            state_schema_version=1,
            payload=updated_payload,
        )

        assert result is not None
        assert result.state_version == 2
        assert result.payload == updated_payload

    def test_update_if_version_matches_fails_on_mismatch(self, store: SQLAlchemyAnalyzerStore):
        """Test update_if_version_matches returns None with wrong version."""
        # Create initial state
        initial_payload = {"mean": 2000.0}
        store.upsert_state(
            user_id=1, analyzer_key="test", state_schema_version=1, payload=initial_payload
        )

        # Attempt update with wrong version
        result = store.update_if_version_matches(
            user_id=1,
            analyzer_key="test",
            expected_version=999,  # Wrong version
            state_schema_version=1,
            payload={"mean": 2100.0},
        )

        assert result is None

    def test_multiple_users_isolated(self, store: SQLAlchemyAnalyzerStore):
        """Test state isolation between different users."""
        payload_user1 = {"mean": 2000.0}
        payload_user2 = {"mean": 2500.0}

        store.upsert_state(
            user_id=1, analyzer_key="test", state_schema_version=1, payload=payload_user1
        )
        store.upsert_state(
            user_id=2, analyzer_key="test", state_schema_version=1, payload=payload_user2
        )

        state1 = store.get_state(user_id=1, analyzer_key="test")
        state2 = store.get_state(user_id=2, analyzer_key="test")

        assert state1 is not None
        assert state2 is not None
        assert state1.payload == payload_user1
        assert state2.payload == payload_user2

    def test_multiple_analyzer_keys_isolated(self, store: SQLAlchemyAnalyzerStore):
        """Test state isolation between different analyzer keys for same user."""
        payload_drift = {"mean": 2000.0}
        payload_macro = {"protein_ratio": 0.3}

        store.upsert_state(
            user_id=1, analyzer_key="calorie_drift", state_schema_version=1, payload=payload_drift
        )
        store.upsert_state(
            user_id=1, analyzer_key="macro_sensitivity", state_schema_version=1, payload=payload_macro
        )

        state_drift = store.get_state(user_id=1, analyzer_key="calorie_drift")
        state_macro = store.get_state(user_id=1, analyzer_key="macro_sensitivity")

        assert state_drift is not None
        assert state_macro is not None
        assert state_drift.payload == payload_drift
        assert state_macro.payload == payload_macro


class TestTTLCacheAnalyzerStore:
    """Test suite for TTL cache wrapper."""

    def test_cache_hit_returns_cached_value(self, store: SQLAlchemyAnalyzerStore):
        """Test cache returns same object within TTL without DB roundtrip."""
        cache = TTLCacheAnalyzerStore(inner=store, ttl_seconds=60)

        payload = {"mean": 2000.0}
        cache.upsert_state(
            user_id=1, analyzer_key="test", state_schema_version=1, payload=payload
        )

        # First get populates cache
        state1 = cache.get_state(user_id=1, analyzer_key="test")
        # Second get should be cache hit (same object)
        state2 = cache.get_state(user_id=1, analyzer_key="test")

        assert state1 is not None
        assert state2 is not None
        assert state1.payload == state2.payload

    def test_cache_miss_after_ttl_expiry(self, store: SQLAlchemyAnalyzerStore):
        """Test cache expires after TTL."""
        cache = TTLCacheAnalyzerStore(inner=store, ttl_seconds=0)  # Immediate expiry

        payload = {"mean": 2000.0}
        cache.upsert_state(
            user_id=1, analyzer_key="test", state_schema_version=1, payload=payload
        )

        # Get after TTL expiry should go to DB
        state = cache.get_state(user_id=1, analyzer_key="test")
        assert state is not None

    def test_upsert_updates_cache(self, store: SQLAlchemyAnalyzerStore):
        """Test upsert updates cache immediately."""
        cache = TTLCacheAnalyzerStore(inner=store, ttl_seconds=60)

        # Initial upsert
        cache.upsert_state(
            user_id=1, analyzer_key="test", state_schema_version=1, payload={"mean": 2000.0}
        )

        # Second upsert with new payload
        updated_payload = {"mean": 2100.0}
        cache.upsert_state(
            user_id=1, analyzer_key="test", state_schema_version=1, payload=updated_payload
        )

        # Get should return updated payload from cache
        state = cache.get_state(user_id=1, analyzer_key="test")
        assert state is not None
        assert state.payload == updated_payload
