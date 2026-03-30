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
    worker_result: WorkerOutput | None = None,
    llm_client: SupportsStructuredLLM | None = None,
    tool_caller: ToolCaller | None = None,
) -> ReviewerOutput:
    review_request = ReviewerInput(
        original_prompt=original_prompt,
        reply=planner_result.reply,
        task=planner_result.task,
        worker_result=worker_result or planner_result.worker_result,
    )

    if llm_client is not None and tool_caller is not None:
        return ReviewerAgent(llm_client, tool_caller, config).run(review_request)

    if llm_client is not None:
        review_step = llm_client.chat_structured(
            messages=build_messages(review_request, config, []),
            agent_name="reviewer",
            response_model=ReviewerStep,
        )
        if review_step.status == "tool_call":
            return ReviewerOutput(
                decision="retry",
                feedback="reviewer requested a tool, but no tool registry was provided",
            )
        if review_step.decision is None:
            return ReviewerOutput(
                decision="retry",
                feedback="reviewer returned completed status without a decision",
            )
        return ReviewerOutput(
            decision=review_step.decision,
            feedback=review_step.summary,
        )

    if review_request.reply is not None:
        return ReviewerOutput(
            decision="approve",
            feedback=(
                "reviewer mock approved direct reply "
                f"with model {config.models.reviewer}"
            ),
        )
    if review_request.worker_result is None or review_request.task is None:
        return ReviewerOutput(
            decision="retry",
            feedback="reviewer mock rejected missing worker result",
        )
    if review_request.worker_result.status != "completed":
        return ReviewerOutput(
            decision="retry",
            feedback=(
                f"reviewer mock rejected task {review_request.task.id} "
                f"with model {config.models.reviewer}"
            ),
        )
    return ReviewerOutput(
        decision="approve",
        feedback=(
            f"reviewer mock approved task {review_request.task.id} "
            f"with model {config.models.reviewer}"
        ),
    )
