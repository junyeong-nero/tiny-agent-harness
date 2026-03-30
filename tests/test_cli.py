from io import StringIO
from pathlib import Path

from tiny_agent_harness.cli import ConsoleRenderer
from tiny_agent_harness.schemas import Event, ListenerEvent, Response


def _renderer(width: int = 80) -> ConsoleRenderer:
    return ConsoleRenderer(stream=StringIO(), color=False, width=width)


class TestConsoleRenderer:
    def test_renders_llm_response_summary_from_json(self):
        renderer = _renderer()
        event = ListenerEvent(
            kind="llm_response",
            agent="planner",
            data={"content": '{"summary": "planned next step"}'},
        )

        line = renderer.render_listener_event(event)

        assert line == "planner    NOTE   planned next step"

    def test_renders_tool_started_with_compact_json_arguments(self):
        renderer = _renderer()
        event = ListenerEvent(
            kind="tool_call_started",
            agent="worker",
            data={"tool": "bash", "arguments": {"cmd": "ls", "cwd": "."}},
        )

        line = renderer.render_listener_event(event)

        assert line == 'worker     TOOL   bash {"cmd": "ls", "cwd": "."}'

    def test_renders_tool_finished_with_status(self):
        renderer = _renderer()
        event = ListenerEvent(
            kind="tool_call_finished",
            agent="worker",
            data={"tool": "read_file", "ok": True, "content": "hello"},
        )

        line = renderer.render_listener_event(event)

        assert line == "worker     TOOL   read_file [ok] hello"

    def test_renders_banner_with_workspace_and_command_hints(self):
        renderer = _renderer()
        banner = renderer.render_banner(Path("/tmp/project"), Path("config.yaml"))

        assert "tiny-agent" in banner
        assert "workspace /tmp/project" in banner
        assert "config    " in banner
        assert "help, clear, exit, quit" in banner

    def test_renders_summary_block(self):
        renderer = _renderer()
        event = Event(
            event_id="evt-1",
            session_id="default",
            payload=Response(query="hello", summary="final answer"),
        )

        output = renderer.render_output_event(event)

        assert "result" in output
        assert "  final answer" in output
