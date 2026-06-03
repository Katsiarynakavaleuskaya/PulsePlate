"""Deterministic tests for the EU-first compliance control plane."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
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

_REPO_ROOT = Path(__file__).resolve().parents[1]
_LEGAL_PRIVACY_DOC = _REPO_ROOT / "docs/legal/Privacy.md"
_DATA_MATRIX_DOC = _REPO_ROOT / "docs/compliance/DATA_CLASSIFICATION_AND_PROCESSING_MATRIX.md"
_AI_NOTICE_DOC = _REPO_ROOT / "docs/compliance/AI_TRANSPARENCY_AND_PROFILING_NOTICE.md"
_PROVIDER_INVENTORY_DOC = _REPO_ROOT / "docs/compliance/PROVIDER_INVENTORY.md"
_REGULATED_LANE_DOC = _REPO_ROOT / "docs/compliance/US_REGULATED_LANE_RFC_42_CFR_PART_2.md"
_DSAR_MAP_DOC = _REPO_ROOT / "docs/compliance/DSAR_AND_DELETION_MAP.md"


def test_privacy_payload_contains_additive_control_plane_fields() -> None:
    payload = build_privacy_endpoint_payload()

    assert payload["policy_version"] == "2026-04-10.eu-first.v1"
    assert payload["last_updated"] == "2026-04-10"
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
    ai_generated_analysis = next(
        item
        for item in processing_categories
        if item["category_id"] == "ai_generated_wellness_analysis"
    )
    pseudonymous_identifiers = next(
        item
        for item in processing_categories
        if item["category_id"] == "pseudonymous_security_identifiers"
    )
    signed_audit_envelopes = next(
        item for item in processing_categories if item["category_id"] == "signed_audit_envelopes"
    )
    endpoints = cast(list[str], wellness_inputs["endpoints"])
    ai_generated_endpoints = list(cast(list[str], ai_generated_analysis["endpoints"]))
    pseudonymous_endpoints = cast(list[str], pseudonymous_identifiers["endpoints"])
    signed_audit_endpoints = cast(list[str], signed_audit_envelopes["endpoints"])
    llm_processing = cast(dict[str, object], payload["llm_processing"])
    llm_processing_endpoints = cast(list[str], llm_processing["endpoints"])
    assert "/api/v1/pro/meal/weekly" in endpoints
    assert "/api/v1/premium/plate" in endpoints
    assert "/api/v1/pro/fitchef/explain" in llm_processing_endpoints
    assert "/api/v1/vip/fitchef/insight" in llm_processing_endpoints
    assert "/api/v1/vip/fitchef/insight" in pseudonymous_endpoints
    assert "/api/v1/vip/fitchef/insight" in signed_audit_endpoints
    assert llm_processing_endpoints == ai_generated_endpoints


def test_privacy_metadata_stays_in_sync_with_canonical_docs() -> None:
    payload = build_privacy_endpoint_payload()
    legal_privacy_doc = _LEGAL_PRIVACY_DOC.read_text(encoding="utf-8")
    data_matrix_doc = _DATA_MATRIX_DOC.read_text(encoding="utf-8")
    ai_notice_doc = _AI_NOTICE_DOC.read_text(encoding="utf-8")
    provider_inventory_doc = _PROVIDER_INVENTORY_DOC.read_text(encoding="utf-8")
    regulated_lane_doc = _REGULATED_LANE_DOC.read_text(encoding="utf-8")
    retention_summary = cast(dict[str, object], payload["retention_summary"])
    regulated_lane = cast(dict[str, object], retention_summary["regulated_lane"])
    processing_categories = cast(list[dict[str, object]], payload["processing_categories"])
    ai_generated_surface = next(
        item
        for item in processing_categories
        if item["category_id"] == "ai_generated_wellness_analysis"
    )

    expected_policy_version = cast(str, payload["policy_version"])
    expected_last_updated = cast(str, payload["last_updated"])

    assert f"**Policy version:** `{expected_policy_version}`" in legal_privacy_doc
    assert f"**Policy version:** `{expected_policy_version}`" in data_matrix_doc
    assert f"**Policy version:** `{expected_policy_version}`" in ai_notice_doc
    assert f"**Last updated:** {expected_last_updated}" in legal_privacy_doc
    assert f"**Last updated:** {expected_last_updated}" in data_matrix_doc
    assert f"**Last updated:** {expected_last_updated}" in ai_notice_doc
    assert "Consumer wellness product, not a clinical system" in legal_privacy_doc
    assert (
        "This matrix is the canonical control-plane view for the current wellness runtime."
        in data_matrix_doc
    )
    assert (
        "PulsePlate treats health-adjacent AI features as **automated wellness analysis**."
        in ai_notice_doc
    )

    regulated_lane_examples = cast(list[str], regulated_lane["examples"])
    for blocked_example in regulated_lane_examples:
        assert blocked_example in ai_notice_doc
    assert "separate regulated lane" in ai_notice_doc

    provider_doc_markers = {
        "xai_grok": "xAI/Grok",
        "openai_compatible": "OpenAI-compatible",
        "anthropic_compatible": "Anthropic-compatible",
        "ollama_self_hosted": "Ollama-compatible",
        "otlp_trace_processor": "OTLP collector",
        "pico": "Pico",
    }
    providers = cast(list[dict[str, object]], payload["providers"])
    provider_ids = {cast(str, provider["provider_id"]) for provider in providers}
    for provider_id, doc_marker in provider_doc_markers.items():
        assert provider_id in provider_ids
        assert doc_marker in provider_inventory_doc
        assert doc_marker in legal_privacy_doc

    ai_generated_endpoints = cast(list[str], ai_generated_surface["endpoints"])
    ai_generated_exposure = cast(str, ai_generated_surface["third_party_exposure"])
    assert "/api/v1/pro/fitchef/explain" in ai_generated_endpoints
    assert "/api/v1/vip/fitchef/insight" in ai_generated_endpoints
    assert "/api/v1/pro/fitchef/explain" in legal_privacy_doc
    assert "/api/v1/vip/fitchef/insight" in legal_privacy_doc
    assert "/api/v1/pro/fitchef/explain" in data_matrix_doc
    assert "/api/v1/vip/fitchef/insight" in data_matrix_doc
    assert "telemetry processor" in provider_inventory_doc.lower()
    assert "telemetry processor" in legal_privacy_doc.lower()
    assert "Telemetry processors" in ai_notice_doc
    assert "telemetry trace processor is configured" in data_matrix_doc
    assert "telemetry trace processors" in ai_generated_exposure.lower()
    assert "does not activate the regulated lane by itself" in regulated_lane_doc
    regulated_lane_rule_text = cast(str, regulated_lane["rule"])
    assert "does not activate the regulated lane by itself" in regulated_lane_rule_text


def test_transparency_registry_covers_core_healthish_surfaces() -> None:
    registry = get_transparency_registry()
    ai_notice_doc = _AI_NOTICE_DOC.read_text(encoding="utf-8")

    assert "bmi_wellness_screening" in registry
    assert "bodyfat_estimation" in registry
    assert "nutrition_targets_and_weekly_plan" in registry
    assert "ai_generated_insight" in registry
    assert "fitchef_structured_v1" in registry
    ai_generated_insight = registry["ai_generated_insight"]
    assert ai_generated_insight["analysis_kind"] == "automated AI-assisted analysis"
    nutrition_surface = registry["nutrition_targets_and_weekly_plan"]
    nutrition_endpoints = cast(list[str], nutrition_surface["endpoints"])
    assert "/api/v1/pro/meal/weekly" in nutrition_endpoints
    fitchef_surface = registry["fitchef_structured_v1"]
    fitchef_endpoints = cast(list[str], fitchef_surface["endpoints"])
    assert fitchef_surface["analysis_kind"] == "automated AI-assisted wellness coaching structure"
    assert "/api/v1/pro/fitchef/explain" in fitchef_endpoints
    assert "/api/v1/vip/fitchef/insight" in fitchef_endpoints
    assert "fitchef_structured_v1" in ai_notice_doc
    assert "/api/v1/pro/fitchef/explain" in ai_notice_doc
    assert "/api/v1/vip/fitchef/insight" in ai_notice_doc


def test_sensitive_field_taxonomy_and_minimization_rules() -> None:
    taxonomy = get_sensitive_field_taxonomy()

    assert taxonomy["prompt"].persistence_rule == "hash_only"
    assert taxonomy["query"].persistence_rule == "redact_and_truncate"
    minimized_query = minimize_free_text(
        "user@example.com " + "x" * 800,
        field_name="query",
    )
    hashed_prompt = minimize_free_text("private provider prompt", field_name="prompt")
    minimized_response = minimize_free_text(
        "member@example.com " + "y" * 5000,
        field_name="llm_response",
    )
    minimized_correction = minimize_free_text(
        "member@example.com " + "z" * 5000,
        field_name="user_correction",
    )
    minimized_source_content = minimize_free_text(
        "member@example.com " + "k" * 1000,
        field_name="content",
    )
    hashed_provider_trace = minimize_free_text("trace payload", field_name="provider_trace")
    hashed_profile = minimize_free_text("profile payload", field_name="health_profile")

    assert minimized_query is not None
    assert "[EMAIL_REDACTED]" in minimized_query
    assert "user@example.com" not in minimized_query
    assert len(minimized_query) <= 512
    assert hashed_prompt is not None
    assert len(hashed_prompt) == 64
    assert taxonomy["llm_response"].persistence_rule == "redact_and_truncate"
    assert taxonomy["user_correction"].persistence_rule == "redact_and_truncate"
    assert taxonomy["source_content"].persistence_rule == "redact_and_truncate"
    assert taxonomy["provider_trace"].persistence_rule == "hash_only"
    assert taxonomy["health_profile"].persistence_rule == "hash_only"
    assert minimized_response is not None
    assert "[EMAIL_REDACTED]" in minimized_response
    assert "member@example.com" not in minimized_response
    assert len(minimized_response) <= 4000
    assert minimized_correction is not None
    assert "[EMAIL_REDACTED]" in minimized_correction
    assert "member@example.com" not in minimized_correction
    assert len(minimized_correction) <= 4000
    assert minimized_source_content is not None
    assert "[EMAIL_REDACTED]" in minimized_source_content
    assert "member@example.com" not in minimized_source_content
    assert len(minimized_source_content) <= 240
    assert hashed_provider_trace is not None
    assert len(hashed_provider_trace) == 64
    assert hashed_profile is not None
    assert len(hashed_profile) == 64


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
    assert any(item["provider_id"] == "otlp_trace_processor" for item in inventory)
    otlp_processor = next(
        item for item in inventory if item["provider_id"] == "otlp_trace_processor"
    )

    assert "local_runtime" in provider_ids
    assert "ollama_self_hosted" in provider_ids
    assert "xai_grok" in provider_ids
    assert otlp_processor["category"] == "telemetry_processor"
    assert "non-reversible, deployment-local" in cast(str, otlp_processor["data_scope"])
    assert "never raw prompts or completions" in cast(str, otlp_processor["data_scope"])


def test_privacy_docs_do_not_promise_public_dsar_api() -> None:
    legal_privacy_doc = _LEGAL_PRIVACY_DOC.read_text(encoding="utf-8").lower()
    dsar_map_doc = _DSAR_MAP_DOC.read_text(encoding="utf-8").lower()

    assert "public self-service endpoint is available" not in legal_privacy_doc
    assert "public dsar api is available" not in legal_privacy_doc
    assert "public dsar api still deferred" in dsar_map_doc
    assert dsar_map_doc.count("public dsar api") == 1


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
