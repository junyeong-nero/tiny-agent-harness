from typing import Protocol

from tiny_agent_harness.providers import ChatMessage
from tiny_agent_harness.schemas import AppConfig, RunState, Task
from tiny_agent_harness.agents.orchestrator.prompt import EXECUTOR_TOOLS, build_messages


class SupportsStructuredLLM(Protocol):
    def chat_structured(
        self,
        messages: list[ChatMessage],
        agent_name: str,
        response_model: type,
        model: str | None = None,
        max_retries: int | None = None,
    ): ...


def main_loop_agent(
    state: RunState,
    config: AppConfig,
    llm_client: SupportsStructuredLLM | None = None,
) -> Task:
    if llm_client is not None:
        return llm_client.chat_structured(
            messages=build_messages(state, config),
            agent_name="main_loop",
            response_model=Task,
        )

    return Task(
        id=f"task-{state.step_count + 1}",
        instructions=state.goal,
        context=(
            f"Plan the next action for goal '{state.goal}'. "
            f"main_loop model={config.models.main_loop}"
        ),
        allowed_tools=EXECUTOR_TOOLS,
    )
