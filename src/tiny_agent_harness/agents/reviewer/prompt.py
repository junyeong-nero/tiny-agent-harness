from tiny_agent_harness.agents.shared import format_tool_catalog
from tiny_agent_harness.providers import ChatMessage
from tiny_agent_harness.schemas import AppConfig, ExecutorResult, Task, ToolRequirement


def build_initial_messages(
    task: Task,
    executor_result: ExecutorResult,
    config: AppConfig,
    tool_requirements: list[ToolRequirement],
) -> list[ChatMessage]:
    tool_catalog = format_tool_catalog(tool_requirements)

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
                f"configured_model: {config.models.reviewer}"
            ),
        },
    ]
