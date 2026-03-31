from tiny_agent_harness.agents.tool_calling_agent import ToolCallingAgent
from tiny_agent_harness.agents.protocols import SupportsStructuredLLM
from tiny_agent_harness.agents.worker.prompt import build_messages
from tiny_agent_harness.schemas import (
    WorkerOutput,
    WorkerInput,
)
from tiny_agent_harness.tools import ToolCaller


class WorkerAgent(ToolCallingAgent[WorkerInput, WorkerOutput]):
    def __init__(
        self,
        llm_client: SupportsStructuredLLM,
        tool_caller: ToolCaller,
    ):
        super().__init__(
            agent_name="worker",
            llm_client=llm_client,
            tool_caller=tool_caller,
            message_builder=build_messages,
            input_schema=WorkerInput,
            output_schema=WorkerOutput,
        )

    def run(self, subtask: WorkerInput) -> WorkerOutput:
        return super().run(subtask)
