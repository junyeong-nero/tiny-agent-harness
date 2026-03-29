from tiny_agent_harness.agents.shared import SupportsStructuredLLM, format_tool_result
from tiny_agent_harness.agents.orchestrator.prompt import (
    EXECUTOR_TOOLS,
    ORCHESTRATOR_TOOLS,
    build_initial_messages,
)
from tiny_agent_harness.schemas import AppConfig, OrchestratorStep, RunState, Task
from tiny_agent_harness.tools import ToolCaller


def _build_fallback_task(state: RunState, reason: str) -> Task:
    return Task(
        id=f"task-{state.step_count + 1}",
        instructions=state.task,
        context=f"Fallback task for goal '{state.task}'. reason={reason}",
        allowed_tools=EXECUTOR_TOOLS,
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
    messages = build_initial_messages(state, config, tool_requirements)

    for _ in range(max_tool_steps):
        step = llm_client.chat_structured(
            messages=messages,
            agent_name="orchestrator",
            response_model=OrchestratorStep,
        )
        messages = messages + [{"role": "assistant", "content": step.model_dump_json()}]

        if step.status == "completed":
            if step.task is None:
                return _build_fallback_task(
                    state, "orchestrator returned completed status without a task"
                )
            return step.task

        if step.tool_call is None:
            return _build_fallback_task(
                state, "orchestrator returned tool_call status without a tool_call payload"
            )

        result = tool_caller.run_call(
            step.tool_call,
            actor="orchestrator",
            allowed_tool_names=ORCHESTRATOR_TOOLS,
        )
        messages = messages + [{"role": "user", "content": format_tool_result(result)}]

    return _build_fallback_task(state, "orchestrator exceeded maximum tool steps")


def orchestrator_agent(
    state: RunState,
    config: AppConfig,
    llm_client: SupportsStructuredLLM | None = None,
    tool_caller: ToolCaller | None = None,
) -> Task:
    if llm_client is not None and tool_caller is not None:
        return _execute_with_tools(
            state, config, llm_client=llm_client, tool_caller=tool_caller
        )

    if llm_client is not None:
        step = llm_client.chat_structured(
            messages=build_initial_messages(state, config, []),
            agent_name="orchestrator",
            response_model=OrchestratorStep,
        )
        if step.status == "tool_call":
            return _build_fallback_task(
                state, "orchestrator requested a tool, but no tool registry was provided"
            )
        if step.task is None:
            return _build_fallback_task(
                state, "orchestrator returned completed status without a task"
            )
        return step.task

    return Task(
        id=f"task-{state.step_count + 1}",
        instructions=state.task,
        context=(
            f"Plan the next action for goal '{state.task}'. "
            f"orchestrator model={config.models.orchestrator}"
        ),
        allowed_tools=EXECUTOR_TOOLS,
    )
