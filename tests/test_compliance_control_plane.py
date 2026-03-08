"""Deterministic tests for the EU-first compliance control plane."""

from __future__ import annotations

import importlib

import pytest

from core.compliance import (
    build_privacy_endpoint_payload,
    get_dsar_artifact_map,
    get_provider_inventory,
    get_sensitive_field_taxonomy,
    get_transparency_registry,
    minimize_free_text,
    summarize_dsar_support,
)


def test_privacy_payload_contains_additive_control_plane_fields() -> None:
    payload = build_privacy_endpoint_payload()

    assert payload["policy_version"] == "2026-03-08.eu-first.v1"
    assert payload["last_updated"] == "2026-03-08"
    assert isinstance(payload["providers"], list)
    assert isinstance(payload["processing_categories"], list)
    assert isinstance(payload["rights"], list)
    assert isinstance(payload["automated_analysis"], list)
    assert payload["retention_summary"]["artifact_support"]["artifact_count"] >= 1


def test_transparency_registry_covers_core_healthish_surfaces() -> None:
    registry = get_transparency_registry()

    assert "bmi_wellness_screening" in registry
    assert "bodyfat_estimation" in registry
    assert "nutrition_targets_and_weekly_plan" in registry
    assert "ai_generated_insight" in registry
    assert registry["ai_generated_insight"]["analysis_kind"] == "automated AI-assisted analysis"
    assert "/api/v1/pro/meal/weekly" in registry["nutrition_targets_and_weekly_plan"]["endpoints"]


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


def test_minimization_fallback_and_drop_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    minimization = importlib.import_module("core.compliance.minimization")

    assert minimize_free_text("plain text", field_name="unmapped_field") == "plain text"
    assert minimization.sanitize_audit_string("unmapped_field", "plain text") == "plain text"

    drop_policy = minimization.SensitiveFieldPolicy(
        field_name="drop_field",
        persistence_rule="drop",
        max_chars=None,
        rationale="test-only coverage branch",
    )
    monkeypatch.setitem(minimization._SENSITIVE_FIELD_TAXONOMY, "drop_field", drop_policy)

    assert minimize_free_text("secret", field_name="drop_field") is None
    assert minimization.sanitize_audit_string("drop_field", "secret") is None
