from tiny_agent_harness.channels.queue import IngressQueue
from tiny_agent_harness.schemas import Request


class InputChannel:
    def __init__(
        self,
        ingress_queue: IngressQueue | None = None,
    ) -> None:
        self.ingress_queue = ingress_queue or IngressQueue()

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
