import argparse
import json
from pathlib import Path
from typing import Callable, Sequence

from tiny_agent_harness.harness import TinyHarness
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
        content = truncate(
            str(event.data.get("content", "") or event.data.get("error", ""))
        )
        print(f"{agent}← {tool} [{status}] {content}")
        return

    print(f"{agent}{event.message}".rstrip())


def console_output_handler(_: str, event: OutputEvent) -> None:
    print(event.payload.result.summary)


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

    harness = TinyHarness(
        config=config,
        workspace_root=str(workspace_root),
    )
    harness.ch_output.add_channel("console", console_output_handler)
    harness.ch_listener.add_channel("console", console_listener)

    prompt = " ".join(args.prompt).strip()
    if prompt:
        harness.ch_input.queue(prompt)
        harness.run()
        return 0

    print("tiny-agent interactive mode (type 'exit' or press Ctrl+D to quit)")
    while True:
        try:
            prompt = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not prompt:
            continue
        if prompt.lower() in {"exit", "quit"}:
            break

        harness.ch_input.queue(prompt)
        harness.run()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
