from tiny_agent_harness.agents.base_agent import BaseAgent
from tiny_agent_harness.agents.shared import SupportsStructuredLLM
from tiny_agent_harness.agents.worker.prompt import build_messages
from tiny_agent_harness.schemas import (
    AppConfig,
    WorkerOutput,
    WorkerStep,
    WorkerInput,
)
from tiny_agent_harness.tools import ToolCaller


class WorkerAgent(BaseAgent[WorkerInput, WorkerStep]):
    def __init__(
        self,
        llm_client: SupportsStructuredLLM,
        tool_caller: ToolCaller,
        config: AppConfig,
    ):
        super().__init__(
            agent_name="worker",
            llm_client=llm_client,
            tool_caller=tool_caller,
            config=config,
            message_builder=build_messages,
            input_schema=WorkerInput,
            output_schema=WorkerStep,
            max_tool_steps=config.runtime.worker_max_tool_steps,
        )

    def _get_allowed_tools(self, subtask: WorkerInput) -> list[str]:
        return subtask.allowed_tools

    def run(self, subtask: WorkerInput) -> WorkerOutput:
        worker_step = super().run(subtask)
        if worker_step.status in {"completed", "failed"}:
            return WorkerOutput(
                status=worker_step.status,
                summary=worker_step.summary,
                artifacts=worker_step.artifacts,
            )
        return WorkerOutput(
            status="failed", summary="worker exceeded maximum tool steps"
        )


def worker_agent(
    subtask: WorkerInput,
    config: AppConfig,
    llm_client: SupportsStructuredLLM,
    tool_caller: ToolCaller,
) -> WorkerOutput:

    return WorkerAgent(llm_client, tool_caller, config).run(subtask)
