from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from tiny_agent_harness.schemas.agents.explore import ExploreOutput
from tiny_agent_harness.schemas.agents.planner import PlannerOutput
from tiny_agent_harness.schemas.agents.verifier import VerifierOutput
from tiny_agent_harness.schemas.agents.worker import WorkerOutput


class SubAgentCall(BaseModel):
    """Instruction from the supervisor to invoke a subagent."""

    model_config = ConfigDict(extra="forbid")

    agent: Literal["planner", "explorer", "worker", "verifier"]
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
    explore_outputs: list[ExploreOutput] = Field(default_factory=list)
    worker_outputs: list[WorkerOutput] = Field(default_factory=list)
    verifier_outputs: list[VerifierOutput] = Field(default_factory=list)
