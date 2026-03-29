from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ToolResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool: str
    ok: bool
    content: str = ""
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class BaseTool(ABC):
    name: str = "base"

    def __init__(self, workspace_root: str | Path) -> None:
        self.workspace_root = Path(workspace_root).resolve()
        if not self.workspace_root.exists() or not self.workspace_root.is_dir():
            raise ValueError("workspace_root must point to an existing directory")

    def _resolve_path(self, path: str | Path) -> Path:
        candidate = (self.workspace_root / path).resolve()
        if self.workspace_root not in candidate.parents and candidate != self.workspace_root:
            raise ValueError(f"path '{path}' escapes the workspace root")
        return candidate

    @abstractmethod
    def run(self, *args: Any, **kwargs: Any) -> ToolResult:
        raise NotImplementedError
