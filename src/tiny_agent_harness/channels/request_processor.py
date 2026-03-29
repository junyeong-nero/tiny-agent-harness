from tiny_agent_harness.channels.queue import EgressQueue, IngressQueue
from tiny_agent_harness.runtime import run_harness
from tiny_agent_harness.schemas import AppConfig, OutputEvent, RunOutput
from tiny_agent_harness.tools import ToolCaller


class RequestProcessor:
    def __init__(
        self,
        ingress_queue: IngressQueue,
        egress_queue: EgressQueue,
        config: AppConfig,
        llm_client=None,
        tool_caller: ToolCaller | None = None,
    ) -> None:
        self.ingress_queue = ingress_queue
        self.egress_queue = egress_queue
        self.config = config
        self.llm_client = llm_client
        self.tool_caller = tool_caller

    def process_next(self) -> OutputEvent | None:
        request = self.ingress_queue.receive()
        if request is None:
            return None

        if request.kind != "run_request":
            raise ValueError(f"unsupported input request kind: {request.kind}")

        state, result = run_harness(
            request.payload,
            self.config,
            llm_client=self.llm_client,
            tool_caller=self.tool_caller,
        )
        output = OutputEvent(
            event_id=f"{request.message_id}:run_result",
            session_id=request.session_id,
            payload=RunOutput(
                request=request.payload,
                state=state,
                result=result,
            ),
        )
        self.egress_queue.send(output)
        return output

    def drain(self) -> list[OutputEvent]:
        outputs: list[OutputEvent] = []
        while True:
            output = self.process_next()
            if output is None:
                return outputs
            outputs.append(output)

    def is_idle(self) -> bool:
        return self.ingress_queue.is_empty()
