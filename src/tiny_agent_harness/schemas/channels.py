from typing import Literal

from pydantic import BaseModel, ConfigDict

from tiny_agent_harness.schemas.runtime import RunRequest, RunResult, RunState


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


class OutputEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str
    session_id: str
    kind: Literal["run_result"] = "run_result"
    payload: RunOutput
