from tiny_agent_harness.agents.shared import format_tool_catalog
from tiny_agent_harness.providers import ChatMessage
from tiny_agent_harness.schemas import ReviewerInput, ToolSpec


def build_messages(
    reviewer_input: ReviewerInput,
    tool_specs: list[ToolSpec],
) -> list[ChatMessage]:
    tool_catalog = format_tool_catalog(tool_specs)

    return [
        {
            "role": "system",
            "content": (
                "You are the reviewer agent. Your job is to verify whether the given task "
                "has been properly completed.\n\n"
                "You have two options:\n"
                "1. Use a read-only tool to inspect the workspace (status='tool_call').\n"
                "2. Return your final review decision (status='completed').\n\n"
                "Approve only if the task is fully and correctly completed. "
                "Otherwise, retry with specific, actionable feedback."
            ),
        },
        {
            "role": "user",
            "content": (
                f"task: {reviewer_input.task}\n"
                f"tool_catalog:\n{tool_catalog}"
            ),
        },
    ]
