import subprocess

from pydantic import BaseModel

from tiny_agent_harness.schemas import ToolResult
from tiny_agent_harness.tools.base import BaseTool
from tiny_agent_harness.tools.git_status.description import DESCRIPTION
from tiny_agent_harness.tools.git_status.schema import GitStatusArgs


class GitStatusTool(BaseTool):
    name = "git_status"
    description = DESCRIPTION
    args_model = GitStatusArgs

    def execute(self, arguments: BaseModel) -> ToolResult:
        validated_arguments = GitStatusArgs.model_validate(arguments.model_dump())
        command = ["git", "status"]
        if validated_arguments.porcelain:
            command.append("--porcelain")

        completed = subprocess.run(
            command,
            cwd=self.workspace_root,
            capture_output=True,
            text=True,
        )
        return ToolResult(
            tool=self.name,
            ok=completed.returncode == 0,
            content=completed.stdout,
            error=completed.stderr or None,
            metadata={
                "exit_code": completed.returncode,
                "porcelain": validated_arguments.porcelain,
            },
        )
