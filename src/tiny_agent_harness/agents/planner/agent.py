from tiny_agent_harness.agents.base_agent import BaseAgent
from tiny_agent_harness.agents.shared import SupportsStructuredLLM
from tiny_agent_harness.agents.planner.prompt import (
    PLANNER_TOOLS,
    WORKER_TOOLS,
    build_messages,
)
from tiny_agent_harness.schemas import (
    AppConfig,
    PlannerOutput,
    PlannerStep,
    RunState,
    WorkerTask,
)
from tiny_agent_harness.tools import ToolCaller


def _build_fallback_subtask(state: RunState, reason: str) -> WorkerTask:
    return WorkerTask(
        id=f"task-{state.step_count + 1}",
        kind="implement",
        instructions=state.task,
        context=f"Fallback task for goal '{state.task}'. reason={reason}",
        allowed_tools=WORKER_TOOLS,
    )


def _select_worker_subtask(plan_step: PlannerStep) -> WorkerTask | None:
    if plan_step.task is not None:
        return plan_step.task

    for subtask in plan_step.subtasks:
        if subtask.kind == "implement":
            return subtask

    if plan_step.subtasks:
        return plan_step.subtasks[0]
    return None


class PlannerAgent(BaseAgent[RunState, PlannerStep]):
    def __init__(
        self,
        llm_client: SupportsStructuredLLM,
        tool_caller: ToolCaller,
        config: AppConfig,
    ):
        super().__init__(
            agent_name="planner",
            llm_client=llm_client,
            tool_caller=tool_caller,
            config=config,
            message_builder=build_messages,
            input_schema=RunState,
            output_schema=PlannerStep,
            max_tool_steps=config.runtime.planner_max_tool_steps,
            allowed_tools=PLANNER_TOOLS,
        )

    def run(self, state: RunState) -> PlannerOutput:
        from tiny_agent_harness.agents.worker import worker_agent

        plan_step = super().run(state)

        if plan_step.status == "reply":
            return PlannerOutput(reply=plan_step.summary, plan=[plan_step])

        worker_subtask = _select_worker_subtask(plan_step)
        if worker_subtask is None:
            worker_subtask = _build_fallback_subtask(
                state,
                "planner exceeded maximum tool steps or returned delegation without a task",
            )

        worker_output = worker_agent(
            worker_subtask, self.config, self.client, self.tool_caller
        )
        return PlannerOutput(
            plan=[plan_step],
            task=worker_subtask,
            worker_result=worker_output,
        )


def planner_agent(
    state: RunState,
    config: AppConfig,
    llm_client: SupportsStructuredLLM | None = None,
    tool_caller: ToolCaller | None = None,
) -> PlannerOutput:
    from tiny_agent_harness.agents.worker import worker_agent

    if llm_client is not None and tool_caller is not None:
        return PlannerAgent(llm_client, tool_caller, config).run(state)

    if llm_client is not None:
        plan_step = llm_client.chat_structured(
            messages=build_messages(state, config, []),
            agent_name="planner",
            response_model=PlannerStep,
        )
        if plan_step.status == "reply":
            return PlannerOutput(reply=plan_step.summary, plan=[plan_step])
        if plan_step.status == "tool_call":
            worker_subtask = _build_fallback_subtask(
                state,
                "planner requested a tool, but no tool registry was provided",
            )
        else:
            worker_subtask = _select_worker_subtask(plan_step)
            if worker_subtask is None:
                worker_subtask = _build_fallback_subtask(
                    state,
                    "planner returned delegation without a task",
                )
        worker_output = worker_agent(
            worker_subtask, config, llm_client=llm_client, tool_caller=tool_caller
        )
        return PlannerOutput(
            plan=[plan_step],
            task=worker_subtask,
            worker_result=worker_output,
        )

    worker_subtask = WorkerTask(
        id=f"task-{state.step_count + 1}",
        kind="implement",
        instructions=state.task,
        context=(
            f"Plan the next action for goal '{state.task}'. "
            f"planner model={config.models.planner}"
        ),
        allowed_tools=WORKER_TOOLS,
    )
    worker_output = worker_agent(
        worker_subtask, config, llm_client=llm_client, tool_caller=tool_caller
    )
    return PlannerOutput(task=worker_subtask, worker_result=worker_output)
