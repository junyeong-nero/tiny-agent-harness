from pydantic import BaseModel

from tiny_agent_harness.schemas import ToolResult
from tiny_agent_harness.tools.base import BaseTool
from tiny_agent_harness.tools.replace_in_file.description import DESCRIPTION
from tiny_agent_harness.tools.replace_in_file.schema import ReplaceInFileArgs


class ReplaceInFileTool(BaseTool):
    name = "replace_in_file"
    description = DESCRIPTION
    args_model = ReplaceInFileArgs

    def execute(self, arguments: BaseModel) -> ToolResult:
        validated_arguments = ReplaceInFileArgs.model_validate(arguments.model_dump())
        target_path = self._resolve_path(validated_arguments.path)
        if not target_path.exists() or not target_path.is_file():
            return ToolResult(
                tool=self.name,
                ok=False,
                error=f"file not found: {validated_arguments.path}",
            )

        original_content = target_path.read_text(encoding="utf-8")
        occurrence_count = original_content.count(validated_arguments.old_text)
        if occurrence_count != validated_arguments.expected_occurrences:
            return ToolResult(
                tool=self.name,
                ok=False,
                error=(
                    "expected "
                    f"{validated_arguments.expected_occurrences} occurrences of the target text, "
                    f"found {occurrence_count}"
                ),
                metadata={"occurrence_count": occurrence_count},
            )

        updated_content = original_content.replace(
            validated_arguments.old_text,
            validated_arguments.new_text,
        )
        target_path.write_text(updated_content, encoding="utf-8")
        return ToolResult(
            tool=self.name,
            ok=True,
            content=f"updated {validated_arguments.path}",
            metadata={
                "path": validated_arguments.path,
                "replacements": validated_arguments.expected_occurrences,
            },
        )
