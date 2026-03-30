from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from tiny_agent_harness.schemas.tools import ToolInput
from tiny_agent_harness.schemas.agents.worker import WorkerInput, WorkerOutput


class ReviewerInput(BaseModel):
    """All context passed into the reviewer agent."""

    model_config = ConfigDict(extra="forbid")
    task: str


class ReviewerOutput(BaseModel):
    """Final decision returned by the reviewer agent."""

    model_config = ConfigDict(extra="forbid")
    task: str
    tool_call: ToolInput | None = None
    status: Literal["completed", "failed"]

    decision: Literal["approve", "retry"]
    feedback: str
