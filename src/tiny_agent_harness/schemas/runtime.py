from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from tiny_agent_harness.schemas.tools import ToolCall


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: str


class Task(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    instructions: str
    context: str
    allowed_tools: list[str] = Field(default_factory=list)


class OrchestratorStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["tool_call", "completed"]
    summary: str
    tool_call: ToolCall | None = None
    task: Task | None = None


class ExecutorStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["tool_call", "completed", "failed"]
    summary: str
    tool_call: ToolCall | None = None
    artifacts: list[str] = Field(default_factory=list)


class ExecutorResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["completed", "failed"]
    summary: str
    artifacts: list[str] = Field(default_factory=list)


class ReviewResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["approve", "retry"]
    feedback: str


class ReviewerStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["tool_call", "completed"]
    summary: str
    tool_call: ToolCall | None = None
    decision: Literal["approve", "retry"] | None = None


class RunState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task: str
    step_count: int = 0
    current_task: Task | None = None
    last_executor_result: ExecutorResult | None = None
    last_review_result: ReviewResult | None = None
    done: bool = False


class RunResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["completed", "needs_retry"]
    summary: str
