from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from tiny_agent_harness.schemas.agents.planner import PlannerOutput
from tiny_agent_harness.schemas.agents.reviewer import ReviewerOutput
from tiny_agent_harness.schemas.agents.worker import WorkerOutput


class SubAgentCall(BaseModel):
    """Instruction from the supervisor to invoke a subagent."""

    model_config = ConfigDict(extra="forbid")

    agent: Literal["planner", "worker", "reviewer"]
    task: str


class SupervisorInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task: str


class SupervisorOutput(BaseModel):
    """LLM output at each supervisor step and the final result."""

    model_config = ConfigDict(extra="forbid")

    task: str
    status: Literal["subagent_call", "completed", "failed"]
    subagent_call: SubAgentCall | None = None
    summary: str
    planner_outputs: list[PlannerOutput] = Field(default_factory=list)
    worker_outputs: list[WorkerOutput] = Field(default_factory=list)
    reviewer_outputs: list[ReviewerOutput] = Field(default_factory=list)
