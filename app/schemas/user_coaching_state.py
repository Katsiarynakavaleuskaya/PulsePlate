# -*- coding: utf-8 -*-
"""
UserCoachingState — единый snapshot состояния пользователя для CBT-коучинга и
нутрициологической персонализации в PulsePlate.

RU: Собирает все персистентные поля из существующих контрактов (bmi.py, bmr.py,
    bayes_adherence.py, nutrition_log.py, nutrition_recommendations.py,
    fitchef_coaching.py) в один неизменяемый объект, который передаётся в
    промпт FitChef-агента вместо повторного сбора данных per-request.

EN: Aggregates persistent user fields from existing contracts into a single
    immutable snapshot injected into the FitChef-agent prompt, eliminating
    stateless per-request reconstruction.

Architecture note:
    - This schema is READ-ONLY at runtime: it is assembled by UserCoachingStateBuilder
      (service layer) and passed downstream to FitChef task envelopes as context.
    - It is NOT persisted as a single table — each sub-block corresponds to its
      canonical source of truth in the DB (AdherenceRecord, NutritionEvent, etc.).
    - Markov-like property: the next FitChef response depends ONLY on this snapshot
      plus the current request, not on raw event history.

IMPORTANT:
    - No medical claims. Wellness-only scope.
    - All fields are Optional unless they are guaranteed by onboarding flow.
    - feature_flags gate must be checked before injecting into LLM prompt.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

# ---------------------------------------------------------------------------
# Shared type aliases (mirror existing contracts)
# ---------------------------------------------------------------------------

BmiGroup = Literal[
    "general", "athlete", "elderly", "child", "teen", "too_young", "pregnant"
]

GoalDirection = Literal["maintain", "reduce", "increase", "medical_review"]

ActivityLevel = Literal[
    "sedentary", "light", "moderate", "active", "very_active"
]  # matches bmr.py BMRRequest.activity pattern

NutritionGoal = Literal["loss", "maintain", "gain"]  # matches ProfileInput.goal

AgeBand = Literal[
    "too_young", "child", "teen", "adult", "elderly"
]  # mirrors BMICalculateResponse.age_band

RiskLevel = Literal["low", "moderate", "high"]  # mirrors bmi.py WaistRiskResultSchema

FitChefScenario = Literal[
    "mascot_insight",
    "weekly_reflection",
    "slip_support",
    "distortion_simulator",
    "identity_loop_mapper",
]  # mirrors FitChefTaskType in fitchef.py

AdherenceEventTypeAlias = Literal[
    "meal_logged", "slip"
]  # mirrors bayes_adherence.py AdherenceEventType

LifeStage = Literal[
    "adult", "pregnant", "lactating", "elderly"
]  # mirrors ProfileInput.life_stage

# ---------------------------------------------------------------------------
# Sub-block 1: Биометрия — источник: BMI/BMR endpoints
# ---------------------------------------------------------------------------


class BiometricStateBlock(BaseModel):
    """
    RU: Текущий биометрический снимок пользователя.
        Сборка из BMICalculateResponse + BMRResponse.
    EN: Current biometric snapshot assembled from BMI/BMR response fields.

    Source contracts: app/schemas/bmi.py, app/schemas/bmr.py
    """

    model_config = ConfigDict(frozen=True)

    bmi: float | None = Field(
        default=None,
        ge=5.0,
        le=80.0,
        description=(
            "Last calculated BMI. "
            "None if not yet computed or age_band in (too_young, child, teen, pregnant)."
        ),
        examples=[22.5, 27.1, None],
    )
    bmi_group: BmiGroup | None = Field(
        default=None,
        description=(
            "BMI group from auto_group(). "
            "Determines which coaching track FitChef activates. "
            "Mirrors BMICalculateResponse.group."
        ),
        examples=["general", "athlete", "pregnant"],
    )
    age_band: AgeBand | None = Field(
        default=None,
        description="Age band for UI/coaching differentiation. Mirrors BMICalculateResponse.age_band.",
        examples=["adult", "elderly"],
    )
    goal_direction: GoalDirection | None = Field(
        default=None,
        description=(
            "BMI-derived goal direction from interpretation_v1.goal_direction. "
            "Used by FitChef to frame coaching tone: reduce vs maintain vs increase."
        ),
        examples=["maintain", "reduce"],
    )
    weight_kg: float | None = Field(
        default=None,
        gt=0,
        description="Last known body weight in kg.",
        examples=[72.5, 85.0],
    )
    height_cm: float | None = Field(
        default=None,
        gt=0,
        description="Height in cm.",
        examples=[170.0, 182.5],
    )
    waist_risk_level: RiskLevel | None = Field(
        default=None,
        description=(
            "Waist risk level from WaistRiskResultSchema.risk_level. "
            "Present only if waist_cm was provided at BMI calculation."
        ),
        examples=["low", "moderate"],
    )
    wht_ratio: float | None = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="Waist-to-Height Ratio if waist_cm was provided.",
        examples=[0.47, 0.54],
    )
    bodyfat_pct: float | None = Field(
        default=None,
        ge=3.0,
        le=60.0,
        description="Body fat % (optional, from ProfileInput.bodyfat or manual entry).",
        examples=[18.0, 25.5],
    )
    is_pregnant: bool = Field(
        default=False,
        description=(
            "Pregnancy status — gates coaching tone and wellness boundary checks. "
            "When True, FitChef MUST add prenatal wellness disclaimer."
        ),
    )
    is_athlete: bool = Field(
        default=False,
        description="Athlete flag — adjusts BMI interpretation and coaching register.",
    )
    bmi_computed_at: datetime | None = Field(
        default=None,
        description="UTC timestamp of last BMI calculation. Used for staleness check.",
    )

    @model_validator(mode="after")
    def _validate_pregnancy_group_consistency(self) -> "BiometricStateBlock":
        """
        RU: Если is_pregnant=True, bmi_group должен быть 'pregnant' или None.
        EN: When is_pregnant=True, bmi_group must be 'pregnant' or None (never 'general').
        """
        if self.is_pregnant and self.bmi_group not in (None, "pregnant"):
            raise ValueError(
                f"is_pregnant=True but bmi_group='{self.bmi_group}'. "
                "Expected bmi_group='pregnant' or None."
            )
        return self


# ---------------------------------------------------------------------------
# Sub-block 2: Нутрициологические цели — источник: nutrition_recommendations.py
# ---------------------------------------------------------------------------


class NutritionTargetsBlock(BaseModel):
    """
    RU: Персонализированные нутрициологические цели.
        Источник: NutrientRecommendationsResponse + ProfileInput.
    EN: Personalized nutrition targets assembled from recommendation endpoints.

    Source contracts: app/schemas/nutrition_recommendations.py
    """

    model_config = ConfigDict(frozen=True)

    kcal_daily: int | None = Field(
        default=None,
        ge=500,
        le=10000,
        description="Target daily calories (kcal). From NutrientRecommendationsResponse.kcal_daily.",
        examples=[2100, 1800],
    )
    protein_g: int | None = Field(
        default=None,
        ge=0,
        description="Daily protein target (g). From macros dict.",
        examples=[150, 120],
    )
    fat_g: int | None = Field(
        default=None,
        ge=0,
        description="Daily fat target (g). From macros dict.",
        examples=[70, 60],
    )
    carbs_g: int | None = Field(
        default=None,
        ge=0,
        description="Daily carbs target (g). From macros dict.",
        examples=[250, 200],
    )
    fiber_g: int | None = Field(
        default=None,
        ge=0,
        description="Daily fiber target (g). From macros dict.",
        examples=[30, 25],
    )
    water_ml_daily: int | None = Field(
        default=None,
        ge=0,
        description="Daily water intake target (ml).",
        examples=[2500, 2000],
    )
    activity_level: ActivityLevel | None = Field(
        default=None,
        description=(
            "Physical activity level from BMRRequest.activity. "
            "Used by FitChef to calibrate intensity of exercise coaching."
        ),
        examples=["moderate", "active"],
    )
    nutrition_goal: NutritionGoal | None = Field(
        default=None,
        description="Explicit nutrition goal (loss/maintain/gain). From ProfileInput.goal.",
        examples=["maintain", "loss"],
    )
    life_stage: LifeStage | None = Field(
        default=None,
        description=(
            "Life stage for adjusted targets. "
            "Mirrors ProfileInput.life_stage. "
            "FitChef uses this for safe-messaging boundaries."
        ),
        examples=["adult", "pregnant"],
    )
    diet_flags: list[str] = Field(
        default_factory=list,
        description=(
            "Active dietary flags: VEG, GF, DAIRY_FREE, LOW_COST, etc. "
            "From ProfileInput.diet_flags. "
            "FitChef uses these to filter food recommendations."
        ),
        examples=[["VEG", "GF"], []],
    )
    deficit_pct: float | None = Field(
        default=None,
        ge=5.0,
        le=25.0,
        description="Active calorie deficit % for weight loss. From ProfileInput.deficit_pct.",
        examples=[15.0, 10.0],
    )
    surplus_pct: float | None = Field(
        default=None,
        ge=5.0,
        le=20.0,
        description="Active calorie surplus % for weight gain. From ProfileInput.surplus_pct.",
        examples=[10.0, None],
    )
    overall_nutrition_score: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description=(
            "Last coverage score from NutrientCoverageSummary.overall_score. "
            "FitChef uses this to assess coaching urgency."
        ),
        examples=[72.5, 55.0],
    )
    deficient_nutrients: list[str] = Field(
        default_factory=list,
        description=(
            "Nutrient names with deficient coverage status from last NutrientCoverageResponse. "
            "Directly informs FitChef food-based deficiency coaching."
        ),
        examples=[["iron", "vitamin_d"], []],
    )


# ---------------------------------------------------------------------------
# Sub-block 3: Adherence / Байес — источник: bayes_adherence.py, nutrition_log.py
# ---------------------------------------------------------------------------


class AdherenceBayesBlock(BaseModel):
    """
    RU: Байесовский prior/posterior пользователя по соблюдению плана питания.
        Источник: AdherenceResponse из bayes_adherence.py.

    EN: Bayesian adherence prior assembled from AdherenceResponse.
        This is the Markov-property core: FitChef's next response depends on
        current (alpha, beta, n) — not on raw event history.

    Source contracts: app/schemas/bayes_adherence.py, app/schemas/nutrition_log.py
    """

    model_config = ConfigDict(frozen=True)

    alpha: float = Field(
        default=1.0,
        gt=0.0,
        description=(
            "Beta distribution alpha (successes + prior). "
            "From AdherenceResponse.alpha. "
            "Higher = better adherence history."
        ),
        examples=[5.0, 12.0],
    )
    beta: float = Field(
        default=1.0,
        gt=0.0,
        description=(
            "Beta distribution beta (failures + prior). "
            "From AdherenceResponse.beta. "
            "Higher = more slips recorded."
        ),
        examples=[2.0, 8.0],
    )
    n: int = Field(
        default=0,
        ge=0,
        description="Total events observed. From AdherenceResponse.n.",
        examples=[14, 30],
    )
    risk_slip: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description=(
            "Current posterior slip probability. "
            "From AdherenceResponse.risk_slip. "
            "FitChef uses this to decide whether to trigger slip_support proactively."
        ),
        examples=[0.15, 0.45],
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description=(
            "Model confidence. From AdherenceResponse.confidence. "
            "When low, FitChef should avoid high-confidence coaching assertions."
        ),
        examples=[0.82, 0.45],
    )
    needs_more_data: bool = Field(
        default=True,
        description=(
            "Whether the Bayesian model needs more observations. "
            "From AdherenceResponse.needs_more_data. "
            "When True, FitChef frames coaching as exploratory, not prescriptive."
        ),
    )
    analyzer_key: str = Field(
        default="v1:adherence",
        min_length=3,
        max_length=64,
        description="Analyzer version key from AdherenceEventRequest.analyzer_key.",
    )
    recent_slip_count_7d: int = Field(
        default=0,
        ge=0,
        description=(
            "Count of 'slip' events in last 7 days from NutritionEvent table. "
            "Rolling window for recency-aware coaching. "
            "Computed at state assembly time, not from Bayesian model directly."
        ),
        examples=[0, 2, 5],
    )
    last_meal_logged_at: datetime | None = Field(
        default=None,
        description=(
            "UTC timestamp of last 'meal_logged' event from NutritionEvent. "
            "Engagement signal: if >48h ago, FitChef can offer re-engagement nudge."
        ),
    )
    last_day_closed_at: date | None = Field(
        default=None,
        description=(
            "Last date where day_close event was recorded. "
            "Consistency signal for weekly reflection scenario."
        ),
        examples=["2026-06-04"],
    )
    streak_days: int = Field(
        default=0,
        ge=0,
        description=(
            "Consecutive days with at least one meal_logged or day_close event. "
            "Computed at state assembly. Used by FitChef for streak-based motivation."
        ),
        examples=[0, 7, 14],
    )


# ---------------------------------------------------------------------------
# Sub-block 4: CBT-контекст — источник: fitchef_coaching.py
# ---------------------------------------------------------------------------


class CbtSessionBlock(BaseModel):
    """
    RU: Накопленный CBT-контекст из предыдущих сессий FitChef.
        Источник: результаты FitChefDistortionSimulatorResult,
                  FitChefIdentityLoopMapperResult, FitChefSlipSupportResult.

    EN: Accumulated CBT context from previous FitChef sessions.
        This is the minimal session memory that enables continuity across
        distortion_simulator → identity_loop_mapper → slip_support flows.

    Source contracts: app/schemas/fitchef.py, app/schemas/fitchef_coaching.py

    WARNING: These fields are wellness-only. They MUST NOT be interpreted as
             clinical diagnoses or used to make medical claims.
    """

    model_config = ConfigDict(frozen=True)

    last_scenario: FitChefScenario | None = Field(
        default=None,
        description=(
            "Last FitChef scenario executed. "
            "Enables scenario sequencing: e.g., after distortion_simulator → suggest identity_loop_mapper."
        ),
        examples=["slip_support", "distortion_simulator"],
    )
    last_scenario_at: datetime | None = Field(
        default=None,
        description="UTC timestamp of last FitChef scenario execution.",
    )
    active_goal: str | None = Field(
        default=None,
        max_length=200,
        description=(
            "Current user-stated goal extracted from last coaching request. "
            "Propagated from FitChefSlipSupportRequest.goal or FitChefWeeklyReflectionRequest.goal. "
            "FitChef uses this to maintain goal continuity across sessions."
        ),
        examples=["Eat less processed food", "Build consistent breakfast habit"],
    )
    active_distortions: list[str] = Field(
        default_factory=list,
        max_length=10,
        description=(
            "CBT distortion labels identified in last distortion_simulator result. "
            "From FitChefDistortionSimulatorResult.distortion_labels. "
            "FitChef references these in subsequent sessions for continuity."
        ),
        examples=[["all_or_nothing", "catastrophizing"], []],
    )
    identity_belief: str | None = Field(
        default=None,
        max_length=500,
        description=(
            "Core belief from last FitChefIdentityLoopValue.belief. "
            "FitChef uses this to avoid repeating identity-loop analysis from scratch."
        ),
        examples=["I always fail at diets"],
    )
    identity_shift_statement: str | None = Field(
        default=None,
        max_length=500,
        description=(
            "Last identity_shift_statement from FitChefIdentityLoopMapperResult. "
            "Injected into mascot_insight prompt for continuity."
        ),
    )
    recent_slip_events: list[str] = Field(
        default_factory=list,
        max_length=5,
        description=(
            "Last N slip event_text values from FitChefSlipSupportRequest (max 5). "
            "Used to detect recurring slip patterns for proactive coaching."
        ),
        examples=[["Ate chips late at night", "Skipped lunch and binged at dinner"], []],
    )
    slip_repair_action: str | None = Field(
        default=None,
        max_length=500,
        description=(
            "Last repair_if_slip from FitChefIdentityLoopMapperResult. "
            "FitChef references this in slip_support scenarios for consistency."
        ),
    )
    weekly_reflection_summary: str | None = Field(
        default=None,
        max_length=500,
        description=(
            "Last summary field from FitChefWeeklyReflectionRequest. "
            "Used in mascot_insight to acknowledge recent progress."
        ),
    )
    total_sessions: int = Field(
        default=0,
        ge=0,
        description=(
            "Total FitChef coaching sessions completed. "
            "Tier-aware: informs quota_state logic and VIP upsell triggers."
        ),
        examples=[0, 5, 23],
    )


# ---------------------------------------------------------------------------
# Sub-block 5: Квота и tier — источник: fitchef.py, subscriptions
# ---------------------------------------------------------------------------


class QuotaAndTierBlock(BaseModel):
    """
    RU: Текущее состояние квоты LLM и тир подписки.
        Источник: LLMQuotaUsage model, subscriptions.py.

    EN: Current LLM quota state and subscription tier.

    Source contracts: app/models/llm_quota_usage.py, app/models/subscriptions.py

    Note: This block gates FitChef scenario availability at prompt-assembly time,
          before the LLM is called. tier='FREE' limits available scenarios.
    """

    model_config = ConfigDict(frozen=True)

    tier: Literal["FREE", "PRO", "VIP"] = Field(
        default="FREE",
        description="Active subscription tier. Controls which FitChef scenarios are available.",
    )
    quota_remaining: int | None = Field(
        default=None,
        ge=0,
        description=(
            "Remaining LLM quota calls for current billing period. "
            "None = unlimited (VIP). "
            "FitChef checks this before constructing task envelope."
        ),
        examples=[3, 10, None],
    )
    quota_state: Literal["not_consumed", "consumed"] | None = Field(
        default=None,
        description=(
            "Last quota transaction state from FitChefCoachingResponseBase.quota_state. "
            "Cached to avoid redundant quota checks within same session."
        ),
    )
    available_scenarios: list[FitChefScenario] = Field(
        default_factory=list,
        description=(
            "FitChef scenarios available at current tier. "
            "Computed at state assembly, not at LLM call time. "
            "FREE: [mascot_insight]. PRO: all except VIP-only. VIP: all."
        ),
        examples=[
            ["mascot_insight"],
            [
                "mascot_insight",
                "weekly_reflection",
                "slip_support",
                "distortion_simulator",
                "identity_loop_mapper",
            ],
        ],
    )


# ---------------------------------------------------------------------------
# Root: UserCoachingState
# ---------------------------------------------------------------------------


class UserCoachingState(BaseModel):
    """
    RU: Единый immutable snapshot состояния пользователя для FitChef-агента.

        Реализует «марковское свойство» на уровне приложения:
        FitChef-промпт зависит ТОЛЬКО от этого объекта + текущего запроса,
        а не от сырой истории событий.

        Собирается сервисом UserCoachingStateBuilder из:
        - BMI endpoint results        → biometrics
        - Nutrition endpoints results → nutrition_targets
        - AdherenceResponse + events  → adherence
        - FitChef session results     → cbt_session
        - Subscription/quota models   → quota_and_tier

        Передаётся в FitChefTaskEnvelope.context (новое поле).

    EN: Single immutable coaching state snapshot for FitChef agent.

        Assembles Markov-like "current state" from existing contracts.
        FitChef response = f(UserCoachingState, current_request) — no raw history needed.

    Architecture invariants:
        - FROZEN: no mutation after construction.
        - NO direct DB access: assembled by service layer only.
        - NO medical claims: wellness-only scope enforced by wellness_boundary string.
        - feature_flag='coaching_state_v1' must be True to inject into LLM prompt.
        - All sub-blocks are optional: partial state is valid (onboarding may be incomplete).

    BACKLOG note:
        This schema is speculative/experimental until promoted through repo-reviewed
        contract + AGENTS.md update. Do not treat as production truth until merged.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Identity
    user_id: int = Field(
        ...,
        description="Internal user ID. Derived from authenticated API key, never from payload.",
        examples=[42, 1001],
    )
    state_version: Literal["v1"] = Field(
        default="v1",
        description="State schema version for forward compatibility.",
    )
    assembled_at: datetime = Field(
        ...,
        description="UTC timestamp when this snapshot was assembled. Used for TTL/staleness checks.",
    )
    lang: Literal["en", "ru", "es"] = Field(
        default="en",
        description="User preferred language. Mirrors Language from core.i18n.",
    )

    # Sub-blocks (all optional — partial onboarding is valid)
    biometrics: BiometricStateBlock = Field(
        default_factory=BiometricStateBlock,
        description="Biometric snapshot from BMI/BMR endpoints.",
    )
    nutrition_targets: NutritionTargetsBlock = Field(
        default_factory=NutritionTargetsBlock,
        description="Personalized nutrition targets from recommendation endpoints.",
    )
    adherence: AdherenceBayesBlock = Field(
        default_factory=AdherenceBayesBlock,
        description="Bayesian adherence state — the Markov core of coaching continuity.",
    )
    cbt_session: CbtSessionBlock = Field(
        default_factory=CbtSessionBlock,
        description="Accumulated CBT session context from previous FitChef interactions.",
    )
    quota_and_tier: QuotaAndTierBlock = Field(
        default_factory=QuotaAndTierBlock,
        description="Quota and subscription tier — gates scenario availability.",
    )

    # Derived / computed coaching signals (assembled at build time, not stored)
    coaching_urgency: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        default=0.0,
        description=(
            "Composite urgency score [0..1] for FitChef tone calibration. "
            "Derived from: risk_slip * 0.4 + recent_slip_count_7d/7 * 0.3 + "
            "(1 - overall_nutrition_score/100) * 0.3. "
            "High urgency → empathetic, low-judgment tone. "
            "Low urgency → motivational, forward-looking tone."
        ),
        examples=[0.2, 0.65, 0.85],
    )
    wellness_boundary: str = Field(
        default=(
            "PulsePlate is a wellness planning tool, not a medical service. "
            "For medical concerns, consult a qualified healthcare professional."
        ),
        description=(
            "Injected into every FitChef prompt as the last line. "
            "Mirrors FitChefCoachingResponseBase.wellness_boundary contract."
        ),
    )
    next_recommended_scenario: FitChefScenario | None = Field(
        default=None,
        description=(
            "Backend-recommended next FitChef scenario based on state signals. "
            "Logic: "
            "  risk_slip > 0.4 → slip_support; "
            "  active_distortions not empty → distortion_simulator; "
            "  streak_days > 6 → weekly_reflection; "
            "  identity_belief is None → identity_loop_mapper; "
            "  else → mascot_insight. "
            "Client may override. This is advisory, not enforcement."
        ),
        examples=["slip_support", "mascot_insight"],
    )

    @model_validator(mode="after")
    def _compute_next_scenario(self) -> "UserCoachingState":
        """
        RU: Вычисляет next_recommended_scenario на основе текущего состояния.
            Детерминированные правила v1 — аналог NextBestAction из intervention.py.
        EN: Derives next_recommended_scenario from state signals.
            Deterministic v1 rules — mirrors NextBestAction pattern from intervention.py.
        """
        if self.next_recommended_scenario is not None:
            return self  # already set explicitly (e.g. in tests)

        available = set(self.quota_and_tier.available_scenarios)
        adh = self.adherence
        cbt = self.cbt_session

        def _pick(scenario: FitChefScenario) -> FitChefScenario | None:
            return scenario if scenario in available else None

        # Priority chain (highest to lowest)
        if adh.risk_slip > 0.4:
            candidate = _pick("slip_support")
        elif cbt.active_distortions:
            candidate = _pick("distortion_simulator")
        elif adh.streak_days >= 7:
            candidate = _pick("weekly_reflection")
        elif cbt.identity_belief is None and adh.n >= 5:
            candidate = _pick("identity_loop_mapper")
        else:
            candidate = _pick("mascot_insight")

        # Pydantic frozen model — use object.__setattr__ to bypass immutability
        # during model_validator execution (before freeze is applied).
        object.__setattr__(self, "next_recommended_scenario", candidate)
        return self

    @model_validator(mode="after")
    def _compute_coaching_urgency(self) -> "UserCoachingState":
        """
        RU: Вычисляет coaching_urgency как взвешенную сумму трёх сигналов.
        EN: Computes coaching_urgency as weighted sum of three signals.

        Formula:
            urgency = risk_slip * 0.4
                    + min(recent_slip_count_7d / 7, 1.0) * 0.3
                    + (1 - overall_nutrition_score / 100) * 0.3

        All components clamped to [0, 1] individually.
        Final result rounded to 4 decimal places.
        """
        if self.coaching_urgency != 0.0:
            return self  # already set explicitly

        slip_signal = min(self.adherence.risk_slip, 1.0) * 0.4

        slip_7d_signal = min(self.adherence.recent_slip_count_7d / 7.0, 1.0) * 0.3

        score = self.nutrition_targets.overall_nutrition_score
        nutrition_signal = (1.0 - min(score / 100.0, 1.0)) * 0.3 if score is not None else 0.15

        urgency = round(slip_signal + slip_7d_signal + nutrition_signal, 4)
        object.__setattr__(self, "coaching_urgency", max(0.0, min(urgency, 1.0)))
        return self


# ---------------------------------------------------------------------------
# Builder interface (thin service contract — NOT a Pydantic model)
# ---------------------------------------------------------------------------


class UserCoachingStateBuilderContract:
    """
    RU: Описание контракта для сервиса UserCoachingStateBuilder.
        Реализация находится в app/services/coaching_state_builder.py (to be created).
        Это — только документация интерфейса.

    EN: Interface contract for UserCoachingStateBuilder service.
        Implementation lives in app/services/coaching_state_builder.py (to be created).
        This class documents the expected interface only.

    Methods to implement:
        async def build(user_id: int, db: AsyncSession) -> UserCoachingState
            1. Query AdherenceRecord for (alpha, beta, n, risk_slip, confidence).
            2. Query NutritionEvent for recent_slip_count_7d, last_meal_logged_at,
               last_day_closed_at, streak_days.
            3. Query last BMI calculation result (from cache or plans table).
            4. Query last NutrientCoverageResponse (if stored).
            5. Query last FitChef session metadata (last_scenario, active_goal, etc.).
            6. Query subscription tier and quota usage.
            7. Assemble all sub-blocks → UserCoachingState(assembled_at=utcnow()).
            8. Cache result in Redis with TTL=300s under key user_coaching_state:{user_id}.

        Invalidation triggers:
            - On AdherenceEvent recorded.
            - On BMI recalculated.
            - On FitChef scenario completed.
            - On subscription tier change.
    """

    pass


# ---------------------------------------------------------------------------
# FitChef task envelope extension (context injection contract)
# ---------------------------------------------------------------------------


class FitChefCoachInsightInputWithState(BaseModel):
    """
    RU: Расширенный input для coach-insight задачи с инжектированным UserCoachingState.
        Заменяет FitChefCoachInsightInput при включённом feature_flag='coaching_state_v1'.

    EN: Extended coach-insight input with injected UserCoachingState.
        Replaces FitChefCoachInsightInput when feature_flag='coaching_state_v1' is active.

    Usage in router (pseudocode):
        if feature_flags.coaching_state_v1:
            state = await builder.build(user_id, db)
            input_ = FitChefCoachInsightInputWithState(
                safe_query=safe_query,
                api_key=api_key,
                endpoint=endpoint,
                method=method,
                coaching_state=state,
            )

    Source: extends FitChefCoachInsightInput from app/schemas/fitchef.py
    """

    safe_query: str = Field(..., min_length=1)
    api_key: str = Field(..., min_length=1)
    endpoint: str = Field(..., min_length=1)
    method: str = Field(..., min_length=1)
    coaching_state: UserCoachingState | None = Field(
        default=None,
        description=(
            "Full coaching state snapshot. "
            "When present, FitChef prompt builder serializes this into system prompt context. "
            "When None, FitChef falls back to stateless behavior (current v1 behavior)."
        ),
    )
