"""Deterministic LLM output validator (wellness-safe, falsifiable claims).

Pure logic: no network, no temperature, regex/rules only.
Used by coordinator to require rewrite when BLOCKER detected.

Codes:
- WELLNESS_MEDICAL_CLAIM_* — medical/diagnostic claims (wellness-only posture)
- WELLNESS_GUARANTEE — outcome guarantees (non-falsifiable)
- NON_FALSIFIABLE_VAGUE — vague unverifiable claims
- POTENTIAL_CONTRADICTION — contradiction markers
- FITCHEF_FOOD_MORALITY — food = moral worth framing
- FITCHEF_PUNITIVE_RECOVERY — punitive recovery language
- FITCHEF_COMPENSATION_LANGUAGE — compensatory food/exercise language
- FITCHEF_THERAPIST_DRIFT — therapist-like motive interpretation
- FITCHEF_MANIPULATIVE_REASSURANCE — manipulative certainty / emotional overclaim

Report.ok is False only when BLOCKER-level findings exist.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Tuple

# Aligned with tests/guards BLOCKER_PATTERNS (wellness language blocker guard)
_BLOCKER_PATTERNS: List[Tuple[str, re.Pattern[str]]] = [
    (
        "WELLNESS_MEDICAL_CLAIM_RU",
        re.compile(
            r"\b(лечит|вылечит|вылечим|исцелит|диагноз|диагностирую|диагностирует)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "WELLNESS_MEDICAL_CLAIM_EN",
        re.compile(
            r"\b(we\s+cure|we\s+diagnose|will\s+cure|will\s+diagnose"
            r"|cures?\s+your|cures?\s+the|diagnoses?\s+your|diagnoses?\s+the"
            r"|(?:this|it)\s+(?:cures?|diagnoses?))\b",
            re.IGNORECASE,
        ),
    ),
    (
        "WELLNESS_GUARANTEE",
        re.compile(
            r"\b(guaranteed?\s+to\s+cure|100%\s+guaranteed|will\s+definitely\s+cure"
            r"|guaranteed\s+results?|money[- ]back\s+guarantee\s+if\s+not\s+cured)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "NON_FALSIFIABLE_VAGUE",
        re.compile(
            r"\b(many\s+people\s+say\s+it\s+cures?|some\s+experts\s+say\s+it\s+cures?"
            r"|it\s+is\s+known\s+to\s+cure|proven\s+to\s+cure\s+everyone)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "POTENTIAL_CONTRADICTION",
        re.compile(
            r"\b(however\s*,\s*we\s+cure|but\s+we\s+also\s+diagnose)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "FITCHEF_FOOD_MORALITY",
        re.compile(
            r"\b(good|bad|clean|dirty)\s+(food|foods|meal|meals|eating|dessert|snack)\b"
            r"|\b(cheat\s+meal|cheat\s+day)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "FITCHEF_PUNITIVE_RECOVERY",
        re.compile(
            r"\b(punish\s+(yourself|the slip)|make\s+up\s+for\s+it|atone\s+for\s+it)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "FITCHEF_COMPENSATION_LANGUAGE",
        re.compile(
            r"\b(earn\s+it\s+back|burn\s+it\s+off|work\s+it\s+off|skip\s+the\s+next\s+meal)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "FITCHEF_THERAPIST_DRIFT",
        re.compile(
            r"\b(you\s+really\s+did\s+this\s+because|deep\s+down\s+you|your\s+inner\s+self)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "FITCHEF_MANIPULATIVE_REASSURANCE",
        re.compile(
            r"\b(i\s+know\s+exactly\s+how\s+you\s+feel|i\s+promise\s+everything\s+will\s+be\s+okay)\b",
            re.IGNORECASE,
        ),
    ),
]


@dataclass
class Finding:
    """Single validation finding."""

    code: str
    start: int
    end: int
    matched: str


@dataclass
class Report:
    """Validation report. ok=False only when BLOCKER-level findings exist."""

    ok: bool
    blockers: List[Finding] = field(default_factory=list)
    domain: str | None = None


def validate_llm_output(text: str, *, domain: str | None = None) -> Report:
    """Validate LLM output for wellness-safe, falsifiable claims.

    Deterministic: no network, no temperature, regex/rules only.
    Report.ok is False only when BLOCKER-level findings exist.

    Args:
        text: LLM output to validate.
        domain: Optional domain hint (e.g. 'nutrition', 'coaching'). Reserved for future use.

    Returns:
        Report with ok=False if any BLOCKER found, else ok=True.
    """
    blockers: List[Finding] = []
    for code, pattern in _BLOCKER_PATTERNS:
        for m in pattern.finditer(text):
            blockers.append(Finding(code=code, start=m.start(), end=m.end(), matched=m.group(0)))
    blockers.sort(key=lambda b: b.start)
    return Report(ok=len(blockers) == 0, blockers=blockers, domain=domain)
