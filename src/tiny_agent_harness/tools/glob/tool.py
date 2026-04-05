import shutil
import subprocess
from pathlib import Path

from pydantic import BaseModel

from tiny_agent_harness.schemas import ToolResult
from tiny_agent_harness.tools.base import BaseTool
from tiny_agent_harness.tools.glob.description import DESCRIPTION
from tiny_agent_harness.tools.glob.schema import GlobArgs


class GlobTool(BaseTool):
    name = "glob"
    description = DESCRIPTION
    args_model = GlobArgs

    def execute(self, arguments: BaseModel) -> ToolResult:
        validated_arguments = GlobArgs.model_validate(arguments.model_dump())
        search_root = self._resolve_path(validated_arguments.path)
        rg_path = shutil.which("rg")

        if rg_path:
            completed = subprocess.run(
                [
                    rg_path,
                    "--files",
                    str(search_root),
                    "-g",
                    validated_arguments.pattern,
                ],
                cwd=self.workspace_root,
                capture_output=True,
                text=True,
            )
            if completed.returncode != 0:
                return ToolResult(
                    tool=self.name,
                    ok=False,
                    error=completed.stderr or "glob command failed",
                )

            matches = [
                self._normalize_match_path(line)
                for line in completed.stdout.splitlines()
                if line.strip()
            ]
            limited_matches = matches[: validated_arguments.limit]
            return ToolResult(
                tool=self.name,
                ok=True,
                content="\n".join(limited_matches),
                metadata={
                    "matches_found": bool(matches),
                    "match_count": len(matches),
                    "truncated": len(matches) > validated_arguments.limit,
                },
            )

        matches = self._fallback_matches(
            search_root=search_root,
            pattern=validated_arguments.pattern,
        )
        limited_matches = matches[: validated_arguments.limit]
        return ToolResult(
            tool=self.name,
            ok=True,
            content="\n".join(limited_matches),
            metadata={
                "matches_found": bool(matches),
                "match_count": len(matches),
                "truncated": len(matches) > validated_arguments.limit,
            },
        )

    def _fallback_matches(self, search_root: Path, pattern: str) -> list[str]:
        matches = [
            str(candidate.relative_to(self.workspace_root))
            for candidate in search_root.glob(pattern)
            if candidate.is_file()
        ]
        matches.sort()
        return matches

    def _normalize_match_path(self, raw_path: str) -> str:
        candidate = Path(raw_path)
        if candidate.is_absolute():
            return str(candidate.relative_to(self.workspace_root))
        return raw_path
