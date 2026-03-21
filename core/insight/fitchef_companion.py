"""FitChef mascot coaching helpers.

RU: Детерминированные helper-функции для текстового coaching FitChef.
EN: Deterministic helper functions for text-only FitChef coaching.
"""

from __future__ import annotations

import json
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
_SLIP_SUPPORT_ACTION_KEYWORDS = ("pause", "restart", "return", "plan", *_DEFAULT_ACTION_KEYWORDS)
_DEFAULT_LIST_LIMIT = 3
_DISTORTION_LABEL_ALIASES: dict[str, str] = {
    "all_or_nothing_thinking": "all_or_nothing_thinking",
    "all or nothing thinking": "all_or_nothing_thinking",
    "black and white thinking": "all_or_nothing_thinking",
    "catastrophizing": "catastrophizing",
    "emotional_reasoning": "emotional_reasoning",
    "emotional reasoning": "emotional_reasoning",
    "should_statements": "should_statements",
    "should statements": "should_statements",
    "mental_filtering": "mental_filtering",
    "mental filtering": "mental_filtering",
}
_DEFAULT_DISTORTION_LABEL = "emotional_reasoning"


@dataclass(frozen=True)
class FitChefDistortionDraft:
    """Structured distortion-simulator draft.

    RU: Нормализованный structured draft для distortion simulator.
    EN: Normalized structured draft for the distortion simulator.
    """

    distortion_labels: list[str]
    why_it_matches: str
    evidence_for: list[str]
    evidence_against: list[str]
    balanced_reframe: str
    next_small_action: str
    warnings: list[str]


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
- Turn the reflection into 2-3 realistic next steps.
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

Return a concise weekly reflection with 2-3 short bullet next steps."""

    return f"""{system_prompt}

Weekly summary:
{summary}

{goal_line}

Return a concise weekly reflection with 2-3 short bullet next steps."""


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


def build_slip_support_prompt(event_text: str, goal: str | None, rag_context: str) -> str:
    """Build the FitChef slip-support prompt."""

    goal_line = f"Current goal: {goal}" if goal else "Current goal: not provided"
    system_prompt = """You are FitChef, a friendly mascot-style wellness coach for PulsePlate.

Goals:
- Help the user recover from a slip with calm, non-judgmental wellness coaching.
- Turn the moment into 2-3 concrete next steps.
- Keep the tone steady, practical, and recovery-oriented.

Hard boundaries:
- Do not diagnose, treat, or cure conditions.
- Do not present yourself as a therapist or clinician.
- Do not shame, blame, or moralize about food or setbacks.
- Do not promise guaranteed outcomes.
"""

    if rag_context:
        return f"""{system_prompt}

Relevant context:
{rag_context}

Slip event:
{event_text}

{goal_line}

Return a concise recovery-oriented response with 2-3 short bullet next steps."""

    return f"""{system_prompt}

Slip event:
{event_text}

{goal_line}

Return a concise recovery-oriented response with 2-3 short bullet next steps."""


def prepare_slip_support_draft(
    raw_text: str,
    *,
    event_text: str,
    goal: str | None,
) -> FitChefCoachingDraft:
    """Normalize slip-support output and rewrite blocker language deterministically."""

    return _prepare_fitchef_draft(
        raw_text=raw_text,
        fallback_builder=lambda warnings: _slip_support_fallback_draft(
            event_text=event_text,
            goal=goal,
            warnings=warnings,
        ),
        action_keywords=_SLIP_SUPPORT_ACTION_KEYWORDS,
    )


def build_distortion_simulator_prompt(
    situation: str,
    automatic_thought: str,
    emotion: str,
    goal: str | None,
    rag_context: str,
) -> str:
    """Build the structured distortion-simulator prompt."""

    goal_line = f"Goal: {goal}" if goal else "Goal: not provided"
    system_prompt = """You are FitChef, a wellness-only CBT coaching surface for PulsePlate.

Return only one JSON object with this exact shape:
{
  "distortion_labels": ["all_or_nothing_thinking"],
  "why_it_matches": "string",
  "evidence_for": ["string"],
  "evidence_against": ["string"],
  "balanced_reframe": "string",
  "next_small_action": "string"
}

Rules:
- Use only these distortion labels: all_or_nothing_thinking, catastrophizing, emotional_reasoning, should_statements, mental_filtering
- Keep the response wellness-only and non-clinical
- Do not diagnose, treat, or use therapist framing
- Keep evidence items concrete and short
- Keep next_small_action realistic and behavior-sized
"""

    if rag_context:
        return f"""{system_prompt}

Relevant CBT context:
{rag_context}

Situation: {situation}
Automatic thought: {automatic_thought}
Emotion: {emotion}
{goal_line}
""".strip()

    return f"""{system_prompt}

Situation: {situation}
Automatic thought: {automatic_thought}
Emotion: {emotion}
{goal_line}
""".strip()


def prepare_distortion_simulator_draft(
    raw_text: str,
    *,
    situation: str,
    automatic_thought: str,
    emotion: str,
    goal: str | None,
) -> FitChefDistortionDraft:
    """Normalize distortion-simulator provider output into a safe structured draft."""

    warnings: list[str] = []
    try:
        payload = _extract_json_payload(raw_text)
    except ValueError:
        warnings.append("structured_parse_fallback")
        return _fallback_distortion_draft(
            situation=situation,
            automatic_thought=automatic_thought,
            emotion=emotion,
            goal=goal,
            warnings=warnings,
        )

    labels = _normalize_distortion_labels(payload.get("distortion_labels"))
    why_it_matches = _normalize_structured_string(payload.get("why_it_matches"))
    evidence_for = _normalize_string_list(payload.get("evidence_for"))
    evidence_against = _normalize_string_list(payload.get("evidence_against"))
    balanced_reframe = _normalize_structured_string(payload.get("balanced_reframe"))
    next_small_action = _normalize_structured_string(payload.get("next_small_action"))

    if not why_it_matches:
        why_it_matches = _build_distortion_reason(
            labels=labels,
            automatic_thought=automatic_thought,
        )
    if not evidence_for:
        evidence_for = _fallback_evidence_for(emotion=emotion)
    if not evidence_against:
        evidence_against = _fallback_evidence_against(goal=goal)
    if not balanced_reframe:
        balanced_reframe = _fallback_balanced_reframe(
            automatic_thought=automatic_thought,
            goal=goal,
        )
    if not next_small_action:
        next_small_action = _fallback_next_small_action(goal=goal)

    if not _structured_texts_are_safe(
        why_it_matches,
        *evidence_for,
        *evidence_against,
        balanced_reframe,
        next_small_action,
    ):
        warnings.append("wellness_language_rewritten")
        return _fallback_distortion_draft(
            situation=situation,
            automatic_thought=automatic_thought,
            emotion=emotion,
            goal=goal,
            warnings=warnings,
        )

    return FitChefDistortionDraft(
        distortion_labels=labels,
        why_it_matches=why_it_matches,
        evidence_for=evidence_for,
        evidence_against=evidence_against,
        balanced_reframe=balanced_reframe,
        next_small_action=next_small_action,
        warnings=warnings,
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


def _slip_support_fallback_draft(
    *,
    event_text: str,
    goal: str | None,
    warnings: list[str],
) -> FitChefCoachingDraft:
    """Return a deterministic safe fallback for slip-support."""

    safe_message = (
        "FitChef is here to help you reset with a calm, wellness-only next step. "
        "A slip is a moment, not a verdict, so let's pause, restart, and pick one small recovery move."
    )
    return FitChefCoachingDraft(
        message=safe_message,
        action_items=_slip_support_action_items(event_text, goal),
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


def _slip_support_action_items(event_text: str, goal: str | None) -> list[str]:
    """Return deterministic fallback actions for slip-support."""

    lowered_event = event_text.lower()
    if "night" in lowered_event or "late" in lowered_event:
        return [
            "Pause before the next late-night snack and add water or tea first.",
            "Restart with one balanced meal at the next eating moment, not tomorrow.",
            "Plan one evening cue that helps you stop the spiral earlier.",
        ]
    if goal:
        return [
            f"Return to one next step that still supports your goal: {goal}.",
            "Pause the blame language and restart with the next meal or snack.",
            "Plan one friction-reducing recovery step before the next trigger window.",
        ]
    return [
        "Pause for one calm breath before choosing the next meal or snack.",
        "Restart with one balanced next step instead of trying to fix the whole day.",
        "Plan one small recovery action for the next trigger moment you expect.",
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


def _extract_json_payload(raw_message: str) -> dict[str, object]:
    """Extract the first JSON object from provider text, tolerating fenced output."""

    stripped = raw_message.strip()
    if stripped.startswith("```"):
        newline_index = stripped.find("\n")
        if newline_index != -1:
            stripped = stripped[newline_index + 1 :]
            if stripped.endswith("```"):
                stripped = stripped[:-3]
            stripped = stripped.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        loaded = json.loads(stripped)
        if isinstance(loaded, dict):
            return loaded
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or start >= end:
        raise ValueError("Provider response did not contain a JSON object.")
    loaded = json.loads(stripped[start : end + 1])
    if not isinstance(loaded, dict):
        raise ValueError("Provider response JSON must be an object.")
    return loaded


def _normalize_structured_string(raw_value: object) -> str:
    """Normalize a structured string field."""

    if not isinstance(raw_value, str):
        return ""
    return " ".join(raw_value.split())[:_MAX_MESSAGE_LENGTH].strip()


def _normalize_string_list(raw_value: object) -> list[str]:
    """Normalize a short list of strings."""

    if not isinstance(raw_value, list):
        return []
    normalized = [
        _normalize_structured_string(item)
        for item in raw_value
        if _normalize_structured_string(item)
    ]
    return normalized[:_DEFAULT_LIST_LIMIT]


def _normalize_distortion_labels(raw_value: object) -> list[str]:
    """Normalize distortion labels to the canonical stable label set."""

    values = raw_value if isinstance(raw_value, list) else [raw_value]
    normalized: list[str] = []
    for value in values:
        if not isinstance(value, str):
            continue
        canonical = _DISTORTION_LABEL_ALIASES.get(value.strip().lower())
        if canonical and canonical not in normalized:
            normalized.append(canonical)
    if normalized:
        return normalized
    return [_DEFAULT_DISTORTION_LABEL]


def _infer_distortion_labels(automatic_thought: str) -> list[str]:
    """Infer at least one canonical distortion label from the automatic thought."""

    lowered = automatic_thought.lower()
    labels: list[str] = []
    if any(token in lowered for token in ("always", "never", "ruined", "perfect", "completely")):
        labels.append("all_or_nothing_thinking")
    if any(
        token in lowered
        for token in ("disaster", "awful", "terrible", "never reach", "nothing will")
    ):
        labels.append("catastrophizing")
    if "should" in lowered or "must" in lowered or "ought" in lowered:
        labels.append("should_statements")
    if "i feel" in lowered or "feels like" in lowered:
        labels.append("emotional_reasoning")
    if any(
        token in lowered
        for token in ("only", "nothing good", "all i can see", "but i still failed")
    ):
        labels.append("mental_filtering")
    if labels:
        return labels[:2]
    return [_DEFAULT_DISTORTION_LABEL]


def _build_distortion_reason(*, labels: list[str], automatic_thought: str) -> str:
    """Return a deterministic short explanation for the detected distortion labels."""

    label = labels[0] if labels else _DEFAULT_DISTORTION_LABEL
    if label == "all_or_nothing_thinking":
        return (
            "The thought turns one moment into an all-or-total conclusion instead of leaving room "
            "for a middle ground."
        )
    if label == "catastrophizing":
        return "The thought jumps quickly from a setback to the worst-case outcome."
    if label == "should_statements":
        return "The thought uses rigid rules that create pressure instead of workable guidance."
    if label == "mental_filtering":
        return "The thought zooms in on the negative part and screens out the rest of the picture."
    if "feel" in automatic_thought.lower():
        return "The thought treats a difficult feeling as proof, even though feelings are not the whole evidence."
    return "The thought is being treated as a fact even though it may be only one interpretation."


def _fallback_evidence_for(*, emotion: str) -> list[str]:
    """Return deterministic evidence-for items without inventing facts."""

    return [
        f"You reported feeling {emotion.strip() or 'strong emotion'} in this situation.",
        "The thought may fit part of the moment even if it does not describe the whole pattern.",
    ]


def _fallback_evidence_against(*, goal: str | None) -> list[str]:
    """Return deterministic evidence-against items."""

    items = [
        "One difficult moment does not define the full day or the long-term pattern.",
        "A more useful response can still happen at the next meal, snack, or planning moment.",
    ]
    if goal:
        items.insert(1, f"Your goal can still be supported by the next small step toward {goal}.")
    return items[:_DEFAULT_LIST_LIMIT]


def _fallback_balanced_reframe(*, automatic_thought: str, goal: str | None) -> str:
    """Return a deterministic balanced reframe."""

    if goal:
        return (
            "This moment is frustrating, but it does not erase the bigger goal. "
            f"I can answer the thought kindly and take one next step that still supports {goal}."
        )
    return (
        "This moment is real, but the first automatic thought is not the only interpretation. "
        "I can step back, use the evidence, and choose one calmer next action."
    )


def _fallback_next_small_action(*, goal: str | None) -> str:
    """Return a deterministic next-small-action field."""

    if goal:
        return f"Choose one meal or habit step in the next 24 hours that clearly supports {goal}."
    return "Write one kinder replacement thought and pair it with one concrete next meal or habit step."


def _fallback_distortion_draft(
    *,
    situation: str,
    automatic_thought: str,
    emotion: str,
    goal: str | None,
    warnings: list[str],
) -> FitChefDistortionDraft:
    """Return a safe deterministic fallback for the distortion simulator."""

    labels = _infer_distortion_labels(automatic_thought)
    return FitChefDistortionDraft(
        distortion_labels=labels,
        why_it_matches=_build_distortion_reason(labels=labels, automatic_thought=automatic_thought),
        evidence_for=_fallback_evidence_for(emotion=emotion),
        evidence_against=_fallback_evidence_against(goal=goal),
        balanced_reframe=_fallback_balanced_reframe(
            automatic_thought=automatic_thought,
            goal=goal,
        ),
        next_small_action=_fallback_next_small_action(goal=goal),
        warnings=warnings,
    )


def _structured_texts_are_safe(*values: str) -> bool:
    """Return True when all structured strings pass the wellness-safe validator."""

    return all(validate_llm_output(value, domain="fitchef_mascot").ok for value in values if value)
