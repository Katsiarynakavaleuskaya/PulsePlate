"""Deterministic contract helpers for creative research offline evaluation.

RU: Валидирует offline bundle для creative_research и считает model-free scorecard.
EN: Validates offline creative_research bundles and computes a model-free scorecard.
"""

from __future__ import annotations

import re
from typing import Any

from core.insight.philosophy_validator import validate_llm_output
from scripts.orchestration.context_pack import normalize_text

SCHEMA_VERSION = "1.0"
TASK_CLASS = "creative_research"
VALID_PHASES: tuple[str, ...] = ("divergence", "convergence", "verification")
CONFIDENCE_LEVELS: tuple[str, ...] = ("low", "medium", "high", "unknown")
OUTPUT_CLASSES: tuple[str, ...] = (
    "mechanistic_hypothesis",
    "experimental_proposal",
    "anomaly_explanation_candidate",
    "creative_ideation",
)
PROMOTION_DECISIONS: tuple[str, ...] = ("promote", "defer", "discard")
DISCOVERY_REQUIRED_FIELDS: tuple[str, ...] = ("mechanism", "evidence_needed", "falsifier")

_TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)
_STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "into",
    "will",
    "can",
    "under",
    "after",
    "when",
    "then",
    "than",
    "using",
    "use",
    "users",
    "user",
    "meal",
    "meals",
    "plan",
    "plans",
    "week",
    "weeks",
    "more",
    "less",
    "their",
    "they",
    "them",
    "while",
}
_MECHANISM_HINTS = (
    "because",
    "friction",
    "feedback",
    "loop",
    "cue",
    "trigger",
    "reduces",
    "reduce",
    "increase",
    "shifts",
    "depletion",
    "overload",
)
_EVIDENCE_HINTS = (
    "compare",
    "measure",
    "track",
    "a b",
    "ab",
    "cohort",
    "trial",
    "retrospective",
    "completion",
    "adherence",
    "rate",
    "time",
    "weeks",
    "days",
    "survey",
)
_FALSIFIER_HINTS = (
    "if",
    "despite",
    "fails",
    "wrong",
    "would not",
    "does not",
    "stay flat",
    "persists",
    "remains",
    "compare",
)
_ANOMALY_HINTS = (
    "unexpected",
    "anomaly",
    "contradict",
    "conflicting",
    "signal",
    "drop",
    "depletion",
    "persist",
)
_PROPOSAL_HINTS = (
    "experiment",
    "trial",
    "a b",
    "ab",
    "crossover",
    "cohort",
    "randomized",
    "measure",
    "compare",
)


def _require_non_empty_string(payload: dict[str, Any], *, key: str, label: str) -> str:
    value = str(payload.get(key, "")).strip()
    if not value:
        raise ValueError(f"{label} must include a non-empty {key}.")
    return value


def _normalize_string_list(raw: Any, *, label: str) -> list[str]:
    if not isinstance(raw, list):
        raise ValueError(f"{label} must be a list.")
    values = [str(item).strip() for item in raw if str(item).strip()]
    return list(dict.fromkeys(values))


def _tokenize(*parts: str) -> set[str]:
    normalized = normalize_text(*parts)
    tokens = {match.group(0) for match in _TOKEN_RE.finditer(normalized)}
    return {token for token in tokens if len(token) >= 3 and token not in _STOPWORDS}


def _max_similarity(tokens: set[str], other_token_sets: list[set[str]]) -> float:
    if not tokens or not other_token_sets:
        return 0.0
    similarities: list[float] = []
    for other in other_token_sets:
        if not other:
            similarities.append(0.0)
            continue
        union = tokens | other
        similarities.append(len(tokens & other) / len(union) if union else 0.0)
    return max(similarities, default=0.0)


def _score_from_thresholds(value: float, thresholds: tuple[float, ...]) -> int:
    for index, threshold in enumerate(thresholds):
        if value < threshold:
            return 5 - index
    return 0


def _count_hints(text: str, hints: tuple[str, ...]) -> int:
    normalized = normalize_text(text)
    text_tokens = [match.group(0) for match in _TOKEN_RE.finditer(normalized)]
    if not text_tokens:
        return 0

    hint_hits = 0
    for hint in hints:
        hint_tokens = [match.group(0) for match in _TOKEN_RE.finditer(normalize_text(hint))]
        if not hint_tokens:
            continue
        window = len(hint_tokens)
        if any(
            text_tokens[index : index + window] == hint_tokens
            for index in range(len(text_tokens) - window + 1)
        ):
            hint_hits += 1
    return hint_hits


def _contains_any(text: str, hints: tuple[str, ...]) -> bool:
    return _count_hints(text, hints) > 0


def validate_bundle(payload: Any) -> dict[str, Any]:
    """Validate and normalize a creative research offline bundle."""

    if not isinstance(payload, dict):
        raise ValueError("Creative research eval bundle must be a JSON object.")

    schema_version = str(payload.get("schema_version", "")).strip()
    if schema_version != SCHEMA_VERSION:
        raise ValueError(
            f"Creative research eval bundle schema_version must equal {SCHEMA_VERSION!r}, "
            f"got {schema_version!r}."
        )

    bundle_id = _require_non_empty_string(
        payload,
        key="bundle_id",
        label="Creative research eval bundle",
    )
    task_class = _require_non_empty_string(
        payload,
        key="task_class",
        label="Creative research eval bundle",
    ).lower()
    if task_class != TASK_CLASS:
        raise ValueError(f"Creative research eval bundle task_class must equal {TASK_CLASS!r}.")

    phase = _require_non_empty_string(
        payload,
        key="phase",
        label="Creative research eval bundle",
    ).lower()
    if phase not in VALID_PHASES:
        allowed = ", ".join(VALID_PHASES)
        raise ValueError(f"Creative research eval bundle phase must be one of: {allowed}.")

    prompt_seed = _require_non_empty_string(
        payload,
        key="prompt_seed",
        label="Creative research eval bundle",
    )
    reference_corpus = _normalize_string_list(
        payload.get("reference_corpus", []),
        label="Creative research eval bundle reference_corpus",
    )

    candidates_raw = payload.get("candidates")
    if not isinstance(candidates_raw, list) or not candidates_raw:
        raise ValueError("Creative research eval bundle candidates must be a non-empty list.")

    candidates: list[dict[str, Any]] = []
    for index, candidate_raw in enumerate(candidates_raw, start=1):
        if not isinstance(candidate_raw, dict):
            raise ValueError(f"Creative research candidate #{index} must be an object.")
        label = f"Creative research candidate #{index}"
        confidence = _require_non_empty_string(
            candidate_raw,
            key="confidence",
            label=label,
        ).lower()
        if confidence not in CONFIDENCE_LEVELS:
            allowed = ", ".join(CONFIDENCE_LEVELS)
            raise ValueError(f"{label} confidence must be one of: {allowed}.")

        candidates.append(
            {
                "candidate_id": _require_non_empty_string(
                    candidate_raw,
                    key="candidate_id",
                    label=label,
                ),
                "claim": _require_non_empty_string(
                    candidate_raw,
                    key="claim",
                    label=label,
                ),
                "mechanism": str(candidate_raw.get("mechanism", "")).strip(),
                "evidence_needed": str(candidate_raw.get("evidence_needed", "")).strip(),
                "falsifier": str(candidate_raw.get("falsifier", "")).strip(),
                "confidence": confidence,
                "known_risks": _normalize_string_list(
                    candidate_raw.get("known_risks", []),
                    label=f"{label} known_risks",
                ),
                "wellness_boundary": _require_non_empty_string(
                    candidate_raw,
                    key="wellness_boundary",
                    label=label,
                ),
            }
        )

    return {
        "schema_version": schema_version,
        "bundle_id": bundle_id,
        "task_class": task_class,
        "phase": phase,
        "prompt_seed": prompt_seed,
        "reference_corpus": reference_corpus,
        "candidates": candidates,
    }


def classify_output(candidate: dict[str, Any]) -> tuple[str, list[str]]:
    """Return the deterministic output class and triggered control labels."""

    missing_required = [
        field_name for field_name in DISCOVERY_REQUIRED_FIELDS if not candidate[field_name].strip()
    ]
    controls: list[str] = []
    if missing_required:
        controls.append("missing_required_discovery_fields")
        return "creative_ideation", controls

    classification_text = normalize_text(candidate["claim"], candidate["mechanism"])
    if _contains_any(classification_text, _ANOMALY_HINTS):
        return "anomaly_explanation_candidate", controls
    if _contains_any(classification_text, _PROPOSAL_HINTS):
        return "experimental_proposal", controls
    return "mechanistic_hypothesis", controls


def build_scorecard(
    candidate: dict[str, Any],
    *,
    output_class: str,
    reference_overlap: float,
    peer_overlap: float,
    duplicate_candidate: bool,
) -> tuple[dict[str, int], list[str]]:
    """Compute deterministic scorecard values and triggered controls."""

    combined_text = " ".join(
        [
            candidate["claim"],
            candidate["mechanism"],
            candidate["evidence_needed"],
            candidate["falsifier"],
        ]
    )
    report = validate_llm_output(combined_text, domain="creative_research")
    controls: list[str] = []
    if duplicate_candidate:
        controls.append("duplicate_candidate")
    if reference_overlap >= 0.72:
        controls.append("corpus_overlap_high")
    if not report.ok:
        controls.append("unsafe_wellness_language")

    originality = _score_from_thresholds(reference_overlap, (0.2, 0.3, 0.45, 0.6, 0.75))
    flexibility = (
        0
        if duplicate_candidate
        else _score_from_thresholds(
            peer_overlap,
            (0.2, 0.3, 0.45, 0.6, 0.75),
        )
    )

    mechanism_tokens = len(_tokenize(candidate["mechanism"]))
    mechanism_hints = _count_hints(candidate["mechanism"], _MECHANISM_HINTS)
    if not candidate["mechanism"].strip():
        mechanism_specificity = 0
    elif mechanism_tokens >= 18 and mechanism_hints >= 2:
        mechanism_specificity = 5
    elif mechanism_tokens >= 12 and mechanism_hints >= 1:
        mechanism_specificity = 4
    elif mechanism_tokens >= 8:
        mechanism_specificity = 3
    elif mechanism_tokens >= 4:
        mechanism_specificity = 2
    else:
        mechanism_specificity = 1

    evidence_hits = _count_hints(candidate["evidence_needed"], _EVIDENCE_HINTS)
    evidence_tokens = len(_tokenize(candidate["evidence_needed"]))
    if not candidate["evidence_needed"].strip():
        groundedness = 0
    elif evidence_hits >= 4 and candidate["known_risks"]:
        groundedness = 5
    elif evidence_hits >= 3:
        groundedness = 4
    elif evidence_hits >= 1 or evidence_tokens >= 10:
        groundedness = 3
    elif evidence_tokens >= 5:
        groundedness = 2
    else:
        groundedness = 1

    falsifier_hits = _count_hints(candidate["falsifier"], _FALSIFIER_HINTS)
    falsifier_tokens = len(_tokenize(candidate["falsifier"]))
    normalized_falsifier = normalize_text(candidate["falsifier"])
    if not candidate["falsifier"].strip():
        falsifiability = 0
    elif _contains_any(normalized_falsifier, ("if", "when")) and falsifier_hits >= 2:
        falsifiability = 5
    elif falsifier_hits >= 2:
        falsifiability = 4
    elif falsifier_hits >= 1 or falsifier_tokens >= 10:
        falsifiability = 3
    elif falsifier_tokens >= 5:
        falsifiability = 2
    else:
        falsifiability = 1
    if falsifiability < 3 and output_class != "creative_ideation":
        controls.append("weak_falsifier")

    boundary = normalize_text(candidate["wellness_boundary"])
    if not report.ok:
        wellness_safety = 0
    elif "wellness" in boundary and ("not diagnosis" in boundary or "not treatment" in boundary):
        wellness_safety = 5
    elif "wellness" in boundary:
        wellness_safety = 4
    else:
        wellness_safety = 3

    hallucination_risk = 5 - min(groundedness, falsifiability)
    if duplicate_candidate or reference_overlap >= 0.72:
        hallucination_risk = max(hallucination_risk, 4)
    if candidate["confidence"] == "high" and min(groundedness, falsifiability) <= 2:
        hallucination_risk = min(5, hallucination_risk + 1)
    if not report.ok:
        hallucination_risk = 5

    scorecard = {
        "originality": originality,
        "flexibility": flexibility,
        "mechanism_specificity": mechanism_specificity,
        "groundedness": groundedness,
        "falsifiability": falsifiability,
        "wellness_safety": wellness_safety,
        "hallucination_risk": hallucination_risk,
    }
    return scorecard, list(dict.fromkeys(controls))


def select_promotion_decision(
    *,
    output_class: str,
    scorecard: dict[str, int],
    negative_controls: list[str],
) -> tuple[str, str | None]:
    """Return deterministic promote/defer/discard plus optional degrade label."""

    if (
        output_class == "creative_ideation"
        or "unsafe_wellness_language" in negative_controls
        or "duplicate_candidate" in negative_controls
        or scorecard["hallucination_risk"] >= 4
    ):
        return "discard", "interesting but unverified hypothesis"

    promotable = (
        scorecard["originality"] >= 3
        and scorecard["flexibility"] >= 3
        and scorecard["mechanism_specificity"] >= 3
        and scorecard["groundedness"] >= 3
        and scorecard["falsifiability"] >= 3
        and scorecard["wellness_safety"] >= 4
        and scorecard["hallucination_risk"] <= 2
    )
    if promotable:
        return "promote", None
    return "defer", "interesting but unverified hypothesis"


def evaluate_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    """Evaluate a normalized creative research bundle into deterministic results."""

    validated = validate_bundle(bundle)
    reference_token_sets = [_tokenize(item) for item in validated["reference_corpus"]]
    candidate_token_sets = [
        _tokenize(
            candidate["claim"],
            candidate["mechanism"],
            candidate["evidence_needed"],
            candidate["falsifier"],
        )
        for candidate in validated["candidates"]
    ]
    evaluated_candidates: list[dict[str, Any]] = []

    for index, candidate in enumerate(validated["candidates"]):
        output_class, controls = classify_output(candidate)
        candidate_tokens = candidate_token_sets[index]
        peer_sets = [
            token_set
            for peer_index, token_set in enumerate(candidate_token_sets)
            if peer_index != index
        ]
        reference_overlap = round(_max_similarity(candidate_tokens, reference_token_sets), 4)
        peer_overlap = round(_max_similarity(candidate_tokens, peer_sets), 4)
        duplicate_candidate = peer_overlap >= 0.8

        scorecard, extra_controls = build_scorecard(
            candidate,
            output_class=output_class,
            reference_overlap=reference_overlap,
            peer_overlap=peer_overlap,
            duplicate_candidate=duplicate_candidate,
        )
        negative_controls = list(dict.fromkeys([*controls, *extra_controls]))
        promotion_decision, degrade_label = select_promotion_decision(
            output_class=output_class,
            scorecard=scorecard,
            negative_controls=negative_controls,
        )
        evaluated_candidates.append(
            {
                **candidate,
                "output_class": output_class,
                "reference_overlap": reference_overlap,
                "peer_overlap": peer_overlap,
                "negative_controls_triggered": negative_controls,
                "scorecard": scorecard,
                "promotion_decision": promotion_decision,
                "presentation_label": degrade_label,
            }
        )

    decision_counts = {decision: 0 for decision in PROMOTION_DECISIONS}
    for candidate in evaluated_candidates:
        decision_counts[candidate["promotion_decision"]] += 1

    return {
        "schema_version": SCHEMA_VERSION,
        "bundle_id": validated["bundle_id"],
        "task_class": validated["task_class"],
        "phase": validated["phase"],
        "prompt_seed": validated["prompt_seed"],
        "reference_corpus_size": len(validated["reference_corpus"]),
        "summary": {
            "candidate_count": len(evaluated_candidates),
            **decision_counts,
        },
        "candidates": evaluated_candidates,
    }
