from collections import deque

from tiny_agent_harness.schemas import Request


class IngressQueue:
    def __init__(self) -> None:
        self._queue: deque[Request] = deque()

    def push(self, request: Request) -> None:
        self._queue.append(request)

    def receive(self) -> Request | None:
        if self.is_empty():
            return None
        return self._queue.popleft()

    def flush(self):
        self._queue.clear()

    def is_empty(self) -> bool:
        return not self._queue
