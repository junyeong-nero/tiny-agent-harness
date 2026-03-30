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
        self.assertEqual(config.runtime.orchestrator_max_tool_steps, 10)

    def test_load_config_reads_orchestrator_model_and_tool_permissions(self) -> None:
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
                        "  executor:",
                        "    - bash",
                        "  reviewer:",
                        "    - git_diff",
                    ]
                ),
                encoding="utf-8",
            )

            config = load_config(config_path)

            self.assertEqual(config.models.orchestrator, "demo-orchestrator")
            self.assertEqual(config.llm.max_retries, 4)
            self.assertEqual(config.runtime.orchestrator_max_tool_steps, 5)
            self.assertEqual(
                config.tools.as_actor_permissions(),
                {
                    "orchestrator": ["search"],
                    "executor": ["bash"],
                    "reviewer": ["git_diff"],
                },
            )


if __name__ == "__main__":
    unittest.main()
