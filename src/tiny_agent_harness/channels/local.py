from collections import deque

from tiny_agent_harness.channels.base import EgressQueue, IngressQueue
from tiny_agent_harness.schemas import InputRequest, OutputEvent


class LocalIngressQueue(IngressQueue):
    def __init__(self) -> None:
        self._queue: deque[InputRequest] = deque()

    def push(self, request: InputRequest) -> None:
        self._queue.append(request)

    def receive(self) -> InputRequest | None:
        if self.is_empty():
            return None
        return self._queue.popleft()

    def is_empty(self) -> bool:
        return not self._queue


class LocalEgressQueue(EgressQueue):
    def __init__(self) -> None:
        self._queue: deque[OutputEvent] = deque()

    def send(self, event: OutputEvent) -> None:
        self._queue.append(event)

    def receive(self) -> OutputEvent | None:
        if self.is_empty():
            return None
        return self._queue.popleft()

    def drain(self) -> list[OutputEvent]:
        items = list(self._queue)
        self._queue.clear()
        return items

    def is_empty(self) -> bool:
        return not self._queue
