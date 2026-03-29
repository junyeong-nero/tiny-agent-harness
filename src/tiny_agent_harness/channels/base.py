from abc import ABC, abstractmethod

from tiny_agent_harness.schemas import InputRequest, OutputEvent


class IngressQueue(ABC):
    @abstractmethod
    def push(self, request: InputRequest) -> None:
        raise NotImplementedError

    @abstractmethod
    def receive(self) -> InputRequest | None:
        raise NotImplementedError

    @abstractmethod
    def is_empty(self) -> bool:
        raise NotImplementedError


class EgressQueue(ABC):
    @abstractmethod
    def send(self, event: OutputEvent) -> None:
        raise NotImplementedError

    @abstractmethod
    def receive(self) -> OutputEvent | None:
        raise NotImplementedError

    @abstractmethod
    def drain(self) -> list[OutputEvent]:
        raise NotImplementedError

    @abstractmethod
    def is_empty(self) -> bool:
        raise NotImplementedError
