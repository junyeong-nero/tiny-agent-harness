from typing import Literal

from pydantic import BaseModel, ConfigDict

from tiny_agent_harness.schemas.agents import (
    PlannerOutput,
    PlannerStep,
    RunRequest,
    RunResult,
    RunState,
    ReviewerOutput,
    WorkerInput,
    WorkerOutput,
)


class InputRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message_id: str
    session_id: str = "default"
    kind: Literal["run_request"] = "run_request"
    payload: RunRequest


class RunOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request: RunRequest
    state: RunState
    result: RunResult
    planner_result: PlannerOutput | None = None
    worker_result: WorkerOutput | None = None
    review_result: ReviewerOutput | None = None
    done: bool = False

    @property
    def plan(self) -> list[PlannerStep]:
        if self.planner_result is None:
            return []
        return list(self.planner_result.plan)

    @property
    def reply(self) -> str | None:
        if self.planner_result is None:
            return None
        return self.planner_result.reply

    @property
    def task(self) -> WorkerInput | None:
        if self.planner_result is None:
            return None
        return self.planner_result.task


class OutputEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str
    session_id: str
    kind: Literal["run_result"] = "run_result"
    payload: RunOutput
