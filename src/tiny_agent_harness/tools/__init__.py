from tiny_agent_harness.channels.listener import ListenerChannel
from tiny_agent_harness.schemas import ToolResult
from tiny_agent_harness.tools.apply_patch import ApplyPatchTool
from tiny_agent_harness.tools.base import BaseTool
from tiny_agent_harness.tools.bash import BashTool
from tiny_agent_harness.tools.git_diff import GitDiffTool
from tiny_agent_harness.tools.list_files import ListFilesTool
from tiny_agent_harness.tools.read_file import ReadFileTool
from tiny_agent_harness.tools.search import SearchTool
from tiny_agent_harness.tools.tool_executor import (
    ActorPermissions,
    ToolExecutor,
    ToolRegistry,
)


def create_default_tools(workspace_root: str) -> ToolRegistry:
    tools: list[BaseTool] = [
        BashTool(workspace_root),
        ReadFileTool(workspace_root),
        SearchTool(workspace_root),
        ListFilesTool(workspace_root),
        ApplyPatchTool(workspace_root),
        GitDiffTool(workspace_root),
    ]
    return {tool.name: tool for tool in tools}


def create_default_tool_executor(
    workspace_root: str,
    actor_permissions: ActorPermissions | None = None,
    listeners: ListenerChannel | None = None,
) -> ToolExecutor:
    return ToolExecutor(
        tools=create_default_tools(workspace_root),
        actor_permissions=actor_permissions,
        ch_listener=listeners,
    )


__all__ = [
    "ApplyPatchTool",
    "BaseTool",
    "BashTool",
    "GitDiffTool",
    "ListFilesTool",
    "ReadFileTool",
    "SearchTool",
    "ToolExecutor",
    "ToolRegistry",
    "ToolResult",
    "create_default_tool_executor",
    "create_default_tools",
]
