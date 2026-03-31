import argparse
import json
import os
import shutil
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence, TextIO

from tiny_agent_harness.harness import TinyHarness
from tiny_agent_harness.schemas import Event, ListenerEvent, load_config
from tiny_agent_harness.utils import truncate

_RESET = "\033[0m"


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


def _llm_summary(event: ListenerEvent) -> str:
    raw = event.data.get("content", "")
    try:
        summary = json.loads(raw).get("summary", "").strip()
    except (TypeError, json.JSONDecodeError, AttributeError):
        summary = ""
    return summary or truncate(str(raw))


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

    def meta(self, label: str, value: str) -> str:
        padded = f"{label:<9}"
        return f"{self.style(padded, '2', '36')} {value}"

    def prompt(self) -> str:
        return f"{self.style('tiny-agent', '1', '36')}> "

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

    def render_banner(self, workspace_root: Path, config_path: Path | None) -> str:
        config_label = str(config_path.resolve()) if config_path else "packaged default"
        lines = [
            self.rule("tiny-agent"),
            self.meta("workspace", str(workspace_root)),
            self.meta("config", config_label),
            self.meta("mode", "interactive"),
            self.meta("commands", "help, clear, exit, quit"),
            self.rule(),
        ]
        return "\n".join(lines)

    def render_help(self) -> str:
        lines = [
            self.rule("commands"),
            self.meta("help", "show this help"),
            self.meta("clear", "clear the screen and redraw the banner"),
            self.meta("exit", "leave the interactive session"),
            self.meta("input", "any other text is sent to the harness"),
            self.rule(),
        ]
        return "\n".join(lines)

    def render_listener_event(self, event: ListenerEvent) -> str | None:
        if event.kind == "llm_request":
            return None

        agent = (event.agent or "system")[:10].ljust(10)
        agent_label = self.style(agent, "1", "36") if event.agent else self.style(agent, "2")

        if event.kind == "run_started":
            return f"\n{agent_label} {self.style('RUN   ', '1', '34')} starting harness run"

        if event.kind == "run_completed":
            return f"{agent_label} {self.style('DONE  ', '1', '32')} completed"

        if event.kind == "run_failed":
            return f"{agent_label} {self.style('FAIL  ', '1', '31')} failed"

        if event.kind == "llm_response":
            return f"{agent_label} {self.style('NOTE  ', '1', '36')} {_llm_summary(event)}"

        if event.kind == "llm_error":
            message = event.message.strip() or "llm error"
            return f"{agent_label} {self.style('ERROR ', '1', '31')} {message}"

        if event.kind == "tool_call_started":
            tool = str(event.data.get("tool", "unknown"))
            arguments = truncate(_compact_json(event.data.get("arguments", {})))
            return (
                f"{agent_label} {self.style('TOOL  ', '1', '33')}"
                f" {tool} {arguments}"
            )

        if event.kind == "tool_call_finished":
            tool = str(event.data.get("tool", "unknown"))
            ok = bool(event.data.get("ok", False))
            status = self.style("[ok]", "32") if ok else self.style("[failed]", "31")
            content = truncate(
                str(event.data.get("content", "") or event.data.get("error", ""))
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
        return f"\n{self.rule('result')}\n{body}\n{self.rule()}"


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

    print(renderer.render_banner(workspace_root, args.config), file=renderer.stream)
    while True:
        try:
            prompt = input(f"\n{renderer.prompt()}").strip()
        except (EOFError, KeyboardInterrupt):
            print(file=renderer.stream)
            break

        lowered = prompt.lower()
        if not prompt:
            continue
        if lowered in {"exit", "quit"}:
            break
        if lowered in {"help", "/help"}:
            print(renderer.render_help(), file=renderer.stream)
            continue
        if lowered in {"clear", "/clear"}:
            print(renderer.clear_screen(), end="", file=renderer.stream)
            print(renderer.render_banner(workspace_root, args.config), file=renderer.stream)
            continue

        harness.ch_input.queue(prompt)
        harness.run()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
