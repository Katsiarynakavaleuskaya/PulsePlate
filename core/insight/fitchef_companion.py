"""FitChef mascot coaching helpers.

RU: Детерминированные helper-функции для текстового coaching FitChef.
EN: Deterministic helper functions for text-only FitChef coaching.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from core.insight.philosophy_validator import validate_llm_output

_MAX_MESSAGE_LENGTH = 1200
_ACTION_ITEM_LIMIT = 3
_MIN_ACTION_ITEM_LENGTH = 8
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_BULLET_LINE_RE = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s*(.+?)\s*$")
_DEFAULT_ACTION_KEYWORDS = ("try", "start", "choose", "add")
_WEEKLY_REFLECTION_ACTION_KEYWORDS = ("keep", "plan", "notice", *_DEFAULT_ACTION_KEYWORDS)


@dataclass(frozen=True)
class FitChefCoachingDraft:
    """Prepared coaching response.

    RU: Нормализованный результат coaching после safety-проверок.
    EN: Normalized coaching result after safety validation.
    """

    message: str
    action_items: list[str]
    warnings: list[str]


FitChefMascotDraft = FitChefCoachingDraft


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


def build_weekly_reflection_prompt(summary: str, goal: str | None, rag_context: str) -> str:
    """Build the FitChef weekly reflection prompt."""

    goal_line = f"Current goal: {goal}" if goal else "Current goal: not provided"
    system_prompt = """You are FitChef, a friendly mascot-style wellness coach for PulsePlate.

Goals:
- Help the user reflect on the week in a supportive, non-judgmental way.
- Turn the reflection into 2-4 realistic next steps.
- Keep the coaching practical, wellness-only, and emotionally steady.

Hard boundaries:
- Do not diagnose, treat, or cure conditions.
- Do not present yourself as a therapist or clinician.
- Do not moralize about food or setbacks.
- Do not promise guaranteed outcomes.
"""

    if rag_context:
        return f"""{system_prompt}

Relevant context:
{rag_context}

Weekly summary:
{summary}

{goal_line}

Return a concise weekly reflection with practical next steps."""

    return f"""{system_prompt}

Weekly summary:
{summary}

{goal_line}

Return a concise weekly reflection with practical next steps."""


def prepare_mascot_draft(raw_text: str, *, query: str) -> FitChefCoachingDraft:
    """Normalize mascot output and rewrite blocker language deterministically."""

    return _prepare_fitchef_draft(
        raw_text=raw_text,
        fallback_builder=lambda warnings: _fallback_draft(query=query, warnings=warnings),
        action_keywords=_DEFAULT_ACTION_KEYWORDS,
    )


def prepare_weekly_reflection_draft(
    raw_text: str,
    *,
    summary: str,
    goal: str | None,
) -> FitChefCoachingDraft:
    """Normalize weekly reflection output and rewrite blocker language deterministically."""

    return _prepare_fitchef_draft(
        raw_text=raw_text,
        fallback_builder=lambda warnings: _weekly_reflection_fallback_draft(
            summary=summary,
            goal=goal,
            warnings=warnings,
        ),
        action_keywords=_WEEKLY_REFLECTION_ACTION_KEYWORDS,
    )


def _prepare_fitchef_draft(
    *,
    raw_text: str,
    fallback_builder: Callable[[list[str]], FitChefCoachingDraft],
    action_keywords: tuple[str, ...],
) -> FitChefCoachingDraft:
    """Normalize FitChef coaching output and rewrite blocker language deterministically."""

    normalized_lines = "\n".join(
        " ".join(line.split()) for line in raw_text.splitlines() if line.strip()
    ).strip()
    normalized_message = " ".join(raw_text.split()).strip()
    trimmed = normalized_message[:_MAX_MESSAGE_LENGTH].strip()
    report = validate_llm_output(trimmed, domain="fitchef_mascot")
    warnings: list[str] = []

    if not trimmed:
        warnings.append("empty_provider_response")
        return fallback_builder(warnings)

    if not report.ok:
        warnings.append("wellness_language_rewritten")
        return fallback_builder(warnings)

    bounded_action_source = (normalized_lines or raw_text)[:_MAX_MESSAGE_LENGTH]
    action_items = _extract_action_items(bounded_action_source, action_keywords=action_keywords)
    if not action_items:
        fallback = fallback_builder(warnings.copy())
        action_items = fallback.action_items
    return FitChefCoachingDraft(message=trimmed, action_items=action_items, warnings=warnings)


def _fallback_draft(*, query: str, warnings: list[str]) -> FitChefCoachingDraft:
    """Return a deterministic safe fallback when provider output is blocked."""

    safe_message = (
        "FitChef is here with wellness-only guidance. Let's reset with one small step, "
        "keep the tone kind, and focus on the next meal or habit you can control."
    )
    return FitChefCoachingDraft(
        message=safe_message,
        action_items=_default_action_items(query),
        warnings=warnings,
    )


def _weekly_reflection_fallback_draft(
    *,
    summary: str,
    goal: str | None,
    warnings: list[str],
) -> FitChefCoachingDraft:
    """Return a deterministic safe fallback for weekly reflection."""

    safe_message = (
        "FitChef is here to help you review the week with a steady, wellness-only lens. "
        "Let's keep what worked, notice one friction point, and pick a small reset for next week."
    )
    return FitChefCoachingDraft(
        message=safe_message,
        action_items=_weekly_reflection_action_items(summary, goal),
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


def _weekly_reflection_action_items(summary: str, goal: str | None) -> list[str]:
    """Return deterministic fallback actions for weekly reflection."""

    lowered_summary = summary.lower()
    if "late" in lowered_summary or "night" in lowered_summary:
        return [
            "Pick one evening meal template you can repeat this week.",
            "Set one small stopping cue before late-night snacking starts.",
            "Write one sentence about what made evenings harder this week.",
        ]
    if goal:
        return [
            f"Choose one action this week that clearly supports your goal: {goal}.",
            "Keep one meal habit that already worked at least once this week.",
            "Plan one small recovery step for the moment your routine slips.",
        ]
    return [
        "Keep one meal habit that already worked this week.",
        "Choose one friction point to simplify before next week starts.",
        "Plan one small reset you can do at the next meal, not next Monday.",
    ]


def _extract_action_items(text: str, *, action_keywords: tuple[str, ...]) -> list[str]:
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
        if not any(keyword in candidate.lower() for keyword in action_keywords):
            continue
        items.append(candidate)
        if len(items) >= _ACTION_ITEM_LIMIT:
            break
    return items[:_ACTION_ITEM_LIMIT]
