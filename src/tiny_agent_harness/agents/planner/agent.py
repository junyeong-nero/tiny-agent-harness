from tiny_agent_harness.agents.tool_calling_agent import ToolCallingAgent
from tiny_agent_harness.agents.protocols import SupportsStructuredLLM
from tiny_agent_harness.agents.planner.prompt import (
    PLANNER_TOOLS,
    build_messages,
)
from tiny_agent_harness.schemas import (
    PlannerInput,
    PlannerOutput,
)
from tiny_agent_harness.tools import ToolExecutor


class PlannerAgent(ToolCallingAgent[PlannerInput, PlannerOutput]):
    def __init__(
        self,
        llm_client: SupportsStructuredLLM,
        tool_executor: ToolExecutor,
    ):
        super().__init__(
            agent_name="planner",
            llm_client=llm_client,
            tool_executor=tool_executor,
            message_builder=build_messages,
            input_schema=PlannerInput,
            output_schema=PlannerOutput,
            allowed_tools=PLANNER_TOOLS,
            max_tool_steps=3,
        )

    def run(self, state: PlannerInput) -> PlannerOutput:
        return super().run(state)
