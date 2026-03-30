from typing import Literal

from pydantic import BaseModel, ConfigDict

from tiny_agent_harness.schemas.agents import (
    PlannerOutput,
    ReviewerOutput,
    WorkerInput,
    WorkerOutput,
)

from tiny_agent_harness.schemas.harness import HarnessOutput, HarnessInput


class Request(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    session_id: str = "default"
    kind: Literal["run_request"] = "run_request"


class Response(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str
    summary: str
    done: bool = False


class Event(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str
    session_id: str
    kind: Literal["run_result"] = "run_result"
    payload: Response
