from tiny_agent_harness.providers import ChatMessage
from tiny_agent_harness.schemas import AppConfig, RunState


EXECUTOR_TOOLS = ["bash", "read_file", "search", "list_files", "apply_patch"]


def build_messages(state: RunState, config: AppConfig) -> list[ChatMessage]:
    return [
        {
            "role": "system",
            "content": (
                "You are the main_loop agent. Create the next internal task for the executor. "
                "Return only a Task object."
            ),
        },
        {
            "role": "user",
            "content": (
                f"goal: {state.goal}\n"
                f"step_count: {state.step_count}\n"
                f"executor_allowed_tools: {', '.join(EXECUTOR_TOOLS)}\n"
                f"configured_model: {config.models.main_loop}"
            ),
        },
    ]
