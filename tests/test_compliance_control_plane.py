"""Deterministic tests for the EU-first compliance control plane."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import cast
from unittest.mock import MagicMock

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.compliance import dsar_service
from core.compliance import (
    build_privacy_endpoint_payload,
    build_direct_user_deletion_plan,
    delete_direct_user_artifacts,
    export_direct_user_artifacts,
    get_dsar_artifact_map,
    get_provider_inventory,
    get_sensitive_field_taxonomy,
    get_transparency_registry,
    minimize_free_text,
    sanitize_audit_string,
    summarize_dsar_support,
)
from core.compliance.transparency import get_blocked_regulated_lane


def test_privacy_payload_contains_additive_control_plane_fields() -> None:
    payload = build_privacy_endpoint_payload()

    assert payload["policy_version"] == "2026-03-08.eu-first.v1"
    assert payload["last_updated"] == "2026-03-08"
    assert isinstance(payload["providers"], list)
    assert isinstance(payload["processing_categories"], list)
    assert isinstance(payload["rights"], list)
    assert isinstance(payload["automated_analysis"], list)
    retention_summary = cast(dict[str, object], payload["retention_summary"])
    artifact_support = cast(dict[str, int], retention_summary["artifact_support"])
    assert artifact_support["artifact_count"] >= 1
    processing_categories = cast(list[dict[str, object]], payload["processing_categories"])
    wellness_inputs = next(
        item for item in processing_categories if item["category_id"] == "wellness_profile_inputs"
    )
    endpoints = cast(list[str], wellness_inputs["endpoints"])
    assert "/api/v1/pro/meal/weekly" in endpoints
    assert "/api/v1/premium/plate" in endpoints


def test_transparency_registry_covers_core_healthish_surfaces() -> None:
    registry = get_transparency_registry()

    assert "bmi_wellness_screening" in registry
    assert "bodyfat_estimation" in registry
    assert "nutrition_targets_and_weekly_plan" in registry
    assert "ai_generated_insight" in registry
    ai_generated_insight = registry["ai_generated_insight"]
    assert ai_generated_insight["analysis_kind"] == "automated AI-assisted analysis"
    nutrition_surface = registry["nutrition_targets_and_weekly_plan"]
    nutrition_endpoints = cast(list[str], nutrition_surface["endpoints"])
    assert "/api/v1/pro/meal/weekly" in nutrition_endpoints


def test_sensitive_field_taxonomy_and_minimization_rules() -> None:
    taxonomy = get_sensitive_field_taxonomy()

    assert taxonomy["prompt"].persistence_rule == "hash_only"
    assert taxonomy["query"].persistence_rule == "redact_and_truncate"
    minimized_query = minimize_free_text(
        "user@example.com " + "x" * 800,
        field_name="query",
    )
    hashed_prompt = minimize_free_text("private provider prompt", field_name="prompt")

    assert minimized_query is not None
    assert "[EMAIL_REDACTED]" in minimized_query
    assert "user@example.com" not in minimized_query
    assert len(minimized_query) <= 512
    assert hashed_prompt is not None
    assert len(hashed_prompt) == 64


def test_dsar_artifact_map_distinguishes_direct_and_indirect_artifacts() -> None:
    artifact_map = get_dsar_artifact_map()
    support = summarize_dsar_support()

    artifact_ids = {item["artifact_id"] for item in artifact_map}
    assert "rag_feedback" in artifact_ids
    assert "agent_control_audit" in artifact_ids
    assert support["artifact_count"] == len(artifact_map)
    assert support["deletion_supported_count"] >= 1


def test_provider_inventory_includes_local_and_conditional_ai_families() -> None:
    inventory = get_provider_inventory()
    provider_ids = {item["provider_id"] for item in inventory}

    assert "local_runtime" in provider_ids
    assert "ollama_self_hosted" in provider_ids
    assert "xai_grok" in provider_ids


def test_dsar_timestamp_serializer_covers_none_and_aware_values() -> None:
    aware_dt = datetime(2026, 3, 9, 12, 0, tzinfo=timezone.utc)
    naive_dt = datetime(2026, 3, 9, 12, 0)

    assert dsar_service._serialize_timestamp(None) is None
    assert dsar_service._serialize_timestamp(aware_dt) == aware_dt.isoformat()
    assert (
        dsar_service._serialize_timestamp(naive_dt)
        == naive_dt.replace(tzinfo=timezone.utc).isoformat()
    )


def test_minimization_fallback_and_drop_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import core.compliance.minimization as minimization

    unknown_minimized = minimize_free_text("plain text", field_name="unmapped_field")
    audit_marker = sanitize_audit_string("unmapped_field", "plain text")
    assert isinstance(audit_marker, dict)
    assert unknown_minimized == audit_marker["sha256"]
    assert audit_marker["length"] == len("plain text")
    assert audit_marker["sha256"]

    drop_policy = minimization.SensitiveFieldPolicy(
        field_name="drop_field",
        persistence_rule="drop",
        max_chars=None,
        rationale="test-only coverage branch",
    )
    monkeypatch.setitem(minimization._SENSITIVE_FIELD_TAXONOMY, "drop_field", drop_policy)

    assert minimize_free_text("secret", field_name="drop_field") is None
    assert sanitize_audit_string("drop_field", "secret") is None


def test_blocked_regulated_lane_returns_deep_copy() -> None:
    first = get_blocked_regulated_lane()
    first_examples = cast(list[str], first["examples"])
    first_examples.append("mutated")
    second = get_blocked_regulated_lane()
    second_examples = cast(list[str], second["examples"])

    assert "mutated" not in second_examples


def test_canonical_field_name_avoids_loose_substring_matches() -> None:
    aliased = minimize_free_text(
        "person@example.com " + "x" * 400,
        field_name="query_preview",
    )
    canonical = minimize_free_text(
        "person@example.com " + "x" * 400,
        field_name="preview",
    )
    unmatched = minimize_free_text("plain text", field_name="request_context")

    assert aliased == canonical
    assert unmatched is not None
    assert len(unmatched) == 64


def test_dsar_helpers_export_and_delete_direct_user_artifacts() -> None:
    from app.models.rag_feedback import RAGFeedback, UserKnowledge
    from core.db import SessionLocal
    from core.models import User

    assert SessionLocal is not None

    with SessionLocal() as session:
        existing_user = session.execute(
            select(User).where(User.email == "dsar-direct@example.com")
        ).scalar_one_or_none()
        if existing_user is not None:
            delete_direct_user_artifacts(session=session, user_id=existing_user.id)
            session.delete(existing_user)
            session.commit()

        user = User(email="dsar-direct@example.com", name="DSAR Direct User")
        session.add(user)
        session.flush()
        user_id = user.id

        session.add(
            RAGFeedback(
                user_id=user_id,
                agent_id="insight",
                query="[EMAIL_REDACTED] wants a plate",
                retrieved_chunks=[{"chunk_id": "c1", "preview": "lean protein", "score": 0.9}],
                llm_response="balanced plan",
                user_rating=5,
                user_correction="more fiber",
                confidence=0.91,
                hops=2,
            )
        )
        session.add(
            UserKnowledge(
                user_id=user_id,
                content="prefers oatmeal breakfasts",
                embedding="[0.1,0.2]",
                source="manual_note",
            )
        )
        session.commit()

        exported = export_direct_user_artifacts(session=session, user_id=user_id)

        counts = cast(dict[str, int], exported["artifact_counts"])
        artifacts = cast(dict[str, object], exported["artifacts"])
        user_record = cast(dict[str, object], artifacts["account_user_record"])
        feedback_records = cast(list[dict[str, object]], artifacts["rag_feedback"])
        knowledge_records = cast(list[dict[str, object]], artifacts["user_knowledge"])

        assert counts == {
            "account_user_record": 1,
            "rag_feedback": 1,
            "user_knowledge": 1,
        }
        assert user_record["email"] == "dsar-direct@example.com"
        assert feedback_records[0]["query"] == "[EMAIL_REDACTED] wants a plate"
        assert knowledge_records[0]["content"] == "prefers oatmeal breakfasts"

        deletion_plan = build_direct_user_deletion_plan(session=session, user_id=user_id)
        plan_artifacts = cast(dict[str, dict[str, object]], deletion_plan["artifacts"])
        assert (
            plan_artifacts["account_user_record"]["helper_action"]
            == "manual_existing_user_delete_flow"
        )
        assert plan_artifacts["rag_feedback"]["present_count"] == 1
        assert plan_artifacts["user_knowledge"]["present_count"] == 1

        deleted = delete_direct_user_artifacts(session=session, user_id=user_id)

        deleted_counts = cast(dict[str, int], deleted["deleted"])
        assert deleted_counts == {
            "account_user_record": 0,
            "rag_feedback": 1,
            "user_knowledge": 1,
        }
        assert deleted["deleted_any"] is True
        assert deleted["pending_manual_artifacts"] == ["account_user_record"]
        assert export_direct_user_artifacts(session=session, user_id=user_id)[
            "artifact_counts"
        ] == {
            "account_user_record": 1,
            "rag_feedback": 0,
            "user_knowledge": 0,
        }
        cleanup = session.get(User, user_id)
        if cleanup is not None:
            session.delete(cleanup)
            session.commit()


def test_dsar_delete_helper_is_idempotent_for_missing_user() -> None:
    from core.db import SessionLocal

    assert SessionLocal is not None

    with SessionLocal() as session:
        deleted = delete_direct_user_artifacts(session=session, user_id=999_999)

    assert deleted == {
        "user_id": 999_999,
        "deleted": {
            "account_user_record": 0,
            "rag_feedback": 0,
            "user_knowledge": 0,
        },
        "deleted_any": False,
        "pending_manual_artifacts": [],
    }


def test_dsar_deletion_plan_handles_user_without_direct_artifacts() -> None:
    from core.db import SessionLocal
    from core.models import User

    assert SessionLocal is not None

    with SessionLocal() as session:
        existing_user = session.execute(
            select(User).where(User.email == "dsar-empty@example.com")
        ).scalar_one_or_none()
        if existing_user is not None:
            session.delete(existing_user)
            session.commit()

        user = User(email="dsar-empty@example.com", name="DSAR Empty User")
        session.add(user)
        session.commit()

        deletion_plan = build_direct_user_deletion_plan(session=session, user_id=user.id)
        plan_artifacts = cast(dict[str, dict[str, object]], deletion_plan["artifacts"])

        assert plan_artifacts["account_user_record"]["present"] is True
        assert plan_artifacts["rag_feedback"]["present_count"] == 0
        assert plan_artifacts["user_knowledge"]["present_count"] == 0

        session.delete(user)
        session.commit()


def test_dsar_delete_helper_preserves_account_row_without_direct_artifacts() -> None:
    from core.db import SessionLocal
    from core.models import User

    assert SessionLocal is not None

    with SessionLocal() as session:
        existing_user = session.execute(
            select(User).where(User.email == "dsar-no-artifacts@example.com")
        ).scalar_one_or_none()
        if existing_user is not None:
            session.delete(existing_user)
            session.commit()

        user = User(email="dsar-no-artifacts@example.com", name="DSAR No Artifacts User")
        session.add(user)
        session.commit()

        deleted = delete_direct_user_artifacts(session=session, user_id=user.id)

        assert deleted == {
            "user_id": user.id,
            "deleted": {
                "account_user_record": 0,
                "rag_feedback": 0,
                "user_knowledge": 0,
            },
            "deleted_any": False,
            "pending_manual_artifacts": ["account_user_record"],
        }

        cleanup = session.get(User, user.id)
        if cleanup is not None:
            session.delete(cleanup)
            session.commit()


def test_dsar_delete_helper_rolls_back_and_logs_on_delete_failure(
    caplog: pytest.LogCaptureFixture,
) -> None:
    class BrokenSession:
        def __init__(self) -> None:
            self.rollback_called = False

        def get(self, _model: object, _user_id: int) -> object:
            return object()

        def execute(self, _statement: object) -> object:
            raise RuntimeError("delete boom")

        def rollback(self) -> None:
            self.rollback_called = True

    broken_session = BrokenSession()

    with caplog.at_level("ERROR", logger="core.compliance.dsar_service"):
        with pytest.raises(RuntimeError, match="delete boom"):
            delete_direct_user_artifacts(session=cast(Session, broken_session), user_id=7)

    assert broken_session.rollback_called is True
    assert "DSAR direct-user artifact delete failed" in caplog.text


def test_dsar_helpers_apply_db_rls_context(monkeypatch: pytest.MonkeyPatch) -> None:
    """DSAR helpers must set DB RLS context before user-bound SQL operations."""
    trace: list[tuple[str, str, int | None]] = []
    current_helper = {"name": ""}

    monkeypatch.setattr(
        dsar_service,
        "apply_user_rls_context",
        lambda session, *, user_id: trace.append(("apply", current_helper["name"], user_id)),
    )

    session = MagicMock()
    scalar_result = MagicMock()
    scalar_result.scalar_one.return_value = 0
    scalar_result.scalars.return_value.all.return_value = []
    session.get.side_effect = (
        lambda *args, **kwargs: trace.append(("get", current_helper["name"], None)) or None
    )
    session.execute.side_effect = (
        lambda *args, **kwargs: trace.append(("execute", current_helper["name"], None))
        or scalar_result
    )

    for helper in (
        export_direct_user_artifacts,
        build_direct_user_deletion_plan,
        delete_direct_user_artifacts,
    ):
        current_helper["name"] = helper.__name__
        helper(session=cast(Session, session), user_id=17)

    for helper_name in (
        "export_direct_user_artifacts",
        "build_direct_user_deletion_plan",
        "delete_direct_user_artifacts",
    ):
        helper_trace = [event for event in trace if event[1] == helper_name]
        assert helper_trace[0] == ("apply", helper_name, 17)
        assert any(event[0] in {"get", "execute"} for event in helper_trace[1:])
