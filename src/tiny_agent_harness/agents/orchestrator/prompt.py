from tiny_agent_harness.providers import ChatMessage
from tiny_agent_harness.schemas import AppConfig, RunState, ToolRequirement


ORCHESTRATOR_TOOLS = ["list_files", "search"]
EXECUTOR_TOOLS = ["bash", "read_file", "search", "list_files", "apply_patch"]


def _format_tool_results(tool_results: list[str]) -> str:
    if not tool_results:
        return "none"
    return "\n\n".join(tool_results)


def build_messages(
    state: RunState,
    config: AppConfig,
    tool_requirements: list[ToolRequirement],
    tool_results: list[str],
) -> list[ChatMessage]:
    tool_catalog = "\n".join(
        f"- {req.name}: {req.description}\n  schema: {req.arguments_schema}"
        for req in tool_requirements
    ) or "none"

    return [
        {
            "role": "system",
            "content": (
                "You are the orchestrator agent. You may either choose one read-only tool call "
                "to inspect the workspace or return the next internal Task for the executor. "
                "Use status='tool_call' when inspection is needed. Use status='completed' "
                "only when returning the final Task."
            ),
        },
        {
            "role": "user",
            "content": (
                f"goal: {state.goal}\n"
                f"step_count: {state.step_count}\n"
                f"orchestrator_allowed_tools: {', '.join(ORCHESTRATOR_TOOLS)}\n"
                f"executor_allowed_tools: {', '.join(EXECUTOR_TOOLS)}\n"
                f"tool_catalog:\n{tool_catalog}\n"
                f"tool_results:\n{_format_tool_results(tool_results)}\n"
                f"configured_model: {config.models.orchestrator}"
            ),
        },
    ]
