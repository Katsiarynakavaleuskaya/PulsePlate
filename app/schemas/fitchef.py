"""Internal FitChef runtime contracts. / Внутренние контракты runtime FitChef."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

FitChefAgentId = Literal["fitchef-agent"]
FitChefExecutionMode = Literal["auto-safe", "review-required", "blocked"]
FitChefTaskType = Literal["coach_insight", "weekly_plan", "shopping_followup"]
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
