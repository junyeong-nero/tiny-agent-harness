import argparse
import json
import os
import shutil
import sys
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Sequence, TextIO

from tiny_agent_harness.harness import TinyHarness
from tiny_agent_harness.schemas import Event, ListenerEvent, load_config

_RESET = "\033[0m"
_AGENT_ORDER = ("planner", "worker", "reviewer")


def collecting_listener(
    events: list[ListenerEvent],
) -> Callable[[str, ListenerEvent], None]:
    def _collect(_: str, event: ListenerEvent) -> None:
        events.append(event)

    return _collect


def _supports_color(stream: TextIO) -> bool:
    if os.getenv("NO_COLOR") is not None:
        return False
    if os.getenv("TERM", "").lower() == "dumb":
        return False
    return bool(getattr(stream, "isatty", lambda: False)())


def _compact_json(value: object) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(", ", ": "),
        )
    except TypeError:
        return str(value)


def _truncate(value: str, limit: int = 240) -> str:
    if len(value) <= limit:
        return value
    return f"{value[:limit]}..."


def _llm_summary(event: ListenerEvent) -> str:
    raw = event.data.get("content", "")
    try:
        summary = json.loads(raw).get("summary", "").strip()
    except (TypeError, json.JSONDecodeError, AttributeError):
        summary = ""
    return summary or _truncate(str(raw))


def _load_structured_content(event: ListenerEvent) -> dict[str, Any] | None:
    raw = event.data.get("content", "")
    if not isinstance(raw, str):
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _compact_tool_call(tool_call: dict[str, Any]) -> str:
    tool = str(tool_call.get("tool", "unknown"))
    arguments = tool_call.get("arguments", {})
    rendered_args = _compact_json(arguments)
    return f"{tool} {_truncate(rendered_args)}".rstrip()


def _short_text(value: object, fallback: str = "") -> str:
    text = str(value or fallback).strip()
    return _truncate(text) if text else ""


def _llm_action(event: ListenerEvent) -> str | None:
    payload = _load_structured_content(event)
    if payload is None:
        return None

    if event.agent == "supervisor":
        if payload.get("status") == "subagent_call":
            call = payload.get("subagent_call") or {}
            if isinstance(call, dict):
                agent = str(call.get("agent", "unknown"))
                task = _short_text(call.get("task"), fallback="(no task)")
                return f"delegate -> {agent} | {task}"
        summary = _short_text(payload.get("summary"))
        status = str(payload.get("status", "completed"))
        return f"{status} | {summary or '(no summary)'}"

    tool_call = payload.get("tool_call")
    if isinstance(tool_call, dict):
        return f"request tool {_compact_tool_call(tool_call)}"

    if event.agent == "planner":
        plans = payload.get("plans")
        if isinstance(plans, list) and plans:
            summary = _short_text(payload.get("summary"))
            return f"plan {len(plans)} step(s) | {summary or '(no summary)'}"

    if event.agent == "reviewer":
        decision = str(payload.get("decision", "")).strip()
        feedback = _short_text(payload.get("feedback"))
        if decision:
            return f"{decision} | {feedback or '(no feedback)'}"

    kind = str(payload.get("kind", "")).strip()
    status = str(payload.get("status", "")).strip()
    summary = _short_text(payload.get("summary"))
    prefix = f"{kind} {status}".strip()
    if prefix:
        return f"{prefix} | {summary or '(no summary)'}"
    if summary:
        return summary
    return None


@dataclass(frozen=True)
class ConsoleRenderer:
    stream: TextIO
    color: bool
    width: int

    @classmethod
    def for_stream(cls, stream: TextIO) -> "ConsoleRenderer":
        terminal_width = shutil.get_terminal_size((96, 24)).columns
        return cls(
            stream=stream,
            color=_supports_color(stream),
            width=max(60, min(terminal_width, 100)),
        )

    def style(self, text: str, *codes: str) -> str:
        if not self.color or not codes:
            return text
        return f"\033[{';'.join(codes)}m{text}{_RESET}"

    def rule(self, title: str | None = None) -> str:
        if not title:
            return self.style("=" * self.width, "2")

        inner = f" {title} "
        available = max(self.width - len(inner), 4)
        left = "=" * (available // 2)
        right = "=" * (available - len(left))
        return (
            f"{self.style(left, '2')}"
            f"{self.style(inner, '1', '36')}"
            f"{self.style(right, '2')}"
        )

    def render_logo(self) -> str:
        logo_lines = [
            r"   ________   ________  ________  ________  ________  ________  ________  ________  ________ ",
            "  /        \\ /        \\/    /   \\/    /   \\/        \\/        \\/        \\/    /   \\/        \\",
            r" /        _/_/       //         /         /         /       __/         /         /        _/",
            r" /       / /         /         /\__      /         /       / /        _/         //       /  ",
            r" \______/  \________/\__/_____/   \_____/\___/____/\________/\________/\__/_____/ \______/   ",
        ]
        return "\n".join(self.style(line, "1", "36") for line in logo_lines) + "\n"

    def meta(self, label: str, value: str) -> str:
        padded = f"{label:<9}"
        return f"{self.style(padded, '2', '36')} {value}"

    def prompt(self, multiline: bool = False) -> str:
        marker = "..." if multiline else ">"
        return f"{self.style(marker, '1', '36')} "

    def wrap(self, text: str, indent: str = "") -> str:
        width = max(24, self.width - len(indent))
        lines: list[str] = []
        for raw_line in text.splitlines() or [""]:
            if not raw_line.strip():
                lines.append("")
                continue
            lines.append(
                textwrap.fill(
                    raw_line.strip(),
                    width=width,
                    initial_indent=indent,
                    subsequent_indent=indent,
                )
            )
        return "\n".join(lines)

    def render_banner(
        self,
        workspace_root: Path,
        config_path: Path | None,
        skill_names: list[str],
        tool_access: dict[str, list[str]],
        provider_name: str,
        default_model: str,
    ) -> str:
        lines = [
            self.meta("workspace", str(workspace_root)),
            self.meta("model", default_model),
            self.meta("tips", "/help, /skills"),
        ]
        return "\n".join(lines)

    def render_help(
        self,
        skills: list[tuple[str, str]],
        tool_access: dict[str, list[str]],
        provider_name: str,
        default_model: str,
    ) -> str:
        lines = [
            self.rule("help"),
            self.meta("session", f"{provider_name} / {default_model}"),
            self.rule("commands"),
            self.meta("/help", "show this help"),
            self.meta("/status", "show workspace, model, skills, and tool access"),
            self.meta("/agents", "show agent workflow and assigned models"),
            self.meta("/tools", "show tool access by agent"),
            self.meta("/skills", "show installed slash skills"),
            self.meta("/paste", "enter multiline mode"),
            self.meta("/clear", "clear the screen and redraw the banner"),
            self.meta("/exit", "leave the interactive session"),
            self.meta("input", "any other text runs immediately"),
            self.rule("compose"),
            self.meta("/send", "submit the current multiline draft"),
            self.meta("/cancel", "discard the current multiline draft"),
            self.rule("agents"),
            self.meta("agents", "supervisor -> planner | worker | reviewer"),
            self.rule("skills"),
        ]
        if skills:
            for name, description in skills:
                lines.append(self.meta(f"/{name}", description))
        else:
            lines.append(self.meta("skills", "none"))
        lines.append(self.rule("tool access"))
        for agent in _AGENT_ORDER:
            lines.append(
                self.meta(agent, ", ".join(tool_access.get(agent, [])) or "none")
            )
        lines.append(self.rule())
        return "\n".join(lines)

    def render_compose_banner(self) -> str:
        lines = [
            self.rule("multiline mode"),
            self.meta("draft", "type freely; blank lines are preserved"),
            self.meta("/send", "submit the draft"),
            self.meta("/cancel", "discard the draft"),
            self.rule(),
        ]
        return "\n".join(lines)

    def render_agents(self, agent_models: dict[str, str]) -> str:
        lines = [
            self.rule("agents"),
            self.meta("flow", "supervisor -> planner | worker | reviewer"),
        ]
        for agent in ("supervisor", "planner", "worker", "reviewer"):
            lines.append(self.meta(agent, agent_models.get(agent, "unknown")))
        lines.append(self.rule())
        return "\n".join(lines)

    def render_tools(self, tool_access: dict[str, list[str]]) -> str:
        lines = [self.rule("tools")]
        for agent in _AGENT_ORDER:
            lines.append(
                self.meta(agent, ", ".join(tool_access.get(agent, [])) or "none")
            )
        lines.append(self.rule())
        return "\n".join(lines)

    def render_skills(self, skills: list[tuple[str, str]]) -> str:
        lines = [self.rule("skills")]
        if not skills:
            lines.append(self.meta("skills", "none"))
        else:
            for name, description in skills:
                lines.append(self.meta(f"/{name}", description))
        lines.append(self.rule())
        return "\n".join(lines)

    def render_status(
        self,
        workspace_root: Path,
        config_path: Path | None,
        provider_name: str,
        default_model: str,
        skills: list[tuple[str, str]],
        tool_access: dict[str, list[str]],
    ) -> str:
        config_label = str(config_path.resolve()) if config_path else "packaged default"
        skill_names = ", ".join(f"/{name}" for name, _ in skills) if skills else "none"
        lines = [
            self.rule("status"),
            self.meta("session", f"{provider_name} / {default_model}"),
            self.meta("workspace", str(workspace_root)),
            self.meta("config", config_label),
            self.meta("skills", skill_names),
        ]
        for agent in _AGENT_ORDER:
            lines.append(
                self.meta(agent, ", ".join(tool_access.get(agent, [])) or "none")
            )
        lines.append(self.rule())
        return "\n".join(lines)

    def render_notice(self, label: str, message: str) -> str:
        return self.meta(label, message)

    def render_listener_event(self, event: ListenerEvent) -> str | None:
        if event.kind == "llm_request":
            return None

        agent = (event.agent or "system")[:10].ljust(10)
        agent_label = (
            self.style(agent, "1", "36") if event.agent else self.style(agent, "2")
        )

        if event.kind == "run_started":
            task = _short_text(event.data.get("task"), fallback="starting harness run")
            return f"\n{agent_label} {self.style('RUN   ', '1', '34')} {task}"

        if event.kind == "run_completed":
            summary = _short_text(event.data.get("summary"))
            suffix = f" | {summary}" if summary else ""
            return f"{agent_label} {self.style('DONE  ', '1', '32')} completed{suffix}"

        if event.kind == "run_failed":
            summary = _short_text(event.data.get("summary"))
            suffix = f" | {summary}" if summary else ""
            return f"{agent_label} {self.style('FAIL  ', '1', '31')} failed{suffix}"

        if event.kind == "llm_response":
            action = _llm_action(event)
            if action:
                return f"{agent_label} {self.style('ACTION', '1', '35')} {action}"
            return (
                f"{agent_label} {self.style('NOTE  ', '1', '36')} {_llm_summary(event)}"
            )

        if event.kind == "llm_error":
            message = event.message.strip() or "llm error"
            return f"{agent_label} {self.style('ERROR ', '1', '31')} {message}"

        if event.kind == "skill_error":
            message = event.message.strip() or "skill error"
            return f"{agent_label} {self.style('ERROR ', '1', '31')} {message}"

        if event.kind == "skill_resolved":
            skill = str(event.data.get("skill", "")).strip()
            args = str(event.data.get("args", "")).strip()
            prompt_preview = _short_text(event.data.get("prompt"))
            detail = f"/{skill}"
            if args:
                detail = f"{detail} {args}"
            if prompt_preview:
                detail = f"{detail} | {prompt_preview}"
            return f"{agent_label} {self.style('SKILL ', '1', '34')} {detail}"

        if event.kind == "tool_call_started":
            tool = str(event.data.get("tool", "unknown"))
            arguments = _truncate(_compact_json(event.data.get("arguments", {})))
            return (
                f"{agent_label} {self.style('TOOL  ', '1', '33')}"
                f" {tool} {arguments}"
            )

        if event.kind == "tool_call_finished":
            tool = str(event.data.get("tool", "unknown"))
            ok = bool(event.data.get("ok", False))
            status = self.style("[ok]", "32") if ok else self.style("[failed]", "31")
            content = _truncate(
                str(event.data.get("content") or event.data.get("error") or "")
            )
            return (
                f"{agent_label} {self.style('TOOL  ', '1', '33')}"
                f" {tool} {status} {content}"
            )

        message = event.message.strip()
        return f"{agent_label} {self.style('INFO  ', '2')} {message}".rstrip()

    def clear_screen(self) -> str:
        return "\033[2J\033[H" if self.color else ""

    def render_output_event(self, event: Event) -> str:
        summary = event.payload.summary.strip() or "(no summary)"
        body = self.wrap(summary, indent="  ")
        return f"\n{self.rule('assistant')}\n{body}\n{self.rule()}"


@dataclass
class InteractiveShell:
    renderer: ConsoleRenderer
    workspace_root: Path
    config_path: Path | None
    provider_name: str
    default_model: str
    skills: list[tuple[str, str]]
    tool_access: dict[str, list[str]]
    submit_prompt: Callable[[str], None]
    agent_models: dict[str, str] = field(default_factory=dict)
    compose_mode: bool = False
    draft_lines: list[str] = field(default_factory=list)

    @property
    def is_composing(self) -> bool:
        return self.compose_mode

    def print(self, text: str) -> None:
        print(text, file=self.renderer.stream)

    def banner(self) -> str:
        skill_names = [name for name, _ in self.skills]
        return self.renderer.render_banner(
            workspace_root=self.workspace_root,
            config_path=self.config_path,
            skill_names=skill_names,
            tool_access=self.tool_access,
            provider_name=self.provider_name,
            default_model=self.default_model,
        )

    def help_text(self) -> str:
        return self.renderer.render_help(
            skills=self.skills,
            tool_access=self.tool_access,
            provider_name=self.provider_name,
            default_model=self.default_model,
        )

    def handle_interrupt(self) -> bool:
        print(file=self.renderer.stream)
        if not self.compose_mode:
            return False

        self.compose_mode = False
        self.draft_lines.clear()
        self.print(self.renderer.render_notice("compose", "draft discarded"))
        return True

    def _submit(self, prompt: str) -> None:
        normalized = prompt.strip()
        if not normalized:
            return
        self.submit_prompt(normalized)

    def _enter_compose_mode(self) -> None:
        self.compose_mode = True
        self.draft_lines.clear()
        self.print(self.renderer.render_compose_banner())

    def _complete_draft(self) -> None:
        prompt = "\n".join(self.draft_lines).rstrip()
        if not prompt.strip():
            self.print(self.renderer.render_notice("compose", "draft is empty"))
            return
        self.compose_mode = False
        self.draft_lines.clear()
        self._submit(prompt)

    def _cancel_draft(self) -> None:
        self.compose_mode = False
        self.draft_lines.clear()
        self.print(self.renderer.render_notice("compose", "draft discarded"))

    def _show_status(self) -> None:
        self.print(
            self.renderer.render_status(
                workspace_root=self.workspace_root,
                config_path=self.config_path,
                provider_name=self.provider_name,
                default_model=self.default_model,
                skills=self.skills,
                tool_access=self.tool_access,
            )
        )

    def _show_agents(self) -> None:
        agent_models = self.agent_models or {
            "supervisor": self.default_model,
            "planner": self.default_model,
            "worker": self.default_model,
            "reviewer": self.default_model,
        }
        self.print(self.renderer.render_agents(agent_models))

    def _show_tools(self) -> None:
        self.print(self.renderer.render_tools(self.tool_access))

    def _show_skills(self) -> None:
        self.print(self.renderer.render_skills(self.skills))

    def _handle_compose_command(self, command: str) -> bool:
        if command == "/send":
            self._complete_draft()
            return True
        if command in {"/cancel", "/exit", "quit"}:
            self._cancel_draft()
            return True
        if command in {"/help", "help"}:
            self.print(self.help_text())
            return True
        return False

    def handle_line(self, line: str) -> bool:
        raw = line.rstrip("\n")
        stripped = raw.strip()
        command = stripped.lower()

        if self.compose_mode:
            if stripped and self._handle_compose_command(command):
                return True
            self.draft_lines.append(raw)
            return True

        if not stripped:
            return True

        if command in {"/exit", "exit", "quit"}:
            return False
        if command in {"/help", "help"}:
            self.print(self.help_text())
            return True
        if command in {"/status"}:
            self._show_status()
            return True
        if command in {"/agents"}:
            self._show_agents()
            return True
        if command in {"/tools"}:
            self._show_tools()
            return True
        if command in {"/skills"}:
            self._show_skills()
            return True
        if command in {"/paste"}:
            self._enter_compose_mode()
            return True
        if command in {"/clear", "clear"}:
            print(self.renderer.clear_screen(), end="", file=self.renderer.stream)
            self.print(self.banner())
            return True

        self._submit(raw)
        return True


def make_console_listener(
    renderer: ConsoleRenderer,
) -> Callable[[str, ListenerEvent], None]:
    def _listener(_: str, event: ListenerEvent) -> None:
        line = renderer.render_listener_event(event)
        if line is None:
            return
        print(line, file=renderer.stream)

    return _listener


def make_console_output_handler(
    renderer: ConsoleRenderer,
) -> Callable[[str, Event], None]:
    def _handler(_: str, event: Event) -> None:
        print(renderer.render_output_event(event), file=renderer.stream)

    return _handler


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tiny-agent",
        description="Run the tiny-agent harness against a workspace.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to a YAML config file. Defaults to the packaged config.",
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        default=None,
        help="Workspace root to expose to tools. Defaults to the current directory.",
    )
    parser.add_argument(
        "prompt",
        nargs="*",
        help="Optional one-shot prompt. If omitted, starts interactive mode.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    config = load_config(args.config)
    workspace_root = (args.workspace or Path.cwd()).resolve()
    renderer = ConsoleRenderer.for_stream(sys.stdout)

    harness = TinyHarness(
        config=config,
        workspace_root=str(workspace_root),
    )
    harness.ch_output.add_channel("console", make_console_output_handler(renderer))
    harness.ch_listener.add_channel("console", make_console_listener(renderer))

    prompt = " ".join(args.prompt).strip()
    if prompt:
        harness.ch_input.queue(prompt)
        harness.run()
        return 0

    skills = harness.skill_runner.available_skills()
    tool_access = {
        agent: harness.tool_caller.allowed_tool_names(actor=agent)
        for agent in _AGENT_ORDER
    }
    agent_models = {
        "supervisor": config.models.supervisor or config.models.default,
        "planner": config.models.planner or config.models.default,
        "worker": config.models.worker or config.models.default,
        "reviewer": config.models.reviewer or config.models.default,
    }

    def _submit_prompt(task: str) -> None:
        harness.ch_input.queue(task)
        harness.run()

    shell = InteractiveShell(
        renderer=renderer,
        workspace_root=workspace_root,
        config_path=args.config,
        provider_name=config.provider,
        default_model=config.models.default,
        skills=skills,
        tool_access=tool_access,
        submit_prompt=_submit_prompt,
        agent_models=agent_models,
    )

    if getattr(renderer.stream, "isatty", lambda: False)():
        print(renderer.render_logo(), file=renderer.stream)
    print(shell.banner(), file=renderer.stream)
    while True:
        try:
            prompt = input(f"\n{renderer.prompt(multiline=shell.is_composing)}")
        except EOFError:
            print(file=renderer.stream)
            break
        except KeyboardInterrupt:
            if shell.handle_interrupt():
                continue
            break

        if not shell.handle_line(prompt):
            break

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
