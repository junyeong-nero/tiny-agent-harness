from tiny_agent_harness.agents.tool_calling_agent import ToolCallingAgent
from tiny_agent_harness.agents.protocols import SupportsStructuredLLM
from tiny_agent_harness.agents.verifier.prompt import build_messages
from tiny_agent_harness.schemas import VerifierInput, VerifierOutput
from tiny_agent_harness.tools import ToolExecutor


class VerifierAgent(ToolCallingAgent[VerifierInput, VerifierOutput]):
    def __init__(
        self,
        llm_client: SupportsStructuredLLM,
        tool_executor: ToolExecutor,
    ):
        super().__init__(
            agent_name="verifier",
            llm_client=llm_client,
            tool_executor=tool_executor,
            message_builder=build_messages,
            input_schema=VerifierInput,
            output_schema=VerifierOutput,
        )

    def run(self, verifier_input: VerifierInput) -> VerifierOutput:
        return super().run(verifier_input)
