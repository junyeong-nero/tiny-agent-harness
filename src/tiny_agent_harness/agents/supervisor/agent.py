from dataclasses import dataclass, field

from tiny_agent_harness.agents.explore import ExploreAgent
from tiny_agent_harness.agents.planner import PlannerAgent
from tiny_agent_harness.agents.protocols import SupportsStructuredLLM
from tiny_agent_harness.agents.supervisor.prompt import build_messages
from tiny_agent_harness.agents.verifier import VerifierAgent
from tiny_agent_harness.agents.worker import WorkerAgent
from tiny_agent_harness.llm.providers import ChatMessage
from tiny_agent_harness.schemas import (
    ExploreInput,
    ExploreOutput,
    PlannerInput,
    PlannerOutput,
    SupervisorInput,
    SupervisorOutput,
    SupervisorStep,
    VerifierInput,
    VerifierOutput,
    WorkerInput,
    WorkerOutput,
)
from tiny_agent_harness.schemas.agents.supervisor import SubAgentCall
from tiny_agent_harness.tools import ToolExecutor

_MAX_STEPS = 10
SubAgentOutput = PlannerOutput | ExploreOutput | WorkerOutput | VerifierOutput


@dataclass
class _SupervisorState:
    planner_outputs: list[PlannerOutput] = field(default_factory=list)
    explore_outputs: list[ExploreOutput] = field(default_factory=list)
    worker_outputs: list[WorkerOutput] = field(default_factory=list)
    verifier_outputs: list[VerifierOutput] = field(default_factory=list)
    steps: list[SupervisorStep] = field(default_factory=list)
    latest_subagent_name: str | None = None
    latest_subagent_result: SubAgentOutput | None = None


class SupervisorAgent:
    def __init__(
        self,
        llm_client: SupportsStructuredLLM,
        tool_executor: ToolExecutor,
    ) -> None:
        self.llm_client = llm_client
        self.tool_executor = tool_executor

    def _dispatch(
        self,
        call: SubAgentCall,
        state: _SupervisorState,
    ) -> SubAgentOutput:
        if call.agent == "planner":
            result = PlannerAgent(self.llm_client, self.tool_executor).run(
                PlannerInput(task=call.task)
            )
            state.planner_outputs.append(result)
            return result
        if call.agent == "explorer":
            result = ExploreAgent(self.llm_client, self.tool_executor).run(
                ExploreInput(task=call.task)
            )
            state.explore_outputs.append(result)
            return result
        if call.agent == "worker":
            result = WorkerAgent(self.llm_client, self.tool_executor).run(
                WorkerInput(task=call.task)
            )
            state.worker_outputs.append(result)
            return result
        if call.agent == "verifier":
            result = VerifierAgent(self.llm_client, self.tool_executor).run(
                VerifierInput(task=call.task)
            )
            state.verifier_outputs.append(result)
            return result
        raise ValueError(f"unknown subagent: {call.agent!r}")

    def _failed_output(
        self,
        supervisor_input: SupervisorInput,
        summary: str,
        state: _SupervisorState,
    ) -> SupervisorOutput:
        return SupervisorOutput(
            task=supervisor_input.task,
            status="failed",
            summary=summary,
            planner_outputs=state.planner_outputs,
            explore_outputs=state.explore_outputs,
            worker_outputs=state.worker_outputs,
            verifier_outputs=state.verifier_outputs,
        )

    def _subagent_failure_summary(
        self,
        agent_name: str,
        result: SubAgentOutput,
    ) -> str:
        detail = (
            getattr(result, "summary", None)
            or getattr(result, "findings", None)
            or getattr(result, "feedback", None)
            or "subagent failed"
        )
        return f"{agent_name} failed: {detail}"

    def _build_retry_worker_task(
        self,
        supervisor_input: SupervisorInput,
        verifier_output: VerifierOutput,
        state: _SupervisorState,
    ) -> str:
        sections = [
            "address the verifier feedback and update the implementation",
            f"original task: {supervisor_input.task}",
            f"verifier feedback: {verifier_output.feedback}",
        ]

        if state.worker_outputs:
            last_worker_output = state.worker_outputs[-1]
            sections.append(f"latest worker summary: {last_worker_output.summary}")
            if last_worker_output.changed_files:
                sections.append(
                    "latest changed files: "
                    + ", ".join(last_worker_output.changed_files)
                )
            if last_worker_output.test_results:
                sections.append(
                    "latest test results: "
                    + " | ".join(last_worker_output.test_results)
                )

        if state.explore_outputs:
            sections.append(
                f"latest explore findings: {state.explore_outputs[-1].findings}"
            )

        return "\n".join(sections)

    def _retry_after_verifier_feedback(
        self,
        supervisor_input: SupervisorInput,
        verifier_output: VerifierOutput,
        state: _SupervisorState,
    ) -> WorkerOutput:
        retry_task = self._build_retry_worker_task(
            supervisor_input=supervisor_input,
            verifier_output=verifier_output,
            state=state,
        )
        retry_result = WorkerAgent(self.llm_client, self.tool_executor).run(
            WorkerInput(task=retry_task)
        )
        state.worker_outputs.append(retry_result)
        state.latest_subagent_name = "worker"
        state.latest_subagent_result = retry_result
        return retry_result

    def _build_messages(
        self,
        supervisor_input: SupervisorInput,
        state: _SupervisorState,
    ) -> list[ChatMessage]:
        return build_messages(
            supervisor_input=supervisor_input,
            steps=state.steps,
            planner_outputs=state.planner_outputs,
            explore_outputs=state.explore_outputs,
            worker_outputs=state.worker_outputs,
            verifier_outputs=state.verifier_outputs,
            latest_subagent_name=state.latest_subagent_name,
            latest_subagent_result=state.latest_subagent_result,
        )

    def run(self, supervisor_input: SupervisorInput) -> SupervisorOutput:
        state = _SupervisorState()
        step: SupervisorStep | None = None

        for _ in range(_MAX_STEPS):
            step = self.llm_client.chat_structured(
                messages=self._build_messages(supervisor_input, state),
                agent_name="supervisor",
                response_model=SupervisorStep,
            )
            state.steps.append(step)

            if step.status != "subagent_call" or step.subagent_call is None:
                break

            result = self._dispatch(step.subagent_call, state)
            state.latest_subagent_name = step.subagent_call.agent
            state.latest_subagent_result = result
            if result.status == "failed":
                return self._failed_output(
                    supervisor_input=supervisor_input,
                    summary=self._subagent_failure_summary(step.subagent_call.agent, result),
                    state=state,
                )
            if (
                step.subagent_call.agent == "verifier"
                and isinstance(result, VerifierOutput)
                and result.decision == "retry"
            ):
                retry_result = self._retry_after_verifier_feedback(
                    supervisor_input=supervisor_input,
                    verifier_output=result,
                    state=state,
                )
                if retry_result.status == "failed":
                    return self._failed_output(
                        supervisor_input=supervisor_input,
                        summary=self._subagent_failure_summary("worker", retry_result),
                        state=state,
                    )

        if step is None:
            return self._failed_output(
                supervisor_input=supervisor_input,
                summary="supervisor produced no steps",
                state=state,
            )

        if step.status == "subagent_call" and step.subagent_call is not None:
            return self._failed_output(
                supervisor_input=supervisor_input,
                summary=(
                    "max supervisor steps exceeded with pending subagent call: "
                    f"{step.subagent_call.agent}"
                ),
                state=state,
            )

        if step.status == "failed":
            return self._failed_output(
                supervisor_input=supervisor_input,
                summary=step.summary,
                state=state,
            )

        return SupervisorOutput(
            task=supervisor_input.task,
            status="completed",
            summary=step.summary,
            planner_outputs=state.planner_outputs,
            explore_outputs=state.explore_outputs,
            worker_outputs=state.worker_outputs,
            verifier_outputs=state.verifier_outputs,
        )


__all__ = ["SupervisorAgent"]
