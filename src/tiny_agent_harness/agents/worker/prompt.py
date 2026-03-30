from tiny_agent_harness.agents.shared import format_tool_catalog
from tiny_agent_harness.providers import ChatMessage
from tiny_agent_harness.schemas import AppConfig, ToolSpec, WorkerInput


def build_messages(
    worker_task: WorkerInput,
    config: AppConfig,
    tool_specs: list[ToolSpec],
) -> list[ChatMessage]:
    tool_catalog = format_tool_catalog(tool_specs)

    return [
        {
            "role": "system",
            "content": (
                "You are the worker agent. Either choose one tool call or return a final result.\n"
                "Use status='tool_call' when a tool is needed.\n"
                "Use status='completed' or status='failed' only when returning a final answer.\n\n"
                "If the task context is 'conversational' or no tools are listed, "
                "do NOT call any tools. Respond directly with status='completed' "
                "and put your reply in the summary field."
            ),
        },
        {
            "role": "user",
            "content": (
                f"task_id: {worker_task.id}\n"
                f"instructions: {worker_task.instructions}\n"
                f"context: {worker_task.context}\n"
                f"allowed_tools: {', '.join(worker_task.allowed_tools)}\n"
                f"tool_catalog:\n{tool_catalog}\n"
                f"configured_model: {config.models.worker}"
            ),
        },
    ]
