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


class WorkerInput(BaseModel):
    """Task definition passed from orchestrator to worker."""

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
    task: WorkerInput | None = None


class WorkerStep(BaseModel):
    """Structured LLM output during worker's internal loop."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["tool_call", "completed", "failed"]
    summary: str
    tool_call: ToolInput | None = None
    artifacts: list[str] = Field(default_factory=list)


class WorkerOutput(BaseModel):
    """Final result returned by the worker agent."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["completed", "failed"]
    summary: str
    artifacts: list[str] = Field(default_factory=list)


class ReviewerInput(BaseModel):
    """All context passed into the reviewer agent."""

    model_config = ConfigDict(extra="forbid")

    original_prompt: str
    reply: str | None = None
    task: WorkerInput | None = None
    worker_result: WorkerOutput | None = None


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
    current_task: WorkerInput | None = None
    last_worker_result: WorkerOutput | None = None
    last_review_result: ReviewerOutput | None = None
    done: bool = False


class OrchestratorOutput(BaseModel):
    """Result returned by the orchestrator agent (task + worker result, or a direct reply)."""

    model_config = ConfigDict(extra="forbid")

    task: WorkerInput | None = None
    worker_result: WorkerOutput | None = None
    reply: str | None = None


class OrchestrationResult(BaseModel):
    """Full pipeline result stored after each run cycle."""

    model_config = ConfigDict(extra="forbid")

    reply: str | None = None
    task: WorkerInput | None = None
    worker_result: WorkerOutput | None = None
    review_result: ReviewerOutput
    done: bool


# Backward-compatible aliases for older imports.
ExecutorInput = WorkerInput
ExecutorStep = WorkerStep
ExecutorOutput = WorkerOutput
