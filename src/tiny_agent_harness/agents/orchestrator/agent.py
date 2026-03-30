from tiny_agent_harness.agents.base_agent import BaseAgent
from tiny_agent_harness.agents.shared import SupportsStructuredLLM
from tiny_agent_harness.agents.orchestrator.prompt import (
    EXECUTOR_TOOLS,
    ORCHESTRATOR_TOOLS,
    build_messages,
)
from tiny_agent_harness.schemas import (
    AppConfig,
    ExecutorInput,
    OrchestratorOutput,
    OrchestratorStep,
    RunState,
)
from tiny_agent_harness.tools import ToolCaller


def _build_fallback_task(state: RunState, reason: str) -> ExecutorInput:
    return ExecutorInput(
        id=f"task-{state.step_count + 1}",
        instructions=state.task,
        context=f"Fallback task for goal '{state.task}'. reason={reason}",
        allowed_tools=EXECUTOR_TOOLS,
    )


class OrchestratorAgent(BaseAgent[RunState, OrchestratorStep]):
    def __init__(
        self,
        llm_client: SupportsStructuredLLM,
        tool_caller: ToolCaller,
        config: AppConfig,
    ):
        super().__init__(
            agent_name="orchestrator",
            llm_client=llm_client,
            tool_caller=tool_caller,
            config=config,
            message_builder=build_messages,
            input_schema=RunState,
            output_schema=OrchestratorStep,
            max_tool_steps=config.runtime.orchestrator_max_tool_steps,
            allowed_tools=ORCHESTRATOR_TOOLS,
        )

    def run(self, state: RunState) -> OrchestratorOutput:
        from tiny_agent_harness.agents.executor import executor_agent

        step = super().run(state)

        if step.status == "reply":
            return OrchestratorOutput(reply=step.summary)

        if step.status == "delegate" and step.task is not None:
            task = step.task
        else:
            task = _build_fallback_task(
                state, "orchestrator exceeded maximum tool steps or returned delegate without task"
            )

        executor_result = executor_agent(task, self.config, self.client, self.tool_caller)
        return OrchestratorOutput(task=task, executor_result=executor_result)


def orchestrator_agent(
    state: RunState,
    config: AppConfig,
    llm_client: SupportsStructuredLLM | None = None,
    tool_caller: ToolCaller | None = None,
) -> OrchestratorOutput:
    from tiny_agent_harness.agents.executor import executor_agent

    if llm_client is not None and tool_caller is not None:
        return OrchestratorAgent(llm_client, tool_caller, config).run(state)

    if llm_client is not None:
        step = llm_client.chat_structured(
            messages=build_messages(state, config, []),
            agent_name="orchestrator",
            response_model=OrchestratorStep,
        )
        if step.status == "tool_call":
            task = _build_fallback_task(
                state,
                "orchestrator requested a tool, but no tool registry was provided",
            )
        elif step.task is None:
            task = _build_fallback_task(
                state, "orchestrator returned delegate status without a task"
            )
        else:
            task = step.task
    else:
        task = ExecutorInput(
            id=f"task-{state.step_count + 1}",
            instructions=state.task,
            context=(
                f"Plan the next action for goal '{state.task}'. "
                f"orchestrator model={config.models.orchestrator}"
            ),
            allowed_tools=EXECUTOR_TOOLS,
        )

    executor_result = executor_agent(
        task, config, llm_client=llm_client, tool_caller=tool_caller
    )
    return OrchestratorOutput(task=task, executor_result=executor_result)
