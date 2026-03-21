"""Creative research evaluation contract helpers.

RU: Общий SoT для creative_research: валидация bundle, классификация output
типов и детерминированный scorecard для offline/runtime reuse.
EN: Shared SoT for creative_research: bundle validation, output-class
classification, and deterministic scorecard logic reused by offline/runtime
paths.
"""

from __future__ import annotations

import re
from typing import Literal, TypedDict, cast

from core.insight.philosophy_validator import validate_llm_output

SCHEMA_VERSION = "1.0"
TASK_CLASS = "creative_research"
CreativeResearchPhase = Literal["divergence", "convergence", "verification"]
CreativeResearchConfidence = Literal["low", "medium", "high", "unknown"]
CreativeResearchOutputClass = Literal[
    "mechanistic_hypothesis",
    "experimental_proposal",
    "anomaly_explanation_candidate",
    "creative_ideation",
]
CreativeResearchPromotionDecision = Literal["promote", "defer", "discard"]

VALID_PHASES: tuple[CreativeResearchPhase, ...] = ("divergence", "convergence", "verification")
CONFIDENCE_LEVELS: tuple[CreativeResearchConfidence, ...] = ("low", "medium", "high", "unknown")
OUTPUT_CLASSES: tuple[CreativeResearchOutputClass, ...] = (
    "mechanistic_hypothesis",
    "experimental_proposal",
    "anomaly_explanation_candidate",
    "creative_ideation",
)
PROMOTION_DECISIONS: tuple[CreativeResearchPromotionDecision, ...] = (
    "promote",
    "defer",
    "discard",
)
DISCOVERY_REQUIRED_FIELDS: tuple[str, ...] = ("mechanism", "evidence_needed", "falsifier")
SCIENTIFIC_DISCOVERY_FIELDS: tuple[str, ...] = (
    "alternative_explanations",
    "counterevidence",
    "stopping_rule",
    "decision_rule",
    "minimum_observation",
)


class CreativeResearchCandidateRecord(TypedDict):
    """Validated creative-research candidate record."""

    candidate_id: str
    claim: str
    mechanism: str
    evidence_needed: str
    falsifier: str
    confidence: CreativeResearchConfidence
    known_risks: list[str]
    wellness_boundary: str
    alternative_explanations: list[str]
    counterevidence: list[str]
    stopping_rule: str
    decision_rule: str
    minimum_observation: str


class CreativeResearchBundleRecord(TypedDict):
    """Validated creative-research bundle record."""

    schema_version: str
    bundle_id: str
    task_class: str
    phase: CreativeResearchPhase
    prompt_seed: str
    reference_corpus: list[str]
    candidates: list[CreativeResearchCandidateRecord]


class CreativeResearchScorecardRecord(TypedDict):
    """Deterministic creative-research scorecard record."""

    originality: int
    flexibility: int
    mechanism_specificity: int
    groundedness: int
    falsifiability: int
    wellness_safety: int
    hallucination_risk: int


class CreativeResearchEvaluatedCandidateRecord(CreativeResearchCandidateRecord):
    """Evaluated candidate record with deterministic outputs."""

    output_class: CreativeResearchOutputClass
    reference_overlap: float
    peer_overlap: float
    negative_controls_triggered: list[str]
    scorecard: CreativeResearchScorecardRecord
    promotion_decision: CreativeResearchPromotionDecision
    presentation_label: str | None


class CreativeResearchEvaluationSummaryRecord(TypedDict):
    """Aggregate promote/defer/discard counts for one bundle."""

    candidate_count: int
    promote: int
    defer: int
    discard: int


class CreativeResearchEvaluationResultRecord(TypedDict):
    """Fully evaluated creative-research bundle record."""

    schema_version: str
    bundle_id: str
    task_class: str
    phase: CreativeResearchPhase
    prompt_seed: str
    reference_corpus_size: int
    summary: CreativeResearchEvaluationSummaryRecord
    candidates: list[CreativeResearchEvaluatedCandidateRecord]


TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)
STOPWORDS = {
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
MECHANISM_HINTS = (
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
EVIDENCE_HINTS = (
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
FALSIFIER_HINTS = (
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
ANOMALY_HINTS = (
    "unexpected",
    "anomaly",
    "contradict",
    "conflicting",
    "signal",
    "drop",
    "depletion",
    "persist",
)
PROPOSAL_HINTS = (
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


def normalize_creative_research_text(*parts: str) -> str:
    """Normalize free text for deterministic lexical matching."""

    raw = " ".join(part.strip().lower() for part in parts if part.strip())
    for token in ("/", "_", "-", ".", ":", "(", ")", ","):
        raw = raw.replace(token, " ")
    return " ".join(raw.split())


def _require_object_mapping(
    raw: object,
    *,
    label: str,
    expected_phrase: str = "an object",
) -> dict[str, object]:
    """Validate raw object payloads before domain normalization."""

    if not isinstance(raw, dict):
        raise ValueError(f"{label} must be {expected_phrase}.")
    return {str(key): value for key, value in raw.items()}


def _require_non_empty_string(payload: dict[str, object], *, key: str, label: str) -> str:
    value = str(payload.get(key, "")).strip()
    if not value:
        raise ValueError(f"{label} must include a non-empty {key}.")
    return value


def _normalize_string_list(raw: object, *, label: str) -> list[str]:
    if not isinstance(raw, list):
        raise ValueError(f"{label} must be a list.")
    values = [str(item).strip() for item in raw if str(item).strip()]
    return list(dict.fromkeys(values))


def _tokenize(*parts: str) -> set[str]:
    normalized = normalize_creative_research_text(*parts)
    tokens = {match.group(0) for match in TOKEN_RE.finditer(normalized)}
    return {token for token in tokens if len(token) >= 3 and token not in STOPWORDS}


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
    normalized = normalize_creative_research_text(text)
    text_tokens = [match.group(0) for match in TOKEN_RE.finditer(normalized)]
    if not text_tokens:
        return 0

    hint_hits = 0
    for hint in hints:
        hint_tokens = [
            match.group(0) for match in TOKEN_RE.finditer(normalize_creative_research_text(hint))
        ]
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


def validate_bundle(payload: object) -> CreativeResearchBundleRecord:
    """Validate and normalize a creative research bundle."""

    payload_dict = _require_object_mapping(
        payload,
        label="Creative research eval bundle",
        expected_phrase="a JSON object",
    )

    schema_version = str(payload_dict.get("schema_version", "")).strip()
    if schema_version != SCHEMA_VERSION:
        raise ValueError(
            f"Creative research eval bundle schema_version must equal {SCHEMA_VERSION!r}, "
            f"got {schema_version!r}."
        )

    bundle_id = _require_non_empty_string(
        payload_dict,
        key="bundle_id",
        label="Creative research eval bundle",
    )
    task_class = _require_non_empty_string(
        payload_dict,
        key="task_class",
        label="Creative research eval bundle",
    ).lower()
    if task_class != TASK_CLASS:
        raise ValueError(f"Creative research eval bundle task_class must equal {TASK_CLASS!r}.")

    phase = _require_non_empty_string(
        payload_dict,
        key="phase",
        label="Creative research eval bundle",
    ).lower()
    if phase not in VALID_PHASES:
        allowed = ", ".join(VALID_PHASES)
        raise ValueError(f"Creative research eval bundle phase must be one of: {allowed}.")

    prompt_seed = _require_non_empty_string(
        payload_dict,
        key="prompt_seed",
        label="Creative research eval bundle",
    )
    reference_corpus = _normalize_string_list(
        payload_dict.get("reference_corpus", []),
        label="Creative research eval bundle reference_corpus",
    )

    candidates_raw = payload_dict.get("candidates")
    if not isinstance(candidates_raw, list) or not candidates_raw:
        raise ValueError("Creative research eval bundle candidates must be a non-empty list.")

    candidates: list[CreativeResearchCandidateRecord] = []
    for index, candidate_raw in enumerate(candidates_raw, start=1):
        candidate_payload = _require_object_mapping(
            candidate_raw,
            label=f"Creative research candidate #{index}",
        )
        label = f"Creative research candidate #{index}"
        confidence = _require_non_empty_string(
            candidate_payload,
            key="confidence",
            label=label,
        ).lower()
        if confidence not in CONFIDENCE_LEVELS:
            allowed = ", ".join(CONFIDENCE_LEVELS)
            raise ValueError(f"{label} confidence must be one of: {allowed}.")

        normalized_confidence = cast(CreativeResearchConfidence, confidence)
        candidate: CreativeResearchCandidateRecord = {
            "candidate_id": _require_non_empty_string(
                candidate_payload,
                key="candidate_id",
                label=label,
            ),
            "claim": _require_non_empty_string(
                candidate_payload,
                key="claim",
                label=label,
            ),
            "mechanism": str(candidate_payload.get("mechanism", "")).strip(),
            "evidence_needed": str(candidate_payload.get("evidence_needed", "")).strip(),
            "falsifier": str(candidate_payload.get("falsifier", "")).strip(),
            "confidence": normalized_confidence,
            "known_risks": _normalize_string_list(
                candidate_payload.get("known_risks", []),
                label=f"{label} known_risks",
            ),
            "wellness_boundary": _require_non_empty_string(
                candidate_payload,
                key="wellness_boundary",
                label=label,
            ),
            "alternative_explanations": _normalize_string_list(
                candidate_payload.get("alternative_explanations", []),
                label=f"{label} alternative_explanations",
            ),
            "counterevidence": _normalize_string_list(
                candidate_payload.get("counterevidence", []),
                label=f"{label} counterevidence",
            ),
            "stopping_rule": str(candidate_payload.get("stopping_rule", "")).strip(),
            "decision_rule": str(candidate_payload.get("decision_rule", "")).strip(),
            "minimum_observation": str(candidate_payload.get("minimum_observation", "")).strip(),
        }
        candidates.append(candidate)

    normalized_phase = cast(CreativeResearchPhase, phase)
    bundle_record: CreativeResearchBundleRecord = {
        "schema_version": schema_version,
        "bundle_id": bundle_id,
        "task_class": task_class,
        "phase": normalized_phase,
        "prompt_seed": prompt_seed,
        "reference_corpus": reference_corpus,
        "candidates": candidates,
    }
    return bundle_record


def classify_output(
    candidate: CreativeResearchCandidateRecord,
) -> tuple[CreativeResearchOutputClass, list[str]]:
    """Return the deterministic output class and triggered control labels."""

    candidate_required_values = {
        "mechanism": candidate["mechanism"],
        "evidence_needed": candidate["evidence_needed"],
        "falsifier": candidate["falsifier"],
    }
    missing_required = [
        field_name
        for field_name in DISCOVERY_REQUIRED_FIELDS
        if not candidate_required_values[field_name].strip()
    ]
    controls: list[str] = []
    if missing_required:
        controls.append("missing_required_discovery_fields")
        return "creative_ideation", controls

    classification_text = normalize_creative_research_text(
        candidate["claim"],
        candidate["mechanism"],
    )
    if _contains_any(classification_text, ANOMALY_HINTS):
        return "anomaly_explanation_candidate", controls
    if _contains_any(classification_text, PROPOSAL_HINTS):
        return "experimental_proposal", controls
    return "mechanistic_hypothesis", controls


def build_scorecard(
    candidate: CreativeResearchCandidateRecord,
    *,
    output_class: CreativeResearchOutputClass,
    reference_overlap: float,
    peer_overlap: float,
    duplicate_candidate: bool,
) -> tuple[CreativeResearchScorecardRecord, list[str]]:
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
    missing_scientific_fields = [
        field_name
        for field_name in SCIENTIFIC_DISCOVERY_FIELDS
        if (
            not candidate.get(field_name, "")
            if isinstance(candidate.get(field_name, ""), str)
            else not candidate.get(field_name, [])
        )
    ]
    if missing_scientific_fields:
        controls.append("missing_scientific_research_fields")

    originality = _score_from_thresholds(reference_overlap, (0.2, 0.3, 0.45, 0.6, 0.75))
    flexibility = (
        0
        if duplicate_candidate
        else _score_from_thresholds(peer_overlap, (0.2, 0.3, 0.45, 0.6, 0.75))
    )

    mechanism_tokens = len(_tokenize(candidate["mechanism"]))
    mechanism_hints = _count_hints(candidate["mechanism"], MECHANISM_HINTS)
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

    evidence_hits = _count_hints(candidate["evidence_needed"], EVIDENCE_HINTS)
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

    falsifier_hits = _count_hints(candidate["falsifier"], FALSIFIER_HINTS)
    falsifier_tokens = len(_tokenize(candidate["falsifier"]))
    normalized_falsifier = normalize_creative_research_text(candidate["falsifier"])
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

    boundary = normalize_creative_research_text(candidate["wellness_boundary"])
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

    scorecard: CreativeResearchScorecardRecord = {
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
    output_class: CreativeResearchOutputClass,
    scorecard: CreativeResearchScorecardRecord,
    negative_controls: list[str],
) -> tuple[CreativeResearchPromotionDecision, str | None]:
    """Return deterministic promote/defer/discard plus optional degrade label."""

    if (
        output_class == "creative_ideation"
        or "unsafe_wellness_language" in negative_controls
        or "duplicate_candidate" in negative_controls
        or scorecard["hallucination_risk"] >= 4
    ):
        return "discard", "interesting but unverified hypothesis"
    if "missing_scientific_research_fields" in negative_controls:
        return "defer", "interesting but unverified hypothesis"

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


def evaluate_bundle(bundle: object) -> CreativeResearchEvaluationResultRecord:
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
    evaluated_candidates: list[CreativeResearchEvaluatedCandidateRecord] = []

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
        evaluated_candidate: CreativeResearchEvaluatedCandidateRecord = {
            **candidate,
            "output_class": output_class,
            "reference_overlap": reference_overlap,
            "peer_overlap": peer_overlap,
            "negative_controls_triggered": negative_controls,
            "scorecard": scorecard,
            "promotion_decision": promotion_decision,
            "presentation_label": degrade_label,
        }
        evaluated_candidates.append(evaluated_candidate)

    decision_counts: dict[CreativeResearchPromotionDecision, int] = {
        decision: 0 for decision in PROMOTION_DECISIONS
    }
    for candidate in evaluated_candidates:
        decision_counts[candidate["promotion_decision"]] += 1

    summary: CreativeResearchEvaluationSummaryRecord = {
        "candidate_count": len(evaluated_candidates),
        "promote": decision_counts["promote"],
        "defer": decision_counts["defer"],
        "discard": decision_counts["discard"],
    }
    result: CreativeResearchEvaluationResultRecord = {
        "schema_version": SCHEMA_VERSION,
        "bundle_id": validated["bundle_id"],
        "task_class": validated["task_class"],
        "phase": validated["phase"],
        "prompt_seed": validated["prompt_seed"],
        "reference_corpus_size": len(validated["reference_corpus"]),
        "summary": summary,
        "candidates": evaluated_candidates,
    }
    return result


__all__ = [
    "CONFIDENCE_LEVELS",
    "DISCOVERY_REQUIRED_FIELDS",
    "SCIENTIFIC_DISCOVERY_FIELDS",
    "OUTPUT_CLASSES",
    "PROMOTION_DECISIONS",
    "SCHEMA_VERSION",
    "TASK_CLASS",
    "VALID_PHASES",
    "CreativeResearchBundleRecord",
    "CreativeResearchCandidateRecord",
    "CreativeResearchConfidence",
    "CreativeResearchEvaluatedCandidateRecord",
    "CreativeResearchEvaluationResultRecord",
    "CreativeResearchEvaluationSummaryRecord",
    "CreativeResearchOutputClass",
    "CreativeResearchPhase",
    "CreativeResearchPromotionDecision",
    "CreativeResearchScorecardRecord",
    "_count_hints",
    "build_scorecard",
    "classify_output",
    "evaluate_bundle",
    "normalize_creative_research_text",
    "select_promotion_decision",
    "validate_bundle",
]
