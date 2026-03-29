from pathlib import Path

from tiny_agent_harness.tools.base import BaseTool, ToolResult


class ReadFileTool(BaseTool):
    name = "read_file"

    def run(
        self,
        path: str,
        start_line: int | None = None,
        end_line: int | None = None,
    ) -> ToolResult:
        file_path = self._resolve_path(path)
        if not file_path.exists() or not file_path.is_file():
            return ToolResult(
                tool=self.name,
                ok=False,
                error=f"file not found: {path}",
            )

        content = file_path.read_text(encoding="utf-8")
        if start_line is None and end_line is None:
            return ToolResult(
                tool=self.name,
                ok=True,
                content=content,
                metadata={"path": str(file_path.relative_to(self.workspace_root))},
            )

        lines = content.splitlines()
        start_index = 0 if start_line is None else max(start_line - 1, 0)
        end_index = len(lines) if end_line is None else max(end_line, 0)
        selected = "\n".join(lines[start_index:end_index])

        return ToolResult(
            tool=self.name,
            ok=True,
            content=selected,
            metadata={
                "path": str(file_path.relative_to(self.workspace_root)),
                "start_line": start_line,
                "end_line": end_line,
            },
        )
