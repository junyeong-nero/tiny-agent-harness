from tiny_agent_harness.agents.shared import SupportsStructuredLLM, format_tool_result
from tiny_agent_harness.agents.executor.prompt import build_initial_messages
from tiny_agent_harness.schemas import AppConfig, ExecutorResult, ExecutorStep, Task
from tiny_agent_harness.tools import ToolCaller


def _execute_with_tools(
    task: Task,
    config: AppConfig,
    llm_client: SupportsStructuredLLM,
    tool_caller: ToolCaller,
) -> ExecutorResult:
    max_tool_steps = config.runtime.executor_max_tool_steps
    tool_requirements = tool_caller.available_tool_requirements(
        actor="executor",
        allowed_tool_names=task.allowed_tools,
    )
    messages = list(build_initial_messages(task, config, tool_requirements))

    for _ in range(max_tool_steps):
        step = llm_client.chat_structured(
            messages=messages,
            agent_name="executor",
            response_model=ExecutorStep,
        )
        messages = messages + [{"role": "assistant", "content": step.model_dump_json()}]

        if step.status in {"completed", "failed"}:
            return ExecutorResult(
                status=step.status,
                summary=step.summary,
                artifacts=step.artifacts,
            )

        if step.tool_call is None:
            return ExecutorResult(
                status="failed",
                summary="executor returned tool_call status without a tool_call payload",
            )

        try:
            result = tool_caller.run_call(
                step.tool_call,
                actor="executor",
                allowed_tool_names=task.allowed_tools,
            )
        except ValueError as exc:
            return ExecutorResult(status="failed", summary=str(exc))

        messages = messages + [{"role": "user", "content": format_tool_result(result)}]

    return ExecutorResult(status="failed", summary="executor exceeded maximum tool steps")


def executor_agent(
    task: Task,
    config: AppConfig,
    llm_client: SupportsStructuredLLM | None = None,
    tool_caller: ToolCaller | None = None,
) -> ExecutorResult:
    if llm_client is not None and tool_caller is not None:
        return _execute_with_tools(task, config, llm_client=llm_client, tool_caller=tool_caller)

    if llm_client is not None:
        step = llm_client.chat_structured(
            messages=build_initial_messages(task, config, []),
            agent_name="executor",
            response_model=ExecutorStep,
        )
        if step.status == "tool_call":
            return ExecutorResult(
                status="failed",
                summary="executor requested a tool, but no tool registry was provided",
            )
        return ExecutorResult(
            status=step.status,
            summary=step.summary,
            artifacts=step.artifacts,
        )

    return ExecutorResult(
        status="completed",
        summary=(
            f"executor mock completed '{task.instructions}' "
            f"with model {config.models.executor}"
        ),
        artifacts=[task.id],
    )
