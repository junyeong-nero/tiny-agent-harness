from typing import Sequence

from tiny_agent_harness.llm.providers import ChatMessage
from tiny_agent_harness.schemas import (
    ExploreOutput,
    PlannerOutput,
    SupervisorInput,
    SupervisorStep,
    VerifierOutput,
    WorkerOutput,
)

SubAgentOutput = PlannerOutput | ExploreOutput | WorkerOutput | VerifierOutput


def _render_step_history(steps: Sequence[SupervisorStep]) -> str:
    if not steps:
        return "none"

    return "\n".join(
        (
            f"- step {index}: status={step.status}"
            + (
                f", subagent={step.subagent_call.agent}, subtask={step.subagent_call.task}"
                if step.subagent_call is not None
                else ""
            )
            + f", summary={step.summary}"
        )
        for index, step in enumerate(steps, start=1)
    )


def _render_output_list(
    label: str,
    outputs: Sequence[SubAgentOutput],
) -> str:
    if not outputs:
        return f"{label}: []"

    rendered = ", ".join(output.model_dump_json() for output in outputs)
    return f"{label}: [{rendered}]"


def build_messages(
    supervisor_input: SupervisorInput,
    *,
    steps: Sequence[SupervisorStep] = (),
    planner_outputs: Sequence[PlannerOutput] = (),
    explore_outputs: Sequence[ExploreOutput] = (),
    worker_outputs: Sequence[WorkerOutput] = (),
    verifier_outputs: Sequence[VerifierOutput] = (),
    latest_subagent_name: str | None = None,
    latest_subagent_result: SubAgentOutput | None = None,
) -> list[ChatMessage]:
    latest_result = (
        latest_subagent_result.model_dump_json()
        if latest_subagent_result is not None
        else "none"
    )
    return [
        {
            "role": "system",
            "content": (
                "You are the supervisor agent. Orchestrate subagents to complete the user's task.\n\n"
                "Available subagents:\n"
                "  planner  — Breaks the goal into concrete steps.\n"
                "  explorer — Reads code, docs, and resources to gather context.\n"
                "             Output: structured findings for the next agent.\n"
                "  worker   — Makes changes: writes code, applies patches, runs commands.\n"
                "             Does NOT explore. Needs full context in the task description.\n"
                "  verifier — Checks whether a completed task is correct.\n\n"
                "Routing rules:\n"
                "  - 'explore:' steps from planner → explorer\n"
                "  - 'implement:' steps from planner → worker\n"
                "  - If a worker task requires understanding the codebase, run explorer first\n"
                "    and pass its findings in the worker task description.\n"
                "  - Run verifier after worker to confirm correctness.\n\n"
                "Status rules:\n"
                "1. Use status='subagent_call' to delegate work.\n"
                "2. Use status='completed' once the overall goal is fully satisfied.\n"
                "3. Use status='failed' only if the goal cannot be achieved.\n\n"
                "Use the provided step history and accumulated subagent outputs as ground truth.\n"
                "Do not re-request work that has already succeeded unless the latest verifier\n"
                "feedback or prior result clearly justifies a retry.\n\n"
                "summary field:\n"
                "  When status='completed' or 'failed', write the FINAL ANSWER shown directly\n"
                "  to the user. Include actual content from subagents — not status notes.\n\n"
                "If the task is simple or conversational, return status='completed' immediately\n"
                "without calling any subagents. Answer directly in summary."
            ),
        },
        {
            "role": "user",
            "content": (
                f"task: {supervisor_input.task}\n"
                f"step_history:\n{_render_step_history(steps)}\n"
                f"{_render_output_list('planner_outputs', planner_outputs)}\n"
                f"{_render_output_list('explore_outputs', explore_outputs)}\n"
                f"{_render_output_list('worker_outputs', worker_outputs)}\n"
                f"{_render_output_list('verifier_outputs', verifier_outputs)}\n"
                f"latest_subagent: {latest_subagent_name or 'none'}\n"
                f"latest_subagent_result: {latest_result}"
            ),
        },
    ]
