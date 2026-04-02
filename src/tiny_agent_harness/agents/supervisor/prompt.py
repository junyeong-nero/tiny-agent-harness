from tiny_agent_harness.llm.providers import ChatMessage
from tiny_agent_harness.schemas import SupervisorInput


def build_messages(supervisor_input: SupervisorInput) -> list[ChatMessage]:
    return [
        {
            "role": "system",
            "content": (
                "You are the supervisor agent. Orchestrate subagents to complete the user's task.\n\n"
                "Available subagents:\n"
                "  planner  — Analyzes the task and breaks it into concrete steps.\n"
                "  worker   — Executes a specific task (explore, implement, or verify).\n"
                "  verifier — Verifies whether a task was correctly completed.\n\n"
                "Decision rules:\n"
                "1. Use status='subagent_call' to delegate work. Set agent and task accordingly.\n"
                "2. Use status='completed' once the overall goal is fully satisfied.\n"
                "3. Use status='failed' only if the goal cannot be achieved.\n\n"
                "summary field:\n"
                "  When status='completed' or 'failed', summary is the FINAL ANSWER shown directly\n"
                "  to the user. Write a complete, helpful response — not a status note.\n"
                "  Incorporate the actual content produced by subagents (e.g. the text they\n"
                "  generated, findings, or results). Do NOT write things like 'task completed'.\n\n"
                "If the task is simple or conversational, return status='completed' immediately "
                "without calling any subagents. Answer directly in summary."
            ),
        },
        {
            "role": "user",
            "content": f"task: {supervisor_input.task}",
        },
    ]
