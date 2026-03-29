import uuid

from tiny_agent_harness.agents import executor_agent, orchestrator_agent, reviewer_agent
from tiny_agent_harness.channels.input import InputChannel
from tiny_agent_harness.channels.output import OutputChannel
from tiny_agent_harness.handlers.listener import ListenerChannel
from tiny_agent_harness.llm.client import LLMClient
from tiny_agent_harness.schemas import (
    AppConfig,
    ListenerEvent,
    OutputEvent,
    RunOutput,
    RunResult,
    RunState,
)
from tiny_agent_harness.tools import ToolCaller, create_default_tool_caller
from tiny_agent_harness.llm.factory import create_llm_client


class Harness:

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
        self.llm_client = llm_client or create_llm_client(config, listeners=self.ch_listener)
        self.tool_caller = tool_caller or create_default_tool_caller(
            workspace_root=workspace_root,
            actor_permissions=config.tools.as_actor_permissions(),
            listeners=self.ch_listener,
        )

    def _emit(self, kind: str, message: str = "") -> None:
        self.ch_listener.call(ListenerEvent(kind=kind, message=message))

    def run(self) -> None:
        while True:
            input_request = self.ch_input.dequeue()
            if input_request is None:
                break

            request = input_request.payload
            state = RunState(task=request.prompt)
            self._emit("run_started", "run started")

            task = orchestrator_agent(
                state,
                self.config,
                llm_client=self.llm_client,
                tool_caller=self.tool_caller,
            )
            state = state.model_copy(
                update={"current_task": task, "step_count": state.step_count + 1}
            )

            executor_result = executor_agent(
                task,
                self.config,
                llm_client=self.llm_client,
                tool_caller=self.tool_caller,
            )
            state = state.model_copy(update={"last_executor_result": executor_result})

            review_result = reviewer_agent(
                task,
                executor_result,
                self.config,
                llm_client=self.llm_client,
                tool_caller=self.tool_caller,
            )
            done = review_result.decision == "approve"
            state = state.model_copy(
                update={"last_review_result": review_result, "done": done}
            )

            status = "completed" if done else "needs_retry"
            result = RunResult(
                status=status,
                summary=(
                    f"prompt='{state.task}' "
                    f"task='{task.id}' "
                    f"executor_status='{executor_result.status}' "
                    f"review_decision='{review_result.decision}'"
                ),
            )

            self.ch_output.call(
                OutputEvent(
                    event_id=str(uuid.uuid4()),
                    session_id=input_request.session_id,
                    payload=RunOutput(request=request, state=state, result=result),
                )
            )
            kind = "run_completed" if done else "run_failed"
            self._emit(kind, f"run finished with status={status}")
