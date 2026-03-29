from tiny_agent_harness.channels import EgressQueue
from tiny_agent_harness.output_handlers import OutputHandler
from tiny_agent_harness.schemas import OutputEvent


class EgressDispatcher:
    def __init__(
        self,
        egress_queue: EgressQueue,
        handlers: list[OutputHandler] | None = None,
    ) -> None:
        self.egress_queue = egress_queue
        self.handlers = handlers or []

    def register(self, handler: OutputHandler) -> None:
        self.handlers.append(handler)

    def dispatch_next(self) -> OutputEvent | None:
        event = self.egress_queue.receive()
        if event is None:
            return None

        for handler in self.handlers:
            handler.handle(event)
        return event

    def drain(self) -> list[OutputEvent]:
        events = self.egress_queue.drain()
        for event in events:
            for handler in self.handlers:
                handler.handle(event)
        return events
