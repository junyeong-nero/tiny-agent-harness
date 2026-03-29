from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from tiny_agent_harness.schemas import ToolRequirement


class ToolResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool: str
    ok: bool
    content: str = ""
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class BaseTool(ABC):
    name: str = "base"
    description: str = ""
    args_model: type[BaseModel] = BaseModel

    def __init__(self, workspace_root: str | Path) -> None:
        self.workspace_root = Path(workspace_root).resolve()
        if not self.workspace_root.exists() or not self.workspace_root.is_dir():
            raise ValueError("workspace_root must point to an existing directory")

    def _resolve_path(self, path: str | Path) -> Path:
        candidate = (self.workspace_root / path).resolve()
        if self.workspace_root not in candidate.parents and candidate != self.workspace_root:
            raise ValueError(f"path '{path}' escapes the workspace root")
        return candidate

    def requirements(self) -> ToolRequirement:
        return ToolRequirement(
            name=self.name,
            description=self.description,
            arguments_schema=self.args_model.model_json_schema(),
        )

    def validate_arguments(self, arguments: dict[str, Any]) -> BaseModel:
        return self.args_model.model_validate(arguments)

    def run(self, arguments: dict[str, Any]) -> ToolResult:
        validated_arguments = self.validate_arguments(arguments)
        return self.execute(validated_arguments)

    @abstractmethod
    def execute(self, arguments: BaseModel) -> ToolResult:
        raise NotImplementedError
