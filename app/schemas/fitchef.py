"""Internal FitChef runtime contracts. / Внутренние контракты runtime FitChef."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.shopping_list import ShoppingListDTO, ShoppingListPreferences
from core.judgment import ClaimType, EvidenceMode

FitChefAgentId = Literal["fitchef-agent"]
FitChefExecutionMode = Literal["auto-safe", "review-required", "blocked"]
FitChefTaskType = Literal[
    "coach_insight",
    "distortion_simulator",
    "identity_loop_mapper",
    "weekly_plan",
    "shopping_followup",
    "mascot_insight",
    "weekly_reflection",
    "slip_support",
]
FitChefQuotaState = Literal["not_consumed", "consumed"]
FitChefWeeklyReflectionResponseState = Literal[
    "generated",
    "clarification_required",
]
FitChefDistortionFieldPath = Literal[
    "distortion_labels",
    "why_it_matches",
    "evidence_for",
    "evidence_against",
    "balanced_reframe",
    "next_small_action",
]
FitChefFieldAssuranceState = Literal[
    "not_evidence_bearing",
    "request_context_only",
    "candidate_linked_unverified",
    "evidence_link_missing",
    "source_snapshot_mismatch",
    "assessment_unavailable",
]
FitChefFieldAssuranceReasonCode = Literal[
    "request_context_not_source_evidence",
    "candidate_sources_present_unverified",
    "candidate_sources_missing",
    "not_evidence_bearing",
    "source_snapshot_mismatch",
    "duplicate_source_identity",
    "snapshot_fingerprint_unavailable",
    "assessment_unavailable",
]

_FITCHEF_DISTORTION_FIELD_ORDER: tuple[FitChefDistortionFieldPath, ...] = (
    "distortion_labels",
    "why_it_matches",
    "evidence_for",
    "evidence_against",
    "balanced_reframe",
    "next_small_action",
)
_OPAQUE_SHA256_PREFIX = "sha256:"


class FitChefCoachInsightInput(BaseModel):
    """Internal coach-insight task input. / Входные данные coach-insight задачи."""

    safe_query: str = Field(..., min_length=1)
    api_key: str = Field(..., min_length=1)
    endpoint: str = Field(..., min_length=1)
    method: str = Field(..., min_length=1)


class FitChefTaskEnvelope(BaseModel):
    """Shared internal FitChef task envelope. / Общий внутренний envelope задачи FitChef."""

    agent_id: FitChefAgentId = "fitchef-agent"
    mode: FitChefExecutionMode
    task_type: FitChefTaskType
    tool_budget: int = Field(default=1, ge=1, le=3)


class FitChefCoachInsightTaskEnvelope(FitChefTaskEnvelope):
    """Coach-insight task envelope. / Envelope для задачи coach-insight."""

    task_type: Literal["coach_insight"] = "coach_insight"
    input: FitChefCoachInsightInput


class FitChefDistortionSimulatorInput(BaseModel):
    """Internal distortion-simulator task input."""

    safe_situation: str = Field(..., min_length=1)
    safe_automatic_thought: str = Field(..., min_length=1)
    safe_emotion: str = Field(..., min_length=1)
    safe_goal: str | None = None
    api_key: str = Field(..., min_length=1)
    endpoint: str = Field(..., min_length=1)
    method: str = Field(..., min_length=1)


class FitChefDistortionSimulatorTaskEnvelope(FitChefTaskEnvelope):
    """Distortion-simulator task envelope."""

    task_type: Literal["distortion_simulator"] = "distortion_simulator"
    input: FitChefDistortionSimulatorInput


class FitChefIdentityLoopMapperInput(BaseModel):
    """Internal identity-loop mapper task input."""

    safe_goal: str = Field(..., min_length=1)
    safe_recent_pattern: str = Field(..., min_length=1)
    safe_self_talk: str = Field(..., min_length=1)
    safe_trigger_context: str | None = None
    api_key: str = Field(..., min_length=1)
    endpoint: str = Field(..., min_length=1)
    method: str = Field(..., min_length=1)


class FitChefIdentityLoopMapperTaskEnvelope(FitChefTaskEnvelope):
    """Identity-loop mapper task envelope."""

    task_type: Literal["identity_loop_mapper"] = "identity_loop_mapper"
    input: FitChefIdentityLoopMapperInput


class FitChefMascotInsightInput(BaseModel):
    """Internal mascot-insight task input. / Входные данные mascot-insight задачи."""

    safe_query: str = Field(..., min_length=1)
    api_key: str = Field(..., min_length=1)
    endpoint: str = Field(..., min_length=1)
    method: str = Field(..., min_length=1)


class FitChefMascotInsightTaskEnvelope(FitChefTaskEnvelope):
    """Mascot-insight task envelope. / Envelope для задачи mascot-insight."""

    task_type: Literal["mascot_insight"] = "mascot_insight"
    input: FitChefMascotInsightInput


class FitChefWeeklyReflectionInput(BaseModel):
    """Internal weekly-reflection task input. / Входные данные weekly-reflection задачи."""

    safe_summary: str = Field(..., min_length=1)
    safe_goal: str | None = None
    api_key: str = Field(..., min_length=1)
    endpoint: str = Field(..., min_length=1)
    method: str = Field(..., min_length=1)


class FitChefWeeklyReflectionTaskEnvelope(FitChefTaskEnvelope):
    """Weekly-reflection task envelope. / Envelope для weekly-reflection."""

    task_type: Literal["weekly_reflection"] = "weekly_reflection"
    input: FitChefWeeklyReflectionInput


class FitChefSlipSupportInput(BaseModel):
    """Internal slip-support task input. / Входные данные slip-support задачи."""

    safe_event_text: str = Field(..., min_length=1)
    safe_goal: str | None = None
    api_key: str = Field(..., min_length=1)
    endpoint: str = Field(..., min_length=1)
    method: str = Field(..., min_length=1)


class FitChefSlipSupportTaskEnvelope(FitChefTaskEnvelope):
    """Slip-support task envelope. / Envelope для slip-support."""

    task_type: Literal["slip_support"] = "slip_support"
    input: FitChefSlipSupportInput


class FitChefWeeklyPlanInput(BaseModel):
    """Internal weekly-plan input. / Входные данные weekly-plan задачи."""

    request_data: dict[str, Any] = Field(default_factory=dict)


class FitChefWeeklyPlanTaskEnvelope(FitChefTaskEnvelope):
    """Weekly-plan task envelope. / Envelope для задачи weekly-plan."""

    task_type: Literal["weekly_plan"] = "weekly_plan"
    input: FitChefWeeklyPlanInput


class FitChefSourceItem(BaseModel):
    """Internal source item. / Внутренний элемент источника."""

    chunk_id: str
    file: str
    preview: str
    score: float


class FitChefClarificationV1(BaseModel):
    """Fixed request-scoped clarification contract for FitChef."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["fitchef_clarification.v1"] = "fitchef_clarification.v1"
    kind: Literal["missing_required_context"] = "missing_required_context"
    question_id: Literal["weekly_reflection.current_goal"] = "weekly_reflection.current_goal"
    requested_fields: tuple[Literal["goal"]] = ("goal",)
    question_count: Literal[1] = 1


class FitChefFieldAssuranceRecordV1(BaseModel):
    """Negative-only field assurance for one Distortion Simulator output field."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    field_path: FitChefDistortionFieldPath
    claim_type: ClaimType
    evidence_mode: EvidenceMode
    adjudicated_support_status: None = None
    assurance_state: FitChefFieldAssuranceState
    candidate_source_refs: tuple[str, ...] = ()
    conflict_adjudicated: Literal[False] = False
    reason_codes: tuple[FitChefFieldAssuranceReasonCode, ...]

    @field_validator("adjudicated_support_status", mode="before")
    @classmethod
    def _require_null_support_status(cls, value: object) -> object:
        if value is not None:
            raise ValueError("adjudicated_support_status is null-only in v1")
        return value

    @field_validator("conflict_adjudicated", mode="before")
    @classmethod
    def _require_exact_false_conflict(cls, value: object) -> object:
        if value is not False:
            raise ValueError("conflict_adjudicated must be exactly false in v1")
        return value

    @field_validator("candidate_source_refs")
    @classmethod
    def _validate_candidate_source_refs(cls, refs: tuple[str, ...]) -> tuple[str, ...]:
        if len(set(refs)) != len(refs):
            raise ValueError("candidate_source_refs must be unique occurrence refs")
        for ref in refs:
            if (
                not ref.startswith(_OPAQUE_SHA256_PREFIX)
                or len(ref) != len(_OPAQUE_SHA256_PREFIX) + 64
                or any(char not in "0123456789abcdef" for char in ref[len(_OPAQUE_SHA256_PREFIX) :])
            ):
                raise ValueError("candidate_source_refs must be opaque sha256 fingerprints")
        return refs

    @model_validator(mode="after")
    def _validate_surface_policy(self) -> "FitChefFieldAssuranceRecordV1":
        if self.field_path in _FITCHEF_DISTORTION_FIELD_ORDER[:4]:
            if self.claim_type != "inference" or self.evidence_mode != "heuristic":
                raise ValueError("request-context fields require inference/heuristic metadata")
            allowed_states = {"request_context_only", "assessment_unavailable"}
        elif self.field_path == "balanced_reframe":
            if self.claim_type != "recommendation" or self.evidence_mode != "none":
                raise ValueError("balanced_reframe requires recommendation/none metadata")
            allowed_states = {
                "candidate_linked_unverified",
                "evidence_link_missing",
                "source_snapshot_mismatch",
                "assessment_unavailable",
            }
        else:
            if self.claim_type != "recommendation" or self.evidence_mode != "none":
                raise ValueError("next_small_action requires recommendation/none metadata")
            allowed_states = {"not_evidence_bearing", "assessment_unavailable"}
        if self.assurance_state not in allowed_states:
            raise ValueError("assurance_state is not allowed for this field")

        expected_reasons: dict[FitChefFieldAssuranceState, tuple[tuple[str, ...], ...]] = {
            "request_context_only": (("request_context_not_source_evidence",),),
            "candidate_linked_unverified": (("candidate_sources_present_unverified",),),
            "evidence_link_missing": (("candidate_sources_missing",),),
            "not_evidence_bearing": (("not_evidence_bearing",),),
            "source_snapshot_mismatch": (
                ("source_snapshot_mismatch",),
                ("duplicate_source_identity",),
            ),
            "assessment_unavailable": (
                ("snapshot_fingerprint_unavailable",),
                ("assessment_unavailable",),
            ),
        }
        if self.reason_codes not in expected_reasons[self.assurance_state]:
            raise ValueError("reason_codes must match the exact assurance state")
        if self.candidate_source_refs:
            if self.field_path != "balanced_reframe":
                raise ValueError("only balanced_reframe may carry candidate_source_refs")
            if self.assurance_state != "candidate_linked_unverified":
                raise ValueError("candidate_source_refs require candidate_linked_unverified")
        elif self.assurance_state == "candidate_linked_unverified":
            raise ValueError("candidate_linked_unverified requires candidate_source_refs")
        return self


class FitChefDistortionFieldAssuranceAssessmentV1(BaseModel):
    """Internal negative-only six-field assurance for the Distortion Simulator."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["fitchef_distortion_field_assurance.v1"] = (
        "fitchef_distortion_field_assurance.v1"
    )
    surface: Literal["distortion_simulator"] = "distortion_simulator"
    field_policy_version: Literal["distortion_fields.v1"] = "distortion_fields.v1"
    source_snapshot_fingerprint: str | None
    records: tuple[FitChefFieldAssuranceRecordV1, ...]
    assessed_field_count: Literal[6]
    request_context_only_count: int = Field(..., ge=0, le=6)
    evidence_sensitive_field_count: Literal[1]
    candidate_linked_unverified_count: int = Field(..., ge=0, le=1)
    evidence_link_missing_count: int = Field(..., ge=0, le=1)
    source_snapshot_mismatch_count: int = Field(..., ge=0, le=1)
    assessment_unavailable_count: int = Field(..., ge=0, le=6)
    support_claimed_count: Literal[0] = 0
    public_response_authority: Literal[False] = False
    provider_retry_authority: Literal[False] = False
    cache_admission_authority: Literal[False] = False
    knowledge_promotion_authority: Literal[False] = False
    plan_mutation_authority: Literal[False] = False

    @field_validator("source_snapshot_fingerprint")
    @classmethod
    def _validate_snapshot_fingerprint(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if (
            not value.startswith(_OPAQUE_SHA256_PREFIX)
            or len(value) != len(_OPAQUE_SHA256_PREFIX) + 64
            or any(char not in "0123456789abcdef" for char in value[len(_OPAQUE_SHA256_PREFIX) :])
        ):
            raise ValueError("source_snapshot_fingerprint must be an opaque sha256 fingerprint")
        return value

    @field_validator(
        "assessed_field_count",
        "request_context_only_count",
        "evidence_sensitive_field_count",
        "candidate_linked_unverified_count",
        "evidence_link_missing_count",
        "source_snapshot_mismatch_count",
        "assessment_unavailable_count",
        "support_claimed_count",
        mode="before",
    )
    @classmethod
    def _require_builtin_counts(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("assurance counts must be built-in integers")
        return value

    @field_validator(
        "public_response_authority",
        "provider_retry_authority",
        "cache_admission_authority",
        "knowledge_promotion_authority",
        "plan_mutation_authority",
        mode="before",
    )
    @classmethod
    def _require_exact_false_authority(cls, value: object) -> object:
        if value is not False:
            raise ValueError("v1 authority flags must be exactly false")
        return value

    @model_validator(mode="after")
    def _validate_exact_records_and_counts(
        self,
    ) -> "FitChefDistortionFieldAssuranceAssessmentV1":
        if tuple(record.field_path for record in self.records) != _FITCHEF_DISTORTION_FIELD_ORDER:
            raise ValueError("records must contain the exact six-field order")

        expected_counts = {
            "request_context_only_count": sum(
                record.assurance_state == "request_context_only" for record in self.records
            ),
            "candidate_linked_unverified_count": sum(
                record.assurance_state == "candidate_linked_unverified" for record in self.records
            ),
            "evidence_link_missing_count": sum(
                record.assurance_state == "evidence_link_missing" for record in self.records
            ),
            "source_snapshot_mismatch_count": sum(
                record.assurance_state == "source_snapshot_mismatch" for record in self.records
            ),
            "assessment_unavailable_count": sum(
                record.assurance_state == "assessment_unavailable" for record in self.records
            ),
        }
        for field_name, expected_count in expected_counts.items():
            if getattr(self, field_name) != expected_count:
                raise ValueError(f"{field_name} must equal the exact state count")

        if self.assessment_unavailable_count not in {0, len(self.records)}:
            raise ValueError("assessment_unavailable must apply to all six records or none")
        unavailable = self.assessment_unavailable_count == len(self.records)
        if unavailable and len({record.reason_codes for record in self.records}) != 1:
            raise ValueError("all unavailable records must use one exact shared reason")
        if unavailable != (self.source_snapshot_fingerprint is None):
            raise ValueError(
                "only a fully unavailable assessment may omit the snapshot fingerprint"
            )
        return self


class FitChefCoachInsightResult(BaseModel):
    """Internal coach-insight result. / Внутренний результат coach-insight."""

    insight: str
    rag_used: bool
    sources: list[FitChefSourceItem]
    confidence: float
    uncertainty: float = Field(..., ge=0.0, le=1.0)
    warnings: list[str]
    mode: FitChefExecutionMode
    quota_state: FitChefQuotaState
    automated_analysis: bool
    transparency_notice_id: str
    wellness_boundary: str


class FitChefDistortionSimulatorResult(BaseModel):
    """Internal structured result for distortion simulator."""

    scenario: Literal["distortion_simulator"] = "distortion_simulator"
    distortion_labels: list[str]
    why_it_matches: str
    evidence_for: list[str]
    evidence_against: list[str]
    balanced_reframe: str
    next_small_action: str
    claim_evidence_assessment: FitChefDistortionFieldAssuranceAssessmentV1 = Field(exclude=True)
    sources: list[FitChefSourceItem]
    confidence: float
    warnings: list[str]
    mode: FitChefExecutionMode
    quota_state: FitChefQuotaState
    transparency_notice_id: str
    wellness_boundary: str


class FitChefIdentityLoopValue(BaseModel):
    """Structured identity-loop block."""

    belief: str
    behavior: str
    short_term_reward: str
    long_term_cost: str


class FitChefIdentityLoopMapperResult(BaseModel):
    """Internal structured result for identity-loop mapper."""

    scenario: Literal["identity_loop_mapper"] = "identity_loop_mapper"
    identity_loop: FitChefIdentityLoopValue
    identity_shift_statement: str
    replacement_action: str
    repair_if_slip: str
    sources: list[FitChefSourceItem]
    confidence: float
    warnings: list[str]
    mode: FitChefExecutionMode
    quota_state: FitChefQuotaState
    transparency_notice_id: str
    wellness_boundary: str


class FitChefMascotInsightResult(BaseModel):
    """Internal mascot-insight result. / Внутренний результат mascot-insight."""

    message: str
    scenario: Literal["mascot_insight"] = "mascot_insight"
    sources: list[FitChefSourceItem]
    confidence: float
    warnings: list[str]
    action_items: list[str]
    mode: FitChefExecutionMode
    quota_state: FitChefQuotaState
    transparency_notice_id: str
    wellness_boundary: str


class FitChefWeeklyReflectionResult(BaseModel):
    """Internal weekly-reflection result. / Внутренний результат weekly-reflection."""

    message: str
    scenario: Literal["weekly_reflection"] = "weekly_reflection"
    sources: list[FitChefSourceItem]
    confidence: float
    warnings: list[str]
    action_items: list[str]
    mode: FitChefExecutionMode
    quota_state: FitChefQuotaState
    transparency_notice_id: str
    wellness_boundary: str
    response_state: FitChefWeeklyReflectionResponseState = "generated"
    clarification: FitChefClarificationV1 | None = None


class FitChefSlipSupportResult(BaseModel):
    """Internal slip-support result. / Внутренний результат slip-support."""

    message: str
    scenario: Literal["slip_support"] = "slip_support"
    sources: list[FitChefSourceItem]
    confidence: float
    warnings: list[str]
    action_items: list[str]
    mode: FitChefExecutionMode
    quota_state: FitChefQuotaState
    transparency_notice_id: str
    wellness_boundary: str


class FitChefWeeklyPlanResult(BaseModel):
    """Internal weekly-plan result. / Внутренний результат weekly-plan."""

    menu: dict[str, Any]


class FitChefShoppingFollowupInput(BaseModel):
    """Internal shopping-followup input. / Входные данные shopping-followup задачи."""

    weekly_plan_id: str | None = None
    plan_data: dict[str, Any] | None = None
    preferences: ShoppingListPreferences = Field(default_factory=ShoppingListPreferences)


class FitChefShoppingFollowupTaskEnvelope(FitChefTaskEnvelope):
    """Shopping-followup task envelope. / Envelope для shopping-followup."""

    task_type: Literal["shopping_followup"] = "shopping_followup"
    input: FitChefShoppingFollowupInput


class FitChefShoppingFollowupResult(BaseModel):
    """Internal shopping-followup result. / Внутренний результат shopping-followup."""

    shopping_list: ShoppingListDTO
