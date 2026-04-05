from tiny_agent_harness.agents.protocols import format_tool_catalog
from tiny_agent_harness.llm.providers import ChatMessage
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
                "You are the worker agent. Your job is to make concrete changes: write code,\n"
                "apply patches, run commands, and produce results.\n\n"
                "You do NOT explore or gather context. Assume the task description already\n"
                "contains everything you need to know. If context is missing, mark the task\n"
                "as failed — do not use tools to read files for understanding.\n\n"
                "Allowed tool usage:\n"
                "  - Read a file immediately before patching it (targeted, not exploratory).\n"
                "  - Prefer replace_in_file for small exact edits when the target text is known.\n"
                "  - Use apply_patch for multi-line, structural, or context-dependent edits.\n"
                "  - Run bash to build, test, or execute.\n"
                "  - Use git_status to confirm workspace state when it directly helps implementation.\n\n"
                "status values:\n"
                "  'completed' — all changes are made. Fill summary, artifacts, changed_files,\n"
                "                and test_results as appropriate.\n"
                "  'failed'    — the task cannot be completed. Explain why in summary.\n\n"
                "tool_call field:\n"
                "  Set tool_call only when a tool directly advances the implementation.\n"
                "  You will be called again with the result until the task is done."
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
