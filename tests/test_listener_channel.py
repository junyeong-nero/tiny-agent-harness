import sys
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cli import collecting_listener
from tiny_agent_harness.handlers.listener import ListenerChannel
from tiny_agent_harness.schemas import ListenerEvent


class ListenerChannelTestCase(unittest.TestCase):
    def test_listener_channel_dispatches_to_registered_channels(self) -> None:
        listener = ListenerChannel()
        events: list[ListenerEvent] = []
        calls: list[tuple[str, ListenerEvent]] = []

        listener.add_channel("collector", collecting_listener(events))
        listener.add_channel("audit", lambda name, event: calls.append((name, event)))

        event = ListenerEvent(kind="llm_request", agent="executor", message="sending request")

        listener.call(event)

        self.assertEqual(events, [event])
        self.assertEqual(calls, [("audit", event)])


if __name__ == "__main__":
    unittest.main()
