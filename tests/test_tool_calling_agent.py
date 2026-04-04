from typing import Literal
from unittest.mock import MagicMock

from pydantic import BaseModel

from tiny_agent_harness.agents.tool_calling_agent import ToolCallingAgent
from tiny_agent_harness.schemas import ToolInput, ToolResult, ToolSpec
from tiny_agent_harness.tools.tool_executor import ToolExecutor


class DummyInput(BaseModel):
    task: str


class DummyOutput(BaseModel):
    task: str
    status: Literal["completed", "failed"]
    summary: str
    tool_call: ToolInput | None = None


def _build_messages(data: DummyInput, tool_specs: list[ToolSpec]) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": "Use tools when needed."},
        {
            "role": "user",
            "content": f"task={data.task}\ntools={[spec.name for spec in tool_specs]}",
        },
    ]


class TestToolCallingAgent:
    def test_tool_calling_agent_is_importable_from_new_module(self):
        assert ToolCallingAgent.__name__ == "ToolCallingAgent"

    def test_recoverable_tool_failure_is_added_to_messages_and_run_continues(self):
        llm = MagicMock()
        llm.chat_structured.side_effect = [
            DummyOutput(
                task="recover",
                status="completed",
                summary="try a missing tool first",
                tool_call=ToolInput(tool="missing_tool", arguments={}),
            ),
            DummyOutput(
                task="recover",
                status="completed",
                summary="fallback to allowed tool",
                tool_call=ToolInput(tool="echo", arguments={"message": "hello"}),
            ),
            DummyOutput(
                task="recover",
                status="completed",
                summary="done after recovery",
            ),
        ]
        tool_executor = MagicMock(spec=ToolExecutor)
        tool_executor.available_tool_specs.return_value = [
            ToolSpec(
                name="echo",
                description="echo text",
                arguments_schema={"type": "object"},
            )
        ]
        tool_executor.run_call.side_effect = [
            ToolResult(tool="missing_tool", ok=False, error="unknown tool: missing_tool"),
            ToolResult(tool="echo", ok=True, content="hello"),
        ]

        agent = ToolCallingAgent(
            agent_name="worker",
            llm_client=llm,
            tool_executor=tool_executor,
            message_builder=_build_messages,
            input_schema=DummyInput,
            output_schema=DummyOutput,
            max_tool_steps=3,
            allowed_tools=["echo"],
        )

        result = agent.run(DummyInput(task="recover"))

        assert result.summary == "done after recovery"
        assert llm.chat_structured.call_count == 3
        assert tool_executor.run_call.call_count == 2
        second_messages = llm.chat_structured.call_args_list[1].kwargs["messages"]
        assert second_messages[-1]["role"] == "user"
        assert "tool=missing_tool" in second_messages[-1]["content"]
        assert "ok=False" in second_messages[-1]["content"]
        assert "unknown tool: missing_tool" in second_messages[-1]["content"]
