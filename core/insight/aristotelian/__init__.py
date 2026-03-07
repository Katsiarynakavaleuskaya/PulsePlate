"""Aristotelian reasoning helpers for deterministic LLM validation.

RU: Детерминированные аристотелевы проверки для /insight.
EN: Deterministic Aristotelian checks for /insight.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

_RANGE_RE = re.compile(r"(\d+\.?\d*)\s*[-\u2013]\s*(\d+\.?\d*)")
_SECTION_RE = re.compile(r"(?im)^\s*(major premise|minor premise|conclusion)\s*:\s*(.+?)\s*$")
_NEGATION_RE = re.compile(r"\b(?:not|no|never|without|isn't|aren't|doesn't|don't)\b", re.IGNORECASE)


def _split_sentences(text: str) -> list[str]:
    """Split text into deterministic sentence-like chunks."""
    parts = re.split(r"(?<=[.!?])\s+|\n+", text.strip())
    return [part.strip(" -") for part in parts if part.strip()]


def _normalize_claim(text: str) -> str:
    """Normalize claim for cheap contradiction matching."""
    lowered = re.sub(
        r"\b(?:major premise|minor premise|conclusion)\b", "", text, flags=re.IGNORECASE
    )
    lowered = re.sub(r"[^a-z0-9\s]", " ", lowered.lower())
    lowered = re.sub(r"\b(?:all|some|no|not|therefore|thus|according|to|the|a|an)\b", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


@dataclass(frozen=True)
class SyllogismValidation:
    """Validation result for a syllogistic response."""

    valid: bool
    major_premise: str = ""
    minor_premise: str = ""
    conclusion: str = ""
    form: str = "unknown"


class CategoricalType(str, Enum):
    """Classical A/E/I/O categorical forms."""

    UNIVERSAL_AFFIRMATIVE = "A"
    UNIVERSAL_NEGATIVE = "E"
    PARTICULAR_AFFIRMATIVE = "I"
    PARTICULAR_NEGATIVE = "O"


@dataclass(frozen=True)
class CategoricalStatement:
    """Normalized categorical statement."""

    text: str
    statement_type: CategoricalType
    subject: str
    predicate: str


@dataclass(frozen=True)
class Contradiction:
    """Detected contradiction between two statements."""

    first: str
    second: str
    kind: str


class SyllogisticPromptBuilder:
    """Build Aristotelian prompts and validate response structure."""

    def build_prompt(
        self, query: str, *, domain: str = "wellness", context: str | None = None
    ) -> str:
        """Build an explicit premise-driven prompt."""
        context_block = f"Context:\n{context}\n\n" if context else ""
        return (
            "Answer as a concise Aristotelian syllogism.\n\n"
            f"{context_block}"
            f"Domain: {domain}\n"
            f"Question: {query}\n\n"
            "Required format:\n"
            "MAJOR PREMISE: [general rule]\n"
            "MINOR PREMISE: [specific case]\n"
            "CONCLUSION: [logical conclusion]\n"
            "Keep claims concrete, wellness-safe, and evidence-aware."
        )

    def validate_syllogism(self, response: str) -> SyllogismValidation:
        """Validate that major/minor/conclusion structure exists and is coherent."""
        labeled_sections = {
            match.group(1).lower(): match.group(2).strip()
            for match in _SECTION_RE.finditer(response)
        }
        if labeled_sections:
            major = labeled_sections.get("major premise", "")
            minor = labeled_sections.get("minor premise", "")
            conclusion = labeled_sections.get("conclusion", "")
        else:
            sentences = _split_sentences(response)
            major = sentences[0] if sentences else ""
            minor = sentences[1] if len(sentences) > 1 else ""
            conclusion = sentences[2] if len(sentences) > 2 else ""

        valid = all((major, minor, conclusion)) and self._conclusion_links_to_premises(
            major,
            minor,
            conclusion,
        )
        return SyllogismValidation(
            valid=valid,
            major_premise=major,
            minor_premise=minor,
            conclusion=conclusion,
            form="categorical" if valid else "invalid",
        )

    def _conclusion_links_to_premises(self, major: str, minor: str, conclusion: str) -> bool:
        """Cheap overlap check between premises and conclusion."""
        major_words = set(_normalize_claim(major).split())
        minor_words = set(_normalize_claim(minor).split())
        conclusion_words = set(_normalize_claim(conclusion).split())
        if not conclusion_words:
            return False
        shared = conclusion_words.intersection(major_words.union(minor_words))
        return len(shared) >= 2


class CategoricalValidator:
    """Extract A/E/I/O statements and detect classical contradictions."""

    def extract_statements(self, text: str) -> list[CategoricalStatement]:
        """Extract deterministic categorical statements."""
        statements: list[CategoricalStatement] = []
        for sentence in _split_sentences(text):
            lowered = sentence.lower()
            if lowered.startswith("all "):
                parsed = self._parse_statement(sentence, CategoricalType.UNIVERSAL_AFFIRMATIVE)
            elif lowered.startswith("no "):
                parsed = self._parse_statement(sentence, CategoricalType.UNIVERSAL_NEGATIVE)
            elif lowered.startswith("some ") and " not " in lowered:
                parsed = self._parse_statement(sentence, CategoricalType.PARTICULAR_NEGATIVE)
            elif lowered.startswith("some "):
                parsed = self._parse_statement(sentence, CategoricalType.PARTICULAR_AFFIRMATIVE)
            else:
                parsed = None
            if parsed is not None:
                statements.append(parsed)
        return statements

    def find_contradictions(self, statements: list[CategoricalStatement]) -> list[Contradiction]:
        """Find A vs O and E vs I contradictions with the same terms."""
        contradictions: list[Contradiction] = []
        for index, first in enumerate(statements):
            for second in statements[index + 1 :]:
                if self._same_terms(first, second) and self._is_contradictory_pair(first, second):
                    contradictions.append(
                        Contradiction(first=first.text, second=second.text, kind="categorical")
                    )
        return contradictions

    def _parse_statement(
        self,
        sentence: str,
        statement_type: CategoricalType,
    ) -> CategoricalStatement | None:
        """Parse a basic subject/predicate pair."""
        match = re.match(
            r"(?i)^(all|no|some)\s+(.+?)\s+(?:are|is|can be|should be)\s+(.+)$",
            sentence.strip(),
        )
        if match is None:
            return None
        predicate = match.group(3).strip().lower().rstrip(".!?")
        if statement_type == CategoricalType.PARTICULAR_NEGATIVE:
            predicate = re.sub(r"^not\s+", "", predicate)
        return CategoricalStatement(
            text=sentence.strip(),
            statement_type=statement_type,
            subject=match.group(2).strip().lower(),
            predicate=predicate,
        )

    def _same_terms(self, first: CategoricalStatement, second: CategoricalStatement) -> bool:
        """Check if statements talk about the same subject and predicate."""
        return first.subject == second.subject and first.predicate == second.predicate

    def _is_contradictory_pair(
        self,
        first: CategoricalStatement,
        second: CategoricalStatement,
    ) -> bool:
        contradictory_pairs = {
            frozenset(
                (
                    CategoricalType.UNIVERSAL_AFFIRMATIVE,
                    CategoricalType.PARTICULAR_NEGATIVE,
                )
            ),
            frozenset(
                (
                    CategoricalType.UNIVERSAL_NEGATIVE,
                    CategoricalType.PARTICULAR_AFFIRMATIVE,
                )
            ),
        }
        return frozenset((first.statement_type, second.statement_type)) in contradictory_pairs


class NonContradictionChecker:
    """Detect simple contradictions in final LLM output."""

    def __init__(self) -> None:
        self._categorical = CategoricalValidator()

    def check(self, text: str) -> list[Contradiction]:
        """Return deterministic contradiction findings."""
        contradictions: list[Contradiction] = []
        statements = self._categorical.extract_statements(text)
        contradictions.extend(self._categorical.find_contradictions(statements))
        contradictions.extend(self._find_negation_contradictions(text))
        contradictions.extend(self._find_numeric_range_contradictions(text))
        return contradictions

    def count(self, text: str) -> int:
        """Convenience helper for metadata."""
        return len(self.check(text))

    def _find_negation_contradictions(self, text: str) -> list[Contradiction]:
        """Detect A / not-A patterns using normalized sentence pairs."""
        contradictions: list[Contradiction] = []
        seen: dict[str, list[tuple[str, bool]]] = {}
        for sentence in _split_sentences(text):
            normalized = _normalize_claim(sentence)
            if not normalized:
                continue
            is_negative = _NEGATION_RE.search(sentence) is not None
            seen.setdefault(normalized, []).append((sentence, is_negative))

        for items in seen.values():
            positives = [sentence for sentence, negative in items if not negative]
            negatives = [sentence for sentence, negative in items if negative]
            for positive in positives:
                for negative in negatives:
                    contradictions.append(
                        Contradiction(first=positive, second=negative, kind="negation")
                    )
        return contradictions

    def _find_numeric_range_contradictions(self, text: str) -> list[Contradiction]:
        """Detect non-overlapping numeric ranges in the same answer."""
        contradictions: list[Contradiction] = []
        ranges: list[tuple[str, tuple[float, float]]] = []
        for sentence in _split_sentences(text):
            for match in _RANGE_RE.finditer(sentence):
                low = float(match.group(1))
                high = float(match.group(2))
                if low < high:
                    ranges.append((sentence, (low, high)))

        for index, (first_sentence, first_range) in enumerate(ranges):
            for second_sentence, second_range in ranges[index + 1 :]:
                if first_range[1] < second_range[0] or second_range[1] < first_range[0]:
                    contradictions.append(
                        Contradiction(
                            first=first_sentence,
                            second=second_sentence,
                            kind="numeric_range",
                        )
                    )
        return contradictions


__all__ = [
    "CategoricalStatement",
    "CategoricalType",
    "CategoricalValidator",
    "Contradiction",
    "NonContradictionChecker",
    "SyllogismValidation",
    "SyllogisticPromptBuilder",
]
