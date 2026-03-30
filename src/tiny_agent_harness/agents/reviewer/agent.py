from tiny_agent_harness.agents.base_agent import BaseAgent
from tiny_agent_harness.agents.shared import SupportsStructuredLLM
from tiny_agent_harness.agents.reviewer.prompt import build_messages
from tiny_agent_harness.schemas import ReviewerInput, ReviewerOutput
from tiny_agent_harness.tools import ToolCaller


class ReviewerAgent(BaseAgent[ReviewerInput, ReviewerOutput]):
    def __init__(
        self,
        llm_client: SupportsStructuredLLM,
        tool_caller: ToolCaller,
    ):
        super().__init__(
            agent_name="reviewer",
            llm_client=llm_client,
            tool_caller=tool_caller,
            message_builder=build_messages,
            input_schema=ReviewerInput,
            output_schema=ReviewerOutput,
        )

    def run(self, reviewer_input: ReviewerInput) -> ReviewerOutput:
        return super().run(reviewer_input)


def reviewer_agent(
    reviewer_input: ReviewerInput,
    llm_client: SupportsStructuredLLM,
    tool_caller: ToolCaller,
) -> ReviewerOutput:
    return ReviewerAgent(llm_client, tool_caller).run(reviewer_input)
