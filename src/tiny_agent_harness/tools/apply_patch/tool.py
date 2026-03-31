import subprocess

from tiny_agent_harness.tools.apply_patch.description import DESCRIPTION
from tiny_agent_harness.tools.apply_patch.schema import ApplyPatchArgs
from tiny_agent_harness.schemas import ToolResult
from tiny_agent_harness.tools.base import BaseTool


class ApplyPatchTool(BaseTool):
    name = "apply_patch"
    description = DESCRIPTION
    args_model = ApplyPatchArgs

    def execute(self, arguments: ApplyPatchArgs) -> ToolResult:
        completed = subprocess.run(
            ["git", "apply", "--whitespace=nowarn", "-"],
            cwd=self.workspace_root,
            input=arguments.patch,
            capture_output=True,
            text=True,
        )
        return ToolResult(
            tool=self.name,
            ok=completed.returncode == 0,
            content=completed.stdout,
            error=completed.stderr or None,
            metadata={"exit_code": completed.returncode},
        )
