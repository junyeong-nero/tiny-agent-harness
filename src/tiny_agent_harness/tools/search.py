import shutil
import subprocess

from tiny_agent_harness.tools.base import BaseTool, ToolResult


class SearchTool(BaseTool):
    name = "search"

    def run(self, pattern: str, path: str = ".") -> ToolResult:
        search_root = self._resolve_path(path)
        rg_path = shutil.which("rg")

        if rg_path:
            completed = subprocess.run(
                [
                    rg_path,
                    "--line-number",
                    "--with-filename",
                    "--color",
                    "never",
                    pattern,
                    str(search_root),
                ],
                cwd=self.workspace_root,
                capture_output=True,
                text=True,
            )
            if completed.returncode not in (0, 1):
                return ToolResult(
                    tool=self.name,
                    ok=False,
                    error=completed.stderr or "search command failed",
                )

            return ToolResult(
                tool=self.name,
                ok=True,
                content=completed.stdout,
                metadata={"matches_found": bool(completed.stdout.strip())},
            )

        matches: list[str] = []
        for candidate in search_root.rglob("*"):
            if not candidate.is_file():
                continue
            try:
                lines = candidate.read_text(encoding="utf-8").splitlines()
            except UnicodeDecodeError:
                continue
            for index, line in enumerate(lines, start=1):
                if pattern in line:
                    rel_path = candidate.relative_to(self.workspace_root)
                    matches.append(f"{rel_path}:{index}:{line}")

        return ToolResult(
            tool=self.name,
            ok=True,
            content="\n".join(matches),
            metadata={"matches_found": bool(matches)},
        )
