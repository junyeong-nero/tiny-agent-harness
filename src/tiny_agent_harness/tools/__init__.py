from tiny_agent_harness.tools.apply_patch import ApplyPatchTool
from tiny_agent_harness.tools.base import BaseTool, ToolResult
from tiny_agent_harness.tools.bash import BashTool
from tiny_agent_harness.tools.git_diff import GitDiffTool
from tiny_agent_harness.tools.list_files import ListFilesTool
from tiny_agent_harness.tools.read_file import ReadFileTool
from tiny_agent_harness.tools.search import SearchTool


def create_default_tools(workspace_root: str) -> dict[str, BaseTool]:
    tools: list[BaseTool] = [
        BashTool(workspace_root),
        ReadFileTool(workspace_root),
        SearchTool(workspace_root),
        ListFilesTool(workspace_root),
        ApplyPatchTool(workspace_root),
        GitDiffTool(workspace_root),
    ]
    return {tool.name: tool for tool in tools}


__all__ = [
    "ApplyPatchTool",
    "BaseTool",
    "BashTool",
    "GitDiffTool",
    "ListFilesTool",
    "ReadFileTool",
    "SearchTool",
    "ToolResult",
    "create_default_tools",
]
