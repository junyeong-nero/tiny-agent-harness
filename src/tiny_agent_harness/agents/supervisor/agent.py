from tiny_agent_harness.agents.planner import planner_agent
from tiny_agent_harness.agents.reviewer import reviewer_agent
from tiny_agent_harness.agents.shared import SupportsStructuredLLM
from tiny_agent_harness.agents.supervisor.prompt import build_messages
from tiny_agent_harness.agents.worker import worker_agent
from tiny_agent_harness.schemas import (
    PlannerInput,
    PlannerOutput,
    ReviewerInput,
    ReviewerOutput,
    SupervisorInput,
    SupervisorOutput,
    WorkerInput,
    WorkerOutput,
)
from tiny_agent_harness.schemas.agents.supervisor import SubAgentCall
from tiny_agent_harness.tools import ToolCaller

_MAX_STEPS = 10


class SupervisorAgent:
    def __init__(
        self,
        llm_client: SupportsStructuredLLM,
        tool_caller: ToolCaller,
    ) -> None:
        self.llm_client = llm_client
        self.tool_caller = tool_caller

    def _dispatch(
        self,
        call: SubAgentCall,
        planner_outputs: list[PlannerOutput],
        worker_outputs: list[WorkerOutput],
        reviewer_outputs: list[ReviewerOutput],
    ) -> str:
        if call.agent == "planner":
            result = planner_agent(
                PlannerInput(task=call.task), self.llm_client, self.tool_caller
            )
            planner_outputs.append(result)
            return result.model_dump_json()
        if call.agent == "worker":
            result = worker_agent(
                WorkerInput(task=call.task), self.llm_client, self.tool_caller
            )
            worker_outputs.append(result)
            return result.model_dump_json()
        if call.agent == "reviewer":
            result = reviewer_agent(
                ReviewerInput(task=call.task), self.llm_client, self.tool_caller
            )
            reviewer_outputs.append(result)
            return result.model_dump_json()
        raise ValueError(f"unknown subagent: {call.agent!r}")

    def run(self, supervisor_input: SupervisorInput) -> SupervisorOutput:
        messages = build_messages(supervisor_input)
        planner_outputs: list[PlannerOutput] = []
        worker_outputs: list[WorkerOutput] = []
        reviewer_outputs: list[ReviewerOutput] = []

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

            result_json = self._dispatch(
                step.subagent_call, planner_outputs, worker_outputs, reviewer_outputs
            )
            messages = messages + [
                {
                    "role": "user",
                    "content": (
                        f"subagent: {step.subagent_call.agent}\n"
                        f"result: {result_json}"
                    ),
                }
            ]

        final_status = (
            "completed" if (step and step.status == "completed") else "failed"
        )
        return SupervisorOutput(
            task=supervisor_input.task,
            status=final_status,
            summary=step.summary if step else "",
            planner_outputs=planner_outputs,
            worker_outputs=worker_outputs,
            reviewer_outputs=reviewer_outputs,
        )


def supervisor_agent(
    supervisor_input: SupervisorInput,
    llm_client: SupportsStructuredLLM,
    tool_caller: ToolCaller,
) -> SupervisorOutput:
    return SupervisorAgent(llm_client, tool_caller).run(supervisor_input)


__all__ = ["SupervisorAgent", "supervisor_agent"]
