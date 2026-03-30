from itertools import count
from tiny_agent_harness.channels.queue import IngressQueue
from tiny_agent_harness.schemas import Request
from tiny_agent_harness.schemas.harness import HarnessInput


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

    def queue(self, query: str, session_id: str = "default") -> Request:
        request = Request(
            query=query,
            session_id=session_id,
        )
        self.ingress_queue.push(request)
        return request

    def dequeue(self) -> Request | None:
        return self.ingress_queue.receive()
