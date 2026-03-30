from tiny_agent_harness.agents.base_agent import BaseAgent
from tiny_agent_harness.agents.shared import SupportsStructuredLLM
from tiny_agent_harness.agents.executor.prompt import build_messages
from tiny_agent_harness.schemas import (
    AppConfig,
    ExecutorInput,
    ExecutorOutput,
    ExecutorStep,
)
from tiny_agent_harness.tools import ToolCaller


class ExecutorAgent(BaseAgent[ExecutorInput, ExecutorStep]):
    def __init__(
        self,
        llm_client: SupportsStructuredLLM,
        tool_caller: ToolCaller,
        config: AppConfig,
    ):
        super().__init__(
            agent_name="executor",
            llm_client=llm_client,
            tool_caller=tool_caller,
            config=config,
            message_builder=build_messages,
            input_schema=ExecutorInput,
            output_schema=ExecutorStep,
            max_tool_steps=config.runtime.executor_max_tool_steps,
        )

    def _get_allowed_tools(self, data: ExecutorInput) -> list[str]:
        return data.allowed_tools

    def run(self, task: ExecutorInput) -> ExecutorOutput:
        step = super().run(task)
        if step.status in {"completed", "failed"}:
            return ExecutorOutput(
                status=step.status,
                summary=step.summary,
                artifacts=step.artifacts,
            )
        return ExecutorOutput(
            status="failed", summary="executor exceeded maximum tool steps"
        )


def executor_agent(
    task: ExecutorInput,
    config: AppConfig,
    llm_client: SupportsStructuredLLM | None = None,
    tool_caller: ToolCaller | None = None,
) -> ExecutorOutput:
    if llm_client is not None and tool_caller is not None:
        return ExecutorAgent(llm_client, tool_caller, config).run(task)

    if llm_client is not None:
        step = llm_client.chat_structured(
            messages=build_messages(task, config, []),
            agent_name="executor",
            response_model=ExecutorStep,
        )
        if step.status == "tool_call":
            return ExecutorOutput(
                status="failed",
                summary="executor requested a tool, but no tool registry was provided",
            )
        return ExecutorOutput(
            status=step.status,
            summary=step.summary,
            artifacts=step.artifacts,
        )

    return ExecutorOutput(
        status="completed",
        summary=(
            f"executor mock completed '{task.instructions}' "
            f"with model {config.models.executor}"
        ),
        artifacts=[task.id],
    )
