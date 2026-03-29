from tiny_agent_harness.providers import ChatMessage
from tiny_agent_harness.schemas import AppConfig, ExecutorResult, Task, ToolRequirement


def _format_tool_results(tool_results: list[str]) -> str:
    if not tool_results:
        return "none"
    return "\n\n".join(tool_results)


def build_messages(
    task: Task,
    executor_result: ExecutorResult,
    config: AppConfig,
    tool_requirements: list[ToolRequirement],
    tool_results: list[str],
) -> list[ChatMessage]:
    tool_catalog = "\n".join(
        f"- {req.name}: {req.description}\n  schema: {req.arguments_schema}"
        for req in tool_requirements
    ) or "none"

    return [
        {
            "role": "system",
            "content": (
                "You are the reviewer agent. Inspect the executor result and either choose "
                "one read-only tool call or return a final review decision. Use "
                "status='tool_call' when more inspection is needed. Use status='completed' "
                "only when returning the final review decision."
            ),
        },
        {
            "role": "user",
            "content": (
                f"task_id: {task.id}\n"
                f"instructions: {task.instructions}\n"
                f"context: {task.context}\n"
                f"executor_status: {executor_result.status}\n"
                f"executor_summary: {executor_result.summary}\n"
                f"artifacts: {', '.join(executor_result.artifacts)}\n"
                f"tool_catalog:\n{tool_catalog}\n"
                f"tool_results:\n{_format_tool_results(tool_results)}\n"
                f"configured_model: {config.models.reviewer}"
            ),
        },
    ]
