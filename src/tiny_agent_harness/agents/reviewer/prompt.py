from tiny_agent_harness.providers import ChatMessage
from tiny_agent_harness.schemas import AppConfig, ExecutorResult, Task


REVIEWER_TOOLS = ["read_file", "search", "list_files", "git_diff"]


def build_messages(
    task: Task,
    executor_result: ExecutorResult,
    config: AppConfig,
) -> list[ChatMessage]:
    return [
        {
            "role": "system",
            "content": (
                "You are the reviewer agent. Review the executor result and return "
                "only a ReviewResult."
            ),
        },
        {
            "role": "user",
            "content": (
                f"task_id: {task.id}\n"
                f"instructions: {task.instructions}\n"
                f"executor_status: {executor_result.status}\n"
                f"executor_summary: {executor_result.summary}\n"
                f"artifacts: {', '.join(executor_result.artifacts)}\n"
                f"allowed_tools: {', '.join(REVIEWER_TOOLS)}\n"
                f"configured_model: {config.models.reviewer}"
            ),
        },
    ]
