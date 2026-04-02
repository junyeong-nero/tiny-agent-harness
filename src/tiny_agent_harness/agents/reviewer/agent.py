from tiny_agent_harness.agents.tool_calling_agent import ToolCallingAgent
from tiny_agent_harness.agents.protocols import SupportsStructuredLLM
from tiny_agent_harness.agents.reviewer.prompt import build_messages
from tiny_agent_harness.schemas import ReviewerInput, ReviewerOutput
from tiny_agent_harness.tools import ToolExecutor


class ReviewerAgent(ToolCallingAgent[ReviewerInput, ReviewerOutput]):
    def __init__(
        self,
        llm_client: SupportsStructuredLLM,
        tool_executor: ToolExecutor,
    ):
        super().__init__(
            agent_name="reviewer",
            llm_client=llm_client,
            tool_executor=tool_executor,
            message_builder=build_messages,
            input_schema=ReviewerInput,
            output_schema=ReviewerOutput,
        )

    def run(self, reviewer_input: ReviewerInput) -> ReviewerOutput:
        return super().run(reviewer_input)
