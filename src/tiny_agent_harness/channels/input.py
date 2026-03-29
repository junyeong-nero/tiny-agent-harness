from itertools import count
from tiny_agent_harness.channels.queue import IngressQueue
from tiny_agent_harness.schemas import InputRequest
from tiny_agent_harness.schemas.runtime import RunRequest


class InputChannel:
    def __init__(
        self,
        ingress_queue: IngressQueue | None = None,
        message_prefix: str = "input",
    ) -> None:
        self.ingress_queue = ingress_queue or IngressQueue()
        self.message_prefix = message_prefix
        self._counter = count(start=1)

    def is_empty(self) -> bool:
        return self.ingress_queue.is_empty()

    def queue(self, query: str, session_id: str = "default") -> InputRequest:
        request = InputRequest(
            message_id=f"{self.message_prefix}-{next(self._counter)}",
            session_id=session_id,
            payload=RunRequest(prompt=query),
        )
        self.ingress_queue.push(request)
        return request

    def dequeue(self) -> InputRequest | None:
        return self.ingress_queue.receive()
