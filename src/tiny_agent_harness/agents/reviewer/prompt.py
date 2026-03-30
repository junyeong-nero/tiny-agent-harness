from tiny_agent_harness.agents.shared import format_tool_catalog
from tiny_agent_harness.providers import ChatMessage
from tiny_agent_harness.schemas import AppConfig, ReviewerInput, ToolSpec


def _build_user_content(request: ReviewerInput, tool_catalog: str, config: AppConfig) -> str:
    if request.reply is not None:
        return (
            f"original_prompt: {request.original_prompt}\n"
            f"response_type: direct_reply\n"
            f"reply: {request.reply}\n"
            f"configured_model: {config.models.reviewer}"
        )
    return (
        f"original_prompt: {request.original_prompt}\n"
        f"task_id: {request.task.id}\n"
        f"task_instructions: {request.task.instructions}\n"
        f"task_context: {request.task.context}\n"
        f"worker_status: {request.worker_result.status}\n"
        f"worker_summary: {request.worker_result.summary}\n"
        f"artifacts: {', '.join(request.worker_result.artifacts)}\n"
        f"tool_catalog:\n{tool_catalog}\n"
        f"configured_model: {config.models.reviewer}"
    )


def build_messages(
    request: ReviewerInput,
    config: AppConfig,
    tool_specs: list[ToolSpec],
) -> list[ChatMessage]:
    tool_catalog = format_tool_catalog(tool_specs)

    return [
        {
            "role": "system",
            "content": (
                "You are the reviewer agent. Your job is to verify whether the response "
                "fulfills the user's original request.\n\n"
                "You have two options:\n"
                "1. Use a read-only tool to inspect the workspace (status='tool_call').\n"
                "2. Return your final review decision (status='completed').\n\n"
                "Evaluate against the original_prompt, not just the task instructions.\n\n"
                "If the response is a direct conversational reply (no task was executed), "
                "simply approve it if it appropriately addresses the user's input."
            ),
        },
        {
            "role": "user",
            "content": _build_user_content(request, tool_catalog, config),
        },
    ]
