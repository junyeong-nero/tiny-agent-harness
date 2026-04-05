from tiny_agent_harness.agents.protocols import format_tool_catalog
from tiny_agent_harness.llm.providers import ChatMessage
from tiny_agent_harness.schemas import ExploreInput, ToolSpec


EXPLORE_TOOLS = ["list_files", "search", "glob", "read_file", "git_status", "git_diff"]


def build_messages(
    explore_input: ExploreInput,
    tool_specs: list[ToolSpec],
) -> list[ChatMessage]:
    tool_catalog = format_tool_catalog(tool_specs)

    return [
        {
            "role": "system",
            "content": (
                "You are the explore agent. You read, search, and collect context.\n"
                "You must NOT modify any files or run commands.\n\n"
                "Your output (findings) will be handed directly to the worker agent.\n"
                "Write findings as actionable context: what exists, where it is, what\n"
                "patterns are used, and what the worker needs to know to act.\n"
                "Do not summarize vaguely — include file paths, function names, and\n"
                "concrete details the worker can reference without re-reading anything.\n\n"
                "status values:\n"
                "  'completed' — context is fully gathered. Write structured findings and\n"
                "                list every file you read in sources.\n"
                "  'failed'    — required information cannot be found. Explain why.\n\n"
                "tool_call field:\n"
                "  Set tool_call when you need more information. You will be called again\n"
                "  with the result. Only use: list_files, search, glob, read_file, git_status, git_diff.\n\n"
                "Stop as soon as the worker has enough to act. Do not over-explore."
            ),
        },
        {
            "role": "user",
            "content": (
                f"task: {explore_input.task}\n"
                f"tool_catalog:\n{tool_catalog}\n"
            ),
        },
    ]
