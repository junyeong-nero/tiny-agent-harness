from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ToolCall(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    description: str
    arguments_schema: dict[str, Any]
