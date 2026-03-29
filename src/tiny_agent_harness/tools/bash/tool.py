import subprocess

from tiny_agent_harness.tools.base import BaseTool, ToolResult
from tiny_agent_harness.tools.bash.description import DESCRIPTION
from tiny_agent_harness.tools.bash.schema import BashArgs


class BashTool(BaseTool):
    name = "bash"
    description = DESCRIPTION
    args_model = BashArgs

    def execute(self, arguments: BashArgs) -> ToolResult:
        try:
            completed = subprocess.run(
                ["/bin/zsh", "-lc", arguments.command],
                cwd=self.workspace_root,
                capture_output=True,
                text=True,
                timeout=arguments.timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            return ToolResult(
                tool=self.name,
                ok=False,
                error=f"command timed out after {arguments.timeout_seconds} seconds",
                metadata={
                    "command": arguments.command,
                    "timeout_seconds": arguments.timeout_seconds,
                },
            )

        return ToolResult(
            tool=self.name,
            ok=completed.returncode == 0,
            content=completed.stdout,
            error=completed.stderr or None,
            metadata={"command": arguments.command, "exit_code": completed.returncode},
        )
