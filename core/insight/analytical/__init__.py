"""Analytical philosophy helpers for verification and falsification.

RU: Детерминированные проверки верифицируемости и фальсифицируемости.
EN: Deterministic verification and falsification helpers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

_CITATION_RE = re.compile(r"\b(?:WHO|USDA|CDC)\b|\b(?i:study|research|guideline|source)\b")
_VAGUE_RE = re.compile(
    r"\b(?:may help|might work|could be|some people|it depends|varies by individual)\b",
    re.IGNORECASE,
)
_TESTABLE_RE = re.compile(
    r"\b(?:\d+\.?\d*|less than|greater than|between|if|when|within)\b", re.IGNORECASE
)


def extract_claims(text: str) -> list[str]:
    """Extract deterministic claim-like segments from an answer."""
    parts = re.split(r"(?<=[.!?])\s+|\n+", text.strip())
    return [part.strip(" -") for part in parts if len(part.strip()) >= 12]


class StatementKind(str, Enum):
    """Analytical vs synthetic classification."""

    ANALYTICAL = "analytical"
    SYNTHETIC = "synthetic"
    METAPHYSICAL = "metaphysical"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class VerificationReport:
    """Verification result for a full answer."""

    verification_rate: float
    verified_claims: list[str] = field(default_factory=list)
    unverified_claims: list[str] = field(default_factory=list)
    classifications: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class FalsificationReport:
    """Falsification result for a full answer."""

    falsifiability_rate: float
    falsifiable_claims: list[str] = field(default_factory=list)
    unfalsifiable_claims: list[str] = field(default_factory=list)


class AnalyticalSyntheticClassifier:
    """Classify statements into analytical, synthetic, or metaphysical buckets."""

    _ANALYTICAL_PATTERNS = (
        re.compile(r"\b(?:is defined as|means|definition of|refers to)\b", re.IGNORECASE),
        re.compile(
            r"\b(?:bmi|bmr|tdee)\b\s+(?:is|means)\s+(?:a|an|the)?\s*"
            r"(?:measurement|metric|index|estimate|calculation|formula)\b",
            re.IGNORECASE,
        ),
    )
    _SYNTHETIC_PATTERNS = (
        re.compile(r"\b(?:according to|research|study|guideline)\b|\b(?:WHO|USDA|CDC)\b"),
        re.compile(r"\b\d+\.?\d*\b", re.IGNORECASE),
        re.compile(r"\b(?:overweight|underweight|calories|protein|fiber|sleep)\b", re.IGNORECASE),
    )
    _METAPHYSICAL_PATTERNS = (
        re.compile(r"\b(?:best for everyone|always works|perfect|guaranteed)\b", re.IGNORECASE),
        re.compile(r"\b(?:secret solution|ultimate answer)\b", re.IGNORECASE),
    )

    def classify(self, statement: str) -> StatementKind:
        """Classify a statement with deterministic regex rules."""
        if any(pattern.search(statement) for pattern in self._METAPHYSICAL_PATTERNS):
            return StatementKind.METAPHYSICAL
        if any(pattern.search(statement) for pattern in self._SYNTHETIC_PATTERNS):
            return StatementKind.SYNTHETIC
        if any(pattern.search(statement) for pattern in self._ANALYTICAL_PATTERNS):
            return StatementKind.ANALYTICAL
        return StatementKind.UNKNOWN


class VerificationEnforcer:
    """Require that synthetic claims are supported by available evidence."""

    def __init__(self, classifier: AnalyticalSyntheticClassifier | None = None) -> None:
        self._classifier = classifier or AnalyticalSyntheticClassifier()

    def validate(self, text: str, *, citations: list[str] | None = None) -> VerificationReport:
        """Validate whether claims are backed by citations or are analytical."""
        citations = citations or []
        claims = extract_claims(text)
        verified_claims: list[str] = []
        unverified_claims: list[str] = []
        classifications = {kind.value: 0 for kind in StatementKind}

        for claim in claims:
            kind = self._classifier.classify(claim)
            classifications[kind.value] += 1
            if kind == StatementKind.ANALYTICAL:
                verified_claims.append(claim)
                continue
            if kind == StatementKind.SYNTHETIC and self._is_verified_synthetic(claim, citations):
                verified_claims.append(claim)
                continue
            if kind in {StatementKind.UNKNOWN, StatementKind.SYNTHETIC, StatementKind.METAPHYSICAL}:
                unverified_claims.append(claim)

        rate = len(verified_claims) / len(claims) if claims else 1.0
        return VerificationReport(
            verification_rate=round(rate, 4),
            verified_claims=verified_claims,
            unverified_claims=unverified_claims,
            classifications=classifications,
        )

    def _is_verified_synthetic(self, claim: str, citations: list[str]) -> bool:
        """Check for explicit evidence or supporting citations."""
        if _CITATION_RE.search(claim):
            return True
        if citations and any(citation.strip() for citation in citations):
            return True
        return False


class FalsificationChecker:
    """Apply Popper-style falsifiability scoring."""

    def validate(self, text: str) -> FalsificationReport:
        """Assess whether claims are testable rather than vague."""
        claims = extract_claims(text)
        falsifiable_claims: list[str] = []
        unfalsifiable_claims: list[str] = []

        for claim in claims:
            if self._is_falsifiable(claim):
                falsifiable_claims.append(claim)
            else:
                unfalsifiable_claims.append(claim)

        rate = len(falsifiable_claims) / len(claims) if claims else 1.0
        return FalsificationReport(
            falsifiability_rate=round(rate, 4),
            falsifiable_claims=falsifiable_claims,
            unfalsifiable_claims=unfalsifiable_claims,
        )

    def _is_falsifiable(self, claim: str) -> bool:
        """Return True for claims with concrete or testable conditions."""
        if _VAGUE_RE.search(claim):
            return False
        return _TESTABLE_RE.search(claim) is not None or _CITATION_RE.search(claim) is not None


__all__ = [
    "AnalyticalSyntheticClassifier",
    "FalsificationChecker",
    "FalsificationReport",
    "StatementKind",
    "VerificationEnforcer",
    "VerificationReport",
    "extract_claims",
]
