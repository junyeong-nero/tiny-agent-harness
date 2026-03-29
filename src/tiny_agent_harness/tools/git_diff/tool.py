import subprocess

from tiny_agent_harness.tools.base import BaseTool, ToolResult
from tiny_agent_harness.tools.git_diff.description import DESCRIPTION
from tiny_agent_harness.tools.git_diff.schema import GitDiffArgs


class GitDiffTool(BaseTool):
    name = "git_diff"
    description = DESCRIPTION
    args_model = GitDiffArgs

    def execute(self, arguments: GitDiffArgs) -> ToolResult:
        command = ["git", "diff"]
        if arguments.staged:
            command.append("--staged")
        if arguments.paths:
            command.append("--")
            command.extend(arguments.paths)
        completed = subprocess.run(command, cwd=self.workspace_root, capture_output=True, text=True)
        return ToolResult(
            tool=self.name,
            ok=completed.returncode == 0,
            content=completed.stdout,
            error=completed.stderr or None,
            metadata={"exit_code": completed.returncode, "staged": arguments.staged},
        )
