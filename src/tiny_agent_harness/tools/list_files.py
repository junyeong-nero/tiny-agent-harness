import os
import shutil
import subprocess
from pathlib import Path

from tiny_agent_harness.tools.base import BaseTool, ToolResult


class ListFilesTool(BaseTool):
    name = "list_files"

    def run(self, path: str = ".", glob_pattern: str | None = None) -> ToolResult:
        list_root = self._resolve_path(path)
        rg_path = shutil.which("rg")

        if rg_path:
            command = [rg_path, "--files", str(list_root)]
            if glob_pattern:
                command.extend(["-g", glob_pattern])

            completed = subprocess.run(
                command,
                cwd=self.workspace_root,
                capture_output=True,
                text=True,
            )
            if completed.returncode != 0:
                return ToolResult(
                    tool=self.name,
                    ok=False,
                    error=completed.stderr or "list files command failed",
                )

            return ToolResult(
                tool=self.name,
                ok=True,
                content=completed.stdout,
            )

        files: list[str] = []
        for root, _, filenames in os.walk(list_root):
            for filename in filenames:
                files.append(
                    str((Path(root) / filename).resolve().relative_to(self.workspace_root))
                )

        files.sort()
        return ToolResult(
            tool=self.name,
            ok=True,
            content="\n".join(files),
        )
