from tiny_agent_harness.agents.protocols import format_tool_catalog
from tiny_agent_harness.llm.providers import ChatMessage
from tiny_agent_harness.schemas import Config, PlannerInput, ToolSpec


PLANNER_TOOLS = ["list_files", "search"]


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
                "Analyze the goal and produce a concrete list of steps.\n\n"
                "Step writing rules:\n"
                "  - If a step requires understanding code, docs, or structure,\n"
                "    prefix it with 'explore:' so the supervisor routes it to the explorer.\n"
                "  - If a step requires making changes or running commands,\n"
                "    prefix it with 'implement:' so the supervisor routes it to the worker.\n"
                "  - Keep each step focused on a single action or question.\n\n"
                "status values:\n"
                "  'no-planning' — the input is conversational or requires no workspace operations.\n"
                "                  Put a brief note in summary. Leave plans empty.\n"
                "  'completed'   — planning is done. Fill the plans list.\n"
                "  'failed'      — the goal is impossible or too ambiguous to plan.\n\n"
                "tool_call field:\n"
                "  Set tool_call when you need a high-level view of the workspace before\n"
                "  finalising the plan (e.g. list_files, search). Do not repeat the same call.\n\n"
                "If a previous attempt was rejected, use the verifier feedback to improve the plan."
            ),
        },
        {
            "role": "user",
            "content": user_content,
        },
    ]
