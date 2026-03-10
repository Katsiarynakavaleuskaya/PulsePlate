"""Internal FitChef runtime contracts. / Внутренние контракты runtime FitChef."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.shopping_list import ShoppingListDTO, ShoppingListPreferences

FitChefAgentId = Literal["fitchef-agent"]
FitChefExecutionMode = Literal["auto-safe", "review-required", "blocked"]
FitChefTaskType = Literal["coach_insight", "weekly_plan", "shopping_followup", "mascot_insight"]
FitChefQuotaState = Literal["not_consumed", "consumed"]


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
