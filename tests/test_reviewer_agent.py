import pytest
from unittest.mock import MagicMock, patch

from tiny_agent_harness.agents.reviewer.agent import ReviewerAgent
from tiny_agent_harness.agents.reviewer.prompt import build_messages
from tiny_agent_harness.schemas import (
    ReviewerInput,
    ReviewerOutput,
    ToolInput,
    ToolResult,
    ToolSpec,
)
from tiny_agent_harness.tools.tool_executor import ToolExecutor


# ── helpers ───────────────────────────────────────────────────────────────────

def _input(**kw) -> ReviewerInput:
    return ReviewerInput(**{"task": "implement feature X", **kw})


def _output(**kw) -> ReviewerOutput:
    defaults = {
        "task": "implement feature X",
        "status": "completed",
        "decision": "approve",
        "feedback": "looks good",
    }
    return ReviewerOutput(**{**defaults, **kw})


def _mock_llm(return_value=None) -> MagicMock:
    llm = MagicMock()
    llm.chat_structured.return_value = return_value or _output()
    return llm


def _mock_tool_executor(specs=None) -> MagicMock:
    tc = MagicMock(spec=ToolExecutor)
    tc.available_tool_specs.return_value = specs or []
    return tc


# ── ReviewerInput schema ──────────────────────────────────────────────────────

class TestReviewerInput:
    def test_valid_input(self):
        ri = ReviewerInput(task="write unit tests for auth.py")
        assert ri.task == "write unit tests for auth.py"

    def test_task_required(self):
        with pytest.raises(Exception):
            ReviewerInput()

    def test_extra_fields_forbidden(self):
        with pytest.raises(Exception):
            ReviewerInput(task="t", unknown="x")


# ── ReviewerOutput schema ─────────────────────────────────────────────────────

class TestReviewerOutput:
    def test_approve_decision(self):
        ro = ReviewerOutput(task="t", status="completed", decision="approve", feedback="ok")
        assert ro.decision == "approve"
        assert ro.tool_call is None

    def test_retry_decision(self):
        ro = ReviewerOutput(task="t", status="completed", decision="retry", feedback="missing tests")
        assert ro.decision == "retry"

    def test_all_status_values(self):
        for status in ("completed", "failed"):
            ro = ReviewerOutput(task="t", status=status, decision="approve", feedback="x")
            assert ro.status == status

    def test_invalid_decision_rejected(self):
        with pytest.raises(Exception):
            ReviewerOutput(task="t", status="completed", decision="unknown", feedback="x")

    def test_with_tool_call(self):
        ro = _output(tool_call=ToolInput(tool="read_file", arguments={"path": "main.py"}))
        assert ro.tool_call.tool == "read_file"

    def test_extra_fields_forbidden(self):
        with pytest.raises(Exception):
            ReviewerOutput(task="t", status="completed", decision="approve", feedback="x", unknown="y")


# ── ReviewerAgent construction ────────────────────────────────────────────────

class TestReviewerAgentInit:
    def test_agent_name_is_reviewer(self):
        agent = ReviewerAgent(_mock_llm(), _mock_tool_executor())
        assert agent.agent_name == "reviewer"

    def test_max_tool_steps_defaults_to_three(self):
        agent = ReviewerAgent(_mock_llm(), _mock_tool_executor())
        assert agent.max_tool_steps == 3

    def test_stores_llm_and_tool_executor(self):
        llm, tc = _mock_llm(), _mock_tool_executor()
        agent = ReviewerAgent(llm, tc)
        assert agent.client is llm
        assert agent.tool_executor is tc


# ── ReviewerAgent.run ─────────────────────────────────────────────────────────

class TestReviewerAgentRun:
    @patch("tiny_agent_harness.agents.reviewer.agent.build_messages")
    def test_returns_approve_decision(self, mock_bm):
        mock_bm.return_value = [{"role": "user", "content": "review"}]
        expected = _output(decision="approve", feedback="task completed correctly")

        result = ReviewerAgent(_mock_llm(expected), _mock_tool_executor()).run(_input())

        assert result.decision == "approve"
        assert result.feedback == "task completed correctly"

    @patch("tiny_agent_harness.agents.reviewer.agent.build_messages")
    def test_returns_retry_when_task_incomplete(self, mock_bm):
        mock_bm.return_value = []
        expected = _output(decision="retry", feedback="no tests were written")

        result = ReviewerAgent(_mock_llm(expected), _mock_tool_executor()).run(_input())

        assert result.decision == "retry"
        assert "tests" in result.feedback

    @patch("tiny_agent_harness.agents.reviewer.agent.build_messages")
    def test_single_llm_call_when_no_tool_call(self, mock_bm):
        llm = _mock_llm()
        mock_bm.return_value = []

        ReviewerAgent(llm, _mock_tool_executor()).run(_input())

        llm.chat_structured.assert_called_once()

    @patch("tiny_agent_harness.agents.reviewer.agent.build_messages")
    def test_inspects_workspace_then_returns_decision(self, mock_bm):
        tool_output = _output(tool_call=ToolInput(tool="read_file", arguments={"path": "main.py"}))
        final_output = _output(decision="approve", feedback="implementation verified")
        llm = _mock_llm()
        llm.chat_structured.side_effect = [tool_output, final_output]
        tc = _mock_tool_executor()
        tc.run_call.return_value = ToolResult(tool="read_file", ok=True, content="def foo(): ...")
        mock_bm.return_value = [{"role": "user", "content": "review"}]

        result = ReviewerAgent(llm, tc).run(_input())

        assert result.decision == "approve"
        assert llm.chat_structured.call_count == 2
        tc.run_call.assert_called_once()

    @patch("tiny_agent_harness.agents.reviewer.agent.build_messages")
    def test_stops_after_max_tool_steps(self, mock_bm):
        always_tool = _output(tool_call=ToolInput(tool="read_file", arguments={}))
        llm = _mock_llm(always_tool)
        tc = _mock_tool_executor()
        tc.run_call.return_value = ToolResult(tool="read_file", ok=True, content="x")
        mock_bm.return_value = []

        ReviewerAgent(llm, tc).run(_input())

        assert llm.chat_structured.call_count == 3

    @patch("tiny_agent_harness.agents.reviewer.agent.build_messages")
    def test_tool_executor_receives_reviewer_actor(self, mock_bm):
        tool_output = _output(tool_call=ToolInput(tool="read_file", arguments={}))
        llm = _mock_llm()
        llm.chat_structured.side_effect = [tool_output, _output()]
        tc = _mock_tool_executor()
        tc.run_call.return_value = ToolResult(tool="read_file", ok=True, content="x")
        mock_bm.return_value = []

        ReviewerAgent(llm, tc).run(_input())

        assert tc.run_call.call_args.kwargs.get("actor") == "reviewer"

    @patch("tiny_agent_harness.agents.reviewer.agent.build_messages")
    def test_llm_called_with_reviewer_output_schema(self, mock_bm):
        llm = _mock_llm()
        mock_bm.return_value = []

        ReviewerAgent(llm, _mock_tool_executor()).run(_input())

        assert llm.chat_structured.call_args.kwargs.get("response_model") is ReviewerOutput

    @patch("tiny_agent_harness.agents.reviewer.agent.build_messages")
    def test_messages_accumulate_across_tool_steps(self, mock_bm):
        tool_output = _output(tool_call=ToolInput(tool="read_file", arguments={}))
        final_output = _output()
        llm = _mock_llm()
        llm.chat_structured.side_effect = [tool_output, final_output]
        tc = _mock_tool_executor()
        tc.run_call.return_value = ToolResult(tool="read_file", ok=True, content="content")
        mock_bm.return_value = [{"role": "user", "content": "review"}]

        ReviewerAgent(llm, tc).run(_input())

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
        messages = build_messages(_input(task="add error handling to parser.py"), [])
        assert "add error handling to parser.py" in messages[1]["content"]

    def test_system_message_mentions_approve_and_retry(self):
        messages = build_messages(_input(), [])
        system_content = messages[0]["content"]
        assert "approve" in system_content.lower()
        assert "retry" in system_content.lower()

    def test_tool_catalog_included(self):
        specs = [ToolSpec(name="read_file", description="read a file", arguments_schema={})]
        messages = build_messages(_input(), specs)
        assert "read_file" in messages[1]["content"]

    def test_empty_tool_catalog_shows_none(self):
        messages = build_messages(_input(), [])
        assert "none" in messages[1]["content"]
