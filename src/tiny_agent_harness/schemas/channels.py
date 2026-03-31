from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
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


class ListenerEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal[
        "run_started",
        "run_completed",
        "run_failed",
        "llm_request",
        "llm_response",
        "llm_error",
        "tool_call_started",
        "tool_call_finished",
        "skill_resolved",
        "skill_error",
    ]
    agent: str | None = None
    message: str = ""
    data: dict[str, Any] = Field(default_factory=dict)
