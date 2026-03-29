from typing import Protocol

from tiny_agent_harness.agents.orchestrator.prompt import (
    EXECUTOR_TOOLS,
    ORCHESTRATOR_TOOLS,
    build_messages,
)
from tiny_agent_harness.providers import ChatMessage
from tiny_agent_harness.schemas import AppConfig, OrchestratorStep, RunState, Task
from tiny_agent_harness.tools import ToolCaller, ToolResult


class SupportsStructuredLLM(Protocol):
    def chat_structured(
        self,
        messages: list[ChatMessage],
        agent_name: str,
        response_model: type,
        model: str | None = None,
        max_retries: int | None = None,
    ): ...


def _format_tool_result(result: ToolResult) -> str:
    return (
        f"tool={result.tool}\n"
        f"ok={result.ok}\n"
        f"content={result.content}\n"
        f"error={result.error or ''}"
    )


def _execute_with_tools(
    state: RunState,
    config: AppConfig,
    llm_client: SupportsStructuredLLM,
    tool_caller: ToolCaller,
) -> Task:
    max_tool_steps = config.runtime.orchestrator_max_tool_steps
    tool_requirements = tool_caller.available_tool_requirements(
        actor="orchestrator",
        allowed_tool_names=ORCHESTRATOR_TOOLS,
    )
    tool_results: list[str] = []

    for _ in range(max_tool_steps):
        step = llm_client.chat_structured(
            messages=build_messages(state, config, tool_requirements, tool_results),
            agent_name="orchestrator",
            response_model=OrchestratorStep,
        )

        if step.status == "completed":
            if step.task is None:
                raise ValueError("orchestrator returned completed status without a task")
            return step.task

        if step.tool_call is None:
            raise ValueError("orchestrator returned tool_call status without a tool_call payload")

        result = tool_caller.run_call(
            step.tool_call,
            actor="orchestrator",
            allowed_tool_names=ORCHESTRATOR_TOOLS,
        )
        tool_results.append(_format_tool_result(result))

    raise ValueError("orchestrator exceeded maximum tool steps")


def orchestrator_agent(
    state: RunState,
    config: AppConfig,
    llm_client: SupportsStructuredLLM | None = None,
    tool_caller: ToolCaller | None = None,
) -> Task:
    if llm_client is not None and tool_caller is not None:
        return _execute_with_tools(state, config, llm_client=llm_client, tool_caller=tool_caller)

    if llm_client is not None:
        step = llm_client.chat_structured(
            messages=build_messages(state, config, [], []),
            agent_name="orchestrator",
            response_model=OrchestratorStep,
        )
        if step.status == "tool_call":
            raise ValueError("orchestrator requested a tool, but no tool registry was provided")
        if step.task is None:
            raise ValueError("orchestrator returned completed status without a task")
        return step.task

    return Task(
        id=f"task-{state.step_count + 1}",
        instructions=state.goal,
        context=(
            f"Plan the next action for goal '{state.goal}'. "
            f"orchestrator model={config.models.orchestrator}"
        ),
        allowed_tools=EXECUTOR_TOOLS,
    )
