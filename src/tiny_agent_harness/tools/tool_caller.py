from typing import Any

from tiny_agent_harness.handlers.listener import ListenerChannel
from tiny_agent_harness.schemas import ListenerEvent, ToolCall, ToolPermissionsConfig, ToolRequirement
from tiny_agent_harness.tools.base import BaseTool, ToolResult

ToolRegistry = dict[str, BaseTool]
ActorPermissions = dict[str, list[str]]


class ToolCaller:
    def __init__(
        self,
        tools: ToolRegistry,
        actor_permissions: ActorPermissions | None = None,
        ch_listener: ListenerChannel | None = None,
    ) -> None:
        self.tools = tools
        self.actor_permissions = actor_permissions or {}
        self.ch_listener = ch_listener or ListenerChannel()

    @classmethod
    def from_config(
        cls,
        tools: ToolRegistry,
        config: ToolPermissionsConfig,
        ch_listener: ListenerChannel | None = None,
    ) -> "ToolCaller":
        return cls(
            tools=tools,
            actor_permissions=config.as_actor_permissions(),
            ch_listener=ch_listener,
        )

    def _emit(
        self,
        kind: str,
        actor: str | None = None,
        message: str = "",
        data: dict[str, Any] | None = None,
    ) -> None:
        event = ListenerEvent(
            kind=kind,
            agent=actor,
            message=message,
            data=data or {},
        )
        self.ch_listener.call(event)

    def allowed_tool_names(
        self,
        actor: str | None = None,
        allowed_tool_names: list[str] | None = None,
    ) -> list[str]:
        names = set(self.tools.keys())
        if allowed_tool_names:
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
        names = self.allowed_tool_names(
            actor=actor, allowed_tool_names=allowed_tool_names
        )
        return [self.tool_requirements(name) for name in names]

    def run(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        actor: str | None = None,
        allowed_tool_names: list[str] | None = None,
    ) -> ToolResult:
        allowed_names = self.allowed_tool_names(
            actor=actor, allowed_tool_names=allowed_tool_names
        )
        if tool_name not in allowed_names:
            raise ValueError(f"tool '{tool_name}' is not allowed")

        tool = self.tools.get(tool_name)
        if tool is None:
            raise ValueError(f"unknown tool: {tool_name}")

        resolved_arguments = arguments or {}
        self._emit(
            kind="tool_call_started",
            actor=actor,
            message="starting tool call",
            data={"tool": tool_name, "arguments": resolved_arguments},
        )
        result = tool.run(resolved_arguments)
        self._emit(
            kind="tool_call_finished",
            actor=actor,
            message="finished tool call",
            data={
                "tool": tool_name,
                "ok": result.ok,
                "content": result.content,
                "error": result.error,
            },
        )
        return result

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
