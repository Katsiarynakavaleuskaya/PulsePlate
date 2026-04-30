from __future__ import annotations

import re
from typing import cast

import pytest

from core.evidence.fingerprints import JsonValue, fingerprint_payload
from core.evidence.policies import validate_fingerprint


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
