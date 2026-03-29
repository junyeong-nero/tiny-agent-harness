from typing import Protocol

from tiny_agent_harness.providers import ChatMessage
from tiny_agent_harness.schemas import AppConfig, ExecutorResult, ExecutorStep, Task
from tiny_agent_harness.agents.executor.prompt import build_messages
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
    tool_results: list[str] = []

    for _ in range(max_tool_steps):
        step = llm_client.chat_structured(
            messages=build_messages(task, config, tool_requirements, tool_results),
            agent_name="executor",
            response_model=ExecutorStep,
        )

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
                artifacts=[],
            )

        try:
            result = tool_caller.run_call(
                step.tool_call,
                actor="executor",
                allowed_tool_names=task.allowed_tools,
            )
        except ValueError as exc:
            return ExecutorResult(
                status="failed",
                summary=str(exc),
                artifacts=[],
            )
        tool_results.append(_format_tool_result(result))

    return ExecutorResult(
        status="failed",
        summary="executor exceeded maximum tool steps",
        artifacts=[],
    )


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
            messages=build_messages(task, config, [], []),
            agent_name="executor",
            response_model=ExecutorStep,
        )
        if step.status == "tool_call":
            return ExecutorResult(
                status="failed",
                summary="executor requested a tool, but no tool registry was provided",
                artifacts=[],
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
