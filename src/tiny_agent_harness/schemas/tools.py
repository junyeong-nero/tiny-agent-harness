from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    description: str
    arguments_schema: dict[str, Any]


class ToolResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool: str
    ok: bool
    content: str = ""
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
