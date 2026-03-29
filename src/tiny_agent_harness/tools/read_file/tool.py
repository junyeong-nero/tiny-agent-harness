from tiny_agent_harness.tools.base import BaseTool, ToolResult
from tiny_agent_harness.tools.read_file.description import DESCRIPTION
from tiny_agent_harness.tools.read_file.schema import ReadFileArgs


class ReadFileTool(BaseTool):
    name = "read_file"
    description = DESCRIPTION
    args_model = ReadFileArgs

    def execute(self, arguments: ReadFileArgs) -> ToolResult:
        file_path = self._resolve_path(arguments.path)
        if not file_path.exists() or not file_path.is_file():
            return ToolResult(tool=self.name, ok=False, error=f"file not found: {arguments.path}")

        content = file_path.read_text(encoding="utf-8")
        if arguments.start_line is None and arguments.end_line is None:
            return ToolResult(
                tool=self.name,
                ok=True,
                content=content,
                metadata={"path": str(file_path.relative_to(self.workspace_root))},
            )

        lines = content.splitlines()
        start_index = 0 if arguments.start_line is None else max(arguments.start_line - 1, 0)
        end_index = len(lines) if arguments.end_line is None else max(arguments.end_line, 0)
        selected = "\n".join(lines[start_index:end_index])
        return ToolResult(
            tool=self.name,
            ok=True,
            content=selected,
            metadata={
                "path": str(file_path.relative_to(self.workspace_root)),
                "start_line": arguments.start_line,
                "end_line": arguments.end_line,
            },
        )
