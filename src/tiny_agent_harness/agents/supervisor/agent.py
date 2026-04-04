from tiny_agent_harness.agents.explore import ExploreAgent
from tiny_agent_harness.agents.planner import PlannerAgent
from tiny_agent_harness.agents.protocols import SupportsStructuredLLM
from tiny_agent_harness.agents.verifier import VerifierAgent
from tiny_agent_harness.agents.supervisor.prompt import build_messages
from tiny_agent_harness.agents.worker import WorkerAgent
from tiny_agent_harness.schemas import (
    ExploreInput,
    ExploreOutput,
    PlannerInput,
    PlannerOutput,
    VerifierInput,
    VerifierOutput,
    SupervisorInput,
    SupervisorOutput,
    WorkerInput,
    WorkerOutput,
)
from tiny_agent_harness.schemas.agents.supervisor import SubAgentCall
from tiny_agent_harness.tools import ToolExecutor

_MAX_STEPS = 10
SubAgentOutput = PlannerOutput | ExploreOutput | WorkerOutput | VerifierOutput


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
        planner_outputs: list[PlannerOutput],
        explore_outputs: list[ExploreOutput],
        worker_outputs: list[WorkerOutput],
        verifier_outputs: list[VerifierOutput],
    ) -> SubAgentOutput:
        if call.agent == "planner":
            result = PlannerAgent(self.llm_client, self.tool_executor).run(
                PlannerInput(task=call.task)
            )
            planner_outputs.append(result)
            return result
        if call.agent == "explorer":
            result = ExploreAgent(self.llm_client, self.tool_executor).run(
                ExploreInput(task=call.task)
            )
            explore_outputs.append(result)
            return result
        if call.agent == "worker":
            result = WorkerAgent(self.llm_client, self.tool_executor).run(
                WorkerInput(task=call.task)
            )
            worker_outputs.append(result)
            return result
        if call.agent == "verifier":
            result = VerifierAgent(self.llm_client, self.tool_executor).run(
                VerifierInput(task=call.task)
            )
            verifier_outputs.append(result)
            return result
        raise ValueError(f"unknown subagent: {call.agent!r}")

    def _failed_output(
        self,
        supervisor_input: SupervisorInput,
        summary: str,
        planner_outputs: list[PlannerOutput],
        explore_outputs: list[ExploreOutput],
        worker_outputs: list[WorkerOutput],
        verifier_outputs: list[VerifierOutput],
    ) -> SupervisorOutput:
        return SupervisorOutput(
            task=supervisor_input.task,
            status="failed",
            summary=summary,
            planner_outputs=planner_outputs,
            explore_outputs=explore_outputs,
            worker_outputs=worker_outputs,
            verifier_outputs=verifier_outputs,
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

    def run(self, supervisor_input: SupervisorInput) -> SupervisorOutput:
        messages = build_messages(supervisor_input)
        planner_outputs: list[PlannerOutput] = []
        explore_outputs: list[ExploreOutput] = []
        worker_outputs: list[WorkerOutput] = []
        verifier_outputs: list[VerifierOutput] = []

        step: SupervisorOutput | None = None
        for _ in range(_MAX_STEPS):
            step = self.llm_client.chat_structured(
                messages=messages,
                agent_name="supervisor",
                response_model=SupervisorOutput,
            )
            messages = messages + [
                {"role": "assistant", "content": step.model_dump_json()}
            ]

            if step.status != "subagent_call" or step.subagent_call is None:
                break

            result = self._dispatch(
                step.subagent_call,
                planner_outputs,
                explore_outputs,
                worker_outputs,
                verifier_outputs,
            )
            if result.status == "failed":
                return self._failed_output(
                    supervisor_input=supervisor_input,
                    summary=self._subagent_failure_summary(step.subagent_call.agent, result),
                    planner_outputs=planner_outputs,
                    explore_outputs=explore_outputs,
                    worker_outputs=worker_outputs,
                    verifier_outputs=verifier_outputs,
                )

            messages = messages + [
                {
                    "role": "user",
                    "content": (
                        f"subagent: {step.subagent_call.agent}\n"
                        f"result: {result.model_dump_json()}"
                    ),
                }
            ]

        if step and step.status == "subagent_call" and step.subagent_call is not None:
            return self._failed_output(
                supervisor_input=supervisor_input,
                summary=(
                    "max supervisor steps exceeded with pending subagent call: "
                    f"{step.subagent_call.agent}"
                ),
                planner_outputs=planner_outputs,
                explore_outputs=explore_outputs,
                worker_outputs=worker_outputs,
                verifier_outputs=verifier_outputs,
            )

        final_status = (
            "completed" if (step and step.status == "completed") else "failed"
        )
        return SupervisorOutput(
            task=supervisor_input.task,
            status=final_status,
            summary=step.summary if step else "",
            planner_outputs=planner_outputs,
            explore_outputs=explore_outputs,
            worker_outputs=worker_outputs,
            verifier_outputs=verifier_outputs,
        )


__all__ = ["SupervisorAgent"]
