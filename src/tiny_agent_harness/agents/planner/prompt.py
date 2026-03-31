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
                "Analyze the goal and produce one of the following outputs:\n\n"
                "status values:\n"
                "  'no-planning' — the input is conversational or requires no workspace operations.\n"
                "                  Put a brief note in summary. Leave plans empty.\n"
                "  'completed'   — planning is done. Fill the plans list with concrete task steps.\n"
                "  'failed'      — the goal is impossible or too ambiguous to plan.\n\n"
                "tool_call field:\n"
                "  Set tool_call (and keep status='completed') when you need to inspect the\n"
                "  workspace with a read-only tool before finalising the plan.\n"
                "  Only do this when necessary. Do not repeat the same inspection.\n\n"
                "If a previous attempt was rejected, use the reviewer feedback to improve the plan."
            ),
        },
        {
            "role": "user",
            "content": user_content,
        },
    ]
