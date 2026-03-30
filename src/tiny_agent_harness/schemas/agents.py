from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tiny_agent_harness.schemas.tools import ToolInput


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: str


class RunResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["completed", "needs_retry"]
    summary: str


class WorkerTask(BaseModel):
    """Task definition passed from planner to worker."""

    model_config = ConfigDict(extra="forbid")

    id: str
    kind: Literal["explore", "implement", "verify"] = "implement"
    instructions: str
    context: str
    allowed_tools: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)


class PlannerStep(BaseModel):
    """Structured LLM output during planner's internal loop."""

    model_config = ConfigDict(extra="forbid")

    status: Literal[
        "tool_call",
        "delegate",
        "delegate_explorer",
        "delegate_worker",
        "reply",
        "complete_plan",
    ]
    summary: str
    tool_call: ToolInput | None = None
    subtasks: list[WorkerTask] = Field(default_factory=list)
    task: WorkerTask | None = None

    @model_validator(mode="after")
    def normalize_subtasks(self) -> "PlannerStep":
        if self.task is not None and not self.subtasks:
            self.subtasks = [self.task]
        if self.task is None and self.subtasks:
            self.task = self.subtasks[0]
        return self


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
    changed_files: list[str] = Field(default_factory=list)
    test_results: list[str] = Field(default_factory=list)


class ReviewerInput(BaseModel):
    """All context passed into the reviewer agent."""

    model_config = ConfigDict(extra="forbid")

    original_prompt: str
    reply: str | None = None
    task: WorkerTask | None = None
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
    current_task: WorkerTask | None = None
    last_worker_result: WorkerOutput | None = None
    last_review_result: ReviewerOutput | None = None
    plan: list[PlannerStep] = Field(default_factory=list)
    completed_subtasks: list[WorkerTask] = Field(default_factory=list)
    exploration_notes: list[str] = Field(default_factory=list)
    worker_results: list[WorkerOutput] = Field(default_factory=list)
    review_cycles: int = 0
    done: bool = False


class PlannerOutput(BaseModel):
    """Result returned by the planner agent (task + worker result, or a direct reply)."""

    model_config = ConfigDict(extra="forbid")

    plan: list[PlannerStep] = Field(default_factory=list)
    task: WorkerTask | None = None
    worker_result: WorkerOutput | None = None
    reply: str | None = None


class OrchestrationResult(BaseModel):
    """Full pipeline result stored after each run cycle."""

    model_config = ConfigDict(extra="forbid")

    plan: list[PlannerStep] = Field(default_factory=list)
    reply: str | None = None
    task: WorkerTask | None = None
    worker_result: WorkerOutput | None = None
    review_result: ReviewerOutput
    done: bool


# Backward-compatible aliases for older imports.
Subtask = WorkerTask
WorkerInput = WorkerTask
ExecutorInput = WorkerInput
ExecutorStep = WorkerStep
ExecutorOutput = WorkerOutput
PlanStep = PlannerStep
OrchestratorStep = PlannerStep
OrchestratorOutput = PlannerOutput
