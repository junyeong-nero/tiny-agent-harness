from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from tiny_agent_harness.schemas.tools import ToolInput
from tiny_agent_harness.schemas.agents.worker import WorkerInput, WorkerOutput
from tiny_agent_harness.schemas.agents.reviewer import ReviewerOutput


class Plan(BaseModel):
    task: str


class PlannerInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task: str


class PlannerOutput(BaseModel):
    """Result returned by the planner agent before supervisor executes downstream work."""

    model_config = ConfigDict(extra="forbid")

    task: str
    tool_call: ToolInput | None = None
    status: Literal["completed", "failed", "no-planning"]

    summary: str
    plans: list[Plan] = Field(default_factory=list)
