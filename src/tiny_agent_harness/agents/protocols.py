from typing import Protocol

from tiny_agent_harness.llm.providers import ChatMessage
from tiny_agent_harness.schemas import ToolResult, ToolSpec


class SupportsStructuredLLM(Protocol):
    def chat_structured(
        self,
        messages: list[ChatMessage],
        agent_name: str,
        response_model: type,
        model: str | None = None,
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
