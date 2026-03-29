from typing import Any

from tiny_agent_harness.schemas import ToolCall, ToolRequirement
from tiny_agent_harness.tools.base import BaseTool, ToolResult

ToolRegistry = dict[str, BaseTool]
ActorPermissions = dict[str, list[str]]


class ToolCaller:
    def __init__(
        self,
        tools: ToolRegistry,
        actor_permissions: ActorPermissions | None = None,
    ) -> None:
        self.tools = tools
        self.actor_permissions = actor_permissions or {}

    def allowed_tool_names(
        self,
        actor: str | None = None,
        allowed_tool_names: list[str] | None = None,
    ) -> list[str]:
        names = set(self.tools.keys())
        if allowed_tool_names is not None:
            names &= set(allowed_tool_names)
        if actor and actor in self.actor_permissions:
            names &= set(self.actor_permissions[actor])
        return sorted(names)

    def tool_requirements(self, tool_name: str) -> ToolRequirement:
        tool = self.tools.get(tool_name)
        if tool is None:
            raise ValueError(f"unknown tool: {tool_name}")
        return tool.requirements()

    def available_tool_requirements(
        self,
        actor: str | None = None,
        allowed_tool_names: list[str] | None = None,
    ) -> list[ToolRequirement]:
        names = self.allowed_tool_names(actor=actor, allowed_tool_names=allowed_tool_names)
        return [self.tool_requirements(name) for name in names]

    def run(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        actor: str | None = None,
        allowed_tool_names: list[str] | None = None,
    ) -> ToolResult:
        allowed_names = self.allowed_tool_names(actor=actor, allowed_tool_names=allowed_tool_names)
        if tool_name not in allowed_names:
            raise ValueError(f"tool '{tool_name}' is not allowed")

        tool = self.tools.get(tool_name)
        if tool is None:
            raise ValueError(f"unknown tool: {tool_name}")

        return tool.run(arguments or {})

    def run_call(
        self,
        tool_call: ToolCall,
        actor: str | None = None,
        allowed_tool_names: list[str] | None = None,
    ) -> ToolResult:
        return self.run(
            tool_name=tool_call.tool,
            arguments=tool_call.arguments,
            actor=actor,
            allowed_tool_names=allowed_tool_names,
        )
