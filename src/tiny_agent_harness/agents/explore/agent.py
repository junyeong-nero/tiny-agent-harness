from tiny_agent_harness.agents.tool_calling_agent import ToolCallingAgent
from tiny_agent_harness.agents.protocols import SupportsStructuredLLM
from tiny_agent_harness.agents.explore.prompt import EXPLORE_TOOLS, build_messages
from tiny_agent_harness.schemas import ExploreInput, ExploreOutput
from tiny_agent_harness.tools import ToolExecutor


class ExploreAgent(ToolCallingAgent[ExploreInput, ExploreOutput]):
    def __init__(
        self,
        llm_client: SupportsStructuredLLM,
        tool_executor: ToolExecutor,
    ):
        super().__init__(
            agent_name="explorer",
            llm_client=llm_client,
            tool_executor=tool_executor,
            message_builder=build_messages,
            input_schema=ExploreInput,
            output_schema=ExploreOutput,
            allowed_tools=EXPLORE_TOOLS,
        )

    def run(self, explore_input: ExploreInput) -> ExploreOutput:
        return super().run(explore_input)
