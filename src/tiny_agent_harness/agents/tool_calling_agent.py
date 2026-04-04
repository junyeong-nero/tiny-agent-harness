from typing import Any, Callable, Generic, TypeVar

from pydantic import BaseModel

from tiny_agent_harness.agents.protocols import (
    SupportsStructuredLLM,
    format_tool_result,
)
from tiny_agent_harness.llm.providers import ChatMessage
from tiny_agent_harness.schemas import ToolSpec
from tiny_agent_harness.tools import ToolExecutor

InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


class ToolCallingAgent(Generic[InputT, OutputT]):
    def __init__(
        self,
        agent_name: str,
        llm_client: SupportsStructuredLLM,
        tool_executor: ToolExecutor,
        message_builder: Callable[[InputT, list[ToolSpec]], list[ChatMessage]],
        input_schema: type[InputT],
        output_schema: type[OutputT],
        max_tool_steps: int = 100,
        allowed_tools: list[str] | None = None,
    ):
        self.agent_name = agent_name
        self.client = llm_client
        self.tool_executor = tool_executor
        self.message_builder = message_builder
        self.input_schema = input_schema
        self.output_schema = output_schema
        self.max_tool_steps = max_tool_steps
        self.allowed_tools = allowed_tools or []

    def _get_allowed_tools(self, data: InputT) -> list[str]:
        return self.allowed_tools

    def _build_step_limit_message(self, result: OutputT | None) -> str:
        tool_name = None
        if result is not None:
            tool_call = getattr(result, "tool_call", None)
            tool_name = getattr(tool_call, "tool", None)

        suffix = f"; pending tool call: {tool_name}" if tool_name else ""
        return (
            f"max tool steps exceeded after {self.max_tool_steps} steps{suffix}"
        )

    def _build_failed_output(
        self,
        data: InputT,
        message: str,
        result: OutputT | None = None,
    ) -> OutputT:
        schema_fields = self.output_schema.model_fields

        if result is not None:
            payload: dict[str, Any] = result.model_dump()
        else:
            payload = {
                key: value
                for key, value in data.model_dump().items()
                if key in schema_fields
            }

        payload["status"] = "failed"
        if "tool_call" in schema_fields:
            payload["tool_call"] = None
        if "summary" in schema_fields:
            payload["summary"] = message
        if "findings" in schema_fields:
            payload["findings"] = message
        if "feedback" in schema_fields:
            payload["feedback"] = message
        if "decision" in schema_fields:
            payload["decision"] = "retry"

        return self.output_schema.model_validate(payload)

    def run(self, data: InputT) -> OutputT:
        self.input_schema.model_validate(data.model_dump())
        allowed = self._get_allowed_tools(data)
        tool_specs = self.tool_executor.available_tool_specs(
            actor=self.agent_name,
            allowed_tool_names=allowed,
        )
        messages = self.message_builder(data, tool_specs)

        result: OutputT | None = None
        for _ in range(self.max_tool_steps):
            result = self.client.chat_structured(
                messages=messages,
                agent_name=self.agent_name,
                response_model=self.output_schema,
            )
            messages = messages + [
                {"role": "assistant", "content": result.model_dump_json()}
            ]

            if not getattr(result, "tool_call", None):
                return result

            tool_result = self.tool_executor.run_call(
                result.tool_call,
                actor=self.agent_name,
                allowed_tool_names=allowed,
            )
            messages = messages + [
                {"role": "user", "content": format_tool_result(tool_result)}
            ]

        return self._build_failed_output(
            data=data,
            message=self._build_step_limit_message(result),
            result=result,
        )
