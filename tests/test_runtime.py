import sys
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tiny_agent_harness.runtime import run_harness
from tiny_agent_harness.schemas import ExecutorResult, ReviewResult, RunRequest, Task, load_config


class FakeStructuredLLM:
    def __init__(self) -> None:
        self.calls: list[tuple[str, type]] = []

    def chat_structured(self, messages, agent_name, response_model, model=None, max_retries=None):
        self.calls.append((agent_name, response_model))

        if response_model is Task:
            return Task(
                id="task-llm-1",
                instructions="llm task",
                context="llm context",
                allowed_tools=["bash"],
            )

        if response_model is ExecutorResult:
            return ExecutorResult(
                status="completed",
                summary="llm executor result",
                artifacts=["artifact-1"],
            )

        if response_model is ReviewResult:
            return ReviewResult(
                decision="approve",
                feedback="llm reviewer approved",
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
                ("main_loop", Task),
                ("executor", ExecutorResult),
                ("reviewer", ReviewResult),
            ],
        )
        self.assertEqual(state.current_task.id, "task-llm-1")
        self.assertEqual(state.last_executor_result.summary, "llm executor result")
        self.assertEqual(state.last_review_result.feedback, "llm reviewer approved")
        self.assertEqual(result.status, "completed")


if __name__ == "__main__":
    unittest.main()
