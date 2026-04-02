from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from tiny_agent_harness.schemas.tools import ToolInput


class ExploreInput(BaseModel):
    """Task definition for the explore agent."""

    model_config = ConfigDict(extra="forbid")

    task: str


class ExploreOutput(BaseModel):
    """Context gathered by the explore agent."""

    model_config = ConfigDict(extra="forbid")

    task: str

    tool_call: ToolInput | None = None
    status: Literal["completed", "failed"]

    findings: str
    sources: list[str] = Field(default_factory=list)
