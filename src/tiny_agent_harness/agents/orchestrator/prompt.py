from tiny_agent_harness.agents.shared import format_tool_catalog
from tiny_agent_harness.providers import ChatMessage
from tiny_agent_harness.schemas import AppConfig, RunState, ToolSpec


ORCHESTRATOR_TOOLS = ["list_files", "search"]
EXECUTOR_TOOLS = ["bash", "read_file", "search", "list_files", "apply_patch"]


def build_messages(
    state: RunState,
    config: AppConfig,
    tool_specs: list[ToolSpec],
) -> list[ChatMessage]:
    tool_catalog = format_tool_catalog(tool_specs)

    user_content = (
        f"goal: {state.task}\n"
        f"step_count: {state.step_count}\n"
        f"available_tools: {', '.join(ORCHESTRATOR_TOOLS)}\n"
        f"tool_catalog:\n{tool_catalog}"
    )
    if state.last_review_result is not None:
        user_content += f"\nprevious_review_decision: {state.last_review_result.decision}"
        user_content += f"\nprevious_review_feedback: {state.last_review_result.feedback}"

    return [
        {
            "role": "system",
            "content": (
                "You are the orchestrator agent in a multi-agent system.\n"
                "Analyze the user's input and choose one of three actions:\n\n"
                "1. status='reply' — the input is a greeting, question, or chitchat that does NOT\n"
                "   require workspace operations. Put your response in the summary field.\n"
                "   Do NOT delegate to the executor for conversational inputs.\n\n"
                "2. status='tool_call' — inspect the workspace with a read-only tool before planning.\n"
                "   Only do this when necessary. Do not repeat the same inspection.\n\n"
                "3. status='delegate' — hand off a Task to the executor agent.\n"
                "   Set task.id, task.instructions, task.context, and task.allowed_tools\n"
                f"   (subset of [{', '.join(EXECUTOR_TOOLS)}]).\n\n"
                "If a previous attempt was rejected, use the reviewer feedback to improve the task."
            ),
        },
        {
            "role": "user",
            "content": user_content,
        },
    ]
