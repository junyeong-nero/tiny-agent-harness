import uuid

from tiny_agent_harness.agents import supervisor_agent
from tiny_agent_harness.channels.input import InputChannel
from tiny_agent_harness.channels.listener import ListenerChannel
from tiny_agent_harness.channels.output import OutputChannel
from tiny_agent_harness.llm.factory import create_llm_client
from tiny_agent_harness.schemas import (
    Config,
    ListenerEvent,
    Event,
    Request,
    Response,
    HarnessInput,
    HarnessOutput,
    SupervisorInput,
    SupervisorOutput,
)
from tiny_agent_harness.tools import create_default_tool_caller


class TinyHarness:

    def __init__(
        self,
        config: Config,
        workspace_root: str,
    ) -> None:
        self.config = config
        self.ch_input = InputChannel()
        self.ch_listener = ListenerChannel()
        self.ch_output = OutputChannel()
        self.llm_client = create_llm_client(config, listeners=self.ch_listener)
        self.tool_caller = create_default_tool_caller(
            workspace_root=workspace_root,
            actor_permissions=config.tools.as_actor_permissions(),
            listeners=self.ch_listener,
        )

    def _run(
        self,
        harness_input: HarnessInput,
    ) -> HarnessOutput:

        self.ch_listener.call(ListenerEvent(kind="run_started", message="run started"))
        final_run_output: SupervisorOutput = None

        for _ in range(self.config.runtime.supervisor_max_retries):

            supervisor_input = SupervisorInput(task=harness_input.task)
            supervisor_output = supervisor_agent(
                supervisor_input,
                llm_client=self.llm_client,
                tool_caller=self.tool_caller,
            )
            final_run_output = supervisor_output

            if supervisor_output.status == "completed":
                break

        if final_run_output is None:
            raise RuntimeError("supervisor did not produce an orchestration result")

        completion_event_kind = (
            "run_completed" if supervisor_output.status == "completed" else "run_failed"
        )
        self.ch_listener.call(
            ListenerEvent(
                kind=completion_event_kind,
                message=f"run finished with status={final_run_output.status}\nsummary: {final_run_output.summary}",
            )
        )

        return HarnessOutput(
            task=harness_input.task,
            summary=final_run_output.summary,
            session_id=harness_input.session_id,
        )

    def run(self) -> None:
        while True:
            request: Request = self.ch_input.dequeue()
            if request is None:
                break

            harness_input = HarnessInput(
                task=request.query, session_id=request.session_id
            )
            harness_output = self._run(harness_input)

            response: Response = Response(
                query=request.query, summary=harness_output.summary, done=True
            )
            self.ch_output.call(
                Event(
                    event_id=str(uuid.uuid4()),
                    session_id=harness_input.session_id,
                    payload=response,
                )
            )
