import json
import sys
from pathlib import Path
from typing import Callable

from tiny_agent_harness.channels.input import InputChannel
from tiny_agent_harness.channels.output import OutputChannel
from tiny_agent_harness.handlers.listener import ListenerChannel
from tiny_agent_harness.runtime import Harness
from tiny_agent_harness.schemas import (
    ListenerEvent,
    OutputEvent,
    load_config,
)
from tiny_agent_harness.utils import truncate


def collecting_listener(
    events: list[ListenerEvent],
) -> Callable[[str, ListenerEvent], None]:
    def _collect(_: str, event: ListenerEvent) -> None:
        events.append(event)

    return _collect


def console_listener(_: str, event: ListenerEvent) -> None:
    agent = f"[{event.agent}] " if event.agent else ""

    if event.kind == "llm_request":
        return

    if event.kind == "llm_response":
        raw = event.data.get("content", "")
        try:
            summary = json.loads(raw).get("summary", "").strip()
        except (json.JSONDecodeError, AttributeError):
            summary = truncate(str(raw))
        if summary:
            print(f"{agent}{summary}")
        return

    if event.kind == "llm_error":
        print(f"{agent}error: {event.message}")
        return

    if event.kind == "tool_call_started":
        tool = event.data.get("tool", "unknown")
        args = truncate(str(event.data.get("arguments", {})))
        print(f"{agent}→ {tool}({args})")
        return

    if event.kind == "tool_call_finished":
        tool = event.data.get("tool", "unknown")
        ok = event.data.get("ok", False)
        status = "ok" if ok else "failed"
        content = truncate(str(event.data.get("content", "") or event.data.get("error", "")))
        print(f"{agent}← {tool} [{status}] {content}")
        return

    print(f"{agent}{event.message}".rstrip())


def console_output_handler(_: str, event: OutputEvent) -> None:
    print(event.payload.result.summary)


def _build_harness(project_root: Path) -> tuple[Harness, InputChannel]:
    config = load_config(project_root / "config.yaml")

    ch_input = InputChannel()

    ch_listener = ListenerChannel()
    ch_listener.add_channel("console", console_listener)

    ch_output = OutputChannel()
    ch_output.add_channel("console", console_output_handler)

    harness = Harness(
        config=config,
        workspace_root=str(project_root),
        ch_input=ch_input,
        ch_listener=ch_listener,
        ch_output=ch_output,
    )
    return harness, ch_input


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    project_root = Path(__file__).resolve().parents[1]
    harness, ch_input = _build_harness(project_root)

    if args:
        ch_input.queue(" ".join(args))
        harness.run()
        return 0

    print("tiny-agent interactive mode (type 'exit' or press Ctrl+D to quit)")
    while True:
        try:
            goal = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not goal:
            continue
        if goal.lower() in {"exit", "quit"}:
            break

        ch_input.queue(goal)
        harness.run()

    return 0


if __name__ == "__main__":
    main()
