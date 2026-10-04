"""Deterministic LLM output validator (wellness-safe, falsifiable claims).

Pure logic: no network, no temperature, regex/rules only.
Used by coordinator to require rewrite when BLOCKER detected.

Codes:
- WELLNESS_MEDICAL_CLAIM_RU/EN/ES — bounded medical/diagnostic claim phrases
  (wellness-only posture; language-wide recognition is not claimed)
- WELLNESS_GUARANTEE — outcome guarantees (non-falsifiable)
- NON_FALSIFIABLE_VAGUE — vague unverifiable claims
- POTENTIAL_CONTRADICTION — contradiction markers
- FITCHEF_FOOD_MORALITY — food = moral worth framing
- FITCHEF_PUNITIVE_RECOVERY — punitive recovery language
- FITCHEF_COMPENSATION_LANGUAGE — compensatory food/exercise language
- FITCHEF_THERAPIST_DRIFT — therapist-like motive interpretation
- FITCHEF_MANIPULATIVE_REASSURANCE — manipulative certainty / emotional overclaim

Report.ok is False only when BLOCKER-level findings exist.
Locale rules recognize finite reviewed constructions, not general language safety.
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
            r"|(?:this|it)\s+(?:cures?|diagnoses?)"
            r"|(?:need|needs|require|requires)\s+(?:medical\s+)?treatment)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "WELLNESS_MEDICAL_CLAIM_ES",
        re.compile(
            r"\b(esto\s+cura|te\s+diagnostico\s+con)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "WELLNESS_GUARANTEE",
        re.compile(
            r"\b(guaranteed?\s+to\s+cure|100%\s+guaranteed|will\s+definitely\s+cure"
            r"|guaranteed\s+results?|money[- ]back\s+guarantee\s+if\s+not\s+cured"
            r"|гарантирую\s+результаты|te\s+garantizo\s+resultados)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "NON_FALSIFIABLE_VAGUE",
        re.compile(
            r"\b(many\s+people\s+say\s+it\s+cures?|some\s+experts\s+say\s+it\s+cures?"
            r"|it\s+is\s+known\s+to\s+cure|proven\s+to\s+cure\s+everyone"
            r"|многие\s+говорят,?\s+что\s+это\s+лечит"
            r"|algunos\s+expertos\s+dicen\s+que\s+esto\s+cura)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "POTENTIAL_CONTRADICTION",
        re.compile(
            r"\b(however\s*,\s*we\s+cure|but\s+we\s+also\s+diagnose"
            r"|однако,?\s+мы\s+лечим|sin\s+embargo,?\s+curamos)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "FITCHEF_FOOD_MORALITY",
        re.compile(
            r"\b(good|bad|clean|dirty)\s+(food|foods|meal|meals|eating|dessert|desserts|snack|snacks)\b"
            r"|\b(cheat\s+meal|cheat\s+day)\b"
            r"|\bплохая\s+еда\b"
            r"|\bcomida\s+mala\b",
            re.IGNORECASE,
        ),
    ),
    (
        "FITCHEF_PUNITIVE_RECOVERY",
        re.compile(
            r"\b(punish\s+(yourself|the slip)|make\s+up\s+for\s+it|atone\s+for\s+it)\b"
            r"|\bнакажи\s+себя\b"
            r"|\bcast[íi]gate\b",
            re.IGNORECASE,
        ),
    ),
    (
        "FITCHEF_COMPENSATION_LANGUAGE",
        re.compile(
            r"\b(earn\s+it\s+back|burn\s+it\s+off|work\s+it\s+off|skip\s+the\s+next\s+meal)\b"
            r"|\bпропусти\s+следующий\s+при[её]м\s+пищи\b"
            r"|\bs[áa]ltate\s+la\s+pr[óo]xima\s+comida\b",
            re.IGNORECASE,
        ),
    ),
    (
        "FITCHEF_THERAPIST_DRIFT",
        re.compile(
            r"\b(you\s+really\s+did\s+this\s+because|deep\s+down\s+you|your\s+inner\s+self)\b"
            r"|\bты\s+на\s+самом\s+деле\s+сделал\s+это\s+потому,\s+что\b"
            r"|\ben\s+el\s+fondo\s+hiciste\s+esto\s+porque\b",
            re.IGNORECASE,
        ),
    ),
    (
        "FITCHEF_MANIPULATIVE_REASSURANCE",
        re.compile(
            r"\b(i\s+know\s+exactly\s+how\s+you\s+feel|i\s+promise\s+everything\s+will\s+be\s+okay)\b"
            r"|\bя\s+точно\s+знаю,\s+что\s+ты\s+чувствуешь\b"
            r"|\bs[ée]\s+exactamente\s+c[óo]mo\s+te\s+sientes\b",
            re.IGNORECASE,
        ),
    ),
]

# Only the reviewed code/construction pairs exempt their own occurrence.
# Sentence anchoring rejects stacked negation and leaves later positives visible.
_RU_COMPENSATION_DENIAL_PREFIX = re.compile(r"(?:\A|[.!?])\s*не\s+$", re.IGNORECASE)
_REVIEWED_NEGATION_PREFIXES: dict[tuple[str, str], re.Pattern[str]] = {
    (
        "FITCHEF_COMPENSATION_LANGUAGE",
        "пропусти следующий прием пищи",
    ): _RU_COMPENSATION_DENIAL_PREFIX,
    (
        "FITCHEF_COMPENSATION_LANGUAGE",
        "пропусти следующий приём пищи",
    ): _RU_COMPENSATION_DENIAL_PREFIX,
    ("FITCHEF_FOOD_MORALITY", "плохая еда"): re.compile(
        r"(?:\A|[.!?])\s*(?:это\s+)?не\s+$", re.IGNORECASE
    ),
    ("FITCHEF_FOOD_MORALITY", "comida mala"): re.compile(
        r"(?:\A|[.!?])\s*no\s+es\s+$", re.IGNORECASE
    ),
    ("WELLNESS_MEDICAL_CLAIM_ES", "te diagnostico con"): re.compile(
        r"(?:\A|[.!?])\s*no\s+$", re.IGNORECASE
    ),
    ("WELLNESS_GUARANTEE", "гарантирую результаты"): re.compile(
        r"(?:\A|[.!?])\s*(?:я\s+)?не\s+$", re.IGNORECASE
    ),
    ("WELLNESS_GUARANTEE", "te garantizo resultados"): re.compile(
        r"(?:\A|[.!?])\s*no\s+$", re.IGNORECASE
    ),
}


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
            negation_prefix = _REVIEWED_NEGATION_PREFIXES.get(
                (code, " ".join(m.group(0).casefold().split()))
            )
            if negation_prefix is not None and negation_prefix.search(text[: m.start()]):
                continue
            blockers.append(Finding(code=code, start=m.start(), end=m.end(), matched=m.group(0)))
    blockers.sort(key=lambda b: b.start)
    return Report(ok=len(blockers) == 0, blockers=blockers, domain=domain)
