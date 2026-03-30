from tiny_agent_harness.agents.planner import planner_agent
from tiny_agent_harness.agents.reviewer import reviewer_agent
from tiny_agent_harness.agents.shared import SupportsStructuredLLM
from tiny_agent_harness.agents.supervisor.prompt import (
    SUPERVISOR_PIPELINE_LABEL,
    SUPERVISOR_ROLE_DESCRIPTION,
)
from tiny_agent_harness.agents.worker import worker_agent
from tiny_agent_harness.schemas import (
    AppConfig,
    PlannerOutput,
    RunOutput,
    RunRequest,
    RunResult,
    ReviewerOutput,
    RunState,
    WorkerOutput,
)
from tiny_agent_harness.tools import ToolCaller


class SupervisorAgent:
    def __init__(
        self,
        config: AppConfig,
        llm_client: SupportsStructuredLLM,
        tool_caller: ToolCaller,
    ) -> None:
        self.config = config
        self.llm_client = llm_client
        self.tool_caller = tool_caller

    def _promote_planner_reply(self, planner_result: PlannerOutput) -> PlannerOutput:
        if planner_result.reply is not None:
            return planner_result
        if not planner_result.plan:
            return planner_result

        final_plan_step = planner_result.plan[-1]
        if final_plan_step.status != "reply":
            return planner_result

        return planner_result.model_copy(update={"reply": final_plan_step.summary})

    def _build_next_state(
        self,
        state: RunState,
        planner_result: PlannerOutput,
        worker_result: WorkerOutput | None,
        review_result: ReviewerOutput,
        done: bool,
    ) -> RunState:
        completed_subtasks = list(state.completed_subtasks)
        if planner_result.task is not None:
            completed_subtasks.append(planner_result.task)

        worker_outputs = list(state.worker_results)
        if worker_result is not None:
            worker_outputs.append(worker_result)

        return state.model_copy(
            update={
                "current_task": planner_result.task,
                "last_worker_result": worker_result,
                "last_review_result": review_result,
                "plan": state.plan + planner_result.plan,
                "completed_subtasks": completed_subtasks,
                "worker_results": worker_outputs,
                "review_cycles": state.review_cycles + 1,
                "done": done,
                "step_count": state.step_count + 1,
            }
        )

    def _build_run_result(
        self,
        state: RunState,
        planner_result: PlannerOutput,
        worker_result: WorkerOutput | None,
        review_result: ReviewerOutput,
    ) -> RunResult:
        status = "completed" if review_result.decision == "approve" else "needs_retry"
        if planner_result.reply is not None:
            summary = (
                f"prompt='{state.task}' "
                f"reply='{planner_result.reply}' "
                f"review_decision='{review_result.decision}'"
            )
        elif planner_result.task is not None and worker_result is not None:
            summary = (
                f"prompt='{state.task}' "
                f"task='{planner_result.task.id}' "
                f"worker_status='{worker_result.status}' "
                f"review_decision='{review_result.decision}'"
            )
        else:
            summary = (
                f"prompt='{state.task}' "
                f"review_decision='{review_result.decision}' "
                "reason='missing planner reply and worker task'"
            )
        return RunResult(status=status, summary=summary)

    def _build_run_output(
        self,
        request: RunRequest,
        state: RunState,
        planner_result: PlannerOutput,
        worker_result: WorkerOutput | None,
        review_result: ReviewerOutput,
    ) -> RunOutput:
        done = review_result.decision == "approve"
        next_state = self._build_next_state(
            state=state,
            planner_result=planner_result,
            worker_result=worker_result,
            review_result=review_result,
            done=done,
        )
        return RunOutput(
            request=request,
            state=next_state,
            result=self._build_run_result(
                state=state,
                planner_result=planner_result,
                worker_result=worker_result,
                review_result=review_result,
            ),
            planner_result=planner_result,
            worker_result=worker_result,
            review_result=review_result,
            done=done,
        )

    def _review_invalid_plan(
        self,
        request: RunRequest,
        state: RunState,
        planner_result: PlannerOutput,
    ) -> RunOutput:
        review_result = ReviewerOutput(
            decision="retry",
            feedback=(
                f"{SUPERVISOR_ROLE_DESCRIPTION} "
                f"The {SUPERVISOR_PIPELINE_LABEL} cycle received neither a direct reply nor a worker task."
            ),
        )
        return self._build_run_output(
            request=request,
            state=state,
            planner_result=planner_result,
            worker_result=None,
            review_result=review_result,
        )

    def run(self, state: RunState, request: RunRequest | None = None) -> RunOutput:
        resolved_request = request or RunRequest(prompt=state.task)
        planner_result = planner_agent(
            state,
            self.config,
            llm_client=self.llm_client,
            tool_caller=self.tool_caller,
        )
        planner_result = self._promote_planner_reply(planner_result)
        if planner_result.reply is None and planner_result.task is None:
            return self._review_invalid_plan(resolved_request, state, planner_result)

        worker_result: WorkerOutput | None = None
        if planner_result.reply is None and planner_result.task is not None:
            worker_result = worker_agent(
                planner_result.task,
                self.config,
                llm_client=self.llm_client,
                tool_caller=self.tool_caller,
            )

        review_result = reviewer_agent(
            state.task,
            planner_result,
            self.config,
            worker_result=worker_result,
            llm_client=self.llm_client,
            tool_caller=self.tool_caller,
        )
        return self._build_run_output(
            request=resolved_request,
            state=state,
            planner_result=planner_result,
            worker_result=worker_result,
            review_result=review_result,
        )


def supervisor_agent(
    state: RunState,
    config: AppConfig,
    request: RunRequest,
    llm_client: SupportsStructuredLLM,
    tool_caller: ToolCaller,
) -> RunOutput:
    return SupervisorAgent(
        config=config,
        llm_client=llm_client,
        tool_caller=tool_caller,
    ).run(state, request=request)


__all__ = ["SupervisorAgent", "supervisor_agent"]
