import sys
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tiny_agent_harness.channels import (
    EgressQueue,
    IngressQueue,
    InputChannel,
    OutputChannel,
)
from tiny_agent_harness.schemas import (
    InputRequest,
    OutputEvent,
    RunOutput,
    RunRequest,
    RunResult,
    RunState,
)


class ChannelsTestCase(unittest.TestCase):
    def test_local_ingress_queue_preserves_fifo_order(self) -> None:
        ingress_queue = IngressQueue()
        first = InputRequest(message_id="msg-1", payload=RunRequest(prompt="first"))
        second = InputRequest(message_id="msg-2", payload=RunRequest(prompt="second"))

        ingress_queue.push(first)
        ingress_queue.push(second)

        self.assertEqual(ingress_queue.receive(), first)
        self.assertEqual(ingress_queue.receive(), second)
        self.assertTrue(ingress_queue.is_empty())

    def test_input_channel_queue_and_dequeue(self) -> None:
        input_channel = InputChannel(message_prefix="test")

        first = input_channel.queue("first goal", session_id="session-a")
        second = input_channel.queue("second goal", session_id="session-b")

        self.assertEqual(first.message_id, "test-1")
        self.assertEqual(second.message_id, "test-2")
        self.assertEqual(input_channel.dequeue(), first)
        self.assertEqual(input_channel.dequeue(), second)
        self.assertTrue(input_channel.is_empty())

    def test_egress_queue_preserves_fifo_order(self) -> None:
        egress_queue = EgressQueue()
        first = OutputEvent(
            event_id="evt-1",
            session_id="session-a",
            payload=RunOutput(
                request=RunRequest(prompt="first"),
                state=RunState(task="first", done=True),
                result=RunResult(status="completed", summary="first done"),
            ),
        )
        second = OutputEvent(
            event_id="evt-2",
            session_id="session-b",
            payload=RunOutput(
                request=RunRequest(prompt="second"),
                state=RunState(task="second", done=False),
                result=RunResult(status="needs_retry", summary="second retry"),
            ),
        )

        egress_queue.send(first)
        egress_queue.send(second)

        self.assertEqual(egress_queue.receive(), first)
        self.assertEqual(egress_queue.receive(), second)
        self.assertTrue(egress_queue.is_empty())

    def test_output_channel_dispatches_to_registered_channels(self) -> None:
        output_channel = OutputChannel()
        calls: list[tuple[str, OutputEvent]] = []

        output_channel.add_channel(
            "console", lambda name, event: calls.append((name, event))
        )
        output_channel.add_channel(
            "collector", lambda name, event: calls.append((name, event))
        )

        event = OutputEvent(
            event_id="evt-1",
            session_id="session-a",
            payload=RunOutput(
                request=RunRequest(prompt="demo"),
                state=RunState(task="demo", done=True),
                result=RunResult(status="completed", summary="done"),
            ),
        )

        output_channel.call(event)

        self.assertEqual(
            calls,
            [
                ("console", event),
                ("collector", event),
            ],
        )


if __name__ == "__main__":
    unittest.main()
