from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


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
        "skill_error",
    ]
    agent: str | None = None
    message: str = ""
    data: dict[str, Any] = Field(default_factory=dict)
