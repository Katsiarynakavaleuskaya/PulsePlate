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
    input_sha: str | None = None
    prompt_sha: str | None = None
    context_item_shas: tuple[str, ...] = field(default_factory=tuple)
    answer_sha: str | None = None
    prompt_char_count: int | None = None
    prompt_trimmed: bool | None = None
    prompt_original_char_count: int | None = None
    prompt_final_char_count: int | None = None
    prompt_trim_limit: int | None = None
    prompt_trimmed_char_count: int | None = None
    verification_hops: int = 0
    verification_calls: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "input_sha", self.input_digest)
        object.__setattr__(self, "prompt_sha", self.prompt_digest)
        object.__setattr__(self, "context_item_shas", self.context_item_digests)
        object.__setattr__(self, "answer_sha", self.answer_digest)


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
