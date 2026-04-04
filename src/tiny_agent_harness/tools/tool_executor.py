from typing import Any

from tiny_agent_harness.channels.listener import ListenerChannel
from tiny_agent_harness.schemas import (
    ListenerEvent,
    ToolInput,
    ToolPermissionsConfig,
    ToolResult,
    ToolSpec,
)
from tiny_agent_harness.tools.base import BaseTool

ToolRegistry = dict[str, BaseTool]
ActorPermissions = dict[str, list[str]]


class ToolExecutor:
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
    ) -> "ToolExecutor":
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
        self.ch_listener.call(ListenerEvent(
            kind=kind,
            agent=actor,
            message=message,
            data=data or {},
        ))

    def _emit_finished(self, actor: str | None, result: ToolResult) -> None:
        self._emit(
            "tool_call_finished",
            actor=actor,
            message="finished tool call",
            data={
                "tool": result.tool,
                "ok": result.ok,
                "content": result.content,
                "error": result.error,
            },
        )

    def _failed_result(
        self,
        *,
        tool_name: str,
        actor: str | None,
        error: str,
        metadata: dict[str, Any] | None = None,
    ) -> ToolResult:
        result = ToolResult(
            tool=tool_name,
            ok=False,
            error=error,
            metadata=metadata or {},
        )
        self._emit_finished(actor, result)
        return result

    def _format_exception(self, error: Exception) -> str:
        message = str(error).strip()
        if not message:
            return type(error).__name__
        return f"{type(error).__name__}: {message}"

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

    def tool_spec(self, tool_name: str) -> ToolSpec:
        tool = self.tools.get(tool_name)
        if tool is None:
            raise ValueError(f"unknown tool: {tool_name}")
        return tool.requirements()

    def available_tool_specs(
        self,
        actor: str | None = None,
        allowed_tool_names: list[str] | None = None,
    ) -> list[ToolSpec]:
        names = self.allowed_tool_names(actor=actor, allowed_tool_names=allowed_tool_names)
        return [self.tool_spec(name) for name in names]

    def run(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        actor: str | None = None,
        allowed_tool_names: list[str] | None = None,
    ) -> ToolResult:
        resolved_arguments = arguments or {}
        self._emit(
            "tool_call_started",
            actor=actor,
            message="starting tool call",
            data={"tool": tool_name, "arguments": resolved_arguments},
        )

        tool = self.tools.get(tool_name)
        if tool is None:
            return self._failed_result(
                tool_name=tool_name,
                actor=actor,
                error=f"unknown tool: {tool_name}",
                metadata={"failure_kind": "unknown_tool"},
            )

        allowed_names = self.allowed_tool_names(
            actor=actor, allowed_tool_names=allowed_tool_names
        )
        if tool_name not in allowed_names:
            return self._failed_result(
                tool_name=tool_name,
                actor=actor,
                error=f"tool '{tool_name}' is not allowed",
                metadata={"failure_kind": "disallowed_tool"},
            )

        try:
            result = tool.run(resolved_arguments)
        except Exception as exc:
            return self._failed_result(
                tool_name=tool_name,
                actor=actor,
                error=self._format_exception(exc),
                metadata={
                    "failure_kind": "tool_exception",
                    "exception_type": type(exc).__name__,
                },
            )

        self._emit_finished(actor, result)
        return result

    def run_call(
        self,
        tool_input: ToolInput,
        actor: str | None = None,
        allowed_tool_names: list[str] | None = None,
    ) -> ToolResult:
        return self.run(
            tool_name=tool_input.tool,
            arguments=tool_input.arguments,
            actor=actor,
            allowed_tool_names=allowed_tool_names,
        )
