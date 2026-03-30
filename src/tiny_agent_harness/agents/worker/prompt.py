from tiny_agent_harness.agents.shared import format_tool_catalog
from tiny_agent_harness.providers import ChatMessage
from tiny_agent_harness.schemas import Config, ToolSpec, WorkerInput


def build_messages(
    worker_task: WorkerInput,
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
                f"task: {worker_task.task}\n"
                f"kind: {worker_task.kind}\n"
                f"tool_catalog:\n{tool_catalog}\n"
            ),
        },
    ]
