from tiny_agent_harness.agents.shared import format_tool_catalog
from tiny_agent_harness.providers import ChatMessage
from tiny_agent_harness.schemas import AppConfig, RunState, ToolSpec


PLANNER_TOOLS = ["list_files", "search"]
WORKER_TOOLS = ["bash", "read_file", "search", "list_files", "apply_patch"]


def build_messages(
    planner_state: RunState,
    config: AppConfig,
    tool_specs: list[ToolSpec],
) -> list[ChatMessage]:
    tool_catalog = format_tool_catalog(tool_specs)

    user_content = (
        f"goal: {planner_state.task}\n"
        f"step_count: {planner_state.step_count}\n"
        f"review_cycles: {planner_state.review_cycles}\n"
        f"available_tools: {', '.join(PLANNER_TOOLS)}\n"
        f"tool_catalog:\n{tool_catalog}"
    )
    if planner_state.last_review_result is not None:
        user_content += (
            f"\nprevious_review_decision: {planner_state.last_review_result.decision}"
        )
        user_content += (
            f"\nprevious_review_feedback: {planner_state.last_review_result.feedback}"
        )

    return [
        {
            "role": "system",
            "content": (
                "You are the planner agent in a multi-agent system.\n"
                "Analyze the user's input and choose one of three actions:\n\n"
                "1. status='reply' — the input is a greeting, question, or chitchat that does NOT\n"
                "   require workspace operations. Put your response in the summary field.\n"
                "   Do NOT delegate to the worker for conversational inputs.\n\n"
                "2. status='tool_call' — inspect the workspace with a read-only tool before planning.\n"
                "   Only do this when necessary. Do not repeat the same inspection.\n\n"
                "3. status='delegate_worker' or status='delegate' — hand off one implement subtask\n"
                "   to the worker agent. Set subtask.id, subtask.instructions, subtask.context,\n"
                f"   and subtask.allowed_tools (subset of [{', '.join(WORKER_TOOLS)}]).\n\n"
                "If a previous attempt was rejected, use the reviewer feedback to improve the task."
            ),
        },
        {
            "role": "user",
            "content": user_content,
        },
    ]
