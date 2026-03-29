import sys
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tiny_agent_harness.runtime import run_harness
from tiny_agent_harness.schemas import (
    ExecutorStep,
    OrchestratorStep,
    ReviewerStep,
    ReviewResult,
    RunRequest,
    Task,
    ToolCall,
    ToolRequirement,
    load_config,
)
from tiny_agent_harness.tools import ToolCaller
from tiny_agent_harness.tools.base import ToolResult


class FakeStructuredLLM:
    def __init__(self) -> None:
        self.calls: list[tuple[str, type]] = []

    def chat_structured(self, messages, agent_name, response_model, model=None, max_retries=None):
        self.calls.append((agent_name, response_model))

        if response_model is OrchestratorStep:
            return OrchestratorStep(
                status="completed",
                summary="llm orchestrator task ready",
                task=Task(
                    id="task-llm-1",
                    instructions="llm task",
                    context="llm context",
                    allowed_tools=["bash"],
                ),
            )

        if response_model is ExecutorStep:
            return ExecutorStep(
                status="completed",
                summary="llm executor result",
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
    def test_run_harness_completes_single_mock_cycle(self) -> None:
        config = load_config(ROOT_DIR / "config.yaml")
        request = RunRequest(goal="demo goal")

        state, result = run_harness(request, config)

        self.assertEqual(state.step_count, 1)
        self.assertIsNotNone(state.current_task)
        self.assertEqual(state.current_task.id, "task-1")
        self.assertEqual(state.current_task.instructions, "demo goal")
        self.assertIsNotNone(state.last_executor_result)
        self.assertEqual(state.last_executor_result.status, "completed")
        self.assertIsNotNone(state.last_review_result)
        self.assertEqual(state.last_review_result.decision, "approve")
        self.assertTrue(state.done)
        self.assertEqual(result.status, "completed")

    def test_run_harness_uses_structured_llm_client_when_provided(self) -> None:
        config = load_config(ROOT_DIR / "config.yaml")
        request = RunRequest(goal="demo goal")
        llm_client = FakeStructuredLLM()

        state, result = run_harness(request, config, llm_client=llm_client)

        self.assertEqual(
            llm_client.calls,
            [
                ("orchestrator", OrchestratorStep),
                ("executor", ExecutorStep),
                ("reviewer", ReviewerStep),
            ],
        )
        self.assertEqual(state.current_task.id, "task-llm-1")
        self.assertEqual(state.last_executor_result.summary, "llm executor result")
        self.assertEqual(state.last_review_result.feedback, "llm reviewer approved")
        self.assertEqual(result.status, "completed")

    def test_run_harness_executes_executor_tool_calls_when_tools_are_available(self) -> None:
        class FakeReadFileTool:
            name = "read_file"
            description = "Read a file from the workspace."

            def requirements(self) -> ToolRequirement:
                return ToolRequirement(
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
                self.executor_calls = 0

            def chat_structured(self, messages, agent_name, response_model, model=None, max_retries=None):
                self.calls.append((agent_name, response_model))

                if response_model is OrchestratorStep:
                    return OrchestratorStep(
                        status="completed",
                        summary="task is ready",
                        task=Task(
                            id="task-llm-1",
                            instructions="inspect a file",
                            context="read something first",
                            allowed_tools=["read_file"],
                        ),
                    )

                if response_model is ExecutorStep:
                    self.executor_calls += 1
                    if self.executor_calls == 1:
                        return ExecutorStep(
                            status="tool_call",
                            summary="need to read the file first",
                            tool_call=ToolCall(
                                tool="read_file",
                                arguments={"path": "README.md"},
                            ),
                        )
                    return ExecutorStep(
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
        request = RunRequest(goal="demo goal")
        llm_client = FakeToolAwareLLM()
        read_file_tool = FakeReadFileTool()
        tool_caller = ToolCaller(
            tools={"read_file": read_file_tool},
            actor_permissions={"executor": ["read_file"]},
        )

        state, result = run_harness(
            request,
            config,
            llm_client=llm_client,
            tool_caller=tool_caller,
        )

        self.assertEqual(read_file_tool.last_path, "README.md")
        self.assertEqual(state.last_executor_result.status, "completed")
        self.assertEqual(state.last_executor_result.artifacts, ["README.md"])
        self.assertEqual(state.last_review_result.decision, "approve")
        self.assertEqual(result.status, "completed")

    def test_run_harness_executes_reviewer_tool_calls_when_tools_are_available(self) -> None:
        class FakeGitDiffTool:
            name = "git_diff"
            description = "Show git diff for selected paths."

            def requirements(self) -> ToolRequirement:
                return ToolRequirement(
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

            def chat_structured(self, messages, agent_name, response_model, model=None, max_retries=None):
                self.calls.append((agent_name, response_model))

                if response_model is OrchestratorStep:
                    return OrchestratorStep(
                        status="completed",
                        summary="task is ready",
                        task=Task(
                            id="task-llm-1",
                            instructions="review the README change",
                            context="executor already changed README.md",
                            allowed_tools=["read_file"],
                        ),
                    )

                if response_model is ExecutorStep:
                    return ExecutorStep(
                        status="completed",
                        summary="executor finished the README update",
                        artifacts=["README.md"],
                    )

                if response_model is ReviewerStep:
                    self.reviewer_calls += 1
                    if self.reviewer_calls == 1:
                        return ReviewerStep(
                            status="tool_call",
                            summary="need to inspect the diff first",
                            tool_call=ToolCall(
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
        request = RunRequest(goal="demo goal")
        llm_client = FakeReviewerToolAwareLLM()
        git_diff_tool = FakeGitDiffTool()
        tool_caller = ToolCaller(
            tools={"git_diff": git_diff_tool, "read_file": git_diff_tool},
            actor_permissions={"executor": ["read_file"], "reviewer": ["git_diff"]},
        )

        state, result = run_harness(
            request,
            config,
            llm_client=llm_client,
            tool_caller=tool_caller,
        )

        self.assertEqual(git_diff_tool.last_paths, ["README.md"])
        self.assertEqual(state.last_review_result.decision, "approve")
        self.assertEqual(state.last_review_result.feedback, "review completed after checking the diff")
        self.assertEqual(result.status, "completed")

    def test_run_harness_executes_orchestrator_read_only_tool_calls_when_available(self) -> None:
        class FakeSearchTool:
            name = "search"
            description = "Search for strings in the workspace."

            def requirements(self) -> ToolRequirement:
                return ToolRequirement(
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

        class FakeOrchestratorToolAwareLLM:
            def __init__(self) -> None:
                self.calls: list[tuple[str, type]] = []
                self.orchestrator_calls = 0

            def chat_structured(self, messages, agent_name, response_model, model=None, max_retries=None):
                self.calls.append((agent_name, response_model))

                if response_model is OrchestratorStep:
                    self.orchestrator_calls += 1
                    if self.orchestrator_calls == 1:
                        return OrchestratorStep(
                            status="tool_call",
                            summary="inspect the repo first",
                            tool_call=ToolCall(
                                tool="search",
                                arguments={"pattern": "tiny-agent-harness"},
                            ),
                        )
                    return OrchestratorStep(
                        status="completed",
                        summary="task is ready after inspection",
                        task=Task(
                            id="task-llm-1",
                            instructions="update README based on the repo state",
                            context="README.md mentions tiny-agent-harness",
                            allowed_tools=["read_file"],
                        ),
                    )

                if response_model is ExecutorStep:
                    return ExecutorStep(
                        status="completed",
                        summary="executor finished",
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
        request = RunRequest(goal="demo goal")
        llm_client = FakeOrchestratorToolAwareLLM()
        search_tool = FakeSearchTool()
        tool_caller = ToolCaller(
            tools={"search": search_tool, "read_file": search_tool},
            actor_permissions={"orchestrator": ["search"], "executor": ["read_file"]},
        )

        state, result = run_harness(
            request,
            config,
            llm_client=llm_client,
            tool_caller=tool_caller,
        )

        self.assertEqual(search_tool.last_pattern, "tiny-agent-harness")
        self.assertEqual(state.current_task.instructions, "update README based on the repo state")
        self.assertEqual(state.last_review_result.decision, "approve")
        self.assertEqual(result.status, "completed")


if __name__ == "__main__":
    unittest.main()
