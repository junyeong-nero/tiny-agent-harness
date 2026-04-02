import pytest
from unittest.mock import MagicMock, patch

from tiny_agent_harness.agents.worker.agent import WorkerAgent
from tiny_agent_harness.agents.worker.prompt import build_messages
from tiny_agent_harness.schemas import (
    ToolInput,
    ToolResult,
    ToolSpec,
    WorkerInput,
    WorkerOutput,
)
from tiny_agent_harness.tools.tool_executor import ToolExecutor


# ── helpers ───────────────────────────────────────────────────────────────────

def _input(**kw) -> WorkerInput:
    return WorkerInput(**{"task": "do something", **kw})


def _output(**kw) -> WorkerOutput:
    defaults = {"task": "do something", "status": "completed", "summary": "done"}
    return WorkerOutput(**{**defaults, **kw})


def _mock_llm(return_value=None) -> MagicMock:
    llm = MagicMock()
    llm.chat_structured.return_value = return_value or _output()
    return llm


def _mock_tool_executor(specs=None) -> MagicMock:
    tc = MagicMock(spec=ToolExecutor)
    tc.available_tool_specs.return_value = specs or []
    return tc


# ── WorkerInput schema ────────────────────────────────────────────────────────

class TestWorkerInput:
    def test_defaults(self):
        wi = WorkerInput(task="explore src/")
        assert wi.task == "explore src/"
        assert wi.kind == "implement"

    def test_all_kind_values(self):
        for kind in ("implement", "verify"):
            assert WorkerInput(task="t", kind=kind).kind == kind

    def test_explore_kind_rejected(self):
        with pytest.raises(Exception):
            WorkerInput(task="t", kind="explore")

    def test_invalid_kind_rejected(self):
        with pytest.raises(Exception):
            WorkerInput(task="t", kind="unknown")

    def test_extra_fields_forbidden(self):
        with pytest.raises(Exception):
            WorkerInput(task="t", extra="x")

    def test_task_required(self):
        with pytest.raises(Exception):
            WorkerInput()


# ── WorkerOutput schema ───────────────────────────────────────────────────────

class TestWorkerOutput:
    def test_defaults(self):
        wo = WorkerOutput(task="t", status="completed", summary="ok")
        assert wo.tool_call is None
        assert wo.artifacts == []
        assert wo.changed_files == []
        assert wo.test_results == []

    def test_failed_status(self):
        wo = WorkerOutput(task="t", status="failed", summary="err")
        assert wo.status == "failed"

    def test_with_tool_call(self):
        wo = _output(tool_call=ToolInput(tool="bash", arguments={"cmd": "ls"}))
        assert wo.tool_call.tool == "bash"
        assert wo.tool_call.arguments == {"cmd": "ls"}

    def test_with_artifacts_and_changed_files(self):
        wo = _output(artifacts=["a.py"], changed_files=["b.py"])
        assert wo.artifacts == ["a.py"]
        assert wo.changed_files == ["b.py"]

    def test_extra_fields_forbidden(self):
        with pytest.raises(Exception):
            WorkerOutput(task="t", status="completed", summary="x", unknown="y")


# ── WorkerAgent construction ──────────────────────────────────────────────────

class TestWorkerAgentInit:
    def test_agent_name_is_worker(self):
        agent = WorkerAgent(_mock_llm(), _mock_tool_executor())
        assert agent.agent_name == "worker"

    def test_max_tool_steps_defaults_to_three(self):
        agent = WorkerAgent(_mock_llm(), _mock_tool_executor())
        assert agent.max_tool_steps == 3

    def test_stores_llm_and_tool_executor(self):
        llm, tc = _mock_llm(), _mock_tool_executor()
        agent = WorkerAgent(llm, tc)
        assert agent.client is llm
        assert agent.tool_executor is tc


# ── WorkerAgent.run ───────────────────────────────────────────────────────────

class TestWorkerAgentRun:
    @patch("tiny_agent_harness.agents.worker.agent.build_messages")
    def test_returns_immediately_when_no_tool_call(self, mock_bm):
        expected = _output(summary="result")
        mock_bm.return_value = [{"role": "user", "content": "task"}]

        result = WorkerAgent(_mock_llm(expected), _mock_tool_executor()).run(_input())

        assert result.status == "completed"
        assert result.summary == "result"

    @patch("tiny_agent_harness.agents.worker.agent.build_messages")
    def test_single_llm_call_when_no_tool_call(self, mock_bm):
        llm = _mock_llm()
        mock_bm.return_value = []

        WorkerAgent(llm, _mock_tool_executor()).run(_input())

        llm.chat_structured.assert_called_once()

    @patch("tiny_agent_harness.agents.worker.agent.build_messages")
    def test_executes_tool_call_then_returns_final(self, mock_bm):
        tool_output = _output(tool_call=ToolInput(tool="bash", arguments={"cmd": "ls"}))
        final_output = _output(summary="final")
        llm = _mock_llm()
        llm.chat_structured.side_effect = [tool_output, final_output]

        tc = _mock_tool_executor()
        tc.run_call.return_value = ToolResult(tool="bash", ok=True, content="file.py")
        mock_bm.return_value = [{"role": "user", "content": "task"}]

        result = WorkerAgent(llm, tc).run(_input())

        assert result.summary == "final"
        assert llm.chat_structured.call_count == 2
        tc.run_call.assert_called_once()

    @patch("tiny_agent_harness.agents.worker.agent.build_messages")
    def test_stops_after_max_tool_steps(self, mock_bm):
        always_tool = _output(tool_call=ToolInput(tool="bash", arguments={}))
        llm = _mock_llm(always_tool)  # always returns tool_call
        tc = _mock_tool_executor()
        tc.run_call.return_value = ToolResult(tool="bash", ok=True, content="x")
        mock_bm.return_value = []

        WorkerAgent(llm, tc).run(_input())  # max_tool_steps == 3 by default

        assert llm.chat_structured.call_count == 3

    @patch("tiny_agent_harness.agents.worker.agent.build_messages")
    def test_messages_accumulate_across_tool_steps(self, mock_bm):
        tool_output = _output(tool_call=ToolInput(tool="bash", arguments={}))
        final_output = _output()
        llm = _mock_llm()
        llm.chat_structured.side_effect = [tool_output, final_output]
        tc = _mock_tool_executor()
        tc.run_call.return_value = ToolResult(tool="bash", ok=True, content="output")
        mock_bm.return_value = [{"role": "user", "content": "task"}]

        WorkerAgent(llm, tc).run(_input())

        first_msgs = llm.chat_structured.call_args_list[0].kwargs["messages"]
        second_msgs = llm.chat_structured.call_args_list[1].kwargs["messages"]
        assert len(second_msgs) > len(first_msgs)

    @patch("tiny_agent_harness.agents.worker.agent.build_messages")
    def test_tool_executor_receives_worker_actor(self, mock_bm):
        tool_output = _output(tool_call=ToolInput(tool="bash", arguments={}))
        llm = _mock_llm()
        llm.chat_structured.side_effect = [tool_output, _output()]
        tc = _mock_tool_executor()
        tc.run_call.return_value = ToolResult(tool="bash", ok=True, content="x")
        mock_bm.return_value = []

        WorkerAgent(llm, tc).run(_input())

        assert tc.run_call.call_args.kwargs.get("actor") == "worker"

    @patch("tiny_agent_harness.agents.worker.agent.build_messages")
    def test_llm_called_with_agent_name(self, mock_bm):
        llm = _mock_llm()
        mock_bm.return_value = []

        WorkerAgent(llm, _mock_tool_executor()).run(_input())

        call_kwargs = llm.chat_structured.call_args.kwargs
        assert call_kwargs.get("agent_name") == "worker"

    @patch("tiny_agent_harness.agents.worker.agent.build_messages")
    def test_llm_called_with_worker_output_schema(self, mock_bm):
        llm = _mock_llm()
        mock_bm.return_value = []

        WorkerAgent(llm, _mock_tool_executor()).run(_input())

        call_kwargs = llm.chat_structured.call_args.kwargs
        assert call_kwargs.get("response_model") is WorkerOutput

# ── build_messages prompt ─────────────────────────────────────────────────────

class TestBuildMessages:
    """
    Documents the schema/prompt mismatch.

    `build_messages` references WorkerInput fields (id, instructions, context,
    allowed_tools) that do not exist in the current schema.  This test will pass
    once the prompt is updated to use the actual WorkerInput fields (task, kind).
    """

    def test_no_error_with_valid_input(self):
        messages = build_messages(_input(), [])
        assert messages is not None

    def test_returns_two_messages(self):
        messages = build_messages(_input(), [])
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

    def test_user_message_contains_task_and_kind(self):
        messages = build_messages(_input(task="write tests", kind="verify"), [])
        content = messages[1]["content"]
        assert "write tests" in content
        assert "verify" in content

    def test_tool_catalog_included_in_user_message(self):
        specs = [ToolSpec(name="bash", description="run shell", arguments_schema={})]
        messages = build_messages(_input(), specs)
        assert "bash" in messages[1]["content"]
