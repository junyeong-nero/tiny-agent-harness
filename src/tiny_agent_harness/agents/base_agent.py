from typing import Callable, Generic, TypeVar

from pydantic import BaseModel

from tiny_agent_harness.agents.shared import SupportsStructuredLLM, format_tool_result
from tiny_agent_harness.providers import ChatMessage
from tiny_agent_harness.schemas import AppConfig, ToolSpec
from tiny_agent_harness.tools import ToolCaller

InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


class BaseAgent(Generic[InputT, OutputT]):
    def __init__(
        self,
        agent_name: str,
        llm_client: SupportsStructuredLLM,
        tool_caller: ToolCaller,
        config: AppConfig,
        message_builder: Callable[
            [InputT, AppConfig, list[ToolSpec]], list[ChatMessage]
        ],
        input_schema: type[InputT],
        output_schema: type[OutputT],
        max_tool_steps: int = 3,
        allowed_tools: list[str] | None = None,
    ):
        self.agent_name = agent_name
        self.client = llm_client
        self.tool_caller = tool_caller
        self.config = config
        self.message_builder = message_builder
        self.input_schema = input_schema
        self.output_schema = output_schema
        self.max_tool_steps = max_tool_steps
        self.allowed_tools = allowed_tools or []

    def _get_allowed_tools(self, data: InputT) -> list[str]:
        return self.allowed_tools

    def run(self, data: InputT) -> OutputT:
        self.input_schema.model_validate(data.model_dump())
        allowed = self._get_allowed_tools(data)
        tool_specs = self.tool_caller.available_tool_specs(
            actor=self.agent_name,
            allowed_tool_names=allowed,
        )
        messages = self.message_builder(data, self.config, tool_specs)

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
                break

            tool_result = self.tool_caller.run_call(
                result.tool_call,
                actor=self.agent_name,
                allowed_tool_names=allowed,
            )
            messages = messages + [
                {"role": "user", "content": format_tool_result(tool_result)}
            ]

        return result
