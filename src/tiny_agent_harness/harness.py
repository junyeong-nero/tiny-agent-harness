import uuid

from tiny_agent_harness.agents.supervisor import SupervisorAgent
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
)
from tiny_agent_harness.skills import SkillRunner, create_default_skills
from tiny_agent_harness.tools import create_default_tool_executor


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
        self.tool_executor = create_default_tool_executor(
            workspace_root=workspace_root,
            actor_permissions=config.tools.as_actor_permissions(),
            listeners=self.ch_listener,
        )
        self.skill_runner = SkillRunner(create_default_skills())

    def _resolve_task(self, query: str) -> str | None:
        """Expands /skill-name into a prompt. Returns None and emits skill_error on failure."""
        if not query.startswith("/"):
            return query

        parts = query[1:].split(None, 1)
        name = parts[0]
        args = parts[1] if len(parts) > 1 else ""

        result = self.skill_runner.run(name, args)
        if result is None:
            self.ch_listener.call(
                ListenerEvent(kind="skill_error", message=f"unknown skill: {name}")
            )
            return None
        if not result.ok:
            self.ch_listener.call(
                ListenerEvent(
                    kind="skill_error", message=f"skill error: {result.error}"
                )
            )
            return None
        self.ch_listener.call(
            ListenerEvent(
                kind="skill_resolved",
                message=f"resolved skill: {name}",
                data={
                    "skill": name,
                    "args": args,
                    "prompt": result.prompt,
                },
            )
        )
        return result.prompt

    def _run(
        self,
        harness_input: HarnessInput,
    ) -> HarnessOutput:

        self.ch_listener.call(
            ListenerEvent(
                kind="run_started",
                message="run started",
                data={"task": harness_input.task},
            )
        )

        task = self._resolve_task(harness_input.task)
        if task is None:
            self.ch_listener.call(
                ListenerEvent(kind="run_failed", message="skill resolution failed")
            )
            return HarnessOutput(
                task=harness_input.task,
                summary="",
                session_id=harness_input.session_id,
            )

        supervisor_input = SupervisorInput(task=task)
        final_run_output = SupervisorAgent(
            self.llm_client,
            self.tool_executor,
        ).run(supervisor_input)

        completion_event_kind = (
            "run_completed" if final_run_output.status == "completed" else "run_failed"
        )
        self.ch_listener.call(
            ListenerEvent(
                kind=completion_event_kind,
                message=f"run finished with status={final_run_output.status}\nsummary: {final_run_output.summary}",
                data={
                    "status": final_run_output.status,
                    "summary": final_run_output.summary,
                },
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
