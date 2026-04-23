"""Verification admission policies.

RU: Policy для internal verification admission invariant.
EN: Policy for the internal verification admission invariant.
"""

from __future__ import annotations

from dataclasses import dataclass

KNOWLEDGE_WRITE_SCOPE = "knowledge_write"
SEMANTIC_CACHE_SCOPE = "semantic_cache"
ACTION_EXECUTION_SCOPE = "action_execution"
KNOWLEDGE_WRITE_REQUIRED_RATE = 1.0


@dataclass(frozen=True)
class VerificationPolicy:
    """Admission policy for a verification bundle scope."""

    scope: str
    allow_warn: bool = False
    required_rate: float = KNOWLEDGE_WRITE_REQUIRED_RATE


KNOWLEDGE_WRITE_POLICY = VerificationPolicy(
    scope=KNOWLEDGE_WRITE_SCOPE,
    allow_warn=False,
    required_rate=KNOWLEDGE_WRITE_REQUIRED_RATE,
)
