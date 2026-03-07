"""Linguistic philosophy helpers for cheap-path routing.

RU: Классификаторы речевых актов и language games.
EN: Speech-act and language-game classifiers.
"""

from __future__ import annotations

import re
from enum import Enum


class SpeechActType(str, Enum):
    """Supported speech acts for routing."""

    QUESTION = "question"
    COMMAND = "command"
    REQUEST = "request"
    EXPRESSION = "expression"
    UNKNOWN = "unknown"


class LanguageGameType(str, Enum):
    """Supported language-game buckets."""

    MEDICAL = "medical"
    FITNESS = "fitness"
    NUTRITION = "nutrition"
    GENERAL = "general"


class SpeechActClassifier:
    """Classify speech acts using cheap regex heuristics."""

    _QUESTION_RE = re.compile(
        r"^\s*(?:what|how|why|when|where|is|are|can|does|do)\b|\?\s*$", re.IGNORECASE
    )
    _COMMAND_RE = re.compile(
        r"^\s*(?:calculate|show|give|list|summarize|compare|estimate)\b", re.IGNORECASE
    )
    _REQUEST_RE = re.compile(r"\b(?:please|can you|could you|would you)\b", re.IGNORECASE)
    _EXPRESSION_RE = re.compile(
        r"\b(?:i feel|i am worried|i'm worried|i need help|i am struggling|i'm struggling)\b",
        re.IGNORECASE,
    )

    def classify(self, query: str) -> SpeechActType:
        """Return the most likely speech act."""
        if self._EXPRESSION_RE.search(query):
            return SpeechActType.EXPRESSION
        if self._COMMAND_RE.search(query):
            return SpeechActType.COMMAND
        if self._REQUEST_RE.search(query):
            return SpeechActType.REQUEST
        if self._QUESTION_RE.search(query):
            return SpeechActType.QUESTION
        return SpeechActType.UNKNOWN


class LanguageGameIdentifier:
    """Bucket a query into a domain-specific language game."""

    _MEDICAL = ("symptom", "diagnosis", "disease", "treatment", "medication", "doctor", "pain")
    _FITNESS = ("workout", "exercise", "training", "muscle", "strength", "cardio", "steps")
    _NUTRITION = ("calorie", "protein", "meal", "diet", "nutrient", "fiber", "bmi", "bmr", "tdee")

    def identify(self, query: str) -> LanguageGameType:
        """Identify the query's language game."""
        lowered = query.lower()
        if any(keyword in lowered for keyword in self._MEDICAL):
            return LanguageGameType.MEDICAL
        if any(keyword in lowered for keyword in self._FITNESS):
            return LanguageGameType.FITNESS
        if any(keyword in lowered for keyword in self._NUTRITION):
            return LanguageGameType.NUTRITION
        return LanguageGameType.GENERAL


class MeaningAsUseResolver:
    """Simplify noisy phrasing before retrieval and generation."""

    _POLITENESS_RE = re.compile(r"\b(?:please|can you|could you|would you|kindly)\b", re.IGNORECASE)
    _FILLER_RE = re.compile(r"\b(?:tell me|help me understand|i want to know)\b", re.IGNORECASE)

    def resolve(self, query: str) -> str:
        """Normalize whitespace and remove politeness filler."""
        simplified = self._POLITENESS_RE.sub(" ", query)
        simplified = self._FILLER_RE.sub(" ", simplified)
        simplified = re.sub(r"\s+", " ", simplified).strip(" ?")
        return simplified or query.strip()


__all__ = [
    "LanguageGameIdentifier",
    "LanguageGameType",
    "MeaningAsUseResolver",
    "SpeechActClassifier",
    "SpeechActType",
]
