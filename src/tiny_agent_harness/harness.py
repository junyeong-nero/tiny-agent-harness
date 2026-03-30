import uuid

from tiny_agent_harness.agents import supervisor_agent
from tiny_agent_harness.channels.input import InputChannel
from tiny_agent_harness.channels.listener import ListenerChannel
from tiny_agent_harness.channels.output import OutputChannel
from tiny_agent_harness.llm.client import LLMClient
from tiny_agent_harness.llm.factory import create_llm_client
from tiny_agent_harness.schemas import (
    AppConfig,
    ListenerEvent,
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
    final_run_output: RunOutput | None = None

    for _ in range(config.runtime.supervisor_max_retries):
        final_run_output = supervisor_agent(
            run_state,
            config,
            request=request,
            llm_client=llm_client,
            tool_caller=tool_caller,
        )
        run_state = final_run_output.state

        if final_run_output.done:
            break

    if final_run_output is None:
        raise RuntimeError("supervisor did not produce an orchestration result")

    output_channel.call(
        OutputEvent(
            event_id=str(uuid.uuid4()),
            session_id=resolved_session_id,
            payload=final_run_output,
        )
    )
    completion_event_kind = "run_completed" if final_run_output.done else "run_failed"
    listener_channel.call(
        ListenerEvent(
            kind=completion_event_kind,
            message=f"run finished with status={final_run_output.result.status}",
        )
    )

    return final_run_output.state, final_run_output.result


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
