from typing import Protocol

from tiny_agent_harness.providers import ChatMessage
from tiny_agent_harness.schemas import AppConfig, ExecutorResult, ReviewResult, Task
from tiny_agent_harness.agents.reviewer.prompt import build_messages


class SupportsStructuredLLM(Protocol):
    def chat_structured(
        self,
        messages: list[ChatMessage],
        agent_name: str,
        response_model: type,
        model: str | None = None,
        max_retries: int | None = None,
    ): ...


def reviewer_agent(
    task: Task,
    executor_result: ExecutorResult,
    config: AppConfig,
    llm_client: SupportsStructuredLLM | None = None,
) -> ReviewResult:
    if llm_client is not None:
        return llm_client.chat_structured(
            messages=build_messages(task, executor_result, config),
            agent_name="reviewer",
            response_model=ReviewResult,
        )

    if executor_result.status != "completed":
        return ReviewResult(
            decision="retry",
            feedback=(
                f"reviewer mock rejected task {task.id} "
                f"with model {config.models.reviewer}"
            ),
        )

    return ReviewResult(
        decision="approve",
        feedback=(
            f"reviewer mock approved task {task.id} "
            f"with model {config.models.reviewer}"
        ),
    )
