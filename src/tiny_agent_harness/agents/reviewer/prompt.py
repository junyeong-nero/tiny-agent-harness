from tiny_agent_harness.agents.protocols import format_tool_catalog
from tiny_agent_harness.llm.providers import ChatMessage
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
                "You are the reviewer agent. Verify whether the given task has been properly completed.\n\n"
                "status values:\n"
                "  'completed' — review is done. Set decision to 'approve' or 'retry'.\n"
                "                Always fill feedback with your reasoning.\n"
                "  'failed'    — you cannot determine the outcome. Explain why in feedback.\n\n"
                "tool_call field:\n"
                "  Set tool_call when you need to inspect the workspace with a read-only tool\n"
                "  before making your decision. You will be called again with the tool result.\n\n"
                "Approve only if the task is fully and correctly completed.\n"
                "Otherwise use decision='retry' with specific, actionable feedback."
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
