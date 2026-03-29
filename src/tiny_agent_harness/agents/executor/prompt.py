from tiny_agent_harness.providers import ChatMessage
from tiny_agent_harness.schemas import AppConfig, Task


def build_messages(task: Task, config: AppConfig) -> list[ChatMessage]:
    return [
        {
            "role": "system",
            "content": (
                "You are the executor agent. Execute the task and return only an ExecutorResult."
            ),
        },
        {
            "role": "user",
            "content": (
                f"task_id: {task.id}\n"
                f"instructions: {task.instructions}\n"
                f"context: {task.context}\n"
                f"allowed_tools: {', '.join(task.allowed_tools)}\n"
                f"configured_model: {config.models.executor}"
            ),
        },
    ]
