"""Post-analytical philosophy helpers.

RU: Прагматические и герменевтические оптимизаторы глубины.
EN: Pragmatic and hermeneutic depth helpers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from core.insight.linguistic import LanguageGameType, SpeechActType


@dataclass(frozen=True)
class PragmaticAssessment:
    """Utility assessment for a generated answer."""

    practically_useful: bool
    actionable: bool
    contextually_relevant: bool
    usefulness_score: float


class PragmaticValidator:
    """Stop refinement when answer is actionable enough for the user."""

    _ACTIONABLE_RE = re.compile(
        r"\b(?:first|then|next|finally|try|use|aim for|start with|you can|consider)\b",
        re.IGNORECASE,
    )

    def assess(
        self, text: str, *, query: str, language_game: LanguageGameType
    ) -> PragmaticAssessment:
        """Assess practical usefulness with deterministic heuristics."""
        actionable = self._ACTIONABLE_RE.search(text) is not None
        query_terms = {term for term in re.findall(r"[a-zA-Z]{4,}", query.lower())}
        answer_terms = set(re.findall(r"[a-zA-Z]{4,}", text.lower()))
        overlap = len(query_terms.intersection(answer_terms))
        contextually_relevant = overlap >= 1 or language_game == LanguageGameType.MEDICAL
        score = 0.0
        if actionable:
            score += 0.5
        if contextually_relevant:
            score += 0.4
        if len(text.split()) <= 120:
            score += 0.1
        score = round(min(score, 1.0), 4)
        return PragmaticAssessment(
            practically_useful=score >= 0.7,
            actionable=actionable,
            contextually_relevant=contextually_relevant,
            usefulness_score=score,
        )


class HermeneuticDepthOptimizer:
    """Choose depth from speech act, language game, and text complexity."""

    def determine_depth(
        self,
        query: str,
        *,
        speech_act: SpeechActType,
        language_game: LanguageGameType,
    ) -> int:
        """Determine a bounded depth in [1, 3]."""
        base_depth = {
            SpeechActType.COMMAND: 1,
            SpeechActType.EXPRESSION: 1,
            SpeechActType.REQUEST: 2,
            SpeechActType.QUESTION: 2,
            SpeechActType.UNKNOWN: 2,
        }[speech_act]
        if language_game == LanguageGameType.MEDICAL:
            return 1
        if language_game == LanguageGameType.NUTRITION:
            base_depth += 1
        if len(query.split()) > 18:
            base_depth += 1
        if len(query.split()) < 6:
            base_depth -= 1
        return max(1, min(base_depth, 3))


__all__ = [
    "HermeneuticDepthOptimizer",
    "PragmaticAssessment",
    "PragmaticValidator",
]
