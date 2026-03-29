from typing import Protocol

from tiny_agent_harness.providers import ChatMessage
from tiny_agent_harness.schemas import AppConfig, ExecutorResult, Task
from tiny_agent_harness.agents.executor.prompt import build_messages


class SupportsStructuredLLM(Protocol):
    def chat_structured(
        self,
        messages: list[ChatMessage],
        agent_name: str,
        response_model: type,
        model: str | None = None,
        max_retries: int | None = None,
    ): ...


def executor_agent(
    task: Task,
    config: AppConfig,
    llm_client: SupportsStructuredLLM | None = None,
) -> ExecutorResult:
    if llm_client is not None:
        return llm_client.chat_structured(
            messages=build_messages(task, config),
            agent_name="executor",
            response_model=ExecutorResult,
        )

    return ExecutorResult(
        status="completed",
        summary=(
            f"executor mock completed '{task.instructions}' "
            f"with model {config.models.executor}"
        ),
        artifacts=[task.id],
    )
