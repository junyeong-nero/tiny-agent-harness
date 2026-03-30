from tiny_agent_harness.agents.base_agent import BaseAgent
from tiny_agent_harness.agents.shared import SupportsStructuredLLM
from tiny_agent_harness.agents.reviewer.prompt import build_messages
from tiny_agent_harness.schemas import (
    AppConfig,
    PlannerOutput,
    ReviewerInput,
    ReviewerOutput,
    ReviewerStep,
    WorkerOutput,
)
from tiny_agent_harness.tools import ToolCaller


class ReviewerAgent(BaseAgent[ReviewerInput, ReviewerStep]):
    def __init__(
        self,
        llm_client: SupportsStructuredLLM,
        tool_caller: ToolCaller,
        config: AppConfig,
    ):
        super().__init__(
            agent_name="reviewer",
            llm_client=llm_client,
            tool_caller=tool_caller,
            config=config,
            message_builder=build_messages,
            input_schema=ReviewerInput,
            output_schema=ReviewerStep,
            max_tool_steps=config.runtime.reviewer_max_tool_steps,
        )

    def run(self, review_request: ReviewerInput) -> ReviewerOutput:
        review_step = super().run(review_request)
        if review_step.status == "completed":
            if review_step.decision is None:
                return ReviewerOutput(
                    decision="retry",
                    feedback="reviewer returned completed status without a decision",
                )
            return ReviewerOutput(
                decision=review_step.decision,
                feedback=review_step.summary,
            )
        return ReviewerOutput(
            decision="retry", feedback="reviewer exceeded maximum tool steps"
        )


def reviewer_agent(
    original_prompt: str,
    planner_result: PlannerOutput,
    config: AppConfig,
    worker_result: WorkerOutput,
    llm_client: SupportsStructuredLLM,
    tool_caller: ToolCaller,
) -> ReviewerOutput:
    review_request = ReviewerInput(
        original_prompt=original_prompt,
        reply=planner_result.reply,
        task=planner_result.task,
        worker_result=worker_result or planner_result.worker_result,
    )

    return ReviewerAgent(llm_client, tool_caller, config).run(review_request)
