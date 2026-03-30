from tiny_agent_harness.agents.base_agent import BaseAgent
from tiny_agent_harness.agents.shared import SupportsStructuredLLM
from tiny_agent_harness.agents.reviewer.prompt import build_messages
from tiny_agent_harness.schemas import (
    AppConfig,
    OrchestratorOutput,
    ReviewerInput,
    ReviewerOutput,
    ReviewerStep,
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

    def run(self, request: ReviewerInput) -> ReviewerOutput:
        step = super().run(request)
        if step.status == "completed":
            if step.decision is None:
                return ReviewerOutput(
                    decision="retry",
                    feedback="reviewer returned completed status without a decision",
                )
            return ReviewerOutput(decision=step.decision, feedback=step.summary)
        return ReviewerOutput(
            decision="retry", feedback="reviewer exceeded maximum tool steps"
        )


def reviewer_agent(
    original_prompt: str,
    execution: OrchestratorOutput,
    config: AppConfig,
    llm_client: SupportsStructuredLLM | None = None,
    tool_caller: ToolCaller | None = None,
) -> ReviewerOutput:
    request = ReviewerInput(
        original_prompt=original_prompt,
        reply=execution.reply,
        task=execution.task,
        worker_result=execution.worker_result,
    )

    if llm_client is not None and tool_caller is not None:
        return ReviewerAgent(llm_client, tool_caller, config).run(request)

    if llm_client is not None:
        step = llm_client.chat_structured(
            messages=build_messages(request, config, []),
            agent_name="reviewer",
            response_model=ReviewerStep,
        )
        if step.status == "tool_call":
            return ReviewerOutput(
                decision="retry",
                feedback="reviewer requested a tool, but no tool registry was provided",
            )
        if step.decision is None:
            return ReviewerOutput(
                decision="retry",
                feedback="reviewer returned completed status without a decision",
            )
        return ReviewerOutput(decision=step.decision, feedback=step.summary)

    if request.reply is not None:
        return ReviewerOutput(
            decision="approve",
            feedback=f"reviewer mock approved direct reply with model {config.models.reviewer}",
        )
    if request.worker_result.status != "completed":
        return ReviewerOutput(
            decision="retry",
            feedback=(
                f"reviewer mock rejected task {request.task.id} "
                f"with model {config.models.reviewer}"
            ),
        )
    return ReviewerOutput(
        decision="approve",
        feedback=(
            f"reviewer mock approved task {request.task.id} "
            f"with model {config.models.reviewer}"
        ),
    )
