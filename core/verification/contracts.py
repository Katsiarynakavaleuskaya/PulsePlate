"""Verification registry contracts.

RU: Канонические internal-only контракты для verification artifact/bundle.
EN: Canonical internal-only contracts for verification artifact/bundle.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

VerificationStatus = Literal["pass", "warn", "fail"]


@dataclass(frozen=True)
class VerificationProvenance:
    """Internal-only provenance labels for a verification admission decision."""

    input_digest: str | None = None
    prompt_digest: str | None = None
    context_item_digests: tuple[str, ...] = field(default_factory=tuple)
    answer_digest: str | None = None
    prompt_char_count: int | None = None
    prompt_trimmed: bool | None = None
    verification_hops: int = 0
    verification_calls: int = 0


@dataclass(frozen=True)
class VerificationArtifact:
    """Deterministic verification artifact emitted by one runtime verifier."""

    artifact_id: str
    verifier_id: str
    status: VerificationStatus
    checked_at: datetime | None = field(default=None, compare=False)
    scope: str = "knowledge_write"
    evidence_refs: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()
    failure_reason: str | None = None


@dataclass(frozen=True)
class VerificationBundle:
    """Canonical bundle used for internal admission decisions."""

    artifacts: tuple[VerificationArtifact, ...]
    overall_status: VerificationStatus
    admission_allowed: bool
    reason_codes: tuple[str, ...] = field(default_factory=tuple)
    provenance: VerificationProvenance | None = field(default=None, compare=False)
