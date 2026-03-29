import json
import sys
from pathlib import Path
from typing import Callable

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
        content = truncate(
            str(event.data.get("content", "") or event.data.get("error", ""))
        )
        print(f"{agent}← {tool} [{status}] {content}")
        return

    print(f"{agent}{event.message}".rstrip())


def console_output_handler(_: str, event: OutputEvent) -> None:
    print(event.payload.result.summary)


def main() -> int:

    project_root = Path(__file__).resolve().parents[1]
    config = load_config(project_root / "config.yaml")

    harness = Harness(
        config=config,
        workspace_root=str(project_root),
    )
    harness.ch_output.add_channel("console", console_output_handler)
    harness.ch_listener.add_channel("console", console_listener)

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
    main()
