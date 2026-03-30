from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from tiny_agent_harness.schemas.tools import ToolInput


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: str


class RunResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["completed", "needs_retry"]
    summary: str


class ExecutorInput(BaseModel):
    """Task definition passed from orchestrator to executor."""

    model_config = ConfigDict(extra="forbid")

    id: str
    instructions: str
    context: str
    allowed_tools: list[str] = Field(default_factory=list)


class OrchestratorStep(BaseModel):
    """Structured LLM output during orchestrator's internal loop."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["tool_call", "delegate", "reply"]
    summary: str
    tool_call: ToolInput | None = None
    task: ExecutorInput | None = None


class ExecutorStep(BaseModel):
    """Structured LLM output during executor's internal loop."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["tool_call", "completed", "failed"]
    summary: str
    tool_call: ToolInput | None = None
    artifacts: list[str] = Field(default_factory=list)


class ExecutorOutput(BaseModel):
    """Final result returned by the executor agent."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["completed", "failed"]
    summary: str
    artifacts: list[str] = Field(default_factory=list)


class ReviewerInput(BaseModel):
    """All context passed into the reviewer agent."""

    model_config = ConfigDict(extra="forbid")

    original_prompt: str
    reply: str | None = None
    task: ExecutorInput | None = None
    executor_result: ExecutorOutput | None = None


class ReviewerStep(BaseModel):
    """Structured LLM output during reviewer's internal loop."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["tool_call", "completed"]
    summary: str
    tool_call: ToolInput | None = None
    decision: Literal["approve", "retry"] | None = None


class ReviewerOutput(BaseModel):
    """Final decision returned by the reviewer agent."""

    model_config = ConfigDict(extra="forbid")

    decision: Literal["approve", "retry"]
    feedback: str


class RunState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task: str
    step_count: int = 0
    current_task: ExecutorInput | None = None
    last_executor_result: ExecutorOutput | None = None
    last_review_result: ReviewerOutput | None = None
    done: bool = False


class OrchestratorOutput(BaseModel):
    """Result returned by the orchestrator agent (task + executor result, or a direct reply)."""

    model_config = ConfigDict(extra="forbid")

    task: ExecutorInput | None = None
    executor_result: ExecutorOutput | None = None
    reply: str | None = None


class OrchestrationResult(BaseModel):
    """Full pipeline result stored after each run cycle."""

    model_config = ConfigDict(extra="forbid")

    reply: str | None = None
    task: ExecutorInput | None = None
    executor_result: ExecutorOutput | None = None
    review_result: ReviewerOutput
    done: bool
