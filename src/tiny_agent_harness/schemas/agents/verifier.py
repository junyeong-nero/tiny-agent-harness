from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from tiny_agent_harness.schemas.tools import ToolInput
from tiny_agent_harness.schemas.agents.worker import WorkerInput, WorkerOutput


class VerifierInput(BaseModel):
    """All context passed into the verifier agent."""

    model_config = ConfigDict(extra="forbid")
    task: str


class VerifierOutput(BaseModel):
    """Final decision returned by the verifier agent."""

    model_config = ConfigDict(extra="forbid")
    task: str
    tool_call: ToolInput | None = None
    status: Literal["completed", "failed"]

    decision: Literal["approve", "retry"]
    feedback: str
