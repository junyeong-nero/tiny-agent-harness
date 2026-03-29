import subprocess

from tiny_agent_harness.tools.base import BaseTool, ToolResult


class ApplyPatchTool(BaseTool):
    name = "apply_patch"

    def run(self, patch: str) -> ToolResult:
        completed = subprocess.run(
            ["git", "apply", "--whitespace=nowarn", "-"],
            cwd=self.workspace_root,
            input=patch,
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
