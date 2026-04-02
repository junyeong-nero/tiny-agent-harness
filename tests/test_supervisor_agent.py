import pytest
from unittest.mock import MagicMock, patch, call

from tiny_agent_harness.agents.supervisor.agent import SupervisorAgent, _MAX_STEPS
from tiny_agent_harness.agents.supervisor.prompt import build_messages
from tiny_agent_harness.schemas import (
    ExploreInput, ExploreOutput,
    PlannerInput, PlannerOutput,
    VerifierInput, VerifierOutput,
    SupervisorInput, SupervisorOutput,
    WorkerInput, WorkerOutput,
)
from tiny_agent_harness.schemas.agents.planner import Plan
from tiny_agent_harness.schemas.agents.supervisor import SubAgentCall
from tiny_agent_harness.tools.tool_executor import ToolExecutor


# ── helpers ───────────────────────────────────────────────────────────────────

def _sup_input(**kw) -> SupervisorInput:
    return SupervisorInput(**{"task": "build a feature", **kw})


def _step(**kw) -> SupervisorOutput:
    defaults = {"task": "build a feature", "status": "completed", "summary": "done"}
    return SupervisorOutput(**{**defaults, **kw})


def _step_call(agent: str, task: str, summary: str = "delegating") -> SupervisorOutput:
    return SupervisorOutput(
        task="build a feature",
        status="subagent_call",
        subagent_call=SubAgentCall(agent=agent, task=task),
        summary=summary,
    )


def _planner_out(**kw) -> PlannerOutput:
    return PlannerOutput(**{"task": "plan", "status": "completed", "summary": "planned", **kw})


def _worker_out(**kw) -> WorkerOutput:
    return WorkerOutput(**{"task": "work", "status": "completed", "summary": "done", **kw})


def _verifier_out(**kw) -> VerifierOutput:
    return VerifierOutput(**{"task": "review", "status": "completed", "decision": "approve", "feedback": "ok", **kw})


def _mock_llm(*side_effects) -> MagicMock:
    llm = MagicMock()
    if len(side_effects) == 1:
        llm.chat_structured.return_value = side_effects[0]
    else:
        llm.chat_structured.side_effect = list(side_effects)
    return llm


def _mock_tool_executor() -> MagicMock:
    return MagicMock(spec=ToolExecutor)


# ── SubAgentCall schema ───────────────────────────────────────────────────────

class TestSubAgentCall:
    def test_valid_agents(self):
        for agent in ("planner", "worker", "verifier"):
            sc = SubAgentCall(agent=agent, task="do something")
            assert sc.agent == agent

    def test_invalid_agent_rejected(self):
        with pytest.raises(Exception):
            SubAgentCall(agent="unknown", task="x")

    def test_extra_fields_forbidden(self):
        with pytest.raises(Exception):
            SubAgentCall(agent="worker", task="x", extra="y")


# ── SupervisorOutput — step-level fields ─────────────────────────────────────

class TestSupervisorOutputStepFields:
    def test_completed_without_subagent_call(self):
        so = SupervisorOutput(task="t", status="completed", summary="all done")
        assert so.subagent_call is None

    def test_subagent_call_status(self):
        so = SupervisorOutput(
            task="t",
            status="subagent_call",
            subagent_call=SubAgentCall(agent="worker", task="write code"),
            summary="delegating to worker",
        )
        assert so.subagent_call.agent == "worker"

    def test_all_status_values(self):
        for status in ("subagent_call", "completed", "failed"):
            so = SupervisorOutput(task="t", status=status, summary="x")
            assert so.status == status

    def test_invalid_status_rejected(self):
        with pytest.raises(Exception):
            SupervisorOutput(task="t", status="unknown", summary="x")


# ── SupervisorInput / SupervisorOutput schema ─────────────────────────────────

class TestSupervisorSchemas:
    def test_input_requires_task(self):
        with pytest.raises(Exception):
            SupervisorInput()

    def test_output_defaults(self):
        so = SupervisorOutput(task="t", status="completed", summary="ok")
        assert so.planner_outputs == []
        assert so.worker_outputs == []
        assert so.verifier_outputs == []

    def test_output_with_all_subagent_results(self):
        so = SupervisorOutput(
            task="t",
            status="completed",
            summary="ok",
            planner_outputs=[_planner_out()],
            worker_outputs=[_worker_out()],
            verifier_outputs=[_verifier_out()],
        )
        assert len(so.planner_outputs) == 1
        assert len(so.worker_outputs) == 1
        assert len(so.verifier_outputs) == 1

    def test_output_extra_fields_forbidden(self):
        with pytest.raises(Exception):
            SupervisorOutput(task="t", status="completed", summary="ok", unknown="y")


# ── SupervisorAgent construction ──────────────────────────────────────────────

class TestSupervisorAgentInit:
    def test_stores_llm_and_tool_executor(self):
        llm, tc = _mock_llm(_step()), _mock_tool_executor()
        agent = SupervisorAgent(llm, tc)
        assert agent.llm_client is llm
        assert agent.tool_executor is tc


# ── SupervisorAgent.run — no subagent calls ───────────────────────────────────

class TestSupervisorAgentRunDirect:
    def test_returns_completed_without_subagents(self):
        result = SupervisorAgent(_mock_llm(_step(summary="hi there")), _mock_tool_executor()).run(_sup_input())
        assert result.status == "completed"
        assert result.summary == "hi there"

    def test_no_subagent_outputs_when_not_called(self):
        result = SupervisorAgent(_mock_llm(_step()), _mock_tool_executor()).run(_sup_input())
        assert result.planner_outputs == []
        assert result.worker_outputs == []
        assert result.verifier_outputs == []

    def test_single_llm_call_when_no_subagent(self):
        llm = _mock_llm(_step())
        SupervisorAgent(llm, _mock_tool_executor()).run(_sup_input())
        llm.chat_structured.assert_called_once()

    def test_llm_called_with_supervisor_output_schema(self):
        llm = _mock_llm(_step())
        SupervisorAgent(llm, _mock_tool_executor()).run(_sup_input())
        assert llm.chat_structured.call_args.kwargs["response_model"] is SupervisorOutput

    def test_failed_status_propagated(self):
        result = SupervisorAgent(_mock_llm(_step(status="failed", summary="cannot do")), _mock_tool_executor()).run(_sup_input())
        assert result.status == "failed"


# ── SupervisorAgent.run — subagent dispatch ───────────────────────────────────

class TestSupervisorAgentSubagentDispatch:
    @patch("tiny_agent_harness.agents.supervisor.agent.PlannerAgent")
    def test_calls_planner_subagent(self, mock_planner_agent):
        mock_planner_agent.return_value.run.return_value = _planner_out()
        llm = _mock_llm(
            _step_call("planner", "analyze the task"),
            _step(summary="done"),
        )
        tool_executor = _mock_tool_executor()
        result = SupervisorAgent(llm, tool_executor).run(_sup_input())

        mock_planner_agent.assert_called_once_with(llm, tool_executor)
        called_input = mock_planner_agent.return_value.run.call_args.args[0]
        assert isinstance(called_input, PlannerInput)
        assert called_input.task == "analyze the task"
        assert len(result.planner_outputs) == 1

    @patch("tiny_agent_harness.agents.supervisor.agent.WorkerAgent")
    def test_calls_worker_subagent(self, mock_worker_agent):
        mock_worker_agent.return_value.run.return_value = _worker_out()
        llm = _mock_llm(
            _step_call("worker", "implement the feature"),
            _step(summary="done"),
        )
        tool_executor = _mock_tool_executor()
        result = SupervisorAgent(llm, tool_executor).run(_sup_input())

        mock_worker_agent.assert_called_once_with(llm, tool_executor)
        called_input = mock_worker_agent.return_value.run.call_args.args[0]
        assert isinstance(called_input, WorkerInput)
        assert called_input.task == "implement the feature"
        assert len(result.worker_outputs) == 1

    @patch("tiny_agent_harness.agents.supervisor.agent.VerifierAgent")
    def test_calls_verifier_subagent(self, mock_verifier_agent):
        mock_verifier_agent.return_value.run.return_value = _verifier_out()
        llm = _mock_llm(
            _step_call("verifier", "verify the implementation"),
            _step(summary="done"),
        )
        tool_executor = _mock_tool_executor()
        result = SupervisorAgent(llm, tool_executor).run(_sup_input())

        mock_verifier_agent.assert_called_once_with(llm, tool_executor)
        called_input = mock_verifier_agent.return_value.run.call_args.args[0]
        assert isinstance(called_input, VerifierInput)
        assert called_input.task == "verify the implementation"
        assert len(result.verifier_outputs) == 1

    @patch("tiny_agent_harness.agents.supervisor.agent.ExploreAgent")
    def test_calls_explorer_subagent(self, mock_explore_agent):
        mock_explore_agent.return_value.run.return_value = ExploreOutput(
            task="gather context", status="completed", findings="here is the context"
        )
        llm = _mock_llm(
            _step_call("explorer", "gather context"),
            _step(summary="done"),
        )
        tool_executor = _mock_tool_executor()
        result = SupervisorAgent(llm, tool_executor).run(_sup_input())

        mock_explore_agent.assert_called_once_with(llm, tool_executor)
        called_input = mock_explore_agent.return_value.run.call_args.args[0]
        assert isinstance(called_input, ExploreInput)
        assert called_input.task == "gather context"
        assert len(result.explore_outputs) == 1

    @patch("tiny_agent_harness.agents.supervisor.agent.PlannerAgent")
    @patch("tiny_agent_harness.agents.supervisor.agent.WorkerAgent")
    @patch("tiny_agent_harness.agents.supervisor.agent.VerifierAgent")
    def test_full_pipeline_planner_worker_verifier(
        self, mock_verifier_agent, mock_worker_agent, mock_planner_agent
    ):
        mock_planner_agent.return_value.run.return_value = _planner_out()
        mock_worker_agent.return_value.run.return_value = _worker_out()
        mock_verifier_agent.return_value.run.return_value = _verifier_out()
        llm = _mock_llm(
            _step_call("planner", "plan it"),
            _step_call("worker", "do it"),
            _step_call("verifier", "check it"),
            _step(summary="all approved"),
        )

        result = SupervisorAgent(llm, _mock_tool_executor()).run(_sup_input())

        assert result.status == "completed"
        assert len(result.planner_outputs) == 1
        assert len(result.worker_outputs) == 1
        assert len(result.verifier_outputs) == 1

    @patch("tiny_agent_harness.agents.supervisor.agent.WorkerAgent")
    def test_multiple_worker_calls_accumulate(self, mock_worker_agent):
        mock_worker_agent.return_value.run.side_effect = [
            _worker_out(summary="step 1"),
            _worker_out(summary="step 2"),
        ]
        llm = _mock_llm(
            _step_call("worker", "task 1"),
            _step_call("worker", "task 2"),
            _step(summary="done"),
        )

        result = SupervisorAgent(llm, _mock_tool_executor()).run(_sup_input())

        assert len(result.worker_outputs) == 2
        assert result.worker_outputs[0].summary == "step 1"
        assert result.worker_outputs[1].summary == "step 2"

    @patch("tiny_agent_harness.agents.supervisor.agent.WorkerAgent")
    def test_subagent_result_appended_to_messages(self, mock_worker_agent):
        mock_worker_agent.return_value.run.return_value = _worker_out(
            summary="file written"
        )
        llm = _mock_llm(
            _step_call("worker", "write file"),
            _step(summary="done"),
        )

        SupervisorAgent(llm, _mock_tool_executor()).run(_sup_input())

        # Third LLM call (after worker result) should see the result in messages
        second_call_msgs = llm.chat_structured.call_args_list[1].kwargs["messages"]
        last_msg = second_call_msgs[-1]
        assert last_msg["role"] == "user"
        assert "worker" in last_msg["content"]

    def test_stops_after_max_steps(self):
        always_call = _step_call("worker", "do something")
        llm = MagicMock()
        llm.chat_structured.return_value = always_call
        tc = _mock_tool_executor()

        with patch("tiny_agent_harness.agents.supervisor.agent.WorkerAgent") as mock_worker_agent:
            mock_worker_agent.return_value.run.return_value = _worker_out()
            SupervisorAgent(llm, tc).run(_sup_input())

        assert llm.chat_structured.call_count == _MAX_STEPS


# ── build_messages prompt ─────────────────────────────────────────────────────

class TestBuildMessages:
    def test_returns_two_messages(self):
        msgs = build_messages(_sup_input())
        assert len(msgs) == 2
        assert msgs[0]["role"] == "system"
        assert msgs[1]["role"] == "user"

    def test_user_message_contains_task(self):
        msgs = build_messages(_sup_input(task="refactor auth module"))
        assert "refactor auth module" in msgs[1]["content"]

    def test_system_message_lists_all_subagents(self):
        system = build_messages(_sup_input())[0]["content"]
        assert "planner" in system
        assert "worker" in system
        assert "verifier" in system

    def test_system_message_describes_status_values(self):
        system = build_messages(_sup_input())[0]["content"]
        assert "subagent_call" in system
        assert "completed" in system
