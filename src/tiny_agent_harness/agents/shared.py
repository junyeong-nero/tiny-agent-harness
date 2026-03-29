from typing import Protocol

from tiny_agent_harness.providers import ChatMessage
from tiny_agent_harness.schemas import ToolRequirement
from tiny_agent_harness.tools import ToolResult


class SupportsStructuredLLM(Protocol):
    def chat_structured(
        self,
        messages: list[ChatMessage],
        agent_name: str,
        response_model: type,
        model: str | None = None,
        max_retries: int | None = None,
    ): ...


def format_tool_catalog(tool_requirements: list[ToolRequirement]) -> str:
    return (
        "\n".join(
            f"- {req.name}: {req.description}\n  schema: {req.arguments_schema}"
            for req in tool_requirements
        )
        or "none"
    )


def format_tool_result(result: ToolResult) -> str:
    return (
        f"tool={result.tool}\n"
        f"ok={result.ok}\n"
        f"content={result.content}\n"
        f"error={result.error or ''}"
    )
