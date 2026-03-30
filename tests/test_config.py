import sys
import tempfile
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tiny_agent_harness.schemas import load_config


class ConfigTestCase(unittest.TestCase):
    def test_load_config_without_path_reads_packaged_default(self) -> None:
        config = load_config()

        self.assertEqual(config.provider, "openai")
        self.assertEqual(config.models.default, "gpt-4o-mini")
        self.assertEqual(config.models.supervisor, "gpt-4o-mini")
        self.assertEqual(config.models.planner, "gpt-4o-mini")
        self.assertEqual(config.models.orchestrator, "gpt-4o-mini")
        self.assertEqual(config.runtime.supervisor_max_retries, 3)
        self.assertEqual(config.runtime.planner_max_tool_steps, 10)
        self.assertEqual(config.runtime.orchestrator_max_tool_steps, 10)
        self.assertEqual(config.tools.as_actor_permissions()["supervisor"], [])

    def test_load_config_reads_legacy_orchestrator_keys_into_planner_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            config_path.write_text(
                "\n".join(
                    [
                        "provider: openrouter",
                        "models:",
                        "  default: demo-default",
                        "  orchestrator: demo-orchestrator",
                        "llm:",
                        "  max_retries: 4",
                        "runtime:",
                        "  orchestrator_max_tool_steps: 5",
                        "tools:",
                        "  orchestrator:",
                        "    - search",
                        "  worker:",
                        "    - bash",
                        "  reviewer:",
                        "    - git_diff",
                    ]
                ),
                encoding="utf-8",
            )

            config = load_config(config_path)

            self.assertEqual(config.models.planner, "demo-orchestrator")
            self.assertEqual(config.models.orchestrator, "demo-orchestrator")
            self.assertEqual(config.llm.max_retries, 4)
            self.assertEqual(config.runtime.planner_max_tool_steps, 5)
            self.assertEqual(config.runtime.orchestrator_max_tool_steps, 5)
            permissions = config.tools.as_actor_permissions()
            self.assertEqual(permissions["planner"], ["search"])
            self.assertEqual(permissions["orchestrator"], ["search"])
            self.assertEqual(permissions["worker"], ["bash"])
            self.assertEqual(permissions["reviewer"], ["git_diff"])

    def test_load_config_reads_planner_keys_and_keeps_legacy_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            config_path.write_text(
                "\n".join(
                    [
                        "provider: openai",
                        "models:",
                        "  default: demo-default",
                        "  planner: demo-planner",
                        "runtime:",
                        "  planner_max_tool_steps: 7",
                        "tools:",
                        "  planner:",
                        "    - list_files",
                        "    - search",
                    ]
                ),
                encoding="utf-8",
            )

            config = load_config(config_path)

            self.assertEqual(config.models.planner, "demo-planner")
            self.assertEqual(config.models.orchestrator, "demo-planner")
            self.assertEqual(config.runtime.planner_max_tool_steps, 7)
            self.assertEqual(config.runtime.orchestrator_max_tool_steps, 7)
            permissions = config.tools.as_actor_permissions()
            self.assertEqual(permissions["planner"], ["list_files", "search"])
            self.assertEqual(permissions["orchestrator"], ["list_files", "search"])


if __name__ == "__main__":
    unittest.main()
