from typing import Protocol

from tiny_agent_harness.providers import ChatMessage
from tiny_agent_harness.schemas import (
    AppConfig,
    ExecutorResult,
    ReviewResult,
    RunRequest,
    RunResult,
    RunState,
    Task,
)


MAIN_LOOP_TOOLS = ["list_files", "search"]
EXECUTOR_TOOLS = ["bash", "read_file", "search", "list_files", "apply_patch"]
REVIEWER_TOOLS = ["read_file", "search", "list_files", "git_diff"]


class SupportsStructuredLLM(Protocol):
    def chat_structured(
        self,
        messages: list[ChatMessage],
        agent_name: str,
        response_model: type,
        model: str | None = None,
        max_retries: int | None = None,
    ): ...


def create_initial_state(request: RunRequest) -> RunState:
    return RunState(goal=request.goal)


def _main_loop_messages(state: RunState, config: AppConfig) -> list[ChatMessage]:
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


def main_loop_agent(
    state: RunState,
    config: AppConfig,
    llm_client: SupportsStructuredLLM | None = None,
) -> Task:
    if llm_client is not None:
        return llm_client.chat_structured(
            messages=_main_loop_messages(state, config),
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


def _executor_messages(task: Task, config: AppConfig) -> list[ChatMessage]:
    return [
        {
            "role": "system",
            "content": (
                "You are the executor agent. Execute the task and return only an ExecutorResult."
            ),
        },
        {
            "role": "user",
            "content": (
                f"task_id: {task.id}\n"
                f"instructions: {task.instructions}\n"
                f"context: {task.context}\n"
                f"allowed_tools: {', '.join(task.allowed_tools)}\n"
                f"configured_model: {config.models.executor}"
            ),
        },
    ]


def executor_agent(
    task: Task,
    config: AppConfig,
    llm_client: SupportsStructuredLLM | None = None,
) -> ExecutorResult:
    if llm_client is not None:
        return llm_client.chat_structured(
            messages=_executor_messages(task, config),
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


def reviewer_agent(
    task: Task,
    executor_result: ExecutorResult,
    config: AppConfig,
    llm_client: SupportsStructuredLLM | None = None,
) -> ReviewResult:
    if llm_client is not None:
        return llm_client.chat_structured(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are the reviewer agent. Review the executor result and return "
                        "only a ReviewResult."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"task_id: {task.id}\n"
                        f"instructions: {task.instructions}\n"
                        f"executor_status: {executor_result.status}\n"
                        f"executor_summary: {executor_result.summary}\n"
                        f"artifacts: {', '.join(executor_result.artifacts)}\n"
                        f"allowed_tools: {', '.join(REVIEWER_TOOLS)}\n"
                        f"configured_model: {config.models.reviewer}"
                    ),
                },
            ],
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


def run_harness(
    request: RunRequest,
    config: AppConfig,
    llm_client: SupportsStructuredLLM | None = None,
) -> tuple[RunState, RunResult]:
    state = create_initial_state(request)

    task = main_loop_agent(state, config, llm_client=llm_client)
    state.current_task = task
    state.step_count += 1

    executor_result = executor_agent(task, config, llm_client=llm_client)
    state.last_executor_result = executor_result

    review_result = reviewer_agent(
        task,
        executor_result,
        config,
        llm_client=llm_client,
    )
    state.last_review_result = review_result
    state.done = review_result.decision == "approve"

    status = "completed" if state.done else "needs_retry"
    result = RunResult(
        status=status,
        summary=(
            f"goal='{state.goal}' "
            f"task='{task.id}' "
            f"executor_status='{executor_result.status}' "
            f"review_decision='{review_result.decision}'"
        ),
    )

    return state, result
