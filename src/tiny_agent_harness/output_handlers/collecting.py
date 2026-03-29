from tiny_agent_harness.output_handlers.base import OutputHandler
from tiny_agent_harness.schemas import OutputEvent


class CollectingOutputHandler(OutputHandler):
    def __init__(self) -> None:
        self.events: list[OutputEvent] = []

    def handle(self, event: OutputEvent) -> None:
        self.events.append(event)
