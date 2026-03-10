"""FitChef mascot coaching helpers.

RU: Детерминированные helper-функции для текстового mascot coaching.
EN: Deterministic helper functions for text-only mascot coaching.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from core.insight.philosophy_validator import validate_llm_output

_MAX_MESSAGE_LENGTH = 1200
_ACTION_ITEM_LIMIT = 3
_MIN_ACTION_ITEM_LENGTH = 8
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_BULLET_LINE_RE = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s*(.+?)\s*$")


@dataclass(frozen=True)
class FitChefMascotDraft:
    """Prepared mascot response.

    RU: Нормализованный результат mascot coaching после safety-проверок.
    EN: Normalized mascot coaching result after safety validation.
    """

    message: str
    action_items: list[str]
    warnings: list[str]


def build_mascot_prompt(query: str, rag_context: str) -> str:
    """Build the FitChef mascot prompt."""

    system_prompt = """You are FitChef, a friendly mascot-style wellness coach for PulsePlate.

Goals:
- Give supportive, practical nutrition coaching in a warm mascot voice.
- Stay concrete and action-oriented.
- Keep coaching wellness-only and non-clinical.
- Suggest 2-3 small next steps when possible.

Hard boundaries:
- Do not diagnose, treat, or cure conditions.
- Do not present yourself as a therapist or clinician.
- Do not promise guaranteed outcomes.
- If the user sounds distressed, respond supportively but keep the guidance wellness-only.
"""

    if rag_context:
        return f"""{system_prompt}

Relevant context:
{rag_context}

User request:
{query}

Return a concise mascot-style coaching response with practical next steps."""

    return f"""{system_prompt}

User request:
{query}

Return a concise mascot-style coaching response with practical next steps."""


def prepare_mascot_draft(raw_text: str, *, query: str) -> FitChefMascotDraft:
    """Normalize mascot output and rewrite blocker language deterministically."""

    normalized_lines = "\n".join(
        " ".join(line.split()) for line in raw_text.splitlines() if line.strip()
    ).strip()
    normalized_message = " ".join(raw_text.split()).strip()
    trimmed = normalized_message[:_MAX_MESSAGE_LENGTH].strip()
    report = validate_llm_output(trimmed, domain="fitchef_mascot")
    warnings: list[str] = []

    if not trimmed:
        warnings.append("empty_provider_response")
        return _fallback_draft(query=query, warnings=warnings)

    if not report.ok:
        warnings.append("wellness_language_rewritten")
        return _fallback_draft(query=query, warnings=warnings)

    bounded_action_source = (normalized_lines or raw_text)[:_MAX_MESSAGE_LENGTH]
    action_items = _extract_action_items(bounded_action_source)
    if not action_items:
        action_items = _default_action_items(query)
    return FitChefMascotDraft(message=trimmed, action_items=action_items, warnings=warnings)


def _fallback_draft(*, query: str, warnings: list[str]) -> FitChefMascotDraft:
    """Return a deterministic safe fallback when provider output is blocked."""

    safe_message = (
        "FitChef is here with wellness-only guidance. Let's reset with one small step, "
        "keep the tone kind, and focus on the next meal or habit you can control."
    )
    return FitChefMascotDraft(
        message=safe_message,
        action_items=_default_action_items(query),
        warnings=warnings,
    )


def _default_action_items(query: str) -> list[str]:
    """Return deterministic fallback actions."""

    lowered = query.lower()
    if "snack" in lowered or "craving" in lowered:
        return [
            "Plan one balanced snack before the next craving window.",
            "Add water or tea before deciding on a second snack.",
            "Write one trigger you noticed today.",
        ]
    return [
        "Choose one balanced next meal you can realistically make today.",
        "Add one protein or fiber anchor to that meal.",
        "Notice one thought that makes nutrition feel harder and answer it kindly.",
    ]


def _extract_action_items(text: str) -> list[str]:
    """Extract up to three concrete action items from model output."""

    items: list[str] = []
    for line in text.splitlines():
        match = _BULLET_LINE_RE.match(line)
        if not match:
            continue
        candidate = match.group(1).strip()
        if len(candidate) < _MIN_ACTION_ITEM_LENGTH:
            continue
        items.append(candidate)
        if len(items) >= _ACTION_ITEM_LIMIT:
            return items

    for sentence in _SENTENCE_SPLIT_RE.split(text):
        candidate = sentence.strip(" -•\t")
        if len(candidate) < _MIN_ACTION_ITEM_LENGTH:
            continue
        if not any(keyword in candidate.lower() for keyword in ("try", "start", "choose", "add")):
            continue
        items.append(candidate)
        if len(items) >= _ACTION_ITEM_LIMIT:
            break
    return items[:_ACTION_ITEM_LIMIT]
