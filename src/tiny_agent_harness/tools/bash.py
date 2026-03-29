import subprocess
from typing import Any

from tiny_agent_harness.tools.base import BaseTool, ToolResult


class BashTool(BaseTool):
    name = "bash"

    def run(self, command: str, timeout_seconds: int = 60) -> ToolResult:
        try:
            completed = subprocess.run(
                ["/bin/zsh", "-lc", command],
                cwd=self.workspace_root,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            return ToolResult(
                tool=self.name,
                ok=False,
                error=f"command timed out after {timeout_seconds} seconds",
                metadata={"command": command, "timeout_seconds": timeout_seconds},
            )

        return ToolResult(
            tool=self.name,
            ok=completed.returncode == 0,
            content=completed.stdout,
            error=completed.stderr or None,
            metadata={
                "command": command,
                "exit_code": completed.returncode,
            },
        )
