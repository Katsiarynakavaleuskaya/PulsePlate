"""Sensitive-field minimization helpers for wellness and AI surfaces.

RU: Политики минимизации для health-adjacent и AI payloads.
EN: Minimization policies for health-adjacent and AI payloads.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Literal, TypedDict

from core.pii_redaction import redact_pii_from_text

PersistenceRule = Literal["redact_and_truncate", "hash_only", "drop"]


class Sha256Marker(TypedDict):
    """Deterministic hash marker persisted for hash-only fields."""

    sha256: str
    length: int


@dataclass(frozen=True)
class SensitiveFieldPolicy:
    """Policy for a sensitive field family."""

    field_name: str
    persistence_rule: PersistenceRule
    max_chars: int | None
    rationale: str


_SENSITIVE_FIELD_TAXONOMY: dict[str, SensitiveFieldPolicy] = {
    "query": SensitiveFieldPolicy(
        field_name="query",
        persistence_rule="redact_and_truncate",
        max_chars=512,
        rationale="Keep a minimized quality-improvement trace without long raw health-ish text.",
    ),
    "preview": SensitiveFieldPolicy(
        field_name="preview",
        persistence_rule="redact_and_truncate",
        max_chars=240,
        rationale="Limit source preview exposure in feedback and response metadata.",
    ),
    "llm_response": SensitiveFieldPolicy(
        field_name="llm_response",
        persistence_rule="redact_and_truncate",
        max_chars=4000,
        rationale="Persist only the minimized response needed for QA and dispute review.",
    ),
    "user_correction": SensitiveFieldPolicy(
        field_name="user_correction",
        persistence_rule="redact_and_truncate",
        max_chars=4000,
        rationale="Keep the correction signal while reducing raw sensitive content exposure.",
    ),
    "prompt": SensitiveFieldPolicy(
        field_name="prompt",
        persistence_rule="hash_only",
        max_chars=None,
        rationale="Audit the prompt path without persisting provider-ready raw text.",
    ),
    "health_profile": SensitiveFieldPolicy(
        field_name="health_profile",
        persistence_rule="hash_only",
        max_chars=None,
        rationale="Profile-like health inputs must not be copied into logs or audit trails.",
    ),
    "provider_trace": SensitiveFieldPolicy(
        field_name="provider_trace",
        persistence_rule="hash_only",
        max_chars=None,
        rationale="Provider traces may contain raw prompt or user-derived content.",
    ),
    "source_content": SensitiveFieldPolicy(
        field_name="source_content",
        persistence_rule="redact_and_truncate",
        max_chars=240,
        rationale="Limit chunk-content exposure while preserving a compact citation preview.",
    ),
}

_ALIAS_TO_CANONICAL: dict[str, str] = {
    "prompt_text": "prompt",
    "query_text": "query",
    "query_preview": "preview",
    "source_preview": "preview",
    "chunk_preview": "preview",
    "source_content": "source_content",
    "health_profile": "health_profile",
    "profile": "health_profile",
    "user_profile": "health_profile",
    "prompt": "prompt",
    "query": "query",
    "preview": "preview",
    "llm_response": "llm_response",
    "response": "llm_response",
    "user_correction": "user_correction",
    "provider_trace": "provider_trace",
    "content": "source_content",
}


def get_sensitive_field_taxonomy() -> dict[str, SensitiveFieldPolicy]:
    """Return the canonical sensitive-field policy map."""

    return dict(_SENSITIVE_FIELD_TAXONOMY)


def _canonical_field_name(field_name: str) -> str:
    """Normalize variants to a canonical sensitive-field family."""

    lowered = field_name.strip().lower()
    for alias, canonical in _ALIAS_TO_CANONICAL.items():
        if lowered == alias or lowered.endswith(f"_{alias}") or alias in lowered:
            return canonical
    return lowered


def _sha256_marker(value: str) -> Sha256Marker:
    """Return deterministic hash marker for hash-only persistence."""

    return {
        "sha256": hashlib.sha256(value.encode("utf-8")).hexdigest(),
        "length": len(value),
    }


def minimize_free_text(value: str | None, *, field_name: str) -> str | None:
    """Minimize a free-form string according to the field taxonomy."""

    if value is None:
        return None

    canonical = _canonical_field_name(field_name)
    policy = _SENSITIVE_FIELD_TAXONOMY.get(canonical)
    if policy is None:
        return value

    if policy.persistence_rule == "drop":
        return None

    if policy.persistence_rule == "hash_only":
        return _sha256_marker(value)["sha256"]

    redacted = redact_pii_from_text(value) or ""
    if policy.max_chars is None or len(redacted) <= policy.max_chars:
        return redacted
    return redacted[: policy.max_chars]


def sanitize_chunk_preview(value: str | None) -> str | None:
    """Return a minimized preview string for chunk previews."""

    return minimize_free_text(value, field_name="preview")


def sanitize_audit_string(field_name: str, value: str) -> Sha256Marker | str | None:
    """Return the audit-safe representation for a sensitive string field."""

    canonical = _canonical_field_name(field_name)
    policy = _SENSITIVE_FIELD_TAXONOMY.get(canonical)
    if policy is None:
        return value
    if policy.persistence_rule == "drop":
        return None
    # Audit envelopes keep deterministic markers only, never minimized free text.
    return _sha256_marker(value)
