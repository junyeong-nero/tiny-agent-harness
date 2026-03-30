import uuid

from tiny_agent_harness.agents import orchestrator_agent, reviewer_agent
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
    ch_listener = listeners or ListenerChannel()
    ch_output = output_handler or OutputChannel()
    actual_session_id = (
        input_channel.dequeue().session_id
        if input_channel
        else session_id or str(uuid.uuid4())
    )

    ch_listener.call(ListenerEvent(kind="run_started", message="run started"))

    state = RunState(task=request.prompt)
    orchestration: OrchestrationResult | None = None

    for _ in range(config.runtime.orchestrator_max_retries):
        execution = orchestrator_agent(
            state, config, llm_client=llm_client, tool_caller=tool_caller
        )

        review_result = reviewer_agent(
            request.prompt,
            execution,
            config,
            llm_client=llm_client,
            tool_caller=tool_caller,
        )
        done = review_result.decision == "approve"
        orchestration = OrchestrationResult(
            reply=execution.reply,
            task=execution.task,
            worker_result=execution.worker_result,
            review_result=review_result,
            done=done,
        )

        if done:
            break

        state = state.model_copy(
            update={
                "current_task": execution.task or state.current_task,
                "last_worker_result": execution.worker_result or state.last_worker_result,
                "last_review_result": review_result,
                "step_count": state.step_count + 1,
            }
        )

    state = state.model_copy(
        update={
            "current_task": orchestration.task,
            "last_worker_result": orchestration.worker_result,
            "last_review_result": orchestration.review_result,
            "done": orchestration.done,
            "step_count": state.step_count + 1,
        }
    )

    status = "completed" if orchestration.done else "needs_retry"
    if orchestration.reply is not None:
        summary = f"prompt='{state.task}' reply='{orchestration.reply}' review_decision='{orchestration.review_result.decision}'"
    else:
        summary = (
            f"prompt='{state.task}' "
            f"task='{orchestration.task.id}' "
            f"worker_status='{orchestration.worker_result.status}' "
            f"review_decision='{orchestration.review_result.decision}'"
        )
    result = RunResult(status=status, summary=summary)

    ch_output.call(
        OutputEvent(
            event_id=str(uuid.uuid4()),
            session_id=actual_session_id,
            payload=RunOutput(request=request, state=state, result=result),
        )
    )
    kind = "run_completed" if orchestration.done else "run_failed"
    ch_listener.call(
        ListenerEvent(kind=kind, message=f"run finished with status={status}")
    )

    return state, result


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
