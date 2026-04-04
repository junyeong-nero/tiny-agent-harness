import pytest
from unittest.mock import MagicMock, patch

from tiny_agent_harness.agents.explore.agent import ExploreAgent
from tiny_agent_harness.agents.explore.prompt import build_messages
from tiny_agent_harness.schemas import (
    ExploreInput,
    ExploreOutput,
    ToolInput,
    ToolResult,
    ToolSpec,
)
from tiny_agent_harness.tools.tool_executor import ToolExecutor


# ── helpers ───────────────────────────────────────────────────────────────────

def _input(**kw) -> ExploreInput:
    return ExploreInput(**{"task": "understand the codebase", **kw})


def _output(**kw) -> ExploreOutput:
    defaults = {"task": "understand the codebase", "status": "completed", "findings": "found it"}
    return ExploreOutput(**{**defaults, **kw})


def _mock_llm(return_value=None) -> MagicMock:
    llm = MagicMock()
    llm.chat_structured.return_value = return_value or _output()
    return llm


def _mock_tool_executor(specs=None) -> MagicMock:
    tc = MagicMock(spec=ToolExecutor)
    tc.available_tool_specs.return_value = specs or []
    return tc


# ── ExploreInput schema ───────────────────────────────────────────────────────

class TestExploreInput:
    def test_task_required(self):
        with pytest.raises(Exception):
            ExploreInput()

    def test_extra_fields_forbidden(self):
        with pytest.raises(Exception):
            ExploreInput(task="t", extra="x")

    def test_valid_input(self):
        ei = ExploreInput(task="read src/")
        assert ei.task == "read src/"


# ── ExploreOutput schema ──────────────────────────────────────────────────────

class TestExploreOutput:
    def test_defaults(self):
        eo = ExploreOutput(task="t", status="completed", findings="ok")
        assert eo.tool_call is None
        assert eo.sources == []

    def test_failed_status(self):
        eo = ExploreOutput(task="t", status="failed", findings="not found")
        assert eo.status == "failed"

    def test_with_sources(self):
        eo = _output(sources=["src/main.py", "README.md"])
        assert eo.sources == ["src/main.py", "README.md"]

    def test_with_tool_call(self):
        eo = _output(tool_call=ToolInput(tool="read_file", arguments={"path": "src/main.py"}))
        assert eo.tool_call.tool == "read_file"

    def test_extra_fields_forbidden(self):
        with pytest.raises(Exception):
            ExploreOutput(task="t", status="completed", findings="x", unknown="y")


# ── ExploreAgent construction ─────────────────────────────────────────────────

class TestExploreAgentInit:
    def test_agent_name_is_explorer(self):
        agent = ExploreAgent(_mock_llm(), _mock_tool_executor())
        assert agent.agent_name == "explorer"

    def test_allowed_tools_are_readonly(self):
        agent = ExploreAgent(_mock_llm(), _mock_tool_executor())
        assert set(agent.allowed_tools) == {"list_files", "search", "read_file", "git_diff"}

    def test_stores_llm_and_tool_executor(self):
        llm, tc = _mock_llm(), _mock_tool_executor()
        agent = ExploreAgent(llm, tc)
        assert agent.client is llm
        assert agent.tool_executor is tc


# ── ExploreAgent.run ──────────────────────────────────────────────────────────

class TestExploreAgentRun:
    @patch("tiny_agent_harness.agents.explore.agent.build_messages")
    def test_returns_immediately_when_no_tool_call(self, mock_bm):
        expected = _output(findings="all context gathered")
        mock_bm.return_value = [{"role": "user", "content": "task"}]

        result = ExploreAgent(_mock_llm(expected), _mock_tool_executor()).run(_input())

        assert result.status == "completed"
        assert result.findings == "all context gathered"

    @patch("tiny_agent_harness.agents.explore.agent.build_messages")
    def test_single_llm_call_when_no_tool_call(self, mock_bm):
        llm = _mock_llm()
        mock_bm.return_value = []

        ExploreAgent(llm, _mock_tool_executor()).run(_input())

        llm.chat_structured.assert_called_once()

    @patch("tiny_agent_harness.agents.explore.agent.build_messages")
    def test_executes_tool_call_then_returns_final(self, mock_bm):
        tool_output = _output(
            tool_call=ToolInput(tool="read_file", arguments={"path": "src/main.py"})
        )
        final_output = _output(findings="read the file", sources=["src/main.py"])
        llm = _mock_llm()
        llm.chat_structured.side_effect = [tool_output, final_output]

        tc = _mock_tool_executor()
        tc.run_call.return_value = ToolResult(tool="read_file", ok=True, content="def main(): ...")
        mock_bm.return_value = [{"role": "user", "content": "task"}]

        result = ExploreAgent(llm, tc).run(_input())

        assert result.findings == "read the file"
        assert result.sources == ["src/main.py"]
        assert llm.chat_structured.call_count == 2
        tc.run_call.assert_called_once()

    @patch("tiny_agent_harness.agents.explore.agent.build_messages")
    def test_tool_executor_receives_explorer_actor(self, mock_bm):
        tool_output = _output(
            tool_call=ToolInput(tool="read_file", arguments={"path": "f.py"})
        )
        llm = _mock_llm()
        llm.chat_structured.side_effect = [tool_output, _output()]
        tc = _mock_tool_executor()
        tc.run_call.return_value = ToolResult(tool="read_file", ok=True, content="x")
        mock_bm.return_value = []

        ExploreAgent(llm, tc).run(_input())

        assert tc.run_call.call_args.kwargs.get("actor") == "explorer"

    @patch("tiny_agent_harness.agents.explore.agent.build_messages")
    def test_llm_called_with_agent_name(self, mock_bm):
        llm = _mock_llm()
        mock_bm.return_value = []

        ExploreAgent(llm, _mock_tool_executor()).run(_input())

        call_kwargs = llm.chat_structured.call_args.kwargs
        assert call_kwargs.get("agent_name") == "explorer"

    @patch("tiny_agent_harness.agents.explore.agent.build_messages")
    def test_llm_called_with_explore_output_schema(self, mock_bm):
        llm = _mock_llm()
        mock_bm.return_value = []

        ExploreAgent(llm, _mock_tool_executor()).run(_input())

        call_kwargs = llm.chat_structured.call_args.kwargs
        assert call_kwargs.get("response_model") is ExploreOutput

    @patch("tiny_agent_harness.agents.explore.agent.build_messages")
    def test_returns_failed_result_when_max_tool_steps_exceeded(self, mock_bm):
        always_tool = _output(tool_call=ToolInput(tool="read_file", arguments={}))
        llm = _mock_llm(always_tool)
        tc = _mock_tool_executor()
        tc.run_call.return_value = ToolResult(tool="read_file", ok=True, content="x")
        mock_bm.return_value = []

        agent = ExploreAgent(llm, tc)
        agent.max_tool_steps = 2
        result = agent.run(_input())

        assert llm.chat_structured.call_count == 2
        assert result.status == "failed"
        assert result.tool_call is None
        assert "max tool steps exceeded" in result.findings


# ── build_messages prompt ─────────────────────────────────────────────────────

class TestBuildMessages:
    def test_returns_two_messages(self):
        messages = build_messages(_input(), [])
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

    def test_user_message_contains_task(self):
        messages = build_messages(_input(task="find auth logic"), [])
        assert "find auth logic" in messages[1]["content"]

    def test_system_message_restricts_to_readonly(self):
        messages = build_messages(_input(), [])
        system = messages[0]["content"]
        assert "NOT modify" in system or "read-only" in system

    def test_tool_catalog_included_in_user_message(self):
        specs = [ToolSpec(name="read_file", description="read a file", arguments_schema={})]
        messages = build_messages(_input(), specs)
        assert "read_file" in messages[1]["content"]
