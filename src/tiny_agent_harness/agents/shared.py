from typing import Protocol

from tiny_agent_harness.providers import ChatMessage
from tiny_agent_harness.schemas import ToolSpec
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


def format_tool_catalog(tool_specs: list[ToolSpec]) -> str:
    return (
        "\n".join(
            f"- {spec.name}: {spec.description}\n  schema: {spec.arguments_schema}"
            for spec in tool_specs
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
