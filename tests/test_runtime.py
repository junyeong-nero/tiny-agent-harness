import sys
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tiny_agent_harness.channels import InputChannel, OutputChannel
from tiny_agent_harness.channels.listener import ListenerChannel
from tiny_agent_harness.agents.planner import planner_agent
from tiny_agent_harness.agents.supervisor import supervisor_agent
from tiny_agent_harness.harness import run_harness
from tiny_agent_harness.schemas import (
    OutputEvent,
    PlannerInput,
    PlannerStep,
    RunRequest,
    RunOutput,
    RunState,
    ReviewerStep,
    ToolInput,
    ToolSpec,
    WorkerStep,
    WorkerInput,
    load_config,
)
from tiny_agent_harness.tools import ToolCaller
from tiny_agent_harness.tools.base import ToolResult


class FakeStructuredLLM:
    def __init__(self) -> None:
        self.calls: list[tuple[str, type]] = []

    def chat_structured(
        self, messages, agent_name, response_model, model=None, max_retries=None
    ):
        self.calls.append((agent_name, response_model))

        if response_model is PlannerStep:
            return PlannerStep(
                status="delegate",
                summary="llm orchestrator task ready",
                task=WorkerInput(
                    id="task-llm-1",
                    instructions="llm task",
                    context="llm context",
                    allowed_tools=["bash"],
                ),
            )

        if response_model is WorkerStep:
            return WorkerStep(
                status="completed",
                summary="llm worker result",
                artifacts=["artifact-1"],
            )

        if response_model is ReviewerStep:
            return ReviewerStep(
                status="completed",
                summary="llm reviewer approved",
                decision="approve",
            )

        raise AssertionError(f"unexpected response model: {response_model}")


class RuntimeTestCase(unittest.TestCase):
    def test_planner_agent_returns_a_task_without_running_worker(self) -> None:
        class FakePlannerOnlyLLM:
            def chat_structured(
                self, messages, agent_name, response_model, model=None, max_retries=None
            ):
                if response_model is not PlannerStep:
                    raise AssertionError(f"unexpected response model: {response_model}")
                return PlannerStep(
                    status="delegate_worker",
                    summary="planner prepared the task",
                    task=WorkerInput(
                        id="task-llm-1",
                        instructions="update README",
                        context="planner context",
                        allowed_tools=["read_file"],
                    ),
                )

        config = load_config(ROOT_DIR / "config.yaml")
        state = PlannerInput(task="update README")
        planner_result = planner_agent(state, config, llm_client=FakePlannerOnlyLLM())

        self.assertEqual(planner_result.task.id, "task-llm-1")
        self.assertEqual(planner_result.reply, None)
        self.assertIsNone(planner_result.worker_result)

    def test_planner_agent_leaves_direct_reply_resolution_to_supervisor(self) -> None:
        class FakePlannerReplyLLM:
            def chat_structured(
                self, messages, agent_name, response_model, model=None, max_retries=None
            ):
                if response_model is not PlannerStep:
                    raise AssertionError(f"unexpected response model: {response_model}")
                return PlannerStep(
                    status="reply",
                    summary="hello from planner",
                )

        config = load_config(ROOT_DIR / "config.yaml")
        state = PlannerInput(task="say hello")

        planner_result = planner_agent(state, config, llm_client=FakePlannerReplyLLM())

        self.assertEqual(len(planner_result.plan), 1)
        self.assertEqual(planner_result.plan[0].status, "reply")
        self.assertIsNone(planner_result.reply)
        self.assertIsNone(planner_result.task)

    def test_supervisor_agent_runs_planner_worker_reviewer_pipeline(self) -> None:
        class FakeSupervisorLLM:
            def __init__(self) -> None:
                self.calls: list[tuple[str, type]] = []

            def chat_structured(
                self, messages, agent_name, response_model, model=None, max_retries=None
            ):
                self.calls.append((agent_name, response_model))

                if response_model is PlannerStep:
                    return PlannerStep(
                        status="delegate_worker",
                        summary="planner prepared the task",
                        task=WorkerInput(
                            id="task-llm-1",
                            instructions="update README",
                            context="planner context",
                            allowed_tools=["read_file"],
                        ),
                    )

                if response_model is WorkerStep:
                    return WorkerStep(
                        status="completed",
                        summary="worker finished",
                        artifacts=["README.md"],
                    )

                if response_model is ReviewerStep:
                    return ReviewerStep(
                        status="completed",
                        summary="review approved",
                        decision="approve",
                    )

                raise AssertionError(f"unexpected response model: {response_model}")

        config = load_config(ROOT_DIR / "config.yaml")
        state = RunState(task="update README")
        llm_client = FakeSupervisorLLM()

        cycle_result = supervisor_agent(state, config, llm_client=llm_client)

        self.assertIsInstance(cycle_result, RunOutput)
        self.assertEqual(cycle_result.task.id, "task-llm-1")
        self.assertEqual(cycle_result.worker_result.status, "completed")
        self.assertEqual(cycle_result.review_result.decision, "approve")
        self.assertTrue(cycle_result.done)
        self.assertEqual(
            llm_client.calls,
            [
                ("planner", PlannerStep),
                ("worker", WorkerStep),
                ("reviewer", ReviewerStep),
            ],
        )

    def test_run_harness_retries_full_supervisor_cycle_after_review_retry(self) -> None:
        class FakeRetryingLLM:
            def __init__(self) -> None:
                self.calls: list[tuple[str, type]] = []
                self.planner_calls = 0
                self.reviewer_calls = 0

            def chat_structured(
                self, messages, agent_name, response_model, model=None, max_retries=None
            ):
                self.calls.append((agent_name, response_model))

                if response_model is PlannerStep:
                    self.planner_calls += 1
                    return PlannerStep(
                        status="delegate_worker",
                        summary=f"planner attempt {self.planner_calls}",
                        task=WorkerInput(
                            id=f"task-llm-{self.planner_calls}",
                            instructions=f"attempt {self.planner_calls}",
                            context=f"context {self.planner_calls}",
                            allowed_tools=["bash"],
                        ),
                    )

                if response_model is WorkerStep:
                    return WorkerStep(
                        status="completed",
                        summary="worker completed the delegated task",
                        artifacts=["artifact.txt"],
                    )

                if response_model is ReviewerStep:
                    self.reviewer_calls += 1
                    if self.reviewer_calls == 1:
                        return ReviewerStep(
                            status="completed",
                            summary="needs another pass",
                            decision="retry",
                        )
                    return ReviewerStep(
                        status="completed",
                        summary="looks good now",
                        decision="approve",
                    )

                raise AssertionError(f"unexpected response model: {response_model}")

        config = load_config(ROOT_DIR / "config.yaml")
        request = RunRequest(prompt="demo goal")
        llm_client = FakeRetryingLLM()

        state, result = run_harness(request, config, llm_client=llm_client)

        self.assertEqual(
            llm_client.calls,
            [
                ("planner", PlannerStep),
                ("worker", WorkerStep),
                ("reviewer", ReviewerStep),
                ("planner", PlannerStep),
                ("worker", WorkerStep),
                ("reviewer", ReviewerStep),
            ],
        )
        self.assertEqual(state.step_count, 2)
        self.assertEqual(state.review_cycles, 2)
        self.assertEqual(
            [task.id for task in state.completed_subtasks], ["task-llm-1", "task-llm-2"]
        )
        self.assertEqual(len(state.worker_results), 2)
        self.assertEqual(state.current_task.id, "task-llm-2")
        self.assertEqual(state.last_review_result.decision, "approve")
        self.assertTrue(state.done)
        self.assertEqual(result.status, "completed")

    def test_run_harness_completes_single_mock_cycle(self) -> None:
        config = load_config(ROOT_DIR / "config.yaml")
        request = RunRequest(prompt="demo goal")

        state, result = run_harness(request, config)

        self.assertEqual(state.step_count, 1)
        self.assertIsNotNone(state.current_task)
        self.assertEqual(state.current_task.id, "task-1")
        self.assertEqual(state.current_task.instructions, "demo goal")
        self.assertIsNotNone(state.last_worker_result)
        self.assertEqual(state.last_worker_result.status, "completed")
        self.assertIsNotNone(state.last_review_result)
        self.assertEqual(state.last_review_result.decision, "approve")
        self.assertTrue(state.done)
        self.assertEqual(result.status, "completed")

    def test_run_harness_emits_listener_events_and_output(self) -> None:
        config = load_config(ROOT_DIR / "config.yaml")
        request = RunRequest(prompt="demo goal")
        input_channel = InputChannel()
        queued_request = input_channel.queue(request.prompt, session_id="session-a")
        listeners = ListenerChannel()
        listener_events = []
        listeners.add_channel(
            "collector", lambda _, event: listener_events.append(event)
        )
        output_handler = OutputChannel()
        outputs: list[OutputEvent] = []
        output_handler.add_channel("collector", lambda _, event: outputs.append(event))

        state, result = run_harness(
            request,
            config,
            listeners=listeners,
            output_handler=output_handler,
            input_channel=input_channel,
        )

        self.assertEqual(
            [event.kind for event in listener_events], ["run_started", "run_completed"]
        )
        self.assertEqual(outputs[0].session_id, queued_request.session_id)
        self.assertEqual(outputs[0].payload.request, request)
        self.assertEqual(outputs[0].payload.state, state)
        self.assertEqual(outputs[0].payload.result, result)

    def test_run_harness_uses_structured_llm_client_when_provided(self) -> None:
        config = load_config(ROOT_DIR / "config.yaml")
        request = RunRequest(prompt="demo goal")
        llm_client = FakeStructuredLLM()

        state, result = run_harness(request, config, llm_client=llm_client)

        self.assertEqual(
            llm_client.calls,
            [
                ("planner", PlannerStep),
                ("worker", WorkerStep),
                ("reviewer", ReviewerStep),
            ],
        )
        self.assertEqual(state.current_task.id, "task-llm-1")
        self.assertEqual(state.last_worker_result.summary, "llm worker result")
        self.assertEqual(state.last_review_result.feedback, "llm reviewer approved")
        self.assertEqual(result.status, "completed")

    def test_run_harness_executes_worker_tool_calls_when_tools_are_available(
        self,
    ) -> None:
        class FakeReadFileTool:
            name = "read_file"
            description = "Read a file from the workspace."

            def requirements(self) -> ToolSpec:
                return ToolSpec(
                    name=self.name,
                    description=self.description,
                    arguments_schema={
                        "type": "object",
                        "properties": {"path": {"type": "string"}},
                    },
                )

            def run(self, arguments: dict) -> ToolResult:
                self.last_path = arguments["path"]
                return ToolResult(
                    tool="read_file",
                    ok=True,
                    content="file contents",
                )

        class FakeToolAwareLLM:
            def __init__(self) -> None:
                self.calls: list[tuple[str, type]] = []
                self.worker_calls = 0

            def chat_structured(
                self, messages, agent_name, response_model, model=None, max_retries=None
            ):
                self.calls.append((agent_name, response_model))

                if response_model is PlannerStep:
                    return PlannerStep(
                        status="delegate",
                        summary="task is ready",
                        task=WorkerInput(
                            id="task-llm-1",
                            instructions="inspect a file",
                            context="read something first",
                            allowed_tools=["read_file"],
                        ),
                    )

                if response_model is WorkerStep:
                    self.worker_calls += 1
                    if self.worker_calls == 1:
                        return WorkerStep(
                            status="tool_call",
                            summary="need to read the file first",
                            tool_call=ToolInput(
                                tool="read_file",
                                arguments={"path": "README.md"},
                            ),
                        )
                    return WorkerStep(
                        status="completed",
                        summary="used the tool result and completed the task",
                        artifacts=["README.md"],
                    )

                if response_model is ReviewerStep:
                    return ReviewerStep(
                        status="completed",
                        summary="looks good",
                        decision="approve",
                    )

                raise AssertionError(f"unexpected response model: {response_model}")

        config = load_config(ROOT_DIR / "config.yaml")
        request = RunRequest(prompt="demo goal")
        llm_client = FakeToolAwareLLM()
        read_file_tool = FakeReadFileTool()
        tool_caller = ToolCaller(
            tools={"read_file": read_file_tool},
            actor_permissions={"worker": ["read_file"]},
        )

        state, result = run_harness(
            request,
            config,
            llm_client=llm_client,
            tool_caller=tool_caller,
        )

        self.assertEqual(read_file_tool.last_path, "README.md")
        self.assertEqual(state.last_worker_result.status, "completed")
        self.assertEqual(state.last_worker_result.artifacts, ["README.md"])
        self.assertEqual(state.last_review_result.decision, "approve")
        self.assertEqual(result.status, "completed")

    def test_run_harness_executes_reviewer_tool_calls_when_tools_are_available(
        self,
    ) -> None:
        class FakeGitDiffTool:
            name = "git_diff"
            description = "Show git diff for selected paths."

            def requirements(self) -> ToolSpec:
                return ToolSpec(
                    name=self.name,
                    description=self.description,
                    arguments_schema={
                        "type": "object",
                        "properties": {
                            "paths": {"type": "array", "items": {"type": "string"}},
                            "staged": {"type": "boolean"},
                        },
                    },
                )

            def run(self, arguments: dict) -> ToolResult:
                self.last_paths = arguments.get("paths", [])
                return ToolResult(
                    tool="git_diff",
                    ok=True,
                    content="diff --git a/README.md b/README.md",
                )

        class FakeReviewerToolAwareLLM:
            def __init__(self) -> None:
                self.calls: list[tuple[str, type]] = []
                self.reviewer_calls = 0

            def chat_structured(
                self, messages, agent_name, response_model, model=None, max_retries=None
            ):
                self.calls.append((agent_name, response_model))

                if response_model is PlannerStep:
                    return PlannerStep(
                        status="delegate",
                        summary="task is ready",
                        task=WorkerInput(
                            id="task-llm-1",
                            instructions="review the README change",
                            context="worker already changed README.md",
                            allowed_tools=["read_file"],
                        ),
                    )

                if response_model is WorkerStep:
                    return WorkerStep(
                        status="completed",
                        summary="worker finished the README update",
                        artifacts=["README.md"],
                    )

                if response_model is ReviewerStep:
                    self.reviewer_calls += 1
                    if self.reviewer_calls == 1:
                        return ReviewerStep(
                            status="tool_call",
                            summary="need to inspect the diff first",
                            tool_call=ToolInput(
                                tool="git_diff",
                                arguments={"paths": ["README.md"]},
                            ),
                        )
                    return ReviewerStep(
                        status="completed",
                        summary="review completed after checking the diff",
                        decision="approve",
                    )

                raise AssertionError(f"unexpected response model: {response_model}")

        config = load_config(ROOT_DIR / "config.yaml")
        request = RunRequest(prompt="demo goal")
        llm_client = FakeReviewerToolAwareLLM()
        git_diff_tool = FakeGitDiffTool()
        tool_caller = ToolCaller(
            tools={"git_diff": git_diff_tool},
            actor_permissions={"reviewer": ["git_diff"]},
        )

        state, result = run_harness(
            request,
            config,
            llm_client=llm_client,
            tool_caller=tool_caller,
        )

        self.assertEqual(git_diff_tool.last_paths, ["README.md"])
        self.assertEqual(state.last_review_result.decision, "approve")
        self.assertEqual(
            state.last_review_result.feedback,
            "review completed after checking the diff",
        )
        self.assertEqual(result.status, "completed")

    def test_run_harness_executes_planner_read_only_tool_calls_when_available(
        self,
    ) -> None:
        class FakeSearchTool:
            name = "search"
            description = "Search for strings in the workspace."

            def requirements(self) -> ToolSpec:
                return ToolSpec(
                    name=self.name,
                    description=self.description,
                    arguments_schema={
                        "type": "object",
                        "properties": {"pattern": {"type": "string"}},
                    },
                )

            def run(self, arguments: dict) -> ToolResult:
                self.last_pattern = arguments["pattern"]
                return ToolResult(
                    tool="search",
                    ok=True,
                    content="README.md:1:tiny-agent-harness",
                )

        class FakePlannerToolAwareLLM:
            def __init__(self) -> None:
                self.calls: list[tuple[str, type]] = []
                self.planner_calls = 0

            def chat_structured(
                self, messages, agent_name, response_model, model=None, max_retries=None
            ):
                self.calls.append((agent_name, response_model))

                if response_model is PlannerStep:
                    self.planner_calls += 1
                    if self.planner_calls == 1:
                        return PlannerStep(
                            status="tool_call",
                            summary="inspect the repo first",
                            tool_call=ToolInput(
                                tool="search",
                                arguments={"pattern": "tiny-agent-harness"},
                            ),
                        )
                    return PlannerStep(
                        status="delegate",
                        summary="task is ready after inspection",
                        task=WorkerInput(
                            id="task-llm-1",
                            instructions="update README based on the repo state",
                            context="README.md mentions tiny-agent-harness",
                            allowed_tools=["read_file"],
                        ),
                    )

                if response_model is WorkerStep:
                    return WorkerStep(
                        status="completed",
                        summary="worker finished",
                        artifacts=["README.md"],
                    )

                if response_model is ReviewerStep:
                    return ReviewerStep(
                        status="completed",
                        summary="review approved",
                        decision="approve",
                    )

                raise AssertionError(f"unexpected response model: {response_model}")

        config = load_config(ROOT_DIR / "config.yaml")
        request = RunRequest(prompt="demo goal")
        llm_client = FakePlannerToolAwareLLM()
        search_tool = FakeSearchTool()
        tool_caller = ToolCaller(
            tools={"search": search_tool},
            actor_permissions={"planner": ["search"]},
        )

        state, result = run_harness(
            request,
            config,
            llm_client=llm_client,
            tool_caller=tool_caller,
        )

        self.assertEqual(search_tool.last_pattern, "tiny-agent-harness")
        self.assertEqual(
            state.current_task.instructions, "update README based on the repo state"
        )
        self.assertEqual(state.last_review_result.decision, "approve")
        self.assertEqual(result.status, "completed")

    def test_run_harness_falls_back_when_planner_exceeds_tool_steps(self) -> None:
        class FakeSearchTool:
            name = "search"
            description = "Search for strings in the workspace."

            def requirements(self) -> ToolSpec:
                return ToolSpec(
                    name=self.name,
                    description=self.description,
                    arguments_schema={
                        "type": "object",
                        "properties": {"pattern": {"type": "string"}},
                    },
                )

            def run(self, arguments: dict) -> ToolResult:
                return ToolResult(
                    tool="search",
                    ok=True,
                    content="README.md:1:tiny-agent-harness",
                )

        class LoopingPlannerLLM:
            def chat_structured(
                self, messages, agent_name, response_model, model=None, max_retries=None
            ):
                if response_model is PlannerStep:
                    return PlannerStep(
                        status="tool_call",
                        summary="inspect again",
                        tool_call=ToolInput(
                            tool="search",
                            arguments={"pattern": "tiny-agent-harness"},
                        ),
                    )

                if response_model is WorkerStep:
                    return WorkerStep(
                        status="completed",
                        summary="worker completed fallback task",
                        artifacts=["README.md"],
                    )

                if response_model is ReviewerStep:
                    return ReviewerStep(
                        status="completed",
                        summary="review approved fallback path",
                        decision="approve",
                    )

                raise AssertionError(f"unexpected response model: {response_model}")

        config = load_config(ROOT_DIR / "config.yaml")
        request = RunRequest(prompt="introduce yourself")
        llm_client = LoopingPlannerLLM()
        search_tool = FakeSearchTool()
        tool_caller = ToolCaller(
            tools={"search": search_tool},
            actor_permissions={"planner": ["search"]},
        )

        state, result = run_harness(
            request,
            config,
            llm_client=llm_client,
            tool_caller=tool_caller,
        )

        self.assertIn("planner exceeded maximum tool steps", state.current_task.context)
        self.assertEqual(state.current_task.instructions, "introduce yourself")
        self.assertEqual(state.last_review_result.decision, "approve")
        self.assertEqual(result.status, "completed")

    def test_run_harness_supports_planner_direct_reply_without_worker(self) -> None:
        class FakeDirectReplyLLM:
            def __init__(self) -> None:
                self.calls: list[tuple[str, type]] = []

            def chat_structured(
                self, messages, agent_name, response_model, model=None, max_retries=None
            ):
                self.calls.append((agent_name, response_model))

                if response_model is PlannerStep:
                    return PlannerStep(
                        status="reply",
                        summary="hello from planner",
                    )

                if response_model is ReviewerStep:
                    return ReviewerStep(
                        status="completed",
                        summary="direct reply is acceptable",
                        decision="approve",
                    )

                raise AssertionError(f"unexpected response model: {response_model}")

        config = load_config(ROOT_DIR / "config.yaml")
        request = RunRequest(prompt="say hello")
        llm_client = FakeDirectReplyLLM()

        state, result = run_harness(request, config, llm_client=llm_client)

        self.assertEqual(
            llm_client.calls,
            [
                ("planner", PlannerStep),
                ("reviewer", ReviewerStep),
            ],
        )
        self.assertIsNone(state.current_task)
        self.assertIsNone(state.last_worker_result)
        self.assertEqual(state.last_review_result.decision, "approve")
        self.assertTrue(state.done)
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.summary, "prompt='say hello' reply='hello from planner' review_decision='approve'")


if __name__ == "__main__":
    unittest.main()
