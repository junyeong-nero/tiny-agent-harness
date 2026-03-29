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
    OutputEventDispatcher,
    RequestProcessor,
)
from tiny_agent_harness.output_handlers import CollectingOutputHandler
from tiny_agent_harness.schemas import InputRequest, RunRequest, load_config


class ChannelsTestCase(unittest.TestCase):
    def test_local_ingress_queue_preserves_fifo_order(self) -> None:
        ingress_queue = IngressQueue()
        first = InputRequest(message_id="msg-1", payload=RunRequest(goal="first"))
        second = InputRequest(message_id="msg-2", payload=RunRequest(goal="second"))

        ingress_queue.push(first)
        ingress_queue.push(second)

        self.assertEqual(ingress_queue.receive(), first)
        self.assertEqual(ingress_queue.receive(), second)
        self.assertTrue(ingress_queue.is_empty())

    def test_request_processor_drains_multiple_requests(self) -> None:
        config = load_config(ROOT_DIR / "config.yaml")
        ingress_queue = IngressQueue()
        egress_queue = EgressQueue()
        processor = RequestProcessor(
            ingress_queue=ingress_queue,
            egress_queue=egress_queue,
            config=config,
        )

        ingress_queue.push(
            InputRequest(message_id="msg-1", payload=RunRequest(goal="first goal"))
        )
        ingress_queue.push(
            InputRequest(message_id="msg-2", payload=RunRequest(goal="second goal"))
        )

        outputs = processor.drain()

        self.assertEqual(len(outputs), 2)
        self.assertEqual(outputs[0].session_id, "default")
        self.assertEqual(outputs[0].payload.request.goal, "first goal")
        self.assertEqual(outputs[0].payload.result.status, "completed")
        self.assertEqual(outputs[1].payload.request.goal, "second goal")
        self.assertTrue(ingress_queue.is_empty())
        self.assertEqual(egress_queue.drain(), outputs)

    def test_egress_dispatcher_sends_events_to_registered_handlers(self) -> None:
        config = load_config(ROOT_DIR / "config.yaml")
        ingress_queue = IngressQueue()
        egress_queue = EgressQueue()
        processor = RequestProcessor(
            ingress_queue=ingress_queue,
            egress_queue=egress_queue,
            config=config,
        )
        collector = CollectingOutputHandler()
        dispatcher = OutputEventDispatcher(
            egress_queue=egress_queue,
            handlers=[collector],
        )

        ingress_queue.push(
            InputRequest(message_id="msg-1", payload=RunRequest(goal="first goal"))
        )
        processor.process_next()
        dispatched = dispatcher.dispatch_next()

        self.assertIsNotNone(dispatched)
        self.assertEqual(len(collector.events), 1)
        self.assertEqual(collector.events[0].payload.request.goal, "first goal")
        self.assertTrue(egress_queue.is_empty())


if __name__ == "__main__":
    unittest.main()
