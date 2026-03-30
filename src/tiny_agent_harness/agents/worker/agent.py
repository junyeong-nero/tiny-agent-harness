from tiny_agent_harness.agents.base_agent import BaseAgent
from tiny_agent_harness.agents.shared import SupportsStructuredLLM
from tiny_agent_harness.agents.worker.prompt import build_messages
from tiny_agent_harness.schemas import (
    AppConfig,
    WorkerInput,
    WorkerOutput,
    WorkerStep,
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

    def _get_allowed_tools(self, data: WorkerInput) -> list[str]:
        return data.allowed_tools

    def run(self, task: WorkerInput) -> WorkerOutput:
        step = super().run(task)
        if step.status in {"completed", "failed"}:
            return WorkerOutput(
                status=step.status,
                summary=step.summary,
                artifacts=step.artifacts,
            )
        return WorkerOutput(
            status="failed", summary="worker exceeded maximum tool steps"
        )


def worker_agent(
    task: WorkerInput,
    config: AppConfig,
    llm_client: SupportsStructuredLLM | None = None,
    tool_caller: ToolCaller | None = None,
) -> WorkerOutput:
    if llm_client is not None and tool_caller is not None:
        return WorkerAgent(llm_client, tool_caller, config).run(task)

    if llm_client is not None:
        step = llm_client.chat_structured(
            messages=build_messages(task, config, []),
            agent_name="worker",
            response_model=WorkerStep,
        )
        if step.status == "tool_call":
            return WorkerOutput(
                status="failed",
                summary="worker requested a tool, but no tool registry was provided",
            )
        return WorkerOutput(
            status=step.status,
            summary=step.summary,
            artifacts=step.artifacts,
        )

    return WorkerOutput(
        status="completed",
        summary=(
            f"worker mock completed '{task.instructions}' "
            f"with model {config.models.worker}"
        ),
        artifacts=[task.id],
    )
