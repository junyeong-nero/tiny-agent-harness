from pydantic import BaseModel

from tiny_agent_harness.channels.listener import ListenerChannel
from tiny_agent_harness.schemas import ToolResult
from tiny_agent_harness.tools.base import BaseTool
from tiny_agent_harness.tools.tool_executor import ToolExecutor


class EchoArgs(BaseModel):
    message: str


class EchoTool(BaseTool):
    name = "echo"
    description = "Echo message"
    args_model = EchoArgs

    def execute(self, arguments: EchoArgs) -> ToolResult:
        return ToolResult(tool=self.name, ok=True, content=arguments.message)


class CrashTool(BaseTool):
    name = "crash"
    description = "Raise runtime error"
    args_model = EchoArgs

    def execute(self, arguments: EchoArgs) -> ToolResult:
        raise RuntimeError(f"boom: {arguments.message}")


def _executor(
    *,
    tools: dict[str, BaseTool] | None = None,
    actor_permissions: dict[str, list[str]] | None = None,
    listener: ListenerChannel | None = None,
) -> ToolExecutor:
    return ToolExecutor(
        tools=tools or {"echo": EchoTool("."), "crash": CrashTool(".")},
        actor_permissions=actor_permissions,
        ch_listener=listener,
    )


class TestToolExecutor:
    def test_returns_failed_result_for_unknown_tool(self):
        result = _executor().run("missing_tool", actor="worker")

        assert result.ok is False
        assert result.tool == "missing_tool"
        assert result.error == "unknown tool: missing_tool"

    def test_returns_failed_result_for_disallowed_tool(self):
        result = _executor(actor_permissions={"worker": ["echo"]}).run(
            "crash",
            arguments={"message": "x"},
            actor="worker",
        )

        assert result.ok is False
        assert result.tool == "crash"
        assert result.error == "tool 'crash' is not allowed"

    def test_returns_failed_result_for_invalid_arguments(self):
        result = _executor().run("echo", arguments={"message": 1}, actor="worker")

        assert result.ok is False
        assert result.tool == "echo"
        assert "ValidationError" in (result.error or "")
        assert "message" in (result.error or "")

    def test_returns_failed_result_for_tool_runtime_exception_and_emits_listener_event(self):
        listener = ListenerChannel()
        events = []
        listener.add_channel("test", lambda _, event: events.append(event))

        result = _executor(listener=listener).run(
            "crash",
            arguments={"message": "now"},
            actor="worker",
        )

        assert result.ok is False
        assert result.tool == "crash"
        assert result.error == "RuntimeError: boom: now"
        assert [event.kind for event in events] == ["tool_call_started", "tool_call_finished"]
        assert events[-1].data["tool"] == "crash"
        assert events[-1].data["ok"] is False
        assert events[-1].data["error"] == "RuntimeError: boom: now"
