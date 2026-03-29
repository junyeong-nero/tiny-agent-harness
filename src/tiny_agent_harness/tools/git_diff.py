import subprocess

from tiny_agent_harness.tools.base import BaseTool, ToolResult


class GitDiffTool(BaseTool):
    name = "git_diff"

    def run(self, paths: list[str] | None = None, staged: bool = False) -> ToolResult:
        command = ["git", "diff"]
        if staged:
            command.append("--staged")
        if paths:
            command.append("--")
            command.extend(paths)

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
            metadata={"exit_code": completed.returncode, "staged": staged},
        )
