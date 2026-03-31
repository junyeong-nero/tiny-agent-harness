import pytest
from unittest.mock import MagicMock, patch

from tiny_agent_harness.agents.planner.agent import PlannerAgent, PLANNER_TOOLS
from tiny_agent_harness.agents.planner.prompt import build_messages, WORKER_TOOLS
from tiny_agent_harness.schemas import (
    PlannerInput,
    PlannerOutput,
    ToolInput,
    ToolResult,
    ToolSpec,
)
from tiny_agent_harness.schemas.agents.planner import Plan
from tiny_agent_harness.tools.tool_caller import ToolCaller


# ── helpers ───────────────────────────────────────────────────────────────────

def _input(**kw) -> PlannerInput:
    return PlannerInput(**{"task": "implement feature X", **kw})


def _output(**kw) -> PlannerOutput:
    defaults = {"task": "implement feature X", "status": "completed", "summary": "done"}
    return PlannerOutput(**{**defaults, **kw})


def _mock_llm(return_value=None) -> MagicMock:
    llm = MagicMock()
    llm.chat_structured.return_value = return_value or _output()
    return llm


def _mock_tool_caller(specs=None) -> MagicMock:
    tc = MagicMock(spec=ToolCaller)
    tc.available_tool_specs.return_value = specs or []
    return tc


# ── PlannerInput schema ───────────────────────────────────────────────────────

class TestPlannerInput:
    def test_valid_input(self):
        pi = PlannerInput(task="write a function")
        assert pi.task == "write a function"

    def test_task_required(self):
        with pytest.raises(Exception):
            PlannerInput()

    def test_extra_fields_forbidden(self):
        with pytest.raises(Exception):
            PlannerInput(task="t", unknown="x")


# ── PlannerOutput schema ──────────────────────────────────────────────────────

class TestPlannerOutput:
    def test_defaults(self):
        po = PlannerOutput(task="t", status="completed", summary="done")
        assert po.tool_call is None
        assert po.plans == []

    def test_all_status_values(self):
        for status in ("completed", "failed", "no-planning"):
            po = PlannerOutput(task="t", status=status, summary="x")
            assert po.status == status

    def test_invalid_status_rejected(self):
        with pytest.raises(Exception):
            PlannerOutput(task="t", status="unknown", summary="x")

    def test_with_tool_call(self):
        po = _output(tool_call=ToolInput(tool="list_files", arguments={"path": "."}))
        assert po.tool_call.tool == "list_files"

    def test_with_plans(self):
        po = _output(plans=[Plan(task="step 1"), Plan(task="step 2")])
        assert len(po.plans) == 2
        assert po.plans[0].task == "step 1"

    def test_extra_fields_forbidden(self):
        with pytest.raises(Exception):
            PlannerOutput(task="t", status="completed", summary="x", unknown="y")


# ── PlannerAgent construction ─────────────────────────────────────────────────

class TestPlannerAgentInit:
    def test_agent_name_is_planner(self):
        agent = PlannerAgent(_mock_llm(), _mock_tool_caller())
        assert agent.agent_name == "planner"

    def test_max_tool_steps_defaults_to_three(self):
        agent = PlannerAgent(_mock_llm(), _mock_tool_caller())
        assert agent.max_tool_steps == 3

    def test_stores_llm_and_tool_caller(self):
        llm, tc = _mock_llm(), _mock_tool_caller()
        agent = PlannerAgent(llm, tc)
        assert agent.client is llm
        assert agent.tool_caller is tc

    def test_allowed_tools_set_to_planner_tools(self):
        agent = PlannerAgent(_mock_llm(), _mock_tool_caller())
        assert set(agent.allowed_tools) == set(PLANNER_TOOLS)


# ── PlannerAgent.run ──────────────────────────────────────────────────────────

class TestPlannerAgentRun:
    @patch("tiny_agent_harness.agents.planner.agent.build_messages")
    def test_returns_output_without_tool_call(self, mock_bm):
        expected = _output(status="completed", summary="here is the plan")
        mock_bm.return_value = [{"role": "user", "content": "task"}]

        result = PlannerAgent(_mock_llm(expected), _mock_tool_caller()).run(_input())

        assert result.status == "completed"
        assert result.summary == "here is the plan"

    @patch("tiny_agent_harness.agents.planner.agent.build_messages")
    def test_single_llm_call_when_no_tool_call(self, mock_bm):
        llm = _mock_llm()
        mock_bm.return_value = []

        PlannerAgent(llm, _mock_tool_caller()).run(_input())

        llm.chat_structured.assert_called_once()

    @patch("tiny_agent_harness.agents.planner.agent.build_messages")
    def test_executes_tool_call_then_returns_final(self, mock_bm):
        tool_output = _output(tool_call=ToolInput(tool="list_files", arguments={"path": "."}))
        final_output = _output(summary="explored and planned")
        llm = _mock_llm()
        llm.chat_structured.side_effect = [tool_output, final_output]
        tc = _mock_tool_caller()
        tc.run_call.return_value = ToolResult(tool="list_files", ok=True, content="src/\ntests/")
        mock_bm.return_value = [{"role": "user", "content": "task"}]

        result = PlannerAgent(llm, tc).run(_input())

        assert result.summary == "explored and planned"
        assert llm.chat_structured.call_count == 2
        tc.run_call.assert_called_once()

    @patch("tiny_agent_harness.agents.planner.agent.build_messages")
    def test_stops_after_max_tool_steps(self, mock_bm):
        always_tool = _output(tool_call=ToolInput(tool="list_files", arguments={}))
        llm = _mock_llm(always_tool)
        tc = _mock_tool_caller()
        tc.run_call.return_value = ToolResult(tool="list_files", ok=True, content="x")
        mock_bm.return_value = []

        PlannerAgent(llm, tc).run(_input())

        assert llm.chat_structured.call_count == 3

    @patch("tiny_agent_harness.agents.planner.agent.build_messages")
    def test_tool_caller_receives_planner_actor(self, mock_bm):
        tool_output = _output(tool_call=ToolInput(tool="list_files", arguments={}))
        llm = _mock_llm()
        llm.chat_structured.side_effect = [tool_output, _output()]
        tc = _mock_tool_caller()
        tc.run_call.return_value = ToolResult(tool="list_files", ok=True, content="x")
        mock_bm.return_value = []

        PlannerAgent(llm, tc).run(_input())

        assert tc.run_call.call_args.kwargs.get("actor") == "planner"

    @patch("tiny_agent_harness.agents.planner.agent.build_messages")
    def test_llm_called_with_planner_output_schema(self, mock_bm):
        llm = _mock_llm()
        mock_bm.return_value = []

        PlannerAgent(llm, _mock_tool_caller()).run(_input())

        assert llm.chat_structured.call_args.kwargs.get("response_model") is PlannerOutput

    @patch("tiny_agent_harness.agents.planner.agent.build_messages")
    def test_llm_called_with_agent_name(self, mock_bm):
        llm = _mock_llm()
        mock_bm.return_value = []

        PlannerAgent(llm, _mock_tool_caller()).run(_input())

        assert llm.chat_structured.call_args.kwargs.get("agent_name") == "planner"

    @patch("tiny_agent_harness.agents.planner.agent.build_messages")
    def test_messages_accumulate_across_tool_steps(self, mock_bm):
        tool_output = _output(tool_call=ToolInput(tool="search", arguments={}))
        final_output = _output()
        llm = _mock_llm()
        llm.chat_structured.side_effect = [tool_output, final_output]
        tc = _mock_tool_caller()
        tc.run_call.return_value = ToolResult(tool="search", ok=True, content="results")
        mock_bm.return_value = [{"role": "user", "content": "task"}]

        PlannerAgent(llm, tc).run(_input())

        first_msgs = llm.chat_structured.call_args_list[0].kwargs["messages"]
        second_msgs = llm.chat_structured.call_args_list[1].kwargs["messages"]
        assert len(second_msgs) > len(first_msgs)

# ── build_messages prompt ─────────────────────────────────────────────────────

class TestBuildMessages:
    def test_returns_two_messages(self):
        messages = build_messages(_input(), [])
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

    def test_user_message_contains_task(self):
        messages = build_messages(_input(task="add logging"), [])
        assert "add logging" in messages[1]["content"]

    def test_planner_tools_listed(self):
        messages = build_messages(_input(), [])
        content = messages[1]["content"]
        for tool in PLANNER_TOOLS:
            assert tool in content

    def test_tool_catalog_included(self):
        specs = [ToolSpec(name="list_files", description="list files", arguments_schema={})]
        messages = build_messages(_input(), specs)
        assert "list_files" in messages[1]["content"]

    def test_empty_tool_catalog_shows_none(self):
        messages = build_messages(_input(), [])
        assert "none" in messages[1]["content"]
