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
                "You are the worker agent. Execute the given task step by step.\n\n"
                "status values:\n"
                "  'completed' — the task is fully done. Fill summary, artifacts, changed_files,\n"
                "                and test_results as appropriate.\n"
                "  'failed'    — the task cannot be completed. Explain why in summary.\n\n"
                "tool_call field:\n"
                "  Set tool_call when you need to invoke a tool for this step.\n"
                "  You will be called again with the tool result until the task is done.\n\n"
                "If the task is conversational or no tools are listed, do NOT call any tools.\n"
                "Respond directly with status='completed' and put your reply in summary."
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
