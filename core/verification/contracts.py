"""Verification registry contracts.

RU: Канонические internal-only контракты для verification artifact/bundle.
EN: Canonical internal-only contracts for verification artifact/bundle.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

VerificationStatus = Literal["pass", "warn", "fail"]


@dataclass(frozen=True)
class VerificationArtifact:
    """Deterministic verification artifact emitted by one runtime verifier."""

    artifact_id: str
    verifier_id: str
    status: VerificationStatus
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
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
