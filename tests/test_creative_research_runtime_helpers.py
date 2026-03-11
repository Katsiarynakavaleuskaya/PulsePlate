"""Focused unit tests for creative research runtime helper branches."""

from __future__ import annotations

import pytest

from app.services.creative_research_runtime import (
    _extract_json_payload,
    _normalize_provider_bundle,
    _normalize_provider_candidate,
    _persist_privileged_action_audit,
)


def test_extract_json_payload_accepts_fenced_json() -> None:
    """Fenced provider output must normalize into the first JSON object."""

    payload = _extract_json_payload("""```json\n{\"candidate\": 1}\n```""")

    assert payload == {"candidate": 1}


def test_extract_json_payload_accepts_embedded_json_object() -> None:
    """Embedded provider output must extract the enclosed JSON object."""

    payload = _extract_json_payload('prefix {"candidate": 2} suffix')

    assert payload == {"candidate": 2}


def test_normalize_provider_candidate_defaults_unknown_confidence_and_boundary() -> None:
    """Unexpected provider fields must degrade to safe deterministic defaults."""

    candidate = _normalize_provider_candidate(
        {
            "candidate_id": "",
            "claim": "Weekend depletion affects adherence.",
            "mechanism": "Friction rises after routine disruption.",
            "evidence_needed": "Track completion across weeks.",
            "falsifier": "If the pattern stays flat, reject it.",
            "confidence": "certain",
            "known_risks": "not-a-list",
            "wellness_boundary": "   ",
        },
        index=3,
    )

    assert candidate["candidate_id"] == "candidate-3"
    assert candidate["confidence"] == "unknown"
    assert candidate["known_risks"] == []
    assert candidate["wellness_boundary"] == (
        "Wellness only; not diagnosis, treatment, or medical advice."
    )


def test_normalize_provider_bundle_supports_nested_candidates_dict() -> None:
    """Nested provider candidate containers must collapse into the canonical bundle shape."""

    bundle = _normalize_provider_bundle(
        {
            "bundle_id": "",
            "candidates": {
                "candidates": [
                    {
                        "candidate_id": "nested-1",
                        "claim": "Fallback meals reduce friction.",
                        "mechanism": "A predefined meal shrinks end-of-day decisions.",
                        "evidence_needed": "Compare adherence before and after prompts.",
                        "falsifier": "If adherence is unchanged, reject the mechanism.",
                        "confidence": "medium",
                        "known_risks": ["self-report bias"],
                        "wellness_boundary": "Wellness only; not diagnosis, treatment, or medical advice.",
                    }
                ]
            },
        },
        prompt_seed="meal adherence",
        reference_corpus=["alpha", "beta", "gamma"],
        candidate_count=1,
        bundle_id="fallback-id",
    )

    assert bundle["bundle_id"] == "fallback-id"
    assert bundle["phase"] == "verification"
    assert bundle["reference_corpus"] == ["alpha", "beta"]
    assert bundle["candidates"][0]["candidate_id"] == "nested-1"


def test_normalize_provider_bundle_rejects_invalid_candidate_shapes() -> None:
    """Provider bundles must fail closed on empty or non-object candidate payloads."""

    with pytest.raises(ValueError, match="non-empty candidates list"):
        _normalize_provider_bundle(
            {"candidates": {"candidates": []}},
            prompt_seed="meal adherence",
            reference_corpus=[],
            candidate_count=2,
            bundle_id="bundle-1",
        )

    with pytest.raises(ValueError, match="candidates must be objects"):
        _normalize_provider_bundle(
            {"candidates": ["not-a-dict"]},
            prompt_seed="meal adherence",
            reference_corpus=[],
            candidate_count=2,
            bundle_id="bundle-2",
        )


def test_normalize_provider_bundle_rejects_underfilled_candidate_sets() -> None:
    """Provider bundles must not silently accept fewer candidates than requested."""

    with pytest.raises(ValueError, match="fewer valid candidates"):
        _normalize_provider_bundle(
            {
                "candidates": [
                    {
                        "candidate_id": "only-one",
                        "claim": "Fallback dinners reduce friction.",
                        "mechanism": "A predefined fallback lowers decision fatigue.",
                        "evidence_needed": "Track adherence before and after prompts.",
                        "falsifier": "If adherence remains flat, reject the mechanism.",
                        "confidence": "medium",
                        "known_risks": ["self-report bias"],
                        "wellness_boundary": "Wellness only; not diagnosis, treatment, or medical advice.",
                    }
                ]
            },
            prompt_seed="meal adherence",
            reference_corpus=[],
            candidate_count=2,
            bundle_id="bundle-3",
        )


def test_persist_privileged_action_audit_uses_server_salt_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Audit persistence must use server salt when an explicit signing key is absent."""

    captured: dict[str, object] = {}
    monkeypatch.delenv("AUDIT_SIGNING_KEY", raising=False)
    monkeypatch.setattr(
        "app.services.creative_research_runtime.require_policy_allow",
        lambda *args, **kwargs: {"decision": "allow"},
    )
    monkeypatch.setattr(
        "app.services.creative_research_runtime.require_server_salt",
        lambda: "server-salt",
    )
    monkeypatch.setattr(
        "app.services.creative_research_runtime.sign_audit_envelope",
        lambda decision, *, metadata, secret: {
            "decision": decision,
            "metadata": metadata,
            "signed_with": secret,
        },
    )
    monkeypatch.setattr(
        "app.services.creative_research_runtime.persist_audit_envelope",
        lambda envelope, *, metadata: captured.update({"envelope": envelope, "metadata": metadata}),
    )

    _persist_privileged_action_audit(
        endpoint="/api/v1/internal/creative-research/pilot",
        method="POST",
        mode="auto-safe",
        prompt="Meal adherence under time scarcity",
        candidate_count=4,
        reference_count=2,
    )

    assert captured["metadata"] == {
        "endpoint": "/api/v1/internal/creative-research/pilot",
        "method": "POST",
        "mode": "auto-safe",
        "prompt_hash": captured["metadata"]["prompt_hash"],
        "prompt_length": len("Meal adherence under time scarcity"),
        "candidate_count": 4,
        "reference_count": 2,
    }
    assert captured["envelope"]["signed_with"] == "server-salt"
