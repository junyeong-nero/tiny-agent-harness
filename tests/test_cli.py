from io import StringIO
from pathlib import Path

from tiny_agent_harness.cli import ConsoleRenderer, InteractiveShell
from tiny_agent_harness.schemas import Event, ListenerEvent, Response


def _renderer(width: int = 80, stream: StringIO | None = None) -> ConsoleRenderer:
    return ConsoleRenderer(stream=stream or StringIO(), color=False, width=width)


def _tool_access() -> dict[str, list[str]]:
    return {
        "planner": ["list_files", "search"],
        "worker": ["bash", "read_file"],
        "reviewer": ["read_file", "git_diff"],
    }


def _shell(
    stream: StringIO | None = None,
) -> tuple[InteractiveShell, list[str], StringIO]:
    output = stream or StringIO()
    submitted: list[str] = []
    shell = InteractiveShell(
        renderer=_renderer(stream=output),
        workspace_root=Path("/tmp/project"),
        config_path=Path("config.yaml"),
        provider_name="openai",
        default_model="gpt-4o-mini",
        skills=[("commit", "group changes into logical commits")],
        tool_access=_tool_access(),
        submit_prompt=submitted.append,
    )
    return shell, submitted, output


class TestConsoleRenderer:
    def test_renders_supervisor_action_from_json(self):
        renderer = _renderer()
        event = ListenerEvent(
            kind="llm_response",
            agent="supervisor",
            data={
                "content": (
                    '{"task":"improve cli","status":"subagent_call",'
                    '"subagent_call":{"agent":"worker","task":"update cli output"},'
                    '"summary":"delegate work"}'
                )
            },
        )

        line = renderer.render_listener_event(event)

        assert line == "supervisor ACTION delegate -> worker | update cli output"

    def test_renders_worker_tool_request_as_action(self):
        renderer = _renderer()
        event = ListenerEvent(
            kind="llm_response",
            agent="worker",
            data={
                "content": (
                    '{"task":"inspect file","kind":"implement","status":"completed",'
                    '"summary":"done","tool_call":{"tool":"read_file","arguments":{"path":"src/app.py"}},'
                    '"artifacts":[],"changed_files":[],"test_results":[]}'
                )
            },
        )

        line = renderer.render_listener_event(event)

        assert line == 'worker     ACTION request tool read_file {"path": "src/app.py"}'

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

    def test_truncates_long_tool_finished_content(self):
        renderer = _renderer()
        event = ListenerEvent(
            kind="tool_call_finished",
            agent="worker",
            data={"tool": "read_file", "ok": True, "content": "x" * 300},
        )

        line = renderer.render_listener_event(event)

        assert line.endswith(("x" * 240) + "...")

    def test_renders_banner_with_session_metadata_and_command_hints(self):
        renderer = _renderer()
        banner = renderer.render_banner(
            workspace_root=Path("/tmp/project"),
            config_path=Path("config.yaml"),
            skill_names=["commit"],
            tool_access=_tool_access(),
            provider_name="openai",
            default_model="gpt-4o-mini",
        )

        assert "tiny-agent" in banner
        assert "workspace /tmp/project" in banner
        assert "provider  openai" in banner
        assert "model     gpt-4o-mini" in banner
        assert "commands  /help /status /agents /tools /skills /paste /clear /exit" in banner
        assert "enter     prompt, then Enter to run" in banner

    def test_renders_help_with_multiline_commands(self):
        renderer = _renderer()

        help_text = renderer.render_help(
            skills=[("commit", "group changes into logical commits")],
            tool_access=_tool_access(),
            provider_name="openai",
            default_model="gpt-4o-mini",
        )

        assert "/paste" in help_text
        assert "/send" in help_text
        assert "/cancel" in help_text
        assert "group changes into logical commits" in help_text
        assert "openai / gpt-4o-mini" in help_text

    def test_prompts_match_single_and_multiline_modes(self):
        renderer = _renderer()

        assert renderer.prompt() == "> "
        assert renderer.prompt(multiline=True) == "... "

    def test_renders_compose_banner(self):
        renderer = _renderer()

        banner = renderer.render_compose_banner()

        assert "multiline mode" in banner
        assert "/send" in banner
        assert "/cancel" in banner

    def test_renders_status_panel(self):
        renderer = _renderer()

        panel = renderer.render_status(
            workspace_root=Path("/tmp/project"),
            config_path=Path("config.yaml"),
            provider_name="openai",
            default_model="gpt-4o-mini",
            skills=[("commit", "group changes")],
            tool_access=_tool_access(),
        )

        assert "openai / gpt-4o-mini" in panel
        assert "/commit" in panel
        assert "worker    bash, read_file" in panel

    def test_renders_skill_resolved_event(self):
        renderer = _renderer()
        event = ListenerEvent(
            kind="skill_resolved",
            data={
                "skill": "commit",
                "args": "group by feature",
                "prompt": "Split changes into logical commits.",
            },
        )

        line = renderer.render_listener_event(event)

        assert (
            line
            == "system     SKILL  /commit group by feature | Split changes into logical commits."
        )

    def test_renders_summary_block(self):
        renderer = _renderer()
        event = Event(
            event_id="evt-1",
            session_id="default",
            payload=Response(query="hello", summary="final answer"),
        )

        output = renderer.render_output_event(event)

        assert "assistant" in output
        assert "  final answer" in output


class TestInteractiveShell:
    def test_submits_single_line_prompt(self):
        shell, submitted, _ = _shell()

        keep_running = shell.handle_line("refactor cli output")

        assert keep_running is True
        assert submitted == ["refactor cli output"]

    def test_submits_multiline_prompt_with_send(self):
        shell, submitted, _ = _shell()

        assert shell.handle_line("/paste") is True
        assert shell.handle_line("refactor cli output") is True
        assert shell.handle_line("match codex style") is True
        assert shell.handle_line("/send") is True

        assert submitted == ["refactor cli output\nmatch codex style"]
        assert shell.is_composing is False

    def test_cancels_multiline_prompt_without_submitting(self):
        shell, submitted, _ = _shell()

        shell.handle_line("/paste")
        shell.handle_line("discard this draft")
        shell.handle_line("/cancel")

        assert submitted == []
        assert shell.is_composing is False

    def test_status_command_renders_session_details(self):
        shell, _, output = _shell()

        keep_running = shell.handle_line("/status")

        assert keep_running is True
        assert "openai / gpt-4o-mini" in output.getvalue()
        assert "/commit" in output.getvalue()

    def test_exit_command_stops_loop(self):
        shell, _, _ = _shell()

        keep_running = shell.handle_line("/exit")

        assert keep_running is False
