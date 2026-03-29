from tiny_agent_harness.providers import ChatMessage
from tiny_agent_harness.schemas import AppConfig, Task, ToolRequirement


def _format_tool_results(tool_results: list[str]) -> str:
    if not tool_results:
        return "none"
    return "\n\n".join(tool_results)


def build_messages(
    task: Task,
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
                "You are the executor agent. Either choose one tool call or return a final result. "
                "Use status='tool_call' when a tool is needed. Use status='completed' or "
                "status='failed' only when returning a final answer."
            ),
        },
        {
            "role": "user",
            "content": (
                f"task_id: {task.id}\n"
                f"instructions: {task.instructions}\n"
                f"context: {task.context}\n"
                f"allowed_tools: {', '.join(task.allowed_tools)}\n"
                f"tool_catalog:\n{tool_catalog}\n"
                f"tool_results:\n{_format_tool_results(tool_results)}\n"
                f"configured_model: {config.models.executor}"
            ),
        },
    ]
