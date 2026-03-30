import uuid

from tiny_agent_harness.agents import planner_agent, reviewer_agent
from tiny_agent_harness.channels.input import InputChannel
from tiny_agent_harness.channels.listener import ListenerChannel
from tiny_agent_harness.channels.output import OutputChannel
from tiny_agent_harness.llm.client import LLMClient
from tiny_agent_harness.llm.factory import create_llm_client
from tiny_agent_harness.schemas import (
    AppConfig,
    ListenerEvent,
    OrchestrationResult,
    OutputEvent,
    RunOutput,
    RunRequest,
    RunResult,
    RunState,
)
from tiny_agent_harness.tools import ToolCaller, create_default_tool_caller


def run_harness(
    request: RunRequest,
    config: AppConfig,
    session_id: str | None = None,
    llm_client: LLMClient | None = None,
    tool_caller: ToolCaller | None = None,
    listeners: ListenerChannel | None = None,
    output_handler: OutputChannel | None = None,
    input_channel: InputChannel | None = None,
) -> tuple[RunState, RunResult]:
    listener_channel = listeners or ListenerChannel()
    output_channel = output_handler or OutputChannel()
    resolved_session_id = (
        input_channel.dequeue().session_id
        if input_channel
        else session_id or str(uuid.uuid4())
    )

    listener_channel.call(ListenerEvent(kind="run_started", message="run started"))

    run_state = RunState(task=request.prompt)
    final_cycle_result: OrchestrationResult | None = None

    for _ in range(config.runtime.supervisor_max_retries):
        planner_result = planner_agent(
            run_state, config, llm_client=llm_client, tool_caller=tool_caller
        )

        review_output = reviewer_agent(
            request.prompt,
            planner_result,
            config,
            llm_client=llm_client,
            tool_caller=tool_caller,
        )
        is_approved = review_output.decision == "approve"
        final_cycle_result = OrchestrationResult(
            plan=planner_result.plan,
            reply=planner_result.reply,
            task=planner_result.task,
            worker_result=planner_result.worker_result,
            review_result=review_output,
            done=is_approved,
        )

        if is_approved:
            break

        completed_subtasks = list(run_state.completed_subtasks)
        if planner_result.task is not None:
            completed_subtasks.append(planner_result.task)

        worker_outputs = list(run_state.worker_results)
        if planner_result.worker_result is not None:
            worker_outputs.append(planner_result.worker_result)

        run_state = run_state.model_copy(
            update={
                "current_task": planner_result.task or run_state.current_task,
                "last_worker_result": planner_result.worker_result
                or run_state.last_worker_result,
                "last_review_result": review_output,
                "plan": run_state.plan + planner_result.plan,
                "completed_subtasks": completed_subtasks,
                "worker_results": worker_outputs,
                "review_cycles": run_state.review_cycles + 1,
                "step_count": run_state.step_count + 1,
            }
        )

    completed_subtasks = list(run_state.completed_subtasks)
    if final_cycle_result.task is not None:
        completed_subtasks.append(final_cycle_result.task)

    worker_outputs = list(run_state.worker_results)
    if final_cycle_result.worker_result is not None:
        worker_outputs.append(final_cycle_result.worker_result)

    run_state = run_state.model_copy(
        update={
            "current_task": final_cycle_result.task,
            "last_worker_result": final_cycle_result.worker_result,
            "last_review_result": final_cycle_result.review_result,
            "plan": run_state.plan + final_cycle_result.plan,
            "completed_subtasks": completed_subtasks,
            "worker_results": worker_outputs,
            "review_cycles": run_state.review_cycles + 1,
            "done": final_cycle_result.done,
            "step_count": run_state.step_count + 1,
        }
    )

    status = "completed" if final_cycle_result.done else "needs_retry"
    if final_cycle_result.reply is not None:
        summary = (
            f"prompt='{run_state.task}' "
            f"reply='{final_cycle_result.reply}' "
            f"review_decision='{final_cycle_result.review_result.decision}'"
        )
    else:
        summary = (
            f"prompt='{run_state.task}' "
            f"task='{final_cycle_result.task.id}' "
            f"worker_status='{final_cycle_result.worker_result.status}' "
            f"review_decision='{final_cycle_result.review_result.decision}'"
        )
    run_result = RunResult(status=status, summary=summary)

    output_channel.call(
        OutputEvent(
            event_id=str(uuid.uuid4()),
            session_id=resolved_session_id,
            payload=RunOutput(request=request, state=run_state, result=run_result),
        )
    )
    completion_event_kind = "run_completed" if final_cycle_result.done else "run_failed"
    listener_channel.call(
        ListenerEvent(
            kind=completion_event_kind,
            message=f"run finished with status={status}",
        )
    )

    return run_state, run_result


class TinyHarness:
    def __init__(
        self,
        config: AppConfig,
        workspace_root: str,
        llm_client: LLMClient | None = None,
        tool_caller: ToolCaller | None = None,
        ch_input: InputChannel | None = None,
        ch_listener: ListenerChannel | None = None,
        ch_output: OutputChannel | None = None,
    ) -> None:
        self.config = config
        self.ch_input = ch_input or InputChannel()
        self.ch_listener = ch_listener or ListenerChannel()
        self.ch_output = ch_output or OutputChannel()
        self.llm_client = llm_client or create_llm_client(
            config, listeners=self.ch_listener
        )
        self.tool_caller = tool_caller or create_default_tool_caller(
            workspace_root=workspace_root,
            actor_permissions=config.tools.as_actor_permissions(),
            listeners=self.ch_listener,
        )

    def run(self) -> None:
        while True:
            input_request = self.ch_input.dequeue()
            if input_request is None:
                break

            run_harness(
                input_request.payload,
                self.config,
                session_id=input_request.session_id,
                llm_client=self.llm_client,
                tool_caller=self.tool_caller,
                listeners=self.ch_listener,
                output_handler=self.ch_output,
            )
