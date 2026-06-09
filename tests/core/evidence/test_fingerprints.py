from __future__ import annotations

import re
from typing import cast

import pytest

from core.evidence.fingerprints import (
    JsonValue,
    fingerprint_payload,
    fingerprint_provenance_envelope,
)
from core.evidence.policies import validate_fingerprint

REQ_FINGERPRINT = "sha256:" + "1" * 64
CTX_FINGERPRINT = "sha256:" + "2" * 64
SOURCE_A_FINGERPRINT = "sha256:" + "3" * 64
SOURCE_B_FINGERPRINT = "sha256:" + "4" * 64
MODULE_A_FINGERPRINT = "sha256:" + "5" * 64
MODULE_B_FINGERPRINT = "sha256:" + "6" * 64


def test_fingerprint_is_stable_for_dict_key_ordering() -> None:
    first = fingerprint_payload(
        {
            "metrics": {"fallback_rate": 0.0, "coverage": 1.0},
            "asset": "eval-run-1",
        }
    )
    second = fingerprint_payload(
        {
            "asset": "eval-run-1",
            "metrics": {"coverage": 1.0, "fallback_rate": 0.0},
        }
    )

    assert first == second
    assert first.startswith("sha256:")
    assert len(first.removeprefix("sha256:")) == 64
    assert re.fullmatch(r"sha256:[0-9a-f]{64}", first)


def test_fingerprint_changes_when_payload_changes() -> None:
    passed = fingerprint_payload({"gate": "rag-release", "status": "passed"})
    failed = fingerprint_payload({"gate": "rag-release", "status": "failed"})

    assert passed != failed


def test_fingerprint_does_not_embed_raw_payload_text() -> None:
    sensitive_marker = "private-context-bundle"
    fingerprint = fingerprint_payload({"source": sensitive_marker})

    assert sensitive_marker not in fingerprint


def test_fingerprint_rejects_non_json_payload() -> None:
    with pytest.raises(ValueError, match="JSON-compatible"):
        fingerprint_payload(cast(JsonValue, {"unsupported": {object()}}))


def test_provenance_envelope_fingerprint_is_order_stable() -> None:
    first = fingerprint_provenance_envelope(
        surface="orchestration",
        request_fingerprint=REQ_FINGERPRINT,
        context_fingerprint=CTX_FINGERPRINT,
        source_fingerprints=(SOURCE_B_FINGERPRINT, SOURCE_A_FINGERPRINT),
        policy_version="semantic-cache-cost-o1-v1",
        model_key="model:gpt-family",
        user_tier="internal",
        transparency_notice_id="notice:internal",
        prompt_module_fingerprints=(MODULE_B_FINGERPRINT, MODULE_A_FINGERPRINT),
    )
    second = fingerprint_provenance_envelope(
        surface="orchestration",
        request_fingerprint=REQ_FINGERPRINT,
        context_fingerprint=CTX_FINGERPRINT,
        source_fingerprints=(SOURCE_A_FINGERPRINT, SOURCE_B_FINGERPRINT),
        policy_version="semantic-cache-cost-o1-v1",
        model_key="model:gpt-family",
        user_tier="internal",
        transparency_notice_id="notice:internal",
        prompt_module_fingerprints=(MODULE_A_FINGERPRINT, MODULE_B_FINGERPRINT),
    )

    assert first == second
    assert re.fullmatch(r"sha256:[0-9a-f]{64}", first)


def test_provenance_envelope_fingerprint_omits_raw_payloads() -> None:
    raw_marker = "private prompt text"
    fingerprint = fingerprint_provenance_envelope(
        surface="orchestration",
        request_fingerprint=REQ_FINGERPRINT,
        context_fingerprint=None,
        source_fingerprints=(SOURCE_A_FINGERPRINT,),
        policy_version="semantic-cache-cost-o1-v1",
        model_key="model:gpt-family",
        user_tier=None,
        transparency_notice_id="notice:internal",
    )

    assert raw_marker not in fingerprint


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"request_fingerprint": "private prompt text"}, "fingerprint"),
        ({"context_fingerprint": "file:///tmp/context.txt"}, "fingerprint"),
        ({"source_fingerprints": ("not-a-sha",)}, "fingerprint"),
        ({"prompt_module_fingerprints": ("sha256:abc",)}, "fingerprint"),
        ({"model_key": "raw_prompt"}, "unsafe metadata"),
        ({"transparency_notice_id": "file:///tmp/notice"}, "unsupported characters"),
        ({"user_tier": "billing-account"}, "unsafe metadata"),
    ],
)
def test_provenance_envelope_fails_closed_for_raw_or_malformed_inputs(
    kwargs: dict[str, object],
    match: str,
) -> None:
    payload: dict[str, object] = {
        "surface": "orchestration",
        "request_fingerprint": REQ_FINGERPRINT,
        "context_fingerprint": CTX_FINGERPRINT,
        "source_fingerprints": (SOURCE_A_FINGERPRINT,),
        "policy_version": "semantic-cache-cost-o1-v1",
        "model_key": "model:gpt-family",
        "user_tier": "internal",
        "transparency_notice_id": "notice:internal",
        "prompt_module_fingerprints": (MODULE_A_FINGERPRINT,),
    }
    payload.update(kwargs)
    with pytest.raises(ValueError, match=match):
        fingerprint_provenance_envelope(
            surface=cast(str, payload["surface"]),
            request_fingerprint=cast(str, payload["request_fingerprint"]),
            context_fingerprint=cast(str | None, payload["context_fingerprint"]),
            source_fingerprints=cast(tuple[str, ...], payload["source_fingerprints"]),
            policy_version=cast(str, payload["policy_version"]),
            model_key=cast(str, payload["model_key"]),
            user_tier=cast(str | None, payload["user_tier"]),
            transparency_notice_id=cast(str, payload["transparency_notice_id"]),
            prompt_module_fingerprints=cast(
                tuple[str, ...],
                payload["prompt_module_fingerprints"],
            ),
        )


@pytest.mark.parametrize(
    "fingerprint",
    [
        "not-a-sha",
        "sha256:abc",
        "sha256:0123456789abcdeg0123456789abcdef0123456789abcdef0123456789abcdef",
    ],
)
def test_validate_fingerprint_fails_closed_for_malformed_values(
    fingerprint: str,
) -> None:
    with pytest.raises(ValueError):
        validate_fingerprint(fingerprint)
