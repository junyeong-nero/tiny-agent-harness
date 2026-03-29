from tiny_agent_harness.agents.shared import SupportsStructuredLLM, format_tool_result
from tiny_agent_harness.agents.reviewer.prompt import build_initial_messages
from tiny_agent_harness.schemas import (
    AppConfig,
    ExecutorResult,
    ReviewResult,
    ReviewerStep,
    Task,
)
from tiny_agent_harness.tools import ToolCaller


def _execute_with_tools(
    task: Task,
    executor_result: ExecutorResult,
    config: AppConfig,
    llm_client: SupportsStructuredLLM,
    tool_caller: ToolCaller,
) -> ReviewResult:
    max_tool_steps = config.runtime.reviewer_max_tool_steps
    tool_requirements = tool_caller.available_tool_requirements(actor="reviewer")
    messages = list(build_initial_messages(task, executor_result, config, tool_requirements))

    for _ in range(max_tool_steps):
        step = llm_client.chat_structured(
            messages=messages,
            agent_name="reviewer",
            response_model=ReviewerStep,
        )
        messages = messages + [{"role": "assistant", "content": step.model_dump_json()}]

        if step.status == "completed":
            if step.decision is None:
                return ReviewResult(
                    decision="retry",
                    feedback="reviewer returned completed status without a decision",
                )
            return ReviewResult(decision=step.decision, feedback=step.summary)

        if step.tool_call is None:
            return ReviewResult(
                decision="retry",
                feedback="reviewer returned tool_call status without a tool_call payload",
            )

        try:
            result = tool_caller.run_call(step.tool_call, actor="reviewer")
        except ValueError as exc:
            return ReviewResult(decision="retry", feedback=str(exc))

        messages = messages + [{"role": "user", "content": format_tool_result(result)}]

    return ReviewResult(decision="retry", feedback="reviewer exceeded maximum tool steps")


def reviewer_agent(
    task: Task,
    executor_result: ExecutorResult,
    config: AppConfig,
    llm_client: SupportsStructuredLLM | None = None,
    tool_caller: ToolCaller | None = None,
) -> ReviewResult:
    if llm_client is not None and tool_caller is not None:
        return _execute_with_tools(
            task, executor_result, config, llm_client=llm_client, tool_caller=tool_caller
        )

    if llm_client is not None:
        step = llm_client.chat_structured(
            messages=build_initial_messages(task, executor_result, config, []),
            agent_name="reviewer",
            response_model=ReviewerStep,
        )
        if step.status == "tool_call":
            return ReviewResult(
                decision="retry",
                feedback="reviewer requested a tool, but no tool registry was provided",
            )
        if step.decision is None:
            return ReviewResult(
                decision="retry",
                feedback="reviewer returned completed status without a decision",
            )
        return ReviewResult(decision=step.decision, feedback=step.summary)

    if executor_result.status != "completed":
        return ReviewResult(
            decision="retry",
            feedback=(
                f"reviewer mock rejected task {task.id} "
                f"with model {config.models.reviewer}"
            ),
        )
    return ReviewResult(
        decision="approve",
        feedback=(
            f"reviewer mock approved task {task.id} "
            f"with model {config.models.reviewer}"
        ),
    )
