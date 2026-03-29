from tiny_agent_harness.agents.shared import format_tool_catalog
from tiny_agent_harness.providers import ChatMessage
from tiny_agent_harness.schemas import AppConfig, RunState, ToolRequirement


ORCHESTRATOR_TOOLS = ["list_files", "search"]
EXECUTOR_TOOLS = ["bash", "read_file", "search", "list_files", "apply_patch"]


def build_initial_messages(
    state: RunState,
    config: AppConfig,
    tool_requirements: list[ToolRequirement],
) -> list[ChatMessage]:
    tool_catalog = format_tool_catalog(tool_requirements)

    return [
        {
            "role": "system",
            "content": (
                "You are the orchestrator agent in a multi-agent system.\n"
                "Your job is to analyze the user's goal and produce a Task for the executor agent.\n\n"
                "You have two options:\n"
                "1. Use a read-only tool to inspect the workspace (status='tool_call').\n"
                "   Only inspect when necessary. Do not repeat the same inspection.\n"
                "2. Return the final Task for the executor (status='completed').\n\n"
                "When returning a Task, set:\n"
                f"  - task.id: a short identifier like 'step_1'\n"
                f"  - task.instructions: clear step-by-step instructions for the executor\n"
                f"  - task.context: relevant background from your inspection\n"
                f"  - task.allowed_tools: subset of [{', '.join(EXECUTOR_TOOLS)}] the executor needs"
            ),
        },
        {
            "role": "user",
            "content": (
                f"goal: {state.task}\n"
                f"step_count: {state.step_count}\n"
                f"available_tools: {', '.join(ORCHESTRATOR_TOOLS)}\n"
                f"tool_catalog:\n{tool_catalog}"
            ),
        },
    ]
