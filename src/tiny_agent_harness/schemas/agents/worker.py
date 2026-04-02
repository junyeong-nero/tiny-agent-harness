from pydantic import BaseModel, ConfigDict, Field
from typing import Literal
from tiny_agent_harness.schemas.tools import ToolInput


class WorkerInput(BaseModel):
    """Task definition passed from planner to worker."""

    model_config = ConfigDict(extra="forbid")

    task: str
    kind: Literal["implement", "verify"] = "implement"


class WorkerOutput(BaseModel):
    """Final result returned by the worker agent."""

    model_config = ConfigDict(extra="forbid")

    task: str
    kind: Literal["implement", "verify"] = "implement"

    tool_call: ToolInput | None = None
    status: Literal["completed", "failed"]

    summary: str
    artifacts: list[str] = Field(default_factory=list)
    changed_files: list[str] = Field(default_factory=list)
    test_results: list[str] = Field(default_factory=list)
