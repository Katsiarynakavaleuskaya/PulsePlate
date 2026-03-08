"""Transparency and wellness-boundary registry for health-adjacent surfaces."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class TransparencyNotice:
    """Canonical notice for an automated wellness surface."""

    surface_id: str
    title: str
    analysis_kind: str
    endpoints: tuple[str, ...]
    inputs_used: tuple[str, ...]
    boundary: str
    notice: str
    emergency_use: str
    treatment_decision_use: str
    escalation: str


_TRANSPARENCY_REGISTRY: tuple[TransparencyNotice, ...] = (
    TransparencyNotice(
        surface_id="bmi_wellness_screening",
        title="BMI wellness screening",
        analysis_kind="formula-based automated analysis",
        endpoints=("/bmi", "/api/v1/bmi", "/api/v1/pro/bmi/calculate"),
        inputs_used=("weight", "height", "age", "sex", "optional body context"),
        boundary="Wellness-only; not a medical diagnosis or treatment recommendation.",
        notice="Uses deterministic BMI rules and explanatory copy to summarize a screening metric.",
        emergency_use="Do not use for emergency, acute, or urgent health decisions.",
        treatment_decision_use="Do not use as a sole basis for treatment or medication changes.",
        escalation="Consult a qualified healthcare professional when medical interpretation is needed.",
    ),
    TransparencyNotice(
        surface_id="bodyfat_estimation",
        title="Body fat estimation",
        analysis_kind="formula-based wellness estimation",
        endpoints=("/api/v1/bodyfat",),
        inputs_used=("anthropometrics", "sex", "age"),
        boundary="Estimate-only; not a clinical body-composition assessment.",
        notice="Provides a wellness estimate with known formula limitations and context dependency.",
        emergency_use="Do not use for urgent or diagnostic decisions.",
        treatment_decision_use="Do not use as a sole basis for treatment or care planning.",
        escalation="Use professional measurement methods for clinical or athletic evaluation.",
    ),
    TransparencyNotice(
        surface_id="nutrition_targets_and_weekly_plan",
        title="Nutrition targets and planning",
        analysis_kind="rule-based automated wellness guidance",
        endpoints=(
            "/api/v1/pro/nutrition/daily",
            "/api/v1/pro/meal/weekly",
            "/api/v1/premium/plate",
        ),
        inputs_used=("profile inputs", "goal", "activity", "nutrition formulas"),
        boundary="Wellness planning only; not personalized medical nutrition therapy.",
        notice="Builds calorie, macro, and planning suggestions from deterministic formulas and rules.",
        emergency_use="Not for emergency nutrition support or crisis intervention.",
        treatment_decision_use="Not a substitute for clinician-supervised nutrition decisions.",
        escalation="Use licensed care pathways when medical conditions drive nutrition decisions.",
    ),
    TransparencyNotice(
        surface_id="ai_generated_insight",
        title="AI-generated wellness insight",
        analysis_kind="automated AI-assisted analysis",
        endpoints=("/insight", "/api/v1/insight", "/api/v1/pro/cbt/insight"),
        inputs_used=("user text", "retrieved context", "configured provider output"),
        boundary="Wellness coaching only; not therapy, diagnosis, or clinical decision support.",
        notice="May use retrieval, prompt rewriting, and LLM generation to produce a wellness-oriented response.",
        emergency_use="Not for emergencies, crisis handling, or acute medical situations.",
        treatment_decision_use="Do not use as a sole basis for treatment, medication, or care coordination.",
        escalation="Direct users to qualified professionals or emergency services when clinical risk is suspected.",
    ),
)

_BLOCKED_REGULATED_LANE = {
    "status": "blocked_without_separate_compliance_track",
    "examples": [
        "clinical diagnosis or treatment recommendations",
        "crisis or self-harm intervention workflows",
        "substance-use disorder records or 42 CFR Part 2 data",
        "provider/EHR ingestion and redisclosure",
    ],
    "rule": (
        "These scenarios require a separate regulated lane with consent segregation, "
        "storage segregation, redisclosure controls, and explicit legal approval."
    ),
}


def get_transparency_registry() -> dict[str, dict[str, object]]:
    """Return transparency notices keyed by surface id."""

    return {item.surface_id: asdict(item) for item in _TRANSPARENCY_REGISTRY}


def get_blocked_regulated_lane() -> dict[str, object]:
    """Return the blocked regulated-lane contract."""

    return dict(_BLOCKED_REGULATED_LANE)
