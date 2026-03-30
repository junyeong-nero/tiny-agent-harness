from tiny_agent_harness.agents.shared import format_tool_catalog
from tiny_agent_harness.providers import ChatMessage
from tiny_agent_harness.schemas import Config, PlannerInput, ToolSpec


PLANNER_TOOLS = ["list_files", "search"]
WORKER_TOOLS = ["bash", "read_file", "search", "list_files", "apply_patch"]


def build_messages(
    planner_state: PlannerInput,
    tool_specs: list[ToolSpec],
) -> list[ChatMessage]:
    tool_catalog = format_tool_catalog(tool_specs)

    user_content = (
        f"goal: {planner_state.task}\n"
        f"available_tools: {', '.join(PLANNER_TOOLS)}\n"
        f"tool_catalog:\n{tool_catalog}"
    )

    return [
        {
            "role": "system",
            "content": (
                "You are the planner agent in a multi-agent system.\n"
                "Analyze the user's input and choose one of three actions:\n\n"
                "1. status='reply' — the input is a greeting, question, or chitchat that does NOT\n"
                "   require workspace operations. Put the proposed direct reply in the summary field.\n"
                "   The supervisor, not the planner, owns the final user-facing reply.\n"
                "   Do NOT delegate to the worker for conversational inputs.\n\n"
                "2. status='tool_call' — inspect the workspace with a read-only tool before planning.\n"
                "   Only do this when necessary. Do not repeat the same inspection.\n\n"
                "If a previous attempt was rejected, use the reviewer feedback to improve the task."
            ),
        },
        {
            "role": "user",
            "content": user_content,
        },
    ]
