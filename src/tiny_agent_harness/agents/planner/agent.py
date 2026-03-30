from tiny_agent_harness.agents.base_agent import BaseAgent
from tiny_agent_harness.agents.shared import SupportsStructuredLLM
from tiny_agent_harness.agents.planner.prompt import (
    PLANNER_TOOLS,
    WORKER_TOOLS,
    build_messages,
)
from tiny_agent_harness.schemas import (
    Config,
    PlannerInput,
    PlannerOutput,
    WorkerInput,
)
from tiny_agent_harness.tools import ToolCaller


class PlannerAgent(BaseAgent[PlannerInput, PlannerOutput]):
    def __init__(
        self,
        llm_client: SupportsStructuredLLM,
        tool_caller: ToolCaller,
    ):
        super().__init__(
            agent_name="planner",
            llm_client=llm_client,
            tool_caller=tool_caller,
            message_builder=build_messages,
            input_schema=PlannerInput,
            output_schema=PlannerOutput,
            allowed_tools=PLANNER_TOOLS,
        )

    def run(self, state: PlannerInput) -> PlannerOutput:
        return super().run(state)


def planner_agent(
    planner_input: PlannerInput,
    llm_client: SupportsStructuredLLM,
    tool_caller: ToolCaller,
) -> PlannerOutput:

    return PlannerAgent(llm_client, tool_caller).run(planner_input)
