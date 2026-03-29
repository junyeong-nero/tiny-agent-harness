from abc import ABC, abstractmethod

from tiny_agent_harness.schemas import OutputEvent


class OutputHandler(ABC):
    @abstractmethod
    def handle(self, event: OutputEvent) -> None:
        raise NotImplementedError
