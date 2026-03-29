from tiny_agent_harness.agents import executor_agent, orchestrator_agent, reviewer_agent
from tiny_agent_harness.schemas import (
    AppConfig,
    RunRequest,
    RunResult,
    RunState,
)
from tiny_agent_harness.tools import ToolCaller


def create_initial_state(request: RunRequest) -> RunState:
    return RunState(goal=request.goal)


def run_harness(
    request: RunRequest,
    config: AppConfig,
    llm_client=None,
    tool_caller: ToolCaller | None = None,
) -> tuple[RunState, RunResult]:
    state = create_initial_state(request)

    task = orchestrator_agent(state, config, llm_client=llm_client, tool_caller=tool_caller)
    state.current_task = task
    state.step_count += 1

    executor_result = executor_agent(task, config, llm_client=llm_client, tool_caller=tool_caller)
    state.last_executor_result = executor_result

    review_result = reviewer_agent(
        task,
        executor_result,
        config,
        llm_client=llm_client,
        tool_caller=tool_caller,
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
